# PLAN: Diagnostic Tools — Shell, Supervisor API, Python IO

**Data:** 2026-02-18 (rev2: 2026-02-18 — post-review fixes, rev3: 2026-02-18 — 3-tool strategy)
**Status:** Plan zatwierdzony, implementacja pending
**Autorzy:** @master-of-disaster-rlm (orchestrator), @architect-rlm, @planner-rlm, @brainstorm-rlm

### Changelog (rev3)

| # | Severity | Uwaga | Fix |
|---|----------|-------|-----|
| 7 | ARCHITEKTURA | Analiza mechanizmów dostępu: `self.hass` Python API vs Supervisor REST vs Shell vs asyncio — żaden pojedynczy mechanizm nie pokrywa wszystkich use case'ów | Strategia 3 tooli: `safe_shell_execute` + `supervisor_api` + `safe_file_read` (Python IO) |
| 8 | ARCHITEKTURA | `ping`, `traceroute`, `dig`, `ps aux` — niedostępne przez żadne API, wymagają subprocess | Potwierdza potrzebę shell toola jako niezastąpionego dla diagnostyki sieciowej/systemowej |
| 9 | ARCHITEKTURA | HA Core logs, addon logs — niedostępne przez `self.hass` ani shell, tylko Supervisor REST | `supervisor_api` tool jako równoległy priorytet (nie "przyszły") |

### Changelog (rev2)

| # | Severity | Uwaga z review | Fix |
|---|----------|----------------|-----|
| 1 | WYSOKIE | `ha` CLI niedostępne z procesu HA Core (działa w osobnym kontenerze) | Usunięto `ha` z allowlist shell. Dodano osobny `SupervisorApiTool` używający REST API |
| 2 | WYSOKIE | `communicate()` buforuje cały output w pamięci przed truncation | Zmieniono na streaming read z limitem bajtów (`proc.stdout.read(MAX)`) |
| 3 | WYSOKIE | LLM łatwo obchodzi two-call confirm (sam ustawia `confirm=true`) | Usunięto parametr `confirm`. Wszystkie NEEDS_CONFIRM → REJECTED w MVP. Confirmation dopiero z frontendem |
| 4 | ŚREDNIE | Niespójności: Path.resolve() raz w MVP raz nie; sed/awk walidowane ale nie na allowliście | Ujednolicono: Path.resolve() w MVP. Usunięto sed/awk z argument sanitization (nie ma ich na allowliście) |
| 5 | ŚREDNIE | Brak `safe_shell_execute` w denied_tools heartbeat/subagent | Dodano jawny krok: dodać do `HEARTBEAT_DENIED_TOOLS` i `DENIED_TOOLS` |
| 6 | ŚREDNIE | `docker inspect` leakuje secrets; pattern `key` w nazwie pliku = false positives | Usunięto docker z allowlist. Zawężono blocked filename patterns do precyzyjnych |

---

## 1. Podsumowanie

Nowy tool `safe_shell_execute` dla Homeclaw AI agenta — umożliwia wykonywanie **read-only komend shell** na hoście Home Assistant w celach diagnostycznych i debugowania. Jest to **najniebezpieczniejszy tool w systemie** — security-first design jest absolutnym priorytetem.

### Cel

Dać agentowi AI możliwość:
- Sprawdzania stanu systemu (`df -h`, `free -h`, `uptime`, `ps`)
- Przeszukiwania konfiguracji (`grep`, `jq`)
- Inspekcji plików (`cat`, `ls`, `head`, `tail`)

> **⚠️ WAŻNE (rev2):** Komenda `ha` CLI **NIE jest dostępna** z procesu HA Core.
> HA Core działa w kontenerze Docker, a `ha` CLI to osobny binary w kontenerze CLI.
> Logi i info HA są dostępne przez **Supervisor REST API** (`http://$SUPERVISOR/core/logs`
> z Bearer `$SUPERVISOR_TOKEN`). Dla tych operacji planujemy osobny tool `supervisor_api`
> (patrz sekcja 3 i 4.1), NIE subprocess shell.

### Czego NIE robi
- Nie modyfikuje plików (no write)
- Nie restartuje usług
- Nie instaluje pakietów (no `apt`, `pip`)
- Nie ma dostępu do sieci (no `curl`, `wget`)
- Nie eskaluje uprawnień (no `sudo`, `su`)
- **Nie wywołuje `ha` CLI** (niedostępne w kontenerze HA Core — patrz sekcja 3 i 4.1)

---

## 2. Decyzje architektoniczne (do podjęcia przed implementacją)

### Decyzja 1: Architektura toola

| Opcja | Opis | Zalety | Wady |
|-------|------|--------|------|
| **A: Shell only z lockdown** | Jeden tool `safe_shell_execute` z allowlist/blocklist | Prosty, elastyczny | Ryzykowny, kruchy blocklist |
| **B: Structured API only** | Dedykowane toole: `get_ha_logs()`, `read_config()`, `get_system_info()` | Najbezpieczniejszy | Mniej elastyczny, więcej kodu |
| **C: Hybrid (rekomendowany)** | Structured API (Tier 1) + guarded shell fallback (Tier 2) | Best of both worlds | Dwa systemy do utrzymania |

**Rekomendacja:** Opcja **A na start (MVP)**, z migracją do C w przyszłości. Powód: szybki feedback loop, a structured API tools można dodawać inkrementalnie.

### Decyzja 2: Model potwierdzenia

| Opcja | Opis |
|-------|------|
| **A: Tiered (rekomendowany)** | SAFE commands (ha logs, df, uptime) → bez potwierdzenia. NEEDS_CONFIRM (cat, grep) → LLM musi zapytać usera |
| **B: Always confirm** | Każda komenda wymaga potwierdzenia |
| **C: Never confirm** | Wszystko auto-execute (niebezpieczne) |

**Rekomendacja:** Opcja **A** — two-call pattern (patrz sekcja 8).

### Decyzja 3: Scope instalacji HA

> **⚠️ rev2:** `ha` CLI NIE jest dostępne z procesu HA Core w ŻADNYM typie instalacji.
> HA Core działa jako `python3 -m homeassistant` w kontenerze bez `ha` binary.
> Supervisor API jest dostępny przez HTTP (`$SUPERVISOR` env var) z Bearer tokenem.

