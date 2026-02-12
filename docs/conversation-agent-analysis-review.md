# Walidacja analizy Conversation Agent

Data: 2026-02-12
Status: **ZATWIERDZONO** (z uwagami)

Przeanalizowano dokument `docs/conversation-agent-analysis.md` w kontekście obecnego kodu w `custom_components/homeclaw/`.

## 1. Poprawność Techniczna
**Ocena: WYSOKA**

*   **Stan obecny:** Analiza trafnie diagnozuje brak standardowej integracji (`ConversationEntity`, `manifest.json`, `PLATFORMS`). Potwierdzono w `__init__.py` brak rejestracji platformy `conversation`.
*   **Architektura Homeclaw:** Opis `HomeclawAgent` (wrapper na `core.agent.Agent`) i customowego `ConversationManager` w `core/conversation.py` jest zgodny z kodem.
*   **Streaming:** Potwierdzono, że obecny `Agent.process_query_stream` zwraca słowniki (`{"type": "text", ...}`), co jest niezgodne z oczekiwanym przez HA obiektem `Delta`. Adapter jest niezbędny.

## 2. Referencje i Wzorce
**Ocena: POPRAWNA**

*   Wzorzec "Triple inheritance" jest standardem w HA dla zaawansowanych agentów.
*   Identyfikacja problemu z Tool Calling (custom registry vs HA `llm.API`) jest kluczowa. Podejście hybrydowe (Podejście C) jest najbardziej pragmatyczne, aby nie stracić obecnych funkcjonalności panelu.

## 3. Gap Analysis
**Ocena: KOMPLETNA**

Zidentyfikowano wszystkie krytyczne braki:
*   Brak wpisu w `manifest.json` ("conversation").
*   Brak pliku platformy `conversation.py` (istniejący `core/conversation.py` to manager historii, więc nazwy nie kolidują, ale trzeba uważać przy importach).
*   Niezgodność formatu strumienia danych.

## 4. Plan Implementacji
**Ocena: REALISTYCZNY**

*   **Faza 1 (MVP):** Niezbędna do szybkiego testowania.
*   **Faza 2 (Streaming/Tools):** Najtrudniejsza część. Rekomendacja użycia `_transform_provider_stream` jest słuszna.
*   **Code Reuse:** Należy dopilnować, aby `HomeclawConversationEntity` wywoływała `self.agent.process_query_stream`, a nie reimplementowała logikę wywoływania providerów.

## 5. Ryzyka i Uwagi Krytyczne

1.  **Konflikt Nazw:** Istnieje `custom_components/homeclaw/core/conversation.py` (ConversationManager). Nowy plik to `custom_components/homeclaw/conversation.py` (Platforma). Należy uważać przy importach (używać `from .core.conversation import ConversationManager`).
2.  **Mapping ID:** Należy doprecyzować, jak `conversation_id` z HA będzie mapowane na sesje w Homeclaw. Jeśli Homeclaw nie obsługuje zewnętrznych ID sesji, każda rozmowa z Assist może być traktowana jako nowa lub trafiać do jednego worka "Assist".
3.  **Context Injection:** W planie brakuje szczegółów, jak przekazać kontekst (np. "użytkownik jest w salonie", co HA wie z Assist Pipeline) do `Agent`. Warto dodać to w Fazie 3.

## Rekomendacja
Można przystąpić do implementacji zgodnie z planem.
Sugestia: Rozpocząć od Fazy 1 (rejestracja w UI), co pozwoli zweryfikować poprawność konfiguracji przed wejściem w głęboką wodę streamingu.
