"""Dashboard Manager for Home Assistant Lovelace dashboards.

Extracted from the God Class to handle all dashboard-related operations.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

import yaml

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
                    title = "Overview" if url_path is None else (url_path or "Dashboard")

                # Get icon
                icon = yaml_config.get("icon")
                if not icon:
                    icon = "mdi:home" if url_path is None else "mdi:view-dashboard"

                # Get sidebar/admin settings
                show_in_sidebar = yaml_config.get("show_in_sidebar", True)
                require_admin = yaml_config.get("require_admin", False)

                dashboard_list.append({
                    "url_path": url_path,
                    "title": title,
                    "icon": icon,
                    "show_in_sidebar": show_in_sidebar,
                    "require_admin": require_admin,
                })

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
        self, config: dict[str, Any], dashboard_id: str | None = None
    ) -> dict[str, Any]:
        """Create a new dashboard.

        Args:
            config: Dashboard configuration with title, url_path, views, etc.
            dashboard_id: Optional explicit dashboard ID (uses url_path from config if not provided).

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

            # Create the dashboard YAML file
            lovelace_config_file = self.hass.config.path(
                f"ui-lovelace-{url_path}.yaml"
            )

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
                config_updated = await self._update_configuration_yaml(
                    url_path, config
                )

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

        Args:
            url_path: The sanitized URL path for the dashboard.
            config: Dashboard configuration.

        Returns:
            True if update was successful, False otherwise.
        """
        config_file = self.hass.config.path("configuration.yaml")

        def update_config():
            try:
                with open(config_file, "r") as f:
                    content = f.read()

                dashboard_yaml = f"""    {url_path}:
      mode: yaml
      title: {config["title"]}
      icon: {config.get("icon", "mdi:view-dashboard")}
      show_in_sidebar: {str(config.get("show_in_sidebar", True)).lower()}
      filename: ui-lovelace-{url_path}.yaml"""

                if "lovelace:" not in content:
                    # Add complete lovelace section at the end
                    lovelace_section = f"""
# Lovelace dashboards configuration
lovelace:
  dashboards:
{dashboard_yaml}
"""
                    with open(config_file, "a") as f:
                        f.write(lovelace_section)
                    return True

                # Find dashboards section and add entry
                lines = content.split("\n")
                new_lines = []
                dashboard_added = False

                for line in lines:
                    new_lines.append(line)
                    if "dashboards:" in line and not dashboard_added:
                        new_lines.append(dashboard_yaml)
                        dashboard_added = True

                if dashboard_added:
                    with open(config_file, "w") as f:
                        f.write("\n".join(new_lines))
                    return True

                return False

            except Exception as e:
                _LOGGER.error("Failed to update configuration.yaml: %s", str(e))
                return False

        return await self.hass.async_add_executor_job(update_config)

    async def update_dashboard(
        self, dashboard_id: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing dashboard.

        Args:
            dashboard_id: The dashboard URL path to update.
            config: New dashboard configuration.

        Returns:
            Result dictionary with success status or error.
        """
        try:
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
                    result["warnings"].append(f"View {i}, Card {j}: must be a dictionary")
                    continue

                card_type = card.get("type")
                if card_type and card_type not in KNOWN_CARD_TYPES:
                    # Custom cards are allowed, just warn
                    if not card_type.startswith("custom:"):
                        result["warnings"].append(
                            f"View {i}, Card {j}: unknown card type '{card_type}'"
                        )

        return result