| Typ instalacji | Supervisor API | Shell tools w kontenerze | Rekomendacja |
|----------------|---------------|--------------------------|--------------|
| HA OS | ✅ (HTTP) | BusyBox (ograniczone) | ✅ Shell + Supervisor API |
| HA Container | ✅ (HTTP) | Zależy od image | ⚠️ Shell + Supervisor API |
| HA Core (venv) | ❌ (brak Supervisora) | Full GNU (host) | ⚠️ Tylko shell |
| HA Supervised | ✅ (HTTP) | Full GNU (host) | ✅ Shell + Supervisor API |

**Rekomendacja:** MVP targetuje **HA OS** (najpopularniejszy). Shell tool dla komend systemowych, osobny Supervisor API tool dla logów/info HA.

### Decyzja 4: Obsługa secrets

**Rekomendacja:** Hard-block paths zawierających secrets. Lista zablokowanych:
- `/config/secrets.yaml`
- `/config/.storage/` (cały katalog — tokeny, hashe haseł)
- `/config/.cloud/` (Nabu Casa tokeny)
- `/ssl/` (certyfikaty TLS)
- Pliki z `secret`, `token`, `password`, `key`, `credential` w nazwie
- `/proc/self/environ` (env vars z tokenami)

### Decyzja 5: Format outputu

**Rekomendacja:** Structured JSON w ToolResult metadata:
```json
{
  "stdout": "...",
  "stderr": "...",
  "exit_code": 0,
  "duration_ms": 142,
  "truncated": false
}
```

---

## 3. Analiza mechanizmów dostępu do danych (rev3)

### 3.0 Jak działają obecne `ha_native` tools

Obecne toole (20 szt.) działają **wyłącznie przez in-process Python API** — tool jest
częścią procesu HA Core i ma bezpośredni dostęp do obiektów w pamięci:

| Mechanizm | API | Przykład z kodu | Co daje |
|-----------|-----|-----------------|---------|
| **State Machine** | `self.hass.states.get(entity_id)` | `GetEntityState.execute()` | Stan entity (state + attributes + last_changed) |
| | `self.hass.states.async_all()` | `GetEntitiesByDomain.execute()` | Wszystkie entity w systemie |
| | `self.hass.states.async_all("scene")` | `GetScenes.execute()` | Entity filtrowane po domenie |
| **Registries** | `er.async_get(hass)` | `GetEntityRegistry.execute()` | Entity metadata (disabled, area_id, device_id) |
| | `dr.async_get(hass)` | `GetDeviceRegistry.execute()` | Urządzenia (manufacturer, model, area) |
| | `ar.async_get(hass)` | `GetAreaRegistry.execute()` | Pokoje/strefy (name, floor, labels) |
| **Service calls** | `self.hass.services.async_call(...)` | `CallService.execute()` | Sterowanie urządzeniami |
| | `async_call(..., return_response=True)` | `GetCalendarEvents.execute()` | Serwisy zwracające dane |
| **Recorder** | `get_instance(hass).async_add_executor_job(...)` | `GetHistory.execute()` | Historia stanów z SQLite |

**Żaden z istniejących tools NIE używa:** subprocess, HTTP requests, file I/O, Supervisor API.

### 3.0.1 Macierz: co pokrywa który mechanizm

| Use case | Python `self.hass` | Supervisor REST API | Shell subprocess | Czysty Python (asyncio/pathlib) |
|----------|-------------------|---------------------|------------------|---------------------------------|
| Entity states, attributes | ✅ | — | — | — |
| Service calls (turn on/off) | ✅ | — | — | — |
| Historia stanów (recorder) | ✅ | — | — | — |
| **HA Core logs** | ❌ | ✅ `/core/logs` | ❌ (`ha` nie działa) | — |
| **Addon logs** | ❌ | ✅ `/addons/{slug}/logs` | ❌ | — |
| **Supervisor/host/OS info** | ❌ | ✅ `/supervisor/info`, `/host/info`, `/os/info` | ❌ | — |
| **Network info** | ❌ | ✅ `/network/info` | ✅ `ip addr`, `ss` | — |
| **Czytanie plików config** | ❌ (brak API) | ❌ | ✅ `cat /config/x.yaml` | ✅ `Path.read_text()` |
| **ping / traceroute** | ❌ | ❌ | ✅ `ping -c 4 wp.pl` | ✅ `icmplib` (ale wymaga raw socket) |
| **DNS lookup** | ❌ | ❌ | ✅ `dig`, `nslookup` | ✅ `socket.getaddrinfo()` |
| **Procesy systemowe** | ❌ | ❌ | ✅ `ps aux` | ✅ `psutil` (jeśli zainstalowany) |
| **Logi systemowe** | ❌ | ❌ | ✅ `cat /var/log/...` | ✅ `Path.read_text()` |
| **Disk/memory usage** | ❌ | ✅ `/host/info` (częściowo) | ✅ `df -h`, `free -h` | — |
| **Resolution center** | ❌ | ✅ `/resolution/info` | ❌ | — |

### 3.0.2 Wniosek: strategia 3 tooli (rev3)

**Żaden pojedynczy mechanizm nie pokrywa wszystkich diagnostycznych use case'ów.**
Potrzebujemy 3 niezależnych tooli, każdy z innym mechanizmem:

| # | Tool | Mechanizm | Pokrywa | Ryzyko | Priorytet |
|---|------|-----------|---------|--------|-----------|
| 1 | **`safe_shell_execute`** | `asyncio.create_subprocess_exec()` | ping, traceroute, dig, ps, df, free, cat plików, grep, logi systemowe | Średnie (subprocess sandbox) | **MVP — ten plan** |
| 2 | **`supervisor_api`** | HTTP do Supervisor REST API | Logi HA Core, logi addonów, host/OS info, network info, resolution | Niskie (read-only HTTP, auth tokenem) | **Równoległy priorytet — osobny plan** |
| 3 | **`safe_file_read`** | `pathlib.Path.read_text()` | Czytanie plików config (YAML, JSON, log, txt) — bezpieczniej niż shell `cat` | Niskie (brak subprocess) | **Opcjonalny — może zastąpić `cat` w shell** |

