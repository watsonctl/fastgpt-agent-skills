---
name: fastgpt-workflow-generator
description: "Use when generating new FastGPT workflow or Workflow-Tool JSON. 工作流生成。"
disable-model-invocation: true
---

# FastGPT Workflow Generator

## Purpose

把明确需求生成成可验证的 FastGPT workflow 或 Workflow-Tool JSON。此 Skill 负责设计和产出图，不负责调试已有运行态，也不把 AgentV2 业务逻辑、宿主代码或凭据偷偷塞进工作流。

## When to Use

- 用户要求新建 FastGPT workflow、Workflow-Tool、RAG 流程或可导入 JSON。
- 需要把多个稳定、纯执行阶段拆成结构化工具，并定义输入、输出和错误协议。
- 需要根据目标实例导出和 canonical example 生成最小可导入图。

## When NOT to Use

- 已有图导入/运行/CITE/HTTP/AgentV2 故障：使用 `fastgpt-workflow-debug`。
- 将已有代码、服务或 RAG 系统迁移进 FastGPT：使用 `fastgpt-workflow-migration`。
- 需要写 Python/TS 服务：只有原生能力被证明不足且用户明确批准，才使用对应 host adapter。
- 不把生成器当作 AgentV2 运行时 Skill；本机依赖、`.env` 和 macOS 工具不是 VM 证据。

## Architecture Context

### Source of Truth

- 目标 FastGPT 当前成功导出/导入的 JSON 是结构合同；官方文档是语义参考；旧 probe 不能替代当前实例证据。
- 先记录目标实例版本、OS/architecture、runtime、依赖来源、Secret 作用域、缓存/重试政策和发布边界。当前项目目标是 `4.15.0-beta5`，但不能把该版本硬编码为所有实例的默认值。
- `fastgpt-shared` 是六个维护 Skill 的共同合同和脚本源。引用相对路径，不创建 consumer 副本。
- 如果需求包含 AgentV2 VM 启动初始化，beta5 的配置字段是 `sandboxEntrypoint` 字符串；生成前必须从目标 Agent detail 复核字段形状。启动脚本不自动注入 Skill ZIP 的 `.env`，不写入 Key/Token；需要运行时配置时，先声明已验证的 Secret 来源、目标 Skill loader 和文件交接方式。

### Deliverable Types

- `importable JSON`：无未解决 placeholder，已通过静态验证，并标明尚未做的远端导入/运行验收。
- `template JSON`：可以有 placeholder，但必须明确标记为 template，不能与 importable artifact 混放。
- 任何远端 update/publish 都是独立的、有授权的操作，不是生成或本地验证的默认副作用。

## Generation Operations

### 1. 选择最小架构

先画出阶段和数据边界，再决定 `workflow-only`、`workflow+workflow-tools` 或 `exception-helper-approved`。Workflow-Tool 适合稳定、无状态、可单测的执行边界；若每次调用都要由 Agent 再决策，必须用 tracing 证明总延迟和失败率仍可接受。

Agent/Skill 负责业务意图和受控路由时，工具只接收并执行结构化 route；工具不得让模型自由生成或修改 `datasetId`、`collectionId`。空 route 必须显式进入 fallback，不能退化成全库搜索。

### 2. 从证据构造骨架

先列 node ID 和 `flowNodeType`，再从目标导出或 `../fastgpt-shared/assets/canonical-examples/` 复制高风险节点的形状。不得凭记忆补复杂字段。至少检查：

- 顶层 `nodes`、`edges`、`chatConfig` 是否符合目标导入合同。
- 每个 node 都有 `inputs`、`outputs`；无输出 terminal 也显式写 `outputs: []`。
- `inputs` 的 key、`renderTypeList`、reference value 与真实节点合同一致；不要把 `{{$...$}}` 塞进 reference 数组。
- `code` 节点动态输入按当前导出使用 `system_addInputParam`、`renderTypeList: ["addInputParam"]` 和可编辑 reference。
- optional `valueType` 要么省略、要么使用目标允许的枚举；不要写 JSON `null`。
- 每条 edge 的 source/target、handle 和节点 ID 存在；不添加未经导出证明的容器到 body 边。

### 3. 使用容器和工具

`loop`/`parallelRun` 只从当前 canonical export 取结构。确认 `childrenNodeIdList`、`parentNodeId`、`loopStart`/`loopEnd`、聚合输出、并发和重试字段，不使用旧别名。

Workflow-Tool 必须是：

```text
pluginConfig -> pluginInput -> [纯执行节点] -> pluginOutput
```

