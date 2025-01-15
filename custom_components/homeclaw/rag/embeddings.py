"""Embedding providers for RAG system.

This module provides embedding generation using available AI providers.
Supports Gemini OAuth (preferred), OpenAI, and Gemini API key as fallbacks.

Includes SHA-256 content-addressable caching and batch embedding with retry.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from .sqlite_store import SqliteStore

_LOGGER = logging.getLogger(__name__)

# Retry configuration for embedding API calls
EMBEDDING_RETRY_MAX_ATTEMPTS = 3
EMBEDDING_RETRY_BASE_DELAY = 0.5  # seconds
EMBEDDING_RETRY_MAX_DELAY = 8.0  # seconds

# Batch configuration for Gemini (which doesn't support native batch)
GEMINI_BATCH_DELAY = 0.05  # 50ms between individual Gemini calls to avoid rate limits

# Embedding dimensions for different providers
EMBEDDING_DIMENSIONS = {
    "gemini": 3072,  # gemini-embedding-001
    "openai": 1536,  # text-embedding-3-small
}


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


@dataclass
class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If embedding generation fails.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of the embeddings."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the embedding provider."""


@dataclass
class GeminiOAuthEmbeddings(EmbeddingProvider):
    """Gemini embeddings using existing OAuth token from Gemini CLI.

    Uses the same OAuth authentication as the main GeminiOAuthClient.
    """

    hass: HomeAssistant
    config_entry: ConfigEntry
    model: str = "gemini-embedding-001"
    _session: aiohttp.ClientSession | None = field(default=None, repr=False)

    ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    )

    @property
    def dimension(self) -> int:
        return 3072

    @property
    def provider_name(self) -> str:
        return "gemini_oauth"

    async def _get_valid_token(self) -> str:
        """Get a valid OAuth access token, refreshing if necessary."""
        import time
        from ..gemini_oauth import refresh_token

        # OAuth tokens are stored in the nested "gemini_oauth" dict
        oauth_data = dict(self.config_entry.data.get("gemini_oauth", {}))

        # Check if token is expired or about to expire (within 5 minutes)
        expires_at = oauth_data.get("expires_at", 0)
        if time.time() >= expires_at - 300:
            _LOGGER.debug("Gemini OAuth token expired or expiring, refreshing...")
            refresh = oauth_data.get("refresh_token")
            if not refresh:
                raise EmbeddingError("No refresh token available for Gemini OAuth")

            async with aiohttp.ClientSession() as session:
                new_tokens = await refresh_token(session, refresh)

            # Update oauth_data and persist to config entry
            oauth_data.update(new_tokens)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, "gemini_oauth": oauth_data},
            )
            return new_tokens["access_token"]

        return oauth_data["access_token"]

    async def get_embeddings(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Generate embeddings using Gemini OAuth.

        Sends requests sequentially (Gemini doesn't support batch embedding).
        Rate limiting and retry are handled by the CachedEmbeddingProvider wrapper.

        Args:
            texts: List of texts to embed.
            task_type: Embedding task type - "RETRIEVAL_DOCUMENT" for entities,
                      "RETRIEVAL_QUERY" for search queries.
        """
        if not texts:
            return []

        try:
            token = await self._get_valid_token()
            embeddings = []

            async with aiohttp.ClientSession() as session:
                for i, text in enumerate(texts):
                    url = self.ENDPOINT.format(model=self.model)
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "content": {"parts": [{"text": text}]},
                        "taskType": task_type,
                    }

                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            _LOGGER.error(
                                "Gemini embedding failed: %s - %s",
                                resp.status,
                                error_text,
                            )
                            raise EmbeddingError(
                                f"Gemini embedding failed: {resp.status} - {error_text[:200]}"
                            )

                        data = await resp.json()
                        embedding = data.get("embedding", {}).get("values", [])
                        if not embedding:
                            raise EmbeddingError("No embedding in Gemini response")
                        embeddings.append(embedding)

                    # Small delay between requests to avoid rate limits
                    if i < len(texts) - 1:
                        await asyncio.sleep(GEMINI_BATCH_DELAY)

            _LOGGER.debug("Generated %d embeddings with Gemini OAuth", len(embeddings))
            return embeddings

        except EmbeddingError:
            raise
        except Exception as e:
            _LOGGER.error("Gemini OAuth embedding error: %s", e)
            raise EmbeddingError(f"Gemini OAuth embedding failed: {e}") from e


@dataclass
class GeminiApiKeyEmbeddings(EmbeddingProvider):
    """Gemini embeddings using API key."""

    api_key: str
    model: str = "gemini-embedding-001"

    ENDPOINT = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    )

    @property
    def dimension(self) -> int:
        return 3072

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def get_embeddings(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Generate embeddings using Gemini API key.

        Sends requests sequentially (Gemini doesn't support batch embedding).
        Rate limiting and retry are handled by the CachedEmbeddingProvider wrapper.

        Args:
            texts: List of texts to embed.
            task_type: Embedding task type - "RETRIEVAL_DOCUMENT" for entities,
                      "RETRIEVAL_QUERY" for search queries.
        """
        if not texts:
            return []

        try:
            embeddings = []

            async with aiohttp.ClientSession() as session:
                for i, text in enumerate(texts):
                    url = f"{self.ENDPOINT.format(model=self.model)}?key={self.api_key}"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "content": {"parts": [{"text": text}]},
                        "taskType": task_type,
                    }

                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            _LOGGER.error(
                                "Gemini API embedding failed: %s - %s",
                                resp.status,
                                error_text,
                            )
                            raise EmbeddingError(
                                f"Gemini API embedding failed: {resp.status} - {error_text[:200]}"
                            )

                        data = await resp.json()
                        embedding = data.get("embedding", {}).get("values", [])
                        if not embedding:
                            raise EmbeddingError("No embedding in Gemini response")
                        embeddings.append(embedding)

                    # Small delay between requests to avoid rate limits
                    if i < len(texts) - 1:
                        await asyncio.sleep(GEMINI_BATCH_DELAY)

            _LOGGER.debug(
                "Generated %d embeddings with Gemini API key", len(embeddings)
            )
            return embeddings

        except EmbeddingError:
            raise
        except Exception as e:
            _LOGGER.error("Gemini API embedding error: %s", e)
            raise EmbeddingError(f"Gemini API embedding failed: {e}") from e


@dataclass
class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embeddings using text-embedding-3-small."""

    api_key: str
    model: str = "text-embedding-3-small"

    ENDPOINT = "https://api.openai.com/v1/embeddings"

    @property
    def dimension(self) -> int:
        return 1536

    @property
    def provider_name(self) -> str:
        return "openai"

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API."""
        if not texts:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self.model,
                    "input": texts,
                }

                async with session.post(
                    self.ENDPOINT, headers=headers, json=payload
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.error(
                            "OpenAI embedding failed: %s - %s",
                            resp.status,
                            error_text,
                        )
                        raise EmbeddingError(f"OpenAI embedding failed: {resp.status}")

                    data = await resp.json()
                    embeddings_data = data.get("data", [])
                    if not embeddings_data:
                        raise EmbeddingError("No embeddings in OpenAI response")

                    # Sort by index and extract embeddings
                    embeddings_data.sort(key=lambda x: x.get("index", 0))
                    embeddings = [e["embedding"] for e in embeddings_data]

            _LOGGER.debug("Generated %d embeddings with OpenAI", len(embeddings))
            return embeddings

        except EmbeddingError:
            raise
        except Exception as e:
            _LOGGER.error("OpenAI embedding error: %s", e)
            raise EmbeddingError(f"OpenAI embedding failed: {e}") from e


def create_embedding_provider(
    hass: HomeAssistant,
    config: dict[str, Any],
    config_entry: ConfigEntry | None = None,
) -> EmbeddingProvider:
    """Create an embedding provider based on available configuration.

    Fallback chain:
    1. OpenAI (if configured) - text-embedding-3-small (most reliable)
    2. Gemini API key (if configured) - gemini-embedding-001

    Note: Gemini OAuth tokens from Code Assist do NOT have scopes for
    the embeddings API (generativelanguage.googleapis.com), so we skip it.

    Args:
        hass: Home Assistant instance.
        config: Configuration dictionary with API keys.
        config_entry: Optional config entry for OAuth providers.

    Returns:
        Configured EmbeddingProvider instance.

    Raises:
        EmbeddingError: If no embedding provider could be configured.
    """
    # 1. Try OpenAI API key (most reliable for embeddings)
    openai_token = config.get("openai_token")
    if openai_token and openai_token.startswith("sk-"):
        _LOGGER.info("Using OpenAI for embeddings")
        return OpenAIEmbeddings(api_key=openai_token)

    # 2. Try Gemini API key
    gemini_token = config.get("gemini_token")
    if gemini_token:
        _LOGGER.info("Using Gemini API key for embeddings")
        return GeminiApiKeyEmbeddings(api_key=gemini_token)

    raise EmbeddingError(
        "No embedding provider available. Configure OpenAI API key or Gemini API key. "
        "Note: Gemini OAuth (Code Assist) tokens don't support embeddings API."
    )


async def get_embedding_for_query(
    provider: EmbeddingProvider,
    query: str,
) -> list[float]:
    """Get embedding for a single query text.

    Uses RETRIEVAL_QUERY task type for Gemini embeddings to improve
    search accuracy.

    Args:
        provider: The embedding provider to use.
        query: The query text to embed.

    Returns:
        The embedding vector for the query.
    """
    # Use RETRIEVAL_QUERY task type if provider supports it (Gemini)
    kwargs: dict[str, Any] = {}
    if isinstance(provider, CachedEmbeddingProvider):
        # Unwrap to check the underlying provider
        inner = provider.inner
        if isinstance(inner, (GeminiOAuthEmbeddings, GeminiApiKeyEmbeddings)):
            kwargs["task_type"] = "RETRIEVAL_QUERY"
    elif isinstance(provider, (GeminiOAuthEmbeddings, GeminiApiKeyEmbeddings)):
        kwargs["task_type"] = "RETRIEVAL_QUERY"

    embeddings = await provider.get_embeddings([query], **kwargs)
    if not embeddings:
        raise EmbeddingError("Failed to generate query embedding")
    return embeddings[0]


def _hash_text(text: str) -> str:
    """Compute SHA-256 hash of text for cache key.

    Args:
        text: Text to hash.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_retryable_error(message: str) -> bool:
    """Check if an error message indicates a retryable failure.

    Args:
        message: Error message string.

    Returns:
        True if the error is retryable (rate limit, server error, etc.).
    """
    import re

    return bool(
        re.search(
            r"(rate[_ ]?limit|too many requests|429|resource.+exhausted|5\d\d|cloudflare|timeout)",
            message,
            re.IGNORECASE,
        )
    )


async def _retry_with_backoff(
    func,
    max_attempts: int = EMBEDDING_RETRY_MAX_ATTEMPTS,
    base_delay: float = EMBEDDING_RETRY_BASE_DELAY,
    max_delay: float = EMBEDDING_RETRY_MAX_DELAY,
):
    """Retry an async function with exponential backoff on retryable errors.

    Args:
        func: Async callable to retry.
        max_attempts: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.

    Returns:
        Result of the successful call.

    Raises:
        Last exception if all retries fail.
    """
    delay = base_delay
    last_error: Exception | None = None

    for attempt in range(max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_error = e
            error_msg = str(e)

            if attempt >= max_attempts or not _is_retryable_error(error_msg):
                raise

            # Jittered exponential backoff
            jitter = delay * 0.3 * (random.random() * 2 - 1)
            wait = min(max_delay, max(0, delay + jitter))

            _LOGGER.warning(
                "Embedding API call failed, retrying in %.1fs (attempt %d/%d): %s",
                wait,
                attempt + 1,
                max_attempts,
                error_msg[:200],
            )
            await asyncio.sleep(wait)
            delay *= 2

    if last_error:
        raise last_error
    raise EmbeddingError("Retry exhausted without result")


@dataclass
class CachedEmbeddingProvider(EmbeddingProvider):
    """Wrapper that adds SHA-256 content-addressable caching and retry to any provider.

    Cache flow (inspired by OpenClaw):
    1. Hash each text with SHA-256
    2. Bulk lookup existing embeddings in SQLite cache
    3. Only compute embeddings for cache misses
    4. Store new embeddings back to cache
    5. Return all embeddings in original order

    Also adds:
    - Retry with exponential backoff on retryable errors (429, 5xx)
    - Batch support for Gemini (sends texts sequentially with small delay)
    - LRU cache pruning to prevent unbounded growth
    """

    inner: EmbeddingProvider
    store: SqliteStore
    _cache_hits: int = field(default=0, repr=False)
    _cache_misses: int = field(default=0, repr=False)

    @property
    def dimension(self) -> int:
        return self.inner.dimension

    @property
    def provider_name(self) -> str:
        return self.inner.provider_name

    async def get_embeddings(self, texts: list[str], **kwargs) -> list[list[float]]:
        """Generate embeddings with caching and retry.

        Args:
            texts: List of text strings to embed.
            **kwargs: Additional arguments (e.g., task_type for Gemini).

        Returns:
            List of embedding vectors (one per text, in order).
        """
        if not texts:
            return []

        provider = self.inner.provider_name
        model = self._get_model_name()

        # 1. Hash all texts
        hashes = [_hash_text(t) for t in texts]

        # 2. Bulk cache lookup
        cached = self.store.cache_lookup(provider, model, hashes)

        # 3. Separate hits from misses
        embeddings: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []  # (index, text, hash)

        for i, (text, content_hash) in enumerate(zip(texts, hashes)):
            hit = cached.get(content_hash)
            if hit and len(hit) > 0:
                embeddings[i] = hit
                self._cache_hits += 1
            else:
                missing.append((i, text, content_hash))
                self._cache_misses += 1

        if not missing:
            _LOGGER.debug(
                "Embedding cache: %d/%d hits (100%%), 0 API calls needed",
                len(texts),
                len(texts),
            )
            return [e for e in embeddings if e is not None]  # All hits

        _LOGGER.debug(
            "Embedding cache: %d hits, %d misses out of %d texts",
            len(texts) - len(missing),
            len(missing),
            len(texts),
        )

        # 4. Compute embeddings for misses with retry
        missing_texts = [m[1] for m in missing]

        async def _do_embed():
            return await self.inner.get_embeddings(missing_texts, **kwargs)

        try:
            new_embeddings = await _retry_with_backoff(_do_embed)
        except Exception as e:
            _LOGGER.error(
                "Failed to generate %d embeddings after retries: %s",
                len(missing_texts),
                e,
            )
            raise

        # 5. Merge results and prepare cache entries
        to_cache: list[tuple[str, list[float]]] = []

        for j, (idx, _text, content_hash) in enumerate(missing):
            if j < len(new_embeddings) and new_embeddings[j]:
                embeddings[idx] = new_embeddings[j]
                to_cache.append((content_hash, new_embeddings[j]))

        # 6. Store new embeddings in cache (fire-and-forget, non-blocking)
        if to_cache:
            try:
                self.store.cache_upsert(provider, model, to_cache)
            except Exception as e:
                _LOGGER.warning("Failed to update embedding cache: %s", e)

        # 7. Periodic cache pruning (every ~100 upserts)
        total_ops = self._cache_hits + self._cache_misses
        if total_ops > 0 and total_ops % 500 == 0:
            try:
                self.store.cache_prune(max_entries=10000)
            except Exception as e:
                _LOGGER.warning("Cache prune failed: %s", e)

        # Filter out any None entries (shouldn't happen but safety)
        return [e for e in embeddings if e is not None]

    def _get_model_name(self) -> str:
        """Get the model name from the inner provider."""
        model = getattr(self.inner, "model", None)
        return model if isinstance(model, str) else "unknown"

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache hit/miss statistics.

        Returns:
            Dict with hits, misses, and hit rate.
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_pct": round(hit_rate, 1),
        }
