# HomeClaw Agent

A Home Assistant custom component that adds an AI-powered chat panel to your smart home. Talk to your home in natural language — control devices, create automations, build dashboards, and ask about sensor history.

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Features

- **Natural language control** — turn on lights, set thermostats, trigger scenes, all through conversation
- **Multi-provider support** — Gemini, OpenAI, Anthropic, Groq, Meta Llama, z.ai, OpenRouter, and local models (Ollama, LM Studio)
- **Real-time streaming** — token-by-token responses with server-side tool execution
- **RAG system** — semantic search over your entities, automations, and conversation history
- **Long-term memory** — the agent remembers your preferences, decisions, and context across sessions
- **Session management** — multiple chat sessions with full history persistence
- **Identity system** — customize the agent's name, personality, and language
- **Settings UI** — manage providers, models, and defaults from the frontend
- **HACS compatible** — install and update through the Home Assistant Community Store

## Supported Providers

| Provider | Streaming | Function Calling | OAuth |
|----------|-----------|-----------------|-------|
| Google Gemini | Yes | Native | Yes |
| OpenAI / GPT | No | Native | No |
| Anthropic Claude | No | Native | Yes |
| Groq | No | Native | No |
| Meta Llama | No | Native | No |
| z.ai (Zhipu) | No | Native | No |
| OpenRouter | No | Native | No |
| Local (Ollama) | No | Text-based | No |

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu > **Custom repositories**
3. Add `https://github.com/Thioby/homeclaw-agent` as an **Integration**
4. Search for "Homeclaw Agent" and install
5. Restart Home Assistant
6. Go to **Settings > Devices & Services > Add Integration > Homeclaw Agent**

### Manual

1. Copy `custom_components/homeclaw` to your `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration through the UI

## Configuration

After installation, add the integration and select your AI provider. You'll need an API key for cloud providers, or a local endpoint URL for Ollama/LM Studio.

The settings panel (gear icon in the chat) lets you:
- Switch between providers and models
- Edit available models per provider
- Set default provider/model preferences
- Configure RAG (semantic search) on/off
- Customize the agent identity

## Architecture

```
custom_components/homeclaw/
├── __init__.py              # HA setup entry point
├── config_flow.py           # Configuration UI flow
├── storage.py               # Session/message persistence
├── prompts.py               # System prompts and identity
├── core/                    # Orchestration layer
│   ├── agent.py             # Main agent coordinator
│   ├── query_processor.py   # Message building, streaming, tool loop
│   ├── compaction.py        # Context window management
│   └── token_estimator.py   # Token budget calculation
├── providers/               # AI provider implementations
├── tools/                   # Function calling tools
├── managers/                # HA domain managers
├── memory/                  # Long-term memory system
├── rag/                     # Semantic search subsystem
└── frontend/                # Svelte 5 + Vite + TypeScript
```

## Development

### Requirements

- Python 3.12+
- Node.js 18+ (for frontend)
- Home Assistant 2024.1.0+

### Backend

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Linting
black --check custom_components/
isort --check custom_components/
flake8 custom_components/
```

### Frontend

```bash
cd custom_components/homeclaw/frontend/
npm install
npm run dev      # Dev server
npm run build    # Production build
npm run check    # TypeScript check
```

## License

MIT License — see [LICENSE](LICENSE) for details.
