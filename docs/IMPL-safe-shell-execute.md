# IMPLEMENTATION PLAN: `safe_shell_execute` Tool

**Data:** 2026-02-18 (rev4: 2026-02-18 — post-review fixes from Codex + @reviewer-rlm)
**Status:** Gotowy do implementacji (all blockers resolved)
**Bazuje na:** `docs/PLAN-safe-shell-execute.md` (rev3)
**Autorzy:** @master-of-disaster-rlm (orchestrator), @planner-rlm
**Reviewers:** Codex (gpt-5.3-codex), @reviewer-rlm

---

## Decyzje zamkniete (rev4 — post-review)

> **Q1 (RESOLVED):** `cat`/`head`/`tail` SA ograniczone do text-like extensions:
> `.yaml`, `.yml`, `.json`, `.log`, `.txt`, `.conf`, `.cfg`, `.ini`, `.xml`, `.csv`, `.md`, `.toml`
> Blokujemy binary: `.db`, `.sqlite`, `.bin`, `.so`, `.pyc`, brak rozszerzenia.

> **Q2 (RESOLVED):** `tail -f` jest BLOKOWANY w MVP (flaga `-f` / `--follow` odrzucana
> w argument sanitization). `tail -n` jest dozwolony.

> **Q3 (RESOLVED):** `max_output_bytes` NIE jest parametrem toola (hardcoded 64KB).
> Mniej surface area dla LLM, prostsze API. Arch plan zaktualizowany.

---

## Kolejnosc wykonania (dependency graph)

```
Krok 1: shell_security.py  ─────┐
                                 ├──→ Krok 3: __init__.py ──→ Krok 6: tests
Krok 2: shell_execute.py  ──────┘                              ↑
                                                                │
Krok 4: heartbeat.py  ─────────────────────────────────────────┘
Krok 5: subagent.py   ─────────────────────────────────────────┘
```

**Rekomendowana kolejnosc:**
1. `shell_security.py` (standalone, zero deps)
2. `shell_execute.py` (depends on 1)
3. `__init__.py` (depends on 2)
4. `heartbeat.py` (independent, 1 line)
5. `subagent.py` (independent, 1 line)
6. `test_tools_shell.py` (depends on all above)

Kroki 4 i 5 moga byc wykonane rownolegle z 1-3.

---

## Krok 1: CREATE `tools/shell_security.py` (~120 linii)

**Sciezka:** `custom_components/homeclaw/tools/shell_security.py`
**Akcja:** CREATE
**Zaleznosci:** Brak (standalone modul, zero importow z projektu)

### Struktura

```python
# tools/shell_security.py
from __future__ import annotations

import logging
import re
import shlex
from enum import Enum
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# --- Constants ---
MAX_COMMAND_LENGTH = 1024

class CommandClassification(Enum):
    SAFE = "SAFE"
    REJECTED = "REJECTED"

# --- Allowlist / Blocklist (frozensets + compiled regex) ---
ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "ls", "cat", "head", "tail", "wc", "file", "stat",
    "df", "du", "free", "uptime", "uname", "date", "whoami", "id", "hostname", "ps",
    "grep", "find", "jq", "sort", "uniq", "cut",
})

BLOCKED_COMMANDS: frozenset[str] = frozenset({
    "rm", "rmdir", "mv", "cp", "chmod", "chown", "chroot",
    "sudo", "su", "dd", "mkfs", "mount", "umount",
    "kill", "killall", "pkill", "reboot", "shutdown", "halt",
    "systemctl", "service", "init",
    "wget", "curl", "nc", "ncat", "socat", "ssh", "scp",
    "python", "python3", "perl", "ruby", "node", "bash", "sh",
    "eval", "exec", "source", "export", "unset", "alias",
    "apt", "apt-get", "apk", "pip", "npm", "docker",
    "iptables", "ip", "ifconfig", "route",
    "passwd", "useradd", "userdel", "groupadd", "crontab", "at",
    "sed", "awk", "ha",
})

_BLOCKLIST_PATTERN: re.Pattern = re.compile(r"[;&|><`]|\$\(|\$\{|\.\.|~")

ALLOWED_PATH_PREFIXES: tuple[str, ...] = ("/config/", "/share/", "/tmp/", "/var/log/")

BLOCKED_PATHS: frozenset[str] = frozenset({
    "/config/secrets.yaml", "/config/home-assistant_v2.db",
    "/etc/shadow", "/etc/passwd",
})

BLOCKED_PATH_PREFIXES: tuple[str, ...] = (
    "/config/.storage/", "/config/.cloud/", "/ssl/", "/proc/",
)

ALLOWED_PROC_PATHS: frozenset[str] = frozenset({
    "/proc/cpuinfo", "/proc/meminfo", "/proc/uptime",
})

_BLOCKED_FILENAME_PATTERN: re.Pattern = re.compile(
    r"(^|/)("
    r"secrets\.(yaml|json)"
    r"|\.env(\..*)?$"
    r"|.*\.(pem|key|p12|pfx|jks)$"
    r"|.*_token(\..+)?$"
    r"|.*_credential.*"
    r"|.*_password.*"
    r")",
    re.IGNORECASE,
)

ALLOWED_TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".yaml", ".yml", ".json", ".log", ".txt", ".conf",
    ".cfg", ".ini", ".xml", ".csv", ".md", ".toml",
})

