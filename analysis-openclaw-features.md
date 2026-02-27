# OpenClaw — Szczegółowa Analiza Featuresów

> Analiza kodu źródłowego OpenClaw pod kątem: session management, compaction,
> conversation persistence, tool execution, streaming, error handling, model fallback.
>
> Data: 2026-02-27 | Autor: LucyStrikeMall 📊
>
> Pliki źródłowe: `src/agents/`, `src/auto-reply/reply/`, `src/config/sessions.ts`
>
> **Uwaga:** Ten plik uzupełnia `ANALYSIS-AGENT-LOOP.md`. Punkty już opisane w tamtym pliku są
> tu pominięte. Skupiam się wyłącznie na nowych obserwacjach.

---

## 🔴 KRYTYCZNE — nowe patterns niekryte przez ANALYSIS-AGENT-LOOP.md

---

### 1. Advanced Tool Loop Detection (trzy detektory)

**Co robi:** `tool-loop-detection.ts` implementuje trzy niezależne detektory pętli narzędziowych:
- `generic_repeat` — ten sam tool + te same argumenty >= 10 razy
- `known_poll_no_progress` — polling tool (`process`, `command_status`) z identycznym **wynikiem** >= 10 razy
- `ping_pong` — naprzemienne wywołania dwóch toolów bez postępu (A→B→A→B→...) >= 10 razy

**Kluczowy mechanizm:** nie porównuje surowych argumentów — używa **SHA256 hasha** stabilnej serializacji (`stableStringify`). Dla poll toolów hashuje wynik (status, exitCode, aggregated), żeby wykryć "no-progress" nawet gdy args są identyczne.

**Poziomy:** warning (10) → critical (20) → global circuit breaker (30). Każdy poziom wysyła inną wiadomość do modelu.

**Plik:** `src/agents/tool-loop-detection.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw ma prosty circuit breaker (`count >= 3` identycznych calli). Nie wykrywa ping-pong, nie wykrywa "same tool, same args, same RESULT = brak postępu". Warto zaimplementować przynajmniej `known_poll_no_progress` — bo HA state tools mogą wracać ten sam stan w kółko (np. `get_state("light.x")` zawsze `"off"`).

**Fix HomeClaw:**
```python
# W tool_executor.py — record outcome hash po każdym toolu:
import hashlib, json

