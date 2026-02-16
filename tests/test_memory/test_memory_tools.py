"""Tests for memory tools (memory_store, memory_recall, memory_forget).

Tests cover:
- MemoryStoreTool: store success, duplicate, missing manager, error, importance clamping
- MemoryRecallTool: search results, empty results, missing manager, limit clamping, error
- MemoryForgetTool: delete by id, delete by query, no params, missing manager, no matches, error
- Helper functions: _get_memory_manager, _get_user_id_from_context
"""

from __future__ import annotations

import json
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.memory.memory_store import Memory
from custom_components.homeclaw.tools.memory import (
    MemoryForgetTool,
    MemoryRecallTool,
    MemoryStoreTool,
    _get_user_id_from_context,
    _get_memory_manager,
)


# --- Fixtures ---


def _make_hass(*, with_rag=True, with_memory=True, user_id=None):
    """Create a mock hass object with optional RAG/memory setup."""
    hass = MagicMock()
    hass.data = {}

    if with_rag:
        rag_manager = MagicMock()
        rag_manager.is_initialized = True

        if with_memory:
            memory_manager = AsyncMock()
            rag_manager.memory_manager = memory_manager
        else:
            rag_manager.memory_manager = None

        hass.data[DOMAIN] = {"rag_manager": rag_manager}
    else:
        hass.data[DOMAIN] = {}

    return hass


def _make_memory(
    id="mem-123",
    user_id="user-1",
    text="User likes warm white lights",
    category="preference",
    importance=0.8,
    score=0.92,
):
    """Create a Memory dataclass instance."""
    now = time.time()
    return Memory(
        id=id,
        user_id=user_id,
        text=text,
        category=category,
        importance=importance,
        created_at=now,
        updated_at=now,
        source="auto",
        session_id="",
        score=score,
    )


# --- _get_memory_manager tests ---


class TestGetMemoryManager:
    """Tests for the _get_memory_manager helper."""

    def test_returns_memory_manager(self):
        hass = _make_hass(with_rag=True, with_memory=True)
        result = _get_memory_manager(hass)
        assert result is not None
        assert result is hass.data[DOMAIN]["rag_manager"].memory_manager

    def test_returns_none_when_no_hass(self):
        assert _get_memory_manager(None) is None

    def test_returns_none_when_no_domain(self):
        hass = MagicMock()
        hass.data = {}
        assert _get_memory_manager(hass) is None

    def test_returns_none_when_no_rag_manager(self):
        hass = _make_hass(with_rag=False)
        assert _get_memory_manager(hass) is None

    def test_returns_none_when_rag_not_initialized(self):
        hass = _make_hass(with_rag=True, with_memory=True)
        hass.data[DOMAIN]["rag_manager"].is_initialized = False
        assert _get_memory_manager(hass) is None

    def test_returns_none_when_no_memory_manager_attr(self):
        hass = _make_hass(with_rag=True, with_memory=False)
        # memory_manager is None
        assert _get_memory_manager(hass) is None


# --- _get_user_id_from_context tests ---


class TestGetUserIdFromContext:
    """Tests for the _get_user_id_from_context helper."""

    def test_returns_user_id_from_kwargs(self):
        assert _get_user_id_from_context({"_user_id": "user-42"}) == "user-42"

    def test_returns_default_when_no_user_id(self):
        assert _get_user_id_from_context({}) == "default"

    def test_returns_default_when_no_context_key(self):
        assert _get_user_id_from_context({"other_key": "value"}) == "default"

    def test_returns_empty_string_if_set(self):
        assert _get_user_id_from_context({"_user_id": ""}) == ""


# --- MemoryStoreTool tests ---


