# FastGPT migration playbook

This reference preserves the detailed migration guidance that used to live in `fastgpt-workflow-migration/SKILL.md`. Load it only after the thin migration entry skill has identified the required path.

# FastGPT Workflow Migration

## When to use

Use this skill when the task is to preserve behavior while moving an existing system into FastGPT.

Typical triggers:
- code / program -> FastGPT workflow JSON
- RAG / QA pipeline -> importable FastGPT app
- parity migration with workflow tools, dataset search, loops, branches, or deterministic code nodes
- official-contract validation before import

## Start sequence

1. Read `../fastgpt-shared/references/fastgpt-official-contracts.md`.
2. Read `../fastgpt-shared/references/migration-checklist.md`.
3. Load only the pattern docs you need:
   - RAG: `../fastgpt-shared/references/patterns/rag.md`
   - Workflow tools: `../fastgpt-shared/references/patterns/workflow-tool.md`
   - Tool calls / external capabilities: `../fastgpt-shared/references/patterns/tool-calling.md`
   - Fan-out logic: `../fastgpt-shared/references/patterns/loop-parallel.md`
   - explicit downgrade/fallback: `../fastgpt-shared/references/patterns/reference-only-fallback.md`
   - visual layout: `../fastgpt-shared/references/patterns/visual-layout.md`
4. Run the parity scan first:

```bash
python ../fastgpt-shared/scripts/generate_parity_report.py --repo /absolute/repo/path --format markdown
```

## Default capability ladder

Always decide and record `migrationMode` before implementation:

1. `workflow-only` — all behavior fits in one workflow or one importable workflow JSON.
2. `workflow+workflow-tools` — use one main workflow plus one or more FastGPT 工作流工具 when decomposition improves maintainability or parity.
3. `exception-helper-approved` — only after the user explicitly approves a host Helper API exception.

Default prohibitions:
- Do not use MCP for migration output unless the user explicitly requests it.
- Do not default to repo-hosted Helper APIs.
- Do not hide the original app behind one `/chat` or `/lookup` proxy and call it a migration.

## Business Delivery Harness（迁移验收）

FastGPT 迁移不是复刻某个 workflow 形状，而是迁移业务能力。实现前必须先定义该 Agent 的业务交付物，再决定主工作流、工作流工具、RAG、FAQ、引用授权和补查链路。

交付物映射：
- QA Agent：答案、依据、证据边界、引用或结构化来源。
- 文件/方案审查 Agent：问题清单、风险等级、原文定位、依据、整改建议。
- 方案生成 Agent：方案正文、约束满足情况、依据说明、假设与边界。

迁移验收门槛：
- `task_completed`：交付物能解决用户业务问题。
- `evidence_grounded`：关键判断基于可追溯证据；弱证据不伪装成确定结论。
- `traceable_output`：输出能回到引用、文件位置、条文、数据或决策依据。
- `user_facing_quality`：最终输出不暴露内部编排、评分、补查或调试信息。
- `workflow_closed`：所有正常分支都能稳定进入最终输出。
- `latency_budget`：质量补查有限、可解释、可验收。
- `overfit_guard`：不按 benchmark 题、已见日志、单个关键词写迁移规则。
- `domain_portability`：shared 经验必须可迁移；项目局部经验只能留在项目上下文。

Workflow tools、RAG、FAQ、引用授权和补查链路都服务于交付物质量；不要让用户迁就内部工程结构。


## Core workflow

1. **Find the source of truth**
   - Trace real entrypoints, not just helper functions.
   - Identify analyzer / retrieval / verifier / rerank / fallback / HTTP / loop / parallel behavior.

2. **Build the migration spec**
   - Target output: `nodes + edges + chatConfig` for each workflow/workflow tool JSON.
   - `migrationMode` and `bindingMode`.
   - Workflow-tool split plan, if used.
   - Feature coverage matrix.
   - Import-time placeholders, secrets, dataset scopes, and appId binding needs.

3. **Scaffold only when helpful**

```bash
python ../fastgpt-shared/scripts/scaffold_fastgpt_workflow.py \
  --title "My FastGPT Workflow" \
  --output /absolute/output/workflow.json \
  --variables industry:string,datasetId:any \
  --migration-mode workflow+workflow-tools \
  --patterns direct-answer,dataset-search,workflow-tool,loop,parallel
```

