---
name: orchestrator-workbench
description: Orchestrate complex engineering tasks end-to-end by sequencing analysis, planning, coding, QA, and review with explicit quality gates and status tracking. Use when work spans multiple steps, touches multiple modules, has non-trivial risk, or needs a reliable DONE protocol.
---

# Orchestrator Workbench

## Role

Act as a conductor. Coordinate stages, enforce gates, and keep scope minimal.
Do not skip directly to coding when analysis or planning is missing.

## Stage Flow

1. Analyze
2. Plan
3. Implement
4. QA
5. Review
6. Closeout

For each stage, define:
- objective,
- constraints,
- expected output,
- verification.

## Skill Delegation Map

Use these skills when available:
- `analysis-workbench` for evidence gathering and scope mapping.
- `planning-workbench` for step decomposition and acceptance criteria.
- `coding-workbench` for implementation with minimal diff.
- `qa-workbench` for risk-based validation.
- `review-workbench` for bug/regression-focused review.

If a stage is already complete with evidence, mark it complete and move forward.

## Required Gates

- QA gate: tests/checks aligned with risk are executed or explicitly blocked with reason.
- Review gate: no unresolved critical/high findings.
- Scope gate: no unrelated edits.

Do not declare DONE before all required gates pass.

## Orchestration Output Format

Always respond in this structure:
1. Orchestration Plan
2. Execution
3. Status Board
4. Risks/Blockers
5. Next Actions

When all gates pass, end with:
`<promise>DONE</promise>`

## Status Board Template

Track stages and gates in a compact table:

| Item | Status | Evidence |
| --- | --- | --- |
| Analyze | todo/in_progress/done | files, snippets |
| Plan | todo/in_progress/done | plan + AC |
| Implement | todo/in_progress/done | changed files |
| QA gate | blocked/pass/fail | command outputs |
| Review gate | blocked/pass/fail | findings summary |
| Scope gate | blocked/pass/fail | diff check |

## Guardrails

- Prefer smallest correct next step over broad rewrites.
- Prefer evidence-backed claims over assumptions.
- Escalate blockers immediately instead of guessing.