class TestMemoryStoreTool:
    """Tests for the memory_store tool."""

    @pytest.mark.asyncio
    async def test_store_success(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(return_value="mem-abc")

        tool = MemoryStoreTool(hass=hass)
        result = await tool.execute(
            text="User prefers dark mode",
            category="preference",
            importance=0.9,
            _user_id="user-1",
        )

        assert result.success is True
        data = json.loads(result.output)
        assert data["stored"] is True
        assert data["memory_id"] == "mem-abc"
        assert data["category"] == "preference"
        assert data["importance"] == 0.9
        mm.store_memory.assert_awaited_once_with(
            text="User prefers dark mode",
            user_id="user-1",
            category="preference",
            importance=0.9,
            source="agent",
            ttl_days=None,
        )

    @pytest.mark.asyncio
    async def test_store_duplicate(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(return_value=None)  # duplicate

        tool = MemoryStoreTool(hass=hass)
        result = await tool.execute(text="Already stored", _user_id="user-1")

        assert result.success is True  # not an error, just a "not stored"
        data = json.loads(result.output)
        assert data["stored"] is False
        assert data["reason"] == "duplicate_memory"

    @pytest.mark.asyncio
    async def test_store_no_memory_manager(self):
        hass = _make_hass(with_rag=False)
        tool = MemoryStoreTool(hass=hass)
        result = await tool.execute(text="Something", _user_id="user-1")

        assert result.success is False
        assert result.error == "memory_not_initialized"

    @pytest.mark.asyncio
    async def test_store_defaults(self):
        """Default category=fact, importance=0.8."""
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(return_value="mem-xyz")

        tool = MemoryStoreTool(hass=hass)
        result = await tool.execute(text="Some fact", _user_id="user-1")

        mm.store_memory.assert_awaited_once_with(
            text="Some fact",
            user_id="user-1",
            category="fact",
            importance=0.8,
            source="agent",
            ttl_days=None,
        )

    @pytest.mark.asyncio
    async def test_store_clamps_importance_high(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(return_value="mem-1")

        tool = MemoryStoreTool(hass=hass)
        await tool.execute(text="Important", importance=5.0, _user_id="user-1")

        # Should clamp to 1.0
        call_kwargs = mm.store_memory.call_args[1]
        assert call_kwargs["importance"] == 1.0

    @pytest.mark.asyncio
    async def test_store_clamps_importance_low(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(return_value="mem-1")

        tool = MemoryStoreTool(hass=hass)
        await tool.execute(text="Not important", importance=-0.5, _user_id="user-1")

        call_kwargs = mm.store_memory.call_args[1]
        assert call_kwargs["importance"] == 0.0

    @pytest.mark.asyncio
    async def test_store_exception(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(side_effect=RuntimeError("DB error"))

        tool = MemoryStoreTool(hass=hass)
        result = await tool.execute(text="Something", _user_id="user-1")

        assert result.success is False
        assert "DB error" in result.error

    @pytest.mark.asyncio
    async def test_store_default_user(self):
        """When no _user_id in context, falls back to 'default'."""
        hass = _make_hass()
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.store_memory = AsyncMock(return_value="mem-1")

        tool = MemoryStoreTool(hass=hass)
        # No _user_id passed — should fall back to "default"
        await tool.execute(text="Test")

        call_kwargs = mm.store_memory.call_args[1]
        assert call_kwargs["user_id"] == "default"


# --- MemoryRecallTool tests ---


class TestMemoryRecallTool:
    """Tests for the memory_recall tool."""

    @pytest.mark.asyncio
    async def test_recall_with_results(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(
            return_value=[
                _make_memory(id="m1", text="Likes warm lights", score=0.95),
                _make_memory(id="m2", text="Bedroom temp 21C", score=0.8),
            ]
        )

        tool = MemoryRecallTool(hass=hass)
        result = await tool.execute(query="light preferences", _user_id="user-1")

        assert result.success is True
        data = json.loads(result.output)
        assert data["count"] == 2
        assert data["memories"][0]["id"] == "m1"
        assert data["memories"][0]["score"] == 0.95
        assert data["memories"][1]["id"] == "m2"

        mm.search_memories.assert_awaited_once_with(
            query="light preferences",
            user_id="user-1",
            limit=5,
        )

    @pytest.mark.asyncio
    async def test_recall_empty_results(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(return_value=[])

        tool = MemoryRecallTool(hass=hass)
        result = await tool.execute(query="nonexistent topic", _user_id="user-1")

        assert result.success is True
        data = json.loads(result.output)
        assert data["count"] == 0
        assert data["memories"] == []

    @pytest.mark.asyncio
    async def test_recall_no_memory_manager(self):
        hass = _make_hass(with_rag=False)
        tool = MemoryRecallTool(hass=hass)
        result = await tool.execute(query="anything", _user_id="user-1")

        assert result.success is False
        assert result.error == "memory_not_initialized"

    @pytest.mark.asyncio
    async def test_recall_custom_limit(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(return_value=[])

        tool = MemoryRecallTool(hass=hass)
        await tool.execute(query="test", limit=10, _user_id="user-1")

        mm.search_memories.assert_awaited_once_with(
            query="test",
            user_id="user-1",
            limit=10,
        )

    @pytest.mark.asyncio
    async def test_recall_clamps_limit_high(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(return_value=[])

        tool = MemoryRecallTool(hass=hass)
        await tool.execute(query="test", limit=100, _user_id="user-1")

        # Should clamp to 20
        call_kwargs = mm.search_memories.call_args[1]
        assert call_kwargs["limit"] == 20

    @pytest.mark.asyncio
    async def test_recall_clamps_limit_low(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(return_value=[])

        tool = MemoryRecallTool(hass=hass)
        await tool.execute(query="test", limit=0, _user_id="user-1")

        call_kwargs = mm.search_memories.call_args[1]
        assert call_kwargs["limit"] == 1

    @pytest.mark.asyncio
    async def test_recall_exception(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(side_effect=RuntimeError("Search failed"))

        tool = MemoryRecallTool(hass=hass)
        result = await tool.execute(query="test", _user_id="user-1")

        assert result.success is False
        assert "Search failed" in result.error


# --- MemoryForgetTool tests ---


class TestMemoryForgetTool:
    """Tests for the memory_forget tool."""

    @pytest.mark.asyncio
    async def test_forget_by_id_success(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.forget_memory = AsyncMock(return_value=True)

        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(memory_id="mem-123", _user_id="user-1")

        assert result.success is True
        data = json.loads(result.output)
        assert data["deleted_count"] == 1
        assert "mem-123" in data["deleted_ids"]
        mm.forget_memory.assert_awaited_once_with("mem-123")

    @pytest.mark.asyncio
    async def test_forget_by_id_not_found(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.forget_memory = AsyncMock(return_value=False)

        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(memory_id="nonexistent", _user_id="user-1")

        assert result.success is True  # not an error, just 0 deleted
        data = json.loads(result.output)
        assert data["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_forget_by_query_high_similarity(self):
        """Should delete memories with score >= 0.7."""
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(
            return_value=[
                _make_memory(id="m1", score=0.9),
                _make_memory(id="m2", score=0.75),
                _make_memory(id="m3", score=0.5),  # below threshold
            ]
        )
        mm.forget_memory = AsyncMock(return_value=True)

        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(query="warm lights", _user_id="user-1")

        assert result.success is True
        data = json.loads(result.output)
        assert data["deleted_count"] == 2
        assert "m1" in data["deleted_ids"]
        assert "m2" in data["deleted_ids"]
        assert "m3" not in data["deleted_ids"]

    @pytest.mark.asyncio
    async def test_forget_by_query_no_matches(self):
        """All results below 0.7 similarity."""
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(
            return_value=[
                _make_memory(id="m1", score=0.5),
                _make_memory(id="m2", score=0.3),
            ]
        )

        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(query="something unrelated", _user_id="user-1")

        data = json.loads(result.output)
        assert data["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_forget_no_params(self):
        hass = _make_hass(user_id="user-1")
        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(_user_id="user-1")

        assert result.success is False
        assert result.error == "missing_parameter"

    @pytest.mark.asyncio
    async def test_forget_no_memory_manager(self):
        hass = _make_hass(with_rag=False)
        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(memory_id="mem-1", _user_id="user-1")

        assert result.success is False
        assert result.error == "memory_not_initialized"

    @pytest.mark.asyncio
    async def test_forget_exception(self):
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.forget_memory = AsyncMock(side_effect=RuntimeError("Delete failed"))

        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(memory_id="mem-1", _user_id="user-1")

        assert result.success is False
        assert "Delete failed" in result.error

    @pytest.mark.asyncio
    async def test_forget_by_query_partial_delete_failure(self):
        """Some deletes succeed, some fail."""
        hass = _make_hass(user_id="user-1")
        mm = hass.data[DOMAIN]["rag_manager"].memory_manager
        mm.search_memories = AsyncMock(
            return_value=[
                _make_memory(id="m1", score=0.9),
                _make_memory(id="m2", score=0.8),
            ]
        )
        mm.forget_memory = AsyncMock(side_effect=[True, False])

        tool = MemoryForgetTool(hass=hass)
        result = await tool.execute(query="test", _user_id="user-1")

        data = json.loads(result.output)
        assert data["deleted_count"] == 1
        assert "m1" in data["deleted_ids"]
        assert "m2" not in data["deleted_ids"]


# --- Tool registration tests ---


class TestMemoryToolRegistration:
    """Verify memory tools are properly registered."""

    def test_tools_registered(self):
        from custom_components.homeclaw.tools.base import ToolRegistry

        tool_ids = [t["id"] for t in ToolRegistry.list_tools(enabled_only=False)]
        assert "memory_store" in tool_ids
        assert "memory_recall" in tool_ids
        assert "memory_forget" in tool_ids

    def test_store_tool_metadata(self):
        tool = MemoryStoreTool()
        assert tool.id == "memory_store"
        param_names = [p.name for p in tool.parameters]
        assert "text" in param_names
        assert "category" in param_names
        assert "importance" in param_names

    def test_recall_tool_metadata(self):
        tool = MemoryRecallTool()
        assert tool.id == "memory_recall"
        param_names = [p.name for p in tool.parameters]
        assert "query" in param_names
        assert "limit" in param_names

    def test_forget_tool_metadata(self):
        tool = MemoryForgetTool()
        assert tool.id == "memory_forget"
        param_names = [p.name for p in tool.parameters]
        assert "memory_id" in param_names
        assert "query" in param_names
