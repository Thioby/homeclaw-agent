"""Tests for IdentityStore — SQLite storage for agent identity and user profiles."""

from __future__ import annotations

import pytest

from custom_components.homeclaw.memory.identity_store import (
    AgentIdentity,
    IdentityStore,
)
from custom_components.homeclaw.rag.sqlite_store import SqliteStore


@pytest.fixture
def sqlite_store(tmp_path):
    """Create a real SqliteStore for integration tests."""
    import asyncio

    store = SqliteStore(persist_directory=str(tmp_path))
    asyncio.get_event_loop().run_until_complete(store.async_initialize())
    yield store
    if store._conn:
        store._conn.close()


@pytest.fixture
def identity_store(sqlite_store):
    """Create an IdentityStore backed by real SQLite."""
    import asyncio

    istore = IdentityStore(store=sqlite_store)
    asyncio.get_event_loop().run_until_complete(istore.async_initialize())
    return istore


class TestIdentityStoreInit:
    """Tests for identity store initialization."""

    @pytest.mark.asyncio
    async def test_creates_table(self, sqlite_store) -> None:
        """Test that async_initialize creates agent_identity table."""
        istore = IdentityStore(store=sqlite_store)
        await istore.async_initialize()

        cursor = sqlite_store._conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_identity'"
        )
        assert cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_idempotent_init(self, sqlite_store) -> None:
        """Test that multiple initializations don't fail."""
        istore = IdentityStore(store=sqlite_store)
        await istore.async_initialize()
        await istore.async_initialize()  # Should not raise
        assert istore._table_created is True


class TestGetIdentity:
    """Tests for retrieving identity."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_identity_returns_none(self, identity_store) -> None:
        """Test that get_identity returns None for new user."""
        identity = await identity_store.get_identity("user1")
        assert identity is None

    @pytest.mark.asyncio
    async def test_get_existing_identity(self, identity_store) -> None:
        """Test that get_identity returns saved identity."""
        # Save identity
        original = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            agent_personality="Warm and friendly",
            agent_emoji="🌙",
            user_name="Artur",
            language="pl",
            onboarding_completed=True,
        )
        await identity_store.save_identity(original)

        # Retrieve it
        retrieved = await identity_store.get_identity("user1")
        assert retrieved is not None
        assert retrieved.user_id == "user1"
        assert retrieved.agent_name == "Luna"
        assert retrieved.agent_personality == "Warm and friendly"
        assert retrieved.agent_emoji == "🌙"
        assert retrieved.user_name == "Artur"
        assert retrieved.language == "pl"
        assert retrieved.onboarding_completed is True


class TestSaveIdentity:
    """Tests for saving/updating identity."""

    @pytest.mark.asyncio
    async def test_save_new_identity(self, identity_store) -> None:
        """Test saving a new identity."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Jarvis",
            agent_emoji="🤖",
        )
        await identity_store.save_identity(identity)

        # Verify saved
        retrieved = await identity_store.get_identity("user1")
        assert retrieved is not None
        assert retrieved.agent_name == "Jarvis"
        assert retrieved.agent_emoji == "🤖"

    @pytest.mark.asyncio
    async def test_save_sets_timestamps(self, identity_store) -> None:
        """Test that save_identity sets created_at and updated_at."""
        identity = AgentIdentity(user_id="user1", agent_name="Luna")
        await identity_store.save_identity(identity)

        retrieved = await identity_store.get_identity("user1")
        assert retrieved.created_at > 0
        assert retrieved.updated_at > 0

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, identity_store) -> None:
        """Test that saving twice updates the identity (upsert behavior)."""
        # First save
        identity1 = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            agent_personality="Friendly",
        )
        await identity_store.save_identity(identity1)

        # Second save (update)
        identity2 = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            agent_personality="Warm and slightly playful",
            agent_emoji="🌙",
        )
        await identity_store.save_identity(identity2)

        # Should have updated, not created duplicate
        retrieved = await identity_store.get_identity("user1")
        assert retrieved.agent_name == "Luna"
        assert retrieved.agent_personality == "Warm and slightly playful"
        assert retrieved.agent_emoji == "🌙"

    @pytest.mark.asyncio
    async def test_save_partial_fields(self, identity_store) -> None:
        """Test saving identity with only some fields set."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            # Other fields remain None/default
        )
        await identity_store.save_identity(identity)

        retrieved = await identity_store.get_identity("user1")
        assert retrieved.agent_name == "Luna"
        assert retrieved.agent_personality is None
        assert retrieved.agent_emoji is None
        assert retrieved.language == "auto"

    @pytest.mark.asyncio
    async def test_save_with_user_info(self, identity_store) -> None:
        """Test saving identity with user_name and user_info."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            user_name="Artur",
            user_info="Lives in Warsaw, likes automation",
        )
        await identity_store.save_identity(identity)

        retrieved = await identity_store.get_identity("user1")
        assert retrieved.user_name == "Artur"
        assert retrieved.user_info == "Lives in Warsaw, likes automation"


