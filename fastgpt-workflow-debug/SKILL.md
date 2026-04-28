---
description: FastGPT 工作流 JSON 调试与优化 Skill。覆盖主工作流（advanced workflow）和工具工作流（workflow tool / pluginModule）的结构校验、节点合约检查、边完整性、代码节点排错、工具绑定验证、运行时 bug 诊断。 触发词：修复 FastGPT 工作流、调试 workflow JSON、FastGPT 导入失败、节点连接断裂、代码节点报错、工具工作流 bug、workflow 优化。
metadata:
    github-path: fastgpt-workflow-debug
    github-ref: refs/heads/main
    github-repo: https://github.com/watsonctl/fastgpt-agent-skills
    github-tree-sha: 0cebfd28ddee9bb44a44f66a323583ae73c33f22
name: fastgpt-workflow-debug
---
# FastGPT Workflow Debug & Optimization

## When to Use

当遇到以下场景时**必须**加载本 skill：
- FastGPT 工作流 JSON 导入失败或导入后行为异常
- 节点间数据传递丢失、类型不匹配
- 代码节点（`code`）sandbox 运行报错
- 工具工作流（pluginModule）调用不生效或参数不透传
- LLM 节点（chatNode）输出解析失败
- ifElse / loop / parallelRun 分支逻辑不触发
- edge 断裂导致工作流提前终止
- 从 FastGPT 平台导出的 JSON 需要离线修复再重新导入

## 0. 前置：FastGPT 官方 JSON 合约速查

> 以下枚举和字段名直接来源于 FastGPT 官方仓库 `labring/FastGPT`，是唯一 ground truth。

### 0.1 FlowNodeTypeEnum（节点类型）

```
userGuide          — 系统配置（systemConfig）
workflowStart      — 工作流起始节点
chatNode           — AI 对话（LLM 调用）
datasetSearchNode  — 知识库搜索
datasetConcatNode  — 知识库结果合并
answerNode         — 固定回答
classifyQuestion   — 问题分类
contentExtract     — 内容提取
httpRequest468     — HTTP 请求
code               — 代码运行（JS/Python sandbox）
ifElseNode         — 条件判断
variableUpdate     — 变量更新
textEditor         — 文本编辑器
readFiles          — 读取文件
userSelect         — 用户选择
formInput          — 表单输入
loop               — 循环容器
loopStart          — 循环起始（必须在 loop 内）
loopEnd            — 循环结束（必须在 loop 内）
parallelRun        — 并行容器
pluginConfig       — 插件/工具工作流配置
pluginInput        — 插件输入
pluginOutput       — 插件输出
pluginModule       — 插件/工具引用节点
appModule          — 应用引用
app                — 运行应用（runApp）
tool               — 工具节点
toolSet            — 工具集
agent              — Agent 模式
tools              — toolCall
```

### 0.2 NodeInputKeyEnum（关键输入字段名）

| 字段 | key 值 | 说明 |
|---|---|---|
| 用户输入 | `userChatInput` | 用户问题文本 |
| 模型选择 | `model` | LLM 模型名 |
| 系统提示词 | `systemPrompt` | chatNode 系统提示 |
| 历史记录 | `history` | 对话历史 |
| 数据集引用 | `quoteQA` | 知识库检索结果 |
| 温度 | `temperature` | LLM 温度 |
| 最大 token | `maxToken` | 最大输出 token |
| 代码 | `code` | 代码节点代码 |
| 代码类型 | `codeType` | `js` 或 `py` |
| 数据集选择 | `datasets` | 知识库选择列表；`selectDataset` 只应出现在 `renderTypeList/valueType`，不要作为运行时 input key |
| 相似度 | `similarity` | 检索相似度阈值 |
| 检索数量 | `limit` | observed in tested FastGPT instances 中应按 chunk 数量/检索上限治理；主检索建议 quick≈20、standard≈50、deep≈100，禁止误设 4000+ |
| 搜索模式 | `searchMode` | `embedding` / `fullTextRecall` / `mixedRecall` |
| ReRank | `usingReRank` | 是否启用重排序 |
| 条件判断 | `ifElseList` | ifElse 条件列表 |
| 插件ID | `pluginId` | pluginModule 引用的 appId |
| 变量列表 | `variables` | chatConfig 对话变量 |

### 0.3 NodeOutputKeyEnum（关键输出字段名）

| 字段 | key 值 | 说明 |
|---|---|---|
| 用户输入 | `userChatInput` | 透传用户问题 |
| 回答文本 | `answerText` | LLM 回答内容 |
| 推理文本 | `reasoningText` | 思维链（reasoning） |
| 知识库引用 | `quoteQA` | 检索结果 |
| 原始响应 | `system_rawResponse` | 代码节点完整返回 |
| 错误 | `error` (**deprecated**) / `system_error_text` | 错误输出 |

### 0.4 WorkflowIOValueTypeEnum（值类型）

```
string, number, boolean, object,
arrayString, arrayNumber, arrayBoolean, arrayObject, arrayAny, any,
chatHistory, datasetQuote, dynamic, selectDataset
```

### 0.5 Edge 结构

