#!/usr/bin/env python3
"""Summarize and diagnose FastGPT flowResponses exports."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"expected top-level list in {path}")
    return data


def select_latest_json(directory: Path) -> Path:
    files = sorted(
        [path for path in directory.glob("*.json") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
    )
    if not files:
        raise FileNotFoundError(f"no JSON files found under {directory}")
    return files[-1]


def count_non_empty_items(value: Any) -> int:
    if isinstance(value, list):
        return len([item for item in value if item not in (None, "", [], {})])
    return 0


def find_first(responses: list[dict[str, Any]], predicate):
    for item in responses:
        if predicate(item):
            return item
    return None


def as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value in (None, False):
        return ""
    if isinstance(value, list):
        parts = [as_text(item) for item in value]
        return "\n".join([item for item in parts if item]).strip()
    if isinstance(value, dict):
        for key in ("text", "content", "value"):
            if key in value:
                return as_text(value[key])
    return ""


def flatten_responses(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for item in responses:
        flat.append(item)
        for key in ("pluginDetail", "toolDetail", "loopDetail", "childrenResponses"):
            children = item.get(key)
            if isinstance(children, list):
                flat.extend(flatten_responses([child for child in children if isinstance(child, dict)]))
    return flat


def flatten_native_main_responses(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten main-workflow children that FastGPT can use for native citation registration.

    Workflow-tool/plugin internals are useful for diagnosis, but native citation click
    permissions have repeatedly proven safest when a main-workflow datasetSearchNode
    (including loop/parallel children) records the cited collections.
    """

    flat: list[dict[str, Any]] = []
    for item in responses:
        flat.append(item)
        for key in ("loopDetail", "childrenResponses"):
            children = item.get(key)
            if isinstance(children, list):
                flat.extend(
                    flatten_native_main_responses(
                        [child for child in children if isinstance(child, dict)]
                    )
                )
    return flat


def extract_cite_ids(message: dict[str, Any]) -> list[str]:
    content = message.get("content")
    text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return sorted(set(re.findall(r"\[([0-9a-fA-F]{24})\]\(CITE\)", text)))


def quote_collection_ids(quotes: Any) -> set[str]:
    if not isinstance(quotes, list):
        return set()
    return {
        str(item.get("collectionId"))
        for item in quotes
        if isinstance(item, dict) and item.get("collectionId")
    }


def quote_ids(quotes: Any) -> set[str]:
    if not isinstance(quotes, list):
        return set()
    return {
        str(item.get("id"))
        for item in quotes
        if isinstance(item, dict) and item.get("id")
    }


STANDARD_REF_RE = re.compile(
    r"(?i)([A-Z]{1,6}\s*[\/\\-]?\s*[A-Z]{0,6}|GB\/T|GBT|GB|GBJ|GBZ|DL\/T|DLT|DL|NB\/T|NBT|NB|JGJ|JG|CJJ|CJ|SH|HG|SY|YD|SL|MT|KA|DZ|JT|JTG|YB|TD|CH|JC|JB)\s*[-\s]*\d{1,7}"
)


