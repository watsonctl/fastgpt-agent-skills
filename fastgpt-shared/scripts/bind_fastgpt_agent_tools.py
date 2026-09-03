#!/usr/bin/env python3
"""Persist explicit AgentV2 tool bindings in FastGPT's compact shape.

FastGPT's Agent detail response contains expanded tool templates, while the
Agent node's ``agent_selectedTools`` input is saved as a compact list.  This
module keeps that boundary explicit and provides a small dry-run/apply CLI.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlencode


AGENT_SELECTED_TOOLS_KEY = "agent_selectedTools"
AGENT_GENERATED_MODE = "agentGenerated"
MANUAL_MODE = "manual"
VALID_MODES = {AGENT_GENERATED_MODE, MANUAL_MODE}
VALID_REASONING_EFFORTS = {"low", "high", "max"}
DENIED_AGENT_GENERATED_RENDER_TYPES = {
    "fileSelect",
    "password",
    "selectLLMModel",
    "settingLLMModel",
    "hidden",
    "customVariable",
    "custom",
    "addInputParam",
    "selectApp",
    "selectSkill",
    "selectTool",
    "selectDataset",
    "selectDatasetParamsModal",
    "settingDatasetQuotePrompt",
}
SENSITIVE_KEY = re.compile(
    r"(?:secret|password|token|api[-_]?key|access[-_]?key|authorization|cookie|private[-_]?key)",
    re.IGNORECASE,
)


def _is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.replace("-", "_").lower()
    return normalized == "system_input_config" or bool(SENSITIVE_KEY.search(normalized))


def _sanitize_config(value: object) -> object:
    """Remove credential-like fields before a compact config is persisted."""
    if isinstance(value, dict):
        return {
            key: _sanitize_config(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [_sanitize_config(item) for item in value]
    return copy.deepcopy(value)


def _render_types(input_config: dict) -> list[str]:
    value = input_config.get("renderTypeList")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _selected_render_type(input_config: dict, render_types: list[str]) -> str | None:
    selected = input_config.get("selectedType")
    if isinstance(selected, str):
        return selected
    selected_index = input_config.get("selectedTypeIndex")
    if isinstance(selected_index, int) and 0 <= selected_index < len(render_types):
        return render_types[selected_index]
    return render_types[0] if render_types else None


def _can_input_be_agent_generated(input_config: dict, key: str) -> bool:
    if _is_sensitive_key(key):
        return False
    if input_config.get("canAgentGenerated") is False:
        return False
    if input_config.get("systemInputConfig") is not None:
        return False
    if input_config.get("forbidStream") is True:
        return False
    render_types = _render_types(input_config)
    if not render_types:
        return False
    return not any(item in DENIED_AGENT_GENERATED_RENDER_TYPES for item in render_types)


def _tool_id(tool: dict) -> object:
    # FastGPT's serializeAgentTool uses pluginId first when both fields are
    # present; the detail payload may also contain an editor-local id.
    return tool.get("pluginId") or tool.get("id")


def _compact_input(input_config: object) -> tuple[dict, str | None, object]:
    if not isinstance(input_config, dict):
        raise ValueError("Agent 工具 inputs 含有非对象项")
    key = input_config.get("key")
    if not isinstance(key, str) or not key:
        raise ValueError("Agent 工具 input 缺少有效 key")
    if _is_sensitive_key(key):
        return {}, None, None

    mode = input_config.get("mode")
    if mode is not None:
        if mode not in VALID_MODES:
            raise ValueError(f"Agent 工具 input {key} 的 mode 无效")
        return {"key": key, "mode": mode}, mode, None

    if not _can_input_be_agent_generated(input_config, key):
        return {}, None, None
    render_types = _render_types(input_config)
    selected_type = _selected_render_type(input_config, render_types)
    mode = AGENT_GENERATED_MODE if selected_type == AGENT_GENERATED_MODE else MANUAL_MODE
    value = input_config.get("value") if mode == MANUAL_MODE else None
    return {"key": key, "mode": mode}, mode, value


def compact_agent_tool(tool: object) -> dict:
    """Convert a detail/template tool into AgentV2's compact saved shape."""
    if not isinstance(tool, dict):
        raise ValueError("agent_selectedTools 含有非对象工具项")
    tool_id = _tool_id(tool)
    if not isinstance(tool_id, str) or not tool_id.strip():
        raise ValueError("Agent 工具缺少 id/pluginId")

    compact = {"id": tool_id}
    for key in ("version", "source", "toolConfig"):
        if key in tool and tool[key] is not None:
            compact[key] = (
                _sanitize_config(tool[key])
                if key == "toolConfig"
                else copy.deepcopy(tool[key])
            )

    raw_config = tool.get("config")
    config = _sanitize_config(raw_config if isinstance(raw_config, dict) else {})
    compact_inputs = []
    generated_keys = set()
    raw_inputs = tool.get("inputs")
    if isinstance(raw_inputs, list):
        for raw_input in raw_inputs:
            compact_input, mode, manual_value = _compact_input(raw_input)
            if not compact_input:
                continue
            compact_inputs.append(compact_input)
            key = compact_input["key"]
            if mode == AGENT_GENERATED_MODE:
                generated_keys.add(key)
            elif manual_value is not None and not _is_sensitive_key(key):
                config[key] = _sanitize_config(manual_value)

    for key in generated_keys:
        config.pop(key, None)
    if compact_inputs:
        compact["inputs"] = compact_inputs
    compact["config"] = config
    return compact