```json
{
  "source": "<sourceNodeId>",
  "target": "<targetNodeId>",
  "sourceHandle": "<sourceNodeId>-source-<handleKey>",
  "targetHandle": "<targetNodeId>-target-<handleKey>"
}
```

handle 命名规范：`<nodeId>-source-right` / `<nodeId>-target-left`。
条件分支：`<nodeId>-source-<branchId>`。

### 0.6 顶层 JSON 结构

```json
{
  "nodes": [ ... ],
  "edges": [ ... ],
  "chatConfig": {
    "welcomeText": "",
    "variables": [],
    "questionGuide": {},
    "ttsConfig": {},
    "whisperConfig": {},
    "scheduledTriggerConfig": {},
    "chatInputGuide": {},
    "fileSelectConfig": {},
    "instruction": "",
    "autoExecute": {}
  }
}
```

## 1. 结构完整性检查清单

对目标 JSON 执行以下检查，**每一项必须报告 PASS / FAIL + 具体位置**：

### 1.1 顶层结构
- [ ] JSON 可解析，无语法错误
- [ ] 存在 `nodes` 数组且非空
- [ ] 存在 `edges` 数组
- [ ] 如果是主工作流（非 pluginModule 工具），存在 `chatConfig` 对象
- [ ] 如果是工具工作流，有 `pluginInput` + `pluginOutput` 节点

### 1.2 节点校验
- [ ] 每个节点有唯一 `nodeId`（无重复）
- [ ] 每个节点的 `flowNodeType` 是官方合法枚举值
- [ ] 存在且仅存在一个 `workflowStart` 节点（主工作流）
- [ ] 存在且仅存在一个 `userGuide` 节点（主工作流）
- [ ] `loop` 容器内有且仅有一个 `loopStart` 和一个 `loopEnd`
- [ ] `parallelRun` 容器不包含交互节点（`userSelect` / `formInput`）
- [ ] 嵌套子节点（`parentNodeId`）指向存在的父容器节点

### 1.3 Edge 完整性
- [ ] 每条 edge 的 `source` 和 `target` 对应存在的 nodeId
- [ ] `sourceHandle` 格式正确：`<sourceNodeId>-source-<handleKey>`
- [ ] `targetHandle` 格式正确：`<targetNodeId>-target-<handleKey>`
- [ ] 从 `workflowStart` 出发有可达路径到所有非配置节点
- [ ] 无孤立节点（除 `userGuide` / `pluginConfig` 外）
- [ ] 无自循环 edge

### 1.4 输入引用校验
- [ ] `value: ["nodeId", "outputKey"]` 引用的 nodeId 存在
- [ ] 被引用的 outputKey 在对应节点的 `outputs` 中有定义
- [ ] 引用的 `valueType` 与目标输出的 `valueType` 兼容
- [ ] `VARIABLE_NODE_ID` 引用的 key 在 chatConfig.variables 中有定义

## 2. 节点类型专项检查

### 2.1 chatNode（AI 对话）
- [ ] `model` 字段不为空
- [ ] `systemPrompt` 不为空（除非有明确设计意图）
- [ ] `maxToken` 在合理范围（通常 500~32000）
- [ ] `temperature` 在 0~2 范围
- [ ] `aiChatIsResponseText` / `isResponseAnswerText` 布尔值正确（控制是否流式输出给用户）
- [ ] `quoteQA` 引用的知识库搜索结果格式为 `["nodeId", "quoteQA"]`
- [ ] `history` 值合理（0 = 无历史，影响多轮对话）
- [ ] 模板变量 `{{$nodeId.outputKey$}}` 在 systemPrompt 中引用的节点和 key 存在

### 2.2 code（代码运行）
- [ ] `codeType` 为 `js` 或 `py`
- [ ] `code` 字段非空
- [ ] JS 代码定义了 `async function main(...)` 入口
- [ ] **官方动态输入契约**：必须存在 `key: "addInputParam"`、`renderTypeList: ["addInputParam"]`、`valueType: "dynamic"` 的动态输入。
- [ ] **官方动态输入契约**：所有需要传入 `main()` 的业务输入必须设置 `canEdit: true`；否则运行时不会进入 code sandbox 的 `customVariables`，`flowResponses.customInputs` 会是 `{}`。
- [ ] `main` 函数参数名与可编辑业务 inputs 的 key 一一对应；不要把 `codeType`、`code` 或 `addInputParam` 当业务参数。
- [ ] `return` 的字段名与 outputs 的 key 一一对应（`type: "dynamic"` 的输出）
- [ ] 代码中无 `require()` / `import`（FastGPT sandbox 不支持）
- [ ] 代码中无 `fetch()` / `XMLHttpRequest`（sandbox 无网络）
- [ ] 字符串转义正确：JSON 内嵌代码，`\n` → `\\n`，`"` → `\"`
- [ ] **关键**：代码中的正则表达式转义层级正确（JSON 内嵌需要双重转义）

