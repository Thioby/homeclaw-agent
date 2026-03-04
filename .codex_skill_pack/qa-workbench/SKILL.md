---
name: qa-workbench
description: Execute risk-based QA validation before completion. Use when changes are implemented and you need to verify behavior, prevent regressions, and produce pass/fail evidence across tests, lint, type checks, and critical user paths.
---

# QA Workbench

## Workflow

1. Classify change risk:
   - high: state, persistence, auth, async, migrations, payment, external APIs,
   - medium: feature logic and UI behavior,
   - low: copy/style/docs-only.
2. Select checks proportional to risk.
3. Run checks and capture outcomes.
4. Execute focused manual scenario walkthroughs for impacted paths.
5. Report failures with reproduction steps and suspected cause.

## Suggested Check Matrix

- Python/backend:
```bash
pytest tests/ -v
flake8 custom_components/
mypy --ignore-missing-imports custom_components/
```

- Frontend:
```bash
npm run lint
npm run check
npm run build
```

Run only relevant commands for touched areas; do not run unrelated heavy suites by default.

## QA Report Format

Return:
- Scope tested
- Commands run
- Pass/fail summary
- Regressions found
- Residual risks
- Release recommendation (approve/block)

Do not claim QA pass without command output or explicit manual evidence.
