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
- In FastGPT 4.14.7, treat workflow `datasetSearchNode.limit` as the single-search quote-token cap, not a chunk count. Calibrate it against the target model's `quoteMaxToken`, returned正文 coverage, prompt size, and latency; govern route count and final chunk count with separate caps.
- Treat the parent native `quoteList` and the final model's evidence bundle as different contracts: keep the full parent list for FastGPT CITE authorization, then pass a deterministic 1-5 item `quoteQA` subset to the final model. Require real chunk/dataset/collection IDs, non-empty正文, in-scope route membership, non-failure status, and ID deduplication; suppress generic low-information/deprecated records unless historical status is requested, preserve native ranking, and fail closed when the route snapshot is empty or malformed. Fall back when no valid item remains. Never assume a non-empty quoteList is already a verified evidence bundle.
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

## Benchmark Testing Patterns

These patterns support systematic RAG retrieval quality measurement, particularly for domain-specific knowledge bases (e.g., engineering standards / 工标).

### Pure retrieval workflows (no LLM)

For isolating retrieval quality from LLM generation, use a minimal three-node workflow:

```
workflowStart -> datasetSearchNode -> answerNode (outputs quoteQA directly)
```

This removes all LLM interference. The `answerNode` renders raw `quoteQA` and optionally `searchResult` for full inspection. Use this as the baseline harness before adding query analysis, reranking, or synthesis layers.

### collectionId filtering

Use `collectionIds` on `datasetSearchNode` to scope retrieval to specific documents (e.g., a single standard). This is distinct from `collectionFilterMatch` (tag-based filtering):

- `collectionIds`: explicit list of collection IDs to search within. Use when you know exactly which documents contain the target content.
- `collectionFilterMatch`: tag/attribute-based filtering. Use for dynamic or category-based scoping.

For benchmark testing, `collectionIds` is preferred because it gives deterministic, reproducible scope.

### Retrieval mode comparison matrix

Test all combinations of search mode and reranking to find the optimal configuration for your domain:

| searchMode | usingReRank | Behavior |
|---|---|---|
| `embedding` | `false` | Pure semantic vector search |
| `embedding` | `true` | Semantic search + cross-encoder rerank |
| `fullTextRecall` | `false` | Pure BM25 / Elasticsearch text match |
| `fullTextRecall` | `true` | Text match + cross-encoder rerank |
| `mixedRecall` | `false` | Hybrid (semantic + text) without rerank |
| `mixedRecall` | `true` | Hybrid + cross-encoder rerank |

Key metrics to collect per combination:
- **Top-1 hit rate**: first result contains the correct answer
- **Top-3 hit rate**: correct answer appears in top 3 results
- **Retrieval time**: end-to-end latency of the search node

For engineering standards, `mixedRecall` + `usingReRank: true` typically performs best because standard documents mix structured identifiers with natural language descriptions.

### Standard number inference

Most users ask questions without mentioning standard numbers (e.g., "what's the concrete curing requirement?" instead of "GB 50204 section 7.4"). Add an LLM node before retrieval to infer likely standard numbers from the question:

- Input: user question
- Output: array of candidate standard number strings (e.g., `["GB 50204", "GB/T 50080"]`)
- Keep the candidate list small (2-5) to avoid search drift
- Feed candidates into the search query construction step

This is a `chatNode` or `code` node placed between `workflowStart` and `datasetSearchNode`.

### Search query construction

When standard numbers are inferred, prepend them to the search query for Elasticsearch exact matching priority:

```
query = f"{standard_number} {user_question}"
```

ES indexes standard numbers as high-priority exact-match tokens. Prepending them ensures that the retrieval engine first narrows to the correct document before semantic matching within it. This is a `code` node that takes both the inferred candidates and the original user question, then constructs the final search string passed to `datasetSearchNode.userChatInput`.