### 2.3 datasetSearchNode（知识库搜索）
- [ ] `datasets` 非空，包含至少一个 `{datasetId: "..."}` 对象
- [ ] 当前官方运行时参数 key 必须是 `datasets`；发现旧 key `selectDataset` 时要判为 P1，因为 dispatch 会按 `datasets=[]` 处理
- [ ] `datasets` 的 `selectedTypeIndex` 必须与值形态一致：静态数组 `[{ datasetId }]` 用 `0`，节点引用 `["nodeId", "outputKey"]` 用 `1`；否则 UI 会切到错误模式并报“选择引用变量”。
- [ ] `collectionFilterMatch` 同样遵守值形态：静态空字符串/静态 JSON 用 `selectedTypeIndex: 0`，节点引用才用 `1`。
- [ ] `limit` 不得被当成 token 预算。主检索通常控制在 20~100 chunk；引用授权单 collection 小检索可单独校准，但禁止 4000+ 暴力值
- [ ] `searchMode` 值合法：`embedding` / `fullTextRecall` / `mixedRecall`
- [ ] `similarity` 在 0~1 范围
- [ ] `userChatInput` 引用有效

### 2.4 ifElseNode（条件判断）
- [ ] `ifElseList` 数组非空
- [ ] 每个条件的 `variable` 引用有效
- [ ] `condition` 值合法（`equalTo` / `notEqual` / `isEmpty` / `isNotEmpty` / `greaterThan` / `lessThan` / `greaterThanOrEqualTo` / `lessThanOrEqualTo` / `contain` / `notContain` / `startWith` / `endWith` / `reg` / `lengthEqualTo` / `lengthNotEqualTo` / `lengthGreaterThan` / `lengthGreaterThanOrEqualTo` / `lengthLessThan` / `lengthLessThanOrEqualTo` / `arrayContains`）
- [ ] 每个分支（IF0 / IF1... / ELSE）都有对应的 edge 连出

### 2.5 pluginModule（工具引用）
- [ ] `pluginId` 不为空，且不是占位符（如 `__WORKFLOW_TOOL_*__`）—— 除非是 template 文件
- [ ] 输入/输出与被引用的工具工作流的 `pluginInput` / `pluginOutput` 匹配

### 2.6 loop / parallelRun（容器节点）
- [ ] `childrenNodeIdList` 数组包含所有子节点的 nodeId
- [ ] 子节点的 `parentNodeId` 指向容器节点
- [ ] loop 内有 `loopStart` + `loopEnd`
- [ ] `loopInputArray` 引用有效

## 3. 代码节点深度排错

FastGPT sandbox（VM2）限制严格，以下是高频 bug：

> **v4.14.11+ 变更**：sandbox 镜像更新到 `v4.14.11`，Python 代码空入参不再被忽略（#6756）。如果自部署实例 sandbox 镜像未同步升级，可能仍有旧行为。v4.14.13 修复了 opensandbox 鉴权绕过安全漏洞（#6781），必须确认 sandbox 镜像已包含此补丁。

### 3.1 code node 动态输入契约陷阱

FastGPT 代码运行节点实际只把 `addInputParam` 动态输入下的可编辑变量传给 sandbox。运行态证据：`flowResponses` 里 code 节点的 `customInputs` 应该列出这些变量。

**故障特征**：
- code 节点执行成功，但 `customInputs: {}`。
- `main({ userQuery, analyzerText })` 中所有变量都是 `undefined`。
- 上游 AI 节点 `query` 非空，但下游 code 输出把用户问题洗空。

**修复方式**：
- 在 code node inputs 开头加入 `addInputParam` 动态输入。
- 对所有业务变量输入设置 `canEdit: true`。
- 不要只改 `valueType: any/string`；如果缺少动态输入契约，变量仍不会传入 sandbox。

### 3.2 数据包装陷阱

FastGPT 节点间传值可能被包装为 `{text: ...}` / `{content: ...}` / `{value: ...}` 对象。
**防御模式**：
```javascript
// 推荐始终使用 extractFastGPTPlainText 进行纯文本提取
const extractFastGPTPlainText = (value) => collectFastGPTTextFragments(value)
  .map(item => String(item || '').trim())
  .filter(Boolean)
  .join('\n')
  .trim();
```

### 3.3 RAG 运行态真实性陷阱

以下故障必须优先用 `flowResponses` / `detail=true` 证据判断，不能只看最终 `choices.message.content`：

1. **有 quoteList 但最终无 CITE**
   - 特征：工具内或主工作流 `datasetSearchNode.quoteList` 非空，`finalQuoteQA` 非空，但最终回答没有 `[24hex](CITE)`。
   - 后果：FastGPT `totalQuoteList=[]`，API/历史记录看起来“没有引用”，即使 RAG 实际跑了。
   - 修复：最终 prompt 必须要求复制真实 quote id，证据上下文应显式给出 `引用写法：[id](CITE)`；不要只把 quoteQA 传给 AI。

2. **registry 覆盖缺失**
   - 特征：用户问题出现 `南方电网 / 南网 / Q/CSG`，但 `normalizeInput.availableDatasetKeys` 不含 `southern_grid`；或出现 `DL/NB/电力` 但不含 `energy_power`。
   - 后果：检索只能在默认小 registry 内兜底，表现会显著低于原系统。
   - 修复：从 SoR 的 dataset 清单生成全量 registry，然后用 analyzer/bridge 收敛检索范围，不要把未挂库误判为模型能力差。