主图使用 `pluginModule`，不使用 `runApp`；主图与工具的 output/input port 必须逐项对齐。含系统工具 Secret 的节点放在稳定的独立工具中，准备图只引用其已发布版本，不把 Secret 写入 JSON。

### 4. RAG、联网和 CITE

- `datasetSearchNode` 的 `datasets` 和 `collectionFilterMatch` 必须同时来自同一份受控 route；不要用静态全库 datasets 配合可选过滤器冒充范围控制。
- 网页结果可以发现/确认候选规范；本地有可靠 chunk 时由原生 `datasetSearchNode` 产生 quote 并优先作答。本地没有可靠证据时才进入联网答案分支，并保留真实网页链接。
- `data/v2/list`、`pluginOutput.quotes`、`datasetQuote`、stdout 或模型文本都不是原生 CITE。原生 quote 必须由实际 `datasetSearchNode` 产生，并按目标 AgentV2 实测是否从 `childrenResponses.quoteList` 投影到持久消息 `totalQuoteList`。
- 最终 `quoteQA` 只使用当前 route 内真实 ID、正文非空、非失败且去重的有限 quote；父级 `quoteList` 保留给原生授权。最终文本中的 quote ID 必须与本轮真实 quote 交集一致。
- 缓存只保存成功且证据闭环完整的结果；失败、超时、空 route、降级联网答案不缓存。

### 5. 输入输出协议

为每个工具写清：输入字段、类型、必填性、边界、正常输出、空结果、错误、超时、重试和降级状态。响应结构要稳定，避免让调用方猜测字符串/对象/数组。敏感配置通过 FastGPT Secret 或环境注入；不进入 JSON、fixture、日志和文档。

### 6. AgentV2 启动脚本输出规则

- `sandboxEntrypoint` 只能承担快速、确定性的 VM 初始化和预检；不在启动脚本中执行
  LLM、视觉模型、联网搜索或 request-time `apt`/`pip`/`npm` 安装。
- 脚本必须按 beta5 的 cold/warm、hash 去重和超时语义设计；不能因为“发布成功”就
  断言脚本在每次请求中都重跑。
- 不把 `export` 当作跨 Skill/跨 Sandbox 命令的持久环境；若需要文件交接，优先由 Skill
  已挂载后的自身 `entrypoint.sh` 解析包根目录并生成权限受限文件；只有路径和生命周期
  已验证时，才由 Secret-aware 部署源或 `sandboxEntrypoint` 交接，并让 Skill 显式加载。
- 生成结果须保留目标版本、脚本长度/超时、Secret 来源、回滚方式和未完成的 VM
  smoke；没有目标 detail 与运行证据时，只输出 template，不能称为 importable/runtime-ready。

## Evidence Commands

```bash
python3 ../fastgpt-shared/scripts/validate_fastgpt_workflow.py <workflow.json>
python3 ../fastgpt-shared/scripts/validate_fastgpt_layout.py <workflow.json>
python3 ../fastgpt-shared/scripts/generate_import_readiness_report.py <workflow.json>
```

生成后至少留存：目标版本/导出来源、graph 校验结果、import readiness、workflow-tool binding mode、placeholder 扫描、Secrets 未进入 artifact 的证明，以及远端 smoke 是否仍未验证。静态绿色不等于运行成功。

## Safety / Out of Scope

- 不生成、读取、打印、提交或传播 API Key、Cookie、Token、HTTP/system-tool Secret、内部 URL、真实 Agent/Workflow/Collection ID。
- 不自动修改或发布正式版；不在生成过程中更新远端应用。
- 不为了通过导入而删除原生检索、证据过滤、CITE 投影或联网兜底。
- 不把业务特例写成全局标准；项目特定 route、候选、collection 和回答规则放在项目 source/fixture。

## Escalation / Stop Conditions

目标导出缺失、版本合同冲突、节点 Secret 不可确认、输入输出协议不稳定、需要 runtime 源码权限、需要改正式版，或无法区分 template/importable 时停止生成，输出 schema diff 和待补证据，不凭经验补齐。

## Related Files / Skills

- 基础合同：`../fastgpt-shared/SKILL.md`
- 官方/版本合同：`../fastgpt-shared/references/fastgpt-official-contracts.md`
- VM 边界：`../fastgpt-shared/references/vm-runtime-contract.md`
- Workflow-Tool：`../fastgpt-shared/references/patterns/workflow-tool.md`
- RAG：`../fastgpt-shared/references/patterns/rag.md`
- 调试/迁移：`fastgpt-workflow-debug`、`fastgpt-workflow-migration`
