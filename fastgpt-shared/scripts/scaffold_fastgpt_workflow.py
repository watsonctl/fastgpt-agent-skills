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


def make_ref_input(key, value_type, value, label=None, required=True):
    return {
        "key": key,
        "valueType": value_type,
        "label": label or key,
        "renderTypeList": ["reference"],
        "description": "",
        "canEdit": True,
        "required": required,
        "editField": {"key": True, "valueType": True},
        "value": value,
    }


def make_code_node(node_id, name, x, y, code, inputs=None, outputs=None, parent=None):
    node = make_node(
        node_id,
        name,
        "code",
        x,
        y,
        intro="Generated scaffold code node; replace code and outputs before production use.",
        inputs=[
            {
                "key": "system_addInputParam",
                "renderTypeList": ["addInputParam"],
                "valueType": "dynamic",
                "label": "",
                "required": False,
                "description": "Dynamic Input",
                "editField": {"key": True, "valueType": True},
            },
            *(inputs or []),
            {"key": "codeType", "renderTypeList": ["hidden"], "label": "", "value": "js"},
            {"key": "code", "renderTypeList": ["custom"], "label": "", "value": code},
        ],
        outputs=[
            {
                "id": "system_addOutputParam",
                "key": "system_addOutputParam",
                "type": "dynamic",
                "valueType": "dynamic",
                "label": "",
                "editField": {"key": True, "valueType": True},
                "description": "Return object fields are available as dynamic outputs",
            },
            {"id": "system_rawResponse", "key": "system_rawResponse", "label": "Raw response", "valueType": "object", "type": "static"},
            {"id": "error", "key": "error", "label": "Error", "valueType": "object", "type": "static"},
            *(outputs or []),
        ],
    )
    node["avatar"] = "/imgs/workflow/code.svg"
    node["version"] = "482"
    node["showStatus"] = True
    if parent:
        node["parentNodeId"] = parent
    return node


def make_loop_start(node_id, x, y, parent):
    node = make_node(
        node_id,
        "开始",
        "loopStart",
        x,
        y,
        intro="Container-internal fixed start anchor. Do not replace with parent.currentItem references.",
        inputs=[
            {"key": "loopStartInput", "renderTypeList": ["hidden"], "valueType": "any", "label": "", "required": True, "value": ""},
            {"key": "loopStartIndex", "renderTypeList": ["hidden"], "valueType": "number", "label": "数组元素索引"},
        ],
        outputs=[
            {"id": "loopStartInput", "key": "loopStartInput", "label": "当前数组项", "type": "static", "valueType": "any", "description": ""},
            {"id": "loopStartIndex", "key": "loopStartIndex", "label": "数组元素索引", "type": "static", "valueType": "number", "description": ""},
        ],
    )
    node["avatar"] = "core/workflow/template/loopStart"
    node["version"] = "481"
    node["showStatus"] = False
    node["parentNodeId"] = parent
    return node


def make_loop_end(node_id, x, y, parent, output_ref):
    node = make_node(
        node_id,
        "结束",
        "loopEnd",
        x,
        y,
        intro="Container-internal fixed end anchor.",
        inputs=[
            {
                "key": "loopEndInput",
                "renderTypeList": ["reference"],
                "valueType": "any",
                "label": "",
                "required": True,
                "value": output_ref,
            }
        ],
        outputs=[],
    )
    node["avatar"] = "core/workflow/template/loopEnd"
    node["version"] = "481"
    node["showStatus"] = False
    node["parentNodeId"] = parent
    return node


