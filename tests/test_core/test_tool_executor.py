"""Tests for ToolExecutor denied_tools enforcement."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.core.tool_executor import ToolExecutor
from custom_components.homeclaw.function_calling import FunctionCall


@pytest.mark.asyncio
class TestToolExecutorDeniedTools:
    """Tests for denied_tools enforcement in ToolExecutor."""

    async def test_denied_tool_blocked_yield_none(self):
        """Test that a denied tool is blocked and returns error in messages."""
        fc = FunctionCall(
            id="call_1", name="call_service", arguments={"domain": "light"}
        )
        messages: list[dict] = []
        denied = frozenset({"call_service", "set_entity_state"})

        async for _ in ToolExecutor.execute_tool_calls(
            [fc],
            hass=MagicMock(),
            messages=messages,
            yield_mode="none",
            denied_tools=denied,
        ):
            pass

        assert len(messages) == 1
        assert messages[0]["role"] == "function"
        assert messages[0]["name"] == "call_service"
        content = json.loads(messages[0]["content"])
        assert "error" in content
        assert "not available" in content["error"]

    async def test_denied_tool_blocked_yield_status(self):
        """Test that blocked tool yields a status message."""
        fc = FunctionCall(id="call_1", name="scheduler", arguments={})
        messages: list[dict] = []
        denied = frozenset({"scheduler"})

        events = []
        async for event in ToolExecutor.execute_tool_calls(
            [fc],
            hass=MagicMock(),
            messages=messages,
            yield_mode="status",
            denied_tools=denied,
        ):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "status"
        assert "blocked" in events[0]["message"]

    async def test_denied_tool_blocked_yield_result(self):
        """Test that blocked tool yields a tool_result message."""
        fc = FunctionCall(id="call_1", name="create_automation", arguments={})
        messages: list[dict] = []
        denied = frozenset({"create_automation"})

        events = []
        async for event in ToolExecutor.execute_tool_calls(
            [fc],
            hass=MagicMock(),
            messages=messages,
            yield_mode="result",
            denied_tools=denied,
        ):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "tool_result"
        assert events[0]["name"] == "create_automation"

    async def test_allowed_tool_executes_normally(self):
        """Test that non-denied tools execute normally."""
        fc = FunctionCall(
            id="call_1", name="get_entity_state", arguments={"entity_id": "light.test"}
        )
        messages: list[dict] = []
        denied = frozenset({"call_service"})

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"success": True, "data": "on"}

        with (
            patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.get_tool",
                return_value=None,
            ),
            patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            async for _ in ToolExecutor.execute_tool_calls(
                [fc],
                hass=MagicMock(),
                messages=messages,
                yield_mode="none",
                denied_tools=denied,
            ):
                pass

        assert len(messages) == 1
        assert messages[0]["name"] == "get_entity_state"
        content = json.loads(messages[0]["content"])
        assert content["success"] is True

    async def test_no_denied_tools_executes_all(self):
        """Test that when denied_tools is None, all tools execute."""
        fc = FunctionCall(
            id="call_1", name="call_service", arguments={"domain": "light"}
        )
        messages: list[dict] = []

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"success": True}

        with (
            patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.get_tool",
                return_value=None,
            ),
            patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            async for _ in ToolExecutor.execute_tool_calls(
                [fc],
                hass=MagicMock(),
                messages=messages,
                yield_mode="none",
                denied_tools=None,
            ):
                pass

        assert len(messages) == 1
        content = json.loads(messages[0]["content"])
        assert content["success"] is True

    async def test_mixed_denied_and_allowed(self):
        """Test batch with some denied and some allowed tools."""
        calls = [
            FunctionCall(id="1", name="call_service", arguments={}),
            FunctionCall(
                id="2", name="get_entity_state", arguments={"entity_id": "light.test"}
            ),
            FunctionCall(id="3", name="subagent_spawn", arguments={}),
        ]
        messages: list[dict] = []
        denied = frozenset({"call_service", "subagent_spawn"})

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"success": True}

        with patch(
            "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            async for _ in ToolExecutor.execute_tool_calls(
                calls,
                hass=MagicMock(),
                messages=messages,
                yield_mode="none",
                denied_tools=denied,
            ):
                pass

        assert len(messages) == 3

        # First: blocked
        content_0 = json.loads(messages[0]["content"])
        assert "error" in content_0
        assert "not available" in content_0["error"]

        # Second: executed
        content_1 = json.loads(messages[1]["content"])
        assert content_1["success"] is True

        # Third: blocked
        content_2 = json.loads(messages[2]["content"])
        assert "error" in content_2

    async def test_invalid_arguments_return_structured_validation_error(self):
        """Invalid tool args should fail before execute_tool call."""
        fc = FunctionCall(id="call_1", name="get_entity_state", arguments={})
        messages: list[dict] = []

        mock_tool = MagicMock()
        param = MagicMock()
        param.name = "entity_id"
        param.required = True
        param.default = None
        mock_tool.parameters = [param]
        mock_tool.validate_parameters.return_value = [
            "Missing required parameter: entity_id"
        ]

        with (
            patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.get_tool",
                return_value=mock_tool,
            ),
            patch(
                "custom_components.homeclaw.core.tool_executor.ToolRegistry.execute_tool",
                new_callable=AsyncMock,
            ) as execute_mock,
        ):
            async for _ in ToolExecutor.execute_tool_calls(
                [fc],
                hass=MagicMock(),
                messages=messages,
                yield_mode="none",
                denied_tools=None,
            ):
                pass

        execute_mock.assert_not_called()
        assert len(messages) == 1
        payload = json.loads(messages[0]["content"])
        assert payload["error"] == "Invalid tool arguments"
        assert "entity_id" in payload["required_parameters"]
