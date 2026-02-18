"""Tests for progressive tool loading (load_tool meta-tool).

Tests cover:
- ToolTier enum and tier annotations
- ToolRegistry.get_core_tools() filtering
- ToolRegistry.get_on_demand_descriptions() generation
- LoadToolTool execution (activate, not found, already loaded)
- QueryProcessor._expand_loaded_tools() dynamic schema injection
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.core.query_processor import QueryProcessor
from custom_components.homeclaw.function_calling import (
    FunctionCall,
    ToolSchemaConverter,
)
from custom_components.homeclaw.tools.base import (
    Tool,
    ToolCategory,
    ToolParameter,
    ToolRegistry,
    ToolResult,
    ToolTier,
)
from custom_components.homeclaw.tools.load_tool import LoadToolTool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the tool registry before and after each test."""
    saved_tools = dict(ToolRegistry._tools)
    saved_instances = dict(ToolRegistry._instances)
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()
    ToolRegistry._tools.update(saved_tools)
    ToolRegistry._instances.update(saved_instances)


def _register_sample_tools():
    """Register a mix of CORE and ON_DEMAND tools for testing."""

    @ToolRegistry.register
    class CoreTool(Tool):
        id = "core_tool"
        description = "A core tool always available"
        tier = ToolTier.CORE
        category = ToolCategory.HOME_ASSISTANT

        async def execute(self, **params):
            return ToolResult(output="core result")

    @ToolRegistry.register
    class OnDemandTool(Tool):
        id = "on_demand_tool"
        description = "An on-demand tool loaded via load_tool"
        short_description = "On-demand tool for testing"
        tier = ToolTier.ON_DEMAND
        category = ToolCategory.WEB

        async def execute(self, **params):
            return ToolResult(output="on-demand result")

    @ToolRegistry.register
    class AnotherOnDemand(Tool):
        id = "another_on_demand"
        description = "Another on-demand tool"
        short_description = "Another test tool"
        tier = ToolTier.ON_DEMAND
        category = ToolCategory.UTILITY

        async def execute(self, **params):
            return ToolResult(output="another result")

    # Also register load_tool itself
    ToolRegistry.register(LoadToolTool)

    return CoreTool, OnDemandTool, AnotherOnDemand


# ---------------------------------------------------------------------------
# ToolTier enum tests
# ---------------------------------------------------------------------------


class TestToolTier:
    """Tests for ToolTier enum."""

    def test_tier_values(self):
        assert ToolTier.CORE.value == "core"
        assert ToolTier.ON_DEMAND.value == "on_demand"

    def test_default_tier_is_on_demand(self):
        """Tool base class defaults to ON_DEMAND."""
        assert Tool.tier == ToolTier.ON_DEMAND


# ---------------------------------------------------------------------------
# ToolRegistry tier-aware methods
# ---------------------------------------------------------------------------


class TestRegistryTierMethods:
    """Tests for ToolRegistry.get_core_tools() and get_on_demand_descriptions()."""

    def test_get_core_tools_returns_only_core(self):
        _register_sample_tools()
        core_tools = ToolRegistry.get_core_tools()
        core_ids = {t.id for t in core_tools}

        assert "core_tool" in core_ids
        assert "load_tool" in core_ids  # load_tool is CORE
        assert "on_demand_tool" not in core_ids
        assert "another_on_demand" not in core_ids

    def test_get_on_demand_descriptions_format(self):
        _register_sample_tools()
        desc = ToolRegistry.get_on_demand_descriptions()

        assert "Additional tools available" in desc
        assert "on_demand_tool: On-demand tool for testing" in desc
        assert "another_on_demand: Another test tool" in desc
        # CORE tools should NOT appear as tool entries (load_tool appears in header text)
        assert "core_tool" not in desc
        assert "- load_tool:" not in desc

    def test_get_on_demand_descriptions_empty_when_no_on_demand(self):
        """If all tools are CORE, return empty string."""

        @ToolRegistry.register
        class OnlyCore(Tool):
            id = "only_core"
            description = "Only core"
            tier = ToolTier.CORE

            async def execute(self, **params):
                return ToolResult(output="ok")

        desc = ToolRegistry.get_on_demand_descriptions()
        assert desc == ""

    def test_short_description_falls_back_to_description(self):
        """If short_description is empty, use full description."""

        @ToolRegistry.register
        class NoShortDesc(Tool):
            id = "no_short"
            description = "Full description here"
            tier = ToolTier.ON_DEMAND

            async def execute(self, **params):
                return ToolResult(output="ok")

        desc = ToolRegistry.get_on_demand_descriptions()
        assert "no_short: Full description here" in desc


