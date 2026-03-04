"""Session context retrieval for RAG.

Searches session chunks (vector + keyword) with optional time-range
expansion for temporal queries.  Extracted from context_retriever.py
to keep files under the 300-line project limit.
"""

from __future__ import annotations

import logging
from typing import Any

from ._temporal import has_temporal_hint

_LOGGER = logging.getLogger(__name__)


async def get_session_context(
    query: str,
    embedding_provider: Any,
    store: Any,
    min_similarity: float,
    *,
    top_k: int = 3,
    provider: Any | None = None,
    model: str | None = None,
) -> list[dict[str, Any]]:
    """Search session chunks for relevant conversational context.

    Args:
        query: The user's query text.
        embedding_provider: Cached embedding provider for query embeddings.
        store: SqliteStore for low-level search operations.
        min_similarity: Minimum cosine similarity threshold (0-1).
        top_k: Maximum number of session chunks to include.
        provider: Optional AI provider for LLM time-range expansion.
        model: Optional model name for time-range expansion.

    Returns:
        List of dictionaries containing session chunks, or empty list.
    """
    start_date, end_date = await _resolve_time_range(query, provider, model)

    vector_results = await _search_vector(
        query, embedding_provider, store, top_k, min_similarity, start_date, end_date
    )
    keyword_results = await _search_keyword(query, store, top_k, start_date, end_date)

    results = _merge_and_filter(vector_results, keyword_results, min_similarity, top_k)
    if not results:
        return []

    formatted = _format_chunks(results)
    _LOGGER.debug(
        "Session context: %d chunks found for query: %s...",
        len(formatted),
        query[:50],
    )
    return formatted


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


async def _resolve_time_range(
    query: str,
    provider: Any | None,
    model: str | None,
) -> tuple[str | None, str | None]:
    """Expand temporal hints in *query* to a concrete date range via LLM."""
    from .query_expansion import expand_query_time_range

    if not provider or not has_temporal_hint(query):
        return None, None

    start_date, end_date = await expand_query_time_range(query, provider, model)
    if start_date or end_date:
        _LOGGER.debug(
            "Applying time filter to RAG session search: %s to %s",
            start_date,
            end_date,
        )
    return start_date, end_date


async def _search_vector(
    query: str,
    embedding_provider: Any,
    store: Any,
    top_k: int,
    min_similarity: float,
    start_date: str | None,
    end_date: str | None,
) -> list[Any]:
    """Run vector similarity search on session chunks."""
    from .embeddings import get_embedding_for_query

    query_embedding = await get_embedding_for_query(embedding_provider, query)
    return await store.search_session_chunks(
        query_embedding=query_embedding,
        n_results=top_k * 4,
        min_similarity=min_similarity,
        start_date=start_date,
        end_date=end_date,
    )


async def _search_keyword(
    query: str,
    store: Any,
    top_k: int,
    start_date: str | None,
    end_date: str | None,
) -> list[Any]:
    """Run FTS5 keyword search on session chunks (if available)."""
    from .query_engine import build_fts_query

    fts_query = build_fts_query(query)
    if not fts_query:
        return []
    return await store.keyword_search_sessions(
        fts_query=fts_query,
        n_results=top_k * 4,
        start_date=start_date,
        end_date=end_date,
    )


def _merge_and_filter(
    vector_results: list[Any],
    keyword_results: list[Any],
    min_similarity: float,
    top_k: int,
) -> list[Any]:
    """Merge hybrid results and apply similarity threshold + limit."""
    from .query_engine import merge_hybrid_results

    if vector_results and keyword_results:
        merged = merge_hybrid_results(
            vector_results,
            keyword_results,
            vector_weight=0.7,
            text_weight=0.3,
        )
    elif vector_results:
        merged = vector_results
    elif keyword_results:
        merged = keyword_results
    else:
        return []

    return [r for r in merged if (1.0 - r.distance) >= min_similarity][:top_k]


def _format_chunks(results: list[Any]) -> list[dict[str, Any]]:
    """Format search results into structured chunk dictionaries."""
    formatted: list[dict[str, Any]] = []
    for r in results:
        text = r.text if len(r.text) <= 500 else r.text[:500] + "..."
        chunk_data: dict[str, Any] = {"text": text}
        if r.metadata and "timestamp" in r.metadata:
            chunk_data["timestamp"] = r.metadata["timestamp"]
        formatted.append(chunk_data)
    return formatted
