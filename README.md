# FastGPT Agent Skills

This repository is the GitHub publishing repository for the FastGPT skill pack.

## Source of truth

- Maintenance source: `/home/maintainer/repos/agent-skills`
- Publishing repository: `/home/maintainer/repos/fastgpt-agent-skills`
- Remote: `https://github.com/watsonctl/fastgpt-agent-skills`

The publishing repository must contain materialized real files. Do **not** commit external symlinks that point to a maintainer-local path such as `/home/maintainer/repos/agent-skills`; those links will break for other users after clone.

## Publish sync

From this repository root:

```bash
scripts/sync_from_agent_skills.sh
```

The script copies only FastGPT-related skill directories from the maintenance source, excludes caches and local secret files, parses JSON examples, runs validator smoke checks, scans for obvious secret markers, and prints `git status`. It does not commit.

## Included skill directories

- `fastgpt-shared`
- `fastgpt-workflow-generator`
- `fastgpt-workflow-debug`
- `fastgpt-workflow-migration`
- `fastgpt-ts-node-host-adapter`
- `fastgpt-python-host-adapter`

## Canonical examples

High-risk FastGPT workflow JSON generation must be grounded in target-instance successful exports/imports. Bundled import-verified examples live under:

```text
fastgpt-shared/assets/canonical-examples/
```

Probe examples are exploration aids and are not production templates unless explicitly marked canonical/import-verified.
