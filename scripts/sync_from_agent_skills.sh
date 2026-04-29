#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/sync_from_agent_skills.sh [--source PATH] [--dry-run]

Materialize the FastGPT skill pack from the local maintenance source into this
GitHub publishing repository. This script intentionally copies real files rather
than committing external symlinks.

Defaults:
  --source /home/maintainer/repos/agent-skills
USAGE
}

SOURCE_ROOT="/home/maintainer/repos/agent-skills"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE_ROOT="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLISH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
[[ -x "$PYTHON_BIN" ]] || PYTHON_BIN="$(command -v python3 || true)"

SKILLS=(
  fastgpt-shared
  fastgpt-workflow-generator
  fastgpt-workflow-debug
  fastgpt-workflow-migration
  fastgpt-ts-node-host-adapter
  fastgpt-python-host-adapter
)

command -v rsync >/dev/null 2>&1 || { echo "rsync is required" >&2; exit 1; }
[[ -n "$PYTHON_BIN" ]] || { echo "python3 is required" >&2; exit 1; }
[[ -d "$SOURCE_ROOT" ]] || { echo "Missing source root: $SOURCE_ROOT" >&2; exit 1; }

for skill in "${SKILLS[@]}"; do
  [[ -d "$SOURCE_ROOT/$skill" ]] || { echo "Missing source skill: $SOURCE_ROOT/$skill" >&2; exit 1; }
  [[ -f "$SOURCE_ROOT/$skill/SKILL.md" ]] || { echo "Missing SKILL.md for: $skill" >&2; exit 1; }
done

RSYNC_FLAGS=(
  -aL
  --delete
  --delete-excluded
  --itemize-changes
  --exclude '.git/'
  --exclude '.DS_Store'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '*.pyo'
  --exclude '*.local.env'
  --exclude '*.secrets.local.env'
  --exclude '.env'
  --exclude '.env.*'
  --exclude '*token*.local*'
  --exclude '*secret*.local*'
)
[[ "$DRY_RUN" -eq 1 ]] && RSYNC_FLAGS+=(-n)

printf 'Source: %s\nPublish: %s\nMode: %s\n' "$SOURCE_ROOT" "$PUBLISH_ROOT" "$([[ "$DRY_RUN" -eq 1 ]] && echo dry-run || echo sync)"

for skill in "${SKILLS[@]}"; do
  echo
  echo "== sync $skill =="
  rsync "${RSYNC_FLAGS[@]}" "$SOURCE_ROOT/$skill/" "$PUBLISH_ROOT/$skill/"
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo
  echo "Dry-run complete; no files changed."
  exit 0
fi

echo
echo "== JSON parse check =="
"$PYTHON_BIN" - <<'PY' "$PUBLISH_ROOT"
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
paths = sorted(root.glob('fastgpt-shared/assets/**/*.json'))
for path in paths:
    with path.open(encoding='utf-8-sig') as f:
        json.load(f)
print(f'parsed_json_files={len(paths)}')
PY

echo
echo "== validator smoke check =="
VALIDATOR="$PUBLISH_ROOT/fastgpt-shared/scripts/validate_fastgpt_workflow.py"
for json_file in \
  "$PUBLISH_ROOT/fastgpt-shared/assets/canonical-examples/00-workflow-tool-parallelrun-sample.workflow.json" \
  "$PUBLISH_ROOT/fastgpt-shared/assets/canonical-examples/35-fact-extractor.workflow.json" \
  "$PUBLISH_ROOT/fastgpt-shared/assets/canonical-examples/70-parallel-review-executor.workflow.json" \
  "$PUBLISH_ROOT/fastgpt-shared/assets/probe-examples/03_batch_processing_probe.json" \
  "$PUBLISH_ROOT/fastgpt-shared/assets/probe-examples/04_parallel_run_probe.json"; do
  [[ -f "$json_file" ]] || { echo "Missing expected JSON: $json_file" >&2; exit 1; }
  "$PYTHON_BIN" "$VALIDATOR" "$json_file" >/dev/null
  echo "valid: ${json_file#$PUBLISH_ROOT/}"
done

echo
echo "== secret marker scan =="
if grep -RInE 'openapi-[A-Za-z0-9]{12,}|sk-[A-Za-z0-9]{12,}|Authorization: Bearer [A-Za-z0-9_-]{20,}|api[_-]?key\s*[:=]\s*[A-Za-z0-9_-]{20,}' \
  "$PUBLISH_ROOT/fastgpt-shared" \
  "$PUBLISH_ROOT/fastgpt-workflow-generator" \
  "$PUBLISH_ROOT/fastgpt-workflow-debug" \
  "$PUBLISH_ROOT/fastgpt-workflow-migration" \
  "$PUBLISH_ROOT/fastgpt-ts-node-host-adapter" \
  "$PUBLISH_ROOT/fastgpt-python-host-adapter"; then
  echo "Potential secret marker found; review before commit." >&2
  exit 1
fi
echo "secret_scan=pass"

echo
echo "== git status --short =="
git -C "$PUBLISH_ROOT" status --short

echo
echo "Sync complete. Review git diff and commit manually."
