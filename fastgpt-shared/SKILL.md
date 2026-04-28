---
name: fastgpt-shared
description: "Shared FastGPT contracts, diagnostics, scripts, and patterns."
---

# FastGPT Shared Base

Use this as the base layer for the FastGPT skill pack. It is the shared System of Record for:

- official FastGPT contract references
- runtime diagnostics and flow log tooling
- migration checklists and patterns
- the cross-Agent Business Delivery Harness
- GitHub distribution and multi-device install/sync rules

## Skill-pack install unit

Treat the following directories as one install unit:

- `fastgpt-shared`
- `fastgpt-workflow-debug`
- `fastgpt-workflow-migration`
- `fastgpt-workflow-generator`
- `fastgpt-ts-node-host-adapter`
- `fastgpt-python-host-adapter`

`fastgpt-shared` carries the heavy references/scripts. The other FastGPT skills are thin entrypoints that route into this base.

## Read this first

1. `references/business-delivery-harness.md`
2. `references/fastgpt-official-contracts.md`
3. Load only the next document you actually need:
   - runtime issues -> `references/runtime-diagnostics.md`
   - migration work -> `references/migration-checklist.md`
   - deep debug details -> `references/debug-playbook.md`
   - deep migration details -> `references/migration-playbook.md`
   - RAG / tools / fallback / layout patterns -> `references/patterns/*.md`

## Script index

Use scripts instead of rewriting diagnostics by hand.

- export logs: `scripts/export_fastgpt_flow_logs.py`
- analyze logs: `scripts/analyze_fastgpt_flow_logs.py`
- scaffold workflows: `scripts/scaffold_fastgpt_workflow.py`
- validate workflow JSON: `scripts/validate_fastgpt_workflow.py`
- validate layout: `scripts/validate_fastgpt_layout.py`
- generate import readiness: `scripts/generate_import_readiness_report.py`
- parity scan: `scripts/generate_parity_report.py`
- probe agent identity: `scripts/probe_fastgpt_agent_identity.py`
- host scans: `scripts/scan_ts_node_host.py`, `scripts/scan_python_host.py`

## Multi-device usage

### Ordinary device: install the whole pack from GitHub

Install the complete pack together so `../fastgpt-shared` references always resolve:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo watsonctl/fastgpt-agent-skills \
  --path fastgpt-shared \
  --path fastgpt-workflow-debug \
  --path fastgpt-workflow-migration \
  --path fastgpt-workflow-generator \
  --path fastgpt-ts-node-host-adapter \
  --path fastgpt-python-host-adapter
```

Restart Codex after installation. Use `--ref <tag-or-commit>` when a stable pinned install is required.

### Maintainer device: cloned repo + local mirror sync

- GitHub repo is the SoR.
- Consumer folders such as `~/.codex/skills` are installed mirrors, not editing targets.
- The repo-level sync script is for maintainers who cloned `watsonctl/fastgpt-agent-skills`; it is not bundled when installing a single skill path.
- From the repo root, sync the whole pack with:

```bash
scripts/sync-fastgpt-skill-pack.sh
```

## Guardrails

- Keep `SKILL.md` thin. Heavy knowledge belongs in `references/` and repeatable actions belong in `scripts/`.
- Shared guidance must stay domain-portable. Project-specific benchmark fixes do not belong here.
- Use relative paths only; the GitHub-distributed pack must work on any device after install.
- Do not treat node success as acceptance. Business delivery, evidence, traceability, and stable closure are the acceptance gate.
