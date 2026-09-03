#!/usr/bin/env python3
"""Create and optionally publish a FastGPT workflow or workflow tool.

The input file is the dashboard import shape: nodes/edges/chatConfig.
The FastGPT management API receives the same graph as modules/edges/chatConfig.
Credentials are read from the environment and are never printed or persisted.

FastGPT management endpoints use a logged-in web session (`fastgpt_token`),
not an OpenAPI/workflow Bearer key. Runtime HTTP node credentials are a
separate, optional environment-injected value.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bind_fastgpt_agent_tools import normalize_agent_tools_in_workflow


OBJECT_ID = re.compile(r"^[0-9a-f]{24}$")
PAGE_IMPORT_KEYS = {"nodes", "edges", "chatConfig"}


def normalize_api_base(value: str) -> str:
    base = value.strip().rstrip("/")
    base = re.sub(r"/api/v1/chat/completions$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"/api$", "", base, flags=re.IGNORECASE)
    return base


def load_page_workflow(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"无法读取工作流 JSON: {path} ({error.__class__.__name__})") from error

    if set(document) != PAGE_IMPORT_KEYS:
        raise ValueError("输入必须是页面导入格式，顶层只能包含 nodes、edges、chatConfig")
    if not isinstance(document["nodes"], list) or not document["nodes"]:
        raise ValueError("nodes 必须是非空数组")
    if not isinstance(document["edges"], list) or not isinstance(document["chatConfig"], dict):
        raise ValueError("edges/chatConfig 类型不正确")

    ids = []
    for item in document["nodes"]:
        if not isinstance(item, dict) or not isinstance(item.get("nodeId"), str):
            raise ValueError("节点缺少有效 nodeId")
        if not isinstance(item.get("inputs"), list) or not isinstance(item.get("outputs"), list):
            raise ValueError(f"节点 {item['nodeId']} 必须显式包含 inputs 和 outputs 数组")
        ids.append(item["nodeId"])
    if len(set(ids)) != len(ids):
        raise ValueError("nodes 中存在重复 nodeId")
    node_ids = set(ids)
    for edge in document["edges"]:
        if not isinstance(edge, dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise ValueError("edges 含有不存在的 source/target")

    return normalize_agent_tools_in_workflow(document)


def build_create_payload(document: dict, kind: str, name: str, parent_id: str | None, intro: str) -> dict:
    if kind == "workflow-tool" and not parent_id:
        raise ValueError("workflow-tool 必须提供 toolFolder 的 --parent-id")
    if parent_id and not OBJECT_ID.fullmatch(parent_id):
        raise ValueError("--parent-id 不是 24 位 ObjectId")
    document = normalize_agent_tools_in_workflow(document)
    return {
        **({"parentId": parent_id} if parent_id else {}),
        "name": name,
        "intro": intro,
        "type": "plugin" if kind == "workflow-tool" else "advanced",
        "modules": document["nodes"],
        "edges": document["edges"],
        "chatConfig": document["chatConfig"],
    }


def build_version_save_payload(
    document: dict,
    *,
    is_publish: bool,
    version_name: str | None = None,
    auto_save: bool = False,
) -> dict:
    """Build the graph payload for FastGPT's version save endpoint.

    ``PUT /api/core/app/update`` only updates app metadata. Workflow graphs
    are persisted by ``POST /api/core/app/version/publish``: ``autoSave``
    updates the current draft and ``isPublish`` creates the online version.
    """
    document = normalize_agent_tools_in_workflow(document)
    payload = {
        "nodes": document["nodes"],
        "edges": document["edges"],
        "chatConfig": document["chatConfig"],
        "isPublish": is_publish,
        "autoSave": auto_save,
    }
    if version_name is not None:
        payload["versionName"] = version_name
    return payload


def http_secret_nodes(document: dict) -> list[str]:
    return [
        item["nodeId"]
        for item in document["nodes"]
        if item.get("flowNodeType") == "httpRequest468"
    ]


def inject_http_bearer(document: dict, secret: str) -> dict:
    """Inject a Bearer value into the request copy only.

    FastGPT encrypts system_header_secret while saving the application. The
    source JSON remains secret-free; this value exists only in the in-memory
    request payload and is never printed by this script.
    """
    if not secret:
        raise ValueError("HTTP Bearer Secret 环境变量为空")
    request_document = json.loads(json.dumps(document, ensure_ascii=False))
    for node in request_document["nodes"]:
        if node.get("flowNodeType") != "httpRequest468":
            continue
        secret_input = next(
            (item for item in node["inputs"] if item.get("key") == "system_header_secret"),
            None,
        )
        if secret_input is None:
            raise ValueError(f"HTTP 节点 {node.get('nodeId', '<unknown>')} 缺少 system_header_secret")
        secret_input["value"] = {"Bearer": {"secret": "", "value": secret}}
    return request_document


def _has_http_secret(value: object) -> bool:
    """Return whether a FastGPT HTTP-auth value contains a configured secret.

    The management API may return either the encrypted ``secret`` field or a
    runtime ``value`` field depending on the target build.  We only inspect
    whether one is present; the value is never logged.
    """
    if isinstance(value, dict):
        for key in ("value", "secret"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return True
        return any(_has_http_secret(candidate) for candidate in value.values())
    return isinstance(value, str) and bool(value.strip())


def preserve_remote_http_secrets(document: dict, detail: object) -> dict:
    """Copy existing HTTP node auth values into an in-memory update document.

    Exported/imported workflow JSON intentionally omits ``system_header_secret``.
    When updating an already configured app, replacing the graph with that
    secret-free JSON can silently clear the user's node credentials.  This
    helper preserves only matching node IDs from the read-back detail; it does
    not touch system-tool credentials such as SearchInfinity.
    """
    data = detail.get("data") if isinstance(detail, dict) else None
    remote_nodes = {
        node.get("nodeId"): node
        for node in (data.get("modules", []) if isinstance(data, dict) else [])
        if isinstance(node, dict) and isinstance(node.get("nodeId"), str)
    }
    request_document = json.loads(json.dumps(document, ensure_ascii=False))
    missing = []
    for node in request_document["nodes"]:
        if node.get("flowNodeType") != "httpRequest468":
            continue
        remote_node = remote_nodes.get(node.get("nodeId"))
        remote_input = next(
            (
                item for item in (remote_node.get("inputs", []) if remote_node else [])
                if item.get("key") == "system_header_secret"
            ),
            None,
        )
        remote_value = remote_input.get("value") if remote_input else None
        if not _has_http_secret(remote_value):
            missing.append(node.get("nodeId", "<unknown>"))
            continue
        local_input = next(
            (item for item in node["inputs"] if item.get("key") == "system_header_secret"),
            None,
        )
        if local_input is None:
            raise ValueError(f"HTTP 节点 {node.get('nodeId', '<unknown>')} 缺少 system_header_secret")
        local_input["value"] = remote_value
    if missing:
        names = ", ".join(str(item) for item in missing)
        raise ValueError(f"无法从远端保留 HTTP 节点 Secret，请先在 FastGPT 配置: {names}")
    return request_document


def extract_app_id(response: object) -> str | None:
    values = []
    if isinstance(response, str):
        values.append(response)
    elif isinstance(response, dict):
        for key in ("data", "appId", "_id", "id"):
            values.append(response.get(key))
        if isinstance(response.get("data"), dict):
            values.extend(response["data"].get(key) for key in ("appId", "_id", "id"))
    for value in values:
        if isinstance(value, str) and OBJECT_ID.fullmatch(value):
            return value
    return None


def request_json(
    url: str,
    headers: dict[str, str],
    payload: dict | None,
    timeout: int,
    method: str = "POST",
) -> object:
    request = Request(
        url,
        data=(json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None),
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"FastGPT 请求失败: HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"FastGPT 请求失败: {error.reason.__class__.__name__}") from error
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError as error:
        raise RuntimeError("FastGPT 返回了不可解析的 JSON") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="通过 FastGPT 管理 API 创建或更新工作流；默认只做 dry-run")
    parser.add_argument("--workflow", required=True, type=Path, help="页面导入格式 JSON")
    parser.add_argument("--mode", choices=["create", "update"], default="create", help="操作模式；默认 create")
    parser.add_argument("--app-id", help="update 模式的既有应用 AppID")
    parser.add_argument("--name", help="FastGPT 应用/工具名称；update 模式可省略以保留原名")
    parser.add_argument("--kind", choices=["workflow", "workflow-tool"], default="workflow")
    parser.add_argument("--parent-id", help="workflow-tool 的 toolFolder AppID")
    parser.add_argument("--intro", default="", help="应用简介")
    parser.add_argument("--api-url", default=os.environ.get("FASTGPT_API_URL", ""))
    parser.add_argument(
        "--auth-token-env",
        default="FASTGPT_AUTH_TOKEN",
        help="FastGPT 登录会话 token 所在环境变量名（对应 fastgpt_token；不是 OpenAPI Key）",
    )
    parser.add_argument(
        "--auth-cookie-env",
        help="FastGPT 登录 Cookie 所在环境变量名；与 --auth-token-env 至少提供一个",
    )
    parser.add_argument(
        "--http-bearer-env",
        help="HTTP 节点 Bearer Secret 所在环境变量名；仅在 apply 时读取，不写入源 JSON",
    )
    parser.add_argument(
        "--preserve-remote-http-secrets",
        action="store_true",
        help="update 时从远端 detail 保留同 nodeId 的 HTTP Secret；不触碰系统工具 Secret",
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="实际创建远程应用；未指定时不发请求")
    parser.add_argument("--publish", action="store_true", help="创建成功后发布版本；必须同时指定 --apply")
    parser.add_argument("--version-name", default="正式发布版")
    args = parser.parse_args()

    if args.publish and not args.apply:
        parser.error("--publish 必须与 --apply 一起使用")
    if args.mode == "create" and not args.name:
        parser.error("create 模式必须提供 --name")
    if args.mode == "update" and not args.app_id:
        parser.error("update 模式必须提供 --app-id")
    if args.mode == "update" and not OBJECT_ID.fullmatch(args.app_id):
        parser.error("--app-id 不是 24 位 ObjectId")
    if args.mode == "update" and (args.parent_id or args.kind != "workflow"):
        parser.error("update 模式不接受 --parent-id 或用于创建的 --kind；既有应用类型保持不变")
    if args.preserve_remote_http_secrets and (not args.apply or args.mode != "update"):
        parser.error("--preserve-remote-http-secrets 只适用于 update + apply")
    document = load_page_workflow(args.workflow)
    http_nodes = http_secret_nodes(document)
    if args.apply and http_nodes and not args.http_bearer_env and not args.preserve_remote_http_secrets:
        parser.error(
            "实际写入含 HTTP 节点的应用必须指定 --http-bearer-env，或使用 --preserve-remote-http-secrets 保留远端配置"
        )
    http_secret_injected = False

    if not args.apply:
        payload = (
            build_create_payload(document, args.kind, args.name, args.parent_id, args.intro or "")
            if args.mode == "create"
            else build_version_save_payload(document, is_publish=False, auto_save=True)
        )
        print(json.dumps({
            "ok": True,
            "mode": "dry_run",
            "operation": args.mode,
            "kind": args.kind,
            "name": args.name,
            "appId": args.app_id,
            "nodeCount": len(document["nodes"]),
            "edgeCount": len(document["edges"]),
            "httpSecretNodes": http_nodes,
            "wouldRequest": "POST /api/core/app/create" if args.mode == "create" else "POST /api/core/app/version/publish?appId=... (autoSave=true)",
            "wouldPublish": args.publish,
            "credential": "not-read",
        }, ensure_ascii=False, indent=2))
        return 0

    api_base = normalize_api_base(args.api_url)
    auth_token = os.environ.get(args.auth_token_env, "")
    auth_cookie = os.environ.get(args.auth_cookie_env, "") if args.auth_cookie_env else ""
    if not api_base:
        raise ValueError("缺少 --api-url 或 FASTGPT_API_URL")
    if not auth_token and not auth_cookie:
        raise ValueError(
            f"缺少管理会话凭据：请设置 {args.auth_token_env} 或使用 --auth-cookie-env 指定 fastgpt_token Cookie"
        )
    auth_headers = {}
    if auth_token:
        auth_headers["token"] = auth_token
    if auth_cookie:
        auth_headers["Cookie"] = auth_cookie

    detail = None
    if args.mode == "update":
        # Read once before update. Besides checking permission, this allows a
        # secret-preserving update without asking the user to re-enter node
        # credentials after every generated-graph change.
        detail = request_json(
            f"{api_base}/api/core/app/detail?{urlencode({'appId': args.app_id})}",
            auth_headers,
            None,
            args.timeout,
            method="GET",
        )
        if args.preserve_remote_http_secrets:
            document = preserve_remote_http_secrets(document, detail)
    if args.http_bearer_env:
        document = inject_http_bearer(document, os.environ.get(args.http_bearer_env, ""))
        http_secret_injected = True
    payload = (
        build_create_payload(document, args.kind, args.name, args.parent_id, args.intro or "")
        if args.mode == "create"
        else None
    )

    if args.mode == "create":
        created = request_json(f"{api_base}/api/core/app/create", auth_headers, payload, args.timeout)
        app_id = extract_app_id(created)
        if not app_id:
            raise RuntimeError("创建响应未返回可识别的 AppID；未打印原始响应以避免泄露内部数据")
    else:
        app_id = args.app_id
        # Management routes require a session and app permission. The detail
        # read above probes that permission before writing the graph.
        if detail is None:
            raise RuntimeError("更新前未取得应用 detail")
        metadata = {}
        if args.name is not None:
            metadata["name"] = args.name
        if args.intro is not None:
            metadata["intro"] = args.intro
        if metadata:
            request_json(
                f"{api_base}/api/core/app/update?{urlencode({'appId': app_id})}",
                auth_headers,
                metadata,
                args.timeout,
                method="PUT",
            )
        request_json(
            f"{api_base}/api/core/app/version/publish?{urlencode({'appId': app_id})}",
            auth_headers,
            build_version_save_payload(document, is_publish=False, auto_save=True),
            args.timeout,
        )

    published = False
    if args.publish:
        publish_payload = build_version_save_payload(
            document,
            is_publish=True,
            version_name=args.version_name,
        )
        request_json(
            f"{api_base}/api/core/app/version/publish?{urlencode({'appId': app_id})}",
            auth_headers,
            publish_payload,
            args.timeout,
        )
        published = True

    print(json.dumps({
        "ok": True,
        "mode": "applied",
        "operation": args.mode,
        "kind": args.kind,
        "appId": app_id,
        "published": published,
        "httpSecretNodes": http_nodes,
        "httpSecretInjected": http_secret_injected,
        "secretPolicy": "session and HTTP credentials were read from the environment and not persisted in source JSON or logs",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
