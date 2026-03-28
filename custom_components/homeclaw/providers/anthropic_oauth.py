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

from .adapters.anthropic_adapter import AnthropicAdapter
from .adapters.stream_utils import SSEParser, ToolAccumulator
from .registry import AIProvider, ProviderRegistry

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
        self.adapter = AnthropicAdapter()

        # Load OAuth data from config entry
        if self._config_entry:
            self._oauth_data = dict(self._config_entry.data.get("anthropic_oauth", {}))

    @property
    def supports_tools(self) -> bool:
        """Return True as Anthropic supports function calling."""
        return True

    async def _get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Re-reads the config entry under the refresh lock so that a
        concurrent refresh by another task is picked up.  On permanent
        failures (``invalid_grant``) triggers HA's re-auth flow.

        Returns:
            Valid access token string.

        Raises:
            OAuthRefreshError: If no token available or refresh fails.
        """
        from ..oauth import OAuthRefreshError, refresh_token

        async with self._refresh_lock:
            # Re-read persisted tokens — another task may have refreshed.
            if self._config_entry:
                fresh = dict(self._config_entry.data.get("anthropic_oauth", {}))
                if fresh.get("access_token"):
                    self._oauth_data = fresh

            # Check if token is still valid (with 5 minute buffer)
            if time.time() < self._oauth_data.get("expires_at", 0) - 300:
                access_token = self._oauth_data.get("access_token")
                if not access_token:
                    raise OAuthRefreshError(
                        "No access token available - re-authentication required",
                        is_permanent=True,
                    )
                return access_token

            _LOGGER.debug("Refreshing Anthropic OAuth token")

            # Check if refresh token exists
            refresh_tok = self._oauth_data.get("refresh_token")
            if not refresh_tok:
                self._trigger_reauth()
                raise OAuthRefreshError(
                    "No refresh token available - re-authentication required",
                    is_permanent=True,
                )

            try:
                async with aiohttp.ClientSession() as session:
                    new_tokens = await refresh_token(session, refresh_tok)
            except OAuthRefreshError as e:
                _LOGGER.error("Anthropic OAuth refresh failed: %s", e)
                if e.is_permanent:
                    self._trigger_reauth()
                raise

            self._oauth_data.update(new_tokens)

            # Persist refreshed tokens IMMEDIATELY — critical for token
            # rotation (Anthropic revokes the old refresh token on each use).
            if self._config_entry:
                new_data = {
                    **self._config_entry.data,
                    "anthropic_oauth": self._oauth_data,
                }
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=new_data
                )

            return new_tokens["access_token"]

    def _trigger_reauth(self) -> None:
        """Request HA re-authentication flow for this config entry."""
        if not self._config_entry:
            return
        try:
            self._config_entry.async_start_reauth(self.hass)
            _LOGGER.warning(
                "Anthropic OAuth: triggered re-authentication flow — "
                "check Home Assistant notifications"
            )
        except Exception:
            _LOGGER.debug("Could not trigger reauth flow", exc_info=True)

    def _transform_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Transform request payload for OAuth compatibility.

        Replaces OpenCode references in system prompt with Claude Code
        (required for OAuth access).
        """
        payload = copy.deepcopy(payload)

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

        # Use adapter for message/tool conversion
        anthropic_messages, system_message = self.adapter.transform_messages(messages)

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
            "temperature": self.config.get("temperature", 0.2),
            "messages": anthropic_messages,
            "system": system_blocks,
        }

        # Convert and add tools if provided
        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = self.adapter.transform_tools(tools)
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

                data = json.loads(response_text)

                # Use adapter to parse response, then convert to expected string format
                parsed = self.adapter.extract_response(data)
                return self.adapter.format_response_as_legacy_string(parsed)

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

        # Use adapter for message/tool conversion
        anthropic_messages, system_message = self.adapter.transform_messages(messages)

        system_blocks = [{"type": "text", "text": CLAUDE_CODE_SYSTEM_PREFIX}]
        if system_message:
            system_blocks.append({"type": "text", "text": system_message})

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self.config.get("temperature", 0.2),
            "messages": anthropic_messages,
            "system": system_blocks,
            "stream": True,
        }

        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = self.adapter.transform_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        payload = self._transform_request(payload)

        sse_parser = SSEParser()
        tool_acc = ToolAccumulator()

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

                        for data_text in sse_parser.feed(
                            raw_chunk.decode("utf-8", errors="ignore")
                        ):
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

                            for out_chunk in self.adapter.extract_stream_events(
                                event_data, tool_acc
                            ):
                                yield out_chunk

                    # Flush remaining buffer at stream end.
                    for data_text in sse_parser.flush():
                        try:
                            event_data = json.loads(data_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            continue
                        for out_chunk in self.adapter.extract_stream_events(
                            event_data, tool_acc
                        ):
                            yield out_chunk

                    # Safety flush in case stream ended without message_stop.
                    if tool_acc.has_pending:
                        for tc in tool_acc.flush_all():
                            yield {
                                "type": "tool_call",
                                "id": tc["id"],
                                "name": tc["name"],
                                "args": tc["args"],
                            }

        except Exception as err:
            _LOGGER.error("Anthropic OAuth streaming exception: %s", err)
            yield {"type": "error", "message": str(err)}
