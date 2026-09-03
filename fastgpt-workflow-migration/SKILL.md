---
name: fastgpt-workflow-migration
description: "Use when migrating an existing app or RAG flow to FastGPT JSON. 工作流迁移。"
disable-model-invocation: true
---

# FastGPT Workflow Migration

## Purpose

在保留业务行为、证据链和可回滚性的前提下，把已有应用、RAG 流程或服务迁移成 FastGPT workflow / Workflow-Tool bundle。迁移不是把代码机械翻译成节点，也不是只让 JSON 通过导入。

## When to Use

- 用户要求将现有 workflow、RAG、工具链或应用迁移为 FastGPT JSON。
- 需要比较原系统与 FastGPT 图的能力、数据、证据、错误和性能覆盖。
- 需要输出可导入包、绑定模式、parity 和 import-readiness 证据。

## When NOT to Use

- 新建图：使用 `fastgpt-workflow-generator`。
- 已有图运行异常、CITE 丢失或 AgentV2 长尾：使用 `fastgpt-workflow-debug`。
- 只有在 workflow-only 与 workflow+workflow-tools 都有证据不足后，才考虑 host adapter，并需用户明确批准。

## Architecture Context

- 维护源是 canonical `AGENT-SKILLS` checkout；consumer 是安装镜像或软链。
- 目标 FastGPT 当前成功导出/运行结果优先于旧模板；官方文档只作语义参考。
- 当前项目目标为 `4.15.0-beta5`。每次迁移仍需从目标实例确认版本、节点 schema、VM/架构、依赖来源和 Secret 作用域，不能把 beta5 结论推广到其他版本。
- 运行时所需依赖必须预装或随制品携带；禁止 request-time install、跨 OS native binary 和把本机 `.env` 当 VM 配置。
- 若源系统有 VM 初始化脚本，迁移到 beta5 AgentV2 时映射到目标 Agent detail 的
  `sandboxEntrypoint` 字符串，并单独记录 Skill 挂载顺序、脚本 hash/超时、Secret 来源
  和 cold/warm 行为；不能把源环境 `export` 或 `.env` 直接视为目标 VM 的注入合同。

## Migration Operations

### Capability ladder

先记录模式并说明理由：

1. `workflow-only`
2. `workflow+workflow-tools`
3. `exception-helper-approved`

默认优先原生节点和 Workflow-Tool。稳定纯执行能力才进入工具；意图识别、受控 route 和最终证据决策仍由明确的 Skill/宿主/父图 owner 负责。避免 Agent、工具和 Skill 对同一阶段重复调用模型或检索。

### Required mapping

为每个原系统阶段记录 FastGPT 节点、输入输出、错误/超时/重试、缓存和观测字段。涉及知识库时必须保留受控 `datasetId + collectionId` route、原生 `datasetSearchNode` 和证据范围；联网发现与联网兜底要和本地 CITE 分层。

涉及 AgentV2 时，持久化验收必须覆盖：

```text
native quoteList
  -> childrenResponses.quoteList (if nested)
  -> persisted totalQuoteList
  -> final text real quote IDs
  -> frontend CITE
```

嵌套 quote、`datasetQuote`、工具文本和 `flowResponses` 单独都不构成 CITE 证明。失败、超时和降级结果不进入成功缓存。

迁移启动脚本时还必须验证：

```text
target detail.sandboxEntrypoint
  -> VM startup execution
  -> Skill file/config handoff
  -> Skill entrypoint
  -> actual LLM/vision smoke
```

`sandboxEntrypoint` 能读回只证明配置保存；不能替代 VM 运行证据。若 Secret 来源、
文件生命周期或跨命令环境可见性未验证，应保留为 migration gap，不把本机 `.env`、
不写入硬编码凭据到产物，也不把请求期安装作为兼容层。

### Required outputs

- importable workflow JSON 或明确标记的 template JSON
- migration mode、binding mode 和 target-version note
- parity / coverage view
- import-readiness 与静态验证结果
- Business Delivery Harness acceptance；远端导入、运行、持久消息和前端 CITE 若未实测，必须标为未验证

## Evidence Commands

```bash
python3 ../fastgpt-shared/scripts/validate_fastgpt_workflow.py <workflow.json>
python3 ../fastgpt-shared/scripts/validate_fastgpt_layout.py <workflow.json>
python3 ../fastgpt-shared/scripts/generate_import_readiness_report.py <workflow.json>
python3 ../fastgpt-shared/scripts/generate_parity_report.py <source-evidence.json> <candidate-evidence.json>
```

## Safety / Out of Scope

- 不把 API Key、Cookie、Token、HTTP/system-tool Secret、内部 URL、真实资源 ID 写入产物或日志。
- 不把导入成功称为运行闭环成功，不自动 update/publish 远端应用。
- 不修改或发布正式版 AgentV2；线上写入必须是单独、明确授权的动作，默认只在测试版验证。

## Escalation / Stop Conditions

源行为不可重放、目标导出缺失、版本/schema 冲突、Secret 或 VM 依赖不可验证、parity 关键项无法判断，或需要改变正式版时停止迁移，先输出差异和缺口。

## Related Files / Skills

- 基础合同：`../fastgpt-shared/SKILL.md`
- 迁移清单/深度手册：`../fastgpt-shared/references/migration-checklist.md`、`../fastgpt-shared/references/migration-playbook.md`
- 生成/调试：`fastgpt-workflow-generator`、`fastgpt-workflow-debug`
- 例外 host：`fastgpt-python-host-adapter`、`fastgpt-ts-node-host-adapter`
