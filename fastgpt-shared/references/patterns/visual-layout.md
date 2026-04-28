# Pattern: FastGPT visual layout

Use this for any generated or modified FastGPT workflow JSON before import.

## Goal

A workflow is not import-ready if it works but opens as a tangled canvas. Complex workflows must be laid out for debugging and handoff.

## Default strategy: swimlane

Use horizontal flow from left to right and separate vertical lanes by responsibility.

| Lane | Typical y range | Contents |
|---|---:|---|
| System / config | -900 | `userGuide`, instructions, global config |
| General retrieval | -1200 | parallel retrieval parent + children |
| Precision retrieval | -520 | identifier lookup, scoped dataset search |
| Main spine | 0 | start, normalize, analysis, merge, verify, rank, final answer |
| Direct / fallback | 600 | direct answer and explicit downgrade branches |
| Auto requery | -760 or separate side lane | one-shot citation or missing-evidence requery |

## Spacing

- Use at least `420px` horizontal spacing between top-level nodes.
- Use at least `360px` vertical spacing between independent lanes.
- For wide cards such as `chatNode`, `code`, `httpRequest468`, and `datasetSearchNode`, prefer `480-560px` x gaps.
- Parent nodes (`loop`, `parallelRun`) and their children must not share the main spine lane.

## Loop / parallel children

- Put each parent block on its own lane.
- Keep child nodes in execution order left-to-right.
- Place flatten/merge nodes outside the parent block and closer to the main spine.
- Do not overlap child groups with verifier/ranking/final-answer nodes.

## Position-only relayout rule

When improving readability of an existing working workflow, change only:

```json
node.position.x
node.position.y
```

Do not change:
- `nodeId`
- `flowNodeType`
- `inputs`
- `outputs`
- `edges`
- `chatConfig`
- prompts or code strings

## Import readiness gate

Before handing off a workflow JSON, run:

```bash
python ../fastgpt-shared/scripts/validate_fastgpt_workflow.py /path/workflow.json
python ../fastgpt-shared/scripts/validate_fastgpt_layout.py /path/workflow.json --strategy swimlane
```

If the layout validator reports overlap warnings, fix positions before import unless the user explicitly accepts a dense/debug-only canvas.