3. **推断标准被误当成用户明确指定**
   - 特征：用户原文没有标准号/标准名，`analysisBridge.hasExplicitStandard=true` 且 `precisionTasks` 非空。
   - 后果：FAQ 被压制，precision 锁定错误标准，ranking wrong-standard penalty 反向伤害正确答案。
   - 修复：拆分 `userExplicitStandards` 与 `inferredStandards`；只有用户原文明确出现的标准可进入硬 precision lock，推断标准只能作为软召回 query。

4. **API detail=false 误判 RAG 未运行**
   - FastGPT 对话接口 `detail=false` 只看最终文本。要判断是否接上 RAG，必须使用 `detail=true` 或导出 `flowResponses`，并检查 `candidateQuotes / quoteList / finalQuoteQA / citeIds`。

### 3.4 JSON 双重转义

code 字段的值本身在 JSON 字符串内，因此：
- 代码中的 `\n` 换行 → JSON 中写 `\\n`
- 代码中的 `"` 引号 → JSON 中写 `\"`
- 代码中的 `\b` (regex word boundary) → JSON 中写 `\\b` → 但注意代码中已经是字符串字面量的一部分
- **正则表达式**是最容易出错的：`/\b.../` 在代码中 → 代码字符串 `\\b` → JSON 中 `\\\\b`

### 3.5 sandbox 不可用 API

以下在 FastGPT sandbox 中**不可用**：
- `require()`, `import`
- `fetch()`, `XMLHttpRequest`, `WebSocket`
- `setTimeout()`, `setInterval()`（部分版本受限）
- `process`, `__dirname`, `Buffer`
- `console.log`（不会输出到用户可见位置）

### 3.6 返回值丢失

如果 `main()` 的 `return` 对象中缺少某个 output key 对应的字段，下游节点收到的是 `undefined`。
**检查方法**：对比 `return {...}` 的字段列表 vs node `outputs` 中所有 `type: "dynamic"` 的 key。

## 4. 工具工作流（Workflow Tool）专项

### 4.1 结构要求

工具工作流必须包含：
- 一个 `pluginInput` 节点（定义工具的输入参数）
- 一个 `pluginOutput` 节点（定义工具的输出参数）
- pluginInput → [业务节点链] → pluginOutput 的完整 edge 路径
- `pluginInput.inputs[]` 必须镜像生成同名 `outputs[]`：
  - `id = key`
  - `key = key`
  - `type = "static"`
  - `valueType = input.valueType`
- 原因：FastGPT 内部引用 `["pluginInput", "xxx"]` 时按 `node.outputs.find(output.id === "xxx").value` 取值。若 `pluginInput.outputs=[]`，外层 `toolInput` 即使非空，工具内部 code / datasetSearch 也会拿到空值。

### 4.2 工具绑定验证

检查 manifest 和 bindings 文件：
- `manifest.workflowTools[].placeholderToolId` 在 template JSON 中被引用
- `bindings.appIdByToolName` 中每个工具名对应有效 appId
- 主工作流中的 `pluginModule` 节点 `pluginId` 与 bindings 一致

### 4.3 输入输出对齐

主工作流中调用工具节点时传入的参数 key → 必须与工具工作流 `pluginInput` 节点的 outputs key 一致。


### 4.5 工具内泛检索 `parallelRun` 输出陷阱

**故障特征**：
- 主工作流 `pluginModule.toolInput.generalTasks` 非空。
- 检索工具内部 `datasetSearchNode` 参数理论上有效。
- 但 `pluginOutput.generalQuotes` 为空或 `candidateCount=0`；同时精准检索 `precisionLoop` 曾经能返回结果。

**根因模式**：
- 在部分自部署 FastGPT 中，工作流工具内部 `parallelRun` 的 `parallelSuccessResults` 不稳定或不适合承载 datasetSearch quoteQA 聚合；之前靠“推断标准硬锁 precisionTasks”偶然有结果，一旦修正为软召回，泛检索 0 结果就暴露。

**修复方式**：
- 对关键 RAG 泛检索优先使用 `loop -> loopEnd -> loopArray -> flatten code`，不要把主证据链建立在 `parallelRun.parallelSuccessResults` 上。
- 如果确需并行，必须用 flowResponses 证明 `parallelSuccessResults` 实际含 quoteQA；否则判 P1。
- 分析脚本看到 `generalTasks>0` 且 `generalQuotes=0/candidateCount=0` 时，应先查该模式。


### 4.6 `loop` 稳定后必须控制首轮检索任务数

**故障特征**：
- 为绕开 `parallelRun.parallelSuccessResults` 丢失 quoteQA，已把泛检索改成 `loop -> loopArray`，`candidateCount` 恢复非空。
- 但 `工作流工具：检索编排` 耗时 60s+，flowResponses 显示 `generalTasks` 约 18-20 个，且每个任务都是顺序 datasetSearch。

**根因模式**：
- `loop` 提升了输出稳定性，但它通常是顺序执行；如果 analyzer 把 `rewrittenQueries + inferredStandards` 再乘以多个 dataset/tag 变体，首轮会变成串行暴力检索。

