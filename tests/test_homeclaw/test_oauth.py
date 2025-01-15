"""Tests for Anthropic OAuth helpers."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.oauth import (
    OAuthRefreshError,
    build_auth_url,
    exchange_code,
    generate_pkce,
    refresh_token,
)


class TestGeneratePkce:
    """Test PKCE generation."""

    def test_generates_verifier_and_challenge(self):
        """Test that generate_pkce returns both verifier and challenge."""
        verifier, challenge = generate_pkce()
        assert verifier is not None
        assert challenge is not None
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_verifier_is_url_safe(self):
        """Test that verifier contains only URL-safe characters."""
        verifier, _ = generate_pkce()
        # URL-safe characters: alphanumeric, -, _
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', verifier)

    def test_challenge_is_base64_url_safe(self):
        """Test that challenge is base64 URL-safe encoded."""
        _, challenge = generate_pkce()
        import re
        # Base64 URL-safe without padding
        assert re.match(r'^[A-Za-z0-9_-]+$', challenge)

    def test_different_calls_produce_different_values(self):
        """Test that successive calls produce different values."""
        v1, c1 = generate_pkce()
        v2, c2 = generate_pkce()
        assert v1 != v2
        assert c1 != c2


class TestBuildAuthUrl:
    """Test OAuth authorization URL building."""

    def test_builds_max_mode_url(self):
        """Test building URL for claude.ai (max mode)."""
        url = build_auth_url("test_challenge", "test_verifier", mode="max")
        assert url.startswith("https://claude.ai/oauth/authorize?")
        assert "client_id=" in url
        assert "code_challenge=test_challenge" in url
        assert "state=test_verifier" in url
        assert "code_challenge_method=S256" in url

    def test_builds_console_mode_url(self):
        """Test building URL for console.anthropic.com."""
        url = build_auth_url("challenge", "verifier", mode="console")
        assert url.startswith("https://console.anthropic.com/oauth/authorize?")

    def test_includes_required_params(self):
        """Test that all required OAuth params are included."""
        url = build_auth_url("challenge", "verifier")
        required_params = [
            "code=true",
            "response_type=code",
            "redirect_uri=",
            "scope=",
            "code_challenge=",
            "code_challenge_method=S256",
            "state=",
        ]
        for param in required_params:
            assert param in url


class TestExchangeCode:
    """Test OAuth code exchange."""

    @pytest.mark.asyncio
    async def test_successful_exchange(self):
        """Test successful code exchange."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with patch("time.time", return_value=1000):
            result = await exchange_code(mock_session, "auth_code", "verifier")

        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["expires_at"] == 4600  # 1000 + 3600

    @pytest.mark.asyncio
    async def test_exchange_with_state(self):
        """Test code exchange with CODE#STATE format."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "token",
            "expires_in": 3600,
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await exchange_code(mock_session, "code#state", "verifier")
        assert result["access_token"] == "token"

    @pytest.mark.asyncio
    async def test_exchange_error_status(self):
        """Test code exchange with error HTTP status."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await exchange_code(mock_session, "code", "verifier")
        assert "error" in result
        assert "400" in result["error"]

    @pytest.mark.asyncio
    async def test_exchange_missing_access_token(self):
        """Test code exchange when access_token is missing."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"some_other_field": "value"})

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await exchange_code(mock_session, "code", "verifier")
        assert "error" in result
        assert "missing access_token" in result["error"]


class TestRefreshToken:
    """Test OAuth token refresh."""

    @pytest.mark.asyncio
    async def test_successful_refresh(self):
        """Test successful token refresh."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 7200,
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with patch("time.time", return_value=2000):
            result = await refresh_token(mock_session, "old_refresh_token")

        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["expires_at"] == 9200  # 2000 + 7200

    @pytest.mark.asyncio
    async def test_refresh_preserves_old_refresh_token(self):
        """Test that old refresh token is preserved if not returned."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "new_access_token",
            # No new refresh_token
            "expires_in": 3600,
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await refresh_token(mock_session, "original_refresh")
        assert result["refresh_token"] == "original_refresh"

    @pytest.mark.asyncio
    async def test_refresh_error_status(self):
        """Test token refresh with error HTTP status."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with pytest.raises(OAuthRefreshError) as exc_info:
            await refresh_token(mock_session, "refresh")
        assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_missing_access_token(self):
        """Test token refresh when access_token is missing."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"error": "invalid_grant"})

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with pytest.raises(OAuthRefreshError) as exc_info:
            await refresh_token(mock_session, "refresh")
        assert "missing access_token" in str(exc_info.value)
