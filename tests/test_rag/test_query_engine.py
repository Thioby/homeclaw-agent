"""Tests for query engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Note: homeassistant mocks are set up in conftest.py

from custom_components.homeclaw.rag.sqlite_store import SearchResult
from custom_components.homeclaw.rag.query_engine import (
    QueryEngine,
    MAX_CONTEXT_LENGTH,
    build_fts_query,
    merge_hybrid_results,
    HYBRID_VECTOR_WEIGHT,
    HYBRID_TEXT_WEIGHT,
)


class TestQueryEngine:
    """Tests for QueryEngine class."""

    @pytest.fixture
    def mock_store(self):
        """Return a mock ChromaStore."""
        store = MagicMock()
        store.search = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def mock_embedding_provider(self):
        """Return a mock embedding provider."""
        provider = MagicMock()
        provider.get_embeddings = AsyncMock(return_value=[[0.1] * 768])
        return provider

    @pytest.fixture
    def query_engine(self, mock_store, mock_embedding_provider):
        """Return a QueryEngine instance."""
        return QueryEngine(
            store=mock_store,
            embedding_provider=mock_embedding_provider,
        )

    @pytest.fixture
    def sample_results(self):
        """Return sample search results."""
        return [
            SearchResult(
                id="light.bedroom_lamp",
                text="Bedroom Lamp light in Bedroom",
                metadata={
                    "domain": "light",
                    "friendly_name": "Bedroom Lamp",
                    "area_name": "Bedroom",
                    "state": "on",
                },
                distance=0.1,
            ),
            SearchResult(
                id="switch.kitchen_outlet",
                text="Kitchen Outlet switch in Kitchen",
                metadata={
                    "domain": "switch",
                    "friendly_name": "Kitchen Outlet",
                    "area_name": "Kitchen",
                    "device_class": "outlet",
                    "state": "off",
                },
                distance=0.3,
            ),
            SearchResult(
                id="sensor.temperature",
                text="Living Room Temperature sensor",
                metadata={
                    "domain": "sensor",
                    "friendly_name": "Living Room Temperature",
                    "device_class": "temperature",
                    "state": "22.5",
                },
                distance=0.5,
            ),
        ]

    @pytest.mark.asyncio
    async def test_search_entities(
        self, query_engine, mock_store, mock_embedding_provider, sample_results
    ):
        """Test searching for entities."""
        mock_store.search.return_value = sample_results

        results = await query_engine.search_entities("bedroom light", top_k=10)

        assert len(results) == 3
        mock_embedding_provider.get_embeddings.assert_called_once_with(
            ["bedroom light"]
        )
        mock_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_entities_with_domain_filter(
        self, query_engine, mock_store, mock_embedding_provider
    ):
        """Test searching with domain filter."""
        await query_engine.search_entities("light", domain_filter="light")

        # Verify filter was passed
        call_args = mock_store.search.call_args
        assert call_args[1]["where"] == {"domain": "light"}

    @pytest.mark.asyncio
    async def test_search_entities_error_handling(
        self, query_engine, mock_embedding_provider
    ):
        """Test that errors return empty results."""
        mock_embedding_provider.get_embeddings = AsyncMock(
            side_effect=Exception("API error")
        )

        results = await query_engine.search_entities("test query")

        assert results == []

    def test_build_compressed_context(self, query_engine, sample_results):
        """Test building compressed context."""
        context = query_engine.build_compressed_context(sample_results)

        assert "Potentially relevant entities" in context
        assert "light.bedroom_lamp" in context
        assert "switch.kitchen_outlet" in context
        assert "Bedroom" in context  # Area should be included
        assert "on" in context  # State for actionable entities

    def test_build_compressed_context_empty(self, query_engine):
        """Test building context with no results."""
        context = query_engine.build_compressed_context([])
        assert context == ""

    def test_build_compressed_context_max_length(self, query_engine, sample_results):
        """Test that context respects max length."""
        # Use very short max length
        context = query_engine.build_compressed_context(sample_results, max_length=100)

        assert len(context) <= 100

    def test_format_entity_basic(self, query_engine):
        """Test basic entity formatting."""
        result = SearchResult(
            id="light.test",
            text="Test Light",
            metadata={"domain": "light"},
            distance=0.1,
        )

        formatted = query_engine._format_entity(result)

        assert "light.test" in formatted
        assert "(light)" in formatted

    def test_format_entity_with_friendly_name(self, query_engine):
        """Test formatting with friendly name."""
        result = SearchResult(
            id="light.test",
            text="Test Light",
            metadata={"domain": "light", "friendly_name": "My Special Light"},
            distance=0.1,
        )

        formatted = query_engine._format_entity(result)

        assert '"My Special Light"' in formatted

    def test_format_entity_with_area(self, query_engine):
        """Test formatting with area."""
        result = SearchResult(
            id="light.test",
            text="Test Light",
            metadata={"domain": "light", "area_name": "Bedroom"},
            distance=0.1,
        )

        formatted = query_engine._format_entity(result)

        assert "in Bedroom" in formatted

    def test_format_entity_with_learned_category(self, query_engine):
        """Test formatting with learned category."""
        result = SearchResult(
            id="switch.lamp",
            text="Lamp Switch",
            metadata={"domain": "switch", "learned_category": "light"},
            distance=0.1,
        )

        formatted = query_engine._format_entity(result)

        assert "<light>" in formatted

    def test_format_entity_with_state(self, query_engine):
        """Test formatting actionable entity with state."""
        result = SearchResult(
            id="light.test",
            text="Test Light",
            metadata={"domain": "light", "state": "on"},
            distance=0.1,
        )

        formatted = query_engine._format_entity(result)

        assert "state:on" in formatted

    def test_format_entity_sensor_no_state(self, query_engine):
        """Test that sensors don't show state in compact format."""
        result = SearchResult(
            id="sensor.test",
            text="Test Sensor",
            metadata={"domain": "sensor", "state": "22.5"},
            distance=0.1,
        )

        formatted = query_engine._format_entity(result)

        # Sensors don't show state in compact format (not actionable)
        assert "state:" not in formatted

    @pytest.mark.asyncio
    async def test_search_and_format(self, query_engine, mock_store, sample_results):
        """Test search and format convenience method."""
        mock_store.search.return_value = sample_results

        context = await query_engine.search_and_format("bedroom light")

        assert "Potentially relevant entities" in context
        assert "light.bedroom_lamp" in context

    @pytest.mark.asyncio
    async def test_search_by_criteria(
        self, query_engine, mock_store, mock_embedding_provider
    ):
        """Test searching with multiple criteria."""
        await query_engine.search_by_criteria(
            query="temperature",
            domain="sensor",
            area="Living Room",
            device_class="temperature",
        )

        call_args = mock_store.search.call_args
        where = call_args[1]["where"]
        assert where["domain"] == "sensor"
        assert where["area_name"] == "Living Room"
        assert where["device_class"] == "temperature"


