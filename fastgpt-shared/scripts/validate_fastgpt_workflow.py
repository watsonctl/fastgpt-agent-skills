#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from _fastgpt_contracts import ALLOWED_CHATCONFIG_KEYS, ALLOWED_WORKFLOW_NODE_TYPES

PLACEHOLDER_PATTERN = re.compile(r"__[A-Z0-9_]+__")
BLOCKER_PLACEHOLDERS = {"__FASTGPT_AI_MODEL__"}
WORKFLOW_TOOL_PLACEHOLDER_PATTERN = re.compile(r"__(?:WFT|WORKFLOW_TOOL)_[A-Z0-9_]+__")
DATASET_PLACEHOLDER_PATTERN = re.compile(r"__DATASET_[A-Z0-9_]+__")
DASHBOARD_IMPORT_KEYS = {"nodes", "edges", "chatConfig"}


def is_node_reference_value(value) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], str)
    )


def expected_selected_type_index(value) -> int:
    return 1 if is_node_reference_value(value) else 0


def iter_values(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_values(child)
    else:
        yield value


def value_contains_dataset_placeholder(value) -> bool:
    return any(isinstance(item, str) and DATASET_PLACEHOLDER_PATTERN.search(item) for item in iter_values(value))


def collect_code_nodes(nodes: list[dict]) -> list[dict]:
    code_nodes: list[dict] = []
    for node in nodes:
        if not isinstance(node, dict) or node.get("flowNodeType") != "code":
            continue
        node_id = node.get("nodeId") or "<unknown>"
        inputs = [item for item in node.get("inputs", []) if isinstance(item, dict)]
        input_by_key = {item.get("key"): item for item in inputs}
        code_type = input_by_key.get("codeType", {}).get("value")
        code = input_by_key.get("code", {}).get("value")
        if code_type == "js" and isinstance(code, str) and code.strip():
            code_nodes.append({"nodeId": node_id, "code": code})
    return code_nodes


def validate_js_code_nodes(nodes: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    code_nodes = collect_code_nodes(nodes)
    if not code_nodes:
        return errors, warnings

    if not shutil.which("node"):
        warnings.append("Node.js not found; skipped JS syntax validation for code nodes")
        return errors, warnings

    checker = r'''
const fs = require('fs');
const vm = require('vm');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const errors = [];
for (const item of payload) {
  try {
    new vm.Script(item.code, { filename: `${item.nodeId}.js` });
  } catch (error) {
    errors.push({ nodeId: item.nodeId, message: error && error.message ? error.message : String(error) });
  }
}
process.stdout.write(JSON.stringify(errors));
process.exit(errors.length ? 1 : 0);
'''
    result = subprocess.run(
        ["node", "-e", checker],
        input=json.dumps(code_nodes, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.stdout.strip():
        try:
            node_errors = json.loads(result.stdout)
        except json.JSONDecodeError:
            node_errors = []
            errors.append(f"JS syntax validator returned non-JSON output: {result.stdout.strip()}")
        for item in node_errors:
            errors.append(f"code node JS syntax error on {item.get('nodeId')}: {item.get('message')}")
    if result.returncode not in (0, 1):
        errors.append(f"JS syntax validator failed: {result.stderr.strip() or result.returncode}")
    return errors, warnings


def validate_code_node_runtime_inputs(nodes: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    generation_static_keys = {"governanceSnapshot", "datasetManifest"}
    for node in nodes:
        if not isinstance(node, dict) or node.get("flowNodeType") != "code":
            continue
        node_id = node.get("nodeId") or "<unknown>"
        for item in node.get("inputs", []):
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            if key in {"system_addInputParam", "codeType", "code"}:
                continue
            render_types = item.get("renderTypeList") if isinstance(item.get("renderTypeList"), list) else []
            value_type = item.get("valueType")
            if key in generation_static_keys:
                errors.append(
                    f"code node {node_id} depends on generation-time static input {key}; "
                    "compile it into the JS code instead of passing a hidden runtime object"
                )
            if "hidden" in render_types and value_type in {"object", "arrayObject", "arrayAny", "any"}:
                errors.append(
                    f"code node {node_id} has hidden structured runtime input {key}; "
                    "FastGPT may drop or coerce hidden object inputs at runtime"
                )
            if item.get("renderTypeList") == ["input"] and value_type in {"object", "arrayObject", "arrayAny", "any"}:
                warnings.append(
                    f"code node {node_id} has literal structured input {key}; "
                    "verify it is not static generation data better compiled into code"
                )
    return errors, warnings


def validate_dashboard_import_shape(workflow: dict) -> list[str]:
    if not isinstance(workflow, dict):
        return ["Top-level JSON must be an object"]

    errors: list[str] = []
    keys = set(workflow.keys())
    sorted_keys = sorted(keys)

    if "workflow" in keys:
        errors.append(
            "Detected top-level `workflow` wrapper. FastGPT page import requires the inner "
            "dashboard workflow JSON with top-level nodes, edges, chatConfig; use this wrapper "
            "only for OpenAPI/create or development packaging."
        )
    if "template" in keys:
        errors.append(
            "Detected top-level `template` wrapper. Do not deliver template/development wrappers "
            "as page-import files; unwrap to top-level nodes, edges, chatConfig."
        )
    if "modules" in keys:
        errors.append(
            "Detected top-level `modules`, which indicates an OpenAPI/create-style payload. "
            "FastGPT page import requires top-level nodes, edges, chatConfig."
        )
    if ({"name", "type"} & keys) and not DASHBOARD_IMPORT_KEYS.issubset(keys):
        errors.append(
            "Detected app metadata without dashboard workflow keys. `name`/`type` belong to "
            "OpenAPI/create or template packaging, not the page-import JSON."
        )
    if keys != DASHBOARD_IMPORT_KEYS:
        errors.append(f"Top-level keys must be exactly chatConfig, edges, nodes (got: {sorted_keys})")
    return errors


def validate_placeholders(workflow: dict, nodes: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    raw = json.dumps(workflow, ensure_ascii=False)
    placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(raw)))
    if not placeholders:
        return errors, warnings

    for marker in placeholders:
        if marker in BLOCKER_PLACEHOLDERS or WORKFLOW_TOOL_PLACEHOLDER_PATTERN.fullmatch(marker):
            errors.append(f"Unresolved blocker placeholder: {marker}")

    dataset_placeholders_in_search = set()
    for node in nodes:
        if not isinstance(node, dict) or node.get("flowNodeType") != "datasetSearchNode":
            continue
        for item in node.get("inputs", []):
            if not isinstance(item, dict) or item.get("key") != "datasets":
                continue
            value = item.get("value")
            if value_contains_dataset_placeholder(value):
                dataset_placeholders_in_search.update(DATASET_PLACEHOLDER_PATTERN.findall(json.dumps(value, ensure_ascii=False)))
    for marker in sorted(dataset_placeholders_in_search):
        errors.append(f"Unresolved dataset placeholder used by datasetSearchNode: {marker}")

    warning_markers = []
    for marker in placeholders:
        if marker in BLOCKER_PLACEHOLDERS or WORKFLOW_TOOL_PLACEHOLDER_PATTERN.fullmatch(marker):
            continue
        if marker in dataset_placeholders_in_search:
            continue
        warning_markers.append(marker)
    if warning_markers:
        warnings.append("Unresolved non-blocker placeholders: " + ", ".join(warning_markers))
    return errors, warnings


def validate(workflow: dict, require_strings: list[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(workflow, dict):
        return ["Top-level JSON must be an object"], warnings

    errors.extend(validate_dashboard_import_shape(workflow))

    nodes = workflow.get("nodes")
    edges = workflow.get("edges")
    chat_config = workflow.get("chatConfig")

    if not isinstance(nodes, list):
        errors.append("nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        edges = []
    if not isinstance(chat_config, dict):
        errors.append("chatConfig must be an object")
        chat_config = {}

    node_ids = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue
        node_id = node.get("nodeId")
        node_type = node.get("flowNodeType")
        if not isinstance(node_id, str) or not node_id:
            errors.append(f"nodes[{index}] missing valid nodeId")
        elif node_id in node_ids:
            errors.append(f"Duplicate nodeId: {node_id}")
        else:
            node_ids.add(node_id)
        if node_type not in ALLOWED_WORKFLOW_NODE_TYPES:
            errors.append(f"nodes[{index}] has unsupported flowNodeType: {node_type}")

    for key in chat_config:
        if key not in ALLOWED_CHATCONFIG_KEYS:
            errors.append(f"chatConfig contains unsupported key: {key}")

    has_plugin_input = any(
        isinstance(node, dict) and node.get("flowNodeType") == "pluginInput" for node in nodes
    )
    has_plugin_output = any(
        isinstance(node, dict) and node.get("flowNodeType") == "pluginOutput" for node in nodes
    )
    if has_plugin_input != has_plugin_output:
        errors.append("workflow tool JSON must include both pluginInput and pluginOutput")

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("nodeId")
        if node.get("flowNodeType") == "pluginInput":
            input_keys = [item.get("key") for item in node.get("inputs", []) if isinstance(item, dict)]
            output_keys = [item.get("key") for item in node.get("outputs", []) if isinstance(item, dict)]
            if input_keys != output_keys:
                errors.append(
                    f"pluginInput must mirror inputs as same-name outputs for internal references: {node_id}"
                )
        if node.get("flowNodeType") == "datasetSearchNode":
            inputs = [item for item in node.get("inputs", []) if isinstance(item, dict)]
            input_keys = [item.get("key") for item in inputs]
            input_by_key = {item.get("key"): item for item in inputs}
            if "datasets" not in input_keys:
                errors.append(f"datasetSearchNode missing current FastGPT datasets input: {node_id}")
            if "selectDataset" in input_keys:
                errors.append(f"datasetSearchNode uses legacy selectDataset input key: {node_id}")
            for key in ("datasets", "collectionFilterMatch"):
                input_item = input_by_key.get(key)
                if not input_item or "selectedTypeIndex" not in input_item:
                    continue
                expected_index = expected_selected_type_index(input_item.get("value"))
                if input_item.get("selectedTypeIndex") != expected_index:
                    errors.append(
                        f"datasetSearchNode {key} selectedTypeIndex mismatch on {node_id}: "
                        f"expected {expected_index}, got {input_item.get('selectedTypeIndex')}"
                    )

    js_errors, js_warnings = validate_js_code_nodes(nodes)
    errors.extend(js_errors)
    warnings.extend(js_warnings)

    code_input_errors, code_input_warnings = validate_code_node_runtime_inputs(nodes)
    errors.extend(code_input_errors)
    warnings.extend(code_input_warnings)

    placeholder_errors, placeholder_warnings = validate_placeholders(workflow, nodes)
    errors.extend(placeholder_errors)
    warnings.extend(placeholder_warnings)

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edges[{index}] must be an object")
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids:
            errors.append(f"edges[{index}] source missing from node set: {source}")
        if target not in node_ids:
            errors.append(f"edges[{index}] target missing from node set: {target}")

    raw = json.dumps(workflow, ensure_ascii=False)
    for marker in require_strings:
        if marker not in raw:
            errors.append(f"Required marker not found: {marker}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a FastGPT workflow JSON against the shared baseline contract.")
    parser.add_argument("workflow", help="Path to workflow JSON")
    parser.add_argument("--require-string", action="append", default=[], help="String marker that must appear in the JSON")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    path = Path(args.workflow)
    workflow = json.loads(path.read_text(encoding="utf-8-sig"))
    errors, warnings = validate(workflow, args.require_string)
    result = {
        "workflow": str(path),
        "valid": len(errors) == 0,
        "nodeCount": len(workflow.get("nodes", [])) if isinstance(workflow, dict) else 0,
        "edgeCount": len(workflow.get("edges", [])) if isinstance(workflow, dict) else 0,
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"workflow: {path}")
        print(f"valid: {result['valid']}")
        print(f"nodes: {result['nodeCount']}")
        print(f"edges: {result['edgeCount']}")
        if errors:
            print("errors:")
            for error in errors:
                print(f"- {error}")
        if warnings:
            print("warnings:")
            for warning in warnings:
                print(f"- {warning}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
