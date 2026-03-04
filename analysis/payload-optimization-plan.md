# Plan Optymalizacji Payloadu API — ai_agent_ha

## Kontekst

Analiza 3 kolejnych payloadów Anthropic API wykazała masywny rozmiar requestów (200K+ znaków).
Przyczyny: double-JSON encoding wyników narzędzi, brak kompresji starych tool results w historii,
redundantne opisy narzędzi w system prompcie, trial-and-error rozwiązywanie entity_id.

**Relacja do `context-management-plan.md`**: Ten plan dotyczy **natychmiastowej optymalizacji payloadu**
w ramach pojedynczego requestu. `context-management-plan.md` to strategiczna architektura pamięci
długoterminowej (LongMemEval). Plany są komplementarne — Phase 1-2 można wdrożyć niezależnie,
Phase 4 stanowi fundament mechaniczny pod architekturę z `context-management-plan.md`.

---

## Phase 1: Quick Wins (bez zmiany zachowania)

**Cel**: Redukcja payloadu o ~30-40% przy zerowym ryzyku dla funkcjonalności.
**Szacowane oszczędności**: ~600-2000 tokenów/request.

### 1.1 Naprawa Double-JSON Encoding w ToolExecutor

**Plik**: `core/tool_executor.py:150`

**Problem**: `result_str = json.dumps(result.to_dict())` opakowuje już-JSONowy `output` w drugą
warstwę JSON. LLM widzi:
```json
{"output": "{\"entity_id\": \"light.salon\", \"state\": \"on\"}", "metadata": {...}, "title": null, "success": true, "error": null}
```
Eskejpowany JSON w JSON — ~20-30% narzutu z samego eskejpowania + bezużyteczne pola envelope.

**Fix**:
```python
# Przed (linia ~150):
result_str = json.dumps(result.to_dict())

# Po:
if result.success:
    result_str = result.output  # Już jest JSON stringiem z toola
else:
    result_str = json.dumps({"error": result.error, "tool": fc.name})
```

**Wpływ**: Każdy tool result w konwersacji natychmiast ~20-30% mniejszy.

**Testy**: Zaktualizować `tests/test_core/test_tool_executor.py` — asercje na format wyniku
zmieniają się z envelope na surowy output.

### 1.2 Usunięcie Redundantnych Opisów Narzędzi z System Prompt

**Plik**: `prompts.py` — sekcja "AVAILABLE TOOLS" w `BASE_SYSTEM_PROMPT` (linie ~50-106)

**Problem**: ~2400 znaków tekstowych opisów narzędzi, które duplikują to co jest w strukturalnym
polu `tools` payloadu API. LLM widzi każde narzędzie opisane dwa razy.

**Fix**: Zastąpić verbose blok jednolinijkowym:
```python
# Przed: ~2400 znaków listujących każde narzędzie z opisem
"""
## AVAILABLE TOOLS
- get_entity_state: Get the current state of a Home Assistant entity...
- call_service: Call a Home Assistant service...
[...12+ narzędzi z wieloliniowymi opisami...]
"""

# Po: ~100 znaków
"""
## TOOLS
Use the provided function-calling tools. For additional tools, use load_tool(tool_id).
"""
```

**Wpływ**: ~600 tokenów oszczędności na request.

**Ryzyko**: Niskie. Strukturalne schematy narzędzi już zawierają name, description i parametry.

### 1.3 Usunięcie Metadanych z Tool Results Przed Zapisem do Historii

**Plik**: `ws_handlers/chat.py:270` (gdzie tool results są zapisywane jako content_blocks)

**Problem**: Content blocks przechowują do 10000 znaków per tool result. Przy rekonstrukcji
w `_build_conversation_history()` pełna zawartość trafia do wszystkich przyszłych tur.

**Fix**: Przy zapisie tool result content_block, usunąć pola metadanych niepotrzebne dla LLM:
```python
# W chat.py gdzie tool results są zapisywane:
try:
    parsed = json.loads(result_str)
    if isinstance(parsed, dict) and "output" in parsed:
        result_str = parsed["output"]  # Tylko faktyczny output toola
except (json.JSONDecodeError, TypeError):
    pass  # Zachowaj oryginał jeśli nie JSON
```

