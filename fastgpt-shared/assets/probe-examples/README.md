# FastGPT 工作流 JSON Schema 探针包

> 适用目的：用于在当前 FastGPT 实例中验证工作流 JSON 的 root schema、node schema、edge schema、variable schema、工具工作流调用方式和常用节点导入/运行行为。  
> 使用边界：These files are schema probes and minimal examples, not production business workflows. A production workflow bundle should be generated only after the relevant probes pass in the target FastGPT instance.

更新时间：2026-04-28

---

## 1. 当前结论

本探针包已形成两类基准：

1. **普通工作流基准**
   - `workflowStart`
   - `code`
   - `httpRequest468`
   - `batch / parallel`
   - `tools`
   - `variableUpdate`
   - `ifElseNode`
   - `chatNode`
   - `answerNode`
   - `datasetSearchNode`
   - `pluginModule` 形式的文本加工节点

2. **工具工作流调用基准**
   - 工具工作流本体不是普通 `workflowStart → answerNode` 结构，而是：
     - `pluginConfig`
     - `pluginInput`
     - 业务节点，例如 `code`
     - `pluginOutput`
   - 主工作流调用工具工作流时，不使用旧式 `runApp`。
   - 当前实例真实调用方式是：
     - `flowNodeType: "pluginModule"`
     - `avatar: "/imgs/workflow/tool.svg"`
     - `pluginId: "<真实工具工作流 ID>"`
     - inputs 对齐被调用工具的 `pluginInput`
     - outputs 对齐被调用工具的 `pluginOutput`

因此，旧文件：

```text
13_subworkflow_tool_example.json
```

应废弃，不再作为正式 schema 依据。

新的工具工作流调用探针为：

```text
13_workflow_tool_call_example.json
```

---

## 2. 文件清单

### 00. 空工作流基线

#### `00_empty_workflow_baseline.json`

用途：

- 当前实例的 root schema 基准。
- 校准 `nodes`、`edges`、`chatConfig` 的最小结构。
- 作为后续所有探针的对照样本。

关键点：

```text
root = {
  nodes: [],
  edges: [],
  chatConfig: {}
}
```

当前导出节点版本主要为：

```text
version: "481"
```

---

### 01. Code Run 示例

#### `01_code_run_example.json`

用途：

- 验证代码运行节点导入与执行。
- 验证 JS Code Run 节点的输入、输出、动态字段声明。
- 适合作为后续 JSON 清洗、结构化转换、字段补齐、结果校验的基础模板。

关键节点：

```text
flowNodeType: "code"
version: "482"
```

适合production workflow中的位置：

```text
输入归一化
文档清单整理
证据矩阵合并
问题去重
JSON Schema 校验
最终输出组装
```

---

### 02. HTTP Request 示例

#### `02_http_request_example.json`

用途：

- 验证 HTTP 请求节点。
- 验证 URL、Method、Header、Params、Body 和原始响应输出。
- 可作为后续调用业务系统、解析服务、规则服务、规范服务的基础模板。

关键节点：

```text
flowNodeType: "httpRequest468"
```

适合production workflow中的位置：

```text
调用文件解析服务
调用规则服务
calling reference service
回写审查结果
调用外部审查辅助接口
```

---

### 03. Batch Processing 探针

#### `03_batch_processing_probe.json`

用途：

- 验证批量处理 / 循环处理结构。
- 适合测试数组输入、逐项处理、结果聚合。

适合production workflow中的位置：

```text
逐文件解析
逐章节检查
逐条规则匹配
逐个问题证据补强
```

注意：

- 如果导入成功但运行异常，应优先导出当前实例手工创建的最小批处理工作流，再反推真实 schema。
- 不建议在production workflow main path初版中大量依赖复杂循环；优先使用 Code Run 做稳定聚合。

---

### 04. Parallel Run 探针

#### `04_parallel_run_probe.json`

用途：

- 验证并行执行节点结构。
- 适合测试数组任务并发处理、结果收集和失败重试行为。

适合production workflow中的位置：

```text
多专项模块并行审查
多文件并行解析
多规则包并行命中
多审查维度并行生成候选问题
```

注意：

- 并行节点适合做“并发执行”，但final business output仍应经过后置汇总、证据检查和最终协议收口。
- 不应让并行分支直接输出最终final user-facing report。

---

### 05. Tool Calling / AgentV2 探针

#### `05_tool_calling_probe.json`

用途：

- 验证工具调用节点。
- 验证 `flowNodeType: "tools"` 的节点结构。
- 观察 Agent / Tool Calling 在当前实例里的模型配置、工具选择、输出字段和调试行为。

关键节点：

```text
flowNodeType: "tools"
```

适合production workflow中的位置：

