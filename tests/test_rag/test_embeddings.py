"""Tests for embedding providers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Note: homeassistant mocks are set up in conftest.py

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.homeclaw.rag.embeddings import (
    CachedEmbeddingProvider,
    EmbeddingError,
    EmbeddingProvider,
    GeminiApiKeyEmbeddings,
    GeminiOAuthEmbeddings,
    OpenAIEmbeddings,
    _hash_text,
    _is_retryable_error,
    create_embedding_provider,
    get_embedding_for_query,
)


class TestOpenAIEmbeddings:
    """Tests for OpenAI embedding provider."""

    @pytest.fixture
    def provider(self):
        """Return an OpenAI embeddings provider."""
        return OpenAIEmbeddings(api_key="sk-test-key")

    def test_properties(self, provider):
        """Test provider properties."""
        assert provider.dimension == 1536
        assert provider.provider_name == "openai"

    @pytest.mark.asyncio
    async def test_get_embeddings_success(self, provider):
        """Test successful embedding generation."""
        mock_response = {
            "data": [
                {"index": 0, "embedding": [0.1] * 1536},
                {"index": 1, "embedding": [0.2] * 1536},
            ]
        }

        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response_obj),
                __aexit__=AsyncMock(),
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()
            )

            embeddings = await provider.get_embeddings(["text1", "text2"])

            assert len(embeddings) == 2
            assert len(embeddings[0]) == 1536
            assert embeddings[0][0] == 0.1
            assert embeddings[1][0] == 0.2

    @pytest.mark.asyncio
    async def test_get_embeddings_empty_list(self, provider):
        """Test with empty input list."""
        embeddings = await provider.get_embeddings([])
        assert embeddings == []

    @pytest.mark.asyncio
    async def test_get_embeddings_api_error(self, provider):
        """Test API error handling."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            mock_response_obj = AsyncMock()
            mock_response_obj.status = 401
            mock_response_obj.text = AsyncMock(return_value="Unauthorized")
            mock_session.post.return_value.__aenter__.return_value = mock_response_obj

            with pytest.raises(EmbeddingError, match="OpenAI embedding failed"):
                await provider.get_embeddings(["text"])