# ---------------------------------------------------------------------------
# LoadToolTool execution tests
# ---------------------------------------------------------------------------


class TestLoadToolExecution:
    """Tests for the load_tool meta-tool."""

    @pytest.mark.asyncio
    async def test_load_existing_on_demand_tool(self):
        _register_sample_tools()
        tool = LoadToolTool()
        result = await tool.execute(tool_name="on_demand_tool")

        assert result.success is True
        assert "on_demand_tool" in result.output
        assert "activated" in result.output
        assert result.metadata.get("loaded") is True

    @pytest.mark.asyncio
    async def test_load_nonexistent_tool(self):
        _register_sample_tools()
        tool = LoadToolTool()
        result = await tool.execute(tool_name="nonexistent_tool")

        assert result.success is False
        assert "not found" in result.output
        assert "on_demand_tool" in result.output  # lists available tools

    @pytest.mark.asyncio
    async def test_load_core_tool_returns_already_loaded(self):
        _register_sample_tools()
        tool = LoadToolTool()
        result = await tool.execute(tool_name="core_tool")

        assert result.success is True
        assert "already available" in result.output
        assert result.metadata.get("already_loaded") is True

    @pytest.mark.asyncio
    async def test_load_empty_tool_name(self):
        _register_sample_tools()
        tool = LoadToolTool()
        result = await tool.execute(tool_name="")

        assert result.success is False
        assert "required" in result.output

    @pytest.mark.asyncio
    async def test_load_missing_tool_name_param(self):
        _register_sample_tools()
        tool = LoadToolTool()
        result = await tool.execute()

        assert result.success is False


# ---------------------------------------------------------------------------
# QueryProcessor._expand_loaded_tools tests
# ---------------------------------------------------------------------------


class TestExpandLoadedTools:
    """Tests for dynamic tool schema injection."""

    def test_expand_adds_tool_schema(self):
        _register_sample_tools()

        # Start with only core tool schemas
        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        # Simulate load_tool("on_demand_tool") call
        function_calls = [
            FunctionCall(
                id="call_1", name="load_tool", arguments={"tool_name": "on_demand_tool"}
            )
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, initial_tools, hass=None
        )

        assert result is not None
        assert len(result) == initial_count + 1

        # Verify the new tool is in the list
        tool_names = [t["function"]["name"] for t in result]
        assert "on_demand_tool" in tool_names

    def test_expand_skips_already_loaded(self):
        _register_sample_tools()

        # Pre-load on_demand_tool
        all_tools = ToolSchemaConverter.to_openai_format(ToolRegistry.get_all_tools())
        initial_count = len(all_tools)

        function_calls = [
            FunctionCall(
                id="call_1", name="load_tool", arguments={"tool_name": "on_demand_tool"}
            )
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, all_tools, hass=None
        )

        assert len(result) == initial_count  # no change

    def test_expand_ignores_non_load_tool_calls(self):
        _register_sample_tools()

        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        function_calls = [FunctionCall(id="call_1", name="core_tool", arguments={})]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, initial_tools, hass=None
        )

        assert len(result) == initial_count

    def test_expand_handles_none_tools(self):
        function_calls = [
            FunctionCall(id="call_1", name="load_tool", arguments={"tool_name": "x"})
        ]

        result = QueryProcessor._expand_loaded_tools(function_calls, None, hass=None)

        assert result is None

    def test_expand_handles_unknown_tool(self):
        _register_sample_tools()

        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        function_calls = [
            FunctionCall(
                id="call_1", name="load_tool", arguments={"tool_name": "nonexistent"}
            )
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, initial_tools, hass=None
        )

        assert len(result) == initial_count  # no change

    def test_expand_multiple_load_tool_calls(self):
        _register_sample_tools()

        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        function_calls = [
            FunctionCall(
                id="call_1", name="load_tool", arguments={"tool_name": "on_demand_tool"}
            ),
            FunctionCall(
                id="call_2",
                name="load_tool",
                arguments={"tool_name": "another_on_demand"},
            ),
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, initial_tools, hass=None
        )

        assert len(result) == initial_count + 2
        tool_names = [t["function"]["name"] for t in result]
        assert "on_demand_tool" in tool_names
        assert "another_on_demand" in tool_names


