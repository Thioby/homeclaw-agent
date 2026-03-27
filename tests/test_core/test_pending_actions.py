"""Tests for pending_actions cache."""

from __future__ import annotations

import time
from custom_components.homeclaw.core.pending_actions import store_pending, pop_pending, _pending


class TestPendingActions:

    def setup_method(self):
        _pending.clear()

    def test_store_and_pop(self):
        store_pending("call-1", "create_dashboard", {"title": "Test"})
        result = pop_pending("call-1")
        assert result is not None
        assert result["tool_name"] == "create_dashboard"
        assert result["params"] == {"title": "Test"}

    def test_pop_removes_entry(self):
        store_pending("call-1", "create_dashboard", {"title": "Test"})
        pop_pending("call-1")
        assert pop_pending("call-1") is None

    def test_pop_missing_returns_none(self):
        assert pop_pending("nonexistent") is None

    def test_expired_entries_cleaned(self):
        store_pending("old", "create_dashboard", {"title": "Old"})
        _pending["old"]["timestamp"] = time.time() - 700
        store_pending("new", "create_dashboard", {"title": "New"})
        assert "old" not in _pending
        assert "new" in _pending

    def test_pop_expired_returns_none(self):
        store_pending("old", "create_dashboard", {"title": "Old"})
        _pending["old"]["timestamp"] = time.time() - 700
        assert pop_pending("old") is None