```text
候选问题发现
辅助工具选择
探索性补充分析
非production business workflow辅助推理
```

限制：

- 不建议作为final business output主链。
- 对production business workflow系统，Tool Calling / AgentV2 应作为辅助层，而不是最终判定层。

---

### 06. Variable Update 示例

#### `06_variable_update_example.json`

用途：

- 验证变量更新节点。
- 测试将 Code Run 输出写入全局变量。
- 适合验证 `{{$VARIABLE_NODE_ID.xxx$}}` 的变量引用方式。

关键节点：

```text
flowNodeType: "variableUpdate"
```

适合production workflow中的位置：

```text
维护 review_context
维护 evidence_matrix
维护 blocked_items
维护 candidate_issues
维护 formal_issues
维护 final_result
```

注意：

- 全局变量适合存储小型状态，不适合塞入过大的完整文档内容。
- 大对象建议通过节点输出链路传递，必要时用 Code Run 做压缩/摘要。

---

### 07. Condition Branch 示例

#### `07_condition_branch_example.json`

用途：

- 验证条件判断节点。
- 验证 IF / ELSE 分支连线。
- 适合测试布尔值、字符串、节点输出字段的条件判断。

关键节点：

```text
flowNodeType: "ifElseNode"
```

适合production workflow中的位置：

```text
是否缺少主文件
是否存在 parserLimited
是否存在 blocked_items
是否允许输出final business output
是否启用某个专项模块
是否进入降级输出
```

注意：

- 条件分支中的布尔值要注意当前实例是按 boolean 还是 string 比较。
- 如果 `true` / `"true"` 行为不同，production workflow应统一用 Code Run 先归一化。

---

### 08. AI Chat 基础示例

#### `08_ai_chat_basic_example.json`

用途：

- 验证普通 AI Chat 节点。
- 测试模型、温度、系统提示词、用户输入、文件输入字段。
- 观察 `answerText` 和 `history` 输出。

关键节点：

```text
flowNodeType: "chatNode"
```

适合production workflow中的位置：

```text
审查意图归一化
材料摘要
受控审查判断
候选问题表达
报告语言润色
```

注意：

- AI Chat 节点中的模型名需要替换为当前实例可用模型。
- production workflow中应限制模型自由发挥，尽量提供结构化输入和明确输出协议。

---

### 09. AI Chat JSON 输出示例

#### `09_ai_chat_json_output_example.json`

用途：

- 验证 AI Chat 节点的 JSON 输出能力。
- 测试 JSON Schema / JSON 格式输出约束。
- 适合检查当前实例是否能稳定输出结构化 JSON。

关键节点：

```text
flowNodeType: "chatNode"
```

适合production workflow中的位置：

```text
候选问题结构化
final decision/output structuring
风险等级结构化
最终报告包结构化
```

注意：

- 即使模型支持 JSON 输出，正式链路也应在后面接 Code Run 做 JSON parse / schema 校验。
- 不应直接信任 LLM 输出的 JSON 一定合法。

---

### 10. Answer Final Output 示例

#### `10_answer_final_output_example.json`

用途：

- 验证最终指定回复节点。
- 验证将 Code Run 生成的 JSON 字符串作为最终输出。
- 适合作为正式工作流最终输出节点模板。

关键节点：

```text
flowNodeType: "answerNode"
```

适合production workflow中的位置：

```text
正式 Markdown 报告输出
正式 JSON 结果输出
降级说明输出
阻塞结果输出
```

注意：

- 若业务系统需要纯 JSON，建议最终 `answerNode` 只输出 JSON 字符串，不夹杂 Markdown。
- 若面向用户展示，可输出 Markdown；但机器接口最好单独保留 JSON 协议。

---

### 11. Knowledge Search 示例

#### `11_knowledge_search_example.json`

用途：

- 验证知识库检索节点。
- 测试 `datasetSearchNode` 的导入和运行行为。
- 适合连接reference files库、企业标准库、审查规则库、案例库。

关键节点：

```text
flowNodeType: "datasetSearchNode"
```

导入后必须处理：

```text
手动选择当前实例内的知识库
```

适合production workflow中的位置：

```text
reference service retrieval
条款召回
business rule retrieval
案例参考召回
```

限制：

- 知识库检索结果不能直接等同于正式依据适用性结论。
- production workflow应在检索后增加规则适用性判断和证据约束。

---

### 12. Text Template Concat 示例

#### `12_text_template_concat_example.json`

用途：

- 验证文本加工 / 模板拼接节点。
- 测试 `community-textEditor` 工具插件形式的文本处理。
- 适合将多个变量拼成统一 prompt 或报告片段。

关键节点：

