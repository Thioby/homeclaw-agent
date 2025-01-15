"""Centralized models configuration reader and writer.

Single source of truth for model lists and defaults, backed by models_config.json.
All modules should use these helpers instead of maintaining their own model lists.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Path to models configuration file
MODELS_CONFIG_PATH = Path(__file__).parent / "models_config.json"

_cache: dict[str, Any] | None = None


def load_models_config() -> dict[str, Any]:
    """Load models configuration from JSON file (cached).

    Returns:
        The full models config dictionary.
    """
    global _cache
    if _cache is not None:
        return _cache

    try:
        with open(MODELS_CONFIG_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
            return _cache
    except (FileNotFoundError, json.JSONDecodeError) as err:
        _LOGGER.warning("Could not load models config: %s", err)
        return {}


def invalidate_cache() -> None:
    """Invalidate the models config cache, forcing reload on next access."""
    global _cache
    _cache = None


def save_models_config(config: dict[str, Any]) -> None:
    """Write the full models config to disk and invalidate cache.

    Args:
        config: Complete models config dictionary to persist.

    Raises:
        OSError: If file cannot be written.
    """
    global _cache
    with open(MODELS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")
    _cache = config
    _LOGGER.info("Models config saved to %s", MODELS_CONFIG_PATH)


def get_models_for_provider(provider: str) -> list[dict[str, Any]]:
    """Get available models for a specific provider.

    Args:
        provider: Provider key (e.g. 'openai', 'gemini_oauth').

    Returns:
        List of model dicts with id, name, description, and optional default flag.
    """
    config = load_models_config()
    provider_config = config.get(provider, {})
    return provider_config.get("models", [])


def get_model_ids(provider: str) -> list[str]:
    """Get model IDs for a provider.

    Args:
        provider: Provider key.

    Returns:
        List of model ID strings.
    """
    return [m["id"] for m in get_models_for_provider(provider)]


def get_default_model(provider: str) -> str | None:
    """Get default model ID for a provider.

    Args:
        provider: Provider key.

    Returns:
        Default model ID, or first model ID, or None if no models defined.
    """
    models = get_models_for_provider(provider)
    for m in models:
        if m.get("default"):
            return m["id"]
    return models[0]["id"] if models else None


def get_provider_config(provider: str) -> dict[str, Any]:
    """Get full provider configuration including display_name, description, etc.

    Args:
        provider: Provider key.

    Returns:
        Provider config dict, or empty dict if not found.
    """
    config = load_models_config()
    return config.get(provider, {})


def get_display_name(provider: str) -> str:
    """Get display name for a provider.

    Args:
        provider: Provider key.

    Returns:
        Display name string, or the provider key as fallback.
    """
    config = load_models_config()
    provider_config = config.get(provider, {})
    return provider_config.get("display_name", provider)


def get_allow_custom_model(provider: str) -> bool:
    """Check if provider allows custom model names.

    Args:
        provider: Provider key.

    Returns:
        True if provider allows custom models.
    """
    config = load_models_config()
    provider_config = config.get(provider, {})
    return provider_config.get("allow_custom_model", False)


# Default context window fallback when not specified in config (tokens)
_DEFAULT_CONTEXT_WINDOW = 128_000


def get_context_window(provider: str, model_id: str | None = None) -> int:
    """Get the context window size (in tokens) for a provider/model pair.

    Looks up the ``context_window`` field from models_config.json.
    Falls back to 128 000 tokens if the field is missing or the model
    is not found.

    Args:
        provider: Provider key (e.g. 'openai', 'gemini_oauth').
        model_id: Optional model ID.  When ``None``, returns the context
            window of the default model for the provider.

    Returns:
        Context window in tokens.
    """
    models = get_models_for_provider(provider)

    if model_id:
        for m in models:
            if m["id"] == model_id:
                return m.get("context_window", _DEFAULT_CONTEXT_WINDOW)

    # Fallback: default model or first model
    for m in models:
        if m.get("default"):
            return m.get("context_window", _DEFAULT_CONTEXT_WINDOW)

    if models:
        return models[0].get("context_window", _DEFAULT_CONTEXT_WINDOW)

    return _DEFAULT_CONTEXT_WINDOW
