---
name: fastgpt-workflow-debug
description: "Use when debugging FastGPT workflow, AgentV2, Sandbox, CITE, HTTP, or tool-runtime failures. 工作流调试。"
metadata:
  github-path: fastgpt-workflow-debug
  github-repo: https://github.com/watsonctl/fastgpt-agent-skills
disable-model-invocation: true
---

# FastGPT Workflow Debug

## Purpose

以运行态证据定位 FastGPT 工作流、Workflow-Tool、AgentV2 和 Skill VM 的问题。入口文档只负责分流；节点合同、版本差异和长排错清单放在 `fastgpt-shared/references/`，避免每个 Skill 复制一套互相漂移的规则。

## When to Use

- 导入、保存、发布后运行失败，或 `flowResponses` 与最终回答不一致。
- AgentV2 回合过多、TTFT/TTLT 长尾、Sandbox/VM 依赖失败、HTTP/LLM/视觉调用异常。
- 知识库命中、原生 `quoteList`、持久消息 `totalQuoteList` 或前端 CITE 异常。
- 需要核对 Workflow-Tool 输入输出、版本绑定、路由范围、缓存、重试或降级行为。

## When NOT to Use

- 新建工作流或工具 JSON：使用 `fastgpt-workflow-generator`。
- 将现有代码迁移为 FastGPT 图：使用 `fastgpt-workflow-migration`。
- 只有在原生节点和 Workflow-Tool 都被证据证明不足，并且用户明确批准时，才使用 Python/TS host adapter。
- 不把本 Skill 当作 AgentV2 业务 Skill，也不以本机 macOS 运行结果证明远端 VM 可用。

## Architecture Context

### Source of Truth

- 维护源是本地 `AGENT-SKILLS` 仓库；Codex、Claude 等 consumer 是安装镜像或软链，不在 consumer 中编辑。
- 目标 FastGPT 实例的当前导出、detail、运行日志和持久消息优先于旧模板。官方文档解释语义，不能替代目标实例的 schema 证据。
- 当前项目目标版本是 FastGPT `4.15.0-beta5`。文档中出现的 `4.14.x` 只可作为历史/兼容线索，不能未经复核套用到 beta5。
- beta5 AgentV2 启动脚本使用 `sandboxEntrypoint`；它是 VM 初始化钩子，不是 Skill ZIP 的 `.env` 自动注入合同。具体生命周期、hash 去重、`export` 跨命令限制和安全写文件模式见 `../fastgpt-shared/references/vm-runtime-contract.md`，不能把启动脚本字段读回当作运行成功证明。

### Evidence Planes

把证据分成四层并分别记录：

1. 配置：Agent 模型/推理模式、Sandbox、显式工具、Skill、知识库绑定、草稿/发布版本。
2. 执行：真实 `stream=true` 的 request ID、回合、工具/工作流、VM、HTTP、LLM、视觉、检索、重试和超时 span。
3. 数据：工具输入输出、`childrenResponses`、原生 `datasetSearchNode.quoteList`、候选路由与错误分类。
4. 持久化/UI：最终 AI 消息 `responseData`、非空 `totalQuoteList`、文本中真实 quote ID 与前端实际 CITE。

单看 `flowResponses`、工具 stdout、`datasetQuote`、Markdown 引用或节点“成功”状态，都不能证明最终 CITE 已注册。

## Debug Operations

### 1. 固定对象和版本

先读取目标 Agent 当前 detail，并保存只读快照。确认测试版与正式版名称、版本、模型、Sandbox、显式工具、Skill、知识库绑定和发布状态；默认只分析测试版，禁止顺手写正式版。

如果目标版本、导出图和运行日志互相矛盾，先停在 schema/version diff，不从记忆补字段。对 beta5 先确认实际 runtime 行为，再决定是否保留旧版兼容分支。

### 2. 用一次可重放请求建立时间线

使用真实 `stream=true` 请求和固定题目，保存脱敏后的 request ID、时间戳、配置版本及完整节点顺序。至少区分：

```text
request
  -> Agent decision / model latency
  -> Skill or tool call
  -> workflow queue
  -> HTTP / LLM / VM / vision / dataset search
  -> evidence selection / final answer
  -> persistence
  -> frontend CITE projection
```

TTFT 是首 token 前路径的总和，不能用某个工作流节点耗时代替；TTLT/P95 需保留冷启动、重试、超时和异常样本。

### 3. 按合同分类而不是按现象猜原因

- `configuration`：模型、权限、工具/Skill、Secret、知识库绑定或发布版本不一致。
- `transport`：HTTP URL、认证、文件生命周期、VM 网络、队列或序列化问题。
- `schema`：节点输入输出、动态引用、`pluginInput/pluginOutput`、模板字符串或版本字段不匹配。
- `routing`：Skill/宿主未生成受控 route，或工具试图修改 `datasetId`、`collectionId`。
- `evidence`：目标 collection/chunk 没有进入原生搜索，或证据范围/失败状态过滤错误。
- `persistence`：嵌套 quote 没有投影到持久消息，或最终文本引用了不存在的 ID。

### 4. Route、工具和知识库边界

