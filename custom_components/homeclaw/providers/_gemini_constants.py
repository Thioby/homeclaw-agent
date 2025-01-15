"""Gemini OAuth constants, exceptions, and model helpers."""

from __future__ import annotations

from ..models import get_default_model, get_model_ids


class RateLimitError(Exception):
    """Exception raised when rate limit (429) is encountered."""

    pass


# Cloud Code Assist API constants (from gemini-cli / opencode-gemini-auth)
GEMINI_CODE_ASSIST_ENDPOINT = "https://cloudcode-pa.googleapis.com/v1internal"

GEMINI_CODE_ASSIST_HEADERS = {
    "User-Agent": "google-api-nodejs-client/9.15.1",
    "X-Goog-Api-Client": "gl-node/22.17.0",
    "Client-Metadata": "ideType=IDE_UNSPECIFIED,platform=PLATFORM_UNSPECIFIED,pluginType=GEMINI",
}

GEMINI_CODE_ASSIST_METADATA = {
    "ideType": "IDE_UNSPECIFIED",
    "platform": "PLATFORM_UNSPECIFIED",
    "pluginType": "GEMINI",
}

# Retry configuration (from gemini-cli)
MAX_ATTEMPTS = 10
INITIAL_DELAY_MS = 5000
MAX_DELAY_MS = 30000


def _get_available_models() -> list[str]:
    """Get available model IDs for Gemini OAuth from central config."""
    models = get_model_ids("gemini_oauth")
    return models if models else ["gemini-3-pro-preview"]


# Module-level constant for backward compatibility (used by tests and validation)
GEMINI_AVAILABLE_MODELS = _get_available_models()

DEFAULT_MODEL = get_default_model("gemini_oauth") or "gemini-3-pro-preview"
