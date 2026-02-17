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

import json
import logging
import shutil
from typing import Any

import yaml

from ..utils.yaml_writer import (
    CONFIG_WRITE_LOCK,
    SECRET_REDACTED,
    atomic_write_file,
    backup_file,
    dump_sections,
    is_include_tag,
    is_secret_tag,
    redact_secrets,
    remove_yaml_section,
    safe_load_yaml,
    serialize_for_output,
)
from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier

_LOGGER = logging.getLogger(__name__)

# Maximum integrations returned to avoid blowing up context window
_MAX_LIST_RESULTS = 100


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
    short_description = "List available HA integrations with config flow info"
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
    short_description = "Read current configuration.yaml content"
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
            parsed = safe_load_yaml(content)
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
            serialized = serialize_for_output(value)
            output = {
                "section": section,
                "config": serialized,
                "type": type(value).__name__,
            }
        else:
            # Return summary of all top-level keys
            summary: dict[str, str] = {}
            for key, val in parsed.items():
                if is_include_tag(val):
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
    short_description = "Create YAML-based HA integration configuration"
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

        async with CONFIG_WRITE_LOCK:
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
            existing = safe_load_yaml(raw_content) if raw_content.strip() else {}
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
            if is_include_tag(existing_val):
                conflicts.append(
                    {
                        "key": key,
                        "reason": f"uses '!include {existing_val.path}' — "
                        f"modify that file directly instead",
                    }
                )
                continue

            if not overwrite:
                serialized = serialize_for_output(existing_val)
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
        """Write file atomically (delegates to :func:`atomic_write_file`)."""
        atomic_write_file(path, content)

    @staticmethod
    def _backup_file(path: str) -> bool:
        """Create a backup of the file (delegates to :func:`backup_file`)."""
        return backup_file(path)

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

        Raises:
            ValueError: If a section to overwrite defines a YAML anchor
                that is referenced elsewhere (removal would break the file).
        """
        result = raw_content

        # Handle overwrite keys — remove existing sections from text
        for key in overwrite_keys:
            try:
                result = remove_yaml_section(result, key)
            except ValueError:
                _LOGGER.error(
                    "Cannot overwrite section '%s': it defines a YAML anchor "
                    "referenced elsewhere in configuration.yaml. "
                    "Remove the alias references first.",
                    key,
                )
                raise

        # Append all config keys (both new and overwritten) at end
        keys_to_append = new_keys + overwrite_keys
        sections_yaml = dump_sections(config, keys_to_append)

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
# Backward-compatible re-exports for existing test imports
# ---------------------------------------------------------------------------
_safe_load_yaml = safe_load_yaml
_is_include_tag = is_include_tag
_is_secret_tag = is_secret_tag
_redact_secrets = redact_secrets
_serialize_for_output = serialize_for_output
_dump_sections = dump_sections
_remove_yaml_section = remove_yaml_section
_SECRET_REDACTED = SECRET_REDACTED
