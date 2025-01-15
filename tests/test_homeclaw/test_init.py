"""Test for Homeclaw setup."""

import json
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from homeassistant.core import HomeAssistant, ServiceCall, Context
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from custom_components.homeclaw.const import DOMAIN, CONF_RAG_ENABLED
from custom_components.homeclaw import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
    async_migrate_entry,
)


class TestAsyncSetup:
    """Tests for async_setup function."""

    @pytest.mark.asyncio
    async def test_async_setup_returns_true(self):
        """Test async_setup always returns True."""
        mock_hass = MagicMock()
        mock_config = MagicMock()

        result = await async_setup(mock_hass, mock_config)

        assert result is True


class TestAsyncMigrateEntry:
    """Tests for async_migrate_entry function."""

    @pytest.mark.asyncio
    async def test_migrate_entry_version_1(self):
        """Test migration for version 1 entries."""
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.version = 1

        result = await async_migrate_entry(mock_hass, mock_entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_migrate_entry_future_version(self):
        """Test migration for future version entries."""
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.version = 2

        result = await async_migrate_entry(mock_hass, mock_entry)

        assert result is True


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        return hass

    @pytest.fixture
    def mock_entry(self):
        """Create a mock config entry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 1
        entry.data = {
            "ai_provider": "openai",
            "openai_token": "test_token",
        }
        entry.entry_id = "test_entry_id"
        return entry

    @pytest.mark.asyncio
    async def test_setup_entry_openai_provider(self, mock_hass, mock_entry):
        """Test setup with OpenAI provider."""
        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert DOMAIN in mock_hass.data
            assert "agents" in mock_hass.data[DOMAIN]
            assert "openai" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_anthropic_provider(self, mock_hass):
        """Test setup with Anthropic provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "anthropic",
            "anthropic_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "anthropic" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_anthropic_oauth_provider(self, mock_hass):
        """Test setup with Anthropic OAuth provider passes entry."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "anthropic_oauth",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            # OAuth providers should pass entry to agent constructor
            mock_agent.assert_called_once()
            call_args = mock_agent.call_args
            assert len(call_args[0]) == 3  # hass, config, entry

    @pytest.mark.asyncio
    async def test_setup_entry_gemini_oauth_provider(self, mock_hass):
        """Test setup with Gemini OAuth provider passes entry."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "gemini_oauth",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            # OAuth providers should pass entry to agent constructor
            mock_agent.assert_called_once()
            call_args = mock_agent.call_args
            assert len(call_args[0]) == 3  # hass, config, entry

    @pytest.mark.asyncio
    async def test_setup_entry_missing_ai_provider(self, mock_hass):
        """Test setup fails when ai_provider is missing."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {"openai_token": "test_token"}  # Missing ai_provider
        mock_entry.entry_id = "test_entry_id"

        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(mock_hass, mock_entry)

        assert "ai_provider" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_entry_unknown_provider(self, mock_hass):
        """Test setup fails with unknown provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "unknown_provider",
        }
        mock_entry.entry_id = "test_entry_id"

        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(mock_hass, mock_entry)

        assert "Unknown AI provider" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_entry_local_provider(self, mock_hass):
        """Test setup with local provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "local",
            "local_url": "http://localhost:11434/api/generate",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "local" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_gemini_provider(self, mock_hass):
        """Test setup with Gemini provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "gemini",
            "gemini_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "gemini" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_openrouter_provider(self, mock_hass):
        """Test setup with OpenRouter provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "openrouter",
            "openrouter_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "openrouter" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_llama_provider(self, mock_hass):
        """Test setup with Llama provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "llama",
            "llama_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "llama" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_alter_provider(self, mock_hass):
        """Test setup with Alter provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "alter",
            "alter_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "alter" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_zai_provider(self, mock_hass):
        """Test setup with Z.AI provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 1
        mock_entry.data = {
            "ai_provider": "zai",
            "zai_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert "zai" in mock_hass.data[DOMAIN]["agents"]

    @pytest.mark.asyncio
    async def test_setup_entry_with_rag_enabled(self, mock_hass, mock_entry):
        """Test setup with RAG enabled."""
        mock_entry.data[CONF_RAG_ENABLED] = True

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            with patch("custom_components.homeclaw._initialize_rag", new_callable=AsyncMock) as mock_rag:
                result = await async_setup_entry(mock_hass, mock_entry)

                assert result is True
                mock_rag.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_with_rag_disabled(self, mock_hass, mock_entry):
        """Test setup with RAG disabled."""
        mock_entry.data[CONF_RAG_ENABLED] = False

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            with patch("custom_components.homeclaw._initialize_rag", new_callable=AsyncMock) as mock_rag:
                result = await async_setup_entry(mock_hass, mock_entry)

                assert result is True
                mock_rag.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_entry_incompatible_version(self, mock_hass):
        """Test setup logs warning for incompatible version."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.version = 99  # Unknown version
        mock_entry.data = {
            "ai_provider": "openai",
            "openai_token": "test_token",
        }
        mock_entry.entry_id = "test_entry_id"

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            with patch("custom_components.homeclaw._LOGGER") as mock_logger:
                result = await async_setup_entry(mock_hass, mock_entry)

                assert result is True
                # Should log warning about version
                warning_calls = [c for c in mock_logger.warning.call_args_list
                               if "version" in str(c).lower()]
                assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_setup_entry_agent_creation_error(self, mock_hass, mock_entry):
        """Test setup handles agent creation errors."""
        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_agent.side_effect = Exception("Agent creation failed")

            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(mock_hass, mock_entry)

    @pytest.mark.asyncio
    async def test_setup_entry_initializes_hass_data(self, mock_hass, mock_entry):
        """Test setup initializes hass.data structure correctly."""
        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            await async_setup_entry(mock_hass, mock_entry)

            assert DOMAIN in mock_hass.data
            assert "agents" in mock_hass.data[DOMAIN]
            assert "configs" in mock_hass.data[DOMAIN]
            assert "_ws_registered" in mock_hass.data[DOMAIN]


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    @pytest.fixture
    def mock_hass_with_agent(self):
        """Create a mock HomeAssistant with agent registered."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {"openai": {"ai_provider": "openai"}},
                "_ws_registered": True,
            }
        }
        hass.services = MagicMock()
        hass.services.async_remove = MagicMock()
        return hass

    @pytest.mark.asyncio
    async def test_unload_entry_success(self, mock_hass_with_agent):
        """Test successful unload of entry."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "openai"}

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=False):
                result = await async_unload_entry(mock_hass_with_agent, mock_entry)

        assert result is True
        # DOMAIN should be removed entirely
        assert DOMAIN not in mock_hass_with_agent.data

    @pytest.mark.asyncio
    async def test_unload_entry_removes_data(self, mock_hass_with_agent):
        """Test unload removes all domain data."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "openai"}

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=False):
                await async_unload_entry(mock_hass_with_agent, mock_entry)

        # DOMAIN should be removed entirely
        assert DOMAIN not in mock_hass_with_agent.data

    @pytest.mark.asyncio
    async def test_unload_entry_nonexistent_provider(self, mock_hass_with_agent):
        """Test unload with nonexistent provider."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "nonexistent"}

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=False):
                # Should not raise error
                result = await async_unload_entry(mock_hass_with_agent, mock_entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_unload_entry_removes_services(self, mock_hass_with_agent):
        """Test unload removes all services."""
        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "openai"}

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=False):
                result = await async_unload_entry(mock_hass_with_agent, mock_entry)

                assert result is True
                # Verify all services were removed
                service_calls = mock_hass_with_agent.services.async_remove.call_args_list
                removed_services = [call[0][1] for call in service_calls]

                expected_services = [
                    "query",
                    "create_automation",
                    "save_prompt_history",
                    "load_prompt_history",
                    "create_dashboard",
                    "update_dashboard",
                    "rag_reindex"
                ]

                for service in expected_services:
                    assert service in removed_services

    @pytest.mark.asyncio
    async def test_unload_entry_cleans_storage_cache(self):
        """Test unload cleans up storage cache instances."""
        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {},
            },
            f"{DOMAIN}_storage_cache_1": {},
            f"{DOMAIN}_storage_cache_2": {},
            "other_key": {}
        }
        mock_hass.services = MagicMock()
        mock_hass.services.async_remove = MagicMock()

        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "openai"}

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=False):
                result = await async_unload_entry(mock_hass, mock_entry)

                assert result is True
                # Verify storage cache keys were removed
                assert f"{DOMAIN}_storage_cache_1" not in mock_hass.data
                assert f"{DOMAIN}_storage_cache_2" not in mock_hass.data
                # Verify other keys remain
                assert "other_key" in mock_hass.data
                # Verify domain was removed
                assert DOMAIN not in mock_hass.data


class TestServiceHandlers:
    """Tests for service handlers."""

    @pytest.fixture
    def mock_hass_with_agent(self):
        """Create a mock HomeAssistant with agent."""
        mock_agent = MagicMock()
        mock_agent.process_query = AsyncMock(return_value={"success": True, "answer": "Test response"})
        mock_agent.create_automation = AsyncMock(return_value={"success": True})
        mock_agent.create_dashboard = AsyncMock(return_value={"success": True})
        mock_agent.save_user_prompt_history = AsyncMock(return_value={"success": True})
        mock_agent.load_user_prompt_history = AsyncMock(return_value={"history": []})

        hass = MagicMock(spec=HomeAssistant)
        hass.data = {
            DOMAIN: {
                "agents": {"openai": mock_agent},
                "configs": {"openai": {"ai_provider": "openai"}},
                "_ws_registered": True,
            }
        }
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()
        return hass, mock_agent

    @pytest.mark.asyncio
    async def test_service_query_calls_agent(self, mock_hass_with_agent):
        """Test query service calls agent.process_query."""
        hass, mock_agent = mock_hass_with_agent

        # Simulate service call
        service_call = MagicMock(spec=ServiceCall)
        service_call.data = {"prompt": "Test query", "provider": "openai"}
        service_call.context = MagicMock()
        service_call.context.user_id = "test_user"

        # Get the service handler from setup_entry
        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            # Get registered service handler
            query_handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "query":
                    query_handler = call[0][2]
                    break

            assert query_handler is not None

            # Call the handler
            await query_handler(service_call)

            # Verify agent was called
            mock_agent.process_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_query_no_agents(self):
        """Test query service when no agents configured."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        # Setup with mocked agent that will be cleared
        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            # Get registered service handler
            query_handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "query":
                    query_handler = call[0][2]
                    break

            # Clear agents to simulate no agents state
            hass.data[DOMAIN]["agents"] = {}

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"prompt": "Test query"}
            service_call.context = MagicMock()

            await query_handler(service_call)

            # Should fire error event
            hass.bus.async_fire.assert_called()
            call_args = hass.bus.async_fire.call_args[0]
            assert "error" in call_args[1]

    @pytest.mark.asyncio
    async def test_service_query_fallback_provider(self, mock_hass_with_agent):
        """Test query service falls back to first available provider."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            query_handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "query":
                    query_handler = call[0][2]
                    break

            # Call with non-existent provider
            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"prompt": "Test", "provider": "nonexistent"}
            service_call.context = MagicMock()

            await query_handler(service_call)

            # Should still call agent (fallback to openai)
            mock_agent.process_query.assert_called()

    @pytest.mark.asyncio
    async def test_service_create_automation(self, mock_hass_with_agent):
        """Test create_automation service."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            # Get create_automation handler
            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "create_automation":
                    handler = call[0][2]
                    break

            assert handler is not None

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "automation": {"alias": "Test"},
                "provider": "openai"
            }
            service_call.context = MagicMock()

            await handler(service_call)

            mock_agent.create_automation.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_create_dashboard(self, mock_hass_with_agent):
        """Test create_dashboard service."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "create_dashboard":
                    handler = call[0][2]
                    break

            assert handler is not None

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_config": {"title": "Test"},
                "provider": "openai"
            }
            service_call.context = MagicMock()

            await handler(service_call)

            mock_agent.create_dashboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_create_dashboard_json_string(self, mock_hass_with_agent):
        """Test create_dashboard with JSON string config."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "create_dashboard":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_config": '{"title": "Test"}',  # JSON string
                "provider": "openai"
            }
            service_call.context = MagicMock()

            await handler(service_call)

            # Should parse JSON and call agent
            mock_agent.create_dashboard.assert_called_once()
            call_args = mock_agent.create_dashboard.call_args[0][0]
            assert call_args["title"] == "Test"

    @pytest.mark.asyncio
    async def test_service_save_prompt_history(self, mock_hass_with_agent):
        """Test save_prompt_history service."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "save_prompt_history":
                    handler = call[0][2]
                    break

            assert handler is not None

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "history": [{"role": "user", "content": "Test"}],
                "provider": "openai"
            }
            service_call.context = MagicMock()
            service_call.context.user_id = "test_user"

            await handler(service_call)

            mock_agent.save_user_prompt_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_load_prompt_history(self, mock_hass_with_agent):
        """Test load_prompt_history service."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "load_prompt_history":
                    handler = call[0][2]
                    break

            assert handler is not None

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"provider": "openai"}
            service_call.context = MagicMock()
            service_call.context.user_id = "test_user"

            await handler(service_call)

            mock_agent.load_user_prompt_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_handler_exception(self, mock_hass_with_agent):
        """Test service handler handles exceptions."""
        hass, mock_agent = mock_hass_with_agent
        mock_agent.process_query = AsyncMock(side_effect=Exception("Test error"))

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            query_handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "query":
                    query_handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"prompt": "Test"}
            service_call.context = MagicMock()

            await query_handler(service_call)

            # Should fire error event
            hass.bus.async_fire.assert_called()
            call_args = hass.bus.async_fire.call_args[0]
            assert "error" in call_args[1]

    @pytest.mark.asyncio
    async def test_service_update_dashboard(self, mock_hass_with_agent):
        """Test update_dashboard service."""
        hass, mock_agent = mock_hass_with_agent
        mock_agent.update_dashboard = AsyncMock(return_value={"success": True})

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "update_dashboard":
                    handler = call[0][2]
                    break

            assert handler is not None

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_url": "lovelace-test",
                "dashboard_config": {"title": "Updated"},
                "provider": "openai"
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            mock_agent.update_dashboard.assert_called_once_with(
                "lovelace-test",
                {"title": "Updated"}
            )
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_service_update_dashboard_json_string(self, mock_hass_with_agent):
        """Test update_dashboard with JSON string config."""
        hass, mock_agent = mock_hass_with_agent
        mock_agent.update_dashboard = AsyncMock(return_value={"success": True})

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "update_dashboard":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_url": "lovelace-test",
                "dashboard_config": '{"title": "Updated"}',
                "provider": "openai"
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should parse JSON and call agent
            mock_agent.update_dashboard.assert_called_once()
            call_args = mock_agent.update_dashboard.call_args[0]
            assert call_args[1]["title"] == "Updated"

    @pytest.mark.asyncio
    async def test_service_update_dashboard_missing_url(self, mock_hass_with_agent):
        """Test update_dashboard without dashboard_url."""
        hass, mock_agent = mock_hass_with_agent
        mock_agent.update_dashboard = AsyncMock(return_value={"success": True})

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "update_dashboard":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_config": {"title": "Test"},
                "provider": "openai"
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "required" in result["error"].lower()
            mock_agent.update_dashboard.assert_not_called()

    @pytest.mark.asyncio
    async def test_service_update_dashboard_invalid_json(self, mock_hass_with_agent):
        """Test update_dashboard with invalid JSON string."""
        hass, mock_agent = mock_hass_with_agent
        mock_agent.update_dashboard = AsyncMock(return_value={"success": True})

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "update_dashboard":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_url": "test",
                "dashboard_config": '{invalid json}',
                "provider": "openai"
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return JSON error
            assert "error" in result
            assert "Invalid JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_service_update_dashboard_no_agents(self):
        """Test update_dashboard when no agents configured."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "update_dashboard":
                    handler = call[0][2]
                    break

            # Clear agents
            hass.data[DOMAIN]["agents"] = {}

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_url": "test",
                "dashboard_config": {"title": "Test"}
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "No AI agents" in result["error"]

    @pytest.mark.asyncio
    async def test_service_update_dashboard_exception(self, mock_hass_with_agent):
        """Test update_dashboard handles exceptions."""
        hass, mock_agent = mock_hass_with_agent
        mock_agent.update_dashboard = AsyncMock(side_effect=Exception("Update failed"))

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "update_dashboard":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_url": "test",
                "dashboard_config": {"title": "Test"},
                "provider": "openai"
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "Update failed" in result["error"]

    @pytest.mark.asyncio
    async def test_service_rag_reindex(self):
        """Test rag_reindex service."""
        hass = MagicMock(spec=HomeAssistant)
        mock_rag_manager = MagicMock()
        mock_rag_manager.full_reindex = AsyncMock()
        mock_rag_manager.get_stats = AsyncMock(return_value={"total_documents": 42})

        hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {},
                "_ws_registered": True,
                "rag_manager": mock_rag_manager
            }
        }
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "rag_reindex":
                    handler = call[0][2]
                    break

            assert handler is not None

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {}
            service_call.context = MagicMock()

            result = await handler(service_call)

            mock_rag_manager.full_reindex.assert_called_once()
            mock_rag_manager.get_stats.assert_called_once()
            assert result["success"] is True
            assert result["entities_indexed"] == 42

    @pytest.mark.asyncio
    async def test_service_rag_reindex_not_initialized(self):
        """Test rag_reindex when RAG not initialized."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {},
                "_ws_registered": True,
            }
        }
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "rag_reindex":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {}
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_service_rag_reindex_exception(self):
        """Test rag_reindex handles exceptions."""
        hass = MagicMock(spec=HomeAssistant)
        mock_rag_manager = MagicMock()
        mock_rag_manager.full_reindex = AsyncMock(side_effect=Exception("Reindex failed"))

        hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {},
                "_ws_registered": True,
                "rag_manager": mock_rag_manager
            }
        }
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "rag_reindex":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {}
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "Reindex failed" in result["error"]

    @pytest.mark.asyncio
    async def test_service_registration(self, mock_hass_with_agent):
        """Test all services are registered."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            # Collect all registered service names
            registered_services = set()
            for call in hass.services.async_register.call_args_list:
                service_name = call[0][1]
                registered_services.add(service_name)

            # Verify all expected services are registered
            expected_services = {
                "query",
                "create_automation",
                "save_prompt_history",
                "load_prompt_history",
                "create_dashboard",
                "update_dashboard",
                "rag_reindex"
            }

            assert registered_services == expected_services

    @pytest.mark.asyncio
    async def test_service_create_dashboard_invalid_json(self, mock_hass_with_agent):
        """Test create_dashboard with invalid JSON string."""
        hass, mock_agent = mock_hass_with_agent

        with patch("custom_components.homeclaw.HomeclawAgent", return_value=mock_agent):
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "create_dashboard":
                    handler = call[0][2]
                    break

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {
                "dashboard_config": '{invalid json}',
                "provider": "openai"
            }
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return JSON error
            assert "error" in result
            assert "Invalid JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_service_create_automation_no_agents(self):
        """Test create_automation when no agents configured."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "create_automation":
                    handler = call[0][2]
                    break

            # Clear agents
            hass.data[DOMAIN]["agents"] = {}

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"automation": {"alias": "Test"}}
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "No AI agents" in result["error"]

    @pytest.mark.asyncio
    async def test_service_create_dashboard_no_agents(self):
        """Test create_dashboard when no agents configured."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "create_dashboard":
                    handler = call[0][2]
                    break

            # Clear agents
            hass.data[DOMAIN]["agents"] = {}

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"dashboard_config": {"title": "Test"}}
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "No AI agents" in result["error"]

    @pytest.mark.asyncio
    async def test_service_save_prompt_history_no_agents(self):
        """Test save_prompt_history when no agents configured."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "save_prompt_history":
                    handler = call[0][2]
                    break

            # Clear agents
            hass.data[DOMAIN]["agents"] = {}

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {"history": []}
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "No AI agents" in result["error"]

    @pytest.mark.asyncio
    async def test_service_load_prompt_history_no_agents(self):
        """Test load_prompt_history when no agents configured."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.bus = MagicMock()
        hass.config = MagicMock()
        hass.config.path = MagicMock(return_value="/mock/path")
        hass.http = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        with patch("custom_components.homeclaw.HomeclawAgent") as mock_agent:
            mock_entry = MagicMock(spec=ConfigEntry)
            mock_entry.version = 1
            mock_entry.data = {"ai_provider": "openai", "openai_token": "test"}
            mock_entry.entry_id = "test"

            await async_setup_entry(hass, mock_entry)

            handler = None
            for call in hass.services.async_register.call_args_list:
                if call[0][1] == "load_prompt_history":
                    handler = call[0][2]
                    break

            # Clear agents
            hass.data[DOMAIN]["agents"] = {}

            service_call = MagicMock(spec=ServiceCall)
            service_call.data = {}
            service_call.context = MagicMock()

            result = await handler(service_call)

            # Should return error
            assert "error" in result
            assert "No AI agents" in result["error"]


class TestRAGHelpers:
    """Tests for RAG helper functions."""

    @pytest.mark.asyncio
    async def test_initialize_rag_success(self):
        """Test successful RAG initialization."""
        from custom_components.homeclaw import _initialize_rag

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {
            DOMAIN: {
                "agents": {
                    "openai": MagicMock(set_rag_manager=MagicMock())
                }
            }
        }

        mock_entry = MagicMock(spec=ConfigEntry)
        config_data = {"test": "config"}

        mock_rag_manager = MagicMock()
        mock_rag_manager.async_initialize = AsyncMock()
        mock_rag_manager.get_stats = AsyncMock(return_value={"indexed_entities": 42})

        # Patch the RAGManager import inside the function
        with patch("custom_components.homeclaw.rag.RAGManager", return_value=mock_rag_manager):
            await _initialize_rag(mock_hass, config_data, mock_entry)

            # Verify RAG manager was initialized
            mock_rag_manager.async_initialize.assert_called_once()
            mock_rag_manager.get_stats.assert_called_once()

            # Verify RAG manager was stored
            assert mock_hass.data[DOMAIN]["rag_manager"] == mock_rag_manager

            # Verify agents were connected
            mock_hass.data[DOMAIN]["agents"]["openai"].set_rag_manager.assert_called_once_with(mock_rag_manager)

    @pytest.mark.asyncio
    async def test_initialize_rag_import_error(self):
        """Test RAG initialization with ImportError."""
        from custom_components.homeclaw import _initialize_rag

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {DOMAIN: {"agents": {}}}
        mock_entry = MagicMock(spec=ConfigEntry)
        config_data = {}

        # Mock the import to raise ImportError
        import sys
        with patch.dict(sys.modules, {"custom_components.homeclaw.rag": None}):
            with patch("custom_components.homeclaw._LOGGER") as mock_logger:
                # Should not raise, just log warning
                await _initialize_rag(mock_hass, config_data, mock_entry)

                # Verify warning was logged
                mock_logger.warning.assert_called()
                call_args = str(mock_logger.warning.call_args)
                assert "unavailable" in call_args.lower() or "missing dependencies" in call_args.lower()

    @pytest.mark.asyncio
    async def test_initialize_rag_general_exception(self):
        """Test RAG initialization with general exception."""
        from custom_components.homeclaw import _initialize_rag

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {DOMAIN: {"agents": {}}}
        mock_entry = MagicMock(spec=ConfigEntry)
        config_data = {}

        mock_rag_manager = MagicMock()
        mock_rag_manager.async_initialize = AsyncMock(side_effect=Exception("Init failed"))

        with patch("custom_components.homeclaw.rag.RAGManager", return_value=mock_rag_manager):
            with patch("custom_components.homeclaw._LOGGER") as mock_logger:
                # Should not raise, just log warning
                await _initialize_rag(mock_hass, config_data, mock_entry)

                # Verify warning was logged
                mock_logger.warning.assert_called()
                call_args = str(mock_logger.warning.call_args)
                assert "failed" in call_args.lower()

    @pytest.mark.asyncio
    async def test_shutdown_rag_success(self):
        """Test successful RAG shutdown."""
        from custom_components.homeclaw import _shutdown_rag

        mock_rag_manager = MagicMock()
        mock_rag_manager.async_shutdown = AsyncMock()

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {
            DOMAIN: {
                "rag_manager": mock_rag_manager
            }
        }

        await _shutdown_rag(mock_hass)

        # Verify shutdown was called
        mock_rag_manager.async_shutdown.assert_called_once()

        # Verify RAG manager was removed from hass.data
        assert "rag_manager" not in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_shutdown_rag_no_domain(self):
        """Test RAG shutdown when DOMAIN not in hass.data."""
        from custom_components.homeclaw import _shutdown_rag

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {}

        # Should not raise
        await _shutdown_rag(mock_hass)

    @pytest.mark.asyncio
    async def test_shutdown_rag_no_manager(self):
        """Test RAG shutdown when no RAG manager exists."""
        from custom_components.homeclaw import _shutdown_rag

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {DOMAIN: {}}

        # Should not raise
        await _shutdown_rag(mock_hass)

    @pytest.mark.asyncio
    async def test_shutdown_rag_exception(self):
        """Test RAG shutdown handles exceptions."""
        from custom_components.homeclaw import _shutdown_rag

        mock_rag_manager = MagicMock()
        mock_rag_manager.async_shutdown = AsyncMock(side_effect=Exception("Shutdown failed"))

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {
            DOMAIN: {
                "rag_manager": mock_rag_manager
            }
        }

        with patch("custom_components.homeclaw._LOGGER") as mock_logger:
            # Should not raise
            await _shutdown_rag(mock_hass)

            # Verify warning was logged
            mock_logger.warning.assert_called()

            # Verify RAG manager was still removed
            assert "rag_manager" not in mock_hass.data[DOMAIN]


class TestPanelHelpers:
    """Tests for panel helper functions."""

    @pytest.mark.asyncio
    async def test_panel_exists_true(self):
        """Test _panel_exists returns True when panel exists."""
        from custom_components.homeclaw import _panel_exists

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = MagicMock()
        mock_hass.data.get = MagicMock(return_value={"test_panel": {}})

        result = await _panel_exists(mock_hass, "test_panel")

        assert result is True

    @pytest.mark.asyncio
    async def test_panel_exists_false(self):
        """Test _panel_exists returns False when panel doesn't exist."""
        from custom_components.homeclaw import _panel_exists

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = MagicMock()
        mock_hass.data.get = MagicMock(return_value={})

        result = await _panel_exists(mock_hass, "nonexistent_panel")

        assert result is False

    @pytest.mark.asyncio
    async def test_panel_exists_no_frontend_panels(self):
        """Test _panel_exists when frontend_panels doesn't exist."""
        from custom_components.homeclaw import _panel_exists

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = MagicMock(spec=["some_attr"])
        # hasattr will return False for frontend_panels

        result = await _panel_exists(mock_hass, "test_panel")

        assert result is False

    @pytest.mark.asyncio
    async def test_panel_exists_exception(self):
        """Test _panel_exists handles exceptions."""
        from custom_components.homeclaw import _panel_exists

        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = MagicMock()
        mock_hass.data.get = MagicMock(side_effect=Exception("Get failed"))

        with patch("custom_components.homeclaw._LOGGER") as mock_logger:
            result = await _panel_exists(mock_hass, "test_panel")

            # Should return False on exception
            assert result is False

            # Should log debug message
            mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_unload_entry_with_panel(self):
        """Test unload entry removes panel if it exists."""
        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {},
            }
        }
        mock_hass.services = MagicMock()
        mock_hass.services.async_remove = MagicMock()

        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "openai"}

        mock_async_remove_panel = MagicMock()

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=True):
                with patch("homeassistant.components.frontend.async_remove_panel", mock_async_remove_panel):
                    result = await async_unload_entry(mock_hass, mock_entry)

                    assert result is True
                    mock_async_remove_panel.assert_called_once_with(mock_hass, "homeclaw")

    @pytest.mark.asyncio
    async def test_unload_entry_panel_removal_exception(self):
        """Test unload entry handles panel removal exceptions."""
        mock_hass = MagicMock(spec=HomeAssistant)
        mock_hass.data = {
            DOMAIN: {
                "agents": {"openai": MagicMock()},
                "configs": {},
            }
        }
        mock_hass.services = MagicMock()

        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.data = {"ai_provider": "openai"}

        with patch("custom_components.homeclaw._shutdown_rag", new_callable=AsyncMock):
            with patch("custom_components.homeclaw._panel_exists", new_callable=AsyncMock, return_value=True):
                with patch("homeassistant.components.frontend.async_remove_panel", side_effect=Exception("Panel removal failed")):
                    with patch("custom_components.homeclaw._LOGGER") as mock_logger:
                        # Should not raise
                        result = await async_unload_entry(mock_hass, mock_entry)

                        assert result is True
                        # Should log debug message
                        mock_logger.debug.assert_called()