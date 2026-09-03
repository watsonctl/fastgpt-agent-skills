#!/usr/bin/env python3
"""Export FastGPT flowResponses / complete run logs for one app.

This is a generalized, CLI-first version of the official template script shared by
FastGPT support. It intentionally keeps the exported JSON close to the official
shape so downstream analyzers can rely on the same structure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 50
DEFAULT_RECORD_PAGE_SIZE = 100


def normalize_base_url(raw: str) -> str:
    value = (raw or "").strip().rstrip("/")
    if not value:
        raise ValueError("base URL is required")

    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        raise ValueError(
            f"invalid base URL: {raw!r}. Expected something like https://host or https://host/api"
        )

    path = parts.path.rstrip("/")
    if path == "/api":
        path = ""

    return urlunsplit((parts.scheme, parts.netloc, path, "", "")).rstrip("/")


def _request_json(
    method: str,
    url: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"HTTP {exc.code} for {method.upper()} {url}: {body[:400]}"
        ) from exc
    except URLError as exc:
        body = _request_json_body_with_curl(method, url, api_key, payload=payload, timeout=timeout)
        if body is None:
            raise RuntimeError(f"request failed for {method.upper()} {url}: {exc}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"non-JSON response for {method.upper()} {url}: {body[:400]}"
        ) from exc


def _request_json_body_with_curl(
    method: str,
    url: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None,
    timeout: int,
) -> str | None:
    """Fallback for self-hosted FastGPT HTTPS endpoints that break urllib TLS.

    Some company deployments close Python urllib's TLS handshake with
    ``SSL: UNEXPECTED_EOF_WHILE_READING`` while curl succeeds against the same
    endpoint. Keep this fallback local to the diagnostic exporter so workflow
    debugging is not blocked by client TLS quirks.
    """

    curl = shutil.which("curl")
    if not curl:
        return None

    cmd = [
        curl,
        "-sS",
        "--http1.1",
        "--fail-with-body",
        "--retry",
        "1",
        "--retry-delay",
        "1",
        "-m",
        str(timeout),
        "-X",
        method.upper(),
        "-H",
        f"Authorization: Bearer {api_key}",
        "-H",
        "Content-Type: application/json",
        "-H",
        "Accept: application/json",
        url,
    ]
    if payload is not None:
        cmd.extend(["--data-binary", json.dumps(payload, ensure_ascii=False)])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"curl fallback failed for {method.upper()} {url}: "
            f"exit={result.returncode} stderr={result.stderr[:400]!r} body={result.stdout[:400]!r}"
        )
    return result.stdout


def post_json(base_url: str, api_key: str, path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    return _request_json("POST", f"{base_url}{path}", api_key, payload=payload, timeout=timeout)


def get_json(base_url: str, api_key: str, path: str, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    query = urlencode(params)
    return _request_json("GET", f"{base_url}{path}?{query}", api_key, timeout=timeout)


def expect_ok(response: dict[str, Any], action: str) -> dict[str, Any]:
    if response.get("code") != 200:
        raise RuntimeError(f"{action} failed: code={response.get('code')} message={response.get('message')!r}")
    return response


def get_chat_histories(
    base_url: str,
    api_key: str,
    app_id: str,
    *,
    page_size: int,
    timeout: int,
    source: str | None,
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"appId": app_id, "offset": 0, "pageSize": page_size}
    if source:
        payload["source"] = source
    response = expect_ok(
        post_json(base_url, api_key, "/api/core/chat/history/getHistories", payload, timeout),
        "getHistories",
    )
    return ((response.get("data") or {}).get("list") or []) if isinstance(response, dict) else []


def get_chat_init(
    base_url: str,
    api_key: str,
    app_id: str,
    chat_id: str,
    *,
    timeout: int,
) -> dict[str, Any]:
    response = expect_ok(
        get_json(
            base_url,
            api_key,
            "/api/core/chat/init",
            {"appId": app_id, "chatId": chat_id},
            timeout,
        ),
        "chat init",
    )
    return response.get("data") or {}


def get_chat_records(
    base_url: str,
    api_key: str,
    app_id: str,
    chat_id: str,
    *,
    page_size: int,
    timeout: int,
) -> list[dict[str, Any]]:
    response = expect_ok(
        post_json(
            base_url,
            api_key,
            "/api/core/chat/record/getRecords_v2",
            {"appId": app_id, "chatId": chat_id, "offset": 0, "pageSize": page_size},
            timeout,
        ),
        "getRecords_v2",
    )
    return ((response.get("data") or {}).get("list") or []) if isinstance(response, dict) else []


def get_full_response_data(
    base_url: str,
    api_key: str,
    app_id: str,
    chat_id: str,
    data_id: str,
    *,
    timeout: int,
) -> list[dict[str, Any]]:
    response = expect_ok(
        get_json(
            base_url,
            api_key,
            "/api/core/chat/getResData",
            {"appId": app_id, "chatId": chat_id, "dataId": data_id},
            timeout,
        ),
        "getResData",
    )
    data = response.get("data")
    return data if isinstance(data, list) else []


def build_ai_message_export(
    record: dict[str, Any], flow_responses: list[dict[str, Any]]
) -> dict[str, Any]:
    """Project an AI record without losing persistent citation evidence.

    ``getRecords_v2`` owns the persisted message fields, while
    ``getResData`` owns the run-time response tree. Keep both representations
    in the export. The presence flag distinguishes an actual empty
    ``totalQuoteList`` from an older endpoint/export that did not return the
    field at all.
    """

    return {
        "dataId": record.get("dataId"),
        "role": "AI",
        "content": record.get("value", []),
        "flowResponses": flow_responses,
        "totalQuoteList": record.get("totalQuoteList"),
        "totalQuoteListPresent": "totalQuoteList" in record,
    }


def resolve_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export FastGPT flowResponses / complete run logs for one app.")
    parser.add_argument("--base-url", default=os.getenv("FASTGPT_BASE_URL", ""))
    parser.add_argument("--api-key", default=os.getenv("FASTGPT_API_KEY", ""))
    parser.add_argument("--app-id", default=os.getenv("FASTGPT_APP_ID", ""))
    parser.add_argument("--export-dir", default="./fastgpt-logs")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--record-page-size", type=int, default=DEFAULT_RECORD_PAGE_SIZE)
    parser.add_argument("--max-chats", type=int, default=0, help="0 means no extra limit beyond page-size")
    parser.add_argument("--chat-id", default="", help="export only one chat by chatId")
    parser.add_argument("--source", default="", help="optional FastGPT chat source filter, e.g. api")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return parser.parse_args()


def main() -> int:
    args = resolve_args()
    if not args.base_url or not args.api_key or not args.app_id:
        raise SystemExit(
            "missing required credentials: provide --base-url/--api-key/--app-id or set FASTGPT_BASE_URL/FASTGPT_API_KEY/FASTGPT_APP_ID"
        )

    base_url = normalize_base_url(args.base_url)
    export_dir = Path(args.export_dir).expanduser().resolve()
    export_dir.mkdir(parents=True, exist_ok=True)

    if args.chat_id:
        init_data = get_chat_init(base_url, args.api_key, args.app_id, args.chat_id, timeout=args.timeout)
        chats = [
            {
                "chatId": args.chat_id,
                "title": init_data.get("customTitle") or init_data.get("title") or args.chat_id,
                "updateTime": init_data.get("updateTime"),
            }
        ]
    else:
        chats = get_chat_histories(
            base_url,
            args.api_key,
            args.app_id,
            page_size=args.page_size,
            timeout=args.timeout,
            source=args.source or None,
        )
        if args.max_chats > 0:
            chats = chats[: args.max_chats]

    export_rows: list[dict[str, Any]] = []
    for chat in chats:
        chat_id = str(chat.get("chatId") or "").strip()
        if not chat_id:
            continue
        title = chat.get("title") or "未命名对话"
        print(f"[*] Exporting chat: {title} ({chat_id})")
        records = get_chat_records(
            base_url,
            args.api_key,
            args.app_id,
            chat_id,
            page_size=args.record_page_size,
            timeout=args.timeout,
        )

        chat_row = {
            "chatId": chat_id,
            "title": title,
            "updateTime": chat.get("updateTime"),
            "messages": [],
        }
        for record in records:
            if record.get("obj") != "AI":
                continue
            data_id = record.get("dataId")
            if not data_id:
                continue
            flow_responses = get_full_response_data(
                base_url,
                args.api_key,
                args.app_id,
                chat_id,
                data_id,
                timeout=args.timeout,
            )
            chat_row["messages"].append(build_ai_message_export(record, flow_responses))
        export_rows.append(chat_row)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = export_dir / f"app_{args.app_id}_full_logs_{timestamp}.json"
    output_path.write_text(json.dumps(export_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[√] Exported {len(export_rows)} chat(s) to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
