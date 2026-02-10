"""WebSocket handlers for proactive subsystem (heartbeat, scheduler, subagents)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api

from ..const import DOMAIN
from ._common import _get_user_id

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_heartbeat(hass: HomeAssistant) -> Any:
    """Get the HeartbeatService instance."""
    return hass.data.get(DOMAIN, {}).get("heartbeat")


def _get_scheduler(hass: HomeAssistant) -> Any:
    """Get the SchedulerService instance."""
    return hass.data.get(DOMAIN, {}).get("scheduler")


def _get_subagent_manager(hass: HomeAssistant) -> Any:
    """Get the SubagentManager instance."""
    return hass.data.get(DOMAIN, {}).get("subagent_manager")


# ---------------------------------------------------------------------------
# Heartbeat / Proactive Config
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/proactive/config/get",
    }
)
@websocket_api.async_response
async def ws_proactive_config_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get proactive subsystem configuration (heartbeat + scheduler status)."""
    heartbeat = _get_heartbeat(hass)
    scheduler = _get_scheduler(hass)

    result: dict[str, Any] = {"available": False}

    if heartbeat:
        result["available"] = True
        result["heartbeat"] = heartbeat.get_config()
    if scheduler:
        result["scheduler"] = scheduler.get_status()

    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/proactive/config/set",
        vol.Optional("enabled"): bool,
        vol.Optional("interval_minutes"): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=1440)
        ),
        vol.Optional("throttle_if_active_minutes"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=60)
        ),
        vol.Optional("max_alerts_per_hour"): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
        vol.Optional("monitored_domains"): vol.All(
            [vol.All(str, vol.Length(min=1, max=50))],
            vol.Length(min=1, max=20),
        ),
    }
)
@websocket_api.async_response
async def ws_proactive_config_set(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update heartbeat configuration."""
    heartbeat = _get_heartbeat(hass)
    if not heartbeat:
        connection.send_error(
            msg["id"], "not_available", "Proactive subsystem not initialized"
        )
        return

    # Extract config fields from message (exclude WS metadata)
    config_updates = {
        k: v for k, v in msg.items() if k not in ("id", "type") and v is not None
    }

    if not config_updates:
        connection.send_error(
            msg["id"], "invalid_input", "No configuration fields provided"
        )
        return

    try:
        updated = await heartbeat.async_update_config(**config_updates)
        connection.send_result(msg["id"], {"heartbeat": updated})
    except Exception as err:
        _LOGGER.error("Error updating proactive config: %s", err)
        connection.send_error(msg["id"], "update_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/proactive/alerts",
        vol.Optional("limit"): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
    }
)
@websocket_api.async_response
async def ws_proactive_alerts(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get recent proactive alert history."""
    heartbeat = _get_heartbeat(hass)
    if not heartbeat:
        connection.send_result(msg["id"], {"alerts": [], "available": False})
        return

    limit = msg.get("limit", 50)
    alerts = heartbeat.get_alert_history(limit=limit)
    results = heartbeat.get_result_history(limit=20)

    connection.send_result(
        msg["id"],
        {
            "available": True,
            "alerts": alerts,
            "recent_runs": results,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/proactive/run",
    }
)
@websocket_api.async_response
async def ws_proactive_run(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Manually trigger a heartbeat check."""
    heartbeat = _get_heartbeat(hass)
    if not heartbeat:
        connection.send_error(
            msg["id"], "not_available", "Heartbeat service not initialized"
        )
        return

    try:
        from dataclasses import asdict

        result = await heartbeat.async_run_heartbeat()
        connection.send_result(msg["id"], asdict(result))
    except Exception as err:
        _LOGGER.error("Error running heartbeat: %s", err)
        connection.send_error(msg["id"], "run_failed", str(err))


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/scheduler/list",
        vol.Optional("include_disabled"): bool,
    }
)
@websocket_api.async_response
async def ws_scheduler_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List all scheduled jobs."""
    scheduler = _get_scheduler(hass)
    if not scheduler:
        connection.send_result(msg["id"], {"jobs": [], "available": False})
        return

    include_disabled = msg.get("include_disabled", True)
    jobs = scheduler.list_jobs(include_disabled=include_disabled)

    connection.send_result(
        msg["id"],
        {
            "available": True,
            "jobs": jobs,
            "status": scheduler.get_status(),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/scheduler/add",
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=100)),
        vol.Required("prompt"): vol.All(str, vol.Length(min=1, max=2000)),
        vol.Required("cron"): vol.All(str, vol.Length(min=5, max=100)),
        vol.Optional("one_shot"): bool,
        vol.Optional("notify"): bool,
        vol.Optional("provider"): str,
    }
)
@websocket_api.async_response
async def ws_scheduler_add(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a new scheduled job."""
    scheduler = _get_scheduler(hass)
    if not scheduler:
        connection.send_error(msg["id"], "not_available", "Scheduler not initialized")
        return

    user_id = _get_user_id(connection)

    try:
        from dataclasses import asdict

        job = await scheduler.add_job(
            name=msg["name"],
            prompt=msg["prompt"],
            cron=msg["cron"],
            provider=msg.get("provider"),
            notify=msg.get("notify", True),
            one_shot=msg.get("one_shot", False),
            created_by="user",
            user_id=user_id,
        )
        connection.send_result(msg["id"], {"job": asdict(job)})
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_input", str(err))
    except Exception as err:
        _LOGGER.error("Error adding scheduled job: %s", err)
        connection.send_error(msg["id"], "add_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/scheduler/remove",
        vol.Required("job_id"): str,
    }
)
@websocket_api.async_response
async def ws_scheduler_remove(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Remove a scheduled job."""
    scheduler = _get_scheduler(hass)
    if not scheduler:
        connection.send_error(msg["id"], "not_available", "Scheduler not initialized")
        return

    removed = await scheduler.remove_job(msg["job_id"])
    if removed:
        connection.send_result(msg["id"], {"success": True})
    else:
        connection.send_error(msg["id"], "not_found", f"Job {msg['job_id']} not found")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/scheduler/enable",
        vol.Required("job_id"): str,
        vol.Required("enabled"): bool,
    }
)
@websocket_api.async_response
async def ws_scheduler_enable(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Enable or disable a scheduled job."""
    scheduler = _get_scheduler(hass)
    if not scheduler:
        connection.send_error(msg["id"], "not_available", "Scheduler not initialized")
        return

    from dataclasses import asdict

    job = await scheduler.enable_job(msg["job_id"], msg["enabled"])
    if job:
        connection.send_result(msg["id"], {"job": asdict(job)})
    else:
        connection.send_error(msg["id"], "not_found", f"Job {msg['job_id']} not found")


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/scheduler/run",
        vol.Required("job_id"): str,
    }
)
@websocket_api.async_response
async def ws_scheduler_run(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Manually run a scheduled job now."""
    scheduler = _get_scheduler(hass)
    if not scheduler:
        connection.send_error(msg["id"], "not_available", "Scheduler not initialized")
        return

    try:
        from dataclasses import asdict

        run = await scheduler.run_job(msg["job_id"])
        if run:
            connection.send_result(msg["id"], {"run": asdict(run)})
        else:
            connection.send_error(
                msg["id"], "not_found", f"Job {msg['job_id']} not found"
            )
    except Exception as err:
        _LOGGER.error("Error running job: %s", err)
        connection.send_error(msg["id"], "run_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/scheduler/history",
        vol.Optional("limit"): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    }
)
@websocket_api.async_response
async def ws_scheduler_history(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get scheduled job run history."""
    scheduler = _get_scheduler(hass)
    if not scheduler:
        connection.send_result(msg["id"], {"history": [], "available": False})
        return

    limit = msg.get("limit", 50)
    history = scheduler.get_run_history(limit=limit)
    connection.send_result(
        msg["id"],
        {
            "available": True,
            "history": history,
        },
    )


# ---------------------------------------------------------------------------
# Subagents
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/subagent/list",
    }
)
@websocket_api.async_response
async def ws_subagent_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List active subagent tasks."""
    manager = _get_subagent_manager(hass)
    if not manager:
        connection.send_result(msg["id"], {"tasks": [], "available": False})
        return

    user_id = _get_user_id(connection)
    tasks = manager.list_tasks(user_id=user_id)
    history = manager.get_history(limit=20)

    connection.send_result(
        msg["id"],
        {
            "available": True,
            "tasks": tasks,
            "history": history,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/subagent/get",
        vol.Required("task_id"): str,
    }
)
@websocket_api.async_response
async def ws_subagent_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Get details of a specific subagent task."""
    manager = _get_subagent_manager(hass)
    if not manager:
        connection.send_error(
            msg["id"], "not_available", "Subagent system not initialized"
        )
        return

    from dataclasses import asdict

    task = manager.get_task(msg["task_id"])
    if task:
        connection.send_result(msg["id"], {"task": asdict(task)})
    else:
        connection.send_error(
            msg["id"], "not_found", f"Task {msg['task_id']} not found"
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "homeclaw/subagent/cancel",
        vol.Required("task_id"): str,
    }
)
@websocket_api.async_response
async def ws_subagent_cancel(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Cancel a running subagent task."""
    manager = _get_subagent_manager(hass)
    if not manager:
        connection.send_error(
            msg["id"], "not_available", "Subagent system not initialized"
        )
        return

    cancelled = await manager.cancel_task(msg["task_id"])
    if cancelled:
        connection.send_result(msg["id"], {"success": True})
    else:
        connection.send_error(
            msg["id"],
            "not_found",
            f"Task {msg['task_id']} not found or already completed",
        )
