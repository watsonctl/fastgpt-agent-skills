# Pattern: RAG -> FastGPT workflow / workflow-tool bundle

## What to find in the source system

Look for these functional layers:
- query analysis / rewrite / route classification
- dataset selection / scope control
- retrieval intensity / search budget
- precision lookup by standard number / identifier
- evidence verification / chunk quality scoring
- deterministic reranking / bundle selection
- one-shot requery or citation backfill
- fallback / reference-only downgrade

## Typical mapping

| Source behavior | FastGPT mapping |
|---|---|
| Query analyzer | `chatNode` or `code` before retrieval |
| Dataset scope / variables | `chatConfig.variables` + `code` normalization |
| Dataset retrieval | `datasetSearchNode` |
| Merge quotes | `datasetConcatNode` or `code` |
| Precision lookup | `code` with static snapshot, 工作流工具, or approved Helper API only as exception |
| Verifier / judge | `chatNode` or `code` |
| Deterministic rerank | `code` |
| Citation or metadata enrichment | static snapshot in `code`, 工作流工具, or approved Helper API only as exception |
| Requery | `loop` or explicit second-pass branch |
| Fallback | `ifElseNode` + final `chatNode` prompt guardrails |

## Workflow-tool split pattern

Use `workflow+workflow-tools` when one canvas becomes too dense or when responsibilities are naturally reusable:
- resolver/metadata tool
- retrieval orchestration tool
- evidence bundling/fallback tool
- final synthesis remains in the main workflow

Keep tool calls explicit and deterministic for regulated/domain RAG; do not rely on the LLM to decide whether a critical retrieval tool runs.

## Business Delivery Harness template

Use this harness for any RAG-backed FastGPT Agent, not just QA. The workflow is accepted only when the user-facing deliverable is useful, grounded, traceable, and stable.

- `task_completed`: the final artifact answers, reviews, or generates what the user asked for.
- `evidence_grounded`: key claims are supported by retrieved evidence; weak evidence is labeled as a boundary, not hidden.
- `traceable_output`: citations, source locations, document spans, or decision inputs can be inspected after the run.
- `user_facing_quality`: the user sees a professional deliverable, not routing JSON, scoring text, or requery mechanics.
- `workflow_closed`: every normal path reaches the final answer/artifact node.
- `latency_budget`: first pass is bounded; second pass is quality-gated and capped.
- `overfit_guard`: do not encode benchmark questions, one-off logs, or single-domain phrases as general retrieval rules.
- `domain_portability`: shared patterns must transfer across QA, review, and generation agents; project-local heuristics stay project-local.

Agent mapping:
- QA: answer + evidence + confidence/boundary.
- Review: findings + severity + source location + basis + remediation.
- Generation: generated artifact + constraints satisfied + assumptions + evidence/boundary.


## Guardrails

- Treat node success as necessary but insufficient: final acceptance is the user-facing business deliverable with evidence, traceability, and stable closure.
- Preserve retrieval limits as semantic knobs, not arbitrary large numbers.
- Do not treat workflow `datasetSearchNode.limit` as token budget. For example-rag-project-style RAG, start with quick≈20 / standard≈50 / deep≈100 chunks and verify with flowResponses; 4000+ is a high-risk overload/empty-output setting.
- Do not let supporting/reference evidence impersonate primary target evidence.
- Primary evidence selection must serve the business deliverable, not just lexical similarity. Add scenario-applicability signals before prompt-tuning: question object, action, constraint, and source scope should align. Penalize adjacent-but-wrong scenarios so they remain supporting at most.
- Suppress low-information chunks such as TOC/index/preface/reference lists when the source system already does so.
- If the source system has exact-clause downgrade behavior, carry it over explicitly.
- Prefer static snapshots or workflow tools over runtime host Helper APIs.
- If `parallelRun` is unreliable for datasetSearch aggregation and you switch to `loop/loopArray`, treat task count as a latency budget: first pass should usually be ≤6 retrieval tasks; move inferred-standard/document fan-out to deferred requery/backfill.
- Deferred fan-out should be a quality-gated second pass, not a dead diagnostic field. Trigger it only for weak evidence and cap it to a small number of tasks.
- Friendly evidence-boundary fallback is part of UX quality: when evidence is adjacent or incomplete, answer with a practical conservative framework plus clear boundaries instead of a blunt “not found” message.
- For native clickable citations, ensure the main workflow records datasetSearch `quoteList` coverage for every cited collection. If retrieval happens inside workflow tools, add a main-workflow citation authorization pass with short per-collection searches. For API/history citation metrics, prefer `detail=true` and structured quote fields first; inline `[id](CITE)` markers should be reserved for key evidence-backed conclusions, not forced into every answer tail. If structured quotes exist but inline cites stay at zero, first bind each cite marker to a short key evidence summary in `evidenceDigest/finalUserPrompt`; do not jump straight to tail-style reference lists.
- Internal LLM nodes should be hidden from the user stream by default; final answer and explicit direct-answer branches are the normal exceptions.

- Query expansion should be a small concept-family lexicon, not an ever-growing benchmark phrase list. Trigger by specific concept clusters and cap additions to 3-5 terms to avoid search drift.
