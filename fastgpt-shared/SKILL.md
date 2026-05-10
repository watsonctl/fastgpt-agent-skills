---
name: fastgpt-shared
description: "Shared FastGPT contracts, diagnostics, scripts, and patterns."
---

# FastGPT Shared Base

> This repository is a community FastGPT workflow engineering skill pack. It focuses on workflow JSON generation, import readiness, runtime diagnostics, workflow-tool decomposition, and migration support. It complements FastGPT's maintainer-oriented skills such as API development, PR review, tests, and documentation i18n. It is not a replacement for FastGPT official contracts; generated workflows must be validated against the target FastGPT instance.

Use this as the base layer for the FastGPT skill pack. It is the shared System of Record for:

- official FastGPT contract references
- target-instance canonical workflow examples
- runtime diagnostics and flow log tooling
- migration checklists and patterns
- the cross-Agent Business Delivery Harness
- GitHub distribution and multi-device install/sync rules

## Skill-pack install unit

Treat the following directories as one install unit:

- `fastgpt-shared`
- `fastgpt-workflow-generator`
- `fastgpt-workflow-debug`
- `fastgpt-workflow-migration`
- `fastgpt-ts-node-host-adapter`
- `fastgpt-python-host-adapter`

`fastgpt-shared` carries the heavy references/scripts. The other FastGPT skills are thin entrypoints that route into this base.

## Read this first

1. `references/business-delivery-harness.md`
2. `references/fastgpt-official-contracts.md`
3. For importable workflow JSON, prefer target-instance exports and bundled `assets/canonical-examples/` over old probes.
4. Load only the next document you actually need:
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

## Canonical examples and publishing source

- Local maintenance source: `/home/maintainer/repos/agent-skills`.
- GitHub publishing repo: `watsonctl/fastgpt-agent-skills`.
- Published GitHub content must be materialized real files; do not publish external symlinks that point back to a maintainer's local `/home/maintainer/repos/agent-skills`.
- `assets/golden-examples/` contains end-to-end verified production-grade workflow patterns.
- `assets/canonical-examples/` contains dashboard-import verified JSON and is the bundled System of Record for high-risk node shapes when no fresher target export is available.
- `assets/functional_nodes_library.json` is a comprehensive library of individual FastGPT functional nodes (Chat, Search, Extract, Classify, Tools) with their full input/output schemas.
- `assets/probe-examples/` are exploration probes. They are not production templates unless their README marks them canonical/import-verified.

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

- `/home/maintainer/repos/agent-skills` is the maintainer source of truth for local development; the GitHub repo is a materialized publishing target.
- Consumer folders such as `~/.codex/skills` are installed mirrors, not editing targets.
- The repo-level sync script is for maintainers who cloned `watsonctl/fastgpt-agent-skills`; it materializes selected FastGPT skill directories from the maintenance source and is not bundled when installing a single skill path.
- From the repo root, sync the whole pack with:

```bash
scripts/sync-fastgpt-skill-pack.sh
```

## Guardrails

- **Keep SKILL.md thin**: Heavy knowledge belongs in `references/` and repeatable actions belong in `scripts/`.
- **Domain Portability (Harness Engineering)**: Shared guidance and probe examples must stay domain-portable. 
  - Do not strip FastGPT core schema keys (e.g., `candidates`, `sourceRefs`, `documentType`), but replace specific business payload values (e.g., `008`, `construction_scheme`) with generic placeholders (`generic_document`, `sample_module`).
  - Avoid referencing private instance configurations. Use generic terminology like `Observed in tested FastGPT instances`.
- **Open Source Contribution Strategy**: Do not submit the entire skill pack as a single PR. Follow the calculated contributor path:
  1. **Issue**: Propose feature requests (e.g., Workflow-as-Code capabilities) without hardcoding endpoint designs.
  2. **Docs PR**: Provide restrained, official-style documentation (e.g., `AI-assisted Workflow Development`). Avoid personal engineering paradigms (like "100-node paradigm") and use standard Markdown syntax (e.g., blockquotes instead of GitHub alerts) for compatibility.
  3. **Examples PR**: Submit minimal, highly generic JSON examples. Avoid complex or unstable nodes (`parallelRun`, `loop`) in early submissions.
  4. **Skill/RFC PR**: Only submit minimal skills or API implementations after achieving maintainer consensus.
- **Paths**: Use relative paths only; the GitHub-distributed pack must work on any device after install.
- **Acceptance Gate**: Do not treat node success as acceptance. Business delivery, evidence, traceability, and stable closure are the acceptance gate.
