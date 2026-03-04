"""Shell command security validation for Homeclaw.

Pure validation module — zero I/O, zero async, zero side effects.
Provides allowlist/blocklist-based command validation, path sanitization,
and audit-safe log redaction for the safe shell execution tool.
"""

from __future__ import annotations

import logging
import re
import shlex
import unicodedata
from enum import Enum
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

MAX_COMMAND_LENGTH = 1024


class CommandClassification(Enum):
    """Classification result for a shell command."""

    SAFE = "safe"
    REJECTED = "rejected"


ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {
        "ls",
        "cat",
        "head",
        "tail",
        "wc",
        "file",
        "stat",
        "df",
        "du",
        "free",
        "uptime",
        "uname",
        "date",
        "whoami",
        "id",
        "hostname",
        "ps",
        "grep",
        "find",
        "jq",
        "sort",
        "uniq",
        "cut",
    }
)

BLOCKED_COMMANDS: frozenset[str] = frozenset(
    {
        "rm",
        "rmdir",
        "mv",
        "cp",
        "chmod",
        "chown",
        "chroot",
        "sudo",
        "su",
        "dd",
        "mkfs",
        "mount",
        "umount",
        "kill",
        "killall",
        "pkill",
        "reboot",
        "shutdown",
        "halt",
        "systemctl",
        "service",
        "init",
        "wget",
        "curl",
        "nc",
        "ncat",
        "socat",
        "ssh",
        "scp",
        "python",
        "python3",
        "perl",
        "ruby",
        "node",
        "bash",
        "sh",
        "eval",
        "exec",
        "source",
        "export",
        "unset",
        "alias",
        "apt",
        "apt-get",
        "apk",
        "pip",
        "npm",
        "docker",
        "iptables",
        "ip",
        "ifconfig",
        "route",
        "passwd",
        "useradd",
        "userdel",
        "groupadd",
        "crontab",
        "at",
        "sed",
        "awk",
        "ha",
    }
)

_BLOCKLIST_PATTERN: re.Pattern[str] = re.compile(r"[;&|><`]|\$\(|\$\{|\.\.|~")

ALLOWED_PATH_PREFIXES: tuple[str, ...] = ("/config/", "/share/", "/tmp/", "/var/log/")

BLOCKED_PATHS: frozenset[str] = frozenset(
    {
        "/config/secrets.yaml",
        "/config/home-assistant_v2.db",
        "/etc/shadow",
        "/etc/passwd",
    }
)

BLOCKED_PATH_PREFIXES: tuple[str, ...] = (
    "/config/.storage/",
    "/config/.cloud/",
    "/ssl/",
    "/proc/",
)

ALLOWED_PROC_PATHS: frozenset[str] = frozenset(
    {
        "/proc/cpuinfo",
        "/proc/meminfo",
        "/proc/uptime",
    }
)

_BLOCKED_FILENAME_PATTERN: re.Pattern[str] = re.compile(
    r"(?:secrets\.(?:yaml|json))"
    r"|(?:\.env.*)"
    r"|(?:.*\.(?:pem|key|p12|pfx|jks))"
    r"|(?:.*_token.*)"
    r"|(?:.*_credential.*)"
    r"|(?:.*_password.*)",
    re.IGNORECASE,
)

ALLOWED_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".yaml",
        ".yml",
        ".json",
        ".log",
        ".txt",
        ".conf",
        ".cfg",
        ".ini",
        ".xml",
        ".csv",
        ".md",
        ".toml",
    }
)

FIND_BLOCKED_FLAGS: frozenset[str] = frozenset(
    {
        "-exec",
        "-execdir",
        "-delete",
        "-ok",
        "-okdir",
        "-fprint",
        "-fprint0",
        "-fprintf",
        "-fls",
    }
)
TAIL_BLOCKED_FLAGS: frozenset[str] = frozenset({"-f", "--follow", "-F"})
GREP_BLOCKED_FLAGS: frozenset[str] = frozenset({"-r", "-R", "--recursive"})
SORT_BLOCKED_FLAGS: frozenset[str] = frozenset({"-o", "--output"})

