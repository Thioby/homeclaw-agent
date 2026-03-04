# Raport Analizy Halucynacji HomeClaw (Discord Channel)

## 1. Krytyczny błąd: Brak zapisu historii narzędzi (Discord Specific)
Najpoważniejszą przyczyną halucynacji "pomiędzy turami" jest fakt, że kanał Discord **nie zapisuje wywołań narzędzi (`tool_use`) ani ich wyników (`tool_result`) do trwałej pamięci**.

*   **Mechanizm:** W `custom_components/homeclaw/channels/discord/__init__.py`, po otrzymaniu odpowiedzi od AI, zapisywana jest tylko tekstowa treść odpowiedzi (`assistant`). W przeciwieństwie do panelu Web (gdzie wywołuje się `_persist_tool_messages`), Discord całkowicie ignoruje zdarzenia narzędziowe podczas zapisu.
*   **Skutek:** Przy kolejnej wiadomości od użytkownika, historia ładowana z bazy danych zawiera tylko tekst. Model widzi, że "powiedział", iż temperatura wynosi 22°C, ale **nie widzi dowodu**, że faktycznie wywołał narzędzie `get_entity_state`. 
*   **Efekt halucynacji:** Model traci "łańcuch dowodowy". Przy pytaniu "A co z wilgotnością?", nie wie, o jakie urządzenie chodziło wcześniej, i zaczyna zmyślać nazwy encji lub udawać, że "właśnie sprawdził" (hallucinated tool calling), bo nie ma w kontekście realnych wyników z poprzedniej tury.

## 2. Duplikacja ostatniej wiadomości użytkownika (Discord Specific)
Zidentyfikowałem błąd w logice budowania zapytania w kanale Discord, który powoduje, że ostatnia wiadomość użytkownika jest wysyłana do modelu **dwukrotnie** w tej samej turze.

*   **Mechanizm:** `DiscordChannel._process_and_respond` najpierw zapisuje wiadomość użytkownika do bazy, a następnie ładuje historię (która już zawiera tę wiadomość). Potem przekazuje tę samą treść jako `envelope.text` do procesora zapytań, który ponownie dokleja ją na końcu promptu.
*   **Skutek:** Model otrzymuje prompt zakończony dwiema identycznymi wiadomościami użytkownika pod rząd.
*   **Efekt halucynacji:** Powoduje to dezorientację modelu (tzw. *repetitive bias*), co często skłania AI do ignorowania instrukcji systemowych i przechodzenia w tryb "papugowania" lub wymyślania odpowiedzi bez wywoływania narzędzi, aby "szybciej" odpowiedzieć na powtórzone pytanie.

## 3. Stale (nieaktualne) dane z systemu RAG
System HomeClaw używa RAG (Retrieval-Augmented Generation) do sugerowania encji. Niestety, mechanizm ten wstrzykuje do kontekstu fragmenty **starych rozmów**, które zawierają nieaktualne stany urządzeń.

*   **Mechanizm:** `RAGContextRetriever` wyszukuje podobne fragmenty z poprzednich dni. Jeśli użytkownik zapyta o pogodę, RAG może znaleźć wpis z wczoraj: "Asystent: Pogoda to 15°C i pada". Ten fragment jest wklejany do promptu pod nagłówkiem `--- SUGGESTED ENTITIES ---`.
*   **Skutek:** Model widzi tekst "Pogoda to 15°C" jako sugestię. Ponieważ system podpowiada mu te dane jako "istotny kontekst", model często uznaje, że to są aktualne dane i **zmyśla prognozę** na ich podstawie, zamiast wywołać narzędzie pogodowe.
*   **Efekt halucynacji:** "Zmyślanie pogody" i "wymyślanie urządzeń", które kiedyś istniały w historii, ale nie są aktualnie dostępne w narzędziach.

## 6. Mylące przykłady w System Prompcie
W pliku `prompts.py` znajdują się przykładowe dialogi, które uczą model błędnego formatu.

*   **Mechanizm:** Przykład w prompcie brzmi: `- You: [call get_entity_state tool]`. 
*   **Skutek:** Niektóre modele (szczególnie Gemini w trybie Flash lub Claude przy słabszym kontekście) biorą to dosłownie. Zamiast użyć natywnego mechanizmu *Function Calling* (który jest niewidoczny jako tekst dla użytkownika), model wypisuje tekst: "Zaraz sprawdzę: [call get_entity_state tool]". 
*   **Efekt halucynacji:** Użytkownik widzi tekst o wywołaniu narzędzia, ale HomeClaw nie rozpoznaje tego jako prawdziwego wywołania, więc nie wykonuje akcji. Użytkownik ma wrażenie, że "wymysla ze tool calling byl a nie bylo".

## 5. Niewłaściwe mapowanie modeli (Discord fallback)
Discord Channel często wymusza użycie modelu domyślnego dla danego dostawcy, ignorując preferencje użytkownika ustawione w panelu Web.

*   **Mechanizm:** W `_get_or_create_session_id` w kanale Discord, preferencje modelu są pobierane, ale przy tworzeniu sesji używany jest fallback do domyślnego modelu (często Flash).
*   **Skutek:** Modele typu "Flash" są znacznie bardziej podatne na halucynacje narzędziowe niż modele "Pro". Rozmowa przez Discord może odbywać się na słabszym modelu niż ta sama rozmowa w przeglądarce.
