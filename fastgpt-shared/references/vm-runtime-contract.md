# FastGPT Skill / AgentV2 VM 运行时合同

本文件区分“维护者本地调试”与“AgentV2 线上 VM 执行”。本机 macOS 上命令成功，只能证明维护工具可用，不能证明 AgentV2 Skill、sandbox 或工作流在 Linux VM 中可用。

## Operator lane

维护者本地运行的管理、导出、诊断和 JSON 检查脚本属于 Operator lane。它们可以按本机实际情况使用 Python、Node.js、`curl` 或其他 CLI，但必须把依赖和适用范围标为“本地维护工具”，不能把这些命令写成 AgentV2 请求路径的隐式前提。

## AgentV2 runtime lane

AgentV2 runtime lane 运行在 FastGPT 提供的 VM/Sandbox 中。所有请求期依赖必须满足下表，并在目标 VM 实测：

| 依赖类型 | 必须记录 | 允许的来源 | 请求期间的规则 |
|---|---|---|---|
| OS/CPU/ABI | target OS/architecture，例如 Linux x64/glibc 或 arm64/musl | 目标 VM 固定镜像 | 不按本机 macOS 结果推断 |
| Node/Python | 版本和实际执行面 | VM 预装或 Skill 明确打包 | 不临时 `npm install`/`pip install` |
| 原生库 | binary、ABI、平台包和 hash | 与目标 VM 匹配的发布制品 | 缺失时 fail closed，不切换到未验证 fallback |
| 外部网络/凭据 | DNS、HTTPS、CA、Secret 注入方式 | FastGPT 宿主/工作流节点 | 不写入 Skill、JSON、日志或 URL |
| FastGPT code sandbox | 可用 API 和输入输出 schema | 目标 FastGPT 版本 | 默认无 `require`/`import`/`fetch`/`exec`，以目标实例实测为准 |

## AgentV2 启动脚本（版本敏感）

### beta5 已验证的配置和生命周期

对 FastGPT `4.15.0-beta5`，Agent 节点的 VM 配置字段是字符串型
`sandboxEntrypoint`。它属于 Agent 应用版本配置，不属于 Skill ZIP；应从目标版本
detail 读回后再修改，不能按旧版导出或模型记忆补字段。

官方 beta5 runtime 的执行顺序是：

```text
VM 平台初始化
  -> 注入 Skill 文件
  -> 执行 sandboxEntrypoint（应用启动脚本）
  -> 执行 Skill entrypoint
  -> Agent 请求路径
```

官方 beta5 文档还规定了以下边界：启动脚本以 `/bin/bash` 执行，长度有上限，执行有
单独超时，并按脚本内容 SHA-256 hash 去重；脚本未变化时可能不会每次请求重跑。因此任何
依赖初始化都必须区分 cold/warm，并把脚本版本或 hash 纳入运行证据。启动脚本失败
或超时不能被当作 Skill 已成功初始化；应读取脱敏日志和后续能力探针确认。

目标版本的官方入口：

