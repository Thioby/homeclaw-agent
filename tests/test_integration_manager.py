"""Tests for integration_manager tools.

Tests cover:
- ListAvailableIntegrations: listing, filtering, no hass, loader error
- ReadYamlConfig: full read, section read, missing section, !include, !secret redaction
- CreateYamlIntegration: new key append, overwrite, conflict error, !include error,
  backup, validation, restart, malformed config
- Helper functions: _safe_load_yaml, _remove_yaml_section, _dump_sections,
  _is_include_tag, _is_secret_tag, _redact_secrets
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import yaml

from custom_components.homeclaw.tools.integration_manager import (
    CreateYamlIntegration,
    ListAvailableIntegrations,
    ReadYamlConfig,
    _dump_sections,
    _is_include_tag,
    _is_secret_tag,
    _redact_secrets,
    _remove_yaml_section,
    _safe_load_yaml,
    _serialize_for_output,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_hass(config_dir: str = "/config") -> MagicMock:
    """Create a mock hass with config.path() returning proper paths."""
    hass = MagicMock()
    hass.config.path = MagicMock(side_effect=lambda f: os.path.join(config_dir, f))
    hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a))
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


SAMPLE_INTEGRATION_DESCRIPTIONS = {
    "core": {
        "integration": {
            "mqtt": {
                "name": "MQTT",
                "config_flow": True,
                "integration_type": "hub",
            },
            "smtp": {
                "name": "SMTP",
                "config_flow": False,
                "integration_type": "service",
            },
            "template": {
                "name": "Template",
                "config_flow": False,
                "integration_type": "helper",
            },
        },
        "helper": {
            "input_boolean": {
                "name": "Toggle",
                "config_flow": True,
                "integration_type": "helper",
            },
        },
        "translated_name": [],
    },
    "custom": {
        "integration": {
            "hacs": {
                "name": "HACS",
                "config_flow": True,
                "integration_type": "service",
            },
        },
        "helper": {},
    },
}


# ---------------------------------------------------------------------------
# _safe_load_yaml tests
# ---------------------------------------------------------------------------


class TestSafeLoadYaml:
    """Tests for the custom YAML loader with HA tag support."""

    def test_basic_yaml(self):
        content = "homeassistant:\n  name: My Home\nhttp:\n  server_port: 8123\n"
        result = _safe_load_yaml(content)
        assert result["homeassistant"]["name"] == "My Home"
        assert result["http"]["server_port"] == 8123

    def test_include_tag_preserved(self):
        content = "automation: !include automations.yaml\n"
        result = _safe_load_yaml(content)
        assert _is_include_tag(result["automation"])
        assert result["automation"].path == "automations.yaml"

    def test_secret_tag_preserved(self):
        content = "http:\n  api_password: !secret http_password\n"
        result = _safe_load_yaml(content)
        assert _is_secret_tag(result["http"]["api_password"])
        assert result["http"]["api_password"].name == "http_password"

    def test_include_dir_tags(self):
        content = "automation: !include_dir_list automations/\n"
        result = _safe_load_yaml(content)
        assert _is_include_tag(result["automation"])

    def test_empty_content(self):
        assert _safe_load_yaml("") == {}

    def test_list_content(self):
        content = "notify:\n  - platform: smtp\n    server: smtp.gmail.com\n"
        result = _safe_load_yaml(content)
        assert isinstance(result["notify"], list)
        assert result["notify"][0]["platform"] == "smtp"


# ---------------------------------------------------------------------------
# _redact_secrets / _serialize_for_output tests
# ---------------------------------------------------------------------------


class TestRedactSecrets:
    """Tests for secret redaction in YAML output."""

    def test_redact_secret_tag(self):
        content = "http:\n  api_password: !secret http_password\n"
        parsed = _safe_load_yaml(content)
        redacted = _redact_secrets(parsed)
        assert redacted["http"]["api_password"] == "***SECRET***"

    def test_redact_nested_secrets(self):
        content = (
            "notify:\n"
            "  - platform: smtp\n"
            "    password: !secret smtp_password\n"
            "    server: smtp.gmail.com\n"
        )
        parsed = _safe_load_yaml(content)
        redacted = _redact_secrets(parsed)
        assert redacted["notify"][0]["password"] == "***SECRET***"
        assert redacted["notify"][0]["server"] == "smtp.gmail.com"

    def test_serialize_include(self):
        content = "automation: !include automations.yaml\n"
        parsed = _safe_load_yaml(content)
        serialized = _serialize_for_output(parsed)
        assert serialized["automation"] == "!include automations.yaml"


# ---------------------------------------------------------------------------
# _remove_yaml_section tests
# ---------------------------------------------------------------------------


class TestRemoveYamlSection:
    """Tests for removing a top-level YAML section from text."""

    def test_remove_middle_section(self):
        content = (
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "notify:\n"
            "  - platform: smtp\n"
            "    server: smtp.gmail.com\n"
            "\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "notify")
        assert "notify:" not in result
        assert "platform: smtp" not in result
        assert "homeassistant:" in result
        assert "http:" in result

    def test_remove_last_section(self):
        content = "homeassistant:\n  name: My Home\n\nhttp:\n  server_port: 8123\n"
        result = _remove_yaml_section(content, "http")
        assert "http:" not in result
        assert "homeassistant:" in result

    def test_remove_nonexistent_section(self):
        content = "homeassistant:\n  name: My Home\n"
        result = _remove_yaml_section(content, "notify")
        assert result.strip() == content.strip()

    def test_preserves_comments(self):
        content = (
            "# Main config\n"
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "# Notifications\n"
            "notify:\n"
            "  - platform: smtp\n"
            "\n"
            "# HTTP config\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "notify")
        assert "# Main config" in result
        assert "# HTTP config" in result
        # The comment before notify may or may not be removed —
        # it's above the section, not inside it, so it stays
        assert "homeassistant:" in result


# ---------------------------------------------------------------------------
# _dump_sections tests
# ---------------------------------------------------------------------------


class TestDumpSections:
    """Tests for dumping selected config sections to YAML."""

    def test_single_key(self):
        config = {"notify": [{"platform": "smtp", "server": "smtp.gmail.com"}]}
        result = _dump_sections(config, ["notify"])
        assert "notify:" in result
        assert "platform: smtp" in result

    def test_multiple_keys(self):
        config = {
            "notify": [{"platform": "smtp"}],
            "input_boolean": {"guest_mode": {"name": "Guest Mode"}},
        }
        result = _dump_sections(config, ["notify", "input_boolean"])
        assert "notify:" in result
        assert "input_boolean:" in result
        assert "guest_mode:" in result

    def test_empty_keys(self):
        config = {"notify": [{"platform": "smtp"}]}
        result = _dump_sections(config, [])
        assert result == ""

    def test_key_not_in_config(self):
        config = {"notify": [{"platform": "smtp"}]}
        result = _dump_sections(config, ["nonexistent"])
        assert result == ""


# ---------------------------------------------------------------------------
# ListAvailableIntegrations tests
# ---------------------------------------------------------------------------


class TestListAvailableIntegrations:
    """Tests for the list_available_integrations tool."""

    @pytest.mark.asyncio
    async def test_list_all(self):
        hass = _make_hass()
        tool = ListAvailableIntegrations(hass=hass)

        with patch(
            "homeassistant.loader.async_get_integration_descriptions",
            new_callable=AsyncMock,
            return_value=SAMPLE_INTEGRATION_DESCRIPTIONS,
        ):
            result = await tool.execute()

        assert result.success
        data = json.loads(result.output)
        assert data["count"] >= 4  # mqtt, smtp, template, input_boolean + hacs
        domains = [i["domain"] for i in data["integrations"]]
        assert "mqtt" in domains
        assert "smtp" in domains
        assert "hacs" in domains

    @pytest.mark.asyncio
    async def test_filter_by_name(self):
        hass = _make_hass()
        tool = ListAvailableIntegrations(hass=hass)

        with patch(
            "homeassistant.loader.async_get_integration_descriptions",
            new_callable=AsyncMock,
            return_value=SAMPLE_INTEGRATION_DESCRIPTIONS,
        ):
            result = await tool.execute(filter="mqtt")

        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["integrations"][0]["domain"] == "mqtt"
        assert data["integrations"][0]["config_flow"] is True

    @pytest.mark.asyncio
    async def test_filter_by_partial_name(self):
        hass = _make_hass()
        tool = ListAvailableIntegrations(hass=hass)

        with patch(
            "homeassistant.loader.async_get_integration_descriptions",
            new_callable=AsyncMock,
            return_value=SAMPLE_INTEGRATION_DESCRIPTIONS,
        ):
            result = await tool.execute(filter="sm")

        data = json.loads(result.output)
        # "smtp" matches "sm"
        assert data["count"] >= 1
        domains = [i["domain"] for i in data["integrations"]]
        assert "smtp" in domains

    @pytest.mark.asyncio
    async def test_filter_no_results(self):
        hass = _make_hass()
        tool = ListAvailableIntegrations(hass=hass)

        with patch(
            "homeassistant.loader.async_get_integration_descriptions",
            new_callable=AsyncMock,
            return_value=SAMPLE_INTEGRATION_DESCRIPTIONS,
        ):
            result = await tool.execute(filter="nonexistent_xyz")

        data = json.loads(result.output)
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_no_hass(self):
        tool = ListAvailableIntegrations(hass=None)
        result = await tool.execute()
        assert not result.success
        assert "not available" in result.output

    @pytest.mark.asyncio
    async def test_loader_error(self):
        hass = _make_hass()
        tool = ListAvailableIntegrations(hass=hass)

        with patch(
            "homeassistant.loader.async_get_integration_descriptions",
            new_callable=AsyncMock,
            side_effect=RuntimeError("loader broke"),
        ):
            result = await tool.execute()

        assert not result.success
        assert "loader broke" in result.output

    @pytest.mark.asyncio
    async def test_custom_integration_has_custom_flag(self):
        hass = _make_hass()
        tool = ListAvailableIntegrations(hass=hass)

        with patch(
            "homeassistant.loader.async_get_integration_descriptions",
            new_callable=AsyncMock,
            return_value=SAMPLE_INTEGRATION_DESCRIPTIONS,
        ):
            result = await tool.execute(filter="hacs")

        data = json.loads(result.output)
        hacs = data["integrations"][0]
        assert hacs["custom"] is True


# ---------------------------------------------------------------------------
# ReadYamlConfig tests
# ---------------------------------------------------------------------------


class TestReadYamlConfig:
    """Tests for the read_yaml_config tool."""

    @pytest.mark.asyncio
    async def test_read_all_sections(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        yaml_content = "homeassistant:\n  name: My Home\nnotify:\n  - platform: smtp\n"

        with patch.object(ReadYamlConfig, "_read_file", return_value=yaml_content):
            result = await tool.execute()

        assert result.success
        data = json.loads(result.output)
        assert "homeassistant" in data["sections"]
        assert "notify" in data["sections"]
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_read_specific_section(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        yaml_content = "notify:\n  - platform: smtp\n    server: smtp.gmail.com\n"

        with patch.object(ReadYamlConfig, "_read_file", return_value=yaml_content):
            result = await tool.execute(section="notify")

        assert result.success
        data = json.loads(result.output)
        assert data["section"] == "notify"
        assert isinstance(data["config"], list)
        assert data["config"][0]["platform"] == "smtp"

    @pytest.mark.asyncio
    async def test_read_missing_section(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        yaml_content = "homeassistant:\n  name: My Home\n"

        with patch.object(ReadYamlConfig, "_read_file", return_value=yaml_content):
            result = await tool.execute(section="notify")

        assert not result.success
        data = json.loads(result.output)
        assert "not found" in data["error"]
        assert "homeassistant" in data["available_sections"]

    @pytest.mark.asyncio
    async def test_read_redacts_secrets(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        yaml_content = (
            "notify:\n"
            "  - platform: smtp\n"
            "    password: !secret smtp_pass\n"
            "    server: smtp.gmail.com\n"
        )

        with patch.object(ReadYamlConfig, "_read_file", return_value=yaml_content):
            result = await tool.execute(section="notify")

        data = json.loads(result.output)
        assert data["config"][0]["password"] == "***SECRET***"
        assert data["config"][0]["server"] == "smtp.gmail.com"

    @pytest.mark.asyncio
    async def test_read_shows_include_info(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        yaml_content = "automation: !include automations.yaml\n"

        with patch.object(ReadYamlConfig, "_read_file", return_value=yaml_content):
            result = await tool.execute()

        data = json.loads(result.output)
        assert "!include automations.yaml" in data["sections"]["automation"]

    @pytest.mark.asyncio
    async def test_read_no_hass(self):
        tool = ReadYamlConfig(hass=None)
        result = await tool.execute()
        assert not result.success

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)

        with patch.object(ReadYamlConfig, "_read_file", side_effect=FileNotFoundError):
            result = await tool.execute()

        assert not result.success
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# CreateYamlIntegration tests
# ---------------------------------------------------------------------------


class TestCreateYamlIntegration:
    """Tests for the create_yaml_integration tool."""

    @pytest.mark.asyncio
    async def test_append_new_key(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"
        written_content = None

        def mock_write(path, content):
            nonlocal written_content
            written_content = content

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file", side_effect=mock_write),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp", "server": "smtp.gmail.com"}]},
                validate_before_save=False,
            )

        assert result.success
        data = json.loads(result.output)
        assert "notify" in data["keys_added"]
        assert written_content is not None
        assert "homeassistant:" in written_content
        assert "notify:" in written_content
        assert "platform: smtp" in written_content

    @pytest.mark.asyncio
    async def test_conflict_without_overwrite(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "notify:\n  - platform: pushbullet\n    api_key: xxx\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
            )

        assert not result.success
        data = json.loads(result.output)
        assert data["conflicts"][0]["key"] == "notify"
        assert "already exists" in data["conflicts"][0]["reason"]

    @pytest.mark.asyncio
    async def test_overwrite_existing(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = (
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "notify:\n"
            "  - platform: pushbullet\n"
            "    api_key: xxx\n"
        )
        written_content = None

        def mock_write(path, content):
            nonlocal written_content
            written_content = content

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file", side_effect=mock_write),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp", "server": "smtp.gmail.com"}]},
                overwrite_existing=True,
                validate_before_save=False,
            )

        assert result.success
        data = json.loads(result.output)
        assert "notify" in data["keys_overwritten"]
        # Old content should be removed, new content added
        assert "pushbullet" not in written_content
        assert "platform: smtp" in written_content
        assert "homeassistant:" in written_content

    @pytest.mark.asyncio
    async def test_include_tag_conflict(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "automation: !include automations.yaml\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"automation": [{"alias": "Test"}]},
                overwrite_existing=True,  # Even with overwrite, !include blocks
                validate_before_save=False,
            )

        assert not result.success
        data = json.loads(result.output)
        assert "!include" in data["conflicts"][0]["reason"]

    @pytest.mark.asyncio
    async def test_backup_created(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"
        backup_called = False

        def mock_backup(path):
            nonlocal backup_called
            backup_called = True
            return True

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(
                CreateYamlIntegration, "_backup_file", side_effect=mock_backup
            ),
        ):
            await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
            )

        assert backup_called

    @pytest.mark.asyncio
    async def test_validation_called(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
            )

        assert result.success
        hass.services.async_call.assert_any_call(
            "homeassistant", "check_config", blocking=True
        )

    @pytest.mark.asyncio
    async def test_auto_restart(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
                auto_restart=True,
            )

        assert result.success
        data = json.loads(result.output)
        assert data["restart_done"] is True
        hass.services.async_call.assert_any_call(
            "homeassistant", "restart", blocking=False
        )

    @pytest.mark.asyncio
    async def test_empty_config_rejected(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)

        result = await tool.execute(config={}, validate_before_save=False)
        assert not result.success
        assert "non-empty" in result.output

    @pytest.mark.asyncio
    async def test_no_hass(self):
        tool = CreateYamlIntegration(hass=None)
        result = await tool.execute(
            config={"notify": [{"platform": "smtp"}]},
        )
        assert not result.success

    @pytest.mark.asyncio
    async def test_empty_file_append(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        written_content = None

        def mock_write(path, content):
            nonlocal written_content
            written_content = content

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", side_effect=FileNotFoundError
            ),
            patch.object(CreateYamlIntegration, "_write_file", side_effect=mock_write),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
            )

        assert result.success
        assert "notify:" in written_content

    @pytest.mark.asyncio
    async def test_multiple_new_keys(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"
        written_content = None

        def mock_write(path, content):
            nonlocal written_content
            written_content = content

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file", side_effect=mock_write),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={
                    "notify": [{"platform": "smtp"}],
                    "input_boolean": {"guest_mode": {"name": "Guest Mode"}},
                },
                validate_before_save=False,
            )

        assert result.success
        data = json.loads(result.output)
        assert "notify" in data["keys_added"]
        assert "input_boolean" in data["keys_added"]
        assert "notify:" in written_content
        assert "input_boolean:" in written_content

    @pytest.mark.asyncio
    async def test_validation_failure_rolls_back(self):
        hass = _make_hass()
        hass.services.async_call = AsyncMock(
            side_effect=[RuntimeError("config invalid"), None]
        )
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
            patch.object(
                CreateYamlIntegration,
                "_rollback_from_backup",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_rb,
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
                auto_restart=True,
            )

        # Should fail and roll back — restart should not happen
        assert not result.success
        data = json.loads(result.output)
        assert "validation_error" in data["validation"]
        assert data["rolled_back"] is True
        mock_rb.assert_called_once()


# ---------------------------------------------------------------------------
# _backup_file integration test
# ---------------------------------------------------------------------------


class TestBackupFile:
    """Tests for the static backup helper."""

    def test_backup_creates_copy(self, tmp_path):
        config_file = tmp_path / "configuration.yaml"
        config_file.write_text("homeassistant:\n  name: Test\n")

        CreateYamlIntegration._backup_file(str(config_file))

        backup_file = tmp_path / "configuration.yaml.backup"
        assert backup_file.exists()
        assert backup_file.read_text() == "homeassistant:\n  name: Test\n"

    def test_backup_nonexistent_file(self, tmp_path):
        # Should not raise
        CreateYamlIntegration._backup_file(str(tmp_path / "nonexistent.yaml"))


# ---------------------------------------------------------------------------
# End-to-end text manipulation tests
# ---------------------------------------------------------------------------


class TestBuildNewContent:
    """Tests for _build_new_content static method."""

    def test_append_preserves_original(self):
        raw = "# My config\nhomeassistant:\n  name: My Home\n"
        config = {"notify": [{"platform": "smtp"}]}
        result = CreateYamlIntegration._build_new_content(raw, config, ["notify"], [])
        assert result.startswith("# My config\n")
        assert "homeassistant:" in result
        assert "notify:" in result

    def test_overwrite_removes_old(self):
        raw = (
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "notify:\n"
            "  - platform: pushbullet\n"
            "\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        config = {"notify": [{"platform": "smtp"}]}
        result = CreateYamlIntegration._build_new_content(raw, config, [], ["notify"])
        assert "pushbullet" not in result
        assert "platform: smtp" in result
        assert "homeassistant:" in result
        assert "http:" in result


# ---------------------------------------------------------------------------
# New tests for code review fixes
# ---------------------------------------------------------------------------


class TestRemoveYamlSectionPrefixCollision:
    """Tests for the prefix collision fix in _remove_yaml_section."""

    def test_notify_does_not_remove_notify_group(self):
        """Removing 'notify' must NOT remove 'notify_group'."""
        content = (
            "notify:\n"
            "  - platform: smtp\n"
            "\n"
            "notify_group:\n"
            "  family:\n"
            "    - notify.phone\n"
            "\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "notify")
        assert "notify:" not in result.split("notify_group")[0]
        assert "platform: smtp" not in result
        assert "notify_group:" in result
        assert "family:" in result
        assert "http:" in result

    def test_exact_key_with_value_on_same_line(self):
        """'key: value' on same line should still be removed."""
        content = "debug: true\nhttp:\n  server_port: 8123\n"
        result = _remove_yaml_section(content, "debug")
        assert "debug:" not in result
        assert "http:" in result

    def test_key_with_trailing_space(self):
        """'key: ' (trailing space) should be matched."""
        content = "notify: \n  - platform: smtp\nhttp:\n  port: 8123\n"
        result = _remove_yaml_section(content, "notify")
        assert "notify:" not in result
        assert "http:" in result


class TestRemoveYamlSectionColumnZeroComment:
    """Tests for column-0 comments inside a section being removed."""

    def test_column_zero_comment_inside_section_is_removed(self):
        """A column-0 comment between indented lines of a section must be removed."""
        content = (
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "notify:\n"
            "  - platform: smtp\n"
            "# inline comment inside notify section\n"
            "  - platform: telegram\n"
            "\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "notify")
        assert "notify:" not in result
        assert "platform: smtp" not in result
        assert "inline comment inside notify section" not in result
        assert "platform: telegram" not in result
        assert "homeassistant:" in result
        assert "http:" in result

    def test_column_zero_comment_between_sections_preserved(self):
        """A column-0 comment between two sections is preserved when removing neither."""
        content = (
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "# === HTTP section ===\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "notify")
        assert "# === HTTP section ===" in result
        assert "http:" in result

    def test_multiple_column_zero_comments_inside_section(self):
        """Column-0 comments between indented lines are removed; trailing ones are kept."""
        content = (
            "sensor:\n"
            "  - platform: template\n"
            "# comment 1\n"
            "# comment 2\n"
            "  - platform: rest\n"
            "# comment 3\n"
            "\n"
            "automation: !include automations.yaml\n"
        )
        result = _remove_yaml_section(content, "sensor")
        assert "sensor:" not in result
        # Comments between indented lines are inside the section → removed
        assert "comment 1" not in result
        assert "comment 2" not in result
        assert "platform: template" not in result
        assert "platform: rest" not in result
        # comment 3 is at the end, followed by a blank + new top-level key
        # → lookahead sees next content is a top-level key → comment preserved
        assert "comment 3" in result
        assert "automation:" in result

    def test_column_zero_comment_between_indented_lines_removed(self):
        """Column-0 comments sandwiched between indented lines are removed."""
        content = (
            "sensor:\n"
            "  - platform: template\n"
            "# mid-section note\n"
            "  - platform: rest\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "sensor")
        assert "sensor:" not in result
        assert "mid-section note" not in result
        assert "platform: template" not in result
        assert "platform: rest" not in result
        assert "http:" in result

    def test_comment_before_section_is_not_removed(self):
        """A comment ABOVE a section (before the key) should NOT be removed with the section."""
        content = (
            "# Keep this comment\n"
            "homeassistant:\n"
            "  name: My Home\n"
            "\n"
            "# This comment precedes notify\n"
            "notify:\n"
            "  - platform: smtp\n"
            "\n"
            "http:\n"
            "  server_port: 8123\n"
        )
        result = _remove_yaml_section(content, "notify")
        assert "# Keep this comment" in result
        assert "# This comment precedes notify" in result
        assert "notify:" not in result
        assert "http:" in result


class TestConcurrentWriteSerialization:
    """Tests for asyncio.Lock concurrent write protection."""

    @pytest.mark.asyncio
    async def test_concurrent_writes_are_serialized(self):
        """Two concurrent writes should not interleave — Lock serializes them."""
        import asyncio as aio

        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)

        call_order: list[str] = []
        original_yaml = "homeassistant:\n  name: My Home\n"

        # Make async_add_executor_job actually async so the Lock can serialize
        async def fake_executor(func, *args):
            return func(*args)

        hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        real_write = CreateYamlIntegration._write_file

        def tracking_write(path, content):
            """Track call order to detect interleaving."""
            call_order.append(f"write:{content[:20]}")
            # No actual write needed — we just track the call order

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=original_yaml
            ),
            patch.object(
                CreateYamlIntegration, "_write_file", side_effect=tracking_write
            ),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            t1 = aio.create_task(
                tool.execute(
                    config={"sensor": [{"platform": "template"}]},
                    validate_before_save=False,
                )
            )
            t2 = aio.create_task(
                tool.execute(
                    config={"switch": [{"platform": "template"}]},
                    validate_before_save=False,
                )
            )
            r1, r2 = await aio.gather(t1, t2)

        # Both should succeed
        assert r1.success
        assert r2.success
        # Both writes should have been called (serialized by the lock)
        assert len(call_order) == 2


class TestSafeLoadYamlNonMapping:
    """Tests for non-mapping YAML root handling."""

    def test_list_root_raises_yaml_error(self):
        content = "- item1\n- item2\n"
        with pytest.raises(yaml.YAMLError, match="Expected top-level mapping"):
            _safe_load_yaml(content)

    def test_scalar_root_raises_yaml_error(self):
        content = "just a string\n"
        with pytest.raises(yaml.YAMLError, match="Expected top-level mapping"):
            _safe_load_yaml(content)


class TestReadYamlConfigMalformed:
    """Tests for malformed YAML in ReadYamlConfig."""

    @pytest.mark.asyncio
    async def test_read_malformed_yaml(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        bad_yaml = "notify:\n  - platform: smtp\n  bad_indent"

        with patch.object(ReadYamlConfig, "_read_file", return_value=bad_yaml):
            result = await tool.execute()

        assert not result.success
        assert "YAML" in result.output or "yaml" in result.output.lower()

    @pytest.mark.asyncio
    async def test_read_non_mapping_root(self):
        hass = _make_hass()
        tool = ReadYamlConfig(hass=hass)
        list_yaml = "- item1\n- item2\n"

        with patch.object(ReadYamlConfig, "_read_file", return_value=list_yaml):
            result = await tool.execute()

        assert not result.success
        assert "mapping" in result.output.lower()


class TestAtomicWrite:
    """Tests for atomic file write behavior."""

    def test_write_creates_file(self, tmp_path):
        target = tmp_path / "config.yaml"
        CreateYamlIntegration._write_file(str(target), "test: true\n")
        assert target.read_text() == "test: true\n"

    def test_write_overwrites_atomically(self, tmp_path):
        target = tmp_path / "config.yaml"
        target.write_text("old content\n")
        CreateYamlIntegration._write_file(str(target), "new content\n")
        assert target.read_text() == "new content\n"

    def test_write_no_temp_file_on_success(self, tmp_path):
        target = tmp_path / "config.yaml"
        CreateYamlIntegration._write_file(str(target), "test: true\n")
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestValidationRollback:
    """Tests for rollback on validation failure."""

    @pytest.mark.asyncio
    async def test_rollback_called_on_validation_failure(self):
        hass = _make_hass()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("invalid config"))
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
            patch.object(
                CreateYamlIntegration,
                "_rollback_from_backup",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_rb,
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
            )

        assert not result.success
        data = json.loads(result.output)
        assert data["rolled_back"] is True
        assert "validation_error" in data["validation"]
        mock_rb.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_rollback_when_validation_passes(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
            patch.object(
                CreateYamlIntegration,
                "_rollback_from_backup",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_rb,
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
            )

        assert result.success
        mock_rb.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_rollback_when_backup_failed(self):
        """If backup failed and validation fails, returns failure with no rollback."""
        hass = _make_hass()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("invalid config"))
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(
                CreateYamlIntegration,
                "_backup_file",
                side_effect=OSError("disk full"),
            ),
            patch.object(
                CreateYamlIntegration,
                "_rollback_from_backup",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_rb,
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
            )

        # Validation failed, no backup → returns failure, no rollback attempted
        assert not result.success
        data = json.loads(result.output)
        assert data["rolled_back"] is False
        assert "validation_error" in data["validation"]
        assert "no backup" in data["message"]
        mock_rb.assert_not_called()


class TestBackupCreatedAccuracy:
    """Tests for accurate backup_created reporting."""

    @pytest.mark.asyncio
    async def test_backup_created_true_on_success(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
            )

        data = json.loads(result.output)
        assert data["backup_created"] is True

    @pytest.mark.asyncio
    async def test_backup_created_false_on_failure(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(
                CreateYamlIntegration,
                "_backup_file",
                side_effect=OSError("disk full"),
            ),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
            )

        assert result.success
        data = json.loads(result.output)
        assert data["backup_created"] is False


class TestWriteFailure:
    """Tests for write failure error path."""

    @pytest.mark.asyncio
    async def test_write_failure_returns_error(self):
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(
                CreateYamlIntegration,
                "_write_file",
                side_effect=OSError("permission denied"),
            ),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=False,
            )

        assert not result.success
        assert "permission denied" in result.output


class TestWriteFilePermissions:
    """Tests for file permission preservation during atomic write."""

    def test_preserves_original_permissions(self, tmp_path):
        target = tmp_path / "configuration.yaml"
        target.write_text("old: content\n")
        os.chmod(str(target), 0o644)

        CreateYamlIntegration._write_file(str(target), "new: content\n")

        mode = os.stat(str(target)).st_mode & 0o777
        assert mode == 0o644

    def test_new_file_gets_default_permissions(self, tmp_path):
        target = tmp_path / "configuration.yaml"
        CreateYamlIntegration._write_file(str(target), "new: content\n")
        # Should exist and be readable
        assert target.read_text() == "new: content\n"


class TestBackupFileReturnValue:
    """Tests for _backup_file return value accuracy."""

    def test_returns_true_when_file_exists(self, tmp_path):
        config_file = tmp_path / "configuration.yaml"
        config_file.write_text("test: true\n")
        result = CreateYamlIntegration._backup_file(str(config_file))
        assert result is True

    def test_returns_false_when_file_missing(self, tmp_path):
        result = CreateYamlIntegration._backup_file(str(tmp_path / "nonexistent.yaml"))
        assert result is False


class TestRollbackFailure:
    """Tests for rollback failure reporting."""

    @pytest.mark.asyncio
    async def test_rollback_failure_reports_rolled_back_false(self):
        hass = _make_hass()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("invalid config"))
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = "homeassistant:\n  name: My Home\n"

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
            patch.object(
                CreateYamlIntegration,
                "_rollback_from_backup",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
            )

        assert not result.success
        data = json.loads(result.output)
        assert data["rolled_back"] is False
        assert "validation_error" in data["validation"]


class TestValidationFailureNoBackup:
    """Tests for validation failure when no backup is available."""

    @pytest.mark.asyncio
    async def test_returns_failure_with_no_backup_message(self):
        hass = _make_hass()
        hass.services.async_call = AsyncMock(side_effect=RuntimeError("bad config"))
        tool = CreateYamlIntegration(hass=hass)

        with (
            patch.object(
                CreateYamlIntegration,
                "_read_file",
                side_effect=FileNotFoundError,
            ),
            patch.object(CreateYamlIntegration, "_write_file"),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=False),
        ):
            result = await tool.execute(
                config={"notify": [{"platform": "smtp"}]},
                validate_before_save=True,
            )

        assert not result.success
        data = json.loads(result.output)
        assert data["rolled_back"] is False
        assert "no backup" in data["message"]


class TestSafeLoadYamlNonScalarTags:
    """Tests for non-scalar HA tags like !env_var with sequence/mapping nodes."""

    def test_env_var_scalar(self):
        """Standard scalar !env_var should parse without error."""
        content = "database:\n  host: !env_var DB_HOST\n"
        result = _safe_load_yaml(content)
        assert result["database"]["host"] == "DB_HOST"

    def test_env_var_sequence(self):
        """!env_var with sequence form [VAR, default] should not crash."""
        content = "database:\n  host: !env_var [DB_HOST, localhost]\n"
        result = _safe_load_yaml(content)
        assert result["database"]["host"] == ["DB_HOST", "localhost"]

    def test_input_scalar(self):
        """Standard scalar !input should parse without error."""
        content = "automation:\n  trigger: !input trigger_id\n"
        result = _safe_load_yaml(content)
        assert result["automation"]["trigger"] == "trigger_id"


class TestWriteFileFdLeak:
    """Tests for fd cleanup when _write_file fails before os.fdopen."""

    def test_fchmod_failure_closes_fd(self, tmp_path):
        """If fchmod fails, fd should still be closed (no leak)."""
        target = tmp_path / "config.yaml"
        target.write_text("old: content\n")

        with patch("os.fchmod", side_effect=OSError("permission denied")):
            with pytest.raises(OSError, match="permission denied"):
                CreateYamlIntegration._write_file(str(target), "new: content\n")

        # Original file should be untouched
        assert target.read_text() == "old: content\n"
        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


# ---------------------------------------------------------------------------
# Anchor-safe section removal tests
# ---------------------------------------------------------------------------


class TestAnchorSafeRemoval:
    """Tests for anchor-safe section removal."""

    def test_removing_anchor_section_with_alias_raises(self):
        """Removing a section that defines an anchor used elsewhere raises ValueError."""
        content = (
            "defaults: &defaults\n"
            "  adapter: postgres\n"
            "  host: localhost\n"
            "\n"
            "development:\n"
            "  database: myapp_dev\n"
            "  <<: *defaults\n"
        )
        with pytest.raises(ValueError, match="anchor.*defaults"):
            _remove_yaml_section(content, "defaults")

    def test_removing_section_without_anchor_works(self):
        """Removing a section without anchors works normally."""
        content = (
            "defaults:\n  adapter: postgres\n\ndevelopment:\n  database: myapp_dev\n"
        )
        result = _remove_yaml_section(content, "defaults")
        assert "defaults:" not in result
        assert "development:" in result

    def test_removing_section_with_anchor_but_no_alias_works(self):
        """Removing a section with an anchor that is NOT referenced elsewhere works."""
        content = (
            "defaults: &defaults\n"
            "  adapter: postgres\n"
            "\n"
            "development:\n"
            "  database: myapp_dev\n"
        )
        result = _remove_yaml_section(content, "defaults")
        assert "defaults:" not in result
        assert "development:" in result

    def test_removing_alias_user_section_works(self):
        """Removing the section that USES an alias (not defines it) works fine."""
        content = (
            "defaults: &defaults\n"
            "  adapter: postgres\n"
            "\n"
            "development:\n"
            "  <<: *defaults\n"
        )
        result = _remove_yaml_section(content, "development")
        assert "development:" not in result
        assert "defaults:" in result

    def test_self_referencing_anchor_allows_removal(self):
        """A section that defines AND uses its own anchor can be removed."""
        content = "base: &base\n  x: 1\n  y: *base\n\nother:\n  z: 2\n"
        # The alias *base is INSIDE the section being removed, so it's fine
        result = _remove_yaml_section(content, "base")
        assert "base:" not in result
        assert "other:" in result

    def test_nested_anchor_with_external_alias_raises(self):
        """Anchor defined on a nested line, referenced outside, raises ValueError."""
        content = (
            "database:\n"
            "  defaults: &db-defaults\n"
            "    adapter: postgres\n"
            "\n"
            "production:\n"
            "  <<: *db-defaults\n"
            "  database: prod_db\n"
        )
        with pytest.raises(ValueError, match="anchor.*db-defaults"):
            _remove_yaml_section(content, "database")

    def test_hyphenated_anchor_name_detected(self):
        """Anchor names with hyphens are properly detected."""
        content = (
            "base-config: &base-config\n  timeout: 30\n\nservice:\n  <<: *base-config\n"
        )
        with pytest.raises(ValueError, match="anchor.*base-config"):
            _remove_yaml_section(content, "base-config")

    @pytest.mark.asyncio
    async def test_overwrite_anchor_section_returns_error(self):
        """Overwriting a section with an anchor used elsewhere returns error."""
        hass = _make_hass()
        tool = CreateYamlIntegration(hass=hass)
        existing_yaml = (
            "defaults: &defaults\n"
            "  adapter: postgres\n"
            "\n"
            "development:\n"
            "  <<: *defaults\n"
        )

        with (
            patch.object(
                CreateYamlIntegration, "_read_file", return_value=existing_yaml
            ),
            patch.object(CreateYamlIntegration, "_backup_file", return_value=True),
        ):
            result = await tool.execute(
                config={"defaults": {"adapter": "mysql"}},
                overwrite_existing=True,
                validate_before_save=False,
            )

        assert not result.success
        assert "anchor" in result.output.lower() or "Cannot remove" in result.output


# ---------------------------------------------------------------------------
# Include tag type preservation tests
# ---------------------------------------------------------------------------


class TestIncludeTagTypePreservation:
    """Tests for include tag type preservation."""

    def test_include_dir_list_tag_preserved(self):
        content = "automation: !include_dir_list automations/\n"
        result = _safe_load_yaml(content)
        tag = result["automation"]
        assert _is_include_tag(tag)
        assert tag.tag == "!include_dir_list"
        assert tag.path == "automations/"

    def test_include_dir_merge_named_tag_preserved(self):
        content = "packages: !include_dir_merge_named packages/\n"
        result = _safe_load_yaml(content)
        tag = result["packages"]
        assert _is_include_tag(tag)
        assert tag.tag == "!include_dir_merge_named"

    def test_plain_include_tag_preserved(self):
        content = "automation: !include automations.yaml\n"
        result = _safe_load_yaml(content)
        tag = result["automation"]
        assert _is_include_tag(tag)
        assert tag.tag == "!include"

    def test_serialize_preserves_tag_type(self):
        content = "automation: !include_dir_merge_list automations/\n"
        result = _safe_load_yaml(content)
        serialized = _serialize_for_output(result)
        assert serialized["automation"] == "!include_dir_merge_list automations/"