**Wpływ**: Usuwa narzut envelope z zapisanej historii. W połączeniu z 1.1 zapobiega
wchodzeniu envelope do systemu w ogóle.

---

## Phase 2: Inteligentne Zarządzanie Wynikami Narzędzi

**Cel**: Redukcja rozmiaru tool results u źródła i szybsze ich starzenie.
**Szacowane oszczędności**: 50-70% redukcji zużycia tokenów przez tool results w konwersacji.

### 2.1 Redukcja Początkowego Limitu Tool Result

**Plik**: `core/tool_executor.py:24`

- **Obecny**: `MAX_TOOL_RESULT_CHARS = 30_000` (~7500 tokenów)
- **Proponowany**: `MAX_TOOL_RESULT_CHARS = 8_000` (~2000 tokenów)

**Uzasadnienie**: 30K znaków to znacznie więcej niż LLM potrzebuje do działania na wyniku narzędzia.
8K wciąż mieści 50 encji z pełnymi metadanymi. Narzędzia z paginacją obsługują `limit/offset`
dla większych zbiorów.

### 2.2 Formatery Wyników Specyficzne dla Narzędzi

**Plik**: `tools/ha_native.py` — wiele klas narzędzi

**Problem**: Każde narzędzie zwraca surowy `json.dumps(result)`. Dla list encji, historii i rejestrów
zawiera verbose pola, których LLM rzadko potrzebuje.

#### `get_entity_state` — Filtrowanie atrybutów
```python
# Obecny: zwraca WSZYSTKIE atrybuty (icon, supported_features, effect_list, itp.)
# Proponowany: whitelist tylko istotnych atrybutów
ESSENTIAL_ATTRS = {
    "friendly_name", "device_class", "unit_of_measurement",
    "state_class", "temperature", "humidity", "current_temperature",
    "hvac_action", "preset_mode", "brightness", "color_temp",
    "media_title", "media_artist", "source", "volume_level",
}
attrs = {k: v for k, v in state.attributes.items() if k in ESSENTIAL_ATTRS}
```
**Oszczędności**: 30-60% per wywołanie entity state.

#### `get_history` — Downsampling + kompaktowy format
```python
# Obecny: tablica {"state": "22.5", "timestamp": "2024-01-15T10:00:00+00:00"}
# Proponowany: kompaktowy format CSV-like
# "22.5@10:00, 22.3@11:00, 22.8@12:00, ..."
def _format_history_compact(entries: list[dict]) -> str:
    if not entries:
        return "No history data"
    pairs = [f"{e['state']}@{e['timestamp'][11:16]}" for e in entries]
    return ", ".join(pairs)
```
**Oszczędności**: ~60-70% — 50-elementowa historia z ~3KB JSON do ~500 znaków.

#### `get_entities_by_domain` / `get_entities_by_area` — Kompaktowe listowanie
```python
# Obecny: tablica {"entity_id": "...", "state": "...", "friendly_name": "...", ...}
# Proponowany: format tabelaryczny
# "light.salon_ceiling | Salon Ceiling | on | Salon"
def _format_entity_list_compact(entities: list[dict]) -> str:
    lines = []
    for e in entities:
        parts = [e["entity_id"], e.get("friendly_name", ""), e.get("state", "")]
        if e.get("area"):
            parts.append(e["area"])
        lines.append(" | ".join(parts))
    return "\n".join(lines)
```
**Oszczędności**: ~50% — eliminuje narzut struktury JSON.

#### `get_weather_data` — Limit dni prognozy
```python
# Obecny: pełna tablica forecast (potencjalnie 14+ dni)
# Proponowany: domyślnie 3 dni, parametr days
forecast = forecast_data[:3]
```

### 2.3 Pozycyjne Starzenie Starych Tool Results

**Plik**: `core/query_processor.py` — `_recompact_if_needed()` (linie ~232-300)

**Obecne zachowanie**: Progresywne skracanie 2000→200 znaków, stosowane jednakowo do wszystkich.

**Proponowane**: Starzenie wg pozycji — starsze tool results bardziej agresywnie skracane:
```python
def _recompact_if_needed(self, messages, budget):
    tool_indices = [i for i, m in enumerate(messages)
                    if m.get("role") in ("tool", "function")]
    total = len(tool_indices)
    for rank, idx in enumerate(tool_indices):
        age_ratio = rank / max(total - 1, 1)  # 0.0 (najstarszy) → 1.0 (najnowszy)
        max_chars = int(200 + (2000 - 200) * (1 - age_ratio))
        content = messages[idx].get("content", "")
        if len(content) > max_chars:
            messages[idx]["content"] = content[:max_chars] + "\n...[truncated]"
```

