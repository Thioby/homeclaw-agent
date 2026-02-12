# Conversation Agent Support - Analysis & Implementation Plan

## Status: ZATWIERDZONA (zobacz: docs/conversation-agent-analysis-review.md)

### Decyzje architektoniczne (ustalone)

- **Session model**: Opcja A - osobne swiaty (Voice i Chat niezalezne), ale Voice zapisuje sesje do Homeclaw
- **Tool calling**: Podejscie B - hybrid (ToolRegistry z `external=True` dla obu interfejsow)
- **Entity model**: Opcja A - jedna ConversationEntity per config entry (provider)

---

## 1. Kontekst

Homeclaw (`custom_components/homeclaw/`) to custom component HA z wlasnym panelem Svelte 5, 10 providerami AI, RAG, tool calling, proactive subsystem. Obecnie dziala **wylacznie** przez wlasny WebSocket API (34 komendy) + custom panel. **NIE jest** zarejestrowany jako Conversation Agent w Home Assistant.

Cel: dodac support jako Conversation Agent, zeby Homeclaw byl dostepny w Assist pipeline, voice assistants, i `conversation.process` service.

---

## 2. Referencyjne implementacje

Zbadano dwa projekty:

### Anthropic (HA core) - `homeassistant/components/anthropic/`

- Triple inheritance: `ConversationEntity` + `AbstractConversationAgent` + `AnthropicBaseLLMEntity`
- `_async_handle_message()` -> `chat_log.async_provide_llm_data()` -> `_async_handle_chat_log()` -> `async_get_result_from_chat_log()`
- Streaming: zawsze, przez `chat_log.async_add_delta_content_stream()` + `_transform_stream()`
- Tool calling: HA `llm.API` (AssistAPI) - automatyczne przez ChatLog
- Config: subentry model (v2), jeden config entry = API key, wiele subentries = agentow
- Platforms: `(Platform.AI_TASK, Platform.CONVERSATION)`

### Extended OpenAI Conversation - `custom_components/extended_openai_conversation/`

- Ten sam triple inheritance pattern
- **Custom tool system**: 7 typow executor (native/script/template/rest/scrape/composite/sqlite)
- Tool calls oznaczone `external=True` -> ChatLog NIE wykonuje ich automatycznie
- Wlasny system prompt z Jinja2 template + exposed entities CSV
- Streaming: zawsze, OpenAI SDK `AsyncStream[ChatCompletionChunk]` -> delta format
- Config: subentry model (v2), migracja z v1
- Platforms: `[Platform.CONVERSATION, Platform.AI_TASK]`

### Wspolny wzorzec architektoniczny

```
conversation.py          -> ConversationEntity (rejestracja agenta)
entity.py                -> BaseLLMEntity (_async_handle_chat_log - LLM call loop)
__init__.py              -> PLATFORMS + async_forward_entry_setups()
```

---

## 3. Porownanie: Homeclaw vs wymagania Conversation Agent

| Element                      | Wymagane                         | Homeclaw (teraz)                    | Status     |
| ---------------------------- | -------------------------------- | ----------------------------------- | ---------- |
| `ConversationEntity`         | tak                              | BRAK                                | DO DODANIA |
| `AbstractConversationAgent`  | tak                              | BRAK                                | DO DODANIA |
| `PLATFORMS`                  | `(Platform.CONVERSATION,)`       | BRAK                                | DO DODANIA |
| `async_forward_entry_setups` | tak                              | BRAK                                | DO DODANIA |
| `"conversation"` w deps      | tak                              | BRAK                                | DO DODANIA |
| `_async_handle_message()`    | tak                              | BRAK (ale ma `Agent.process_query`) | ADAPTER    |
| `ChatLog`                    | tak                              | Wlasny `ConversationManager`        | ADAPTER    |
| `async_set_agent()`          | tak                              | BRAK                                | DO DODANIA |
| Streaming                    | `async_add_delta_content_stream` | Wlasny WS stream                    | ADAPTER    |
| Tool calling                 | HA `llm.API` lub `external=True` | Wlasny `ToolRegistry`               | ADAPTER    |
| Historia rozmow              | HA `ChatLog` + `ChatSession`     | Wlasny `SessionStorage`             | ADAPTER    |
| System prompt                | w `ChatLog.content[0]`           | W `agent_compat.py`                 | RE-USE     |
| Multi-provider               | per entity/subentry              | Per config entry                    | KOMPATYBILNE |

---

