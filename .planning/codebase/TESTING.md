# Testing Patterns

**Analysis Date:** 2026-03-20

## Test Framework

**Runner:**
- pytest 7+ (from git history)
- Config: `/Users/anowak/Projects/homeAssistant/ai_agent_ha/pytest.ini`
- Plugin: `pytest-homeassistant-custom-component` for Home Assistant integration testing
- Async support: `pytest-asyncio` with `asyncio_mode = auto`

**Assertion Library:**
- Standard pytest assertions: `assert result["type"] == "text"`
- pytest built-in: `pytest.raises(TypeError, match="abstract method")`
- unittest.mock: `MagicMock`, `AsyncMock`, `patch` for mocking

**Run Commands:**
```bash
pytest tests/                          # Run all tests
pytest tests/ -v                       # Verbose output
pytest tests/ --cov=custom_components/homeclaw --cov-report=html  # With coverage
pytest tests/ -k "test_parse"          # Run specific tests by name
pytest tests/ -m asyncio               # Run only async tests
```

## Test File Organization

**Location:**
- Co-located with source (mirror structure under `tests/`)
- Example: `custom_components/homeclaw/core/agent.py` → `tests/test_core/test_agent.py`
- Example: `custom_components/homeclaw/providers/base_client.py` → `tests/test_providers/test_base_client.py`

**Naming:**
- Test files: `test_*.py` (required by `pytest.ini` python_files pattern)
- Test classes: `Test*` (required by `pytest.ini` python_classes pattern)
- Test functions: `test_*` (required by `pytest.ini` python_functions pattern)

**Structure:**
```
tests/
├── conftest.py                        # Root fixtures (shared across all tests)
├── fixtures/                          # Fixture modules
│   ├── __init__.py
│   └── ha_fixtures.py                 # HA-specific fixtures
├── test_core/
│   ├── __init__.py
│   ├── conftest.py                    # Core module specific fixtures
│   ├── test_agent.py
│   ├── test_response_parser.py
│   └── test_tool_executor.py
├── test_providers/
│   ├── test_base_client.py
│   ├── test_gemini.py
│   └── test_openai.py
├── test_rag/
│   ├── conftest.py                    # RAG-specific fixtures
│   ├── test_query_engine.py
│   └── test_embeddings.py
└── test_memory/
    ├── test_memory_store.py
    └── test_identity_manager.py
```

## Test Structure

**Suite Organization:**
```python
# From tests/test_core/test_agent.py

class TestAgentInitWithProvider:
    """Tests for Agent initialization with AI provider."""

    def test_init_with_provider(self) -> None:
        """Test that Agent initializes with an AI provider."""
        hass = MockHass()
        provider = MockProvider()

        agent = Agent(hass=hass, provider=provider)

        assert agent.hass is hass
        assert agent.provider is provider
```

**Patterns:**
- Test classes: Group related tests together
  - Pattern: `Test{Component}{Scenario}` (e.g., `TestAgentInitWithProvider`, `TestParseTextResponse`)
  - One assertion per test or tightly related assertions
  - Use descriptive docstrings as test documentation

- Test methods: One behavior per test
  - Pattern: `test_{what_is_tested}_{expected_result}` or `test_{scenario}_{outcome}`
  - Example: `test_parse_text_response_returns_plain_text()`
  - Example: `test_init_creates_query_processor()`

- Async tests: Mark with `@pytest.mark.asyncio`
  ```python
  @pytest.mark.asyncio
  async def test_process_query_success(self, hass: HomeAssistant) -> None:
      """Test successful query processing."""
      agent = Agent(hass=hass, provider=MockProvider())
      result = await agent.process_query("Hello")
      assert result["success"] is True
  ```

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**

Mock class design:
```python
# From tests/test_core/test_agent.py
class MockProvider:
    """Mock AI provider for testing."""

    def __init__(self, response: str = "Test response") -> None:
        """Initialize with a canned response."""
        self._response = response
        self.get_response = AsyncMock(return_value=response)
        self.supports_tools = True
```

Mocking in tests:
```python
# From tests/test_providers/test_base_client.py
with patch(
    "custom_components.homeclaw.providers.base_client.async_get_clientsession",
    return_value=mock_session,
) as mock_get_session:
    client = ConcreteHTTPClient(hass, config)
    session = client.session
    mock_get_session.assert_called_once_with(hass)
```

**What to Mock:**
- External dependencies: Home Assistant instances, API clients, file I/O
- Time-dependent operations: Use mocks instead of real delays
- Database operations: Mock storage/persistence layers
- Network calls: Mock HTTP responses and SDK clients

**What NOT to Mock:**
- Pure logic: Parse functions, validation functions should run real code
- Data structures: Use real dataclasses/dicts unless testing data transformation
- Logging: Let real logger calls flow through (test behavior, not logging calls)
- Internal class methods: Test public interface instead

**AsyncMock usage:**
```python
# Create async mock
mock_provider = AsyncMock()
mock_provider.get_response = AsyncMock(return_value="Test response")

# Use with patch
with patch("module.ClassName", return_value=AsyncMock()):
    await some_function()
```

## Fixtures and Factories

**Test Data:**

Home Assistant fixtures (from `tests/fixtures/ha_fixtures.py`):
```python
@pytest.fixture
def homeclaw_config_entry() -> MockConfigEntry:
    """Create a mock config entry for Homeclaw."""
    return MockConfigEntry(
        domain="homeclaw",
        title="Homeclaw",
        data={
            "ai_provider": "openai",
            "openai_token": "sk-test-token",
            "models": {"openai": "gpt-4"},
            "rag_enabled": False,
        },
        entry_id="test_entry_id",
        version=1,
    )
```

