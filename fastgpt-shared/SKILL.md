---
name: fastgpt-shared
description: "Use when using FastGPT shared contracts, diagnostics, or scripts. 共享合同。"
disable-model-invocation: true
---

# FastGPT Shared Base

> This repository is a community FastGPT workflow engineering skill pack. It focuses on workflow JSON generation, import readiness, runtime diagnostics, workflow-tool decomposition, and migration support. It complements FastGPT's maintainer-oriented skills such as API development, PR review, tests, and documentation i18n. It is not a replacement for FastGPT official contracts; generated workflows must be validated against the target FastGPT instance.

Use this as the base layer for the FastGPT skill pack. It is the shared System of Record for:

- official FastGPT contract references
- target-instance canonical workflow examples
- runtime diagnostics and flow log tooling
- migration checklists and patterns
- the cross-Agent Business Delivery Harness
- GitHub distribution and multi-device install/sync rules

## Skill-pack install unit

Treat the following directories as one install unit:

- `fastgpt-shared`
- `fastgpt-workflow-generator`
- `fastgpt-workflow-debug`
- `fastgpt-workflow-migration`
- `fastgpt-ts-node-host-adapter`
- `fastgpt-python-host-adapter`

`fastgpt-shared` carries the heavy references/scripts. The other FastGPT skills are thin entrypoints that route into this base.

## Version and release identity

- This pack has one release identity: the Git tag or commit of the pack, together with the matching `CHANGELOG.md` entry. Do not invent per-skill versions or treat a consumer mirror's timestamp as a release.
- The FastGPT target version is instance-specific. Record and verify it from the current target export/detail before generating, importing, debugging, or publishing; do not generalize a `4.14.x` observation to `4.15.0-beta5` (or the reverse).
- The current project target is FastGPT `4.15.0-beta5`; this is a target-instance fact, not a reason to hard-code that version into portable examples. Version-sensitive claims must be labeled historical or re-verified against the target.
- Operator scripts in this pack are verified with Python 3.10+; if the local `python3` is older, use an available supported interpreter and record that fact. This requirement is for maintenance tooling only and says nothing about the AgentV2 VM runtime.
- Edit only the canonical pack source. Consumers are installed mirrors or symlinks; do not patch a consumer and do not publish/sync as an implicit step of validation.
- A pack release is ready only after all six directories, their referenced files, and the relevant validators have been checked. A green static check does not prove remote dashboard import, runtime behavior, VM dependency availability, or AgentV2 CITE projection.

## Read this first

1. `references/business-delivery-harness.md`
2. `references/fastgpt-official-contracts.md`
3. For importable workflow JSON, prefer target-instance exports and bundled `assets/canonical-examples/` over old probes.
4. Load only the next document you actually need:
   - runtime issues -> `references/runtime-diagnostics.md`
   - VM/OS/dependency issues -> `references/vm-runtime-contract.md`
   - AgentV2 启动脚本、`sandboxEntrypoint` 或 VM 环境注入 -> `references/vm-runtime-contract.md`
   - migration work -> `references/migration-checklist.md`
   - deep debug details -> `references/debug-playbook.md`
   - deep migration details -> `references/migration-playbook.md`
   - RAG / tools / fallback / layout patterns -> `references/patterns/*.md`

## When NOT to Use

- 不把 shared base 当作 AgentV2 业务 Skill；它服务于本地维护、生成、迁移和诊断。
- 不用它替代目标实例的 detail/export、运行日志、持久消息或 VM smoke。
- 不因加载本包就自动修改、发布、同步远端 FastGPT，尤其不能触碰正式版 AgentV2。

## VM-first platform boundary

