---
name: fastgpt-ts-node-host-adapter
description: "Build TS/Node helpers after native FastGPT is insufficient."
---

# FastGPT TS/Node Host Adapter

Use this skill only for the `exception-helper-approved` path in Node.js / TypeScript repos.

## Start sequence

1. Read `../fastgpt-shared/SKILL.md`.
2. Read `../fastgpt-shared/references/fastgpt-official-contracts.md`.
3. Read `../fastgpt-shared/references/migration-checklist.md`.
4. Scan the host repo first:

```bash
python ../fastgpt-shared/scripts/scan_ts_node_host.py --repo /absolute/repo/path --format markdown
```

## Workflow

- prove why `workflow-only` failed
- prove why `workflow+workflow-tools` failed
- confirm the user approved the exception
- keep the helper boundary narrow and stateless
- re-run readiness and runtime diagnostics before widening the boundary

## Guardrails

- Do not turn the original app into one giant helper endpoint.
- Discover host auth/test conventions from the repo before copying patterns.
- If imported runtime behavior is wrong, inspect `flowResponses` before blaming the host helper.
