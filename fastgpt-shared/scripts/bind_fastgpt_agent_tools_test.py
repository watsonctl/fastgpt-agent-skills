#!/usr/bin/env python3
"""Focused tests for AgentV2 tool persistence helpers."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bind_fastgpt_agent_tools as binding_module  # noqa: E402
from bind_fastgpt_agent_tools import (  # noqa: E402
    bind_agent_tools,
    compact_agent_tool,
    normalize_agent_tools_in_workflow,
    agent_model_values,
    set_agent_model,
    set_agent_reasoning_effort,
    set_agent_system_prompt,
)
from create_fastgpt_app import build_version_save_payload, load_page_workflow  # noqa: E402


def agent_workflow(selected_tools):
    return {
        "nodes": [
            {
                "nodeId": "agent-node",
                "flowNodeType": "agent",
                "inputs": [
                    {
                        "key": "agent_selectedTools",
                        "value": selected_tools,
                    }
                ],
                "outputs": [],
            }
        ],
        "edges": [],
        "chatConfig": {},
    }


class AgentToolPersistenceTests(unittest.TestCase):
    def test_set_agent_model_changes_only_the_selected_agent_node(self):
        document = agent_workflow([])
        document["nodes"][0]["inputs"].append(
            {"key": "model", "value": "deepseek-v4-flash-0731"}
        )

        updated = set_agent_model(
            document,
            "GLM-5.3-Flash",
            agent_node_id="agent-node",
        )

        self.assertEqual(
            updated["nodes"][0]["inputs"][1]["value"], "GLM-5.3-Flash"
        )
        self.assertEqual(
            document["nodes"][0]["inputs"][1]["value"], "deepseek-v4-flash-0731"
        )
        self.assertEqual(agent_model_values(updated), [["GLM-5.3-Flash"]])

    def test_set_agent_system_prompt_is_a_copying_transform(self):
        document = agent_workflow([])
        document["nodes"][0]["inputs"].append(
            {"key": "systemPrompt", "value": "old prompt"}
        )

        updated = set_agent_system_prompt(document, "canonical prompt\n")

        self.assertEqual(
            updated["nodes"][0]["inputs"][1]["value"], "canonical prompt"
        )
        self.assertEqual(document["nodes"][0]["inputs"][1]["value"], "old prompt")

    def test_set_agent_reasoning_effort_changes_only_the_selected_agent_node(self):
        document = agent_workflow([])
        document["nodes"][0]["inputs"].extend([
            {"key": "aiChatReasoning", "value": True},
            {"key": "aiChatReasoningEffort", "value": "none"},
        ])

        updated = set_agent_reasoning_effort(
            document,
            "low",
            agent_node_id="agent-node",
        )

        self.assertEqual(
            updated["nodes"][0]["inputs"][2]["value"], "low"
        )
        self.assertEqual(
            document["nodes"][0]["inputs"][2]["value"], "none"
        )

    def test_compact_expanded_tool_to_official_persistence_shape(self):
        expanded = {
            "pluginId": "web-wrapper-app-id",
            "id": "editor-local-id",
            "version": "",
            "name": "Web wrapper",
            "inputs": [
                {
                    "key": "query",
                    "renderTypeList": ["agentGenerated", "textarea"],
                    "selectedType": "agentGenerated",
                    "value": "",
                },
                {
                    "key": "collectionId",
                    "renderTypeList": ["input"],
                    "selectedType": "input",
                    "value": "collection-1",
                },
                {
                    "key": "system_input_config",
                    "renderTypeList": ["hidden"],
                    "value": {"apiKey": "must-not-be-persisted"},
                },
            ],
            "config": {"query": "stale generated value", "limit": 5},
        }

        compact = compact_agent_tool(expanded)

        self.assertEqual(
            compact,
            {
                "id": "web-wrapper-app-id",
                "version": "",
                "inputs": [
                    {"key": "query", "mode": "agentGenerated"},
                    {"key": "collectionId", "mode": "manual"},
                ],
                "config": {"collectionId": "collection-1", "limit": 5},
            },
        )

    def test_bind_replaces_empty_runtime_only_binding_with_explicit_tools(self):
        document = agent_workflow([])
        tools = [
            {"id": "web-wrapper-app-id", "version": "", "config": {}},
            {"id": "directional-retrieval-app-id", "version": "", "config": {}},
        ]

        bound = bind_agent_tools(document, tools)

        selected = bound["nodes"][0]["inputs"][0]["value"]
        self.assertEqual(
            selected,
            [
                {"id": "web-wrapper-app-id", "version": "", "config": {}},
                {"id": "directional-retrieval-app-id", "version": "", "config": {}},
            ],
        )
        self.assertEqual(document["nodes"][0]["inputs"][0]["value"], [])

    def test_normalize_keeps_compact_tools_and_compacts_expanded_tools(self):
        compact = {"id": "already-compact", "version": "", "config": {}}
        expanded = {
            "pluginId": "expanded-tool",
            "inputs": [],
            "config": {},
            "description": "editor-only detail",
        }
        document = agent_workflow([compact, expanded])

        normalized = normalize_agent_tools_in_workflow(document)

        self.assertEqual(
            normalized["nodes"][0]["inputs"][0]["value"],
            [compact, {"id": "expanded-tool", "config": {}}],
        )
        self.assertEqual(document["nodes"][0]["inputs"][0]["value"][1], expanded)

    def test_create_app_loader_normalizes_before_update_payload_is_built(self):
        document = agent_workflow([{"pluginId": "expanded-tool", "inputs": [], "config": {}}])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.json"
            path.write_text(json.dumps(document), encoding="utf-8")

            loaded = load_page_workflow(path)

        self.assertEqual(
            loaded["nodes"][0]["inputs"][0]["value"],
            [{"id": "expanded-tool", "config": {}}],
        )
        payload = build_version_save_payload(document, is_publish=False, auto_save=True)
        self.assertEqual(
            payload["nodes"][0]["inputs"][0]["value"],
            [{"id": "expanded-tool", "config": {}}],
        )
        self.assertTrue(payload["autoSave"])

    def test_cli_dry_run_writes_only_compact_bindings(self):
        document = agent_workflow([])
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            workflow_path = directory_path / "workflow.json"
            output_path = directory_path / "bound.json"
            workflow_path.write_text(json.dumps(document), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "bind_fastgpt_agent_tools.py"),
                    "--workflow",
                    str(workflow_path),
                    "--tool-id",
                    "web-wrapper-app-id",
                    "--tool-id",
                    "directional-retrieval-app-id",
                    "--output",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(
            written["nodes"][0]["inputs"][0]["value"],
            [
                {"id": "web-wrapper-app-id", "version": "", "config": {}},
                {"id": "directional-retrieval-app-id", "version": "", "config": {}},
            ],
        )
        self.assertEqual(json.loads(result.stdout)["credentials"], "not-read")

    def test_apply_updates_publishes_and_verifies_compact_payload(self):
        workflow = agent_workflow([])
        expected = [
            {"id": "web-wrapper-app-id", "version": "", "config": {}},
            {"id": "directional-retrieval-app-id", "version": "", "config": {}},
        ]
        read_back = {
            "data": {
                "modules": agent_workflow(expected)["nodes"],
                "edges": [],
                "chatConfig": {},
            }
        }
        responses = [read_back, None, None, read_back]
        argv = [
            "bind_fastgpt_agent_tools.py",
            "--workflow",
            "workflow.json",
            "--tool-id",
            "web-wrapper-app-id",
            "--tool-id",
            "directional-retrieval-app-id",
            "--api-url",
            "https://fastgpt.example",
            "--app-id",
            "agent-app-id",
            "--apply",
            "--publish",
        ]

        with tempfile.TemporaryDirectory() as directory:
            workflow_path = Path(directory) / "workflow.json"
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            argv[2] = str(workflow_path)
            with (
                patch.object(sys, "argv", argv),
                patch.dict(os.environ, {"FASTGPT_AUTH_TOKEN": "session-token"}),
                patch("create_fastgpt_app.request_json", side_effect=responses) as request,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(binding_module.main(), 0)

        self.assertEqual(request.call_count, 4)
        draft_payload = request.call_args_list[1].args[2]
        self.assertEqual(draft_payload["nodes"][0]["inputs"][0]["value"], expected)
        self.assertTrue(draft_payload["autoSave"])
        self.assertIn("version/publish", request.call_args_list[1].args[0])
        self.assertIn("version/publish", request.call_args_list[2].args[0])
        self.assertTrue(request.call_args_list[2].args[2]["isPublish"])


if __name__ == "__main__":
    unittest.main()
