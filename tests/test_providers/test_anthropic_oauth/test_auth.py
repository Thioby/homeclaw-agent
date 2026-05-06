"""Tests for anthropic_oauth.auth."""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.homeclaw.providers.anthropic_oauth.auth import (
    AuthorizationRequest,
    InflightRefreshGate,
    OAuthRefreshError,
    TokenSet,
    authorize,
    build_authorize_url,
    create_api_key,
    exchange_code,
    parse_callback_input,
    refresh_with_retry,
)
from custom_components.homeclaw.providers.anthropic_oauth.constants import (
    CLIENT_ID,
    CODE_CALLBACK_URL,
    OAUTH_SCOPES,
)
from custom_components.homeclaw.providers.anthropic_oauth.pkce import PKCEPair


class TestBuildAuthorizeUrl:
    def test_max_mode_uses_claude_ai(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="c" * 43)
        url = build_authorize_url(pkce, "state-xyz", mode="max")
        assert url.startswith("https://claude.ai/oauth/authorize?")

    def test_console_mode_uses_platform_claude(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="c" * 43)
        url = build_authorize_url(pkce, "state-xyz", mode="console")
        assert url.startswith("https://platform.claude.com/oauth/authorize?")

    def test_includes_required_params(self):
        pkce = PKCEPair(verifier="v" * 86, challenge="abc123")
        url = build_authorize_url(pkce, "state-xyz", mode="max")
        assert f"client_id={CLIENT_ID}" in url
        assert "response_type=code" in url
        assert "code_challenge=abc123" in url
        assert "code_challenge_method=S256" in url
        assert "state=state-xyz" in url
        assert "code=true" in url

    def test_scope_is_space_joined(self):
        from urllib.parse import unquote
        pkce = PKCEPair(verifier="v" * 86, challenge="c")
        url = build_authorize_url(pkce, "s", mode="max")
        # space-separated scope; decode percent-encoding before checking
        assert "scope=" in url
        decoded = unquote(url)
        for scope in OAUTH_SCOPES:
            assert scope in decoded

    def test_redirect_uri_is_callback(self):
        pkce = PKCEPair(verifier="v", challenge="c")
        url = build_authorize_url(pkce, "s", mode="max")
        from urllib.parse import quote
        assert quote(CODE_CALLBACK_URL, safe="") in url


class TestAuthorize:
    def test_returns_authorization_request_and_pkce(self):
        request, pkce = authorize(mode="max")
        assert isinstance(request, AuthorizationRequest)
        assert isinstance(pkce, PKCEPair)

    def test_request_url_matches_pkce(self):
        request, pkce = authorize(mode="max")
        assert pkce.challenge in request.url
        assert request.state in request.url

    def test_two_calls_have_different_states(self):
        a, _ = authorize()
        b, _ = authorize()
        assert a.state != b.state


class TestParseCallbackInput:
    def test_full_url_format(self):
        url = "https://example.com/cb?code=ABC&state=XYZ&extra=foo"
        assert parse_callback_input(url) == ("ABC", "XYZ")

    def test_hash_format(self):
        assert parse_callback_input("CODE123#STATE456") == ("CODE123", "STATE456")

    def test_query_string_format(self):
        assert parse_callback_input("code=A&state=B") == ("A", "B")

    def test_url_missing_state_returns_none(self):
        assert parse_callback_input("https://example.com/cb?code=ABC") is None

    def test_empty_input_returns_none(self):
        assert parse_callback_input("") is None
        assert parse_callback_input("   ") is None

    def test_whitespace_handling(self):
        assert parse_callback_input("  CODE#STATE  ") == ("CODE", "STATE")

    def test_garbage_input_returns_none(self):
        assert parse_callback_input("nothing useful") is None

    def test_hash_with_empty_parts_returns_none(self):
        assert parse_callback_input("#STATE") is None
        assert parse_callback_input("CODE#") is None


