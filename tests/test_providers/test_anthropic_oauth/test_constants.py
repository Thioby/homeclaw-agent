"""Tests for anthropic_oauth.constants — sanity check on values."""
from __future__ import annotations

from custom_components.homeclaw.providers.anthropic_oauth import constants


class TestUrls:
    def test_token_url_is_platform_claude(self):
        assert constants.TOKEN_URL == "https://platform.claude.com/v1/oauth/token"

    def test_callback_url_is_platform_claude(self):
        assert constants.CODE_CALLBACK_URL == "https://platform.claude.com/oauth/code/callback"

    def test_authorize_console_is_platform_claude(self):
        assert constants.AUTHORIZE_URLS["console"] == "https://platform.claude.com/oauth/authorize"

    def test_authorize_max_is_claude_ai(self):
        assert constants.AUTHORIZE_URLS["max"] == "https://claude.ai/oauth/authorize"

    def test_create_api_key_url_is_anthropic_api(self):
        assert constants.CREATE_API_KEY_URL == "https://api.anthropic.com/api/oauth/claude_cli/create_api_key"


class TestScopes:
    def test_scopes_count_is_six(self):
        assert len(constants.OAUTH_SCOPES) == 6

    def test_scopes_includes_new_v18_scopes(self):
        assert "user:sessions:claude_code" in constants.OAUTH_SCOPES
        assert "user:mcp_servers" in constants.OAUTH_SCOPES
        assert "user:file_upload" in constants.OAUTH_SCOPES

    def test_scopes_keeps_legacy_three(self):
        assert "org:create_api_key" in constants.OAUTH_SCOPES
        assert "user:profile" in constants.OAUTH_SCOPES
        assert "user:inference" in constants.OAUTH_SCOPES


class TestToolPrefix:
    def test_tool_prefix_is_double_underscore_namespaced(self):
        assert constants.TOOL_PREFIX == "mcp__homeclaw__"

    def test_tool_prefix_namespace(self):
        assert constants.TOOL_PREFIX_NAMESPACE == "homeclaw"


class TestBetas:
    def test_required_betas_includes_oauth_2025_04_20(self):
        assert "oauth-2025-04-20" in constants.REQUIRED_BETAS

    def test_required_betas_includes_thinking(self):
        assert "interleaved-thinking-2025-05-14" in constants.REQUIRED_BETAS


class TestUserAgent:
    def test_user_agent_is_claude_cli_2_1_87(self):
        assert constants.USER_AGENT == "claude-cli/2.1.87 (external, cli)"


class TestCCHValues:
    def test_cch_salt(self):
        assert constants.CCH_SALT == "59cf53e54c78"

    def test_cch_positions(self):
        assert constants.CCH_POSITIONS == (4, 7, 20)

    def test_claude_code_version(self):
        assert constants.CLAUDE_CODE_VERSION == "2.1.87"

    def test_claude_code_entrypoint(self):
        assert constants.CLAUDE_CODE_ENTRYPOINT == "sdk-cli"


class TestSanitizationConfig:
    def test_opencode_identity_prefix(self):
        assert constants.OPENCODE_IDENTITY_PREFIX == "You are OpenCode"

    def test_claude_code_identity_is_agent_sdk_phrasing(self):
        assert constants.CLAUDE_CODE_IDENTITY == (
            "You are a Claude agent, built on Anthropic's Claude Agent SDK."
        )

    def test_anchors_include_anomalyco_url(self):
        assert "github.com/anomalyco/opencode" in constants.PARAGRAPH_REMOVAL_ANCHORS

    def test_anchors_include_opencode_docs(self):
        assert "opencode.ai/docs" in constants.PARAGRAPH_REMOVAL_ANCHORS

    def test_critical_phrase_replacement_present(self):
        match_strings = [pair[0] for pair in constants.TEXT_REPLACEMENTS]
        assert any(
            "Here is some useful information about the environment" in m
            for m in match_strings
        ), "Missing critical v1.7.5 classifier-fingerprint replacement"

    def test_inline_replacement_for_opencode_phrase(self):
        match_strings = [pair[0] for pair in constants.TEXT_REPLACEMENTS]
        assert "if OpenCode honestly" in match_strings


class TestRetryConfig:
    def test_refresh_max_retries(self):
        assert constants.REFRESH_MAX_RETRIES == 2

    def test_refresh_base_delay(self):
        assert constants.REFRESH_BASE_DELAY_S == 0.5
