---
name: review-workbench
description: Perform structured code review focused on bugs, regressions, risk, and missing tests. Use when reviewing a diff, branch, commit, or PR before merge, especially for high-impact or cross-module changes.
---

# Review Workbench

## Review Priorities

1. Correctness bugs and broken behavior.
2. Regressions and backward-compatibility risk.
3. Security and data exposure risk.
4. Missing or weak test coverage.
5. Maintainability concerns that materially affect future work.

## Workflow

1. Read intent and acceptance criteria.
2. Inspect changed files first, then nearby integration points.
3. Validate edge cases and failure paths.
4. Check test adequacy for changed behavior.
5. Produce prioritized findings with precise file references.

## Finding Format

Use:
- Severity (`P0` critical, `P1` high, `P2` medium, `P3` low)
- Impact statement
- Reproduction/trigger condition
- Recommended fix direction
- File reference with line

## Approval Rules

- Approve only when no unresolved `P0/P1` findings remain.
- If no findings, state that explicitly and list residual risks or test gaps.
- Keep summary short after findings.

Avoid style-only nitpicks unless they create real risk or cost.