**修复方式**：
- 首轮泛检索只保留 top 1 主查询 × top 2 目标库 × no-tag/高置信 tag 变体，通常 4 个、最多 6 个任务。
- analyzer 推断标准进入 `deferredGeneralTasks`，只作为低证据补查/诊断，不进入首轮 loop。
- 保持“国标优先、行业库补强”为任务顺序和证据排序优先级；不要把它实现成全库全 tag 串行扫描。
- 在 bridge 输出 `initialGeneralTaskCount / deferredGeneralTaskCount / retrievalPriorityPlan`，运行态看到 `generalTasks>6` 应优先判为检索预算失控。


### 4.7 速度恢复后质量下降：检查 deferred 补查是否真正接线

**故障特征**：
- `工作流工具：检索编排` 已降到可接受耗时，`generalTasks<=6`。
- 但回答质量明显变差，常见表现是只命中相邻主题证据、finalQuoteQA 少、回答过度保守。

**排查顺序**：
1. 看 `analysisBridge.workflowBuildVersion`，确认线上发布的是最新 JSON；若仍有 `retrievalLimit=5000/8000`、`<suggested_questions>` 或缺少 `initialGeneralTaskCount`，先判导入/发布漂移。
2. 看 `analysisBridge.deferredGeneralTasks` 是否非空。
3. 看 `evidencePass1.shouldAutoRequery` 是否在弱证据时为 true。
4. 看 `retrievalAuto.toolInput.generalTasks` 是否引用并收到 `evidencePass1.deferredGeneralTasks`；如果为空，说明 deferred 只是诊断字段，没有进入二阶段补查。
5. 看最终回答是否还有“当前知识库未直接检索到…”这类冷冰冰话术；这属于 final prompt / fallback 文案问题，不是检索能力问题。

**修复方式**：
- 保持首轮 `generalTasks<=6`，不要回退到 18-20 个串行任务。
- 将 deferred fan-out 接到二阶段 gated retrieval：弱证据时最多补 4-6 个任务。
- 最终回答采用 friendly evidence-boundary fallback：先给可执行参考判断，再温和说明证据边界；不要把系统失败感暴露给用户。

### 4.4 外层 toolInput 非空但工具内部输出空

**故障特征**：
- 主工作流 `pluginModule.toolInput` 显示 `generalTasks/userQuery/queryType` 非空。
- 工作流工具内部返回空结果，例如 `candidateCount=0`、`finalUserPrompt` 里 `用户问题:` 为空。
- 标准定位、检索编排、证据整理多个工具同时表现为“像没收到参数”。

**优先排查**：
1. 打开被调用的工作流工具 JSON。
2. 检查 `pluginInput.outputs` 是否与 `pluginInput.inputs` 同名同序。
3. 检查内部节点是否引用 `["pluginInput", "<inputKey>"]`，且 `<inputKey>` 在 outputs 中存在。
4. 对检索工具继续检查 datasetSearchNode 是否使用 `key: "datasets"`，不是旧 `selectDataset`。

## 5. 常见 Bug 模式速查表

| Bug 现象 | 根因 | 修复方法 |
|---|---|---|
| 导入后节点全部堆叠在左上角 | `position` 字段缺失或全为 (0,0) | 重新计算 layout |
| datasetSearch 明明有 `[{datasetId}]` 但 UI 显示“选择引用变量”并校验失败 | 静态 `datasets` 被错误设置为 `selectedTypeIndex: 1` | 静态知识库数组改为 `selectedTypeIndex: 0`；动态引用才用 `1` |
| `collectionFilterMatch` 空值却要求选择引用变量 | 静态空字符串被错误设置为引用模式 | 空字符串/静态 filter 用 `selectedTypeIndex: 0`；节点引用才用 `1` |
| "找不到节点" 错误 | edge 的 source/target 引用了不存在的 nodeId | 修复 nodeId 或删除孤立 edge |
| 代码节点报 "main is not a function" | 代码中 `function` 声明被截断或转义错误 | 检查 JSON 字符串转义 |
| 知识库搜索返回空 | `datasets` 值为空数组 `[]` | 填入正确的 `[{datasetId: "..."}]` |
| 外层 workflow tool `toolInput` 非空但工具输出空 | `pluginInput.inputs` 没有镜像为同名 `outputs`，内部引用无法取值 | 给 pluginInput 补同名 outputs |
| datasetSearch 工具输入看起来有库但仍空检索 | 使用旧 input key `selectDataset`，当前 runtime 只读 `datasets` | 将 datasetSearchNode input key 改为 `datasets` |
| code 节点 `customInputs={}` | 缺少 `addInputParam` 动态输入或业务输入未设 `canEdit:true` | 按官方 code-node 契约补动态输入，不要只改 valueType |
| `chat:AI_input_is_empty` | 通常是上游 prompt/userChatInput 被洗空，不一定是 AI 节点本身 | 先查 finalUserPrompt，再查 analysisBridge，再查 code 节点 customInputs |
| 点击引用提示“无权操作该文件” | 最终回答有 `[id](CITE)`，但主工作流顶层 `flowResponses` 没有 `datasetSearchNode.quoteList` 登记 collection 引用权限 | 在最终作答前增加顶层 `citationAuthSearch`，或让最终 AI 直接使用顶层 datasetSearch/concat 输出 |
| LLM 输出无法被下游解析 | chatNode 输出被包装在 `{text:...}` 中 | 下游代码节点使用 `extractFastGPTPlainText` |
| ifElse 始终走 ELSE | `variable` 引用的值为 undefined | 检查上游节点是否正确输出该字段 |
| 工具调用不生效 | `pluginId` 仍是占位符 | 替换为真实 appId |
| 主检索 limit 配错导致检索空/超慢 | 把 `datasetSearchNode.limit` 误当 token 预算或误设为 4000+ | 主检索按 chunk 上限校准，常用 quick=20 / standard=50 / deep=100；用 flowResponses 观察 quoteList 和耗时 |
| limit 设为 4000+ 后后端过载或工作流工具返回空 | 把 limit 当 token budget；多任务 loop/parallel 叠加 datasetSearch | 立即降到 20~100，并检查 `candidateCount/generalQuotes` 是否恢复 |
| 变量引用 `{{$xxx.yyy$}}` 不替换 | 模板变量格式错误或 nodeId 不匹配 | 确认 nodeId 和 key 与上游一致 |
| 循环不执行 | `loopInputArray` 引用为空或非数组 | 检查引用链路和类型 |