```text
flowNodeType: "pluginModule"
pluginId: "community-textEditor"
```

适合production workflow中的位置：

```text
构造domain-specific tool Prompt
构造报告片段
拼接审查依据摘要
拼接证据矩阵说明
```

注意：

- 该节点属于 `pluginModule`，但它是社区文本工具，不是业务工具工作流。
- 不要和 `13_workflow_tool_call_example.json` 中的业务工具工作流调用混淆。

---

### 13. Workflow Tool Call 示例

#### `13_workflow_tool_call_example.json`

用途：

- 验证主工作流通过 `pluginModule` 调用工具工作流。
- 替代已废弃的 `13_subworkflow_tool_example.json`。
- 用于确认当前实例中工具工作流调用的真实 schema。

关键节点：

```text
flowNodeType: "pluginModule"
avatar: "/imgs/workflow/tool.svg"
pluginId: "YOUR_WORKFLOW_TOOL_APP_ID"
```

当前默认调用的工具：

```text
sample support-data preparation workflow tool
```

当前默认 `pluginId`：

```text
YOUR_WORKFLOW_TOOL_APP_ID
```

该 `pluginId` 来自当前实例的production business workflow主流程中的“调用sample support-data preparation”节点。

调用关系：

```text
workflowStart
  ↓
buildReviewContext
  ↓
callSupportWft(pluginModule + pluginId)
  ↓
answerNode
```

输入映射：

```text
callSupportWft.reviewContext
  ← buildReviewContext.reviewContext
```

输出字段：

```text
supportReviewResult
supportResult
supportPacket
artifactIndex
supportLayerContext
```

注意：

- 换 FastGPT 实例后，必须替换 `pluginId`。
- 被调用的工具工作流必须已经存在。
- 主流程的 `pluginModule.outputs` 应与被调用工具工作流的 `pluginOutput.inputs` 对齐。
- 工具工作流本体应使用 `pluginConfig → pluginInput → 业务节点 → pluginOutput` 结构。
- 不要再使用 `runApp` 作为子工作流调用方式。

---

### 14. File Input Variable 示例

#### `14_file_input_variable_example.json`

用途：

- 验证用户上传文件变量。
- 测试 `workflowStartNodeId.userFiles` / `workflowStart.userFiles` 的文件数组传递。
- 适合确认文件 URL 数组能否进入 Code Run。

关键字段：

```text
userFiles
valueType: "arrayString"
```

适合production workflow中的位置：

```text
primary uploaded file传递
supporting files传递
reference files forwarding
上下文文件传递
```

注意：

- 工具工作流不会自动继承主工作流上传文件。
- 如果主流程调用工具工作流，需要显式把文件 URL 数组作为参数传给工具工作流。

---

### 15. HTTP Auth JSON Body 示例

#### `15_http_auth_json_body_example.json`

用途：

- 验证带 Authorization Header 的 HTTP JSON 请求。
- 测试 JSON Body 中引用工作流输入变量。
- 适合模拟调用受鉴权保护的业务接口。

关键节点：

```text
flowNodeType: "httpRequest468"
```

适合production workflow中的位置：

```text
调用内部文件解析服务
calling business rule service
调用task status callback API
调用报告归档接口
调用外部业务系统
```

注意：

- 示例里的 token 是占位值。
- 正式环境不应在 JSON 中硬编码真实密钥。
- 应优先使用 FastGPT 环境变量、密钥配置或后端代理处理鉴权。

---

## 3. 已废弃文件

### `13_subworkflow_tool_example.json`

废弃原因：

该文件曾尝试使用：

```text
flowNodeType: "runApp"
```

但当前实例导入后会出现空白节点，并触发：

```text
工作流校验失败，请检查是否缺失、缺值，连线是否正常
```

根因：

```text
当前 FastGPT 版本没有将 runApp 识别为合法工具工作流调用节点
```

替代文件：

```text
13_workflow_tool_call_example.json
```

正确调用方式：

```text
flowNodeType: "pluginModule"
pluginId: "<真实工具工作流 ID>"
```

---

## 4. 推荐导入顺序

建议按以下顺序导入和验证：

```text
00_empty_workflow_baseline.json

01_code_run_example.json
02_http_request_example.json
03_batch_processing_probe.json
04_parallel_run_probe.json
05_tool_calling_probe.json

06_variable_update_example.json
07_condition_branch_example.json
08_ai_chat_basic_example.json
09_ai_chat_json_output_example.json
10_answer_final_output_example.json
11_knowledge_search_example.json
12_text_template_concat_example.json
13_workflow_tool_call_example.json
14_file_input_variable_example.json
15_http_auth_json_body_example.json
```

如果只验证 production workflow main path 所需能力，优先顺序为：