## 4. Co Homeclaw ma unikalnego (do zachowania)

1. **Multi-provider** - 10 providerow (OpenAI, Gemini, Anthropic, OpenRouter, Groq, Llama, Z.AI, Local, + OAuth warianty)
2. **Wlasny rich UI** - panel Svelte 5 z sessions, markdown, attachments
3. **RAG subsystem** - semantic search, embeddings, memory
4. **Proactive subsystem** - scheduler, heartbeat, subagent
5. **7 HA services** (query, create_automation, dashboard CRUD, RAG reindex)
6. **34 WebSocket commands** - pelna kontrola z frontendu
7. **Custom tool system** - `ToolRegistry` + `ha_native.py` z entity/automation/dashboard/control managerami

Wszystko powyzsze dziala dalej bez zmian - Conversation Agent to **dodatkowy interfejs**, nie replacement.

---

## 5. Gap Analysis - kluczowe wyzwania

### 5.1 Stream format adapter

Homeclaw providers zwracaja:
```python
{"type": "text", "content": "..."}
{"type": "tool_call", "name": "...", "arguments": {...}}
{"type": "status", "content": "..."}
{"type": "complete", "content": "..."}
```

ChatLog oczekuje delta format:
```python
{"role": "assistant"}
{"content": "..."}
{"thinking_content": "..."}
{"tool_calls": [llm.ToolInput(id=..., tool_name=..., tool_args=..., external=True)]}
```

**Rozwiazanie**: Napisac `_transform_provider_stream()` async generator ktory tlumaczy miedzy formatami.

### 5.2 Tool calling bridge

**DECYZJA: Podejscie B - Hybrid (jak Extended OpenAI)**

Voice **I** Chat uzywaja `ToolRegistry` z `external=True`:
- Tool calls oznaczone `external=True` -> ChatLog NIE wykonuje ich automatycznie
- `HomeclawConversationEntity` wykonuje je sam przez `ToolExecutor`
- Zachowujemy pelna funkcjonalnosc custom tools w obu interfejsach
- Opcjonalnie: mozna TEZ dodac HA intents (AssistAPI) obok custom tools

Odrzucone podejscia:
- ~~Podejscie A (tylko HA llm.API)~~: tracimy custom tools
- ~~Podejscie C (dual mode)~~: Voice nie mialby dostepu do custom tools

Co Voice dostaje dzieki Podejsciu B:
- `get_entities` / `control_entity` - pelna kontrola urzadzen
- `create_automation` / `update_automation` - tworzenie automatyzacji glosem
- `get_dashboard` / `create_dashboard` - dashboard management
- `execute_service` - dowolne HA service calls
- Wszystkie przyszle tools dodane do `ToolRegistry`
- System prompt / osobowosc (re-use `_get_system_prompt()`)
- RAG identity + memory context

### 5.3 Per-provider entity model

**DECYZJA: Opcja A** - jedna `ConversationEntity` per config entry (provider).

User widzi w Assist: "Homeclaw (OpenAI)", "Homeclaw (Gemini)", etc.
1:1 z obecnym modelem config entries (kazdy provider = osobny entry).
Migracja do subentries mozliwa pozniej jako osobny refactor.

### 5.4 Session model: Voice vs Chat

**DECYZJA: Osobne swiaty z voice session persistence**

HA `ChatLog` i Homeclaw `SessionStorage` to fundamentalnie rozne modele:

| Cecha              | Svelte Chat (obecny)               | Voice / Assist (nowy)                            |
| ------------------ | ---------------------------------- | ------------------------------------------------ |
| **Sesje**          | Persistent, 90 dni, JSON na dysku  | In-memory, **5 min timeout**, ginie po restart HA |
| **ID format**      | UUID v4                            | ULID                                             |
| **Historia**       | `SessionStorage` (pelna)           | `ChatLog` (efemeryczna)                          |
| **Kto zarzadza**   | Homeclaw `storage.py`              | HA core `chat_log.py`                            |
| **Przetrwa restart** | Tak                              | Nie                                              |

Rozwiazanie: Voice conversations sa **automatycznie zapisywane** do Homeclaw `SessionStorage`
bezposrednio w `_async_handle_message()` - bez subskrypcji, bez monkey-patchingu:

