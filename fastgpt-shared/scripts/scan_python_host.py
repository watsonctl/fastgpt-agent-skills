#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

PATTERNS = {
    "fastapi": ["fastapi", "APIRouter", "@app.post", "@router.post", "FastAPI("],
    "flask": ["flask", "Blueprint", "@app.route", "Flask("],
    "django": ["django", "APIView", "ViewSet", "serializers.Serializer", "serializers.ModelSerializer"],
    "pydantic": ["BaseModel", "pydantic", "Field(", "model_validate"],
    "langchain": ["langchain", "Runnable", "AgentExecutor", "@tool", "StructuredTool"],
    "llamaindex": ["llama_index", "QueryEngine", "VectorStoreIndex", "Retriever"],
    "celery_rq": ["celery", "@shared_task", "Celery(", "rq.Queue", "from rq"],
    "pytest": ["pytest", "TestClient", "def test_", "pytest.fixture"],
    "external_http": ["requests.", "httpx.", "aiohttp", "urllib.request"],
    "rag": ["retriever", "vectorstore", "embedding", "similarity_search", "query_engine"],
}

SEARCH_GLOBS = ["*.py", "**/*.py", "pyproject.toml", "requirements*.txt", "setup.cfg"]


def rg_list(repo: Path, pattern: str) -> list[str]:
    cmd = ["rg", "-l", "-F", pattern, str(repo)]
    for glob in SEARCH_GLOBS:
        cmd.extend(["-g", glob])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"rg failed for pattern: {pattern}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def scan(repo: Path) -> dict:
    categories = {key: [] for key in PATTERNS}
    for category, patterns in PATTERNS.items():
        seen = set()
        for pattern in patterns:
            for path in rg_list(repo, pattern):
                if path not in seen:
                    seen.add(path)
                    categories[category].append(path)
        categories[category] = sorted(categories[category])[:10]

    framework = "unknown"
    for candidate in ["fastapi", "flask", "django"]:
        if categories[candidate]:
            framework = candidate
            break

    schema = "pydantic" if categories["pydantic"] else "unknown"
    test_runner = "pytest" if categories["pytest"] else "unknown"
    orchestration = [key for key in ["langchain", "llamaindex", "celery_rq"] if categories[key]]

    recommendations = []
    if categories["langchain"] or categories["llamaindex"]:
        recommendations.append("Decompose chain/query-engine behavior into FastGPT nodes before deciding helper boundaries.")
    if categories["fastapi"] and categories["pydantic"]:
        recommendations.append("Reuse existing Pydantic models as helper request/response contract sources.")
    if not categories["fastapi"] and not categories["flask"] and not categories["django"]:
        recommendations.append("No obvious web framework found; plan helper hosting explicitly before generating endpoints.")

    return {
        "repo": str(repo),
        "framework": framework,
        "schemaLayer": schema,
        "testRunner": test_runner,
        "orchestration": orchestration,
        "categories": categories,
        "recommendations": recommendations,
    }


def render_markdown(result: dict) -> str:
    lines = [
        f"# Python host scan — {result['repo']}",
        "",
        f"- framework: {result['framework']}",
        f"- schema layer: {result['schemaLayer']}",
        f"- test runner: {result['testRunner']}",
        f"- orchestration: {', '.join(result['orchestration']) if result['orchestration'] else 'none detected'}",
        "",
        "## Evidence",
    ]
    for category, paths in result["categories"].items():
        lines.append(f"### {category}")
        lines.extend([f"- {item}" for item in paths[:5]] or ["- none"])
    lines.append("")
    lines.append("## Recommendations")
    lines.extend([f"- {item}" for item in result["recommendations"]] or ["- Review actual call paths before selecting helper boundaries."])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a Python repo for FastGPT host-adapter conventions.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()
    result = scan(Path(args.repo).resolve())
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
