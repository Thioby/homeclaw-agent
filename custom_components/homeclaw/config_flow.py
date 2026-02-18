"""Config flow for Homeclaw integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

import aiohttp

from .const import (
    CONF_LOCAL_MODEL,
    CONF_LOCAL_URL,
    CONF_RAG_ENABLED,
    DEFAULT_RAG_ENABLED,
    DOMAIN,
)
from .models import get_allow_custom_model, get_default_model, get_model_ids
from .oauth import generate_pkce, build_auth_url, exchange_code
from . import gemini_oauth


# Re-export for backward compatibility (used by config flow steps and tests)
def get_model_options(provider: str) -> list[str]:
    """Get model IDs for a provider from models_config.json."""
    return get_model_ids(provider)


def get_model_options_for_flow(provider: str) -> list[str]:
    """Get model options for config flow UI, including 'Custom...' if applicable.

    Returns model IDs from JSON. Appends 'Custom...' for providers that allow it,
    or if the provider has no predefined models.
    """
    models = get_model_ids(provider)
    allow_custom = get_allow_custom_model(provider)
    if allow_custom or not models:
        if "Custom..." not in models:
            models = models + ["Custom..."]
    return models


_LOGGER = logging.getLogger(__name__)

PROVIDERS = {
    "llama": "Llama",
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "gemini_oauth": "Google Gemini (OAuth)",
    "openrouter": "OpenRouter",
    "anthropic": "Anthropic (Claude)",
    "anthropic_oauth": "Anthropic (Claude Pro/Max)",
    "alter": "Alter",
    "zai": "z.ai",
    "local": "Local Model",
}

TOKEN_FIELD_NAMES = {
    "llama": "llama_token",
    "openai": "openai_token",
    "gemini": "gemini_token",
    "openrouter": "openrouter_token",
    "anthropic": "anthropic_token",
    "alter": "alter_token",
    "zai": "zai_token",
    "zai_endpoint": "zai_endpoint",
    "local": CONF_LOCAL_URL,  # For local models, we use URL instead of token
}

TOKEN_LABELS = {
    "llama": "Llama API Token",
    "openai": "OpenAI API Key",
    "gemini": "Google Gemini API Key",
    "openrouter": "OpenRouter API Key",
    "anthropic": "Anthropic API Key",
    "alter": "Alter API Key",
    "zai": "z.ai API Key",
    "zai_endpoint": "z.ai API Endpoint Type",
    "local": "Local API URL (e.g., http://localhost:11434/api/generate)",
}

DEFAULT_PROVIDER = "openai"


class HomeclawConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
    """Handle a config flow for Homeclaw."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        try:
            return HomeclawOptionsFlowHandler()
        except Exception as e:
            _LOGGER.error("Error creating options flow: %s", e)
            return None

    # ------------------------------------------------------------------
    # Reauth flow (triggered when OAuth refresh token becomes invalid)
    # ------------------------------------------------------------------

    async def async_step_reauth(self, entry_data: dict[str, Any] | None = None):
        """Handle re-authentication trigger from a config entry.

        HA calls this with the config entry's data when
        ``config_entry.async_start_reauth()`` fires.
        """
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_entry_removed")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Show OAuth re-authorization form and exchange the new code."""
        provider = self._reauth_entry.data.get("ai_provider", "")

        if provider == "anthropic_oauth":
            return await self._reauth_anthropic(user_input)
        if provider == "gemini_oauth":
            return await self._reauth_gemini(user_input)

        # Unsupported provider — abort gracefully.
        return self.async_abort(reason="oauth_reconfigure_not_supported")

    async def _reauth_anthropic(self, user_input=None):
        """Re-authorize Anthropic OAuth and update the existing entry."""
        if not hasattr(self, "_pkce_verifier") or self._pkce_verifier is None:
            verifier, challenge = generate_pkce()
            self._pkce_verifier = verifier
            self._pkce_challenge = challenge
            self._auth_url = build_auth_url(
                self._pkce_challenge, self._pkce_verifier, mode="max"
            )

        errors: dict[str, str] = {}

        if user_input is not None:
            code = user_input.get("code", "").strip()
            if code:
                try:
                    async with aiohttp.ClientSession() as session:
                        result = await exchange_code(session, code, self._pkce_verifier)

                    if "error" in result:
                        _LOGGER.error(
                            "Reauth OAuth exchange failed: %s", result.get("error")
                        )
                        errors["base"] = "oauth_failed"
                    else:
                        new_data = {
                            **self._reauth_entry.data,
                            "anthropic_oauth": {
                                "access_token": result["access_token"],
                                "refresh_token": result["refresh_token"],
                                "expires_at": result["expires_at"],
                            },
                        }
                        if self._reauth_entry is not None:
                            self.hass.config_entries.async_update_entry(
                                self._reauth_entry, data=new_data
                            )
                            await self.hass.config_entries.async_reload(
                                self._reauth_entry.entry_id
                            )
                        return self.async_abort(reason="reauth_successful")
                except aiohttp.ClientError as e:
                    _LOGGER.error("Network error during reauth: %s", e)
                    errors["base"] = "oauth_failed"
            else:
                errors["code"] = "required"

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"auth_url": self._auth_url},
            data_schema=vol.Schema(
                {vol.Required("code"): TextSelector(TextSelectorConfig(type="text"))}
            ),
            errors=errors,
        )

    async def _reauth_gemini(self, user_input=None):
        """Re-authorize Gemini OAuth and update the existing entry."""
        if (
            not hasattr(self, "_gemini_pkce_verifier")
            or self._gemini_pkce_verifier is None
        ):
            verifier, challenge = gemini_oauth.generate_pkce()
            self._gemini_pkce_verifier = verifier
            self._gemini_pkce_challenge = challenge
            self._gemini_auth_url = gemini_oauth.build_auth_url(
                self._gemini_pkce_challenge, self._gemini_pkce_verifier
            )

        errors: dict[str, str] = {}

        if user_input is not None:
            code_input = user_input.get("code", "").strip()
            if code_input:
                code = self._extract_oauth_code(code_input)
                try:
                    async with aiohttp.ClientSession() as session:
                        result = await gemini_oauth.exchange_code(
                            session, code, self._gemini_pkce_verifier
                        )

                    if "error" in result:
                        _LOGGER.error(
                            "Reauth Gemini OAuth exchange failed: %s",
                            result.get("error"),
                        )
                        errors["base"] = "oauth_failed"
                    else:
                        new_data = {
                            **self._reauth_entry.data,
                            "gemini_oauth": {
                                "access_token": result["access_token"],
                                "refresh_token": result["refresh_token"],
                                "expires_at": result["expires_at"],
                            },
                        }
                        if self._reauth_entry is not None:
                            self.hass.config_entries.async_update_entry(
                                self._reauth_entry, data=new_data
                            )
                            await self.hass.config_entries.async_reload(
                                self._reauth_entry.entry_id
                            )
                        return self.async_abort(reason="reauth_successful")
                except aiohttp.ClientError as e:
                    _LOGGER.error("Network error during Gemini reauth: %s", e)
                    errors["base"] = "oauth_failed"
            else:
                errors["code"] = "required"

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"auth_url": self._gemini_auth_url},
            data_schema=vol.Schema(
                {vol.Required("code"): TextSelector(TextSelectorConfig(type="text"))}
            ),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if this provider is already configured
            await self.async_set_unique_id(f"homeclaw_{user_input['ai_provider']}")
            self._abort_if_unique_id_configured()

            self.config_data = {"ai_provider": user_input["ai_provider"]}

            if user_input["ai_provider"] == "anthropic_oauth":
                return await self.async_step_anthropic_oauth()

            if user_input["ai_provider"] == "gemini_oauth":
                return await self.async_step_gemini_oauth()

            return await self.async_step_configure()

        # Show provider selection form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("ai_provider"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in PROVIDERS.items()
                            ]
                        )
                    ),
                }
            ),
        )

    async def async_step_configure(self, user_input=None):
        """Handle the configuration step for the selected provider."""
        errors = {}
        provider = self.config_data["ai_provider"]
        token_field = TOKEN_FIELD_NAMES[provider]
        token_label = TOKEN_LABELS[provider]
        default_model = get_default_model(provider) or ""
        # For Alter provider, default to "Custom..." for the dropdown since model is user-provided
        dropdown_default = "Custom..." if provider == "alter" else default_model
        available_models = get_model_options_for_flow(provider)

        if user_input is not None:
            try:
                # Validate the token
                token_value = user_input.get(token_field)
                if not token_value:
                    errors[token_field] = "required"
                    raise InvalidApiKey

                # Store the configuration data
                self.config_data[token_field] = token_value

                # For z.ai, store endpoint type
                if provider == "zai":
                    endpoint_type = user_input.get("zai_endpoint", "general")
                    self.config_data["zai_endpoint"] = endpoint_type

                # Add model configuration if provided
                selected_model = user_input.get("model")
                custom_model = user_input.get("custom_model")

                _LOGGER.debug(
                    f"Config flow - Provider: {provider}, Selected model: {selected_model}, Custom model: {custom_model}"
                )

                # Initialize models dict if it doesn't exist
                if "models" not in self.config_data:
                    self.config_data["models"] = {}

                if custom_model and custom_model.strip():
                    # Use custom model if provided and not empty
                    self.config_data["models"][provider] = custom_model.strip()
                elif selected_model and selected_model != "Custom...":
                    # Use selected model if it's not the "Custom..." option
                    self.config_data["models"][provider] = selected_model
                else:
                    # For local and alter providers, allow empty model name
                    if provider in ("local", "alter", "zai"):
                        self.config_data["models"][provider] = ""
                    else:
                        # Fallback to default model for other providers
                        self.config_data["models"][provider] = default_model

                # Store RAG enabled setting
                self.config_data[CONF_RAG_ENABLED] = user_input.get(
                    CONF_RAG_ENABLED, DEFAULT_RAG_ENABLED
                )

                return self.async_create_entry(
                    title=f"Homeclaw ({PROVIDERS[provider]})",
                    data=self.config_data,
                )
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        if provider == "zai":
            # For z.ai provider, we need token, endpoint type, and optional model name
            model_options = get_model_options_for_flow("zai")
            schema_dict = {
                vol.Required(token_field): TextSelector(
                    TextSelectorConfig(type="password")
                ),
                vol.Optional("zai_endpoint", default="general"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": "general", "label": "General Purpose"},
                            {"value": "coding", "label": "Coding (3× usage, 1/7 cost)"},
                        ]
                    )
                ),
                vol.Optional("model", default="glm-4.7"): SelectSelector(
                    SelectSelectorConfig(options=model_options)
                ),
                vol.Optional("custom_model"): TextSelector(
                    TextSelectorConfig(type="text")
                ),
                vol.Optional(
                    CONF_RAG_ENABLED, default=DEFAULT_RAG_ENABLED
                ): BooleanSelector(),
            }

            return self.async_show_form(
                step_id="configure",
                data_schema=vol.Schema(schema_dict),
                errors=errors,
                description_placeholders={
                    "token_label": token_label,
                    "provider": PROVIDERS[provider],
                },
            )

        if provider == "local":
            # For local provider, we need both URL and optional model name
            schema_dict = {
                vol.Required(CONF_LOCAL_URL): TextSelector(
                    TextSelectorConfig(type="text")
                ),
            }

            # Add model selection
            model_options = get_model_options_for_flow("local")
            schema_dict[vol.Optional("model", default="Custom...")] = SelectSelector(
                SelectSelectorConfig(options=model_options)
            )
            schema_dict[vol.Optional("custom_model")] = TextSelector(
                TextSelectorConfig(type="text")
            )
            schema_dict[vol.Optional(CONF_RAG_ENABLED, default=DEFAULT_RAG_ENABLED)] = (
                BooleanSelector()
            )

            return self.async_show_form(
                step_id="configure",
                data_schema=vol.Schema(schema_dict),
                errors=errors,
                description_placeholders={
                    "token_label": "Local API URL",
                    "provider": PROVIDERS[provider],
                },
            )

        # Build schema for other providers
        schema_dict = {
            vol.Required(token_field): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        # Add model selection if available
        if available_models:
            # Add predefined models + custom option (avoid duplicating "Custom...")
            if "Custom..." in available_models:
                model_options = available_models
            else:
                model_options = available_models + ["Custom..."]
            schema_dict[vol.Optional("model", default=dropdown_default)] = (
                SelectSelector(SelectSelectorConfig(options=model_options))
            )
            schema_dict[vol.Optional("custom_model")] = TextSelector(
                TextSelectorConfig(type="text")
            )

        # Add RAG option for all providers
        schema_dict[vol.Optional(CONF_RAG_ENABLED, default=DEFAULT_RAG_ENABLED)] = (
            BooleanSelector()
        )

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": token_label,
                "provider": PROVIDERS[provider],
            },
        )

    async def async_step_anthropic_oauth(self, user_input=None):
        """Show auth URL and prompt user to authorize, then enter code."""
        if not hasattr(self, "_pkce_verifier") or self._pkce_verifier is None:
            verifier, challenge = generate_pkce()
            self._pkce_verifier = verifier
            self._pkce_challenge = challenge
            self._auth_url = build_auth_url(
                self._pkce_challenge, self._pkce_verifier, mode="max"
            )

        errors = {}

        if user_input is not None:
            code = user_input.get("code", "").strip()
            if code:
                try:
                    async with aiohttp.ClientSession() as session:
                        result = await exchange_code(session, code, self._pkce_verifier)

                    if "error" in result:
                        _LOGGER.error("OAuth exchange failed: %s", result.get("error"))
                        errors["base"] = "oauth_failed"
                    else:
                        return self.async_create_entry(
                            title="Homeclaw (Anthropic OAuth)",
                            data={
                                "ai_provider": "anthropic_oauth",
                                "anthropic_oauth": {
                                    "access_token": result["access_token"],
                                    "refresh_token": result["refresh_token"],
                                    "expires_at": result["expires_at"],
                                },
                            },
                        )
                except aiohttp.ClientError as e:
                    _LOGGER.error("Network error during OAuth exchange: %s", e)
                    errors["base"] = "oauth_failed"
            else:
                errors["code"] = "required"

        return self.async_show_form(
            step_id="anthropic_oauth",
            description_placeholders={"auth_url": self._auth_url},
            data_schema=vol.Schema(
                {
                    vol.Required("code"): TextSelector(TextSelectorConfig(type="text")),
                }
            ),
            errors=errors,
        )

    def _extract_oauth_code(self, input_str: str) -> str:
        """Extract OAuth code from callback URL or return input as-is.

        Accepts either:
        - Full callback URL: http://localhost:8085/oauth2callback?code=4/0A...&state=...
        - Just the authorization code: 4/0A...
        """
        from urllib.parse import urlparse, parse_qs

        if input_str.startswith("http://") or input_str.startswith("https://"):
            parsed = urlparse(input_str)
            params = parse_qs(parsed.query)
            code_list = params.get("code", [])
            if code_list:
                return code_list[0]
        return input_str

    async def async_step_gemini_oauth(self, user_input=None):
        """Show auth URL and prompt user to authorize, then enter code for Gemini OAuth."""
        if (
            not hasattr(self, "_gemini_pkce_verifier")
            or self._gemini_pkce_verifier is None
        ):
            verifier, challenge = gemini_oauth.generate_pkce()
            self._gemini_pkce_verifier = verifier
            self._gemini_pkce_challenge = challenge
            self._gemini_auth_url = gemini_oauth.build_auth_url(
                self._gemini_pkce_challenge, self._gemini_pkce_verifier
            )

        # Available models for Gemini OAuth (from models_config.json)
        gemini_oauth_models = get_model_options("gemini_oauth")
        default_model = get_default_model("gemini_oauth") or "gemini-3-pro-preview"

        errors = {}

        if user_input is not None:
            code_input = user_input.get("code", "").strip()
            selected_model = user_input.get("model", default_model)
            if code_input:
                # Extract code from full callback URL or use as-is
                code = self._extract_oauth_code(code_input)
                try:
                    async with aiohttp.ClientSession() as session:
                        result = await gemini_oauth.exchange_code(
                            session, code, self._gemini_pkce_verifier
                        )

                    if "error" in result:
                        _LOGGER.error(
                            "Gemini OAuth exchange failed: %s", result.get("error")
                        )
                        errors["base"] = "oauth_failed"
                    else:
                        return self.async_create_entry(
                            title="Homeclaw (Gemini OAuth)",
                            data={
                                "ai_provider": "gemini_oauth",
                                "gemini_oauth": {
                                    "access_token": result["access_token"],
                                    "refresh_token": result["refresh_token"],
                                    "expires_at": result["expires_at"],
                                },
                                "models": {"gemini_oauth": selected_model},
                            },
                        )
                except aiohttp.ClientError as e:
                    _LOGGER.error("Network error during Gemini OAuth exchange: %s", e)
                    errors["base"] = "oauth_failed"
            else:
                errors["code"] = "required"

        return self.async_show_form(
            step_id="gemini_oauth",
            description_placeholders={"auth_url": self._gemini_auth_url},
            data_schema=vol.Schema(
                {
                    vol.Required("model", default=default_model): SelectSelector(
                        SelectSelectorConfig(options=gemini_oauth_models)
                    ),
                    vol.Required("code"): TextSelector(TextSelectorConfig(type="text")),
                }
            ),
            errors=errors,
        )


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid API key."""


class HomeclawOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Homeclaw."""

    def __init__(self):
        """Initialize options flow."""
        self.options_data = {}

    async def async_step_init(self, user_input=None):
        """Handle the initial options step - provider selection."""
        current_provider = self.config_entry.data.get("ai_provider", DEFAULT_PROVIDER)

        if user_input is not None:
            # Store selected provider and move to configure step
            self.options_data = {
                "ai_provider": user_input["ai_provider"],
                "current_provider": current_provider,
            }
            return await self.async_step_configure_options()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "ai_provider", default=current_provider
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": k, "label": v} for k, v in PROVIDERS.items()
                            ]
                        )
                    ),
                }
            ),
            description_placeholders={"current_provider": PROVIDERS[current_provider]},
        )

    async def async_step_configure_options(self, user_input=None):
        """Handle the configuration step for the selected provider in options."""
        errors = {}
        provider = self.options_data["ai_provider"]
        current_provider = self.options_data["current_provider"]

        # Get current RAG setting (available for all providers)
        current_rag_enabled = self.config_entry.data.get(
            CONF_RAG_ENABLED, DEFAULT_RAG_ENABLED
        )

        # OAuth providers - show only RAG option (no token reconfiguration)
        if provider in ("anthropic_oauth", "gemini_oauth"):
            if user_input is not None:
                # Update RAG setting
                updated_data = dict(self.config_entry.data)
                updated_data[CONF_RAG_ENABLED] = user_input.get(
                    CONF_RAG_ENABLED, current_rag_enabled
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=updated_data
                )
                # Preserve existing options (e.g. Discord pairing data).
                return self.async_create_entry(
                    title="", data=dict(self.config_entry.options)
                )

            # Show form with only RAG option for OAuth providers
            return self.async_show_form(
                step_id="configure_options",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_RAG_ENABLED, default=current_rag_enabled
                        ): BooleanSelector(),
                    }
                ),
                errors=errors,
                description_placeholders={
                    "token_label": "OAuth",
                    "provider": PROVIDERS[provider],
                },
            )

        token_field = TOKEN_FIELD_NAMES[provider]
        token_label = TOKEN_LABELS[provider]

        # Get current configuration
        current_models = self.config_entry.data.get("models", {})
        default_model = get_default_model(provider) or ""
        current_model = current_models.get(provider, default_model)
        # For Alter provider, if model is empty, default to "Custom..." for the dropdown
        if provider == "alter" and not current_model:
            current_model = "Custom..."
        current_token = self.config_entry.data.get(token_field, "")
        available_models = get_model_options_for_flow(provider)

        # Use current token if provider hasn't changed, otherwise empty
        display_token = current_token if provider == current_provider else ""

        if user_input is not None:
            try:
                token_value = user_input.get(token_field)
                if not token_value:
                    errors[token_field] = "required"
                else:
                    # Prepare the updated configuration
                    updated_data = dict(self.config_entry.data)
                    updated_data["ai_provider"] = provider
                    updated_data[token_field] = token_value

                    # Update model configuration
                    selected_model = user_input.get("model")
                    custom_model = user_input.get("custom_model")

                    # For zai, update endpoint type
                    if provider == "zai":
                        endpoint_type = user_input.get("zai_endpoint", "general")
                        updated_data["zai_endpoint"] = endpoint_type

                    # Initialize models dict if it doesn't exist
                    if "models" not in updated_data:
                        updated_data["models"] = {}

                    if custom_model and custom_model.strip():
                        # Use custom model if provided and not empty
                        updated_data["models"][provider] = custom_model.strip()
                    elif selected_model and selected_model != "Custom...":
                        # Use selected model if it's not the "Custom..." option
                        updated_data["models"][provider] = selected_model
                    else:
                        # For local, alter, and zai providers, allow empty model name
                        if provider in ("local", "alter", "zai"):
                            updated_data["models"][provider] = ""
                        else:
                            # Ensure we keep the current model or use default for other providers
                            if provider not in updated_data["models"]:
                                updated_data["models"][provider] = (
                                    get_default_model(provider) or ""
                                )

                    _LOGGER.debug(
                        f"Options flow - Final model config for {provider}: {updated_data['models'].get(provider)}"
                    )

                    # Update RAG enabled setting
                    updated_data[CONF_RAG_ENABLED] = user_input.get(
                        CONF_RAG_ENABLED, current_rag_enabled
                    )

                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=updated_data
                    )

                    # Preserve existing options (e.g. Discord pairing data).
                    return self.async_create_entry(
                        title="", data=dict(self.config_entry.options)
                    )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options flow")
                errors["base"] = "unknown"

        # Build schema for the selected provider in options
        if provider == "zai":
            current_endpoint = self.config_entry.data.get("zai_endpoint", "general")
            model_options = get_model_options_for_flow("zai")
            schema_dict = {
                vol.Required(token_field, default=display_token): TextSelector(
                    TextSelectorConfig(type="password")
                ),
                vol.Optional("zai_endpoint", default=current_endpoint): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": "general", "label": "General Purpose"},
                            {"value": "coding", "label": "Coding (3× usage, 1/7 cost)"},
                        ]
                    )
                ),
                vol.Optional("model", default=current_model): SelectSelector(
                    SelectSelectorConfig(options=model_options)
                ),
                vol.Optional("custom_model"): TextSelector(
                    TextSelectorConfig(type="text")
                ),
                vol.Optional(
                    CONF_RAG_ENABLED, default=current_rag_enabled
                ): BooleanSelector(),
            }

            return self.async_show_form(
                step_id="configure_options",
                data_schema=vol.Schema(schema_dict),
                errors=errors,
                description_placeholders={
                    "token_label": token_label,
                    "provider": PROVIDERS[provider],
                },
            )

        if provider == "local":
            # For local provider, we need both URL and optional model name
            current_url = self.config_entry.data.get(CONF_LOCAL_URL, "")

            schema_dict = {
                vol.Required(CONF_LOCAL_URL, default=current_url): TextSelector(
                    TextSelectorConfig(type="text")
                ),
            }

            # Add model selection
            model_options = get_model_options_for_flow("local")
            schema_dict[
                vol.Optional(
                    "model", default=current_model if current_model else "Custom..."
                )
            ] = SelectSelector(SelectSelectorConfig(options=model_options))
            schema_dict[vol.Optional("custom_model")] = TextSelector(
                TextSelectorConfig(type="text")
            )
            schema_dict[vol.Optional(CONF_RAG_ENABLED, default=current_rag_enabled)] = (
                BooleanSelector()
            )

            return self.async_show_form(
                step_id="configure_options",
                data_schema=vol.Schema(schema_dict),
                errors=errors,
                description_placeholders={
                    "token_label": "Local API URL",
                    "provider": PROVIDERS[provider],
                },
            )

        # Build schema for other providers
        schema_dict = {
            vol.Required(token_field, default=display_token): TextSelector(
                TextSelectorConfig(type="password")
            ),
        }

        # Add model selection if available
        if available_models:
            # Add predefined models + custom option (avoid duplicating "Custom...")
            if "Custom..." in available_models:
                model_options = available_models
            else:
                model_options = available_models + ["Custom..."]
            schema_dict[vol.Optional("model", default=current_model)] = SelectSelector(
                SelectSelectorConfig(options=model_options)
            )
            schema_dict[vol.Optional("custom_model")] = TextSelector(
                TextSelectorConfig(type="text")
            )

        # Add RAG option for all providers
        schema_dict[vol.Optional(CONF_RAG_ENABLED, default=current_rag_enabled)] = (
            BooleanSelector()
        )

        return self.async_show_form(
            step_id="configure_options",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "token_label": token_label,
                "provider": PROVIDERS[provider],
            },
        )