### 2.4 Jednolinijkowe Podsumowania Bardzo Starych Tool Results

**Plik**: `core/query_processor.py` — nowy helper

Dla tool results starszych niż N tur, zastąpienie treści jednolinijkowym streszczeniem:
```python
def _summarize_old_tool_result(role_name: str, content: str) -> str:
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return f"[{role_name}: returned {len(data)} items]"
        if isinstance(data, dict) and "error" in data:
            return f"[{role_name}: error - {data['error'][:100]}]"
        if isinstance(data, dict) and "state" in data:
            return f"[{role_name}: {data.get('entity_id', '?')} = {data['state']}]"
    except (json.JSONDecodeError, TypeError):
        pass
    return f"[{role_name}: {len(content)} chars]"
```

---

## Phase 3: Lepsza Resolucja Entity ID

**Cel**: Wyeliminowanie wzorca trial-and-error w rozwiązywaniu entity_id (4-6 zbędnych roundtripów).
**Szacowane oszczędności**: 2-6 mniej iteracji narzędzi per złożone zapytanie (4K-30K tokenów).

### 3.1 Nowe Lekkie Narzędzie `resolve_entity`

**Plik**: Nowy `tools/entity_resolver.py`
**Tier**: CORE (zawsze dostępny — na tym polega cały sens)

```python
@ToolRegistry.register
class ResolveEntity(Tool):
    tool_id = "resolve_entity"
    tier = ToolTier.CORE

    async def execute(self, **params) -> ToolResult:
        query = params["query"]
        domain = params.get("domain")
        limit = params.get("limit", 5)

        # Użyj RAG hybrid search (FTS + vector)
        rag_manager = self.hass.data[DOMAIN].get("rag_manager")
        results = await rag_manager.query_engine.hybrid_search(
            query=query,
            where_filter={"domain": domain} if domain else None,
            top_k=limit,
        )

        # Format kompaktowy: entity_id | friendly_name | state | area
        lines = []
        for r in results:
            meta = r.get("metadata", {})
            line = f"{meta['entity_id']} | {meta.get('friendly_name', '?')} | {meta.get('state', '?')}"
            if meta.get("area_name"):
                line += f" | {meta['area_name']}"
            lines.append(line)

        return ToolResult(output="\n".join(lines) if lines else "No matching entities found")
```

**Wpływ**: Zamiast `get_entities_by_domain("sensor") → skanowanie 50 wyników → próba entity_id →
fail → kolejna próba`, LLM wywołuje `resolve_entity("bedroom temperature")` i dostaje
200-znakową odpowiedź z dokładnym ID.

### 3.2 Ulepszone Sugestie Encji RAG w System Prompt

**Plik**: `rag/context_retriever.py` — metoda `get_context()`
**Plik**: `rag/query_engine.py:20` — `MAX_CONTEXT_LENGTH = 2000`

1. **Zwiększyć kontekst RAG** dla zapytań entity-heavy:
   `max_len = 3000 if intent.has_specific_target else 2000`

2. **Zmienić format sugestii** na bardziej bezpośredni:
   ```
   ENTITY MAP (matched from your query):
   sensor.bedroom_temp = "Bedroom Temperature" 22.5°C [Bedroom]
   light.bedroom_lamp = "Bedroom Lamp" on [Bedroom]
   ```

3. **Dodać instrukcję w prompcie**: "If no suggested entity matches, use resolve_entity()
   before trying get_entities_by_domain."

### 3.3 Cache Mapowań Entity ID w Memory

**Plik**: `memory/manager.py` — rozszerzenie `auto_capture.py`

Po udanym `call_service` lub `get_entity_state` wymagającym discovery, zapisać mapowanie:
```python
# W tool_executor.py, po udanym wykonaniu narzędzia:
if fc.name in ("call_service", "get_entity_state"):
    entity_id = exec_params.get("entity_id")
    if entity_id and self._memory_manager:
        await self._memory_manager.store(
            category="entity",
            content=f"Entity '{user_reference}' maps to {entity_id}",
            user_id=user_id,
        )
```

