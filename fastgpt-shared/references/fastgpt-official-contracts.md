# FastGPT official-contract baseline

Use this as the **starting baseline**, not the final source of truth. For anything version-sensitive, re-check current official docs/source before emitting or validating a workflow.

_Last refreshed: 2026-04-28_

## Primary sources

- v4.14.1: 插件 renamed to 工作流工具 and moved to 我的工具: https://doc.fastgpt.io/docs/self-host/upgrading/4-14/4141
- v4.14.11: 并行执行节点、变量更新数组操作增强、code-sandbox/plugin/aiproxy 镜像同步升级
- v4.14.14: DeepSeek 工具调用+思考模式兼容，避免 API 400 错误
- v4.14.15: 旧版系统工具兼容修复（官方建议 4.14.8+ 直接升至此版本）
- v4.14.16: embedding base64 返回值适配、节点弹窗高度修复
- Tool calling / tool termination: https://doc.fastgpt.io/docs/guide/dashboard/workflow/tool/
- Workflow intro: https://doc.fastgpt.io/zh-CN/docs/introduction/guide/dashboard/intro
- Knowledge Base Search: https://doc.fastgpt.io/en/docs/introduction/guide/dashboard/workflow/dataset_search
- HTTP Request: https://doc.fastgpt.io/docs/guide/dashboard/workflow/http/
- Code Run / Sandbox v2: https://doc.fastgpt.io/docs/introduction/guide/dashboard/workflow/sandbox-v2
- Parallel Run: https://doc.fastgpt.io/zh-CN/docs/introduction/guide/dashboard/workflow/parallel_run
- System tool `.pkg` upload, only for root-installed system tools: https://doc.fastgpt.io/docs/introduction/guide/plugins/upload_system_tool

## Target-version gate

- This file is a versioned baseline, not a claim that every item has been revalidated on the current target.
- The current project target is FastGPT `4.15.0-beta5`; the `4.14.x` notes below are historical/compatibility evidence unless a current target export or official source confirms the same behavior.
- Before generating, importing, debugging, or publishing, record the target version and compare the current detail/export, runtime trace, and relevant official source. If they disagree, stop at a version/schema diff instead of silently applying the older contract.
- No beta5-specific runtime behavior is asserted here unless it is directly marked as target evidence; in particular, static node success does not prove AgentV2 VM dependency loading, persistence, or CITE projection.

## Import/export baseline

FastGPT has three related JSON shapes that must not be mixed:

1. **Dashboard page import/export JSON**: the file accepted by page "导入配置".
2. **OpenAPI app/create payload**: an API request body for creating an app.
3. **Template/development wrapper**: a local packaging convenience for generators, templates, or marketplaces.

Dashboard importable workflow files must use this top-level shape and no wrapper:

```json
{
  "nodes": [],
  "edges": [],
  "chatConfig": {}
}
```

Workflow tools use the same top-level dashboard shape. FastGPT identifies a workflow tool when the workflow contains `pluginInput` and `pluginOutput` nodes. Main workflows reference workflow tools through `pluginModule` nodes whose runtime field is still `pluginId` in current source.

For FastGPT 4.14.7, the stored-node schema requires every item in `nodes`/`modules` to contain
both `inputs` and `outputs` arrays. This is a storage-schema requirement, not merely a UI hint:
an output-less terminal node must still carry `"outputs": []`. Do not treat a missing property as
an empty array during validation.

The same schema makes an IO item's `valueType` optional, not nullable. Follow the target template
when it supplies a type; in FastGPT 4.14.7 the code-node template declares editor-only `codeType`
and `code` as `"string"`. Never write `"valueType": null`; it can fail the dashboard create/import
boundary with only the generic `Data validation error` message.

OpenAPI create payloads may contain app metadata or wrapper fields such as `name`, `type`, `modules`, or `workflow`; those payloads are for API calls, not for page import. Template wrappers may contain top-level `template`; those are development artifacts, not user import packages. When preparing a user-facing import bundle, unwrap or regenerate them so each import file has only top-level `nodes`, `edges`, and `chatConfig`.

## Product wording vs internal fields

- Product/user-facing term: **工作流工具 / workflow tool**.
- Legacy/internal source fields may still use `plugin`, `pluginInput`, `pluginOutput`, `pluginModule`, and `pluginId`.
- Template-market wrappers may still show `type: "plugin"`; do not expose that as the user-facing migration mode.
- `.pkg` belongs to root-uploaded system tools, not the default workflow-tool route.

## Baseline node types for this skill pack

- `userGuide`
- `workflowStart`
- `chatNode`
- `datasetSearchNode`
- `datasetConcatNode`
- `code`
- `ifElseNode`
- `httpRequest468`
- `loop`
- `parallelRun`
- nested/system nodes: `loopStart`, `loopEnd`
- workflow-tool nodes: `pluginConfig`, `pluginInput`, `pluginOutput`, `pluginModule`

