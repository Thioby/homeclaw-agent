"""Tests for time-aware query expansion."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.homeclaw.rag.query_expansion import (
    _EXPANSION_CACHE,
    expand_query_time_range,
)


@pytest.mark.asyncio
class TestQueryExpansion:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear expansion cache before each test to prevent cross-test leaks."""
        _EXPANSION_CACHE.clear()
        yield
        _EXPANSION_CACHE.clear()

    @pytest.fixture
    def mock_provider(self):
        """Return a mock AI provider."""
        provider = MagicMock()
        provider.get_response = AsyncMock()
        return provider

    async def test_expand_query_no_dates(self, mock_provider):
        """Test query with no temporal references."""
        mock_provider.get_response.return_value = '{"start": "N/A", "end": "N/A"}'

        start, end = await expand_query_time_range("Włącz światło", mock_provider)

        assert start is None
        assert end is None

    async def test_expand_query_with_dates(self, mock_provider):
        """Test query with temporal references."""
        mock_provider.get_response.return_value = (
            '{"start": "2024-03-01", "end": "2024-03-31"}'
        )

        start, end = await expand_query_time_range(
            "Co się stało w marcu?", mock_provider
        )

        assert start == "2024-03-01"
        assert end == "2024-03-31"

    async def test_expand_query_markdown_json(self, mock_provider):
        """Test parsing of markdown json blocks."""
        mock_provider.get_response.return_value = (
            '```json\n{"start": "2024-03-01", "end": "2024-03-31"}\n```'
        )

        start, end = await expand_query_time_range(
            "Co się stało w marcu?", mock_provider
        )

        assert start == "2024-03-01"
        assert end == "2024-03-31"

    async def test_expand_query_failure(self, mock_provider):
        """Test fallback on LLM failure."""
        mock_provider.get_response.side_effect = Exception("API Error")

        start, end = await expand_query_time_range("Włącz światło", mock_provider)

        assert start is None
        assert end is None

    async def test_expand_query_invalid_json(self, mock_provider):
        """Test fallback on invalid JSON from LLM."""
        mock_provider.get_response.return_value = (
            "I think the dates are 2024-03-01 to 2024-03-31"
        )

        start, end = await expand_query_time_range("Włącz światło", mock_provider)

        assert start is None
        assert end is None

    async def test_expand_query_partial_date_start_only(self, mock_provider):
        """Test query where only start date is valid — partial range accepted."""
        mock_provider.get_response.return_value = (
            '{"start": "2024-03-01", "end": "N/A"}'
        )

        start, end = await expand_query_time_range(
            "Co było na początku marca?", mock_provider
        )

        assert start == "2024-03-01"
        assert end is None

    async def test_expand_query_partial_date_end_only(self, mock_provider):
        """Test query where only end date is valid — partial range accepted."""
        mock_provider.get_response.return_value = (
            '{"start": "N/A", "end": "2024-03-31"}'
        )

        start, end = await expand_query_time_range(
            "Co było do końca marca?", mock_provider
        )

        assert start is None
        assert end == "2024-03-31"

    async def test_expand_query_inverted_dates(self, mock_provider):
        """Test query where start is after end."""
        mock_provider.get_response.return_value = (
            '{"start": "2024-03-31", "end": "2024-03-01"}'
        )

        start, end = await expand_query_time_range("W marcu?", mock_provider)

        assert start is None
        assert end is None

    async def test_expand_query_list_response(self, mock_provider):
        """Test fallback when LLM returns list instead of dict."""
        mock_provider.get_response.return_value = (
            '[{"start": "2024-03-01", "end": "2024-03-31"}]'
        )

        start, end = await expand_query_time_range("W marcu?", mock_provider)

        assert start is None
        assert end is None

    async def test_cache_hit_avoids_llm_call(self, mock_provider):
        """Second identical query should use cache, not call LLM again."""
        mock_provider.get_response.return_value = (
            '{"start": "2024-01-01", "end": "2024-01-31"}'
        )

        # First call — populates cache
        s1, e1 = await expand_query_time_range("w styczniu", mock_provider)
        assert s1 == "2024-01-01"
        assert mock_provider.get_response.call_count == 1

        # Second call — should hit cache
        s2, e2 = await expand_query_time_range("w styczniu", mock_provider)
        assert s2 == "2024-01-01"
        assert e2 == "2024-01-31"
        assert mock_provider.get_response.call_count == 1  # NOT called again
