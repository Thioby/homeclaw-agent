"""Tests for the session sanitizer (LLM-based state removal)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from custom_components.homeclaw.rag.session_sanitizer import (
    sanitize_session_messages,
    SESSION_SANITIZE_PROMPT,
    MAX_INPUT_CHARS,
    MAX_ROUND_CHARS,
)


@pytest.mark.asyncio
class TestSanitizeSessionMessages:
    """Tests for the main sanitization function."""

    @pytest.fixture
    def mock_provider(self):
        """Return a mock AI provider."""
        provider = MagicMock()
        provider.get_response = AsyncMock()
        return provider

    async def test_too_few_messages_returns_empty(self, mock_provider):
        """Sessions with < 1 round are returned empty."""
        messages = [{"role": "user", "content": "Hello"}]
        result = await sanitize_session_messages(messages, mock_provider)
        assert result == []
        mock_provider.get_response.assert_not_called()

    async def test_filters_non_user_assistant(self, mock_provider):
        """Only user/assistant messages are processed into rounds."""
        messages = [
            {"role": "system", "content": "You are a helper"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        # Valid JSON mock
        mock_provider.get_response.return_value = json.dumps(
            [
                {
                    "user_message": "Hello",
                    "assistant_message": "Hi there",
                    "user_facts": "",
                }
            ]
        )

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 1
        assert result[0]["user_message"] == "Hello"

    async def test_calls_llm_with_correct_prompt(self, mock_provider):
        """LLM is called with the sanitization system prompt."""
        messages = [
            {"role": "user", "content": "What temperature?"},
            {"role": "assistant", "content": "22.5 C in living room"},
        ]
        mock_provider.get_response.return_value = json.dumps(
            [
                {
                    "user_message": "What temperature?",
                    "assistant_message": "[provided status information]",
                    "user_facts": "",
                }
            ]
        )

        await sanitize_session_messages(messages, mock_provider)

        call_args = mock_provider.get_response.call_args
        llm_messages = call_args[0][0]
        assert llm_messages[0]["role"] == "system"
        assert "ephemeral" in llm_messages[0]["content"].lower()
        assert "facts" in llm_messages[0]["content"].lower()
        assert llm_messages[1]["role"] == "user"

    async def test_passes_model_override(self, mock_provider):
        """Model parameter is passed through to provider."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = "[]"

        await sanitize_session_messages(
            messages, mock_provider, model="gemini-2.0-flash"
        )

        call_kwargs = mock_provider.get_response.call_args[1]
        assert call_kwargs["model"] == "gemini-2.0-flash"

    async def test_no_model_override(self, mock_provider):
        """No model kwarg when model is None."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = "[]"

        await sanitize_session_messages(messages, mock_provider, model=None)

        call_kwargs = mock_provider.get_response.call_args[1]
        assert "model" not in call_kwargs

    async def test_returns_fallback_on_empty_response(self, mock_provider):
        """Falls back to original rounds when LLM returns empty."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = ""

        result = await sanitize_session_messages(messages, mock_provider)
        # Should return the filtered originals with empty facts
        assert len(result) == 1
        assert result[0]["user_message"] == "Hello"
        assert result[0]["user_facts"] == ""

    async def test_returns_fallback_on_parse_failure(self, mock_provider):
        """Falls back to original rounds when LLM output isn't valid JSON list."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = '{"error": "not a list"}'

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 1
        assert result[0]["user_message"] == "Hello"

    async def test_returns_fallback_on_exception(self, mock_provider):
        """Falls back to original rounds when LLM call raises."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.side_effect = RuntimeError("API down")

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 1
        assert result[0]["user_message"] == "Hello"

    async def test_truncates_long_conversations(self, mock_provider):
        """Very long conversations are truncated by dropping oldest rounds."""
        rounds_count = 60
        messages = []
        for i in range(rounds_count):
            messages.append({"role": "user", "content": f"msg {i}"})
            messages.append({"role": "assistant", "content": "ok"})

        mock_provider.get_response.return_value = "[]"

        await sanitize_session_messages(messages, mock_provider)

        call_args = mock_provider.get_response.call_args
        llm_messages = call_args[0][0]
        # It drops everything down to ~50 rounds
        assert "msg 0" not in llm_messages[1]["content"]

    async def test_successful_sanitization(self, mock_provider):
        """Full successful sanitization flow with JSON parsing."""
        messages = [
            {
                "role": "user",
                "content": "Jaka jest temperatura w salonie?",
                "timestamp": "t1",
            },
            {
                "role": "assistant",
                "content": "Temperatura w salonie wynosi 22.5°C.",
                "timestamp": "t2",
            },
            {
                "role": "user",
                "content": "Ustaw termostat na 23 stopnie",
                "timestamp": "t3",
            },
            {
                "role": "assistant",
                "content": "Ustawiłem termostat climate.salon na 23°C.",
                "timestamp": "t4",
            },
        ]

        mock_provider.get_response.return_value = json.dumps(
            [
                {
                    "user_message": "Jaka jest temperatura w salonie?",
                    "assistant_message": "[provided status information]",
                    "user_facts": "",
                },
                {
                    "user_message": "Ustaw termostat na 23 stopnie",
                    "assistant_message": "Ustawiłem termostat climate.salon na 23°C.",
                    "user_facts": "Lubi ciepło w salonie (23°C)",
                },
            ]
        )

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 2

        # Status report should be replaced
        assert "[provided status information]" in result[0]["assistant_message"]
        # Fact should be extracted
        assert "Lubi ciepło" in result[1]["user_facts"]
        # Timestamps preserved from user message
        assert result[0]["timestamp"] == "t1"
        assert result[1]["timestamp"] == "t3"

    async def test_fallback_truncates_oversized_rounds(self, mock_provider):
        """Fallback truncates oversized rounds to MAX_ROUND_CHARS."""
        huge_user = "u" * 3000
        huge_asst = "a" * 3000
        messages = [
            {"role": "user", "content": huge_user},
            {"role": "assistant", "content": huge_asst},
        ]
        # Force fallback via LLM exception
        mock_provider.get_response.side_effect = RuntimeError("fail")

        result = await sanitize_session_messages(messages, mock_provider)

        assert len(result) == 1
        total = len(result[0]["user_message"]) + len(result[0]["assistant_message"])
        assert total <= MAX_ROUND_CHARS


class TestSanitizePrompt:
    """Tests for the sanitization prompt content."""

    def test_prompt_mentions_keep_rules(self):
        """Prompt contains KEEP section with preferences and decisions."""
        assert "KEEP" in SESSION_SANITIZE_PROMPT
        assert "preferences" in SESSION_SANITIZE_PROMPT.lower()
        assert "decisions" in SESSION_SANITIZE_PROMPT.lower()

    def test_prompt_mentions_remove_rules(self):
        """Prompt contains REMOVE section with sensor readings and states."""
        assert "REMOVE" in SESSION_SANITIZE_PROMPT
        assert "sensor" in SESSION_SANITIZE_PROMPT.lower()
        assert "temperature" in SESSION_SANITIZE_PROMPT.lower()

    def test_prompt_mentions_language_preservation(self):
        """Prompt requires same-language output."""
        assert "LANGUAGE" in SESSION_SANITIZE_PROMPT
        assert "NEVER translate" in SESSION_SANITIZE_PROMPT
