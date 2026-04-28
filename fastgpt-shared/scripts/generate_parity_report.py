#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

CATEGORY_RULES = {
    "entrypoint": ["chat/completions", "export async function POST", "route.ts", "controller", "handler"],
    "analysis": ["analyzer", "retrievalIntensity", "rewrittenQueries", "directAnswerAllowed", "queryType"],
    "retrieval": ["retriev", "datasetSearch", "retrieveChunks", "collectionIds", "rag"],
    "precision_lookup": ["lookupCollection", "collection-lookup", "STANDARD_NUMBER_RE", "precision"],
    "verification": ["verifier", "verifierScore", "目录", "索引", "evidence"],
    "ranking": ["wrongStandardPenalty", "pseudoContentPenalty", "bundleRole", "chunkScore", "rerank", "fusion"],
    "fallback": ["reference_only", "answerMode", "未直接命中", "fallback", "downgrade"],
    "loop_parallel": ["parallelRun", "loopStart", "loopEnd", "Promise.all", "batch"],
    "external_http": ["fetch(", "axios", "httpRequest", "Authorization"],
    "host_adapter": ["auth()", "verifyApiKey", "zod", "vi.mock", "jest.mock"],
}

SEARCH_GLOBS = [
    "app/**/*.ts",
    "app/**/*.tsx",
    "lib/**/*.ts",
    "lib/**/*.tsx",
    "src/**/*.ts",
    "src/**/*.tsx",
    "server/**/*.ts",
    "scripts/**/*.ts",
    "scripts/**/*.js",
    "scripts/**/*.py",
    "workers/**/*.ts",
    "__tests__/**/*.ts",
    "__tests__/**/*.tsx",
]


def rg_list(repo: Path, pattern: str) -> list[str]:
    cmd = ["rg", "-l", "-F", pattern, str(repo)]
    for glob in SEARCH_GLOBS:
        cmd.extend(["-g", glob])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"rg failed for pattern: {pattern}")
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return lines


def score_path(path_str: str) -> tuple[int, str]:
    normalized = path_str.replace("\\", "/")
    preferred = ["/lib/", "/app/api/", "/src/", "/server/", "/scripts/", "/workers/", "/__tests__/"]
    for index, token in enumerate(preferred):
        if token in normalized:
            return (100 - index * 10, normalized)
    return (0, normalized)


def scan(repo: Path):
    result = {key: [] for key in CATEGORY_RULES}
    for category, patterns in CATEGORY_RULES.items():
        matches: list[str] = []
        seen = set()
        for pattern in patterns:
            for item in rg_list(repo, pattern):
                normalized = item.replace("\\", "/")
                if normalized in seen:
                    continue
                seen.add(normalized)
                matches.append(normalized)
        result[category] = [item for item in sorted(matches, key=lambda item: (-score_path(item)[0], item))][:10]
    return result


def status(paths):
    return "found" if paths else "missing"


def render_markdown(repo: Path, result: dict) -> str:
    lines = [f"# Parity report — {repo}", "", "| Category | Status | Evidence |", "|---|---|---|"]
    for category, paths in result.items():
        evidence = "<br>".join(paths[:3]) if paths else "-"
        lines.append(f"| {category} | {status(paths)} | {evidence} |")
    lines.extend([
        "",
        "## Notes",
        "- This is a fast discovery pass. Treat it as a starting map, not proof of parity.",
        "- Evidence is ranked toward implementation files before tests.",
        "- Re-check actual call paths for any category that matters to the migration.",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a heuristic parity report for a repo -> FastGPT migration.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    result = scan(repo)
    if args.format == "json":
        print(json.dumps({"repo": str(repo), "categories": result}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(repo, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
