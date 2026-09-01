from __future__ import annotations

from custom_components.homeclaw.providers.grok_oauth import constants


class TestUrls:
    def test_issuer(self):
        assert constants.ISSUER == "https://auth.x.ai"

    def test_device_code_url(self):
        assert constants.DEVICE_CODE_URL == "https://auth.x.ai/oauth2/device/code"

    def test_token_url(self):
        assert constants.TOKEN_URL == "https://auth.x.ai/oauth2/token"

    def test_chat_completions_is_cli_proxy(self):
        assert constants.CHAT_COMPLETIONS_URL == "https://cli-chat-proxy.grok.com/v1/chat/completions"


class TestClient:
    def test_public_client_id(self):
        assert constants.CLIENT_ID == "b1a00492-073a-47ea-816f-4c329264a828"

    def test_device_grant(self):
        assert constants.DEVICE_CODE_GRANT_TYPE == "urn:ietf:params:oauth:grant-type:device_code"

    def test_cli_headers(self):
        assert constants.TOKEN_AUTH_VALUE == "xai-grok-cli"
        assert constants.CLIENT_IDENTIFIER == "grok-shell"
        assert constants.CLIENT_VERSION == "1.0.13"


class TestScopes:
    def test_includes_cli_and_conversations(self):
        assert "grok-cli:access" in constants.OAUTH_SCOPES
        assert "api:access" in constants.OAUTH_SCOPES
        assert "offline_access" in constants.OAUTH_SCOPES
        assert "conversations:read" in constants.OAUTH_SCOPES
        assert "conversations:write" in constants.OAUTH_SCOPES
        assert "workspaces:read" in constants.OAUTH_SCOPES
