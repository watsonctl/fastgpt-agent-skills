# Pattern: Python host adapter exception path

Use this only after `workflow-only` and `workflow+workflow-tools` are insufficient.

## Scan targets

- FastAPI / Flask / Django route organization
- Pydantic / dataclasses / DRF serializers
- LangChain / LlamaIndex retrievers/chains/graphs
- Celery / RQ / async workers
- pytest / unittest conventions

## Preferred mapping before helpers

| Python source behavior | FastGPT-preferred mapping |
|---|---|
| request parsing / variable normalization | `workflowStart` + `code` |
| deterministic transform | `code` or 工作流工具 |
| retriever | `datasetSearchNode` when using FastGPT datasets |
| chain/router/graph | `chatNode`, `ifElseNode`, `loop`, `parallelRun`, 工作流工具 |
| metadata/static lookup | generated snapshot in `code` |
| true dynamic Python-only operation | approved Helper API only |

## Exception guardrails

- Do not expose the whole Python service as one `/chat` proxy.
- Do not black-box LangChain/LlamaIndex unless the user explicitly accepts a thin wrapper.
- If a Helper API is approved, define Pydantic request/response schemas and pytest cases.
