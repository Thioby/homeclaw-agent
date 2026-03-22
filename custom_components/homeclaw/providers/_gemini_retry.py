"""Retry helpers and error classification for Gemini OAuth API calls.

Implements structured Google API error parsing following gemini-cli patterns:
- RetryInfo.retryDelay → server-suggested wait time
- ErrorInfo.reason → RATE_LIMIT_EXCEEDED vs QUOTA_EXHAUSTED
- QuotaFailure → PerDay (terminal) vs PerMinute (retryable)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from ._gemini_constants import RateLimitError, RetryableQuotaError, TerminalQuotaError

_LOGGER = logging.getLogger(__name__)


def _parse_duration_seconds(duration: str) -> float | None:
    """Parse a Google API duration string (e.g. '34.07s', '500ms') to seconds.

    Args:
        duration: Duration string from RetryInfo.retryDelay.

    Returns:
        Duration in seconds, or None if unparseable.
    """
    if duration.endswith("ms"):
        val = duration[:-2]
        try:
            return float(val) / 1000.0
        except ValueError:
            return None
    if duration.endswith("s"):
        val = duration[:-1]
        try:
            return float(val)
        except ValueError:
            return None
    return None


def _parse_json_text(value: str) -> Any | None:
    """Parse a JSON-like string, including wrapper text around an object.

    Args:
        value: Raw string that may contain JSON.

    Returns:
        Parsed value if JSON was found, otherwise None.
    """
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass

    normalized = value.replace("\u00A0", "").replace("\n", " ")
    try:
        return json.loads(normalized)
    except (json.JSONDecodeError, TypeError):
        pass
    first_brace = normalized.find("{")
    last_brace = normalized.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(normalized[first_brace : last_brace + 1])
        except (json.JSONDecodeError, TypeError):
            return None

    return None


def _unwrap_google_error(raw_error: Any) -> dict[str, Any] | None:
    """Unwrap nested Google API error containers.

    Handles plain error bodies, arrays, wrapper objects, and stringified JSON
    stored inside the ``message`` field.

    Args:
        raw_error: Raw parsed or string response body.

    Returns:
        Normalized Google API error dict, or None if not extractable.
    """
    current = raw_error
    depth = 0

    while depth < 10:
        if isinstance(current, str):
            current = _parse_json_text(current)
            if current is None:
                return None
            depth += 1
            continue

        if isinstance(current, list):
            if not current:
                return None
            current = current[0]
            depth += 1
            continue

        if not isinstance(current, dict):
            return None

        if "error" in current:
            current = current["error"]
            depth += 1
            continue

        response = current.get("response")
        if isinstance(response, dict) and "data" in response:
            current = response["data"]
            depth += 1
            continue

        data = current.get("data")
        if isinstance(data, (dict, list, str)):
            current = data
            depth += 1
            continue

        message = current.get("message")
        if isinstance(message, (dict, list)):
            current = message
            depth += 1
            continue

        if isinstance(message, str):
            parsed_message = _parse_json_text(message)
            if parsed_message is not None:
                current = parsed_message
                depth += 1
                continue

        return current

    return current if isinstance(current, dict) else None


def _normalize_detail(detail: Any) -> dict[str, Any] | None:
    """Normalize a structured Google error detail object.

    Args:
        detail: Raw detail entry.

    Returns:
        Dict detail with normalized ``@type`` key, or None if invalid.
    """
    if isinstance(detail, str):
        detail = _parse_json_text(detail)

    if isinstance(detail, list):
        detail = detail[0] if detail else None

    if not isinstance(detail, dict):
        return None

    normalized = dict(detail)
    type_key = next((key for key in normalized if key.strip() == "@type"), None)
    if type_key:
        normalized["@type"] = normalized[type_key]
        if type_key != "@type":
            normalized.pop(type_key, None)

    return normalized if isinstance(normalized.get("@type"), str) else None


def _extract_message_and_details(
    error: dict[str, Any], fallback_text: str
) -> tuple[str, list[dict[str, Any]]]:
    """Extract a string message and normalized detail objects."""
    message = error.get("message", fallback_text[:200])
    if not isinstance(message, str):
        message = str(message)

    raw_details = error.get("details", [])
    if isinstance(raw_details, str):
        raw_details = _parse_json_text(raw_details) or []
    if not isinstance(raw_details, list):
        raw_details = []

    details: list[dict[str, Any]] = []
    for detail in raw_details:
        normalized = _normalize_detail(detail)
        if normalized:
            details.append(normalized)

    return message, details


def classify_google_error(
    status: int,
    response_text: str,
) -> RateLimitError | TerminalQuotaError | Exception:
    """Classify a Google API error response into retry/terminal categories.

    Parses structured error details from the JSON response body:
    - details[].@type == "google.rpc.RetryInfo" → extract retryDelay
    - details[].@type == "google.rpc.ErrorInfo" → RATE_LIMIT_EXCEEDED / QUOTA_EXHAUSTED
    - details[].@type == "google.rpc.QuotaFailure" → PerDay (terminal) / PerMinute (retryable)

    Args:
        status: HTTP status code.
        response_text: Raw response body text.

    Returns:
        Classified exception: RetryableQuotaError, TerminalQuotaError, or generic Exception.
    """
    body = _parse_json_text(response_text)
    error = _unwrap_google_error(body if body is not None else response_text)
    if not error:
        return _classify_from_text(status, response_text)

    parsed_status = error.get("code")
    effective_status = parsed_status if isinstance(parsed_status, int) else status
    message, details = _extract_message_and_details(error, response_text)

    # Extract structured detail objects (guard against malformed data)
    retry_info: dict[str, Any] | None = None
    error_info: dict[str, Any] | None = None
    quota_failure: dict[str, Any] | None = None

    for detail in details:
        dtype = detail.get("@type", "")
        if not isinstance(dtype, str):
            continue
        if "RetryInfo" in dtype:
            retry_info = detail
        elif "ErrorInfo" in dtype:
            error_info = detail
        elif "QuotaFailure" in dtype:
            quota_failure = detail

    # Parse server-suggested delay from RetryInfo
    delay_seconds: float | None = None
    if retry_info and retry_info.get("retryDelay"):
        delay_seconds = _parse_duration_seconds(retry_info["retryDelay"])

    # Check QuotaFailure for daily limits (terminal)
    if quota_failure:
        for violation in quota_failure.get("violations", []):
            quota_id = violation.get("quotaId", "") + violation.get("quotaMetric", "")
            if "PerDay" in quota_id or "Daily" in quota_id:
                return TerminalQuotaError(
                    f"Daily quota exhausted: {message}",
                    reason="QUOTA_EXHAUSTED_DAILY",
                )

    # Check ErrorInfo reason
    if error_info:
        reason = error_info.get("reason", "")
        text_delay = _extract_delay_from_text(message)

        if reason == "INSUFFICIENT_G1_CREDITS_BALANCE":
            return TerminalQuotaError(message, reason=reason)

        if reason == "QUOTA_EXHAUSTED":
            return TerminalQuotaError(
                f"Quota exhausted (non-retryable): {message}",
                reason=reason,
            )

        if reason == "RATE_LIMIT_EXCEEDED":
            effective_delay = delay_seconds or text_delay or 10.0
            return RetryableQuotaError(
                f"Rate limited: {message}",
                retry_delay_seconds=effective_delay,
            )

        if reason == "MODEL_CAPACITY_EXHAUSTED":
            # Transient capacity exhaustion — retryable.
            # The message typically contains "reset after Xs".
            effective_delay = delay_seconds or text_delay or 30.0
            return RetryableQuotaError(
                f"Model capacity exhausted: {message}",
                retry_delay_seconds=effective_delay,
            )

    # RetryInfo present without specific ErrorInfo → retryable
    if retry_info and delay_seconds:
        return RetryableQuotaError(
            f"Server requested retry after {delay_seconds:.1f}s: {message}",
            retry_delay_seconds=delay_seconds,
        )

    # Check QuotaFailure for per-minute limits (retryable with 60s delay)
    if quota_failure:
        for violation in quota_failure.get("violations", []):
            quota_id = violation.get("quotaId", "") + violation.get("quotaMetric", "")
            if "PerMinute" in quota_id:
                return RetryableQuotaError(
                    f"Per-minute quota exceeded: {message}",
                    retry_delay_seconds=60.0,
                )

    # Fallback for 429/499 without structured details
    if effective_status in (429, 499):
        return _classify_from_text(effective_status, message)

    # Generic 5xx
    if 500 <= effective_status < 600:
        return RetryableQuotaError(f"Server error {effective_status}: {message}")

    return Exception(f"Gemini OAuth API error {effective_status}: {message}")


def _extract_delay_from_text(error_text: str) -> float | None:
    """Extract retry delay from error message text using known patterns.

    Matches:
    - "retry in 5s" / "retry in 500ms" (standard Google pattern)
    - "reset after 24s" / "will reset after 24s" (MODEL_CAPACITY_EXHAUSTED pattern)

    Args:
        error_text: Raw error text to scan.

    Returns:
        Delay in seconds, or None if no pattern matched.
    """
    # Pattern 1: "retry in Xs" / "retry in 500ms"
    match = re.search(r"retry in (\d+(?:\.\d+)?)\s*(s|ms)", error_text, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        unit = match.group(2).lower()
        return val if unit == "s" else val / 1000.0

    # Pattern 2: "reset after 24s" / "will reset after 24s" / "reset after 500ms"
    match = re.search(
        r"reset after (\d+(?:\.\d+)?)\s*(s|ms)", error_text, re.IGNORECASE
    )
    if match:
        val = float(match.group(1))
        unit = match.group(2).lower()
        return val if unit == "s" else val / 1000.0

    return None


def _classify_from_text(
    status: int, error_text: str
) -> RetryableQuotaError | Exception:
    """Fallback: classify error from raw text using regex.

    Args:
        status: HTTP status code.
        error_text: Raw error text.

    Returns:
        RetryableQuotaError with optional parsed delay, or generic Exception.
    """
    delay = _extract_delay_from_text(error_text)

    if status in (429, 499):
        return RetryableQuotaError(
            f"Rate limited ({status}): {error_text[:200]}",
            retry_delay_seconds=delay,
        )

    return Exception(f"Gemini OAuth API error {status}: {error_text[:500]}")


def parse_retry_delay(error_str: str, current_delay: float) -> float:
    """Parse retry delay from error message or compute exponential backoff with jitter.

    If the error is a RetryableQuotaError with a server-suggested delay, uses that.
    Otherwise looks for "retry in 5s" / "reset after 24s" patterns.
    Falls back to exponential backoff with +/-30% jitter.

    Args:
        error_str: Error message that may contain retry delay hint.
        current_delay: Current backoff delay in seconds.

    Returns:
        Delay in seconds before next retry.
    """
    import random

    extracted = _extract_delay_from_text(error_str)
    if extracted is not None:
        return extracted

    # Exponential backoff with jitter (+-30%)
    jitter = current_delay * 0.3 * (random.random() * 2 - 1)
    return max(0, current_delay + jitter)


async def retry_on_rate_limit(
    func, max_retries: int = 3, initial_delay: float = 1.0, logger=None
):
    """Retry async function on 429 rate limit with exponential backoff.

    Args:
        func: Async callable that returns (status_code, data).
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds (doubles each retry).
        logger: Logger instance for logging retry attempts.

    Returns:
        Tuple of (status_code, data) from successful call.

    Raises:
        Last exception if all retries fail.
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            status, data = await func()

            if status == 429 and attempt < max_retries:
                if logger:
                    logger.warning(
                        "Rate limited (429), retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
                continue

            return status, data

        except Exception as e:
            last_error = e
            if attempt < max_retries:
                if logger:
                    logger.warning(
                        "Request failed, retrying in %.1fs (attempt %d/%d): %s",
                        delay,
                        attempt + 1,
                        max_retries,
                        e,
                    )
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise

    if last_error:
        raise last_error