**Dlaczego shell jest niezastąpiony:**
- `ping wp.pl` — żadne HA API tego nie oferuje
- `traceroute 8.8.8.8` — diagnostyka routingu
- `dig google.com` — diagnostyka DNS
- `ps aux` — procesy systemowe
- `df -h` / `free -h` — disk/memory (Supervisor API daje tylko częściowe info)
- `grep -r "error" /var/log/` — przeszukiwanie logów systemowych

**Dlaczego Supervisor API jest niezastąpiony:**
- HA Core logs — jedyny sposób na logi HA z kontenera
- Addon logs — `GET /addons/{slug}/logs`
- Host info — wersja OS, hostname, features
- Resolution center — problemy wykryte przez HA

**Dlaczego `safe_file_read` jest opcjonalny:**
- `Path.read_text()` jest bezpieczniejszy niż subprocess `cat`
- Ale shell `cat` + `grep` + `head`/`tail` dają więcej elastyczności
- Rozważyć w v2 jako bezpieczniejszą alternatywę dla czytania plików config

---

## 4. Architektura — Component Diagram

### 4.1 Trzy toole diagnostyczne (rev3, poprzednio "dwa toole" w rev2)

| Tool | Mechanizm | Cel | Tier | Status |
|------|-----------|-----|------|--------|
| `safe_shell_execute` | `asyncio.create_subprocess_exec()` | Komendy systemowe: `ping`, `df`, `ps`, `grep`, `cat`, `jq` | ON_DEMAND | **Ten plan — MVP** |
| `supervisor_api` | `aiohttp` HTTP do Supervisor REST API | Logi HA, addon info, host info, network, resolution | ON_DEMAND | **Osobny plan — równoległy priorytet** |
| `safe_file_read` (opcjonalny) | `pathlib.Path.read_text()` | Bezpieczne czytanie plików config | ON_DEMAND | **Rozważyć w v2** |

Istniejący `ha_native` tools (20 szt.) już pokrywają: entity state, registries, services,
history, statistics, weather, calendar, automations, scenes, persons, dashboards.

**Supervisor API reference:**
- Endpoint: `http://{os.environ['SUPERVISOR']}/{path}`
- Auth: `Authorization: Bearer {os.environ['SUPERVISOR_TOKEN']}`
- Read-only endpoints: `/core/info`, `/core/stats`, `/core/logs`, `/supervisor/info`,
  `/host/info`, `/os/info`, `/network/info`, `/addons/info`, `/resolution/info`
- Istniejący kod w HA Core: `homeassistant/components/hassio/handler.py` → klasa `HassIO`
- Typed client: `aiohasupervisor` (v0.3.3) → `SupervisorClient`

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM (Gemini/OpenAI/Anthropic)                │
│                                                                     │
│  1. load_tool("safe_shell_execute")                                 │
│  2. safe_shell_execute(command="ls -la /config/")                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    ToolExecutor.execute_tool_calls()                  │
│                    (core/tool_executor.py — BEZ ZMIAN)               │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  SafeShellExecuteTool.execute()                       │
│                  (tools/shell_execute.py)                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 1: CommandValidator  (tools/shell_security.py)          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │  │
│  │  │ Parse & split │→│ Blocklist    │→│ Allowlist prefix     │  │  │
│  │  │ (shlex)       │  │ check        │  │ match               │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────────────┘  │  │
│  │                                              │                 │  │
│  │                                              ▼                 │  │
│  │  ┌──────────────┐                 ┌─────────────────────┐      │  │
│  │  │ Path         │                 │ Classify:           │      │  │
│  │  │ validation   │                 │ SAFE / NEEDS_CONFIRM│      │  │
│  │  └──────────────┘                 └─────────┬───────────┘      │  │
│  └─────────────────────────────────────────────┼──────────────────┘  │
│                                                │                     │
│  ┌─────────────────────────────────────────────┼──────────────────┐  │
│  │  LAYER 2: Execution Sandbox                 │                  │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │ asyncio.create_subprocess_exec()  (NIE shell=True!)      │  │  │
│  │  │ • cwd = /tmp/homeclaw_shell (isolated)                   │  │  │
│  │  │ • env = minimal (PATH only, no secrets)                  │  │  │
│  │  │ • timeout = configurable (default 30s)                   │  │  │
│  │  │ • stdout/stderr capped at MAX_OUTPUT_BYTES               │  │  │
│  │  │ • process.kill() on timeout                              │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  LAYER 3: AuditLogger                                          │  │
│  │  • _LOGGER.info() z pełnym audit entry                         │  │
│  │  • Fields: timestamp, user_id, command, exit_code,             │  │
│  │    duration_ms, output_truncated, classification               │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  → Returns ToolResult with structured metadata                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Security Model — Trzy warstwy obrony

### Layer 1: Static Command Validation (REJECT before execution)

**Pipeline walidacji (5 kroków):**

