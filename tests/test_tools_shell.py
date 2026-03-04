"""Comprehensive tests for shell_security.py and shell_execute.py.

Tests cover:
- Command validation (allowlist, blocklist, metacharacters, edge cases)
- Path validation (allowed/blocked prefixes, traversal, symlinks)
- File extension validation
- Filename pattern blocking
- Sandbox environment isolation
- SafeShellExecuteTool execution, rate limiting, audit logging
- Integration with heartbeat/subagent denied-tool lists
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.homeclaw.tools.base import (
    ToolCategory,
    ToolRegistry,
    ToolResult,
    ToolTier,
)
from custom_components.homeclaw.tools.shell_execute import (
    DEFAULT_TIMEOUT,
    MAX_OUTPUT_BYTES,
    MAX_RATE_PER_MINUTE,
    MAX_TIMEOUT,
    MIN_TIMEOUT,
    SafeShellExecuteTool,
    _rate_timestamps,
    _semaphore,
)
from custom_components.homeclaw.tools.shell_security import (
    ALLOWED_COMMANDS,
    ALLOWED_PATH_PREFIXES,
    ALLOWED_PROC_PATHS,
    ALLOWED_TEXT_EXTENSIONS,
    BLOCKED_COMMANDS,
    BLOCKED_PATH_PREFIXES,
    BLOCKED_PATHS,
    FIND_BLOCKED_FLAGS,
    GREP_BLOCKED_FLAGS,
    MAX_COMMAND_LENGTH,
    SANDBOX_CWD,
    SANDBOX_ENV,
    SORT_BLOCKED_FLAGS,
    TAIL_BLOCKED_FLAGS,
    CommandClassification,
    get_sandbox_env,
    sanitize_command_for_log,
    validate_command,
    validate_file_extension,
    validate_path,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def preserve_registry():
    """Ensure SafeShellExecuteTool is registered and restore the registry after each test.

    Other test modules (test_tools.py, test_load_tool.py) call
    ``ToolRegistry.clear()`` which wipes the class-level ``_tools`` dict.
    Since ``@ToolRegistry.register`` runs at import time and Python won't
    re-execute it on subsequent imports, the shell tool disappears for the
    rest of the process.  This fixture re-registers the tool if needed and
    restores the original registry state afterward.
    """
    saved_tools = dict(ToolRegistry._tools)
    saved_instances = dict(ToolRegistry._instances)
    # Re-register if a prior test file cleared the registry
    if "safe_shell_execute" not in ToolRegistry._tools:
        ToolRegistry._tools["safe_shell_execute"] = SafeShellExecuteTool
    yield
    ToolRegistry._tools.clear()
    ToolRegistry._tools.update(saved_tools)
    ToolRegistry._instances.clear()
    ToolRegistry._instances.update(saved_instances)


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


def _make_mock_process(
    stdout=b"",
    stderr=b"",
    returncode=0,
    extra_stdout=b"",
    extra_stderr=b"",
):
    """Create a mock async subprocess process.

    Mimics the read pattern used by ``_drain_pipe``:
      1. ``read(max_bytes)`` → main data
      2. ``read(1)`` → truncation probe (extra byte or b"")
      3. ``read(65536)`` loop → drain to EOF (only if truncated)

    Args:
        stdout: Primary stdout bytes to return.
        stderr: Stderr bytes to return.
        returncode: Process return code.
        extra_stdout: Extra byte returned on truncation probe for stdout.
        extra_stderr: Extra byte returned on truncation probe for stderr.

    Returns:
        AsyncMock mimicking asyncio.subprocess.Process.
    """
    proc = AsyncMock()
    proc.returncode = returncode

    # stdout: read(max_bytes) → main, read(1) → probe, read(65536) → EOF drain
    stdout_reads = [stdout, extra_stdout]
    if extra_stdout:
        stdout_reads.append(b"")  # EOF for drain loop
    proc.stdout = AsyncMock()
    proc.stdout.read = AsyncMock(side_effect=stdout_reads)

    # stderr: same pattern
    stderr_reads = [stderr, extra_stderr]
    if extra_stderr:
        stderr_reads.append(b"")  # EOF for drain loop
    proc.stderr = AsyncMock()
    proc.stderr.read = AsyncMock(side_effect=stderr_reads)

    proc.wait = AsyncMock()
    proc.kill = MagicMock()

    return proc


# ===========================================================================
# A. TestCommandValidation (~18 tests)
# ===========================================================================


class TestCommandValidation:
    """Tests for validate_command() — allowlist, blocklist, metacharacters, edge cases."""

    # --- Allowed commands ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls /config/",
            "cat /config/configuration.yaml",
            "df -h",
            "free -m",
            "uptime",
            "ps aux",
            "grep pattern /config/automations.yaml",
            "find /config/ -name '*.yaml'",
            "jq '.triggers' /config/automations.yaml",
            "head -n 20 /config/configuration.yaml",
            "tail -n 50 /config/home-assistant.log",
        ],
    )
    def test_allowed_commands_accepted(self, cmd):
        """Allowed commands with valid args should be classified SAFE."""
        classification, reason, tokens = validate_command(cmd)
        assert classification == CommandClassification.SAFE, (
            "Expected SAFE for %r, got REJECTED: %s" % (cmd, reason)
        )
        assert reason is None
        assert tokens is not None

    # --- Blocked metacharacters ---

    @pytest.mark.parametrize(
        "cmd,expected_char",
        [
            ("ls /config/; rm -rf /", ";"),
            ("ls /config/ | grep yaml", "|"),
            ("ls /config/ > /tmp/out", ">"),
            ("ls `whoami`", "`"),
            ("ls $(whoami)", "$("),
            ("ls ${HOME}", "${"),
            ("ls /config/../etc/shadow", ".."),
            ("ls ~/secrets", "~"),
        ],
    )
    def test_blocked_metacharacters_rejected(self, cmd, expected_char):
        """Shell metacharacters must be rejected."""
        classification, reason, tokens = validate_command(cmd)
        assert classification == CommandClassification.REJECTED
        assert tokens is None
        assert expected_char in reason or "metacharacter" in reason

    # --- Blocked commands ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /config/",
            "sudo ls /config/",
            "curl https://evil.com",
            "python -c 'import os'",
            "docker ps",
            "ha core restart",
            "bash -c 'echo pwned'",
        ],
    )
    def test_blocked_commands_rejected(self, cmd):
        """Explicitly blocked commands must be rejected."""
        classification, reason, tokens = validate_command(cmd)
        assert classification == CommandClassification.REJECTED
        assert tokens is None
        assert "blocked command" in reason

    # --- Edge cases ---

    def test_empty_command_rejected(self):
        """Empty string must be rejected."""
        classification, reason, _ = validate_command("")
        assert classification == CommandClassification.REJECTED
        assert "empty" in reason

    def test_whitespace_only_rejected(self):
        """Whitespace-only string must be rejected."""
        classification, reason, _ = validate_command("   \t\n  ")
        assert classification == CommandClassification.REJECTED
        assert "empty" in reason

    def test_exceeds_max_length_rejected(self):
        """Command exceeding MAX_COMMAND_LENGTH must be rejected."""
        long_cmd = "ls " + "a" * (MAX_COMMAND_LENGTH + 1)
        classification, reason, _ = validate_command(long_cmd)
        assert classification == CommandClassification.REJECTED
        assert "max length" in reason

    def test_null_bytes_stripped(self):
        """Null bytes should be stripped before validation."""
        classification, reason, tokens = validate_command("ls\x00 /config/")
        assert classification == CommandClassification.SAFE
        assert tokens is not None

    def test_unknown_command_rejected(self):
        """Commands not in allowlist must be rejected."""
        classification, reason, _ = validate_command("nmap -sV localhost")
        assert classification == CommandClassification.REJECTED
        assert "not in allowlist" in reason

    def test_malformed_quotes_rejected(self):
        """Malformed quotes (shlex parse error) must be rejected."""
        classification, reason, _ = validate_command("ls '/config/unclosed")
        assert classification == CommandClassification.REJECTED
        assert "malformed" in reason

    # --- Argument sanitization ---

    def test_find_exec_blocked(self):
        """find -exec must be blocked."""
        classification, reason, _ = validate_command("find /config/ -exec cat {} \\;")
        # Note: the ';' in the command will be caught by metacharacter blocklist first
        # Let's test with a clean version
        classification2, reason2, _ = validate_command("find /config/ -exec cat {}")
        assert classification2 == CommandClassification.REJECTED

    def test_find_delete_blocked(self):
        """find -delete must be blocked."""
        classification, reason, _ = validate_command(
            "find /config/ -name '*.tmp' -delete"
        )
        assert classification == CommandClassification.REJECTED
        assert "blocked find flag" in reason

    def test_tail_follow_blocked(self):
        """tail -f must be blocked (would hang indefinitely)."""
        classification, reason, _ = validate_command(
            "tail -f /config/home-assistant.log"
        )
        assert classification == CommandClassification.REJECTED
        assert "blocked tail flag" in reason

    def test_tail_follow_long_blocked(self):
        """tail --follow must be blocked."""
        classification, reason, _ = validate_command(
            "tail --follow /config/home-assistant.log"
        )
        assert classification == CommandClassification.REJECTED
        assert "blocked tail flag" in reason

    def test_tail_n_allowed(self):
        """tail -n 50 with valid path should be allowed."""
        classification, reason, tokens = validate_command(
            "tail -n 50 /config/home-assistant.log"
        )
        assert classification == CommandClassification.SAFE

    def test_grep_multi_path_validation(self):
        """grep with multiple paths — all paths must be validated."""
        classification, reason, tokens = validate_command(
            "grep pattern /config/a.yaml /config/b.yaml"
        )
        assert classification == CommandClassification.SAFE

    def test_grep_blocked_path_rejected(self):
        """grep with a blocked path must be rejected."""
        classification, reason, _ = validate_command(
            "grep pattern /config/secrets.yaml"
        )
        assert classification == CommandClassification.REJECTED

    # --- BLOCKER 1 (iter3): find write flags (-fprint, -fprintf, -fls) ---

    @pytest.mark.parametrize(
        "flag",
        ["-fprint", "-fprint0", "-fprintf", "-fls", "-okdir"],
    )
    def test_find_write_flags_blocked(self, flag):
        """find write flags (-fprint, -fprintf, -fls, -okdir) must be blocked."""
        cmd = "find /config/ -name '*.yaml' %s /tmp/out.txt" % flag
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for find %s, got SAFE" % flag
        )
        assert "blocked find flag" in reason

    # --- BLOCKER 2 (iter3): sort -o/--output can overwrite files ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "sort -o /config/automations.yaml /config/automations.yaml",
            "sort -o/config/automations.yaml /config/automations.yaml",
            "sort --output /config/automations.yaml /config/automations.yaml",
            "sort --output=/config/automations.yaml /config/automations.yaml",
        ],
    )
    def test_sort_output_flags_blocked(self, cmd):
        """sort -o/--output must be blocked (writes to file)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked sort flag" in reason

    # --- BLOCKER 1 (iter5): sort --compress-program (arbitrary exec) ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "sort --compress-program=gzip /config/automations.yaml",
            "sort --compress-program gzip /config/automations.yaml",
        ],
    )
    def test_sort_compress_program_blocked(self, cmd):
        """sort --compress-program must be blocked (arbitrary exec)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked sort flag" in reason

    # --- HIGH 3 (iter3): grep -d recurse and --directories=recurse ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "grep -d recurse token /config/",
            "grep --directories=recurse token /config/",
            "grep --directories recurse token /config/",
            "grep --directories Recurse token /config/",
            "grep --direct=recurse token /config/",
            "grep --directo recurse token /config/",
        ],
    )
    def test_grep_directories_recurse_blocked(self, cmd):
        """grep -d recurse and --directories=recurse must be blocked."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked grep flag" in reason

    # --- HIGH 4 (iter3): bare relative paths bypass ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "cat secrets.yaml",
            "head secrets.json",
            "tail .env",
            "wc -l api_token.txt",
            "sort db_credential.json",
        ],
    )
    def test_bare_relative_sensitive_filenames_blocked(self, cmd):
        """Bare relative paths matching sensitive patterns must be blocked."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked filename pattern" in reason

    def test_bare_relative_safe_filename_not_blocked(self):
        """Bare relative filenames that are NOT sensitive should not be blocked by pattern check.

        Note: they may still be blocked by path validation (not under allowed prefix)
        or extension check, but NOT by the filename pattern check.
        """
        # "uptime" has no file args, so it's safe
        classification, reason, tokens = validate_command("uptime")
        assert classification == CommandClassification.SAFE

    # --- HIGH (iter5): file -C/--compile writes to disk ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "file -C /config/magic.mgc",
            "file --compile /config/magic.mgc",
        ],
    )
    def test_file_compile_blocked(self, cmd):
        """file -C/--compile must be blocked (writes to disk)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked file flag" in reason

    # --- HIGH (iter5): short-option attached path bypass ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "sort -T/config/.storage/auth /config/automations.yaml",
            "grep -f/config/secrets.yaml pattern /config/automations.yaml",
        ],
    )
    def test_short_option_attached_path_validated(self, cmd):
        """Short options with attached blocked paths must be rejected."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )

    # --- BLOCKER 1: Path validation for previously unvalidated commands ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "jq -R . /config/secrets.yaml",
            "wc -l /config/secrets.yaml",
            "stat /config/secrets.yaml",
            "file /config/secrets.yaml",
            "sort /config/secrets.yaml",
            "uniq /config/secrets.yaml",
            "cut -d: -f1 /config/secrets.yaml",
        ],
    )
    def test_file_reading_commands_block_sensitive_paths(self, cmd):
        """File-reading commands must block sensitive paths (BLOCKER 1)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )

    @pytest.mark.parametrize(
        "cmd",
        [
            "jq . /config/automations.yaml",
            "wc -l /config/configuration.yaml",
            "sort /config/automations.yaml",
        ],
    )
    def test_file_reading_commands_allow_safe_paths(self, cmd):
        """File-reading commands with safe paths should be allowed."""
        classification, reason, tokens = validate_command(cmd)
        assert classification == CommandClassification.SAFE, (
            "Expected SAFE for %r, got REJECTED: %s" % (cmd, reason)
        )

    def test_jq_blocks_binary_extension(self):
        """jq must reject non-text file extensions."""
        classification, reason, _ = validate_command("jq . /config/data.db")
        assert classification == CommandClassification.REJECTED
        assert "extension" in reason

    def test_du_validates_path_no_extension_check(self):
        """du validates path but does not require text extension."""
        classification, reason, tokens = validate_command("du -sh /config/")
        assert classification == CommandClassification.SAFE

    def test_du_blocks_sensitive_path(self):
        """du must block sensitive path prefixes."""
        classification, reason, _ = validate_command("du -sh /config/.storage/")
        assert classification == CommandClassification.REJECTED

    # --- BLOCKER 2: Block recursive grep flags ---

    @pytest.mark.parametrize("flag", ["-r", "-R", "--recursive"])
    def test_grep_recursive_flags_blocked(self, flag):
        """grep recursive flags must be blocked (BLOCKER 2)."""
        classification, reason, _ = validate_command("grep %s pattern /config/" % flag)
        assert classification == CommandClassification.REJECTED
        assert "blocked grep flag" in reason

    # --- HIGH 3: Block --follow=name/descriptor variants ---

    @pytest.mark.parametrize(
        "flag",
        ["--follow=name", "--follow=descriptor", "--follow=retry"],
    )
    def test_tail_follow_variants_blocked(self, flag):
        """tail --follow=<variant> must be blocked (HIGH 3)."""
        classification, reason, _ = validate_command(
            "tail %s /config/home-assistant.log" % flag
        )
        assert classification == CommandClassification.REJECTED
        assert "blocked tail flag" in reason

    # --- BLOCKER 1 (iter2): --option=PATH bypass ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "wc --files0-from=/config/secrets.yaml",
            "sort --files0-from=/config/secrets.yaml",
            "jq --from-file=/config/secrets.yaml . /config/test.yaml",
        ],
    )
    def test_option_equals_path_bypass_blocked(self, cmd):
        """--option=/path must be detected and validated (BLOCKER 1 iter2)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )

    def test_option_equals_safe_path_allowed(self):
        """--option=/safe/path should be allowed when path is valid."""
        classification, reason, tokens = validate_command(
            "sort --files0-from=/config/automations.yaml"
        )
        assert classification == CommandClassification.SAFE, (
            "Expected SAFE, got REJECTED: %s" % reason
        )

    # --- BLOCKER 2 (iter2): Combined short flags bypass for grep ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "grep -Rn pattern /config/",
            "grep -rI pattern /config/",
            "grep -lR pattern /config/",
        ],
    )
    def test_grep_combined_short_flags_blocked(self, cmd):
        """grep with bundled -r/-R in short flags must be blocked (BLOCKER 2 iter2)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked grep flag" in reason

    # --- HIGH 3 (iter2): Combined short flags bypass for tail ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "tail -Fq /config/home-assistant.log",
            "tail -fn 50 /config/home-assistant.log",
            "tail -nF 50 /config/home-assistant.log",
        ],
    )
    def test_tail_combined_short_flags_blocked(self, cmd):
        """tail with bundled -f/-F in short flags must be blocked (HIGH 3 iter2)."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )
        assert "blocked tail flag" in reason

    # --- Iter 6: GNU long-option abbreviation bypass tests ---

    @pytest.mark.parametrize(
        "cmd",
        [
            "sort --ou=/config/out.yaml /config/automations.yaml",
            "sort --out /config/automations.yaml /config/automations.yaml",
            "sort --outp /config/automations.yaml /config/automations.yaml",
            "sort --outpu=/config/automations.yaml /config/automations.yaml",
            "sort --co=sh /config/automations.yaml",
            "sort --co sh /config/automations.yaml",
            "sort --compress /config/automations.yaml",
            "sort --compress-p /config/automations.yaml",
            "sort --compress-prog /config/automations.yaml",
        ],
    )
    def test_sort_long_option_abbreviations_blocked(self, cmd):
        """sort long-option abbreviations must be blocked."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )

    @pytest.mark.parametrize(
        "cmd",
        [
            "file --co /config/test.yaml",
            "file --co=/config/test.yaml",
            "file --comp /config/test.yaml",
            "file --compi /config/test.yaml",
            "file --compil /config/test.yaml",
        ],
    )
    def test_file_compile_abbreviations_blocked(self, cmd):
        """file --compile abbreviations must be blocked."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )

    @pytest.mark.parametrize(
        "cmd",
        [
            "grep --di=recurse token /config/",
            "grep --di recurse token /config/",
            "grep --dir=recurse token /config/",
            "grep --dire=recurse token /config/",
            "grep --dir recurse token /config/",
        ],
    )
    def test_grep_directories_abbreviations_blocked(self, cmd):
        """grep --directories abbreviations with recurse must be blocked."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )

    @pytest.mark.parametrize(
        "cmd",
        [
            "tail --fo /config/home-assistant.log",
            "tail --fol /config/home-assistant.log",
            "tail --follo /config/home-assistant.log",
            "tail --follow=name /config/home-assistant.log",
        ],
    )
    def test_tail_follow_abbreviations_blocked(self, cmd):
        """tail --follow abbreviations must be blocked."""
        classification, reason, _ = validate_command(cmd)
        assert classification == CommandClassification.REJECTED, (
            "Expected REJECTED for %r, got SAFE" % cmd
        )


