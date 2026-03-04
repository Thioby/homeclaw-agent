---
name: analysis-workbench
description: Perform evidence-first repository analysis before planning or coding. Use when the task is ambiguous, the codebase is large, root-cause is unknown, or you need to map existing modules and risks without reading everything.
---

# Analysis Workbench

## Workflow

1. Define the real goal in one sentence.
2. Map boundaries first:
   - list candidate folders/files,
   - identify interfaces touched by the change,
   - identify likely risk surfaces (state, persistence, auth, async, migrations).
3. Use search/slice/recurse/verify:
   - search anchors (`rg`, symbol names, API endpoints, errors),
   - read only minimal relevant slices,
   - recurse only where evidence points.
4. Extract evidence snippets with exact file locations.
5. Build 2-3 implementation hypotheses and reject weak ones with evidence.
6. Produce a concise analysis brief before any edits.

## Command Playbook

- Map files quickly:
```bash
rg --files
```

- Locate features, handlers, and risks:
```bash
rg -n "keyword|symbol|route|error_name" .
```

- Inspect a focused code window:
```bash
sed -n 'start,endp' path/to/file
```

## Output Contract

Return:
- Objective
- Scope in/out
- Findings with file references
- Risk list
- Recommended smallest safe change

Do not return a coding plan yet; return analysis only.

## Guardrails

- Prefer evidence over assumptions.
- Keep context small; avoid full-file reads unless necessary.
- Flag unknowns explicitly instead of guessing.
