"""Tests for IdentityManager — orchestration, prompt building, and onboarding."""

from __future__ import annotations

import pytest

from custom_components.homeclaw.memory.identity_manager import IdentityManager
from custom_components.homeclaw.memory.identity_store import AgentIdentity
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
def identity_manager(sqlite_store):
    """Create an IdentityManager backed by real SQLite."""
    import asyncio

    manager = IdentityManager(store=sqlite_store)
    asyncio.get_event_loop().run_until_complete(manager.async_initialize())
    return manager


class TestIdentityManagerInit:
    """Tests for identity manager initialization."""

    @pytest.mark.asyncio
    async def test_initialization_creates_store(self, sqlite_store) -> None:
        """Test that async_initialize creates identity store."""
        manager = IdentityManager(store=sqlite_store)
        await manager.async_initialize()

        assert manager._initialized is True
        assert manager._identity_store is not None

    @pytest.mark.asyncio
    async def test_idempotent_init(self, sqlite_store) -> None:
        """Test that multiple initializations don't fail."""
        manager = IdentityManager(store=sqlite_store)
        await manager.async_initialize()
        await manager.async_initialize()  # Should not raise
        assert manager._initialized is True


class TestGetIdentity:
    """Tests for retrieving identity."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_identity(self, identity_manager) -> None:
        """Test getting identity for new user returns None."""
        identity = await identity_manager.get_identity("user1")
        assert identity is None

    @pytest.mark.asyncio
    async def test_get_existing_identity(self, identity_manager) -> None:
        """Test getting saved identity."""
        await identity_manager.save_identity(
            "user1",
            agent_name="Luna",
            agent_personality="Warm",
        )

        identity = await identity_manager.get_identity("user1")
        assert identity is not None
        assert identity.agent_name == "Luna"
        assert identity.agent_personality == "Warm"


class TestSaveIdentity:
    """Tests for saving/updating identity."""

    @pytest.mark.asyncio
    async def test_save_new_identity_partial_fields(self, identity_manager) -> None:
        """Test saving identity with only some fields."""
        await identity_manager.save_identity(
            "user1",
            agent_name="Jarvis",
        )

        identity = await identity_manager.get_identity("user1")
        assert identity.agent_name == "Jarvis"
        assert identity.agent_personality is None

    @pytest.mark.asyncio
    async def test_save_updates_existing_identity(self, identity_manager) -> None:
        """Test that save_identity updates existing fields."""
        # First save
        await identity_manager.save_identity(
            "user1",
            agent_name="Luna",
        )

        # Update with more fields
        await identity_manager.save_identity(
            "user1",
            agent_personality="Warm and playful",
            agent_emoji="🌙",
        )

        identity = await identity_manager.get_identity("user1")
        assert identity.agent_name == "Luna"
        assert identity.agent_personality == "Warm and playful"
        assert identity.agent_emoji == "🌙"

    @pytest.mark.asyncio
    async def test_save_multiple_fields(self, identity_manager) -> None:
        """Test saving multiple fields at once."""
        await identity_manager.save_identity(
            "user1",
            agent_name="Luna",
            agent_personality="Friendly",
            agent_emoji="🌙",
            user_name="Artur",
            language="pl",
        )

        identity = await identity_manager.get_identity("user1")
        assert identity.agent_name == "Luna"
        assert identity.agent_personality == "Friendly"
        assert identity.agent_emoji == "🌙"
        assert identity.user_name == "Artur"
        assert identity.language == "pl"


class TestIsOnboarded:
    """Tests for checking onboarding status."""

    @pytest.mark.asyncio
    async def test_new_user_not_onboarded(self, identity_manager) -> None:
        """Test that new user is not onboarded."""
        is_onboarded = await identity_manager.is_onboarded("user1")
        assert is_onboarded is False

    @pytest.mark.asyncio
    async def test_user_with_identity_not_onboarded_by_default(
        self, identity_manager
    ) -> None:
        """Test that user with identity but no explicit onboarding flag is not onboarded."""
        await identity_manager.save_identity("user1", agent_name="Luna")

        is_onboarded = await identity_manager.is_onboarded("user1")
        assert is_onboarded is False


class TestCompleteOnboarding:
    """Tests for completing onboarding."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_sets_flag(self, identity_manager) -> None:
        """Test that complete_onboarding sets the flag."""
        await identity_manager.save_identity("user1", agent_name="Luna")
        await identity_manager.complete_onboarding("user1")

        is_onboarded = await identity_manager.is_onboarded("user1")
        assert is_onboarded is True

    @pytest.mark.asyncio
    async def test_complete_onboarding_creates_identity_if_missing(
        self, identity_manager
    ) -> None:
        """Test that complete_onboarding works even if no identity exists yet."""
        await identity_manager.complete_onboarding("user1")

        identity = await identity_manager.get_identity("user1")
        assert identity is not None
        assert identity.onboarding_completed is True


