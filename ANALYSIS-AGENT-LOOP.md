# HomeClaw Agent Loop — Analiza i Lista Poprawek

> Porównanie z OpenClaw (open source) — analiza kodu z brancha `fix/agent-loop`
> Data: 2026-02-27 | Autor: LucyStrikeMall 📊

---

## 🔴 KRYTYCZNE — powodują halucynację tooli

### 1. `ResponseParser._extract_json` — fałszywe wykrywanie tool calli

**Problem:** `ResponseParser` szuka **dowolnego JSON-a** w odpowiedzi modelu (nawet wewnątrz tekstu), a `FunctionCallParser` próbuje go zinterpretować jako tool call. Jeśli model wygeneruje np. przykładowy JSON w odpowiedzi tekstowej, zostanie to błędnie rozpoznane jako wywołanie toola.

**Pliki:** `core/response_parser.py`, `core/function_call_parser.py`

```python
# ResponseParser._extract_json — linia problematyczna:
# 3. Try to find JSON object boundaries
json_start = text.find("{")
json_end = text.rfind("}")
# ^ To łapie KAŻDY JSON w tekście, nawet przykładowy!
```

**Jak robi OpenClaw:** Korzysta z `pi-agent-core` (Anthropic SDK) który dostaje tool calle jako **strukturalne obiekty** z API, nie parsowane z tekstu. Tool calls przychodzą jako osobne bloki w odpowiedzi (Anthropic `tool_use`, OpenAI `tool_calls`, Gemini `functionCall` w response parts).

**Fix:**
- Dla providerów ze streaming: używaj natywnych tool call chunks (już to robisz w `process_stream` z `accumulated_tool_calls`)
- Dla non-streaming: parsuj tool calle z response object providera, NIE z tekstu
- `_detect_function_call` powinien być wywoływany TYLKO jako fallback dla providerów bez natywnego tool calling
- Dodaj flagę `provider.supports_native_tool_calls` i omijaj parsowanie tekstu gdy `True`

---

### 2. Brak walidacji czy tool istnieje PRZED próbą wykonania

**Problem:** W `FunctionCallParser._try_simple` każdy JSON z kluczami `function`/`name`/`tool` + `parameters`/`arguments`/`args` jest akceptowany jako tool call. Model może "wymyślić" nieistniejący tool.

**Plik:** `core/function_call_parser.py`

```python
# _try_simple akceptuje dosłownie WSZYSTKO:
name = content.get("function") or content.get("name") or content.get("tool")
args = content.get("parameters") or content.get("arguments") or content.get("args")
if name and isinstance(name, str) and isinstance(args, dict):
    return [FunctionCall(id=name, name=name, arguments=args)]
    # ^ Zero walidacji czy tool "name" faktycznie istnieje!
```

**Jak robi OpenClaw:** Ma `sanitizeToolCallInputs` z whitelistą dozwolonych tool names. Nieznane toole są odrzucane PRZED wykonaniem. Dodatkowo `session-tool-result-guard.ts` waliduje przy persystencji.

**Fix:**
```python
# W FunctionCallParser.detect() — po uzyskaniu function_calls:
from ..tools.base import ToolRegistry

validated = []
for fc in function_calls:
    if ToolRegistry.get_tool_class(fc.name) is not None:
        validated.append(fc)
    else:
        _LOGGER.warning("Rejected hallucinated tool call: %s", fc.name)
return validated if validated else None
```

---

### 3. Anti-halucynacyjny reinforcement jest za słaby i za rzadki

**Problem:** Twój reminder co 5 turnów w `_build_messages`:
```python
enriched_query += (
    "\n\n[SYSTEM REMINDER: Never hallucinate or simulate actions. "
    "You MUST use your tools (function calls) to interact with the system or check state!]"
)
```
To za mało. Po compaction model zaczyna od nowa i nie wie jakie toole ma dostępne.

**Plik:** `core/query_processor.py` (linia ~199)

**Jak robi OpenClaw:** Ma `post-compaction-context.ts` — po każdej kompakcji:
1. Wstrzykuje krytyczne sekcje z AGENTS.md
2. Dodaje explicit `[Post-compaction context refresh]` message
3. Ma `post-compaction-audit.ts` który **weryfikuje** czy agent przeczytał wymagane pliki
4. Jeśli nie — wstrzykuje warning message

