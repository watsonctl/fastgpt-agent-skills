---
name: fastgpt-workflow-generator
description: "Generate FastGPT workflow JSON from requirements; 从自然语言需求生成工作流 JSON."
---

# FastGPT Workflow Generator

Use this skill when a user asks you to create a new FastGPT workflow or RAG pipeline from natural language requirements. Do **not** use this skill to debug existing workflows (use `fastgpt-workflow-debug`) or to migrate existing code/frameworks (use `fastgpt-workflow-migration`).

## 1. Start Sequence

1. Read `../fastgpt-shared/references/fastgpt-official-contracts.md` to understand node types, connection rules, and variables.
2. Locate target-instance schema evidence before generating importable JSON:
   - Prefer successful exports/imports from the user's target FastGPT instance.
   - For high-risk container nodes, read `../fastgpt-shared/assets/canonical-examples/README.md` and the relevant canonical JSON first.
   - Read `../fastgpt-shared/assets/probe-examples/README.md` only as probe guidance. Probes are not production templates unless marked canonical/import-verified.
   - If bundled examples conflict with the target instance export, stop and produce a schema-diff note. Do not invent node objects from memory.
3. Determine if the requirement needs a single workflow or a decomposed **Workflow + Workflow-Tools** architecture.
   - *Rule of thumb*: If the workflow has multiple distinct phases (e.g., entity extraction, knowledge retrieval, cross-check), isolate the complex parts into separate Workflow-Tools.
4. Decide whether the deliverable is:
   - **importable JSON**: no unresolved blocker placeholders; ready for dashboard import.
   - **template JSON**: may contain placeholders, but must be labeled as non-importable and kept separate from importable artifacts.

## 2. Supported Node Types

> Always verify the generated JSON against the target FastGPT instance export/import behavior before treating these contracts as stable. The target instance's successful export/import is the System of Record; official docs are semantic reference, not a replacement for instance schema.

Use target-instance exports or `../fastgpt-shared/assets/canonical-examples/` as the structural template for high-risk nodes. Do not handcraft complex nodes from a minimal mental model.

Supported observed node types include:

- `userGuide`
- `workflowStart`
- `chatNode`
- `code`
- `datasetSearchNode`
- `datasetConcatNode`
- `ifElseNode`
- `httpRequest468`
- `variableUpdate`
- `loop`
- `loopStart`
- `loopEnd`
- `parallelRun`
- `tools`
- `pluginConfig`
- `pluginInput`
- `pluginOutput`
- `pluginModule`
- `answerNode`

## 3. Generation Process

Do NOT hallucinate JSON fields. FastGPT JSON imports can fail even when local graph checks pass.

### Step 1: Component Planning

List the exact node IDs and their `flowNodeType` you plan to use.
Example: `input -> code (normalize) -> datasetSearchNode (retrieve) -> chatNode (answer) -> answerNode`.

### Step 2: Skeleton Generation

Use target instance export/canonical templates to construct the node objects. Pay special attention to:

- `inputs`: Must match the exact `key` expected by the node type.
- `outputs`: Define the `id`, `key`, `type`, and `valueType` correctly.
- Preserve auxiliary fields present in the target export template. Do not omit them merely because the prompt is simple.

#### AI Chat node contract

For `chatNode`, importable JSON must pass these minimum gates:

- `model` is a concrete, non-empty model name and not a placeholder such as `__FASTGPT_AI_MODEL__`.
- JSON output must preserve the target instance's full JSON-response fields when present in exported examples.
- If multiple upstream fields are needed, assemble them in a preceding `code` node first; do not rely on unverified string-template interpolation inside `userChatInput`.

#### Code node dynamic input contract

For `code`, use the target export's dynamic input contract. In current observed exports this includes:

- `key: "system_addInputParam"`
- `renderTypeList: ["addInputParam"]`
- `valueType: "dynamic"`
- Business inputs passed to `main()` must be editable reference inputs whose keys match function parameter names.

#### Loop / Parallel container contract

For `loop` and `parallelRun`, never create a visual-only container and never improvise input/output keys.

