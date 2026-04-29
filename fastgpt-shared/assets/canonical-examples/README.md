# FastGPT canonical workflow examples

These JSON files are **target-instance facts**: they were imported into the target FastGPT instance and passed dashboard validation on 2026-04-29.

Use them as schema references before generating high-risk workflow JSON. Do not infer container-node contracts from old probes or natural-language docs when these examples conflict with them.

## Files

- `00-workflow-tool-parallelrun-sample.workflow.json` — canonical minimal `workflow tool + parallelRun` example. Use this as the primary template for `parallelRun` container shape.
- `35-fact-extractor.workflow.json` — canonical imported example for a workflow-tool `loop` / batch container. Treat the business prompt/code as project-specific; use only the container schema and wiring as a reference.
- `70-parallel-review-executor.workflow.json` — canonical imported example for a workflow-tool `parallelRun` container in a larger review chain. Treat the business prompt/code as project-specific; use only the container schema and wiring as a reference.

## Container schema rule

For `loop` and `parallelRun`, clone the full container shape from a canonical example and then change only IDs, positions, prompts, code, labels, and safe reference targets. Do not invent input/output keys.

Current verified container anchors:

- container input array key: `loopInputArray`
- child list key: `childrenNodeIdList`
- child start anchor: `loopStart` node with outputs `loopStartInput` and `loopStartIndex`
- child end anchor: `loopEnd` node with input `loopEndInput`
- loop aggregate output: `loopArray`
- parallel aggregate outputs: `parallelSuccessResults`, `parallelFullResults`, `parallelStatus`

The old probe keys `array`, `maxConcurrency`, `maxRetries`, `successResults`, `failedResults`, `fullResults`, `status`, and container-level `currentItem` are legacy/unverified for the current target instance and must not be used for new importable JSON.
