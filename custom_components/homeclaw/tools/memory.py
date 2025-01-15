"""Memory tools for Homeclaw.

Provides tools for the AI agent to store, recall, and manage long-term memories
during conversations. These tools allow the agent to explicitly save user
preferences, facts, and decisions, search for relevant memories, and delete
specific memories.

The tools use the MemoryManager from the memory module, accessing it through
the RAG manager stored in hass.data[DOMAIN].
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..const import DOMAIN
from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult

_LOGGER = logging.getLogger(__name__)


def _get_memory_manager(hass: Any) -> Any | None:
    """Get the MemoryManager from hass.data.

    Returns None if RAG/memory is not initialized.
    """
    if not hass or DOMAIN not in hass.data:
        return None

    rag_manager = hass.data[DOMAIN].get("rag_manager")
    if not rag_manager or not rag_manager.is_initialized:
        return None

    return getattr(rag_manager, "memory_manager", None)


def _get_current_user_id(hass: Any) -> str:
    """Get the current user ID from conversation context.

    The websocket handler stores the current user_id in hass.data[DOMAIN]
    before tool execution. Falls back to 'default' if not available.
    """
    if not hass or DOMAIN not in hass.data:
        return "default"

    return hass.data[DOMAIN].get("_current_user_id", "default")


@ToolRegistry.register
class MemoryStoreTool(Tool):
    """Store information in long-term memory.

    Use this tool to remember user preferences, important facts, decisions,
    or any information the user explicitly asks you to remember. Memories
    persist across sessions and conversations.
    """

    id = "memory_store"
    description = (
        "Store information in long-term memory. Use when the user asks you to "
        "remember something, states a preference, makes a decision, or shares "
        "important personal information. Memories persist across conversations."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="text",
            type="string",
            description="The information to remember (e.g., 'User prefers warm white lights')",
            required=True,
        ),
        ToolParameter(
            name="category",
            type="string",
            description="Type of memory",
            required=False,
            default="fact",
            enum=["preference", "fact", "decision", "entity", "observation", "other"],
        ),
        ToolParameter(
            name="importance",
            type="number",
            description="How important this memory is (0.0-1.0, default 0.8)",
            required=False,
            default=0.8,
        ),
        ToolParameter(
            name="ttl_days",
            type="integer",
            description=(
                "Time-to-live in days. Memory auto-expires after this period. "
                "Default: 7 for observations, permanent for other categories."
            ),
            required=False,
        ),
    ]

    async def execute(self, text: str, **kwargs: Any) -> ToolResult:
        """Store a memory."""
        memory_manager = _get_memory_manager(self.hass)
        if not memory_manager:
            return ToolResult(
                output="Memory system not available",
                error="memory_not_initialized",
                success=False,
            )

        category = kwargs.get("category", "fact")
        importance = kwargs.get("importance", 0.8)
        ttl_days = kwargs.get("ttl_days")
        user_id = _get_current_user_id(self.hass)

        try:
            # Clamp importance
            importance = max(0.0, min(1.0, float(importance)))

            # Validate ttl_days
            if ttl_days is not None:
                ttl_days = max(1, min(365, int(ttl_days)))

            memory_id = await memory_manager.store_memory(
                text=text,
                user_id=user_id,
                category=category,
                importance=importance,
                source="agent",
                ttl_days=ttl_days,
            )

            if memory_id:
                result = {
                    "stored": True,
                    "memory_id": memory_id,
                    "category": category,
                    "importance": importance,
                }
                if ttl_days is not None:
                    result["ttl_days"] = ttl_days
                return ToolResult(
                    output=json.dumps(result),
                    metadata=result,
                )
            else:
                return ToolResult(
                    output=json.dumps({"stored": False, "reason": "duplicate_memory"}),
                    metadata={"stored": False, "reason": "duplicate_memory"},
                )

        except Exception as e:
            _LOGGER.error("memory_store tool failed: %s", e)
            return ToolResult(
                output=f"Failed to store memory: {e}",
                error=str(e),
                success=False,
            )


@ToolRegistry.register
class MemoryRecallTool(Tool):
    """Search long-term memory for relevant information.

    Use this tool to look up previously stored memories — user preferences,
    facts, decisions, or any other information that was remembered from
    past conversations.
    """

    id = "memory_recall"
    description = (
        "Search long-term memory for relevant information. Use when you need to "
        "recall user preferences, past decisions, personal details, or any "
        "previously stored facts from earlier conversations."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="What to search for (e.g., 'light preferences', 'bedroom setup')",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of results (default 5)",
            required=False,
            default=5,
        ),
    ]

    async def execute(self, query: str, **kwargs: Any) -> ToolResult:
        """Search memories."""
        memory_manager = _get_memory_manager(self.hass)
        if not memory_manager:
            return ToolResult(
                output="Memory system not available",
                error="memory_not_initialized",
                success=False,
            )

        limit = kwargs.get("limit", 5)
        user_id = _get_current_user_id(self.hass)

        try:
            limit = max(1, min(20, int(limit)))

            memories = await memory_manager.search_memories(
                query=query,
                user_id=user_id,
                limit=limit,
            )

            if not memories:
                return ToolResult(
                    output=json.dumps({"memories": [], "count": 0}),
                    metadata={"memories": [], "count": 0},
                )

            results = [
                {
                    "id": m.id,
                    "text": m.text,
                    "category": m.category,
                    "importance": m.importance,
                    "score": round(m.score, 3),
                }
                for m in memories
            ]

            output = {
                "memories": results,
                "count": len(results),
            }
            return ToolResult(
                output=json.dumps(output),
                metadata=output,
            )

        except Exception as e:
            _LOGGER.error("memory_recall tool failed: %s", e)
            return ToolResult(
                output=f"Failed to search memories: {e}",
                error=str(e),
                success=False,
            )


@ToolRegistry.register
class MemoryForgetTool(Tool):
    """Delete a memory from long-term storage.

    Use this tool when the user explicitly asks to forget something,
    or to remove outdated/incorrect memories.
    """

    id = "memory_forget"
    description = (
        "Delete a specific memory by ID, or search and delete matching memories. "
        "Use when the user asks to forget something or correct outdated information."
    )
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(
            name="memory_id",
            type="string",
            description="The memory ID to delete (from memory_recall results)",
            required=False,
        ),
        ToolParameter(
            name="query",
            type="string",
            description="Search query to find and delete matching memories",
            required=False,
        ),
    ]

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Delete memories."""
        memory_manager = _get_memory_manager(self.hass)
        if not memory_manager:
            return ToolResult(
                output="Memory system not available",
                error="memory_not_initialized",
                success=False,
            )

        memory_id = kwargs.get("memory_id")
        query = kwargs.get("query")
        user_id = _get_current_user_id(self.hass)

        if not memory_id and not query:
            return ToolResult(
                output="Either memory_id or query must be provided",
                error="missing_parameter",
                success=False,
            )

        try:
            deleted = []

            if memory_id:
                # Delete specific memory by ID
                success = await memory_manager.forget_memory(memory_id)
                if success:
                    deleted.append(memory_id)

            elif query:
                # Search for matching memories and delete the top match
                memories = await memory_manager.search_memories(
                    query=query,
                    user_id=user_id,
                    limit=5,
                )
                # Only delete memories with high relevance (>0.7 similarity)
                for m in memories:
                    if m.score >= 0.7:
                        success = await memory_manager.forget_memory(m.id)
                        if success:
                            deleted.append(m.id)

            result = {
                "deleted_count": len(deleted),
                "deleted_ids": deleted,
            }

            if deleted:
                return ToolResult(
                    output=json.dumps(result),
                    metadata=result,
                )
            else:
                return ToolResult(
                    output=json.dumps(
                        {"deleted_count": 0, "message": "No matching memories found"}
                    ),
                    metadata={"deleted_count": 0},
                )

        except Exception as e:
            _LOGGER.error("memory_forget tool failed: %s", e)
            return ToolResult(
                output=f"Failed to delete memory: {e}",
                error=str(e),
                success=False,
            )
