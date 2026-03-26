"""Dashboard Manager for Home Assistant Lovelace dashboards.

Extracted from the God Class to handle all dashboard-related operations.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

import yaml

from ..utils.yaml_writer import (
    CONFIG_WRITE_LOCK,
    atomic_write_file,
    backup_file,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Known Lovelace card types for validation
KNOWN_CARD_TYPES = {
    "alarm-panel",
    "area",
    "button",
    "calendar",
    "conditional",
    "entities",
    "entity",
    "entity-filter",
    "gauge",
    "glance",
    "graph",
    "grid",
    "history-graph",
    "horizontal-stack",
    "humidifier",
    "iframe",
    "light",
    "logbook",
    "map",
    "markdown",
    "media-control",
    "mushroom-alarm-control-panel-card",
    "mushroom-chips-card",
    "mushroom-climate-card",
    "mushroom-cover-card",
    "mushroom-entity-card",
    "mushroom-fan-card",
    "mushroom-light-card",
    "mushroom-lock-card",
    "mushroom-media-player-card",
    "mushroom-number-card",
    "mushroom-person-card",
    "mushroom-select-card",
    "mushroom-template-card",
    "mushroom-title-card",
    "mushroom-update-card",
    "mushroom-vacuum-card",
    "picture",
    "picture-elements",
    "picture-entity",
    "picture-glance",
    "plant-status",
    "sensor",
    "shopping-list",
    "statistics-graph",
    "thermostat",
    "tile",
    "todo-list",
    "vertical-stack",
    "weather-forecast",
}


class DashboardManager:
    """Manager for Home Assistant dashboard operations.

    Provides methods to query, create, update, and validate Lovelace dashboards.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the DashboardManager.

        Args:
            hass: Home Assistant instance.

        Raises:
            ValueError: If hass is None.
        """
        if hass is None:
            raise ValueError("hass is required")
        self.hass = hass

    async def get_dashboards(self) -> list[dict[str, Any]]:
        """Get list of all dashboards.

        Returns:
            List of dashboard info dictionaries with url_path, title, icon,
            show_in_sidebar, and require_admin fields.
        """
        try:
            _LOGGER.debug("Requesting all dashboards")

            from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

            # Get lovelace data
            lovelace_data = self.hass.data.get(LOVELACE_DOMAIN)
            if lovelace_data is None:
                return [{"error": "Lovelace not available"}]

            # Safety check for dashboards attribute
            if not hasattr(lovelace_data, "dashboards"):
                return [{"error": "Lovelace dashboards not available"}]

            dashboards = lovelace_data.dashboards
            yaml_configs = getattr(lovelace_data, "yaml_dashboards", {}) or {}

            dashboard_list = []

            for url_path, dashboard_obj in dashboards.items():
                yaml_config = yaml_configs.get(url_path, {}) or {}

                # Get title
                title = yaml_config.get("title")
                if not title:
                    title = (
                        "Overview" if url_path is None else (url_path or "Dashboard")
                    )

                # Get icon
                icon = yaml_config.get("icon")
                if not icon:
                    icon = "mdi:home" if url_path is None else "mdi:view-dashboard"

                # Get sidebar/admin settings
                show_in_sidebar = yaml_config.get("show_in_sidebar", True)
                require_admin = yaml_config.get("require_admin", False)

                dashboard_list.append(
                    {
                        "url_path": url_path,
                        "title": title,
                        "icon": icon,
                        "show_in_sidebar": show_in_sidebar,
                        "require_admin": require_admin,
                    }
                )

            _LOGGER.debug("Found %d dashboards", len(dashboard_list))
            return dashboard_list

        except Exception as e:
            _LOGGER.exception("Error getting dashboards: %s", str(e))
            return [{"error": f"Error getting dashboards: {str(e)}"}]

    async def get_dashboard_config(
        self, dashboard_id: str | None = None
    ) -> dict[str, Any]:
        """Get configuration of a specific dashboard.

        Args:
            dashboard_id: The dashboard URL path (None for default dashboard).

        Returns:
            Dashboard configuration dictionary or error dict if not found.
        """
        try:
            _LOGGER.debug(
                "Requesting dashboard config for: %s", dashboard_id or "default"
            )

            from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

            lovelace_data = self.hass.data.get(LOVELACE_DOMAIN)
            if lovelace_data is None:
                return {"error": "Lovelace not available"}

            if not hasattr(lovelace_data, "dashboards"):
                return {"error": "Lovelace dashboards not available"}

            dashboards = lovelace_data.dashboards
            dashboard_key = None if dashboard_id is None else dashboard_id

            if dashboard_key in dashboards:
                dashboard = dashboards[dashboard_key]
                config = await dashboard.async_get_info()
                return dict(config) if config else {"error": "No dashboard config"}
            else:
                if dashboard_id is None:
                    return {"error": "Default dashboard not found"}
                else:
                    return {"error": f"Dashboard '{dashboard_id}' not found"}

        except Exception as e:
            _LOGGER.exception("Error getting dashboard config: %s", str(e))
            return {"error": f"Error getting dashboard config: {str(e)}"}

    async def create_dashboard(
        self,
        config: dict[str, Any],
        dashboard_id: str | None = None,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Create a new dashboard.

        Args:
            config: Dashboard configuration with title, url_path, views, etc.
            dashboard_id: Optional explicit dashboard ID (uses url_path from config if not provided).
            dry_run: If True, validate and return a preview without writing any files.

        Returns:
            Result dictionary with success status or error.
        """
        try:
            _LOGGER.debug("Creating dashboard with config: %s", config)

            # Validate required fields
            if not config.get("title"):
                return {"error": "Dashboard title is required"}

            url_path = dashboard_id or config.get("url_path")
            if not url_path:
                return {"error": "Dashboard URL path is required"}

            # Sanitize the URL path
            url_path = url_path.lower().replace(" ", "-").replace("_", "-")

            # Prepare dashboard configuration
            dashboard_data = {
                "title": config["title"],
                "icon": config.get("icon", "mdi:view-dashboard"),
                "show_in_sidebar": config.get("show_in_sidebar", True),
                "require_admin": config.get("require_admin", False),
                "views": config.get("views", []),
            }

            # Check for duplicate — file on disk or registered in HA
            lovelace_config_file = self.hass.config.path(f"ui-lovelace-{url_path}.yaml")
            file_exists = await self.hass.async_add_executor_job(
                lambda: os.path.exists(lovelace_config_file)
            )
            if file_exists:
                return {"error": f"Dashboard '{url_path}' already exists"}

            # Also check HA's in-memory dashboard registry
            try:
                from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

                lovelace_data = self.hass.data.get(LOVELACE_DOMAIN)
                if lovelace_data and hasattr(lovelace_data, "dashboards"):
                    if url_path in lovelace_data.dashboards:
                        return {"error": f"Dashboard '{url_path}' already exists"}
            except Exception:
                pass  # If lovelace not available, skip this check

            if dry_run:
                validation = self.validate_dashboard_config(dashboard_data)
                preview_yaml = yaml.dump(
                    dashboard_data, default_flow_style=False, allow_unicode=True
                )
                return {
                    "dry_run": True,
                    "title": config["title"],
                    "url_path": url_path,
                    "preview": preview_yaml,
                    "validation": validation,
                }

            def write_dashboard_file():
                with open(lovelace_config_file, "w") as f:
                    yaml.dump(
                        dashboard_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                    )

            await self.hass.async_add_executor_job(write_dashboard_file)

            _LOGGER.info(
                "Successfully created dashboard file: %s", lovelace_config_file
            )

            # Update configuration.yaml
            try:
                config_updated = await self._update_configuration_yaml(url_path, config)

                if config_updated:
                    return {
                        "success": True,
                        "message": f"Dashboard '{config['title']}' created successfully. Restart required.",
                        "url_path": url_path,
                        "restart_required": True,
                    }
                else:
                    return {
                        "success": True,
                        "message": f"Dashboard file created. Manual configuration.yaml update may be needed.",
                        "url_path": url_path,
                        "restart_required": True,
                    }

            except Exception as config_error:
                _LOGGER.warning(
                    "Could not update configuration.yaml: %s", str(config_error)
                )
                return {
                    "success": True,
                    "message": f"Dashboard file created but configuration.yaml update failed.",
                    "url_path": url_path,
                    "restart_required": True,
                }

        except Exception as e:
            _LOGGER.exception("Error creating dashboard: %s", str(e))
            return {"error": f"Error creating dashboard: {str(e)}"}

    async def _update_configuration_yaml(
        self, url_path: str, config: dict[str, Any]
    ) -> bool:
        """Update configuration.yaml with new dashboard entry.

        Uses the shared CONFIG_WRITE_LOCK to prevent race conditions with
        integration_manager, creates a backup, and writes atomically.

        Args:
            url_path: The sanitized URL path for the dashboard.
            config: Dashboard configuration.

        Returns:
            True if update was successful, False otherwise.
        """
        config_file = self.hass.config.path("configuration.yaml")

        async with CONFIG_WRITE_LOCK:
            return await self.hass.async_add_executor_job(
                self._do_update_configuration_yaml, config_file, url_path, config
            )

    @staticmethod
    def _do_update_configuration_yaml(
        config_file: str, url_path: str, config: dict[str, Any]
    ) -> bool:
        """Synchronous configuration.yaml update (runs in executor).

        Args:
            config_file: Path to configuration.yaml.
            url_path: Dashboard URL path.
            config: Dashboard configuration dict.

        Returns:
            True if update succeeded, False otherwise.
        """
        try:
            backup_file(config_file)
        except Exception:
            _LOGGER.warning(
                "Failed to backup configuration.yaml before dashboard update"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""

        # Generate properly escaped YAML for the dashboard entry
        dashboard_entry = {
            url_path: {
                "mode": "yaml",
                "title": config.get("title", url_path),
                "icon": config.get("icon", "mdi:view-dashboard"),
                "show_in_sidebar": config.get("show_in_sidebar", True),
                "filename": f"ui-lovelace-{url_path}.yaml",
            }
        }

        entry_yaml = yaml.safe_dump(
            dashboard_entry,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).rstrip()
        # Indent to fit under "dashboards:"
        indented_entry = "\n".join(
            f"    {line}" if line.strip() else line for line in entry_yaml.split("\n")
        )

        lines = content.split("\n")

        # Check for actual lovelace: key (not in comments)
        has_lovelace = False
        has_dashboards = False
        lovelace_line_idx = -1
        dashboards_line_idx = -1

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.match(r"^lovelace:", line):
                has_lovelace = True
                lovelace_line_idx = idx
            if re.match(r"^\s+dashboards:", line):
                has_dashboards = True
                dashboards_line_idx = idx

        if not has_lovelace:
            # Append complete lovelace section
            lovelace_section = (
                "\n# Lovelace dashboards configuration\n"
                "lovelace:\n"
                "  dashboards:\n"
                f"{indented_entry}\n"
            )
            new_content = content.rstrip("\n") + "\n" + lovelace_section
        elif not has_dashboards:
            # Add dashboards: under existing lovelace:
            new_lines = list(lines)
            new_lines.insert(
                lovelace_line_idx + 1,
                f"  dashboards:\n{indented_entry}",
            )
            new_content = "\n".join(new_lines)
        else:
            # Add entry under existing dashboards:
            new_lines = list(lines)
            new_lines.insert(
                dashboards_line_idx + 1,
                indented_entry,
            )
            new_content = "\n".join(new_lines)

        try:
            atomic_write_file(config_file, new_content)
            return True
        except Exception as exc:
            _LOGGER.error("Failed to write configuration.yaml: %s", exc)
            return False

    async def _remove_from_configuration_yaml(self, url_path: str) -> bool:
        """Remove a dashboard entry from configuration.yaml.

        Args:
            url_path: The dashboard URL path to remove.

        Returns:
            True if the entry was found and removed, False otherwise.
        """
        config_file = self.hass.config.path("configuration.yaml")
        async with CONFIG_WRITE_LOCK:
            return await self.hass.async_add_executor_job(
                self._do_remove_from_configuration_yaml, config_file, url_path
            )

    @staticmethod
    def _do_remove_from_configuration_yaml(config_file: str, url_path: str) -> bool:
        """Synchronous configuration.yaml entry removal (runs in executor).

        Line-based scan: find the url_path: line under dashboards:,
        delete it and all following lines at deeper indentation.

        Args:
            config_file: Path to configuration.yaml.
            url_path: Dashboard URL path to remove.

        Returns:
            True if removed, False if not found.
        """
        try:
            backup_file(config_file)
        except Exception:
            _LOGGER.warning(
                "Failed to backup configuration.yaml before dashboard removal"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            return False

        lines = content.split("\n")
        in_lovelace = False
        in_dashboards = False
        entry_start = -1
        entry_indent = -1

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            if re.match(r"^lovelace:", line):
                in_lovelace = True
                continue
            if in_lovelace and re.match(r"^\s+dashboards:", line):
                in_dashboards = True
                continue
            if in_lovelace and not line.startswith(" "):
                in_lovelace = False
                in_dashboards = False
                continue
            if in_dashboards:
                match = re.match(rf"^(\s+){re.escape(url_path)}:", line)
                if match:
                    entry_start = idx
                    entry_indent = len(match.group(1))
                    break

        if entry_start == -1:
            return False

        entry_end = entry_start + 1
        while entry_end < len(lines):
            line = lines[entry_end]
            if not line.strip():
                entry_end += 1
                continue
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= entry_indent:
                break
            entry_end += 1

        new_lines = lines[:entry_start] + lines[entry_end:]
        new_content = "\n".join(new_lines)

        try:
            atomic_write_file(config_file, new_content)
            return True
        except Exception as exc:
            _LOGGER.error("Failed to write configuration.yaml: %s", exc)
            return False

    async def update_dashboard(
        self, dashboard_id: str, config: dict[str, Any], *, dry_run: bool = True
    ) -> dict[str, Any]:
        """Update an existing dashboard.

        Args:
            dashboard_id: The dashboard URL path to update.
            config: New dashboard configuration.
            dry_run: If True, return a preview of the changes without writing.

        Returns:
            Result dictionary with success status or error.
        """
        try:
            if not dashboard_id:
                return {
                    "error": "Cannot modify the default dashboard through this tool"
                }

            _LOGGER.debug("Updating dashboard %s with config: %s", dashboard_id, config)

            # Prepare updated dashboard configuration
            dashboard_data = {
                "title": config.get("title", "Updated Dashboard"),
                "icon": config.get("icon", "mdi:view-dashboard"),
                "show_in_sidebar": config.get("show_in_sidebar", True),
                "require_admin": config.get("require_admin", False),
                "views": config.get("views", []),
            }

            # Try updating the YAML file
            dashboard_file = self.hass.config.path(f"ui-lovelace-{dashboard_id}.yaml")

            def check_file_exists():
                return os.path.exists(dashboard_file)

            file_exists = await self.hass.async_add_executor_job(check_file_exists)

            if not file_exists:
                # Try alternate location
                alt_dashboard_file = self.hass.config.path(
                    f"dashboards/{dashboard_id}.yaml"
                )
                file_exists = await self.hass.async_add_executor_job(
                    lambda: os.path.exists(alt_dashboard_file)
                )
                if file_exists:
                    dashboard_file = alt_dashboard_file

            if not file_exists:
                return {"error": f"Dashboard file for '{dashboard_id}' not found"}

            if dry_run:

                def read_current():
                    with open(dashboard_file, "r") as f:
                        return yaml.safe_load(f) or {}

                current_config = await self.hass.async_add_executor_job(read_current)
                validation = self.validate_dashboard_config(dashboard_data)
                return {
                    "dry_run": True,
                    "dashboard_url": dashboard_id,
                    "current_config": yaml.dump(
                        current_config, default_flow_style=False, allow_unicode=True
                    ),
                    "new_config": yaml.dump(
                        dashboard_data, default_flow_style=False, allow_unicode=True
                    ),
                    "validation": validation,
                }

            def update_dashboard_file():
                with open(dashboard_file, "w") as f:
                    yaml.dump(
                        dashboard_data,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                    )

            await self.hass.async_add_executor_job(update_dashboard_file)

            _LOGGER.info("Successfully updated dashboard file: %s", dashboard_file)
            return {
                "success": True,
                "message": f"Dashboard '{dashboard_id}' updated successfully!",
            }

        except Exception as e:
            _LOGGER.exception("Error updating dashboard: %s", str(e))
            return {"error": f"Error updating dashboard: {str(e)}"}

    async def delete_dashboard(
        self, dashboard_id: str, *, dry_run: bool = True
    ) -> dict[str, Any]:
        """Delete an existing dashboard.

        Args:
            dashboard_id: The dashboard URL path to delete.
            dry_run: If True, return info about what would be deleted without making changes.

        Returns:
            Result dictionary with success status or error.
        """
        try:
            if not dashboard_id:
                return {"error": "Cannot delete the default dashboard"}

            _LOGGER.debug("Deleting dashboard %s (dry_run=%s)", dashboard_id, dry_run)

            dashboard_file = self.hass.config.path(f"ui-lovelace-{dashboard_id}.yaml")
            file_exists = await self.hass.async_add_executor_job(
                lambda: os.path.exists(dashboard_file)
            )

            if not file_exists:
                alt_dashboard_file = self.hass.config.path(
                    f"dashboards/{dashboard_id}.yaml"
                )
                alt_exists = await self.hass.async_add_executor_job(
                    lambda: os.path.exists(alt_dashboard_file)
                )
                if alt_exists:
                    dashboard_file = alt_dashboard_file
                    file_exists = True

            if not file_exists:
                return {"error": f"Dashboard '{dashboard_id}' not found"}

            def read_current():
                with open(dashboard_file, "r") as f:
                    return yaml.safe_load(f) or {}

            current_config = await self.hass.async_add_executor_job(read_current)

            if dry_run:
                return {
                    "dry_run": True,
                    "exists": True,
                    "dashboard_url": dashboard_id,
                    "file": dashboard_file,
                    "title": current_config.get("title", dashboard_id),
                    "preview": yaml.dump(
                        current_config, default_flow_style=False, allow_unicode=True
                    ),
                }

            await self.hass.async_add_executor_job(os.remove, dashboard_file)
            _LOGGER.info("Deleted dashboard file: %s", dashboard_file)

            config_removed = await self._remove_from_configuration_yaml(dashboard_id)
            if not config_removed:
                _LOGGER.warning(
                    "Dashboard file deleted but entry not found in configuration.yaml"
                )

            return {
                "success": True,
                "message": f"Dashboard '{dashboard_id}' deleted. Restart required.",
                "restart_required": True,
            }
        except Exception as e:
            _LOGGER.exception("Error deleting dashboard: %s", str(e))
            return {"error": f"Error deleting dashboard: {str(e)}"}

    def validate_dashboard_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate Lovelace dashboard configuration structure.

        Args:
            config: Dashboard configuration to validate.

        Returns:
            Validation result with 'valid' key and optional warnings/errors.
        """
        result = {"valid": True, "warnings": [], "errors": []}

        # Check for views
        views = config.get("views")
        if views is None:
            result["warnings"].append("No views defined, will use empty dashboard")
            config["views"] = []
        elif not isinstance(views, list):
            result["valid"] = False
            result["errors"].append("Views must be a list")
            return result
        elif len(views) == 0:
            result["warnings"].append("Dashboard has no views")

        # Validate each view
        for i, view in enumerate(config.get("views", [])):
            if not isinstance(view, dict):
                result["valid"] = False
                result["errors"].append(f"View {i} must be a dictionary")
                continue

            # Check cards in view
            cards = view.get("cards", [])
            if not isinstance(cards, list):
                result["warnings"].append(f"View {i}: cards should be a list")
                continue

            for j, card in enumerate(cards):
                if not isinstance(card, dict):
                    result["warnings"].append(
                        f"View {i}, Card {j}: must be a dictionary"
                    )
                    continue

                card_type = card.get("type")
                if card_type and card_type not in KNOWN_CARD_TYPES:
                    # Custom cards are allowed, just warn
                    if not card_type.startswith("custom:"):
                        result["warnings"].append(
                            f"View {i}, Card {j}: unknown card type '{card_type}'"
                        )

        return result
