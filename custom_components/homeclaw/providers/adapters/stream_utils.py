"""Shared streaming utilities for provider adapters."""

from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class SSEParser:
    """Parse Server-Sent Events from raw text chunks.

    Handles events split across chunks, multiple events in one chunk,
    multiline data fields, non-data lines, and the [DONE] sentinel.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> list[str]:
        """Feed raw text and return a list of complete event data strings."""
        self._buffer += chunk
        events: list[str] = []

        while "\n\n" in self._buffer:
            block, self._buffer = self._buffer.split("\n\n", 1)
            data_parts: list[str] = []
            for line in block.splitlines():
                if line.startswith("data:"):
                    data_parts.append(line[len("data:") :].lstrip(" "))
            if data_parts:
                events.append("\n".join(data_parts))

        return events

    def flush(self) -> list[str]:
        """Flush remaining buffer content as events."""
        remaining = self._buffer.strip()
        self._buffer = ""
        if not remaining:
            return []

        data_parts: list[str] = []
        for line in remaining.splitlines():
            if line.startswith("data:"):
                data_parts.append(line[len("data:") :].lstrip(" "))

        if data_parts:
            return ["\n".join(data_parts)]

        # No data: lines — treat raw remaining content as a single event
        return [remaining]


class ToolAccumulator:
    """Accumulate partial tool call fragments across streaming chunks.

    Handles incremental JSON args concatenation and multiple parallel
    tool calls identified by their stream index.
    """

    def __init__(self) -> None:
        # Keyed by index; stores {"id": str, "name": str | None, "args_buf": str}
        self._calls: dict[int, dict[str, Any]] = {}

    @property
    def has_pending(self) -> bool:
        """Whether there are pending tool calls."""
        return bool(self._calls)

    def add_fragment(
        self, index: int, id: str | None, name: str | None, args_delta: str
    ) -> None:
        """Add a tool call fragment by index.

        Args:
            index: Stream index identifying which parallel tool call this belongs to.
            id: Tool call ID (may be None on continuation fragments).
            name: Tool function name (may be None on continuation fragments).
            args_delta: Partial JSON args string to concatenate.
        """
        if index not in self._calls:
            self._calls[index] = {"id": id or "", "name": name or "", "args_buf": ""}

        entry = self._calls[index]
        if id is not None and not entry["id"]:
            entry["id"] = id
        if name is not None and not entry["name"]:
            entry["name"] = name
        entry["args_buf"] += args_delta

    def flush_all(self) -> list[dict[str, Any]]:
        """Flush all pending tool calls in index order.

        Returns a list of dicts with keys: id, name, args (parsed JSON or {}).
        """
        if not self._calls:
            return []

        result: list[dict[str, Any]] = []
        for index in sorted(self._calls):
            entry = self._calls[index]
            raw_args = entry["args_buf"].strip()
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                _LOGGER.debug(
                    "ToolAccumulator: malformed JSON args for index %d: %r",
                    index,
                    raw_args,
                )
                args = {}

            result.append({"id": entry["id"], "name": entry["name"], "args": args})

        self._calls = {}
        return result