FIND_BLOCKED_FLAGS: frozenset[str] = frozenset({"-exec", "-execdir", "-delete", "-ok"})
TAIL_BLOCKED_FLAGS: frozenset[str] = frozenset({"-f", "--follow", "-F"})

SANDBOX_ENV: dict[str, str] = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp/homeclaw_shell",
    "LANG": "C.UTF-8",
}

SANDBOX_CWD = "/tmp/homeclaw_shell"
```

### Public API (5 funkcji)

```python
def validate_command(command: str) -> tuple[CommandClassification, str | None, list[str] | None]:
    """Validate a shell command against security rules.

    Pipeline:
      Step 0: Length + empty check
      Step 1: Blocklist pattern scan (raw string)
      Step 2: shlex.split() — parse tokens
      Step 3: Blocked commands check (tokens[0])
      Step 4: Allowlist prefix match (tokens[0])
      Step 5: Argument sanitization (find flags, path validation)

    Returns:
        Tuple of (classification, rejection_reason, parsed_tokens).
        If REJECTED, tokens is None.
    """

def validate_path(path_str: str) -> tuple[bool, str | None]:
    """Validate a file path against allowed/blocked rules.
    Uses Path.resolve() for symlink resolution.
    Returns: (is_allowed, rejection_reason)
    """

def validate_file_extension(path_str: str, command: str) -> tuple[bool, str | None]:
    """Check if file extension is allowed for read commands (cat/head/tail).
    Returns: (is_allowed, rejection_reason)
    """

def get_sandbox_env() -> dict[str, str]:
    """Return sanitized environment for subprocess execution."""

def sanitize_command_for_log(command: str) -> str:
    """Redact sensitive paths in command string for safe audit logging.

    Replaces paths matching blocked patterns (secrets.yaml, .storage/, etc.)
    with [REDACTED]. Used by _audit_log() in shell_execute.py.
    """
```

### Kluczowe decyzje implementacyjne
- `validate_command()` zwraca 3-tuple: `(classification, reason, tokens)` — tokens potrzebne do `create_subprocess_exec()`
- Null bytes (`\x00`) stripowane na wejsciu
- URL-encoded patterns (`%XX`) odrzucane
- Unicode normalizacja: `unicodedata.normalize("NFKC", command)` przed shlex
- `find` z `-exec`/`-delete` → REJECTED
- **rev4 (FIX B5):** `tail -f` / `tail --follow` → REJECTED (argument sanitization)
- Sciezki w argumentach `cat`/`head`/`tail`/`grep`/`ls` walidowane przez `validate_path()`
- `Path.resolve()` w `validate_path()` — symlink resolution
- **rev4 (FIX B5):** `cat`/`head`/`tail` ograniczone do text-like extensions (ALLOWED_TEXT_EXTENSIONS)
- **rev4 (FIX B3):** Dodac `sanitize_command_for_log(command)` — redakcja sciezek do secrets przed logowaniem

---

## Krok 2: CREATE `tools/shell_execute.py` (~150 linii)

**Sciezka:** `custom_components/homeclaw/tools/shell_execute.py`
**Akcja:** CREATE
**Zaleznosci:** Krok 1 (`shell_security.py`)

### Struktura

```python
# tools/shell_execute.py
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, ClassVar

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier
from .shell_security import (
    CommandClassification,
    SANDBOX_CWD,
    validate_command,
    get_sandbox_env,
)

