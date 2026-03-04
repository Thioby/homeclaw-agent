# Przegląd projektu Homeclaw — refaktoryzacja

Data: 2026-02-11
Narzędzie: Gemini 3 Pro Preview (sandbox, YOLO mode)
Zakres: cały `custom_components/homeclaw/` (backend + frontend)

---

## TOP 5 do refaktoryzacji

### 1. EntityManager.filter_entities — optymalizacja (High)

- **Plik:** `managers/entity_manager.py`
- **Problem:** Skanuje `hass.states.async_all()` przy każdym zapytaniu. Na dużej instancji HA (tysiące encji) to bottleneck blokujący event loop.
- **Fix:** Cache per-domena odświeżany na `state_changed` events, lub bezpośrednie look-upy `hass.states.get(entity_id)` zamiast iteracji po wszystkim.

### 2. gemini_oauth.py + hardkodowane sekrety (High)

- **Plik:** `gemini_oauth.py` (root) + `providers/gemini_oauth.py`
- **Problem:**
  - Plik z OAuth utils (PKCE, URL generation) leży luzem w root zamiast w `providers/helpers/`. Mylące nazewnictwo z `providers/gemini_oauth.py` (provider).
  - `CLIENT_ID` i `CLIENT_SECRET` zahardkodowane — Google może je unieważnić, user nie ma kontroli.
- **Fix:**
  1. Przenieść `gemini_oauth.py` do `providers/helpers/oauth.py` lub `providers/gemini_utils.py`.
  2. Dodać pola w `config_flow` (Advanced Options) na własne `Client ID` / `Client Secret`, obecne jako fallback.

### 3. RAGManager to God Object (Medium)

- **Plik:** `rag/__init__.py`
- **Problem:** Robi wszystko: inicjalizację, wyszukiwanie (`get_relevant_context`), indeksowanie sesji, zarządzanie lifecycle, eventy. Za dużo odpowiedzialności.
- **Fix:** Wydzielić:
  - `RAGContextRetriever` — logika budowania kontekstu z encjami
  - `RAGLifecycleManager` — start/stop/reindex
  - `rag/__init__.py` powinien tylko eksportować interfejs

### 4. QueryProcessor za duży (Medium)

- **Plik:** `core/query_processor.py` (~550 linii)
- **Problem:** Miesza logikę biznesową (budowanie promptu, obsługa załączników) z logiką techniczną (parsowanie formatów JSON różnych providerów w `_detect_function_call`).
- **Fix:** Wydzielić parsery odpowiedzi providerów (OpenAI format, Gemini format, Anthropic format) do osobnych klas strategii/adapterów. W `QueryProcessor` zostawić czystą orkiestrację.

### 5. Weryfikacja zależności manifest.json (Low)

- **Plik:** `manifest.json`
- **Problem:** `pypdf` i `croniter` w requirements zwiększają rozmiar instalacji.
- **Status:** Oba są potrzebne:
  - `pypdf` — ekstrakcja tekstu z PDF (file upload)
  - `croniter` — scheduler proaktywny
- **Fix:** Brak akcji — zależności uzasadnione.

---

## Pozostałe znaleziska

### Architektura

- **Ocena: dobra.** Modularny "Slim Orchestrator" pattern.
- Agent (`core/agent.py`) deleguje do specjalistycznych menedżerów i procesorów.
- Jasny podział: `providers/` (API AI), `managers/` (logika HA), `rag/` (baza wiedzy), `core/` (orkiestracja).
- Frontend odseparowany w `frontend/`, budowany jako osobny artefakt.

### Duplikacja kodu

- **Konwersja wiadomości:** `_gemini_convert.py` ma logikę OpenAI->Gemini. Inne providery mają inline konwersję. W przyszłości warto rozważyć abstrakcyjny `MessageConverter`.
- **Mylące nazewnictwo:** `gemini_oauth.py` (root, utils) vs `providers/gemini_oauth.py` (provider) — łatwo pomylić.

### Bezpieczeństwo

- Brak `eval`/`exec` — OK.
- Tool execution zabezpieczony `denied_tools` (frozenset) — OK.
- Walidacja plików w `file_processor.py`: MIME allowlist, path traversal (basename), size limits — OK.
- Hardkodowane sekrety OAuth — do poprawki (punkt 2).

### Performance

- `EntityManager` — główny bottleneck (punkt 1).
- SQLite w RAG (`sqlite_store.py`) — sprawdzić czy nie blokuje event loop. Powinno używać `aiosqlite` lub delegować do executor.
- `file_processor.py` — poprawnie deleguje I/O do `hass.async_add_executor_job()`.

### Spójność kodu

- Styl zgodny z AGENTS.md (Black, isort, type hints, Google docstrings).
- Nazewnictwo klas i metod czytelne i spójne.
- Frontend: Svelte 5 runes, Prettier, konsystentne stores.

### Martwy kod

- `config_flow.py` — importy selektorów do weryfikacji (czy wszystkie użyte w każdym kroku).
- `gemini_oauth.py` (root) — `CLIENT_ID`/`CLIENT_SECRET` zahardkodowane, do przeniesienia.

---

## Pliki do rozbicia (za duże)

| Plik | Linii | Co wydzielić |
|------|-------|-------------|
| `core/query_processor.py` | ~550 | `FunctionCallParser`, strategy pattern per provider |
| `providers/gemini_oauth.py` | ~600 | Logika onboardingu do osobnego helpera |
| `rag/__init__.py` | ~700 | `RAGContextRetriever`, `RAGLifecycleManager` |

---

## Podsumowanie

Projekt jest w dobrej kondycji architekturalnej. Główne ryzyka to performance (`EntityManager`), security (`hardcoded secrets`), i maintainability (God Objects w RAG i QueryProcessor). Żaden z problemów nie jest krytyczny — to wszystko refaktoring poprawiający skalowalność i czytelność.
