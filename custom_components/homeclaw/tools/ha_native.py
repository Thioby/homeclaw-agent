"""Native Home Assistant tools for Homeclaw.

These tools wrap standard Home Assistant functionality to make it accessible
to the AI agent via native function calling.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers — eliminate duplication across tool classes
# ---------------------------------------------------------------------------


def _get_registries(hass: Any) -> tuple[Any, Any, dict[str, str]]:
    """Fetch entity, device registries and build area_id->name mapping.

    Returns:
        Tuple of (entity_registry, device_registry, area_names dict).
    """
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    area_reg = ar.async_get(hass)

    area_names: dict[str, str] = {}
    if area_reg:
        area_names = {a.id: a.name for a in area_reg.areas.values()}

    return entity_reg, device_reg, area_names


def _resolve_entity_area(entity: Any, device_registry: Any) -> str | None:
    """Resolve area_id for an entity registry entry, falling back to device's area.

    Args:
        entity: Entity registry entry.
        device_registry: HA device registry instance.

    Returns:
        area_id string or None.
    """
    area_id = entity.area_id
    if not area_id and entity.device_id and device_registry:
        device = device_registry.async_get(entity.device_id)
        if device:
            area_id = device.area_id
    return area_id


def _lightweight_entity(state: Any, area: str | None = None) -> dict[str, Any]:
    """Build a lightweight entity dict for LLM consumption.

    Returns only the fields an LLM needs to understand what an entity is.
    Use get_entity_state for full attributes when details are needed.

    Args:
        state: Home Assistant state object.
        area: Resolved area name (optional).

    Returns:
        Dict with entity_id, state, friendly_name, device_class, unit, and area.
    """
    attrs = state.attributes
    result: dict[str, Any] = {
        "entity_id": state.entity_id,
        "state": state.state,
        "friendly_name": attrs.get("friendly_name"),
    }
    dc = attrs.get("device_class")
    if dc:
        result["device_class"] = dc
    unit = attrs.get("unit_of_measurement")
    if unit:
        result["unit"] = unit
    if area:
        result["area"] = area
    return result


# Default pagination limits
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@ToolRegistry.register
class GetEntityState(Tool):
    id = "get_entity_state"
    description = "Get the state and attributes of a specific entity."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="entity_id",
            type="string",
            description="The entity ID (e.g. light.living_room)",
            required=True,
        )
    ]

    async def execute(self, entity_id: str, **kwargs) -> ToolResult:
        if not entity_id:
            return ToolResult(
                output="Entity ID is required", error="Missing entity_id", success=False
            )

        state = self.hass.states.get(entity_id)
        if not state:
            return ToolResult(
                output=f"Entity {entity_id} not found",
                error=f"Entity {entity_id} not found",
                success=False,
            )

        # Basic state info
        result = {
            "entity_id": state.entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": (
                state.last_changed.isoformat() if state.last_changed else None
            ),
            "last_updated": (
                state.last_updated.isoformat() if state.last_updated else None
            ),
        }

        # Format as JSON string for output
        return ToolResult(output=json.dumps(result, default=str), metadata=result)


@ToolRegistry.register
class GetEntitiesByDomain(Tool):
    id = "get_entities_by_domain"
    description = (
        "Get entities for a domain (e.g., light, switch, sensor). "
        "Returns lightweight info — use get_entity_state for full details."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="domain",
            type="string",
            description="The domain to filter by (e.g. 'light', 'sensor')",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(
        self, domain: str, limit: int = 50, offset: int = 0, **kwargs
    ) -> ToolResult:
        if not domain:
            return ToolResult(
                output="Domain is required", error="Missing domain", success=False
            )

        states = [
            state
            for state in self.hass.states.async_all()
            if state.entity_id.startswith(f"{domain}.")
        ]

        total = len(states)
        page = states[offset : offset + min(limit, _MAX_LIMIT)]
        results = [_lightweight_entity(s) for s in page]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "offset": offset},
        )


@ToolRegistry.register
class GetEntityRegistrySummary(Tool):
    id = "get_entity_registry_summary"
    description = "Get a summary of all entities in the system, counted by domain, area, and device_class."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = []  # No parameters

    async def execute(self, **kwargs) -> ToolResult:
        entity_registry, device_registry, area_names = _get_registries(self.hass)
        if not entity_registry:
            return ToolResult(output="{}", metadata={})

        by_domain: dict[str, int] = {}
        by_area: dict[str, int] = {}
        by_device_class: dict[str, int] = {}
        total = 0

        for entry in entity_registry.entities.values():
            if entry.disabled:
                continue

            total += 1
            domain = entry.entity_id.split(".")[0]
            by_domain[domain] = by_domain.get(domain, 0) + 1

            area_id = _resolve_entity_area(entry, device_registry)
            if area_id:
                area_name = area_names.get(area_id, area_id)
                by_area[area_name] = by_area.get(area_name, 0) + 1
            else:
                by_area["unassigned"] = by_area.get("unassigned", 0) + 1

            state = self.hass.states.get(entry.entity_id)
            if state:
                dc = state.attributes.get("device_class")
                if dc:
                    by_device_class[dc] = by_device_class.get(dc, 0) + 1

        summary = {
            "total_entities": total,
            "by_domain": dict(
                sorted(by_domain.items(), key=lambda x: x[1], reverse=True)
            ),
            "by_area": dict(sorted(by_area.items(), key=lambda x: x[1], reverse=True)),
            "by_device_class": dict(
                sorted(by_device_class.items(), key=lambda x: x[1], reverse=True)
            ),
        }

        return ToolResult(output=json.dumps(summary, default=str), metadata=summary)


@ToolRegistry.register
class GetEntityRegistry(Tool):
    id = "get_entity_registry"
    description = "Get list of entities filtered by domain, area, or device_class."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="domain", type="string", description="Filter by domain", required=False
        ),
        ToolParameter(
            name="area_id",
            type="string",
            description="Filter by area ID",
            required=False,
        ),
        ToolParameter(
            name="device_class",
            type="string",
            description="Filter by device class",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset",
            required=False,
            default=0,
        ),
    ]

    async def execute(
        self,
        domain: Optional[str] = None,
        area_id: Optional[str] = None,
        device_class: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        **kwargs,
    ) -> ToolResult:
        entity_registry, device_registry, area_names = _get_registries(self.hass)

        results = []
        for entry in entity_registry.entities.values():
            if entry.disabled:
                continue
            if domain and not entry.entity_id.startswith(f"{domain}."):
                continue

            entity_area = _resolve_entity_area(entry, device_registry)
            if area_id and entity_area != area_id:
                continue

            state = self.hass.states.get(entry.entity_id)
            if device_class:
                if not state or state.attributes.get("device_class") != device_class:
                    continue

            results.append(
                {
                    "entity_id": entry.entity_id,
                    "state": state.state if state else "unknown",
                    "area": (
                        area_names.get(entity_area, entity_area)
                        if entity_area
                        else None
                    ),
                    "device_class": (
                        state.attributes.get("device_class") if state else None
                    ),
                    "friendly_name": (
                        state.attributes.get("friendly_name")
                        if state
                        else entry.original_name
                    ),
                }
            )

        total = len(results)
        results = results[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "offset": offset},
        )


@ToolRegistry.register
class CallService(Tool):
    id = "call_service"
    description = "Call a Home Assistant service to control devices."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="domain",
            type="string",
            description="Service domain (e.g., light)",
            required=True,
        ),
        ToolParameter(
            name="service",
            type="string",
            description="Service name (e.g., turn_on)",
            required=True,
        ),
        ToolParameter(
            name="target",
            type="dict",
            description="Target entities (e.g., {'entity_id': 'light.kitchen'})",
            required=False,
        ),
        ToolParameter(
            name="service_data",
            type="dict",
            description="Service data (e.g., {'brightness': 255})",
            required=False,
        ),
    ]

    async def execute(
        self,
        domain: str,
        service: str,
        target: Optional[Dict] = None,
        service_data: Optional[Dict] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute a Home Assistant service call."""
        if not self.hass:
            return ToolResult(
                output="Home Assistant instance not available", success=False
            )

        try:
            # Prepare service call data
            call_data: Dict[str, Any] = {}

            # Add target entity_id if provided
            if target:
                call_data.update(target)

            # Add additional service data if provided
            if service_data:
                call_data.update(service_data)

            _LOGGER.debug(
                "Calling service %s.%s with data: %s", domain, service, call_data
            )

            await self.hass.services.async_call(
                domain,
                service,
                call_data,
                blocking=True,  # Wait for service to complete
            )

            entity_id = target.get("entity_id", "unknown") if target else "unknown"
            return ToolResult(
                output=f"Successfully called {domain}.{service} on {entity_id}",
                success=True,
                metadata={"domain": domain, "service": service, "target": target},
            )

        except Exception as e:
            error_msg = f"Error calling service {domain}.{service}: {e}"
            _LOGGER.error(error_msg)
            return ToolResult(output=error_msg, success=False, error=str(e))