**Fix:**
- Po compaction: wstrzyknij system message z pełną listą dostępnych tooli i ich opisami
- Dodaj explicit listę entity domains z HA
- Wstrzykuj co compaction, nie co 5 turnów
- Rozważ wstrzykiwanie nazw tooli w formacie: `Available tools: get_state, call_service, ...`

---

## 🟡 WAŻNE — stabilność agent loop

### 4. Circuit breaker za późno (3 identyczne calle)

**Problem:** Circuit breaker w `ToolExecutor` triggeruje dopiero przy `count >= 3`. To 3 zmarnowane API calle + iteracje.

**Plik:** `core/tool_executor.py` (linia ~77)

**Fix:**
- Zmniejsz próg do `>= 2` (drugi identyczny call = circuit break)
- Dodaj **semantic dedup**: nie tylko identyczne argumenty, ale też ten sam tool z bardzo podobnymi args (np. `get_state("light.bedroom")` vs `get_state("light.bedroom ")`)
- Normalize args przed hashowaniem (strip, lowercase entity_ids, sort keys)

---

### 5. `_recompact_if_needed` — ślepa truncacja tool results

**Problem:** Truncacja do min 200 znaków może wyciąć kluczowe dane z tool results, powodując że model próbuje to samo ponownie (bo nie "widzi" wyniku).

**Plik:** `core/query_processor.py` (linia ~303)

```python
# Obecna logika:
msg["content"] = content[:limit] + "\n... [truncated]"
# ^ Zachowuje TYLKO początek. Model nie widzi końca wyniku.
```

**Jak robi OpenClaw:** `tool-result-truncation.ts` zachowuje head + tail + wyjaśniający sufix. `minKeepChars: 2000`.

**Fix:**
```python
# Head + tail truncation:
half = limit // 2
msg["content"] = (
    content[:half] 
    + "\n\n... [truncated — showing first and last portion] ...\n\n" 
    + content[-half:]
)
```

---

### 6. `ConversationManager` nie wie o tool messages

**Problem:** `Message` dataclass ma `role: Literal["system", "user", "assistant"]`. Brakuje `function`/`tool`. Jeśli `ConversationManager.trim_to_limit()` jest wywoływany, może zgubić pary tool_call/tool_result.

**Plik:** `core/conversation.py`

**Fix:**
- Dodaj `"function"` i `"tool"` do Literal type
- Albo: rozważ usunięcie `ConversationManager` — w `query_processor` i tak operujesz na raw `list[dict]`. Dwutorowość (ConversationManager + raw dicts) to ryzyko desync

---

### 7. `_repair_tool_history` — niekompletna walidacja

**Problem:** Repair nie obsługuje:
- Assistant message z `tool_calls` (list) + tekst jednocześnie
- Gemini `thoughtSignature` (repair może je zgubić przy kopiowaniu)
- Brak whitelisty dozwolonych tool names

**Plik:** `core/query_processor.py` (linia ~237)

**Jak robi OpenClaw:** `session-tool-result-guard.ts` + `session-transcript-repair.ts`:
- `sanitizeToolCallInputs` z `allowedToolNames` whitelist
- `makeMissingToolResult` dla orphanów z explicit error message
- Obsługuje `stopReason: "error"/"aborted"` — nie generuje synthetic results dla przerwanych calli

**Fix:**
```python
def _repair_tool_history(self, messages, allowed_tool_names=None):
    # ...
    if role == "assistant":
        # Filtruj tool calle których nie ma w rejestrze
        if allowed_tool_names:
            for fc in fcs:
                if fc.name not in allowed_tool_names:
                    _LOGGER.warning("Dropped unknown tool call: %s", fc.name)
                    continue
                pending_tool_calls[fc.id] = fc.name
```

---

## 🟢 NICE TO HAVE — poprawa jakości

### 8. `EFFECTIVE_MAX_CONTEXT = 200_000` to za dużo

**Problem:** "Lost in the middle" — modele tracą uwagę na środek kontekstu. 200k tokenów to agresywne nawet dla modeli z 1M+ oknem.

