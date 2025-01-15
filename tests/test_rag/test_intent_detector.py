"""Tests for semantic intent detector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.homeclaw.rag.intent_detector import (
    IntentDetector,
    INTENT_THRESHOLD,
    INTENT_PROTOTYPES,
    cosine_similarity,
)


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self):
        """Test identical vectors return 1.0."""
        vec = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Test orthogonal vectors return 0.0."""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Test opposite vectors return -1.0."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_different_lengths(self):
        """Test different length vectors return 0.0."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec1, vec2) == 0.0

    def test_zero_vector(self):
        """Test zero vector returns 0.0."""
        vec1 = [0.0, 0.0]
        vec2 = [1.0, 2.0]
        assert cosine_similarity(vec1, vec2) == 0.0


class TestIntentDetector:
    """Tests for IntentDetector class."""

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create a mock embedding provider."""
        provider = MagicMock()
        provider.provider_name = "test_provider"
        provider.dimension = 3
        return provider

    @pytest.mark.asyncio
    async def test_async_initialize_caches_prototypes(self, mock_embedding_provider):
        """Test initialization caches all prototype embeddings."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)

        # Mock get_embedding_for_query to return predictable embeddings
        call_count = 0
        async def mock_embedding(provider, query):
            nonlocal call_count
            call_count += 1
            return [float(call_count), 0.0, 0.0]  # Different embedding each call

        import custom_components.homeclaw.rag.intent_detector as module
        original_func = module.get_embedding_for_query
        module.get_embedding_for_query = mock_embedding

        try:
            await detector.async_initialize()

            assert detector._initialized is True
            # Should have cached embeddings for all prototypes
            total_prototypes = sum(len(p) for p in INTENT_PROTOTYPES.values())
            assert len(detector._prototype_cache) == total_prototypes
        finally:
            module.get_embedding_for_query = original_func

    @pytest.mark.asyncio
    async def test_async_initialize_already_initialized(self, mock_embedding_provider):
        """Test initialization is skipped if already done."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)
        detector._initialized = True

        # Should return early without doing anything
        await detector.async_initialize()

        # Cache should still be empty since we skipped initialization
        assert len(detector._prototype_cache) == 0

    @pytest.mark.asyncio
    async def test_detect_intent_not_initialized(self, mock_embedding_provider):
        """Test detect_intent returns empty when not initialized."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)

        result = await detector.detect_intent("what is the temperature")

        assert result == {}

    @pytest.mark.asyncio
    async def test_detect_intent_finds_matching_prototype(self, mock_embedding_provider):
        """Test detect_intent finds matching intent based on similarity."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)
        detector._initialized = True

        # Setup: cache a temperature prototype with embedding [1, 0, 0]
        detector._prototype_cache["device_class:temperature:what is the temperature"] = [1.0, 0.0, 0.0]

        # Mock get_embedding_for_query to return similar embedding
        async def mock_embedding(provider, query):
            return [0.95, 0.1, 0.1]  # Very similar to [1, 0, 0]

        import custom_components.homeclaw.rag.intent_detector as module
        original_func = module.get_embedding_for_query
        module.get_embedding_for_query = mock_embedding

        try:
            result = await detector.detect_intent("tell me the temp")

            # Should detect temperature intent (cosine similarity > threshold)
            assert result.get("device_class") == "temperature"
        finally:
            module.get_embedding_for_query = original_func

    @pytest.mark.asyncio
    async def test_detect_intent_no_match(self, mock_embedding_provider):
        """Test detect_intent returns empty when no prototype matches."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)
        detector._initialized = True

        # Setup: cache a temperature prototype with embedding [1, 0, 0]
        detector._prototype_cache["device_class:temperature:what is the temperature"] = [1.0, 0.0, 0.0]

        # Mock get_embedding_for_query to return dissimilar embedding
        async def mock_embedding(provider, query):
            return [0.0, 0.0, 1.0]  # Orthogonal to [1, 0, 0]

        import custom_components.homeclaw.rag.intent_detector as module
        original_func = module.get_embedding_for_query
        module.get_embedding_for_query = mock_embedding

        try:
            result = await detector.detect_intent("random unrelated query")

            # Should not detect any intent
            assert result == {}
        finally:
            module.get_embedding_for_query = original_func

    @pytest.mark.asyncio
    async def test_detect_intent_handles_embedding_error(self, mock_embedding_provider):
        """Test detect_intent handles embedding errors gracefully."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)
        detector._initialized = True

        # Mock get_embedding_for_query to raise exception
        async def mock_embedding(provider, query):
            raise Exception("Embedding API error")

        import custom_components.homeclaw.rag.intent_detector as module
        original_func = module.get_embedding_for_query
        module.get_embedding_for_query = mock_embedding

        try:
            result = await detector.detect_intent("test query")

            # Should return empty dict on error
            assert result == {}
        finally:
            module.get_embedding_for_query = original_func

    def test_get_cache_stats_not_initialized(self, mock_embedding_provider):
        """Test get_cache_stats when not initialized."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)

        stats = detector.get_cache_stats()

        assert stats["initialized"] is False
        assert stats["cached_prototypes"] == 0

    def test_get_cache_stats_initialized(self, mock_embedding_provider):
        """Test get_cache_stats when initialized."""
        detector = IntentDetector(embedding_provider=mock_embedding_provider)
        detector._initialized = True
        detector._prototype_cache = {"key1": [1.0], "key2": [2.0]}

        stats = detector.get_cache_stats()

        assert stats["initialized"] is True
        assert stats["cached_prototypes"] == 2


class TestIntentPrototypes:
    """Tests for intent prototype configuration."""

    def test_all_intent_types_present(self):
        """Test all expected intent types are defined."""
        intent_types = set()
        for key in INTENT_PROTOTYPES.keys():
            intent_type = key.split(":")[0]
            intent_types.add(intent_type)

        assert "domain" in intent_types
        assert "device_class" in intent_types
        assert "area" in intent_types

    def test_prototypes_have_multilingual_examples(self):
        """Test prototypes include both English and Polish examples."""
        # Check temperature device class has both languages
        temp_prototypes = INTENT_PROTOTYPES.get("device_class:temperature", [])

        has_english = any("temperature" in p.lower() for p in temp_prototypes)
        has_polish = any("temperatura" in p.lower() for p in temp_prototypes)

        assert has_english, "Missing English temperature prototypes"
        assert has_polish, "Missing Polish temperature prototypes"

    def test_threshold_is_reasonable(self):
        """Test threshold is in valid range."""
        assert 0.0 < INTENT_THRESHOLD < 1.0
        assert INTENT_THRESHOLD >= 0.5  # Should be at least 50% similar