- Skill 或宿主负责意图、候选规范和受控 route；工具只执行已生成的 `datasetId + collectionId`，不得让模型自由改路由。
- `datasets` 与 `collectionFilterMatch` 必须来自同一份 route 输出；空 route 进入显式 fallback，不能变成全库搜索。
- 联网结果可用于候选发现/确认；本地有可靠 chunk 时优先走原生知识库证据，无本地证据时才以真实网页链接兜底。网页摘要不能伪装成本地标准原文。
- 观察、统计和诊断支路不得阻断答案；失败、超时和降级结果不进入成功缓存。
- 只把稳定、纯执行、结构化边界下沉为 Workflow-Tool；避免 Agent 再选一次工具、工具内部再嵌套一轮模型，除非 tracing 证明其总成本更低。

### 5. CITE 验收链

验证顺序必须是：

```text
datasetSearchNode.quoteList
  -> (nested if applicable) childrenResponses.quoteList
  -> host persistence projection
  -> AI message.responseData.totalQuoteList
  -> final text real quote IDs
  -> frontend CITE
```

原生 `datasetSearchNode` 是 quote 的产生点。工具返回文本、`pluginOutput.quotes`、`datasetQuote` 或嵌套 `quoteList` 本身，不会自动注册父级 CITE。若目标 AgentV2 依赖 child promotion，必须在持久消息中实测非空 `totalQuoteList`，并核对最终引用 ID 与真实 quote ID 的交集。

### 6. 最小修复闭环

1. 保存脱敏配置、导出图和运行证据。
2. 只改一个主要变量，优先修复断裂的合同，不先压低检索量或关闭证据校验。
3. 先做静态 JSON/图校验，再做同题 `stream=true` 运行。
4. 重新检查配置读回、span、quote、持久消息和前端结果。
5. 记录回滚点；未完成远端持久化和真实消息验收，不称为“已修复”。

### 7. 启动脚本专项检查（beta5）

遇到“脚本没有生效”“Skill 读不到环境变量”或冷启动长尾时，按以下顺序检查：

1. 从测试版当前发布 detail 确认 Agent 节点存在 `sandboxEntrypoint` 字符串，且
   `useAgentSandbox`、版本发布状态和 VM feature flag 均有效；不要用草稿或历史版本代替。
2. 先做不含凭据的 marker 读回，再检查 Skill 文件是否已挂载、脚本是否超时/失败和
   是否因 hash 去重而跳过。marker 未出现在后续 Agent 返回中，只说明后续可见性未
   观测到，不能单凭正文判定脚本未执行。
3. 不以 `export` 证明 Skill 已获得变量；启动脚本、Skill entrypoint、Sandbox 命令
   可能是不同执行上下文。优先验证 Skill entrypoint 在自身包根生成的受限配置文件，
   再验证 Skill loader；不要猜测 shell 继承或挂载路径。
4. beta5 默认不提供通用 LLM/视觉 Key 的自动注入；无已验证 Secret 来源时停止写入，
   不写入本机 `.env`、API Key，也不把临时安装命令塞进脚本。
5. 若需要恢复，使用保存的测试版 detail 原样恢复；发布载荷中的
   `agent_selectedTools` 按目标 detail 已验证的紧凑引用格式处理，避免 beta5 将工具
   归一化为空。正式版只做只读比对。

## Evidence Commands

在本 Skill 目录执行，或把路径改为实际 checkout：

```bash
python3 ../fastgpt-shared/scripts/validate_fastgpt_workflow.py <workflow.json>
python3 ../fastgpt-shared/scripts/validate_fastgpt_layout.py <workflow.json>
python3 ../fastgpt-shared/scripts/analyze_fastgpt_flow_logs.py <flow-log.json> --format markdown
python3 ../fastgpt-shared/scripts/generate_import_readiness_report.py <workflow.json>
python3 ../fastgpt-shared/scripts/generate_parity_report.py <baseline.json> <candidate.json>
```

远端检查必须使用脱敏环境变量传入管理会话；OpenAPI/Workflow Bearer Key 不能冒充管理 API 凭据。管理脚本默认 dry-run，只有明确授权才可 `--apply`，发布还必须显式 `--publish`。

## Safety / Out of Scope

- 不读取、打印、提交或写入 API Key、Cookie、Token、HTTP Secret、系统工具 Secret、内部 URL、Agent/Workflow/Collection ID；报告只保留脱敏标识。
- 不修改或发布正式版 `工标（AgentV2）`；测试版也不因诊断自动变更。
- 不把本机 `.env`、macOS 工具、临时文件或本地包当成 AgentV2 VM 的运行证据；VM 依赖按 `vm-runtime-contract.md` 验证。
- 不用全库搜索、伪造 quote、扩大引用上限或删除证据校验换取速度表象。

## Escalation / Stop Conditions

遇到以下情况停止写入并报告：目标版本或权限无法确认；测试版/正式版对象可能混淆；Secret 作用域不明；schema 与当前导出冲突；持久消息不可读；或修复需要 runtime 源码权限、额外外部授权、解绑知识库或改变正式版。

## Related Files / Skills

- 基础合同：`../fastgpt-shared/SKILL.md`
- 运行时/VM：`../fastgpt-shared/references/runtime-diagnostics.md`、`../fastgpt-shared/references/vm-runtime-contract.md`
- 深度排错：`../fastgpt-shared/references/debug-playbook.md`
- 官方与版本合同：`../fastgpt-shared/references/fastgpt-official-contracts.md`
- 生成/迁移：`fastgpt-workflow-generator`、`fastgpt-workflow-migration`
- 例外 host：`fastgpt-python-host-adapter`、`fastgpt-ts-node-host-adapter`