_LOGGER = logging.getLogger(__name__)

# --- Resource limits ---
DEFAULT_TIMEOUT = 30
MIN_TIMEOUT = 5
MAX_TIMEOUT = 120
MAX_OUTPUT_BYTES = 65536  # 64KB
MAX_RATE_PER_MINUTE = 10

# --- Concurrency ---
_semaphore = asyncio.Semaphore(1)
_rate_timestamps: list[float] = []


@ToolRegistry.register
class SafeShellExecuteTool(Tool):
    """Execute read-only shell commands for system diagnostics."""

    id: ClassVar[str] = "safe_shell_execute"
    description: ClassVar[str] = (
        "Execute a read-only shell command for system diagnostics. "
        "Allowed: ls, cat, head, tail, grep, find, df, free, uptime, ps, jq, etc. "
        "Blocked: rm, sudo, curl, python, docker, and all write/network commands. "
        "Paths restricted to /config/, /share/, /tmp/, /var/log/."
    )
    short_description: ClassVar[str] = (
        "Run read-only shell commands (ls, cat, grep, df, ps) for diagnostics"
    )
    category: ClassVar[ToolCategory] = ToolCategory.UTILITY
    tier: ClassVar[ToolTier] = ToolTier.ON_DEMAND
    parameters: ClassVar[list[ToolParameter]] = [
        ToolParameter(
            name="command",
            type="string",
            description="Shell command to execute (e.g. 'ls -la /config/', 'df -h')",
            required=True,
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Timeout in seconds (default: 30, min: 5, max: 120)",
            required=False,
            default=DEFAULT_TIMEOUT,
        ),
    ]

    async def execute(self, **params: Any) -> ToolResult:
        """Execute a validated shell command."""
        # 1. Extract params, clamp timeout
        # 2. Rate limit check → reject if exceeded
        # 3. validate_command() → reject if REJECTED
        # 4. Acquire semaphore
        # 5. _run_subprocess(tokens, timeout)
        # 6. _audit_log(...)
        # 7. Return ToolResult with structured metadata

    def _clamp_timeout(self, timeout: Any) -> int:
        """Clamp timeout to [MIN_TIMEOUT, MAX_TIMEOUT]."""

    def _check_rate_limit(self) -> bool:
        """Check if rate limit exceeded. Cleans old timestamps."""

    def _audit_log(self, command: str, classification: str, user_id: str = "", **kwargs: Any) -> None:
        """Emit structured audit log entry via _LOGGER.info().

        ⚠️ rev4 (FIX B3): Redacts sensitive data from command string before logging.
        Uses _user_id from tool_executor context (injected as _user_id param).
        ⚠️ rev4 (FIX C2): Includes user_id in audit entry for traceability.
        """

    async def _run_subprocess(
        self, tokens: list[str], timeout: int
    ) -> tuple[str, str, int | None, int, bool]:
        """Run subprocess with sandbox and streaming output cap.

        Returns: (stdout, stderr, exit_code, duration_ms, truncated)
        """
        # os.makedirs(SANDBOX_CWD, mode=0o700, exist_ok=True)
        # asyncio.create_subprocess_exec(*tokens, stdout=PIPE, stderr=PIPE, cwd=..., env=...)
        # asyncio.wait_for() with timeout
        #
        # ⚠️ rev4 (FIX B2): ROWNOLEGLE czytanie stdout i stderr zeby uniknac deadlocka:
        #   stdout_data, stderr_data = await asyncio.gather(
        #       proc.stdout.read(MAX_OUTPUT_BYTES),
        #       proc.stderr.read(MAX_OUTPUT_BYTES),
        #   )
        # Potem: sprawdz truncation na stdout (extra = await proc.stdout.read(1))
        # On timeout: proc.kill() + await proc.wait()
        # Decode: .decode("utf-8", errors="replace")