Treat the FastGPT AgentV2 VM/Sandbox as a separate execution target from the maintainer's macOS or Linux host. Before adding a Skill dependency or a tool-workflow helper, record the target OS/architecture, runtime version, dependency origin, and request-time install policy in `references/vm-runtime-contract.md`. `sips`, `curl`, local Python packages, absolute host paths and other macOS/operator conveniences are not AgentV2 runtime evidence; a platform-specific fallback must be explicitly scoped and tested in the target VM. AgentV2 request paths must use preinstalled or packaged dependencies and must fail closed when a required dependency is unavailable—never install or download dependencies during a request.

## Script index

Use scripts instead of rewriting diagnostics by hand.

- export logs: `scripts/export_fastgpt_flow_logs.py`
- analyze logs: `scripts/analyze_fastgpt_flow_logs.py`
- scaffold workflows: `scripts/scaffold_fastgpt_workflow.py`
- validate workflow JSON: `scripts/validate_fastgpt_workflow.py`
- validate layout: `scripts/validate_fastgpt_layout.py`
- generate import readiness: `scripts/generate_import_readiness_report.py`
- create/update/publish workflow app: `scripts/create_fastgpt_app.py`（默认 dry-run；管理会话和节点 Secret 仅从环境变量读取）
- persist AgentV2 tool bindings: `scripts/bind_fastgpt_agent_tools.py`（默认 dry-run；将详情展开模板压缩为 `agent_selectedTools`）
- parity scan: `scripts/generate_parity_report.py`
- probe agent identity: `scripts/probe_fastgpt_agent_identity.py`
- host scans: `scripts/scan_ts_node_host.py`, `scripts/scan_python_host.py`

## Evidence Commands

在 pack root 执行定向发布门禁；`--skill` 可重复使用：

```bash
python3 scripts/check-skill-descriptions.py --root . \
  --skill fastgpt-shared \
  --skill fastgpt-workflow-debug \
  --skill fastgpt-workflow-generator \
  --skill fastgpt-workflow-migration \
  --skill fastgpt-python-host-adapter \
  --skill fastgpt-ts-node-host-adapter
python3 fastgpt-shared/scripts/validate_fastgpt_workflow.py <workflow.json>
```

这些命令只证明本地 pack/JSON 合同；远端导入、AgentV2 VM、运行性能、持久化消息和前端 CITE 仍需单独实测。

## Multi-device usage

## Canonical examples and publishing source

- Local maintenance source: the canonical `AGENT-SKILLS` repository selected by the current workspace; do not encode a maintainer's absolute path in a distributed skill.
- GitHub publishing repo: `watsonctl/fastgpt-agent-skills`.
- Published GitHub content must be materialized real files; do not publish external symlinks that point back to a maintainer's local checkout.
- `assets/golden-examples/` contains end-to-end verified production-grade workflow patterns.
- `assets/canonical-examples/` contains dashboard-import verified JSON and is the bundled System of Record for high-risk node shapes when no fresher target export is available.
- `assets/functional_nodes_library.json` is a comprehensive library of individual FastGPT functional nodes (Chat, Search, Extract, Classify, Tools) with their full input/output schemas.
- `assets/probe-examples/` are exploration probes. They are not production templates unless their README marks them canonical/import-verified.

### Ordinary device: install the whole pack from GitHub

Install the complete pack together so `../fastgpt-shared` references always resolve:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo watsonctl/fastgpt-agent-skills \
  --path fastgpt-shared \
  --path fastgpt-workflow-debug \
  --path fastgpt-workflow-migration \
  --path fastgpt-workflow-generator \
  --path fastgpt-ts-node-host-adapter \
  --path fastgpt-python-host-adapter