## 6. 修复工作流程

### 6.1 运行态优先诊断

导入后行为异常时，优先导出 `flowResponses`，不要只看截图或本地 JSON：

```bash
python ../fastgpt-shared/scripts/export_fastgpt_flow_logs.py \
  --base-url https://<host>/api \
  --api-key '<openapi-key>' \
  --app-id '<app-id>' \
  --export-dir ./fastgpt-logs

python ../fastgpt-shared/scripts/analyze_fastgpt_flow_logs.py \
  --latest ./fastgpt-logs \
  --format text
```

### 6.2 `AI_input_is_empty` 固定排查链

1. 找到报错 AI 节点，确认其 `userChatInput` 引用的是哪个上游输出。
2. 检查该上游输出是否为空，例如 `finalUserPrompt` / `primarySearchQuery` / `userQuery`。
3. 若上游来自 code 节点，检查该 code 节点 `customInputs`：
   - `{}` = code-node 动态输入契约错误，先补 `addInputParam` + `canEdit:true`。
   - 非空但 `customOutputs` 错 = 查 code 内部逻辑、返回字段和错误输出。
4. 只有 code 节点报 `Can not find CODE_SANDBOX_URL` 或 sandbox 请求错误时，才转向自部署 sandbox/env 排查。

### 6.3 导出脚本 TLS fallback

部分自部署 FastGPT 域名会让 Python `urllib` 在 TLS 握手阶段报 `SSL: UNEXPECTED_EOF_WHILE_READING`，但同一接口用 `curl` 正常。运行态导出脚本应支持 `curl` fallback；不要把这种客户端 TLS 兼容问题误判为 FastGPT OpenAPI 不可用。

### 6.4 原生引用权限链排查

FastGPT 的引用弹窗和“全部引用/查看全文”不只看最终回答里的 `[id](CITE)`，还会通过本轮对话保存的 `datasetSearchNode.quoteList` / `citeCollectionIds` 判断该 collection 是否在本轮被引用过。

**故障特征**：
- 回答中有 `[id](CITE)`，悬浮或点击引用时报“无权操作该文件”。
- 运行态日志显示工作流工具内部 `candidateQuotes/finalQuoteQA` 非空。
- 但主工作流顶层 `flowResponses` 中没有任何 `moduleType=datasetSearchNode` 且带 `quoteList` 的节点。

**优先排查**：
1. 导出完整响应并运行 `analyze_fastgpt_flow_logs.py`。
2. 查看 `citation.nativeCitationRisk`：
   - `true` = 有 CITE 但顶层 datasetSearch 引用登记缺失或 collection 未覆盖。
   - `false` = 原生引用权限链大概率已覆盖，若仍失败再查 FastGPT 数据集/分享权限。
3. 如果检索被封装在 workflow tool/pluginModule 内，主工作流最终作答前需要主工作流内的 `datasetSearchNode` 做引用授权检索：
   - 优先按最终证据的 `collectionId` 拆成多条短任务，不要用一个长 query 同时授权多个 collection。
   - 每条任务只过滤一个 collection：`collectionFilterMatch={ collectionIds:[collectionId] }`。
   - `userChatInput` 使用该 collection 的最终证据短片段 + 来源名 + 用户问题。
   - 授权检索默认使用 `searchMode=embedding`、`similarity=0`、`usingReRank=false`；它只负责登记 `quoteList/citeCollectionIds`，不改变最终回答用的精选 `quoteQA`。`limit` 先按 20~100 小步校准，只有引用覆盖不足且耗时可控时才提高。
   - 如果授权检索耗时超过 10s，优先检查 query 长度、是否误用 `mixedRecall`、是否把多个 collection 合到一次搜索。

### 6.5 内部节点输出控制