```

### Kluczowe decyzje implementacyjne
- `_semaphore` i `_rate_timestamps` na poziomie modulu (nie instancji) — singleton behavior
- `_run_subprocess()` wydzielona metoda (~40 linii) — izoluje asyncio complexity
- `os.makedirs(SANDBOX_CWD, mode=0o700, exist_ok=True)` przed exec
- `asyncio.create_subprocess_exec(*tokens, stdout=PIPE, stderr=PIPE, cwd=..., env=...)`
- **NIGDY** `shell=True`
- **rev4 (FIX B2):** Rownolegle czytanie stdout/stderr: `asyncio.gather(proc.stdout.read(MAX), proc.stderr.read(MAX))` — zapobiega deadlockowi gdy jeden bufor sie zapcha
- Po read: sprawdz czy jest wiecej danych (`extra = await proc.stdout.read(1)`) → `truncated=True`
- Na timeout: `proc.kill()` + `await proc.wait()` (reap zombie)
- Decode: `stdout_data.decode("utf-8", errors="replace")`
- **rev4 (FIX B3):** Audit: `_LOGGER.info("shell_audit: %s", json.dumps({...}))` z redakcja wrazliwych danych (sciezki do secrets zamieniane na `[REDACTED]`)
- **rev4 (FIX C2):** Audit entry zawiera `user_id` z kontekstu `_user_id` (wstrzykiwany przez tool_executor)
- **rev4 (FIX B5):** `tail -f` / `tail --follow` blokowane w argument sanitization
- **rev4 (FIX B4):** `max_output_bytes` NIE jest parametrem toola — hardcoded 64KB

---

## Krok 3: MODIFY `tools/__init__.py` (~3 linie zmian)

**Sciezka:** `custom_components/homeclaw/tools/__init__.py`
**Akcja:** MODIFY

### Zmiany

1. **Import block (linia 51-63)** — dodac `shell_execute`:
```python
from . import (
    channel_status,
    context7,
    ha_native,
    identity,
    integration_manager,
    load_tool,
    memory,
    scheduler,
    shell_execute,  # ← NEW
    subagent,
    webfetch,
    websearch,
)
```

2. **`__all__` (linia 76-97)** — dodac `"shell_execute"`:
```python
    "scheduler",
    "shell_execute",  # ← NEW
    "subagent",
```

**UWAGA:** `shell_security.py` NIE jest importowany w `__init__.py` — jest internal module.

---

## Krok 4: MODIFY `proactive/heartbeat.py` (~1 linia)

**Sciezka:** `custom_components/homeclaw/proactive/heartbeat.py`
**Akcja:** MODIFY

Dodac `"safe_shell_execute"` do `HEARTBEAT_DENIED_TOOLS` frozenset (linia ~71):
```python
        "identity_set",
        "safe_shell_execute",  # ← NEW
    }
)
```

---

## Krok 5: MODIFY `core/subagent.py` (~1 linia)

**Sciezka:** `custom_components/homeclaw/core/subagent.py`
**Akcja:** MODIFY

Dodac `"safe_shell_execute"` do `DENIED_TOOLS` frozenset (linia ~56):
```python
        "set_entity_state",
        "safe_shell_execute",  # ← NEW
    }
)
```

---

## Krok 6: CREATE `tests/test_tools_shell.py` (~250 linii)

**Sciezka:** `tests/test_tools_shell.py`
**Akcja:** CREATE
**Zaleznosci:** Kroki 1-5

### Grupy testow

#### A. `TestCommandValidation` (~18 testow)
- Allowed commands: ls, cat, df, free, uptime, ps, grep, find, jq, head/tail
- Blocked patterns: `;`, `|`, `>`, `` ` ``, `$(`, `${`, `..`, `~`
- Blocked commands: rm, sudo, curl, python, docker, ha, bash
- Edge cases: empty, whitespace, >1024 chars, null bytes, unknown command, malformed quotes
- Argument sanitization: find -exec, find -delete
- **rev4:** `tail -f` blocked, `tail --follow` blocked, `tail -n 50` allowed
- **rev4:** `grep pattern /config/a.yaml /config/b.yaml` — multi-path validation

