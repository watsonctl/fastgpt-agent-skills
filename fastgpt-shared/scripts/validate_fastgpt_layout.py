#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

APPROX_WIDTH = {
    "chatNode": 360,
    "code": 360,
    "httpRequest468": 340,
    "datasetSearchNode": 360,
    "datasetConcatNode": 300,
    "ifElseNode": 300,
    "loop": 360,
    "parallelRun": 360,
    "loopStart": 220,
    "loopEnd": 220,
    "workflowStart": 260,
    "userGuide": 260,
}
APPROX_HEIGHT = {
    "chatNode": 420,
    "code": 420,
    "httpRequest468": 360,
    "datasetSearchNode": 420,
    "datasetConcatNode": 300,
    "ifElseNode": 280,
    "loop": 300,
    "parallelRun": 300,
    "loopStart": 160,
    "loopEnd": 160,
    "workflowStart": 220,
    "userGuide": 220,
}


def rect(node):
    pos = node.get("position") or {}
    x = float(pos.get("x", 0))
    y = float(pos.get("y", 0))
    flow = node.get("flowNodeType")
    width = APPROX_WIDTH.get(flow, 340)
    height = APPROX_HEIGHT.get(flow, 320)
    return (x, y, x + width, y + height)


def overlap(a, b, padding_x, padding_y):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 + padding_x <= bx1 or bx2 + padding_x <= ax1 or ay2 + padding_y <= by1 or by2 + padding_y <= ay1)


def validate(workflow, min_gap_x=80, min_gap_y=80):
    errors = []
    warnings = []
    nodes = workflow.get("nodes", [])
    node_by_id = {node.get("nodeId"): node for node in nodes}

    for node in nodes:
        pos = node.get("position")
        if not isinstance(pos, dict) or not isinstance(pos.get("x"), (int, float)) or not isinstance(pos.get("y"), (int, float)):
            errors.append(f"node {node.get('nodeId')} has invalid position")

    for i, left in enumerate(nodes):
        for right in nodes[i + 1:]:
            if left.get("parentNodeId") != right.get("parentNodeId"):
                continue
            if overlap(rect(left), rect(right), min_gap_x, min_gap_y):
                warnings.append(f"possible overlap in same lane/parent: {left.get('nodeId')} <-> {right.get('nodeId')}")

    for edge in workflow.get("edges", []):
        source = node_by_id.get(edge.get("source"))
        target = node_by_id.get(edge.get("target"))
        if not source or not target:
            continue
        sx = (source.get("position") or {}).get("x", 0)
        tx = (target.get("position") or {}).get("x", 0)
        if tx < sx - 40:
            warnings.append(f"edge flows backward: {edge.get('source')} -> {edge.get('target')}")

    parent_ids = {node.get("nodeId") for node in nodes if node.get("flowNodeType") in {"loop", "parallelRun"}}
    for node in nodes:
        parent = node.get("parentNodeId")
        if parent in parent_ids:
            parent_node = node_by_id.get(parent)
            if parent_node:
                py = (parent_node.get("position") or {}).get("y", 0)
                cy = (node.get("position") or {}).get("y", 0)
                if abs(cy - py) > 260:
                    warnings.append(f"child far from parent lane: {node.get('nodeId')} parent={parent}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate visual readability of a FastGPT workflow JSON.")
    parser.add_argument("workflow")
    parser.add_argument("--strategy", choices=["swimlane"], default="swimlane")
    parser.add_argument("--min-gap-x", type=int, default=80)
    parser.add_argument("--min-gap-y", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.workflow)
    workflow = json.loads(path.read_text())
    errors, warnings = validate(workflow, args.min_gap_x, args.min_gap_y)
    result = {
        "workflow": str(path),
        "valid": not errors,
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"workflow: {path}")
        print(f"valid: {result['valid']}")
        print(f"warnings: {len(warnings)}")
        if errors:
            print("errors:")
            for item in errors:
                print(f"- {item}")
        if warnings:
            print("warnings:")
            for item in warnings[:40]:
                print(f"- {item}")
            if len(warnings) > 40:
                print(f"... {len(warnings) - 40} more warnings")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
