"""Integration management tools for Homeclaw.

Provides tools for listing available HA integrations, reading the current
configuration.yaml content, and creating YAML-based integrations by merging
JSON config objects into configuration.yaml.

The AI agent uses these tools to:
1. Check if an integration supports config flow (UI) or requires YAML setup.
2. Read existing configuration before making changes.
3. Write new YAML-based configuration with smart merge and backup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import stat
import tempfile
from typing import Any

import yaml

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)

# Maximum integrations returned to avoid blowing up context window
_MAX_LIST_RESULTS = 100

# Lock to prevent concurrent read-modify-write on configuration.yaml
_CONFIG_WRITE_LOCK = asyncio.Lock()

# Sentinel for !include / !secret tags that should not be parsed
_INCLUDE_TAG = "!include"
_SECRET_TAG = "!secret"
_SECRET_REDACTED = "***SECRET***"


def _safe_load_yaml(content: str) -> dict[str, Any]:
    """Load YAML content with custom constructors for HA tags.

    Handles !include, !include_dir_list, !include_dir_merge_list,
    !include_dir_named, !include_dir_merge_named, !secret, !env_var.
    These are preserved as tagged strings instead of raising errors.

    Args:
        content: Raw YAML string.

    Returns:
        Parsed dict (top-level keys -> values).
    """

    class _IncludeTag:
        """Placeholder for !include tags."""

        def __init__(self, path: str):
            self.path = path

        def __repr__(self) -> str:
            return f"!include {self.path}"

    class _SecretTag:
        """Placeholder for !secret tags."""

        def __init__(self, name: str):
            self.name = name

        def __repr__(self) -> str:
            return f"!secret {self.name}"

    class _SafeLoaderWithHA(yaml.SafeLoader):
        pass

    def _include_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> _IncludeTag:
        return _IncludeTag(loader.construct_scalar(node))

    def _secret_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> _SecretTag:
        return _SecretTag(loader.construct_scalar(node))

    def _generic_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> Any:
        """Preserve value for non-secret, non-include HA tags (!env_var, !input)."""
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return str(node.value)

    # Register HA-specific tags
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


def _is_include_tag(value: Any) -> bool:
    """Check if a value is an !include placeholder."""
    return hasattr(value, "path") and type(value).__name__ == "_IncludeTag"


def _is_secret_tag(value: Any) -> bool:
    """Check if a value is a !secret placeholder."""
    return hasattr(value, "name") and type(value).__name__ == "_SecretTag"


def _redact_secrets(obj: Any) -> Any:
    """Recursively replace !secret tags with redacted placeholder."""
    if _is_secret_tag(obj):
        return _SECRET_REDACTED
    if _is_include_tag(obj):
        return f"!include {obj.path}"
    if isinstance(obj, dict):
        return {k: _redact_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_secrets(item) for item in obj]
    return obj


def _serialize_for_output(obj: Any) -> Any:
    """Convert parsed YAML to JSON-serializable format."""
    if _is_secret_tag(obj):
        return _SECRET_REDACTED
    if _is_include_tag(obj):
        return f"!include {obj.path}"
    if isinstance(obj, dict):
        return {k: _serialize_for_output(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_output(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Tool 1: list_available_integrations
# ---------------------------------------------------------------------------


@ToolRegistry.register
class ListAvailableIntegrations(Tool):
    """List available integrations with config_flow flag."""

    id = "list_available_integrations"
    description = (
        "List available Home Assistant integrations. Returns domain, name, "
        "and config_flow flag. If config_flow=true the integration must be "
        "set up via UI (generate a link for the user). If config_flow=false "
        "it requires YAML configuration (use create_yaml_integration)."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="filter",
            type="string",
            description="Filter by domain or name (case-insensitive substring match)",
            required=False,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """List integrations from HA's integration registry."""
        filter_str = kwargs.get("filter", "")

        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        try:
            from homeassistant.loader import async_get_integration_descriptions

            descriptions = await async_get_integration_descriptions(self.hass)
        except Exception as exc:
            _LOGGER.error("Failed to load integration descriptions: %s", exc)
            return ToolResult(
                output=f"Failed to load integrations: {exc}",
                error=str(exc),
                success=False,
            )

        results: list[dict[str, Any]] = []

        # Process core integrations
        core_data = descriptions.get("core", {})
        for int_type in ("integration", "helper"):
            section = core_data.get(int_type, {})
            for domain, meta in section.items():
                if not isinstance(meta, dict):
                    continue
                entry = {
                    "domain": domain,
                    "name": meta.get("name", domain),
                    "config_flow": meta.get("config_flow", False),
                    "integration_type": meta.get("integration_type", "hub"),
                }
                results.append(entry)

        # Process custom integrations
        custom_data = descriptions.get("custom", {})
        for int_type in ("integration", "helper"):
            section = custom_data.get(int_type, {})
            for domain, meta in section.items():
                if not isinstance(meta, dict):
                    continue
                entry = {
                    "domain": domain,
                    "name": meta.get("name", domain),
                    "config_flow": meta.get("config_flow", False),
                    "integration_type": meta.get("integration_type", "hub"),
                    "custom": True,
                }
                results.append(entry)

        # Apply filter
        if filter_str:
            needle = filter_str.lower()
            results = [
                r
                for r in results
                if needle in r["domain"].lower() or needle in r["name"].lower()
            ]

        # Sort by domain for deterministic output
        results.sort(key=lambda r: r["domain"])

        total = len(results)
        truncated = total > _MAX_LIST_RESULTS
        if truncated:
            results = results[:_MAX_LIST_RESULTS]

        output = {
            "integrations": results,
            "count": len(results),
            "total": total,
            "truncated": truncated,
        }

        return ToolResult(
            output=json.dumps(output),
            metadata=output,
        )


