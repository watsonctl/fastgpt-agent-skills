# FastGPT 常用功能节点库 (Assets)

本目录包含 FastGPT 工作流编排中常用的“功能节点”示例与 Schema 定义，旨在为 AI Agent 在生成或修复工作流 JSON 时提供标准的语法参考。

## 核心资产定义

为了确保工作流生成的质量，资产按以下层级进行分类：

### 1. Golden Examples (`golden-examples/`)
- **定义**：金标准示例。
- **状态**：通过了端到端（E2E）业务验证，且在真实生产环境中稳定运行。
- **用途**：作为最高优先级的参考，用于复制成熟的业务逻辑架构（如：方案审查管道、RAG 融合检索）。

### 2. Canonical Examples (`canonical-examples/`)
- **定义**：权威/标准示例。
- **状态**：符合 FastGPT 当前版本的官方合约，且通过了管理后台的“导入验证”。
- **用途**：作为结构参考，用于学习特定版本下的 JSON 语法、布局算法和节点连接规则。

### 3. Probe Examples (`probe-examples/`)
- **定义**：探索性示例。
- **状态**：实验性代码，可能未经过完整业务验证，或仅为测试特定边缘功能（如：循环节点、自定义插件）。
- **用途**：仅作为灵感参考，禁止直接用于生产环境的架构复制。

### 4. Node Library (`functional_nodes_library.json`)
- **定义**：原子节点词典。
- **状态**：涵盖了 Chat、Search、Extract 等核心功能节点的完整 Schema。
- **用途**：在需要创建或修复单个节点时，查询精确的 `inputs` 和 `outputs` 字段定义。

## 使用规则
- **引用优先级**：`Golden` > `Canonical` > `Node Library` > `Probe`。
- **生成原则**：AI 应优先从 `Golden` 中提取逻辑模式，从 `Node Library` 中提取字段细节。

## 注意事项
- 本库中的 `nodeId` 为示例值，在实际生成工作流时应使用随机生成的 16 位字母数字字符串或语义化 ID（如 `parse_input`）。
- `avatar` 路径必须保持原样，否则前端界面可能无法正确显示节点图标。
