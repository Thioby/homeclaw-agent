"""Tests for anthropic_oauth.cch — billing header computation."""
from __future__ import annotations

import hashlib

from custom_components.homeclaw.providers.anthropic_oauth.cch import (
    build_billing_header_value,
    compute_cch,
    compute_version_suffix,
    extract_first_user_message_text,
)


class TestExtractFirstUserMessageText:
    def test_empty_list_returns_empty(self):
        assert extract_first_user_message_text([]) == ""

    def test_no_user_returns_empty(self):
        msgs = [{"role": "assistant", "content": "hi"}]
        assert extract_first_user_message_text(msgs) == ""

    def test_string_content(self):
        msgs = [{"role": "user", "content": "hello world"}]
        assert extract_first_user_message_text(msgs) == "hello world"

    def test_list_content_first_text_block(self):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {}},
                    {"type": "text", "text": "describe this"},
                ],
            }
        ]
        assert extract_first_user_message_text(msgs) == "describe this"

    def test_list_content_no_text_block_returns_empty(self):
        msgs = [{"role": "user", "content": [{"type": "image", "source": {}}]}]
        assert extract_first_user_message_text(msgs) == ""

    def test_skips_assistant_to_first_user(self):
        msgs = [
            {"role": "assistant", "content": "previous"},
            {"role": "user", "content": "find me"},
        ]
        assert extract_first_user_message_text(msgs) == "find me"

    def test_first_user_with_empty_text_returns_empty(self):
        msgs = [{"role": "user", "content": ""}]
        assert extract_first_user_message_text(msgs) == ""


class TestComputeCCH:
    def test_known_value_hello(self):
        expected = hashlib.sha256(b"hello").hexdigest()[:5]
        assert compute_cch("hello") == expected

    def test_empty_string_is_deterministic(self):
        expected = hashlib.sha256(b"").hexdigest()[:5]
        assert compute_cch("") == expected

    def test_returns_5_hex_chars(self):
        result = compute_cch("any text here")
        assert len(result) == 5
        assert all(c in "0123456789abcdef" for c in result)


class TestComputeVersionSuffix:
    def test_known_value(self):
        # text="abcdefghijklmnopqrstuvwxyz", version="2.1.87"
        # chars = text[4]+text[7]+text[20] = "e" + "h" + "u" = "ehu"
        # payload = "59cf53e54c78" + "ehu" + "2.1.87"
        text = "abcdefghijklmnopqrstuvwxyz"
        payload = "59cf53e54c78ehu2.1.87"
        expected = hashlib.sha256(payload.encode()).hexdigest()[:3]
        assert compute_version_suffix(text, version="2.1.87") == expected

    def test_short_text_uses_zero_fallback(self):
        # text length 3 -> positions 4, 7, 20 all out of range -> "000"
        payload = "59cf53e54c780002.1.87"
        expected = hashlib.sha256(payload.encode()).hexdigest()[:3]
        assert compute_version_suffix("abc", version="2.1.87") == expected

    def test_returns_3_hex_chars(self):
        result = compute_version_suffix("hello world this is a test", version="2.1.87")
        assert len(result) == 3
        assert all(c in "0123456789abcdef" for c in result)


class TestBuildBillingHeaderValue:
    def test_format_with_user_message(self):
        msgs = [{"role": "user", "content": "Hello there, this is a long enough message"}]
        header = build_billing_header_value(msgs)
        assert header.startswith("x-anthropic-billing-header: ")
        assert "cc_version=2.1.87." in header
        assert "cc_entrypoint=sdk-cli;" in header
        assert "cch=" in header
        assert header.endswith(";")

    def test_format_includes_correct_cch(self):
        text = "Hello there, this is a long enough message"
        msgs = [{"role": "user", "content": text}]
        header = build_billing_header_value(msgs)
        expected_cch = hashlib.sha256(text.encode()).hexdigest()[:5]
        assert f"cch={expected_cch};" in header

    def test_custom_version_and_entrypoint(self):
        msgs = [{"role": "user", "content": "hi"}]
        header = build_billing_header_value(msgs, version="9.9.9", entrypoint="custom")
        assert "cc_version=9.9.9." in header
        assert "cc_entrypoint=custom;" in header

    def test_empty_messages_still_produces_deterministic_header(self):
        header = build_billing_header_value([])
        assert header.startswith("x-anthropic-billing-header: ")
        assert "cc_entrypoint=sdk-cli" in header