```python
_async_handle_message(user_input, chat_log):
    user_id = user_input.context.user_id
    conversation_id = chat_log.conversation_id

    # 1. Znajdz lub utworz sesje Homeclaw dla tego conversation_id
    session = get_or_create_voice_session(conversation_id, user_id, provider)

    # 2. Zapisz user message do SessionStorage
    save_message(session_id, role="user", content=user_input.text)

    # 3. Normalny flow: wywolaj provider, streamy, tools...
    ...

    # 4. Zapisz assistant message do SessionStorage
    save_message(session_id, role="assistant", content=response_text)
```

Co user zobaczy w panelu Svelte:
```
Sidebar:
  [chat icon] Rozmowa o oswietleniu          <- z panelu Chat
  [chat icon] Dashboard kuchnia              <- z panelu Chat
  [mic icon]  Voice: Turn on lights          <- z Assist/Voice
  [mic icon]  Voice: What's the temperature  <- z Assist/Voice
```

Sesje voice sa widoczne w panelu (read-only lub kontynuowalne z panelu).
Mapping `conversation_id (ULID)` -> `session_id (UUID)` trzymany w dict w pamieci
+ opcjonalnie w session metadata.

Czego Voice NIE bedzie mial:
- Historii z panelu Chat (kazda rozmowa glosowa zaczyna od zera)
- Attachments (w Voice nie przesylasz plikow)
- Emoji/title generowanie (to feature panelu, ale title moze byc auto-generowany)

---

## 6. Plan implementacji

### Phase 1: Minimum Viable Conversation Agent (~2-3h)

**Cel**: Agent widoczny i dzialajacy w Assist pipeline selector.

1. **`manifest.json`**: dodac `"conversation"` do `dependencies`
2. **`const.py`**: dodac `PLATFORMS = (Platform.CONVERSATION,)`
3. **`__init__.py`**:
   - Import `PLATFORMS`
   - W `async_setup_entry()`: `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`
   - W `async_unload_entry()`: `await hass.config_entries.async_unload_platforms(entry, PLATFORMS)`
4. **Nowy `conversation.py`**:
   ```python
   class HomeclawConversationEntity(
       conversation.ConversationEntity,
       conversation.AbstractConversationAgent,
   ):
       _attr_supports_streaming = True

       async def _async_handle_message(self, user_input, chat_log):
           # 1. Build system prompt (re-use z agent_compat)
           # 2. Set chat_log.content[0] = SystemContent
           # 3. Convert chat_log -> provider messages
           # 4. Call provider (streaming)
           # 5. Feed response through chat_log.async_add_delta_content_stream()
           # 6. Return async_get_result_from_chat_log()
   ```
5. **Test**: agent pojawia sie w Settings > Voice Assistants > Conversation Agent dropdown

### Phase 2: Streaming + Tool Calling (~4-6h)

**Cel**: Pelna funkcjonalnosc z streaming i custom tools.

6. **`_transform_provider_stream()`**: adapter z provider chunk format na ChatLog delta format
7. **ToolRegistry bridge**:
   - Pobranie tools z `ToolRegistry` + skonwertowanie na format providera
   - Tool calls w streamie oznaczone `external=True`
   - Wykonanie tool calls przez `ToolExecutor` (re-use z `core/tool_executor.py`)
   - Wyniki tool calls -> `ToolResultContent` w ChatLog
8. **Tool calling loop**: max 10 iteracji, `chat_log.unresponded_tool_results` jako warunek
9. **System prompt**: re-use `_get_system_prompt()` z `agent_compat.py` + RAG identity context

### Phase 2.5: Voice Session Persistence (~2-2.5h)

**Cel**: Rozmowy z Voice/Assist widoczne w panelu Svelte.

10. **Mapping `conversation_id` -> `session_id`**: dict w pamieci na entity
11. **Auto-create voice session**: `storage.create_session(provider, title="Voice: ...", metadata={"source": "voice"})`
12. **Zapis user message**: `storage.add_message()` przed wywolaniem providera
13. **Zapis assistant message**: `storage.add_message()` po zakonczeniu streamu
14. **Oznaczenie sesji jako "voice"**: pole `source: "voice"` w metadata sesji
15. **UI: badge/ikona "voice" w panelu Svelte**: filtr/label w SessionList (mic icon vs chat icon)

### Phase 3: Polish (~2-4h)

**Cel**: Production-ready experience.

16. **RAG context injection**: wstrzykiwanie RAG context do conversation flow
17. **Error handling**: graceful degradation, ConverseError handling
18. **Supported features**: `ConversationEntityFeature.CONTROL` gdy tools sa dostepne
19. **Device info**: `DeviceInfo` z manufacturer, model (provider name), entry_type=SERVICE
20. **Tests**: unit tests dla conversation entity

