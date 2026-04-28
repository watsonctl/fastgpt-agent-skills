---
name: fastgpt-workflow-generator
description: "Generate FastGPT workflow JSON from requirements; 从自然语言需求生成工作流 JSON."
---

# FastGPT Workflow Generator

Use this skill when a user asks you to create a new FastGPT workflow or RAG pipeline from natural language requirements. Do **not** use this skill to debug existing workflows (use `fastgpt-workflow-debug`) or to migrate existing code/frameworks (use `fastgpt-workflow-migration`).

## 1. Start Sequence

1. Read `../fastgpt-shared/references/fastgpt-official-contracts.md` to understand node types, connection rules, and variables.
2. Read `../fastgpt-shared/assets/probe-examples/README.md` to understand the minimal viable structure for each node type.
3. Determine if the requirement needs a single workflow or a decomposed **Workflow + Workflow-Tools** architecture.
   - *Rule of thumb*: If the workflow has multiple distinct phases (e.g., entity extraction, knowledge retrieval, cross-check), isolate the complex parts into separate Workflow-Tools.

## 2. Supported Node Types (observed against FastGPT v4.14.x exports/probes)

> Always verify the generated JSON against the target FastGPT instance export/import behavior before treating these contracts as stable.

You must ONLY use the following node types. Use `../fastgpt-shared/assets/probe-examples/` as the structural template.

- `workflowStart` (Must be the entry point)
- `chatNode` (LLM inference, text or JSON output)
- `code` (JS data processing, normalization)
- `datasetSearchNode` (Knowledge base retrieval)
- `ifElseNode` (Conditional routing)
- `httpRequest468` (External API calls)
- `variableUpdate` (Global state management)
- `tools` (Agent/Tool-calling, use sparingly as an assistant, not the main flow)
- `pluginModule` (To call a sub-workflow / tool)
- `answerNode` (Final explicit output)

## 3. Generation Process

Do NOT hallucinate JSON fields. FastGPT JSON imports will fail immediately if required fields are missing or edges are invalid.

### Step 1: Component Planning
List the exact node IDs and their `flowNodeType` you plan to use.
Example: `input -> code (normalize) -> datasetSearchNode (retrieve) -> chatNode (answer) -> answerNode`.

### Step 2: Skeleton Generation
Use the templates in `../fastgpt-shared/assets/probe-examples/` to construct the node objects. Pay special attention to:
- `inputs`: Must match the exact `key` expected by the node type.
- `outputs`: Define the `id` and `type` correctly.

### Step 3: Edge Routing
Connect the nodes using `source` and `target` handles.
- A source node's `sourceHandle` must match `nodeId-source-right` (usually).
- A target node's `targetHandle` must match `nodeId-target-left`.

### Step 4: Variable References
When Node B needs Node A's output, declare an input in Node B with `renderTypeList: ["reference"]`, and `value: ["NodeA_ID", "output_key"]`.
Do **not** use `{{$NodeA_ID.output_key$}}` inside a reference value array. Template syntax `{{$}}` is only for string interpolation (like in `chatNode` prompts).

## 4. Workflow-Tools Decomposition

If calling a Workflow-Tool (Sub-workflow) from the main workflow:
1. The Tool Workflow itself MUST start with `pluginConfig` and `pluginInput`, and end with `pluginOutput`.
2. The Main Workflow MUST use `flowNodeType: "pluginModule"` (NOT `runApp`) to call the tool.
3. You must align the `pluginModule.outputs` in the main workflow with the `pluginOutput.inputs` defined in the tool.
4. Replace `YOUR_WORKFLOW_TOOL_APP_ID` with a placeholder or actual AppId.

## 5. Verification

Before giving the final JSON to the user, you MUST verify it:
1. Validate JSON syntax (no trailing commas).
2. Ensure every `source` in `edges` exists in `nodes`.
3. Ensure every `target` in `edges` exists in `nodes`.
4. Ensure no `runApp` node is used for sub-workflows.

## 6. Guardrails

- **Never** compute Jaccard similarities or use fuzzy template matching algorithms. Build the JSON deterministically based on the user's explicit steps.
- **Never** hardcode real API keys or sensitive internal IP addresses in the `httpRequest468` headers. Use variables.
- Keep the `chatConfig` block minimal if not explicitly requested.