class TestQueryIntentExtraction:
    """Tests for query intent extraction."""

    @pytest.fixture
    def query_engine(self):
        """Return a QueryEngine instance."""
        return QueryEngine(
            store=MagicMock(),
            embedding_provider=MagicMock(),
        )

    def test_extract_domain_light(self, query_engine):
        """Test extracting light domain."""
        intent = query_engine.extract_query_intent("turn on the bedroom light")
        assert intent.get("domain") == "light"

    def test_extract_domain_switch(self, query_engine):
        """Test extracting switch domain."""
        intent = query_engine.extract_query_intent("check the kitchen outlet")
        assert intent.get("domain") == "switch"

    def test_extract_domain_sensor(self, query_engine):
        """Test extracting sensor domain."""
        intent = query_engine.extract_query_intent("what's the temperature")
        assert intent.get("domain") == "sensor"

    def test_extract_device_class_temperature(self, query_engine):
        """Test extracting temperature device class."""
        intent = query_engine.extract_query_intent("show me temperature sensors")
        assert intent.get("device_class") == "temperature"

    def test_extract_device_class_motion(self, query_engine):
        """Test extracting motion device class."""
        intent = query_engine.extract_query_intent("any motion detected?")
        assert intent.get("device_class") == "motion"

    def test_extract_area_bedroom(self, query_engine):
        """Test extracting bedroom area."""
        intent = query_engine.extract_query_intent("lights in the bedroom")
        assert intent.get("area") == "bedroom"

    def test_extract_area_living_room(self, query_engine):
        """Test extracting living room area."""
        intent = query_engine.extract_query_intent("turn off living room lights")
        assert intent.get("area") == "living room"

    def test_extract_multiple_intents(self, query_engine):
        """Test extracting multiple intents."""
        intent = query_engine.extract_query_intent("temperature in the bedroom")
        assert intent.get("device_class") == "temperature"
        assert intent.get("area") == "bedroom"

    def test_extract_no_intent(self, query_engine):
        """Test query with no extractable intent."""
        intent = query_engine.extract_query_intent("hello there")
        assert intent == {}