@ToolRegistry.register
class GetHistory(Tool):
    id = "get_history"
    description = (
        "Get historical state changes for an entity over a specified time period. "
        "Returns state and timestamp only — use get_entity_state for current attributes."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="entity_id",
            type="string",
            description="The entity ID to get history for (e.g. sensor.temperature)",
            required=True,
        ),
        ToolParameter(
            name="hours",
            type="integer",
            description="Number of hours of history to retrieve (default: 24)",
            required=False,
            default=24,
        ),
        ToolParameter(
            name="max_entries",
            type="integer",
            description="Maximum number of state changes to return (default: 50, max 200)",
            required=False,
            default=50,
        ),
    ]

    async def execute(
        self, entity_id: str, hours: int = 24, max_entries: int = 50, **kwargs
    ) -> ToolResult:
        """Get historical state changes for an entity."""
        if not entity_id:
            return ToolResult(
                output="Entity ID is required", error="Missing entity_id", success=False
            )

        try:
            from datetime import datetime, timedelta

            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.history import get_significant_states
            from homeassistant.util import dt as dt_util

            # Use timezone-aware datetimes
            end_time = dt_util.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Get recorder instance and use its executor for database access
            recorder_instance = get_instance(self.hass)

            history_data = await recorder_instance.async_add_executor_job(
                get_significant_states,
                self.hass,
                start_time,
                end_time,
                [entity_id],
            )

            results = []
            for entity_id_key, states in history_data.items():
                for state in states:
                    results.append(
                        {
                            "state": state.state,
                            "timestamp": (
                                state.last_changed.isoformat()
                                if state.last_changed
                                else None
                            ),
                        }
                    )

            total = len(results)
            capped = min(max_entries, _MAX_LIMIT)
            results = results[-capped:]  # Keep most recent entries

            _LOGGER.debug(
                "Retrieved %d of %d historical states for %s",
                len(results),
                total,
                entity_id,
            )
            return ToolResult(
                output=json.dumps(results, default=str),
                metadata={
                    "entity_id": entity_id,
                    "total": total,
                    "returned": len(results),
                    "hours": hours,
                },
            )

        except Exception as e:
            _LOGGER.error("Error getting history for %s: %s", entity_id, e)
            return ToolResult(
                output=f"Error getting history: {str(e)}", error=str(e), success=False
            )