If a migration requires more node types, expand this baseline only after checking official docs/source.

## Baseline chatConfig keys

- `welcomeText`
- `variables`
- `autoExecute`
- `questionGuide`
- `ttsConfig`
- `whisperConfig`
- `scheduledTriggerConfig`
- `chatInputGuide`
- `fileSelectConfig`
- `instruction`

## chatNode: JSON output modes

chatNode supports structured JSON output via `aiChatResponseFormat` and `aiChatJsonSchema` inputs.

| aiChatResponseFormat | Mode | aiChatJsonSchema | Behavior |
|---|---|---|---|
| `""` (empty/default) | Plain text | ignored | Model returns free-form text |
| `"json_object"` | JSON mode | ignored | Model returns valid JSON (no schema enforcement) |
| `"json_schema"` | Structured output | JSON Schema string | Model returns JSON matching the exact schema |

**Model compatibility:**
- `"json_object"`: supported by OpenAI, DeepSeek, Qwen, and most OpenAI-compatible APIs
- `"json_schema"`: only verified on OpenAI models (gpt-4o-mini, gpt-4o). DeepSeek v3 does NOT support this mode — FastGPT will send `schema: None` and the API returns 400.

**When to use which:**
- Use `"json_object"` for most cases — combine with a system prompt that specifies the expected JSON structure
- Use `"json_schema"` only when the target model is verified to support it AND strict schema enforcement is needed
- For intent classification / routing, `"json_object"` is sufficient since the code node validates the output

**Probe example:** `assets/probe-examples/09_ai_chat_json_output_example.json` (uses gpt-4o-mini)

## datasetSearchNode: selectedTypeIndex and dynamic dataset selection

The `datasets` input on `datasetSearchNode` supports two modes controlled by `selectedTypeIndex`:

| selectedTypeIndex | Mode | datasets.value | Use case |
|---|---|---|---|
| 0 (default) | **Static** | `[{datasetId: "xxx"}, ...]` | Hardcoded dataset list in workflow JSON |
| 1 | **Reference** | `["nodeId", "outputKey"]` or bound to `chatConfig.variables` | Dynamic selection from upstream node or user variable |

When using mode 1 with a `chatConfig.variables` entry of type `selectDataset`, the FastGPT UI presents a dataset picker to the user at runtime. The selected datasetIds are passed to the `datasetSearchNode` automatically.

When using mode 1 with an upstream `code` node reference, the code node must return `[{datasetId: "xxx"}]` format. The code node output should use `valueType: "selectDataset"` (not `"arrayObject"`) to match the datasetSearchNode input type.

**Known limitation**: The code node → datasetSearchNode reference binding (`selectedTypeIndex: 1` with `value: ["codeNodeId", "datasets"]`) is documented in the contract but has no verified export example. The FastGPT UI may show "知识库变量引用" as empty even when the JSON reference is correct. If the binding doesn't resolve at runtime, use `chatConfig.variables` with `selectDataset` type as fallback (see canonical example), or manually bind the reference in the UI after import.

Canonical example (chatConfig.variables approach): `assets/canonical-examples/dataset-search-dynamic-select.workflow.json`

Other production parameters observed in target-instance exports:
- `datasetSearchUsingExtensionQuery: true` — enables query expansion via LLM before search
- `datasetSearchExtensionModel: "qwen3.5-flash"` — model for query expansion
- `limit: 20000` — an observed high quote-token cap, not a chunk count; keep it only when it is below the target model's `quoteMaxToken` and latency budget. Do not copy this value as a universal default.
- `rerankModel: "jina-reranker-v2-base-multilingual"` — alternative to `bge-reranker-v2-m3`

## Migration defaults

- Decide `migrationMode`: `workflow-only`, `workflow+workflow-tools`, or `exception-helper-approved`.
- Default to no MCP.
- Default to no repo-hosted Helper API.
- Use 工作流工具 for decomposition when a single workflow becomes hard to read or maintain.
- Keep `questionGuide` and `chatInputGuide` enabled unless the target product requires a silent machine-only app.
- For dataset search, remember the output is still an array even when empty.
- For loops/parallel, build explicit flattening/merge steps instead of assuming the UI auto-flattens nested outputs.

## HTTP node cautions

- HTTP node syntax and variable interpolation have changed across FastGPT versions.
- Re-check current HTTP docs before relying on old `{{}}` examples.
- HTTP is acceptable for clear third-party APIs; host Helper APIs require explicit exception approval.

## Migration rule of thumb

A real migration moves the decision logic, branch structure, retrieval semantics, and fallback behavior into workflow JSON and/or workflow tools. If the workflow mostly calls one existing app endpoint and relays its answer, that is a thin wrapper, not a migration.
