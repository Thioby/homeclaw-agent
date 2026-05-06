"""AnthropicOAuthProvider — HA-aware glue around the OAuth modules.

Ported from opencode-anthropic-auth v1.8.0 src/index.ts (MIT, © Ex Machina).
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

import aiohttp

from ..adapters.anthropic_adapter import AnthropicAdapter
from ..adapters.stream_utils import SSEParser, ToolAccumulator
from ..registry import AIProvider, ProviderRegistry
from .auth import InflightRefreshGate, OAuthRefreshError, TokenSet
from .transform import (
    build_oauth_headers,
    is_tls_insecure,
    rewrite_url,
    transform_request_payload,
    unprefix_tool_names_in_event,
    unprefix_tool_names_in_response,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_BASE_API_URL = "https://api.anthropic.com/v1/messages"
_OAUTH_DATA_KEY = "anthropic_oauth"


@ProviderRegistry.register("anthropic_oauth")
class AnthropicOAuthProvider(AIProvider):
    """Anthropic provider using Claude Pro/Max OAuth credentials."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 8192

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._max_tokens = config.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self._config_entry: ConfigEntry | None = config.get("config_entry")
        self._refresh_gate = InflightRefreshGate()
        self.adapter = AnthropicAdapter()

    @property
    def supports_tools(self) -> bool:
        return True

    # ---------- Token management ----------

    def _read_oauth_data(self) -> dict[str, Any]:
        """Re-read latest OAuth tokens from config entry storage."""
        if not self._config_entry:
            return {}
        return dict(self._config_entry.data.get(_OAUTH_DATA_KEY, {}))

    async def _read_refresh_token(self) -> str:
        """Callback for InflightRefreshGate: returns current refresh token."""
        return self._read_oauth_data().get("refresh_token", "")

    def _persist_tokens(self, tokens: TokenSet) -> None:
        """Write refreshed tokens back to config entry IMMEDIATELY.

        Anthropic rotates the refresh token on each use — we must persist
        before the next request, otherwise concurrent refreshers may use
        a revoked token.
        """
        if not self._config_entry:
            return
        new_oauth = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        }
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data={**self._config_entry.data, _OAUTH_DATA_KEY: new_oauth},
        )

    def _trigger_reauth(self) -> None:
        if not self._config_entry:
            return
        try:
            self._config_entry.async_start_reauth(self.hass)
            _LOGGER.warning("Anthropic OAuth: triggered re-authentication — " "check Home Assistant notifications")
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not trigger reauth flow", exc_info=True)

    async def _get_valid_access_token(self) -> str:
        """Return a valid access token, refreshing if needed.

        Concurrent callers coalesce on a single in-flight refresh via
        InflightRefreshGate — prevents 401 cascades from token rotation.
        """
        oauth = self._read_oauth_data()
        access = oauth.get("access_token", "")
        expires_at = oauth.get("expires_at", 0)

        # 5-minute safety buffer.
        if access and time.time() < expires_at - 300:
            return access

        async with aiohttp.ClientSession() as session:
            try:
                tokens = await self._refresh_gate.refresh(session, self._read_refresh_token)
            except OAuthRefreshError as err:
                _LOGGER.error("Anthropic OAuth refresh failed: %s", err)
                if err.is_permanent:
                    self._trigger_reauth()
                raise

        self._persist_tokens(tokens)
        return tokens.access_token

    # ---------- Request execution ----------

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        *,
        stream: bool,
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        anthropic_messages, system_message = self.adapter.transform_messages(messages)
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self.config.get("temperature", 0.2),
            "messages": anthropic_messages,
            "system": system_message,
        }
        if stream:
            payload["stream"] = True
        if tools:
            anthropic_tools = self.adapter.transform_tools(tools)
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        return transform_request_payload(payload)

    def _build_session(self) -> aiohttp.ClientSession:
        connector = aiohttp.TCPConnector(ssl=False) if is_tls_insecure() else None
        return aiohttp.ClientSession(connector=connector)

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        access_token = await self._get_valid_access_token()
        headers = build_oauth_headers(access_token)
        url = rewrite_url(_BASE_API_URL)
        payload = self._build_payload(messages, stream=False, tools=kwargs.get("tools"))

        _LOGGER.debug("Anthropic OAuth POST %s", url)

        async with self._build_session() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                response_text = await resp.text()
                if resp.status != 200:
                    _LOGGER.error("Anthropic OAuth API error %d: %s", resp.status, response_text[:500])
                    raise RuntimeError(f"Anthropic OAuth API error {resp.status}: {response_text[:200]}")
                data = json.loads(response_text)

        unprefix_tool_names_in_response(data)
        parsed = self.adapter.extract_response(data)
        return self.adapter.format_response_as_legacy_string(parsed)

    async def get_response_stream(self, messages: list[dict[str, Any]], **kwargs: Any):
        access_token = await self._get_valid_access_token()
        headers = build_oauth_headers(access_token)
        url = rewrite_url(_BASE_API_URL)
        payload = self._build_payload(messages, stream=True, tools=kwargs.get("tools"))

        sse_parser = SSEParser()
        tool_acc = ToolAccumulator()

        try:
            async with self._build_session() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.error(
                            "Anthropic OAuth stream API error %d: %s",
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
                        for data_text in sse_parser.feed(raw_chunk.decode("utf-8", errors="ignore")):
                            if data_text == "[DONE]":
                                break
                            try:
                                event_data = json.loads(data_text)
                            except (TypeError, ValueError, json.JSONDecodeError):
                                _LOGGER.debug(
                                    "Skipping unparsable Anthropic OAuth event: %s",
                                    data_text[:200],
                                )
                                continue
                            unprefix_tool_names_in_event(event_data)
                            for out_chunk in self.adapter.extract_stream_events(event_data, tool_acc):
                                yield out_chunk

                    for data_text in sse_parser.flush():
                        try:
                            event_data = json.loads(data_text)
                        except (TypeError, ValueError, json.JSONDecodeError):
                            continue
                        unprefix_tool_names_in_event(event_data)
                        for out_chunk in self.adapter.extract_stream_events(event_data, tool_acc):
                            yield out_chunk

                    if tool_acc.has_pending:
                        for tc in tool_acc.flush_all():
                            yield {
                                "type": "tool_call",
                                "id": tc["id"],
                                "name": tc["name"],
                                "args": tc["args"],
                            }

        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Anthropic OAuth streaming exception: %s", err)
            yield {"type": "error", "message": str(err)}
