from __future__ import annotations

CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
ISSUER = "https://auth.x.ai"
DEVICE_CODE_URL = f"{ISSUER}/oauth2/device/code"
TOKEN_URL = f"{ISSUER}/oauth2/token"
DEVICE_CODE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"

OAUTH_SCOPES = (
    "openid",
    "profile",
    "email",
    "offline_access",
    "grok-cli:access",
    "api:access",
    "conversations:read",
    "conversations:write",
    "workspaces:read",
    "workspaces:write",
)

REFERRER = "homeclaw"

CHAT_COMPLETIONS_URL = "https://cli-chat-proxy.grok.com/v1/chat/completions"

TOKEN_AUTH_HEADER = "X-XAI-Token-Auth"
TOKEN_AUTH_VALUE = "xai-grok-cli"
CLIENT_IDENTIFIER = "grok-shell"
CLIENT_VERSION = "1.0.13"

REFRESH_MAX_RETRIES = 2
REFRESH_BASE_DELAY_S = 0.5
ACCESS_TOKEN_SKEW_S = 300

DEVICE_CODE_DEFAULT_INTERVAL_S = 5.0
DEVICE_CODE_MIN_INTERVAL_S = 1.0
DEVICE_CODE_SLOW_DOWN_S = 5.0
DEVICE_CODE_DEFAULT_EXPIRES_S = 300.0
DEVICE_CODE_POLL_MARGIN_S = 1.0