# ---------------------------------------------------------------------------
# Integration: tier annotations on real tools
# ---------------------------------------------------------------------------


class TestRealToolTierAnnotations:
    """Verify that real tool classes have correct tier annotations."""

    def test_ha_native_tools_are_core(self):
        from custom_components.homeclaw.tools.ha_native import (
            CallService,
            GetEntitiesByDomain,
            GetEntityState,
        )

        assert GetEntityState.tier == ToolTier.CORE
        assert CallService.tier == ToolTier.CORE
        assert GetEntitiesByDomain.tier == ToolTier.CORE

    def test_memory_tools_are_core(self):
        from custom_components.homeclaw.tools.memory import (
            MemoryForgetTool,
            MemoryRecallTool,
            MemoryStoreTool,
        )

        assert MemoryStoreTool.tier == ToolTier.CORE
        assert MemoryRecallTool.tier == ToolTier.CORE
        assert MemoryForgetTool.tier == ToolTier.CORE

    def test_scheduler_is_core(self):
        from custom_components.homeclaw.tools.scheduler import SchedulerTool

        assert SchedulerTool.tier == ToolTier.CORE

    def test_load_tool_is_core(self):
        assert LoadToolTool.tier == ToolTier.CORE

    def test_websearch_is_on_demand(self):
        from custom_components.homeclaw.tools.websearch import WebSearchTool

        assert WebSearchTool.tier == ToolTier.ON_DEMAND
        assert WebSearchTool.short_description != ""

    def test_webfetch_is_on_demand(self):
        from custom_components.homeclaw.tools.webfetch import WebFetchTool

        assert WebFetchTool.tier == ToolTier.ON_DEMAND
        assert WebFetchTool.short_description != ""

    def test_context7_is_on_demand(self):
        from custom_components.homeclaw.tools.context7 import (
            Context7DocsTool,
            Context7ResolveTool,
        )

        assert Context7ResolveTool.tier == ToolTier.ON_DEMAND
        assert Context7DocsTool.tier == ToolTier.ON_DEMAND

    def test_identity_is_on_demand(self):
        from custom_components.homeclaw.tools.identity import IdentitySetTool

        assert IdentitySetTool.tier == ToolTier.ON_DEMAND

    def test_channel_status_is_on_demand(self):
        from custom_components.homeclaw.tools.channel_status import (
            CheckDiscordConnection,
        )

        assert CheckDiscordConnection.tier == ToolTier.ON_DEMAND


# ---------------------------------------------------------------------------
# Security: disabled tools, denied tools, tier enforcement
# ---------------------------------------------------------------------------