```text
00_empty_workflow_baseline.json
01_code_run_example.json
02_http_request_example.json
06_variable_update_example.json
07_condition_branch_example.json
08_ai_chat_basic_example.json
09_ai_chat_json_output_example.json
10_answer_final_output_example.json
13_workflow_tool_call_example.json
14_file_input_variable_example.json
15_http_auth_json_body_example.json
```

---

## 5. 正式工作流生成前的验收项

在生成production workflow bundle JSON 前，应至少确认：

```text
1. 00 空工作流可导入
2. 01 Code Run 可导入并运行
3. 02 HTTP Request 可导入并运行
4. 06 变量更新可导入并能写入/读取变量
5. 07 条件分支 IF/ELSE 连线正常
6. 08 AI Chat 能调用当前实例模型
7. 09 AI Chat JSON 输出可用，且后续能被 Code Run 校验
8. 10 Answer 能输出纯 JSON / Markdown
9. 11 知识库节点可在当前实例手动绑定知识库
10. 12 文本加工节点可正常拼接变量
11. 13 工具工作流调用可正常返回 pluginOutput 字段
12. 14 用户文件变量能进入 Code Run
13. 15 HTTP 鉴权 JSON Body 能调用目标接口
```

其中 `13_workflow_tool_call_example.json` 是拆分“主工作流 + 专项工具工作流”的关键验收项。

---

## 6. 对production workflow bundle的建议

建议第一版正式工作流采用：

```text
00_start_input
10_input_normalize
20_visibility_precheck
30_basis_resolve
40_parallel_or_sequential_special_review
50_evidence_check
60_issue_layering
70_final_assembly
80_json_schema_validate
90_answer_output
100_callback_or_export
```

推荐边界：

```text
Code Run：结构化、清洗、合并、校验
HTTP Request：调用外部服务
AI Chat：受控推理和表达
Knowledge Search：依据召回
Tool Calling / AgentV2：辅助候选发现，不做最终final decision maker
Workflow Tool Call：拆分domain-specific workflow tool
Answer：最终协议输出
```

不建议：

```text
1. 让 AgentV2 直接替代production workflow main path
2. 让知识库检索结果直接成为final business output
3. 让工具工作流隐式读取主流程文件
4. 用 runApp 继续模拟子工作流调用
5. 在 JSON 中硬编码生产密钥
6. 未做 JSON Schema 校验就输出final structured output
```

---

## 7. 工具工作流调用 schema 摘要

### 工具工作流本体

典型结构：

```text
pluginConfig
  ↓
pluginInput
  ↓
业务节点，例如 code / chatNode / httpRequest468
  ↓
pluginOutput
```

`pluginInput` 定义对外输入：

```text
reviewContext
documentType
enabledModules
targetFileUrls
...
```

`pluginOutput` 定义对外输出：

```text
supportReviewResult
supportPacket
artifactIndex
supportLayerContext
...
```

### 主工作流调用工具工作流

典型结构：

```text
flowNodeType: "pluginModule"
avatar: "/imgs/workflow/tool.svg"
pluginId: "<目标工具工作流 ID>"
```

输入参数：

```text
通过 value: ["上游节点ID", "输出字段"] 传入
```

输出参数：

```text
手动声明 dynamic outputs，并与目标工具工作流 pluginOutput 对齐
```

---

## 8. 当前风险与后续动作

### 需要继续反推的内容

```text
1. 当前实例真实的 Batch Processing 完整导出 schema
2. 当前实例真实的 Parallel Run 完整导出 schema
3. 当前实例真实的 Knowledge Search 绑定知识库后的导出 schema
4. 当前实例真实的 AgentV2 / AI 虚拟机导出 schema
5. 工具工作流导入后 pluginId 是否会变化
6. 跨实例迁移时 pluginId 的替换策略
```

### 建议后续新增探针

```text
16_plugin_tool_definition_example.json
17_plugin_input_output_minimal_example.json
18_dataset_search_bound_example.json
19_json_schema_validate_code_example.json
20_final_output_contract_probe.json
```

其中最重要的是：

```text
17_plugin_input_output_minimal_example.json
20_final_output_contract_probe.json
```

---

## 9. 总体结论

当前探针包已经可以支撑production business workflow工作流 JSON 的第一轮生成，但应遵守以下原则：

```text
1. 以当前实例导出的 JSON 为 System of Record
2. 不基于文档臆造未知节点
3. 工具工作流调用使用 pluginModule，不使用 runApp
4. 工具工作流本体使用 pluginInput / pluginOutput
5. 文件、变量、知识库、HTTP、AI 输出都必须显式传递和校验
6. Final business outputs should be closed by an explicit output contract rather than unconstrained agent free-form generation.
```

