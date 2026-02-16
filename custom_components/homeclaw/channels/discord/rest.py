"""Lightweight Discord REST API client (v10)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class DiscordRestClient:
    """Minimal Discord REST API client using aiohttp.

    This client supports only operations needed by the Discord channel:
    sending messages and triggering typing indicators.
    """

    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, token: str, timeout_seconds: int = 20) -> None:
        self._token = token.strip()
        self._timeout_seconds = timeout_seconds
        self._session: aiohttp.ClientSession | None = None
        self._max_retries = 2

    async def create_message(self, channel_id: str, content: str) -> dict[str, Any]:
        """Send a message to a Discord channel.

        Args:
            channel_id: Discord channel ID.
            content: Message content.

        Returns:
            Parsed JSON response from Discord.
        """
        path = f"/channels/{channel_id}/messages"
        payload = {"content": content}
        return await self._request("POST", path, json=payload)

    async def trigger_typing(self, channel_id: str) -> None:
        """Trigger Discord typing indicator in a channel."""
        path = f"/channels/{channel_id}/typing"
        await self._request("POST", path)

    async def close(self) -> None:
        """Close the underlying aiohttp session if open."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated request to Discord API.

        Raises:
            RuntimeError: If Discord responds with non-2xx status.
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}{path}"
        headers = {
            "Authorization": f"Bot {self._token}",
            "Content-Type": "application/json",
        }

        for attempt in range(self._max_retries + 1):
            async with session.request(
                method, url, json=json, headers=headers
            ) as response:
                if 200 <= response.status < 300:
                    if response.content_type == "application/json":
                        return await response.json()
                    return {}

                body = await response.text()
                if response.status == 429 and attempt < self._max_retries:
                    retry_after = _extract_retry_after(body)
                    _LOGGER.warning(
                        "Discord API rate limited on %s %s, retry in %.2fs",
                        method,
                        path,
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                _LOGGER.warning(
                    "Discord API %s %s failed: status=%s body=%s",
                    method,
                    path,
                    response.status,
                    body[:300],
                )
                raise RuntimeError(f"Discord API error {response.status}")

        raise RuntimeError("Discord API retry loop exhausted")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Create or return a reusable aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session


def _extract_retry_after(body: str) -> float:
    """Parse retry delay from Discord 429 response body."""
    try:
        payload = json.loads(body)
    except Exception:
        return 1.0

    retry_after = payload.get("retry_after")
    if isinstance(retry_after, (int, float)) and retry_after > 0:
        return float(retry_after)
    return 1.0