def make_container(node_id, name, node_type, x, y, array_ref, children, concurrency=None, retries=None):
    inputs = [
        {
            "key": "loopInputArray",
            "renderTypeList": ["reference"],
            "valueType": "arrayAny",
            "label": "数组",
            "required": True,
            "value": array_ref,
            "debugLabel": "",
            "toolDescription": "",
        }
    ]
    if node_type == "parallelRun":
        inputs.extend(
            [
                {
                    "key": "parallelRunMaxConcurrency",
                    "renderTypeList": ["numberInput"],
                    "valueType": "number",
                    "label": "最大并发数",
                    "required": True,
                    "min": 1,
                    "value": concurrency or 3,
                },
                {
                    "key": "parallelRunMaxRetryTimes",
                    "renderTypeList": ["numberInput"],
                    "valueType": "number",
                    "label": "单轮报错重试次数",
                    "required": True,
                    "min": 0,
                    "max": 5,
                    "value": retries if retries is not None else 1,
                },
            ]
        )
    inputs.extend(
        [
            {"key": "childrenNodeIdList", "renderTypeList": ["hidden"], "valueType": "arrayString", "label": "", "value": children},
            {"key": "nodeWidth", "renderTypeList": ["hidden"], "valueType": "number", "label": "", "value": 900},
            {"key": "nodeHeight", "renderTypeList": ["hidden"], "valueType": "number", "label": "", "value": 500},
            {"key": "loopNodeInputHeight", "renderTypeList": ["hidden"], "valueType": "number", "label": "", "value": 320},
        ]
    )
    outputs = (
        [
            {"id": "parallelSuccessResults", "valueType": "arrayAny", "type": "static", "key": "parallelSuccessResults", "label": "成功结果", "description": ""},
            {"id": "parallelFullResults", "valueType": "arrayObject", "type": "static", "key": "parallelFullResults", "label": "完整结果", "description": ""},
            {"id": "parallelStatus", "valueType": "string", "type": "static", "key": "parallelStatus", "label": "完成状态", "description": ""},
        ]
        if node_type == "parallelRun"
        else [{"id": "loopArray", "valueType": "arrayAny", "type": "static", "key": "loopArray", "label": "循环结果", "description": ""}]
    )
    node = make_node(
        node_id,
        name,
        node_type,
        x,
        y,
        intro="Canonical container scaffold: loopInputArray + loopStart + loopEnd. Clone target exports for production.",
        inputs=inputs,
        outputs=outputs,
    )
    node["avatar"] = f"core/workflow/template/{node_type}"
    node["version"] = "4.14.11" if node_type == "parallelRun" else "481"
    node["showStatus"] = True
    node["childrenNodeIdList"] = children
    return node


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
        prepare_id = "loopPrepareArray"
        loop_id = "loopNode"
        start_id = "loopStart"
        body_id = "loopBody"
        end_id = "loopEnd"
        nodes.append(
            make_code_node(
                prepare_id,
                "准备循环数组",
                x,
                -620,
                "function main(){ return { itemArray: ['alpha', 'beta', 'gamma'] }; }",
                outputs=[{"id": "itemArray", "key": "itemArray", "type": "dynamic", "valueType": "arrayAny", "label": "循环输入数组"}],
            )
        )
        nodes.append(make_container(loop_id, "批量运行占位", "loop", x + 460, -620, [prepare_id, "itemArray"], [start_id, body_id, end_id]))
        nodes.append(make_loop_start(start_id, x + 540, -280, loop_id))
        nodes.append(
            make_code_node(
                body_id,
                "循环体占位",
                x + 820,
                -280,
                "function main({ currentItem, index }){ return { processed: JSON.stringify({ index, currentItem }) }; }",
                inputs=[
                    make_ref_input("currentItem", "any", [start_id, "loopStartInput"]),
                    make_ref_input("index", "number", [start_id, "loopStartIndex"]),
                ],
                outputs=[{"id": "processed", "key": "processed", "type": "dynamic", "valueType": "string", "label": "处理结果JSON"}],
                parent=loop_id,
            )
        )
        nodes.append(make_loop_end(end_id, x + 1160, -280, loop_id, [body_id, "processed"]))
        edges.append(make_edge(last_node, prepare_id))
        edges.append(make_edge(prepare_id, loop_id))
        edges.append(make_edge(start_id, body_id))
        edges.append(make_edge(body_id, end_id))
        last_node = loop_id
        x += 1560
    if "parallel" in patterns:
        prepare_id = "parallelPrepareArray"
        parallel_id = "parallelRun"
        start_id = "parallelStart"
        body_id = "parallelBody"
        end_id = "parallelEnd"
        nodes.append(
            make_code_node(
                prepare_id,
                "准备并行数组",
                x,
                -1180,
                "function main(){ return { itemArray: ['alpha', 'beta', 'gamma'] }; }",
                outputs=[{"id": "itemArray", "key": "itemArray", "type": "dynamic", "valueType": "arrayAny", "label": "并行输入数组"}],
            )
        )
        nodes.append(make_container(parallel_id, "并行执行占位", "parallelRun", x + 460, -1180, [prepare_id, "itemArray"], [start_id, body_id, end_id]))
        nodes.append(make_loop_start(start_id, x + 540, -840, parallel_id))
        nodes.append(
            make_code_node(
                body_id,
                "并行体占位",
                x + 820,
                -840,
                "function main({ currentItem, index }){ return { processed: JSON.stringify({ index, currentItem }) }; }",
                inputs=[
                    make_ref_input("currentItem", "any", [start_id, "loopStartInput"]),
                    make_ref_input("index", "number", [start_id, "loopStartIndex"]),
                ],
                outputs=[{"id": "processed", "key": "processed", "type": "dynamic", "valueType": "string", "label": "处理结果JSON"}],
                parent=parallel_id,
            )
        )
        nodes.append(make_loop_end(end_id, x + 1160, -840, parallel_id, [body_id, "processed"]))
        edges.append(make_edge(last_node, prepare_id))
        edges.append(make_edge(prepare_id, parallel_id))
        edges.append(make_edge(start_id, body_id))
        edges.append(make_edge(body_id, end_id))
        last_node = parallel_id
        x += 1560

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
