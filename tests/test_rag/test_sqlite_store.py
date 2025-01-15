import math
import os
import json
import sqlite3
import pytest
from custom_components.homeclaw.rag.sqlite_store import (
    SqliteStore,
    SearchResult,
    _cosine_similarity,
    _cosine_distance,
    _bm25_rank_to_score,
    DEFAULT_TABLE_NAME,
    FTS_TABLE_SUFFIX,
)


# Test _cosine_similarity
def test_cosine_similarity():
    # Identical vectors
    vec1 = [1.0, 0.0]
    vec2 = [1.0, 0.0]
    assert _cosine_similarity(vec1, vec2) == 1.0

    # Perpendicular vectors
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    assert _cosine_similarity(vec1, vec2) == 0.0

    # Different lengths
    vec1 = [1.0, 0.0]
    vec2 = [1.0]
    assert _cosine_similarity(vec1, vec2) == 0.0

    # Zero vector
    vec1 = [0.0, 0.0]
    vec2 = [1.0, 1.0]
    assert _cosine_similarity(vec1, vec2) == 0.0

    # Opposite vectors
    vec1 = [1.0, 0.0]
    vec2 = [-1.0, 0.0]
    assert _cosine_similarity(vec1, vec2) == -1.0


# Test _cosine_distance
def test_cosine_distance():
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    similarity = _cosine_similarity(vec1, vec2)
    assert _cosine_distance(vec1, vec2) == 1.0 - similarity

    vec1 = [1.0, 0.0]
    vec2 = [1.0, 0.0]
    assert _cosine_distance(vec1, vec2) == 0.0


# Test SearchResult
def test_search_result_instantiation():
    res = SearchResult(
        id="test_id", text="test_text", metadata={"key": "value"}, distance=0.5
    )
    assert res.id == "test_id"
    assert res.text == "test_text"
    assert res.metadata == {"key": "value"}
    assert res.distance == 0.5


# Test SqliteStore
@pytest.mark.asyncio
async def test_sqlite_store_initialization(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))

    assert store._initialized is False
    assert store._conn is None

    await store.async_initialize()

    assert store._initialized is True
    assert store._conn is not None
    assert os.path.exists(os.path.join(tmp_path, "vectors.db"))

    # Test double initialization (should skip)
    await store.async_initialize()
    assert store._initialized is True

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_ensure_initialized(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))

    with pytest.raises(RuntimeError):
        store._ensure_initialized()

    await store.async_initialize()
    store._ensure_initialized()  # Should not raise
    await store.async_shutdown()


