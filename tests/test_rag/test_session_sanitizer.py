"""Tests for the session sanitizer (LLM-based state removal)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.homeclaw.rag.session_sanitizer import (
    sanitize_session_messages,
    _format_conversation,
    _parse_sanitized_response,
    SESSION_SANITIZE_PROMPT,
    MAX_INPUT_CHARS,
)


# --- _format_conversation tests ---


class TestFormatConversation:
    """Tests for the conversation formatting helper."""

    def test_basic_formatting(self):
        """Formats user/assistant messages correctly."""
        messages = [
            {"role": "user", "content": "Turn on the light"},
            {"role": "assistant", "content": "Done, light is on."},
        ]
        result = _format_conversation(messages)
        assert result == "User: Turn on the light\nAssistant: Done, light is on."

    def test_empty_messages(self):
        """Empty list returns empty string."""
        assert _format_conversation([]) == ""

    def test_skips_empty_content(self):
        """Messages with empty content are skipped."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "World"},
        ]
        result = _format_conversation(messages)
        assert result == "User: Hello\nUser: World"

    def test_strips_whitespace(self):
        """Content whitespace is stripped."""
        messages = [{"role": "user", "content": "  hello  "}]
        result = _format_conversation(messages)
        assert result == "User: hello"

    def test_unicode_content(self):
        """Polish/unicode content is preserved."""
        messages = [
            {"role": "user", "content": "Włącz światło w sypialni"},
            {"role": "assistant", "content": "Włączyłem światło."},
        ]
        result = _format_conversation(messages)
        assert "Włącz światło w sypialni" in result
        assert "Włączyłem światło." in result


# --- _parse_sanitized_response tests ---


class TestParseSanitizedResponse:
    """Tests for parsing LLM sanitized output back into messages."""

    def test_basic_parsing(self):
        """Parses simple User:/Assistant: format."""
        response = "User: Turn on the light\nAssistant: Done."
        result = _parse_sanitized_response(response)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Turn on the light"}
        assert result[1] == {"role": "assistant", "content": "Done."}

    def test_multiline_content(self):
        """Handles multi-line message content."""
        response = (
            "User: I need help with two things:\n"
            "1. Turn on lights\n"
            "2. Set temperature\n"
            "Assistant: I'll help with both."
        )
        result = _parse_sanitized_response(response)
        assert len(result) == 2
        assert "1. Turn on lights" in result[0]["content"]
        assert "2. Set temperature" in result[0]["content"]

    def test_empty_response(self):
        """Empty response returns empty list."""
        assert _parse_sanitized_response("") == []
        assert _parse_sanitized_response("   ") == []

    def test_multiple_turns(self):
        """Handles multi-turn conversations."""
        response = (
            "User: What lights do I have?\n"
            "Assistant: [provided status information]\n"
            "User: Turn on bedroom lamp\n"
            "Assistant: I turned on the bedroom lamp."
        )
        result = _parse_sanitized_response(response)
        assert len(result) == 4
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"
        assert result[3]["role"] == "assistant"

    def test_no_role_markers(self):
        """Text without role markers returns empty list."""
        result = _parse_sanitized_response("Just some random text without markers")
        assert result == []

    def test_preserves_unicode(self):
        """Polish/unicode content is preserved in parsing."""
        response = (
            "User: Włącz światło w sypialni\nAssistant: Włączyłem światło w sypialni."
        )
        result = _parse_sanitized_response(response)
        assert len(result) == 2
        assert "Włącz światło" in result[0]["content"]
        assert "Włączyłem światło" in result[1]["content"]


# --- sanitize_session_messages tests ---


