"""Shared YAML utilities -- convenience re-exports.

Import from here for backward compatibility. Individual modules:
- ``yaml_tags``: Tag classes and serialization
- ``yaml_io``: File I/O, locking, loading
- ``yaml_sections``: Section manipulation
"""

from __future__ import annotations

from .yaml_io import (
    CONFIG_WRITE_LOCK,
    atomic_write_file,
    backup_file,
    dump_sections,
    safe_load_yaml,
)
from .yaml_sections import remove_yaml_section
from .yaml_tags import (
    SECRET_REDACTED,
    IncludeTag,
    SecretTag,
    is_include_tag,
    is_secret_tag,
    redact_secrets,
    serialize_for_output,
)

__all__ = [
    "CONFIG_WRITE_LOCK",
    "SECRET_REDACTED",
    "IncludeTag",
    "SecretTag",
    "atomic_write_file",
    "backup_file",
    "dump_sections",
    "is_include_tag",
    "is_secret_tag",
    "redact_secrets",
    "remove_yaml_section",
    "safe_load_yaml",
    "serialize_for_output",
]
