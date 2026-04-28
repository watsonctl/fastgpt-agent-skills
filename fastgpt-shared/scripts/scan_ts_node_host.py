#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


def detect(repo: Path):
    package_json = read_json(repo / "package.json")
    deps = {
        **package_json.get("dependencies", {}),
        **package_json.get("devDependencies", {}),
    }
    scripts = package_json.get("scripts", {}) if isinstance(package_json, dict) else {}

    app_api = repo / "app" / "api"
    pages_api = repo / "pages" / "api"
    route_style = "app-router" if app_api.exists() else "pages-api" if pages_api.exists() else "unknown"

    framework = []
    if "next" in deps:
        framework.append("nextjs")
    if "typescript" in deps or (repo / "tsconfig.json").exists():
        framework.append("typescript")
    if not framework:
        framework.append("node")

    route_files = list(app_api.rglob("route.ts"))[:40] if app_api.exists() else list(pages_api.rglob("*.ts"))[:40]
    auth_candidates = []
    verify_candidates = []
    for file in route_files:
        text = file.read_text(errors="ignore")
        if "auth()" in text or "await auth()" in text or "import { auth }" in text:
            auth_candidates.append(str(file))
        if "verifyApiKey" in text:
            verify_candidates.append(str(file))

    validation = "zod" if "zod" in deps else "unknown"
    test_runner = "vitest" if "vitest" in deps else "jest" if "jest" in deps else "unknown"
    mock_style = "vi.mock" if test_runner == "vitest" else "jest.mock" if test_runner == "jest" else "unknown"

    tsconfig = read_json(repo / "tsconfig.json")
    alias_detected = "@/*" in (((tsconfig.get("compilerOptions") or {}).get("paths") or {}))

    script_dirs = [str(path) for path in [repo / "scripts", repo / "scripts" / "fastgpt"] if path.exists()]

    return {
        "repo": str(repo),
        "framework": framework,
        "routeStyle": route_style,
        "appApiExists": app_api.exists(),
        "pagesApiExists": pages_api.exists(),
        "validationLibrary": validation,
        "testRunner": test_runner,
        "mockStyle": mock_style,
        "pathAliasAt": alias_detected,
        "scriptDirs": script_dirs,
        "authRouteExamples": auth_candidates[:5],
        "apiKeyFallbackExamples": verify_candidates[:5],
        "recommended": {
            "helperRouteRoot": "app/api/rag-helper" if app_api.exists() else "pages/api/rag-helper" if pages_api.exists() else "<detect manually>",
            "testRoot": "__tests__/app/api/rag-helper" if test_runner == "vitest" else "<match repo>",
            "generatorScriptDir": "scripts/fastgpt" if (repo / "scripts").exists() else "scripts",
        },
    }


def render_markdown(result: dict) -> str:
    return "\n".join([
        f"# TS/Node host scan — {result['repo']}",
        "",
        f"- framework: {', '.join(result['framework'])}",
        f"- route style: {result['routeStyle']}",
        f"- validation: {result['validationLibrary']}",
        f"- test runner: {result['testRunner']}",
        f"- mock style: {result['mockStyle']}",
        f"- path alias @/* detected: {result['pathAliasAt']}",
        "",
        "## Recommended locations",
        f"- helper routes: {result['recommended']['helperRouteRoot']}",
        f"- helper tests: {result['recommended']['testRoot']}",
        f"- generator scripts: {result['recommended']['generatorScriptDir']}",
        "",
        "## Auth route examples",
        *([f"- {item}" for item in result['authRouteExamples']] or ["- none found"]),
        "",
        "## API key fallback examples",
        *([f"- {item}" for item in result['apiKeyFallbackExamples']] or ["- none found"]),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a TS/Node repo for FastGPT host-adapter conventions.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    result = detect(Path(args.repo).resolve())
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
