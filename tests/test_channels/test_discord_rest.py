"""Tests for Discord REST client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeclaw.channels.discord.rest import DiscordRestClient


class _FakeResponse:
    def __init__(self, *, status: int, content_type: str, json_data=None, text_data=""):
        self.status = status
        self.content_type = content_type
        self._json_data = json_data or {}
        self._text_data = text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data


@pytest.mark.asyncio
class TestDiscordRestClient:
    async def test_create_message_success(self, monkeypatch):
        client = DiscordRestClient("token")
        fake_session = MagicMock()
        fake_session.request.return_value = _FakeResponse(
            status=200,
            content_type="application/json",
            json_data={"id": "m1"},
        )
        monkeypatch.setattr(
            client, "_get_session", AsyncMock(return_value=fake_session)
        )

        result = await client.create_message("c1", "hello")
        assert result["id"] == "m1"

    async def test_trigger_typing_success(self, monkeypatch):
        client = DiscordRestClient("token")
        fake_session = MagicMock()
        fake_session.request.return_value = _FakeResponse(
            status=204,
            content_type="text/plain",
        )
        monkeypatch.setattr(
            client, "_get_session", AsyncMock(return_value=fake_session)
        )

        await client.trigger_typing("c1")
        assert fake_session.request.call_count == 1

    async def test_request_raises_on_error(self, monkeypatch):
        client = DiscordRestClient("token")
        fake_session = MagicMock()
        fake_session.request.return_value = _FakeResponse(
            status=429,
            content_type="application/json",
            text_data='{"message":"rate limited", "retry_after": 0.01}',
        )
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.rest.asyncio.sleep",
            AsyncMock(),
        )
        monkeypatch.setattr(
            client, "_get_session", AsyncMock(return_value=fake_session)
        )

        with pytest.raises(RuntimeError, match="Discord API error 429"):
            await client.create_message("c1", "hello")

    async def test_request_retries_after_429(self, monkeypatch):
        client = DiscordRestClient("token")
        fake_session = MagicMock()
        fake_session.request.side_effect = [
            _FakeResponse(
                status=429,
                content_type="application/json",
                text_data='{"retry_after": 0.01}',
            ),
            _FakeResponse(
                status=200,
                content_type="application/json",
                json_data={"id": "m2"},
            ),
        ]
        sleep_mock = AsyncMock()
        monkeypatch.setattr(
            "custom_components.homeclaw.channels.discord.rest.asyncio.sleep",
            sleep_mock,
        )
        monkeypatch.setattr(
            client, "_get_session", AsyncMock(return_value=fake_session)
        )

        result = await client.create_message("c1", "hello")
        assert result["id"] == "m2"
        sleep_mock.assert_awaited_once()

    async def test_close_session(self):
        client = DiscordRestClient("token")
        session = AsyncMock()
        session.closed = False
        client._session = session
        await client.close()
        session.close.assert_awaited_once()
