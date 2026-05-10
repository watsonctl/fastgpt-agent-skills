# Feature Request: Workflow-as-Code support for AI-assisted workflow development

## Background

FastGPT already provides powerful visual workflow orchestration, OpenAPI-based invocation, and detailed runtime diagnostics such as `detail=true`, `flowNodeStatus`, `flowResponses`, and plugin output data.

However, the development loop for complex workflows still depends heavily on manual dashboard operations:

1. Design or generate workflow JSON outside FastGPT
2. Manually import or update the workflow in the dashboard
3. Manually run full workflow tests
4. Inspect runtime diagnostics
5. Modify the workflow JSON
6. Repeat the process

This makes AI-assisted workflow engineering possible, but not yet fully automatable.

## Pain Point

For complex workflows, especially those involving code nodes, dataset search, conditional branches, workflow tools, and `pluginModule` calls, developers need a repeatable loop:

**draft import → validation → test run → diagnostics → iteration → publish / rollback**

Currently, runtime diagnostics are available during chat execution, but there does not appear to be an official API/CLI contract for headless workflow draft import, validation, test execution, diagnostics export, and publishing.

## Proposed Direction

It would be valuable for FastGPT to provide an official Workflow-as-Code API or CLI layer.

Possible capabilities could include:

1. Export current workflow configuration
2. Import workflow JSON as a draft without affecting production
3. Validate workflow JSON before import or publish
4. Run a test case against a draft workflow
5. Return structured diagnostics such as node status, runtime errors, `flowResponses`, plugin output, and updated variables
6. Publish a validated draft
7. Roll back to a previous version

The exact endpoint naming, authentication scope, permission model, and edition support should be decided by FastGPT maintainers.

## Why This Matters

This would enable a complete AI-assisted workflow development loop:

* **Plan:** AI reads requirements and current workflow structure
* **Do:** AI generates or patches workflow JSON
* **Check:** FastGPT runs the draft and returns structured diagnostics
* **Act:** AI fixes the workflow based on runtime evidence and repeats the test

This would improve developer experience for complex FastGPT workflows, reduce manual dashboard operations, and make workflow development more suitable for CI/CD and professional engineering environments.

## Security and Permission Considerations

This feature should be designed with explicit permission boundaries. For example:

* Limit workflow import/publish to users with app owner or admin permissions
* Use scoped API tokens for workflow development operations
* Separate draft import from production publish
* Keep dangerous actions such as publishing and rollback auditable
* Consider private deployment and professional developer use cases first

## External Experiment

I have been experimenting with an external FastGPT agent skills pack to explore workflow JSON generation, validation, debugging, migration, and runtime log analysis:

[https://github.com/watsonctl/fastgpt-agent-skills](https://github.com/watsonctl/fastgpt-agent-skills)

The experiment suggests that the missing piece is not workflow generation itself, but an official headless contract for importing, validating, testing, diagnosing, and publishing workflows.

I would be happy to help contribute documentation, minimal workflow JSON examples, or a proposal for the API/CLI contract if the maintainers think this direction is aligned with FastGPT.