class TestLoadToolSecurity:
    """Tests for security validations in load_tool and _expand_loaded_tools."""

    @pytest.mark.asyncio
    async def test_load_disabled_tool_rejected(self):
        """load_tool must refuse to activate a disabled tool."""

        @ToolRegistry.register
        class DisabledTool(Tool):
            id = "disabled_tool"
            description = "A disabled on-demand tool"
            tier = ToolTier.ON_DEMAND
            enabled = False
            category = ToolCategory.UTILITY

            async def execute(self, **params):
                return ToolResult(output="should not run")

        ToolRegistry.register(LoadToolTool)
        tool = LoadToolTool()
        result = await tool.execute(tool_name="disabled_tool")

        assert result.success is False
        assert "disabled" in result.output

    def test_expand_rejects_denied_tool(self):
        """_expand_loaded_tools must not add a tool that is in denied_tools."""
        _register_sample_tools()

        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        function_calls = [
            FunctionCall(
                id="call_1",
                name="load_tool",
                arguments={"tool_name": "on_demand_tool"},
            )
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls,
            initial_tools,
            hass=None,
            denied_tools=frozenset({"on_demand_tool"}),
        )

        assert len(result) == initial_count  # not added

    def test_expand_rejects_disabled_tool(self):
        """_expand_loaded_tools must not add a disabled tool."""

        @ToolRegistry.register
        class DisabledOD(Tool):
            id = "disabled_od"
            description = "Disabled on-demand"
            tier = ToolTier.ON_DEMAND
            enabled = False
            category = ToolCategory.UTILITY

            async def execute(self, **params):
                return ToolResult(output="nope")

        ToolRegistry.register(LoadToolTool)

        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        function_calls = [
            FunctionCall(
                id="call_1",
                name="load_tool",
                arguments={"tool_name": "disabled_od"},
            )
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, initial_tools, hass=None
        )

        assert len(result) == initial_count  # not added

    def test_expand_rejects_core_tier_tool(self):
        """_expand_loaded_tools must not re-add a CORE tool via load_tool."""
        _register_sample_tools()

        # Start with empty tools list (simulate edge case)
        initial_tools: list[dict] = []

        function_calls = [
            FunctionCall(
                id="call_1",
                name="load_tool",
                arguments={"tool_name": "core_tool"},
            )
        ]

        result = QueryProcessor._expand_loaded_tools(
            function_calls, initial_tools, hass=None
        )

        assert len(result) == 0  # CORE tool not added via load_tool


# ---------------------------------------------------------------------------
# ToolRegistry.list_on_demand_ids
# ---------------------------------------------------------------------------


class TestListOnDemandIds:
    """Tests for ToolRegistry.list_on_demand_ids()."""

    def test_returns_only_enabled_on_demand(self):
        _register_sample_tools()
        ids = ToolRegistry.list_on_demand_ids()

        assert "on_demand_tool" in ids
        assert "another_on_demand" in ids
        assert "core_tool" not in ids
        assert "load_tool" not in ids

    def test_excludes_disabled_tools(self):
        @ToolRegistry.register
        class EnabledOD(Tool):
            id = "enabled_od"
            description = "Enabled"
            tier = ToolTier.ON_DEMAND
            category = ToolCategory.UTILITY

            async def execute(self, **params):
                return ToolResult(output="ok")

        @ToolRegistry.register
        class DisabledOD2(Tool):
            id = "disabled_od2"
            description = "Disabled"
            tier = ToolTier.ON_DEMAND
            enabled = False
            category = ToolCategory.UTILITY

            async def execute(self, **params):
                return ToolResult(output="nope")

        ids = ToolRegistry.list_on_demand_ids()
        assert "enabled_od" in ids
        assert "disabled_od2" not in ids

    def test_returns_sorted(self):
        _register_sample_tools()
        ids = ToolRegistry.list_on_demand_ids()
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Security: load_tool itself denied
# ---------------------------------------------------------------------------


class TestLoadToolDenied:
    """Tests for when load_tool itself is in denied_tools."""

    def test_expand_skips_all_when_load_tool_denied(self):
        """If load_tool is denied, _expand_loaded_tools must skip all expansion."""
        _register_sample_tools()

        initial_tools = ToolSchemaConverter.to_openai_format(
            ToolRegistry.get_core_tools()
        )
        initial_count = len(initial_tools)

        function_calls = [
            FunctionCall(
                id="call_1",
                name="load_tool",
                arguments={"tool_name": "on_demand_tool"},
            )
        ]

        # load_tool itself is denied — should skip all expansion
        result = QueryProcessor._expand_loaded_tools(
            function_calls,
            initial_tools,
            hass=None,
            denied_tools=frozenset({"load_tool"}),
        )

        assert len(result) == initial_count  # no change
