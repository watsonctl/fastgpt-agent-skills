# Pattern: FastGPT 工作流工具

## What it is

FastGPT v4.14.1 renamed product-side “插件” to **工作流工具**. Importable workflow-tool JSON still uses the same top-level shape as a workflow:

```json
{
  "nodes": [],
  "edges": [],
  "chatConfig": {}
}
```

A workflow becomes a workflow tool when it contains:
- `pluginInput`
- `pluginOutput`

A main workflow calls it through:
- `pluginModule`
- internal field `pluginId` set to the workflow tool appId

## Version binding

When generating a main workflow that calls workflow tools, default `pluginModule.version` to an empty string (`""`) when the target FastGPT instance export proves this means **保持最新版本**. In short: **保持最新版本 = `pluginModule.version` 空字符串**. Keep `pluginId` bound to the workflow tool appId.

This field is instance-version sensitive. If a future FastGPT export changes the representation, re-confirm from a fresh exported JSON before changing generators or validators.

## When to use

Use `workflow+workflow-tools` when:
- one canvas is too dense to operate safely
- a capability cluster has clear input/output boundaries
- deterministic sub-flows should be reusable
- appId binding can be automated or documented

Do not use workflow tools merely to hide unclear logic. Split by capability, not by file count.

For multi-profile review or generation apps, prefer one workflow tool that resolves a typed profile/rule/config object when the execution chain stays the same. Do not split into one workflow tool per profile type unless the profile type needs a materially different execution path.

## Binding modes

- `by-name-script`: import tools first, script discovers appIds by exact tool name and writes final main workflow JSON.
- `tool-bindings.json`: user supplies `{ toolName: appId }` once; script binds.
- `manual-ui`: only if user accepts hand binding in FastGPT UI.

## Deliverables

For a bundle, provide:
- each workflow-tool JSON
- main workflow template JSON with placeholder `pluginId`s
- manifest with names/files/placeholders
- binding example
- binding script or clear binding command
