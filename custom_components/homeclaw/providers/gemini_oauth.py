"""Gemini OAuth provider implementation using Cloud Code Assist API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

import aiohttp

from ._gemini_constants import (
    DEFAULT_MODEL,
    GEMINI_AVAILABLE_MODELS,
    GEMINI_CODE_ASSIST_ENDPOINT,
    GEMINI_CODE_ASSIST_METADATA,
    INITIAL_DELAY_MS,
    MAX_ATTEMPTS,
    MAX_DELAY_MS,
    TRANSPORT_MAX_RETRIES,
    TRANSPORT_RETRY_DELAY_S,
    RateLimitError,
    RetryableQuotaError,
    TerminalQuotaError,
    _build_user_agent,
    is_retryable_status_in_text,
)
from ._gemini_convert import convert_messages, convert_tools, process_gemini_chunk
from ._gemini_retry import classify_google_error, parse_retry_delay
from .registry import AIProvider, ProviderRegistry

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Re-export for backward compatibility (tests import these from gemini_oauth)
__all__ = [
    "GeminiOAuthProvider",
    "RateLimitError",
    "GEMINI_CODE_ASSIST_ENDPOINT",
    "GEMINI_CODE_ASSIST_METADATA",
    "GEMINI_AVAILABLE_MODELS",
]

MODEL_FALLBACK_CHAINS: dict[str, list[str]] = {
    "gemini-3-pro-preview": ["gemini-3-pro-preview", "gemini-3-flash-preview"],
    "gemini-2.5-flash-lite": [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ],
}


@ProviderRegistry.register("gemini_oauth")
class GeminiOAuthProvider(AIProvider):
    """Gemini provider using OAuth authentication via Cloud Code Assist API.

    Uses cloudcode-pa.googleapis.com endpoint which requires OAuth Bearer token
    and a managed project ID. On first use, the provider will automatically
    onboard the user to obtain a project ID for the FREE tier.
    """

    # Retry configuration (from gemini-cli)
    MAX_ATTEMPTS = MAX_ATTEMPTS
    INITIAL_DELAY_MS = INITIAL_DELAY_MS
    MAX_DELAY_MS = MAX_DELAY_MS
    DEFAULT_MODEL = DEFAULT_MODEL

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize the Gemini OAuth provider.

        Args:
            hass: Home Assistant instance.
            config: Provider configuration containing:
                - config_entry: ConfigEntry with OAuth tokens
                - model: Optional model name (default: gemini-3-pro-preview)
        """
        super().__init__(hass, config)
        self._model = config.get("model", self.DEFAULT_MODEL)
        self._config_entry: ConfigEntry | None = config.get("config_entry")
        self._oauth_data: dict[str, Any] = {}
        self._refresh_lock = asyncio.Lock()
        self._project_lock = asyncio.Lock()
        self._model_cooldowns: dict[str, float] = {}
        self._session: aiohttp.ClientSession | None = None

        # Load OAuth data from config entry
        if self._config_entry:
            self._oauth_data = dict(self._config_entry.data.get("gemini_oauth", {}))

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a reusable aiohttp session with connection pooling.

        Returns:
            Shared aiohttp.ClientSession with keep-alive and connection limits.
        """
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def async_close(self) -> None:
        """Close the shared HTTP session. Call on shutdown or entry removal."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @property
    def supports_tools(self) -> bool:
        """Return True as Gemini supports function calling."""
        return True

    @property
    def lightweight_model(self) -> str | None:
        """Return the cheapest Gemini model for background tasks."""
        from ..models import get_lightweight_model

        return get_lightweight_model("gemini_oauth") or self._model

    # ------------------------------------------------------------------
    # OAuth token management
    # ------------------------------------------------------------------

    async def _get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Re-reads the config entry under the refresh lock so that a
        concurrent refresh by another task is picked up.  On permanent
        failures (``invalid_grant``) triggers HA's re-auth flow.

        Returns:
            Valid access token string.

        Raises:
            GeminiOAuthRefreshError: If no token available or refresh fails.
        """
        from ..gemini_oauth import GeminiOAuthRefreshError, refresh_token

        async with self._refresh_lock:
            # Re-read persisted tokens — another task may have refreshed.
            if self._config_entry:
                fresh = dict(self._config_entry.data.get("gemini_oauth", {}))
                if fresh.get("access_token"):
                    self._oauth_data = fresh

            # Check if token is still valid (with 5 minute buffer)
            if time.time() < self._oauth_data.get("expires_at", 0) - 300:
                access_token = self._oauth_data.get("access_token")
                if not access_token:
                    self._trigger_reauth()
                    raise GeminiOAuthRefreshError(
                        "No access token available - re-authentication required",
                        is_permanent=True,
                    )
                return access_token

            _LOGGER.debug("Refreshing Gemini OAuth token")

            # Check if refresh token exists
            refresh_tok = self._oauth_data.get("refresh_token")
            if not refresh_tok:
                self._trigger_reauth()
                raise GeminiOAuthRefreshError(
                    "No refresh token available - re-authentication required",
                    is_permanent=True,
                )

            try:
                new_tokens = await refresh_token(self._get_session(), refresh_tok)
            except GeminiOAuthRefreshError as e:
                _LOGGER.error("Gemini OAuth refresh failed: %s", e)
                if e.is_permanent:
                    self._trigger_reauth()
                raise

            self._oauth_data.update(new_tokens)
            self._persist_oauth_data()
            return new_tokens["access_token"]

    def _trigger_reauth(self) -> None:
        """Request HA re-authentication flow for this config entry."""
        if not self._config_entry:
            return
        try:
            self._config_entry.async_start_reauth(self.hass)
            _LOGGER.warning(
                "Gemini OAuth: triggered re-authentication flow — "
                "check Home Assistant notifications"
            )
        except Exception:
            _LOGGER.debug("Could not trigger reauth flow", exc_info=True)

    def _persist_oauth_data(self) -> None:
        """Persist current OAuth data to config entry."""
        if self._config_entry:
            new_data = {
                **self._config_entry.data,
                "gemini_oauth": self._oauth_data,
            }
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )

    # ------------------------------------------------------------------
    # Project ID management / onboarding
    # ------------------------------------------------------------------

    async def _save_project_id(self, project_id: str) -> None:
        """Persist managed project ID to config entry."""
        self._oauth_data["managed_project_id"] = project_id
        self._persist_oauth_data()
        _LOGGER.info("Saved Gemini managed project ID: %s", project_id)

    async def _ensure_project_id(
        self, session: aiohttp.ClientSession, access_token: str
    ) -> str:
        """Ensure we have a valid project ID, onboarding if necessary.

        Cloud Code Assist API requires a project ID for all requests.
        For FREE tier users, Google provides a managed project automatically.

        Returns:
            The managed project ID.

        Raises:
            Exception: If project ID cannot be obtained.
        """
        async with self._project_lock:
            # 1. Check if we have cached project ID
            project_id = self._oauth_data.get("managed_project_id")
            if project_id:
                _LOGGER.debug("Using cached Gemini project ID: %s", project_id)
                return project_id

            _LOGGER.info("No Gemini project ID cached, resolving...")

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": _build_user_agent(self._model),
            }

            # 2. Try loadCodeAssist to get existing project
            try:
                async with session.post(
                    f"{GEMINI_CODE_ASSIST_ENDPOINT}:loadCodeAssist",
                    headers=headers,
                    json={"metadata": GEMINI_CODE_ASSIST_METADATA},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    response_text = await resp.text()
                    _LOGGER.debug(
                        "loadCodeAssist response (%d): %s",
                        resp.status,
                        response_text[:500],
                    )
                    if resp.status == 200:
                        data = json.loads(response_text)
                        project_id = data.get("cloudaicompanionProject")
                        if project_id:
                            _LOGGER.info(
                                "Found existing Gemini project: %s", project_id
                            )
                            await self._save_project_id(project_id)
                            return project_id

                        # Check tier - enterprise users need their own project
                        current_tier = data.get("currentTier", {}).get("id")
                        if current_tier and current_tier != "FREE":
                            raise Exception(
                                f"Gemini tier '{current_tier}' requires manual project configuration."
                            )

                        _LOGGER.info(
                            "loadCodeAssist returned no project, will try onboarding"
                        )
                    else:
                        _LOGGER.warning(
                            "loadCodeAssist failed (%d): %s",
                            resp.status,
                            response_text[:200],
                        )
            except aiohttp.ClientError as e:
                _LOGGER.warning("loadCodeAssist request failed: %s", e)

            # 3. Onboard user for FREE tier (with retry loop)
            _LOGGER.info("Onboarding new Gemini FREE tier user...")

            max_attempts = 10
            delay_seconds = 5

            for attempt in range(max_attempts):
                try:
                    async with session.post(
                        f"{GEMINI_CODE_ASSIST_ENDPOINT}:onboardUser",
                        headers=headers,
                        json={
                            "tierId": "FREE",
                            "metadata": GEMINI_CODE_ASSIST_METADATA,
                        },
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            _LOGGER.debug(
                                "onboardUser response (attempt %d): %s",
                                attempt + 1,
                                json.dumps(data)[:300],
                            )

                            # Check if onboarding is complete
                            if data.get("done"):
                                project_id = (
                                    data.get("response", {})
                                    .get("cloudaicompanionProject", {})
                                    .get("id")
                                )
                                if project_id:
                                    _LOGGER.info(
                                        "Gemini onboarding complete, project: %s",
                                        project_id,
                                    )
                                    await self._save_project_id(project_id)
                                    return project_id
                        else:
                            error_text = await resp.text()
                            _LOGGER.warning(
                                "onboardUser failed (%d): %s",
                                resp.status,
                                error_text[:200],
                            )
                except aiohttp.ClientError as e:
                    _LOGGER.warning(
                        "onboardUser request failed (attempt %d): %s", attempt + 1, e
                    )

                if attempt < max_attempts - 1:
                    _LOGGER.debug(
                        "Onboarding in progress, waiting %ds (attempt %d/%d)...",
                        delay_seconds,
                        attempt + 1,
                        max_attempts,
                    )
                    await asyncio.sleep(delay_seconds)

            raise Exception(
                "Failed to obtain Gemini project ID after onboarding. "
                "Please try again later or check your Google account permissions."
            )

    # ------------------------------------------------------------------
    # Message / tool conversion (delegate to pure functions)
    # ------------------------------------------------------------------

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Convert OpenAI-style messages to Gemini format."""
        return convert_messages(messages)

    def _convert_tools(
        self, openai_tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Gemini functionDeclarations format."""
        return convert_tools(openai_tools)

    # ------------------------------------------------------------------
    # Request payload building (shared by streaming and non-streaming)
    # ------------------------------------------------------------------

    def _build_request_payload(
        self, messages: list[dict[str, Any]], model: str, **kwargs: Any
    ) -> tuple[dict[str, Any], str]:
        """Build the Gemini API request payload.

        Converts messages, adds system instruction and tools.
        Returns the request_payload dict and the validated model name.

        Args:
            messages: List of message dictionaries with role and content.
            model: Model name to use (will be validated).
            **kwargs: Additional arguments (tools, temperature, etc.).

        Returns:
            Tuple of (request_payload, validated_model).
        """
        model = self._normalize_model(model)

        # Convert messages to Gemini format
        gemini_contents, system_instruction = self._convert_messages(messages)

        # Build request payload
        request_payload: dict[str, Any] = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": self.config.get("temperature", 0.2),
                "maxOutputTokens": 8192,
            },
        }

        # Add system instruction if present
        if system_instruction:
            request_payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # Add tools for function calling if provided
        tools = kwargs.get("tools")
        if tools:
            from .gemini_schema_sanitizer import clean_tools_for_gemini

            cleaned_tools = clean_tools_for_gemini(tools)
            gemini_tools = self._convert_tools(cleaned_tools)
            if gemini_tools:
                request_payload["tools"] = gemini_tools

        return request_payload, model

    def _normalize_model(self, model: str) -> str:
        """Validate a requested model against the configured Gemini OAuth list."""
        if model not in GEMINI_AVAILABLE_MODELS:
            _LOGGER.warning(
                "Model '%s' not in available models, using default '%s'",
                model,
                self.DEFAULT_MODEL,
            )
            return self.DEFAULT_MODEL
        return model

    def _get_model_chain(self, requested_model: str) -> list[str]:
        """Return the provider-local fallback chain for the requested model."""
        normalized_model = self._normalize_model(requested_model)
        chain = MODEL_FALLBACK_CHAINS.get(normalized_model, [normalized_model])
        filtered_chain = [model for model in chain if model in GEMINI_AVAILABLE_MODELS]
        return filtered_chain or [normalized_model]

    def _get_model_cooldown_remaining(self, model: str) -> float:
        """Return remaining cooldown seconds for a model, cleaning up expired entries."""
        cooldown_until = self._model_cooldowns.get(model)
        if cooldown_until is None:
            return 0.0

        remaining = cooldown_until - time.monotonic()
        if remaining <= 0:
            self._model_cooldowns.pop(model, None)
            return 0.0

        return remaining

    def _mark_model_cooldown(self, model: str, delay_seconds: float | None) -> None:
        """Record a temporary cooldown for a model after a retryable quota response."""
        if not delay_seconds or delay_seconds <= 0:
            return

        cooldown_until = time.monotonic() + delay_seconds
        previous_until = self._model_cooldowns.get(model, 0.0)
        if cooldown_until > previous_until:
            self._model_cooldowns[model] = cooldown_until
            _LOGGER.info(
                "Gemini model '%s' cooling down for %.1fs after quota response",
                model,
                delay_seconds,
            )

    def _select_model_for_request(self, requested_model: str) -> tuple[str, list[str]]:
        """Choose the first available model in the local fallback chain."""
        chain = self._get_model_chain(requested_model)
        skipped_models: list[str] = []

        for model in chain:
            if self._get_model_cooldown_remaining(model) <= 0:
                return model, skipped_models
            skipped_models.append(model)

        return chain[-1], skipped_models

    def _record_retryable_cooldown(
        self, model: str, status: int, error: RetryableQuotaError
    ) -> None:
        """Store cooldown only for retryable rate limits that apply to a model."""
        if status in (429, 499):
            self._mark_model_cooldown(model, error.retry_delay_seconds)

    # ------------------------------------------------------------------
    # Non-streaming request
    # ------------------------------------------------------------------

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Application-level retry with exponential backoff for 429 and 5xx.

        This is the slow retry loop (initial 5s, max 30s, 10 attempts).
        Transport-level fast retry (3x, 1s) is handled inside _do_request().
        TerminalQuotaError is never retried.
        """
        attempt = 0
        current_delay = self.INITIAL_DELAY_MS / 1000

        while attempt < self.MAX_ATTEMPTS:
            attempt += 1
            try:
                return await func(*args, **kwargs)
            except TerminalQuotaError:
                # Never retry terminal errors (daily limit, insufficient credits)
                raise
            except RetryableQuotaError as e:
                if attempt >= self.MAX_ATTEMPTS:
                    _LOGGER.error(
                        "Max retry attempts (%d) reached for Gemini API",
                        self.MAX_ATTEMPTS,
                    )
                    raise
                # Use server-suggested delay if available
                delay = (
                    e.retry_delay_seconds if e.retry_delay_seconds else current_delay
                )
                _LOGGER.warning(
                    "Gemini API retryable quota error (attempt %d/%d). Retrying in %.1fs...",
                    attempt,
                    self.MAX_ATTEMPTS,
                    delay,
                )
                await asyncio.sleep(delay)
                current_delay = min(self.MAX_DELAY_MS / 1000, current_delay * 2)
            except Exception as e:
                error_str = str(e)
                is_retryable = is_retryable_status_in_text(error_str)
                if not is_retryable:
                    raise
                if attempt >= self.MAX_ATTEMPTS:
                    _LOGGER.error(
                        "Max retry attempts (%d) reached for Gemini API",
                        self.MAX_ATTEMPTS,
                    )
                    raise

                delay = parse_retry_delay(error_str, current_delay)
                _LOGGER.warning(
                    "Gemini API error (attempt %d/%d). Retrying in %.1fs...",
                    attempt,
                    self.MAX_ATTEMPTS,
                    delay,
                )
                await asyncio.sleep(delay)
                current_delay = min(self.MAX_DELAY_MS / 1000, current_delay * 2)

        raise Exception("Retry attempts exhausted")

    async def _do_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: dict,
        wrapped_payload: dict,
    ) -> str:
        """Execute the HTTP request with fast transport-level retry.

        Transport retry: max 3 attempts, 1s delay, only on connection/timeouts.
        HTTP error responses are classified immediately so provider-suggested
        retry delays are respected.
        """
        # Log request details (without sensitive data)
        request_contents = wrapped_payload.get("request", {}).get("contents", [])
        _LOGGER.debug(
            "Gemini OAuth request: model=%s, contents_count=%d, has_tools=%s",
            wrapped_payload.get("model"),
            len(request_contents),
            "tools" in wrapped_payload.get("request", {}),
        )
        if request_contents:
            last_content = request_contents[-1]
            parts = last_content.get("parts", [])
            if parts and "text" in parts[0]:
                text_preview = parts[0]["text"][:100]
                _LOGGER.debug("Gemini OAuth request last message: %s...", text_preview)

        # Transport-level fast retry loop (max 3, 1s delay, 429/499/5xx only)
        last_transport_exc: Exception | None = None
        for transport_attempt in range(TRANSPORT_MAX_RETRIES + 1):
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=wrapped_payload,
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:
                    response_text = await resp.text()

                    _LOGGER.debug(
                        "Gemini OAuth response: status=%d, length=%d",
                        resp.status,
                        len(response_text),
                    )

                    if resp.status != 200:
                        _LOGGER.debug(
                            "Gemini error response (HTTP %d, full body):\n%s",
                            resp.status,
                            response_text,
                        )
                        classified = classify_google_error(resp.status, response_text)
                        if isinstance(classified, RetryableQuotaError):
                            self._record_retryable_cooldown(
                                str(wrapped_payload.get("model", self._model)),
                                resp.status,
                                classified,
                            )
                        raise classified

                    return self._parse_response(response_text)

            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_transport_exc = exc
                if transport_attempt < TRANSPORT_MAX_RETRIES:
                    _LOGGER.warning(
                        "Gemini transport retry %d/%d on %s: %s",
                        transport_attempt + 1,
                        TRANSPORT_MAX_RETRIES,
                        type(exc).__name__,
                        exc,
                    )
                    await asyncio.sleep(TRANSPORT_RETRY_DELAY_S)
                    continue
                raise Exception(
                    f"Gemini connection error after {TRANSPORT_MAX_RETRIES} retries: {exc}"
                ) from exc

        # Should never reach here, but satisfy type checker
        if last_transport_exc:
            raise last_transport_exc
        raise Exception("Transport retry loop exited unexpectedly")

    def _parse_response(self, response_text: str) -> str:
        """Parse and extract the response from Gemini API JSON.

        Args:
            response_text: Raw JSON response text from the API.

        Returns:
            Extracted text response or serialized JSON.
        """
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            _LOGGER.error(
                "Gemini OAuth JSON decode error: %s, response: %s",
                e,
                response_text[:500],
            )
            raise Exception(f"Invalid JSON response from Gemini: {e}")

        _LOGGER.debug(
            "Gemini OAuth response keys: %s",
            list(data.keys()) if isinstance(data, dict) else type(data),
        )

        # Unwrap response if it contains 'response' key (Cloud Code API)
        if "response" in data:
            data = data["response"]
            _LOGGER.debug("Gemini OAuth unwrapped response keys: %s", list(data.keys()))

        # Check for error in response
        if "error" in data:
            error_info = data["error"]
            _LOGGER.error(
                "Gemini OAuth API returned error: %s", json.dumps(error_info)[:500]
            )
            raise Exception(f"Gemini API error: {error_info}")

        # Extract response from Gemini format
        candidates = data.get("candidates", [])
        _LOGGER.debug("Gemini OAuth candidates count: %d", len(candidates))

        if candidates:
            finish_reason = candidates[0].get("finishReason")
            if finish_reason:
                _LOGGER.debug("Gemini OAuth finish reason: %s", finish_reason)

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            _LOGGER.debug("Gemini OAuth parts count: %d", len(parts))

            if parts:
                first_part = parts[0]
                if "functionCall" in first_part:
                    func_name = first_part["functionCall"].get("name", "unknown")
                    _LOGGER.debug("Gemini OAuth function call detected: %s", func_name)
                    return json.dumps(first_part)
                if "text" in first_part:
                    text_response = first_part["text"]
                    _LOGGER.debug(
                        "Gemini OAuth text response length: %d, preview: %s...",
                        len(text_response),
                        text_response[:100],
                    )
                    return text_response
                _LOGGER.warning(
                    "Gemini OAuth unexpected part format: %s",
                    list(first_part.keys()),
                )
                return json.dumps(data)
        else:
            prompt_feedback = data.get("promptFeedback")
            if prompt_feedback:
                _LOGGER.warning(
                    "Gemini OAuth prompt feedback (possibly blocked): %s",
                    json.dumps(prompt_feedback),
                )

        _LOGGER.warning("Unexpected Gemini response format: %s", response_text[:500])
        return json.dumps(data)

    async def get_response(self, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        """Get a response from Gemini using OAuth token.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments:
                - tools: List of tools for function calling.
                - model: Optional model override (must be in GEMINI_AVAILABLE_MODELS).

        Returns:
            The AI response as a string.
        """
        requested_model = self._normalize_model(kwargs.get("model") or self._model)

        _LOGGER.info(
            "GeminiOAuthProvider.get_response called. managed_project_id: %s, model: %s",
            self._oauth_data.get("managed_project_id", "NOT_SET"),
            requested_model,
        )
        access_token = await self._get_valid_token()

        build_kwargs = {k: v for k, v in kwargs.items() if k != "model"}
        session = self._get_session()
        project_id = await self._ensure_project_id(session, access_token)
        url = f"{GEMINI_CODE_ASSIST_ENDPOINT}:generateContent"

        async def _perform_request() -> str:
            model, skipped_models = self._select_model_for_request(requested_model)
            request_payload, model = self._build_request_payload(
                messages, model, **build_kwargs
            )

            if model != requested_model:
                _LOGGER.info(
                    "Gemini OAuth fallback model selected: requested=%s actual=%s skipped=%s",
                    requested_model,
                    model,
                    skipped_models or None,
                )

            _LOGGER.debug(
                "Gemini OAuth message conversion: %d contents, system_instruction: %s",
                len(request_payload.get("contents", [])),
                "YES" if "systemInstruction" in request_payload else "NO",
            )
            if "systemInstruction" in request_payload:
                si_text = request_payload["systemInstruction"]["parts"][0]["text"]
                _LOGGER.debug(
                    "Gemini OAuth system instruction added (%d chars), preview: %s...",
                    len(si_text),
                    si_text[:200],
                )
            if "tools" in request_payload:
                _LOGGER.debug(
                    "Added %d tools to Gemini OAuth request",
                    len(request_payload["tools"][0].get("functionDeclarations", [])),
                )

            wrapped_payload = {
                "project": project_id,
                "model": model,
                "user_prompt_id": str(uuid.uuid4()),
                "request": request_payload,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "User-Agent": _build_user_agent(model),
            }

            _LOGGER.debug("Gemini OAuth request URL: %s", url)
            _LOGGER.debug(
                "Gemini OAuth wrapped payload: project=%s, model=%s",
                project_id,
                model,
            )

            return await self._do_request(session, url, headers, wrapped_payload)

        return await self._retry_with_backoff(_perform_request)

    # ------------------------------------------------------------------
    # Streaming request
    # ------------------------------------------------------------------

    async def get_response_stream(self, messages: list[dict[str, Any]], **kwargs: Any):
        """Stream response from Gemini using OAuth token with retry logic.

        Args:
            messages: List of message dictionaries with role and content.
            **kwargs: Additional arguments:
                - tools: List of tools for function calling.
                - model: Optional model override (must be in GEMINI_AVAILABLE_MODELS).

        Yields:
            Dict chunks with type and content:
                - {"type": "text", "content": str} - text chunks
                - {"type": "tool_call", "name": str, "args": dict} - function calls
                - {"type": "status", "message": str} - status updates
                - {"type": "error", "message": str} - errors
        """
        requested_model = self._normalize_model(kwargs.get("model") or self._model)
        build_kwargs = {k: v for k, v in kwargs.items() if k != "model"}
        attempt = 0
        current_delay = self.INITIAL_DELAY_MS / 1000
        stream_started = False

        while attempt < self.MAX_ATTEMPTS:
            attempt += 1

            try:
                async for chunk in self._do_stream_request(
                    messages, requested_model, **build_kwargs
                ):
                    if chunk.get("type") in ["text", "tool_call"]:
                        stream_started = True
                    yield chunk

                # Successfully completed streaming
                return

            except TerminalQuotaError as e:
                _LOGGER.error("Terminal quota error during streaming: %s", e)
                yield {
                    "type": "error",
                    "message": f"Quota exhausted: {e}. "
                    "Please wait for quota reset or upgrade your plan.",
                }
                return

            except RateLimitError as e:
                if attempt >= self.MAX_ATTEMPTS:
                    _LOGGER.error(
                        "Max retry attempts (%d) reached for streaming request",
                        self.MAX_ATTEMPTS,
                    )
                    yield {
                        "type": "error",
                        "message": "Rate limit exceeded after multiple retries. "
                        "Please wait and try again, or consider using Provisioned Throughput.",
                    }
                    return

                # Use server-suggested delay if available (RetryableQuotaError)
                if isinstance(e, RetryableQuotaError) and e.retry_delay_seconds:
                    delay = e.retry_delay_seconds
                else:
                    delay = parse_retry_delay(str(e), current_delay)

                _LOGGER.warning(
                    "Streaming rate limited, retrying in %.1fs (attempt %d/%d)",
                    delay,
                    attempt,
                    self.MAX_ATTEMPTS,
                )

                if stream_started:
                    yield {
                        "type": "status",
                        "message": f"Connection interrupted, retrying in {delay:.1f}s... "
                        f"(attempt {attempt}/{self.MAX_ATTEMPTS})",
                    }

                await asyncio.sleep(delay)
                current_delay = min(self.MAX_DELAY_MS / 1000, current_delay * 2)
                stream_started = False
                continue

            except Exception as e:
                _LOGGER.error("Streaming request failed: %s", e)
                yield {"type": "error", "message": f"Streaming error: {str(e)}"}
                return

    async def _do_stream_request(
        self, messages: list[dict[str, Any]], requested_model: str, **kwargs: Any
    ):
        """Internal method that performs the actual streaming request.

        Raises RateLimitError if 429 is encountered before streaming starts.
        """
        model, skipped_models = self._select_model_for_request(requested_model)
        if model != requested_model:
            yield {
                "type": "status",
                "message": f"Model {requested_model} is cooling down after rate limit; retrying with {model}.",
            }
            _LOGGER.info(
                "Gemini OAuth streaming fallback model selected: requested=%s actual=%s skipped=%s",
                requested_model,
                model,
                skipped_models or None,
            )

        _LOGGER.info("GeminiOAuthProvider._do_stream_request called. model: %s", model)
        access_token = await self._get_valid_token()

        request_payload, model = self._build_request_payload(
            messages, model, **kwargs
        )

        session = self._get_session()
        project_id = await self._ensure_project_id(session, access_token)

        wrapped_payload = {
            "project": project_id,
            "model": model,
            "user_prompt_id": str(uuid.uuid4()),
            "request": request_payload,
        }

        url = f"{GEMINI_CODE_ASSIST_ENDPOINT}:streamGenerateContent"
        url += "?alt=sse"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": _build_user_agent(model),
        }

        _LOGGER.info("Gemini OAuth SSE STREAMING request to: %s", url)

        try:
            async with session.post(
                url,
                headers=headers,
                json=wrapped_payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                _LOGGER.info("Gemini streaming response status: %d", resp.status)

                if resp.status != 200:
                    error_text = await resp.text()
                    _LOGGER.debug(
                        "Gemini streaming error response (HTTP %d, full body):\n%s",
                        resp.status,
                        error_text,
                    )
                    classified = classify_google_error(resp.status, error_text)

                    if isinstance(classified, TerminalQuotaError):
                        _LOGGER.error(
                            "Gemini terminal quota error: %s (reason=%s)",
                            classified,
                            classified.reason,
                        )
                        yield {
                            "type": "error",
                            "message": f"Quota exhausted: {classified}. "
                            "Please wait for quota reset or upgrade your plan.",
                        }
                        return

                    if isinstance(classified, RetryableQuotaError):
                        self._record_retryable_cooldown(model, resp.status, classified)
                        _LOGGER.warning(
                            "Gemini rate limited (%d), delay=%.1fs: %s",
                            resp.status,
                            classified.retry_delay_seconds or 0,
                            error_text[:200],
                        )
                        raise classified

                    if isinstance(classified, RateLimitError):
                        raise classified

                    _LOGGER.error(
                        "Gemini OAuth streaming error %d: %s",
                        resp.status,
                        error_text[:500],
                    )
                    yield {
                        "type": "error",
                        "message": f"API error {resp.status}: {error_text[:200]}",
                    }
                    return

                # Parse SSE stream: lines prefixed with "data: ", empty line = yield
                _LOGGER.info("Gemini streaming (SSE): starting to read chunks")
                chunk_count = 0
                buffered_lines: list[str] = []

                async for raw_line in resp.content:
                    if not raw_line:
                        continue

                    line = raw_line.decode("utf-8").rstrip("\r\n")

                    if line.startswith("data:"):
                        # SSE spec: "data: payload" or "data:payload"
                        payload = line[5:].lstrip(" ") if len(line) > 5 else ""
                        buffered_lines.append(payload.strip())
                    elif line == "" and buffered_lines:
                        # Empty line = end of SSE event → parse buffered data
                        joined = "\n".join(buffered_lines)
                        buffered_lines = []

                        try:
                            chunk = json.loads(joined)
                        except json.JSONDecodeError:
                            _LOGGER.debug(
                                "Gemini SSE: malformed JSON chunk (%d bytes)",
                                len(joined),
                            )
                            continue

                        if not isinstance(chunk, dict):
                            continue

                        chunk_count += 1
                        if chunk_count == 1:
                            _LOGGER.info("Gemini SSE: received first chunk")
                        elif chunk_count % 10 == 0:
                            _LOGGER.debug("Gemini SSE: chunk %d", chunk_count)

                        for result in process_gemini_chunk(chunk):
                            yield result
                    # Ignore comment lines, id: fields, other SSE metadata

                # Flush remaining buffered data (stream ended without trailing blank line)
                if buffered_lines:
                    joined = "\n".join(buffered_lines)
                    try:
                        chunk = json.loads(joined)
                        if isinstance(chunk, dict):
                            chunk_count += 1
                            for result in process_gemini_chunk(
                                chunk, label="[SSE flush]"
                            ):
                                yield result
                    except json.JSONDecodeError:
                        _LOGGER.debug(
                            "Gemini SSE flush: unparseable data (%d bytes)", len(joined)
                        )

                _LOGGER.info(
                    "Gemini SSE streaming: completed, received %d chunks total",
                    chunk_count,
                )

        except aiohttp.ClientError as e:
            error_str = str(e)
            _LOGGER.warning("Gemini streaming connection error: %s", error_str)

            is_retryable = (
                "rate" in error_str.lower()
                or is_retryable_status_in_text(error_str)
            )

            if is_retryable:
                raise RateLimitError(
                    f"Connection error (retryable): {error_str}"
                ) from e
            else:
                yield {"type": "error", "message": f"Connection error: {error_str}"}

        except RateLimitError:
            raise
        except Exception as e:
            _LOGGER.error("Gemini streaming error: %s", e)
            yield {"type": "error", "message": str(e)}