def _selected_tools_input(node: dict) -> dict | None:
    inputs = node.get("inputs")
    if not isinstance(inputs, list):
        return None
    return next(
        (item for item in inputs if isinstance(item, dict) and item.get("key") == AGENT_SELECTED_TOOLS_KEY),
        None,
    )


def normalize_agent_tools_in_workflow(document: dict) -> dict:
    """Return a copy with expanded Agent tool entries compressed for saving."""
    normalized = copy.deepcopy(document)
    for node in normalized.get("nodes", []):
        if not isinstance(node, dict):
            continue
        selected_input = _selected_tools_input(node)
        if selected_input is None or not isinstance(selected_input.get("value"), list):
            continue
        selected = selected_input["value"]
        # The schema also permits a legacy [toolId, version] tuple.
        if len(selected) == 2 and all(isinstance(item, str) for item in selected):
            continue
        selected_input["value"] = [compact_agent_tool(tool) for tool in selected]
    return normalized


def set_agent_system_prompt(
    document: dict,
    prompt: str,
    *,
    agent_node_id: str | None = None,
) -> dict:
    """Return a copy with the canonical prompt applied to Agent nodes."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Agent 系统提示词不能为空")

    canonical_prompt = prompt.rstrip()
    updated = copy.deepcopy(document)
    matched = 0
    for node in updated.get("nodes", []):
        if not isinstance(node, dict) or node.get("flowNodeType") != "agent":
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        for item in node.get("inputs", []):
            if isinstance(item, dict) and item.get("key") == "systemPrompt":
                item["value"] = canonical_prompt
                matched += 1
    if matched == 0:
        suffix = f" nodeId={agent_node_id}" if agent_node_id else ""
        raise ValueError(f"没有找到 Agent 系统提示词输入{suffix}")
    return updated


def set_agent_model(
    document: dict,
    model: str,
    *,
    agent_node_id: str | None = None,
) -> dict:
    """Return a copy with the selected Agent node's model changed.

    AgentV2 stores the FastGPT Model ID in the Agent node's ``model`` input.
    The node selector is required by callers that update a copied application
    so a model experiment cannot silently touch a different Agent node.
    """
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Agent 模型不能为空")

    canonical_model = model.strip()
    updated = copy.deepcopy(document)
    matched = 0
    for node in updated.get("nodes", []):
        if not isinstance(node, dict) or node.get("flowNodeType") != "agent":
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        for item in node.get("inputs", []):
            if isinstance(item, dict) and item.get("key") == "model":
                item["value"] = canonical_model
                matched += 1
    if matched == 0:
        suffix = f" nodeId={agent_node_id}" if agent_node_id else ""
        raise ValueError(f"没有找到 Agent 模型输入{suffix}")
    return updated


def set_agent_reasoning_effort(
    document: dict,
    effort: str,
    *,
    agent_node_id: str | None = None,
) -> dict:
    """Return a copy with the selected Agent node's reasoning effort set."""
    if not isinstance(effort, str) or effort.strip() not in VALID_REASONING_EFFORTS:
        allowed = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise ValueError(f"Agent reasoning effort 必须是 {allowed} 之一")

    canonical_effort = effort.strip()
    updated = copy.deepcopy(document)
    matched = 0
    for node in updated.get("nodes", []):
        if not isinstance(node, dict) or node.get("flowNodeType") != "agent":
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        for item in node.get("inputs", []):
            if isinstance(item, dict) and item.get("key") == "aiChatReasoningEffort":
                item["value"] = canonical_effort
                matched += 1
    if matched == 0:
        suffix = f" nodeId={agent_node_id}" if agent_node_id else ""
        raise ValueError(f"没有找到 Agent reasoning effort 输入{suffix}")
    return updated


