from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from custom_components.homeclaw.providers.grok_oauth.auth import (
    DeviceCode,
    InflightRefreshGate,
    OAuthRefreshError,
    TokenSet,
    access_token_is_fresh,
    poll_device_code_token,
    refresh_with_retry,
    request_device_code,
)
from custom_components.homeclaw.providers.grok_oauth.constants import (
    CLIENT_ID,
    DEVICE_CODE_GRANT_TYPE,
    DEVICE_CODE_URL,
    TOKEN_URL,
)


class FakeResponse:
    def __init__(self, status: int, payload=None):
        self.status = status
        self._payload = payload if payload is not None else {}

    async def json(self, content_type=None):
        return self._payload

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def post(self, url, data=None, headers=None, json=None):
        self.calls.append({"url": url, "data": data, "headers": headers, "json": json})
        return self._responses.pop(0)


def _device(**overrides) -> DeviceCode:
    values = {
        "device_code": "dev-1",
        "user_code": "ABCD-EFGH",
        "verification_uri": "https://auth.x.ai/device",
        "verification_uri_complete": "https://auth.x.ai/device?user_code=ABCD-EFGH",
        "expires_in": 30.0,
        "interval": 1.0,
    }
    values.update(overrides)
    return DeviceCode(**values)


class TestRequestDeviceCode:
    pytestmark = pytest.mark.asyncio

    async def test_parses_response(self):
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    {
                        "device_code": "d",
                        "user_code": "U-1",
                        "verification_uri": "https://auth.x.ai/device",
                        "verification_uri_complete": "https://auth.x.ai/device?user_code=U-1",
                        "expires_in": 600,
                        "interval": 5,
                    },
                )
            ]
        )
        device = await request_device_code(session)
        assert device.device_code == "d"
        assert device.user_code == "U-1"
        assert device.verification_uri_complete.endswith("U-1")
        assert session.calls[0]["url"] == DEVICE_CODE_URL
        assert session.calls[0]["data"]["client_id"] == CLIENT_ID
        assert "grok-cli:access" in session.calls[0]["data"]["scope"]
        assert session.calls[0]["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    async def test_http_error(self):
        session = FakeSession([FakeResponse(400, {"error": "invalid_client"})])
        with pytest.raises(OAuthRefreshError, match="Device code request failed"):
            await request_device_code(session)

    async def test_missing_fields(self):
        session = FakeSession([FakeResponse(200, {"device_code": "d"})])
        with pytest.raises(OAuthRefreshError, match="missing"):
            await request_device_code(session)


class TestPollDeviceCode:
    pytestmark = pytest.mark.asyncio

    async def test_pending_then_success(self):
        sleeps: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        session = FakeSession(
            [
                FakeResponse(400, {"error": "authorization_pending"}),
                FakeResponse(400, {"error": "slow_down"}),
                FakeResponse(
                    200,
                    {
                        "access_token": "A",
                        "refresh_token": "R",
                        "expires_in": 3600,
                    },
                ),
            ]
        )
        tokens = await poll_device_code_token(session, _device(), sleep=fake_sleep)
        assert tokens.access_token == "A"
        assert tokens.refresh_token == "R"
        assert tokens.expires_at > time.time()
        assert session.calls[0]["data"]["grant_type"] == DEVICE_CODE_GRANT_TYPE
        assert session.calls[0]["url"] == TOKEN_URL
        assert sleeps
        assert sleeps[1] > sleeps[0]

    async def test_denied(self):
        session = FakeSession([FakeResponse(400, {"error": "access_denied"})])
        with pytest.raises(OAuthRefreshError, match="denied"):
            await poll_device_code_token(session, _device(), sleep=AsyncMock())

    async def test_expired_token(self):
        session = FakeSession([FakeResponse(400, {"error": "expired_token"})])
        with pytest.raises(OAuthRefreshError, match="expired"):
            await poll_device_code_token(session, _device(), sleep=AsyncMock())

    async def test_timeout(self):
        session = FakeSession([FakeResponse(400, {"error": "authorization_pending"})] * 20)

        async def no_sleep(_seconds: float) -> None:
            return None

        with pytest.raises(OAuthRefreshError, match="timed out"):
            await poll_device_code_token(
                session,
                _device(expires_in=0, interval=0.001),
                sleep=no_sleep,
                now=lambda: time.time(),
            )


class TestRefresh:
    pytestmark = pytest.mark.asyncio

    async def test_rotates_refresh_token(self):
        session = FakeSession(
            [
                FakeResponse(
                    200,
                    {
                        "access_token": "NEW_A",
                        "refresh_token": "NEW_R",
                        "expires_in": 120,
                    },
                )
            ]
        )

        async def read_refresh() -> str:
            return "OLD_R"

        tokens = await refresh_with_retry(session, read_refresh)
        assert tokens.access_token == "NEW_A"
        assert tokens.refresh_token == "NEW_R"
        assert session.calls[0]["data"]["grant_type"] == "refresh_token"
        assert session.calls[0]["data"]["refresh_token"] == "OLD_R"
        assert session.calls[0]["json"] is None

    async def test_keeps_old_refresh_when_omitted(self):
        session = FakeSession([FakeResponse(200, {"access_token": "NEW_A", "expires_in": 60})])

        async def read_refresh() -> str:
            return "OLD_R"

        tokens = await refresh_with_retry(session, read_refresh)
        assert tokens.refresh_token == "OLD_R"

    async def test_invalid_grant_is_permanent(self):
        session = FakeSession([FakeResponse(400, {"error": "invalid_grant"})])

        async def read_refresh() -> str:
            return "DEAD"

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read_refresh)
        assert exc.value.is_permanent is True
        assert exc.value.is_entitlement is False

    async def test_403_is_entitlement(self):
        session = FakeSession([FakeResponse(403, {"error": "permission_denied"})])

        async def read_refresh() -> str:
            return "R"

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read_refresh)
        assert exc.value.is_permanent is True
        assert exc.value.is_entitlement is True


class TestInflightRefreshGate:
    pytestmark = pytest.mark.asyncio

    async def test_concurrent_callers_share_one_refresh(self):
        calls = {"n": 0}

        async def read_refresh() -> str:
            return "R"

        gate = InflightRefreshGate()
        session = FakeSession(
            [
                FakeResponse(200, {"access_token": "A", "refresh_token": "R2", "expires_in": 60}),
            ]
        )

        original = session.post

        def counting_post(*args, **kwargs):
            calls["n"] += 1
            return original(*args, **kwargs)

        session.post = counting_post  # type: ignore[method-assign]
        results = await asyncio.gather(
            gate.refresh(session, read_refresh),
            gate.refresh(session, read_refresh),
            gate.refresh(session, read_refresh),
        )
        assert {r.access_token for r in results} == {"A"}
        assert calls["n"] == 1


class TestAccessTokenIsFresh:
    def test_future_expires_at(self):
        assert access_token_is_fresh("tok", time.time() + 3600) is True

    def test_expired(self):
        assert access_token_is_fresh("tok", time.time() - 10) is False

    def test_empty(self):
        assert access_token_is_fresh("", 0) is False