### Phase 4: Nice-to-have (opcjonalnie)

21. **AI_TASK platform**: structured data generation (jak Extended OpenAI)
22. **Thinking/reasoning passthrough**: dla modeli z extended thinking (Claude, o1)
23. **Subentry migration**: przejscie na subentry model
24. **Voice session continuation**: kontynuowanie voice session z panelu Chat

---

## 7. Architektura docelowa

```
custom_components/homeclaw/
+-- __init__.py              # + PLATFORMS, forward_entry_setups
+-- manifest.json            # + "conversation" w dependencies
+-- const.py                 # + PLATFORMS constant
+-- conversation.py          # NOWY - HomeclawConversationEntity
|   +-- async_setup_entry()
|   +-- HomeclawConversationEntity
|   |   +-- _async_handle_message()       # glowny entry point
|   |   +-- _transform_provider_stream()  # adapter chunk -> delta format
|   |   +-- _convert_chat_log_to_messages() # ChatLog content -> provider msgs
|   |   +-- _execute_tool_calls()         # ToolRegistry bridge
|   |   +-- _save_voice_message()         # zapis do SessionStorage
|   |   +-- async_added_to_hass / async_will_remove_from_hass
|   +-- helper functions
+-- agent_compat.py          # BEZ ZMIAN - custom panel nadal dziala
+-- core/                    # BEZ ZMIAN
+-- providers/               # BEZ ZMIAN
+-- tools/                   # BEZ ZMIAN
+-- managers/                # BEZ ZMIAN
+-- rag/                     # BEZ ZMIAN
+-- websocket_api.py         # BEZ ZMIAN
+-- storage.py               # BEZ ZMIAN (lub +metadata "source" field)
+-- frontend/                # + voice session badge/icon w SessionList
```

**Kluczowy insight**: To jest **bridge pattern**, nie rewrite.
Conversation Agent to cienka warstwa adaptera nad istniejaca infrastruktura.
Custom panel + WS API + services dzialaja dalej bez zmian.

---

## 8. Ryzyka i mitygacje

| Ryzyko | Prawdopodobienstwo | Mitygacja |
| --- | --- | --- |
| ChatLog format incompatibility z niektorymi providerami | Medium | Fallback do non-streaming (single chunk) |
| Tool format mismatch (ToolRegistry tools vs provider format) | Medium | Konwersja per-provider w `_format_tools()` |
| OAuth providers (Gemini/Anthropic) - token refresh w conversation flow | Low | Re-use istniejacego refresh logic |
| Konflikt nazw: `core/conversation.py` vs nowy `conversation.py` | Low | Rozne sciezki importu (`from .core.conversation` vs `from .conversation`) |
| Performance - podwojny zapis (ChatLog + SessionStorage) | Low | SessionStorage zapis jest async, non-blocking |
| Config entry per provider vs Assist expecting single agent | Low | Kazdy provider = osobny agent w dropdown |
| Voice session flooding (duzo krotkich rozmow) | Low | Session retention policy (90 dni) + opcjonalny auto-cleanup |

---

## 9. Definicja "Done"

### Phase 1
- [ ] Homeclaw pojawia sie jako opcja w Settings > Voice Assistants > Conversation Agent
- [ ] Mozna wybrac konkretny provider (np. "Homeclaw (Gemini OAuth)")
- [ ] `conversation.process` service dziala z Homeclaw agentem (basic response)

### Phase 2
- [ ] Streaming dziala (dla providerow ktore to supportuja)
- [ ] Custom tool calling dziala (entity control, automations, etc. przez Assist)
- [ ] System prompt / osobowosc jest taki sam jak w panelu Chat

### Phase 2.5
- [ ] Rozmowy z Voice/Assist sa widoczne w panelu Svelte
- [ ] Sesje voice maja oznaczenie (ikona/badge) odrozniajace je od sesji chat
- [ ] User message i assistant response sa zapisane w SessionStorage

### Phase 3
- [ ] RAG context jest wstrzykiwany w conversation flow
- [ ] Error handling jest graceful (nie crashuje integracji)
- [ ] Unit tests przechodza

### Niezmienniki (musza dzialac przez caly czas)
- [ ] Istniejacy custom panel dziala bez zmian
- [ ] Istniejace WS API dziala bez zmian
- [ ] Istniejace services dzialaja bez zmian
- [ ] Testy jednostkowe przechodza