# Blocked long options per command — used for abbreviation-safe matching.
# Each entry maps a command to a set of long option stems (without --).
_BLOCKED_LONG_OPTIONS: dict[str, set[str]] = {
    "sort": {"output", "compress-program"},
    "grep": {"recursive"},
    "file": {"compile"},
    "tail": {"follow"},
    "find": {"exec", "execdir", "delete"},
}

# Commands that read file contents — path args need extension validation too
_FILE_READING_COMMANDS: frozenset[str] = frozenset(
    {"cat", "head", "tail", "jq", "wc", "file", "stat", "sort", "uniq", "cut"}
)

SANDBOX_ENV: dict[str, str] = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/tmp/homeclaw_shell",
    "LANG": "C.UTF-8",
}
SANDBOX_CWD = "/tmp/homeclaw_shell"


def validate_command(
    command: str,
) -> tuple[CommandClassification, str | None, list[str] | None]:
    """Validate a shell command against security rules.

    Pipeline: length check → unicode normalize → blocklist pattern →
    shlex parse → blocked commands → allowlist → argument sanitization.

    Args:
        command: Raw command string from user input.

    Returns:
        Tuple of (classification, rejection_reason, parsed_tokens).
        If REJECTED, tokens is None.
    """
    # Step 0: Length + empty check
    if not command or not command.strip():
        return CommandClassification.REJECTED, "empty command", None

    command = command.replace("\x00", "")

    if len(command) > MAX_COMMAND_LENGTH:
        return CommandClassification.REJECTED, "command exceeds max length", None

    if re.search(r"%[0-9a-fA-F]{2}", command):
        return CommandClassification.REJECTED, "URL-encoded patterns not allowed", None

    # Step 1: Unicode normalize
    command = unicodedata.normalize("NFKC", command)

    # Step 2: Blocklist pattern scan (raw string)
    match = _BLOCKLIST_PATTERN.search(command)
    if match:
        return (
            CommandClassification.REJECTED,
            "blocked shell metacharacter: %s" % match.group(),
            None,
        )

    # Step 3: shlex.split()
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return CommandClassification.REJECTED, "malformed command: %s" % exc, None

    if not tokens:
        return CommandClassification.REJECTED, "empty command after parsing", None

    base_cmd = tokens[0]

    # Step 4: Blocked commands check
    if base_cmd in BLOCKED_COMMANDS:
        return CommandClassification.REJECTED, "blocked command: %s" % base_cmd, None

    # Step 5: Allowlist prefix match
    if base_cmd not in ALLOWED_COMMANDS:
        return (
            CommandClassification.REJECTED,
            "command not in allowlist: %s" % base_cmd,
            None,
        )

    # Step 6: Argument sanitization
    rejection = _validate_arguments(base_cmd, tokens)
    if rejection:
        return CommandClassification.REJECTED, rejection, None

    return CommandClassification.SAFE, None, tokens