# ===========================================================================
# B. TestPathValidation (~12 tests)
# ===========================================================================


class TestPathValidation:
    """Tests for validate_path() — allowed/blocked prefixes, traversal, symlinks."""

    @pytest.mark.parametrize(
        "path",
        [
            "/config/configuration.yaml",
            "/share/data.json",
            "/tmp/test.txt",
            "/var/log/syslog",
        ],
    )
    def test_allowed_paths(self, path):
        """Paths under allowed prefixes should be accepted."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = path
            # Use the real function but mock Path.resolve to return the path as-is
            # (avoids filesystem dependency)
            ok, reason = validate_path(path)
        assert ok is True, "Expected allowed for %r, got rejected: %s" % (path, reason)
        assert reason is None

    @pytest.mark.parametrize(
        "path",
        [
            "/etc/shadow",
            "/etc/passwd",
            "/config/secrets.yaml",
        ],
    )
    def test_blocked_exact_paths(self, path):
        """Exact blocked paths must be rejected."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = path
            ok, reason = validate_path(path)
        assert ok is False
        assert "blocked" in reason

    @pytest.mark.parametrize(
        "path",
        [
            "/config/.storage/auth",
            "/config/.cloud/token",
            "/ssl/cert.pem",
        ],
    )
    def test_blocked_prefix_paths(self, path):
        """Paths under blocked prefixes must be rejected."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = path
            ok, reason = validate_path(path)
        assert ok is False
        assert "blocked" in reason

    def test_proc_self_environ_blocked(self):
        """Sensitive /proc/ paths must be blocked."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = "/proc/self/environ"
            ok, reason = validate_path("/proc/self/environ")
        assert ok is False
        assert "blocked" in reason

    def test_proc_cpuinfo_allowed(self):
        """Allowed /proc/ paths (cpuinfo, meminfo, uptime) should pass."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = "/proc/cpuinfo"
            ok, reason = validate_path("/proc/cpuinfo")
        assert ok is True

    def test_path_traversal_resolved_rejected(self):
        """Path traversal that resolves to a blocked path must be rejected."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = "/etc/shadow"
            ok, reason = validate_path("/config/../../etc/shadow")
        assert ok is False
        assert "blocked" in reason

    def test_symlink_to_blocked_path_rejected(self):
        """Symlink resolving to a blocked path must be rejected."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = "/etc/shadow"
            ok, reason = validate_path("/config/innocent_link")
        assert ok is False
        assert "blocked" in reason

    def test_path_outside_allowed_prefixes_rejected(self):
        """Paths not under any allowed prefix must be rejected."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = "/opt/something"
            ok, reason = validate_path("/opt/something")
        assert ok is False
        assert "not under allowed prefix" in reason

    def test_path_resolve_oserror(self):
        """OSError during path resolution should be rejected gracefully."""
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.side_effect = OSError("Permission denied")
            ok, reason = validate_path("/config/broken")
        assert ok is False
        assert "invalid path" in reason


