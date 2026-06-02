"""Tests for the approval gate (human-in-the-loop suspend/resume)."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.homeclaw.core.pending_actions import (
    _pending,
    discard_approval,
    register_approval,
    resolve_approval,
)


@pytest.mark.asyncio
class TestApprovalGate:
    def setup_method(self):
        _pending.clear()

    async def test_resolve_sets_future_result_true(self):
        future = register_approval("call-1")
        assert resolve_approval("call-1", True) is True
        assert future.result() is True

    async def test_resolve_sets_future_result_false(self):
        future = register_approval("call-1")
        resolve_approval("call-1", False)
        assert future.result() is False

    async def test_resolve_unknown_returns_false(self):
        assert resolve_approval("nonexistent", True) is False

    async def test_double_resolve_returns_false_second_time(self):
        register_approval("call-1")
        assert resolve_approval("call-1", True) is True
        assert resolve_approval("call-1", True) is False

    async def test_discard_removes_pending_and_blocks_resolve(self):
        register_approval("call-1")
        discard_approval("call-1")
        assert "call-1" not in _pending
        assert resolve_approval("call-1", True) is False

    async def test_suspend_resumes_when_resolved_from_another_task(self):
        future = register_approval("call-1")

        async def approver():
            await asyncio.sleep(0.01)
            resolve_approval("call-1", True)

        task = asyncio.create_task(approver())
        approved = await asyncio.wait_for(future, timeout=2)
        await task
        assert approved is True
