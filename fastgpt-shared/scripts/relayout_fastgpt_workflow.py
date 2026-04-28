#!/usr/bin/env python3
import argparse
import json
from collections import defaultdict, deque
from copy import deepcopy
from pathlib import Path

ENGINEERING_STANDARDS_POSITIONS = {
    "userGuide": (-520, -900),
    "workflowStart": (0, 0),
    "normalizeInput": (520, 0),
    "analyzeQuery": (1040, 0),
    "analysisBridge": (1560, 0),
    "directOrRetrieve": (2080, 0),
    "directAnswer": (2600, 640),
    "generalParallel": (2600, -1180),
    "generalStart": (3040, -1180),
    "generalPrepare": (3500, -1180),
    "generalSearch": (3960, -1180),
    "generalEnd": (4420, -1180),
    "flattenGeneral": (5020, -900),
    "precisionLoop": (2600, -520),
    "precisionStart": (3040, -520),
    "precisionLookupReq": (3500, -520),
    "precisionLookup": (3960, -520),
    "precisionPrepareSearch": (4420, -520),
    "precisionSearch": (4880, -520),
    "precisionEnd": (5340, -520),
    "flattenPrecision": (5860, -520),
    "initialDatasetConcat": (6380, 0),
    "prepareVerifier1": (6900, 0),
    "verifier1": (7420, 0),
    "prepareMetadata1": (7940, 0),
    "metadataHttp1": (8460, 0),
    "rankPlan1": (8980, 0),
    "autoRequeryLoop": (9500, -760),
    "autoRequeryStart": (9940, -760),
    "autoLookupReq": (10400, -760),
    "autoLookup": (10860, -760),
    "autoPrepareSearch": (11320, -760),
    "autoSearch": (11780, -760),
    "autoRequeryEnd": (12240, -760),
    "flattenAutoRequery": (12780, -520),
    "combineCandidates2": (13320, 0),
    "prepareVerifier2": (13840, 0),
    "verifier2": (14360, 0),
    "prepareMetadata2": (14880, 0),
    "metadataHttp2": (15400, 0),
    "rankPlan2": (15920, 0),
    "buildFinalContext": (16440, 0),
    "finalAnswer": (16960, 0),
}


def apply_known_profile(workflow: dict) -> dict:
    result = deepcopy(workflow)
    for node in result.get("nodes", []):
        node_id = node.get("nodeId")
        if node_id in ENGINEERING_STANDARDS_POSITIONS:
            x, y = ENGINEERING_STANDARDS_POSITIONS[node_id]
            node["position"] = {"x": x, "y": y}
    return result


def topological_layers(nodes: list[dict], edges: list[dict]) -> list[list[str]]:
    node_ids = [node.get("nodeId") for node in nodes if isinstance(node.get("nodeId"), str)]
    node_set = set(node_ids)
    indegree = {node_id: 0 for node_id in node_ids}
    outgoing = defaultdict(list)
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in node_set and target in node_set:
            outgoing[source].append(target)
            indegree[target] += 1
    queue = deque([node_id for node_id in node_ids if indegree[node_id] == 0])
    depth = {node_id: 0 for node_id in node_ids}
    seen = set()
    while queue:
        current = queue.popleft()
        seen.add(current)
        for target in outgoing[current]:
            depth[target] = max(depth[target], depth[current] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    for node_id in node_ids:
        if node_id not in seen:
            depth[node_id] = max(depth.values() or [0]) + 1
    layers = defaultdict(list)
    for node_id in node_ids:
        layers[depth[node_id]].append(node_id)
    return [layers[index] for index in sorted(layers)]


def apply_generic_swimlane(workflow: dict) -> dict:
    result = deepcopy(workflow)
    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    node_by_id = {node.get("nodeId"): node for node in nodes}
    layers = topological_layers(nodes, edges)
    positions = {}
    layer_gap_x = 520
    node_gap_y = 420
    start_x = 0

    for layer_index, layer in enumerate(layers):
        x = start_x + layer_index * layer_gap_x
        lane_groups = defaultdict(list)
        for node_id in layer:
            node = node_by_id.get(node_id, {})
            parent_id = node.get("parentNodeId")
            flow_type = node.get("flowNodeType")
            if node_id == "userGuide":
                lane = -2
            elif parent_id or flow_type in {"loopStart", "loopEnd"}:
                lane = -1
            elif flow_type in {"loop", "parallelRun"}:
                lane = -1
            elif "direct" in str(node_id).lower() or "fallback" in str(node_id).lower():
                lane = 1
            else:
                lane = 0
            lane_groups[lane].append(node_id)
        for lane, group in lane_groups.items():
            base_y = lane * 620
            total = (len(group) - 1) * node_gap_y
            for index, node_id in enumerate(group):
                positions[node_id] = (x, base_y - total // 2 + index * node_gap_y)

    if "userGuide" in positions:
        positions["userGuide"] = (-520, -900)

    for node in nodes:
        node_id = node.get("nodeId")
        if node_id in positions:
            x, y = positions[node_id]
            node["position"] = {"x": x, "y": y}
    return result


def unchanged_except_positions(before: dict, after: dict) -> bool:
    stripped_before = deepcopy(before)
    stripped_after = deepcopy(after)
    for workflow in (stripped_before, stripped_after):
        for node in workflow.get("nodes", []):
            node.pop("position", None)
    return stripped_before == stripped_after


def main() -> int:
    parser = argparse.ArgumentParser(description="Relayout a FastGPT workflow JSON without changing behavior.")
    parser.add_argument("workflow", help="Input workflow JSON")
    parser.add_argument("--output", help="Output workflow JSON. Defaults to in-place only with --in-place.")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--strategy", choices=["swimlane"], default="swimlane")
    parser.add_argument("--profile", choices=["auto", "engineering-standards"], default="auto")
    parser.add_argument("--check-position-only", action="store_true", default=True)
    args = parser.parse_args()

    input_path = Path(args.workflow)
    workflow = json.loads(input_path.read_text())
    node_ids = {node.get("nodeId") for node in workflow.get("nodes", [])}
    profile = args.profile
    if profile == "auto" and set(ENGINEERING_STANDARDS_POSITIONS).issubset(node_ids):
        profile = "engineering-standards"

    if profile == "engineering-standards":
        relaid = apply_known_profile(workflow)
    else:
        relaid = apply_generic_swimlane(workflow)

    if args.check_position_only and not unchanged_except_positions(workflow, relaid):
        raise SystemExit("Refusing to write: relayout changed fields other than node.position")

    output_path = input_path if args.in_place else Path(args.output) if args.output else None
    if output_path is None:
        raise SystemExit("Provide --output or --in-place")
    output_path.write_text(json.dumps(relaid, ensure_ascii=False, indent=2) + "\n")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
