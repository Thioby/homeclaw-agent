"""Tests for identity tools (identity_set).

Tests cover:
- IdentitySetTool: set all fields, partial update, mark onboarding complete, missing manager, error
- Helper functions: _get_identity_manager, _get_current_user_id
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.homeclaw.const import DOMAIN
from custom_components.homeclaw.memory.identity_store import AgentIdentity
from custom_components.homeclaw.tools.identity import (
    IdentitySetTool,
    _get_current_user_id,
    _get_identity_manager,
)


# --- Fixtures ---


def _make_hass(*, with_rag=True, with_identity=True, user_id=None):
    """Create a mock hass object with optional RAG/identity setup."""
    hass = MagicMock()
    hass.data = {}

    if with_rag:
        rag_manager = MagicMock()
        rag_manager.is_initialized = True

        if with_identity:
            identity_manager = AsyncMock()
            rag_manager.identity_manager = identity_manager
        else:
            rag_manager.identity_manager = None

        hass.data[DOMAIN] = {"rag_manager": rag_manager}
    else:
        hass.data[DOMAIN] = {}

    if user_id:
        hass.data[DOMAIN]["_current_user_id"] = user_id

    return hass


def _make_identity(
    user_id="user-1",
    agent_name="Luna",
    agent_personality="Warm",
    agent_emoji="🌙",
    user_name="Artur",
    onboarding_completed=False,
):
    """Create an AgentIdentity instance."""
    import time

    now = time.time()
    return AgentIdentity(
        user_id=user_id,
        agent_name=agent_name,
        agent_personality=agent_personality,
        agent_emoji=agent_emoji,
        user_name=user_name,
        onboarding_completed=onboarding_completed,
        created_at=now,
        updated_at=now,
    )


# --- _get_identity_manager tests ---


class TestGetIdentityManager:
    """Tests for the _get_identity_manager helper."""

    def test_returns_identity_manager(self):
        hass = _make_hass(with_rag=True, with_identity=True)
        result = _get_identity_manager(hass)
        assert result is not None
        assert result is hass.data[DOMAIN]["rag_manager"].identity_manager

    def test_returns_none_when_no_hass(self):
        assert _get_identity_manager(None) is None

    def test_returns_none_when_no_domain(self):
        hass = MagicMock()
        hass.data = {}
        assert _get_identity_manager(hass) is None

    def test_returns_none_when_no_rag_manager(self):
        hass = _make_hass(with_rag=False)
        assert _get_identity_manager(hass) is None

    def test_returns_none_when_rag_not_initialized(self):
        hass = _make_hass(with_rag=True, with_identity=True)
        hass.data[DOMAIN]["rag_manager"].is_initialized = False
        assert _get_identity_manager(hass) is None

    def test_returns_none_when_no_identity_manager_attr(self):
        hass = _make_hass(with_rag=True, with_identity=False)
        # identity_manager is None
        assert _get_identity_manager(hass) is None


# --- _get_current_user_id tests ---


class TestGetCurrentUserId:
    """Tests for the _get_current_user_id helper."""

    def test_returns_user_id(self):
        hass = _make_hass(user_id="user-42")
        assert _get_current_user_id(hass) == "user-42"

    def test_returns_default_when_no_hass(self):
        assert _get_current_user_id(None) == "default"

    def test_returns_default_when_no_domain(self):
        hass = MagicMock()
        hass.data = {}
        assert _get_current_user_id(hass) == "default"

    def test_returns_default_when_key_missing(self):
        hass = _make_hass()
        # No _current_user_id set
        assert _get_current_user_id(hass) == "default"


# --- IdentitySetTool tests ---


class TestIdentitySetTool:
    """Tests for the identity_set tool."""

    @pytest.mark.asyncio
    async def test_set_all_fields(self):
        """Test setting all identity fields at once."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        identity = _make_identity(user_id="user-1", onboarding_completed=False)
        im.get_identity = AsyncMock(return_value=identity)
        im.save_identity = AsyncMock()
        im.complete_onboarding = AsyncMock()

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(
            agent_name="Luna",
            agent_personality="Warm and friendly",
            agent_emoji="🌙",
            user_name="Artur",
            user_info="Lives in Warsaw",
            language="pl",
        )

        assert result.success is True
        output = json.loads(result.output)
        assert output["success"] is True
        assert "agent_name" in output["updated_fields"]
        assert "agent_personality" in output["updated_fields"]
        assert "agent_emoji" in output["updated_fields"]
        assert "user_name" in output["updated_fields"]
        assert "user_info" in output["updated_fields"]
        assert "language" in output["updated_fields"]

        # Verify save_identity was called
        im.save_identity.assert_called_once()
        call_kwargs = im.save_identity.call_args[1]
        assert call_kwargs["agent_name"] == "Luna"
        assert call_kwargs["agent_personality"] == "Warm and friendly"
        assert call_kwargs["language"] == "pl"

    @pytest.mark.asyncio
    async def test_set_partial_fields(self):
        """Test setting only some fields."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        identity = _make_identity(user_id="user-1")
        im.get_identity = AsyncMock(return_value=identity)
        im.save_identity = AsyncMock()

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(agent_name="Luna")

        assert result.success is True
        output = json.loads(result.output)
        assert output["updated_fields"] == ["agent_name"]

        im.save_identity.assert_called_once()
        call_kwargs = im.save_identity.call_args[1]
        assert call_kwargs["agent_name"] == "Luna"
        # Should not include other fields
        assert "agent_personality" not in call_kwargs

    @pytest.mark.asyncio
    async def test_mark_onboarding_complete(self):
        """Test marking onboarding as complete."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        identity = _make_identity(user_id="user-1", onboarding_completed=True)
        im.get_identity = AsyncMock(return_value=identity)
        im.save_identity = AsyncMock()
        im.complete_onboarding = AsyncMock()

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(
            agent_name="Luna", mark_onboarding_complete=True
        )

        assert result.success is True
        output = json.loads(result.output)
        assert output["onboarding_completed"] is True

        # Verify complete_onboarding was called
        im.complete_onboarding.assert_called_once_with("user-1")

    @pytest.mark.asyncio
    async def test_does_not_mark_complete_by_default(self):
        """Test that onboarding is not marked complete unless explicitly requested."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        identity = _make_identity(user_id="user-1", onboarding_completed=False)
        im.get_identity = AsyncMock(return_value=identity)
        im.save_identity = AsyncMock()
        im.complete_onboarding = AsyncMock()

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(agent_name="Luna")

        assert result.success is True

        # complete_onboarding should NOT be called
        im.complete_onboarding.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_identity_manager(self):
        """Test error when identity manager is not available."""
        hass = _make_hass(with_rag=True, with_identity=False)

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(agent_name="Luna")

        assert result.success is False
        assert "not available" in result.output
        assert result.error == "identity_not_initialized"

    @pytest.mark.asyncio
    async def test_no_rag_manager(self):
        """Test error when RAG manager doesn't exist."""
        hass = _make_hass(with_rag=False)

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(agent_name="Luna")

        assert result.success is False
        assert result.error == "identity_not_initialized"

    @pytest.mark.asyncio
    async def test_save_identity_raises_exception(self):
        """Test error handling when save_identity fails."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        im.save_identity = AsyncMock(side_effect=Exception("Database error"))

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(agent_name="Luna")

        assert result.success is False
        assert "Failed to set identity" in result.output
        assert "Database error" in result.error

    @pytest.mark.asyncio
    async def test_no_fields_provided(self):
        """Test that tool works even if no fields are provided (e.g., just marking complete)."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        identity = _make_identity(user_id="user-1", onboarding_completed=True)
        im.get_identity = AsyncMock(return_value=identity)
        im.save_identity = AsyncMock()
        im.complete_onboarding = AsyncMock()

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(mark_onboarding_complete=True)

        assert result.success is True
        output = json.loads(result.output)
        assert output["updated_fields"] == []
        assert output["onboarding_completed"] is True

        # save_identity should not be called if no fields
        im.save_identity.assert_not_called()
        # But complete_onboarding should be called
        im.complete_onboarding.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_current_identity_state(self):
        """Test that tool returns the current identity state after update."""
        hass = _make_hass(user_id="user-1")
        im = hass.data[DOMAIN]["rag_manager"].identity_manager

        identity = _make_identity(
            user_id="user-1",
            agent_name="Luna",
            onboarding_completed=False,
        )
        im.get_identity = AsyncMock(return_value=identity)
        im.save_identity = AsyncMock()

        tool = IdentitySetTool()
        tool.hass = hass

        result = await tool.execute(agent_personality="Warm")

        assert result.success is True
        output = json.loads(result.output)
        assert output["agent_name"] == "Luna"
        assert output["onboarding_completed"] is False
