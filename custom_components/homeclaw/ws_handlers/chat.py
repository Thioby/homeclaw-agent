"""WebSocket handlers for chat messaging (send, stream, RAG post-conversation)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..channels.intake import MessageIntake
from ..const import DOMAIN
from ..file_processor import (
    FileProcessingError,
    process_attachments,
)
from ..storage import Message, SessionStorage
from ._common import (
    ERR_SESSION_NOT_FOUND,
    ERR_STORAGE_ERROR,
    _get_storage,
    _get_user_id,
    _validate_message,
    _validate_session_id,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def _rag_post_conversation(
    hass: HomeAssistant,
    *,
    session_id: str,
    user_id: str,
    user_text: str,
    assistant_text: str,
    storage: SessionStorage,
) -> None:
    """Run RAG post-conversation tasks: semantic learning + session indexing + memory capture.

    Called after both streaming and non-streaming message handlers.
    Errors are caught and logged -- never fails the main response flow.

    Args:
        hass: Home Assistant instance.
        session_id: Current conversation session ID.
        user_id: ID of the user who sent the message.
        user_text: The user's message text.
        assistant_text: The assistant's response text.
        storage: SessionStorage for loading session messages.
    """
    if DOMAIN not in hass.data:
        return

    rag_manager = hass.data[DOMAIN].get("rag_manager")
    if not rag_manager or not rag_manager.is_initialized:
        return

    # 1. Semantic learning (category corrections from conversation)
    try:
        await rag_manager.learn_from_conversation(
            user_message=user_text,
            assistant_message=assistant_text,
        )
    except Exception as learn_err:
        _LOGGER.debug("RAG learn_from_conversation failed: %s", learn_err)

    # 2. Session indexing — DISABLED (moved to session creation)
    # Sessions are now sanitized via LLM and indexed when the user creates
    # a new session (see ws_handlers/sessions.py _sanitize_previous_session).
    # This removes ephemeral state data (temperatures, on/off reports) that
    # would otherwise mislead the agent with stale values.

    # 3. Explicit command capture (safety net for "zapamiętaj"/"remember")
    # All other memory capture is handled by the LLM via memory_store tool
    # and AI-powered flush before compaction.
    try:
        recent_msgs = [
            {"role": "user", "content": user_text},
        ]
        captured = await rag_manager.capture_explicit_commands(
            messages=recent_msgs,
            user_id=user_id,
            session_id=session_id,
        )
        if captured:
            _LOGGER.info("Captured %d explicit memory commands", captured)
    except Exception as mem_err:
        _LOGGER.debug("Explicit memory capture failed: %s", mem_err)


async def _build_conversation_history(
    hass: HomeAssistant,
    messages: list[Message],
    max_image_messages: int = 5,
) -> list[dict[str, Any]]:
    """Build conversation history dicts, reconstructing _images for historical messages.

    For user messages that had image attachments, we read the full-resolution image
    from disk and attach it as _images so the AI provider can "see" images from
    earlier in the conversation.

    Only the most recent `max_image_messages` user messages with images are
    reconstructed to avoid context window bloat.

    Args:
        messages: List of Message objects from storage (excluding the current message).
        max_image_messages: Max number of historical image messages to reconstruct.

    Returns:
        List of message dicts with role, content, and optionally _images.
    """
    import base64

    history: list[dict[str, Any]] = []

    # First pass: identify which messages have image attachments
    image_msg_indices: list[int] = []
    for i, m in enumerate(messages):
        if m.role == "user" and m.attachments:
            has_images = any(a.get("is_image") for a in m.attachments)
            if has_images:
                image_msg_indices.append(i)

    # Only reconstruct the most recent N image messages
    reconstruct_set = set(image_msg_indices[-max_image_messages:])

    for i, m in enumerate(messages):
        # Reconstruct tool_use → assistant message with tool call JSON
        if m.role == "tool_use" and m.content_blocks:
            from ..core.tool_call_codec import build_assistant_tool_message

            tool_calls = [
                {
                    "id": block.get("id", block.get("name", "unknown")),
                    "name": block["name"],
                    "args": block.get("arguments", {}),
                }
                for block in m.content_blocks
                if block.get("type") == "tool_call"
            ]
            if tool_calls:
                history.append(
                    {
                        "role": "assistant",
                        "content": build_assistant_tool_message(tool_calls),
                    }
                )
            continue

        # Reconstruct tool_result → function message (internal format)
        if m.role == "tool_result" and m.content_blocks:
            for block in m.content_blocks:
                if block.get("type") == "tool_result":
                    history.append(
                        {
                            "role": "function",
                            "name": block.get("name", "unknown"),
                            "tool_use_id": block.get("tool_call_id", m.tool_call_id),
                            "content": block.get("content", m.content),
                        }
                    )
            continue

        # Regular message (user/assistant/system)
        msg_dict: dict[str, Any] = {"role": m.role, "content": m.content}

        if i in reconstruct_set:
            # Reconstruct _images from stored attachments
            images: list[dict[str, Any]] = []
            for att in m.attachments:
                if not att.get("is_image"):
                    continue
                storage_path = att.get("storage_path", "")
                if not storage_path:
                    continue
                try:
                    raw = await hass.async_add_executor_job(
                        _read_binary_file,
                        storage_path,
                    )
                    b64 = base64.b64encode(raw).decode("ascii")
                    images.append(
                        {
                            "mime_type": att.get("mime_type", "image/jpeg"),
                            "data": b64,
                            "filename": att.get("filename", "image"),
                        }
                    )
                except (OSError, IOError) as err:
                    _LOGGER.debug(
                        "Could not read historical image %s: %s",
                        storage_path,
                        err,
                    )
            if images:
                msg_dict["_images"] = images

        history.append(msg_dict)

    return history


def _read_binary_file(path: str) -> bytes:
    """Read binary file content from disk (executor-only)."""
    with open(path, "rb") as f:
        return f.read()


async def _persist_tool_messages(
    storage: SessionStorage,
    session_id: str,
    event: Any,
    timestamp: str,
) -> None:
    """Persist tool_use and tool_result events to storage.

    Args:
        storage: SessionStorage instance.
        session_id: Current session ID.
        event: AgentEvent (ToolCallEvent or ToolResultEvent).
        timestamp: ISO timestamp for the message.
    """
    event_type = getattr(event, "type", None)

    if event_type == "tool_call":
        args_summary = json.dumps(getattr(event, "tool_args", {}), ensure_ascii=False)[
            :200
        ]
        tool_msg = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role="tool_use",
            content=f"{event.tool_name}({args_summary})",
            timestamp=timestamp,
            status="completed",
            content_blocks=[
                {
                    "type": "tool_call",
                    "id": event.tool_call_id,
                    "name": event.tool_name,
                    "arguments": event.tool_args,
                }
            ],
        )
        await storage.add_message(session_id, tool_msg)

    elif event_type == "tool_result":
        result_str = str(getattr(event, "tool_result", ""))
        content_summary = result_str[:500] if len(result_str) > 500 else result_str
        tool_msg = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role="tool_result",
            content=content_summary,
            timestamp=timestamp,
            status="completed",
            content_blocks=[
                {
                    "type": "tool_result",
                    "tool_call_id": event.tool_call_id,
                    "name": event.tool_name,
                    "content": result_str[:10000],
                }
            ],
            tool_call_id=event.tool_call_id,
        )
        await storage.add_message(session_id, tool_msg)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/chat/send",
        vol.Required("session_id"): _validate_session_id,
        vol.Required("message"): _validate_message,
        vol.Optional("provider"): str,
        vol.Optional("model"): str,
        vol.Optional("debug"): vol.Coerce(bool),
        vol.Optional("attachments"): vol.All(
            list,
            vol.Length(max=5),
            [
                vol.Schema(
                    {
                        vol.Required("filename"): str,
                        vol.Required("mime_type"): str,
                        vol.Required("content"): str,
                        vol.Optional("size"): int,
                    }
                )
            ],
        ),
    }
)
@websocket_api.async_response
async def ws_send_message(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send a chat message and get AI response."""
    user_id = _get_user_id(connection)
    session_id = msg["session_id"]

    try:
        storage = _get_storage(hass, user_id)

        # Verify session exists
        session = await storage.get_session(session_id)
        if session is None:
            connection.send_error(msg["id"], ERR_SESSION_NOT_FOUND, "Session not found")
            return

        now = datetime.now(timezone.utc).isoformat()

        # Process file attachments if present
        processed_attachments = []
        raw_attachments = msg.get("attachments", [])
        if raw_attachments:
            try:
                processed_attachments = await process_attachments(
                    hass, session_id, raw_attachments
                )
                _LOGGER.info(
                    "Processed %d attachments for session %s",
                    len(processed_attachments),
                    session_id,
                )
            except FileProcessingError as fp_err:
                _LOGGER.warning("Attachment processing error: %s", fp_err)
                connection.send_error(msg["id"], "invalid_attachment", str(fp_err))
                return

        # Create and save user message (with attachment refs)
        user_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=msg["message"],
            timestamp=now,
            status="completed",
            attachments=[a.to_storage_dict() for a in processed_attachments],
        )
        await storage.add_message(session_id, user_message)

        # Build conversation history for AI context.
        # Exclude the last message (the one we just saved) -- it will be appended
        # by _build_messages() in QueryProcessor to avoid duplication.
        # Reconstructs _images for historical user messages with image attachments.
        all_messages = await storage.get_session_messages(session_id)
        conversation_history = await _build_conversation_history(
            hass, all_messages[:-1]
        )

        # Determine provider
        provider = msg.get("provider") or session.provider or "anthropic"

        # Create assistant message (will be updated with response)
        assistant_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content="",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="pending",
        )

        # Call AI agent via MessageIntake (using streaming internally to capture tool events)
        try:
            intake = MessageIntake(hass)
            accumulated_text = ""
            stream_error: str | None = None
            tool_timestamp = datetime.now(timezone.utc).isoformat()

            # Use streaming internally to capture and persist tool_use/tool_result events
            async for event in intake.process_message_stream(
                msg["message"],
                user_id=user_id,
                session_id=session_id,
                provider=provider,
                model=msg.get("model"),
                conversation_history=conversation_history,
                attachments=processed_attachments or None,
            ):
                event_type = getattr(event, "type", None)

                if event_type == "text":
                    accumulated_text += getattr(event, "content", "")
                elif event_type in ("tool_call", "tool_result"):
                    # Persist tool messages for history reconstruction
                    await _persist_tool_messages(
                        storage, session_id, event, tool_timestamp
                    )
                elif event_type == "error":
                    stream_error = getattr(event, "message", "Unknown error")
                    break
                elif event_type == "complete":
                    break

            # Update assistant message based on result
            if stream_error:
                assistant_message.status = "error"
                assistant_message.error_message = stream_error
                _LOGGER.error(
                    "AI agent error for session %s: %s",
                    session_id,
                    stream_error,
                )
            else:
                assistant_message.content = accumulated_text
                assistant_message.status = "completed"

        except Exception as ai_err:
            assistant_message.status = "error"
            assistant_message.error_message = str(ai_err)
            _LOGGER.error("AI error for session %s: %s", session_id, ai_err)

        # Save assistant message
        await storage.add_message(session_id, assistant_message)

        # Send result immediately — don't block on post-processing
        connection.send_result(
            msg["id"],
            {
                "user_message": asdict(user_message),
                "assistant_message": asdict(assistant_message),
                "success": assistant_message.status == "completed",
            },
        )

        # Fire-and-forget: learn from conversation + index session + capture memories
        if assistant_message.status == "completed" and assistant_message.content:
            hass.async_create_task(
                _rag_post_conversation(
                    hass,
                    session_id=session_id,
                    user_id=user_id,
                    user_text=msg["message"],
                    assistant_text=assistant_message.content,
                    storage=storage,
                )
            )

    except ValueError:
        connection.send_error(msg["id"], ERR_SESSION_NOT_FOUND, "Session not found")
    except Exception as err:
        _LOGGER.exception(
            "Failed to send message in session %s for user %s", session_id, user_id
        )
        connection.send_error(msg["id"], ERR_STORAGE_ERROR, "Failed to send message")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/chat/send_stream",
        vol.Required("session_id"): _validate_session_id,
        vol.Required("message"): _validate_message,
        vol.Optional("provider"): str,
        vol.Optional("model"): str,
        vol.Optional("debug"): vol.Coerce(bool),
        vol.Optional("attachments"): vol.All(
            list,
            vol.Length(max=5),
            [
                vol.Schema(
                    {
                        vol.Required("filename"): str,
                        vol.Required("mime_type"): str,
                        vol.Required("content"): str,
                        vol.Optional("size"): int,
                    }
                )
            ],
        ),
    }
)
@websocket_api.async_response
async def ws_send_message_stream(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send a chat message and stream AI response."""
    user_id = _get_user_id(connection)
    session_id = msg["session_id"]
    request_id = msg["id"]

    _LOGGER.info("=" * 80)
    _LOGGER.info(
        "WS_SEND_MESSAGE_STREAM CALLED! User: %s, Session: %s", user_id, session_id
    )
    _LOGGER.info("Message: %s", msg.get("message", "")[:100])
    _LOGGER.info("=" * 80)

    try:
        storage = _get_storage(hass, user_id)

        # Verify session exists
        session = await storage.get_session(session_id)
        if session is None:
            _LOGGER.warning("Session %s NOT FOUND for user %s", session_id, user_id)
            connection.send_error(
                request_id, ERR_SESSION_NOT_FOUND, "Session not found"
            )
            return

        now = datetime.now(timezone.utc).isoformat()

        # Process file attachments if present
        processed_attachments = []
        raw_attachments = msg.get("attachments", [])
        if raw_attachments:
            try:
                processed_attachments = await process_attachments(
                    hass, session_id, raw_attachments
                )
                _LOGGER.info(
                    "Processed %d attachments for session %s",
                    len(processed_attachments),
                    session_id,
                )
            except FileProcessingError as fp_err:
                _LOGGER.warning("Attachment processing error: %s", fp_err)
                connection.send_error(request_id, "invalid_attachment", str(fp_err))
                return

        # Create and save user message (with attachment refs)
        user_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=msg["message"],
            timestamp=now,
            status="completed",
            attachments=[a.to_storage_dict() for a in processed_attachments],
        )
        await storage.add_message(session_id, user_message)

        # Send initial response with user message
        _LOGGER.info("Sending user_message event")
        connection.send_message(
            {
                "id": request_id,
                "type": "event",
                "event": {
                    "type": "user_message",
                    "message": asdict(user_message),
                },
            }
        )
        _LOGGER.info("user_message event sent")

        # Build conversation history for AI context.
        # Exclude the last message (the one we just saved) -- it will be appended
        # by _build_messages() in QueryProcessor to avoid duplication.
        # Reconstructs _images for historical user messages with image attachments.
        all_messages = await storage.get_session_messages(session_id)
        conversation_history = await _build_conversation_history(
            hass, all_messages[:-1]
        )

        # Determine provider
        provider = msg.get("provider") or session.provider or "anthropic"

        # Create assistant message (will be updated with streamed content)
        assistant_message_id = str(uuid.uuid4())
        assistant_message = Message(
            message_id=assistant_message_id,
            session_id=session_id,
            role="assistant",
            content="",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="streaming",
        )

        # Send stream start event
        _LOGGER.info("Sending stream_start event")
        connection.send_message(
            {
                "id": request_id,
                "type": "event",
                "event": {
                    "type": "stream_start",
                    "message_id": assistant_message_id,
                },
            }
        )
        _LOGGER.info("stream_start event sent")

        # Stream AI response via MessageIntake
        accumulated_text = ""
        stream_error = None

        try:
            intake = MessageIntake(hass)
            async for event in intake.process_message_stream(
                msg["message"],
                user_id=user_id,
                session_id=session_id,
                provider=provider,
                model=msg.get("model"),
                conversation_history=conversation_history,
                attachments=processed_attachments or None,
            ):
                # Convert AgentEvent dataclasses to WS event messages
                event_type = getattr(event, "type", None)

                if event_type == "text":
                    content = getattr(event, "content", "")
                    accumulated_text += content
                    connection.send_message(
                        {
                            "id": request_id,
                            "type": "event",
                            "event": {
                                "type": "stream_chunk",
                                "message_id": assistant_message_id,
                                "chunk": content,
                            },
                        }
                    )
                elif event_type == "status":
                    connection.send_message(
                        {
                            "id": request_id,
                            "type": "event",
                            "event": {
                                "type": "status",
                                "message": getattr(event, "message", ""),
                            },
                        }
                    )
                elif event_type in ("tool_call", "tool_result"):
                    # Persist tool messages to storage for history reconstruction
                    await _persist_tool_messages(
                        storage,
                        session_id,
                        event,
                        datetime.now(timezone.utc).isoformat(),
                    )
                elif event_type == "error":
                    stream_error = getattr(event, "message", "Unknown error")
                    break
                elif event_type == "complete":
                    break

        except Exception as ai_err:
            _LOGGER.error("AI streaming error for session %s: %s", session_id, ai_err)
            stream_error = str(ai_err)

        # Update assistant message with final content
        _LOGGER.info(
            "Stream finished. accumulated_text length: %d chars, error: %s",
            len(accumulated_text),
            stream_error,
        )
        if accumulated_text:
            _LOGGER.debug(
                "Final accumulated text (first 200 chars): %s",
                accumulated_text[:200],
            )
        assistant_message.content = accumulated_text
        assistant_message.status = "error" if stream_error else "completed"
        if stream_error:
            assistant_message.error_message = stream_error

        # Save assistant message
        await storage.add_message(session_id, assistant_message)

        # Send stream end event immediately — don't block on post-processing
        connection.send_message(
            {
                "id": request_id,
                "type": "event",
                "event": {
                    "type": "stream_end",
                    "message_id": assistant_message_id,
                    "success": not stream_error,
                    "error": stream_error,
                },
            }
        )

        # Send final result
        connection.send_result(
            request_id,
            {
                "user_message": asdict(user_message),
                "assistant_message": asdict(assistant_message),
                "success": assistant_message.status == "completed",
            },
        )

        # Fire-and-forget: learn from conversation + index session + capture memories
        if not stream_error and accumulated_text:
            hass.async_create_task(
                _rag_post_conversation(
                    hass,
                    session_id=session_id,
                    user_id=user_id,
                    user_text=msg["message"],
                    assistant_text=accumulated_text,
                    storage=storage,
                )
            )

    except ValueError as err:
        _LOGGER.exception("ValueError in ws_send_message_stream: %s", err)
        connection.send_error(request_id, ERR_SESSION_NOT_FOUND, "Session not found")
    except Exception as err:
        _LOGGER.exception(
            "Failed to send streaming message in session %s for user %s",
            session_id,
            user_id,
        )
        connection.send_error(request_id, ERR_STORAGE_ERROR, "Failed to send message")
