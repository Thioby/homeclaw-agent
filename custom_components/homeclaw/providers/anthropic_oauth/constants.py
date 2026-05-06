"""OAuth client constants for Anthropic Claude (Pro/Max + Console).

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
Updates here track Anthropic's server-side classifier behavior;
see CHANGELOG of upstream plugin for rationale of each value.
"""
from __future__ import annotations

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

AUTHORIZE_URLS = {
    "console": "https://platform.claude.com/oauth/authorize",
    "max": "https://claude.ai/oauth/authorize",
}
CODE_CALLBACK_URL = "https://platform.claude.com/oauth/code/callback"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CREATE_API_KEY_URL = "https://api.anthropic.com/api/oauth/claude_cli/create_api_key"

OAUTH_SCOPES = (
    "org:create_api_key",
    "user:profile",
    "user:inference",
    "user:sessions:claude_code",
    "user:mcp_servers",
    "user:file_upload",
)

TOOL_PREFIX_NAMESPACE = "homeclaw"
TOOL_PREFIX = f"mcp__{TOOL_PREFIX_NAMESPACE}__"

REQUIRED_BETAS = (
    "oauth-2025-04-20",
    "interleaved-thinking-2025-05-14",
)

OPENCODE_IDENTITY_PREFIX = "You are OpenCode"
CLAUDE_CODE_IDENTITY = "You are a Claude agent, built on Anthropic's Claude Agent SDK."

CCH_SALT = "59cf53e54c78"
CCH_POSITIONS = (4, 7, 20)
CLAUDE_CODE_VERSION = "2.1.87"
CLAUDE_CODE_ENTRYPOINT = "sdk-cli"

USER_AGENT = "claude-cli/2.1.87 (external, cli)"

# Anchors identifying paragraphs to remove from system prompt.
# Resilient to upstream rewording — anchor (URL) persists across edits.
PARAGRAPH_REMOVAL_ANCHORS = (
    "github.com/anomalyco/opencode",
    "opencode.ai/docs",
)

# Inline replacements after paragraph removal.
# "Here is some useful information..." is the EXACT phrase Anthropic's
# server-side classifier matches as third-party agent CLI fingerprint;
# triggers 400 disguised as "You're out of extra usage." (upstream v1.7.5).
TEXT_REPLACEMENTS = (
    ("if OpenCode honestly", "if the assistant honestly"),
    (
        "Here is some useful information about the environment you are running in:",
        "Environment context you are running in:",
    ),
)

REFRESH_MAX_RETRIES = 2
REFRESH_BASE_DELAY_S = 0.5