@ToolRegistry.register
class GetEntitiesByDeviceClass(Tool):
    id = "get_entities_by_device_class"
    description = (
        "Get entities with a specific device_class (e.g., temperature, humidity, motion). "
        "Returns lightweight info — use get_entity_state for full details."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="device_class",
            type="string",
            description="The device class to filter by (e.g., 'temperature', 'humidity', 'motion')",
            required=True,
        ),
        ToolParameter(
            name="domain",
            type="string",
            description="Optional domain to restrict search (e.g., 'sensor', 'binary_sensor')",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(
        self,
        device_class: str,
        domain: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        **kwargs,
    ) -> ToolResult:
        if not device_class:
            return ToolResult(
                output="Device class is required",
                error="Missing device_class",
                success=False,
            )

        matching = []
        for state in self.hass.states.async_all():
            if domain and not state.entity_id.startswith(f"{domain}."):
                continue
            if state.attributes.get("device_class") == device_class:
                matching.append(state)

        total = len(matching)
        page = matching[offset : offset + min(limit, _MAX_LIMIT)]
        results = [_lightweight_entity(s) for s in page]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={
                "total": total,
                "returned": len(results),
                "device_class": device_class,
            },
        )


@ToolRegistry.register
class GetEntitiesByArea(Tool):
    id = "get_entities_by_area"
    description = (
        "Get entities for a specific area. "
        "Returns lightweight info — use get_entity_state for full details."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="area_id",
            type="string",
            description="The area ID to filter by",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(
        self, area_id: str, limit: int = 50, offset: int = 0, **kwargs
    ) -> ToolResult:
        if not area_id:
            return ToolResult(
                output="Area ID is required", error="Missing area_id", success=False
            )

        entity_registry, device_registry, area_names = _get_registries(self.hass)

        matching = []
        for entity in entity_registry.entities.values():
            if entity.disabled:
                continue
            if _resolve_entity_area(entity, device_registry) != area_id:
                continue
            state = self.hass.states.get(entity.entity_id)
            if state:
                area_name = area_names.get(area_id, area_id)
                matching.append(_lightweight_entity(state, area=area_name))

        total = len(matching)
        results = matching[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "area_id": area_id},
        )


