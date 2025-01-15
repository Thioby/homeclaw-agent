"""Retry helpers for Gemini OAuth API calls."""

from __future__ import annotations

import asyncio
import logging
import re

_LOGGER = logging.getLogger(__name__)


def parse_retry_delay(error_str: str, current_delay: float) -> float:
    """Parse retry delay from error message or compute exponential backoff with jitter.

    Looks for patterns like "retry in 5s" or "retry in 500ms" in the error string.
    Falls back to exponential backoff with +/-30% jitter.

    Args:
        error_str: Error message that may contain retry delay hint.
        current_delay: Current backoff delay in seconds.

    Returns:
        Delay in seconds before next retry.
    """
    import random

    retry_match = re.search(
        r"retry in (\d+(?:\.\d+)?)\s*(s|ms)",
        error_str,
        re.IGNORECASE,
    )
    if retry_match:
        delay_value = float(retry_match.group(1))
        delay_unit = retry_match.group(2).lower()
        return delay_value if delay_unit == "s" else delay_value / 1000

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
