#!/usr/bin/env python3
import argparse
from pathlib import Path
from string import Template

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
ROUTE_TEMPLATE = Template((ASSET_DIR / "ts-node-helper-route.ts.tpl").read_text())
TEST_TEMPLATE = Template((ASSET_DIR / "ts-node-helper-test.ts.tpl").read_text())


def render(helper_name: str):
    helper_id = helper_name.replace("-", "_")
    return {
        "route": ROUTE_TEMPLATE.safe_substitute(HELPER_NAME=helper_name, HELPER_ID=helper_id),
        "test": TEST_TEMPLATE.safe_substitute(HELPER_NAME=helper_name, HELPER_ID=helper_id),
    }


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold TS/Node helper routes and tests for a FastGPT migration.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--helper-name", action="append", required=True)
    parser.add_argument("--route-root", default="app/api/rag-helper")
    parser.add_argument("--test-root", default="__tests__/app/api/rag-helper")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not args.write:
        args.dry_run = True

    for helper_name in args.helper_name:
        rendered = render(helper_name)
        route_path = repo / args.route_root / helper_name / "route.ts"
        test_path = repo / args.test_root / f"{helper_name}.test.ts"
        print(f"# {helper_name}")
        print(f"route: {route_path}")
        print(f"test:  {test_path}")
        if args.write:
            write_file(route_path, rendered["route"])
            write_file(test_path, rendered["test"])
            print("written: yes")
        else:
            print("written: no (dry-run)")
            print("--- route template preview ---")
            print(rendered["route"][:600].rstrip())
            print("--- test template preview ---")
            print(rendered["test"][:600].rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