#### B. `TestPathValidation` (~12 testow)
- Allowed: /config/, /share/, /tmp/, /var/log/
- Blocked: /etc/shadow, /etc/passwd, secrets.yaml, .storage/, .cloud/, /ssl/
- Blocked: /proc/self/environ (allowed: /proc/cpuinfo)
- Path traversal: /config/../../etc/shadow → resolved
- Symlink: mock Path.resolve()

#### C. `TestFileExtensionValidation` (~4 testy)
- Allowed: .yaml, .json, .log, .txt
- Blocked: .db, .bin, no extension

#### D. `TestFilenamePatterns` (~6 testow)
- secrets.yaml, .pem, .env, *_token, *_credential, normal.yaml

#### E. `TestSandboxEnv` (~3 testy)
- Minimal env, no SUPERVISOR_TOKEN, has PATH

#### F. `TestSafeShellExecuteTool` (~17 testow)
- Registration, metadata, successful execution, rejected, timeout, truncation
- stderr, nonzero exit, duration, binary output, shlex error
- Timeout clamping (min/max), audit log, rate limit
- **rev4:** audit log contains `user_id` from `_user_id` context
- **rev4:** audit log redacts sensitive paths (secrets.yaml → [REDACTED])
- **rev4:** concurrent stdout+stderr read (asyncio.gather mock)

#### G. `TestShellIntegration` (~4 testy)
- denied_in_heartbeat, denied_in_subagent, on_demand_listed, execute_via_registry

**Total: ~64 test cases**

### Mock strategy
- `asyncio.create_subprocess_exec` → `AsyncMock` returning mock process
- `pathlib.Path.resolve` → mock for symlink tests
- `_LOGGER` → mock for audit log verification
- **ZADNE prawdziwe komendy shell** — 100% mocked subprocess

### Fixtures
```python
@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Clear rate limit timestamps between tests."""
    from custom_components.homeclaw.tools import shell_execute
    shell_execute._rate_timestamps.clear()
    yield
    shell_execute._rate_timestamps.clear()

@pytest.fixture
def tool():
    """Create a SafeShellExecuteTool instance."""
    return SafeShellExecuteTool()
```

---

## Podzial odpowiedzialnosci miedzy moduly

| Odpowiedzialnosc | `shell_security.py` | `shell_execute.py` |
|---|---|---|
| Allowlist/blocklist definitions | ✅ | ❌ |
| Command parsing (shlex) | ✅ | ❌ |
| Path validation + resolve() | ✅ | ❌ |
| Filename pattern blocking | ✅ | ❌ |
| File extension check | ✅ | ❌ |
| Sandbox env definition | ✅ | ❌ (imports) |
| Tool class + registration | ❌ | ✅ |
| Subprocess execution | ❌ | ✅ |
| Timeout + kill + reap | ❌ | ✅ |
| Output streaming + truncation | ❌ | ✅ |
| Rate limiting | ❌ | ✅ |
| Semaphore (serial exec) | ❌ | ✅ |
| Audit logging | ❌ | ✅ |
| ToolResult construction | ❌ | ✅ |

**Zasada:** `shell_security.py` = **pure validation** (zero I/O, zero async, zero side effects).
`shell_execute.py` = **orchestration** (async, subprocess, logging).

---

## Ryzyka