**Wpływ**: Następnym razem gdy użytkownik powie "bedroom temperature", memory recall zawiera:
`[entity] Entity 'bedroom temperature' maps to sensor.smart_temp_humidity_sensor_120027d20d55_temperature`

### 3.4 Pre-resolve Encji w QueryProcessor Przed Pierwszym Wywołaniem LLM

**Plik**: `core/query_processor.py` — `_build_messages()`

Przed wysłaniem do LLM, szybki RAG lookup i wstrzyknięcie kompaktowej mapy encji:
```python
if rag_manager:
    entities = await rag_manager.quick_resolve(user_query, top_k=5)
    if entities:
        entity_map = "\n".join(
            f"  {e['entity_id']} = \"{e['friendly_name']}\" ({e['state']})"
            for e in entities
        )
        system_prompt += f"\n\nMATCHED ENTITIES:\n{entity_map}\n"
```

---

## Phase 4: Przebudowa Zarządzania Historią Konwersacji

**Cel**: Naprawić fundamentalne problemy architektoniczne pozwalające na nieograniczony wzrost kontekstu.
**Szacowane oszczędności**: Zapobiega przekroczeniu budżetu kontekstu niezależnie od długości konwersacji.

> **Uwaga**: Ta faza pokrywa się z `context-management-plan.md` krokami 4 i 5. Zmiany poniżej
> są kompatybilne i mogą służyć jako "mechaniczny fundament" pod architekturę z tamtego planu.

### 4.1 Naprawa Bypassu 500-Wiadomości ze Storage

**Plik**: `ws_handlers/chat.py` — `_build_conversation_history()` i wywołania w liniach ~357-360, ~564-567

**Problem**: Ścieżka streamingowa ładuje WSZYSTKIE wiadomości sesji (do 499 ze storage) i rekonstruuje
pełne pary tool_use/tool_result. Limit 100 wiadomości z `ConversationManager` jest całkowicie ominięty.

**Fix**: Twardy limit na wiadomości ładowane ze storage przed rekonstrukcją:
```python
MAX_HISTORY_MESSAGES = 40  # ~20 tur user/assistant

all_messages = await storage.get_session_messages(session_id)
recent_messages = all_messages[-MAX_HISTORY_MESSAGES:]
conversation_history = await _build_conversation_history(hass, recent_messages)
```

**Dlaczego 40?** Przy `MIN_RECENT_MESSAGES = 8` w compaction i typowych 2 wiadomościach per tool call,
40 wiadomości pokrywa ~10 ostatnich interakcji z pełnym detalem. Starsze są już podsumowane.

**Alternatywa** (zgodna z `context-management-plan.md`): Kanały stateless — przekazują tylko
`session_id`, `QueryProcessor` decyduje ile wiadomości załadować, używając RAG turn-level index
dla starszego kontekstu.

### 4.2 Liczenie Schematów Narzędzi w Budżecie Tokenów

**Plik**: `core/token_estimator.py` — `estimate_messages_tokens()`
**Plik**: `core/query_processor.py` — `_build_messages()`

**Problem**: Budżet tokenów (`available = context_window - output_reserve - safety`) liczy tylko
treść wiadomości. Schematy narzędzi (28 tools × ~200 tokenów = ~5600 tokenów) są niewidoczne
dla estymatora.

**Fix**:
```python
# W token_estimator.py:
def estimate_tools_tokens(tools: list[dict]) -> int:
    if not tools:
        return 0
    tools_str = json.dumps(tools)
    return estimate_tokens(tools_str)

# W query_processor.py _build_messages():
tools_tokens = estimate_tools_tokens(effective_tools)
available_for_messages = available_budget - tools_tokens
```

### 4.3 Atomowe Pary Tool-Call w Compaction

**Plik**: `core/compaction.py` — `truncation_fallback()` (linie ~272-334)

**Problem**: Truncation fallback usuwa wiadomości indywidualnie, co może rozdzielić `assistant`
tool_use od `function` tool_result. Powoduje "Gemini loop" bug.

**Fix**: Grupowanie tool_use/tool_result jako atomowe pary:
```python
def _group_messages_into_blocks(messages):
    blocks = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg.get("role") == "assistant":
            block = [msg]
            j = i + 1
            while j < len(messages) and messages[j].get("role") in ("function", "tool"):
                block.append(messages[j])
                j += 1
            blocks.append(block)
            i = j
        else:
            blocks.append([msg])
            i += 1
    return blocks
```

