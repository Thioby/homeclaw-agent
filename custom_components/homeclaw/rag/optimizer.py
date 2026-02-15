"""RAG Optimizer — condenses session chunks and memories using an AI provider.

When the RAG database grows too large (many session chunks, redundant memories),
this module uses a selected AI provider to:
1. Merge and summarize session chunks per session (fewer, denser chunks).
2. Deduplicate and condense memories (merge similar entries).

The optimizer is invoked on-demand from the frontend RAG viewer panel.
Progress is streamed back via WebSocket events.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

_LOGGER = logging.getLogger(__name__)

# --- Constants ---

# Sessions with fewer chunks than this are skipped (already compact)
MIN_CHUNKS_TO_OPTIMIZE = 3

# Maximum number of chunks to send per AI call (context window safety)
MAX_CHUNKS_PER_BATCH = 20

# Target: reduce chunk count to roughly this ratio of the original
TARGET_COMPRESSION_RATIO = 0.4  # 40% of original count

# Maximum characters of chunk text per AI call
MAX_TEXT_PER_BATCH = 12_000

# System prompt for session chunk condensation
SESSION_CONDENSE_PROMPT = """You are a precise information condenser for a Home Assistant AI assistant's memory system.

Your task: Take multiple conversation chunks from the same session and produce a CONDENSED set of summary chunks.

CRITICAL RULE — LANGUAGE PRESERVATION:
You MUST write the output in the SAME LANGUAGE as the input text. If the conversation is in Polish, output in Polish. If in English, output in English. If mixed, preserve each part's language. NEVER translate or switch languages.

Rules:
1. Preserve ALL actionable information: entity names, entity IDs, user preferences, decisions, commands given, and outcomes.
2. Preserve the chronological flow — summaries should reflect the order of events.
3. Remove redundancy: greetings, repetitive confirmations, filler language.
4. Keep technical details (entity_id formats like "light.living_room", automation names, service calls).
5. Each summary chunk should be 200-400 characters — dense but readable.
6. Output ONLY the condensed chunks, one per line, separated by "---" on its own line.
7. Do NOT add commentary, headers, or explanations outside the chunks.
8. Do NOT translate — keep the original language of the input.
9. CRITICAL: Remove ALL ephemeral entity state data — sensor readings (temperatures, humidity, power, lux), on/off status reports, and current values. Entity states change constantly; storing old values creates misleading context. Keep entity names and relationships but strip their state values.

If the input is already concise, return it with minimal changes."""

# System prompt for memory condensation
MEMORY_CONDENSE_PROMPT = """You are a precise information condenser for a Home Assistant AI assistant's long-term memory system.

Your task: Take a list of memories that may contain duplicates or overlapping information, and produce a CONDENSED list.

CRITICAL RULE — LANGUAGE PRESERVATION:
You MUST write the output in the SAME LANGUAGE as the input text. If memories are in Polish, output in Polish. If in English, output in English. NEVER translate or switch languages.

Rules:
1. Merge memories that describe the same fact, preference, or decision into a single entry.
2. Keep the most specific and recent version when merging.
3. Preserve ALL distinct facts — do not lose unique information.
4. Each condensed memory should be a single clear statement in the ORIGINAL language.
5. Preserve category labels (fact, preference, decision, entity) — output format: [category] memory text
6. Output ONLY the condensed memories, one per line.
7. Do NOT add commentary, headers, or explanations.
8. Do NOT translate — keep the original language of the input.

Example input:
[preference] User prefers warm white lights in the bedroom
[preference] User likes warm lighting in the bedroom at night
[fact] User's name is Adam

Example output:
[preference] User prefers warm white lights in the bedroom, especially at night
[fact] User's name is Adam"""


# Type alias for progress callback
ProgressCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


