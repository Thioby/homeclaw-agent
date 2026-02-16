<p align="center">
  <img src="https://brands.home-assistant.io/_/homeclaw/icon@2x.png" alt="HomeClaw" width="128">
</p>

# HomeClaw Agent

AI assistant for Home Assistant. Control your devices, check sensors, build dashboards, create automations — just by chatting. Works with many AI providers and runs as a custom component.

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What it does

You get a chat panel inside Home Assistant. You type what you want, and the AI does it. It knows your devices, rooms, sensors, automations — everything. It can also control them. Like having a smart assistant that actually knows your home.

### Chat with your home

Say things like "turn off the lights in the bedroom" or "what's the temperature outside?" The agent sees all your entities, areas, automations, scenes, and dashboards. If you can do it from the HA UI, you can just ask.

### Conversation Agent for HA Assist

HomeClaw works as a Conversation Agent in Home Assistant. You can set it as your default assistant, use it in Assist pipelines, and talk to it through voice satellites. TTS is also there, but still in beta. It also supports AI Task — give it a JSON schema, get structured data back.

### Many AI providers

Use Gemini, OpenAI, Anthropic, Groq, Llama, z.ai, or OpenRouter. Want to keep things local? Ollama and LM Studio work too. You can switch providers anytime from the settings. Some providers support OAuth — no API key needed.

### Smart search (RAG)

The agent indexes all your entities and past conversations into a local database. When you ask something, it automatically finds the most relevant info. Nothing leaves your machine — everything stays local. Over time, it gets better at understanding what you mean.

### Memory

The agent remembers things between conversations. Your preferences, past decisions, important details — it keeps them and brings them up when needed. You can also tell it to forget something.

### File uploads

Send images, PDFs, CSVs, or text files in the chat. The agent can read documents (up to 10 PDF pages), look at images, and use file content to answer your questions.

### Proactive monitoring

The agent can check your home on a schedule and let you know if something seems wrong. It only reads data — it won't change anything on its own. Alerts are rate-limited so you won't get flooded.

### Scheduler

Set up tasks that run on a schedule — once or repeating. The agent can create them during a conversation, or you can manage them from the UI.

### Web search

When the agent doesn't know something, it can search the web. Good for troubleshooting, finding docs, or answering questions that go beyond your smart home.

### Dashboards and automations

Tell the agent what you want to see and it will build a dashboard for you. You can also ask it to update an existing one — add cards, rearrange things, change layout. Same with automations — describe what should happen and when, and the agent creates the YAML and applies it. No need to dig through the UI yourself.

### Subagents

For bigger tasks, the agent can start other agents that work at the same time. Each one works independently.

### Integration management

The agent can set up simple YAML-based integrations for you — it creates the config and applies it, with automatic backup in case something breaks. For more complex integrations that use a UI flow (like Zigbee2MQTT or Google Home), it can walk you through the process step by step and explain what each option does.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu > **Custom repositories**
3. Add `https://github.com/Thioby/homeclaw-agent` as an **Integration**
4. Search for "Homeclaw Agent" and install
5. Restart Home Assistant
6. Go to **Settings > Devices & Services > Add Integration > Homeclaw Agent**

### Manual

1. Copy `custom_components/homeclaw` to your `config/custom_components/`
2. Restart Home Assistant
3. Add the integration from the UI

## Configuration

After you install, add the integration and pick your AI provider. Cloud providers need an API key. For Ollama or LM Studio, you just need the local URL.

In the settings panel you can:
- Switch providers and models
- Edit model lists
- Set defaults
- Turn RAG on or off
- Change the agent's name, personality, and language

## Development

### Requirements

- Python 3.12+
- Node.js 18+ (for frontend)
- Home Assistant 2024.1.0+

### Backend

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Frontend

Built with Svelte 5, Vite, and TypeScript.

```bash
cd custom_components/homeclaw/frontend/
npm install
npm run dev      # Dev server
npm run build    # Production build
npm run check    # TypeScript check
```

## License

MIT — see [LICENSE](LICENSE) for details.
