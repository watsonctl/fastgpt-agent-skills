#!/usr/bin/env python3
import argparse
import json
from copy import deepcopy
from pathlib import Path

from _fastgpt_contracts import ALLOWED_CHATCONFIG_KEYS, ALLOWED_WORKFLOW_NODE_TYPES

ASSET_PATH = Path(__file__).resolve().parent.parent / "assets" / "workflow-skeleton.json"


def pos(x, y):
    return {"x": x, "y": y}


def make_edge(source, target):
    return {
        "source": source,
        "target": target,
        "sourceHandle": f"{source}-source-right",
        "targetHandle": f"{target}-target-left",
    }


def make_node(node_id, name, node_type, x, y, intro="", inputs=None, outputs=None):
    return {
        "nodeId": node_id,
        "name": name,
        "intro": intro,
        "avatar": f"custom/{node_type}",
        "flowNodeType": node_type,
        "position": pos(x, y),
        "version": "latest",
        "inputs": inputs or [],
        "outputs": outputs or [],
    }


def parse_variables(raw: str):
    variables = []
    for item in [part.strip() for part in raw.split(",") if part.strip()]:
        if ":" in item:
            key, value_type = item.split(":", 1)
        else:
            key, value_type = item, "string"
        key = key.strip()
        value_type = value_type.strip() or "string"
        variables.append({
            "required": False,
            "list": [{"label": "", "value": ""}],
            "enums": [{"label": "", "value": ""}],
            "id": f"{key}_var",
            "key": key,
            "label": key,
            "type": "input" if value_type != "any" else "custom",
            "description": f"Generated variable: {key}",
            "valueType": value_type,
            "defaultValue": [] if value_type == "any" else "",
        })
    return variables


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a starter FastGPT workflow JSON.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--bundle-dir", help="Optional directory for a multi-JSON bundle with workflow tools.")
    parser.add_argument(
        "--migration-mode",
        choices=["workflow-only", "workflow+workflow-tools", "exception-helper-approved"],
        default="workflow-only",
    )
    parser.add_argument("--variables", default="industry:string,datasetId:any")
    parser.add_argument("--patterns", default="direct-answer,dataset-search")
    parser.add_argument("--welcome-text", default="Describe the target behavior and variables before import.")
    args = parser.parse_args()

    workflow = json.loads(ASSET_PATH.read_text())
    workflow["chatConfig"]["welcomeText"] = args.welcome_text
    workflow["chatConfig"]["instruction"] = f"Generated scaffold for: {args.title}; migrationMode={args.migration_mode}"
    workflow["chatConfig"]["variables"] = parse_variables(args.variables)

    nodes = workflow["nodes"]
    edges = workflow["edges"]
    patterns = {item.strip() for item in args.patterns.split(",") if item.strip()}

    # Swimlane-first scaffold: main path at y=0, retrieval at y=-620, direct/fallback at y=640.
    for node in nodes:
        if node.get("nodeId") == "userGuide":
            node["position"] = pos(-520, -900)
        if node.get("nodeId") == "workflowStart":
            node["position"] = pos(0, 0)

    last_node = "workflowStart"
    x = 560
    if "direct-answer" in patterns:
        nodes.append(make_node("directAnswer", "直接回答占位", "chatNode", x, 640, "Replace with direct-answer prompt / behavior"))
        edges.append(make_edge(last_node, "directAnswer"))
        last_node = "directAnswer"
        x += 520
    if "dataset-search" in patterns:
        nodes.append(make_node("datasetSearch", "知识库检索占位", "datasetSearchNode", x, -620, "Replace with dataset search config"))
        nodes.append(make_node("datasetConcat", "引用合并占位", "datasetConcatNode", x + 560, 0, "Replace with quote merge logic"))
        edges.append(make_edge(last_node, "datasetSearch"))
        edges.append(make_edge("datasetSearch", "datasetConcat"))
        last_node = "datasetConcat"
        x += 1120
    if "http-helper" in patterns:
        if args.migration_mode != "exception-helper-approved":
            raise SystemExit("http-helper pattern requires --migration-mode exception-helper-approved")
        nodes.append(make_node("httpHelper", "HTTP Helper 占位", "httpRequest468", x, -620, "Replace with narrow helper endpoint"))
        edges.append(make_edge(last_node, "httpHelper"))
        last_node = "httpHelper"
        x += 520
    if "workflow-tool" in patterns:
        nodes.append(make_node("workflowToolRef", "工作流工具引用占位", "pluginModule", x, -620, "Bind pluginId to workflow tool appId"))
        nodes[-1]["pluginId"] = "__WORKFLOW_TOOL_EXAMPLE__"
        edges.append(make_edge(last_node, "workflowToolRef"))
        last_node = "workflowToolRef"
        x += 520
    if "loop" in patterns:
        nodes.append(make_node("loopNode", "批量运行占位", "loop", x, -620, "Replace with sequential item processing"))
        nodes.append(make_node("loopStart", "循环开始", "loopStart", x + 520, -620))
        nodes.append(make_node("loopEnd", "循环结束", "loopEnd", x + 1040, -620))
        edges.append(make_edge(last_node, "loopNode"))
        edges.append(make_edge("loopNode", "loopStart"))
        edges.append(make_edge("loopStart", "loopEnd"))
        last_node = "loopEnd"
        x += 1560
    if "parallel" in patterns:
        nodes.append(make_node("parallelRun", "并行执行占位", "parallelRun", x, -1180, "Replace with independent fan-out logic"))
        edges.append(make_edge(last_node, "parallelRun"))
        last_node = "parallelRun"
        x += 520

    nodes.append(make_node("finalAnswer", "最终回答占位", "chatNode", x, 0, "Replace with final synthesis / fallback prompt"))
    edges.append(make_edge(last_node, "finalAnswer"))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
    print(output)

    if args.bundle_dir and "workflow-tool" in patterns:
        bundle_dir = Path(args.bundle_dir)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        tool_workflow = {
            "nodes": [
                make_node("pluginConfig", "工具配置", "pluginConfig", -260, -120),
                make_node("pluginInput", "工作流工具输入", "pluginInput", 0, 0),
                make_node("toolLogic", "工具逻辑占位", "code", 420, 0),
                make_node("pluginOutput", "工作流工具输出", "pluginOutput", 840, 0),
            ],
            "edges": [make_edge("pluginInput", "toolLogic"), make_edge("toolLogic", "pluginOutput")],
            "chatConfig": {"instruction": f"workflowTool scaffold for: {args.title}"},
        }
        tool_path = bundle_dir / "workflow-tool-example.json"
        manifest_path = bundle_dir / "workflow-bundle.manifest.json"
        tool_path.write_text(json.dumps(tool_workflow, ensure_ascii=False, indent=2) + "\n")
        manifest_path.write_text(
            json.dumps(
                {
                    "migrationMode": "workflow+workflow-tools",
                    "usesWorkflowTools": True,
                    "workflowToolCount": 1,
                    "bindingMode": "by-name-script",
                    "workflowTools": [
                        {
                            "name": "workflow-tool-example",
                            "file": str(tool_path),
                            "type": "workflowTool",
                            "placeholderToolId": "__WORKFLOW_TOOL_EXAMPLE__",
                            "toolIdField": "pluginId",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        print(tool_path)
        print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
