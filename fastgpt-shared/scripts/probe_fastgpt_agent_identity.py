#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _fingerprint(secret: str) -> str:
    text = (secret or "").strip()
    if len(text) >= 16:
        return f"{text[:8]}...{text[-6:]}"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


def _read_key(args: argparse.Namespace) -> str:
    if args.api_key_stdin:
        return sys.stdin.read().strip()
    value = os.getenv(args.api_key_env)
    if not value:
        raise SystemExit(f"missing API key env var: {args.api_key_env}")
    return value.strip()


def _load_payload(args: argparse.Namespace) -> dict:
    if args.payload:
        with open(args.payload, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    return {
        "stream": False,
        "detail": True,
        "chatId": args.chat_id or f"identity-probe-{int(time.time())}",
        "messages": [{"role": "user", "content": args.query}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a FastGPT OpenAPI key to confirm which app/workflow it reaches.")
    parser.add_argument("--chat-url", required=True, help="FastGPT /v1/chat/completions URL")
    parser.add_argument("--api-key-env", default="FASTGPT_API_KEY")
    parser.add_argument("--api-key-stdin", action="store_true", help="read API key from stdin")
    parser.add_argument("--payload", help="optional JSON payload to send; must not contain secrets")
    parser.add_argument("--query", default="身份探测：请返回一句中文确认。")
    parser.add_argument("--chat-id", default="")
    parser.add_argument("--expect-node", action="append", default=[], help="nodeId/moduleName/moduleType marker expected in responseData")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    api_key = _read_key(args)
    payload = _load_payload(args)
    payload["stream"] = False
    payload["detail"] = True

    request = urllib.request.Request(
        args.chat_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        status = error.code
        raw = error.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw[:2000]}

    content = ""
    try:
        content = body.get("choices", [{}])[0].get("message", {}).get("content") or ""
    except Exception:
        content = ""
    response_data = body.get("responseData") if isinstance(body, dict) else None
    nodes = []
    if isinstance(response_data, list):
        for item in response_data:
            if not isinstance(item, dict):
                continue
            nodes.append(
                {
                    "nodeId": item.get("nodeId"),
                    "moduleType": item.get("moduleType"),
                    "moduleName": item.get("moduleName"),
                    "errorText": item.get("errorText"),
                }
            )
    observed = json.dumps(nodes, ensure_ascii=False)
    missing_expected = [marker for marker in args.expect_node if marker not in observed]
    result = {
        "chatUrl": args.chat_url,
        "keyFingerprint": _fingerprint(api_key),
        "httpStatus": status,
        "topError": body.get("error") if isinstance(body, dict) else None,
        "contentLength": len(content),
        "contentPreview": content[:160],
        "nodeCount": len(nodes),
        "nodes": nodes,
        "expectedMissing": missing_expected,
        "identityOk": status < 400 and not missing_expected and bool(nodes or content),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"chatUrl: {result['chatUrl']}")
        print(f"keyFingerprint: {result['keyFingerprint']}")
        print(f"httpStatus: {result['httpStatus']}")
        print(f"topError: {result['topError']}")
        print(f"contentLength: {result['contentLength']}")
        print("nodes:")
        for node in nodes:
            print(f"- {node['nodeId']} / {node['moduleType']} / {node['moduleName']} / error={node['errorText']}")
        if missing_expected:
            print("expectedMissing: " + ", ".join(missing_expected))
        print(f"identityOk: {result['identityOk']}")
    return 0 if result["identityOk"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
