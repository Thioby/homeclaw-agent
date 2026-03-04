---
name: planning-workbench
description: Convert analysis findings into an execution plan with acceptance criteria and verification strategy. Use after discovery is complete and before implementation, especially for multi-step, risky, or cross-module changes.
---

# Planning Workbench

## Workflow

1. Restate objective and non-goals.
2. Lock constraints:
   - platform/runtime limits,
   - compatibility constraints,
   - performance/security requirements,
   - delivery constraints.
3. Define the smallest correct change.
4. Split work into atomic steps that can be validated independently.
5. Add acceptance criteria per step.
6. Define validation commands (tests, lint, type-check, smoke checks).
7. Call out rollback and fallback strategy.

## Planning Template

Return:
- Problem statement
- Constraints
- Step-by-step plan
- Acceptance criteria
- Risk matrix (risk, impact, mitigation)
- Verification matrix (command, expected result)

## Decomposition Rules

- Keep each step small enough for one focused edit/test loop.
- Avoid bundling refactors with behavior changes.
- Mark dependencies explicitly.
- Mark blocking unknowns explicitly.

## Exit Criteria

- Plan is actionable without hidden assumptions.
- Each step has objective verification.
- Risks and mitigations are explicit.

Do not start coding while open questions remain unresolved.
