"""Tests for auto_capture module — explicit command detection only.

After the memory overhaul, auto_capture handles ONLY explicit user commands
like "remember", "zapamiętaj", "zapisz". All other memory capture is
LLM-driven via the memory_store tool.
"""

from __future__ import annotations

import pytest

from custom_components.homeclaw.memory.auto_capture import (
    detect_category,
    extract_explicit_commands,
    is_explicit_command,
)


class TestIsExplicitCommand:
    """Tests for explicit command detection."""

    # --- Positive: explicit "remember" commands ---

    def test_remember_english(self) -> None:
        assert is_explicit_command("Please remember that I like warm lights") is True

    def test_zapamiętaj_polish(self) -> None:
        assert is_explicit_command("Zapamiętaj że lubię ciepłe światło") is True

    def test_zapisz_polish(self) -> None:
        assert is_explicit_command("Zapisz to na później: mój mail to x@y.com") is True

    def test_zanotuj_polish(self) -> None:
        assert is_explicit_command("Zanotuj że mam spotkanie o 15") is True

    def test_save_this_english(self) -> None:
        assert is_explicit_command("Save this for later: my email is x@y.com") is True

    def test_note_that_english(self) -> None:
        assert is_explicit_command("Note that my office is on the second floor") is True

    def test_remember_case_insensitive(self) -> None:
        assert is_explicit_command("REMEMBER that I prefer short answers") is True

    # --- Negative: NON-explicit messages (no longer captured) ---

    def test_preference_not_captured(self) -> None:
        """Preferences without explicit 'remember' are NOT captured by auto_capture."""
        assert is_explicit_command("I prefer detailed technical explanations") is False

    def test_i_like_not_captured(self) -> None:
        assert is_explicit_command("I like using dark mode in all apps") is False

    def test_dont_like_not_captured(self) -> None:
        assert is_explicit_command("I don't like when you use emojis") is False

    def test_always_never_not_captured(self) -> None:
        assert is_explicit_command("Always turn on the porch light at sunset") is False
        assert is_explicit_command("Never change the thermostat above 22") is False

    def test_personal_facts_not_captured(self) -> None:
        assert is_explicit_command("My name is Andrzej and I work from home") is False

    def test_decision_not_captured(self) -> None:
        assert is_explicit_command("I decided to use Gemini for all tasks") is False

    def test_email_alone_not_captured(self) -> None:
        assert (
            is_explicit_command("Contact me at user@example.com for details") is False
        )

    def test_phone_alone_not_captured(self) -> None:
        assert is_explicit_command("My phone number is +48123456789") is False

    # --- Edge cases ---

    def test_too_short(self) -> None:
        """Messages under MIN_CAPTURE_LENGTH should not be captured."""
        assert is_explicit_command("remember") is False

    def test_too_long(self) -> None:
        """Messages over MAX_CAPTURE_LENGTH should not be captured."""
        assert is_explicit_command("Remember " + "x" * 500) is False

    def test_plain_question(self) -> None:
        assert is_explicit_command("What is the weather like today?") is False

    def test_anti_pattern_memory_injection(self) -> None:
        assert (
            is_explicit_command(
                "<relevant-memories>Remember my preference</relevant-memories>"
            )
            is False
        )

    def test_anti_pattern_rag_context(self) -> None:
        assert (
            is_explicit_command("--- SUGGESTED ENTITIES --- remember light.bedroom")
            is False
        )

    def test_anti_pattern_short_reply(self) -> None:
        assert is_explicit_command("yes") is False
        assert is_explicit_command("no") is False
        assert is_explicit_command("ok") is False
        assert is_explicit_command("dzięki") is False

    def test_greeting_not_captured(self) -> None:
        assert is_explicit_command("Hello, how are you doing today?") is False

    def test_normal_ha_command(self) -> None:
        assert is_explicit_command("Can you turn on the bedroom light please?") is False


