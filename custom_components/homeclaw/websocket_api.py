"""WebSocket API for Homeclaw chat sessions.

This module is a backward-compatible facade. The actual handler implementations
live in the ``ws_handlers`` package. All public symbols are re-exported here so
that existing imports (``from .websocket_api import ...``) continue to work.
"""

from __future__ import annotations

# Re-export the registration entry-point (used by __init__.py)
from .ws_handlers import async_register_websocket_commands  # noqa: F401

# Re-export shared helpers, validators and constants (used by tests)
from .ws_handlers._common import (  # noqa: F401
    _STORAGE_CACHE_PREFIX,
    ERR_AI_ERROR,
    ERR_INVALID_INPUT,
    ERR_RATE_LIMITED,
    ERR_SESSION_NOT_FOUND,
    ERR_STORAGE_ERROR,
    MAX_TITLE_LENGTH,
    UUID_PATTERN,
    _get_storage,
    _get_user_id,
    _validate_message,
    _validate_session_id,
    _validate_title,
)

# Re-export all handlers (used by tests that import individual handlers)
from .ws_handlers.chat import (  # noqa: F401
    _rag_post_conversation,
    ws_send_message,
    ws_send_message_stream,
)
from .ws_handlers.models import (  # noqa: F401
    _validate_model_entry,
    ws_config_models_add_provider,
    ws_config_models_get,
    ws_config_models_remove_provider,
    ws_config_models_update,
    ws_get_available_models,
    ws_get_preferences,
    ws_get_providers_config,
    ws_set_preferences,
)
from .ws_handlers.rag import (  # noqa: F401
    ws_rag_identity,
    ws_rag_identity_update,
    ws_rag_memories,
    ws_rag_memory_delete,
    ws_rag_optimize_analyze,
    ws_rag_optimize_run,
    ws_rag_search,
    ws_rag_sessions,
    ws_rag_stats,
)
from .ws_handlers.proactive import (  # noqa: F401
    ws_proactive_alerts,
    ws_proactive_config_get,
    ws_proactive_config_set,
    ws_proactive_run,
    ws_scheduler_add,
    ws_scheduler_enable,
    ws_scheduler_history,
    ws_scheduler_list,
    ws_scheduler_remove,
    ws_scheduler_run,
    ws_subagent_cancel,
    ws_subagent_get,
    ws_subagent_list,
)
from .ws_handlers.sessions import (  # noqa: F401
    ws_create_session,
    ws_delete_session,
    ws_generate_emoji,
    ws_get_session,
    ws_list_sessions,
    ws_rename_session,
)