- [AgentV2 启动脚本（FastGPT v4.15.0-beta5）](https://github.com/labring/FastGPT/blob/v4.15.0-beta5/document/content/guide/build/agentv2/startup.mdx)
- [beta5 AgentV2 节点模板](https://github.com/labring/FastGPT/blob/v4.15.0-beta5/packages/global/core/workflow/template/system/agent/index.ts)
- [beta5 启动脚本 runtime](https://github.com/labring/FastGPT/blob/v4.15.0-beta5/packages/service/core/ai/skill/runtime/entrypoint.ts)
- [beta5 VM 初始化顺序](https://github.com/labring/FastGPT/blob/v4.15.0-beta5/packages/service/core/workflow/dispatch/ai/agent/sub/sandbox/runtime.ts)

### 不要把 `export` 当成跨命令环境合同

启动脚本由一次独立的 sandbox 执行调用运行；后续 Skill entrypoint、内置 Sandbox
命令或工作流节点是否复用该 shell 的进程环境，必须在目标版本实测。即使脚本内的
`export` 成功，也不能默认它会进入后续命令。一次真实 beta5 探针已确认字段可以
读回并接受发布，但没有观察到后续 Agent Shell 返回的标记；这只能记为“后续可见性
未证实”，不能写成“启动脚本一定未执行”。

因此：

- `export` 只适合脚本自身的子进程和同一执行上下文；不要用它作为 Skill API Key
  注入的唯一机制。
- 若确实需要把运行时配置交给 Skill，必须先证明 Secret-aware 来源已将变量注入
  VM 进程上下文。优先由 Skill 自带的 `entrypoint.sh` 使用自身解析出的包根目录写入
  权限受限的配置文件；只有在已验证路径和生命周期的部署适配层存在时，才由
  `sandboxEntrypoint` 交接文件。Skill 自身必须显式加载该文件。
- beta5 默认 VM 环境只包含 FastGPT runtime 的内部变量，不等于自动注入通用的
  `LLM_API_KEY`、`VISION_API_KEY` 或业务 `.env`。没有已验证的 Secret 来源时，
  启动脚本不能凭空生成凭据，也不能把本机 `.env` 当作线上输入。
- 配置文件中不得硬编码 Key、Token 或内部 URL；失败时应 fail closed，不切换到
  未授权的联网或模型降级路径。

### 推荐的无密钥初始化模板

启动脚本首先只做快速、确定性的预检，例如：

```bash
set -eu
umask 077

# 仅用于验证脚本生命周期；生产环境不要把凭据写进脚本。
printf '%s\n' 'startup-probe' > /workspace/.agent-startup-probe
```

若目标部署已经有经过验证的 Secret 注入，应将下面的写文件动作作为“部署适配层”
实现，而不是把值写入 Skill、JSON、fixture 或文档：

```bash
set -eu
umask 077
: "${LLM_BASE_URL:?secret-aware environment is not configured}"
: "${LLM_API_KEY:?secret-aware environment is not configured}"

for skill_root in /workspace/projects/*; do
  [ -d "$skill_root" ] || continue
  {
    printf 'LLM_BASE_URL=%s\n' "$LLM_BASE_URL"
    printf 'LLM_API_KEY=%s\n' "$LLM_API_KEY"
  } > "$skill_root/.env"
  chmod 600 "$skill_root/.env"
done
```

上面的生产模板只有在两项事实都已验证时才可采用：一是目标 VM 确实提供这两个
变量，二是 Skill 的 loader 确实从对应包根目录加载 `.env`。否则应改为 FastGPT
Secret-backed Workflow-Tool 或其他已验证的凭据边界。启动脚本不应执行 LLM、视觉
模型、联网搜索、`apt`、`pip` 或 `npm` 安装；这些动作会把冷启动、失败点和敏感面
引入请求路径。

### 配置发布和验收方法

1. 保存测试版 Agent detail；只在允许的测试版修改 `sandboxEntrypoint`，其他节点、
   工具引用、Skill、知识库绑定和 chatConfig 保持不变。
2. 用一个无敏感 marker 做 cold-start 探针，再做 warm-start 探针；同时读回发布版本
   确认 `sandboxEntrypoint` 内容确实保存。marker 未出现在 Agent 返回中时，只能记为
   “运行结果未观测到”，不能从响应正文反推脚本是否执行。
3. 单独验证 Skill entrypoint、配置文件可见性和 LLM/视觉调用；不要把启动脚本执行
   成功等同于 Skill 已拿到凭据。
4. 记录脚本 hash、执行耗时、超时/失败、冷暖启动、Skill 初始化和后续请求耗时；
   成功缓存只接收证据闭环完整的成功结果，启动失败、超时和降级不入缓存。
5. 测试完成后用原 detail 恢复测试版并再次读回；正式版只做 updateTime/版本摘要比对，
   不接受任何写入。

## Platform-specific rules

- `sips` 是 macOS-only 的本地图片辅助路径；它不能作为 AgentV2 VM 的生产依赖。Linux 图片压缩必须使用随发布制品提供、与目标架构匹配的 `sharp` 或目标 VM 明确提供的等价能力。
- `curl`、`wget`、`brew`、APT、Python 包和系统 `libvips` 不能被默认视为 AgentV2 Skill 依赖。若它们只用于导出/诊断，应留在 Operator lane；若确需线上使用，必须进入依赖清单、发布制品和目标 VM smoke。
- Skill/工作流不得在每次请求中安装、下载、编译或刷新依赖；这是 **no request-time install** 合同。镜像初始化、Skill 打包和请求执行是三个不同阶段。
- AgentV2 工作流中的 `code` 节点遵守 FastGPT sandbox 合同；不要把本地 Node/Python 脚本、绝对路径、macOS 工具或宿主文件读取能力当作 sandbox 能力。
- 同一 Skill 可以有本地兼容实现，但必须明确按 `platform` 分支；未验证的平台不得静默复用另一平台的 native binary 或 fallback。

## VM-first checklist

编写或修改 AgentV2 Skill、工具工作流或视觉链路时，先记录：

1. 执行面：Operator、AgentV2 VM、FastGPT code sandbox 或工作流节点。
2. target OS/architecture、运行时版本、依赖来源和是否打包。
3. cold/warm 的入口、依赖加载、文本请求和图片请求 smoke。
4. 网络、Secret、文件系统和子进程权限；不可用时的显式失败行为。
5. 发布包清单、排除项和与目标 VM 相同的干净解包验证。

如果只能在 macOS 验证，应把 Linux/VM 验收标为 deferred，而不是写成“已兼容”；发布记录必须明确 `target VM` 尚未验证。