@dataclass
class OptimizationResult:
    """Result of a RAG optimization run."""

    sessions_processed: int = 0
    chunks_before: int = 0
    chunks_after: int = 0
    memories_before: int = 0
    memories_after: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for WebSocket response."""
        return {
            "sessions_processed": self.sessions_processed,
            "chunks_before": self.chunks_before,
            "chunks_after": self.chunks_after,
            "chunks_saved": self.chunks_before - self.chunks_after,
            "memories_before": self.memories_before,
            "memories_after": self.memories_after,
            "memories_saved": self.memories_before - self.memories_after,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 1),
        }


@dataclass
class AnalysisResult:
    """Result of RAG size analysis (pre-optimization)."""

    total_session_chunks: int = 0
    total_sessions: int = 0
    optimizable_sessions: int = 0
    estimated_chunks_after: int = 0
    total_memories: int = 0
    estimated_memories_after: int = 0
    total_size_mb: float = 0.0
    session_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for WebSocket response."""
        return {
            "total_session_chunks": self.total_session_chunks,
            "total_sessions": self.total_sessions,
            "optimizable_sessions": self.optimizable_sessions,
            "estimated_chunks_after": self.estimated_chunks_after,
            "potential_chunk_savings": self.total_session_chunks
            - self.estimated_chunks_after,
            "total_memories": self.total_memories,
            "estimated_memories_after": self.estimated_memories_after,
            "potential_memory_savings": self.total_memories
            - self.estimated_memories_after,
            "total_size_mb": self.total_size_mb,
            "session_details": self.session_details[:20],  # Top 20 largest sessions
        }