```

Restart Codex after installation. Use `--ref <tag-or-commit>` when a stable pinned install is required.

### Maintainer device: cloned repo + local mirror sync

- The canonical `AGENT-SKILLS` checkout is the maintainer source of truth for local development; the GitHub repo is a materialized publishing target.
- Consumer folders such as `~/.codex/skills` are installed mirrors, not editing targets.
- The repo-level sync script is for maintainers who cloned `watsonctl/fastgpt-agent-skills`; it materializes selected FastGPT skill directories from the maintenance source and is not bundled when installing a single skill path.
- From the repo root, sync the whole pack with:

```bash
scripts/sync-fastgpt-skill-pack.sh
```

## Runtime citation and schema-drift invariants

- Native frontend citations have one authoritative source: an actually executed `datasetSearchNode` whose quote is preserved by the host. A parent-workflow node is the default owner; on a tested AgentV2 host, a native child node under `childrenResponses` may be promoted at save time into the final message's `totalQuoteList`. Child `pluginModule` output, tool stdout, and Markdown `[id](CITE)` text alone do not register a quote.
- Citation probes must inspect the final message `responseData`, enable `retainDatasetCite: true`, and verify the intersection of the authoritative native `datasetSearchNode.quoteList` IDs with CITE IDs in final `text.content`; when the node is nested, also verify persisted `totalQuoteList`.
- A non-empty system-tool result that becomes empty after a code-node transform is a contract failure. Normalize only finite, documented aliases/case variants and make the loss visible; do not classify it as a genuine empty search.
- A pure Skill that is not the parent workflow must not call a FastGPT workflow over HTTP to simulate native citation registration. Keep tool workflows and parent-native citation ownership as separate responsibilities.
- A scoped parent `datasetSearchNode` must receive both `datasets` and `collectionFilterMatch` from the same runtime route output. A static all-dataset value plus an optional collection filter is not a scoped search contract and can degrade to dataset-wide retrieval when filtering is unavailable.
- When a route is empty, keep the native dataset input empty and take an explicit fallback branch; never turn an empty route into a default all-dataset search. If native `quoteQA` is empty, a separate web-answer branch may consume normalized web context; a non-empty native quote must stay on the native citation path.
- Continuous-dialogue retrieval has a separate contract: `chatNode.history` on the final answer is not enough. Before candidate/metadata/native search, use one bounded history-aware normalizer to turn the current turn into a self-contained query; bind downstream semantic `query` inputs to that output, keep the original current-turn text for the final answer, and never treat prior answer text as evidence. Test same-`chatId` follow-ups, a self-contained new question, an image follow-up, and invalid/truncated normalizer output.
- When query analysis merges observed and bounded model candidates, the metadata mapper must consume that merged output (`parsePlan.standardCandidates` or the equivalent), not only the raw observed-candidate output. Remove stale DAG edges that no longer represent an input dependency; otherwise valid model candidates can be dropped before `datasetId/collectionId` resolution or the graph can wait on an unrelated predecessor. This remains a bounded catalog lookup and never authorizes dataset-wide search.
- An observed legacy standard/version must not suppress a materially related current/replacement candidate from the bounded query plan. Merge and deduplicate observed plus planner candidates before catalog mapping, cap the merged set, and require every hypothesis to pass the controlled catalog; the absence of a matching collection must remain an explicit no-route state rather than a hardcoded or dataset-wide fallback.
- When a candidate includes a year but a controlled catalog row for the same standard number has no separate year field, route joining must prefer the exact `standardNo+year` row and may fall back only to the same-number yearless row; it must never fall back to an unrelated year. Treat a missing year as a catalog-shape compatibility case, not as permission to widen the search scope.
- For an unversioned shorthand such as `JGJ46`, decide version eligibility from the user's query rather than a year inferred by web context: use a bounded same-family/number yearless index and emit the catalog's actual edition. If the user explicitly writes a year, require that exact edition and never silently map to another year. Any `JGJ`/`JGJ/T` shorthand compatibility remains narrow and cannot become cross-family or dataset-wide search.
- Route identity is the normalized standard family + number + year, not number/year alone. A `GB`, `GB/T`, `JGJ`, `DB` or other family with the same number/year must never open another family's collection; a candidate without a family prefix is not a wildcard. When an explicit standard identity is present but unmapped, do not append generic catalog-title hints that could route a neighboring family. Title hints remain available for questions with no explicit standard identity and must still pass the bounded catalog and native evidence gates.
- `data/v2/list` 枚举出的正文只是“目标候选”，不会自动成为父消息 CITE；它必须通过有限的正文标题/规范性句子锚点，回填到父级 `datasetSearchInput`，再由原生 `datasetSearchNode` 重新产生 `quoteList`。只把原问题或无意义的中文二元词传给原生节点，会出现“枚举到目标 chunk、原生检索却 0 条”的假成功；回归应记录 `enumeratedChunkCount → anchorQueries → nativeQuoteList → final CITE` 的逐级交集。
- Web 观察候选与模型提出的有界候选必须分层合并：材料牌号、网页编号和偶然提及不能占满标准候选槽位；网页候选设置有限上限，并为 `precisionQueries` 保留槽位。所有候选仍须经目录映射和 `datasetId + collectionId` 双重范围校验，不能用候选扩容替代目标正文交付。
- When web results or natural-language input identify only a standard topic/name without a parseable standard number, a bounded catalog-title hint stage may propose at most three hypotheses. It must require distinctive overlap from the question (and use web context when available), treat the result as `observedIn=catalog_hint` rather than evidence, and keep title-only hints separate from正文. If candidate and retrieval-preparation logic are merged into one tool, the merged tool must retain the same non-empty compact catalog-title index as the standalone candidate module; an import-size optimization may compress the index but must not replace it with `[]` or a dataset-wide search. Every hint still goes through the controlled catalog, collection filter, native `datasetSearchNode`, failure filtering, and verification; no usable signal means no hint and never a dataset-wide search.
- 法律、法规、条例、规章、办法、通知等规范性文档可能没有可解析标准号，但其 collection 已存在于维护快照。为这类文档建立独立的 `normativeDocumentCandidates` 标题候选（最多 3 个），保留真实 `datasetId + collectionId`；候选必须经过非通用词/上下文门禁，不能虚构标准号，也不能把法规 collection 全量注入检索。候选仍须经过 collection-scoped 原生检索、失败过滤、验证和 CITE 投影。
- 规范性文档候选与标准号候选必须分层审计：`observed`/`catalog_hint`/`normative_document` 可进入受控目录核验；仅 `llm_candidate` 且没有独立问题、网页或标题佐证的标准号不得开 collection 路由。该门禁用于防止“模型猜到库内编号后误开相邻 collection”，不等同于恢复全库搜索。
- 规范性文档标题可能附带发文号/年份后缀；候选比较可使用经约束的核心标题变体，并优先网页/问题的非通用领域信号，避免“建筑/工程/规定”等通用词遮蔽目标文档。核心标题只确认快照中的真实 `collectionId`，仍须继续定向原生检索和证据门禁。
- 跨模块传递路由时必须同时保留 numbered-standard 与 `normative_document` 两种 route kind；不能让 resolver 只按标准号建索引，从而把已经由 `buildRouteCatalog` 生成的无标准号法律/法规/办法路由静默变成空路由。只接受上游受控 `routeCatalog` 中带完整 `datasetId + collectionId` 的标题路由，仍不得从任意模型输出或全量 collection 推断。
- 证据过滤只在比较层归一化标准号格式：`JGJ46`、`JGJ/T 46`、`JGJT46`、`JGJ_T46` 可视为同一 JGJ/T 家族进行相关性校验；不得据此修改目录身份、collection 路由或扩大检索范围。遇到“原生 quote 非空但过滤后为零”，先检查 `sourceName/q/a` 的标准号格式和 `relevanceRejectedCount`，不要直接判为库内无正文。
- A credential-bearing system-tool node must not be bundled into a frequently regenerated preparation graph. Put `systemTool-searchInfinity` (or another Secret-backed system tool) in a small, stable standalone workflow tool, configure and publish that tool once, and let the preparation workflow reference its published AppID through `pluginModule`. Later preparation/main graph updates must contain zero system-tool nodes; they must not attempt to preserve or inject the system Secret. The standalone tool may return normalized ordinary data such as bounded web context; native FastGPT CITE remains owned by a parent `datasetSearchNode` by default, or by a tested AgentV2 child-promotion path only after persisted-message verification.

## FastGPT API 创建与发布边界

目标实例允许通过管理 REST 接口直接创建、更新工作流或工作流工具：页面导入文件的
`nodes/edges/chatConfig` 会映射为 `POST /api/core/app/create` 的
`modules/edges/chatConfig`。普通工作流使用 `type: "advanced"`；工作流工具使用
`type: "plugin"`，并且必须把 `parentId` 指向 `toolFolder`。创建后如需上线，再向
`POST /api/core/app/version/publish?appId=...` 提交同一份图和 `isPublish: true`。
已有应用的工作流图通过 `POST /api/core/app/version/publish?appId=...` 保存：
`autoSave: true` 更新当前草稿，`isPublish: true` 创建线上版本；
`PUT /api/core/app/update?appId=...` 只适合更新名称、介绍、头像、类型或目录等应用元数据，不能拿来保存图。
更新时应用原有类型和工具目录归属保持不变，不应把创建用的 `type`/
`parentId` 误传成更新参数。

优先使用 `scripts/create_fastgpt_app.py`。它默认只做 schema/dry-run 校验，只有显式
`--apply` 才写入远程实例；`--mode update --app-id ...` 通过版本接口更新既有应用草稿，`--publish` 必须与
`--apply` 同时使用。管理 API 认证只能通过 FastGPT 登录会话环境变量注入；脚本不接受命令行明文 Key，
不打印原始响应，也不把凭据、Secret 或内部响应写入 JSON。实际创建/更新含 `httpRequest468` 节点的应用还必须显式
指定 `--http-bearer-env`；脚本只在发送请求时把该环境变量注入内存中的
`system_header_secret`，源 JSON 和日志仍不含 Secret。
如果 Secret 已由维护者在目标应用中手动配置，可在 `update + apply` 时使用
`--preserve-remote-http-secrets`：脚本先读取同一 AppID 的 detail，再按 `nodeId`
把已有 HTTP 节点 Secret 合并到内存中的更新请求；它不读取、不修改
`systemTool-searchInfinity` 等系统工具凭据。若远端对应节点没有已配置 Secret，脚本会停止更新，避免把空值覆盖到线上。
管理 API 的认证必须使用 FastGPT 登录会话
`fastgpt_token`：通过 `--auth-token-env` 传递 token 请求头，或通过 `--auth-cookie-env` 传递 Cookie；
不要把工作流/OpenAPI Bearer Key 当作管理凭据。该 API 可能受团队创建权限、
工具目录父级、应用数量上限和模型权限影响；创建成功不等于 HTTP Secret 已配置，也不等于
运行时 CITE/最终回答已验收。创建或更新后的 AppID 必须通过目标实例页面或 API 复核，发布后
还要运行 detail/flowResponses 冒烟。管理 API 写入成功不等于工作流运行闭环完成。

页面导入 JSON 与 OpenAPI create payload 不得混用：前者顶层只能是
`nodes/edges/chatConfig`，后者才包含 `name/type/modules`。`systemTool-searchInfinity`
和 HTTP `system_header_secret` 仍由 FastGPT 的系统工具/节点 Secret 配置管理，不能为了
自动创建而把密钥写进 payload。导入后，HTTP 节点要在画布节点右上角的认证面板分别配置
`Bearer`；`system_header_secret` 是每个 `httpRequest468` 节点自己的隐藏配置，两个节点不会
自动共享。对于 `system_httpContentType=json`，上游代码节点必须输出 JSON 字符串（通常为
`JSON.stringify(payload)`），不能直接输出对象。另一个容易忽略的 v4.15 运行时合同是：
`httpRequest468` 的隐藏 `system_httpReqUrl`/`system_httpJsonBody` 输入不会按普通
`[nodeId, outputKey]` 数组引用解析；应使用 `{{$nodeId.outputKey$}}` 模板承载上游 URL
和 Body 字符串，否则可能分别报 `Invalid URL` 或 `Invalid JSON body`。更新并发布成功后仍须
运行模块冒烟，确认实际请求 URL/Body 已解析。

应用 `update/publish` 不会替 `systemTool-searchInfinity` 写入系统工具凭据；该凭据必须在
系统工具/插件管理中保存，或使用目标实例已授权的手动输入模式。HTTP Secret 注入成功、
AppID 正确或发布接口返回成功，都不能替代一次发布后的准备模块直连冒烟。若运行态返回
`Either apiKey or both volcengineAccessKey and volcengineSecretKey must be provided`，应将其
分类为系统工具凭据作用域/保存状态故障；系统工具管理接口返回 `403` 时停止写入，不得把
普通工作流 Bearer Key 当作管理凭据，也不得用 fallback 文本或 HTTP 200 判定成功。

注意：管理 API 的 `update` 可能重写工作流节点快照，但不会把用户在 FastGPT UI 中保存的
`systemTool-searchInfinity` Secret 作为页面导入 JSON 或发布 payload 的一部分可靠回填。凡更新含
系统工具节点的应用，发布后必须重新做一次该节点的真实运行冒烟；若出现系统工具凭据缺失，只能
由有权限的维护者在 FastGPT 系统工具/节点认证面板重新保存，技能和管理脚本不得偷偷注入或打印该密钥。

当联网工具需要长期使用而其上游检索准备逻辑仍会频繁调整时，应先创建一个只包含
`pluginConfig → pluginInput → systemTool → 结果归一化 → pluginOutput` 的独立工作流工具。
首次配置该工具的系统 Secret 并发布后，准备模块只引用它的已发布 AppID；更新准备模块时可使用
`--preserve-remote-http-secrets` 保留其 HTTP 节点认证，但不能把独立工具的系统 Secret 当作可由
图更新自动保留的配置。独立工具没有密钥时的运行失败必须单独归类为凭据作用域问题，不能误判为
“联网无结果”或“本地知识库没有标准”。

## Guardrails

- **Keep SKILL.md thin**: Heavy knowledge belongs in `references/` and repeatable actions belong in `scripts/`.
- **Domain Portability (Harness Engineering)**: Shared guidance and probe examples must stay domain-portable. 
  - Do not strip FastGPT core schema keys (e.g., `candidates`, `sourceRefs`, `documentType`), but replace specific business payload values (e.g., `008`, `construction_scheme`) with generic placeholders (`generic_document`, `sample_module`).
  - Avoid referencing private instance configurations. Use generic terminology like `Observed in tested FastGPT instances`.
- **Open Source Contribution Strategy**: Do not submit the entire skill pack as a single PR. Follow the calculated contributor path:
  1. **Issue**: Propose feature requests (e.g., Workflow-as-Code capabilities) without hardcoding endpoint designs.
  2. **Docs PR**: Provide restrained, official-style documentation (e.g., `AI-assisted Workflow Development`). Avoid personal engineering paradigms (like "100-node paradigm") and use standard Markdown syntax (e.g., blockquotes instead of GitHub alerts) for compatibility.
  3. **Examples PR**: Submit minimal, highly generic JSON examples. Avoid complex or unstable nodes (`parallelRun`, `loop`) in early submissions.
  4. **Skill/RFC PR**: Only submit minimal skills or API implementations after achieving maintainer consensus.
- **Paths**: Use relative paths only; the GitHub-distributed pack must work on any device after install.
- **Acceptance Gate**: Do not treat node success as acceptance. Business delivery, evidence, traceability, and stable closure are the acceptance gate.

## Safety / Stop Conditions

目标版本、当前导出、Secret 作用域、VM 依赖或证据 owner 无法确认时停止，不凭记忆补合同。需要 remote update/publish、runtime 源码权限、正式版变更或跨 OS fallback 时，先报告缺口并等待明确授权。