def _merge_tools(existing: list, additions: list[dict]) -> list[dict]:
    merged = []
    positions = {}
    for tool in existing + additions:
        compact = compact_agent_tool(tool)
        tool_id = compact["id"]
        if tool_id in positions:
            merged[positions[tool_id]] = compact
        else:
            positions[tool_id] = len(merged)
            merged.append(compact)
    return merged


def bind_agent_tools(
    document: dict,
    tools: list[dict],
    *,
    replace: bool = True,
    agent_node_id: str | None = None,
) -> dict:
    """Set explicit tool bindings on one or all Agent nodes in a workflow."""
    bound = copy.deepcopy(document)
    compact_tools = [compact_agent_tool(tool) for tool in tools]
    matched = 0
    for node in bound.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        selected_input = _selected_tools_input(node)
        if selected_input is None:
            continue
        existing = selected_input.get("value")
        if not isinstance(existing, list):
            if replace and existing in (None, []):
                existing = []
            else:
                raise ValueError(f"Agent 节点 {node.get('nodeId', '<unknown>')} 的 selectedTools 不是数组")
        selected_input["value"] = (
            compact_tools if replace else _merge_tools(existing, compact_tools)
        )
        matched += 1
    if matched == 0:
        suffix = f" nodeId={agent_node_id}" if agent_node_id else ""
        raise ValueError(f"没有找到带 {AGENT_SELECTED_TOOLS_KEY} 的 Agent 节点{suffix}")
    return bound


def agent_tool_ids(document: dict, agent_node_id: str | None = None) -> list[list[str]]:
    """Return selected tool IDs grouped by Agent node, for read-back checks."""
    groups = []
    for node in document.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        selected_input = _selected_tools_input(node)
        if selected_input is None or not isinstance(selected_input.get("value"), list):
            continue
        selected = selected_input["value"]
        if len(selected) == 2 and all(isinstance(item, str) for item in selected):
            groups.append([selected[0]])
            continue
        groups.append([
            _tool_id(item)
            for item in selected
            if isinstance(item, dict) and isinstance(_tool_id(item), str)
        ])
    return groups


def agent_model_values(document: dict, agent_node_id: str | None = None) -> list[list[str]]:
    """Return Agent model inputs grouped by Agent node for read-back checks."""
    groups = []
    for node in document.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        if node.get("flowNodeType") != "agent":
            continue
        groups.append([
            item["value"]
            for item in node.get("inputs", [])
            if isinstance(item, dict)
            and item.get("key") == "model"
            and isinstance(item.get("value"), str)
        ])
    return groups


