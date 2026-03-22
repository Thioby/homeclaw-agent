# Coding Conventions

**Analysis Date:** 2026-03-20

## Naming Patterns

**Files:**
- Lowercase with underscores: `query_processor.py`, `token_estimator.py`, `base_client.py`
- Test files: `test_*.py` prefix (required by pytest config)
- Module organization: related functionality grouped in directories (e.g., `core/`, `providers/`, `rag/`, `managers/`)

**Functions:**
- Async functions: `async def async_setup()`, `async def async_get_or_create()`
- Synchronous functions: `def _clean_response()`, `def parse()`, `def load_models_config()`
- Private functions: underscore prefix: `_build_headers()`, `_extract_response()`, `_is_tool_call()`
- Public class methods for internal classes: PascalCase: `get_response()`, `supports_tools`

**Variables:**
- Local variables: snake_case: `call_history_hashes`, `non_system_messages`, `max_iterations`
- Module-level constants: UPPERCASE: `DEFAULT_MAX_RETRIES`, `MAX_TOOL_RESULT_CHARS`, `INVISIBLE_CHARS`
- Private module variables: underscore prefix: `_LOGGER`, `_cache`, `_SENSITIVE_KEYS`

**Types:**
- Class names: PascalCase: `Agent`, `ResponseParser`, `ConversationManager`, `BaseHTTPClient`
- Dataclass usage: `@dataclass` decorator for immutable message types (e.g., `Message`, `ChannelTarget`)
- Type hints: Full type annotations with `from __future__ import annotations` at top of file
- Union types: Modern syntax `Type1 | Type2` instead of `Union[Type1, Type2]`
- Optional types: `str | None` instead of `Optional[str]`

## Code Style

**Formatting:**
- Line length: 127 characters (per `setup.cfg` flake8 config)
- No automatic formatter enforced (flake8 + isort + mypy only)
- Indentation: 4 spaces (PEP 8)
- Imports: Sort with isort profile `black` (alphabetical within groups)

**Linting:**
- Tool: flake8 with selective ignores in `setup.cfg`
  - Ignores: E203, W503, W291, W293, E128, E226, E501, C901, F401, F811, F821, F841
  - Per-file: `__init__.py` ignores F401 (unused imports in barrel files)
- Type checking: mypy with lenient settings
  - `disallow_untyped_defs = False`
  - `ignore_missing_imports = True`
  - `allow_untyped_calls = True` (permissive for Home Assistant integration)

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library: `import logging`, `import json`, `from typing import ...`
3. Third-party: `from homeassistant.core import ...`, `import pytest`
4. Local imports: `from ..providers.registry import ...`, `from .response_parser import ...`

**Path Aliases:**
- Relative imports: Use `..` and `.` for navigation (e.g., `from ..function_calling import`, `from .query_processor import`)
- TYPE_CHECKING blocks: Used for type-only imports to avoid circular dependencies:
  ```python
  if TYPE_CHECKING:
      from homeassistant.core import HomeAssistant
      from ..providers.registry import AIProvider
  ```
- Avoid star imports: Always explicit `from module import Class, function`

## Error Handling

**Patterns:**
- Broad exception catching: `except Exception as e:` used in tool execution and fallback paths
  - Example in `tool_executor.py` line 232: Circuit breaker catches all exceptions
  - Example in `compaction.py` line 180: Graceful fallback to truncation on any error
- Specific exceptions: `except (FileNotFoundError, json.JSONDecodeError) as err:` when parsing files
- RuntimeError for contract violations: `raise RuntimeError("Circuit breaker activated: ...")` in `subagent.py`
- ConfigEntryNotReady: Home Assistant specific exception for async setup failures
- No custom exception classes defined in codebase (all use built-in or HA exceptions)

**Error context:**
- Always include context in error messages: `_LOGGER.error("Could not load models config: %s", err)`
- Error messages use format strings with `%s` placeholders (not f-strings)
- Include relevant data in exception messages for debugging

## Logging

**Framework:** Built-in Python `logging` module

