"""Tests for context window compaction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.core.compaction import (
    COMPACTION_TRIGGER_RATIO,
    MIN_RECENT_MESSAGES,
    truncation_fallback,
    compact_messages,
)
from custom_components.homeclaw.core.token_estimator import (
    estimate_messages_tokens,
)


def _make_messages(n: int, content_len: int = 100) -> list[dict]:
    """Build a list of alternating user/assistant messages."""
    msgs = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": f"Message {i}: " + "x" * content_len})
    return msgs


def _make_full_conversation(n_history: int, content_len: int = 100) -> list[dict]:
    """Build [system] + history + [user query]."""
    msgs = [{"role": "system", "content": "You are a helpful assistant. " + "s" * 200}]
    msgs.extend(_make_messages(n_history, content_len))
    msgs.append({"role": "user", "content": "What is the weather?"})
    return msgs


class TestCompactMessagesPassthrough:
    """When messages fit in budget, they should pass through unchanged."""

    @pytest.mark.asyncio
    async def test_small_history_passes_through(self):
        """Short conversation should not trigger compaction."""
        messages = _make_full_conversation(4, content_len=50)
        provider = AsyncMock()

        result = await compact_messages(
            messages,
            context_window=128_000,
            provider=provider,
        )

        assert result == messages
        provider.get_response.assert_not_called()


class TestCompactMessagesTriggered:
    """When messages exceed budget, compaction should kick in."""

    @pytest.mark.asyncio
    async def test_large_history_triggers_compaction(self):
        """Large conversation should trigger AI summarization."""
        # Build a conversation that exceeds a tiny context window
        messages = _make_full_conversation(30, content_len=200)
        estimated = estimate_messages_tokens(messages)

        # Use a small context window so compaction triggers
        small_window = int(estimated * 0.5)

        provider = AsyncMock()
        provider.get_response.return_value = (
            "Summary of the conversation: discussed lights and automations."
        )

        result = await compact_messages(
            messages,
            context_window=small_window,
            provider=provider,
        )

        # Should have called summarization
        provider.get_response.assert_called_once()

        # Result should be shorter
        assert len(result) < len(messages)

        # Should still have system message, summary, and recent messages
        assert result[0]["role"] == "system"
        # Last message should be the user query
        assert result[-1]["role"] == "user"
        assert result[-1]["content"] == "What is the weather?"

    @pytest.mark.asyncio
    async def test_memory_flush_called_before_compaction(self):
        """Memory flush should be called with old messages before they are discarded."""
        messages = _make_full_conversation(30, content_len=200)
        estimated = estimate_messages_tokens(messages)
        small_window = int(estimated * 0.5)

        provider = AsyncMock()
        provider.get_response.return_value = "Summary: discussed home automation."

        flush_fn = AsyncMock(return_value=3)

        result = await compact_messages(
            messages,
            context_window=small_window,
            provider=provider,
            memory_flush_fn=flush_fn,
            user_id="test_user",
            session_id="test_session",
        )

        # Flush should have been called
        flush_fn.assert_called_once()
        call_args = flush_fn.call_args
        # First arg is the old messages
        assert len(call_args[0][0]) > 0
        # Second arg is user_id
        assert call_args[0][1] == "test_user"
        # Third arg is session_id
        assert call_args[0][2] == "test_session"

    @pytest.mark.asyncio
    async def test_summary_injected_as_context(self):
        """The summary should appear as a system message in the result."""
        # Use more messages to ensure compaction triggers
        messages = _make_full_conversation(30, content_len=200)
        estimated = estimate_messages_tokens(messages)
        # Need a window where:
        # 1. estimated > available * 0.8 (triggers compaction)
        # 2. compacted result < available (fits after compaction)
        # compute_context_budget: available = window * 0.8 - 8192 - 5000 (TOOL_SCHEMA_RESERVE_TOKENS)
        # Set available = estimated * 1.1 so original exceeds 80% but compacted fits.
        target_available = int(estimated * 1.1)
        # Reverse: available = window * 0.8 - 8192 - 5000 => window = (available + 8192 + 5000) / 0.8
        small_window = int((target_available + 8192 + 5000) / 0.8)

        summary = "Previously: user asked about lights, assistant turned them on."
        provider = AsyncMock()
        provider.get_response.return_value = summary

        result = await compact_messages(
            messages,
            context_window=small_window,
            provider=provider,
        )

        # Find the summary message
        summary_found = False
        for msg in result:
            if "[Previous conversation summary]" in msg.get("content", ""):
                summary_found = True
                assert summary in msg["content"]
                break
        assert summary_found, "Summary not found in compacted messages"


class TestCompactMessagesFallback:
    """When AI summarization fails, truncation fallback should apply."""

    @pytest.mark.asyncio
    async def test_fallback_on_summarization_failure(self):
        """If summarization returns empty, fallback to truncation."""
        messages = _make_full_conversation(20, content_len=200)
        estimated = estimate_messages_tokens(messages)
        small_window = int(estimated * 0.5)

        provider = AsyncMock()
        provider.get_response.return_value = ""  # Empty summary

        result = await compact_messages(
            messages,
            context_window=small_window,
            provider=provider,
        )

        # Should still return something valid
        assert len(result) > 0
        assert len(result) < len(messages)

    @pytest.mark.asyncio
    async def test_fallback_on_provider_exception(self):
        """If provider throws, fallback to truncation."""
        messages = _make_full_conversation(20, content_len=200)
        estimated = estimate_messages_tokens(messages)
        small_window = int(estimated * 0.5)

        provider = AsyncMock()
        provider.get_response.side_effect = Exception("API Error")

        result = await compact_messages(
            messages,
            context_window=small_window,
            provider=provider,
        )

        assert len(result) > 0
        assert len(result) < len(messages)


class TestTruncationFallback:
    """Tests for the truncation fallback function."""

    def test_keeps_system_and_user_query(self):
        messages = _make_full_conversation(10, content_len=100)
        result = truncation_fallback(messages, budget_tokens=500)

        assert result[0]["role"] == "system"
        assert result[-1]["role"] == "user"

    def test_keeps_most_recent(self):
        """Should keep messages from the end (most recent), not the beginning."""
        messages = _make_full_conversation(20, content_len=100)
        # Use a budget small enough that truncation must drop some messages
        # 20 history msgs * ~110 chars = ~2200 chars = ~550 tokens, plus system ~230 chars
        result = truncation_fallback(messages, budget_tokens=300)

        # Result should be shorter than input but include the last user message
        assert len(result) < len(messages)
        assert result[-1] == messages[-1]

    def test_empty_messages(self):
        result = truncation_fallback([], budget_tokens=1000)
        assert result == []

    def test_very_small_budget(self):
        """With tiny budget, should still keep system + user query at minimum."""
        messages = _make_full_conversation(10, content_len=100)
        result = truncation_fallback(messages, budget_tokens=50)

        # At minimum: system + user query
        assert len(result) >= 2
        assert result[0]["role"] == "system"
        assert result[-1]["role"] == "user"


class TestShortHistorySkipsCompaction:
    """History shorter than MIN_RECENT_MESSAGES should skip compaction."""

    @pytest.mark.asyncio
    async def test_short_history_uses_truncation(self):
        """With few messages that still exceed budget, use truncation not summarization."""
        # 4 messages + system + query = 6 total, history = 4 < MIN_RECENT_MESSAGES
        messages = _make_full_conversation(4, content_len=2000)
        estimated = estimate_messages_tokens(messages)
        tiny_window = int(estimated * 0.3)

        provider = AsyncMock()

        result = await compact_messages(
            messages,
            context_window=tiny_window,
            provider=provider,
        )

        # Should NOT call summarization (history too short)
        provider.get_response.assert_not_called()

        # Should still return something
        assert len(result) > 0
