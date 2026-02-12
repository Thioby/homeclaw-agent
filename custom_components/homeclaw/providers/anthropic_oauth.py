"""Anthropic OAuth provider for Claude Pro/Max subscription."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any

import aiohttp

from .registry import AIProvider, ProviderRegistry
from ..core.tool_call_codec import extract_tool_calls_from_assistant_content

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Required system prompt prefix for OAuth access to Claude models
CLAUDE_CODE_SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude."

# Beta headers required for OAuth (simplified as of Jan 2025)
ANTHROPIC_BETA_FLAGS = "oauth-2025-04-20,interleaved-thinking-2025-05-14"

# User agent matching claude-cli
USER_AGENT = "claude-cli/2.1.2 (external, cli)"


@ProviderRegistry.register("anthropic_oauth")
class AnthropicOAuthProvider(AIProvider):
    """Anthropic provider using OAuth authentication for Claude Pro/Max.

    This provider uses OAuth Bearer tokens instead of API keys and requires
    special system prompt prefixes and beta headers to work with Claude.
    """

    # Note: ?beta=true query param is required for OAuth
    API_URL = "https://api.anthropic.com/v1/messages?beta=true"
    ANTHROPIC_VERSION = "2023-06-01"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 8192
    TOOL_PREFIX = "mcp_"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the Anthropic OAuth provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration containing:
                - config_entry: ConfigEntry with OAuth tokens
                - model: Optional model name
                - max_tokens: Optional max tokens
        """
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._max_tokens = config.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self._config_entry: ConfigEntry | None = config.get("config_entry")
        self._oauth_data: dict[str, Any] = {}
        self._refresh_lock = asyncio.Lock()

        # Load OAuth data from config entry
        if self._config_entry:
            self._oauth_data = dict(self._config_entry.data.get("anthropic_oauth", {}))

    @property
    def supports_tools(self) -> bool:
        """Return True as Anthropic supports function calling."""
        return True

    async def _get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            Exception: If no token available or refresh fails.
        """
        from ..oauth import refresh_token, OAuthRefreshError

        async with self._refresh_lock:
            # Check if token is still valid (with 5 minute buffer)
            if time.time() < self._oauth_data.get("expires_at", 0) - 300:
                access_token = self._oauth_data.get("access_token")
                if not access_token:
                    raise OAuthRefreshError(
                        "No access token available - re-authentication required"
                    )
                return access_token

            _LOGGER.debug("Refreshing Anthropic OAuth token")

            # Check if refresh token exists
            refresh_tok = self._oauth_data.get("refresh_token")
            if not refresh_tok:
                raise OAuthRefreshError(
                    "No refresh token available - re-authentication required"
                )

            try:
                async with aiohttp.ClientSession() as session:
                    new_tokens = await refresh_token(session, refresh_tok)
            except OAuthRefreshError as e:
                _LOGGER.error("Anthropic OAuth refresh failed: %s", e)
                raise

            self._oauth_data.update(new_tokens)

            # Persist refreshed tokens to config entry
            if self._config_entry:
                new_data = {
                    **self._config_entry.data,
                    "anthropic_oauth": self._oauth_data,
                }
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )

            return new_tokens["access_token"]

    def _transform_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Transform request payload for OAuth compatibility.

        Adds mcp_ prefix to tool names as required by Claude Code OAuth.
        """
        payload = copy.deepcopy(payload)

        # Add prefix to tool definitions
        if "tools" in payload:
            payload["tools"] = [
                {**t, "name": f"{self.TOOL_PREFIX}{t['name']}"}
                for t in payload["tools"]
            ]

        # Add prefix to tool_use blocks in messages
        if "messages" in payload:
            for msg in payload["messages"]:
                if isinstance(msg.get("content"), list):
                    for block in msg["content"]:
                        if block.get("type") == "tool_use" and "name" in block:
                            block["name"] = f"{self.TOOL_PREFIX}{block['name']}"

        # Replace OpenCode references in system prompt
        if "system" in payload:
            if isinstance(payload["system"], str):
                payload["system"] = payload["system"].replace("OpenCode", "Claude Code")
                payload["system"] = re.sub(
                    r"opencode", "Claude", payload["system"], flags=re.IGNORECASE
                )
            elif isinstance(payload["system"], list):
                for item in payload["system"]:
                    if item.get("type") == "text" and "text" in item:
                        item["text"] = item["text"].replace("OpenCode", "Claude Code")
                        item["text"] = re.sub(
                            r"opencode", "Claude", item["text"], flags=re.IGNORECASE
                        )

        return payload

    def _transform_response(self, text: str) -> str:
        """Transform response to remove mcp_ prefix from tool names."""
        return re.sub(r'"name"\s*:\s*"mcp_([^"]+)"', r'"name": "\1"', text)

    def _unprefix_tool_name(self, name: str) -> str:
        """Remove mcp_ prefix from tool names returned by OAuth API."""
        if name.startswith(self.TOOL_PREFIX):
            return name[len(self.TOOL_PREFIX) :]
        return name

    def _assistant_tool_use_blocks(
        self, parsed_content: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract Anthropic tool_use blocks from stored assistant JSON."""
        blocks: list[dict[str, Any]] = []

        for call in extract_tool_calls_from_assistant_content(parsed_content):
            blocks.append(
                {
                    "type": "tool_use",
                    "id": call.get("id", ""),
                    "name": self._unprefix_tool_name(call.get("name", "")),
                    "input": call.get("args", {}),
                }
            )

        return blocks

    def _convert_tools(
        self, openai_tools: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic input_schema format."""
        if not openai_tools:
            return []

        anthropic_tools: list[dict[str, Any]] = []

        for tool in openai_tools:
            if tool.get("type") == "function":
                function_def = tool.get("function", {})
                anthropic_tool = {
                    "name": function_def.get("name", ""),
                    "description": function_def.get("description", ""),
                    "input_schema": function_def.get("parameters", {}),
                }
                anthropic_tools.append(anthropic_tool)

        return anthropic_tools

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Get a response from Anthropic using OAuth token.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments (e.g., tools for function calling).

        Returns:
            The AI response as a string.
        """
        access_token = await self._get_valid_token()

        _LOGGER.debug(
            "Making OAuth request to Anthropic API with model: %s", self._model
        )

        headers = {
            "authorization": f"Bearer {access_token}",
            "content-type": "application/json",
            "anthropic-version": self.ANTHROPIC_VERSION,
            "anthropic-beta": ANTHROPIC_BETA_FLAGS,
            "user-agent": USER_AGENT,
        }

        # Extract system message and convert messages
        system_message = None
        anthropic_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                system_message = content
            elif role == "function":
                # Tool result - Anthropic uses tool_result in user role
                tool_use_id = message.get("tool_use_id")
                if not tool_use_id:
                    _LOGGER.warning(
                        "Skipping tool_result without tool_use_id for tool '%s'",
                        message.get("name", "unknown"),
                    )
                    continue
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": content,
                            }
                        ],
                    }
                )
            elif role == "assistant" and content:
                # Check if this contains tool_use JSON
                try:
                    parsed = json.loads(content)
                    tool_use_blocks = self._assistant_tool_use_blocks(parsed)
                    if tool_use_blocks:
                        anthropic_messages.append(
                            {
                                "role": "assistant",
                                "content": tool_use_blocks,
                            }
                        )
                        continue
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
                anthropic_messages.append({"role": "assistant", "content": content})
            elif role == "user" and content:
                images = message.get("_images", [])
                if images:
                    # Build multimodal content blocks for Anthropic vision API
                    content_blocks: list[dict[str, Any]] = [
                        {"type": "text", "text": content},
                    ]
                    for img in images:
                        content_blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img["mime_type"],
                                    "data": img["data"],
                                },
                            }
                        )
                    anthropic_messages.append(
                        {"role": "user", "content": content_blocks}
                    )
                else:
                    anthropic_messages.append({"role": "user", "content": content})

        # Build system as array with Claude Code identifier first (required for OAuth)
        # MUST be sent as array of text blocks, not a single string
        system_blocks = [
            {"type": "text", "text": CLAUDE_CODE_SYSTEM_PREFIX},
        ]
        # Add actual system message as second block if present
        if system_message:
            system_blocks.append({"type": "text", "text": system_message})

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self.config.get("temperature", 0.7),
            "messages": anthropic_messages,
            "system": system_blocks,
        }

        # Convert and add tools if provided
        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = self._convert_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        # Transform for OAuth compatibility
        payload = self._transform_request(payload)

        _LOGGER.debug(
            "Anthropic OAuth request payload: %s", json.dumps(payload, indent=2)
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                response_text = await resp.text()

                if resp.status != 200:
                    _LOGGER.error(
                        "Anthropic OAuth API error %d: %s", resp.status, response_text
                    )
                    raise Exception(
                        f"Anthropic OAuth API error {resp.status}: {response_text[:200]}"
                    )

                # Transform response to remove mcp_ prefix
                response_text = self._transform_response(response_text)
                data = json.loads(response_text)

                # Extract text from content blocks
                content_blocks = data.get("content", [])

                if not content_blocks:
                    return ""

                # Separate text blocks from tool_use blocks
                text_parts = []
                tool_use_blocks = []
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_use_blocks.append(block)

                if tool_use_blocks:
                    # Return ONLY tool_use as structured JSON — text is stored
                    # separately and will be yielded by query_processor before
                    # the tool call. We embed the prefixed text so it can be
                    # extracted downstream.
                    result: dict[str, Any] = {
                        "tool_use": {
                            "id": tool_use_blocks[0].get("id"),
                            "name": tool_use_blocks[0].get("name"),
                            "input": tool_use_blocks[0].get("input"),
                        }
                    }
                    # Attach any text the model produced before the tool call
                    if text_parts:
                        result["text"] = " ".join(text_parts)
                    # If multiple tool calls, attach extras
                    if len(tool_use_blocks) > 1:
                        result["additional_tool_calls"] = [
                            {
                                "id": tb.get("id"),
                                "name": tb.get("name"),
                                "input": tb.get("input"),
                            }
                            for tb in tool_use_blocks[1:]
                        ]
                    return json.dumps(result)

                return " ".join(text_parts) if text_parts else ""

    @staticmethod
    def _build_tool_call_chunk(
        tool_state: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Build a normalized tool_call chunk from streaming tool state."""
        name = tool_state.get("name", "")
        if not name:
            return None

        args: dict[str, Any] = {}
        start_input = tool_state.get("input")
        if isinstance(start_input, dict):
            args = dict(start_input)

        # Anthropic may send `{}` in content_block_start and stream the actual
        # arguments later in input_json_delta events, so always parse deltas too.
        input_json = "".join(tool_state.get("input_json_parts", []))
        if input_json:
            try:
                parsed = json.loads(input_json)
                if isinstance(parsed, dict):
                    args = {**args, **parsed}
            except (TypeError, ValueError, json.JSONDecodeError):
                _LOGGER.warning(
                    "Failed to parse Anthropic OAuth tool input JSON for %s", name
                )

        return {
            "type": "tool_call",
            "name": name,
            "args": args,
            "id": tool_state.get("id", ""),
        }

    def _extract_stream_chunks(
        self,
        event_data: dict[str, Any],
        pending_tools: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert one Anthropic OAuth stream event into normalized chunks."""
        output: list[dict[str, Any]] = []
        event_type = event_data.get("type", "")

        if event_type == "content_block_start":
            block = event_data.get("content_block", {})
            if block.get("type") == "tool_use":
                index = int(event_data.get("index", 0))
                pending_tools[index] = {
                    "id": block.get("id", ""),
                    "name": self._unprefix_tool_name(block.get("name", "")),
                    "input": block.get("input"),
                    "input_json_parts": [],
                }
            return output

        if event_type == "content_block_delta":
            delta = event_data.get("delta", {})
            delta_type = delta.get("type", "")

            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    output.append({"type": "text", "content": text})
                return output

            if delta_type == "input_json_delta":
                index = int(event_data.get("index", 0))
                tool_state = pending_tools.setdefault(
                    index,
                    {
                        "id": "",
                        "name": "",
                        "input": None,
                        "input_json_parts": [],
                    },
                )
                partial_json = delta.get("partial_json", "")
                if partial_json:
                    tool_state["input_json_parts"].append(partial_json)
                return output

        if event_type in {"message_delta", "message_stop"}:
            for index in sorted(pending_tools):
                chunk = self._build_tool_call_chunk(pending_tools[index])
                if chunk:
                    output.append(chunk)
            pending_tools.clear()

        return output

    async def get_response_stream(self, messages: list[dict[str, Any]], **kwargs: Any):
        """Stream response chunks from Anthropic OAuth Messages API."""
        access_token = await self._get_valid_token()

        headers = {
            "authorization": f"Bearer {access_token}",
            "content-type": "application/json",
            "anthropic-version": self.ANTHROPIC_VERSION,
            "anthropic-beta": ANTHROPIC_BETA_FLAGS,
            "user-agent": USER_AGENT,
        }

        system_message = None
        anthropic_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                system_message = content
            elif role == "function":
                tool_use_id = message.get("tool_use_id")
                if not tool_use_id:
                    _LOGGER.warning(
                        "Skipping tool_result without tool_use_id for tool '%s'",
                        message.get("name", "unknown"),
                    )
                    continue
                anthropic_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": content,
                            }
                        ],
                    }
                )
            elif role == "assistant" and content:
                try:
                    parsed = json.loads(content)
                    tool_use_blocks = self._assistant_tool_use_blocks(parsed)
                    if tool_use_blocks:
                        anthropic_messages.append(
                            {
                                "role": "assistant",
                                "content": tool_use_blocks,
                            }
                        )
                        continue
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass
                anthropic_messages.append({"role": "assistant", "content": content})
            elif role == "user" and content:
                images = message.get("_images", [])
                if images:
                    content_blocks: list[dict[str, Any]] = [
                        {"type": "text", "text": content},
                    ]
                    for img in images:
                        content_blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img["mime_type"],
                                    "data": img["data"],
                                },
                            }
                        )
                    anthropic_messages.append(
                        {"role": "user", "content": content_blocks}
                    )
                else:
                    anthropic_messages.append({"role": "user", "content": content})

        system_blocks = [{"type": "text", "text": CLAUDE_CODE_SYSTEM_PREFIX}]
        if system_message:
            system_blocks.append({"type": "text", "text": system_message})

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self.config.get("temperature", 0.7),
            "messages": anthropic_messages,
            "system": system_blocks,
            "stream": True,
        }

        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = self._convert_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        payload = self._transform_request(payload)

        pending_tools: dict[int, dict[str, Any]] = {}
        buffer = ""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.error(
                            "Anthropic OAuth streaming API error %d: %s",
                            resp.status,
                            error_text[:500],
                        )
                        yield {
                            "type": "error",
                            "message": f"Anthropic OAuth API error {resp.status}: {error_text[:200]}",
                        }
                        return

                    async for raw_chunk in resp.content.iter_any():
                        if not raw_chunk:
                            continue

                        buffer += raw_chunk.decode("utf-8", errors="ignore")

                        while "\n\n" in buffer:
                            raw_event, buffer = buffer.split("\n\n", 1)
                            if not raw_event.strip():
                                continue

                            data_lines = [
                                line[5:].strip()
                                for line in raw_event.splitlines()
                                if line.startswith("data:")
                            ]
                            if not data_lines:
                                continue

                            data_text = "\n".join(data_lines)
                            if data_text == "[DONE]":
                                break

                            try:
                                event_data = json.loads(data_text)
                            except (TypeError, ValueError, json.JSONDecodeError):
                                _LOGGER.debug(
                                    "Skipping unparsable Anthropic OAuth stream event: %s",
                                    data_text[:200],
                                )
                                continue

                            for out_chunk in self._extract_stream_chunks(
                                event_data, pending_tools
                            ):
                                yield out_chunk

                    if buffer.strip():
                        for raw_event in buffer.strip().split("\n\n"):
                            data_lines = [
                                line[5:].strip()
                                for line in raw_event.splitlines()
                                if line.startswith("data:")
                            ]
                            if not data_lines:
                                continue
                            try:
                                event_data = json.loads("\n".join(data_lines))
                            except (TypeError, ValueError, json.JSONDecodeError):
                                continue
                            for out_chunk in self._extract_stream_chunks(
                                event_data, pending_tools
                            ):
                                yield out_chunk

                    if pending_tools:
                        for index in sorted(pending_tools):
                            chunk = self._build_tool_call_chunk(pending_tools[index])
                            if chunk:
                                yield chunk

        except Exception as err:
            _LOGGER.error("Anthropic OAuth streaming exception: %s", err)
            yield {"type": "error", "message": str(err)}
