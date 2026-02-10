"""Tests for SubagentManager."""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.core.subagent import (
    DENIED_TOOLS,
    EVENT_SUBAGENT_COMPLETE,
    EVENT_SUBAGENT_STARTED,
    MAX_CONCURRENT_PER_USER,
    SubagentManager,
    SubagentTask,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"agents": {}}}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    return hass


class TestSubagentTask:
    """Tests for SubagentTask dataclass."""

    def test_default_values(self):
        """Test default task values."""
        task = SubagentTask(
            task_id="abc",
            label="test task",
            prompt="Do something",
        )
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None
        assert task.completed_at is None
        assert task.duration_ms == 0

    def test_serialization(self):
        """Test task serialization."""
        task = SubagentTask(
            task_id="abc",
            label="test",
            prompt="Do something",
            status="completed",
            result="Done!",
            user_id="user1",
        )
        d = asdict(task)
        assert d["task_id"] == "abc"
        assert d["status"] == "completed"
        assert d["result"] == "Done!"


class TestDeniedTools:
    """Tests for DENIED_TOOLS configuration."""

    def test_critical_tools_denied(self):
        """Test that dangerous tools are in DENIED_TOOLS."""
        assert "scheduler" in DENIED_TOOLS
        assert "subagent_spawn" in DENIED_TOOLS
        assert "call_service" in DENIED_TOOLS
        assert "set_entity_state" in DENIED_TOOLS
        assert "identity_set" in DENIED_TOOLS
        assert "memory_store" in DENIED_TOOLS

    def test_read_tools_not_denied(self):
        """Test that read-only tools are NOT denied."""
        assert "get_entity_state" not in DENIED_TOOLS
        assert "web_fetch" not in DENIED_TOOLS
        assert "web_search" not in DENIED_TOOLS
        assert "memory_recall" not in DENIED_TOOLS


class TestSubagentManagerSpawn:
    """Tests for spawning subagents."""

    @pytest.mark.asyncio
    async def test_spawn_success(self, mock_hass):
        """Test successful subagent spawn."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": "Analysis complete.",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Analyze energy data",
            label="energy_analysis",
            user_id="user1",
        )

        assert task_id is not None
        assert len(task_id) == 8

        # Check started event was fired
        mock_hass.bus.async_fire.assert_called_with(
            EVENT_SUBAGENT_STARTED,
            {
                "task_id": task_id,
                "label": "energy_analysis",
                "user_id": "user1",
            },
        )

        # Give the background task time to complete
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_spawn_concurrency_limit(self, mock_hass):
        """Test that concurrency limit is enforced."""

        async def slow_query(**kwargs):
            await asyncio.sleep(10)
            return {"answer": "done", "success": True}

        mock_agent = MagicMock()
        mock_agent.process_query = slow_query
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)

        # Spawn up to limit
        for i in range(MAX_CONCURRENT_PER_USER):
            await manager.spawn(
                prompt=f"Task {i}",
                label=f"task_{i}",
                user_id="user1",
            )

        # Next one should fail
        with pytest.raises(RuntimeError, match="Maximum concurrent"):
            await manager.spawn(
                prompt="One too many",
                label="overflow",
                user_id="user1",
            )

        # But different user should succeed
        task_id = await manager.spawn(
            prompt="Different user",
            label="other",
            user_id="user2",
        )
        assert task_id is not None

        # Clean up
        for tid in list(manager._running_asyncio_tasks.keys()):
            task = manager._running_asyncio_tasks[tid]
            task.cancel()
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_spawn_no_agent(self, mock_hass):
        """Test spawn when no agent available — task should fail gracefully."""
        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="No agent",
            label="test",
            user_id="user1",
        )

        # Wait for background task
        await asyncio.sleep(0.1)

        # Task should be in history as failed
        history = manager.get_history()
        found = [h for h in history if h["task_id"] == task_id]
        assert len(found) == 1
        assert found[0]["status"] == "failed"
        assert "No AI agent" in found[0]["error"]


class TestSubagentManagerTaskManagement:
    """Tests for task management operations."""

    def test_list_tasks_empty(self, mock_hass):
        """Test listing tasks when empty."""
        manager = SubagentManager(mock_hass)
        tasks = manager.list_tasks()
        assert tasks == []

    def test_list_tasks_filtered_by_user(self, mock_hass):
        """Test listing tasks filtered by user."""
        manager = SubagentManager(mock_hass)

        task1 = SubagentTask(
            task_id="t1", label="Task 1", prompt="p1", user_id="user1", status="running"
        )
        task2 = SubagentTask(
            task_id="t2", label="Task 2", prompt="p2", user_id="user2", status="running"
        )
        manager._tasks["t1"] = task1
        manager._tasks["t2"] = task2

        tasks_user1 = manager.list_tasks(user_id="user1")
        assert len(tasks_user1) == 1
        assert tasks_user1[0]["task_id"] == "t1"

    def test_get_task_active(self, mock_hass):
        """Test getting an active task."""
        manager = SubagentManager(mock_hass)

        task = SubagentTask(task_id="t1", label="Test", prompt="p1")
        manager._tasks["t1"] = task

        result = manager.get_task("t1")
        assert result is not None
        assert result.task_id == "t1"

    def test_get_task_from_history(self, mock_hass):
        """Test getting a task from completed history."""
        manager = SubagentManager(mock_hass)

        manager._completed_history.append(
            {
                "task_id": "old1",
                "label": "Old Task",
                "prompt": "old prompt",
                "status": "completed",
                "result": "Done",
                "error": None,
                "created_at": time.time(),
                "completed_at": time.time(),
                "parent_session_id": "",
                "user_id": "user1",
                "provider": None,
                "duration_ms": 100,
            }
        )

        result = manager.get_task("old1")
        assert result is not None
        assert result.status == "completed"

    def test_get_task_not_found(self, mock_hass):
        """Test getting a non-existent task."""
        manager = SubagentManager(mock_hass)
        assert manager.get_task("nonexistent") is None

    def test_get_history(self, mock_hass):
        """Test getting completed task history."""
        manager = SubagentManager(mock_hass)
        assert manager.get_history() == []

        manager._completed_history.append({"task_id": "t1", "status": "completed"})
        manager._completed_history.append({"task_id": "t2", "status": "failed"})

        history = manager.get_history(limit=1)
        assert len(history) == 1
        assert history[0]["task_id"] == "t2"  # Most recent last


class TestSubagentCancellation:
    """Tests for task cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_running_task(self, mock_hass):
        """Test cancelling a running task."""

        async def slow_query(**kwargs):
            await asyncio.sleep(10)
            return {"answer": "done", "success": True}

        mock_agent = MagicMock()
        mock_agent.process_query = slow_query
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Slow task",
            label="slow",
            user_id="user1",
        )

        await asyncio.sleep(0.05)  # Let it start

        cancelled = await manager.cancel_task(task_id)
        assert cancelled is True

        # Wait for cancellation to propagate
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, mock_hass):
        """Test cancelling a non-existent task."""
        manager = SubagentManager(mock_hass)
        assert await manager.cancel_task("ghost") is False

    @pytest.mark.asyncio
    async def test_cancel_completed_task(self, mock_hass):
        """Test cancelling an already-completed task."""
        manager = SubagentManager(mock_hass)

        task = SubagentTask(
            task_id="done1", label="Done", prompt="p", status="completed"
        )
        manager._tasks["done1"] = task

        assert await manager.cancel_task("done1") is False


