---
name: fastgpt-ts-node-host-adapter
description: "Use when native FastGPT cannot meet a TS/Node helper need. TS/Node 例外适配。"
disable-model-invocation: true
---

# FastGPT TS/Node Host Adapter

Use this skill only for the `exception-helper-approved` path in Node.js / TypeScript repos. It is a narrow operator-side integration boundary, not the AgentV2 runtime Skill and not a replacement for a native node or Workflow-Tool.

## When NOT to Use

- Do not use for ordinary workflow generation, migration, or runtime debugging.
- Do not proxy the original `/chat` chain, visual path, knowledge-base citation path, or final AgentV2 answer through a helper by default.
- Do not use a macOS helper result as proof that the FastGPT VM can load the dependency.

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

## Evidence / Stop Conditions

- Record target FastGPT version, VM OS/architecture, runtime, dependency origin, timeout/retry/cache policy, and the exact helper input/output contract.
- Stop if the helper would receive or emit a secret, arbitrary route IDs, unbounded history, raw internal URLs, or a mutable final citation list.
- Stop if the failure can be fixed in the native graph, if the target export is missing, or if remote update/publish or formal AgentV2 changes would be required.

## Evidence Commands

```bash
python3 ../fastgpt-shared/scripts/scan_ts_node_host.py --repo /absolute/repo/path --format markdown
python3 ../fastgpt-shared/scripts/validate_fastgpt_workflow.py <workflow.json>
```

## Guardrails

- Do not turn the original app into one giant helper endpoint.
- Discover host auth/test conventions from the repo before copying patterns.
- If imported runtime behavior is wrong, inspect `flowResponses` before blaming the host helper.
