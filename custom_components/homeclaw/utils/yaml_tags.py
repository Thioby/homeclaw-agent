"""YAML tag classes and serialization helpers for Homeclaw.

Provides placeholder classes for Home Assistant custom YAML tags
(``!include``, ``!secret``) and utilities for redacting/serializing
parsed YAML structures.
"""

from __future__ import annotations

from typing import Any

SECRET_REDACTED = "***SECRET***"


class IncludeTag:
    """Placeholder for ``!include`` / ``!include_dir_*`` YAML tags.

    Preserves the exact tag variant so round-trip serialization is lossless.
    """

    def __init__(self, path: str, tag: str = "!include") -> None:
        self.path = path
        self.tag = tag

    def __repr__(self) -> str:
        return f"{self.tag} {self.path}"


class SecretTag:
    """Placeholder for ``!secret`` YAML tags."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"!secret {self.name}"


def is_include_tag(value: Any) -> bool:
    """Return ``True`` if *value* is an :class:`IncludeTag` instance."""
    return isinstance(value, IncludeTag)


def is_secret_tag(value: Any) -> bool:
    """Return ``True`` if *value* is a :class:`SecretTag` instance."""
    return isinstance(value, SecretTag)


def redact_secrets(obj: Any) -> Any:
    """Recursively replace ``!secret`` tags with a redacted placeholder."""
    if is_secret_tag(obj):
        return SECRET_REDACTED
    if is_include_tag(obj):
        return repr(obj)
    if isinstance(obj, dict):
        return {k: redact_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_secrets(item) for item in obj]
    return obj


def serialize_for_output(obj: Any) -> Any:
    """Convert parsed YAML to a JSON-serializable structure."""
    if is_secret_tag(obj):
        return SECRET_REDACTED
    if is_include_tag(obj):
        return repr(obj)
    if isinstance(obj, dict):
        return {k: serialize_for_output(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_output(item) for item in obj]
    return obj