@dataclass
class RAGOptimizer:
    """Optimizes the RAG database by condensing session chunks and memories.

    Uses an AI provider to intelligently merge and summarize content while
    preserving actionable information.

    Args:
        store: The SqliteStore instance from the RAG system.
        embedding_provider: The CachedEmbeddingProvider for re-embedding condensed text.
        memory_manager: Optional MemoryManager for memory optimization.
    """

    store: Any  # SqliteStore
    embedding_provider: Any  # CachedEmbeddingProvider
    memory_manager: Any | None = None  # MemoryManager

    async def analyze(self, user_id: str | None = None) -> AnalysisResult:
        """Analyze current RAG size and estimate optimization potential.

        Args:
            user_id: User ID for memory analysis (memories are per-user).

        Returns:
            AnalysisResult with current stats and optimization estimates.
        """
        result = AnalysisResult()

        try:
            # Get session chunk stats
            chunk_stats = await self.store.get_session_chunk_stats()
            result.total_session_chunks = chunk_stats.get("total_chunks", 0)
            result.total_sessions = chunk_stats.get("indexed_sessions", 0)
            result.total_size_mb = chunk_stats.get("total_mb", 0.0)

            # Analyze per-session chunk distribution
            session_groups = await self._get_session_chunk_groups()
            optimizable = 0
            estimated_after = 0

            session_details = []
            for session_id, chunk_count in sorted(
                session_groups.items(), key=lambda x: x[1], reverse=True
            ):
                if chunk_count >= MIN_CHUNKS_TO_OPTIMIZE:
                    optimizable += 1
                    target = max(1, int(chunk_count * TARGET_COMPRESSION_RATIO))
                    estimated_after += target
                    session_details.append(
                        {
                            "session_id": session_id[:12],
                            "chunks": chunk_count,
                            "estimated_after": target,
                        }
                    )
                else:
                    estimated_after += chunk_count

            result.optimizable_sessions = optimizable
            result.estimated_chunks_after = estimated_after
            result.session_details = session_details

            # Get memory stats
            if self.memory_manager and user_id:
                try:
                    mem_stats = await self.memory_manager.get_stats(user_id)
                    result.total_memories = mem_stats.get("total", 0)
                    # Estimate ~20% reduction from dedup/merge
                    result.estimated_memories_after = (
                        max(1, int(result.total_memories * 0.8))
                        if result.total_memories > 5
                        else result.total_memories
                    )
                except Exception as e:
                    _LOGGER.debug("Memory stats failed during analysis: %s", e)

        except Exception as e:
            _LOGGER.error("RAG optimization analysis failed: %s", e)

        return result

    async def optimize_sessions(
        self,
        provider: Any,  # AIProvider
        model: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> OptimizationResult:
        """Optimize session chunks by condensing them per session.

        Args:
            provider: AI provider instance to use for condensation.
            model: Model to use (provider default if None).
            progress_callback: Async callback for progress updates.

        Returns:
            OptimizationResult with stats about the optimization.
        """
        result = OptimizationResult()
        start_time = time.time()

        try:
            session_groups = await self._get_session_chunk_groups()
            optimizable = {
                sid: count
                for sid, count in session_groups.items()
                if count >= MIN_CHUNKS_TO_OPTIMIZE
            }

            if not optimizable:
                await self._send_progress(
                    progress_callback, "status", "No sessions need optimization"
                )
                result.duration_seconds = time.time() - start_time
                return result

            total = len(optimizable)
            result.chunks_before = sum(optimizable.values())

            await self._send_progress(
                progress_callback,
                "status",
                f"Optimizing {total} sessions ({result.chunks_before} chunks)...",
            )

            processed = 0
            for session_id, chunk_count in optimizable.items():
                processed += 1
                pct = int((processed / total) * 100)
                await self._send_progress(
                    progress_callback,
                    "progress",
                    f"Session {processed}/{total}: condensing {chunk_count} chunks...",
                    progress=pct,
                    session=processed,
                    total_sessions=total,
                )

                try:
                    new_count = await self._optimize_single_session(
                        session_id, provider, model
                    )
                    result.chunks_after += new_count
                    result.sessions_processed += 1
                    await self._send_progress(
                        progress_callback,
                        "session_done",
                        f"Session {processed}/{total}: {chunk_count} -> {new_count} chunks",
                        progress=pct,
                        chunks_before=chunk_count,
                        chunks_after=new_count,
                    )
                except Exception as e:
                    error_msg = f"Session {session_id[:8]}: {e}"
                    _LOGGER.warning(
                        "Failed to optimize session %s: %s", session_id[:8], e
                    )
                    result.errors.append(error_msg)
                    # Keep original chunks on failure
                    result.chunks_after += chunk_count
                    await self._send_progress(
                        progress_callback,
                        "session_error",
                        f"Session {processed}/{total}: failed - {e}",
                        progress=pct,
                    )

            # Add non-optimizable chunks to the after count
            non_optimizable_count = sum(
                count
                for sid, count in session_groups.items()
                if count < MIN_CHUNKS_TO_OPTIMIZE
            )
            result.chunks_after += non_optimizable_count

        except Exception as e:
            _LOGGER.exception("Session optimization failed: %s", e)
            result.errors.append(f"Fatal: {e}")

        result.duration_seconds = time.time() - start_time
        return result

    async def optimize_memories(
        self,
        provider: Any,  # AIProvider
        model: str | None = None,
        user_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> OptimizationResult:
        """Optimize memories by merging duplicates and condensing.

        Args:
            provider: AI provider instance to use for condensation.
            model: Model to use (provider default if None).
            user_id: User whose memories to optimize.
            progress_callback: Async callback for progress updates.

        Returns:
            OptimizationResult with stats about the optimization.
        """
        result = OptimizationResult()
        start_time = time.time()

        if not self.memory_manager or not user_id:
            await self._send_progress(
                progress_callback, "status", "Memory system not available"
            )
            result.duration_seconds = time.time() - start_time
            return result

        try:
            # Get all memories
            memories = await self.memory_manager.list_memories(user_id, limit=500)
            result.memories_before = len(memories)

            if result.memories_before < 5:
                await self._send_progress(
                    progress_callback, "status", "Too few memories to optimize"
                )
                result.memories_after = result.memories_before
                result.duration_seconds = time.time() - start_time
                return result

            await self._send_progress(
                progress_callback,
                "status",
                f"Condensing {result.memories_before} memories...",
            )

            # Group memories by category for better condensation
            by_category: dict[str, list[Any]] = defaultdict(list)
            for mem in memories:
                by_category[mem.category].append(mem)

            all_new_memories: list[dict[str, Any]] = []
            total_cats = len(by_category)
            processed_cats = 0

            for category, cat_memories in by_category.items():
                processed_cats += 1
                pct = int((processed_cats / total_cats) * 100)
                cat_count = len(cat_memories)
                await self._send_progress(
                    progress_callback,
                    "progress",
                    f"Category: {category} ({cat_count} memories)...",
                    progress=pct,
                )

                if cat_count < 3:
                    # Too few to condense — keep as-is
                    for mem in cat_memories:
                        all_new_memories.append(
                            {
                                "text": mem.text,
                                "category": mem.category,
                                "importance": mem.importance,
                                "source": mem.source,
                            }
                        )
                    await self._send_progress(
                        progress_callback,
                        "category_done",
                        f"Category {category}: kept {cat_count} (too few to condense)",
                        progress=pct,
                        memories_before=cat_count,
                        memories_after=cat_count,
                    )
                    continue

                try:
                    condensed = await self._condense_memories(
                        cat_memories, provider, model
                    )
                    all_new_memories.extend(condensed)
                    await self._send_progress(
                        progress_callback,
                        "category_done",
                        f"Category {category}: {cat_count} -> {len(condensed)} memories",
                        progress=pct,
                        memories_before=cat_count,
                        memories_after=len(condensed),
                    )
                except Exception as e:
                    error_msg = f"Category {category}: {e}"
                    _LOGGER.warning("Failed to condense %s memories: %s", category, e)
                    result.errors.append(error_msg)
                    # Keep originals on failure
                    for mem in cat_memories:
                        all_new_memories.append(
                            {
                                "text": mem.text,
                                "category": mem.category,
                                "importance": mem.importance,
                                "source": mem.source,
                            }
                        )
                    await self._send_progress(
                        progress_callback,
                        "category_error",
                        f"Category {category}: failed - {e}",
                        progress=pct,
                    )

            # Replace memories: delete all, re-store condensed
            if all_new_memories and not result.errors:
                await self._send_progress(
                    progress_callback,
                    "status",
                    "Replacing memories with condensed versions...",
                )

                # Delete all old memories
                await self.memory_manager.forget_all_user_memories(user_id)

                # Store condensed memories
                for mem_data in all_new_memories:
                    try:
                        await self.memory_manager.store_memory(
                            text=mem_data["text"],
                            user_id=user_id,
                            category=mem_data["category"],
                            importance=mem_data.get("importance", 0.7),
                            source="optimizer",
                        )
                    except Exception as e:
                        _LOGGER.debug("Failed to store condensed memory: %s", e)

                result.memories_after = len(all_new_memories)
            else:
                result.memories_after = result.memories_before

        except Exception as e:
            _LOGGER.exception("Memory optimization failed: %s", e)
            result.errors.append(f"Fatal: {e}")

        result.duration_seconds = time.time() - start_time
        return result

    async def optimize_all(
        self,
        provider: Any,
        model: str | None = None,
        user_id: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> OptimizationResult:
        """Run full optimization (sessions + memories).

        Args:
            provider: AI provider instance for condensation.
            model: Model to use.
            user_id: User ID for memory optimization.
            progress_callback: Async callback for progress updates.

        Returns:
            Combined OptimizationResult.
        """
        await self._send_progress(
            progress_callback, "status", "Starting full RAG optimization..."
        )

        # Phase 1: Sessions
        await self._send_progress(
            progress_callback, "phase", "Phase 1: Optimizing session chunks..."
        )
        session_result = await self.optimize_sessions(
            provider, model, progress_callback
        )

        # Phase 2: Memories
        await self._send_progress(
            progress_callback, "phase", "Phase 2: Optimizing memories..."
        )
        memory_result = await self.optimize_memories(
            provider, model, user_id, progress_callback
        )

        # Combine results
        combined = OptimizationResult(
            sessions_processed=session_result.sessions_processed,
            chunks_before=session_result.chunks_before,
            chunks_after=session_result.chunks_after,
            memories_before=memory_result.memories_before,
            memories_after=memory_result.memories_after,
            errors=session_result.errors + memory_result.errors,
            duration_seconds=session_result.duration_seconds
            + memory_result.duration_seconds,
        )

        await self._send_progress(
            progress_callback, "complete", "Optimization complete!"
        )
        return combined

    # --- Private Helpers ---

    async def _get_session_chunk_groups(self) -> dict[str, int]:
        """Get chunk counts grouped by session_id.

        Returns:
            Dict mapping session_id to chunk count.
        """
        try:
            conn = self.store._conn
            if not conn:
                return {}
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id, COUNT(*) as cnt FROM session_chunks GROUP BY session_id"
            )
            return {row["session_id"]: row["cnt"] for row in cursor.fetchall()}
        except Exception as e:
            _LOGGER.error("Failed to get session chunk groups: %s", e)
            return {}

    async def _get_full_session_chunks(self, session_id: str) -> list[dict[str, Any]]:
        """Get all chunks for a session with full text.

        Args:
            session_id: Session to retrieve chunks for.

        Returns:
            List of chunk dicts with id, text, metadata, start_msg, end_msg.
        """
        try:
            conn = self.store._conn
            if not conn:
                return []
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, session_id, text, metadata, start_msg, end_msg
                   FROM session_chunks WHERE session_id = ?
                   ORDER BY start_msg ASC""",
                (session_id,),
            )
            results = []
            for row in cursor.fetchall():
                import json

                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                results.append(
                    {
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "text": row["text"],
                        "metadata": metadata,
                        "start_msg": row["start_msg"],
                        "end_msg": row["end_msg"],
                    }
                )
            return results
        except Exception as e:
            _LOGGER.error(
                "Failed to get full chunks for session %s: %s", session_id[:8], e
            )
            return []

    async def _optimize_single_session(
        self,
        session_id: str,
        provider: Any,
        model: str | None,
    ) -> int:
        """Optimize chunks for a single session.

        Args:
            session_id: Session whose chunks to optimize.
            provider: AI provider for condensation.
            model: Model to use.

        Returns:
            Number of new chunks after optimization.

        Raises:
            Exception: If optimization fails.
        """
        chunks = await self._get_full_session_chunks(session_id)
        if not chunks:
            return 0

        # Build batches respecting MAX_TEXT_PER_BATCH
        batches = self._build_chunk_batches(chunks)
        all_condensed_texts: list[str] = []

        for batch in batches:
            batch_text = "\n---\n".join(c["text"] for c in batch)
            target_count = max(1, int(len(batch) * TARGET_COMPRESSION_RATIO))

            user_prompt = (
                f"Condense these {len(batch)} conversation chunks into approximately "
                f"{target_count} summary chunks. Input:\n\n{batch_text}"
            )

            messages = [
                {"role": "system", "content": SESSION_CONDENSE_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            kwargs: dict[str, Any] = {}
            if model:
                kwargs["model"] = model

            response = await provider.get_response(messages, **kwargs)
            if not response or not response.strip():
                raise ValueError("Empty response from AI provider")

            # Parse response into individual chunks
            parsed = self._parse_condensed_chunks(response)
            if parsed:
                all_condensed_texts.extend(parsed)
            else:
                # If parsing fails, use the whole response as one chunk
                all_condensed_texts.append(response.strip())

        if not all_condensed_texts:
            return len(chunks)

        # Generate embeddings for condensed chunks
        embeddings = await self.embedding_provider.get_embeddings(all_condensed_texts)
        if not embeddings or len(embeddings) != len(all_condensed_texts):
            raise ValueError("Embedding generation failed for condensed chunks")

        # Build new chunk data
        import json

        now = time.time()
        new_ids = []
        new_texts = []
        new_metadatas = []
        original_start = chunks[0]["start_msg"]
        original_end = chunks[-1]["end_msg"]

        for i, text in enumerate(all_condensed_texts):
            # Deterministic ID based on content
            chunk_hash = hashlib.sha256(
                f"optimized:{session_id}:{i}:{text}".encode()
            ).hexdigest()[:16]
            chunk_id = f"opt_{session_id[:8]}_{chunk_hash}"

            # Distribute start/end range across condensed chunks
            total_condensed = len(all_condensed_texts)
            range_size = original_end - original_start
            chunk_start = original_start + int((i / total_condensed) * range_size)
            chunk_end = original_start + int(((i + 1) / total_condensed) * range_size)

            new_ids.append(chunk_id)
            new_texts.append(text)
            new_metadatas.append(
                {
                    "start_msg": chunk_start,
                    "end_msg": chunk_end,
                    "optimized": True,
                    "optimized_at": now,
                    "original_chunk_count": len(chunks),
                }
            )

        # Replace old chunks with new ones atomically
        # First delete old chunks
        await self.store.delete_session_chunks(session_id)

        # Then add new condensed chunks
        content_hash = hashlib.sha256(
            json.dumps(all_condensed_texts, sort_keys=True).encode()
        ).hexdigest()

        await self.store.add_session_chunks(
            ids=new_ids,
            texts=new_texts,
            embeddings=embeddings,
            metadatas=new_metadatas,
            session_id=session_id,
            content_hash=content_hash,
        )

        _LOGGER.info(
            "Optimized session %s: %d chunks -> %d chunks",
            session_id[:8],
            len(chunks),
            len(all_condensed_texts),
        )

        return len(all_condensed_texts)

    def _build_chunk_batches(
        self, chunks: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Split chunks into batches that fit within MAX_TEXT_PER_BATCH.

        Args:
            chunks: All chunks for a session, ordered by start_msg.

        Returns:
            List of batches, each a list of chunk dicts.
        """
        batches: list[list[dict[str, Any]]] = []
        current_batch: list[dict[str, Any]] = []
        current_text_len = 0

        for chunk in chunks:
            chunk_len = len(chunk.get("text", ""))
            if current_batch and (
                current_text_len + chunk_len > MAX_TEXT_PER_BATCH
                or len(current_batch) >= MAX_CHUNKS_PER_BATCH
            ):
                batches.append(current_batch)
                current_batch = []
                current_text_len = 0

            current_batch.append(chunk)
            current_text_len += chunk_len

        if current_batch:
            batches.append(current_batch)

        return batches

    def _parse_condensed_chunks(self, response: str) -> list[str]:
        """Parse AI response into individual condensed chunks.

        Expected format: chunks separated by "---" on its own line.

        Args:
            response: Raw AI response text.

        Returns:
            List of individual chunk texts.
        """
        # Split by "---" separator
        parts = response.split("\n---\n")
        if len(parts) < 2:
            # Try alternative separators
            parts = response.split("\n---")
            if len(parts) < 2:
                parts = response.split("---\n")

        # Clean up each chunk
        result = []
        for part in parts:
            cleaned = part.strip()
            if cleaned and len(cleaned) > 20:  # Skip very short fragments
                result.append(cleaned)

        return result

    async def _condense_memories(
        self,
        memories: list[Any],
        provider: Any,
        model: str | None,
    ) -> list[dict[str, Any]]:
        """Condense a list of memories using AI.

        Args:
            memories: List of Memory objects to condense.
            provider: AI provider instance.
            model: Model to use.

        Returns:
            List of condensed memory dicts with text, category, importance, source.
        """
        # Build input text
        memory_lines = []
        for mem in memories:
            memory_lines.append(f"[{mem.category}] {mem.text}")

        input_text = "\n".join(memory_lines)

        messages = [
            {"role": "system", "content": MEMORY_CONDENSE_PROMPT},
            {
                "role": "user",
                "content": f"Condense these {len(memories)} memories:\n\n{input_text}",
            },
        ]

        kwargs: dict[str, Any] = {}
        if model:
            kwargs["model"] = model

        response = await provider.get_response(messages, **kwargs)
        if not response or not response.strip():
            raise ValueError("Empty response from AI provider")

        # Parse response
        condensed = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Extract category from [category] prefix
            category = memories[0].category  # Default to group category
            if line.startswith("["):
                bracket_end = line.find("]")
                if bracket_end > 0:
                    parsed_cat = line[1:bracket_end].strip().lower()
                    text = line[bracket_end + 1 :].strip()
                    if parsed_cat in (
                        "fact",
                        "preference",
                        "decision",
                        "entity",
                        "other",
                    ):
                        category = parsed_cat
                    else:
                        text = line
                else:
                    text = line
            else:
                text = line

            if text and len(text) > 10:
                # Average importance of merged memories
                avg_importance = sum(m.importance for m in memories) / len(memories)
                condensed.append(
                    {
                        "text": text,
                        "category": category,
                        "importance": round(avg_importance, 2),
                        "source": "optimizer",
                    }
                )

        return (
            condensed
            if condensed
            else [
                {
                    "text": m.text,
                    "category": m.category,
                    "importance": m.importance,
                    "source": m.source,
                }
                for m in memories
            ]
        )

    @staticmethod
    async def _send_progress(
        callback: ProgressCallback | None,
        event_type: str,
        message: str,
        **kwargs: Any,
    ) -> None:
        """Send a progress update via the callback.

        Args:
            callback: The async callback function, or None.
            event_type: Type of progress event (status, progress, phase, complete).
            message: Human-readable progress message.
            **kwargs: Additional data (e.g., progress=50 for percentage).
        """
        if callback is None:
            return
        try:
            await callback({"type": event_type, "message": message, **kwargs})
        except Exception:
            pass  # Progress reporting is non-critical
