"""Comprehensive tests for configuration flow."""

import pytest
from unittest.mock import patch, MagicMock
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.homeclaw import config_flow
from custom_components.homeclaw.const import DOMAIN, CONF_LOCAL_URL, CONF_RAG_ENABLED
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def enable_custom_integrations(auto_enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture(autouse=True)
def bypass_setup_entry():
    """Bypass entry setup."""
    with patch("custom_components.homeclaw.async_setup_entry", return_value=True):
        yield


async def test_step_user_provider_selection(hass: HomeAssistant):
    """Test user step selecting a provider."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select OpenAI (non-OAuth)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "openai"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "configure"


async def test_step_user_anthropic_oauth(hass: HomeAssistant):
    """Test user step selecting Anthropic OAuth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.config_flow.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.config_flow.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "anthropic_oauth"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "anthropic_oauth"
    assert "auth_url" in result["description_placeholders"]


async def test_step_user_gemini_oauth(hass: HomeAssistant):
    """Test user step selecting Gemini OAuth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.gemini_oauth.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.gemini_oauth.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "gemini_oauth"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "gemini_oauth"
    assert "auth_url" in result["description_placeholders"]


async def test_step_configure_local(hass: HomeAssistant):
    """Test configure step for local provider."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "local"},
    )
    assert result["step_id"] == "configure"

    # Fill form
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LOCAL_URL: "http://localhost:11434",
            "model": "llama3.2",
            CONF_RAG_ENABLED: False,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["ai_provider"] == "local"
    assert result["data"][CONF_LOCAL_URL] == "http://localhost:11434"
    assert result["data"]["models"]["local"] == "llama3.2"


async def test_step_configure_zai(hass: HomeAssistant):
    """Test configure step for zai provider."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "zai"},
    )
    assert result["step_id"] == "configure"

    # Fill form
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "zai_token": "secret_token",
            "zai_endpoint": "coding",
            "model": "glm-4.7",
            CONF_RAG_ENABLED: True,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["ai_provider"] == "zai"
    assert result["data"]["zai_token"] == "secret_token"
    assert result["data"]["zai_endpoint"] == "coding"
    assert result["data"]["models"]["zai"] == "glm-4.7"


async def test_step_configure_empty_token(hass: HomeAssistant):
    """Test configure step with empty token."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "openai"},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"openai_token": "", "model": "gpt-4o"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["openai_token"] == "required"


async def test_step_configure_custom_model(hass: HomeAssistant):
    """Test configure step with custom model."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "openai"},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "openai_token": "token",
            "model": "gpt-4o",
            "custom_model": "my-custom-gpt",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["models"]["openai"] == "my-custom-gpt"


async def test_step_configure_custom_fallback(hass: HomeAssistant):
    """Test configure step with 'Custom...' selected but empty custom_model field."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "openai"},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"openai_token": "token", "model": "Custom...", "custom_model": ""},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Should fallback to default from models_config.json
    from custom_components.homeclaw.config_flow import get_default_model

    assert result["data"]["models"]["openai"] == get_default_model("openai")


async def test_step_anthropic_oauth_success(hass: HomeAssistant):
    """Test successful Anthropic OAuth flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.config_flow.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.config_flow.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "anthropic_oauth"},
        )

    with patch(
        "custom_components.homeclaw.config_flow.exchange_code",
        return_value={"access_token": "at", "refresh_token": "rt", "expires_at": 12345},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"code": "my_code"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Homeclaw (Anthropic OAuth)"
    assert result["data"]["anthropic_oauth"]["access_token"] == "at"


async def test_step_anthropic_oauth_no_code(hass: HomeAssistant):
    """Test Anthropic OAuth step with no code."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.config_flow.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.config_flow.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "anthropic_oauth"},
        )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"code": ""},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["code"] == "required"


async def test_step_anthropic_oauth_failed(hass: HomeAssistant):
    """Test Anthropic OAuth step with exchange failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.config_flow.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.config_flow.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "anthropic_oauth"},
        )

    with patch(
        "custom_components.homeclaw.config_flow.exchange_code",
        return_value={"error": "failed"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"code": "my_code"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "oauth_failed"


async def test_step_gemini_oauth_success(hass: HomeAssistant):
    """Test successful Gemini OAuth flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.gemini_oauth.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.gemini_oauth.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "gemini_oauth"},
        )

    with patch(
        "custom_components.homeclaw.gemini_oauth.exchange_code",
        return_value={"access_token": "at", "refresh_token": "rt", "expires_at": 12345},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"code": "my_code", "model": "gemini-2.5-flash"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Homeclaw (Gemini OAuth)"
    assert result["data"]["gemini_oauth"]["access_token"] == "at"
    assert result["data"]["models"]["gemini_oauth"] == "gemini-2.5-flash"


async def test_step_gemini_oauth_url_parsing(hass: HomeAssistant):
    """Test Gemini OAuth with full URL code."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.homeclaw.gemini_oauth.generate_pkce",
            return_value=("verifier", "challenge"),
        ),
        patch(
            "custom_components.homeclaw.gemini_oauth.build_auth_url",
            return_value="http://auth-url",
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"ai_provider": "gemini_oauth"},
        )

    callback_url = "http://localhost:8085/oauth2callback?code=extracted_code&state=xyz"

    with patch(
        "custom_components.homeclaw.gemini_oauth.exchange_code",
        return_value={"access_token": "at", "refresh_token": "rt", "expires_at": 12345},
    ) as mock_exchange:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"code": callback_url, "model": "gemini-2.5-flash"},
        )

        # Verify extraction happened
        call_args = mock_exchange.call_args
        assert call_args[0][1] == "extracted_code"

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_extract_oauth_code(hass: HomeAssistant):
    """Test the helper method for extracting oauth code."""
    flow = config_flow.HomeclawConfigFlow()

    # Test plain code
    assert flow._extract_oauth_code("my_code") == "my_code"

    # Test URL
    url = "http://localhost:8085/oauth2callback?code=my_code&state=xyz"
    assert flow._extract_oauth_code(url) == "my_code"

    # Test URL without code
    url_no_code = "http://localhost:8085/oauth2callback?state=xyz"
    assert (
        flow._extract_oauth_code(url_no_code)
        == "http://localhost:8085/oauth2callback?state=xyz"
    )


async def test_options_flow_init(hass: HomeAssistant):
    """Test options flow initialization."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ai_provider": "openai", "openai_token": "abc"}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_switch_provider(hass: HomeAssistant):
    """Test switching provider in options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ai_provider": "openai", "openai_token": "abc"}
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "llama"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "configure_options"

    # Check that it asks for llama token
    # (voluptuous schema is not easy to introspect deeply here, but we check step transition)


async def test_options_flow_oauth_provider(hass: HomeAssistant):
    """Test options flow for OAuth provider (limited options)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "ai_provider": "anthropic_oauth",
            "anthropic_oauth": {"access_token": "x"},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Keep same provider
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "anthropic_oauth"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "configure_options"

    # Should only have RAG option
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_RAG_ENABLED: False},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_RAG_ENABLED] is False


async def test_options_flow_update_provider(hass: HomeAssistant):
    """Test updating settings for standard provider."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "ai_provider": "openai",
            "openai_token": "old",
            "models": {"openai": "old-model"},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Select same provider
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"ai_provider": "openai"},
    )

    # Update token and model
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "openai_token": "new_token",
            "model": "gpt-5",
            CONF_RAG_ENABLED: True,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data["openai_token"] == "new_token"
    assert entry.data["models"]["openai"] == "gpt-5"
    assert entry.data[CONF_RAG_ENABLED] is True
