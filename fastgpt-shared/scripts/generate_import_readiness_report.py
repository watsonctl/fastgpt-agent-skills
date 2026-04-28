#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Optional

from _fastgpt_contracts import LEGACY_HELPER_MARKERS, MCP_CONFIG_MARKERS, MIGRATION_MODES
from validate_fastgpt_workflow import validate
from validate_fastgpt_layout import validate as validate_layout

WORKFLOW_TOOL_PLACEHOLDER_RE = re.compile(r"__WORKFLOW_TOOL_[A-Z0-9_]+__")


def _raw_contains_any(raw: str, markers: set[str]) -> bool:
    lowered = raw.lower()
    return any(marker.lower() in lowered for marker in markers)


def _infer_from_instruction(instruction: str, key: str):
    match = re.search(rf"{re.escape(key)}=([^;\n，。]+)", instruction or "")
    return match.group(1).strip() if match else None


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def readiness(repo: Path, workflow_path: Optional[Path], manifest_path: Optional[Path] = None):
    report = {
        "repo": str(repo),
        "workflow": str(workflow_path) if workflow_path else None,
        "manifest": str(manifest_path) if manifest_path else None,
        "migrationMode": None,
        "bindingMode": None,
        "workflowValid": None,
        "workflowErrors": [],
        "layoutValid": None,
        "layoutWarnings": [],
        "layoutErrors": [],
        "helperFree": None,
        "usesMcp": None,
        "usesWorkflowTools": None,
        "workflowToolCount": 0,
        "workflowToolPlaceholders": [],
        "workflowToolPackagesRequired": [],
        "manualFastgptSetupRequired": None,
        "helperRoutesDetected": [],
        "generatorScriptsDetected": [],
        "status": "warn",
    }

    manifest = None
    if manifest_path and manifest_path.exists():
        manifest = _load_json(manifest_path)
        report["migrationMode"] = manifest.get("migrationMode")
        report["bindingMode"] = manifest.get("bindingMode")
        report["usesWorkflowTools"] = manifest.get("usesWorkflowTools")
        report["workflowToolCount"] = int(manifest.get("workflowToolCount") or 0)
        report["workflowToolPackagesRequired"] = manifest.get("workflowToolPackagesRequired") or []

    raw = ""
    workflow = None
    if workflow_path and workflow_path.exists():
        workflow = _load_json(workflow_path)
        errors, warnings = validate(workflow, [])
        report["workflowValid"] = len(errors) == 0
        report["workflowErrors"] = errors
        if warnings:
            report.setdefault("workflowWarnings", warnings)
        layout_errors, layout_warnings = validate_layout(workflow)
        report["layoutValid"] = len(layout_errors) == 0
        report["layoutErrors"] = layout_errors
        report["layoutWarnings"] = layout_warnings
        raw = json.dumps(workflow, ensure_ascii=False)

        instruction = str((workflow.get("chatConfig") or {}).get("instruction") or "")
        workflow_binding_mode = _infer_from_instruction(instruction, "bindingMode")
        report["migrationMode"] = report["migrationMode"] or _infer_from_instruction(instruction, "migrationMode")
        report["bindingMode"] = "bound" if workflow_binding_mode == "bound" else (report["bindingMode"] or workflow_binding_mode)
        nodes = [node for node in workflow.get("nodes", []) if isinstance(node, dict)]
        flow_types = [node.get("flowNodeType") for node in nodes]
        plugin_ids = sorted(
            {
                str(node.get("pluginId"))
                for node in nodes
                if node.get("flowNodeType") == "pluginModule" and node.get("pluginId")
            }
        )
        report["usesWorkflowTools"] = report["usesWorkflowTools"] if report["usesWorkflowTools"] is not None else ("pluginModule" in flow_types or "pluginInput" in flow_types)
        report["workflowToolCount"] = report["workflowToolCount"] or len(plugin_ids)
        report["workflowToolPlaceholders"] = sorted(set(WORKFLOW_TOOL_PLACEHOLDER_RE.findall(raw)))
        report["helperFree"] = not _raw_contains_any(raw, LEGACY_HELPER_MARKERS)
        report["usesMcp"] = _raw_contains_any(raw, MCP_CONFIG_MARKERS)
    else:
        report["workflowErrors"].append("workflow file missing or not provided")

    for path in (repo / "app" / "api").rglob("route.ts") if (repo / "app" / "api").exists() else []:
        if "rag-helper" in str(path):
            report["helperRoutesDetected"].append(str(path))
    for path in (repo / "scripts").rglob("*") if (repo / "scripts").exists() else []:
        if path.is_file() and "fastgpt" in str(path).lower():
            report["generatorScriptsDetected"].append(str(path))

    mode = report.get("migrationMode")
    binding_mode = report.get("bindingMode")
    report["manualFastgptSetupRequired"] = bool(
        report["workflowToolPlaceholders"]
        and binding_mode not in {"by-name-script", "tool-bindings.json", "bound"}
    )

    blocked = False
    if report["workflowValid"] is False or report["layoutValid"] is False:
        blocked = True
    if mode in {"workflow-only", "workflow+workflow-tools"}:
        if report["helperFree"] is False or report["usesMcp"] is True:
            blocked = True
    if mode and mode not in MIGRATION_MODES:
        report["workflowErrors"].append(f"unsupported migrationMode: {mode}")
        blocked = True

    if blocked:
        report["status"] = "blocked"
    elif report["workflowValid"]:
        if report["workflowToolPlaceholders"]:
            report["status"] = "ready-after-binding"
        else:
            report["status"] = "ready"
    return report


def render_markdown(report: dict) -> str:
    lines = [
        f"# Import readiness — {report['repo']}",
        "",
        f"- workflow: {report['workflow']}",
        f"- manifest: {report['manifest']}",
        f"- migrationMode: {report['migrationMode']}",
        f"- bindingMode: {report['bindingMode']}",
        f"- workflow valid: {report['workflowValid']}",
        f"- layout valid: {report['layoutValid']}",
        f"- helperFree: {report['helperFree']}",
        f"- usesMcp: {report['usesMcp']}",
        f"- usesWorkflowTools: {report['usesWorkflowTools']}",
        f"- workflowToolCount: {report['workflowToolCount']}",
        f"- manualFastgptSetupRequired: {report['manualFastgptSetupRequired']}",
        f"- status: {report['status']}",
        "",
        "## Workflow tool placeholders",
        *([f"- {item}" for item in report["workflowToolPlaceholders"]] or ["- none"]),
        "",
        "## Helper routes detected in repo (legacy/exception references)",
        *([f"- {item}" for item in report["helperRoutesDetected"]] or ["- none"]),
        "",
        "## Generator scripts detected",
        *([f"- {item}" for item in report["generatorScriptsDetected"]] or ["- none"]),
    ]
    if report["workflowErrors"]:
        lines.extend(["", "## Workflow errors", *[f"- {item}" for item in report["workflowErrors"]]])
    if report["layoutErrors"]:
        lines.extend(["", "## Layout errors", *[f"- {item}" for item in report["layoutErrors"]]])
    if report["layoutWarnings"]:
        lines.extend(["", "## Layout warnings", *[f"- {item}" for item in report["layoutWarnings"][:20]]])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an import-readiness report for a FastGPT workflow or workflow-tool bundle.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--workflow")
    parser.add_argument("--manifest")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    workflow_path = Path(args.workflow).resolve() if args.workflow else None
    manifest_path = Path(args.manifest).resolve() if args.manifest else None
    report = readiness(repo, workflow_path, manifest_path)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0 if report["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