def agent_reasoning_effort_values(document: dict, agent_node_id: str | None = None) -> list[list[str]]:
    """Return Agent reasoning-effort inputs grouped by Agent node."""
    groups = []
    for node in document.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if agent_node_id and node.get("nodeId") != agent_node_id:
            continue
        if node.get("flowNodeType") != "agent":
            continue
        groups.append([
            item["value"]
            for item in node.get("inputs", [])
            if isinstance(item, dict)
            and item.get("key") == "aiChatReasoningEffort"
            and isinstance(item.get("value"), str)
        ])
    return groups


def load_workflow_document(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取工作流 JSON: {path} ({error.__class__.__name__})") from error

    document = raw
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        document = raw["data"]
    if not isinstance(document, dict):
        raise ValueError("输入必须是页面工作流或 FastGPT detail JSON 对象")
    nodes = document.get("nodes")
    if not isinstance(nodes, list):
        nodes = document.get("modules")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("工作流 JSON 缺少非空 nodes/modules 数组")
    edges = document.get("edges")
    chat_config = document.get("chatConfig", {})
    if not isinstance(edges, list) or not isinstance(chat_config, dict):
        raise ValueError("工作流 JSON 的 edges/chatConfig 类型不正确")
    return normalize_agent_tools_in_workflow({
        "nodes": nodes,
        "edges": edges,
        "chatConfig": chat_config,
    })


def load_bindings(path: Path) -> list[dict]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取工具绑定 JSON: {path} ({error.__class__.__name__})") from error
    tools = raw.get("tools") if isinstance(raw, dict) else raw
    if not isinstance(tools, list) or not tools:
        raise ValueError("工具绑定 JSON 必须是非空数组，或包含 tools 数组")
    return [compact_agent_tool(tool) for tool in tools]


def _tool_bindings_from_args(args: argparse.Namespace) -> list[dict]:
    if bool(args.tool_id) == bool(args.bindings):
        raise ValueError("必须且只能指定 --tool-id 或 --bindings")
    if args.bindings:
        return load_bindings(args.bindings)
    return [
        {"id": tool_id, "version": args.tool_version, "config": {}}
        for tool_id in args.tool_id
    ]


def _write_workflow(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _detail_to_workflow(detail: object) -> dict:
    if not isinstance(detail, dict):
        raise RuntimeError("FastGPT detail 返回格式不正确")
    return load_workflow_document_from_object(detail)


def load_workflow_document_from_object(raw: dict) -> dict:
    document = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    nodes = document.get("nodes")
    if not isinstance(nodes, list):
        nodes = document.get("modules")
    edges = document.get("edges")
    chat_config = document.get("chatConfig", {})
    if not isinstance(nodes, list) or not isinstance(edges, list) or not isinstance(chat_config, dict):
        raise RuntimeError("FastGPT detail 缺少 nodes/modules、edges 或 chatConfig")
    return normalize_agent_tools_in_workflow({
        "nodes": nodes,
        "edges": edges,
        "chatConfig": chat_config,
    })


def main() -> int:
    parser = argparse.ArgumentParser(
        description="将 FastGPT AgentV2 工具绑定写成 agent_selectedTools 的紧凑持久化格式；默认 dry-run"
    )
    parser.add_argument("--workflow", required=True, type=Path, help="页面导入 JSON，或 FastGPT detail JSON")
    parser.add_argument("--tool-id", action="append", help="要显式绑定的工作流工具 AppID；可重复")
    parser.add_argument("--tool-version", default="", help="--tool-id 对应版本；空字符串表示 latest")
    parser.add_argument("--bindings", type=Path, help="工具绑定 JSON：数组或 {tools: [...]}；可包含 config/inputs")
    parser.add_argument("--append", action="store_true", help="追加工具并按 id 去重；默认替换 Agent 工具列表")
    parser.add_argument("--agent-node-id", help="只修改指定 nodeId；默认修改所有带 agent_selectedTools 的节点")
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="将指定的 canonical AgentV2 系统提示词与工具绑定一起发布",
    )
    parser.add_argument(
        "--model",
        help="将 Agent 节点的 model 输入改为指定 FastGPT Model ID，并与工具/Prompt 原子发布",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=sorted(VALID_REASONING_EFFORTS),
        help="设置 AgentV2 的 reasoning effort；GLM-5.3-Flash 不接受 none",
    )
    parser.add_argument("--output", type=Path, help="写出修改后的页面导入格式 JSON")
    parser.add_argument("--api-url", default=os.environ.get("FASTGPT_API_URL", ""))
    parser.add_argument("--app-id", help="apply 时要更新的 Agent AppID")
    parser.add_argument("--auth-token-env", default="FASTGPT_AUTH_TOKEN")
    parser.add_argument("--auth-cookie-env", help="管理会话 Cookie 所在环境变量名")
    parser.add_argument("--http-bearer-env", help="含 HTTP 节点时注入 Bearer Secret 的环境变量名")
    parser.add_argument(
        "--preserve-remote-http-secrets",
        action="store_true",
        help="apply 时从远端 detail 保留同 nodeId 的 HTTP Secret",
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="实际调用 FastGPT update")
    parser.add_argument("--publish", action="store_true", help="update 后发布版本；必须同时指定 --apply")
    parser.add_argument("--version-name", default="Agent 工具绑定修复")
    args = parser.parse_args()

    if args.publish and not args.apply:
        parser.error("--publish 必须与 --apply 一起使用")
    if args.apply and (not args.api_url or not args.app_id):
        parser.error("--apply 必须同时提供 --api-url 和 --app-id")
    if args.preserve_remote_http_secrets and not args.apply:
        parser.error("--preserve-remote-http-secrets 只适用于 --apply")

    document = load_workflow_document(args.workflow)
    bindings = _tool_bindings_from_args(args)
    document = bind_agent_tools(
        document,
        bindings,
        replace=not args.append,
        agent_node_id=args.agent_node_id,
    )
    if args.system_prompt_file:
        try:
            system_prompt = args.system_prompt_file.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(
                f"无法读取 Agent 系统提示词文件: {args.system_prompt_file} ({error.__class__.__name__})"
            ) from error
        document = set_agent_system_prompt(
            document,
            system_prompt,
            agent_node_id=args.agent_node_id,
        )
    if args.model:
        document = set_agent_model(
            document,
            args.model,
            agent_node_id=args.agent_node_id,
        )
    if args.reasoning_effort:
        document = set_agent_reasoning_effort(
            document,
            args.reasoning_effort,
            agent_node_id=args.agent_node_id,
        )

    if args.output:
        _write_workflow(args.output, document)

    expected_ids = [tool["id"] for tool in bindings]
    if not args.apply:
        print(json.dumps({
            "ok": True,
            "mode": "dry_run",
            "agentToolGroups": agent_tool_ids(document, args.agent_node_id),
            "agentModelGroups": agent_model_values(document, args.agent_node_id),
            "agentReasoningEffortGroups": agent_reasoning_effort_values(document, args.agent_node_id),
            "requestedToolIds": expected_ids,
            "requestedModel": args.model,
            "requestedReasoningEffort": args.reasoning_effort,
            "systemPromptFile": str(args.system_prompt_file) if args.system_prompt_file else None,
            "output": str(args.output) if args.output else None,
            "credentials": "not-read",
        }, ensure_ascii=False, indent=2))
        return 0

    # Import the existing management API helpers only for the apply path.  The
    # pure transformation and dry-run path remains network-free and testable.
    from create_fastgpt_app import (  # pylint: disable=import-outside-toplevel
        build_version_save_payload,
        http_secret_nodes,
        inject_http_bearer,
        normalize_api_base,
        preserve_remote_http_secrets,
        request_json,
    )

    api_base = normalize_api_base(args.api_url)
    auth_token = os.environ.get(args.auth_token_env, "")
    auth_cookie = os.environ.get(args.auth_cookie_env, "") if args.auth_cookie_env else ""
    if not auth_token and not auth_cookie:
        raise ValueError(
            f"缺少管理会话凭据：请设置 {args.auth_token_env} 或使用 --auth-cookie-env 指定 Cookie"
        )
    auth_headers = {}
    if auth_token:
        auth_headers["token"] = auth_token
    if auth_cookie:
        auth_headers["Cookie"] = auth_cookie

    detail = request_json(
        f"{api_base}/api/core/app/detail?{urlencode({'appId': args.app_id})}",
        auth_headers,
        None,
        args.timeout,
        method="GET",
    )
    http_nodes = http_secret_nodes(document)
    if http_nodes and args.preserve_remote_http_secrets:
        document = preserve_remote_http_secrets(document, detail)
    elif http_nodes and args.http_bearer_env:
        document = inject_http_bearer(document, os.environ.get(args.http_bearer_env, ""))
    elif http_nodes:
        raise ValueError(
            "实际写入含 HTTP 节点的工作流必须指定 --http-bearer-env，或使用 --preserve-remote-http-secrets"
        )

    # FastGPT's generic app/update endpoint only changes metadata. Graph
    # persistence belongs to the version endpoint: autoSave updates the
    # current draft, and the optional second call creates the published
    # version. Sending the graph to app/update can return HTTP 200 while
    # silently leaving agent_selectedTools unchanged.
    request_json(
        f"{api_base}/api/core/app/version/publish?{urlencode({'appId': args.app_id})}",
        auth_headers,
        build_version_save_payload(document, is_publish=False, auto_save=True),
        args.timeout,
    )

    if args.publish:
        request_json(
            f"{api_base}/api/core/app/version/publish?{urlencode({'appId': args.app_id})}",
            auth_headers,
            build_version_save_payload(
                document,
                is_publish=True,
                version_name=args.version_name,
            ),
            args.timeout,
        )

    read_back = _detail_to_workflow(
        request_json(
            f"{api_base}/api/core/app/detail?{urlencode({'appId': args.app_id})}",
            auth_headers,
            None,
            args.timeout,
            method="GET",
        )
    )
    expected_set = set(expected_ids)
    observed_groups = agent_tool_ids(read_back, args.agent_node_id)
    if not observed_groups or any(
        (set(group) != expected_set if not args.append else not expected_set.issubset(set(group)))
        for group in observed_groups
    ):
        raise RuntimeError(
            "Agent 工具绑定读回校验失败：update 返回成功但 agent_selectedTools 未保存为期望列表"
        )
    if args.model:
        observed_models = agent_model_values(read_back, args.agent_node_id)
        if not observed_models or any(
            group != [args.model] for group in observed_models
        ):
            raise RuntimeError(
                "Agent 模型读回校验失败：update 返回成功但 Agent model 未保存为期望值"
            )
    if args.reasoning_effort:
        observed_efforts = agent_reasoning_effort_values(read_back, args.agent_node_id)
        if not observed_efforts or any(
            group != [args.reasoning_effort] for group in observed_efforts
        ):
            raise RuntimeError(
                "Agent reasoning effort 读回校验失败：update 返回成功但 effort 未保存为期望值"
            )

    print(json.dumps({
        "ok": True,
        "mode": "applied",
        "appId": args.app_id,
        "published": args.publish,
        "agentToolGroups": observed_groups,
        "agentModelGroups": agent_model_values(read_back, args.agent_node_id),
        "agentReasoningEffortGroups": agent_reasoning_effort_values(read_back, args.agent_node_id),
        "requestedToolIds": expected_ids,
        "requestedModel": args.model,
        "requestedReasoningEffort": args.reasoning_effort,
        "secretPolicy": "管理会话和 HTTP Secret 仅从环境变量读取，未写入日志",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
