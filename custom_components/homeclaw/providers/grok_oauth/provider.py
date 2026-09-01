from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from ..openai import OpenAIProvider
from ..registry import ProviderRegistry
from .auth import InflightRefreshGate, OAuthRefreshError, TokenSet, access_token_is_fresh
from .constants import (
    CHAT_COMPLETIONS_URL,
    CLIENT_IDENTIFIER,
    CLIENT_VERSION,
    TOKEN_AUTH_HEADER,
    TOKEN_AUTH_VALUE,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_OAUTH_DATA_KEY = "grok_oauth"
_ENTITLEMENT_MESSAGE = (
    "Grok subscription is not entitled to Grok Build. SuperGrok or X Premium+ with Grok Build access is required."
)


@ProviderRegistry.register("grok_oauth")
class GrokOAuthProvider(OpenAIProvider):
    API_URL = CHAT_COMPLETIONS_URL
    DEFAULT_MODEL = "grok-4.6"

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        super().__init__(hass, config)
        self._config_entry: ConfigEntry | None = config.get("config_entry")
        self._refresh_gate = InflightRefreshGate()
        self._token = self._read_oauth_data().get("access_token", "")

    @property
    def api_url(self) -> str:
        return self.API_URL

    @property
    def lightweight_model(self) -> str | None:
        from ...models import get_lightweight_model

        return get_lightweight_model("grok_oauth") or "grok-4.5"

    def _read_oauth_data(self) -> dict[str, Any]:
        if not self._config_entry:
            return {}
        return dict(self._config_entry.data.get(_OAUTH_DATA_KEY, {}))

    async def _read_refresh_token(self) -> str:
        return self._read_oauth_data().get("refresh_token", "")

    def _persist_tokens(self, tokens: TokenSet) -> None:
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
            _LOGGER.warning("Grok OAuth: triggered re-authentication — check Home Assistant notifications")
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not trigger reauth flow", exc_info=True)

    async def _get_valid_access_token(self) -> str:
        oauth = self._read_oauth_data()
        access = oauth.get("access_token", "")
        expires_at = float(oauth.get("expires_at") or 0)
        if access_token_is_fresh(access, expires_at):
            self._token = access
            return access

        try:
            tokens = await self._refresh_gate.refresh(self.session, self._read_refresh_token)
        except OAuthRefreshError as err:
            _LOGGER.error("Grok OAuth refresh failed: %s", err)
            if err.is_permanent and not err.is_entitlement:
                self._trigger_reauth()
            raise

        self._persist_tokens(tokens)
        self._token = tokens.access_token
        return tokens.access_token

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            TOKEN_AUTH_HEADER: TOKEN_AUTH_VALUE,
            "x-grok-client-identifier": CLIENT_IDENTIFIER,
            "x-grok-client-version": CLIENT_VERSION,
            "x-grok-model-override": self._model,
        }

    def _build_payload(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        payload = super()._build_payload(messages, **kwargs)
        payload.pop("reasoning_effort", None)
        return payload

    def _rewrite_entitlement_error(self, chunk: dict[str, Any]) -> dict[str, Any]:
        if chunk.get("type") != "error":
            return chunk
        message = str(chunk.get("message") or "")
        if " 402:" in message or " 403:" in message or "status=402" in message or "status=403" in message:
            return {"type": "error", "message": _ENTITLEMENT_MESSAGE}
        return chunk

    async def get_response_stream(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        if kwargs.get("model"):
            self._model = kwargs["model"]
        try:
            await self._get_valid_access_token()
        except OAuthRefreshError as err:
            yield {"type": "error", "message": str(err)}
            return
        async for chunk in super().get_response_stream(messages, **kwargs):
            yield self._rewrite_entitlement_error(chunk)

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        texts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        async for chunk in self.get_response_stream(messages, **kwargs):
            chunk_type = chunk.get("type")
            if chunk_type == "text":
                texts.append(chunk.get("content") or "")
            elif chunk_type == "tool_call":
                args = chunk.get("args") or {}
                tool_calls.append(
                    {
                        "id": chunk.get("id"),
                        "type": "function",
                        "function": {
                            "name": chunk.get("name"),
                            "arguments": args if isinstance(args, str) else json.dumps(args),
                        },
                    }
                )
            elif chunk_type == "error":
                raise RuntimeError(chunk.get("message") or "Grok OAuth error")
        if tool_calls:
            return json.dumps({"tool_calls": tool_calls})
        return "".join(texts)
