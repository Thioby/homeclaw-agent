"""Tests for anthropic_oauth.transform."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from custom_components.homeclaw.providers.anthropic_oauth.constants import (
    CLAUDE_CODE_IDENTITY,
    REQUIRED_BETAS,
    USER_AGENT,
)


class TestPrefixToolName:
    def test_simple_name(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prefix_tool_name

        assert prefix_tool_name("memory") == "mcp__homeclaw__memory"

    def test_snake_case_preserved(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prefix_tool_name

        assert prefix_tool_name("ha_native") == "mcp__homeclaw__ha_native"
        assert prefix_tool_name("shell_execute") == "mcp__homeclaw__shell_execute"

    def test_idempotent_when_already_prefixed(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prefix_tool_name

        already = "mcp__homeclaw__memory"
        assert prefix_tool_name(already) == already


class TestUnprefixToolName:
    def test_strips_prefix(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import unprefix_tool_name

        assert unprefix_tool_name("mcp__homeclaw__memory") == "memory"

    def test_idempotent_when_unprefixed(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import unprefix_tool_name

        assert unprefix_tool_name("memory") == "memory"

    def test_preserves_snake_case(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import unprefix_tool_name

        assert unprefix_tool_name("mcp__homeclaw__ha_native") == "ha_native"


class TestPrefixToolNamesInPayload:
    def test_prefixes_tools_array(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )

        payload = {"tools": [{"name": "memory", "description": "x"}]}
        prefix_tool_names_in_payload(payload)
        assert payload["tools"][0]["name"] == "mcp__homeclaw__memory"

    def test_prefixes_tool_use_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )

        payload = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "id": "1", "name": "memory", "input": {}}],
                }
            ]
        }
        prefix_tool_names_in_payload(payload)
        assert payload["messages"][0]["content"][0]["name"] == "mcp__homeclaw__memory"

    def test_leaves_tool_result_blocks_alone(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": "1", "content": "ok"}],
                }
            ]
        }
        prefix_tool_names_in_payload(payload)
        # tool_result has no `name` field — nothing to do
        assert payload["messages"][0]["content"][0] == {"type": "tool_result", "tool_use_id": "1", "content": "ok"}

    def test_no_tools_no_messages_does_nothing(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            prefix_tool_names_in_payload,
        )

        payload = {"model": "x"}
        prefix_tool_names_in_payload(payload)
        assert payload == {"model": "x"}


class TestUnprefixToolNamesInEvent:
    def test_unprefixes_content_block_start(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            unprefix_tool_names_in_event,
        )

        event = {
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "id": "1", "name": "mcp__homeclaw__memory"},
        }
        unprefix_tool_names_in_event(event)
        assert event["content_block"]["name"] == "memory"

    def test_no_op_for_text_delta_event(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            unprefix_tool_names_in_event,
        )

        event = {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}}
        unprefix_tool_names_in_event(event)
        assert event == {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hi"}}


class TestUnprefixToolNamesInResponse:
    def test_unprefixes_tool_use_in_content(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import (
            unprefix_tool_names_in_response,
        )

        data = {
            "content": [
                {"type": "text", "text": "let me check"},
                {"type": "tool_use", "id": "1", "name": "mcp__homeclaw__memory", "input": {}},
            ]
        }
        unprefix_tool_names_in_response(data)
        assert data["content"][1]["name"] == "memory"
        assert data["content"][0] == {"type": "text", "text": "let me check"}


class TestSanitizeSystemText:
    def test_drops_opencode_identity_paragraph(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        text = "Para1\n\nYou are OpenCode, an agent.\n\nPara3"
        result = sanitize_system_text(text)
        assert "OpenCode" not in result
        assert "Para1" in result
        assert "Para3" in result

    def test_drops_paragraph_with_anomalyco_anchor(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        text = "Keep me\n\nFeedback at github.com/anomalyco/opencode/issues\n\nKeep me too"
        result = sanitize_system_text(text)
        assert "github.com/anomalyco/opencode" not in result
        assert "Keep me" in result
        assert "Keep me too" in result

    def test_drops_paragraph_with_opencode_docs_anchor(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        text = "Useful\n\nDocs: opencode.ai/docs/agents\n\nMore"
        result = sanitize_system_text(text)
        assert "opencode.ai/docs" not in result

    def test_critical_phrase_v175_replacement(self):
        """v1.7.5 critical phrase rewrite — must trigger to bypass classifier."""
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        text = "Here is some useful information about the environment you are running in:\nLinux x86_64"
        result = sanitize_system_text(text)
        assert "Environment context you are running in:" in result
        assert "useful information about the environment" not in result

    def test_inline_opencode_replacement(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        text = "Be honest if OpenCode honestly does not know."
        result = sanitize_system_text(text)
        assert "if the assistant honestly" in result
        assert "OpenCode" not in result

    def test_empty_input_returns_empty(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        assert sanitize_system_text("") == ""

    def test_only_whitespace_returns_empty(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import sanitize_system_text

        assert sanitize_system_text("   \n\n   ") == ""


class TestPrependClaudeCodeIdentity:
    def test_none_returns_only_identity_block(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        result = prepend_claude_code_identity(None)
        assert result == [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]

    def test_string_with_content(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        result = prepend_claude_code_identity("You are a helpful assistant.")
        assert len(result) == 2
        assert result[0]["text"] == CLAUDE_CODE_IDENTITY
        assert result[1]["text"] == "You are a helpful assistant."

    def test_empty_string_collapses_to_identity_only(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        result = prepend_claude_code_identity("")
        assert result == [{"type": "text", "text": CLAUDE_CODE_IDENTITY}]

    def test_list_of_text_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        system = [
            {"type": "text", "text": "First block."},
            {"type": "text", "text": "Second block."},
        ]
        result = prepend_claude_code_identity(system)
        assert len(result) == 3
        assert result[0]["text"] == CLAUDE_CODE_IDENTITY
        assert result[1]["text"] == "First block."
        assert result[2]["text"] == "Second block."

    def test_idempotent_when_first_block_is_identity(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        system = [
            {"type": "text", "text": CLAUDE_CODE_IDENTITY},
            {"type": "text", "text": "Existing."},
        ]
        result = prepend_claude_code_identity(system)
        assert len(result) == 2
        assert result[0]["text"] == CLAUDE_CODE_IDENTITY

    def test_preserves_extra_fields_on_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        system = [{"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}]
        result = prepend_claude_code_identity(system)
        assert result[1]["cache_control"] == {"type": "ephemeral"}

    def test_sanitizes_content_in_blocks(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import prepend_claude_code_identity

        system = [{"type": "text", "text": "Here is some useful information about the environment you are running in:"}]
        result = prepend_claude_code_identity(system)
        assert "Environment context" in result[1]["text"]


class TestMergeBetaHeaders:
    def test_none_returns_required_only(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers

        result = merge_beta_headers(None)
        assert result == ",".join(REQUIRED_BETAS)

    def test_existing_appended(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers

        result = merge_beta_headers("custom-beta-1,foo")
        parts = result.split(",")
        for required in REQUIRED_BETAS:
            assert required in parts
        assert "custom-beta-1" in parts
        assert "foo" in parts

    def test_dedupes_required_collision(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers

        result = merge_beta_headers("oauth-2025-04-20,extra")
        parts = result.split(",")
        assert parts.count("oauth-2025-04-20") == 1
        assert "extra" in parts

    def test_empty_string_treated_as_none(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import merge_beta_headers

        result = merge_beta_headers("")
        assert result == ",".join(REQUIRED_BETAS)


class TestBuildOauthHeaders:
    def test_required_headers_set(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers

        h = build_oauth_headers("ACCESS")
        assert h["authorization"] == "Bearer ACCESS"
        assert h["content-type"] == "application/json"
        assert h["anthropic-version"] == "2023-06-01"
        assert h["user-agent"] == USER_AGENT
        for required in REQUIRED_BETAS:
            assert required in h["anthropic-beta"]

    def test_drops_x_api_key_from_extra(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers

        h = build_oauth_headers("ACCESS", extra={"x-api-key": "leaked"})
        assert "x-api-key" not in h

    def test_extra_headers_preserved(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers

        h = build_oauth_headers("ACCESS", extra={"x-custom": "v"})
        assert h["x-custom"] == "v"

    def test_extra_betas_merged(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import build_oauth_headers

        h = build_oauth_headers("ACCESS", extra={"anthropic-beta": "extra-beta"})
        assert "extra-beta" in h["anthropic-beta"]
        for required in REQUIRED_BETAS:
            assert required in h["anthropic-beta"]


class TestRewriteUrl:
    def test_v1_messages_gets_beta_query(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url

        result = rewrite_url("https://api.anthropic.com/v1/messages")
        assert "beta=true" in result

    def test_existing_beta_query_not_doubled(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url

        result = rewrite_url("https://api.anthropic.com/v1/messages?beta=true")
        # Should still have exactly one beta param
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(result).query)
        assert qs["beta"] == ["true"]

    def test_other_path_not_modified_when_no_base_url(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            result = rewrite_url("https://api.anthropic.com/v1/models")
            assert "beta" not in result

    def test_base_url_override(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import rewrite_url

        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "http://localhost:8080"}):
            result = rewrite_url("https://api.anthropic.com/v1/messages")
            assert result.startswith("http://localhost:8080/v1/messages")
            assert "beta=true" in result


class TestResolveBaseUrl:
    def test_unset_returns_none(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            assert _resolve_base_url() is None

    def test_valid_https_returned(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url

        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://proxy.example.com"}):
            assert _resolve_base_url() == "https://proxy.example.com"

    def test_userinfo_rejected(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url

        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://user:pass@proxy.com"}):
            assert _resolve_base_url() is None

    def test_non_http_scheme_rejected(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import _resolve_base_url

        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "ftp://proxy.com"}):
            assert _resolve_base_url() is None


class TestIsTlsInsecure:
    def test_no_base_url_means_secure(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import is_tls_insecure

        with patch.dict(os.environ, {"ANTHROPIC_INSECURE": "1"}, clear=False):
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            assert is_tls_insecure() is False

    def test_with_base_url_and_flag(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import is_tls_insecure

        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_BASE_URL": "http://localhost",
                "ANTHROPIC_INSECURE": "true",
            },
        ):
            assert is_tls_insecure() is True

    def test_with_base_url_no_flag(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import is_tls_insecure

        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_BASE_URL": "http://localhost",
            },
            clear=False,
        ):
            os.environ.pop("ANTHROPIC_INSECURE", None)
            assert is_tls_insecure() is False


class TestTransformRequestPayload:
    def test_user_message_produces_billing_block(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload

        payload = {
            "messages": [{"role": "user", "content": "hello"}],
            "system": "You are helpful.",
        }
        result = transform_request_payload(payload)
        assert isinstance(result["system"], list)
        assert result["system"][0]["text"].startswith("x-anthropic-billing-header:")
        assert result["system"][1]["text"] == CLAUDE_CODE_IDENTITY
        assert result["system"][2]["text"] == "You are helpful."

    def test_no_user_message_no_billing(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload

        payload = {
            "messages": [{"role": "assistant", "content": "hi"}],
            "system": "S",
        }
        result = transform_request_payload(payload)
        assert result["system"][0]["text"] == CLAUDE_CODE_IDENTITY  # no billing prepended
        assert result["system"][1]["text"] == "S"

    def test_tools_prefixed(self):
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload

        payload = {
            "messages": [{"role": "user", "content": "x"}],
            "tools": [{"name": "memory", "description": "d"}],
        }
        result = transform_request_payload(payload)
        assert result["tools"][0]["name"] == "mcp__homeclaw__memory"

    def test_billing_header_uses_first_user_text(self):
        """Billing computed BEFORE prefixing — first user message text matters."""
        from custom_components.homeclaw.providers.anthropic_oauth.cch import compute_cch
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload

        payload = {
            "messages": [{"role": "user", "content": "specific message"}],
        }
        result = transform_request_payload(payload)
        billing = result["system"][0]["text"]
        expected_cch = compute_cch("specific message")
        assert f"cch={expected_cch};" in billing

    def test_returns_same_dict(self):
        """Mutates and returns payload (allows chaining)."""
        from custom_components.homeclaw.providers.anthropic_oauth.transform import transform_request_payload

        payload = {"messages": [{"role": "user", "content": "x"}]}
        result = transform_request_payload(payload)
        assert result is payload