4. **Refine to parity**
   - Preserve behavior, not just surface I/O.
   - Prefer `code`, `datasetSearchNode`, `loop`, and 工作流工具 decomposition before host helpers. Use `parallelRun` only after runtime proof that the target instance preserves outputs such as datasetSearch `quoteQA`.
   - For RAG migrations, build the full available dataset registry from the project SoR first, then narrow per query with deterministic routing, tags, metadata, and analyzer signals. Do not ship a tiny “core registry” when the source system can reach more datasets.
   - Split user-explicit constraints from model-inferred hints. User-explicit standard/document names may hard-lock precision lookup; inferred standards/documents are soft recall only and must not suppress FAQ or fallback retrieval.
   - Hide internal analyzer/router/verifier/planner `chatNode` output by default; use the current official `isResponseAnswerText` key and only final user-facing branches should set response-text streaming on.
   - If native FastGPT citations must be clickable, register cited collections in the main workflow with datasetSearch quoteList coverage; workflow-tool-internal retrieval alone may not be enough. For critical final chains, prefer fixed citation-auth slots over top-level parallelRun after ifElse. For primary RAG retrieval inside workflow tools, prefer loop/loopArray unless parallelRun output preservation has been verified in flowResponses.
   - When replacing `parallelRun` with `loop/loopArray` for RAG stability, cap first-pass retrieval tasks. A safe default is top 1 query × top 2 datasets × no-tag/high-confidence-tag variants (usually 4, max 6); put inferred-document/standard expansions into deferred requery tasks instead of the initial loop.
   - Do not leave deferred requery as diagnostics only. For quality parity, wire it behind a quality gate: weak evidence, low finalQuoteQA count, reference-only mode, or low answerability/support should run a bounded second pass (usually 4-6 tasks).
   - Colloquial query expansion should be concept-family based, narrowly triggered, and capped to a few high-signal terms; do not append broad industry terms to every query.
   - Use friendly evidence-boundary fallback. If direct clauses are missing, still provide a conservative practical judgment/framework with clear boundaries; avoid cold phrases like “当前知识库未直接检索到…”.
   - If API/history citation metrics matter, prefer `detail=true` and validate structured `quoteList/responseData/flowResponses` first. Final answer text should use literal `[24hex](CITE)` markers only for key evidence-backed conclusions; do not force every answer to append a tail-style reference list just to satisfy benchmarks.
   - Evidence bundling must optimize for **business deliverable quality**, not lexical score alone. Primary evidence should be chosen by scenario applicability (question object, action, constraint) ahead of broad semantic overlap; add structural penalties for adjacent-but-wrong scenarios before touching prompt wording.
   - When inline cite is unstable, fix the **binding layer** before adding harder prompt constraints: evidence digest should expose a short “key evidence summary” next to each real cite marker, and final synthesis prompts should tell the model to keep that marker when it directly adopts the summary’s conclusion.
   - Weak-boundary handling is part of business safety. If evidence only covers adjacent clauses, device conditions, or general process requirements, the migrated workflow may provide a conservative actionable judgment, but must not overstate that as a direct finding on permissions, qualifications, liabilities, or target-clause text.
   - Keep final synthesis prompts user-facing: do not expose tool calls, scoring, rerank, fallback machinery, or requery mechanics to end users.
   - Do not force LLM-generated XML such as `<suggested_questions>` into final answers. Use FastGPT `questionGuide` or UI-side follow-up generation instead.
   - If a migration still proxies all logic back to the original app, it is not a real migration.

5. **Make layout import-ready**
   - For complex workflows, relayout with `swimlane` before import.
   - For existing working workflows, keep relayout position-only.

```bash
python ../fastgpt-shared/scripts/relayout_fastgpt_workflow.py /absolute/output/workflow.json --in-place --strategy swimlane
```


### Code node generation contract

When a generator emits large JavaScript snippets into FastGPT `code` nodes, the source generator must preserve JavaScript escapes exactly. Use `String.raw` or an equivalent raw-string/template mechanism before JSON serialization; do not build regex-heavy JS with ordinary template strings that can consume `\n` / `\s` / `\d` / regex boundary escapes before export.

Before claiming import readiness, extract every generated `codeType=js` node and run a syntax-only compile gate such as Node `vm.Script`. This gate is required because FastGPT import can succeed while runtime immediately returns empty due to `Invalid regular expression` or `Invalid or unexpected token` inside a code node.

6. **Validate before claiming done**

```bash
python ../fastgpt-shared/scripts/validate_fastgpt_workflow.py /absolute/output/workflow.json
python ../fastgpt-shared/scripts/validate_fastgpt_layout.py /absolute/output/workflow.json --strategy swimlane
python ../fastgpt-shared/scripts/generate_import_readiness_report.py \
  --repo /absolute/repo/path \
  --workflow /absolute/output/workflow.json
```

