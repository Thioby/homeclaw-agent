"""Base HTTP client for AI providers."""
from __future__ import annotations

import asyncio
import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .registry import AIProvider

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class BaseHTTPClient(AIProvider):
    """Base class for HTTP-based AI providers.

    This class provides common HTTP functionality for AI providers that
    communicate via REST APIs. Subclasses must implement the abstract
    methods to customize the request/response handling.
    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the HTTP client.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration dictionary.
        """
        super().__init__(hass, config)
        self._max_retries = config.get("max_retries", self.DEFAULT_MAX_RETRIES)
        self._retry_delay = config.get("retry_delay", self.DEFAULT_RETRY_DELAY)

    @property
    def session(self) -> ClientSession:
        """Get the aiohttp client session.

        Returns:
            The aiohttp ClientSession for making HTTP requests.
        """
        return async_get_clientsession(self.hass)

    @property
    @abstractmethod
    def api_url(self) -> str:
        """Return the API endpoint URL.

        Returns:
            The full URL for the API endpoint.
        """

    @abstractmethod
    def _build_headers(self) -> dict[str, str]:
        """Build the HTTP headers for the request.

        Returns:
            Dictionary of HTTP headers.
        """

    @abstractmethod
    def _build_payload(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Build the request payload.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The request payload dictionary.
        """

    @abstractmethod
    def _extract_response(self, response_data: dict[str, Any]) -> str:
        """Extract the response text from the API response.

        Args:
            response_data: The parsed JSON response from the API.

        Returns:
            The extracted response text.
        """

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Get a response from the AI provider.

        This is the template method that orchestrates the HTTP request
        with retry logic.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The AI response as a string.

        Raises:
            Exception: If the request fails after all retries.
        """
        headers = self._build_headers()
        payload = self._build_payload(messages, **kwargs)

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                async with self.session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return self._extract_response(response_data)

                    # Log non-200 responses
                    error_text = await response.text()
                    _LOGGER.warning(
                        "API request failed (attempt %d/%d): status=%d, body=%s",
                        attempt + 1,
                        self._max_retries,
                        response.status,
                        error_text,
                    )
                    last_error = Exception(
                        f"API request failed with status {response.status}: {error_text}"
                    )

            except Exception as e:
                _LOGGER.warning(
                    "API request exception (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries,
                    str(e),
                )
                last_error = e

            # Wait before retry (unless this is the last attempt)
            if attempt < self._max_retries - 1:
                await asyncio.sleep(self._retry_delay)

        # All retries exhausted
        raise last_error or Exception("API request failed after all retries")
