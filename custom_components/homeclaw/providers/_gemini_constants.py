"""Gemini OAuth constants, exceptions, and model helpers."""

from __future__ import annotations

import functools
import json
import platform
import re
import sys
from pathlib import Path

from ..models import get_default_model, get_model_ids


def _read_manifest_version() -> str:
    """Read version from manifest.json (single source of truth)."""
    try:
        manifest = Path(__file__).parent.parent / "manifest.json"
        return json.loads(manifest.read_text())["version"]
    except Exception:  # noqa: BLE001
        return "0.0.0"


HOMECLAW_VERSION = _read_manifest_version()


class RateLimitError(Exception):
    """Exception raised when rate limit (429) is encountered."""

    pass


class TerminalQuotaError(Exception):
    """Exception for non-retryable quota errors (e.g. daily limit exhausted)."""

    def __init__(self, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason


class RetryableQuotaError(RateLimitError):
    """Exception for retryable quota errors with optional server-suggested delay."""

    def __init__(self, message: str, retry_delay_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_delay_seconds = retry_delay_seconds


# Cloud Code Assist API constants (from gemini-cli / opencode-gemini-auth)
GEMINI_CODE_ASSIST_ENDPOINT = "https://cloudcode-pa.googleapis.com/v1internal"


@functools.lru_cache(maxsize=16)
def _build_user_agent(model: str = "unknown") -> str:
    """Build User-Agent matching gemini-cli pattern.

    Format: HomeClaw/<version>/<model> (<platform>; <arch>)
    """
    return f"HomeClaw/{HOMECLAW_VERSION}/{model} ({sys.platform}; {platform.machine()})"


GEMINI_CODE_ASSIST_METADATA = {
    "ideType": "IDE_UNSPECIFIED",
    "platform": "PLATFORM_UNSPECIFIED",
    "pluginType": "GEMINI",
}

# Retry configuration (from gemini-cli)
MAX_ATTEMPTS = 10
INITIAL_DELAY_MS = 5000
MAX_DELAY_MS = 30000

# Transport-level retry (fast, for non-streaming only)
TRANSPORT_MAX_RETRIES = 3
TRANSPORT_RETRY_DELAY_S = 1.0

_RETRYABLE_RE = re.compile(r"\b(429|499|5\d{2})\b")


def is_retryable_status_in_text(error_str: str) -> bool:
    """Check if error text mentions a retryable HTTP status code."""
    return bool(_RETRYABLE_RE.search(error_str))


def _get_available_models() -> list[str]:
    """Get available model IDs for Gemini OAuth from central config."""
    models = get_model_ids("gemini_oauth")
    return models if models else ["gemini-3-pro-preview"]


# Module-level constant for backward compatibility (used by tests and validation)
GEMINI_AVAILABLE_MODELS = _get_available_models()

DEFAULT_MODEL = get_default_model("gemini_oauth") or "gemini-3-pro-preview"
