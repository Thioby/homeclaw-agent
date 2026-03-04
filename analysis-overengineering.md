# Analiza Architektury projektu HomeClaw Agent (ai_agent_ha)

## Podsumowanie
Projekt cierpi na *over-engineering* i posiada liczne nadmiarowe warstwy abstrakcji. Tendencja do mnożenia warstw utrudnia jego utrzymanie i rozwój. Wymagane jest uproszczenie kodu poprzez usunięcie redundancji, konsolidację menedżerów oraz spłaszczenie hierarchii klas.

## Główne obszary wymagające uproszczenia:

### 1. Podwójna warstwa Agenta (Wrappery)
**Problem:** Istnienie `agent_compat.py` (~28KB), który zawiera klasę `HomeclawAgent` pełniącą rolę warstwy kompatybilności dla nowszego agenta z `core/agent.py` (~14KB). To wrapper na wrappera, co znacznie zwiększa narzut poznawczy.
**Rozwiązanie:** Spłaszczenie architektury poprzez połączenie `HomeclawAgent` i `core.agent.Agent` w jedną klasę. Usunięcie starego, nieużywanego API.

### 2. Rozczłonkowanie na Menedżery (Manager Pattern)
**Problem:** W katalogu `managers/` znajduje się 5 różnych menedżerów (`automation_manager.py`, `control_manager.py`, itp.). To powoduje fragmentację logiki i wymusza skomplikowane wstrzykiwanie zależności.
**Rozwiązanie:** Konsolidacja do prostej fasady (np. `HomeAssistantInterface`), wykorzystującej bezpośrednio natywne, asynchroniczne funkcje HA.

### 3. Zdublowana logika konwersacji
**Problem:** Logika rozbita między główny `conversation.py` (~21KB - integracja z HA, transformacja strumieni) a `core/conversation.py` (~4KB - zarządzanie stanem wewnątrz core'a).
**Rozwiązanie:** Przeniesienie zarządzania stanem w jedno miejsce i uproszczenie transformacji strumieni na bezpośrednie funkcje, eliminując skomplikowane wielowarstwowe generatory.

### 4. Monolityczny Procesor Zapytań
**Problem:** Plik `core/query_processor.py` (~40KB) łamie zasadę pojedynczej odpowiedzialności (SRP). Obsługuje pętlę narzędzi, błędy, RAG i formatowanie odpowiedzi.
**Rozwiązanie:** Rozbicie pliku. Wyciągnięcie logiki wykonywania narzędzi do `tool_executor.py`, a logiki RAG do dedykowanego komponentu w `rag/`. `QueryProcessor` powinien pełnić rolę lekkiego koordynatora.

### 5. Przedwczesna optymalizacja ładowania narzędzi
**Problem:** Złożony system ładowania narzędzi (`CORE` vs `ON_DEMAND`) w `agent_compat.py` mający na celu oszczędność tokenów za pomocą heurystyk.
**Rozwiązanie:** Usunięcie heurystycznego ładowania i domyślne ładowanie wszystkich narzędzi. Okna kontekstowe współczesnych modeli są wystarczająco duże, co pozwoli drastycznie skrócić i uprościć kod.
\n## Weryfikacja objawów:
1. **Duplikacja pętli agenta:** Została potwierdzona.
2. **Duplikacja handlerów WS:** Została potwierdzona.
3. **Zbyt gruba warstwa Compat Layer:** Została potwierdzona.
4. **Za duże pliki domenowe (narzędzia):** Została potwierdzona.
