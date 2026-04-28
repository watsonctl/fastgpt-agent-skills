# Pattern: tool / capability mapping

Use this when the source system calls external tools, APIs, or deterministic helpers.

## Default capability order

1. Built-in workflow nodes (`code`, `datasetSearchNode`, `loop`, `parallelRun`, `httpRequest468` for true third-party APIs).
2. 工作流工具 when decomposition, reuse, or canvas readability matters.
3. Host Helper API only in `exception-helper-approved` mode.

## Decision table

| Source capability | Preferred FastGPT mapping |
|---|---|
| Pure formatting or local deterministic transform | `code` |
| External third-party HTTP API with clear request/response | `httpRequest468` |
| Knowledge-base retrieval | `datasetSearchNode` |
| Repeated per-item transform/retrieval | `loop` / `parallelRun` + `code` / `datasetSearchNode` |
| Reusable sub-flow or dense capability cluster | 工作流工具 (`pluginInput`/`pluginOutput`, main `pluginModule`) |
| Large host-side business flow | usually **not** a single proxy endpoint |

## Guardrails

- Do not wrap the whole source application behind one HTTP node and call that a migration.
- Split workflow tools by durable capability boundary.
- Keep workflow tools narrow enough to test and bind by exact name or appId.
- Record `bindingMode` when using workflow tools.
- Record each approved Helper API in the migration spec and readiness report.