复杂工作流中，除最终用户可见节点外，内部 LLM 节点默认应关闭 `aiChatIsResponseText`：
- 允许输出：最终回答、明确直答分支。
- 默认关闭：analyzer、router、verifier、planner、reranker、工作流工具内部判断节点。
- 最终 prompt 不应暴露“工具调用、补查、评分、重排、内部策略”等执行机制；这些应保留在 code/tool 输出和 flowResponses 诊断中。

**注意**：这不代表之前没有走知识库；它通常代表“知识库检索发生在工具工作流内部，但原生引用权限没有在主工作流顶层登记”。

```
1. 加载 JSON 文件
2. 执行 §1 结构完整性检查 → 列出所有 FAIL 项
3. 按优先级排序：
   P0: 导入会失败的问题（无效 nodeType、edge 断裂、JSON 语法）
   P1: 运行会报错的问题（代码节点 bug、引用断裂）
   P2: 逻辑不符预期的问题（条件不触发、数据类型不匹配）
   P3: 优化项（layout、prompt 改进、参数调优）
4. 逐项修复，每次修复后重新检查受影响的节点/edge
5. 完成后重新执行完整检查确认零 FAIL
6. 输出修复报告：改了什么、为什么改、如何验证
```

## 7. 优化建议清单

修复完 bug 后，可进一步优化：

- **prompt 精炼**：systemPrompt 是否有冗余指令、是否缺少关键约束
- **检索参数调优**：similarity / limit / searchMode 是否匹配业务场景
- **代码去重**：多个 code 节点是否重复定义相同的 helper 函数（如 `extractFastGPTPlainText`）
- **edge 简化**：是否有冗余的中间透传节点可以合并
- **错误处理**：关键节点是否有 `catchError: true` 或 error output 处理
- **layout 可读性**：节点 position 是否形成清晰的从左到右流水线

## 8. 验证方法

修复后必须执行以下验证之一：

1. **静态验证**：用 `jq` 或脚本检查 JSON 结构合规性
2. **导入验证**：导入 FastGPT 平台，检查节点渲染和连线
3. **运行验证**：发送测试问题，检查每个节点的实际输出
4. **对比验证**：修复前后 diff，确认只改了预期位置

```bash
# 快速结构检查示例
cat workflow.json | jq '.nodes | length'
cat workflow.json | jq '.nodes[] | {nodeId, flowNodeType}'
cat workflow.json | jq '.edges[] | {source, target}'
cat workflow.json | jq '[.nodes[].nodeId] | unique | length == (.nodes | length)'
```

## 9. 项目特定上下文（示例模板）

使用此 skill 时，建议为每个项目维护一个项目特定上下文章节。格式参考：

### 示例：某 RAG 问答工作流架构

```
workflowStart
  → normalizeInput (code: 变量归一化)
    → analyzeQuery (chatNode: LLM 分析器)
      → routeDecision (ifElse: 直答/检索分支)
        ├─ directAnswer (chatNode: 直答)
        └─ 检索管线
            → entityLookup (pluginModule: 实体定位工具)
            → metadataEnrich (pluginModule: 元数据补全工具)
            → retrieval (pluginModule: 检索编排工具)
            → evidenceBundle (pluginModule: 证据整理工具)
            → finalAnswer (chatNode: 最终回答)
```

### 工作流工具清单模板

| 工具 | appId | 角色 |
|---|---|---|
| 实体定位工具 | `YOUR_APP_ID` | 实体名 → collectionId |
| 元数据补全工具 | `YOUR_APP_ID` | collectionId → 元信息 |
| 检索编排工具 | `YOUR_APP_ID` | 多模式检索编排 |
| 证据整理工具 | `YOUR_APP_ID` | 证据评分与降级 |

> 在你的项目中，用实际的 appId 替换 `YOUR_APP_ID`。


## Guardrails

1. **不要凭记忆猜 FastGPT 字段名**。必须对照 §0 的官方合约。
2. **不要手动格式化大型 JSON**。用 `jq` 或 `JSON.stringify(null, 2)` 处理。
3. **不要把 limit 当 token 预算**。observed in tested FastGPT instances, main search limit 应按 chunk 数/检索上限治理：quick≈20、standard≈50、deep≈100；4000+ 属于高风险配置。
4. **修复代码节点时注意双重转义**。最安全的方法是先写好 JS 代码 → 再用 `JSON.stringify()` 生成 JSON 值。
5. **修改 JSON 后必须重新校验**。至少执行 `jq .` 确认格式正确。

## 10. 2026-04-24 运行态新增规则：FAQ、固定引用授权、tags 与输出泄露

### 10.1 `isResponseAnswerText` 是当前官方输出开关

- 当前 FastGPT `chatNode` 控制是否把 AI 输出流给用户的 key 是 `isResponseAnswerText`。
- 旧字段 `aiChatIsResponseText` 可能只在旧样例/旧导出中出现；新建或修复工作流时不得再依赖旧 key。
- 默认规则：除最终用户可见节点（最终回答、明确直答）外，analyzer / verifier / router / reranker / 工具内部 AI 节点都必须 `isResponseAnswerText=false`。
- 若用户看到 analyzer JSON、verifier scores、ranking/fallback 文本，优先判为“内部 AI 输出泄露”，先查该 key。