# ---------------------------------------------------------------------------
# Tool 2: read_yaml_config
# ---------------------------------------------------------------------------


@ToolRegistry.register
class ReadYamlConfig(Tool):
    """Read current configuration.yaml content."""

    id = "read_yaml_config"
    description = (
        "Read configuration.yaml content. Optionally read a specific section "
        "(top-level key). Secrets are redacted. Use before create_yaml_integration "
        "to check existing config and merge correctly."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="section",
            type="string",
            description=(
                "Top-level key to read (e.g. 'notify', 'sensor', 'input_boolean'). "
                "Omit to list all top-level keys with their types."
            ),
            required=False,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Read and return configuration.yaml content."""
        section = kwargs.get("section")

        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        config_path = self.hass.config.path("configuration.yaml")

        try:
            content = await self.hass.async_add_executor_job(
                self._read_file, config_path
            )
        except FileNotFoundError:
            return ToolResult(
                output="configuration.yaml not found",
                error="file_not_found",
                success=False,
            )
        except Exception as exc:
            _LOGGER.error("Failed to read configuration.yaml: %s", exc)
            return ToolResult(
                output=f"Failed to read configuration.yaml: {exc}",
                error=str(exc),
                success=False,
            )

        try:
            parsed = _safe_load_yaml(content)
        except yaml.YAMLError as exc:
            _LOGGER.error("Failed to parse configuration.yaml: %s", exc)
            return ToolResult(
                output=f"Failed to parse YAML: {exc}",
                error=str(exc),
                success=False,
            )

        if section:
            if section not in parsed:
                return ToolResult(
                    output=json.dumps(
                        {
                            "error": f"Section '{section}' not found",
                            "available_sections": list(parsed.keys()),
                        }
                    ),
                    success=False,
                )

            value = parsed[section]
            serialized = _serialize_for_output(value)
            output = {
                "section": section,
                "config": serialized,
                "type": type(value).__name__,
            }
        else:
            # Return summary of all top-level keys
            summary: dict[str, str] = {}
            for key, val in parsed.items():
                if _is_include_tag(val):
                    summary[key] = f"!include {val.path}"
                elif isinstance(val, list):
                    summary[key] = f"list ({len(val)} items)"
                elif isinstance(val, dict):
                    summary[key] = f"dict ({len(val)} keys)"
                elif val is None:
                    summary[key] = "empty"
                else:
                    summary[key] = type(val).__name__
            output = {"sections": summary, "count": len(summary)}

        return ToolResult(
            output=json.dumps(output, default=str),
            metadata=output,
        )

    @staticmethod
    def _read_file(path: str) -> str:
        """Read file content synchronously (runs in executor)."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


# ---------------------------------------------------------------------------
# Tool 3: create_yaml_integration
# ---------------------------------------------------------------------------


@ToolRegistry.register
class CreateYamlIntegration(Tool):
    """Create or update a YAML-based integration in configuration.yaml."""

    id = "create_yaml_integration"
    description = (
        "Add YAML-based integration to configuration.yaml. Pass config as a "
        "JSON object with top-level domain keys — it is converted to YAML and "
        "appended. Use only for integrations without config_flow. "
        'Example: {"notify": [{"platform": "smtp", "server": "smtp.gmail.com"}]}'
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="config",
            type="object",
            description=(
                "Configuration as JSON object. Top-level keys are HA domain names. "
                "Converted directly to YAML and merged into configuration.yaml."
            ),
            required=True,
        ),
        ToolParameter(
            name="overwrite_existing",
            type="boolean",
            description=(
                "If a top-level key already exists, overwrite it (after backup). "
                "Default false — returns error if key exists."
            ),
            required=False,
            default=False,
        ),
        ToolParameter(
            name="validate_before_save",
            type="boolean",
            description="Validate config with HA before saving. Default true.",
            required=False,
            default=True,
        ),
        ToolParameter(
            name="auto_restart",
            type="boolean",
            description="Restart HA after saving. YAML changes require restart.",
            required=False,
            default=False,
        ),
    ]

    async def execute(self, config: dict[str, Any], **kwargs: Any) -> ToolResult:
        """Write config to configuration.yaml with smart merge."""
        overwrite = kwargs.get("overwrite_existing", False)
        validate = kwargs.get("validate_before_save", True)
        auto_restart = kwargs.get("auto_restart", False)

        if not self.hass:
            return ToolResult(
                output="Home Assistant not available",
                error="hass_not_available",
                success=False,
            )

        if not config or not isinstance(config, dict):
            return ToolResult(
                output="config must be a non-empty JSON object",
                error="invalid_config",
                success=False,
            )

        async with _CONFIG_WRITE_LOCK:
            return await self._execute_locked(config, overwrite, validate, auto_restart)

    async def _execute_locked(
        self,
        config: dict[str, Any],
        overwrite: bool,
        validate: bool,
        auto_restart: bool,
    ) -> ToolResult:
        """Execute write operation under lock."""
        config_path = self.hass.config.path("configuration.yaml")

        # Step 1: Read existing file
        try:
            raw_content = await self.hass.async_add_executor_job(
                self._read_file, config_path
            )
        except FileNotFoundError:
            raw_content = ""
        except Exception as exc:
            _LOGGER.error("Failed to read configuration.yaml: %s", exc)
            return ToolResult(
                output=f"Failed to read file: {exc}",
                error=str(exc),
                success=False,
            )

        # Step 2: Parse existing YAML to check for key conflicts
        try:
            existing = _safe_load_yaml(raw_content) if raw_content.strip() else {}
        except yaml.YAMLError as exc:
            _LOGGER.error("Failed to parse existing YAML: %s", exc)
            return ToolResult(
                output=f"Existing configuration.yaml has YAML errors: {exc}",
                error=str(exc),
                success=False,
            )

        # Step 3: Check for conflicts
        conflicts: list[dict[str, Any]] = []
        new_keys: list[str] = []
        overwrite_keys: list[str] = []

        for key in config:
            if key not in existing:
                new_keys.append(key)
                continue

            existing_val = existing[key]

            # !include → always error, cannot merge with included files
            if _is_include_tag(existing_val):
                conflicts.append(
                    {
                        "key": key,
                        "reason": f"uses '!include {existing_val.path}' — "
                        f"modify that file directly instead",
                    }
                )
                continue

            if not overwrite:
                serialized = _serialize_for_output(existing_val)
                conflicts.append(
                    {
                        "key": key,
                        "reason": "already exists (set overwrite_existing=true to replace)",
                        "current_value": serialized,
                    }
                )
            else:
                overwrite_keys.append(key)

        if conflicts:
            return ToolResult(
                output=json.dumps(
                    {
                        "success": False,
                        "conflicts": conflicts,
                        "message": "Some keys already exist in configuration.yaml",
                    },
                    default=str,
                ),
                success=False,
            )

        # Step 4: Backup
        backup_created = False
        try:
            backup_created = await self.hass.async_add_executor_job(
                self._backup_file, config_path
            )
        except Exception as exc:
            _LOGGER.warning("Failed to create backup: %s", exc)
            # Continue anyway — backup is best-effort

        # Step 5: Build new content
        try:
            new_content = await self.hass.async_add_executor_job(
                self._build_new_content,
                raw_content,
                config,
                new_keys,
                overwrite_keys,
            )
        except Exception as exc:
            _LOGGER.error("Failed to build new configuration: %s", exc)
            return ToolResult(
                output=f"Failed to build configuration: {exc}",
                error=str(exc),
                success=False,
            )

        # Step 6: Write file (atomic via temp + os.replace)
        try:
            await self.hass.async_add_executor_job(
                self._write_file, config_path, new_content
            )
        except Exception as exc:
            _LOGGER.error("Failed to write configuration.yaml: %s", exc)
            return ToolResult(
                output=f"Failed to write file: {exc}",
                error=str(exc),
                success=False,
            )

        # Step 7: Validate (optional) — rollback on failure
        validation_result = None
        if validate:
            validation_result = await self._validate_config()
            if validation_result != "valid":
                if backup_created:
                    _LOGGER.warning(
                        "Validation failed, rolling back configuration.yaml from backup"
                    )
                    rolled_back = await self._rollback_from_backup(config_path)
                    return ToolResult(
                        output=json.dumps(
                            {
                                "success": False,
                                "message": "Validation failed — config rolled back from backup",
                                "validation": validation_result,
                                "rolled_back": rolled_back,
                            }
                        ),
                        success=False,
                    )
                else:
                    _LOGGER.error(
                        "Validation failed and no backup available for rollback"
                    )
                    return ToolResult(
                        output=json.dumps(
                            {
                                "success": False,
                                "message": "Validation failed — no backup available for rollback, "
                                "config may be invalid",
                                "validation": validation_result,
                                "rolled_back": False,
                            }
                        ),
                        success=False,
                    )

        # Step 8: Restart (optional)
        restart_done = False
        if auto_restart and (not validate or validation_result == "valid"):
            restart_done = await self._restart_ha()

        result = {
            "success": True,
            "message": "Configuration updated",
            "keys_added": new_keys,
            "keys_overwritten": overwrite_keys,
            "restart_required": True,
            "restart_done": restart_done,
            "backup_created": backup_created,
        }
        if validation_result:
            result["validation"] = validation_result

        return ToolResult(
            output=json.dumps(result),
            metadata=result,
        )

    @staticmethod
    def _read_file(path: str) -> str:
        """Read file synchronously."""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _write_file(path: str, content: str) -> None:
        """Write file atomically via temp file + fsync + os.replace.

        Preserves original file permissions when the target already exists.
        """
        dir_name = os.path.dirname(path) or "."

        # Capture original permissions before replacing
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
                fd_closed = True  # os.fdopen now owns fd
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except BaseException:
            # Close fd if os.fdopen never took ownership
            if not fd_closed:
                try:
                    os.close(fd)
                except OSError:
                    pass
            # Clean up temp file on any error
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _backup_file(path: str) -> bool:
        """Create a backup of the file.

        Returns:
            True if a backup was actually created, False if source file
            does not exist (no-op).
        """
        backup_path = path + ".backup"
        if os.path.exists(path):
            shutil.copy2(path, backup_path)
            return True
        return False

    @staticmethod
    def _build_new_content(
        raw_content: str,
        config: dict[str, Any],
        new_keys: list[str],
        overwrite_keys: list[str],
    ) -> str:
        """Build new file content with appended/replaced sections.

        For new keys: append YAML at end of file.
        For overwrite keys: replace the existing section in-place.
        """
        result = raw_content

        # Handle overwrite keys — remove existing sections from text
        for key in overwrite_keys:
            result = _remove_yaml_section(result, key)

        # Append all config keys (both new and overwritten) at end
        keys_to_append = new_keys + overwrite_keys
        sections_yaml = _dump_sections(config, keys_to_append)

        if sections_yaml:
            # Ensure file ends with newline before appending
            if result and not result.endswith("\n"):
                result += "\n"
            if result and not result.endswith("\n\n"):
                result += "\n"
            result += sections_yaml

        return result

    async def _validate_config(self) -> str:
        """Run HA config validation."""
        try:
            await self.hass.services.async_call(
                "homeassistant", "check_config", blocking=True
            )
            return "valid"
        except Exception as exc:
            _LOGGER.warning("Config validation failed: %s", exc)
            return f"validation_error: {exc}"

    async def _restart_ha(self) -> bool:
        """Restart Home Assistant."""
        try:
            await self.hass.services.async_call(
                "homeassistant", "restart", blocking=False
            )
            return True
        except Exception as exc:
            _LOGGER.error("Failed to restart HA: %s", exc)
            return False

    async def _rollback_from_backup(self, config_path: str) -> bool:
        """Restore configuration.yaml from backup after failed validation.

        Returns:
            True if rollback succeeded, False otherwise.
        """
        backup_path = config_path + ".backup"
        try:
            await self.hass.async_add_executor_job(
                shutil.copy2, backup_path, config_path
            )
            _LOGGER.info("Rolled back configuration.yaml from backup")
            return True
        except Exception as exc:
            _LOGGER.error("Failed to rollback from backup: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Helper functions for YAML text manipulation
# ---------------------------------------------------------------------------


def _dump_sections(config: dict[str, Any], keys: list[str]) -> str:
    """Dump selected keys from config dict to YAML string.

    Each key is dumped as a separate top-level section.
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


def _next_content_is_indented(lines: list[str], start: int) -> bool:
    """Check if the next non-blank, non-comment line is indented.

    Used during section removal to decide whether a column-0 comment
    belongs to the section being removed (next content is indented) or
    to the following section (next content is a top-level key).

    Args:
        lines: All lines of the file.
        start: Index to start scanning from.

    Returns:
        True if the next meaningful line is indented (part of current section).
    """
    for j in range(start, len(lines)):
        s = lines[j].strip()
        if not s:
            continue  # skip blank lines
        if s.startswith("#") and not lines[j].startswith((" ", "\t")):
            continue  # skip more column-0 comments — keep looking
        # Found a non-blank, non-column-0-comment line
        return lines[j].startswith((" ", "\t"))
    # Reached EOF — no more content, comment is trailing
    return False


def _remove_yaml_section(content: str, key: str) -> str:
    """Remove a top-level YAML section from raw text.

    Finds the line matching exactly 'key:' (with optional trailing content)
    and removes all lines until the next top-level key (a non-indented,
    non-comment line containing ':') or end of file.  Column-0 comments
    inside the section are removed only when the next non-blank content
    is indented (belongs to the same section).  Comments followed by a
    new top-level key are preserved.

    Uses regex boundary to avoid prefix collisions (e.g. 'notify' vs
    'notify_group').

    Args:
        content: Raw YAML text.
        key: Top-level key to remove.

    Returns:
        Content with the section removed.
    """
    # Match exactly "key:" at start of line (key followed by colon,
    # then space/newline/EOF — NOT "key_suffix:")
    key_pattern = re.compile(rf"^{re.escape(key)}:(\s|$)")

    lines = content.split("\n")
    result: list[str] = []
    skip = False

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if stripped and not line.startswith((" ", "\t")):
            if stripped.startswith("#"):
                # Column-0 comment during skip: decide via lookahead.
                # If the next non-blank, non-comment line is indented
                # (belongs to the current section), skip the comment too.
                # Otherwise the comment belongs to the next section — end skip.
                if skip:
                    if _next_content_is_indented(lines, i + 1):
                        # Comment is inside the section being removed
                        continue
                    # Next content is a new top-level key (or EOF) — end skip
                    skip = False
            elif key_pattern.match(stripped):
                skip = True
                continue
            else:
                skip = False

        if not skip:
            result.append(line)

    # Clean up extra blank lines left behind
    text = "\n".join(result)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text