class TestBuildFtsQuery:
    """Tests for the FTS5 query builder."""

    def test_simple_query(self):
        """Test basic multi-word query."""
        result = build_fts_query("bedroom light")
        assert result == '"bedroom" AND "light"'

    def test_single_word(self):
        """Test single word query."""
        result = build_fts_query("light")
        assert result == '"light"'

    def test_underscores_preserved(self):
        """Test that underscores stay in tokens (entity_id style)."""
        result = build_fts_query("bedroom_lamp")
        assert result == '"bedroom_lamp"'

    def test_hyphens_split(self):
        """Test that hyphens split into separate tokens."""
        result = build_fts_query("living-room")
        assert result == '"living" AND "room"'

    def test_dots_split(self):
        """Test that dots split into separate tokens (entity_id)."""
        result = build_fts_query("light.bedroom_lamp")
        assert result == '"light" AND "bedroom_lamp"'

    def test_empty_string(self):
        """Test empty string returns None."""
        assert build_fts_query("") is None

    def test_only_punctuation(self):
        """Test string with only punctuation returns None."""
        assert build_fts_query("!@#$%^&*()") is None

    def test_whitespace_only(self):
        """Test whitespace-only returns None."""
        assert build_fts_query("   ") is None

    def test_mixed_case(self):
        """Test that case is preserved (FTS5 is case-insensitive anyway)."""
        result = build_fts_query("Bedroom LAMP")
        assert result == '"Bedroom" AND "LAMP"'

    def test_special_chars_stripped(self):
        """Test special characters act as delimiters."""
        result = build_fts_query("what's the temperature?")
        assert result == '"what" AND "s" AND "the" AND "temperature"'

    def test_numbers_preserved(self):
        """Test numbers are valid tokens."""
        result = build_fts_query("sensor 42")
        assert result == '"sensor" AND "42"'


