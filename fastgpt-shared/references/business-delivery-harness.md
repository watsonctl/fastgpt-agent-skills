# FastGPT Business Delivery Harness

Use this harness for any FastGPT agent where the user is buying the **business deliverable**, not the internal workflow shape.
It applies across QA, file/plan review, proposal generation, and other RAG / tool-orchestration / traceability agents.

## Core checks

- `task_completed`: the final artifact actually answers, reviews, or generates what the user asked for.
- `evidence_grounded`: key conclusions are supported by retrieved evidence; weak evidence is labeled as a boundary.
- `traceable_output`: citations, source locations, document spans, or decision inputs can be inspected after the run.
- `user_facing_quality`: the user sees a professional deliverable, not analyzer JSON, scores, or requery mechanics.
- `workflow_closed`: every normal path reaches the final user-visible output.
- `runtime_contract_intact`: code nodes and workflow tools receive the real runtime inputs they need; static generation data is not silently lost.
- `latency_budget`: first pass is bounded; second pass is quality-gated and capped.
- `overfit_guard`: do not encode benchmark questions, one-off logs, or single-domain phrases as general rules.
- `domain_portability`: shared patterns must transfer across QA, review, and generation; project-local heuristics stay project-local.

## Agent mapping

- **QA Agent**: answer + evidence + confidence/boundary.
- **File / plan review Agent**: findings + severity + source location + basis + remediation.
- **Proposal / plan generation Agent**: generated artifact + constraints satisfied + assumptions + evidence/boundary.

## Overfit guard

Shared FastGPT skills must not ship project-specific benchmark fixes as defaults.
The following belong in project-local context instead of shared skills unless they generalize structurally:

- customer-specific vocabulary lists
- single benchmark regressions
- one corpus's standard hierarchy or dataset routing
- one deployment's auth or sandbox quirks

Promote a rule into shared references only if it is structural, explainable, and portable.

## What good looks like

- The workflow closes reliably into one user-visible output path.
- A fast node-level success is not accepted if the business artifact is empty, generic, or missing required evidence.
- Quality recovery is bounded instead of silently becoming a 60s+ waiting game.
- Weak evidence produces a conservative, useful, clearly bounded deliverable.
- Structured citations and traceability survive even when inline cite style varies.
- The user never has to understand the internal workflow topology to trust the output.

## Delivery import-package gate

FastGPT page import ("导入配置") accepts the dashboard workflow JSON shape only:

```json
{
  "nodes": [],
  "edges": [],
  "chatConfig": {}
}
```

This applies to both main workflows and workflow tools. A workflow tool is still imported with the same top-level shape; `pluginInput` and `pluginOutput` nodes distinguish it from a main workflow.

Do not hand a user any of these as the page-import file:

- OpenAPI create payloads, such as JSON with top-level `modules`, `name`, `type`, or `workflow`.
- Template or development wrappers, such as JSON with top-level `template`.
- Generator source, manifests, readiness reports, or binding scripts.

Delivery bundles must contain a single clearly named import directory, for example `fastgpt-import/`, with only the JSON files the user should import through the FastGPT page. Put source files, template wrappers, manifests, reports, and scripts in separate directories. The handoff text must explicitly say "only import these files" and list those filenames.

Before delivery, run `scripts/validate_fastgpt_workflow.py` on every page-import JSON. Treat "top-level keys must be exactly `nodes`, `edges`, `chatConfig`" as a blocking packaging error, not as a runtime debugging issue.

## Credential-to-agent identity gate

FastGPT OpenAPI keys are app-scoped in common deployments. A host-level URL such as `https://host/api/v1/chat/completions` is not enough to identify the business agent.

Before acceptance testing, establish the exact credential identity without storing the secret:

- Maintain a local, non-secret credential inventory with agent name, base URL, app purpose, owner, expected workflow entry nodes, and a short key fingerprint such as first 8 plus last 6 characters. Never store the full key in repo docs, reports, skill files, or logs.
- If the user provides a key in chat, use it only for the current process. Do not copy it into files. After the run, update only the non-secret inventory fields if a persistent mapping is needed.
- Run a cheap identity probe before business testing: call the app with `detail=true`, then compare `responseData` node IDs/module names with the expected workflow. A scheme-review agent should show the review chain, not an unrelated `datasetSearchNode`.
- If the probe reaches a different app, stop and report `wrong_agent_key` with observed non-secret node evidence. Do not tune payloads, datasets, or prompts against the wrong app.

Acceptance claims must name the credential identity source in non-secret terms, for example "scheme-review key provided by user this session" or "local inventory entry: scheme-review / fingerprint abcd1234...xyz789".
