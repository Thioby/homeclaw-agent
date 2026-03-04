"""Tests for token estimation and context budget utilities."""

from __future__ import annotations

from custom_components.homeclaw.core.token_estimator import (
    CHARS_PER_TOKEN,
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_OUTPUT_RESERVE,
    DEFAULT_SAFETY_MARGIN,
    MESSAGE_OVERHEAD_TOKENS,
    TOOL_SCHEMA_RESERVE_TOKENS,
    compute_context_budget,
    estimate_messages_tokens,
    estimate_tokens,
)


class TestEstimateTokens:
    """Tests for estimate_tokens()."""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        # "hello" = 5 chars -> 5 // 4 = 1 token
        assert estimate_tokens("hello") == 1

    def test_known_length(self):
        text = "a" * 400  # exactly 400 chars -> 100 tokens
        assert estimate_tokens(text) == 400 // CHARS_PER_TOKEN

    def test_multilingual(self):
        # Polish text: "Cześć, jak się masz?" = 20 chars -> 5 tokens
        text = "Cześć, jak się masz?"
        assert estimate_tokens(text) == len(text) // CHARS_PER_TOKEN

    def test_long_text(self):
        text = "x" * 10_000
        # 10_000 chars / CHARS_PER_TOKEN (3) = 3333 tokens
        assert estimate_tokens(text) == 10_000 // CHARS_PER_TOKEN


class TestEstimateMessagesTokens:
    """Tests for estimate_messages_tokens()."""

    def test_empty_list(self):
        assert estimate_messages_tokens([]) == 0

    def test_single_message(self):
        msgs = [{"role": "user", "content": "a" * 400}]
        expected = 400 // CHARS_PER_TOKEN + MESSAGE_OVERHEAD_TOKENS
        assert estimate_messages_tokens(msgs) == expected

    def test_multiple_messages(self):
        msgs = [
            {"role": "system", "content": "a" * 200},
            {"role": "user", "content": "b" * 100},
            {"role": "assistant", "content": "c" * 300},
        ]
        expected = sum(
            len(m["content"]) // CHARS_PER_TOKEN + MESSAGE_OVERHEAD_TOKENS for m in msgs
        )
        assert estimate_messages_tokens(msgs) == expected

    def test_missing_content_key(self):
        msgs = [{"role": "user"}]  # no 'content'
        assert estimate_messages_tokens(msgs) == MESSAGE_OVERHEAD_TOKENS


class TestComputeContextBudget:
    """Tests for compute_context_budget()."""

    def test_default_values(self):
        budget = compute_context_budget()
        assert budget["total"] == DEFAULT_CONTEXT_WINDOW
        assert budget["output_reserve"] == DEFAULT_OUTPUT_RESERVE
        safety = int(DEFAULT_CONTEXT_WINDOW * DEFAULT_SAFETY_MARGIN)
        assert budget["safety_buffer"] == safety
        # Formula: available = window - output_reserve - safety - TOOL_SCHEMA_RESERVE_TOKENS
        expected_available = (
            DEFAULT_CONTEXT_WINDOW
            - DEFAULT_OUTPUT_RESERVE
            - safety
            - TOOL_SCHEMA_RESERVE_TOKENS
        )
        assert budget["available_for_input"] == expected_available

    def test_custom_window(self):
        budget = compute_context_budget(context_window=200_000)
        assert budget["total"] == 200_000
        assert budget["available_for_input"] > 0

    def test_small_window_no_negative(self):
        # Very small window that would go negative
        budget = compute_context_budget(
            context_window=100, output_reserve=80, safety_margin=0.5
        )
        assert budget["available_for_input"] >= 0

    def test_zero_safety_margin(self):
        budget = compute_context_budget(context_window=100_000, safety_margin=0.0)
        assert budget["safety_buffer"] == 0
        # Formula: available = window - output_reserve - safety (0) - TOOL_SCHEMA_RESERVE_TOKENS
        assert budget["available_for_input"] == (
            100_000 - DEFAULT_OUTPUT_RESERVE - TOOL_SCHEMA_RESERVE_TOKENS
        )

    def test_budget_sums_correctly(self):
        budget = compute_context_budget(context_window=128_000)
        # available + output_reserve + safety_buffer should approximately equal total
        # (available may be 0 if window is too small, so use <=)
        assert (
            budget["available_for_input"]
            + budget["output_reserve"]
            + budget["safety_buffer"]
            <= budget["total"]
        )
