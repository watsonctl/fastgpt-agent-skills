#!/usr/bin/env python3
"""Regression tests for the FastGPT flow-log exporter."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analyze_fastgpt_flow_logs import summarize_message

import export_fastgpt_flow_logs as exporter


class ExportFastGPTFlowLogsTest(unittest.TestCase):
    def test_export_preserves_persistent_total_quote_list(self) -> None:
        quote = {
            "id": "0123456789abcdef01234567",
            "datasetId": "dataset-1",
            "collectionId": "collection-1",
            "q": "条文正文",
        }
        records = [
            {
                "obj": "AI",
                "dataId": "message-1",
                "value": "依据 [0123456789abcdef01234567](CITE) 作答",
                "totalQuoteList": [quote],
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(
                exporter,
                "resolve_args",
                return_value=argparse.Namespace(
                    base_url="https://fastgpt.example",
                    api_key="test-key",
                    app_id="app-1",
                    export_dir=temp_dir,
                    page_size=50,
                    record_page_size=100,
                    max_chats=0,
                    chat_id="",
                    source="",
                    timeout=30,
                ),
            ), patch.object(
                exporter,
                "get_chat_histories",
                return_value=[{"chatId": "chat-1", "title": "测试对话", "updateTime": None}],
            ), patch.object(exporter, "get_chat_records", return_value=records), patch.object(
                exporter, "get_full_response_data", return_value=[]
            ):
                self.assertEqual(exporter.main(), 0)

            output_path = next(Path(temp_dir).glob("*.json"))
            exported = json.loads(output_path.read_text(encoding="utf-8"))

        message = exported[0]["messages"][0]
        self.assertEqual(message.get("totalQuoteList"), [quote])
        self.assertTrue(message.get("totalQuoteListPresent"))

    def test_export_marks_missing_persistent_total_quote_list_as_unavailable(self) -> None:
        records = [
            {
                "obj": "AI",
                "dataId": "message-1",
                "value": "没有持久引用字段",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(
                exporter,
                "resolve_args",
                return_value=argparse.Namespace(
                    base_url="https://fastgpt.example",
                    api_key="test-key",
                    app_id="app-1",
                    export_dir=temp_dir,
                    page_size=50,
                    record_page_size=100,
                    max_chats=0,
                    chat_id="",
                    source="",
                    timeout=30,
                ),
            ), patch.object(
                exporter,
                "get_chat_histories",
                return_value=[{"chatId": "chat-1", "title": "测试对话", "updateTime": None}],
            ), patch.object(exporter, "get_chat_records", return_value=records), patch.object(
                exporter, "get_full_response_data", return_value=[]
            ):
                self.assertEqual(exporter.main(), 0)

            output_path = next(Path(temp_dir).glob("*.json"))
            exported = json.loads(output_path.read_text(encoding="utf-8"))

        message = exported[0]["messages"][0]
        self.assertIsNone(message.get("totalQuoteList"))
        self.assertFalse(message.get("totalQuoteListPresent", False))

    def test_analyzer_uses_persistent_total_quote_list_for_frontend_cite_status(self) -> None:
        quote = {
            "id": "0123456789abcdef01234567",
            "datasetId": "dataset-1",
            "collectionId": "collection-1",
            "q": "条文正文",
        }
        summary = summarize_message(
            {"chatId": "chat-1", "title": "测试对话"},
            {
                "dataId": "message-1",
                "content": "依据 [0123456789abcdef01234567](CITE) 作答",
                "flowResponses": [
                    {
                        "moduleType": "pluginModule",
                        "moduleName": "定向检索工具",
                        "childrenResponses": [
                            {"moduleType": "datasetSearchNode", "quoteList": [quote]}
                        ],
                    }
                ],
                "totalQuoteList": [quote],
                "totalQuoteListPresent": True,
            },
        )

        citation = summary["citation"]
        self.assertTrue(citation.get("totalQuoteListPresent"))
        self.assertEqual(citation.get("totalQuoteListCount"), 1)
        self.assertEqual(citation.get("citeIdsMatchingTotalQuoteListCount"), 1)
        self.assertTrue(citation.get("frontendCitationAuthorized"))
        self.assertFalse(citation.get("nativeCitationRisk"))

    def test_analyzer_reports_persistent_cite_status_as_unknown_for_old_exports(self) -> None:
        summary = summarize_message(
            {"chatId": "chat-1", "title": "旧导出"},
            {
                "dataId": "message-1",
                "content": "依据 [0123456789abcdef01234567](CITE) 作答",
                "flowResponses": [],
            },
        )

        citation = summary["citation"]
        self.assertFalse(citation.get("totalQuoteListPresent", False))
        self.assertIsNone(citation.get("frontendCitationAuthorized"))

    def test_analyzer_distinguishes_empty_persistent_quote_list_from_missing_field(self) -> None:
        summary = summarize_message(
            {"chatId": "chat-1", "title": "空引用"},
            {
                "dataId": "message-1",
                "content": "依据 [0123456789abcdef01234567](CITE) 作答",
                "flowResponses": [],
                "totalQuoteList": [],
                "totalQuoteListPresent": True,
            },
        )

        citation = summary["citation"]
        self.assertTrue(citation["totalQuoteListPresent"])
        self.assertEqual(citation["totalQuoteListCount"], 0)
        self.assertFalse(citation["frontendCitationAuthorized"])


if __name__ == "__main__":
    unittest.main()