class TestMergeHybridResults:
    """Tests for hybrid result merging."""

    def test_vector_only(self):
        """Test merge with only vector results."""
        vector = [
            SearchResult(id="a", text="A", metadata={}, distance=0.2),
            SearchResult(id="b", text="B", metadata={}, distance=0.5),
        ]
        merged = merge_hybrid_results(vector, [])

        assert len(merged) == 2
        assert merged[0].id == "a"
        # With text_score=0: final = 0.7 * 0.8 + 0.3 * 0 = 0.56
        # distance = 1 - 0.56 = 0.44
        assert abs(merged[0].distance - 0.44) < 0.01

    def test_keyword_only(self):
        """Test merge with only keyword results."""
        keyword = [
            SearchResult(id="a", text="A", metadata={}, distance=0.1),
        ]
        merged = merge_hybrid_results([], keyword)

        assert len(merged) == 1
        assert merged[0].id == "a"
        # With vector_score=0: final = 0.7 * 0 + 0.3 * 0.9 = 0.27
        # distance = 1 - 0.27 = 0.73
        assert abs(merged[0].distance - 0.73) < 0.01

    def test_overlap_boosts_score(self):
        """Test that results in both sets get boosted scores."""
        vector = [
            SearchResult(id="a", text="A", metadata={"from": "vec"}, distance=0.2),
        ]
        keyword = [
            SearchResult(id="a", text="A", metadata={"from": "kw"}, distance=0.1),
        ]
        merged = merge_hybrid_results(vector, keyword)

        assert len(merged) == 1
        assert merged[0].id == "a"
        # final = 0.7 * 0.8 + 0.3 * 0.9 = 0.56 + 0.27 = 0.83
        # distance = 1 - 0.83 = 0.17
        assert abs(merged[0].distance - 0.17) < 0.01

    def test_deduplication(self):
        """Test that overlapping results are deduplicated."""
        vector = [
            SearchResult(id="a", text="A", metadata={}, distance=0.3),
            SearchResult(id="b", text="B", metadata={}, distance=0.5),
        ]
        keyword = [
            SearchResult(id="a", text="A", metadata={}, distance=0.2),
            SearchResult(id="c", text="C", metadata={}, distance=0.4),
        ]
        merged = merge_hybrid_results(vector, keyword)

        ids = [r.id for r in merged]
        assert len(ids) == 3
        assert set(ids) == {"a", "b", "c"}

    def test_sorted_by_score(self):
        """Test results are sorted by final score (best first)."""
        vector = [
            SearchResult(id="bad", text="Bad", metadata={}, distance=0.9),
            SearchResult(id="good", text="Good", metadata={}, distance=0.1),
        ]
        keyword = [
            SearchResult(id="good", text="Good", metadata={}, distance=0.1),
        ]
        merged = merge_hybrid_results(vector, keyword)

        assert merged[0].id == "good"  # Best score
        assert merged[-1].id == "bad"  # Worst score

    def test_empty_inputs(self):
        """Test merge with both empty returns empty."""
        merged = merge_hybrid_results([], [])
        assert merged == []

    def test_custom_weights(self):
        """Test custom weight parameters."""
        vector = [SearchResult(id="a", text="A", metadata={}, distance=0.0)]
        keyword = [SearchResult(id="a", text="A", metadata={}, distance=0.0)]

        # Equal weights
        merged = merge_hybrid_results(
            vector, keyword, vector_weight=0.5, text_weight=0.5
        )
        assert len(merged) == 1
        # Both scores are 1.0, equal weights: final = 0.5 * 1 + 0.5 * 1 = 1.0
        assert abs(merged[0].distance - 0.0) < 0.01

    def test_weight_normalization(self):
        """Test that weights are normalized to sum to 1.0."""
        vector = [SearchResult(id="a", text="A", metadata={}, distance=0.0)]
        # Weights 7 and 3 should normalize to 0.7 and 0.3
        merged = merge_hybrid_results(vector, [], vector_weight=7.0, text_weight=3.0)
        assert len(merged) == 1
        # vector_score=1.0, text_score=0: final = 0.7 * 1.0 = 0.7
        assert abs(merged[0].distance - 0.3) < 0.01