class TestGeminiApiKeyEmbeddings:
    """Tests for Gemini API key embedding provider."""

    @pytest.fixture
    def provider(self):
        """Return a Gemini API key embeddings provider."""
        return GeminiApiKeyEmbeddings(api_key="test-gemini-key")

    def test_properties(self, provider):
        """Test provider properties."""
        assert provider.dimension == 3072
        assert provider.provider_name == "gemini"

    @pytest.mark.asyncio
    async def test_get_embeddings_success(self, provider):
        """Test successful embedding generation."""
        mock_response = {"embedding": {"values": [0.1] * 768}}

        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response_obj),
                __aexit__=AsyncMock(),
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()
            )

            embeddings = await provider.get_embeddings(["text1"])

            assert len(embeddings) == 1
            assert len(embeddings[0]) == 768

    @pytest.mark.asyncio
    async def test_get_embeddings_api_error(self, provider):
        """Test API error handling."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            mock_response_obj = AsyncMock()
            mock_response_obj.status = 400
            mock_response_obj.text = AsyncMock(return_value="Bad Request")
            mock_session.post.return_value.__aenter__.return_value = mock_response_obj

            with pytest.raises(EmbeddingError, match="Gemini API embedding failed"):
                await provider.get_embeddings(["text"])


class TestGeminiOAuthEmbeddings:
    """Tests for Gemini OAuth embedding provider."""

    @pytest.fixture
    def provider(self, hass, config_entry):
        """Return a Gemini OAuth embeddings provider."""
        return GeminiOAuthEmbeddings(hass=hass, config_entry=config_entry)

    def test_properties(self, provider):
        """Test provider properties."""
        assert provider.dimension == 3072
        assert provider.provider_name == "gemini_oauth"

    @pytest.mark.asyncio
    async def test_get_embeddings_success(self, provider):
        """Test successful embedding generation with OAuth."""
        mock_response = {"embedding": {"values": [0.1] * 768}}

        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response_obj),
                __aexit__=AsyncMock(),
            )
        )

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.return_value = AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()
            )

            embeddings = await provider.get_embeddings(["text1"])

            assert len(embeddings) == 1
            assert len(embeddings[0]) == 768

    @pytest.mark.asyncio
    async def test_get_embeddings_token_refresh(self, hass):
        """Test token refresh when expired."""
        from custom_components.homeclaw.rag import embeddings as embeddings_module
        from custom_components.homeclaw import gemini_oauth

        # Create a real MockConfigEntry instead of using the MagicMock fixture
        config_entry = MockConfigEntry(
            domain="homeclaw",
            data={
                "ai_provider": "gemini_oauth",
                "gemini_oauth": {
                    "access_token": "test_access_token",
                    "refresh_token": "test_refresh_token",
                    "expires_at": 0,  # Expired
                },
            },
        )
        config_entry.add_to_hass(hass)

        provider = GeminiOAuthEmbeddings(hass=hass, config_entry=config_entry)

        mock_response = {"embedding": {"values": [0.1] * 768}}

        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response_obj),
                __aexit__=AsyncMock(),
            )
        )

        mock_refresh = AsyncMock(
            return_value={
                "access_token": "new_token",
                "refresh_token": "new_refresh",
                "expires_at": 9999999999,
            }
        )

        with (
            patch("aiohttp.ClientSession") as mock_session_class,
            patch.object(gemini_oauth, "refresh_token", mock_refresh),
        ):
            mock_session_class.return_value = AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()
            )

            embeddings = await provider.get_embeddings(["text"])

            # Verify refresh was called
            mock_refresh.assert_called_once()
            assert len(embeddings) == 1


class TestCreateEmbeddingProvider:
    """Tests for the embedding provider factory function."""

    def test_create_with_openai(self, hass):
        """Test creating OpenAI provider."""
        config = {"openai_token": "sk-test-key"}

        provider = create_embedding_provider(hass, config)

        assert isinstance(provider, OpenAIEmbeddings)
        assert provider.provider_name == "openai"

    def test_create_with_gemini_api_key(self, hass):
        """Test creating Gemini API key provider."""
        config = {"gemini_token": "test-gemini-key"}

        provider = create_embedding_provider(hass, config)

        assert isinstance(provider, GeminiApiKeyEmbeddings)
        assert provider.provider_name == "gemini"

    def test_gemini_oauth_without_fallback_raises(self, hass, config_entry):
        """Test that Gemini OAuth alone raises error (no embedding scopes)."""
        config = {"ai_provider": "gemini_oauth"}

        # Gemini OAuth tokens don't have scopes for embeddings API
        with pytest.raises(EmbeddingError):
            create_embedding_provider(hass, config, config_entry)

    def test_gemini_oauth_with_openai_fallback(self, hass, config_entry):
        """Test that OpenAI is used as fallback when Gemini OAuth configured."""
        config = {
            "ai_provider": "gemini_oauth",
            "openai_token": "sk-test-key",
            "gemini_token": "test-gemini-key",
        }

        provider = create_embedding_provider(hass, config, config_entry)

        # OpenAI is preferred for embeddings (Gemini OAuth lacks scopes)
        assert provider.provider_name == "openai"

    def test_fallback_to_openai(self, hass):
        """Test fallback to OpenAI when Gemini OAuth not available."""
        config = {
            "ai_provider": "anthropic",
            "openai_token": "sk-test-key",
            "gemini_token": "test-gemini-key",
        }

        provider = create_embedding_provider(hass, config)

        # OpenAI is preferred over Gemini API key
        assert provider.provider_name == "openai"

    def test_no_provider_available_raises(self, hass):
        """Test that missing providers raises error."""
        config = {"ai_provider": "anthropic"}

        with pytest.raises(EmbeddingError, match="No embedding provider available"):
            create_embedding_provider(hass, config)


class TestGetEmbeddingForQuery:
    """Tests for the query embedding helper."""

    @pytest.mark.asyncio
    async def test_get_embedding_for_query(self):
        """Test getting a single embedding for a query."""
        mock_provider = MagicMock()
        mock_provider.get_embeddings = AsyncMock(return_value=[[0.1] * 768])

        embedding = await get_embedding_for_query(mock_provider, "test query")

        assert len(embedding) == 768
        mock_provider.get_embeddings.assert_called_once_with(["test query"])

    @pytest.mark.asyncio
    async def test_get_embedding_for_query_empty_result(self):
        """Test handling of empty embedding result."""
        mock_provider = MagicMock()
        mock_provider.get_embeddings = AsyncMock(return_value=[])

        with pytest.raises(EmbeddingError, match="Failed to generate query embedding"):
            await get_embedding_for_query(mock_provider, "test query")


class TestHashText:
    """Tests for SHA-256 text hashing."""

    def test_hash_text_consistent(self):
        """Test that same text always produces same hash."""
        hash1 = _hash_text("hello world")
        hash2 = _hash_text("hello world")
        assert hash1 == hash2

    def test_hash_text_different(self):
        """Test that different texts produce different hashes."""
        hash1 = _hash_text("hello")
        hash2 = _hash_text("world")
        assert hash1 != hash2

    def test_hash_text_is_sha256(self):
        """Test that hash is a valid SHA-256 hex string."""
        result = _hash_text("test")
        assert len(result) == 64  # SHA-256 hex is 64 characters
        assert all(c in "0123456789abcdef" for c in result)


class TestIsRetryableError:
    """Tests for retryable error detection."""

    def test_rate_limit(self):
        assert _is_retryable_error("rate limit exceeded")
        assert _is_retryable_error("Rate_Limit hit")

    def test_429(self):
        assert _is_retryable_error("HTTP 429 Too Many Requests")

    def test_500(self):
        assert _is_retryable_error("Internal Server Error 500")

    def test_cloudflare(self):
        assert _is_retryable_error("Cloudflare error")

    def test_timeout(self):
        assert _is_retryable_error("Connection timeout")

    def test_non_retryable(self):
        assert not _is_retryable_error("Invalid API key")
        assert not _is_retryable_error("Not found")


class TestCachedEmbeddingProvider:
    """Tests for the caching embedding provider wrapper."""

    @pytest.fixture
    def mock_inner(self):
        """Create a mock inner provider."""
        inner = MagicMock()
        inner.provider_name = "test"
        inner.dimension = 768
        inner.model = "test-model"
        inner.get_embeddings = AsyncMock(return_value=[[0.1] * 768])
        return inner

    @pytest.fixture
    def mock_store(self):
        """Create a mock SQLite store for cache operations."""
        store = MagicMock()
        store.cache_lookup = MagicMock(return_value={})  # No cache hits by default
        store.cache_upsert = MagicMock()
        store.cache_prune = MagicMock()
        return store

    def test_properties(self, mock_inner, mock_store):
        """Test provider properties delegate to inner."""
        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)
        assert cached.provider_name == "test"
        assert cached.dimension == 768

    @pytest.mark.asyncio
    async def test_cache_miss_calls_provider(self, mock_inner, mock_store):
        """Test that cache miss calls the inner provider."""
        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)

        result = await cached.get_embeddings(["hello"])

        assert len(result) == 1
        mock_inner.get_embeddings.assert_called_once_with(["hello"])
        # Should have stored the result in cache
        mock_store.cache_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_provider(self, mock_inner, mock_store):
        """Test that cache hit skips the API call."""
        text_hash = _hash_text("hello")
        mock_store.cache_lookup.return_value = {text_hash: [0.5] * 768}

        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)
        result = await cached.get_embeddings(["hello"])

        assert len(result) == 1
        # Inner provider should NOT be called (cache hit)
        mock_inner.get_embeddings.assert_not_called()
        # No new entries to cache
        mock_store.cache_upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_cache_hit(self, mock_inner, mock_store):
        """Test mixed cache hits and misses."""
        hash_a = _hash_text("cached text")
        mock_store.cache_lookup.return_value = {hash_a: [0.1] * 768}

        mock_inner.get_embeddings = AsyncMock(return_value=[[0.2] * 768])

        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)
        result = await cached.get_embeddings(["cached text", "new text"])

        assert len(result) == 2
        # Only "new text" should be sent to provider
        mock_inner.get_embeddings.assert_called_once_with(["new text"])

    @pytest.mark.asyncio
    async def test_empty_texts(self, mock_inner, mock_store):
        """Test empty text list returns empty."""
        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)
        result = await cached.get_embeddings([])
        assert result == []
        mock_inner.get_embeddings.assert_not_called()

    def test_get_cache_stats(self, mock_inner, mock_store):
        """Test cache statistics."""
        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)
        cached._cache_hits = 80
        cached._cache_misses = 20

        stats = cached.get_cache_stats()
        assert stats["hits"] == 80
        assert stats["misses"] == 20
        assert stats["total"] == 100
        assert stats["hit_rate_pct"] == 80.0

    @pytest.mark.asyncio
    async def test_kwargs_passed_to_inner(self, mock_inner, mock_store):
        """Test that kwargs like task_type are passed to inner provider."""
        cached = CachedEmbeddingProvider(inner=mock_inner, store=mock_store)
        await cached.get_embeddings(["text"], task_type="RETRIEVAL_QUERY")

        mock_inner.get_embeddings.assert_called_once_with(
            ["text"], task_type="RETRIEVAL_QUERY"
        )
