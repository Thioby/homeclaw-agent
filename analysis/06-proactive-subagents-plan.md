# 06 - Plan: Proaktywnosc + Subagenty dla HomeClaw

Data: 2026-02-10
Status: W trakcie implementacji

## Spis tresci

1. [Porownanie podejsc (PicoClaw vs OpenClaw vs HomeClaw)](#1-porownanie-podejsc)
2. [FAZA 1: Proaktywnosc (Heartbeat + Scheduler)](#2-faza-1-proaktywnosc)
3. [FAZA 2: Subagenty](#3-faza-2-subagenty)
4. [FAZA 3: Integracja i prompty](#4-faza-3-integracja-i-prompty)
5. [Kolejnosc implementacji](#5-kolejnosc-implementacji)
6. [Natywne mechanizmy HA](#6-natywne-mechanizmy-ha)

---

## 1. Porownanie podejsc

### Trzy projekty referencyjne

| Aspekt | PicoClaw (Go) | OpenClaw (TS) | **HomeClaw (plan)** |
|--------|--------------|---------------|---------------------|
| **Heartbeat** | Plikowy `HEARTBEAT.md`, timer co N sekund, callback do agenta | Config per-agent `heartbeat: undefined`, `HEARTBEAT.md` w bootstrap | HA `async_track_time_interval`, dedykowany prompt, wyniki przez `hass.bus.async_fire` |
| **Cron/Scheduler** | `CronService` z plikiem JSON, at/every schedule, agent self-schedules | `cron` tool z akcjami: add/remove/list/run/wake, zintegrowany z gateway | HA Storage persistence + **HA Automations** jako natywny scheduler |
| **Subagent** | `SubagentManager.Spawn()` — goroutine z wlasnym kontekstem LLM, brak narzedzi | `sessions_spawn` — izolowany subagent z ograniczonym promptem (tylko AGENTS.md + TOOLS.md), brak rekursji, concurrency limits (main:3, subagent:2) | `asyncio.create_task`, izolowana instancja `QueryProcessor`, ograniczone tools, wyniki przez events |
| **Persistence** | Pliki JSON w `sessions/` i `cron/jobs.json` | Pliki sesji + SQLite | HA `Store` helpers + istniejacy SQLite |
| **Wyzwalanie** | Go channels (MessageBus) | Gateway RPC | HA event bus + `async_track_time_interval` |
| **Widzialnosc dla usera** | Brak (CLI only) | Brak (plikowe) | **Pelna** (HA Automations UI + panel HomeClaw) |

### Co bierzemy z kazdego projektu

**Z PicoClaw:**
- Koncept heartbeatu jako periodycznego "budzenia" agenta
- Prostota: plik `HEARTBEAT.md` jako zrodlo kontekstu
- Subagent jako goroutine (= `asyncio.create_task`)
- Self-scheduling: agent sam tworzy sobie zadania

**Z OpenClaw:**
- Izolacja subagentow: ograniczony prompt (bez MEMORY, SOUL, IDENTITY), brak rekursji
- Concurrency limits: max N subagentow na raz
- Cron tool z akcjami: status/list/add/remove
- Memory flush przed kompakcja (juz zaimplementowane w HomeClaw)
- Hook system na lifecycle events (do rozszerzenia w przyszlosci)

**Unikalne dla HomeClaw:**
- Wykorzystanie natywnych mechanizmow HA (async_track_time_interval, HA Automations)
- Zaplanowane zadania agenta staja sie standardowymi HA automatyzacjami
- Pelna widzialnosc w HA UI
- Trzy kanaly powiadomien: events + persistent notifications + dedykowana sesja

---

## 2. FAZA 1: Proaktywnosc (Heartbeat + Scheduler)

### 2.1 Nowa struktura katalogow

```
custom_components/homeclaw/proactive/
    __init__.py          # Re-exports
    heartbeat.py         # HeartbeatService
    scheduler.py         # SchedulerService (zarzadzanie jobami)
```

### 2.2 HeartbeatService (`proactive/heartbeat.py`)

**Architektura:**

```
async_at_started(hass, _deferred_start)
    |
    v
async_track_time_interval(hass, _heartbeat_tick, interval)
    |
    v
_heartbeat_tick(now: datetime)
    |-- Sprawdz throttle (nie uruchamiaj jesli user aktywny)
    |-- Zbierz snapshot krytycznych encji
    |-- Buduje HEARTBEAT_PROMPT z aktualnym stanem
    |-- Wybiera providera (pierwszy aktywny z hass.data[DOMAIN]["agents"])
    |-- Wywoluje agent.process_query(heartbeat_prompt, tools=read_only_tools)
    |-- Parsuje odpowiedz JSON: {alerts, observations, actions_taken}
    |-- Jezeli alerts:
    |   |-- hass.bus.async_fire("homeclaw_proactive_alert", data)
    |   |-- persistent_notification.create (krytyczne)
    |   |-- Zapisz do dedykowanej sesji "Proactive Monitor"
    |-- Jezeli observations:
    |   |-- memory_manager.store_memory() (trwale obserwacje)
    |-- Zapisz wynik do historii heartbeatow
    v
Frontend subskrybuje "homeclaw_proactive_alert" event
```

**Kluczowe parametry:**

| Parametr | Domyslna | Opis |
|----------|----------|------|
| `interval_minutes` | 60 | Interwal miedzy heartbeatami |
| `enabled` | False | Domyslnie wylaczony |
| `throttle_if_active_minutes` | 5 | Nie uruchamiaj jesli user byl aktywny w ostatnich N minutach |
| `max_alerts_per_hour` | 5 | Limit alertow (anty-spam) |
| `monitored_domains` | `["sensor", "binary_sensor", "light", "lock", "alarm_control_panel"]` | Domeny do monitorowania |

**Dostep do tools: read-only subset:**
- `get_state` — odczyt stanu encji
- `get_entities_by_domain` — listowanie encji per domena
- `get_areas` — listowanie obszarow
- `memory_search` — wyszukiwanie we wspomnieniach
- `memory_store` — zapisywanie obserwacji

BEZ dostepu do:
- `call_service` — brak mozliwosci sterowania
- `create_automation` — brak tworzenia automatyzacji
- `scheduler` — brak self-scheduling z heartbeatu
- `subagent_spawn` — brak spawnowania subagentow

### 2.3 SchedulerService (`proactive/scheduler.py`)

**Podwojna strategia:**

**Warstwa 1 — Wewnetrzne zadania (async_track_*):**

Dla prostych, programistycznych zadan (heartbeat, reminders):

```python
# Periodyczne (co N minut)
cancel = async_track_time_interval(hass, callback, timedelta(minutes=N))

# Jednorazowe (o konkretnej godzinie)
cancel = async_track_point_in_time(hass, callback, target_datetime)

# Opoznione (za N sekund)
cancel = async_call_later(hass, delay_seconds, callback)
```

**Warstwa 2 — HA Automations (widoczne dla usera):**

Gdy agent sam planuje zadanie (przez scheduler tool), tworzy HA automation:

```yaml
automation:
  alias: "Homeclaw: Sprawdz temperature"
  trigger:
    platform: time_pattern
    hours: "/4"
  action:
    service: homeclaw.run_scheduled_prompt
    data:
      prompt: "Sprawdz temperature we wszystkich pokojach"
      notify: true
```

**Warstwa 3 — Serwisy HA (uzytkownik moze tworzyc automatyzacje sam):**

| Serwis | Opis | Schemat danych |
|--------|------|---------------|
| `homeclaw.run_heartbeat` | Uruchamia heartbeat check manualnie | `{}` |
| `homeclaw.run_scheduled_prompt` | Uruchamia dowolny prompt AI | `{prompt: str, notify: bool, provider?: str}` |
| `homeclaw.check_entities` | Sprawdza encje pod katem anomalii | `{domains?: list[str], filter?: str}` |

**Dataclass ScheduledJob (wewnetrzna warstwa):**

```python
@dataclass
class ScheduledJob:
    job_id: str
    name: str
    enabled: bool
    schedule_type: str           # "interval" | "at" | "cron_expr"
    interval_seconds: int | None # dla "interval"
    run_at: str | None           # ISO datetime, dla "at"
    cron_expression: str | None  # dla przyszlego uzycia
    prompt: str                  # Co agent ma zrobic
    provider: str | None         # Ktory provider (None = domyslny)
    notify: bool                 # Czy powiadamiac usera
    delete_after_run: bool       # Jednorazowe (at)
    created_by: str              # "user" | "agent"
    user_id: str
    # State
    last_run: str | None         # ISO datetime
    next_run: str | None         # ISO datetime
    last_status: str             # "ok" | "error" | "pending"
    last_error: str
    # HA integration
    ha_automation_id: str | None # ID powiazanej HA automation (warstwa 2)
    cancel_callback: Any | None  # Callback do anulowania (warstwa 1)
```

**Persistence:** HA `Store` helper (`Store(hass, "homeclaw_scheduler")`)

### 2.4 Nowe narzedzie: `tools/scheduler.py`

```python
@ToolRegistry.register
class SchedulerTool(Tool):
    id = "scheduler"
    description = "Manage scheduled tasks and reminders."
    category = ToolCategory.HOME_ASSISTANT
    parameters = [
        ToolParameter(name="action", type="string", required=True,
                      enum=["list", "add", "remove", "status"],
                      description="Action to perform"),
        ToolParameter(name="name", type="string", required=False,
                      description="Human-readable job name"),
        ToolParameter(name="prompt", type="string", required=False,
                      description="What the agent should do when the job runs"),
        ToolParameter(name="interval_minutes", type="integer", required=False,
                      description="Run every N minutes (for periodic jobs)"),
        ToolParameter(name="run_at", type="string", required=False,
                      description="ISO datetime for one-shot jobs"),
        ToolParameter(name="job_id", type="string", required=False,
                      description="Job ID (for remove action)"),
        ToolParameter(name="notify", type="boolean", required=False,
                      description="Whether to notify the user (default true)"),
    ]
```

**Przyklady uzycia przez agenta:**

```
User: "Przypomnij mi jutro o 8:00 zeby sprawdzic pogode"
Agent -> scheduler(action="add", name="weather_check",
                   prompt="Sprawdz pogode i powiadom uzytkownika",
                   run_at="2026-02-11T08:00:00", notify=true)

User: "Co 4 godziny monitoruj temperature w piwnicy"
Agent -> scheduler(action="add", name="basement_temp",
                   prompt="Sprawdz sensor.temperature_piwnica. Alert jesli < 5C",
                   interval_minutes=240, notify=true)
```

### 2.5 WebSocket API — nowe komendy

| Komenda | Handler | Opis |
|---------|---------|------|
| `homeclaw/proactive/config/get` | `ws_proactive_config_get` | Pobierz konfiguracje heartbeatu |
| `homeclaw/proactive/config/set` | `ws_proactive_config_set` | Ustaw interwal, toggle on/off |
| `homeclaw/proactive/alerts` | `ws_proactive_alerts` | Lista ostatnich alertow |
| `homeclaw/proactive/subscribe` | `ws_proactive_subscribe` | Subskrypcja real-time alertow |
| `homeclaw/scheduler/list` | `ws_scheduler_list` | Lista zaplanowanych zadan |
| `homeclaw/scheduler/add` | `ws_scheduler_add` | Reczne dodanie zadania |
| `homeclaw/scheduler/remove` | `ws_scheduler_remove` | Usuniecie zadania |

### 2.6 Frontend — nowy komponent

`Settings/ProactiveSettings.svelte` w panelu Settings:
- Toggle: heartbeat on/off
- Slider: interwal (15min - 24h)
- Lista zaplanowanych zadan z mozliwoscia dodawania/usuwania
- Historia alertow proaktywnych

---

## 3. FAZA 2: Subagenty

### 3.1 SubagentManager (`core/subagent.py`)

**Architektura:**

```python
class SubagentManager:
    """Zarzadza subagentami — izolowanymi instancjami agenta."""

    MAX_CONCURRENT_PER_USER = 2
    MAX_ITERATIONS = 5
    TIMEOUT_SECONDS = 120

    async def spawn(self, prompt, label, user_id, session_id, provider=None) -> str:
        """Tworzy nowy subagent task i uruchamia go w tle."""
        # 1. Sprawdz limity concurrency
        # 2. Stworz SubagentTask
        # 3. asyncio.create_task(_run_subagent)
        # 4. Zwroc task_id

    async def _run_subagent(self, task):
        """Wykonuje subagenta z izolowanym kontekstem."""
        # 1. Uzyj istniejacego providera
        # 2. Stworz izolowany QueryProcessor(max_iterations=5)
        # 3. Uzyj SUBAGENT_SYSTEM_PROMPT (minimalny)
        # 4. Ogranicz narzedzia (brak scheduler, spawn, memory_store)
        # 5. Wywolaj process() — NIE stream
        # 6. hass.bus.async_fire("homeclaw_subagent_complete", result)
```

**Izolacja subagenta vs glowny agent:**

| Aspekt | Glowny agent | Subagent |
|--------|-------------|----------|
| System prompt | Pelny (identity + BASE) | `SUBAGENT_SYSTEM_PROMPT` (minimalny) |
| Memory recall | Tak | Nie |
| Memory store | Tak | Nie |
| Scheduler tool | Tak | Nie |
| Subagent spawn | Tak | **Nie** (brak rekursji — jak OpenClaw) |
| HA native tools | Tak | Tak (read-only subset) |
| Web tools | Tak | Tak |
| Max iterations | 20 | 5 |
| Streaming | Tak | Nie (fire-and-forget) |
| Concurrency | — | Max 2 per user |
| Timeout | — | 120s |

### 3.2 Nowe narzedzia

**`tools/subagent.py`:**

```python
@ToolRegistry.register
class SubagentSpawnTool(Tool):
    id = "subagent_spawn"
    description = "Delegate a complex task to a background subagent."
    parameters = [
        ToolParameter(name="task", type="string", required=True,
                      description="Detailed task description for the subagent"),
        ToolParameter(name="label", type="string", required=False,
                      description="Short label for tracking"),
    ]
```

**`tools/subagent_status.py`:**

```python
@ToolRegistry.register
class SubagentStatusTool(Tool):
    id = "subagent_status"
    description = "Check status and results of background subagent tasks."
    parameters = [
        ToolParameter(name="action", type="string", required=True,
                      enum=["list", "get", "cancel"]),
        ToolParameter(name="task_id", type="string", required=False),
    ]
```

### 3.3 SubagentTask dataclass

```python
@dataclass
class SubagentTask:
    task_id: str
    label: str
    prompt: str
    status: str              # "pending" | "running" | "completed" | "failed" | "cancelled"
    result: str | None
    error: str | None
    created_at: float
    completed_at: float | None
    parent_session_id: str
    user_id: str
    provider: str | None
```

### 3.4 Frontend

`Components/SubagentIndicator.svelte`:
- Badge z liczba aktywnych taskow (przy headerze czatu)
- Po kliknieciu: lista z label, status, wynik (skrocony)
- Real-time update przez event subscription (`homeclaw_subagent_complete`)

---

## 4. FAZA 3: Integracja i prompty

### 4.1 Nowe prompty w `prompts.py`

```python
HEARTBEAT_SYSTEM_PROMPT = """You are an autonomous Home Assistant monitor.
Your job is to periodically check the state of the smart home and report anomalies.

INSTRUCTIONS:
1. Review the entity states provided below.
2. Identify any anomalies, risks, or noteworthy changes.
3. Check if any monitored thresholds are exceeded.
4. Report ONLY significant findings.

OUTPUT FORMAT (JSON):
{
  "alerts": [{"severity": "warning|critical", "entity_id": "...", "message": "..."}],
  "observations": [{"message": "...", "worth_remembering": true|false}],
  "all_clear": true|false
}

RULES:
- Do NOT report normal/expected states.
- Use the SAME LANGUAGE as the user's preferred language.
- Be concise. Max 3 alerts, max 3 observations per check.
- Severity "critical" only for safety/security issues (open locks, fire alarms, water leaks).
"""

SUBAGENT_SYSTEM_PROMPT = """You are a focused background subagent for Home Assistant.
Complete the given task independently and return the result.

RULES:
- Be concise and focused on the task.
- You have access to Home Assistant entity data and web tools.
- Do NOT spawn further subagents.
- Do NOT modify device states (read-only access).
- Return your findings in a clear, structured format.
"""
```

### 4.2 Rozszerzenie AgentIdentity

Nowe pola:
```python
proactive_enabled: bool = False
heartbeat_interval_minutes: int = 60
```

SQLite migration: `ALTER TABLE agent_identity ADD COLUMN proactive_enabled ...`

### 4.3 Aktualizacja BASE_SYSTEM_PROMPT

Dodanie sekcji o nowych mozliwosciach:
```
## Background Tasks & Scheduling
- Use `scheduler` tool to create reminders and periodic checks
- Use `subagent_spawn` to delegate complex analysis tasks to background workers
- Scheduled tasks become HA automations visible in the Automations tab
```

---

## 5. Kolejnosc implementacji

| Krok | Opis | Pliki | Zaleznosci |
|------|------|-------|-----------|
| 1 | `proactive/__init__.py`, `heartbeat.py` | Nowe | — |
| 2 | `proactive/scheduler.py` + dataclass `ScheduledJob` | Nowe | — |
| 3 | `tools/scheduler.py` — tool dla agenta | Nowe | Krok 2 |
| 4 | Integracja w `__init__.py` — start/stop + serwisy | Edit | Krok 1-2 |
| 5 | WS handlers: `ws_handlers/proactive.py` | Nowe | Krok 1-2 |
| 6 | `core/subagent.py` — SubagentManager | Nowe | — |
| 7 | `tools/subagent.py` + `tools/subagent_status.py` | Nowe | Krok 6 |
| 8 | Integracja subagent w `__init__.py` | Edit | Krok 6 |
| 9 | Prompty: `HEARTBEAT_SYSTEM_PROMPT`, `SUBAGENT_SYSTEM_PROMPT` | Edit `prompts.py` | — |
| 10 | Rozszerzenie `AgentIdentity` + migracja | Edit `identity_store.py` | — |
| 11 | Frontend: `ProactiveSettings.svelte`, `SubagentIndicator.svelte` | Nowe | Krok 5,7 |
| 12 | Testy: `tests/test_proactive/`, `tests/test_core/test_subagent.py` | Nowe | Krok 1-8 |

**Szacowany rozmiar:** ~1200 LOC Python + ~400 LOC Svelte + ~500 LOC testy

---

## 6. Natywne mechanizmy HA

### Wykorzystywane helpery

| Helper | Uzycie | Import |
|--------|--------|--------|
| `async_track_time_interval` | Heartbeat loop | `homeassistant.helpers.event` |
| `async_track_point_in_time` | One-shot reminders | `homeassistant.helpers.event` |
| `async_track_time_change` | Cron-like (np. "o 8:00 codziennie") | `homeassistant.helpers.event` |
| `async_call_later` | Opoznione wykonanie, retry | `homeassistant.helpers.event` |
| `async_at_started` | Odroczony start heartbeatu | `homeassistant.helpers.start` |
| `Store` | Persistence jobów schedulera | `homeassistant.helpers.storage` |
| `hass.bus.async_fire` | Powiadomienia o alertach | Wbudowane |
| `hass.services.async_register` | Nowe serwisy | Wbudowane |
| `persistent_notification.create` | Krytyczne alerty | Serwis HA |

### Testowanie

```python
from pytest_homeassistant_custom_component.common import async_fire_time_changed

async def test_heartbeat_fires(hass):
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1))
    await hass.async_block_till_done()
    assert heartbeat_mock.call_count == 1
```

---

## Kluczowa przewaga HomeClaw

W porownaniu z PicoClaw (pliki JSON) i OpenClaw (wlasny gateway):

1. **Zaplanowane zadania = HA Automations** — widoczne, edytowalne, zintegrowane
2. **Heartbeat jako serwis HA** — uzytkownik moze go sam triggerowac z dowolnej automatyzacji
3. **Persistent notifications** — krytyczne alerty w natywnym HA UI
4. **Testowalne** — HA test framework z `async_fire_time_changed`
5. **Lifecycle management** — HA sam zarzadza startem/stopem przy restartach
