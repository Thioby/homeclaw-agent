"""WebSocket handlers for chat messaging (send, stream, RAG post-conversation)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

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

_CONFIRMABLE_TOOLS = frozenset({"create_dashboard", "update_dashboard", "delete_dashboard"})


@dataclass(slots=True)
class _PreparedChatRequest:
    """Prepared request payload reused by send and send_stream handlers."""

    storage: SessionStorage
    user_id: str
    session_id: str
    provider: str
    user_message: Message
    conversation_history: list[dict[str, Any]]
    processed_attachments: list[Any]


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


_COMPACTION_SUMMARY_PREFIX = "[Previous conversation summary]\n"


async def _persist_compaction_if_needed(
    storage: SessionStorage,
    session_id: str,
    completion_messages: list[dict[str, Any]],
) -> None:
    """Persist compaction summary to storage if one is present.

    Looks for a system message with the ``[Previous conversation summary]``
    prefix in the completion messages emitted by the agent and calls
    ``storage.compact_session_messages`` so the next request loads already
    compacted history instead of re-triggering compaction.
    """
    from ..core.compaction import MIN_RECENT_MESSAGES

    for msg in completion_messages:
        if msg.get("role") != "system":
            continue
        content = msg.get("content", "")
        if content.startswith(_COMPACTION_SUMMARY_PREFIX):
            summary = content[len(_COMPACTION_SUMMARY_PREFIX) :]
            if summary:
                _LOGGER.debug(
                    "Persisting compaction summary for session %s (%d chars)",
                    session_id,
                    len(summary),
                )
                try:
                    await storage.compact_session_messages(
                        session_id, summary, keep_last=MIN_RECENT_MESSAGES
                    )
                except Exception:
                    _LOGGER.exception(
                        "Failed to persist compaction for session %s",
                        session_id,
                    )
            return


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


def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def _prepare_chat_request(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    *,
    user_id: str,
    request_id: Any,
) -> _PreparedChatRequest | None:
    """Prepare and persist shared chat request state for send and send_stream."""
    session_id = msg["session_id"]
    storage = _get_storage(hass, user_id)

    session = await storage.get_session(session_id)
    if session is None:
        connection.send_error(request_id, ERR_SESSION_NOT_FOUND, "Session not found")
        return None

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
            return None

    user_message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=msg["message"],
        timestamp=_now_iso(),
        status="completed",
        attachments=[a.to_storage_dict() for a in processed_attachments],
    )
    await storage.add_message(session_id, user_message)

    # Exclude the just-added user message; QueryProcessor appends current query itself.
    all_messages = await storage.get_session_messages(session_id)
    conversation_history = await _build_conversation_history(hass, all_messages[:-1])

    # Provider is locked to the session — ignore any override from the message
    provider = session.provider or "anthropic"

    return _PreparedChatRequest(
        storage=storage,
        user_id=user_id,
        session_id=session_id,
        provider=provider,
        user_message=user_message,
        conversation_history=conversation_history,
        processed_attachments=processed_attachments,
    )


async def _run_agent_stream(
    hass: HomeAssistant,
    *,
    storage: SessionStorage,
    user_text: str,
    user_id: str,
    session_id: str,
    provider: str,
    model: str | None,
    conversation_history: list[dict[str, Any]],
    attachments: list[Any],
    on_text: Callable[[str], None] | None = None,
    on_status: Callable[[str], None] | None = None,
    on_tool_result: Callable[[str, Any, str], None] | None = None,
    tool_timestamp_factory: Callable[[], str] | None = None,
    error_log_prefix: str = "AI streaming error",
) -> tuple[str, str | None, list[dict[str, Any]]]:
    """Execute the shared streaming event loop and return final text/error/completion_messages."""
    intake = MessageIntake(hass)
    accumulated_text = ""
    stream_error: str | None = None
    completion_messages: list[dict[str, Any]] = []
    timestamp_factory = tool_timestamp_factory or _now_iso

    try:
        async for event in intake.process_message_stream(
            user_text,
            user_id=user_id,
            session_id=session_id,
            provider=provider,
            model=model,
            conversation_history=conversation_history,
            attachments=attachments or None,
        ):
            event_type = getattr(event, "type", None)

            if event_type == "text":
                content = getattr(event, "content", "")
                if content:
                    accumulated_text += content
                    if on_text:
                        on_text(content)
            elif event_type == "status":
                if on_status:
                    on_status(getattr(event, "message", ""))
            elif event_type in ("tool_call", "tool_result"):
                await _persist_tool_messages(
                    storage,
                    session_id,
                    event,
                    timestamp_factory(),
                )
                if event_type == "tool_call" and event.tool_name in _CONFIRMABLE_TOOLS:
                    from ..core.pending_actions import store_pending

                    store_pending(event.tool_call_id, event.tool_name, event.tool_args)
                if event_type == "tool_result" and on_tool_result:
                    on_tool_result(
                        event.tool_name,
                        getattr(event, "tool_result", ""),
                        event.tool_call_id,
                    )
            elif event_type == "error":
                stream_error = getattr(event, "message", "Unknown error")
                break
            elif event_type == "complete":
                completion_messages = getattr(event, "messages", [])
                break
    except Exception as ai_err:
        _LOGGER.error("%s for session %s: %s", error_log_prefix, session_id, ai_err)
        stream_error = str(ai_err)

    return accumulated_text, stream_error, completion_messages


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
    request_id = msg["id"]

    try:
        prepared = await _prepare_chat_request(
            hass,
            connection,
            msg,
            user_id=user_id,
            request_id=request_id,
        )
        if prepared is None:
            return

        # Create assistant message (will be updated with response)
        assistant_message = Message(
            message_id=str(uuid.uuid4()),
            session_id=prepared.session_id,
            role="assistant",
            content="",
            timestamp=_now_iso(),
            status="pending",
        )

        tool_timestamp = _now_iso()
        accumulated_text, stream_error, completion_messages = await _run_agent_stream(
            hass,
            storage=prepared.storage,
            user_text=msg["message"],
            user_id=prepared.user_id,
            session_id=prepared.session_id,
            provider=prepared.provider,
            model=msg.get("model"),
            conversation_history=prepared.conversation_history,
            attachments=prepared.processed_attachments,
            tool_timestamp_factory=lambda: tool_timestamp,
            error_log_prefix="AI error",
        )

        if stream_error:
            assistant_message.status = "error"
            assistant_message.error_message = stream_error
            _LOGGER.error(
                "AI agent error for session %s: %s",
                prepared.session_id,
                stream_error,
            )
        else:
            assistant_message.content = accumulated_text
            assistant_message.status = "completed"

        # Save assistant message
        await prepared.storage.add_message(prepared.session_id, assistant_message)

        # Persist compaction to storage so next request doesn't re-trigger
        if completion_messages:
            await _persist_compaction_if_needed(
                prepared.storage, prepared.session_id, completion_messages
            )

        # Send result immediately — don't block on post-processing
        connection.send_result(
            request_id,
            {
                "user_message": asdict(prepared.user_message),
                "assistant_message": asdict(assistant_message),
                "success": assistant_message.status == "completed",
            },
        )

        # Fire-and-forget: learn from conversation + index session + capture memories
        if assistant_message.status == "completed" and assistant_message.content:
            hass.async_create_task(
                _rag_post_conversation(
                    hass,
                    session_id=prepared.session_id,
                    user_id=prepared.user_id,
                    user_text=msg["message"],
                    assistant_text=assistant_message.content,
                    storage=prepared.storage,
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

    try:
        prepared = await _prepare_chat_request(
            hass,
            connection,
            msg,
            user_id=user_id,
            request_id=request_id,
        )
        if prepared is None:
            return

        # Send initial response with user message
        connection.send_message(
            {
                "id": request_id,
                "type": "event",
                "event": {
                    "type": "user_message",
                    "message": asdict(prepared.user_message),
                },
            }
        )

        # Create assistant message (will be updated with streamed content)
        assistant_message_id = str(uuid.uuid4())
        assistant_message = Message(
            message_id=assistant_message_id,
            session_id=prepared.session_id,
            role="assistant",
            content="",
            timestamp=_now_iso(),
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

        def _send_stream_chunk(content: str) -> None:
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

        def _send_status(status_message: str) -> None:
            connection.send_message(
                {
                    "id": request_id,
                    "type": "event",
                    "event": {
                        "type": "status",
                        "message": status_message,
                    },
                }
            )

        def _send_tool_result(
            tool_name: str, raw_result: Any, tool_call_id: str
        ) -> None:
            """Forward tool_result to frontend for rich rendering."""
            result_data = raw_result
            if isinstance(result_data, str):
                try:
                    parsed = json.loads(result_data)
                    if isinstance(parsed, dict) and "output" in parsed:
                        try:
                            result_data = json.loads(parsed["output"])
                        except (json.JSONDecodeError, TypeError):
                            result_data = parsed
                    else:
                        result_data = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
            if isinstance(result_data, dict) and result_data.get("ui_type"):
                connection.send_message(
                    {
                        "id": request_id,
                        "type": "event",
                        "event": {
                            "type": "tool_result",
                            "name": tool_name,
                            "tool_call_id": tool_call_id,
                            "result": result_data,
                        },
                    }
                )

        accumulated_text, stream_error, completion_messages = await _run_agent_stream(
            hass,
            storage=prepared.storage,
            user_text=msg["message"],
            user_id=prepared.user_id,
            session_id=prepared.session_id,
            provider=prepared.provider,
            model=msg.get("model"),
            conversation_history=prepared.conversation_history,
            attachments=prepared.processed_attachments,
            on_text=_send_stream_chunk,
            on_status=_send_status,
            on_tool_result=_send_tool_result,
        )

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
        await prepared.storage.add_message(prepared.session_id, assistant_message)

        # Persist compaction to storage so next request doesn't re-trigger
        if completion_messages:
            await _persist_compaction_if_needed(
                prepared.storage, prepared.session_id, completion_messages
            )

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
                "user_message": asdict(prepared.user_message),
                "assistant_message": asdict(assistant_message),
                "success": assistant_message.status == "completed",
            },
        )

        # Fire-and-forget: learn from conversation + index session + capture memories
        if not stream_error and accumulated_text:
            hass.async_create_task(
                _rag_post_conversation(
                    hass,
                    session_id=prepared.session_id,
                    user_id=prepared.user_id,
                    user_text=msg["message"],
                    assistant_text=accumulated_text,
                    storage=prepared.storage,
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