**Plik:** `core/compaction.py` (linia ~37)

**Fix:** Zmniejsz do 100-128k. Testuj z realną konwersacją — lepiej kompaktować częściej niż ryzykować halucynacje.

---

### 9. Brak post-compaction audit

**Problem:** Po compaction model może "zapomnieć" o konfiguracji HA, dostępnych entity, itp. Nie ma mechanizmu weryfikacji.

**Jak robi OpenClaw:** `post-compaction-audit.ts` sprawdza czy agent przeczytał wymagane pliki. Jeśli nie — wstrzykuje warning.

**Fix:** Po compaction wstrzyknij system message z:
- Listą dostępnych domen entity (light, switch, sensor, etc.)
- Top 10 najczęściej używanych entity_id z sesji
- Krytycznymi regułami (np. "zawsze używaj tools, nigdy nie symuluj")

---

### 10. Brak hard cap na tool results przy persystencji

**Problem:** `MAX_TOOL_RESULT_CHARS = 30_000` w ToolExecutor to runtime cap, ale wyniki w historii konwersacji mogą się kumulować (np. 20 tool calli × 30k = 600k znaków).

**Jak robi OpenClaw:** `session-tool-result-guard.ts` z `HARD_MAX_TOOL_RESULT_CHARS` truncuje wyniki **PRZED** zapisem do sesji (persystencja).

**Fix:** Dodaj hard cap w `_repair_tool_history` lub w `_build_messages` przy ładowaniu historii.

---

### 11. `process()` nie robi finalnego zapytania po max iterations

**Problem:** W `process_stream()` po wyczerpaniu iteracji robisz finalne zapytanie bez tooli (model MUSI wyprodukować tekst). Ale w `process()` zwracasz tylko error dict — user nie dostaje żadnej odpowiedzi.

**Plik:** `core/query_processor.py` (linia ~1044)

**Fix:** Skopiuj logikę z `process_stream` — po max iterations zrób jedno ostatnie zapytanie bez tooli.

---

## 📋 Priorytet wdrożenia

| # | Poprawka | Impact | Effort |
|---|---------|--------|--------|
| 1 | Natywne tool calling (nie parsuj JSON z tekstu) | 🔴 Krytyczny | Duży |
| 2 | Walidacja tool names przy detekcji | 🔴 Krytyczny | Mały |
| 3 | Post-compaction tool reinstrukcja | 🔴 Krytyczny | Średni |
| 7 | allowedToolNames w repair | 🟡 Ważny | Mały |
| 5 | Head+tail truncation | 🟡 Ważny | Mały |
| 4 | Circuit breaker threshold → 2 | 🟡 Ważny | Mały |
| 6 | ConversationManager roles | 🟡 Ważny | Mały |
| 11 | Final response w process() | 🟢 Nice | Mały |
| 9 | Post-compaction audit | 🟢 Nice | Średni |
| 10 | Hard cap przy persystencji | 🟢 Nice | Mały |
| 8 | EFFECTIVE_MAX_CONTEXT → 100k | 🟢 Nice | Trivial |

---

## 🏗️ Architektura — co OpenClaw robi fundamentalnie inaczej

1. **Session-based persistence:** OpenClaw zapisuje sesje do JSONL z `session-tool-result-guard` — każdy message jest walidowany przed zapisem. HomeClaw trzyma historię w pamięci (`ConversationManager`) co jest mniej odporne na corrupcję.

2. **Model fallback chain:** OpenClaw ma `runWithModelFallback` — jeśli primary model failuje, automatycznie próbuje fallback. HomeClaw tego nie ma.

3. **Compaction auto-recovery:** OpenClaw automatycznie resetuje sesję gdy compaction failuje lub wykryje corrupcję (role ordering conflicts, Gemini function call ordering bugs). HomeClaw nie ma recovery.

4. **Tool result serialization:** OpenClaw serializuje delivery tool results żeby zachować ordering. HomeClaw może mieć race conditions przy concurrent tool callbacks.

---

*Analiza oparta na: HomeClaw branch `fix/agent-loop` vs OpenClaw `main` (2026-02-27)*