7. **If runtime behavior disagrees with the static JSON, switch to runtime diagnostics before editing more**

For OpenAPI smoke tests, request `detail=true` when possible and store `responseData/flowResponses/quoteList/cite_count/datasetIds`. `detail=false` only proves the final text path, not whether RAG actually ran.

```bash
python ../fastgpt-shared/scripts/export_fastgpt_flow_logs.py \
  --base-url https://your-fastgpt-host \
  --api-key "$FASTGPT_API_KEY" \
  --app-id YOUR_APP_ID \
  --export-dir ./fastgpt-logs

python ../fastgpt-shared/scripts/analyze_fastgpt_flow_logs.py \
  --latest ./fastgpt-logs \
  --format text
```

Read `../fastgpt-shared/references/runtime-diagnostics.md` for the standard diagnosis flow.

## Required outputs

Every completed migration should produce:
- importable FastGPT workflow JSON, or a multi-JSON bundle with main workflow + 工作流工具
- `migrationMode`, `usesWorkflowTools`, `workflowToolCount`, `bindingMode`
- helper/API exception list only if exception mode was user-approved
- parity / coverage matrix
- import readiness report
- layout validation report

## Guardrails

- Use official FastGPT docs and, when version-sensitive, official source behavior; do not trust stale memory.
- When imported FastGPT behavior and local JSON reasoning diverge, export `flowResponses` and diagnose runtime inputs/outputs before changing builder logic again.
- Product wording is **工作流工具 / workflow tool**. Legacy internal fields may still say `plugin`, but do not present “plugin/system-plugin” as the user-facing mode.
- Prefer thick migration over thin proxy wrapping.
- Do not assume host-framework auth/test conventions inside this skill.
- Complex workflows default to swimlane layout; do not hand off tangled canvases unless the user explicitly accepts debug-only layout.
- Keep exact-clause / evidence / fallback semantics explicit when the source system depends on them.

## Golden example

- `../fastgpt-shared/assets/golden-examples/example-rag-project-manifest.json`
  - first bundle pattern: main workflow + multiple 工作流工具 + binding script, no MCP, no runtime Helper API; current example-rag-project golden case uses 5 tools: standard lookup, metadata, retrieval orchestration, evidence bundling, and FAQ retrieval/scoring.

## Shared resources

- Contracts: `../fastgpt-shared/references/fastgpt-official-contracts.md`
- Checklist: `../fastgpt-shared/references/migration-checklist.md`
- Scripts: `../fastgpt-shared/scripts/`
- Assets/templates: `../fastgpt-shared/assets/`

## Complex RAG default pattern: FAQ + standards + workflow tools

For engineering standards, policy/audit, document-review, proposal-generation, or other high-precision RAG agents, default to this decomposed pattern when it improves parity:

1. Main workflow performs input normalization, analysis/routing, deterministic orchestration, final citation registration, and final user-facing answer.
2. Workflow tools perform bounded subjobs:
   - FAQ retrieval/scoring for high-frequency known answers.
   - Entity/standard/document lookup.
   - Retrieval orchestration across datasets.
   - Metadata enrichment.
   - Evidence verification/ranking/fallback packaging.
3. FAQ branch runs in parallel with corpus retrieval, but must obey priority rules:
   - FAQ extreme match may dominate only if the user did not explicitly name a controlling source/standard/document.
   - FAQ medium match is supplemental context.
   - FAQ low match is discarded.
4. Corpus retrieval should express business priority in both retrieval and ranking:
   - explicit user-specified source first;
   - active/current status before deprecated/replaced;
   - authority/applicability tier next;
   - common/high-frequency source as soft convergence;
   - tags first when supported, sourceName/metadata soft ranking as fallback.
5. Registry coverage: include all source-system reachable datasets in the registry (except deliberately separate FAQ/special corpora), then narrow by prefix/industry/tag. Missing datasets masquerade as model failure.
6. Native citations: if final answer cites workflow-tool-internal evidence, main workflow must still register top-level datasetSearch quoteList coverage before final answer and final text must include `[id](CITE)` markers.
7. Output hygiene: no internal analyzer/verifier/ranking JSON should stream to users; final prompts should not expose tool calls, scoring, requery, fallback machinery, or XML follow-up blocks.

This pattern is not limited to QA bots. Apply the same split to file/方案审查 agents and 方案生成 agents: FAQ/knowledge shortcuts can be supplemental, but source-grounded corpus evidence and final citation/traceability remain the trust boundary.
