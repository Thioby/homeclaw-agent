# Plan Architektury Zarządzania Kontekstem dla ai_agent_ha

## Kontekst i Motywacja
Opierając się na badaniu **LongMemEval (arXiv:2410.10813)** oraz zjawisku "lost in the middle", obecny mechanizm monolitycznej kompresji i wstrzykiwania długiej historii w `ai_agent_ha` ulega refaktoryzacji. Opracowanie udowadnia spadek dokładności o ~30-60% dla długich historii przetwarzanych w jednym prompt-cie bez zaawansowanego retrieval-u.

## Główne Założenia (Nowa Architektura)

### 1. Indexing: Granularność Tur i Multi-Key (Key Expansion)
- **Granularność (Value):** Zamiast całych sesji lub monolitycznych podsumowań, zapisujemy historię w postaci pojedynczych tur rozmowy (Round: User Message + Assistant Response). *(Potwierdzone: optymalne dla QA wg sekcji 4.2 i 5.2).*
- **Rozszerzenie Klucza (Key = Value + Fact):** Zanim tura wypadnie z podręcznej pamięci (Short-Term Memory), LLM dokonuje ekstrakcji "User Facts" (np. preferencje, informacje o domu). Do indeksu wektorowego trafia klucz będący połączeniem oryginalnego tekstu oraz wyekstrahowanych faktów, co radykalnie zwiększa skuteczność Retrievalu *(Potwierdzone: +9.4% Recall, +5.4% QA wg sekcji 5.3).*
- **Timestamping:** Każda tura jest indeksowana ze ścisłym i precyzyjnym znacznikiem czasu.

### 2. Retrieval: Time-Aware Query Expansion
- Mechanizm RAG (Retrieval-Augmented Generation) zostaje wzbogacony o przed-przetwarzanie zapytania.
- Gdy nadchodzi nowe zapytanie od użytkownika, model wykonuje `Query Expansion`, próbując ustalić ramy czasowe z zapytania (np. "wczoraj", "w zeszłym tygodniu" -> `{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}`).
- Wyszukiwanie stosuje hybrydowy filtr: odrzuca tury spoza zakresu czasu, a następnie realizuje wyszukiwanie semantyczne (wektorowe Top-K). *(Potwierdzone: +11.3% precyzji dla temporal reasoning wg sekcji 5.4).*
- **UWAGA ARCHITEKTONICZNA (Wniosek Codex):** Ekstrakcja czasu (`Query Expansion`) musi być realizowana przez **silny model (np. GPT-4o)**. Użycie słabych/szybkich modeli do tego kroku (np. Llama 8B) często skutkuje "false positives" i ucinaniem istotnych danych z wyszukiwania (Dodatek E.4).

### 3. Reading Strategy: Chain-of-Note i Format JSON
- Wyniki zwrócone przez RAG wstawiane są do promptu systemowego w ustrukturyzowanym formacie **JSON**, a nie jako wolny tekst.
- **Chain-of-Note (CoN):** LLM zostaje poinstruowany w prompcie, aby przed udzieleniem odpowiedzi zawsze wygenerował blok "notatek", w którym kopiuje/ekstrahuje potrzebne informacje ze zwróconego JSON-a. Dzięki temu model zyskuje na precyzji czytania długiego kontekstu *(Potwierdzone: wzrost skuteczności o blisko 10 punktów absolutnych wg sekcji 5.5).*

### 4. Egzekwowanie Limitu Kontekstowego (Context Window Budgeting)
- Kanały komunikacji (Discord, Webchat, zadania w tle) są od teraz "stateless" (bezstanowe). Przesyłają do core'a wyłącznie bieżącą wiadomość i `session_id`.
- Moduł budowania promptu (np. `QueryProcessor` / `compaction.py`) wprowadza twardy limit odcięcia starego kontekstu (heurystyka początkowa: **65%**, choć nie jest to wartość ugruntowana naukowo).
- **UWAGA ARCHITEKTONICZNA (Wniosek Codex):** Limit kompresji/odcięcia (np. próg w okolicach 65%) to dobra heurystyka inżynieryjna gwarantująca przestrzeń na output, ale docelowo wartość ta powinna być konfigurowalna (per provider/model). Modele GPT-4o wykazują większą oporność na degradację i mogą skutecznie korzystać z okna wielkości >20k tokenów odzyskanej pamięci, podczas gdy słabsze modele lokalne tracą jakość już powyżej 3k tokenów (sekcja 5.2).

## Kolejność Prac Implementacyjnych (Refaktoryzacja)

1. **`rag/session_indexer.py` i `rag/session_sanitizer.py`**
   - Dodanie do indeksu logiki ekstrakcji faktów ("User Facts") oraz wymuszenie indeksowania na poziomie tury (Round) z dołączonymi datami.
2. **`rag/context_retriever.py`**
   - Implementacja filtra `Time-Aware Query Expansion` z uwzględnieniem kierowania go tylko na potężniejsze instancje modelów, omijając fallback do najmniejszych jednostek.
3. **`prompts.py`**
   - Zmiana szablonów wstrzykiwania historii na format ustrukturyzowany (JSON).
   - Dodanie wymogu Chain-of-Note do promptu systemowego.
4. **`core/compaction.py` i `core/token_estimator.py`**
   - Wyrzucenie monolitycznego podsumowania historii. Zamiast tego odrzucane z limitu kontekstu tury (Round) trafiają prosto jako "Value" do RAG z uruchomieniem równoległym ekstrakcji faktów.
   - Uelastycznienie `COMPACTION_TRIGGER_RATIO` w zależności od Providera (np. 0.65 dla GPT i 0.40 dla małych modeli lokalnych).
5. **`channels/discord/__init__.py` i `ws_handlers/chat.py`**
   - Usunięcie ładowania pełnej historii z kanałów, przekazanie logiki Short-Term Memory na warstwę `ConversationManager`.