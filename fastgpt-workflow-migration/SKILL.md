---
name: fastgpt-workflow-migration
description: "Migrate flows to FastGPT workflow JSON; 工作流迁移."
---

# FastGPT Workflow Migration

Use this skill when the task is to preserve business behavior while moving an existing system into FastGPT workflow JSON.

## Start sequence

1. Read `../fastgpt-shared/SKILL.md`.
2. Read `../fastgpt-shared/references/business-delivery-harness.md`.
3. Read `../fastgpt-shared/references/fastgpt-official-contracts.md`.
4. Read `../fastgpt-shared/references/migration-checklist.md`.
5. Load `../fastgpt-shared/references/migration-playbook.md` only for the sections you need.
6. Load the relevant pattern docs under `../fastgpt-shared/references/patterns/`.

## Capability ladder

Decide and record the migration mode before implementation:

1. `workflow-only`
2. `workflow+workflow-tools`
3. `exception-helper-approved`

Default rule: prefer native FastGPT nodes and workflow tools before any host Helper/API boundary.

## Required outputs

- importable workflow JSON or workflow-tool bundle
- recorded migration mode and binding mode
- parity / coverage view
- import readiness evidence
- explicit Business Delivery Harness acceptance

## Guardrails

- Migrate the business deliverable, not just the canvas shape.
- Keep heavy examples and detailed rules in shared references, not this entry skill.
- If runtime behavior diverges from the static bundle, switch to exported runtime diagnostics before changing builder logic again.
- Shared migration guidance must stay cross-Agent and cross-domain; project-local heuristics stay local.
- For workflow-tool calls, confirm version-binding semantics from a current export; current observed default for "保持最新版本" is documented in `../fastgpt-shared/references/patterns/workflow-tool.md`.
