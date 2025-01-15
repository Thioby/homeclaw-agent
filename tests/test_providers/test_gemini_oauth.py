"""Tests for Gemini OAuth provider."""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from aiohttp import ClientResponseError

from custom_components.homeclaw.providers.gemini_oauth import (
    GeminiOAuthProvider,
    GEMINI_CODE_ASSIST_ENDPOINT,
    GEMINI_CODE_ASSIST_HEADERS,
    GEMINI_CODE_ASSIST_METADATA,
    GEMINI_AVAILABLE_MODELS,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with OAuth tokens."""
    entry = MagicMock()
    entry.data = {
        "gemini_oauth": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": 9999999999.0,  # Far future
            "managed_project_id": "test-project-123",
        }
    }
    return entry


@pytest.fixture
def provider(mock_hass, mock_config_entry):
    """Create a GeminiOAuthProvider instance."""
    config = {
        "model": "gemini-3-pro-preview",
        "config_entry": mock_config_entry,
    }
    return GeminiOAuthProvider(mock_hass, config)


class TestGeminiOAuthProviderInit:
    """Tests for provider initialization."""

    def test_init_stores_hass(self, mock_hass, mock_config_entry):
        """Test that provider stores hass reference."""
        config = {"config_entry": mock_config_entry}
        provider = GeminiOAuthProvider(mock_hass, config)
        assert provider.hass is mock_hass

    def test_init_uses_default_model(self, mock_hass, mock_config_entry):
        """Test that provider uses default model if not specified."""
        config = {"config_entry": mock_config_entry}
        provider = GeminiOAuthProvider(mock_hass, config)
        assert provider._model == "gemini-3-pro-preview"

    def test_init_custom_model(self, mock_hass, mock_config_entry):
        """Test that provider uses custom model if specified."""
        config = {"model": "gemini-2.5-flash", "config_entry": mock_config_entry}
        provider = GeminiOAuthProvider(mock_hass, config)
        assert provider._model == "gemini-2.5-flash"

    def test_init_loads_oauth_data_from_config_entry(
        self, mock_hass, mock_config_entry
    ):
        """Test that provider loads OAuth data from config entry."""
        config = {"config_entry": mock_config_entry}
        provider = GeminiOAuthProvider(mock_hass, config)
        assert provider._oauth_data["access_token"] == "test_access_token"
        assert provider._oauth_data["refresh_token"] == "test_refresh_token"

    def test_supports_tools(self, provider):
        """Test that provider reports tool support."""
        assert provider.supports_tools is True


class TestGeminiOAuthProviderTokenManagement:
    """Tests for OAuth token management."""

    @pytest.mark.asyncio
    async def test_get_valid_token_returns_cached_token(self, provider):
        """Test that valid token is returned without refresh."""
        token = await provider._get_valid_token()
        assert token == "test_access_token"

    @pytest.mark.asyncio
    async def test_get_valid_token_refreshes_expired_token(
        self, mock_hass, mock_config_entry
    ):
        """Test that expired token triggers refresh."""
        import time

        mock_config_entry.data = {
            "gemini_oauth": {
                "access_token": "old_token",
                "refresh_token": "test_refresh_token",
                "expires_at": time.time() - 1000,  # Expired
            }
        }

        config = {"config_entry": mock_config_entry}
        provider = GeminiOAuthProvider(mock_hass, config)

        with patch(
            "custom_components.homeclaw.gemini_oauth.refresh_token"
        ) as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_at": time.time() + 3600,
            }

            token = await provider._get_valid_token()

            assert token == "new_access_token"
            mock_refresh.assert_called_once()


class TestGeminiOAuthProviderProjectManagement:
    """Tests for project ID management."""

    @pytest.mark.asyncio
    async def test_ensure_project_id_returns_cached_id(self, provider):
        """Test that cached project ID is returned."""
        mock_session = MagicMock()
        project_id = await provider._ensure_project_id(
            mock_session, "test_access_token"
        )
        assert project_id == "test-project-123"

    @pytest.mark.asyncio
    async def test_ensure_project_id_calls_load_code_assist(
        self, mock_hass, mock_config_entry
    ):
        """Test that loadCodeAssist is called when no cached project ID."""
        mock_config_entry.data = {
            "gemini_oauth": {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_at": 9999999999.0,
                # No managed_project_id
            }
        }

        config = {"config_entry": mock_config_entry}
        provider = GeminiOAuthProvider(mock_hass, config)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value='{"cloudaicompanionProject": "loaded-project-456"}'
        )
        mock_response.json = AsyncMock(
            return_value={"cloudaicompanionProject": "loaded-project-456"}
        )

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response)
            )
        )

        project_id = await provider._ensure_project_id(
            mock_session, "test_access_token"
        )

        assert project_id == "loaded-project-456"
        mock_session.post.assert_called()


class TestGeminiOAuthProviderMessageConversion:
    """Tests for message format conversion."""

    def test_convert_messages_user(self, provider):
        """Test user message conversion."""
        messages = [{"role": "user", "content": "Hello"}]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Hello"
        assert system is None

    def test_convert_messages_assistant(self, provider):
        """Test assistant message conversion to model role."""
        messages = [{"role": "assistant", "content": "Hi there"}]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert contents[0]["role"] == "model"
        assert contents[0]["parts"][0]["text"] == "Hi there"

    def test_convert_messages_system(self, provider):
        """Test system message extraction."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert system == "You are a helpful assistant"

    def test_convert_messages_multiple_system(self, provider):
        """Test multiple system messages are concatenated."""
        messages = [
            {"role": "system", "content": "First instruction"},
            {"role": "system", "content": "Second instruction"},
            {"role": "user", "content": "Hello"},
        ]
        contents, system = provider._convert_messages(messages)

        assert len(contents) == 1
        assert "First instruction" in system
        assert "Second instruction" in system


class TestGeminiOAuthProviderToolConversion:
    """Tests for tool/function conversion."""

    def test_convert_tools_empty(self, provider):
        """Test empty tools list."""
        result = provider._convert_tools([])
        assert result == []

    def test_convert_tools_single_function(self, provider):
        """Test single function conversion."""
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]

        result = provider._convert_tools(openai_tools)

        assert len(result) == 1
        assert "functionDeclarations" in result[0]
        declarations = result[0]["functionDeclarations"]
        assert len(declarations) == 1
        assert declarations[0]["name"] == "get_weather"
        assert declarations[0]["description"] == "Get weather for a location"


