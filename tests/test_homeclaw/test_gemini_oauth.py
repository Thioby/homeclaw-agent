"""Tests for Gemini OAuth helpers."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.gemini_oauth import (
    GeminiOAuthRefreshError,
    build_auth_url,
    exchange_code,
    generate_pkce,
    get_user_info,
    refresh_token,
)


class TestGeneratePkce:
    """Test PKCE generation for Gemini OAuth."""

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
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', verifier)

    def test_challenge_is_base64_url_safe(self):
        """Test that challenge is base64 URL-safe encoded without padding."""
        _, challenge = generate_pkce()
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', challenge)
        assert "=" not in challenge  # No padding

    def test_different_calls_produce_different_values(self):
        """Test that successive calls produce different values."""
        v1, c1 = generate_pkce()
        v2, c2 = generate_pkce()
        assert v1 != v2
        assert c1 != c2


class TestBuildAuthUrl:
    """Test OAuth authorization URL building for Gemini."""

    def test_builds_google_oauth_url(self):
        """Test building Google OAuth URL."""
        url = build_auth_url("test_challenge", "test_state")
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "code_challenge=test_challenge" in url
        assert "state=test_state" in url
        assert "code_challenge_method=S256" in url

    def test_includes_required_params(self):
        """Test that all required OAuth params are included."""
        url = build_auth_url("challenge", "state")
        required_params = [
            "client_id=",
            "redirect_uri=",
            "response_type=code",
            "scope=",
            "code_challenge=",
            "code_challenge_method=S256",
            "state=",
            "access_type=offline",
            "prompt=consent",
        ]
        for param in required_params:
            assert param in url

    def test_includes_gemini_scopes(self):
        """Test that Gemini required scopes are included."""
        url = build_auth_url("challenge", "state")
        assert "cloud-platform" in url or "googleapis.com" in url


class TestExchangeCode:
    """Test Gemini OAuth code exchange."""

    @pytest.mark.asyncio
    async def test_successful_exchange(self):
        """Test successful code exchange."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with patch("time.time", return_value=1000):
            result = await exchange_code(mock_session, "auth_code", "verifier")

        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["expires_at"] == 4600  # 1000 + 3600
        assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_exchange_without_refresh_token(self):
        """Test code exchange when no refresh_token is returned."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "access_token",
            "expires_in": 3600,
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await exchange_code(mock_session, "code", "verifier")
        assert result["access_token"] == "access_token"
        assert result["refresh_token"] == ""  # Empty when not returned

    @pytest.mark.asyncio
    async def test_exchange_error_status(self):
        """Test code exchange with error HTTP status."""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="invalid_grant")

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
        mock_response.json = AsyncMock(return_value={"error": "invalid_grant"})

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await exchange_code(mock_session, "code", "verifier")
        assert "error" in result
        assert "missing access_token" in result["error"]


class TestRefreshToken:
    """Test Gemini OAuth token refresh."""

    @pytest.mark.asyncio
    async def test_successful_refresh(self):
        """Test successful token refresh."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 7200,
            "token_type": "Bearer",
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
            # No new refresh_token returned
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
        mock_response.text = AsyncMock(return_value="Token expired")

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with pytest.raises(GeminiOAuthRefreshError) as exc_info:
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

        with pytest.raises(GeminiOAuthRefreshError) as exc_info:
            await refresh_token(mock_session, "refresh")
        assert "missing access_token" in str(exc_info.value)


class TestGetUserInfo:
    """Test Gemini user info retrieval."""

    @pytest.mark.asyncio
    async def test_successful_user_info(self):
        """Test successful user info retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        })

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await get_user_info(mock_session, "valid_token")
        assert result["email"] == "user@example.com"
        assert result["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_user_info_error(self):
        """Test user info retrieval with error."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Invalid token")

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        result = await get_user_info(mock_session, "invalid_token")
        assert "error" in result
        assert "401" in result["error"]
