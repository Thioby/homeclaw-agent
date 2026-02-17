"""YAML file I/O utilities for Homeclaw.

Provides safe YAML loading (with HA tag support), atomic file writing,
backup creation, and section dumping.

The module-level ``CONFIG_WRITE_LOCK`` is a singleton ``asyncio.Lock``
shared by every importer -- all callers that modify ``configuration.yaml``
**must** acquire it before read-modify-write sequences.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import stat
import tempfile
from typing import Any

import yaml

from .yaml_tags import IncludeTag, SecretTag

_LOGGER = logging.getLogger(__name__)

CONFIG_WRITE_LOCK: asyncio.Lock = asyncio.Lock()
"""Acquire before any read-modify-write on ``configuration.yaml``."""


def safe_load_yaml(content: str) -> dict[str, Any]:
    """Load YAML with custom constructors for Home Assistant tags.

    Handles ``!include``, ``!include_dir_*``, ``!secret``, ``!env_var``,
    and ``!input``.  Tags are preserved as :class:`IncludeTag` /
    :class:`SecretTag` instances instead of raising errors.

    Args:
        content: Raw YAML string.

    Returns:
        Parsed dict (top-level keys to values).

    Raises:
        yaml.YAMLError: If the content is not a valid top-level mapping.
    """

    class _SafeLoaderWithHA(yaml.SafeLoader):
        pass

    def _include_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> IncludeTag:
        return IncludeTag(loader.construct_scalar(node), tag=node.tag)

    def _secret_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> SecretTag:
        return SecretTag(loader.construct_scalar(node))

    def _generic_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> Any:
        """Preserve value for non-secret, non-include HA tags."""
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return str(node.value)

    for tag in (
        "!include",
        "!include_dir_list",
        "!include_dir_merge_list",
        "!include_dir_named",
        "!include_dir_merge_named",
    ):
        _SafeLoaderWithHA.add_constructor(tag, _include_constructor)

    _SafeLoaderWithHA.add_constructor("!secret", _secret_constructor)
    _SafeLoaderWithHA.add_constructor("!env_var", _generic_constructor)
    _SafeLoaderWithHA.add_constructor("!input", _generic_constructor)

    result = yaml.load(content, Loader=_SafeLoaderWithHA)
    if result is None:
        return {}
    if not isinstance(result, dict):
        raise yaml.YAMLError(f"Expected top-level mapping, got {type(result).__name__}")
    return result


def atomic_write_file(path: str, content: str) -> None:
    """Write *content* to *path* atomically via temp file + fsync + replace.

    Preserves original file permissions when the target already exists.
    """
    dir_name = os.path.dirname(path) or "."

    orig_mode = None
    try:
        orig_mode = os.stat(path).st_mode
    except FileNotFoundError:
        pass

    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    fd_closed = False
    try:
        if orig_mode is not None:
            os.fchmod(fd, stat.S_IMODE(orig_mode))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd_closed = True
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        if not fd_closed:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def backup_file(path: str) -> bool:
    """Create a ``.backup`` copy of *path*.

    Returns:
        ``True`` if a backup was created, ``False`` if source does not exist.
    """
    if os.path.exists(path):
        shutil.copy2(path, path + ".backup")
        return True
    return False


def dump_sections(config: dict[str, Any], keys: list[str]) -> str:
    """Dump selected *keys* from *config* to a YAML string.

    Each key is emitted as a separate top-level section.
    """
    if not keys:
        return ""

    parts: list[str] = []
    for key in keys:
        if key not in config:
            continue
        section = {key: config[key]}
        dumped = yaml.safe_dump(
            section,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        parts.append(dumped.rstrip())

    return "\n\n".join(parts) + "\n" if parts else ""
