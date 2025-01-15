"""Tests for semantic learner."""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Note: homeassistant mocks are set up in conftest.py

from custom_components.homeclaw.rag.semantic_learner import (
    CategoryCorrection,
    SemanticLearner,
    CORRECTION_PATTERNS,
    VALID_CATEGORIES,
)


@dataclass
class MockState:
    """Mock Home Assistant state."""

    entity_id: str
    state: str
    attributes: dict


class TestSemanticLearner:
    """Tests for SemanticLearner class."""

    @pytest.fixture
    def mock_indexer(self):
        """Return a mock indexer."""
        indexer = MagicMock()
        indexer.set_learned_categories = MagicMock()
        indexer.index_entity = AsyncMock()
        return indexer

    @pytest.fixture
    def mock_states(self):
        """Return mock states for entity resolution."""
        states = [
            MockState("switch.bedroom_lamp", "on", {"friendly_name": "Bedroom Lamp Switch"}),
            MockState("light.kitchen", "off", {"friendly_name": "Kitchen Light"}),
            MockState("sensor.temperature", "22", {"friendly_name": "Temperature"}),
        ]
        return states

    @pytest.fixture
    def learner(self, hass, mock_indexer, mock_states, tmp_path):
        """Return a SemanticLearner instance."""
        with patch("homeassistant.core.StateMachine.async_all", return_value=mock_states), \
             patch("homeassistant.core.StateMachine.get", side_effect=lambda eid: next(
                (s for s in mock_states if s.entity_id == eid), None
            )):
            yield SemanticLearner(
                hass=hass,
                indexer=mock_indexer,
                storage_path=str(tmp_path / "categories.json"),
            )

    def test_detect_corrections_is_actually(self, learner):
        """Test detecting 'is actually a' pattern."""
        text = "switch.bedroom_lamp is actually a light"

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 1
        assert corrections[0].entity_id == "switch.bedroom_lamp"
        assert corrections[0].category == "light"

    def test_detect_corrections_treat_as(self, learner):
        """Test detecting 'treat as' pattern."""
        text = "treat switch.bedroom_lamp as a light"

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 1
        assert corrections[0].entity_id == "switch.bedroom_lamp"
        assert corrections[0].category == "light"

    def test_detect_corrections_controls(self, learner):
        """Test detecting 'controls' pattern."""
        text = "switch.bedroom_lamp controls the light"

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 1
        assert corrections[0].entity_id == "switch.bedroom_lamp"
        assert corrections[0].category == "light"

    def test_detect_corrections_should_be_categorized(self, learner):
        """Test detecting 'should be categorized as' pattern."""
        text = "switch.bedroom_lamp should be categorized as light"

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 1
        assert corrections[0].entity_id == "switch.bedroom_lamp"
        assert corrections[0].category == "light"

    def test_detect_corrections_invalid_category(self, learner):
        """Test that invalid categories are ignored."""
        text = "switch.bedroom_lamp is actually a foobar"

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 0

    def test_detect_corrections_case_insensitive(self, learner):
        """Test case-insensitive pattern matching."""
        text = "SWITCH.BEDROOM_LAMP IS ACTUALLY A LIGHT"

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 1
        assert corrections[0].category == "light"

    def test_detect_corrections_multiple(self, learner):
        """Test detecting multiple corrections."""
        text = (
            "switch.bedroom_lamp is actually a light and "
            "sensor.temperature should be categorized as temperature"
        )

        corrections = learner.detect_corrections(text)

        assert len(corrections) == 2

    def test_resolve_entity_hint_direct_match(self, learner):
        """Test resolving entity by direct ID."""
        result = learner._resolve_entity_hint("switch.bedroom_lamp")
        assert result == "switch.bedroom_lamp"

    def test_resolve_entity_hint_partial_match(self, learner):
        """Test resolving entity by partial match."""
        result = learner._resolve_entity_hint("bedroom_lamp")
        assert result == "switch.bedroom_lamp"

    def test_resolve_entity_hint_friendly_name(self, learner):
        """Test resolving entity by friendly name."""
        result = learner._resolve_entity_hint("Kitchen Light")
        assert result == "light.kitchen"

    def test_resolve_entity_hint_not_found(self, learner):
        """Test that unresolvable hints return None."""
        result = learner._resolve_entity_hint("nonexistent entity xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_persist_correction(self, learner, mock_indexer):
        """Test persisting a correction."""
        await learner.persist_correction("switch.lamp", "light")

        assert learner.categories["switch.lamp"] == "light"
        mock_indexer.set_learned_categories.assert_called()
        mock_indexer.index_entity.assert_called_with("switch.lamp")

    @pytest.mark.asyncio
    async def test_persist_correction_saves_to_file(self, learner, tmp_path):
        """Test that corrections are saved to disk."""
        await learner.persist_correction("switch.lamp", "light")

        # Verify file was created
        storage_path = tmp_path / "categories.json"
        assert storage_path.exists()

        with open(storage_path) as f:
            data = json.load(f)
            assert data["categories"]["switch.lamp"] == "light"

    @pytest.mark.asyncio
    async def test_detect_and_persist(self, learner, mock_indexer):
        """Test detecting and persisting in one operation."""
        user_message = "switch.bedroom_lamp is actually a light"
        assistant_message = "I'll remember that."

        corrections = await learner.detect_and_persist(user_message, assistant_message)

        assert len(corrections) == 1
        assert learner.categories.get("switch.bedroom_lamp") == "light"

    @pytest.mark.asyncio
    async def test_async_load(self, learner, mock_indexer, tmp_path):
        """Test loading categories from disk."""
        # Create a categories file
        storage_path = tmp_path / "categories.json"
        with open(storage_path, "w") as f:
            json.dump({"categories": {"switch.test": "light"}}, f)

        learner.storage_path = str(storage_path)
        await learner.async_load()

        assert learner.categories["switch.test"] == "light"
        mock_indexer.set_learned_categories.assert_called()

    @pytest.mark.asyncio
    async def test_async_load_no_file(self, learner):
        """Test loading when file doesn't exist."""
        learner.storage_path = "/nonexistent/path/categories.json"
        await learner.async_load()  # Should not raise
        assert learner.categories == {}

    def test_get_category(self, learner):
        """Test getting a category."""
        learner.categories["switch.test"] = "light"

        assert learner.get_category("switch.test") == "light"
        assert learner.get_category("nonexistent") is None

    def test_remove_category(self, learner, mock_indexer):
        """Test removing a category."""
        learner.categories["switch.test"] = "light"

        result = learner.remove_category("switch.test")

        assert result is True
        assert "switch.test" not in learner.categories
        mock_indexer.set_learned_categories.assert_called()

    def test_remove_category_not_found(self, learner):
        """Test removing a non-existent category."""
        result = learner.remove_category("nonexistent")
        assert result is False

    def test_get_all_categories(self, learner):
        """Test getting all categories."""
        learner.categories = {"a": "1", "b": "2"}

        result = learner.get_all_categories()

        assert result == {"a": "1", "b": "2"}
        # Should return a copy
        result["c"] = "3"
        assert "c" not in learner.categories


class TestCategoryCorrection:
    """Tests for CategoryCorrection dataclass."""

    def test_category_correction_creation(self):
        """Test creating a CategoryCorrection."""
        correction = CategoryCorrection(
            entity_id="switch.lamp",
            category="light",
            source="user",
            confidence=0.9,
        )

        assert correction.entity_id == "switch.lamp"
        assert correction.category == "light"
        assert correction.source == "user"
        assert correction.confidence == 0.9


class TestPatterns:
    """Tests for correction patterns."""

    def test_patterns_compile(self):
        """Test that all patterns compile successfully."""
        assert len(CORRECTION_PATTERNS) > 0
        for pattern in CORRECTION_PATTERNS:
            assert pattern is not None

    def test_valid_categories_not_empty(self):
        """Test that valid categories set is not empty."""
        assert len(VALID_CATEGORIES) > 0
        assert "light" in VALID_CATEGORIES
        assert "switch" in VALID_CATEGORIES
        assert "sensor" in VALID_CATEGORIES