class TestIsOnboarded:
    """Tests for checking onboarding status."""

    @pytest.mark.asyncio
    async def test_new_user_not_onboarded(self, identity_store) -> None:
        """Test that new user is not onboarded."""
        is_onboarded = await identity_store.is_onboarded("user1")
        assert is_onboarded is False

    @pytest.mark.asyncio
    async def test_user_with_incomplete_onboarding(self, identity_store) -> None:
        """Test that user with identity but onboarding_completed=False is not onboarded."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            onboarding_completed=False,
        )
        await identity_store.save_identity(identity)

        is_onboarded = await identity_store.is_onboarded("user1")
        assert is_onboarded is False

    @pytest.mark.asyncio
    async def test_user_with_completed_onboarding(self, identity_store) -> None:
        """Test that user with onboarding_completed=True is onboarded."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            onboarding_completed=True,
        )
        await identity_store.save_identity(identity)

        is_onboarded = await identity_store.is_onboarded("user1")
        assert is_onboarded is True


class TestMultiUser:
    """Tests for multi-user isolation."""

    @pytest.mark.asyncio
    async def test_identities_are_per_user(self, identity_store) -> None:
        """Test that each user has their own identity."""
        identity1 = AgentIdentity(user_id="user1", agent_name="Luna")
        identity2 = AgentIdentity(user_id="user2", agent_name="Jarvis")

        await identity_store.save_identity(identity1)
        await identity_store.save_identity(identity2)

        retrieved1 = await identity_store.get_identity("user1")
        retrieved2 = await identity_store.get_identity("user2")

        assert retrieved1.agent_name == "Luna"
        assert retrieved2.agent_name == "Jarvis"

    @pytest.mark.asyncio
    async def test_onboarding_status_per_user(self, identity_store) -> None:
        """Test that onboarding status is tracked per user."""
        identity1 = AgentIdentity(user_id="user1", onboarding_completed=True)
        identity2 = AgentIdentity(user_id="user2", onboarding_completed=False)

        await identity_store.save_identity(identity1)
        await identity_store.save_identity(identity2)

        assert await identity_store.is_onboarded("user1") is True
        assert await identity_store.is_onboarded("user2") is False


class TestLanguageField:
    """Tests for language field."""

    @pytest.mark.asyncio
    async def test_default_language_is_auto(self, identity_store) -> None:
        """Test that language defaults to 'auto'."""
        identity = AgentIdentity(user_id="user1", agent_name="Luna")
        await identity_store.save_identity(identity)

        retrieved = await identity_store.get_identity("user1")
        assert retrieved.language == "auto"

    @pytest.mark.asyncio
    async def test_explicit_language(self, identity_store) -> None:
        """Test setting explicit language."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            language="pl",
        )
        await identity_store.save_identity(identity)

        retrieved = await identity_store.get_identity("user1")
        assert retrieved.language == "pl"