@pytest.mark.asyncio
class TestSanitizeSessionMessages:
    """Tests for the main sanitization function."""

    @pytest.fixture
    def mock_provider(self):
        """Return a mock AI provider."""
        provider = MagicMock()
        provider.get_response = AsyncMock()
        return provider

    async def test_too_few_messages_returns_as_is(self, mock_provider):
        """Sessions with < 2 messages are returned unchanged."""
        messages = [{"role": "user", "content": "Hello"}]
        result = await sanitize_session_messages(messages, mock_provider)
        assert result == messages
        mock_provider.get_response.assert_not_called()

    async def test_filters_non_user_assistant(self, mock_provider):
        """Only user/assistant messages are processed."""
        messages = [
            {"role": "system", "content": "You are a helper"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        mock_provider.get_response.return_value = "User: Hello\nAssistant: Hi there"
        result = await sanitize_session_messages(messages, mock_provider)
        # System message should be filtered out
        assert all(m["role"] in ("user", "assistant") for m in result)

    async def test_calls_llm_with_correct_prompt(self, mock_provider):
        """LLM is called with the sanitization system prompt."""
        messages = [
            {"role": "user", "content": "What temperature?"},
            {"role": "assistant", "content": "22.5 C in living room"},
        ]
        mock_provider.get_response.return_value = (
            "User: What temperature?\nAssistant: [provided status information]"
        )

        await sanitize_session_messages(messages, mock_provider)

        call_args = mock_provider.get_response.call_args
        llm_messages = call_args[0][0]
        assert llm_messages[0]["role"] == "system"
        assert "ephemeral" in llm_messages[0]["content"].lower()
        assert llm_messages[1]["role"] == "user"

    async def test_passes_model_override(self, mock_provider):
        """Model parameter is passed through to provider."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = "User: Hello\nAssistant: Hi"

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
        mock_provider.get_response.return_value = "User: Hello\nAssistant: Hi"

        await sanitize_session_messages(messages, mock_provider, model=None)

        call_kwargs = mock_provider.get_response.call_args[1]
        assert "model" not in call_kwargs

    async def test_returns_originals_on_empty_response(self, mock_provider):
        """Falls back to originals when LLM returns empty."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = ""

        result = await sanitize_session_messages(messages, mock_provider)
        # Should return the filtered originals
        assert len(result) == 2
        assert result[0]["content"] == "Hello"

    async def test_returns_originals_on_parse_failure(self, mock_provider):
        """Falls back to originals when LLM output can't be parsed."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        # Response without any User:/Assistant: markers
        mock_provider.get_response.return_value = "Some gibberish without markers"

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 2
        assert result[0]["content"] == "Hello"

    async def test_returns_originals_on_exception(self, mock_provider):
        """Falls back to originals when LLM call raises."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.side_effect = RuntimeError("API down")

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 2
        assert result[0]["content"] == "Hello"

    async def test_truncates_long_conversations(self, mock_provider):
        """Very long conversations are truncated before sending to LLM."""
        # Create messages that exceed MAX_INPUT_CHARS
        long_content = "x" * (MAX_INPUT_CHARS + 1000)
        messages = [
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": "OK"},
        ]
        mock_provider.get_response.return_value = "User: [long message]\nAssistant: OK"

        await sanitize_session_messages(messages, mock_provider)

        # LLM should still be called (conversation truncated, not skipped)
        mock_provider.get_response.assert_called_once()

    async def test_successful_sanitization(self, mock_provider):
        """Full successful sanitization flow."""
        messages = [
            {"role": "user", "content": "Jaka jest temperatura w salonie?"},
            {
                "role": "assistant",
                "content": "Temperatura w salonie wynosi 22.5°C "
                "według sensor.salon_temperature.",
            },
            {"role": "user", "content": "Ustaw termostat na 23 stopnie"},
            {
                "role": "assistant",
                "content": "Ustawiłem termostat climate.salon na 23°C.",
            },
        ]

        # LLM returns sanitized version
        mock_provider.get_response.return_value = (
            "User: Jaka jest temperatura w salonie?\n"
            "Assistant: [provided status information]\n"
            "User: Ustaw termostat na 23 stopnie\n"
            "Assistant: Ustawiłem termostat climate.salon na 23°C."
        )

        result = await sanitize_session_messages(messages, mock_provider)
        assert len(result) == 4

        # Status report should be replaced
        assert "[provided status information]" in result[1]["content"]

        # Action confirmation should be preserved
        assert "Ustawiłem termostat" in result[3]["content"]

    async def test_skips_empty_content_messages(self, mock_provider):
        """Messages with empty/whitespace content are excluded."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "   "},
            {"role": "user", "content": "World"},
            {"role": "assistant", "content": "Hi"},
        ]
        mock_provider.get_response.return_value = (
            "User: Hello\nUser: World\nAssistant: Hi"
        )

        result = await sanitize_session_messages(messages, mock_provider)
        # Empty assistant message should have been filtered before LLM call
        assert mock_provider.get_response.called


# --- SESSION_SANITIZE_PROMPT tests ---


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
