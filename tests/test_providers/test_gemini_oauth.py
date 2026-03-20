"""Tests for Gemini OAuth provider."""

import json
from collections.abc import AsyncIterator
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from custom_components.homeclaw.providers.gemini_oauth import (
    GeminiOAuthProvider,
    GEMINI_CODE_ASSIST_ENDPOINT,
    GEMINI_CODE_ASSIST_METADATA,
    GEMINI_AVAILABLE_MODELS,
)
from custom_components.homeclaw.providers._gemini_constants import (
    RateLimitError,
    RetryableQuotaError,
    TerminalQuotaError,
    _build_user_agent,
)
from custom_components.homeclaw.providers._gemini_retry import (
    _extract_delay_from_text,
    classify_google_error,
    parse_retry_delay,
)


class _AsyncContextManager:
    """Minimal async context manager for mocked aiohttp responses."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _AsyncBytesIterable:
    """Async iterator for mocked SSE byte chunks."""

    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    def __aiter__(self) -> AsyncIterator[bytes]:
        async def _iterate():
            for chunk in self._chunks:
                yield chunk

        return _iterate()


def _make_mock_response(
    status: int,
    *,
    text: str = "",
    json_data: dict | list | None = None,
    content_chunks: list[bytes] | None = None,
):
    """Create a mocked aiohttp response object."""
    response = AsyncMock()
    response.status = status
    response.text = AsyncMock(return_value=text)
    response.json = AsyncMock(return_value=json_data if json_data is not None else {})
    response.content = _AsyncBytesIterable(content_chunks or [])
    return response


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
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
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
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
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
                        "candidates": [{"content": {"parts": [{"text": "Response"}]}}]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
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

    def test_user_agent_format(self):
        """Test that dynamic User-Agent follows HomeClaw/<ver>/<model> pattern."""
        ua = _build_user_agent("gemini-3-pro-preview")
        assert ua.startswith("HomeClaw/")
        assert "gemini-3-pro-preview" in ua

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
                        "candidates": [{"content": {"parts": [{"text": "Response"}]}}]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
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
                        "candidates": [{"content": {"parts": [{"text": "Response"}]}}]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
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
                        "candidates": [{"content": {"parts": [{"text": "Response"}]}}]
                    }
                }
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
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


class TestClassifyGoogleError:
    """Tests for structured Google API error classification."""

    def test_rate_limit_exceeded_with_retry_info(self):
        """RetryInfo + RATE_LIMIT_EXCEEDED → RetryableQuotaError with delay."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Rate limit hit",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "34.07s",
                        },
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "RATE_LIMIT_EXCEEDED",
                            "domain": "cloudcode-pa.googleapis.com",
                        },
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert abs(err.retry_delay_seconds - 34.07) < 0.01

    def test_quota_exhausted_is_terminal(self):
        """QUOTA_EXHAUSTED → TerminalQuotaError (never retry)."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Quota exhausted",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "QUOTA_EXHAUSTED",
                            "domain": "cloudcode-pa.googleapis.com",
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, TerminalQuotaError)
        assert err.reason == "QUOTA_EXHAUSTED"

    def test_daily_quota_failure_is_terminal(self):
        """QuotaFailure with PerDay → TerminalQuotaError."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Daily quota exceeded",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                            "violations": [{"quotaId": "RequestsPerDay"}],
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, TerminalQuotaError)

    def test_per_minute_quota_is_retryable(self):
        """QuotaFailure with PerMinute → RetryableQuotaError with 60s."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Per-minute limit",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                            "violations": [{"quotaId": "RequestsPerMinute"}],
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert err.retry_delay_seconds == 60.0

    def test_insufficient_credits_is_terminal(self):
        """INSUFFICIENT_G1_CREDITS_BALANCE → TerminalQuotaError."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "No credits",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "INSUFFICIENT_G1_CREDITS_BALANCE",
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, TerminalQuotaError)

    def test_bare_429_without_details(self):
        """Plain 429 without structured details → RetryableQuotaError."""
        err = classify_google_error(429, "Rate limited")
        assert isinstance(err, RetryableQuotaError)

    def test_5xx_is_retryable(self):
        """Server errors → RetryableQuotaError."""
        body = json.dumps({"error": {"code": 503, "message": "Unavailable"}})
        err = classify_google_error(503, body)
        assert isinstance(err, RetryableQuotaError)

    def test_malformed_details_graceful(self):
        """Malformed details array doesn't crash."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Bad data",
                    "details": ["not-a-dict", 42, None],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, (RetryableQuotaError, RateLimitError))

    def test_nested_stringified_wrapper_is_parsed(self):
        """Stringified Google error inside message is unwrapped."""
        body = json.dumps(
            {
                "code": 429,
                "message": json.dumps(
                    {
                        "error": {
                            "code": 429,
                            "message": "Rate limit hit",
                            "details": [
                                {
                                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                    "retryDelay": "12s",
                                },
                                {
                                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                    "reason": "RATE_LIMIT_EXCEEDED",
                                    "domain": "cloudcode-pa.googleapis.com",
                                },
                            ],
                        }
                    }
                ),
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert err.retry_delay_seconds == 12.0

    def test_embedded_json_wrapper_and_trimmed_type_key_is_parsed(self):
        """Wrapper text with embedded JSON and spaced @type still parses."""
        body = (
            'Request failed: {"error":{"code":429,"message":"Rate limit hit","details":'
            '[{" @type":"type.googleapis.com/google.rpc.RetryInfo","retryDelay":"7s"},'
            '{"@type":"type.googleapis.com/google.rpc.ErrorInfo","reason":"RATE_LIMIT_EXCEEDED",'
            '"domain":"cloudcode-pa.googleapis.com"}]}}'
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert err.retry_delay_seconds == 7.0

    def test_400_is_not_retryable(self):
        """400 errors → generic Exception."""
        body = json.dumps({"error": {"code": 400, "message": "Bad request"}})
        err = classify_google_error(400, body)
        assert not isinstance(err, RateLimitError)

    def test_retry_delay_ms_format(self):
        """RetryInfo with millisecond format is parsed correctly."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Wait",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "500ms",
                        },
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "RATE_LIMIT_EXCEEDED",
                        },
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert abs(err.retry_delay_seconds - 0.5) < 0.01

    def test_rate_limit_exceeded_without_retry_info_uses_message_delay(self):
        """RATE_LIMIT_EXCEEDED falls back to reset-after delay in message."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "You have exhausted your capacity on this model. "
                    "Your quota will reset after 35s.",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "RATE_LIMIT_EXCEEDED",
                            "domain": "cloudcode-pa.googleapis.com",
                            "metadata": {
                                "uiMessage": "true",
                                "model": "gemini-3-flash-preview",
                            },
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert err.retry_delay_seconds == 35.0

    def test_model_capacity_exhausted_is_retryable(self):
        """MODEL_CAPACITY_EXHAUSTED → RetryableQuotaError with delay from message."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "You have exhausted your capacity on this model. "
                    "Your quota will reset after 24s.",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "MODEL_CAPACITY_EXHAUSTED",
                            "domain": "cloudcode-pa.googleapis.com",
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert err.retry_delay_seconds == 24.0

    def test_model_capacity_exhausted_with_retry_info(self):
        """MODEL_CAPACITY_EXHAUSTED + RetryInfo → prefers RetryInfo delay."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Capacity exhausted. Your quota will reset after 24s.",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "30s",
                        },
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "MODEL_CAPACITY_EXHAUSTED",
                            "domain": "cloudcode-pa.googleapis.com",
                        },
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        # RetryInfo (30s) takes precedence over text-extracted (24s)
        assert err.retry_delay_seconds == 30.0

    def test_model_capacity_exhausted_no_delay_hint(self):
        """MODEL_CAPACITY_EXHAUSTED without any delay hint → defaults to 30s."""
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "Capacity exhausted",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                            "reason": "MODEL_CAPACITY_EXHAUSTED",
                        }
                    ],
                }
            }
        )
        err = classify_google_error(429, body)
        assert isinstance(err, RetryableQuotaError)
        assert err.retry_delay_seconds == 30.0


class TestExtractDelayFromText:
    """Tests for _extract_delay_from_text helper."""

    def test_retry_in_seconds(self):
        """Matches 'retry in 5s'."""
        assert _extract_delay_from_text("Please retry in 5s") == 5.0

    def test_retry_in_milliseconds(self):
        """Matches 'retry in 500ms'."""
        assert _extract_delay_from_text("retry in 500ms") == 0.5

    def test_reset_after_seconds(self):
        """Matches 'reset after 24s'."""
        assert _extract_delay_from_text("Your quota will reset after 24s.") == 24.0

    def test_reset_after_float_seconds(self):
        """Matches 'reset after 34.07s'."""
        assert abs(_extract_delay_from_text("reset after 34.07s") - 34.07) < 0.01

    def test_reset_after_milliseconds(self):
        """Matches 'reset after 500ms'."""
        assert _extract_delay_from_text("reset after 500ms") == 0.5

    def test_no_match(self):
        """Returns None when no pattern found."""
        assert _extract_delay_from_text("Something went wrong") is None

    def test_case_insensitive(self):
        """Regex is case-insensitive."""
        assert _extract_delay_from_text("RESET AFTER 10S") == 10.0
        assert _extract_delay_from_text("Retry In 3s") == 3.0

    def test_real_google_message(self):
        """Matches actual Google 429 message format."""
        msg = (
            "You have exhausted your capacity on this model. "
            "Your quota will reset after 24s."
        )
        assert _extract_delay_from_text(msg) == 24.0


class TestParseRetryDelay:
    """Tests for parse_retry_delay with new patterns."""

    def test_retry_in_pattern(self):
        """Classic 'retry in 5s' pattern."""
        assert parse_retry_delay("retry in 5s", 10.0) == 5.0

    def test_reset_after_pattern(self):
        """New 'reset after 24s' pattern."""
        assert parse_retry_delay("reset after 24s", 10.0) == 24.0

    def test_fallback_to_backoff(self):
        """Falls back to jittered backoff when no pattern matches."""
        delay = parse_retry_delay("unknown error", 10.0)
        # Jitter is +-30%, so delay should be between 7.0 and 13.0
        assert 7.0 <= delay <= 13.0


class TestGeminiOAuthRetryAndFallback:
    """Tests for exact retry timing and provider-local model fallback."""

    @pytest.mark.asyncio
    async def test_get_response_waits_exact_delay_and_falls_back(self, provider):
        """Non-stream requests wait exact provider delay and switch models."""
        rate_limited = _make_mock_response(
            429,
            text=json.dumps(
                {
                    "error": {
                        "code": 429,
                        "message": "Rate limit hit",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "34.07s",
                            },
                            {
                                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                "reason": "RATE_LIMIT_EXCEEDED",
                                "domain": "cloudcode-pa.googleapis.com",
                            },
                        ],
                    }
                }
            ),
        )
        success = _make_mock_response(
            200,
            text=json.dumps(
                {
                    "response": {
                        "candidates": [{"content": {"parts": [{"text": "Fallback response"}]}}]
                    }
                }
            ),
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = MagicMock(
            side_effect=[
                _AsyncContextManager(rate_limited),
                _AsyncContextManager(success),
            ]
        )
        provider._session = mock_session

        with patch.object(provider, "_get_valid_token", AsyncMock(return_value="token")):
            with patch.object(provider, "_ensure_project_id", AsyncMock(return_value="project")):
                with patch(
                    "custom_components.homeclaw.providers.gemini_oauth.asyncio.sleep",
                    new=AsyncMock(),
                ) as sleep_mock:
                    result = await provider.get_response(
                        [{"role": "user", "content": "Hello"}]
                    )

        assert result == "Fallback response"
        assert sleep_mock.await_count == 1
        assert abs(sleep_mock.await_args.args[0] - 34.07) < 0.01
        posted_models = [
            call.kwargs["json"]["model"] for call in mock_session.post.call_args_list
        ]
        assert posted_models == ["gemini-3-pro-preview", "gemini-3-flash-preview"]
        assert provider._model == "gemini-3-pro-preview"

    def test_select_model_skips_cooled_down_preview_pro(self, provider):
        """Cooldown on preview pro pushes next request to preview flash."""
        provider._mark_model_cooldown("gemini-3-pro-preview", 20.0)

        selected_model, skipped_models = provider._select_model_for_request(
            "gemini-3-pro-preview"
        )

        assert selected_model == "gemini-3-flash-preview"
        assert skipped_models == ["gemini-3-pro-preview"]

    @pytest.mark.asyncio
    async def test_terminal_quota_does_not_fallback(self, provider):
        """Terminal quota errors do not trigger fallback or cooldown."""
        terminal = _make_mock_response(
            429,
            text=json.dumps(
                {
                    "error": {
                        "code": 429,
                        "message": "Quota exhausted",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                "reason": "QUOTA_EXHAUSTED",
                                "domain": "cloudcode-pa.googleapis.com",
                            }
                        ],
                    }
                }
            ),
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = MagicMock(return_value=_AsyncContextManager(terminal))
        provider._session = mock_session

        with patch.object(provider, "_get_valid_token", AsyncMock(return_value="token")):
            with patch.object(provider, "_ensure_project_id", AsyncMock(return_value="project")):
                with patch(
                    "custom_components.homeclaw.providers.gemini_oauth.asyncio.sleep",
                    new=AsyncMock(),
                ) as sleep_mock:
                    with pytest.raises(TerminalQuotaError):
                        await provider.get_response([{"role": "user", "content": "Hello"}])

        assert mock_session.post.call_count == 1
        assert provider._model_cooldowns == {}
        assert sleep_mock.await_count == 0

    @pytest.mark.asyncio
    async def test_stream_waits_exact_delay_and_emits_fallback_status(self, provider):
        """Streaming path respects provider delay and emits fallback status."""
        rate_limited = _make_mock_response(
            429,
            text=json.dumps(
                {
                    "error": {
                        "code": 429,
                        "message": "Rate limit hit",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": "12s",
                            },
                            {
                                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                "reason": "RATE_LIMIT_EXCEEDED",
                                "domain": "cloudcode-pa.googleapis.com",
                            },
                        ],
                    }
                }
            ),
        )
        stream_success = _make_mock_response(
            200,
            content_chunks=[
                b'data: {"response":{"candidates":[{"content":{"parts":[{"text":"stream ok"}]}}]}}\n',
                b"\n",
            ],
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = MagicMock(
            side_effect=[
                _AsyncContextManager(rate_limited),
                _AsyncContextManager(stream_success),
            ]
        )
        provider._session = mock_session

        with patch.object(provider, "_get_valid_token", AsyncMock(return_value="token")):
            with patch.object(provider, "_ensure_project_id", AsyncMock(return_value="project")):
                with patch(
                    "custom_components.homeclaw.providers.gemini_oauth.asyncio.sleep",
                    new=AsyncMock(),
                ) as sleep_mock:
                    chunks = [
                        chunk
                        async for chunk in provider.get_response_stream(
                            [{"role": "user", "content": "Hello"}]
                        )
                    ]

        assert sleep_mock.await_count == 1
        assert sleep_mock.await_args.args[0] == 12.0
        assert any(
            chunk["type"] == "status"
            and "retrying with gemini-3-flash-preview" in chunk["message"]
            for chunk in chunks
        )
        assert any(
            chunk["type"] == "text" and chunk["content"] == "stream ok"
            for chunk in chunks
        )
        posted_models = [
            call.kwargs["json"]["model"] for call in mock_session.post.call_args_list
        ]
        assert posted_models == ["gemini-3-pro-preview", "gemini-3-flash-preview"]

    @pytest.mark.asyncio
    async def test_stream_uses_message_delay_when_retry_info_missing(self, provider):
        """Streaming uses reset-after delay from message when RetryInfo is absent."""
        provider._model = "gemini-3-flash-preview"

        rate_limited = _make_mock_response(
            429,
            text=json.dumps(
                {
                    "error": {
                        "code": 429,
                        "message": "You have exhausted your capacity on this model. "
                        "Your quota will reset after 35s.",
                        "status": "RESOURCE_EXHAUSTED",
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                "reason": "RATE_LIMIT_EXCEEDED",
                                "domain": "cloudcode-pa.googleapis.com",
                                "metadata": {
                                    "uiMessage": "true",
                                    "model": "gemini-3-flash-preview",
                                },
                            }
                        ],
                    }
                }
            ),
        )
        stream_success = _make_mock_response(
            200,
            content_chunks=[
                b'data: {"response":{"candidates":[{"content":{"parts":[{"text":"stream ok"}]}}]}}\n',
                b"\n",
            ],
        )

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = MagicMock(
            side_effect=[
                _AsyncContextManager(rate_limited),
                _AsyncContextManager(stream_success),
            ]
        )
        provider._session = mock_session

        with patch.object(provider, "_get_valid_token", AsyncMock(return_value="token")):
            with patch.object(provider, "_ensure_project_id", AsyncMock(return_value="project")):
                with patch(
                    "custom_components.homeclaw.providers.gemini_oauth.asyncio.sleep",
                    new=AsyncMock(),
                ) as sleep_mock:
                    chunks = [
                        chunk
                        async for chunk in provider.get_response_stream(
                            [{"role": "user", "content": "Hello"}]
                        )
                    ]

        assert sleep_mock.await_count == 1
        assert sleep_mock.await_args.args[0] == 35.0
        assert any(
            chunk["type"] == "text" and chunk["content"] == "stream ok"
            for chunk in chunks
        )
        posted_models = [
            call.kwargs["json"]["model"] for call in mock_session.post.call_args_list
        ]
        assert posted_models == ["gemini-3-flash-preview", "gemini-3-flash-preview"]