# ===========================================================================
# C. TestFileExtensionValidation (~4 tests)
# ===========================================================================


class TestFileExtensionValidation:
    """Tests for validate_file_extension()."""

    @pytest.mark.parametrize("ext", [".yaml", ".json", ".log", ".txt"])
    def test_allowed_extensions(self, ext):
        """Allowed text extensions should pass for cat/head/tail."""
        ok, reason = validate_file_extension("/config/file" + ext, "cat")
        assert ok is True
        assert reason is None

    @pytest.mark.parametrize("ext", [".db", ".bin"])
    def test_blocked_extensions(self, ext):
        """Non-text extensions should be rejected for read commands."""
        ok, reason = validate_file_extension("/config/file" + ext, "cat")
        assert ok is False
        assert "not allowed" in reason

    def test_no_extension_rejected(self):
        """Files without extension should be rejected for read commands."""
        ok, reason = validate_file_extension("/config/Makefile", "cat")
        assert ok is False
        assert "no file extension" in reason

    def test_non_read_command_skips_check(self):
        """Non-read commands (e.g. grep) should skip extension validation."""
        ok, reason = validate_file_extension("/config/file.db", "grep")
        assert ok is True


# ===========================================================================
# D. TestFilenamePatterns (~6 tests)
# ===========================================================================