@ToolRegistry.register
class GetEntities(Tool):
    id = "get_entities"
    description = (
        "Get entities by area(s) — supports single area or multiple areas. "
        "Returns lightweight info — use get_entity_state for full details."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="area_id",
            type="string",
            description="Single area ID to filter by",
            required=False,
        ),
        ToolParameter(
            name="area_ids",
            type="array",
            description="List of area IDs to filter by",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(
        self,
        area_id: Optional[str] = None,
        area_ids: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        **kwargs,
    ) -> ToolResult:
        target_areas = list(area_ids) if area_ids else [area_id] if area_id else []
        if not target_areas:
            return ToolResult(
                output="Provide area_id or area_ids parameter",
                error="Missing area",
                success=False,
            )

        entity_registry, device_registry, area_names = _get_registries(self.hass)

        matching = []
        for entity in entity_registry.entities.values():
            if entity.disabled:
                continue
            entity_area = _resolve_entity_area(entity, device_registry)
            if entity_area not in target_areas:
                continue
            state = self.hass.states.get(entity.entity_id)
            if state:
                area_name = (
                    area_names.get(entity_area, entity_area) if entity_area else None
                )
                matching.append(_lightweight_entity(state, area=area_name))

        total = len(matching)
        results = matching[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "areas": target_areas},
        )


@ToolRegistry.register
class GetClimateRelatedEntities(Tool):
    id = "get_climate_related_entities"
    description = (
        "Get climate-related entities including thermostats, temperature sensors, "
        "and humidity sensors. Returns lightweight info."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(self, limit: int = 50, offset: int = 0, **kwargs) -> ToolResult:
        matching = []
        for state in self.hass.states.async_all():
            domain = state.entity_id.split(".")[0]
            device_class = state.attributes.get("device_class")

            is_climate = domain == "climate"
            is_temp = device_class == "temperature"
            is_humidity = device_class == "humidity"

            if is_climate or is_temp or is_humidity:
                matching.append(
                    {
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "device_class": device_class,
                        "friendly_name": state.attributes.get("friendly_name"),
                        "unit": state.attributes.get("unit_of_measurement"),
                    }
                )

        total = len(matching)
        results = matching[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results)},
        )