| # | Ryzyko | Severity | Mitigation |
|---|--------|----------|------------|
| R1 | `Path.resolve()` na nieistniejacej sciezce | LOW | Dziala (normalizuje bez I/O). Subprocess zwroci error. |
| R2 | Module-level `_semaphore` po HA restart | LOW | Nowy event loop → nowy import → nowy semaphore. OK. |
| R3 | `_rate_timestamps` rosnie bez limitu | LOW | Czyscic stare timestamps (>60s) w `_check_rate_limit()`. |
| R4 | Unicode homoglyphs (`rm` zamiast `rm`) | MEDIUM | `unicodedata.normalize("NFKC", command)` przed shlex. |
| R5 | `os.makedirs(SANDBOX_CWD)` fail | LOW | Graceful error w ToolResult, nie crash. |
| R6 | `proc.stdout.read(MAX)` zwraca mniej niz MAX | MEDIUM | Po read sprawdz `extra = await proc.stdout.read(1)` → truncated. |
| R7 | TOCTOU race (path check → symlink → read) | MEDIUM | Akceptowalne w MVP. Open-then-check w v2. |
| R8 | ~~Deadlock stdout/stderr~~ | ~~HIGH~~ | **rev4 RESOLVED:** `asyncio.gather()` na obu streamach rownoczesnie. |
| R9 | Audit log leakuje wrazliwe sciezki | MEDIUM | **rev4 RESOLVED:** `sanitize_command_for_log()` redaguje sciezki secrets. |

### Notatka: Rate limiter (C1)
Istnieje `ChannelRateLimiter` w `channels/base.py` (per-user, minute+hour windows).
Shell tool potrzebuje prostszego global limiter (10/min, bez per-user).
**Decyzja:** Inline implementation w MVP (prostsza, ~10 linii). Jesli pojawi sie trzeci
rate limiter w repo, wydzielic shared utility.

---

## Acceptance Criteria (Definition of Done)

### Pliki
- [ ] `tools/shell_security.py` istnieje, < 150 linii
- [ ] `tools/shell_execute.py` istnieje, < 180 linii
- [ ] `tests/test_tools_shell.py` istnieje, ≥ 30 test cases
- [ ] `tools/__init__.py` ma import `shell_execute` i wpis w `__all__`
- [ ] `proactive/heartbeat.py` ma `"safe_shell_execute"` w `HEARTBEAT_DENIED_TOOLS`
- [ ] `core/subagent.py` ma `"safe_shell_execute"` w `DENIED_TOOLS`

