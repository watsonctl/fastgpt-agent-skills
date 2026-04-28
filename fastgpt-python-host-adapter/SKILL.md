---
name: fastgpt-python-host-adapter
description: "Build Python helpers after native FastGPT is insufficient."
---

# FastGPT Python Host Adapter

Use this skill only for the `exception-helper-approved` path in Python repos.

## Start sequence

1. Read `../fastgpt-shared/SKILL.md`.
2. Read `../fastgpt-shared/references/fastgpt-official-contracts.md`.
3. Read `../fastgpt-shared/references/migration-checklist.md`.
4. Read `../fastgpt-shared/references/patterns/python-host-adapter.md`.
5. Scan the host repo first:

```bash
python ../fastgpt-shared/scripts/scan_python_host.py --repo /absolute/repo/path --format markdown
```

## Workflow

- prove why `workflow-only` failed
- prove why `workflow+workflow-tools` failed
- confirm the user approved the exception
- keep the helper/API boundary narrow and stateless
- re-run readiness and runtime diagnostics before widening the boundary

## Guardrails

- Do not proxy the original `/chat` chain through one helper endpoint.
- Trace actual Python framework and schema conventions before designing routes.
- If imported runtime behavior is wrong, inspect `flowResponses` before blaming the helper boundary.
