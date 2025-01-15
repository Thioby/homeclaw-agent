"""Fixtures for RAG system tests."""

import sys
import asyncio
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

@pytest.fixture
def hass(hass):
    """Return a Home Assistant instance with a temporary directory config path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hass.config.path = lambda *args: str(Path(tmpdir).joinpath(*args))
        yield hass


@pytest.fixture
def config_entry():
    """Return a mock config entry with OAuth tokens.

    Note: OAuth tokens are stored in the nested 'gemini_oauth' dict,
    matching the real config entry structure used by the integration.
    """
    mock_entry = MagicMock()
    mock_entry.data = {
        "ai_provider": "gemini_oauth",
        "gemini_oauth": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": 9999999999,  # Far future
        },
    }
    return mock_entry


@pytest.fixture
def config():
    """Return a basic config dictionary."""
    return {
        "ai_provider": "openai",
        "openai_token": "sk-test-token-12345",
    }


@pytest.fixture
def chroma_store(tmp_path):
    """Return a ChromaStore instance with temporary directory."""
    from custom_components.homeclaw.rag.chroma_store import ChromaStore

    return ChromaStore(persist_directory=str(tmp_path / "chroma_db"))


@dataclass
class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    dimension: int = 768
    provider_name: str = "mock"
    _call_count: int = field(default=0, repr=False)
    _embeddings: list[list[float]] = field(default_factory=list, repr=False)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate fake embeddings."""
        self._call_count += 1
        embeddings = []
        for i, text in enumerate(texts):
            # Create deterministic but varied embeddings based on text hash
            base = hash(text) % 100 / 100
            embedding = [base + j * 0.001 for j in range(self.dimension)]
            embeddings.append(embedding)
        self._embeddings.extend(embeddings)
        return embeddings


@pytest.fixture
def mock_embedding_provider():
    """Return a mock embedding provider."""
    return MockEmbeddingProvider()


@pytest.fixture
def mock_entity_registry():
    """Return a mock entity registry with test entities."""
    mock_registry = MagicMock()

    # Create mock entity entries
    entries = {}

    @dataclass
    class MockEntityEntry:
        entity_id: str
        name: str | None = None
        area_id: str | None = None
        device_class: str | None = None
        original_device_class: str | None = None

    # Add test entities
    test_entities = [
        MockEntityEntry(
            entity_id="light.bedroom_lamp",
            name="Bedroom Lamp",
            area_id="bedroom",
            device_class="light",
        ),
        MockEntityEntry(
            entity_id="switch.kitchen_outlet",
            name="Kitchen Outlet",
            area_id="kitchen",
        ),
        MockEntityEntry(
            entity_id="sensor.living_room_temperature",
            name="Living Room Temperature",
            area_id="living_room",
            device_class="temperature",
        ),
        MockEntityEntry(
            entity_id="switch.bedroom_lamp_switch",
            name="Bedroom Lamp Switch",
            area_id="bedroom",
        ),
        MockEntityEntry(
            entity_id="cover.garage_door",
            name="Garage Door",
            area_id="garage",
            device_class="garage",
        ),
    ]

    for entry in test_entities:
        entries[entry.entity_id] = entry

    mock_registry.entities = entries
    mock_registry.async_get = lambda eid: entries.get(eid)

    return mock_registry


@pytest.fixture
def mock_area_registry():
    """Return a mock area registry."""
    mock_registry = MagicMock()

    @dataclass
    class MockArea:
        name: str
        id: str

    areas = {
        "bedroom": MockArea(name="Bedroom", id="bedroom"),
        "kitchen": MockArea(name="Kitchen", id="kitchen"),
        "living_room": MockArea(name="Living Room", id="living_room"),
        "garage": MockArea(name="Garage", id="garage"),
    }

    mock_registry.async_get_area = lambda aid: areas.get(aid)

    return mock_registry


@pytest.fixture
def mock_states():
    """Return mock Home Assistant states."""
    states = {}

    @dataclass
    class MockState:
        entity_id: str
        state: str
        attributes: dict[str, Any]

    test_states = [
        MockState(
            entity_id="light.bedroom_lamp",
            state="on",
            attributes={"friendly_name": "Bedroom Lamp", "brightness": 255},
        ),
        MockState(
            entity_id="switch.kitchen_outlet",
            state="off",
            attributes={"friendly_name": "Kitchen Outlet"},
        ),
        MockState(
            entity_id="sensor.living_room_temperature",
            state="22.5",
            attributes={"friendly_name": "Living Room Temperature", "unit_of_measurement": "°C"},
        ),
        MockState(
            entity_id="switch.bedroom_lamp_switch",
            state="on",
            attributes={"friendly_name": "Bedroom Lamp Switch"},
        ),
        MockState(
            entity_id="cover.garage_door",
            state="closed",
            attributes={"friendly_name": "Garage Door"},
        ),
    ]

    for state in test_states:
        states[state.entity_id] = state

    mock_states_obj = MagicMock()
    mock_states_obj.get = lambda eid: states.get(eid)
    mock_states_obj.async_all = lambda: list(states.values())

    return mock_states_obj


@pytest.fixture
def hass_with_entities(hass, mock_entity_registry, mock_area_registry, mock_states):
    """Return a Home Assistant mock with entity/area registries and states."""
    hass.states = mock_states

    # Configure the module-level registry mocks using patch to ensure they stay in place
    with patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_registry), \
         patch("homeassistant.helpers.area_registry.async_get", return_value=mock_area_registry):
        yield hass