### Security
- [ ] ZERO uzyc `shell=True` w calym module
- [ ] ZERO uzyc `os.system()`, `subprocess.call()`, `eval()`, `exec()`
- [ ] Allowlist jest deny-by-default
- [ ] Blocklist pokrywa: `;`, `&`, `|`, `>`, `<`, `` ` ``, `$(`, `${`, `..`, `~`
- [ ] `secrets.yaml`, `.storage/`, `.cloud/`, `/ssl/` — hard blocked
- [ ] `SANDBOX_ENV` nie zawiera `SUPERVISOR_TOKEN`
- [ ] `Path.resolve()` uzywany przed sprawdzeniem allowed paths
- [ ] `proc.kill()` + `proc.wait()` na timeout (no zombies)
- [ ] **rev4:** stdout/stderr czytane rownolegle (`asyncio.gather`) — brak deadlocka
- [ ] **rev4:** audit log redaguje wrazliwe sciezki (sanitize_command_for_log)
- [ ] **rev4:** `tail -f` / `tail --follow` blokowane
- [ ] **rev4:** `cat`/`head`/`tail` ograniczone do text-like extensions

### Quality
- [ ] `pytest tests/test_tools_shell.py -v` — all pass
- [ ] `pytest tests/ -v` — all pass (no regressions)
- [ ] `black --check` — pass
- [ ] `isort --check` — pass
- [ ] `flake8` — pass
- [ ] `bandit -r` — clean (or only expected B603)
- [ ] Zadne f-strings w logger calls
- [ ] Coverage ≥ 70%

### Smoke tests (po deploy)
- [ ] `load_tool("safe_shell_execute")` → success
- [ ] `safe_shell_execute(command="ls -la /config/")` → stdout
- [ ] `safe_shell_execute(command="df -h")` → disk usage
- [ ] `safe_shell_execute(command="rm -rf /")` → REJECTED
- [ ] `safe_shell_execute(command="cat /config/configuration.yaml")` → content
- [ ] `safe_shell_execute(command="cat /config/secrets.yaml")` → REJECTED
- [ ] `safe_shell_execute(command="cat /etc/shadow")` → REJECTED
- [ ] `safe_shell_execute(command="ha core logs")` → REJECTED
- [ ] `safe_shell_execute(command="docker ps")` → REJECTED
- [ ] `safe_shell_execute(command="ls; rm -rf /")` → REJECTED

---

## Komendy weryfikacyjne (copy-paste ready)

```bash
# 1. Testy nowego toola
pytest tests/test_tools_shell.py -v

# 2. Wszystkie testy (regression)
pytest tests/ -v

# 3. Linting
black --check custom_components/homeclaw/tools/shell_security.py custom_components/homeclaw/tools/shell_execute.py tests/test_tools_shell.py
isort --check custom_components/homeclaw/tools/shell_security.py custom_components/homeclaw/tools/shell_execute.py tests/test_tools_shell.py
flake8 custom_components/homeclaw/tools/shell_security.py custom_components/homeclaw/tools/shell_execute.py

# 4. Security scan
bandit -r custom_components/homeclaw/tools/shell_security.py custom_components/homeclaw/tools/shell_execute.py

# 5. Coverage
pytest tests/ --cov=custom_components/homeclaw --cov-fail-under=70 -v

# 6. Deploy
./deploy.sh
ssh root@192.168.1.109 "ha core restart"
```

---

## Estimated Effort

| Krok | Scope | Effort | Risk |
|------|-------|--------|------|
| 1. shell_security.py | Pure validation module | ~45 min | Low |
| 2. shell_execute.py | Tool class + subprocess | ~60 min | Medium |
| 3. __init__.py | 3 linie zmian | ~2 min | None |
| 4. heartbeat.py | 1 linia | ~1 min | None |
| 5. subagent.py | 1 linia | ~1 min | None |
| 6. test_tools_shell.py | ~58 test cases | ~90 min | Low |
| **Total** | **MVP** | **~3.5h** | **Medium** |

---

## Changelog (rev4 — post-review)

| # | Severity | Zrodlo | Fix |
|---|----------|--------|-----|
| B1 | BLOCKER | @reviewer-rlm | Wyczyszczono sprzecznosc NEEDS_CONFIRM w PLAN sekcja 12 |
| B2 | BLOCKER | @reviewer-rlm | stdout/stderr read zmieniony na `asyncio.gather()` (deadlock fix) |
| B3 | BLOCKER | @reviewer-rlm | Dodano `sanitize_command_for_log()` — redakcja wrazliwych sciezek w audit |
| B4 | BLOCKER | @reviewer-rlm | `max_output_bytes` usuniety z parametrow toola (hardcoded 64KB) |
| B5 | BLOCKER | @reviewer-rlm | Zamknieto decyzje: extension policy (TAK), `tail -f` (BLOKOWANY) |
| B6 | BLOCKER | Codex + @reviewer-rlm | `List[...]` → `list[...]` (nowoczesna skladnia per AGENTS.md) |
| C1 | CONCERN | @reviewer-rlm | Notatka o rate limiter reuse (inline w MVP, shared utility jesli 3+) |
| C2 | CONCERN | @reviewer-rlm | `_user_id` dodany do audit entry |
| C3 | CONCERN | @reviewer-rlm | Dodano testy: tail -f, multi-path grep, concurrent read |
| C4 | CONCERN | @reviewer-rlm | Dodano testy: audit redaction, user_id in audit |

## Tooling Trace

- Primary agent: @master-of-disaster-rlm (orchestrator)
- Sub-agents used: @planner-rlm, @explore, @reviewer-rlm, Codex (gpt-5.3-codex)
- Tools used: mcp_read, mcp_glob, mcp_grep (codebase exploration), codex exec (review)
- Files analyzed: tools/base.py, tools/__init__.py, tools/load_tool.py, tools/ha_native.py,
  proactive/heartbeat.py, core/subagent.py, core/tool_executor.py, channels/base.py,
  tests/ directory, setup.cfg, pytest.ini, AGENTS.md
- Ralph iterations: 0 (planning only, no code)
- Review iterations: 1 (Codex + @reviewer-rlm → 6 blockers found → all resolved)
