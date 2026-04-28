# FastGPT runtime diagnostics

Use this when a FastGPT workflow imports successfully but runtime behavior does not match the static JSON.

## When runtime diagnostics is mandatory

Run runtime diagnostics before changing workflow logic when any of these happen:
- imported workflow behaves differently from local unit tests
- a node output is unexpectedly empty at runtime
- a workflow tool receives empty input despite non-empty upstream UI content
- dataset search does not fire or gets an empty query / empty dataset list
- direct answer / retrieval routing looks correct in JSON but wrong in execution

## Standard flow

0. Confirm credential-to-agent identity
1. Export the raw flow responses
2. Analyze the exported JSON
3. Only then decide whether the fix belongs in:
   - workflow builder fields / wiring
   - code-node runtime parsing
   - prompt contract
   - workflow-tool I/O mapping
   - dataset / collection config

## Credential identity diagnostics

When several FastGPT OpenAPI keys exist on the same machine, assume they may point to different apps even if they share the same base URL.

Required checks:

- Do not select a key by filename alone. Confirm the app purpose through a non-secret inventory entry or a fresh `detail=true` probe.
- Compare the observed first nodes in `responseData` to the expected workflow chain. For example, a governed scheme-review app may show `workflowStart -> normalizeInput -> callReviewContextWft -> callAiReviewWft -> callFinalAssemblerWft`; a response that immediately hits `datasetSearchNode` is a different app.
- Treat `HTTP 200 + empty choices.message.content` as a failure until `responseData` proves a valid final output path. Do not count it as business success.
- If the wrong key was used, classify the diagnosis as `wrong_agent_key` before investigating workflow internals.

Secret handling:

- Full keys stay in process env, stdin, a local secret manager, or another approved secret source only.
- Reports and skill docs may include only non-secret identity fields: agent name, base URL, key fingerprint, expected nodes, and last verified date.

Helper script:

```bash
printf '%s' "$FASTGPT_API_KEY" | python ../scripts/probe_fastgpt_agent_identity.py \
  --chat-url https://your-fastgpt-host/api/v1/chat/completions \
  --api-key-stdin \
  --expect-node normalizeInput \
  --expect-node callFinalAssemblerWft
```

The script prints only a key fingerprint and non-secret node evidence.

## Export script

Script:
- `../scripts/export_fastgpt_flow_logs.py`

Recommended usage:

```bash
python ../scripts/export_fastgpt_flow_logs.py \
  --base-url https://your-fastgpt-host \
  --api-key "$FASTGPT_API_KEY" \
  --app-id YOUR_APP_ID \
  --export-dir ./fastgpt-logs
```

### Credential passing

Preferred order:
1. CLI args
2. environment variables

Supported env vars:
- `FASTGPT_BASE_URL`
- `FASTGPT_API_KEY`
- `FASTGPT_APP_ID`

### Base URL rule

Pass the FastGPT host root, not a specific endpoint.

Accepted inputs:
- `https://host`
- `https://host/api`

The script normalizes both forms and then calls `/api/core/...` endpoints itself.

## Analyze script

Script:
- `../scripts/analyze_fastgpt_flow_logs.py`

Recommended usage:

```bash
python ../scripts/analyze_fastgpt_flow_logs.py \
  --latest ./fastgpt-logs \
  --title-contains "your user-visible query title" \
  --format text
```

Useful filters:
- `--chat-id`
- `--title-contains`
- `--data-id`
- `--latest DIR`
- `--input FILE`

## Common failure chains

### 0) Code node returns too fast with empty business output
Symptoms:
- API call finishes normally but the final business artifact is empty, generic, or a fast degradation
- workflow-tool nodes appear to execute, but reviewer/task selection arrays are empty
- local tests pass because static objects were available in the generated JSON

Likely cause:
- generation-time static data such as governance snapshots, registries, template manifests, or dataset manifests was passed as hidden object inputs to code nodes
- FastGPT dropped or coerced those hidden structured inputs at runtime, so the code fell back to `{}` and selected no work

Fix pattern:
- compile generation-time static data into the code node JavaScript as constants
- keep runtime inputs limited to real user/task data and explicit node references
- add a validator check for hidden structured code-node inputs
- verify the business artifact, not just node execution

### 1) Input lost before normalize/code
Symptoms:
- analyzer `query` is non-empty
- normalize/code node `userQuery` is empty

Likely cause:
- code node treated FastGPT structured message content as a plain string

### 2) Analyzer output lost before bridge
Symptoms:
- analyzer visibly answered with JSON
- bridge shows default values / empty rewritten queries / empty tasks

Likely cause:
- bridge code expected a plain string, but FastGPT passed structured content items

### 3) Workflow tool receives empty tasks
Symptoms:
- `pluginModule.toolInput.generalTasks=[]`
- `pluginModule.toolInput.userQuery=""`
- reviewer or worker selection arrays are empty even though the workflow should have enabled work

Likely cause:
- upstream bridge/normalize node already lost the real inputs
- generation-time registries were not available to the workflow tool code node at runtime

First checks:
- inspect `customInputs/customOutputs` for the workflow tool and the first code node inside it
- confirm static registries are compiled into code or loaded from a real runtime source, not passed as hidden object inputs
- run the workflow JSON validator after generation

### 4) Dataset search does not run meaningfully
Symptoms:
- dataset search runs but query is empty
- dataset search input datasets are empty or mismatched

Likely cause:
- bad upstream task shaping or dataset selector wiring

## Local execution caveats

- Do not assume screenshots are enough; exported `flowResponses` are the source of truth.
- Avoid running temporary Python copies in polluted directories such as `/tmp` if your machine has conflicting module filenames there.
- Keep the raw exported JSON unchanged; do diagnosis in a separate script or notebook.