class TestHybridSearch:
    """Tests for QueryEngine.hybrid_search method."""

    @pytest.fixture
    def mock_store(self):
        """Return a mock SqliteStore."""
        store = MagicMock()
        store.search = AsyncMock(return_value=[])
        store.keyword_search = AsyncMock(return_value=[])
        store.fts_available = True
        return store

    @pytest.fixture
    def mock_embedding_provider(self):
        """Return a mock embedding provider."""
        provider = MagicMock()
        provider.get_embeddings = AsyncMock(return_value=[[0.1] * 768])
        return provider

    @pytest.fixture
    def query_engine(self, mock_store, mock_embedding_provider):
        """Return a QueryEngine instance."""
        return QueryEngine(
            store=mock_store,
            embedding_provider=mock_embedding_provider,
        )

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self, query_engine, mock_store):
        """Test hybrid search combines vector and keyword results."""
        vector_result = SearchResult(
            id="light.bedroom",
            text="Bedroom Light",
            metadata={"domain": "light"},
            distance=0.2,
        )
        keyword_result = SearchResult(
            id="light.kitchen",
            text="Kitchen Light",
            metadata={"domain": "light"},
            distance=0.3,
        )
        mock_store.search.return_value = [vector_result]
        mock_store.keyword_search.return_value = [keyword_result]

        results = await query_engine.hybrid_search("bedroom light", top_k=10)

        assert len(results) == 2
        mock_store.search.assert_called_once()
        mock_store.keyword_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search_vector_only_when_fts_unavailable(
        self, query_engine, mock_store
    ):
        """Test falls back to vector-only when FTS5 is not available."""
        mock_store.fts_available = False
        vector_result = SearchResult(
            id="light.test", text="Test", metadata={}, distance=0.1
        )
        mock_store.search.return_value = [vector_result]

        results = await query_engine.hybrid_search("test", top_k=10)

        assert len(results) == 1
        assert results[0].id == "light.test"
        mock_store.keyword_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_hybrid_search_with_where_filter(self, query_engine, mock_store):
        """Test hybrid search passes where filter to vector search."""
        mock_store.search.return_value = []

        await query_engine.hybrid_search("test", top_k=5, where={"domain": "light"})

        call_args = mock_store.search.call_args
        assert call_args[1]["where"] == {"domain": "light"}

    @pytest.mark.asyncio
    async def test_hybrid_search_min_similarity_filter(self, query_engine, mock_store):
        """Test hybrid search applies min_similarity threshold."""
        # Vector result with low similarity (distance 0.8 -> similarity 0.2)
        low_sim = SearchResult(id="low", text="Low", metadata={}, distance=0.8)
        mock_store.search.return_value = [low_sim]
        mock_store.keyword_search.return_value = []

        results = await query_engine.hybrid_search("test", top_k=10, min_similarity=0.5)

        # Result should be filtered out (similarity 0.2 < 0.5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_hybrid_search_overlap_boost(self, query_engine, mock_store):
        """Test that results found by both searches get boosted."""
        same_result_vec = SearchResult(
            id="light.a", text="A", metadata={}, distance=0.3
        )
        same_result_kw = SearchResult(id="light.a", text="A", metadata={}, distance=0.2)
        mock_store.search.return_value = [same_result_vec]
        mock_store.keyword_search.return_value = [same_result_kw]

        results = await query_engine.hybrid_search("light a", top_k=10)

        assert len(results) == 1
        assert results[0].id == "light.a"
        # Merged score should be higher than either individual score
        # vec: 0.7, kw: 0.8 -> final = 0.7*0.7 + 0.3*0.8 = 0.49 + 0.24 = 0.73
        assert results[0].distance < same_result_vec.distance

    @pytest.mark.asyncio
    async def test_hybrid_search_error_returns_empty(
        self, query_engine, mock_store, mock_embedding_provider
    ):
        """Test that errors return empty results gracefully."""
        mock_embedding_provider.get_embeddings = AsyncMock(
            side_effect=Exception("API error")
        )

        results = await query_engine.hybrid_search("test")

        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_candidate_multiplier(self, query_engine, mock_store):
        """Test that candidate multiplier fetches more than top_k."""
        mock_store.search.return_value = []

        await query_engine.hybrid_search("test", top_k=5)

        # Should request 5 * 4 = 20 candidates from vector search
        call_args = mock_store.search.call_args
        assert call_args[1]["n_results"] == 20