### 10.2 ifElse 后接顶层 `parallelRun` 的停链风险

运行态已见过：`ifElseNode -> parallelRun -> finalAnswer` 在部分自部署实例上会停在 parallelRun/loopStart 附近，最终 AI 节点不执行。

诊断特征：
- `flowResponses.nodeChain` 最后停在“是否登记原生引用权限”或 `citationAuth*`。
- 上游 `finalQuoteQA` 已存在，但没有 `finalAnswer` 节点。

修复优先级：
1. 对必须稳定进入最终回答的链路，优先使用固定槽位：`ifElse -> datasetSearch -> nextIfElse -> ... -> finalAnswer`。
2. 不要在主工作流最终回答前使用顶层 `parallelRun` 做引用授权。
3. 大规模并行仍可放在工作流工具内部；主工作流末端要可预测、可串行落地。

### 10.3 原生引用授权建议

- 工作流工具内部检索可以提供真实证据，但 FastGPT 原生 CITE 鉴权最好由主工作流顶层 `datasetSearchNode.quoteList` 登记。
- 引用授权检索只负责登记引用权限，不参与答案排序。
- 稳定模式：按最终证据 collection 拆成 3-4 个固定槽位，每槽单 collection、短 query、`searchMode=embedding`、`similarity=0`、`usingReRank=false`；`limit` 与主检索分开校准，优先从 20~100 起测，只有引用覆盖不足且耗时可接受时才小幅提高。
- 如果授权检索耗时高，先降低槽位数和 query 长度；不要把所有 collection 塞进一个长 mixedRecall 检索。

### 10.4 metadata / tags / stale import 诊断

- 若 metadata 工具输入 `collectionIds` 非空但输出 `metadataRawResponse.items=[]`，先查：
  1. 工具是否重新导入到了当前 appId（旧 appId 可能仍指向旧 JSON）。
  2. `pluginInput.inputs` 是否镜像为 outputs。
  3. 输入类型是否过窄；collectionIds 最好用 `arrayAny` 并在 code 中递归提取字符串、quote.collectionId、nested collectionIds。
- FastGPT Plus 源码支持 `collectionFilterMatch.tags.$and/$or`；若实例未启用 Plus 或 tags 未建好，tag filter 可能退化。此时必须保留无 tag fallback 检索，并在 ranking 里用 metadata/sourceName 做软排序。
- tagsid 在业务上可能就是“国标”“现行”“JG 建筑工程”等标签文本；不要假设一定是 ObjectId。

### 10.5 FAQ 并行分支诊断

复杂 RAG 可加 FAQ 工作流工具，但不能覆盖用户明确指定标准：
- `faqMode=direct` 只允许在无明确标准号/标准名且 FAQ 极高匹配时支配回答。
- `faqMode=supplemental` 只能作为补充上下文。
- `faqMode=discard` 不应进入最终证据。
- 运行态检查：主工作流应同时出现 FAQ 工具和标准检索工具；如果标准号问题被 FAQ 直接覆盖，判为 P1 策略错误。

## 11. v4.14.11-v4.14.16 版本适配要点

### 11.1 变量更新节点增强（v4.14.11）

- 变量更新节点新增了更多数字操作和数组操作，可用于循环计数器、数组拼接等场景。
- 在 `loop` 内使用变量更新做数组 push/concat 时，注意 `valueType` 必须与实际操作匹配。

### 11.2 DeepSeek 工具调用+思考模式兼容（v4.14.14）

- v4.14.14 兼容了 DeepSeek 模型的工具调用（tool_call）与思考模式（reasoning）共存，避免之前可能出现的 API 400 错误。
- 如果使用 DeepSeek-R1 / DeepSeek-V3 等模型做 `tools` / `agent` 节点的工具调用，v4.14.14+ 是必要版本。
- 注意：DeepSeek 思考模式下的 `reasoningText` 输出仍通过 `NodeOutputKeyEnum.reasoningText` 获取。

### 11.3 旧版系统工具兼容修复（v4.14.15）

- v4.14.15 修复了选中系统组件被错误识别为系统工具的问题。
- 如果工作流中使用了系统内置工具（如联网搜索、知识库搜索等系统组件），升级到 v4.14.15+ 可解决之前可能出现的组件加载异常。

### 11.4 安全修复摘要

| 版本 | 修复内容 | 优先级 |
|---|---|---|
| v4.14.10.4 | NoSQL 注入防护 | P0 |
| v4.14.13 | opensandbox 鉴权绕过 RCE（#6781） | P0 |
| v4.14.13 | 分享链接引用鉴权 | P1 |
| v4.14.11 | 部分接口权限校验缺失 | P1 |

### 11.5 其他运维要点

- v4.14.11 要求同步更新：`code-sandbox` 镜像 -> `v4.14.11`，`fastgpt-plugin` 镜像 -> `v0.6.0`，Aiproxy -> `v0.5.3`。
- v4.14.12 新增 Agent PI 模式（beta），目前不建议在生产工作流中使用。
- v4.14.16 修复了 embedding 适配 base64 字符串返回值，对使用部分 embedding API（返回 base64 而非 float 数组）的场景有帮助。