class TestGeminiOAuthProviderGetResponse:
    """Tests for get_response method."""

    @pytest.mark.asyncio
    async def test_get_response_success(self, provider):
        """Test successful API response."""
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "Hello there!"}]}}
                        ]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response)
                )
            )
            mock_session_class.return_value = mock_session

            response = await provider.get_response(messages)

            assert response == "Hello there!"

    @pytest.mark.asyncio
    async def test_get_response_with_tools(self, provider):
        """Test API request includes tools when provided."""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_func",
                    "description": "Test",
                    "parameters": {},
                },
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "Response"}]}}
                        ]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response)
                )
            )
            mock_session_class.return_value = mock_session

            await provider.get_response(messages, tools=tools)

            # Verify post was called with wrapped payload
            call_args = mock_session.post.call_args
            assert call_args is not None


class TestGeminiOAuthProviderConstants:
    """Tests for provider constants."""

    def test_endpoint_is_cloud_code_api(self):
        """Test that endpoint uses Cloud Code Assist API."""
        assert "cloudcode-pa.googleapis.com" in GEMINI_CODE_ASSIST_ENDPOINT
        assert "v1internal" in GEMINI_CODE_ASSIST_ENDPOINT

    def test_headers_include_required_fields(self):
        """Test that headers include required API client info."""
        assert "User-Agent" in GEMINI_CODE_ASSIST_HEADERS
        assert "X-Goog-Api-Client" in GEMINI_CODE_ASSIST_HEADERS
        assert "Client-Metadata" in GEMINI_CODE_ASSIST_HEADERS

    def test_metadata_includes_plugin_type(self):
        """Test that metadata includes plugin type."""
        assert GEMINI_CODE_ASSIST_METADATA["pluginType"] == "GEMINI"

    def test_available_models_defined(self):
        """Test that available models list is defined."""
        assert len(GEMINI_AVAILABLE_MODELS) > 0
        assert "gemini-3-pro-preview" in GEMINI_AVAILABLE_MODELS
        assert "gemini-3-flash" in GEMINI_AVAILABLE_MODELS
        assert "gemini-2.5-pro" in GEMINI_AVAILABLE_MODELS
        assert "gemini-2.5-flash" in GEMINI_AVAILABLE_MODELS


class TestGeminiOAuthProviderModelSelection:
    """Tests for per-request model selection."""

    @pytest.mark.asyncio
    async def test_get_response_with_model_override(self, provider):
        """Test that model can be overridden per request."""
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "Response"}]}}
                        ]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response)
                )
            )
            mock_session_class.return_value = mock_session

            # Override model to gemini-3-flash
            await provider.get_response(messages, model="gemini-3-flash")

            # Verify post was called with the overridden model
            call_args = mock_session.post.call_args
            assert call_args is not None
            payload = call_args.kwargs.get("json", {})
            assert payload.get("model") == "gemini-3-flash"

    @pytest.mark.asyncio
    async def test_get_response_invalid_model_uses_default(self, provider):
        """Test that invalid model falls back to default."""
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "Response"}]}}
                        ]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response)
                )
            )
            mock_session_class.return_value = mock_session

            # Try to use invalid model
            await provider.get_response(messages, model="invalid-model-xyz")

            # Verify post was called with the default model
            call_args = mock_session.post.call_args
            assert call_args is not None
            payload = call_args.kwargs.get("json", {})
            # Should fall back to default
            assert payload.get("model") == "gemini-3-pro-preview"

    @pytest.mark.asyncio
    async def test_get_response_without_model_uses_configured(self, provider):
        """Test that configured model is used when no override specified."""
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value=json.dumps(
                {
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "Response"}]}}
                        ]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response)
                )
            )
            mock_session_class.return_value = mock_session

            # No model override
            await provider.get_response(messages)

            # Verify post was called with the configured model
            call_args = mock_session.post.call_args
            assert call_args is not None
            payload = call_args.kwargs.get("json", {})
            # Should use the provider's configured model
            assert payload.get("model") == "gemini-3-pro-preview"