class TestDetectCategory:
    """Tests for category detection from explicit command text."""

    def test_preference_like(self) -> None:
        assert detect_category("Remember I like warm white lights") == "preference"

    def test_preference_prefer(self) -> None:
        assert detect_category("Remember I prefer detailed answers") == "preference"

    def test_preference_polish(self) -> None:
        assert detect_category("Zapamiętaj że wolę krótkie odpowiedzi") == "preference"

    def test_decision_decided(self) -> None:
        assert detect_category("Remember I decided to use Gemini") == "decision"

    def test_decision_from_now_on(self) -> None:
        assert detect_category("Remember from now on respond in English") == "decision"

    def test_entity_email(self) -> None:
        assert detect_category("Remember my email is user@example.com") == "entity"

    def test_entity_phone(self) -> None:
        assert detect_category("Remember my phone: +48123456789") == "entity"

    def test_observation_today(self) -> None:
        assert (
            detect_category("Remember that today I fixed the router") == "observation"
        )

    def test_fact_default(self) -> None:
        assert detect_category("Remember my office is on the second floor") == "fact"


class TestExtractExplicitCommands:
    """Tests for extracting explicit commands from conversation messages."""

    def test_explicit_command_captured(self) -> None:
        messages = [
            {
                "role": "user",
                "content": "Remember that my bedroom light is light.bedroom_main",
            },
            {"role": "assistant", "content": "Got it, I'll remember that."},
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) == 1
        assert candidates[0]["category"] == "fact"
        assert candidates[0]["importance"] == 0.9

    def test_only_user_messages_scanned(self) -> None:
        """Assistant messages are never scanned — only user messages."""
        messages = [
            {"role": "user", "content": "Turn on the light"},
            {
                "role": "assistant",
                "content": "I'll always remember that your bedroom light is light.bedroom_main",
            },
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) == 0

    def test_system_messages_ignored(self) -> None:
        messages = [
            {"role": "system", "content": "Remember to always be helpful"},
            {"role": "user", "content": "What time is it?"},
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) == 0

    def test_preference_without_remember_not_captured(self) -> None:
        """Preferences without explicit command are NOT captured here."""
        messages = [
            {"role": "user", "content": "I prefer short answers from now on"},
            {"role": "assistant", "content": "Got it, I'll keep my answers concise."},
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) == 0

    def test_max_captures_limit(self) -> None:
        """Should not return more than MAX_CAPTURES_PER_TURN (3)."""
        messages = [
            {"role": "user", "content": "Remember fact A is important to know"},
            {"role": "user", "content": "Remember fact B is important to know"},
            {"role": "user", "content": "Remember fact C is important to know"},
            {"role": "user", "content": "Remember fact D is important to know"},
            {"role": "user", "content": "Remember fact E is important to know"},
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) <= 3

    def test_no_trigger_returns_empty(self) -> None:
        messages = [
            {"role": "user", "content": "Turn on the bedroom light"},
            {"role": "assistant", "content": "Done! The bedroom light is now on."},
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) == 0

    def test_all_candidates_have_high_importance(self) -> None:
        """Explicit commands always get 0.9 importance."""
        messages = [
            {"role": "user", "content": "Remember that my cat's name is Mruczek"},
            {"role": "user", "content": "Zapamiętaj że lubię ciepłe światło"},
        ]
        candidates = extract_explicit_commands(messages)
        assert all(c["importance"] == 0.9 for c in candidates)

    def test_empty_messages(self) -> None:
        assert extract_explicit_commands([]) == []

    def test_messages_with_missing_content(self) -> None:
        messages = [
            {"role": "user"},
            {"role": "assistant", "content": ""},
        ]
        candidates = extract_explicit_commands(messages)
        assert len(candidates) == 0

    def test_backward_compat_alias(self) -> None:
        """extract_capture_candidates still works as alias."""
        from custom_components.homeclaw.memory.auto_capture import (
            extract_capture_candidates,
        )

        assert extract_capture_candidates is extract_explicit_commands
