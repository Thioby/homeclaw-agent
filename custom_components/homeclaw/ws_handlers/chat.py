"""WebSocket handlers for chat messaging (send, stream, RAG post-conversation)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN
from ..file_processor import (
    FileProcessingError,
    process_attachments,
)
from ..models import get_context_window
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


def _build_conversation_history(
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
                    with open(storage_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("ascii")
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
        conversation_history = _build_conversation_history(all_messages[:-1])

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

        # Call AI agent
        try:
            # Set current user ID for memory tools to access
            if DOMAIN in hass.data:
                hass.data[DOMAIN]["_current_user_id"] = user_id

            if DOMAIN in hass.data and provider in hass.data[DOMAIN].get("agents", {}):
                agent = hass.data[DOMAIN]["agents"][provider]

                # Build kwargs for non-streaming (including attachments)
                query_kwargs: dict[str, Any] = {
                    "provider": provider,
                    "model": msg.get("model"),
                    "debug": msg.get("debug", False),
                    "conversation_history": conversation_history,
                    "user_id": user_id,
                    "session_id": session_id,
                }
                if processed_attachments:
                    query_kwargs["attachments"] = processed_attachments

                result = await agent.process_query(
                    msg["message"],
                    **query_kwargs,
                )

                # Check if AI agent returned success or error
                if result.get("success", False):
                    assistant_message.content = result.get("answer", "")
                    assistant_message.status = "completed"
                    assistant_message.metadata = {
                        k: v
                        for k, v in {
                            "automation": result.get("automation"),
                            "dashboard": result.get("dashboard"),
                            "debug": result.get("debug"),
                        }.items()
                        if v is not None
                    }
                else:
                    # AI agent returned an error
                    assistant_message.status = "error"
                    assistant_message.error_message = result.get(
                        "error", "Unknown AI error"
                    )
                    _LOGGER.error(
                        "AI agent error for session %s: %s",
                        session_id,
                        assistant_message.error_message,
                    )
            else:
                raise HomeAssistantError(f"Provider {provider} not configured")

        except Exception as ai_err:
            assistant_message.status = "error"
            assistant_message.error_message = str(ai_err)
            _LOGGER.error("AI error for session %s: %s", session_id, ai_err)
        finally:
            # Clear current user ID after tool execution
            if DOMAIN in hass.data:
                hass.data[DOMAIN].pop("_current_user_id", None)

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
        conversation_history = _build_conversation_history(all_messages[:-1])

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

        # Stream AI response
        accumulated_text = ""
        stream_error = None

        try:
            # Set current user ID for memory tools to access
            if DOMAIN in hass.data:
                hass.data[DOMAIN]["_current_user_id"] = user_id

            if DOMAIN in hass.data and provider in hass.data[DOMAIN].get("agents", {}):
                agent = hass.data[DOMAIN]["agents"][provider]

                # Build kwargs for streaming
                model_id = msg.get("model")
                kwargs: dict[str, Any] = {
                    "hass": hass,
                    "conversation_history": conversation_history,
                    "user_id": user_id,
                    "session_id": session_id,
                }
                if msg.get("debug", False):
                    kwargs["debug"] = True
                if model_id:
                    kwargs["model"] = model_id

                # Pass processed attachments for multimodal content
                if processed_attachments:
                    kwargs["attachments"] = processed_attachments

                # Add tools for native function calling
                from ..agent_compat import HomeclawAgent

                if isinstance(agent, HomeclawAgent):
                    tools = agent._get_tools_for_provider()
                    if tools:
                        kwargs["tools"] = tools

                    # Add RAG context if available (with memory recall for user)
                    if agent._rag_manager:
                        rag_context = await agent._get_rag_context(
                            msg["message"], user_id=user_id
                        )
                        if rag_context:
                            kwargs["rag_context"] = rag_context

                    # Get system prompt with identity context
                    system_prompt = await agent._get_system_prompt(user_id)
                    if system_prompt:
                        kwargs["system_prompt"] = system_prompt

                    # Context window for compaction
                    kwargs["context_window"] = get_context_window(provider, model_id)

                    # Memory flush function for pre-compaction capture
                    if agent._rag_manager and agent._rag_manager.is_initialized:
                        mem_mgr = getattr(agent._rag_manager, "_memory_manager", None)
                        if mem_mgr:
                            kwargs["memory_flush_fn"] = mem_mgr.flush_from_messages

                # Check if agent supports streaming
                if hasattr(agent, "process_query_stream") or hasattr(
                    agent._agent, "process_query_stream"
                ):
                    # Use streaming
                    _LOGGER.info("Agent supports streaming, starting stream...")
                    agent_stream = (
                        agent._agent.process_query_stream
                        if hasattr(agent, "_agent")
                        else agent.process_query_stream
                    )

                    _LOGGER.debug("Starting to consume stream chunks...")
                    async for event in agent_stream(msg["message"], **kwargs):
                        # Handle both dataclass events and legacy dict chunks
                        chunk = (
                            asdict(event)
                            if hasattr(event, "__dataclass_fields__")
                            else event
                        )
                        _LOGGER.debug(
                            "Received chunk from agent: type=%s", chunk.get("type")
                        )
                        if chunk.get("type") == "text":
                            # Text chunk
                            content = chunk.get("content", "")
                            accumulated_text += content
                            _LOGGER.debug("Sending stream_chunk: %s", content[:50])
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
                        elif chunk.get("type") == "status":
                            # Status update (e.g., "Calling tool X...")
                            connection.send_message(
                                {
                                    "id": request_id,
                                    "type": "event",
                                    "event": {
                                        "type": "status",
                                        "message": chunk.get("message", ""),
                                    },
                                }
                            )
                        elif chunk.get("type") == "tool_call":
                            # Tool call notification (deprecated - tools executed internally now)
                            _LOGGER.debug(
                                "Ignoring tool_call chunk (handled internally)"
                            )
                        elif chunk.get("type") == "tool_result":
                            # Tool result notification (deprecated - tools executed internally now)
                            _LOGGER.debug(
                                "Ignoring tool_result chunk (handled internally)"
                            )
                        elif chunk.get("type") == "error":
                            # Error during streaming
                            stream_error = chunk.get("message", "Unknown error")
                            break
                        elif chunk.get("type") == "complete":
                            # Stream complete
                            break
                else:
                    # Fallback to non-streaming
                    _LOGGER.info("Agent doesn't support streaming, using non-streaming")
                    result = await agent.process_query(
                        msg["message"],
                        provider=provider,
                        model=msg.get("model"),
                        debug=msg.get("debug", False),
                        conversation_history=conversation_history,
                    )

                    if result.get("success", False):
                        accumulated_text = result.get("answer", "")
                        # Send as single chunk
                        connection.send_message(
                            {
                                "id": request_id,
                                "type": "event",
                                "event": {
                                    "type": "stream_chunk",
                                    "message_id": assistant_message_id,
                                    "chunk": accumulated_text,
                                },
                            }
                        )
                    else:
                        stream_error = result.get("error", "Unknown error")
            else:
                stream_error = f"Provider {provider} not configured"

        except Exception as ai_err:
            _LOGGER.error("AI streaming error for session %s: %s", session_id, ai_err)
            stream_error = str(ai_err)
        finally:
            # Clear current user ID after tool execution
            if DOMAIN in hass.data:
                hass.data[DOMAIN].pop("_current_user_id", None)

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