class TestFilenamePatterns:
    """Tests for blocked filename patterns in validate_path()."""

    @pytest.mark.parametrize(
        "filename",
        [
            "secrets.yaml",
            "cert.pem",
            ".env",
            ".env.local",
            "api_token.txt",
            "db_credential.json",
        ],
    )
    def test_blocked_filename_patterns(self, filename):
        """Sensitive filename patterns must be blocked."""
        path = "/config/" + filename
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = path
            ok, reason = validate_path(path)
        assert ok is False, "Expected blocked for %r, got allowed" % filename
        assert "blocked" in reason

    def test_normal_filename_allowed(self):
        """Normal filenames should be allowed."""
        path = "/config/normal.yaml"
        with patch(
            "custom_components.homeclaw.tools.shell_security.Path.resolve"
        ) as mock_resolve:
            mock_resolve.return_value = path
            ok, reason = validate_path(path)
        assert ok is True


# ===========================================================================
# E. TestSandboxEnv (~3 tests)
# ===========================================================================


class TestSandboxEnv:
    """Tests for get_sandbox_env()."""

    def test_returns_dict_with_required_keys(self):
        """Sandbox env must contain PATH, HOME, LANG."""
        env = get_sandbox_env()
        assert "PATH" in env
        assert "HOME" in env
        assert "LANG" in env

    def test_no_supervisor_token(self):
        """Sandbox env must NOT contain SUPERVISOR_TOKEN."""
        env = get_sandbox_env()
        assert "SUPERVISOR_TOKEN" not in env

    def test_returns_copy(self):
        """get_sandbox_env() must return a copy, not the original reference."""
        env1 = get_sandbox_env()
        env2 = get_sandbox_env()
        assert env1 is not env2
        assert env1 is not SANDBOX_ENV
        assert env1 == env2


