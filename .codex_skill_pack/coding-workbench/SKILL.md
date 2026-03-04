---
name: coding-workbench
description: Implement planned changes with minimal blast radius, targeted edits, and explicit verification. Use when requirements are clear and coding should start while preserving style, architecture, and safety constraints.
---

# Coding Workbench

## Workflow

1. Reconfirm scope and acceptance criteria.
2. Locate canonical files before creating new ones.
3. Implement the smallest working slice first.
4. Run targeted checks after each meaningful edit.
5. Keep diff focused; skip opportunistic refactors.
6. Verify behavior and summarize what changed.

## Editing Rules

- Preserve existing project conventions (naming, imports, formatting).
- Avoid generated files and build artifacts.
- Avoid unrelated dependency upgrades.
- Avoid hidden behavior changes.

## Verification Rules

- Prefer narrow checks first (targeted tests, type-check for touched scope).
- Run broader checks when risk or touched surface is high.
- Report commands executed and outcomes.
- If a check cannot run, state why and estimate residual risk.

## Completion Checklist

- Acceptance criteria satisfied.
- No unrelated files changed.
- Tests/checks aligned with risk.
- Final summary includes file references and behavior impact.

Never mark implementation done before verification evidence exists.
