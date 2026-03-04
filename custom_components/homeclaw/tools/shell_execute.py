"""Safe shell execution tool for Homeclaw.

Provides sandboxed, allowlist-gated shell command execution with rate limiting,
audit logging, and output truncation. Uses asyncio.create_subprocess_exec
exclusively — never shell=True.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, ClassVar

from .base import Tool, ToolCategory, ToolParameter, ToolRegistry, ToolResult, ToolTier
from .shell_security import (
    SANDBOX_CWD,
    CommandClassification,
    get_sandbox_env,
    sanitize_command_for_log,
    validate_command,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
MIN_TIMEOUT = 5
MAX_TIMEOUT = 120
MAX_OUTPUT_BYTES = 65536  # 64 KB
MAX_RATE_PER_MINUTE = 10

_semaphore = asyncio.Semaphore(1)
_rate_timestamps: list[float] = []


async def _drain_pipe(
    pipe: asyncio.StreamReader | None, max_bytes: int
) -> tuple[bytes, bool]:
    """Read up to *max_bytes* from *pipe*, then drain remainder to EOF.

    Draining prevents the child process from blocking on a full pipe
    buffer, which would cause ``proc.wait()`` to hang.

    Args:
        pipe: Async stream reader (stdout or stderr).
        max_bytes: Maximum bytes to keep.

    Returns:
        Tuple of (kept_bytes, was_truncated).
    """
    if pipe is None:
        return b"", False

    data = await pipe.read(max_bytes)
    # Probe for extra data beyond the cap
    extra = await pipe.read(1)
    truncated = bool(extra)
    if truncated:
        # Continue draining to EOF so the process can finish
        while True:
            chunk = await pipe.read(65536)
            if not chunk:
                break
    return data, truncated


@ToolRegistry.register
class SafeShellExecuteTool(Tool):
    """Execute read-only shell commands in a sandboxed environment.

    Only commands from the allowlist are permitted (ls, cat, head, tail,
    grep, find, ps, df, du, free, uptime, etc.). Destructive commands
    (rm, mv, chmod, sudo, curl, python, etc.) are blocked. Shell
    metacharacters, pipes, redirects, and command chaining are rejected.

    Output is capped at 64 KB. Execution is rate-limited to 10 commands
    per minute with a concurrency limit of 1.
    """

    id: ClassVar[str] = "safe_shell_execute"
    description: ClassVar[str] = (
        "Execute a read-only shell command in a sandboxed environment. "
        "Allowed: ls, cat, head, tail, wc, file, stat, df, du, free, uptime, "
        "uname, date, whoami, id, hostname, ps, grep, find, jq, sort, uniq, cut. "
        "Blocked: rm, mv, cp, chmod, sudo, curl, wget, python, bash, docker, "
        "and all destructive/network/scripting commands. "
        "No pipes, redirects, or command chaining. "
        "Paths restricted to /config/, /share/, /tmp/, /var/log/. "
        "Output capped at 64 KB, timeout 5-120s."
    )
    short_description: ClassVar[str] = (
        "Run safe read-only shell commands (ls, cat, grep, find, ps, df, etc.)"
    )
    category: ClassVar[ToolCategory] = ToolCategory.UTILITY
    tier: ClassVar[ToolTier] = ToolTier.ON_DEMAND
    parameters: ClassVar[list[ToolParameter]] = [
        ToolParameter(
            name="command",
            type="string",
            description="Shell command to execute (must be from the allowlist)",
            required=True,
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Execution timeout in seconds (default 30, range 5-120)",
            required=False,
            default=DEFAULT_TIMEOUT,
        ),
    ]

    async def execute(self, **params: Any) -> ToolResult:
        """Execute a validated shell command.

        Args:
            **params: Must include 'command' (str). Optional: 'timeout' (int),
                '_user_id' (str, injected by ToolExecutor).

        Returns:
            ToolResult with stdout, stderr, exit code, and execution metadata.
        """
        command: str = params.get("command", "")
        timeout_raw = params.get("timeout", DEFAULT_TIMEOUT)
        user_id: str = params.get("_user_id", "")

        timeout = self._clamp_timeout(timeout_raw)

        # Validate command (pure function — safe outside semaphore)
        classification, rejection_reason, tokens = validate_command(command)

        if classification == CommandClassification.REJECTED:
            self._audit_log(
                command, classification, user_id, rejected_reason=rejection_reason
            )
            return ToolResult(
                output="",
                success=False,
                error="Command rejected: %s" % rejection_reason,
                title="Shell: rejected",
            )

        assert tokens is not None  # guaranteed by SAFE classification above

        # Everything else under semaphore for atomic rate limiting + execution
        async with _semaphore:
            # Rate limit check (atomic under semaphore)
            if self._check_rate_limit():
                self._audit_log(
                    command,
                    CommandClassification.REJECTED,
                    user_id,
                    rejected_reason="rate_limit_exceeded",
                )
                return ToolResult(
                    output="",
                    success=False,
                    error="Rate limit exceeded — max %d commands per minute"
                    % MAX_RATE_PER_MINUTE,
                    title="Shell: rate limited",
                )

            (
                stdout,
                stderr,
                exit_code,
                duration_ms,
                truncated,
            ) = await self._run_subprocess(tokens, timeout)
            _rate_timestamps.append(time.monotonic())

        self._audit_log(
            command,
            classification,
            user_id,
            exit_code=exit_code,
            duration_ms=duration_ms,
            truncated=truncated,
        )

        # Build output
        output_parts: list[str] = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append("STDERR:\n%s" % stderr)

        output_text = "\n".join(output_parts) if output_parts else "(no output)"

        metadata: dict[str, Any] = {
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "truncated": truncated,
            "command": tokens[0] if tokens else "",
        }

        success = exit_code == 0
        title = "Shell: %s (exit %s, %dms)" % (
            tokens[0] if tokens else "?",
            exit_code,
            duration_ms,
        )

        return ToolResult(
            output=output_text,
            success=success,
            error=stderr if not success and stderr else None,
            title=title,
            metadata=metadata,
        )

    def _clamp_timeout(self, timeout: Any) -> int:
        """Clamp timeout to [MIN_TIMEOUT, MAX_TIMEOUT].

        Args:
            timeout: Raw timeout value (may be non-int).

        Returns:
            Clamped integer timeout in seconds.
        """
        try:
            val = int(timeout)
        except (TypeError, ValueError):
            val = DEFAULT_TIMEOUT
        return max(MIN_TIMEOUT, min(MAX_TIMEOUT, val))

    def _check_rate_limit(self) -> bool:
        """Check if rate limit has been exceeded.

        Cleans timestamps older than 60 seconds, then checks count.

        Returns:
            True if rate limit exceeded, False otherwise.
        """
        now = time.monotonic()
        cutoff = now - 60.0

        # Remove old timestamps
        while _rate_timestamps and _rate_timestamps[0] < cutoff:
            _rate_timestamps.pop(0)

        return len(_rate_timestamps) >= MAX_RATE_PER_MINUTE

    def _audit_log(
        self,
        command: str,
        classification: CommandClassification,
        user_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Write structured audit log entry.

        Args:
            command: Original command string (will be redacted).
            classification: SAFE or REJECTED.
            user_id: User who issued the command.
            **kwargs: Additional fields (exit_code, duration_ms, truncated, rejected_reason).
        """
        entry: dict[str, Any] = {
            "timestamp": time.time(),
            "user_id": user_id,
            "command": sanitize_command_for_log(command),
            "classification": classification.value,
        }

        for key in ("exit_code", "duration_ms", "truncated", "rejected_reason"):
            if key in kwargs:
                if key == "rejected_reason" and kwargs[key]:
                    entry[key] = sanitize_command_for_log(str(kwargs[key]))
                else:
                    entry[key] = kwargs[key]

        _LOGGER.info("shell_audit: %s", json.dumps(entry, default=str))

    async def _run_subprocess(
        self,
        tokens: list[str],
        timeout: int,
    ) -> tuple[str, str, int | None, int, bool]:
        """Run a validated command as an async subprocess.

        Drains both pipes fully in parallel to prevent pipe-buffer
        deadlocks, then waits for the process.  The entire lifecycle
        (read + drain + wait) is wrapped in the timeout.

        Args:
            tokens: Parsed command tokens (already validated).
            timeout: Execution timeout in seconds.

        Returns:
            Tuple of (stdout, stderr, exit_code, duration_ms, truncated).
        """
        os.makedirs(SANDBOX_CWD, mode=0o700, exist_ok=True)

        start_time = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *tokens,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=SANDBOX_CWD,
                env=get_sandbox_env(),
            )

            try:
                # Drain both pipes in parallel to avoid deadlock
                (
                    (stdout_bytes, stdout_trunc),
                    (stderr_bytes, stderr_trunc),
                ) = await asyncio.wait_for(
                    asyncio.gather(
                        _drain_pipe(proc.stdout, MAX_OUTPUT_BYTES),
                        _drain_pipe(proc.stderr, MAX_OUTPUT_BYTES),
                    ),
                    timeout=timeout,
                )
                # Short timeout for wait — pipes are already drained
                await asyncio.wait_for(proc.wait(), timeout=5)

            except (asyncio.TimeoutError, TimeoutError):
                _LOGGER.warning(
                    "shell command timed out after %ds: %s", timeout, tokens[0]
                )
                proc.kill()
                await proc.wait()
                duration_ms = int((time.monotonic() - start_time) * 1000)
                return (
                    "",
                    "command timed out after %ds" % timeout,
                    -1,
                    duration_ms,
                    False,
                )

        except FileNotFoundError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return "", "command not found: %s" % tokens[0], 127, duration_ms, False
        except PermissionError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return "", "permission denied: %s" % tokens[0], 126, duration_ms, False
        except OSError as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return "", "OS error: %s" % exc, -1, duration_ms, False

        duration_ms = int((time.monotonic() - start_time) * 1000)
        truncated = stdout_trunc or stderr_trunc

        stdout_str = stdout_bytes.decode("utf-8", errors="replace")
        stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        return stdout_str, stderr_str, proc.returncode, duration_ms, truncated