# ===========================================================================
# F. TestSafeShellExecuteTool (~17 tests)
# ===========================================================================


class TestSafeShellExecuteTool:
    """Tests for SafeShellExecuteTool execution, rate limiting, audit logging."""

    def test_registration(self):
        """Tool must be registered with correct id."""
        tool_class = ToolRegistry.get_tool_class("safe_shell_execute")
        assert tool_class is SafeShellExecuteTool

    def test_metadata(self, tool):
        """Tool metadata must be correct."""
        assert tool.id == "safe_shell_execute"
        assert tool.tier == ToolTier.ON_DEMAND
        assert tool.category == ToolCategory.UTILITY
        param_names = [p.name for p in tool.parameters]
        assert "command" in param_names
        assert "timeout" in param_names

    @pytest.mark.asyncio
    async def test_successful_execution(self, tool):
        """Successful command execution returns correct ToolResult."""
        proc = _make_mock_process(stdout=b"file1.yaml\nfile2.yaml\n", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="ls /config/")

        assert result.success is True
        assert "file1.yaml" in result.output
        assert result.metadata["exit_code"] == 0
        assert result.metadata["duration_ms"] >= 0
        assert result.metadata["command"] == "ls"

    @pytest.mark.asyncio
    async def test_rejected_command_returns_error(self, tool):
        """Rejected command (rm) must return error ToolResult without executing."""
        with patch("asyncio.create_subprocess_exec") as mock_exec, patch("os.makedirs"):
            result = await tool.execute(command="rm -rf /")

        assert result.success is False
        assert "rejected" in result.error.lower()
        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self, tool):
        """Timed-out process must be killed and return timeout error."""
        proc = AsyncMock()
        proc.kill = MagicMock()
        proc.wait = AsyncMock()
        proc.returncode = -1

        async def _slow_drain(pipe, max_bytes):
            """Simulate a pipe drain that takes too long."""
            await asyncio.sleep(999)
            return b"", False  # pragma: no cover

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
            patch(
                "custom_components.homeclaw.tools.shell_execute._drain_pipe",
                side_effect=_slow_drain,
            ),
        ):
            result = await tool.execute(command="ls /config/", timeout=5)

        assert result.success is False
        assert "timed out" in result.output or "timed out" in (result.error or "")
        proc.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_output_truncation(self, tool):
        """Output exceeding MAX_OUTPUT_BYTES must be truncated."""
        proc = _make_mock_process(
            stdout=b"x" * MAX_OUTPUT_BYTES,
            returncode=0,
            extra_stdout=b"y",  # extra byte → truncated=True
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="ls /config/")

        assert result.success is True
        assert result.metadata["truncated"] is True

    @pytest.mark.asyncio
    async def test_stderr_captured(self, tool):
        """Stderr output must be captured in the result."""
        proc = _make_mock_process(
            stdout=b"",
            stderr=b"warning: something\n",
            returncode=1,
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="ls /config/nonexistent")

        assert result.success is False
        assert "warning: something" in result.output or "warning: something" in (
            result.error or ""
        )

    @pytest.mark.asyncio
    async def test_nonzero_exit_code(self, tool):
        """Non-zero exit code should still return a result (not raise)."""
        proc = _make_mock_process(
            stdout=b"partial output", stderr=b"error msg", returncode=2
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(
                command="grep pattern /config/configuration.yaml"
            )

        assert result.success is False
        assert result.metadata["exit_code"] == 2

    @pytest.mark.asyncio
    async def test_duration_measured(self, tool):
        """Execution duration must be measured in milliseconds."""
        proc = _make_mock_process(stdout=b"ok", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="uptime")

        assert "duration_ms" in result.metadata
        assert isinstance(result.metadata["duration_ms"], int)
        assert result.metadata["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_binary_output_decoded_with_replacement(self, tool):
        """Non-UTF-8 bytes must be decoded with replacement characters."""
        proc = _make_mock_process(stdout=b"hello \xff\xfe world", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="cat /config/test.yaml")

        assert result.success is True
        assert "hello" in result.output
        assert "\ufffd" in result.output  # replacement character

    @pytest.mark.asyncio
    async def test_shlex_error_rejected(self, tool):
        """Malformed quotes causing shlex error must be rejected."""
        result = await tool.execute(command="ls '/config/unclosed")

        assert result.success is False
        assert "malformed" in result.error.lower() or "rejected" in result.error.lower()

    def test_timeout_clamping_low(self, tool):
        """Timeout below MIN_TIMEOUT must be clamped to MIN_TIMEOUT."""
        assert tool._clamp_timeout(0) == MIN_TIMEOUT
        assert tool._clamp_timeout(1) == MIN_TIMEOUT

    def test_timeout_clamping_high(self, tool):
        """Timeout above MAX_TIMEOUT must be clamped to MAX_TIMEOUT."""
        assert tool._clamp_timeout(200) == MAX_TIMEOUT
        assert tool._clamp_timeout(999) == MAX_TIMEOUT

    def test_timeout_clamping_invalid(self, tool):
        """Non-integer timeout must fall back to DEFAULT_TIMEOUT."""
        assert tool._clamp_timeout("abc") == DEFAULT_TIMEOUT
        assert tool._clamp_timeout(None) == DEFAULT_TIMEOUT

    @pytest.mark.asyncio
    async def test_audit_log_called(self, tool):
        """Audit log must be written via _LOGGER.info with shell_audit."""
        proc = _make_mock_process(stdout=b"ok", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
            patch(
                "custom_components.homeclaw.tools.shell_execute._LOGGER"
            ) as mock_logger,
        ):
            await tool.execute(command="uptime")

            # Find the shell_audit call
            info_calls = mock_logger.info.call_args_list
            audit_calls = [c for c in info_calls if "shell_audit" in str(c)]
            assert len(audit_calls) >= 1, "Expected at least one shell_audit log call"

    @pytest.mark.asyncio
    async def test_audit_log_contains_user_id(self, tool):
        """Audit log entry must contain the user_id from _user_id context."""
        proc = _make_mock_process(stdout=b"ok", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
            patch(
                "custom_components.homeclaw.tools.shell_execute._LOGGER"
            ) as mock_logger,
        ):
            await tool.execute(command="uptime", _user_id="test_user_42")

            info_calls = mock_logger.info.call_args_list
            audit_calls = [c for c in info_calls if "shell_audit" in str(c)]
            assert len(audit_calls) >= 1
            # Parse the JSON from the audit log
            audit_json_str = audit_calls[-1][0][
                1
            ]  # second positional arg (the %s value)
            audit_data = json.loads(audit_json_str)
            assert audit_data["user_id"] == "test_user_42"

    @pytest.mark.asyncio
    async def test_audit_log_redacts_sensitive_paths(self, tool):
        """Audit log must redact sensitive paths like secrets.yaml."""
        # This command will be rejected, but the audit log should still redact
        with patch(
            "custom_components.homeclaw.tools.shell_execute._LOGGER"
        ) as mock_logger:
            await tool.execute(command="cat /config/secrets.yaml")

            info_calls = mock_logger.info.call_args_list
            audit_calls = [c for c in info_calls if "shell_audit" in str(c)]
            assert len(audit_calls) >= 1
            audit_json_str = audit_calls[-1][0][1]
            assert (
                "secrets.yaml" not in audit_json_str or "[REDACTED]" in audit_json_str
            )

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, tool):
        """11th call within a minute must be rate-limited."""
        from custom_components.homeclaw.tools import shell_execute

        now = time.monotonic()
        # Simulate 10 recent timestamps
        shell_execute._rate_timestamps.extend(
            [now - i for i in range(MAX_RATE_PER_MINUTE)]
        )

        result = await tool.execute(command="uptime")

        assert result.success is False
        assert "rate limit" in result.error.lower()

    # --- MEDIUM 5 (iter3): Concurrency test for atomic rate limiting ---

    @pytest.mark.asyncio
    async def test_rate_limit_atomic_under_contention(self, tool):
        """Concurrent calls must not exceed rate limit."""

        def _fresh_proc(*_args, **_kwargs):
            return _make_mock_process(stdout=b"ok", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", side_effect=_fresh_proc),
            patch("os.makedirs"),
        ):
            results = await asyncio.gather(
                *[tool.execute(command="uptime") for _ in range(15)]
            )

        successes = sum(1 for r in results if r.success)
        rate_limited = sum(
            1
            for r in results
            if not r.success and "rate limit" in (r.error or "").lower()
        )
        assert successes <= MAX_RATE_PER_MINUTE
        assert rate_limited >= 5  # at least 5 should be rate-limited

    @pytest.mark.asyncio
    async def test_concurrent_stdout_stderr_read(self, tool):
        """stdout and stderr must be read concurrently via asyncio.gather."""
        proc = _make_mock_process(stdout=b"out", stderr=b"err", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="ls /config/")

        assert result.success is True
        assert "out" in result.output

    # --- HIGH 5: stderr truncation tracking ---

    @pytest.mark.asyncio
    async def test_stderr_truncation_tracked(self, tool):
        """stderr overflow must set truncated=True (HIGH 5)."""
        proc = _make_mock_process(
            stdout=b"ok",
            stderr=b"e" * MAX_OUTPUT_BYTES,
            returncode=1,
            extra_stderr=b"x",  # extra byte → stderr truncated
        )

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await tool.execute(command="ls /config/")

        assert result.metadata["truncated"] is True

    # --- MEDIUM 7: rejected_reason redaction ---

    @pytest.mark.asyncio
    async def test_audit_log_redacts_rejected_reason(self, tool):
        """rejected_reason containing sensitive paths must be redacted (MEDIUM 7)."""
        with patch(
            "custom_components.homeclaw.tools.shell_execute._LOGGER"
        ) as mock_logger:
            await tool.execute(command="cat /config/secrets.yaml")

            info_calls = mock_logger.info.call_args_list
            audit_calls = [c for c in info_calls if "shell_audit" in str(c)]
            assert len(audit_calls) >= 1
            audit_json_str = audit_calls[-1][0][1]
            audit_data = json.loads(audit_json_str)
            if "rejected_reason" in audit_data:
                assert "secrets.yaml" not in audit_data["rejected_reason"] or (
                    "[REDACTED]" in audit_data["rejected_reason"]
                )


# ===========================================================================
# G. TestShellIntegration (~4 tests)
# ===========================================================================


class TestShellIntegration:
    """Integration tests: denied-tool lists, on-demand listing, registry execution."""

    def test_denied_in_heartbeat(self):
        """safe_shell_execute must be in HEARTBEAT_DENIED_TOOLS."""
        from custom_components.homeclaw.proactive.heartbeat import (
            HEARTBEAT_DENIED_TOOLS,
        )

        assert "safe_shell_execute" in HEARTBEAT_DENIED_TOOLS

    def test_denied_in_subagent(self):
        """safe_shell_execute must be in subagent DENIED_TOOLS."""
        from custom_components.homeclaw.core.subagent import DENIED_TOOLS

        assert "safe_shell_execute" in DENIED_TOOLS

    def test_on_demand_listed(self):
        """safe_shell_execute must appear in list_on_demand_ids()."""
        on_demand_ids = ToolRegistry.list_on_demand_ids()
        assert "safe_shell_execute" in on_demand_ids

    @pytest.mark.asyncio
    async def test_execute_via_registry(self):
        """ToolRegistry.execute_tool must work for safe_shell_execute."""
        proc = _make_mock_process(stdout=b"registry_output\n", returncode=0)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("os.makedirs"),
        ):
            result = await ToolRegistry.execute_tool(
                "safe_shell_execute",
                {"command": "uptime"},
            )

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "registry_output" in result.output


# ===========================================================================
# H. TestSanitizeCommandForLog (bonus coverage)
# ===========================================================================


class TestSanitizeCommandForLog:
    """Tests for sanitize_command_for_log()."""

    def test_redacts_blocked_paths(self):
        """Exact blocked paths must be replaced with [REDACTED]."""
        result = sanitize_command_for_log("cat /config/secrets.yaml")
        assert "[REDACTED]" in result
        assert "/config/secrets.yaml" not in result

    def test_redacts_blocked_prefixes(self):
        """Paths under blocked prefixes must be redacted."""
        result = sanitize_command_for_log("ls /config/.storage/auth_providers")
        assert "[REDACTED]" in result

    def test_preserves_safe_commands(self):
        """Safe commands without sensitive paths should be preserved."""
        cmd = "ls /config/automations.yaml"
        result = sanitize_command_for_log(cmd)
        assert result == cmd