@ToolRegistry.register
class GetStatistics(Tool):
    id = "get_statistics"
    description = (
        "Get statistics (mean, min, max, sum) for an entity from the recorder."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="entity_id",
            type="string",
            description="The entity ID to get statistics for",
            required=True,
        ),
    ]

    async def execute(self, entity_id: str, **kwargs) -> ToolResult:
        if not entity_id:
            return ToolResult(
                output="Entity ID is required", error="Missing entity_id", success=False
            )

        try:
            import homeassistant.components.recorder.statistics as stats_module
            from homeassistant.components.recorder import get_instance

            recorder_instance = get_instance(self.hass)
            if not recorder_instance:
                return ToolResult(
                    output="Recorder component is not available",
                    error="No recorder",
                    success=False,
                )

            stats = await recorder_instance.async_add_executor_job(
                stats_module.get_last_short_term_statistics,
                self.hass,
                1,
                entity_id,
                True,
                set(),
            )

            if entity_id in stats:
                stat_data = stats[entity_id][0] if stats[entity_id] else {}
                result = {
                    "entity_id": entity_id,
                    "start": stat_data.get("start"),
                    "mean": stat_data.get("mean"),
                    "min": stat_data.get("min"),
                    "max": stat_data.get("max"),
                    "last_reset": stat_data.get("last_reset"),
                    "state": stat_data.get("state"),
                    "sum": stat_data.get("sum"),
                }
                return ToolResult(
                    output=json.dumps(result, default=str), metadata=result
                )
            else:
                return ToolResult(
                    output=f"No statistics available for entity {entity_id}",
                    error="No statistics",
                    success=False,
                )
        except Exception as e:
            _LOGGER.error("Error getting statistics for %s: %s", entity_id, e)
            return ToolResult(
                output=f"Error getting statistics: {str(e)}",
                error=str(e),
                success=False,
            )


@ToolRegistry.register
class GetDeviceRegistrySummary(Tool):
    id = "get_device_registry_summary"
    description = "Get a summary of all devices in the system, counted by manufacturer, area, and integration."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = []

    async def execute(self, **kwargs) -> ToolResult:
        _, device_registry, area_names = _get_registries(self.hass)

        by_manufacturer: dict[str, int] = {}
        by_area: dict[str, int] = {}
        total = 0

        for device in device_registry.devices.values():
            if device.disabled:
                continue
            total += 1
            mfr = device.manufacturer or "Unknown"
            by_manufacturer[mfr] = by_manufacturer.get(mfr, 0) + 1
            area_name = (
                area_names.get(device.area_id, "unassigned")
                if device.area_id
                else "unassigned"
            )
            by_area[area_name] = by_area.get(area_name, 0) + 1

        summary = {
            "total_devices": total,
            "by_manufacturer": dict(
                sorted(by_manufacturer.items(), key=lambda x: x[1], reverse=True)
            ),
            "by_area": dict(sorted(by_area.items(), key=lambda x: x[1], reverse=True)),
        }

        return ToolResult(output=json.dumps(summary, default=str), metadata=summary)


@ToolRegistry.register
class GetDeviceRegistry(Tool):
    id = "get_device_registry"
    description = "Get device registry entries with filtering and pagination."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="area_id",
            type="string",
            description="Filter by area ID",
            required=False,
        ),
        ToolParameter(
            name="manufacturer",
            type="string",
            description="Filter by manufacturer name",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset",
            required=False,
            default=0,
        ),
    ]

    async def execute(
        self,
        area_id: Optional[str] = None,
        manufacturer: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        **kwargs,
    ) -> ToolResult:
        _, device_registry, area_names = _get_registries(self.hass)

        results = []
        for device in device_registry.devices.values():
            if device.disabled:
                continue
            if area_id and device.area_id != area_id:
                continue
            if (
                manufacturer
                and (device.manufacturer or "").lower() != manufacturer.lower()
            ):
                continue
            results.append(
                {
                    "id": device.id,
                    "name": device.name or device.name_by_user,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area": (
                        area_names.get(device.area_id, device.area_id)
                        if device.area_id
                        else None
                    ),
                }
            )

        total = len(results)
        results = results[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "offset": offset},
        )