**Setup pattern:**
- Every module: `_LOGGER = logging.getLogger(__name__)` at module level
- Example: `custom_components/homeclaw/models.py` line 14

**Patterns:**
- Debug logs for detailed flow: `_LOGGER.debug("Heartbeat disabled, not starting interval")`
- Info logs for significant state changes: `_LOGGER.info("Successfully set up Homeclaw for provider: %s", provider)`
- Warning logs for recoverable issues: `_LOGGER.warning("Could not load models config: %s", err)`
- Error logs for failures: `_LOGGER.error("Failed to get Gemini user info: %s", error_text)`
- Exception logs via `.exception()`: Not used (prefer explicit error logging)

**Log message format:**
- Use interpolation: `_LOGGER.info("Message %s", variable)` not `f"Message {variable}"`
- Prefix with context: `"Heartbeat: no agent available"` includes component context
- Include recovery info: `"Circuit breaker triggered for tool '%s' (called %d times...)"`

## Comments

**When to Comment:**
- Complex algorithms: Annotate strategy (e.g., ResponseParser explains JSON extraction strategy)
- Non-obvious workarounds: Comment temporary solutions and why they exist
- Business logic: Explain intent, not what the code does
- Do NOT comment obvious code: `x = 1  # set x to 1` is noise

**JSDoc/TSDoc:**
- Use module docstrings: Every file starts with `"""Purpose of this module."""`
- Use class docstrings: `"""ClassName - what it does."""` with Attributes section
- Use method docstrings: Describe Args, Returns, Raises in Google style
- Example from `agent.py` (lines 30-40): Class docstring with purpose, attributes
- Function docstrings required for public methods: `async def process_query(...) -> dict[str, Any]:`

**Docstring style:**
```python
def method(self, arg: str) -> bool:
    """Brief description.

    Longer description explaining intent and behavior.

    Args:
        arg: What this argument means.

    Returns:
        What the return value represents.

    Raises:
        ValueError: When something goes wrong.
    """
```

## Function Design

**Size:** No strict limit observed; functions range from 10 to 150+ lines
- Preference: Smaller focused functions (< 50 lines) for readability
- Large functions: `_run_stream` in `discord/__init__.py` handles complex logic sequentially
- Refactoring target: Large files split into focused modules (e.g., `query_processor.py` split into `context_builder.py`, `tool_loop.py`, `stream_loop.py`)

**Parameters:**
- Type hints always included
- Default values for optional parameters: `max_iterations: int = 20`
- Kwargs for extensibility: `async def execute_tool_calls(..., **kwargs: Any) -> AsyncGenerator`
- Positional-only rarely used; prefer named arguments for clarity

**Return Values:**
- Type hints required: `-> dict[str, Any]`, `-> AsyncGenerator[dict, None]`, `-> bool`
- Return dict with status: Pattern used in async operations
  ```python
  # Example from agent.py
  return {
      "success": True,
      "response": parsed_response,
      "tool_calls": tool_calls,
  }
  ```
- Async generators: Used for streaming results with `yield` statements

## Module Design

**Exports:**
- Public API: Defined explicitly in module docstrings
- Barrel files (`__init__.py`): Re-export main classes for convenience
  - Example: `custom_components/homeclaw/core/__init__.py` exports `Agent`, `QueryProcessor`, `ResponseParser`
  - Home Assistant integration pattern: Allow `from custom_components.homeclaw.core import Agent`

**Barrel Files:**
- Purpose: Simplify imports for consumers
- Convention: Only export classes/functions meant for external use
- Private modules: Prefixed with `_` (e.g., `_temporal.py`, `_store_cache.py`) not in barrel exports

**Module organization:**
- Utilities: `custom_components/homeclaw/utils/` for shared helpers (yaml_io, yaml_writer)
- Providers: `custom_components/homeclaw/providers/` for AI provider implementations
- RAG: `custom_components/homeclaw/rag/` for retrieval-augmented generation system
- Tools: `custom_components/homeclaw/tools/` for agent tools
- Managers: `custom_components/homeclaw/managers/` for Home Assistant subsystem managers

---

*Convention analysis: 2026-03-20*
