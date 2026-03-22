# Technology Stack

**Analysis Date:** 2026-03-20

## Languages

**Primary:**
- Python 3.12+ - Core integration code for Home Assistant custom component
- Python 3.14 - Current development environment

**Secondary:**
- JavaScript/Node.js - Frontend tooling (bun, OpenCode plugin)
- YAML - Configuration files (Home Assistant manifests, translations)
- JSON - Model configuration, service schemas

## Runtime

**Environment:**
- Home Assistant Core (custom component: `homeclaw`)
- Async/await architecture via asyncio

**Package Manager:**
- pip - Python dependency management
- Lockfile: `requirements.txt` and `requirements-dev.txt` (implicit pinning via manifest)

## Frameworks

**Core:**
- Home Assistant Framework - Integration platform, config entries, storage, websocket APIs
  - `homeassistant.config_entries` - Configuration management
  - `homeassistant.helpers.storage` - Session/data persistence
  - `homeassistant.conversation` - Conversation API integration
  - `homeassistant.core` - HomeAssistant service objects

**Async HTTP:**
- aiohttp 3.8.0+ - Async HTTP client for all external API calls
  - Used by all LLM providers (Gemini, OpenAI, Anthropic, etc.)
  - Discord gateway and REST API communication
  - OAuth token exchange and refresh

**Data & Validation:**
- voluptuous 0.13.1+ - Config schema validation
- pypdf 4.0.0+ - PDF file processing for RAG system

**Async Utilities:**
- croniter 1.3.0+ - Cron expression parsing (proactive task scheduling)

**Testing:**
- pytest 7.3.1+ - Test framework
- pytest-asyncio 0.21.0+ - Async test support
- pytest-cov 4.1.0+ - Coverage reporting
- pytest-homeassistant-custom-component 0.13.0+ - HA component test fixtures
- syrupy 4.0.0+ - Snapshot testing for responses

**Code Quality:**
- flake8 6.0.0+ - Linting
- black 23.1.0+ - Code formatting
- isort 5.12.0+ - Import sorting
- mypy 1.0.1+ - Type checking (lenient configuration)
- bandit 1.7.5+ - Security scanning

**Build/Dev:**
- setuptools (implicit) - Package distribution

## Key Dependencies

**Critical:**
- aiohttp - HTTP communication backbone for all external integrations
- voluptuous - Config schema validation for setup
- pypdf - Document processing for RAG embeddings

**Infrastructure:**
- croniter - Scheduled task management for proactive features
- sqlite3 (stdlib) - Local vector store for RAG embeddings
- json (stdlib) - Model config and message serialization

## Configuration

**Environment:**
- Home Assistant config entry system (`config_flow.py`)
- Environment variables via OAuth flows (refresh tokens, access tokens)
- Local Storage via HA Store API (`storage.py`)

**Config Files:**
- `manifest.json` - Integration metadata, version, dependencies
- `models_config.json` - LLM provider configurations and available models
- `setup.cfg` - flake8, isort, mypy configuration
- `services.yaml` - Service definitions for custom services
- `strings.json` - Localization strings

**Configuration Requirements:**
- AI provider selection (one or more of: gemini_oauth, gemini, anthropic_oauth, anthropic, openai, openrouter, groq, zai, local, alter)
- Provider-specific authentication (API keys or OAuth tokens)
- Optional: RAG (Retrieval-Augmented Generation) enablement
- Optional: Discord bot integration (token + channel/DM policy)
- Optional: Model selection per provider

## Platform Requirements

**Development:**
- Python 3.12 minimum (Home Assistant requirement)
- Home Assistant dev container or local installation
- pip and virtual environment support

**Production:**
- Home Assistant 2024.x+ (version 1.3.1+ of this integration)
- Deployment: Home Assistant supervised/Core/OS with custom component support
- Network: Outbound HTTPS for all LLM provider APIs, Discord, OAuth services

## Database

**Storage:**
- SQLite 3 (no external database required)
  - Location: Home Assistant config directory (`config/.storage/` and RAG directories)
  - Primary use: Session storage, conversation history, embedding cache
  - Vector store: Simple cosine similarity with binary blob embeddings

**Persistence:**
- Home Assistant Store API for user data (encrypted at rest by HA)
- SQLite for RAG embeddings and session chunks

---

*Stack analysis: 2026-03-20*
