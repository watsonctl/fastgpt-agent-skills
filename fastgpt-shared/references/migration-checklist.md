# FastGPT migration checklist

Use this checklist before implementation, during conversion, and before declaring parity.

## 1. Source discovery

- Identify the real user-facing entrypoint(s).
- Trace actually wired analyzer / retrieval / ranking / fallback logic.
- Distinguish active code from dead helpers or archived experiments.

## 2. Behavior inventory

Document these before building the workflow:
- direct-answer conditions
- mandatory retrieval conditions
- precision / identifier routing
- dataset scope / whitelist behavior
- loop / fan-out behavior
- deterministic ranking or post-processing
- fallback / downgrade rules
- native citation requirements and whether citations must open in the FastGPT UI
- which LLM nodes are user-facing vs internal-only
- external HTTP dependencies, if any
- import-time placeholders, secrets, tool bindings, or dataset scopes

## 3. Migration mode decision

Choose one and record why:

1. `workflow-only`
2. `workflow+workflow-tools`
3. `exception-helper-approved`

Hard validationChecks:
- no MCP unless explicitly requested
- no repo Helper API unless exception-approved
- no whole-app `/chat` proxy as a fake migration
- if workflow tools are used, record `usesWorkflowTools`, `workflowToolCount`, and `bindingMode`

## 4. Node / tool mapping

Build a behavior-to-node table:
- source behavior
- FastGPT node(s) or workflow tool
- data handed between nodes/tools
- parity risks if the mapping is imperfect
- what, if anything, still needs an approved external helper

## 5. Workflow-tool bundle validationChecks

If using 工作流工具:
- each tool JSON is still `nodes + edges + chatConfig`
- each tool has `pluginInput` and `pluginOutput`
- main workflow uses explicit `pluginModule` references
- main workflow `pluginModule.version` is intentionally set: use `""` for "保持最新版本" only after confirming that shape from a current instance export
- binding method is documented (`by-name-script`, `tool-bindings.json`, or `manual-ui` only if accepted)
- tool responsibilities are narrow and deterministic where possible
- if tool-internal retrieval produces final citations, the main workflow still has a citation registration strategy for native clickable references

## 6. Self-check passes

Minimum self-validationChecks:
- workflow JSON structure valid
- only allowed node types used
- chatConfig keys valid
- no residual `__RAG_HELPER_*__`
- no residual `/api/rag-helper/` unless exception mode
- no MCP tool config unless explicitly requested
- internal analyzer/router/verifier/planner chat nodes are not configured as user-visible response text
- final prompts do not expose internal tool calls, scoring, rerank, fallback machinery, or requery mechanics
- native citation coverage is checked when the answer contains `[id](CITE)`
- parity report reviewed
- import readiness report reviewed
- visual layout validation reviewed
- no obvious same-lane node overlap or backward main-spine edges
- UI global-variable controls are validated against the target instance's recognizable exported structure, especially select / multipleSelect enums and value types.

## 7. Delivery bundle

A strong migration handoff includes:
- importable workflow JSON, or multi-JSON bundle with main workflow + 工作流工具
- binding manifest / script if workflow tools need appIds
- parity/coverage matrix
- import readiness report
- layout validation report
- golden example or fixture if this is a repeated migration pattern

## 2026-04-24 Addendum: complex RAG / review / generation agents

- [ ] If using internal analyzer/router/verifier chatNodes, confirm only final user-facing nodes set `isResponseAnswerText=true`; old `aiChatIsResponseText` is not sufficient on current FastGPT.
- [ ] If a final citation uses evidence produced inside workflow tools, confirm main workflow top-level datasetSearch quoteList covers the final cited collectionIds.
- [ ] For every datasetSearchNode, verify `datasets.selectedTypeIndex`: static `[{ datasetId }]` must be `0`; node references must be `1`. Also verify static empty `collectionFilterMatch` uses `0`.
- [ ] Avoid `ifElse -> top-level parallelRun -> finalAnswer` on critical final chains; prefer fixed slots or a workflow tool boundary if runtime logs show stop-chain behavior.
- [ ] For FAQ + corpus patterns, record FAQ thresholds and enforce: explicit user source/standard/document beats FAQ direct mode.
- [ ] For tags filtering, include a no-tag fallback path and ranking fallback using metadata/sourceName, because tags filter may depend on instance capability/config.
- [ ] Runtime diagnostic report should include final-answer presence, internal-output leakage, FAQ branch execution, metadata item count, native citation coverage, and slow citation auth searches.