def _validate_arguments(base_cmd: str, tokens: list[str]) -> str | None:
    """Validate command arguments based on command type.

    Applies command-specific flag checks first, then a universal
    catch-all that validates ALL path-like arguments for every
    allowlisted command.  File-reading commands also get extension
    validation on path arguments.

    Returns rejection reason string, or None if arguments are valid.
    """
    args = tokens[1:]

    # --- command-specific flag checks ---
    if base_cmd == "find":
        for arg in args:
            if arg in FIND_BLOCKED_FLAGS:
                return "blocked find flag: %s" % arg

    elif base_cmd == "tail":
        for arg in args:
            if arg in TAIL_BLOCKED_FLAGS or arg.startswith("--fo"):
                return "blocked tail flag: %s" % arg
            if _short_flags_contain(arg, {"f", "F"}):
                return "blocked tail flag: %s" % arg

    elif base_cmd == "grep":
        for i, arg in enumerate(args):
            if arg in GREP_BLOCKED_FLAGS:
                return "blocked grep flag: %s" % arg
            if _short_flags_contain(arg, {"r", "R"}):
                return "blocked grep flag: %s" % arg
            # Block -d recurse and --directories/abbreviations with recurse value
            if arg == "-d" and i + 1 < len(args) and args[i + 1].lower() == "recurse":
                return "blocked grep flag: -d recurse"
            if (
                arg.startswith("--di")
                and "=" not in arg
                and i + 1 < len(args)
                and args[i + 1].lower() == "recurse"
            ):
                return "blocked grep flag: --directories recurse"
            if arg.startswith("--di") and "=" in arg and "recurse" in arg.lower():
                return "blocked grep flag: %s" % arg

    elif base_cmd == "sort":
        for arg in args:
            if arg in SORT_BLOCKED_FLAGS or arg.startswith("-o"):
                return "blocked sort flag: %s" % arg

    elif base_cmd == "file":
        for arg in args:
            if arg in {"-C"}:
                return "blocked file flag: %s" % arg

    # --- universal long-option abbreviation check ---
    for arg in args:
        if arg.startswith("--"):
            matched = _is_abbrev_of_blocked_long_option(arg, base_cmd)
            if matched:
                return "blocked %s flag (abbreviation of --%s): %s" % (
                    base_cmd,
                    matched,
                    arg,
                )

    # --- universal catch-all: validate every path-like arg ---
    for arg in args:
        paths = _extract_paths_from_arg(arg)
        for path in paths:
            ok, reason = validate_path(path)
            if not ok:
                return reason

            # Extension check for commands that read file contents
            if base_cmd in _FILE_READING_COMMANDS:
                ok, reason = validate_file_extension(path, base_cmd)
                if not ok:
                    return reason

    # --- bare filename pattern check (catches relative paths like "secrets.yaml") ---
    for arg in args:
        if arg.startswith("-"):
            continue
        filename = Path(arg).name
        if _BLOCKED_FILENAME_PATTERN.fullmatch(filename):
            return "blocked filename pattern: %s" % filename

    return None


def _extract_paths_from_arg(arg: str) -> list[str]:
    """Extract filesystem paths from an argument.

    Handles:
    - Direct paths: /config/foo.yaml, ./foo
    - Option=path: --files0-from=/config/secrets.yaml

    Args:
        arg: A single command-line argument.

    Returns:
        List of path strings found in the argument (0 or 1 items).
    """
    if arg.startswith("/") or arg.startswith("./"):
        return [arg]
    # Check for --option=/path or --option=./path
    if "=" in arg and arg.startswith("-"):
        _, _, value = arg.partition("=")
        if value.startswith("/") or value.startswith("./"):
            return [value]
    # Check for -X/path (short option with attached path operand)
    if arg.startswith("-") and not arg.startswith("--") and len(arg) > 2:
        # Short flag like -T/tmp or -f/config/file — the path starts after -X
        potential_path = arg[2:]
        if potential_path.startswith("/") or potential_path.startswith("./"):
            return [potential_path]
    return []


def _short_flags_contain(arg: str, blocked_chars: set[str]) -> bool:
    """Check if a short flag bundle (-abc) contains any blocked flag character.

    Args:
        arg: A single command-line argument (e.g. "-Rn", "-fq").
        blocked_chars: Set of single characters to check for.

    Returns:
        True if the arg is a short flag bundle containing a blocked char.
    """
    if not arg.startswith("-") or arg.startswith("--"):
        return False
    flag_chars = arg[1:]  # strip leading -
    return bool(blocked_chars & set(flag_chars))