class TestSubagentExecution:
    """Tests for subagent execution flow."""

    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_hass):
        """Test a subagent completes successfully."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": "Found 3 unused devices in the living room.",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Audit devices",
            label="audit",
            user_id="user1",
        )

        await asyncio.sleep(0.1)

        history = manager.get_history()
        found = [h for h in history if h["task_id"] == task_id]
        assert len(found) == 1
        assert found[0]["status"] == "completed"
        assert "unused devices" in found[0]["result"]
        assert found[0]["duration_ms"] >= 0

        fire_calls = mock_hass.bus.async_fire.call_args_list
        event_names = [c[0][0] for c in fire_calls]
        assert EVENT_SUBAGENT_COMPLETE in event_names

    @pytest.mark.asyncio
    async def test_failed_execution(self, mock_hass):
        """Test a subagent that fails."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": "",
                "success": False,
                "error": "Provider error",
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Fail task",
            label="fail",
            user_id="user1",
        )

        await asyncio.sleep(0.1)

        history = manager.get_history()
        found = [h for h in history if h["task_id"] == task_id]
        assert len(found) == 1
        assert found[0]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_exception_during_execution(self, mock_hass):
        """Test a subagent that throws an exception."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(side_effect=ValueError("Boom!"))
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Crash task",
            label="crash",
            user_id="user1",
        )

        await asyncio.sleep(0.1)

        history = manager.get_history()
        found = [h for h in history if h["task_id"] == task_id]
        assert len(found) == 1
        assert found[0]["status"] == "failed"
        assert "Boom!" in found[0]["error"]

    @pytest.mark.asyncio
    async def test_passes_denied_tools(self, mock_hass):
        """Test that _run_subagent passes DENIED_TOOLS to agent.process_query."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": "Done with restrictions.",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Check devices",
            label="check",
            user_id="user1",
        )

        await asyncio.sleep(0.1)

        # Verify process_query was called with denied_tools
        mock_agent.process_query.assert_called_once()
        call_kwargs = mock_agent.process_query.call_args
        assert call_kwargs.kwargs.get("denied_tools") == DENIED_TOOLS

    @pytest.mark.asyncio
    async def test_passes_subagent_system_prompt(self, mock_hass):
        """Test that _run_subagent passes SUBAGENT_SYSTEM_PROMPT."""
        from custom_components.homeclaw.prompts import SUBAGENT_SYSTEM_PROMPT

        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": "Analyzed.",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        await manager.spawn(
            prompt="Analyze data",
            label="analyze",
            user_id="user1",
        )

        await asyncio.sleep(0.1)

        call_kwargs = mock_agent.process_query.call_args
        assert call_kwargs.kwargs.get("system_prompt") == SUBAGENT_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_move_to_history(self, mock_hass):
        """Test that completed tasks are moved from active to history."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(
            return_value={
                "answer": "Done",
                "success": True,
            }
        )
        mock_hass.data[DOMAIN]["agents"] = {"test": mock_agent}

        manager = SubagentManager(mock_hass)
        task_id = await manager.spawn(
            prompt="Quick",
            label="quick",
            user_id="user1",
        )

        await asyncio.sleep(0.1)

        # Active tasks should be empty
        assert task_id not in manager._tasks
        # History should have it
        assert len(manager._completed_history) == 1