RAG fixtures (from `tests/test_rag/conftest.py`):
```python
@dataclass
class MockEmbeddingProvider:
    """Mock embedding provider for testing."""
    dimension: int = 768
    provider_name: str = "mock"
    _call_count: int = field(default=0, repr=False)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate fake embeddings."""
        self._call_count += 1
        embeddings = []
        for i, text in enumerate(texts):
            base = hash(text) % 100 / 100
            embedding = [base + j * 0.001 for j in range(self.dimension)]
            embeddings.append(embedding)
        return embeddings
```

**Location:**
- Root fixtures: `tests/conftest.py` (global scope)
- Module-specific: `tests/test_core/conftest.py`, `tests/test_rag/conftest.py`
- Fixture library: `tests/fixtures/ha_fixtures.py` (re-exported in root conftest)
- Imported in conftest: `from tests.fixtures import *`

**Fixture lifecycle:**
- Scope: `function` (default, recreated per test) or `module` (shared across module tests)
- Async fixtures: `@pytest_asyncio.fixture async def fixture_name():`
- Setup/teardown: Use `yield` to separate setup from cleanup
  ```python
  @pytest_asyncio.fixture
  async def setup_homeclaw(hass, homeclaw_config_entry):
      homeclaw_config_entry.add_to_hass(hass)
      with patch("...ProviderRegistry") as mock_registry:
          await hass.config_entries.async_setup(...)
          yield {...}
  ```

## Coverage

**Requirements:**
- Target: 70% minimum (per `pytest.ini` `--cov-fail-under=70`)
- Fail CI if below: `--cov-fail-under=70` enforced in test run

**View Coverage:**
```bash
pytest tests/ --cov=custom_components/homeclaw --cov-report=term-missing
pytest tests/ --cov=custom_components/homeclaw --cov-report=html  # Open htmlcov/index.html
pytest tests/ --cov=custom_components/homeclaw --cov-report=xml   # For CI integration
```

**Coverage reports:**
- Terminal output: Shows line numbers not covered (term-missing)
- HTML report: `htmlcov/index.html` for interactive exploration
- XML report: `coverage.xml` for CI integration

## Test Types

**Unit Tests:**
- Scope: Single function or class method in isolation
- Mocking: Heavy use of mocks for dependencies
- Speed: Fast (< 100ms per test)
- Location: `tests/test_core/test_response_parser.py` (pure logic)
- Example: Testing ResponseParser.parse() with various input formats

**Integration Tests:**
- Scope: Multiple components working together
- Mocking: Mock only external systems (APIs, file I/O)
- Speed: Medium (100ms - 1s per test)
- Location: `tests/test_rag/test_integration.py`, `tests/test_chat_integration.py`
- Example: Testing agent processing with tool execution

**E2E Tests:**
- Status: Not used in this codebase
- Note: Home Assistant integration tests serve as functional tests instead

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_async_operation(self) -> None:
    """Test async function."""
    result = await async_function()
    assert result == expected
```

Or use async fixture:
```python
@pytest_asyncio.fixture
async def hass(request):
    """Wrap the HA hass fixture with pytest_asyncio."""
    hass_fixture = request.getfixturevalue("hass")
    if hasattr(hass_fixture, "__anext__"):
        hass_instance = await hass_fixture.__anext__()
        yield hass_instance
    else:
        yield hass_fixture
```

**Error Testing:**
```python
# From tests/test_providers/test_base_client.py
def test_build_headers_abstract(self, hass: HomeAssistant) -> None:
    """Test that _build_headers raises NotImplementedError when not implemented."""
    config = {}
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteClient(hass, config)
```

Multiple error expectations:
```python
def test_parse_json_error(self) -> None:
    """Test parsing invalid JSON."""
    parser = ResponseParser()
    result = parser.parse("{invalid json}")
    assert result["type"] == "text"  # Falls back to text
    assert "invalid" in result["content"]
```

**Fixtures with parameters:**
```python
@pytest.fixture
def mock_entities(hass: HomeAssistant):
    """Set up common test entities."""
    hass.states.async_set("light.living_room", "on", {
        "brightness": 255,
        "friendly_name": "Living Room Light",
    })
    hass.states.async_set("light.bedroom", "off", {
        "friendly_name": "Bedroom Light",
    })
    return hass
```

## Test Markers

Available markers (from `pytest.ini`):
- `@pytest.mark.asyncio` - Async test
- `@pytest.mark.unit` - Unit test (not enforced, informational)
- `@pytest.mark.integration` - Integration test (not enforced)
- `@pytest.mark.slow` - Slow running test (can skip with `-m "not slow"`)

Example:
```python
@pytest.mark.slow
@pytest.mark.integration
async def test_full_conversation_flow():
    """Test complete conversation with RAG."""
```

## Key Test Files

**Core logic tests:**
- `tests/test_core/test_agent.py` - Agent orchestrator (MockProvider, MockHass patterns)
- `tests/test_core/test_response_parser.py` - Response parsing for JSON/text
- `tests/test_core/test_token_estimator.py` - Token counting
- `tests/test_core/test_compaction.py` - Message compaction strategy

**Provider tests:**
- `tests/test_providers/test_base_client.py` - HTTP client base class (abstract method testing)
- `tests/test_providers/test_openai.py` - OpenAI provider
- `tests/test_providers/test_gemini.py` - Gemini provider

**RAG system tests:**
- `tests/test_rag/test_query_engine.py` - Query execution
- `tests/test_rag/test_embeddings.py` - Embedding generation
- `tests/test_rag/test_session_indexer.py` - Session indexing

**Integration tests:**
- `tests/test_homeclaw/test_init.py` - Component setup
- `tests/test_chat_integration.py` - Full conversation flow
- `tests/test_lifecycle.py` - Component lifecycle

---

*Testing analysis: 2026-03-20*