class TestExchangeCode:
    pytestmark = pytest.mark.asyncio

    async def test_success(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 200
        ctx.__aenter__.return_value.json = AsyncMock(return_value={
            "access_token": "AC", "refresh_token": "RF", "expires_in": 3600,
        })
        session.post = MagicMock(return_value=ctx)

        before = time.time()
        result = await exchange_code(session, "code#state", "verifier", expected_state="state")
        assert isinstance(result, TokenSet)
        assert result.access_token == "AC"
        assert result.refresh_token == "RF"
        assert result.expires_at >= before + 3599

    async def test_unparseable_input_raises_permanent(self):
        session = MagicMock()
        with pytest.raises(OAuthRefreshError) as exc:
            await exchange_code(session, "garbage", "v")
        assert exc.value.is_permanent is True

    async def test_state_mismatch_raises_permanent(self):
        session = MagicMock()
        with pytest.raises(OAuthRefreshError) as exc:
            await exchange_code(session, "code#WRONG", "v", expected_state="EXPECTED")
        assert exc.value.is_permanent is True

    async def test_http_error_raises_permanent(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 400
        ctx.__aenter__.return_value.text = AsyncMock(return_value="bad request")
        session.post = MagicMock(return_value=ctx)

        with pytest.raises(OAuthRefreshError) as exc:
            await exchange_code(session, "code#state", "v")
        assert exc.value.is_permanent is True


class TestRefreshWithRetry:
    pytestmark = pytest.mark.asyncio

    @staticmethod
    def _mock_session(*responses):
        """Build a session whose `.post` returns the given mocked responses in order.

        Each item is a dict like {"status": 200, "json": {...}} or {"status": 500, "text": "..."}
        or {"raise": <exception>} for transport errors.
        """
        session = MagicMock()
        contexts = []
        for r in responses:
            ctx = AsyncMock()
            if "raise" in r:
                ctx.__aenter__.side_effect = r["raise"]
            else:
                ctx.__aenter__.return_value.status = r["status"]
                if "json" in r:
                    ctx.__aenter__.return_value.json = AsyncMock(return_value=r["json"])
                if "text" in r:
                    ctx.__aenter__.return_value.text = AsyncMock(return_value=r["text"])
            contexts.append(ctx)
        session.post = MagicMock(side_effect=contexts)
        return session

    async def test_success_on_first_try(self):
        session = self._mock_session(
            {"status": 200, "json": {"access_token": "A", "refresh_token": "R", "expires_in": 3600}}
        )
        read = AsyncMock(return_value="REFRESH")

        tokens = await refresh_with_retry(session, read)
        assert tokens.access_token == "A"
        assert tokens.refresh_token == "R"
        assert read.await_count == 1

    async def test_5xx_retried_and_succeeds(self):
        session = self._mock_session(
            {"status": 503, "text": "boom"},
            {"status": 200, "json": {"access_token": "A2", "refresh_token": "R2", "expires_in": 3600}},
        )
        read = AsyncMock(return_value="REFRESH")

        tokens = await refresh_with_retry(session, read)
        assert tokens.access_token == "A2"
        assert read.await_count == 2  # re-read each attempt

    async def test_invalid_grant_raises_permanent_no_retry(self):
        session = self._mock_session(
            {"status": 400, "text": '{"error":"invalid_grant"}'},
        )
        read = AsyncMock(return_value="REFRESH")

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read)
        assert exc.value.is_permanent is True
        assert read.await_count == 1

    async def test_network_error_retried(self):
        session = self._mock_session(
            {"raise": aiohttp.ClientConnectionError("ECONNRESET")},
            {"status": 200, "json": {"access_token": "A3", "refresh_token": "R3", "expires_in": 3600}},
        )
        read = AsyncMock(return_value="REFRESH")

        tokens = await refresh_with_retry(session, read)
        assert tokens.access_token == "A3"
        assert read.await_count == 2

    async def test_exhausts_retries_on_persistent_network_error(self):
        # Fail on every attempt (max_retries + 1 = 3 attempts total)
        session = self._mock_session(
            {"raise": aiohttp.ClientConnectionError("err")},
            {"raise": aiohttp.ClientConnectionError("err")},
            {"raise": aiohttp.ClientConnectionError("err")},
        )
        read = AsyncMock(return_value="REFRESH")

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read)
        assert exc.value.is_permanent is False
        assert read.await_count == 3

    async def test_no_refresh_token_raises_permanent(self):
        session = MagicMock()
        read = AsyncMock(return_value="")

        with pytest.raises(OAuthRefreshError) as exc:
            await refresh_with_retry(session, read)
        assert exc.value.is_permanent is True


class TestInflightRefreshGate:
    pytestmark = pytest.mark.asyncio

    async def test_concurrent_calls_share_one_refresh(self):
        gate = InflightRefreshGate()

        call_count = 0

        async def fake_refresh(session, read):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # simulate latency
            return TokenSet("A", "R", time.time() + 3600)

        session = MagicMock()
        read = AsyncMock(return_value="REFRESH")

        with patch(
            "custom_components.homeclaw.providers.anthropic_oauth.auth.refresh_with_retry",
            side_effect=fake_refresh,
        ):
            results = await asyncio.gather(*[gate.refresh(session, read) for _ in range(5)])

        assert call_count == 1
        assert all(r.access_token == "A" for r in results)

    async def test_gate_resets_after_completion(self):
        gate = InflightRefreshGate()

        call_count = 0

        async def fake_refresh(session, read):
            nonlocal call_count
            call_count += 1
            return TokenSet(f"A{call_count}", "R", time.time() + 3600)

        session = MagicMock()
        read = AsyncMock(return_value="REFRESH")

        with patch(
            "custom_components.homeclaw.providers.anthropic_oauth.auth.refresh_with_retry",
            side_effect=fake_refresh,
        ):
            r1 = await gate.refresh(session, read)
            r2 = await gate.refresh(session, read)

        assert r1.access_token == "A1"
        assert r2.access_token == "A2"

    async def test_exception_propagates_to_all_waiters(self):
        gate = InflightRefreshGate()

        async def failing_refresh(session, read):
            await asyncio.sleep(0.01)
            raise OAuthRefreshError("nope", is_permanent=True)

        session = MagicMock()
        read = AsyncMock(return_value="REFRESH")

        with patch(
            "custom_components.homeclaw.providers.anthropic_oauth.auth.refresh_with_retry",
            side_effect=failing_refresh,
        ):
            results = await asyncio.gather(
                *[gate.refresh(session, read) for _ in range(3)],
                return_exceptions=True,
            )

        assert all(isinstance(r, OAuthRefreshError) for r in results)


class TestCreateApiKey:
    pytestmark = pytest.mark.asyncio

    async def test_success_returns_raw_key(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 200
        ctx.__aenter__.return_value.json = AsyncMock(return_value={"raw_key": "sk-ant-XYZ"})
        session.post = MagicMock(return_value=ctx)

        result = await create_api_key(session, "ACCESS")
        assert result == "sk-ant-XYZ"

    async def test_http_error_raises_permanent(self):
        session = MagicMock()
        ctx = AsyncMock()
        ctx.__aenter__.return_value.status = 403
        ctx.__aenter__.return_value.text = AsyncMock(return_value="forbidden")
        session.post = MagicMock(return_value=ctx)

        with pytest.raises(OAuthRefreshError) as exc:
            await create_api_key(session, "ACCESS")
        assert exc.value.is_permanent is True