def _stable_hash(tool_name: str, args: dict, result: Any) -> str:
    payload = json.dumps({"tool": tool_name, "args": args, "result": str(result)}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

# W circuit_breaker: sprawdzaj nie tylko args-hash ale args-hash + result-hash
```

---

### 2. Model Fallback z Cooldown Probe Throttling

**Co robi:** `model-fallback.ts` buduje listę kandydatów (primary + fallbacks z config), ale przed
próbą sprawdza **stan auth profile**:
- Jeśli wszystkie profile danego providera są w cooldown z powodu `auth` lub `billing` → **permanentny skip** (nie próbuje nawet)
- Jeśli cooldown z powodu `rate_limit` → może próbować fallbacka w ramach tego samego providera (rate limit bywa model-scoped)
- Primary model: po upływie 30s cooldownu (probe throttle) → jeden próbny request, żeby sprawdzić czy provider wrócił

**Ważna logika:** Context overflow error jest **rethrowowany** i NIE przekazywany do fallbacka — inne modele mogą mieć mniejszy context window i fail jeszcze szybciej.

**Plik:** `src/agents/model-fallback.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw nie ma fallback chain wcale (punkt z ANALYSIS-AGENT-LOOP.md). Ale gdy będzie implementowana, cooldown tracking jest kluczowy dla stabilności — inaczej fallback będzie próbował te same modele bez sensu.

---

### 3. Context Window Guard — blokowanie przed zbyt małym oknem

**Co robi:** `context-window-guard.ts` definiuje dwa progi:
- `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000` — warning
- `CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000` — hard block (agent odmawia uruchomienia)

Rozmiar okna jest resolvowany z: modelsConfig > model.contextWindow > default. Można go dodatkowo
ograniczyć przez `agents.defaults.contextTokens` w konfigu.

**Plik:** `src/agents/context-window-guard.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw używa `EFFECTIVE_MAX_CONTEXT = 200_000` (punkt #8 w tamtym pliku). Brakuje dolnego progu — jeśli model zwróci bardzo małe context window, agent może crash w dziwny sposób. Warto dodać hard minimum check przed uruchomieniem.

---

### 4. Session Write Lock — file-based locking z watchdogiem

**Co robi:** `session-write-lock.ts` tworzy plik `.jsonl.lock` przy każdym zapisie do sesji.
Lock zawiera PID i timestamp. Mechanizmy:
- **Stale lock detection** (domyślnie 30min): jeśli PID z locka nie żyje lub lock za stary → reclaim
- **Watchdog timer** (co 60s): automatycznie zwalnia locki trzymane > 5min (zapobiega wiecznym deadlockom)
- **Reentrant support**: ten sam proces może wielokrotnie acquire tego samego locka (counter)
- **Cleanup on exit**: `SIGINT`, `SIGTERM`, `SIGQUIT`, `SIGABRT` + `process.exit` zwalniają wszystkie locki synchronicznie

**Plik:** `src/agents/session-write-lock.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw trzyma historię w pamięci (`ConversationManager`) — nie ma persystencji pliku więc nie ma problemu z lockami. ALE gdy będzie wdrażana persystencja JSONL (punkt #1 z ANALYSIS-AGENT-LOOP.md), file locking będzie krytyczne. HA może wywoływać agenta z wielu równoległych automations.

---

## 🟡 WAŻNE — nieoczekiwane zachowania i wzorce

---

### 5. Proaktywne Pruning Kontekstu (przed compaction)

**Co robi:** `pi-extensions/context-pruning/pruner.ts` implementuje dwie fazy przycinania
tool results **przed** compaction (żeby w ogóle nie trzeba było compactować):

- **Soft trim** (przy `softTrimRatio` np. 0.7): dla każdego prunowalnego tool resultu zachowuje
  `headChars` z początku + `tailChars` z końca, środek zastępuje `\n...\n`
- **Hard clear** (przy `hardClearRatio` np. 0.85): zastępuje cały tool result placeholderem np.
  `"[tool result cleared to free context]"`

**Ochrony:** nigdy nie przycina przed pierwszą wiadomością user (bootstrap safety), chroni ostatnie
N assistant turns (`keepLastAssistants`), pomija tool results z obrazami.

**Plik:** `src/agents/pi-extensions/context-pruning/pruner.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw kompaktuje gdy wypełni okno (`EFFECTIVE_MAX_CONTEXT`).
Alternatywą/uzupełnieniem jest proaktywne przycinanie starych tool results ZANIM kontekst się
zapełni. Szczególnie przydatne dla HomeClaw bo HA state results mogą być powtarzalne i duże
(np. `get_history` z wieloma punktami danych).

**Pomysł na fix:**
```python
def _proactive_prune_tool_results(self, messages, context_ratio):
    """Przytnij stare tool results gdy kontekst > 70% zapełniony."""
    if context_ratio < 0.70:
        return messages
    # Soft trim: zachowaj head 500 + tail 200 chars dla każdego tool result > 1000 chars
    pruned = []
    for msg in messages:
        if msg["role"] == "tool" and len(str(msg.get("content", ""))) > 1000:
            content = str(msg["content"])
            if context_ratio > 0.85:
                msg = {**msg, "content": "[tool result cleared to free context]"}
            else:
                head, tail = content[:500], content[-200:]
                msg = {**msg, "content": f"{head}\n...\n{tail}"}
        pruned.append(msg)
    return pruned
```

---

### 6. Compaction Safety Timeout

**Co robi:** `compaction-safety-timeout.ts` wrappuje `session.compact()` w timeout 300 sekund.
Jeśli compaction wisi dłużej (LLM nie odpowiada), rzuca błąd zamiast czekać w nieskończoność.

**Plik:** `src/agents/pi-embedded-runner/compaction-safety-timeout.ts`

**Dlaczego ważne dla HomeClaw:** `core/compaction.py` nie ma timeoutu na samą operację
compaction (wywołanie LLM). Jeśli model zawiesi się podczas compaction, agent zawiesi się na zawsze.
Warto dodać:
```python
async with asyncio.timeout(300):  # 5 minut max na compaction
    await self._compact_session()
```

---

### 7. Compaction Safeguard Extension — comprehensywne pre-compaction processing

**Co robi:** `pi-extensions/compaction-safeguard.ts` jest rozszerzeniem wywoływanym **przed**
każdą kompakcją. Robi więcej niż zwykłe `generateSummary`:

1. **Anuluje compaction** jeśli nie ma realnych wiadomości do zsumowania (zapobiega pustej kompakcji)
2. **Historia pruning** przed summarization: jeśli nowe wiadomości zużywają > 50% okna, starsze
   chunki historii są najpierw zsumowane oddzielnie i dropowane, żeby summary się zmieściło
3. **Adaptive chunk ratio** na podstawie rozmiaru wiadomości (nie stały ratio)
4. **Tool failures section**: zbiera do 8 ostatnich błędów narzędziowych (z `isError: true`),
   formatuje jako listę `- tool_name (exitCode=1): error message` i dołącza do summary
5. **File operations**: dołącza listę read i modified plików do summary
6. **AGENTS.md critical context**: ekstraktuje sekcje "Session Startup" i "Red Lines" (max 2000
   znaków) i dołącza jako `<workspace-critical-rules>` do summary
7. **Split turn support**: jeśli compaction tnie w środku tury agenta, prefix jest summaryzowany
   oddzielnie

**Plik:** `src/agents/pi-extensions/compaction-safeguard.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw's `_compact_session()` w `core/compaction.py` robi
proste wywołanie LLM z historią. Nie dołącza informacji o błędach toolów, nie osadza krytycznych
reguł do summary. Po compaction model "zapomina" co się nie udało i jakie mają HA entity.

**Fix priorytetowy:** Do summary compaction dołącz:
- Lista ostatnich błędów narzędziowych (tool_name + error) — model nie będzie próbował tych samych
  podejść po compaction
- Top entity HA używane w sesji (z HA session state)
- Krytyczne reguły (np. "zawsze używaj tools, nigdy nie symuluj")

---

### 8. Per-Session-Type History Limits

**Co robi:** `pi-embedded-runner/history.ts` implementuje `limitHistoryTurns()` — ogranicz
historię do ostatnich N tur użytkownika. Konfigurowalny przez typ sesji:
- DM (`dm` / `direct`): `dmHistoryLimit` per provider, per user override (`dms[userId].historyLimit`)
- Channel/group: osobny `historyLimit`
- Obsługuje thread session keys (`session:channel:123:thread:456` → strip thread suffix)

**Plik:** `src/agents/pi-embedded-runner/history.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw nie ma per-session limits. Wszystkie sesje używają
`EFFECTIVE_MAX_CONTEXT = 200_000`. W długotrwałych sesjach HA (agent sterujący domem przez
godziny) historia rośnie bez ograniczeń aż do compaction. Możliwość konfiguracji "zachowaj tylko
ostatnie 20 tur" byłaby użyteczna.

---

### 9. Compaction Timeout Recovery — snapshot pre-compaction

**Co robi:** `pi-embedded-runner/run/compaction-timeout.ts` śledzi snapshot wiadomości
**przed** uruchomieniem compaction. Jeśli compaction timeout-uje lub failuje w trakcie, można
wrócić do pre-compaction state (zamiast używać potencjalnie uszkodzonego post-compaction state).

```ts
// Jeśli timeout był podczas compaction → użyj pre-compaction snapshot
selectCompactionTimeoutSnapshot({
  timedOutDuringCompaction,
  preCompactionSnapshot,   // <-- zapisany przed compact()
  currentSnapshot,
})
```

**Plik:** `src/agents/pi-embedded-runner/run/compaction-timeout.ts`

**Dlaczego ważne dla HomeClaw:** `core/compaction.py` nie ma rollback mechanizmu. Jeśli
compaction failuje w połowie, `self.messages` może być w niespójnym stanie. Warto przed kompakcją
zapisać snapshot i przywrócić go przy błędzie.

---

### 10. Session Reset po Role Ordering Conflict

**Co robi:** `agent-runner.ts` ma dwa scenariusze reset sesji:

- `resetSessionAfterCompactionFailure`: tworzy nowe `sessionId` (ale zachowuje plik) i próbuje
  dalej — autocompaction po prostu się nie udała, sesja żyje dalej
- `resetSessionAfterRoleOrderingConflict`: **usuwa plik sesji** i tworzy nową — używane gdy
  transcript ma nienaprawialne konflikty kolejności ról (np. Gemini function call ordering bugs)

**Plik:** `src/auto-reply/reply/agent-runner.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw nie ma automatycznego recovery. Gdy `_repair_tool_history`
zawiedzie, sesja jest uszkodzona bez możliwości odratowania. Warto dodać: jeśli N kolejnych prób
repair fail → reset sesji (wyczyść historię, zachowaj session key).

---

### 11. Compaction Plugin Hooks (before/after)

**Co robi:** `compact.ts` wywołuje `hookRunner.runBeforeCompaction()` i
`hookRunner.runAfterCompaction()` — pluginy mogą wykonywać kod wokół kompakcji.
- `before_compaction`: dostaje listę wiadomości do kompakcji, może je analizować/logować
- `after_compaction`: dostaje nową liczbę wiadomości i liczbę tokenów

Wywołania są **fire-and-forget** (nie blokują głównego flow kompakcji).

**Plik:** `src/agents/pi-embedded-runner/compact.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw mogłoby zaimplementować "pre-compaction hook" który
wyciąga z historii ważne entity_ids, service calls, itp. i zapisuje je do pliku kontekstowego
przed kompakcją. Ten kontekst byłby potem wstrzyknięty jako post-compaction context.

---

### 12. Pełny Flow Post-Compaction (Context + Audit + Reminder Guard)

**Co robi:** `agent-runner.ts` po zakończeniu auto-compaction wykonuje sekwencję:

1. **Increment compaction counter** — śledzi ile razy sesja była kompaktowana
2. **Post-compaction context injection** (`readPostCompactionContext`): czyta AGENTS.md,
   ekstraktuje "Session Startup" i "Red Lines" (max 3000 znaków), wysyła jako system event
   do następnej tury agenta z prefixem `[Post-compaction context refresh]`
3. **Pending audit flag** — ustawia `pendingPostCompactionAudits.set(sessionKey, true)`
4. Na **NASTĘPNEJ** turze: czyta ostatnie 100 linii z session JSONL, wyciąga ścieżki plików
   z tool_use bloków gdzie `name === "read"`, sprawdza czy agent przeczytał `WORKFLOW_AUTO.md`
   i daily memory file, jeśli nie → injectuje warning system event

**Plik:** `src/auto-reply/reply/agent-runner.ts`

**Dlaczego ważne dla HomeClaw:** To jest pełna implementacja "post-compaction audit" opisanego
w ANALYSIS-AGENT-LOOP.md — tu widać konkretnie jak jest wykonywana. Audit jest one-shot (usuwa
flagę przed sprawdzeniem → nie ponawia nawet jeśli agent dalej nie przeczyta). HomeClaw mogłoby
zrobić analogiczny mechanizm: po compaction → wstrzyknij listę dostępnych HA entity i domen,
sprawdź w kolejnej turze czy agent użył `get_state` lub `call_service`.

---

### 13. Reminder Commitment Detection (anty-halucynacja przypomnień)

**Co robi:** `agent-runner.ts` wykrywa wzorce w odpowiedzi agenta sugerujące obietnicę
przypomnienia ("I'll remind you", "I'll follow up", "I'll check back in..."), sprawdza czy
agent faktycznie wywołał `cron_tool` w tej turze. Jeśli nie → automatycznie dołącza notatkę:
`"Note: I did not schedule a reminder in this turn, so this will not trigger automatically."`

**Plik:** `src/auto-reply/reply/agent-runner.ts`

**Dlaczego ważne dla HomeClaw:** HomeClaw może mieć analogiczny problem — agent mówi "włączę
światła o 20:00" ale nie wywołuje `call_service` z `schedule`. Można zaimplementować prosty
pattern matcher dla obietnicy akcji HA i sprawdzać czy odpowiedni tool był wywołany.

---

## 🟢 NICE TO HAVE — mniejsze wzorce

---

### 14. Announce Idempotency dla Subagentów

**Co robi:** `announce-idempotency.ts` tworzy unikalny klucz `v1:{childSessionKey}:{childRunId}`
dla ogłoszeń zakończenia subagenta. Zapobiega duplikatom (np. gdy subagent wykona retry i ogłosi
wynik dwa razy).

**Plik:** `src/agents/announce-idempotency.ts`

**Dlaczego ważne dla HomeClaw:** Mniej krytyczne, ale jeśli HomeClaw będzie spawnował "micro-agents"
do konkretnych HA task (np. "sprawdź i napraw klimatyzację"), idempotency klucze zapobiegają
podwójnemu procesowaniu wyników.

---

### 15. Compaction Diagnostics — szczegółowe logi przed/po

**Co robi:** `compact.ts` przy `log.isEnabled("debug")` zbiera i loguje metryki przed i po
kompakcji: liczba wiadomości, znaki tekstu historii, znaki tool results, estimated tokens.
Loguje też top-3 "contributors" (role + znaki + nazwa toola).

**Plik:** `src/agents/pi-embedded-runner/compact.ts`

**Dlaczego ważne dla HomeClaw:** Przy debugowaniu dlaczego agent musi tak często kompaktować,
takie logi byłyby bardzo pomocne. HomeClaw loguje tylko `"Compaction done"`.

---

### 16. Tool Result Context Guard (runtime pre-send truncation)

**Co robi:** `pi-embedded-runner/tool-result-context-guard.ts` + `tool-result-truncation.ts`
implementują dwa poziomy ochrony:
- **Runtime guard** (przed wysłaniem do LLM): truncuje tool results które zajmują > 30% context
  window. Max `HARD_MAX_TOOL_RESULT_CHARS = 400_000` znaków na jeden result.
- **Persistence guard** (`session-tool-result-guard.ts`): truncuje przy zapisie do JSONL używając
  tego samego `HARD_MAX_TOOL_RESULT_CHARS` (ale z innym suffixem informacyjnym)

Oba używają head-only truncation z informatywnym suffixem wskazującym użycie offset/limit.

**Pliki:** `src/agents/pi-embedded-runner/tool-result-truncation.ts`,
`src/agents/session-tool-result-guard.ts`

**Dlaczego ważne dla HomeClaw:** Punkt #5 z ANALYSIS-AGENT-LOOP.md mówi o head+tail truncation —
ale OpenClaw używa HEAD-only z dobrym suffixem. Head+tail jest w Context Pruning (punkt #5 tu),
nie w głównej truncation. HomeClaw powinien wybrać: head-only (jak OpenClaw dla
runtime/persistence) vs head+tail (jak Context Pruning dla proactive pruning). Oba mają
uzasadnienie.

---

## 📋 Priorytet Implementacji (HomeClaw-specific)

| # | Feature | Impact | Effort | Priorytet |
|---|---------|--------|--------|-----------|
| 1 | Tool Loop Detection (ping-pong + no-progress) | 🔴 Krytyczny | Średni | ASAP |
| 7 | Compaction Safeguard (tool failures + HA context w summary) | 🔴 Krytyczny | Średni | ASAP |
| 12 | Pełny flow post-compaction (context + audit) | 🔴 Krytyczny | Mały | ASAP |
| 5 | Proaktywne Context Pruning | 🟡 Ważny | Duży | v2 |
| 6 | Compaction Safety Timeout | 🟡 Ważny | Trivial | ASAP |
| 9 | Compaction Timeout Recovery (snapshot) | 🟡 Ważny | Mały | v2 |
| 10 | Session Reset po role conflict | 🟡 Ważny | Mały | v2 |
| 3 | Context Window Guard (hard min 16k) | 🟡 Ważny | Trivial | ASAP |
| 8 | Per-session history limits | 🟢 Nice | Mały | v2 |
| 11 | Compaction plugin hooks | 🟢 Nice | Duży | v3 |
| 13 | Reminder commitment detection (HA edition) | 🟢 Nice | Mały | v2 |

---

## 🏗️ Kluczowe Wzorce Architektoniczne (nowe obserwacje)

### Compaction Extension Architecture

OpenClaw używa systemu rozszerzeń (`ExtensionAPI`) który hookouje się w cykl życia kompakcji.
`compactionSafeguardExtension` rejestruje handler `session_before_compact` i może:
- Anulować kompakcję (`return { cancel: true }`)
- Modyfikować summary przed zapisem
- Dostać dostęp do `preparation.messagesToSummarize`, `preparation.fileOps`, `preparation.settings`

HomeClaw mógłby zaimplementować analogiczny "kompakcja middleware" pattern:
```python
class CompactionMiddleware:
    async def before_compact(self, messages, context) -> CompactionDecision:
        # Zbierz tool failures, entity stats, etc.
        # Zwróć cancel=True jeśli nie warto kompaktować
        # Albo dodatkowy kontekst do summary
        ...
```

### Trzy-warstwowy Ochrona Kontekstu

OpenClaw ma layered approach do zarządzania kontekstem:
1. **Proactive pruning** (Context Pruning Extension) — trim tool results gdy okno > 70% pełne
2. **Compaction** (główna kompakcja) — gdy okno krytycznie pełne
3. **Persistence guard** (session-tool-result-guard) — hard limit 400k chars przy zapisie

HomeClaw ma tylko warstwę 2 (compaction). Brakuje warstwy 1 i 3.

---

*Analiza oparta na: OpenClaw `main` (2026-02-27)*
*Plik uzupełniający: `ANALYSIS-AGENT-LOOP.md`*