def dataset_search_diagnostics(searches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in searches:
        quote_list = item.get("quoteList") if isinstance(item.get("quoteList"), list) else []
        node_response = item.get("nodeResponse") if isinstance(item.get("nodeResponse"), dict) else {}
        query = as_text(item.get("query") or node_response.get("query"))
        collection_filter = item.get("collectionFilterMatch") or node_response.get("collectionFilterMatch")
        items.append(
            {
                "moduleName": item.get("moduleName"),
                "nodeId": item.get("nodeId"),
                "runningTime": item.get("runningTime"),
                "queryLength": len(query),
                "limit": item.get("limit") or node_response.get("limit"),
                "searchMode": item.get("searchMode") or node_response.get("searchMode"),
                "quoteCount": count_non_empty_items(quote_list),
                "collectionIds": sorted(quote_collection_ids(quote_list)),
                "collectionFilterMatch": collection_filter,
            }
        )
    return items


def summarize_message(chat: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    responses = message.get("flowResponses") or []
    flat_responses = flatten_responses([item for item in responses if isinstance(item, dict)])
    native_main_responses = flatten_native_main_responses(
        [item for item in responses if isinstance(item, dict)]
    )
    normalize = find_first(
        responses,
        lambda item: item.get("moduleType") == "code"
        and isinstance(item.get("customOutputs"), dict)
        and "userQuery" in item.get("customOutputs", {}),
    )
    bridge = find_first(
        responses,
        lambda item: item.get("moduleType") == "code"
        and isinstance(item.get("customOutputs"), dict)
        and (
            "generalTasks" in item.get("customOutputs", {})
            or "rewrittenQueries" in item.get("customOutputs", {})
        ),
    )
    analyzer = find_first(
        responses,
        lambda item: item.get("moduleType") == "chatNode"
        and (
            item.get("nodeId") == "analyzeQuery"
            or "分析" in str(item.get("moduleName") or "")
            or "analy" in str(item.get("nodeId") or "").lower()
        ),
    )
    plugin_modules = [item for item in responses if item.get("moduleType") == "pluginModule"]
    native_dataset_searches = [
        item
        for item in native_main_responses
        if item.get("moduleType") == "datasetSearchNode" and isinstance(item.get("quoteList"), list)
    ]
    all_dataset_searches = [
        item
        for item in flat_responses
        if item.get("moduleType") == "datasetSearchNode" and isinstance(item.get("quoteList"), list)
    ]
    final_context = find_first(
        responses,
        lambda item: item.get("moduleType") == "code"
        and isinstance(item.get("customOutputs"), dict)
        and "finalQuoteQA" in item.get("customOutputs", {}),
    )
    final_answer = find_first(
        responses,
        lambda item: item.get("moduleType") == "chatNode"
        and (
            item.get("nodeId") == "finalAnswer"
            or "最终作答" in str(item.get("moduleName") or "")
        ),
    )

    normalize_outputs = (normalize or {}).get("customOutputs") or {}
    bridge_outputs = (bridge or {}).get("customOutputs") or {}
    final_context_outputs = (final_context or {}).get("customOutputs") or {}

    anomalies: list[str] = []
    message_text = as_text(message.get("content"))
    if re.search(r"\{[\s\S]*(queryType|retrievalIntensity|scores|verifier|rankPlan)[\s\S]*\}", message_text):
        anomalies.append("internal_ai_output_leaked_to_user")
    if not final_answer and not any("直接回答" in str(name or "") for name in [item.get("moduleName") for item in responses]):
        anomalies.append("final_answer_missing")
    if responses:
        last_name = str(responses[-1].get("moduleName") or responses[-1].get("nodeId") or "")
        if "引用授权" in last_name or "citationAuth" in last_name:
            anomalies.append(f"stopped_at_citation_auth:{last_name}")
    analyzer_query = as_text((analyzer or {}).get("query"))
    normalize_user_query = as_text(normalize_outputs.get("userQuery"))
    if analyzer_query and not normalize_user_query:
        anomalies.append("input_lost_before_normalize: analyzer.query 非空，但 normalizeInput.userQuery 为空")

    bridge_primary = as_text(bridge_outputs.get("primarySearchQuery"))
    bridge_rewritten = bridge_outputs.get("rewrittenQueries") or []
    bridge_general_tasks = bridge_outputs.get("generalTasks") or []
    available_dataset_keys = normalize_outputs.get("availableDatasetKeys") or []
    if normalize_user_query and not bridge_primary:
        anomalies.append("bridge_primary_search_query_empty")
    if not bridge_rewritten:
        anomalies.append("bridge_rewritten_queries_empty")
    if not bridge_general_tasks:
        anomalies.append("bridge_general_tasks_empty")
    if (
        bridge_outputs.get("hasExplicitStandard") is True
        and normalize_user_query
        and not STANDARD_REF_RE.search(normalize_user_query)
        and count_non_empty_items(bridge_outputs.get("precisionTasks") or []) > 0
    ):
        anomalies.append("inferred_standard_hard_locked_as_explicit")

    tool_summaries = []
    for tool in plugin_modules:
        tool_input = tool.get("toolInput") or {}
        tool_output = tool.get("pluginOutput") or {}
        flags = []
        if isinstance(tool_input, dict):
            for key in ("generalTasks", "precisionTasks", "autoTasks", "lookupTasks", "collectionIds"):
                if key in tool_input and count_non_empty_items(tool_input.get(key)) == 0:
                    flags.append(f"{key}=empty")
            if "userQuery" in tool_input and not as_text(tool_input.get("userQuery")):
                flags.append("userQuery=empty")
            if "primarySearchQuery" in tool_input and not as_text(tool_input.get("primarySearchQuery")):
                flags.append("primarySearchQuery=empty")
        if isinstance(tool_output, dict):
            if "candidateCount" in tool_output and int(tool_output.get("candidateCount") or 0) == 0:
                flags.append("candidateCount=0")
            if "matchedCollectionIds" in tool_output and count_non_empty_items(tool_output.get("matchedCollectionIds")) == 0:
                flags.append("matchedCollectionIds=empty")
            metadata = tool_output.get("metadataRawResponse")
            if isinstance(metadata, dict) and "items" in metadata:
                input_collection_count = (
                    count_non_empty_items(tool_input.get("collectionIds"))
                    if isinstance(tool_input, dict)
                    else 0
                )
                if input_collection_count > 0 and count_non_empty_items(metadata.get("items")) == 0:
                    flags.append("metadata.items=empty_for_nonempty_collectionIds")
            if "faqMode" in tool_output:
                flags.append(
                    f"faqMode={tool_output.get('faqMode')};faqScore={tool_output.get('faqScore')}"
                )
            final_user_prompt = as_text(tool_output.get("finalUserPrompt"))
            if final_user_prompt:
                input_user_query = as_text(tool_input.get("userQuery")) if isinstance(tool_input, dict) else ""
                input_query_type = as_text(tool_input.get("queryType")) if isinstance(tool_input, dict) else ""
                if input_user_query and not (
                    f"用户问题: {input_user_query}" in final_user_prompt
                    or f"用户问题：{input_user_query}" in final_user_prompt
                ):
                    flags.append("finalUserPrompt.userQuery_lost")
        tool_summaries.append(
            {
                "moduleName": tool.get("moduleName"),
                "nodeId": tool.get("nodeId"),
                "flags": flags,
                "toolInput": tool_input,
                "pluginOutput": tool_output,
            }
        )
        if flags:
            anomalies.append(f"tool_issue:{tool.get('moduleName')}:{','.join(flags)}")

    cite_ids = extract_cite_ids(message)
    final_quote_qa = final_context_outputs.get("finalQuoteQA") or []
    final_quote_collections = quote_collection_ids(final_quote_qa)
    final_quote_ids = quote_ids(final_quote_qa)
    top_level_quote_lists = [item.get("quoteList") or [] for item in native_dataset_searches]
    top_level_collection_ids = set().union(*(quote_collection_ids(items) for items in top_level_quote_lists)) if top_level_quote_lists else set()
    top_level_quote_ids = set().union(*(quote_ids(items) for items in top_level_quote_lists)) if top_level_quote_lists else set()
    uncovered_collections = sorted(final_quote_collections - top_level_collection_ids)
    native_citation_risk = bool(cite_ids) and (
        not native_dataset_searches or bool(uncovered_collections)
    )
    if not cite_ids and (
        final_quote_ids
        or any(count_non_empty_items(items) > 0 for items in top_level_quote_lists)
    ):
        anomalies.append(
            "final_answer_missing_cite_markers: quoteList/finalQuoteQA exists but final text has no [24hex](CITE)"
        )
    if cite_ids and not native_dataset_searches:
        anomalies.append("native_citation_auth_chain_missing: final answer has CITE ids but main-workflow flowResponses has no datasetSearchNode.quoteList")
    elif uncovered_collections:
        anomalies.append(
            "native_citation_collection_not_covered:" + ",".join(uncovered_collections)
        )
    slow_native_dataset_searches = [
        item
        for item in dataset_search_diagnostics(native_dataset_searches)
        if float(item.get("runningTime") or 0) >= 10
    ]
    for item in slow_native_dataset_searches:
        anomalies.append(
            f"slow_native_dataset_search:{item.get('moduleName') or item.get('nodeId')}:"
            f"{item.get('runningTime')}s:queryLength={item.get('queryLength')}:"
            f"limit={item.get('limit')}:searchMode={item.get('searchMode')}"
        )

    return {
        "chatId": chat.get("chatId"),
        "title": chat.get("title"),
        "dataId": message.get("dataId"),
        "nodeChain": [item.get("moduleName") for item in responses],
        "analyzer": {
            "moduleName": (analyzer or {}).get("moduleName"),
            "query": analyzer_query,
            "runningTime": (analyzer or {}).get("runningTime"),
        },
        "normalizeInput": {
            "moduleName": (normalize or {}).get("moduleName"),
            "userQuery": normalize_user_query,
            "industry": as_text(normalize_outputs.get("industry")),
            "availableDatasetKeys": available_dataset_keys,
        },
        "analysisBridge": {
            "moduleName": (bridge or {}).get("moduleName"),
            "questionDomain": bridge_outputs.get("questionDomain"),
            "rewrittenQueries": bridge_rewritten,
            "primarySearchQuery": bridge_primary,
            "generalTasksCount": count_non_empty_items(bridge_general_tasks),
            "precisionTasksCount": count_non_empty_items(bridge_outputs.get("precisionTasks") or []),
            "bridgeFallbackApplied": bridge_outputs.get("bridgeFallbackApplied"),
            "directAnswerDecisionSource": bridge_outputs.get("directAnswerDecisionSource"),
        },
        "runtime": {
            "hasFinalAnswerNode": bool(final_answer),
            "finalAnswerRunningTime": (final_answer or {}).get("runningTime"),
            "internalOutputLeakRisk": "internal_ai_output_leaked_to_user" in anomalies,
            "stoppedAt": responses[-1].get("moduleName") if responses else None,
        },
        "tools": tool_summaries,
        "citation": {
            "citeIds": cite_ids,
            "citeIdCount": len(cite_ids),
            "finalQuoteIds": sorted(final_quote_ids),
            "finalQuoteCollectionIds": sorted(final_quote_collections),
            "topLevelDatasetSearchCount": len(native_dataset_searches),
            "topLevelQuoteCount": sum(count_non_empty_items(items) for items in top_level_quote_lists),
            "topLevelQuoteIds": sorted(top_level_quote_ids),
            "topLevelCollectionIds": sorted(top_level_collection_ids),
            "allDatasetSearchCount": len(all_dataset_searches),
            "nativeDatasetSearches": dataset_search_diagnostics(native_dataset_searches),
            "slowNativeDatasetSearches": slow_native_dataset_searches,
            "uncoveredCollectionIds": uncovered_collections,
            "nativeCitationRisk": native_citation_risk,
        },
        "anomalies": anomalies,
    }


def filter_rows(rows: list[dict[str, Any]], *, chat_id: str, title_contains: str, data_id: str) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for chat in rows:
        if chat_id and chat.get("chatId") != chat_id:
            continue
        if title_contains and title_contains not in str(chat.get("title") or ""):
            continue
        messages = chat.get("messages") or []
        chat_copy = {**chat, "messages": []}
        for message in messages:
            if data_id and message.get("dataId") != data_id:
                continue
            chat_copy["messages"].append(message)
        if chat_copy["messages"]:
            filtered.append(chat_copy)
    return filtered


def render_text(path: Path, summaries: list[dict[str, Any]]) -> str:
    lines = [f"# FastGPT flow log analysis", f"- input: {path}", f"- matched_messages: {len(summaries)}", ""]
    for item in summaries:
        lines.extend(
            [
                f"## {item['title']} ({item['chatId']}) / dataId={item['dataId']}",
                f"- nodeChain: {' -> '.join(item['nodeChain'])}",
                f"- analyzer.query: {item['analyzer']['query']!r}",
                f"- normalizeInput.userQuery: {item['normalizeInput']['userQuery']!r}",
                f"- normalizeInput.availableDatasetKeys: {json.dumps(item['normalizeInput'].get('availableDatasetKeys') or [], ensure_ascii=False)}",
                f"- analysisBridge.primarySearchQuery: {item['analysisBridge']['primarySearchQuery']!r}",
                f"- analysisBridge.rewrittenQueries: {json.dumps(item['analysisBridge']['rewrittenQueries'], ensure_ascii=False)}",
                f"- analysisBridge.generalTasksCount: {item['analysisBridge']['generalTasksCount']}",
                f"- runtime.hasFinalAnswerNode: {str(item['runtime']['hasFinalAnswerNode']).lower()}",
                f"- runtime.internalOutputLeakRisk: {str(item['runtime']['internalOutputLeakRisk']).lower()}",
                f"- runtime.stoppedAt: {item['runtime']['stoppedAt']}",
                f"- citation.nativeCitationRisk: {str(item['citation']['nativeCitationRisk']).lower()}",
                f"- citation.citeIdCount: {item['citation']['citeIdCount']}",
                f"- citation.topLevelDatasetSearchCount: {item['citation']['topLevelDatasetSearchCount']}",
                f"- citation.topLevelQuoteCount: {item['citation']['topLevelQuoteCount']}",
                f"- citation.finalQuoteCollectionIds: {json.dumps(item['citation']['finalQuoteCollectionIds'], ensure_ascii=False)}",
                f"- citation.topLevelCollectionIds: {json.dumps(item['citation']['topLevelCollectionIds'], ensure_ascii=False)}",
                f"- citation.slowNativeDatasetSearches: {json.dumps(item['citation']['slowNativeDatasetSearches'], ensure_ascii=False)}",
                f"- anomalies: {', '.join(item['anomalies']) if item['anomalies'] else 'none'}",
                "- tools:",
            ]
        )
        for tool in item["tools"]:
            flags = ", ".join(tool["flags"]) if tool["flags"] else "none"
            lines.append(f"  - {tool['moduleName']}: {flags}")
        lines.append("")
    return "\n".join(lines)


def render_markdown(path: Path, summaries: list[dict[str, Any]]) -> str:
    return render_text(path, summaries)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze exported FastGPT flowResponses JSON.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="path to one exported JSON file")
    source.add_argument("--latest", help="directory; analyze the latest JSON file under it")
    parser.add_argument("--chat-id", default="")
    parser.add_argument("--title-contains", default="")
    parser.add_argument("--data-id", default="")
    parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.input).expanduser().resolve() if args.input else select_latest_json(Path(args.latest).expanduser().resolve())
    rows = load_json(path)
    filtered = filter_rows(rows, chat_id=args.chat_id, title_contains=args.title_contains, data_id=args.data_id)
    summaries = [summarize_message(chat, message) for chat in filtered for message in (chat.get("messages") or [])]

    if args.format == "json":
        print(json.dumps({"input": str(path), "messages": summaries}, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(render_markdown(path, summaries))
    else:
        print(render_text(path, summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