Use `../fastgpt-shared/assets/canonical-examples/00-workflow-tool-parallelrun-sample.workflow.json` for `parallelRun` shape and `../fastgpt-shared/assets/canonical-examples/35-fact-extractor.workflow.json` only as a `loop` schema reference. Do not copy 35/70 business logic into generic templates.

Current verified container anchors:

- container input array key: `loopInputArray`
- child list key: `childrenNodeIdList`
- layout keys: `nodeWidth`, `nodeHeight`, `loopNodeInputHeight`
- child start anchor: `loopStart` node with outputs `loopStartInput` and `loopStartIndex`
- child end anchor: `loopEnd` node with input `loopEndInput`
- loop aggregate output: `loopArray`
- parallel concurrency keys: `parallelRunMaxConcurrency`, `parallelRunMaxRetryTimes`
- parallel aggregate outputs: `parallelSuccessResults`, `parallelFullResults`, `parallelStatus`

Mandatory rules:

- `childrenNodeIdList` must contain every child node ID.
- Every child must set `parentNodeId` to the container node ID.
- Body nodes must read current item and index from the `loopStart` child:
  - current item: `["<loopStartId>", "loopStartInput"]`
  - index: `["<loopStartId>", "loopStartIndex"]`
- Body output must feed `loopEnd.loopEndInput`.
- Downstream aggregation must reference canonical aggregate outputs only.
- Do **not** reference old parent-container fields such as `["<containerId>", "currentItem"]`.
- Do **not** use legacy/unverified keys in new importable JSON: `array`, `maxConcurrency`, `maxRetries`, `successResults`, `failedResults`, `fullResults`, `status`, `currentItem`.
- For `parallelRun`, default to the canonical minimal body: `loopStart -> one body node -> loopEnd`, then aggregate after `parallelRun`.

### Step 3: Edge Routing

Connect nodes using `source` and `target` handles:

- A source node's `sourceHandle` must match `nodeId-source-right` unless a current export proves another handle.
- A target node's `targetHandle` must match `nodeId-target-left` unless a current export proves another handle.
- Current verified container exports start the internal body chain at `loopStart`; they do not require an explicit container-to-`loopStart` edge. Do not add legacy container-to-body edges.

### Step 4: Variable References

When Node B needs Node A's output, declare an input in Node B with `renderTypeList: ["reference"]`, and `value: ["NodeA_ID", "output_key"]`.

Do **not** use `{{$NodeA_ID.output_key$}}` inside a reference value array. Template syntax `{{$}}` is only for string interpolation when the target export proves it is accepted.

## 4. Workflow-Tools Decomposition

If calling a Workflow-Tool from the main workflow:

1. The Tool Workflow itself MUST start with `pluginConfig` and `pluginInput`, and end with `pluginOutput`.
2. The Main Workflow MUST use `flowNodeType: "pluginModule"` (NOT `runApp`) to call the tool.
3. Align `pluginModule.outputs` in the main workflow with `pluginOutput.inputs` defined in the tool.
4. In importable JSON, replace workflow-tool AppId placeholders with actual AppIds. Do not store API keys in workflow JSON; use environment variables or a gitignored local secret file.

## 5. Verification

Before giving final JSON to the user, verify it:

1. Validate JSON syntax.
2. Ensure every edge source/target exists.
3. Ensure no `runApp` node is used for workflow tools.
4. Ensure no unresolved blocker placeholders remain.
5. Run shared validators when available:

```bash
python3 ../fastgpt-shared/scripts/validate_fastgpt_workflow.py <workflow.json>
python3 ../fastgpt-shared/scripts/validate_fastgpt_layout.py <workflow.json>
```

6. Treat local validators as static checks only. Do not claim dashboard import success unless the target FastGPT page import/export was actually verified.

## 6. Guardrails

- Never compute Jaccard similarities or use fuzzy template matching algorithms. Build JSON deterministically based on explicit steps and canonical templates.
- Never hardcode real API keys, tokens, or sensitive internal URLs in docs, examples, scripts, or workflow JSON.
- Keep `chatConfig` minimal if not explicitly requested.
- Do not downgrade target-instance schema requirements to make generated JSON look simpler.
- Do not treat probe examples as production templates unless they are marked canonical/import-verified.
