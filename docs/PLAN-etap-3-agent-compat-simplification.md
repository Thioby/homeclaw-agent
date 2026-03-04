# PLAN: Etap 3 - Simplify `agent_compat` (Bez Zmiany Zachowania)

## Cel
Odchudzić warstwę kompatybilności `HomeclawAgent` tak, aby była cienkim facade i nie duplikowała orkiestracji już obecnej w `Agent` / `QueryProcessor`.

## Zakres
- Plik główny: `custom_components/homeclaw/agent_compat.py`
- Powiązane testy:
  - `tests/test_agent_compat.py`
  - testy smoke ścieżek chat/intake jeśli wymagane po refaktorze

Poza zakresem:
- Zmiana publicznego API metod `process_query()` / `stream_query()`
- Zmiana kontraktu eventów, payloadów WS, semantyki tool-calls
- Duży redesign providerów lub lifecycle

## Problem Dzisiaj
- `process_query()` i `stream_query()` przygotowują kontekst różnymi ścieżkami.
- Jest duplikacja logiki: tools, auto-load, context window, memory flush, RAG context, system prompt.
- `agent_compat` zawiera za dużo własnej orkiestracji jak na warstwę kompatybilności.

## Kierunek Refaktoru
1. Ustalić jedno źródło budowania kwargs dla obu trybów (sync/stream).
2. Wspólne helpery przygotowania:
   - tools + auto-load
   - context window + memory flush
   - RAG context
   - system prompt
3. Utrzymać identyczne wyjście API i zachowanie biznesowe.
4. Ograniczyć logikę w `agent_compat` do delegowania i mapowania formatu odpowiedzi.

## Kroki Wdrożenia (Plan)
1. Wydzielić wspólne helpery konfiguracyjne w `agent_compat.py`.
2. Przepiąć `process_query()` i `stream_query()` na wspólną ścieżkę przygotowania.
3. Usunąć lokalne duplikacje i nieużywane fragmenty.
4. Uzupełnić testy jednostkowe tam, gdzie refaktor dotknie pokrycia.
5. Zweryfikować brak regresji na testach celowanych.

## Kryteria Akceptacji
- Brak zmiany publicznego API `HomeclawAgent`.
- Brak zmiany formatu odpowiedzi zwracanego do callerów.
- `process_query()` i `stream_query()` korzystają z jednego, spójnego przygotowania kontekstu.
- Testy przechodzą dla `agent_compat` i ścieżek chat/intake dotkniętych refaktorem.

## Ryzyka
- Różnice w przekazywaniu `system_prompt` vs `system_prompt_override`.
- Niezamierzona zmiana auto-load ON_DEMAND tools.
- Różnice w kolejności/obecności `rag_context` i `attachments`.

## Plan Weryfikacji (Po Implementacji)
1. `python3 -m py_compile custom_components/homeclaw/agent_compat.py`
2. `.venv/bin/python -m pytest tests/test_agent_compat.py -v`
3. `.venv/bin/python -m pytest tests/test_channels/test_intake.py -v`
4. `.venv/bin/python -m pytest tests/test_websocket_api.py -k "send_message or send_stream" -v`

## Status
- **2026-03-04: częściowo zrealizowane (wdrożenie + walidacja testami)**.
- Zaimplementowano wspólną ścieżkę przygotowania kwargs (`build_query_kwargs` + `_add_async_query_context`)
  dla `process_query()` i `stream_query()` bez zmiany publicznego API.
- Usunięto duplikację w `conversation.py`: `_build_stream_kwargs()` deleguje do
  `HomeclawAgent.build_query_kwargs()`.
- Walidacja wykonana:
  - `python3 -m py_compile custom_components/homeclaw/agent_compat.py custom_components/homeclaw/conversation.py`
  - `.venv/bin/python -m pytest tests/test_agent_compat.py -v`
  - `.venv/bin/python -m pytest tests/test_homeclaw/test_conversation.py -v`
  - `.venv/bin/python -m pytest tests/test_channels/test_intake.py -v`
  - `.venv/bin/python -m pytest tests/test_websocket_api.py -k "send_message or send_stream" -v`
- Pozostałe do osobnego etapu (thin-facade cleanup): dalsza ekstrakcja logiki z `agent_compat.py`
  (provider config / prompt builder / auto-load hints / RAG helper) do dedykowanych modułów.