@ToolRegistry.register
class GetAreaRegistry(Tool):
    id = "get_area_registry"
    description = "Get all areas defined in Home Assistant with their details."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = []

    async def execute(self, **kwargs) -> ToolResult:
        from homeassistant.helpers import area_registry as ar

        registry = ar.async_get(self.hass)
        if not registry:
            return ToolResult(output="{}", metadata={})

        result = {}
        for area in registry.areas.values():
            result[area.id] = {
                "name": area.name,
                "normalized_name": area.normalized_name,
                "picture": area.picture,
                "icon": area.icon,
                "floor_id": area.floor_id,
                "labels": list(area.labels) if area.labels else [],
            }

        return ToolResult(output=json.dumps(result, default=str), metadata=result)


@ToolRegistry.register
class GetWeatherData(Tool):
    id = "get_weather_data"
    description = (
        "Get current weather data and forecast from available weather entities."
    )
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = []

    async def execute(self, **kwargs) -> ToolResult:
        weather_entities = [
            state for state in self.hass.states.async_all() if state.domain == "weather"
        ]

        if not weather_entities:
            return ToolResult(
                output="No weather entities found in the system.",
                error="No weather entities",
                success=False,
            )

        state = weather_entities[0]
        attrs = state.attributes
        forecast = attrs.get("forecast", [])

        processed_forecast = []
        for day in forecast:
            entry = {
                "datetime": day.get("datetime"),
                "temperature": day.get("temperature"),
                "condition": day.get("condition"),
                "precipitation": day.get("precipitation"),
                "precipitation_probability": day.get("precipitation_probability"),
                "humidity": day.get("humidity"),
                "wind_speed": day.get("wind_speed"),
            }
            if any(v is not None for v in entry.values()):
                processed_forecast.append(entry)

        current = {
            "entity_id": state.entity_id,
            "temperature": attrs.get("temperature"),
            "humidity": attrs.get("humidity"),
            "pressure": attrs.get("pressure"),
            "wind_speed": attrs.get("wind_speed"),
            "wind_bearing": attrs.get("wind_bearing"),
            "condition": state.state,
            "forecast_available": len(processed_forecast) > 0,
        }

        result = {"current": current, "forecast": processed_forecast}
        return ToolResult(output=json.dumps(result, default=str), metadata=result)


@ToolRegistry.register
class GetCalendarEvents(Tool):
    id = "get_calendar_events"
    description = "Get calendar events from calendar entities."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="entity_id",
            type="string",
            description="Optional specific calendar entity ID to query",
            required=False,
        ),
        ToolParameter(
            name="days",
            type="integer",
            description="Number of days ahead to look (default 7, max 30)",
            required=False,
            default=7,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Max events to return (default 50, max 200)",
            required=False,
            default=50,
        ),
    ]

    async def execute(
        self, entity_id: Optional[str] = None, days: int = 7, limit: int = 50, **kwargs
    ) -> ToolResult:
        from datetime import datetime, timedelta

        from homeassistant.util import dt as dt_util

        now = dt_util.now()
        end = now + timedelta(days=min(days, 30))

        # Find calendar entities
        if entity_id:
            calendar_entities = [entity_id]
        else:
            calendar_entities = [
                state.entity_id
                for state in self.hass.states.async_all()
                if state.entity_id.startswith("calendar.")
            ]

        if not calendar_entities:
            return ToolResult(
                output="No calendar entities found.",
                success=True,
                metadata={"count": 0},
            )

        all_events = []
        for cal_id in calendar_entities:
            try:
                result = await self.hass.services.async_call(
                    "calendar",
                    "get_events",
                    {
                        "entity_id": cal_id,
                        "start_date_time": now.isoformat(),
                        "end_date_time": end.isoformat(),
                    },
                    blocking=True,
                    return_response=True,
                )
                if result and cal_id in result:
                    events = result[cal_id].get("events", [])
                    for event in events:
                        all_events.append(
                            {
                                "calendar": cal_id,
                                "summary": event.get("summary"),
                                "start": event.get("start"),
                                "end": event.get("end"),
                                "description": event.get("description"),
                            }
                        )
            except Exception as e:
                _LOGGER.debug("Error getting events from %s: %s", cal_id, e)

        total = len(all_events)
        all_events = all_events[: min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(all_events, default=str),
            metadata={"total": total, "returned": len(all_events)},
        )


