"""Tests for the BaseHTTPClient."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.providers.base_client import BaseHTTPClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class ConcreteHTTPClient(BaseHTTPClient):
    """Concrete implementation for testing abstract methods."""

    @property
    def supports_tools(self) -> bool:
        return True

    def _build_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer test_key"}

    def _build_payload(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return {"messages": messages, **kwargs}

    def _extract_response(self, response_data: dict[str, Any]) -> str:
        return response_data.get("content", "")

    @property
    def api_url(self) -> str:
        return "https://api.test.com/v1/chat"


class IncompleteClient(BaseHTTPClient):
    """Client that doesn't implement abstract methods - for testing."""

    @property
    def supports_tools(self) -> bool:
        return False


class TestBaseHTTPClientAbstractMethods:
    """Tests for BaseHTTPClient abstract method behavior."""

    def test_build_headers_abstract(self, hass: HomeAssistant) -> None:
        """Test that _build_headers raises NotImplementedError when not implemented."""
        config = {}

        # Cannot even instantiate without implementing all abstract methods
        with pytest.raises(TypeError, match="abstract method"):
            IncompleteClient(hass, config)

    def test_build_payload_abstract(self, hass: HomeAssistant) -> None:
        """Test that _build_payload raises NotImplementedError when not implemented."""
        config = {}

        # Same - abstract methods must all be implemented
        with pytest.raises(TypeError, match="abstract method"):
            IncompleteClient(hass, config)

    def test_extract_response_abstract(self, hass: HomeAssistant) -> None:
        """Test that _extract_response raises NotImplementedError when not implemented."""
        config = {}

        # Same - abstract methods must all be implemented
        with pytest.raises(TypeError, match="abstract method"):
            IncompleteClient(hass, config)


class TestBaseHTTPClientSession:
    """Tests for BaseHTTPClient session property."""

    def test_session_uses_async_get_clientsession(self, hass: HomeAssistant) -> None:
        """Test that session property uses async_get_clientsession."""
        mock_session = MagicMock()
        config = {}

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ) as mock_get_session:
            client = ConcreteHTTPClient(hass, config)
            session = client.session

            mock_get_session.assert_called_once_with(hass)
            assert session is mock_session


class TestBaseHTTPClientGetResponse:
    """Tests for BaseHTTPClient get_response template method."""

    @pytest.mark.asyncio
    async def test_get_response_success(self, hass: HomeAssistant) -> None:
        """Test successful response from API."""
        config = {}
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"content": "Hello there!"})

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            client = ConcreteHTTPClient(hass, config)
            response = await client.get_response(messages)

            assert response == "Hello there!"

    @pytest.mark.asyncio
    async def test_get_response_with_retry_on_failure(self, hass: HomeAssistant) -> None:
        """Test that get_response retries on transient failures."""
        config = {"max_retries": 3, "retry_delay": 0.01}
        messages = [{"role": "user", "content": "Hello"}]

        # First call fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status = 500
        mock_response_fail.text = AsyncMock(return_value="Server Error")

        mock_response_success = MagicMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={"content": "Success!"})

        call_count = 0

        class MockContextManager:
            """Mock async context manager that returns different responses."""

            async def __aenter__(self):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return mock_response_fail
                return mock_response_success

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=MockContextManager())

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            client = ConcreteHTTPClient(hass, config)
            response = await client.get_response(messages)

            assert response == "Success!"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_get_response_max_retries_exceeded(self, hass: HomeAssistant) -> None:
        """Test that get_response raises after max retries exceeded."""
        config = {"max_retries": 2, "retry_delay": 0.01}
        messages = [{"role": "user", "content": "Hello"}]

        mock_response_fail = MagicMock()
        mock_response_fail.status = 500
        mock_response_fail.text = AsyncMock(return_value="Server Error")

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response_fail)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_context)

        with patch(
            "custom_components.homeclaw.providers.base_client.async_get_clientsession",
            return_value=mock_session,
        ):
            client = ConcreteHTTPClient(hass, config)

            with pytest.raises(Exception, match="API request failed"):
                await client.get_response(messages)