class TestBuildSystemPrompt:
    """Tests for system prompt construction."""

    def test_build_system_prompt_no_identity(self, identity_manager) -> None:
        """Test that build_system_prompt returns ONBOARDING_PROMPT for new users."""
        from custom_components.homeclaw.prompts import ONBOARDING_PROMPT

        prompt = identity_manager.build_system_prompt(None)
        assert prompt == ONBOARDING_PROMPT

    def test_build_system_prompt_not_onboarded(self, identity_manager) -> None:
        """Test that build_system_prompt returns ONBOARDING_PROMPT if not onboarded."""
        from custom_components.homeclaw.prompts import ONBOARDING_PROMPT

        identity = AgentIdentity(user_id="user1", agent_name="Luna", onboarding_completed=False)
        prompt = identity_manager.build_system_prompt(identity)
        assert prompt == ONBOARDING_PROMPT

    def test_build_system_prompt_with_onboarded_identity(self, identity_manager) -> None:
        """Test that build_system_prompt includes identity context and base prompt."""
        from custom_components.homeclaw.prompts import BASE_SYSTEM_PROMPT

        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            agent_personality="Warm and friendly",
            agent_emoji="🌙",
            user_name="Artur",
            onboarding_completed=True,
        )
        prompt = identity_manager.build_system_prompt(identity)

        # Should include identity context
        assert "<agent-identity>" in prompt
        assert "Your name is Luna" in prompt
        assert "Warm and friendly" in prompt
        assert "🌙" in prompt
        assert "Artur" in prompt
        assert "</agent-identity>" in prompt

        # Should include base system prompt
        assert BASE_SYSTEM_PROMPT in prompt

    def test_build_system_prompt_with_partial_identity(self, identity_manager) -> None:
        """Test prompt building with only some identity fields set."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            onboarding_completed=True,
        )
        prompt = identity_manager.build_system_prompt(identity)

        assert "Your name is Luna" in prompt
        # Shouldn't include fields that are None
        assert "personality" not in prompt.lower() or "Your personality:" not in prompt


class TestBuildIdentityContext:
    """Tests for identity context formatting."""

    def test_build_identity_context_full(self, identity_manager) -> None:
        """Test building identity context with all fields."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            agent_personality="Warm and slightly playful",
            agent_emoji="🌙",
            user_name="Artur",
            language="pl",
            user_info="Lives in Warsaw, likes automation",
        )
        context = identity_manager.build_identity_context(identity)

        assert context.startswith("<agent-identity>")
        assert context.endswith("</agent-identity>")
        assert "Your name is Luna" in context
        assert "Your personality: Warm and slightly playful" in context
        assert "Your emoji: 🌙" in context
        assert "You are speaking with Artur" in context
        assert "Preferred language: pl" in context
        assert "About the user: Lives in Warsaw, likes automation" in context

    def test_build_identity_context_minimal(self, identity_manager) -> None:
        """Test building identity context with minimal fields."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
        )
        context = identity_manager.build_identity_context(identity)

        assert context.startswith("<agent-identity>")
        assert context.endswith("</agent-identity>")
        assert "Your name is Luna" in context

    def test_build_identity_context_skips_auto_language(self, identity_manager) -> None:
        """Test that 'auto' language is not included in context."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            language="auto",
        )
        context = identity_manager.build_identity_context(identity)

        assert "Preferred language" not in context

    def test_build_identity_context_includes_explicit_language(
        self, identity_manager
    ) -> None:
        """Test that explicit language is included."""
        identity = AgentIdentity(
            user_id="user1",
            agent_name="Luna",
            language="pl",
        )
        context = identity_manager.build_identity_context(identity)

        assert "Preferred language: pl" in context