@ToolRegistry.register
class GetAutomations(Tool):
    id = "get_automations"
    description = "Get automations in the system with pagination."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(self, limit: int = 50, offset: int = 0, **kwargs) -> ToolResult:
        states = [
            state
            for state in self.hass.states.async_all()
            if state.entity_id.startswith("automation.")
        ]

        all_results = []
        for state in states:
            all_results.append(
                {
                    "entity_id": state.entity_id,
                    "state": state.state,
                    "friendly_name": state.attributes.get("friendly_name"),
                    "last_triggered": state.attributes.get("last_triggered"),
                }
            )

        total = len(all_results)
        results = all_results[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "offset": offset},
        )


@ToolRegistry.register
class GetScenes(Tool):
    id = "get_scenes"
    description = "Get scenes in the system with pagination."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="limit",
            type="integer",
            description="Max results (default 50, max 200)",
            required=False,
            default=50,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Pagination offset (default 0)",
            required=False,
            default=0,
        ),
    ]

    async def execute(self, limit: int = 50, offset: int = 0, **kwargs) -> ToolResult:
        all_results = []
        for state in self.hass.states.async_all("scene"):
            all_results.append(
                {
                    "entity_id": state.entity_id,
                    "name": state.attributes.get("friendly_name", state.entity_id),
                    "last_activated": state.attributes.get("last_activated"),
                    "icon": state.attributes.get("icon"),
                }
            )

        total = len(all_results)
        results = all_results[offset : offset + min(limit, _MAX_LIMIT)]

        return ToolResult(
            output=json.dumps(results, default=str),
            metadata={"total": total, "returned": len(results), "offset": offset},
        )


@ToolRegistry.register
class GetPersonData(Tool):
    id = "get_person_data"
    description = "Get person tracking information including location data."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = []

    async def execute(self, **kwargs) -> ToolResult:
        results = []
        for state in self.hass.states.async_all("person"):
            results.append(
                {
                    "entity_id": state.entity_id,
                    "name": state.attributes.get("friendly_name", state.entity_id),
                    "state": state.state,
                    "latitude": state.attributes.get("latitude"),
                    "longitude": state.attributes.get("longitude"),
                    "source": state.attributes.get("source"),
                    "gps_accuracy": state.attributes.get("gps_accuracy"),
                    "last_changed": (
                        state.last_changed.isoformat() if state.last_changed else None
                    ),
                }
            )

        return ToolResult(
            output=json.dumps(results, default=str), metadata={"count": len(results)}
        )


@ToolRegistry.register
class GetDashboards(Tool):
    id = "get_dashboards"
    description = "Get list of all Lovelace dashboards."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = []

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from ..managers.dashboard_manager import DashboardManager

            manager = DashboardManager(self.hass)
            dashboards = await manager.get_dashboards()
            return ToolResult(
                output=json.dumps(dashboards, default=str),
                metadata={"count": len(dashboards)},
            )
        except Exception as e:
            _LOGGER.error("Error getting dashboards: %s", e)
            return ToolResult(
                output=f"Error getting dashboards: {e}", error=str(e), success=False
            )


@ToolRegistry.register
class GetDashboardConfig(Tool):
    id = "get_dashboard_config"
    description = "Get configuration of a specific dashboard."
    category = ToolCategory.HOME_ASSISTANT
    tier = ToolTier.CORE
    parameters = [
        ToolParameter(
            name="dashboard_url",
            type="string",
            description="Dashboard URL path (None for default dashboard)",
            required=False,
        ),
    ]

    async def execute(
        self, dashboard_url: Optional[str] = None, **kwargs
    ) -> ToolResult:
        try:
            from ..managers.dashboard_manager import DashboardManager

            manager = DashboardManager(self.hass)
            config = await manager.get_dashboard_config(dashboard_url)
            return ToolResult(
                output=json.dumps(config, default=str),
                metadata=config,
            )
        except Exception as e:
            _LOGGER.error("Error getting dashboard config: %s", e)
            return ToolResult(
                output=f"Error getting dashboard config: {e}",
                error=str(e),
                success=False,
            )