Zgodne z wnioskiem z `gemini_investigation/research_findings.md:49`:
> "any context management MUST treat an assistant (tool call) and its subsequent function (tool results)
> as a single, atomic, indivisible block"

### 4.4 Współczynniki Compaction Specyficzne dla Providera

**Plik**: `core/compaction.py:37` — `COMPACTION_TRIGGER_RATIO`

**Obecny**: Uniwersalny 80% trigger, 128K domyślny kontekst.
**Proponowany**: Konfiguracja per-provider:
```python
PROVIDER_BUDGETS = {
    "anthropic": {"trigger_ratio": 0.75, "chars_per_token": 3.5},
    "anthropic_oauth": {"trigger_ratio": 0.75, "chars_per_token": 3.5},
    "openai": {"trigger_ratio": 0.80, "chars_per_token": 4.0},
    "gemini": {"trigger_ratio": 0.80, "chars_per_token": 4.0},
    "gemini_oauth": {"trigger_ratio": 0.80, "chars_per_token": 4.0},
    "local": {"trigger_ratio": 0.60, "chars_per_token": 4.0},
}
```

**Uzasadnienie** (zgodne z `context-management-plan.md` krok 4): Anthropic potrzebuje niższego triggera
bo tokenizer produkuje więcej tokenów per znak dla JSON. Lokalne modele wymagają jeszcze bardziej
agresywnej compaction z powodu małych okien kontekstowych.

### 4.5 Oddzielne Storage Wyników Narzędzi od Treści Wyświetlanych

**Plik**: `ws_handlers/chat.py` — storage content_blocks
**Plik**: `storage.py` — dataclass `Message`

**Problem**: Tool results w `content_blocks` służą dwóm celom:
1. **Wyświetlanie** we froncie (user widzi detale wykonania narzędzia)
2. **Kontekst** dla kolejnych wywołań LLM (rekonstrukcja historii)

Mają różne wymagania rozmiarowe.

**Fix**: Dodanie pola `compact_content` do content_blocks:
```python
content_block = {
    "type": "tool_result",
    "tool_id": fc.name,
    "tool_use_id": tool_use_id,
    "content": result_str,                                  # Pełny dla frontu
    "compact_content": _compact_result(result_str, fc.name),  # Max 500 znaków dla LLM
}
```

`_build_conversation_history()` używa `compact_content` (jeśli dostępny) zamiast `content`
przy rekonstrukcji wiadomości dla LLM.

---

## Podsumowanie: Mapa Implementacji

| Phase | Zmiany | Modyfikowane pliki | Est. oszczędności | Ryzyko |
|-------|--------|--------------------|-------------------|--------|
| **1** | Double-JSON fix, strip envelope, usunięcie redundantnych opisów | `tool_executor.py`, `prompts.py`, `ws_handlers/chat.py` | ~600-2000 tok/req | **Niskie** |
| **2** | Redukcja capów, formatery per-tool, pozycyjne starzenie | `tool_executor.py`, `ha_native.py`, `query_processor.py` | ~50-70% tool results | **Średnie** |
| **3** | `resolve_entity` tool, ulepszone RAG injection, entity caching | Nowy `entity_resolver.py`, `context_retriever.py`, `memory/manager.py` | 4K-30K per złożone zapytanie | **Średnie** |
| **4** | Fix 500-msg bypass, liczenie schematów, atomowe pary, dual storage | `ws_handlers/chat.py`, `token_estimator.py`, `compaction.py`, `storage.py` | Zapobiega nieogr. wzrostowi | **Wyższe** |

### Sugerowana kolejność wykonania

1. Phase 1 (najbezpieczniejsza, natychmiastowy wpływ)
2. Phase 2 (wymaga testowania formatów output ze wszystkimi providerami)
3. Phase 4.1-4.2 (fix 500-msg bypass i liczenie schematów — szybkie zmiany strukturalne)
4. Phase 3 (nowa funkcjonalność, wymaga najwięcej testów)
5. Phase 4.3-4.5 (głębsze zmiany architektoniczne, najlepiej razem z `context-management-plan.md`)
