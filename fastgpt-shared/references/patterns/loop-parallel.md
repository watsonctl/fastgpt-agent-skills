# Pattern: loop vs parallel

## Use `loop` when

- order matters
- later iterations depend on earlier iteration outputs
- you need deterministic per-item accumulation
- the source code is conceptually a for-loop or map-with-join

## Use `parallelRun` when

- items are independent
- failures should not block siblings
- the source system is doing safe fan-out work
- parallel latency reduction matters more than strict order

## Guardrails

- Keep array size and concurrency explicit.
- Add flatten/merge logic after nested execution.
- Prefer a single purpose per loop/parallel block.
- Do not use parallel fan-out if the source logic actually depends on sequential evidence accumulation.
- Treat `loop` / `parallelRun` as FastGPT nested containers, not ordinary parent nodes.
- Instantiate from `assets/canonical-examples/` or a fresh target-instance export. Do not use legacy keys from old probes.
- Current verified container keys:
  - input array: `loopInputArray`
  - child list: `childrenNodeIdList`
  - layout: `nodeWidth`, `nodeHeight`, `loopNodeInputHeight`
  - start child outputs: `loopStartInput`, `loopStartIndex`
  - end child input: `loopEndInput`
  - loop output: `loopArray`
  - parallel inputs: `parallelRunMaxConcurrency`, `parallelRunMaxRetryTimes`
  - parallel outputs: `parallelSuccessResults`, `parallelFullResults`, `parallelStatus`
- Do not reference container-level legacy fields such as `currentItem`, `result`, `successResults`, `fullResults`, or `status`; body nodes must read current item/index from the `loopStart` child.

## FastGPT RAG caveat

For critical RAG retrieval inside workflow tools, prefer `loop -> loopArray -> flatten code` until the target instance proves `parallelRun.parallelSuccessResults` preserves `datasetSearchNode.quoteQA`. Runtime evidence from self-hosted FastGPT showed `generalTasks` non-empty but `generalQuotes/candidateCount` empty when泛检索 depended on `parallelSuccessResults`; sequential `loop` is slower but reliable for primary evidence chains.