def _is_abbrev_of_blocked_long_option(arg: str, base_cmd: str) -> str | None:
    """Check if a --arg is an abbreviation of any blocked long option.

    GNU utilities accept unambiguous prefixes of long options.
    This function checks if the argument (stripped of = and value)
    matches the start of any blocked long option for the command.

    Args:
        arg: A single command-line argument starting with --.
        base_cmd: The base command name.

    Returns:
        The matched blocked option name, or None if no match.
    """
    blocked = _BLOCKED_LONG_OPTIONS.get(base_cmd)
    if not blocked:
        return None

    # Strip -- prefix and any =value suffix
    option_part = arg[2:]
    if "=" in option_part:
        option_part = option_part.split("=", 1)[0]

    # Check if option_part is a prefix of any blocked option (min 2 chars to catch
    # GNU-style abbreviations like --ou for --output, --co for --compress-program)
    if len(option_part) < 2:
        return None

    for blocked_opt in blocked:
        if blocked_opt.startswith(option_part):
            return blocked_opt

    return None


def _looks_like_path(arg: str) -> bool:
    """Heuristic: does this argument look like a filesystem path?"""
    return arg.startswith("/") or arg.startswith("./")


def validate_path(path_str: str) -> tuple[bool, str | None]:
    """Validate a filesystem path against security rules.

    Resolves symlinks, checks blocked paths/prefixes, and verifies
    the path falls under an allowed prefix.

    Args:
        path_str: Raw path string to validate.

    Returns:
        Tuple of (is_allowed, rejection_reason).
    """
    try:
        resolved = str(Path(path_str).resolve())
    except (OSError, ValueError) as exc:
        return False, "invalid path: %s" % exc

    # Exact blocked paths
    if resolved in BLOCKED_PATHS:
        return False, "blocked path: %s" % resolved

    # Blocked path prefixes
    for prefix in BLOCKED_PATH_PREFIXES:
        if resolved.startswith(prefix) or resolved == prefix.rstrip("/"):
            # Special case: allowed /proc/ paths
            if resolved in ALLOWED_PROC_PATHS:
                return True, None
            return False, "blocked path prefix: %s" % prefix

    # Blocked filename patterns
    filename = Path(resolved).name
    if _BLOCKED_FILENAME_PATTERN.fullmatch(filename):
        return False, "blocked filename pattern: %s" % filename

    # Must match at least one allowed prefix
    # Also match the directory root itself (e.g. /config resolves without trailing /)
    for prefix in ALLOWED_PATH_PREFIXES:
        if resolved.startswith(prefix) or resolved == prefix.rstrip("/"):
            return True, None

    return False, "path not under allowed prefix: %s" % resolved


def validate_file_extension(path_str: str, command: str) -> tuple[bool, str | None]:
    """Validate file extension for file-reading commands.

    Args:
        path_str: Path to check.
        command: The command being used.

    Returns:
        Tuple of (is_allowed, rejection_reason).
    """
    if command not in _FILE_READING_COMMANDS:
        return True, None

    suffix = Path(path_str).suffix.lower()
    if not suffix:
        return False, "no file extension — cannot verify file type"

    if suffix not in ALLOWED_TEXT_EXTENSIONS:
        return False, "file extension not allowed for %s: %s" % (command, suffix)

    return True, None


def get_sandbox_env() -> dict[str, str]:
    """Return a copy of the sandbox environment variables.

    Returns:
        Dict of environment variables for sandboxed execution.
    """
    return dict(SANDBOX_ENV)


def sanitize_command_for_log(command: str) -> str:
    """Redact sensitive paths from a command string for audit logging.

    Replaces paths matching blocked paths, blocked prefixes, and
    blocked filename patterns with [REDACTED].

    Args:
        command: Raw command string.

    Returns:
        Sanitized command string safe for logging.
    """
    result = command

    for blocked in BLOCKED_PATHS:
        result = result.replace(blocked, "[REDACTED]")

    for prefix in BLOCKED_PATH_PREFIXES:
        result = re.sub(re.escape(prefix) + r"\S*", "[REDACTED]", result)

    result = _BLOCKED_FILENAME_PATTERN.sub("[REDACTED]", result)

    return result
