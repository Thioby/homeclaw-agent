"""Tests for AutomationManager.

Tests automation operations extracted from the God Class.
Uses TDD approach - tests written first.
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from custom_components.homeclaw.managers.automation_manager import AutomationManager


class MockState:
    """Mock Home Assistant state object."""

    def __init__(
        self,
        entity_id: str,
        state: str,
        attributes: dict = None,
        last_changed: datetime = None,
    ):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.last_changed = last_changed or datetime.now(timezone.utc)


@pytest.fixture
def automation_manager(hass):
    """Create an AutomationManager with mocked hass."""
    # Mock states and services on the real hass object to support existing tests
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    
    return AutomationManager(hass)


@pytest.fixture
def sample_automation_states():
    """Create sample automation states for testing."""
    return [
        MockState(
            "automation.morning_lights",
            "on",
            {"friendly_name": "Morning Lights", "last_triggered": "2025-01-29T07:00:00"},
        ),
        MockState(
            "automation.evening_routine",
            "off",
            {"friendly_name": "Evening Routine", "last_triggered": "2025-01-28T18:00:00"},
        ),
        MockState(
            "automation.motion_alert",
            "on",
            {"friendly_name": "Motion Alert", "last_triggered": None},
        ),
    ]


@pytest.fixture
def config_dir(hass, tmp_path):
    """Point hass at a temp config dir with a standard automation include."""
    hass.config.config_dir = str(tmp_path)
    (tmp_path / "configuration.yaml").write_text(
        "automation: !include automations.yaml\n"
    )
    return tmp_path


@pytest.fixture
def live_automations_content():
    """Raw content of the production automations.yaml fixture."""
    fixture = Path(__file__).parent.parent / "fixtures" / "live_automations.yaml"
    return fixture.read_text()


@pytest.fixture
def valid_automation_config():
    """Create a valid automation configuration."""
    return {
        "alias": "Test Automation",
        "trigger": [
            {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
        ],
        "action": [
            {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
        ],
    }


class TestValidateAutomationValid:
    """Tests for validate_automation method with valid configurations."""

    def test_validate_automation_valid(self, automation_manager):
        """Test that a valid automation config returns {valid: True}."""
        config = {
            "alias": "Test Automation",
            "trigger": [
                {"platform": "state", "entity_id": "binary_sensor.motion", "to": "on"}
            ],
            "action": [
                {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
            ],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True
        assert "error" not in result or result.get("error") is None

    def test_validate_automation_valid_with_single_trigger(self, automation_manager):
        """Test that a single trigger (not in list) is also valid."""
        config = {
            "alias": "Single Trigger Automation",
            "trigger": {"platform": "time", "at": "07:00:00"},
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True

    def test_validate_automation_valid_with_single_action(self, automation_manager):
        """Test that a single action (not in list) is also valid."""
        config = {
            "alias": "Single Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": {"service": "notify.mobile_app"},
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True

    def test_validate_automation_valid_with_action_field(self, automation_manager):
        """Test that action field (instead of service) is valid."""
        config = {
            "alias": "Action Field Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [{"action": "light.turn_on", "target": {"entity_id": "light.test"}}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is True


class TestValidateAutomationMissingTrigger:
    """Tests for validate_automation with missing trigger."""

    def test_validate_automation_missing_trigger(self, automation_manager):
        """Test that missing trigger returns {valid: False, error: ...}."""
        config = {
            "alias": "No Trigger Automation",
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "trigger" in result["error"].lower()

    def test_validate_automation_empty_trigger(self, automation_manager):
        """Test that empty trigger list returns {valid: False, error: ...}."""
        config = {
            "alias": "Empty Trigger Automation",
            "trigger": [],
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "trigger" in result["error"].lower()

    def test_validate_automation_null_trigger(self, automation_manager):
        """Test that null trigger returns {valid: False, error: ...}."""
        config = {
            "alias": "Null Trigger Automation",
            "trigger": None,
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result


class TestValidateAutomationMissingAction:
    """Tests for validate_automation with missing action."""

    def test_validate_automation_missing_action(self, automation_manager):
        """Test that missing action returns {valid: False, error: ...}."""
        config = {
            "alias": "No Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "action" in result["error"].lower()

    def test_validate_automation_empty_action(self, automation_manager):
        """Test that empty action list returns {valid: False, error: ...}."""
        config = {
            "alias": "Empty Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result
        assert "action" in result["error"].lower()

    def test_validate_automation_action_missing_service_and_action(self, automation_manager):
        """Test that action without service or action field returns {valid: False, error: ...}."""
        config = {
            "alias": "Invalid Action Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [{"target": {"entity_id": "light.test"}}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "error" in result


class TestCreateAutomation:
    """Tests for create_automation method."""

    @pytest.mark.asyncio
    async def test_create_automation(
        self, automation_manager, hass, config_dir, valid_automation_config
    ):
        """Test that create_automation writes the file and reloads."""
        result = await automation_manager.create_automation(valid_automation_config)

        hass.services.async_call.assert_called_with("automation", "reload", {})
        assert result["success"] is True
        assert (config_dir / "automations.yaml").exists()

    @pytest.mark.asyncio
    async def test_create_automation_generates_id_if_missing(
        self, automation_manager, hass, config_dir
    ):
        """Test that create_automation generates an ID if not provided."""
        config = {
            "alias": "Auto ID Automation",
            "trigger": [{"platform": "time", "at": "08:00:00"}],
            "action": [{"service": "light.turn_on"}],
        }

        result = await automation_manager.create_automation(config)

        assert result["success"] is True
        assert len(result["id"]) == 32

    @pytest.mark.asyncio
    async def test_create_automation_uses_provided_id(
        self, automation_manager, hass, config_dir
    ):
        """Test that create_automation uses the provided ID."""
        config = {
            "id": "custom_automation_id",
            "alias": "Custom ID Automation",
            "trigger": [{"platform": "time", "at": "08:00:00"}],
            "action": [{"service": "light.turn_on"}],
        }

        result = await automation_manager.create_automation(config)

        assert result["success"] is True
        assert result.get("id") == "custom_automation_id"


class TestGetAutomations:
    """Tests for get_automations method."""

    def test_get_automations(self, automation_manager, hass, sample_automation_states):
        """Test that get_automations returns list from hass.states.async_all("automation")."""
        hass.states.async_all.return_value = sample_automation_states

        result = automation_manager.get_automations()

        assert isinstance(result, list)
        assert len(result) == 3
        entity_ids = [a["entity_id"] for a in result]
        assert "automation.morning_lights" in entity_ids
        assert "automation.evening_routine" in entity_ids
        assert "automation.motion_alert" in entity_ids

    def test_get_automations_empty(self, automation_manager, hass):
        """Test that get_automations returns empty list when no automations."""
        hass.states.async_all.return_value = []

        result = automation_manager.get_automations()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_automations_filters_by_domain(self, automation_manager, hass, sample_automation_states):
        """Test that get_automations only returns automation domain entities."""
        # Add some non-automation entities
        mixed_states = sample_automation_states + [
            MockState("light.test", "on", {}),
            MockState("sensor.test", "25", {}),
        ]
        hass.states.async_all.return_value = mixed_states

        result = automation_manager.get_automations()

        # Should only return automation entities
        for entity in result:
            assert entity["entity_id"].startswith("automation.")

    def test_get_automations_returns_proper_dict_structure(
        self, automation_manager, hass, sample_automation_states
    ):
        """Test that get_automations returns proper dict structure."""
        hass.states.async_all.return_value = sample_automation_states

        result = automation_manager.get_automations()

        assert len(result) > 0
        for automation in result:
            assert "entity_id" in automation
            assert "state" in automation
            assert "attributes" in automation


class TestToggleAutomationOn:
    """Tests for toggle_automation with enable=True."""

    @pytest.mark.asyncio
    async def test_toggle_automation_on(self, automation_manager, hass):
        """Test that toggle_automation with enable=True calls automation.turn_on."""
        entity_id = "automation.morning_lights"

        result = await automation_manager.toggle_automation(entity_id, enable=True)

        hass.services.async_call.assert_called_once_with(
            "automation",
            "turn_on",
            {"entity_id": entity_id},
        )
        assert result is not None
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_toggle_automation_on_returns_entity_id(self, automation_manager, hass):
        """Test that toggle_automation returns the entity_id in result."""
        entity_id = "automation.test_automation"

        result = await automation_manager.toggle_automation(entity_id, enable=True)

        assert result.get("entity_id") == entity_id


class TestToggleAutomationOff:
    """Tests for toggle_automation with enable=False."""

    @pytest.mark.asyncio
    async def test_toggle_automation_off(self, automation_manager, hass):
        """Test that toggle_automation with enable=False calls automation.turn_off."""
        entity_id = "automation.evening_routine"

        result = await automation_manager.toggle_automation(entity_id, enable=False)

        hass.services.async_call.assert_called_once_with(
            "automation",
            "turn_off",
            {"entity_id": entity_id},
        )
        assert result is not None
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_toggle_automation_off_returns_entity_id(self, automation_manager, hass):
        """Test that toggle_automation returns the entity_id in result."""
        entity_id = "automation.test_automation"

        result = await automation_manager.toggle_automation(entity_id, enable=False)

        assert result.get("entity_id") == entity_id


class TestAutomationManagerInitialization:
    """Tests for AutomationManager initialization."""

    def test_init_stores_hass(self, hass):
        """Test that AutomationManager stores hass reference."""
        manager = AutomationManager(hass)

        assert manager.hass is hass

    def test_init_with_none_hass_raises(self):
        """Test that AutomationManager raises error with None hass."""
        with pytest.raises(ValueError, match="hass is required"):
            AutomationManager(None)


class TestValidateAutomationModernFormat:
    """Tests for validate_automation with modern plural keys and blueprints."""

    def test_modern_plural_keys_accepted(self, automation_manager):
        config = {
            "alias": "Modern",
            "triggers": [{"trigger": "state", "entity_id": "sensor.temp"}],
            "conditions": [],
            "actions": [{"action": "light.turn_on", "target": {"entity_id": "light.x"}}],
        }

        assert automation_manager.validate_automation(config)["valid"] is True

    def test_blueprint_without_triggers_accepted(self, automation_manager):
        config = {
            "alias": "Blueprint",
            "use_blueprint": {
                "path": "homeassistant/motion_light.yaml",
                "input": {"motion_entity": "binary_sensor.motion"},
            },
        }

        assert automation_manager.validate_automation(config)["valid"] is True

    def test_both_singular_and_plural_rejected(self, automation_manager):
        config = {
            "trigger": [{"platform": "state"}],
            "triggers": [{"trigger": "state"}],
            "action": [{"service": "light.turn_on"}],
        }

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "not both" in result["error"]

    def test_non_dict_config_rejected(self, automation_manager):
        result = automation_manager.validate_automation("not a dict")

        assert result["valid"] is False

    def test_structured_action_entries_accepted(self, automation_manager):
        config = {
            "trigger": [{"platform": "state", "entity_id": "sensor.temp"}],
            "action": [
                {"delay": "00:00:05"},
                {"choose": [], "default": []},
                {"event": "custom_event"},
            ],
        }

        assert automation_manager.validate_automation(config)["valid"] is True


class TestCreateAutomationSafeWrite:
    """Tests that create_automation never corrupts the HA configuration."""

    NEW_AUTOMATION = {
        "alias": "Test light on motion",
        "triggers": [{"trigger": "state", "entity_id": "binary_sensor.motion", "to": "on"}],
        "actions": [{"action": "light.turn_on", "target": {"entity_id": "light.office"}}],
        "mode": "single",
    }

    @pytest.fixture
    def live_file(self, config_dir, live_automations_content):
        path = config_dir / "automations.yaml"
        path.write_text(live_automations_content)
        return path

    @pytest.mark.asyncio
    async def test_appends_preserving_live_config_bytes(
        self, automation_manager, live_file, live_automations_content
    ):
        original = yaml.safe_load(live_automations_content)

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        new_content = live_file.read_text()
        assert new_content.startswith(live_automations_content)
        parsed = yaml.safe_load(new_content)
        assert len(parsed) == len(original) + 1
        assert parsed[-1]["alias"] == "Test light on motion"
        assert parsed[-1]["id"] == result["id"]
        assert parsed[: len(original)] == original

    @pytest.mark.asyncio
    async def test_backup_created_with_original_content(
        self, automation_manager, live_file, live_automations_content
    ):
        await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        backup = live_file.parent / "automations.yaml.backup"
        assert backup.read_text() == live_automations_content

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(
        self, automation_manager, hass, live_file, live_automations_content
    ):
        result = await automation_manager.create_automation(
            dict(self.NEW_AUTOMATION), dry_run=True
        )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert yaml.safe_load(result["preview"])[0]["alias"] == "Test light on motion"
        assert live_file.read_text() == live_automations_content
        assert not (live_file.parent / "automations.yaml.backup").exists()
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_id_from_live_config_rejected(
        self, automation_manager, live_file, live_automations_content
    ):
        existing_id = yaml.safe_load(live_automations_content)[0]["id"]
        config = {**self.NEW_AUTOMATION, "id": existing_id}

        result = await automation_manager.create_automation(config)

        assert result["success"] is False
        assert "already exists" in result["error"]
        assert live_file.read_text() == live_automations_content

    @pytest.mark.asyncio
    async def test_unparseable_file_left_untouched(self, automation_manager, config_dir):
        path = config_dir / "automations.yaml"
        broken = "- id: '1'\n  alias: [unclosed\n"
        path.write_text(broken)

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is False
        assert "not valid YAML" in result["error"]
        assert path.read_text() == broken
        assert not (config_dir / "automations.yaml.backup").exists()

    @pytest.mark.asyncio
    async def test_non_list_file_rejected(self, automation_manager, config_dir):
        path = config_dir / "automations.yaml"
        content = "automation:\n  foo: bar\n"
        path.write_text(content)

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is False
        assert path.read_text() == content

    @pytest.mark.asyncio
    async def test_missing_file_created(self, automation_manager, config_dir):
        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        parsed = yaml.safe_load((config_dir / "automations.yaml").read_text())
        assert len(parsed) == 1

    @pytest.mark.asyncio
    async def test_empty_file_handled(self, automation_manager, config_dir):
        (config_dir / "automations.yaml").write_text("")

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        parsed = yaml.safe_load((config_dir / "automations.yaml").read_text())
        assert len(parsed) == 1

    @pytest.mark.asyncio
    async def test_literal_empty_list_replaced(self, automation_manager, config_dir):
        (config_dir / "automations.yaml").write_text("[]\n")

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        parsed = yaml.safe_load((config_dir / "automations.yaml").read_text())
        assert len(parsed) == 1

    @pytest.mark.asyncio
    async def test_comments_only_file_preserved(self, automation_manager, config_dir):
        (config_dir / "automations.yaml").write_text("# my precious notes\n")

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        content = (config_dir / "automations.yaml").read_text()
        assert content.startswith("# my precious notes\n")
        assert len(yaml.safe_load(content)) == 1

    @pytest.mark.asyncio
    async def test_file_without_trailing_newline(self, automation_manager, config_dir):
        (config_dir / "automations.yaml").write_text(
            "- id: 'old'\n  alias: Old\n  trigger: []\n  action: []"
        )

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        parsed = yaml.safe_load((config_dir / "automations.yaml").read_text())
        assert len(parsed) == 2
        assert parsed[0]["id"] == "old"

    @pytest.mark.asyncio
    async def test_blueprint_automation_written(self, automation_manager, live_file):
        config = {
            "alias": "Blueprint based",
            "use_blueprint": {
                "path": "homeassistant/motion_light.yaml",
                "input": {"motion_entity": "binary_sensor.motion"},
            },
        }

        result = await automation_manager.create_automation(config)

        assert result["success"] is True
        parsed = yaml.safe_load(live_file.read_text())
        assert parsed[-1]["use_blueprint"]["path"] == "homeassistant/motion_light.yaml"

    @pytest.mark.asyncio
    async def test_jinja_template_survives_roundtrip(self, automation_manager, live_file):
        config = {
            **self.NEW_AUTOMATION,
            "actions": [
                {
                    "action": "notify.mobile_app",
                    "data": {"message": "{{ states('sensor.temp') | float > 21 }}"},
                }
            ],
        }

        result = await automation_manager.create_automation(config)

        assert result["success"] is True
        parsed = yaml.safe_load(live_file.read_text())
        assert (
            parsed[-1]["actions"][0]["data"]["message"]
            == "{{ states('sensor.temp') | float > 21 }}"
        )

    @pytest.mark.asyncio
    async def test_reload_service_missing_aborts_before_write(
        self, automation_manager, hass, config_dir
    ):
        hass.services.has_service.return_value = False

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is False
        assert "not loaded" in result["error"]
        assert not (config_dir / "automations.yaml").exists()

    @pytest.mark.asyncio
    async def test_split_config_layout_rejected(
        self, automation_manager, hass, config_dir
    ):
        (config_dir / "configuration.yaml").write_text(
            "automation: !include_dir_merge_list automations/\n"
        )

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is False
        assert "layout" in result["error"]
        assert not (config_dir / "automations.yaml").exists()

    @pytest.mark.asyncio
    async def test_missing_configuration_yaml_rejected(
        self, automation_manager, hass, tmp_path
    ):
        hass.config.config_dir = str(tmp_path)

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is False
        assert not (tmp_path / "automations.yaml").exists()

    @pytest.mark.asyncio
    async def test_symlinked_file_updated_in_place(
        self, automation_manager, config_dir, live_automations_content, tmp_path
    ):
        real_dir = tmp_path / "external"
        real_dir.mkdir()
        real_file = real_dir / "automations.yaml"
        real_file.write_text(live_automations_content)
        link = config_dir / "automations.yaml"
        link.symlink_to(real_file)

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        assert link.is_symlink()
        assert len(yaml.safe_load(real_file.read_text())) == len(
            yaml.safe_load(live_automations_content)
        ) + 1

    @pytest.mark.asyncio
    async def test_concurrent_creates_both_land(
        self, automation_manager, live_file, live_automations_content
    ):
        first = {**self.NEW_AUTOMATION, "id": "concurrent_one"}
        second = {**self.NEW_AUTOMATION, "id": "concurrent_two", "alias": "Second"}

        results = await asyncio.gather(
            automation_manager.create_automation(first),
            automation_manager.create_automation(second),
        )

        assert all(r["success"] for r in results)
        parsed = yaml.safe_load(live_file.read_text())
        assert len(parsed) == len(yaml.safe_load(live_automations_content)) + 2
        ids = {entry["id"] for entry in parsed}
        assert {"concurrent_one", "concurrent_two"} <= ids

    @pytest.mark.asyncio
    async def test_reload_failure_still_reports_saved(
        self, automation_manager, hass, live_file
    ):
        hass.services.async_call.side_effect = RuntimeError("reload boom")

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        assert "reload failed" in result["warning"]

    @pytest.mark.asyncio
    async def test_invalid_config_never_touches_disk(
        self, automation_manager, live_file, live_automations_content
    ):
        result = await automation_manager.create_automation({"alias": "no trigger"})

        assert result["success"] is False
        assert live_file.read_text() == live_automations_content


class TestReviewFindings:
    """Regression tests for gemini review findings."""

    NEW_AUTOMATION = TestCreateAutomationSafeWrite.NEW_AUTOMATION

    @pytest.mark.asyncio
    async def test_comments_with_empty_list_literal_preserved(
        self, automation_manager, config_dir
    ):
        (config_dir / "automations.yaml").write_text("# my notes\n[]\n")

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True
        content = (config_dir / "automations.yaml").read_text()
        assert content.startswith("# my notes\n")
        assert len(yaml.safe_load(content)) == 1

    @pytest.mark.asyncio
    async def test_include_inside_list_accepted(
        self, automation_manager, hass, config_dir
    ):
        (config_dir / "configuration.yaml").write_text(
            "automation:\n- !include automations.yaml\n"
        )

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_include_with_relative_prefix_accepted(
        self, automation_manager, hass, config_dir
    ):
        (config_dir / "configuration.yaml").write_text(
            "automation: !include ./automations.yaml\n"
        )

        result = await automation_manager.create_automation(dict(self.NEW_AUTOMATION))

        assert result["success"] is True

    def test_empty_dict_trigger_rejected(self, automation_manager):
        config = {"trigger": {}, "action": [{"service": "light.turn_on"}]}

        result = automation_manager.validate_automation(config)

        assert result["valid"] is False
        assert "trigger" in result["error"].lower()

    def test_use_blueprint_must_be_dict_with_path(self, automation_manager):
        assert (
            automation_manager.validate_automation({"use_blueprint": "oops"})["valid"]
            is False
        )
        assert (
            automation_manager.validate_automation({"use_blueprint": {}})["valid"]
            is False
        )

    @pytest.mark.asyncio
    async def test_entries_without_id_cause_no_false_conflict(
        self, automation_manager, config_dir
    ):
        (config_dir / "automations.yaml").write_text(
            "- alias: Legacy no id\n  trigger: []\n  action: []\n"
        )
        config = {**self.NEW_AUTOMATION, "id": "None"}

        result = await automation_manager.create_automation(config)

        assert result["success"] is True