```
Raw command string
    │
    ├─ Step 1: shlex.split() — parsowanie na tokeny
    │   → REJECT jeśli shlex fail (niezbalansowane cudzysłowy)
    │
    ├─ Step 2: Blocklist scan (na RAW stringu, przed split)
    │   Regex patterns:
    │   • [;&|]           — command chaining / piping
    │   • [><]            — redirects
    │   • `               — backtick subshell
    │   • \$\(            — $() subshell
    │   • \$\{            — ${} variable expansion
    │   • \.\.            — path traversal
    │   • ~               — home directory expansion
    │   → REJECT jeśli match
    │
    ├─ Step 3: Blocked commands check
    │   tokens[0] NOT IN: rm, rmdir, mv, cp, chmod, chown, chroot,
    │   sudo, su, dd, mkfs, mount, umount, kill, killall, pkill,
    │   reboot, shutdown, halt, systemctl, service, init,
    │   wget, curl, nc, ncat, socat, ssh, scp,
    │   python, python3, perl, ruby, node, bash, sh,
    │   eval, exec, source, export, unset, alias,
    │   apt, apt-get, apk, pip, npm, docker (exec/run/build),
    │   iptables, ip, ifconfig, route,
    │   passwd, useradd, userdel, groupadd, crontab, at
    │   → REJECT jeśli match
    │
    ├─ Step 4: Allowlist prefix match
    │   tokens[:N] MUST match one of:
    │   • File inspection: ls, cat, head, tail, wc, file, stat
    │   • System info: df, du, free, uptime, uname, date, whoami, id, hostname, ps
    │   • Search/parse: grep, find (no -exec/-delete), jq, sort, uniq, cut
    │   • (opcjonalnie, jeśli zainstalowane): rg
    │
    │   ⚠️ rev2: USUNIĘTO z allowlist:
    │   • `ha` CLI — niedostępne z kontenera HA Core (patrz 3.1)
    │   • `docker` — docker inspect/logs mogą leakować secrets (env vars, config)
    │   • `sed`, `awk` — zbyt potężne, nie były na allowliście a miały walidację
    │   → REJECT jeśli brak match
    │
    └─ Step 5: Argument sanitization (post-allowlist)
        • find: reject -exec, -execdir, -delete, -ok
        • cat/head/tail/ls: validate path against ALLOWED_PATHS
        • grep/rg: validate target path against ALLOWED_PATHS
        • rg: reject --exec flag
        → REJECT jeśli dangerous arguments
```

### Layer 2: Path Validation

**Allowed paths (read-only):**
- `/config/` — z wykluczeniami (patrz blocked)
- `/share/`
- `/tmp/`
- `/var/log/`

**Blocked paths (HARD BLOCK, nigdy nie czytelne):**
- `/config/secrets.yaml`
- `/config/.storage/` (cały katalog — tokeny sesji, hashe haseł)
- `/config/.cloud/` (Nabu Casa tokeny)
- `/ssl/` (certyfikaty TLS, klucze prywatne)
- `/proc/self/environ` (env vars z SUPERVISOR_TOKEN)
- `/proc/` (cały katalog poza `/proc/cpuinfo`, `/proc/meminfo`, `/proc/uptime`)
- `/etc/shadow`, `/etc/passwd`
- `/config/home-assistant_v2.db` (binary, dane prywatne)

**Blocked filename patterns (rev2 — zawężone, mniej false positives):**

> ⚠️ rev2 (FIX #6): Poprzednia wersja blokowała pliki z `key` w nazwie, co dawało
> masę false positives (np. `keyboard.yaml`, `api_key_rotation.log`).
> Zawężono do precyzyjnych wzorców:

- `secrets.yaml`, `secrets.json` — dokładne nazwy
- `.pem`, `.key`, `.p12`, `.pfx`, `.jks` — rozszerzenia certyfikatów/kluczy
- `*_token`, `*_token.*` — pliki tokenów
- `*_credential*`, `*_password*` — pliki credentials
- `.env`, `.env.*` — pliki environment

**NIE blokujemy** ogólnych słów jak `key` czy `secret` w ścieżce — to daje za dużo
false positives. Zamiast tego blokujemy **konkretne katalogi** (`.storage/`, `.cloud/`, `/ssl/`)
które zawierają wrażliwe dane.

**Symlink resolution (rev2 — w MVP, nie odłożone):** `pathlib.Path.resolve()` PRZED sprawdzeniem allowlist.
Poprzednia wersja planu miała niespójność: sekcja 5 wymagała resolve() ale sekcja 12 wykluczała
z MVP. **Resolve() jest w MVP** — to krytyczna obrona przed symlink bypass.

### Layer 3: Execution Sandbox

- `asyncio.create_subprocess_exec()` — **NIGDY** `shell=True`
- `cwd = /tmp/homeclaw_shell` (tworzony jeśli nie istnieje, mode 0o700)
- `env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp/homeclaw_shell", "LANG": "C.UTF-8"}`
  - **BEZ** `SUPERVISOR_TOKEN`, API keys, HA secrets
- Timeout: `asyncio.wait_for()` + `proc.kill()` + `proc.wait()` (reap zombie)
- **Output cap (rev2 — streaming read, NIE communicate()):**
  ```
  # ⚠️ communicate() buforuje CAŁY output w pamięci przed zwróceniem.
  # Jeśli komenda zwróci 500MB, communicate() zaalokuje 500MB RAM.
  # Zamiast tego: czytamy strumieniowo z limitem bajtów.
  
  stdout_data = await proc.stdout.read(MAX_OUTPUT_BYTES)  # max 64KB
  stderr_data = await proc.stderr.read(MAX_OUTPUT_BYTES)  # max 64KB
  # Jeśli jest więcej danych → truncated=True
  # Potem: proc.kill() + proc.wait() żeby nie zostawić zombie
  ```
  To chroni pamięć procesu HA Core nawet jeśli komenda generuje gigabajty outputu.

---

## 6. Resource Limits

| Zasób | Limit | Default | Konfigurowalny? | Enforcement |
|-------|-------|---------|-----------------|-------------|
| Timeout per-command | 5-120s | 30s | Tak (parametr) | `asyncio.wait_for()` + `proc.kill()` |
| Max output | stdout + stderr | 64KB each | Tak (parametr) | **Streaming read z limitem** (rev2: NIE communicate()) |
| Max command length | Raw input | 1024 chars | Hardcoded | Walidacja przed parsowaniem |
| Concurrent executions | Global | 1 (serial) | Hardcoded | `asyncio.Semaphore(1)` |
| Rate limit | Per user | 10/min | Hardcoded | In-memory counter + timestamp ring |

---

## 7. Audit Logging

### Format wpisu

```json
{
  "timestamp": "2026-02-18T14:30:00.000Z",
  "user_id": "abc123",
  "tool": "safe_shell_execute",
  "command_raw": "ha core logs --lines 50",
  "command_tokens": ["ha", "core", "logs", "--lines", "50"],
  "classification": "SAFE",
  "confirmed": true,
  "exit_code": 0,
  "duration_ms": 1234,
  "stdout_bytes": 2048,
  "stderr_bytes": 0,
  "truncated": false,
  "rejection_reason": null,
  "error": null
}
```

### Storage
- **Primary:** `_LOGGER.info("shell_audit: %s", json.dumps(entry))` — HA log, rotacja standardowa
- **Secondary (v2):** `hass.components.persistent_notification.async_create()` — dla NEEDS_CONFIRM i REJECTED
- **In ToolResult:** Pełny audit entry w `metadata` — przechowywany w historii sesji

---

## 8. User Confirmation Flow (rev2 — przebudowane)

> **⚠️ rev2:** Poprzedni two-call pattern z parametrem `confirm=true` był **łatwy do obejścia
> przez LLM** — model mógł sam ustawić `confirm=true` bez pytania użytkownika.
> Sama instrukcja w tool description + audit to zbyt słaba kontrola.

### MVP: Brak confirmation — tylko SAFE i REJECTED

W MVP **nie ma kategorii NEEDS_CONFIRM**. Każda komenda jest albo:
- **SAFE** → auto-execute (ls, df, free, uptime, ps, date, uname, whoami, id, hostname, wc)
- **REJECTED** → odmowa z wyjaśnieniem

Komendy czytające pliki (`cat`, `head`, `tail`, `grep`, `find`, `jq`) są **SAFE** pod warunkiem
że ścieżka przechodzi walidację (allowed paths + blocked paths + Path.resolve()).

**Parametr `confirm` USUNIĘTY z API toola.** Nie ma go w MVP.

### Przyszłość (v2): Frontend confirmation dialog

Prawdziwe potwierdzenie wymaga **mechanizmu poza kontrolą LLM**:

```
1. Tool zwraca ToolResult z error="confirmation_required"
2. Frontend wyświetla dialog: "Agent chce wykonać: cat /config/configuration.yaml [Zezwól] [Odmów]"
3. User klika [Zezwól] → frontend wysyła WebSocket event z confirmation_token
4. Tool otrzymuje token → weryfikuje → wykonuje
```

To wymaga:
- Nowego WebSocket command: `ai_agent_ha/shell/confirm`
- Nowego event type w `events.py`: `ShellConfirmationRequestEvent`
- Frontend component: `ConfirmationDialog.svelte`
- Timeout na confirmation (30s → auto-reject)

**Kluczowa różnica:** Token confirmation pochodzi z **frontendu** (user action),
nie z **LLM** (model action). LLM nie może sfabrykować tokenu.

---

## 9. ToolResult Contract — JSON

### Input (parametry toola)

```json
{
  "command": "ls -la /config/",
  "timeout": 30
}
```

> **rev2:** Parametr `confirm` usunięty. Patrz sekcja 8.
> **rev4:** Parametr `max_output_bytes` usunięty — hardcoded 64KB. Mniej surface area dla LLM.

### Output — Success

```json
{
  "output": "total 48\ndrwxr-xr-x 1 root root 4096 Feb 18 14:30 .\n...",
  "success": true,
  "error": null,
  "title": "Shell: ls -la /config/",
  "metadata": {
    "command": "ls -la /config/",
    "exit_code": 0,
    "duration_ms": 42,
    "stdout_bytes": 2048,
    "stderr_bytes": 0,
    "truncated": false,
    "classification": "SAFE",
    "stderr": ""
  }
}
```

### Output — Rejected

```json
{
  "output": "Command rejected: contains blocked command 'rm'.",
  "success": false,
  "error": "command_rejected",
  "title": "Shell: REJECTED",
  "metadata": {
    "command": "rm -rf /",
    "classification": "REJECTED",
    "reason": "Blocked command: rm",
    "blocked_by": "BLOCKED_COMMANDS"
  }
}
```

### Output — Timeout

```json
{
  "output": "",
  "success": false,
  "error": "timeout",
  "title": "Shell: tail -f /var/log/syslog (timeout)",
  "metadata": {
    "command": "tail -f /var/log/syslog",
    "exit_code": null,
    "duration_ms": 30000,
    "timeout_seconds": 30,
    "process_killed": true
  }
}
```

---

## 10. Risk Matrix

| # | Ryzyko | Severity | Likelihood | Mitigation | Residual |
|---|--------|----------|------------|------------|----------|
| R1 | Command injection via crafted string | CRITICAL | Medium | shlex.split + blocklist + no shell=True | LOW |
| R2 | LLM auto-confirms bez user consent | HIGH | High | **rev2: Usunięto parametr confirm. MVP: SAFE/REJECTED only. v2: frontend token** | LOW |
| R3 | Path traversal (cat ../../etc/shadow) | HIGH | Medium | Blocklist `..` + allowed paths + resolve() | LOW |
| R4 | Resource exhaustion (fork bomb, infinite output) | HIGH | Low | Timeout + output cap + semaphore + rate limit | LOW |
| R5 | Secret leakage via env vars | HIGH | Medium | Sanitized env (PATH only) | LOW |
| R6 | Symlink bypass | MEDIUM | Low | Path.resolve() before validation | LOW (v1) |
| R7 | Binary not available on HA OS | MEDIUM | Medium | Graceful error + binary detection | LOW |
| R8 | Docker socket access | CRITICAL | Low | **rev2: Docker usunięty z allowlist. Brak docker commands** | NEGLIGIBLE |
| R9 | Secrets file read (secrets.yaml, .storage/) | CRITICAL | High | Hard-block paths + filename patterns | LOW |
| R10 | jq `env` function leaks env vars | MEDIUM | Low | Sanitized env + consider blocking jq env | LOW |
| R11 | rg --exec flag executes commands | HIGH | Low | Strip dangerous flags per tool | LOW |
| R12 | cat /proc/self/environ | HIGH | Medium | Block /proc/ entirely | LOW |
| R13 | TOCTOU race (path check → symlink → read) | MEDIUM | Low | Open-then-check pattern (v2) | MEDIUM |
| R14 | LLM retry storm (50 calls/min) | MEDIUM | Medium | Rate limit 10/min + circuit breaker | LOW |

---

## 11. Edge Cases — Exhaustive List

### Command Validation
1. Empty command → reject
2. Whitespace-only → reject
3. Shell metacharacters (`;`, `&&`, `||`, `|`) → blocklist
4. Backtick substitution → blocklist
5. `$(...)` substitution → blocklist
6. `${...}` expansion → blocklist
7. Unicode homoglyphs (`ｒｍ` zamiast `rm`) → normalize to ASCII
8. URL-encoded characters (`%72%6D`) → reject `%XX` patterns
9. Null bytes (`cat\x00/etc/shadow`) → strip null bytes
10. Very long command (>1024 chars) → reject
11. Command not in allowlist → reject
12. Allowed command with disallowed subcommand (`ha core restart`) → subcommand validation

### Path Traversal
13. `cat /etc/shadow` → path not in allowed prefixes
14. `cat /config/../../etc/shadow` → resolve + prefix check
15. `cat /config/secrets.yaml` → hard-blocked filename
16. `ls /` → path not in allowed prefixes
17. Symlink pointing outside allowed paths → resolve() catches

### Resource Limits
18. Command hangs forever (`tail -f`) → timeout kills
19. Massive output (`cat /dev/urandom`) → output truncation + /dev/ blocked
20. Fork bomb → HA container cgroup limits
21. Timeout = 0 or negative → clamp to minimum (5s)
22. Timeout > 120 → clamp to maximum (120s)

### HA OS Specifics
23. Binary not found (`rg` not installed) → graceful error
24. ~~`ha` CLI not available~~ → **rev2: `ha` usunięte z allowlist, nie dotyczy**
25. Permission denied → return stderr
26. Container restart during execution → timeout handles cleanup

### Subprocess Edge Cases
27. `shlex.split()` fails on malformed quotes → catch ValueError
28. Non-zero exit code → still return result (not error)
29. Process killed by signal → negative exit code, report signal
30. stderr has content but stdout empty → return both
31. Binary output (non-UTF-8) → decode with `errors="replace"`

### Concurrency
32. Multiple simultaneous commands → Semaphore(1) serializes
33. Rate limit exceeded → reject with clear error

---

## 12. Plan implementacji

### Faza 1: MVP (~3-4h)

#### Pliki do stworzenia/modyfikacji

| # | Plik | Akcja | Cel | Est. linii |
|---|------|-------|-----|------------|
| 1 | `tools/shell_security.py` | CREATE | Walidacja security: allowlist, blocklist, path validation, env sanitization | ~120 |
| 2 | `tools/shell_execute.py` | CREATE | Tool class: `SafeShellExecuteTool` z `execute()` | ~150 |
| 3 | `tools/__init__.py` | MODIFY | Dodanie importu `shell_execute` + `__all__` | ~3 linie zmian |
| 4 | `proactive/heartbeat.py` | MODIFY | Dodanie `"safe_shell_execute"` do `HEARTBEAT_DENIED_TOOLS` | ~1 linia |
| 5 | `core/subagent.py` | MODIFY | Dodanie `"safe_shell_execute"` do `DENIED_TOOLS` | ~1 linia |
| 6 | `tests/test_tools_shell.py` | CREATE | Comprehensive test suite | ~250 |

> **rev2 (FIX #5):** `safe_shell_execute` MUSI być w `denied_tools` dla heartbeat i subagent.
> Heartbeat i subagent działają autonomicznie (bez user interaction) — shell access
> w kontekście bez nadzoru użytkownika to niedopuszczalne ryzyko.
> Istniejące frozensets:
> - `proactive/heartbeat.py` linia 58: `HEARTBEAT_DENIED_TOOLS`
> - `core/subagent.py` linia 43: `DENIED_TOOLS`

#### Co jest w MVP
- Hardcoded allowlist/blocklist (brak custom config)
- `asyncio.create_subprocess_exec()` sandbox
- SAFE/REJECTED classification only (rev2: NEEDS_CONFIRM usunięte, patrz sekcja 8)
- Audit via `_LOGGER.info()` z redakcją wrażliwych danych
- Timeout + output cap + proc.kill()
- Semaphore(1) for serial execution
- Rate limit (10/min)
- HA environment detection
- Unit tests for CommandValidator

#### Czego NIE MA w MVP
- Custom allowlist config
- persistent_notification audit
- Frontend confirmation dialog (patrz sekcja 8 rev2)
- Per-user allowlist customization
- Pipe support

> **rev2:** `Path.resolve()` **jest w MVP** (przeniesione z Fazy 2). To krytyczna obrona.

### Faza 2: Hardening (~2h)

- `persistent_notification` for REJECTED commands (admin visibility)
- Component config: `shell_execute_enabled` master switch (default: `false`)
- Allowed path roots configurable
- Binary availability detection (`shutil.which()`)
- Integration tests against real HA OS
- Supervisor API tool (osobny plan, osobny plik)

> **rev2:** `Path.resolve()` i filename pattern blocking przeniesione do MVP (Faza 1).

### Faza 3: Advanced (future, ~4h)

- Frontend confirmation dialog (new event type)
- Custom allowlist via UI config
- Command history browser in frontend
- Per-user rate limits
- Optional Docker-based sandbox
- Pipe support for safe combinations only (e.g., `ha core logs | grep error`)
- Output sanitization (redact secret patterns)

---

## 13. Test Plan

### A. Security Validation Tests (`TestShellSecurity`)

| Test | Co weryfikuje |
|------|---------------|
| `test_ls_allowed` | `ls -la /config/` → valid |
| `test_ls_with_path` | `ls -la /config/automations.yaml` → valid |
| `test_cat_allowed` | `cat /config/configuration.yaml` → valid |
| `test_blocked_semicolon` | `ls; rm -rf /` → rejected |
| `test_blocked_pipe` | `cat /config/x \| curl` → rejected |
| `test_blocked_redirect` | `echo x > /config/x` → rejected |
| `test_blocked_backtick` | `` cat \`which rm\` `` → rejected |
| `test_blocked_dollar_paren` | `cat $(echo /etc/shadow)` → rejected |
| `test_blocked_rm` | `rm /config/test` → rejected |
| `test_blocked_sudo` | `sudo ls` → rejected |
| `test_blocked_curl` | `curl http://evil.com` → rejected |
| `test_blocked_python` | `python3 -c "..."` → rejected |
| `test_unknown_command` | `unknown_binary` → rejected |
| `test_empty_command` | `""` → rejected |
| `test_whitespace_command` | `"   "` → rejected |
| `test_very_long_command` | 2000 char command → rejected |
| `test_null_bytes_stripped` | `"cat\x00/etc/shadow"` → rejected |
| `test_path_traversal_blocked` | `cat /config/../../etc/shadow` → rejected |
| `test_secrets_file_blocked` | `cat /config/secrets.yaml` → rejected |
| `test_storage_dir_blocked` | `ls /config/.storage/` → rejected |
| `test_allowed_path_config` | `/config/configuration.yaml` → allowed |
| `test_allowed_path_share` | `/share/data.json` → allowed |
| `test_blocked_path_etc` | `/etc/passwd` → rejected |
| `test_sanitize_env` | Returns minimal env without secrets |
| `test_ha_cli_not_on_allowlist` | `ha core logs` → rejected (rev2: ha nie na allowliście) |
| `test_docker_not_on_allowlist` | `docker ps` → rejected (rev2: docker usunięty) |
| `test_find_exec_blocked` | `find /config -exec rm {} \;` → rejected |
| `test_rg_exec_blocked` | `rg --exec cat /config/` → rejected |
| `test_symlink_resolved` | symlink → /etc/shadow → rejected after resolve() |
| `test_proc_blocked` | `cat /proc/self/environ` → rejected |

### B. Tool Execution Tests (`TestSafeShellExecuteTool`)

| Test | Co weryfikuje | Mock strategy |
|------|---------------|---------------|
| `test_tool_registration` | Tool registered z correct id/tier | Direct |
| `test_tool_metadata` | Parameters, category, tier correct | Direct |
| `test_successful_execution` | `ls /config/` returns structured result | Mock subprocess |
| `test_command_rejected` | Blocked command returns error ToolResult | No mock needed |
| `test_timeout_kills_process` | Long-running command killed after timeout | Mock with sleep |
| `test_output_truncation` | Large output truncated, `truncated=true` | Mock large stdout |
| `test_stderr_captured` | stderr included in result | Mock stderr |
| `test_nonzero_exit_code` | Non-zero exit reported, still success=True | Mock returncode=1 |
| `test_duration_measured` | `duration_ms` is reasonable positive number | Mock subprocess |
| `test_binary_output_handled` | Non-UTF-8 bytes decoded with replacement | Mock bytes |
| `test_shlex_split_error` | Malformed quotes return error | No mock |
| `test_timeout_clamped` | timeout=0 → 5, timeout=200 → 120 | Direct |
| `test_audit_log_emitted` | `_LOGGER.info` called with command details | Mock logger |
| `test_rate_limit_exceeded` | 11th call in 1 minute → rejected | Direct |
| `test_streaming_output_cap` | Output > 64KB → only first 64KB read, truncated=true | Mock large stdout |
| `test_denied_in_heartbeat` | safe_shell_execute in HEARTBEAT_DENIED_TOOLS | Direct import check |
| `test_denied_in_subagent` | safe_shell_execute in DENIED_TOOLS (subagent) | Direct import check |

### C. Integration Tests

| Test | Co weryfikuje |
|------|---------------|
| `test_execute_via_registry` | `ToolRegistry.execute_tool("safe_shell_execute", ...)` works |
| `test_on_demand_listed` | Tool appears in `list_on_demand_ids()` |
| `test_load_tool_activates` | `load_tool(tool_name="safe_shell_execute")` succeeds |

**Mock strategy:** Wszystkie subprocess calls mockowane. Żadne prawdziwe komendy shell w testach.

---

## 14. Security Review Checklist (przed shipem)

- [ ] **No shell=True** — `create_subprocess_exec` used, NOT `create_subprocess_shell`
- [ ] **Allowlist is deny-by-default** — unknown commands rejected
- [ ] **Blocklist covers all shell metacharacters** — `;`, `&&`, `||`, `|`, `` ` ``, `$(`, `${`, `>`, `<`, `>>`, `<<`
- [ ] **Path traversal blocked** — `..` in blocklist + allowed path prefixes
- [ ] **Sensitive files blocked** — secrets.yaml, .storage/, .cloud/, /ssl/
- [ ] **No secrets in env** — sanitize_env() strips API keys, tokens
- [ ] **Timeout enforced** — asyncio.wait_for + proc.kill() on timeout
- [ ] **Output size limited** — truncation before returning to LLM
- [ ] **Audit log complete** — every execution logged
- [ ] **No f-strings in logger calls** — use `%s` placeholders
- [ ] **bandit clean** — no security findings
- [ ] **No hardcoded credentials**
- [ ] **shlex.split error handled** — malformed input doesn't crash
- [ ] **Non-UTF-8 output handled** — `errors="replace"` on decode
- [ ] **Process cleanup on timeout** — proc.kill() + proc.wait() (no zombies)
- [ ] **Command length limit** — reject > 1024 chars
- [ ] **No eval(), exec(), os.system(), subprocess.call(shell=True)** in module

---

## 15. Dependencies

**Brak nowych pakietów Python.** Wszystko w stdlib:
- `asyncio` — `create_subprocess_exec`, `wait_for`
- `shlex` — `split()` for safe command parsing
- `pathlib` — `Path.resolve()` for symlink resolution
- `time` — `monotonic()` for duration measurement
- `re` — compiled patterns for blocklist
- `shutil` — `which()` for binary availability detection

---

## 16. Rollback Plan

### Natychmiastowe wyłączenie (bez deploy)
```python
class SafeShellExecuteTool(Tool):
    enabled = False  # ← flip this
```
Restart HA → tool nie pojawia się w `list_on_demand_ids()`.

### Pełne usunięcie
1. Delete `tools/shell_execute.py` i `tools/shell_security.py`
2. Remove import z `tools/__init__.py`
3. Deploy + restart HA

### Emergency (bez zmiany kodu)
Tool jest ON_DEMAND → nigdy nie ładowany automatycznie. Dodanie do `denied_tools` w ToolExecutor blokuje nawet po load_tool.

---

## 17. Acceptance Criteria (Definition of Done)

- [ ] `tools/shell_security.py` exists, < 150 lines, all validation functions tested
- [ ] `tools/shell_execute.py` exists, < 180 lines, follows existing tool patterns
- [ ] Tool registered jako `safe_shell_execute` z `tier = ToolTier.ON_DEMAND`
- [ ] `pytest tests/test_tools_shell.py -v` — all tests pass (≥25 test cases)
- [ ] `pytest tests/ --cov=custom_components/homeclaw --cov-fail-under=70` — coverage maintained
- [ ] `bandit -r custom_components/homeclaw/tools/shell_security.py shell_execute.py` — clean
- [ ] `black --check`, `isort --check`, `flake8` — all pass
- [ ] `safe_shell_execute` dodane do `HEARTBEAT_DENIED_TOOLS` i `DENIED_TOOLS` (subagent)
- [ ] Deployed to HA at 192.168.1.109, restart successful
- [ ] Smoke test: `load_tool("safe_shell_execute")` → `ls -la /config/` works
- [ ] Smoke test: `rm -rf /` rejected with clear error
- [ ] Smoke test: `cat /config/configuration.yaml` works, `cat /etc/shadow` rejected
- [ ] Smoke test: `cat /config/secrets.yaml` HARD BLOCKED
- [ ] Smoke test: `ha core logs` REJECTED (ha nie na allowliście — patrz rev2)
- [ ] Smoke test: `docker ps` REJECTED (docker usunięty — patrz rev2)
- [ ] No secrets, API keys, or credentials in committed files
- [ ] Output streaming: komenda z dużym outputem nie zjada pamięci HA Core

---

## 18. Otwarte pytania (do dyskusji przed implementacją)

1. **Czy `shell_execute_enabled` powinno defaultować na `true` czy `false`?**
   Rekomendacja: `false` (opt-in). Ale to wymaga config flow change.

2. **Czy pipe (`|`) kiedykolwiek powinien być dozwolony?**
   Rekomendacja: Block w MVP, rozważ safe pipe patterns w v2.

3. **Czy `cat` powinien być ograniczony do konkretnych rozszerzeń plików?**
   Np. tylko `.yaml`, `.json`, `.log`, `.txt` — blokuje binary.
   Rekomendacja: Tak w v1.

4. ~~**Kiedy zrobić `supervisor_api` tool?**~~ **RESOLVED (rev3):**
   Równoległy priorytet. Shell i Supervisor API pokrywają różne, nieprzekrywające
   się use case'y. Shell = diagnostyka systemowa/sieciowa. Supervisor API = logi HA/addonów.
   Oba potrzebne. Osobny plan dla `supervisor_api` do stworzenia.

5. **Jak obsłużyć `jq` z funkcją `env`?**
   `jq 'env.HOME'` leakuje env vars. Sanitized env mityguje, ale nie eliminuje.
   Rekomendacja: Sanitized env wystarczy na MVP.

6. **(NOWE) Czy `tail -f` powinien być na allowliście?**
   `-f` (follow) nigdy się nie kończy — timeout go zabije, ale user może chcieć
   "ostatnie logi". Rekomendacja: Dozwolony `tail -n` ale NIE `tail -f`.

---

## 19. Estimated Effort

### `safe_shell_execute` (ten plan)

| Faza | Scope | Effort | Risk |
|------|-------|--------|------|
| **Faza 1 (MVP)** | Security module + tool + tests | **3-4h** | Medium |
| **Faza 2 (Hardening)** | Path validation, binary detection, audit | **1.5-2h** | Low |
| **Faza 3 (Advanced)** | UI confirmation, custom config, pipes | **3-4h** | High |
| **Total MVP** | Faza 1 + 2 | **~5-6h** | — |

### Pełna roadmapa diagnostycznych tooli (rev3)

| Tool | Effort | Priorytet | Zależności |
|------|--------|-----------|-----------|
| `safe_shell_execute` | ~5-6h (MVP+hardening) | **P0 — ten plan** | Brak |
| `supervisor_api` | ~3-4h (osobny plan) | **P0 — równoległy** | Supervisor env vars |
| `safe_file_read` | ~2h | P2 — opcjonalny | Może zastąpić `cat` w shell |

---

## Tooling Trace

### Rev 1 (initial)
- Primary agent: @master-of-disaster-rlm (orchestrator)
- Sub-agents used: @architect-rlm, @planner-rlm, @brainstorm-rlm
- Tools used: mcp_read, mcp_glob, mcp_grep (codebase exploration)
- Files analyzed: tools/base.py, tools/__init__.py, core/tool_executor.py, todo-tools-architecture.md, AGENTS.md

### Rev 2 (post-review)
- Primary agent: @master-of-disaster-rlm (orchestrator)
- Sub-agents used: @explore (ha CLI availability research)
- Tools used: mcp_read, mcp_grep, mcp_edit (plan updates)
- Files analyzed: core/ Dockerfile, homeassistant/components/hassio/handler.py, hassio/http.py,
  proactive/heartbeat.py (HEARTBEAT_DENIED_TOOLS), core/subagent.py (DENIED_TOOLS)
- Key finding: `ha` CLI definitywnie NIE jest dostępne z procesu HA Core (potwierdzone
  analizą Dockerfile + handler.py + http.py). Supervisor REST API jest jedynym mechanizmem.
- Ralph iterations: 0 (planning only, no code)

### Rev 3 (3-tool strategy)
- Primary agent: @master-of-disaster-rlm (orchestrator)
- Sub-agents used: brak (analiza bezpośrednia)
- Tools used: mcp_read (tools/ha_native.py, tools/base.py), mcp_edit (plan updates)
- Files analyzed: tools/ha_native.py (1358 lines — pełna analiza 20 istniejących tooli),
  tools/base.py (583 lines — Tool ABC, ToolRegistry, ToolResult)
- Key finding: Wszystkie istniejące toole używają wyłącznie in-process Python API
  (`self.hass.states`, registries, services, recorder). Żaden nie używa subprocess/HTTP/file IO.
  Analiza macierzy dostępu potwierdza: żaden pojedynczy mechanizm nie pokrywa wszystkich
  diagnostycznych use case'ów → strategia 3 niezależnych tooli.
- Ralph iterations: 0 (planning only, no code)