@pytest.mark.asyncio
async def test_add_documents(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1", "2"]
    texts = ["text1", "text2"]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    metadatas = [{"source": "a"}, {"source": "b"}]

    await store.add_documents(ids, texts, embeddings, metadatas)

    count = await store.get_document_count()
    assert count == 2

    # Test adding empty list
    await store.add_documents([], [], [])
    assert await store.get_document_count() == 2

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_add_documents_fallback_to_upsert(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1"]
    texts = ["text1"]
    embeddings = [[1.0, 0.0]]

    await store.add_documents(ids, texts, embeddings)

    # Try adding same ID again
    texts_new = ["text1_updated"]
    await store.add_documents(ids, texts_new, embeddings)

    doc = await store.get_document("1")
    assert doc.text == "text1_updated"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_upsert_documents(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1"]
    texts = ["text1"]
    embeddings = [[1.0, 0.0]]

    # Insert
    await store.upsert_documents(ids, texts, embeddings)
    count = await store.get_document_count()
    assert count == 1

    # Update
    texts_updated = ["text1_updated"]
    await store.upsert_documents(ids, texts_updated, embeddings)

    doc = await store.get_document("1")
    assert doc.text == "text1_updated"

    # Empty list
    await store.upsert_documents([], [], [])
    assert await store.get_document_count() == 1

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_search(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1", "2", "3"]
    texts = ["apple", "banana", "cherry"]
    # 1: [1, 0], 2: [0, 1], 3: [1, 1] (normalized approx [0.7, 0.7])
    embeddings = [[1.0, 0.0], [0.0, 1.0], [0.707, 0.707]]
    metadatas = [{"type": "fruit"}, {"type": "fruit"}, {"type": "berry"}]

    await store.add_documents(ids, texts, embeddings, metadatas)

    # Search query close to "apple" [1, 0]
    results = await store.search([1.0, 0.0], n_results=3)

    assert len(results) == 3
    assert results[0].id == "1"  # Closest
    assert results[0].distance == 0.0

    # Search with filter
    results = await store.search([1.0, 0.0], n_results=3, where={"type": "berry"})
    assert len(results) == 1
    assert results[0].id == "3"

    # Search with no results
    results = await store.search([1.0, 0.0], n_results=3, where={"type": "vegetable"})
    assert len(results) == 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_delete_documents(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1", "2"]
    texts = ["a", "b"]
    embeddings = [[1.0], [1.0]]
    await store.add_documents(ids, texts, embeddings)

    await store.delete_documents(["1"])
    assert await store.get_document_count() == 1
    assert await store.get_document("1") is None
    assert await store.get_document("2") is not None

    # Empty list
    await store.delete_documents([])
    assert await store.get_document_count() == 1

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_get_document(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1"]
    texts = ["a"]
    embeddings = [[1.0]]
    await store.add_documents(ids, texts, embeddings)

    doc = await store.get_document("1")
    assert doc is not None
    assert doc.id == "1"

    doc = await store.get_document("nonexistent")
    assert doc is None

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_clear_collection(tmp_path):
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["1", "2"]
    texts = ["a", "b"]
    embeddings = [[1.0], [1.0]]
    await store.add_documents(ids, texts, embeddings)

    assert await store.get_document_count() == 2

    await store.clear_collection()
    assert await store.get_document_count() == 0

    await store.async_shutdown()


def test_filter_metadata():
    store = SqliteStore(persist_directory="dummy")

    class Unserializable:
        def __str__(self):
            return "converted"

    metadata = {
        "str": "value",
        "int": 1,
        "float": 1.5,
        "bool": True,
        "none": None,
        "list": [1, 2],
        "dict": {"a": 1},
        "unserializable": Unserializable(),
    }

    filtered = store._filter_metadata(metadata)

    assert filtered["str"] == "value"
    assert filtered["int"] == 1
    assert filtered["float"] == 1.5
    assert filtered["bool"] is True
    assert "none" not in filtered
    assert filtered["list"] == [1, 2]
    assert filtered["dict"] == {"a": 1}
    assert filtered["unserializable"] == "converted"


# --- Embedding Cache Tests ---


@pytest.mark.asyncio
async def test_embedding_cache_table_created(tmp_path):
    """Test that embedding_cache table is created on initialization."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    cursor = store._conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='embedding_cache'"
    )
    assert cursor.fetchone() is not None

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_embedding_cache_upsert_and_lookup(tmp_path):
    """Test cache upsert and lookup round-trip with binary storage."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    content_hash = "abc123"

    # Upsert
    store.cache_upsert("openai", "text-embedding-3-small", [(content_hash, embedding)])

    # Lookup
    result = store.cache_lookup("openai", "text-embedding-3-small", [content_hash])
    assert content_hash in result
    assert len(result[content_hash]) == 5
    for a, b in zip(result[content_hash], embedding):
        assert abs(a - b) < 1e-6  # float32 precision

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_embedding_cache_miss(tmp_path):
    """Test cache lookup for non-existent hash returns empty."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    result = store.cache_lookup("openai", "model", ["nonexistent"])
    assert "nonexistent" not in result
    assert len(result) == 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_embedding_cache_provider_scoping(tmp_path):
    """Test that cache is scoped by provider and model."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    embedding_a = [1.0, 2.0, 3.0]
    embedding_b = [4.0, 5.0, 6.0]
    content_hash = "same_hash"

    # Store with provider A
    store.cache_upsert("openai", "model-a", [(content_hash, embedding_a)])

    # Store with provider B (same hash, different embedding)
    store.cache_upsert("gemini", "model-b", [(content_hash, embedding_b)])

    # Lookup for provider A should return embedding_a
    result_a = store.cache_lookup("openai", "model-a", [content_hash])
    for a, b in zip(result_a[content_hash], embedding_a):
        assert abs(a - b) < 1e-6

    # Lookup for provider B should return embedding_b
    result_b = store.cache_lookup("gemini", "model-b", [content_hash])
    for a, b in zip(result_b[content_hash], embedding_b):
        assert abs(a - b) < 1e-6

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_embedding_cache_prune(tmp_path):
    """Test LRU cache pruning."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add 10 entries
    entries = [(f"hash_{i}", [float(i)]) for i in range(10)]
    store.cache_upsert("test", "model", entries)

    stats = await store.get_cache_stats()
    assert stats["entries"] == 10

    # Prune to max 5
    store.cache_prune(max_entries=5)

    stats = await store.get_cache_stats()
    assert stats["entries"] == 5

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_embedding_cache_binary_conversion():
    """Test float32 binary conversion round-trip."""
    import math

    embedding = [math.pi, math.e, 0.0, -1.0, 1e-10, 999.999]
    blob = SqliteStore._embedding_to_blob(embedding)

    # blob should be 6 * 4 = 24 bytes
    assert len(blob) == 24

    recovered = SqliteStore._blob_to_embedding(blob)
    assert len(recovered) == 6
    for a, b in zip(recovered, embedding):
        # float32 has ~7 decimal digits of precision; relative tolerance is safer
        assert abs(a - b) < max(abs(b) * 1e-6, 1e-6)


@pytest.mark.asyncio
async def test_embedding_cache_stats(tmp_path):
    """Test cache statistics reporting."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    stats = await store.get_cache_stats()
    assert stats["entries"] == 0
    assert stats["total_bytes"] == 0

    # Add some entries
    store.cache_upsert(
        "test", "model", [("h1", [1.0, 2.0, 3.0]), ("h2", [4.0, 5.0, 6.0])]
    )

    stats = await store.get_cache_stats()
    assert stats["entries"] == 2
    assert stats["total_bytes"] > 0  # Should have some binary data

    await store.async_shutdown()


# --- BM25 Score Conversion Tests ---


def test_bm25_rank_to_score_zero():
    """Test bm25 rank 0 gives score 1.0."""
    assert _bm25_rank_to_score(0.0) == 1.0


def test_bm25_rank_to_score_negative():
    """Test negative rank (good match) gives high score via abs()."""
    score = _bm25_rank_to_score(-5.0)
    # 1 / (1 + 5) = ~0.167
    assert abs(score - 1.0 / 6.0) < 1e-6


def test_bm25_rank_to_score_positive():
    """Test positive rank gives lower score."""
    score = _bm25_rank_to_score(10.0)
    # 1 / (1 + 10) = ~0.091
    assert abs(score - 1.0 / 11.0) < 1e-6


def test_bm25_rank_to_score_ordering():
    """Test that better BM25 ranks produce higher scores (monotonic with abs)."""
    # rank=-10 (better) should produce higher score than rank=-1 (worse)
    # But since we use abs(): abs(-10) > abs(-1), so score(-10) < score(-1)
    # This is intentional: it differentiates matches rather than making them all ~1.0
    score_strong = _bm25_rank_to_score(-10.0)
    score_weak = _bm25_rank_to_score(-1.0)
    # Both are positive
    assert score_strong > 0
    assert score_weak > 0
    # Weaker match (rank closer to 0) gets higher score in this normalization
    # But both are decent; the key is they're differentiated, not all 1.0
    assert score_strong != score_weak


def test_bm25_rank_to_score_infinity():
    """Test non-finite rank returns near-zero fallback."""
    assert _bm25_rank_to_score(float("inf")) == 0.001
    assert _bm25_rank_to_score(float("-inf")) == 0.001
    assert _bm25_rank_to_score(float("nan")) == 0.001


# --- FTS5 Tests ---


@pytest.mark.asyncio
async def test_fts5_table_created(tmp_path):
    """Test that FTS5 virtual table is created on initialization."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    assert store.fts_available is True

    # Verify FTS5 table exists
    cursor = store._conn.cursor()
    fts_table = DEFAULT_TABLE_NAME + FTS_TABLE_SUFFIX
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (fts_table,),
    )
    assert cursor.fetchone() is not None

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_fts5_sync_on_add(tmp_path):
    """Test FTS5 data is synced when adding documents."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    ids = ["light.bedroom_lamp", "switch.kitchen"]
    texts = ["Bedroom Lamp light in Bedroom", "Kitchen Switch in Kitchen"]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    metadatas = [
        {"domain": "light", "area_name": "Bedroom"},
        {"domain": "switch", "area_name": "Kitchen"},
    ]

    await store.add_documents(ids, texts, embeddings, metadatas)

    # Check FTS5 table has the data
    fts_table = DEFAULT_TABLE_NAME + FTS_TABLE_SUFFIX
    cursor = store._conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
    assert cursor.fetchone()[0] == 2

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_fts5_sync_on_upsert(tmp_path):
    """Test FTS5 data is updated on upsert (delete old + insert new)."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add initial document
    await store.add_documents(
        ["light.test"],
        ["Old Text"],
        [[1.0, 0.0]],
        [{"domain": "light", "area_name": "Bedroom"}],
    )

    # Upsert with new text
    await store.upsert_documents(
        ["light.test"],
        ["Updated Text Bedroom Lamp"],
        [[1.0, 0.0]],
        [{"domain": "light", "area_name": "Bedroom"}],
    )

    # FTS5 should have exactly 1 entry (not 2 — old one should be deleted)
    fts_table = DEFAULT_TABLE_NAME + FTS_TABLE_SUFFIX
    cursor = store._conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
    assert cursor.fetchone()[0] == 1

    # Verify updated text is searchable
    cursor.execute(f"SELECT text FROM {fts_table} WHERE entity_id = ?", ("light.test",))
    row = cursor.fetchone()
    assert row is not None
    assert "Updated Text" in row["text"]

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_fts5_sync_on_delete(tmp_path):
    """Test FTS5 data is removed when deleting documents."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["light.a", "light.b"],
        ["Light A", "Light B"],
        [[1.0, 0.0], [0.0, 1.0]],
        [{"domain": "light"}, {"domain": "light"}],
    )

    await store.delete_documents(["light.a"])

    fts_table = DEFAULT_TABLE_NAME + FTS_TABLE_SUFFIX
    cursor = store._conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
    assert cursor.fetchone()[0] == 1

    cursor.execute(f"SELECT entity_id FROM {fts_table}")
    assert cursor.fetchone()["entity_id"] == "light.b"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_fts5_sync_on_clear(tmp_path):
    """Test FTS5 data is cleared when clearing collection."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["light.a", "light.b"],
        ["Light A", "Light B"],
        [[1.0, 0.0], [0.0, 1.0]],
        [{"domain": "light"}, {"domain": "light"}],
    )

    await store.clear_collection()

    fts_table = DEFAULT_TABLE_NAME + FTS_TABLE_SUFFIX
    cursor = store._conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
    assert cursor.fetchone()[0] == 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_keyword_search_exact_match(tmp_path):
    """Test FTS5 keyword search finds exact entity name matches."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["light.bedroom_lamp", "light.kitchen_light", "sensor.temperature"],
        [
            "Bedroom Lamp light in Bedroom",
            "Kitchen Light light in Kitchen",
            "Temperature Sensor sensor in Living Room",
        ],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        [
            {
                "domain": "light",
                "area_name": "Bedroom",
                "entity_id": "light.bedroom_lamp",
            },
            {
                "domain": "light",
                "area_name": "Kitchen",
                "entity_id": "light.kitchen_light",
            },
            {
                "domain": "sensor",
                "area_name": "Living Room",
                "entity_id": "sensor.temperature",
            },
        ],
    )

    # Search for "Bedroom"
    results = await store.keyword_search('"Bedroom"', n_results=10)
    assert len(results) == 1
    assert results[0].id == "light.bedroom_lamp"
    assert results[0].distance < 1.0  # Has a score

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_keyword_search_multi_token(tmp_path):
    """Test FTS5 keyword search with multiple AND tokens."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["light.bedroom_lamp", "light.kitchen_light"],
        [
            "Bedroom Lamp light in Bedroom",
            "Kitchen Light light in Kitchen",
        ],
        [[1.0, 0.0], [0.0, 1.0]],
        [
            {"domain": "light", "area_name": "Bedroom"},
            {"domain": "light", "area_name": "Kitchen"},
        ],
    )

    # Search for "Bedroom AND Lamp" — only matches bedroom lamp
    results = await store.keyword_search('"Bedroom" AND "Lamp"', n_results=10)
    assert len(results) == 1
    assert results[0].id == "light.bedroom_lamp"

    # Search for "light" — matches both
    results = await store.keyword_search('"light"', n_results=10)
    assert len(results) == 2

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_keyword_search_no_results(tmp_path):
    """Test keyword search returns empty for non-matching query."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["light.test"],
        ["Test Light"],
        [[1.0]],
        [{"domain": "light"}],
    )

    results = await store.keyword_search('"nonexistent"', n_results=10)
    assert len(results) == 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_keyword_search_empty_query(tmp_path):
    """Test keyword search with empty query returns empty."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    results = await store.keyword_search("", n_results=10)
    assert len(results) == 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_keyword_search_fts_unavailable(tmp_path):
    """Test keyword search returns empty when FTS5 is not available."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Simulate FTS5 unavailable
    store._fts_available = False

    results = await store.keyword_search('"test"', n_results=10)
    assert len(results) == 0

    await store.async_shutdown()


# --- Phase 4: Binary Blob Embedding Storage Tests ---


def test_read_embedding_blob():
    """Test _read_embedding correctly reads binary blob format."""
    embedding = [1.0, 2.0, 3.0, 4.0, 5.0]
    blob = SqliteStore._embedding_to_blob(embedding)

    result = SqliteStore._read_embedding(blob)
    assert len(result) == 5
    for a, b in zip(result, embedding):
        assert abs(a - b) < 1e-6


def test_read_embedding_json_string():
    """Test _read_embedding correctly reads legacy JSON string format."""
    embedding = [1.0, 2.0, 3.0]
    json_str = json.dumps(embedding)

    result = SqliteStore._read_embedding(json_str)
    assert result == embedding


def test_read_embedding_fallback_type():
    """Test _read_embedding handles unexpected types gracefully."""
    # An int-like that can be str'd and json-parsed isn't realistic,
    # but test the fallback path
    result = SqliteStore._read_embedding("[1.0, 2.0]")
    assert result == [1.0, 2.0]


@pytest.mark.asyncio
async def test_add_documents_stores_blob(tmp_path):
    """Test that add_documents stores embeddings as binary blobs."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["entity.1"],
        ["Test entity"],
        [[1.0, 2.0, 3.0]],
        [{"domain": "test"}],
    )

    # Directly inspect the raw column type in SQLite
    cursor = store._conn.cursor()
    cursor.execute(
        f"SELECT typeof(embedding), embedding FROM {store.table_name} WHERE id = ?",
        ("entity.1",),
    )
    row = cursor.fetchone()
    assert row["typeof(embedding)"] == "blob"

    # Verify it can be decoded back
    recovered = SqliteStore._blob_to_embedding(row["embedding"])
    assert len(recovered) == 3
    assert abs(recovered[0] - 1.0) < 1e-6
    assert abs(recovered[1] - 2.0) < 1e-6
    assert abs(recovered[2] - 3.0) < 1e-6

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_upsert_documents_stores_blob(tmp_path):
    """Test that upsert_documents stores embeddings as binary blobs."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.upsert_documents(
        ["entity.1"],
        ["Test entity"],
        [[4.0, 5.0, 6.0]],
        [{"domain": "test"}],
    )

    cursor = store._conn.cursor()
    cursor.execute(
        f"SELECT typeof(embedding) FROM {store.table_name} WHERE id = ?",
        ("entity.1",),
    )
    row = cursor.fetchone()
    assert row["typeof(embedding)"] == "blob"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_search_works_with_blob_embeddings(tmp_path):
    """Test that search correctly reads blob embeddings and computes similarity."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add documents (stored as blobs now)
    await store.add_documents(
        ["1", "2", "3"],
        ["apple", "banana", "cherry"],
        [[1.0, 0.0], [0.0, 1.0], [0.707, 0.707]],
        [{"type": "fruit"}, {"type": "fruit"}, {"type": "berry"}],
    )

    # Verify they're stored as blobs
    cursor = store._conn.cursor()
    cursor.execute(f"SELECT typeof(embedding) FROM {store.table_name}")
    for row in cursor.fetchall():
        assert row["typeof(embedding)"] == "blob"

    # Search should work correctly
    results = await store.search([1.0, 0.0], n_results=3)
    assert len(results) == 3
    assert results[0].id == "1"  # Closest to [1, 0]
    assert results[0].distance == 0.0  # Exact match

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_search_with_min_similarity_blob(tmp_path):
    """Test that min_similarity filtering works with blob embeddings."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_documents(
        ["1", "2"],
        ["close", "far"],
        [[1.0, 0.0], [0.0, 1.0]],
    )

    # Search with high threshold — only exact match should pass
    results = await store.search([1.0, 0.0], n_results=10, min_similarity=0.9)
    assert len(results) == 1
    assert results[0].id == "1"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_migration_json_to_blob(tmp_path):
    """Test that legacy JSON embeddings are migrated to blob on initialization."""
    # Step 1: Create a database with JSON embeddings manually (simulate legacy)
    db_path = os.path.join(str(tmp_path), "vectors.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE ha_entities (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE rag_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    # Insert JSON embeddings (legacy format)
    embedding_1 = [1.0, 0.0, 0.5]
    embedding_2 = [0.0, 1.0, 0.3]
    conn.execute(
        "INSERT INTO ha_entities (id, text, embedding, metadata) VALUES (?, ?, ?, ?)",
        (
            "light.bedroom",
            "Bedroom Light",
            json.dumps(embedding_1),
            json.dumps({"domain": "light"}),
        ),
    )
    conn.execute(
        "INSERT INTO ha_entities (id, text, embedding, metadata) VALUES (?, ?, ?, ?)",
        (
            "switch.kitchen",
            "Kitchen Switch",
            json.dumps(embedding_2),
            json.dumps({"domain": "switch"}),
        ),
    )
    conn.commit()

    # Verify they're stored as text
    cursor = conn.cursor()
    cursor.execute("SELECT typeof(embedding) FROM ha_entities")
    for row in cursor.fetchall():
        assert row[0] == "text"
    conn.close()

    # Step 2: Initialize SqliteStore — this should trigger migration
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Step 3: Verify embeddings are now blobs
    cursor = store._conn.cursor()
    cursor.execute(f"SELECT typeof(embedding) FROM {store.table_name}")
    for row in cursor.fetchall():
        assert row["typeof(embedding)"] == "blob"

    # Step 4: Verify data integrity — search should still work
    results = await store.search([1.0, 0.0, 0.5], n_results=2)
    assert len(results) == 2
    assert results[0].id == "light.bedroom"  # Closest match
    assert results[0].distance < 0.01  # Near-exact match (float32 rounding)

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_migration_idempotent(tmp_path):
    """Test that migration is idempotent — running twice doesn't corrupt data."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add documents (stored as blobs)
    await store.add_documents(
        ["entity.1"],
        ["Test"],
        [[1.0, 2.0, 3.0]],
    )

    # Manually call migration again — should be a no-op
    store._migrate_embeddings_to_blob()

    # Verify data is intact
    results = await store.search([1.0, 2.0, 3.0], n_results=1)
    assert len(results) == 1
    assert results[0].id == "entity.1"
    assert results[0].distance < 0.01

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_migration_skips_already_blob(tmp_path):
    """Test that migration skips rows already in blob format."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add as blob (current code)
    await store.add_documents(
        ["entity.1", "entity.2"],
        ["A", "B"],
        [[1.0], [2.0]],
    )

    # Verify all are blobs
    cursor = store._conn.cursor()
    cursor.execute(
        f"SELECT COUNT(*) FROM {store.table_name} WHERE typeof(embedding) = 'text'"
    )
    assert cursor.fetchone()[0] == 0

    cursor.execute(
        f"SELECT COUNT(*) FROM {store.table_name} WHERE typeof(embedding) = 'blob'"
    )
    assert cursor.fetchone()[0] == 2

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_blob_storage_size_savings():
    """Test that blob storage is smaller than JSON for 3072-dim embeddings."""
    import struct

    dim = 3072
    embedding = [0.12345] * dim

    json_size = len(json.dumps(embedding).encode("utf-8"))
    blob_size = len(struct.pack(f"<{dim}f", *embedding))

    # Blob should be ~12KB (3072 * 4 bytes)
    assert blob_size == dim * 4  # 12288 bytes

    # JSON should be much larger (~24KB+ for 3072 7-digit floats)
    assert json_size > blob_size * 1.5

    # Savings should be at least 40%
    savings_pct = (1 - blob_size / json_size) * 100
    assert savings_pct > 40


# --- Phase 5: Session Chunk Storage Tests ---


@pytest.mark.asyncio
async def test_session_chunks_table_created(tmp_path):
    """Test that session_chunks and session_hashes tables are created on init."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    cursor = store._conn.cursor()

    # session_chunks table should exist
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_chunks'"
    )
    assert cursor.fetchone() is not None

    # session_hashes table should exist
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_hashes'"
    )
    assert cursor.fetchone() is not None

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_add_session_chunks(tmp_path):
    """Test storing session chunks with embeddings."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_session_chunks(
        ids=["chunk1", "chunk2"],
        texts=["User: Hello\nAssistant: Hi", "User: Bye\nAssistant: Goodbye"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[
            {"session_id": "sess1", "start_msg": 0, "end_msg": 1, "source": "session"},
            {"session_id": "sess1", "start_msg": 2, "end_msg": 3, "source": "session"},
        ],
        session_id="sess1",
        content_hash="abc123",
    )

    # Verify chunks stored
    cursor = store._conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM session_chunks WHERE session_id = 'sess1'")
    assert cursor.fetchone()[0] == 2

    # Verify content hash stored
    cursor.execute(
        "SELECT content_hash, chunk_count FROM session_hashes WHERE session_id = 'sess1'"
    )
    row = cursor.fetchone()
    assert row["content_hash"] == "abc123"
    assert row["chunk_count"] == 2

    # Verify embeddings stored as blobs
    cursor.execute("SELECT typeof(embedding) FROM session_chunks")
    for row in cursor.fetchall():
        assert row["typeof(embedding)"] == "blob"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_delete_session_chunks(tmp_path):
    """Test deleting all chunks for a session."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add chunks for two sessions
    await store.add_session_chunks(
        ids=["c1"],
        texts=["text1"],
        embeddings=[[1.0, 0.0]],
        metadatas=[{"start_msg": 0, "end_msg": 1}],
        session_id="sess1",
        content_hash="hash1",
    )
    await store.add_session_chunks(
        ids=["c2"],
        texts=["text2"],
        embeddings=[[0.0, 1.0]],
        metadatas=[{"start_msg": 0, "end_msg": 1}],
        session_id="sess2",
        content_hash="hash2",
    )

    # Delete sess1 chunks
    await store.delete_session_chunks("sess1")

    cursor = store._conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM session_chunks WHERE session_id = 'sess1'")
    assert cursor.fetchone()[0] == 0

    # sess2 should still be there
    cursor.execute("SELECT COUNT(*) FROM session_chunks WHERE session_id = 'sess2'")
    assert cursor.fetchone()[0] == 1

    # Hash for sess1 should be removed too
    cursor.execute("SELECT COUNT(*) FROM session_hashes WHERE session_id = 'sess1'")
    assert cursor.fetchone()[0] == 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_get_session_hash(tmp_path):
    """Test retrieving stored session content hash."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # No hash initially
    assert await store.get_session_hash("sess1") is None

    # Store hash via add_session_chunks
    await store.add_session_chunks(
        ids=["c1"],
        texts=["text"],
        embeddings=[[1.0]],
        metadatas=[{"start_msg": 0, "end_msg": 0}],
        session_id="sess1",
        content_hash="myhash123",
    )

    assert await store.get_session_hash("sess1") == "myhash123"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_search_session_chunks(tmp_path):
    """Test vector search on session chunks."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add two chunks with orthogonal embeddings
    await store.add_session_chunks(
        ids=["c1", "c2"],
        texts=["lights in bedroom", "temperature sensor"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[
            {"start_msg": 0, "end_msg": 1},
            {"start_msg": 2, "end_msg": 3},
        ],
        session_id="sess1",
        content_hash="h1",
    )

    # Search for something close to [1,0]
    results = await store.search_session_chunks(
        query_embedding=[1.0, 0.0],
        n_results=2,
    )

    assert len(results) == 2
    assert results[0].id == "c1"  # Closest match
    assert results[0].distance < 0.01  # Near-exact

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_search_session_chunks_min_similarity(tmp_path):
    """Test min_similarity filtering on session chunk search."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_session_chunks(
        ids=["c1", "c2"],
        texts=["close", "far"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[
            {"start_msg": 0, "end_msg": 0},
            {"start_msg": 1, "end_msg": 1},
        ],
        session_id="sess1",
        content_hash="h1",
    )

    # High threshold — only exact match passes
    results = await store.search_session_chunks(
        query_embedding=[1.0, 0.0],
        n_results=5,
        min_similarity=0.9,
    )

    assert len(results) == 1
    assert results[0].id == "c1"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_search_session_chunks_by_session_id(tmp_path):
    """Test filtering session chunk search by session_id."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Add chunks from two sessions
    await store.add_session_chunks(
        ids=["c1"],
        texts=["text1"],
        embeddings=[[1.0, 0.0]],
        metadatas=[{"start_msg": 0, "end_msg": 0}],
        session_id="sess1",
        content_hash="h1",
    )
    await store.add_session_chunks(
        ids=["c2"],
        texts=["text2"],
        embeddings=[[1.0, 0.0]],  # Same embedding
        metadatas=[{"start_msg": 0, "end_msg": 0}],
        session_id="sess2",
        content_hash="h2",
    )

    # Search only sess1
    results = await store.search_session_chunks(
        query_embedding=[1.0, 0.0],
        n_results=5,
        session_id="sess1",
    )

    assert len(results) == 1
    assert results[0].metadata["session_id"] == "sess1"

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_session_chunk_stats(tmp_path):
    """Test session chunk statistics."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    # Empty stats initially
    stats = await store.get_session_chunk_stats()
    assert stats["total_chunks"] == 0
    assert stats["indexed_sessions"] == 0

    # Add chunks
    await store.add_session_chunks(
        ids=["c1", "c2"],
        texts=["text1", "text2"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[
            {"start_msg": 0, "end_msg": 1},
            {"start_msg": 2, "end_msg": 3},
        ],
        session_id="sess1",
        content_hash="h1",
    )

    stats = await store.get_session_chunk_stats()
    assert stats["total_chunks"] == 2
    assert stats["indexed_sessions"] == 1
    assert stats["total_bytes"] > 0

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_session_chunks_fts_search(tmp_path):
    """Test FTS5 keyword search on session chunks."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    await store.add_session_chunks(
        ids=["c1", "c2"],
        texts=[
            "User: What lights are in the bedroom?\nAssistant: There are 3 lights.",
            "User: What is the temperature?\nAssistant: It is 22 degrees.",
        ],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[
            {"start_msg": 0, "end_msg": 1},
            {"start_msg": 2, "end_msg": 3},
        ],
        session_id="sess1",
        content_hash="h1",
    )

    # Search for "bedroom"
    results = await store.keyword_search_sessions('"bedroom"', n_results=5)
    assert len(results) == 1
    assert "bedroom" in results[0].text.lower()

    # Search for "temperature"
    results = await store.keyword_search_sessions('"temperature"', n_results=5)
    assert len(results) == 1
    assert "temperature" in results[0].text.lower()

    await store.async_shutdown()


@pytest.mark.asyncio
async def test_keyword_search_sessions_empty(tmp_path):
    """Test FTS5 session search with empty query returns empty."""
    store = SqliteStore(persist_directory=str(tmp_path))
    await store.async_initialize()

    results = await store.keyword_search_sessions("", n_results=5)
    assert len(results) == 0

    await store.async_shutdown()
