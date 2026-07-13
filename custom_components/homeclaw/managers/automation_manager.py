"""Automation Manager for Home Assistant automations.

Extracted from the God Class to handle all automation-related operations.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import TYPE_CHECKING, Any

import yaml

from ..utils.yaml_writer import (
    CONFIG_WRITE_LOCK,
    atomic_write_file,
    backup_file,
    is_include_tag,
    load_ha_yaml,
    safe_load_yaml,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

AUTOMATION_DOMAIN = "automation"
AUTOMATIONS_FILE = "automations.yaml"


def _read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


RECOGNIZED_ACTION_KEYS = frozenset(
    {
        "service",
        "action",
        "delay",
        "wait_template",
        "wait_for_trigger",
        "choose",
        "if",
        "repeat",
        "parallel",
        "sequence",
        "stop",
        "event",
        "scene",
        "device_id",
        "variables",
        "set_conversation_response",
    }
)


class AutomationManager:
    """Manager for Home Assistant automation operations.

    Provides methods to validate, create, list, and toggle automations.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the AutomationManager.

        Args:
            hass: Home Assistant instance.

        Raises:
            ValueError: If hass is None.
        """
        if hass is None:
            raise ValueError("hass is required")
        self.hass = hass

    def _state_to_dict(self, state) -> dict[str, Any]:
        """Convert a Home Assistant state object to a dictionary.

        Args:
            state: Home Assistant state object.

        Returns:
            Dictionary with entity_id, state, attributes, and last_changed.
        """
        return {
            "entity_id": state.entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": (
                state.last_changed.isoformat() if state.last_changed else None
            ),
        }

    def validate_automation(self, config: dict) -> dict:
        """Validate automation configuration.

        Accepts both the legacy singular keys (``trigger``/``action``) and the
        modern plural keys (``triggers``/``actions``) that current HA writes.
        Blueprint automations (``use_blueprint``) carry neither and are valid.

        Args:
            config: Automation configuration dictionary.

        Returns:
            Dict with 'valid' boolean and optional 'error' string.
        """
        if not isinstance(config, dict):
            return {"valid": False, "error": "Automation config must be a dictionary"}

        if "use_blueprint" in config:
            blueprint = config["use_blueprint"]
            if isinstance(blueprint, dict) and blueprint.get("path"):
                return {"valid": True}
            return {
                "valid": False,
                "error": "'use_blueprint' must be a dictionary with a 'path'",
            }

        errors = self._section_errors(config, "trigger", "triggers")
        errors += self._section_errors(config, "action", "actions")
        if not errors:
            errors += self._action_entry_errors(config)

        if errors:
            return {"valid": False, "error": "; ".join(errors)}

        return {"valid": True}

    def _section_errors(self, config: dict, singular: str, plural: str) -> list[str]:
        if singular in config and plural in config:
            return [f"Use either '{singular}' or '{plural}', not both"]
        value = config.get(singular, config.get(plural))
        if value is None or (isinstance(value, (list, dict)) and not value):
            return [f"At least one {singular} is required"]
        if not isinstance(value, (list, dict)):
            return [f"{singular.capitalize()} must be a list or dictionary"]
        return []

    def _action_entry_errors(self, config: dict) -> list[str]:
        actions = config.get("action", config.get("actions"))
        entries = actions if isinstance(actions, list) else [actions]
        errors: list[str] = []
        for i, entry in enumerate(entries):
            if isinstance(entry, dict) and not RECOGNIZED_ACTION_KEYS & entry.keys():
                errors.append(f"Action {i} must have 'service' or 'action' field")
        return errors

    async def create_automation(self, config: dict, *, dry_run: bool = False) -> dict:
        """Create a new automation by appending it to automations.yaml.

        Existing file content is preserved byte-for-byte; the new entry is
        appended, the merged result is re-parsed before writing, the write is
        atomic and a ``.backup`` copy is made first.

        Args:
            config: Automation configuration dictionary.
            dry_run: If True, validate and return a preview without writing.

        Returns:
            Dict with 'success' boolean, 'id', and 'preview' when dry_run.
        """
        validation = self.validate_automation(config)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

        if not self.hass.services.has_service(AUTOMATION_DOMAIN, "reload"):
            return {"success": False, "error": "The automation integration is not loaded"}

        layout_error = await self._automations_include_error()
        if layout_error:
            return {"success": False, "error": layout_error}

        automation_id = str(config.get("id") or uuid.uuid4().hex)
        item = {"id": automation_id, **{k: v for k, v in config.items() if k != "id"}}
        new_item_yaml = yaml.dump(
            [item], sort_keys=False, allow_unicode=True, default_flow_style=False
        )
        if dry_run:
            _raw, existing, error = await self._load_existing(self._automations_path())
            if error:
                return {"success": False, "error": error}
            duplicate = self._duplicate_id_error(existing, automation_id)
            if duplicate:
                return {"success": False, "error": duplicate}
            return {
                "success": True,
                "dry_run": True,
                "id": automation_id,
                "preview": new_item_yaml,
            }

        async with CONFIG_WRITE_LOCK:
            path = self._automations_path()
            raw, existing, error = await self._load_existing(path)
            if error:
                return {"success": False, "error": error}
            duplicate = self._duplicate_id_error(existing, automation_id)
            if duplicate:
                return {"success": False, "error": duplicate}

            new_content = self._merged_content(raw, existing, new_item_yaml)
            error = self._roundtrip_error(new_content, len(existing))
            if error:
                return {"success": False, "error": error}

            await self.hass.async_add_executor_job(backup_file, path)
            await self.hass.async_add_executor_job(atomic_write_file, path, new_content)

        _LOGGER.info("Created automation %s in %s", automation_id, path)

        try:
            await self.hass.services.async_call(AUTOMATION_DOMAIN, "reload", {})
        except Exception as e:
            _LOGGER.exception("Automation %s saved but reload failed", automation_id)
            return {
                "success": True,
                "id": automation_id,
                "warning": f"Automation saved but reload failed: {e}",
            }

        return {"success": True, "id": automation_id}

    def _automations_path(self) -> str:
        return os.path.realpath(self.hass.config.path(AUTOMATIONS_FILE))

    async def _automations_include_error(self) -> str | None:
        config_path = self.hass.config.path("configuration.yaml")
        raw = await self.hass.async_add_executor_job(_read_text, config_path)
        if raw is None:
            return "configuration.yaml not found; cannot verify automation storage layout"
        try:
            parsed = safe_load_yaml(raw)
        except yaml.YAMLError:
            return "configuration.yaml could not be parsed; refusing to create automations"
        automations_path = self._automations_path()
        for key, value in parsed.items():
            if key != "automation" and not str(key).startswith("automation "):
                continue
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if (
                    is_include_tag(candidate)
                    and candidate.tag == "!include"
                    and os.path.realpath(self.hass.config.path(candidate.path))
                    == automations_path
                ):
                    return None
        return (
            "configuration.yaml does not map 'automation' to "
            f"'!include {AUTOMATIONS_FILE}'; creating automations is not "
            "supported for this configuration layout"
        )

    async def _load_existing(self, path: str) -> tuple[str | None, list, str | None]:
        raw = await self.hass.async_add_executor_job(_read_text, path)
        if raw is None:
            return None, [], None
        try:
            parsed = load_ha_yaml(raw)
        except yaml.YAMLError as e:
            return raw, [], f"{AUTOMATIONS_FILE} is not valid YAML, refusing to modify it: {e}"
        if parsed is None:
            parsed = []
        if not isinstance(parsed, list):
            return raw, [], f"{AUTOMATIONS_FILE} does not contain a list, refusing to modify it"
        return raw, parsed, None

    def _duplicate_id_error(self, existing: list, automation_id: str) -> str | None:
        for entry in existing:
            if not isinstance(entry, dict) or entry.get("id") is None:
                continue
            if str(entry["id"]) == automation_id:
                return f"Automation id '{automation_id}' already exists"
        return None

    def _merged_content(
        self, raw: str | None, existing: list, new_item_yaml: str
    ) -> str:
        if raw is None or not raw.strip():
            return new_item_yaml
        if existing:
            base = raw if raw.endswith("\n") else raw + "\n"
            return base + new_item_yaml
        comment_lines = [
            line
            for line in raw.splitlines()
            if not line.strip() or line.lstrip().startswith("#")
        ]
        preserved = "\n".join(comment_lines).rstrip("\n")
        if preserved.strip():
            return preserved + "\n" + new_item_yaml
        return new_item_yaml

    def _roundtrip_error(self, content: str, previous_count: int) -> str | None:
        try:
            parsed = load_ha_yaml(content)
        except yaml.YAMLError as e:
            return f"Refusing to write: merged {AUTOMATIONS_FILE} would be invalid YAML: {e}"
        if not isinstance(parsed, list) or len(parsed) != previous_count + 1:
            return f"Refusing to write: merged {AUTOMATIONS_FILE} failed verification"
        return None

    def get_automations(self) -> list[dict[str, Any]]:
        """Get all automation entities.

        Returns:
            List of automation entity state dictionaries.
        """
        _LOGGER.debug("Getting all automations")
        prefix = f"{AUTOMATION_DOMAIN}."
        states = [
            state
            for state in self.hass.states.async_all()
            if state.entity_id.startswith(prefix)
        ]

        _LOGGER.debug("Found %d automations", len(states))
        return [self._state_to_dict(state) for state in states]

    async def toggle_automation(self, entity_id: str, enable: bool) -> dict:
        """Turn an automation on or off.

        Args:
            entity_id: The automation entity ID.
            enable: True to turn on, False to turn off.

        Returns:
            Dict with 'success' boolean and 'entity_id'.
        """
        service = "turn_on" if enable else "turn_off"
        _LOGGER.debug("Toggling automation %s to %s", entity_id, service)

        try:
            await self.hass.services.async_call(
                AUTOMATION_DOMAIN,
                service,
                {"entity_id": entity_id},
            )

            return {"success": True, "entity_id": entity_id}
        except Exception as e:
            _LOGGER.exception("Error toggling automation %s: %s", entity_id, str(e))
            return {"success": False, "entity_id": entity_id, "error": str(e)}
