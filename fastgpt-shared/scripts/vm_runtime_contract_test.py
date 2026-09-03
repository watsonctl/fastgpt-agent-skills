#!/usr/bin/env python3
"""Structural guard for the FastGPT Skill/AgentV2 VM boundary contract."""

from pathlib import Path
import unittest


SKILL_PACK_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = SKILL_PACK_ROOT.parent


class VmRuntimeContractTest(unittest.TestCase):
    def test_shared_skill_routes_to_vm_runtime_contract(self) -> None:
        content = (SKILL_PACK_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/vm-runtime-contract.md", content)
        self.assertIn("VM-first", content)
        self.assertIn("macOS", content)
        self.assertIn("request-time", content)

    def test_vm_runtime_reference_declares_separate_execution_lanes(self) -> None:
        content = (SKILL_PACK_ROOT / "references" / "vm-runtime-contract.md").read_text(encoding="utf-8")
        for marker in (
            "Operator lane",
            "AgentV2 runtime lane",
            "target OS/architecture",
            "sips",
            "sharp",
            "curl",
            "no request-time install",
            "target VM",
        ):
            self.assertIn(marker, content)

    def test_authoring_standard_requires_vm_first_dependency_review(self) -> None:
        content = (SOURCE_ROOT / "SKILL_AUTHORING_STANDARD.md").read_text(encoding="utf-8")
        for marker in (
            "VM-first",
            "target OS/architecture",
            "macOS-only",
            "AgentV2 VM",
            "request-time install",
        ):
            self.assertIn(marker, content)

    def test_direct_fastgpt_entry_skills_route_to_the_same_vm_reference(self) -> None:
        for skill_name in ("fastgpt-workflow-debug", "fastgpt-workflow-generator"):
            content = (SOURCE_ROOT / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("../fastgpt-shared/references/vm-runtime-contract.md", content)

    def test_startup_script_contract_is_documented_for_beta5(self) -> None:
        shared = (SKILL_PACK_ROOT / "SKILL.md").read_text(encoding="utf-8")
        vm = (SKILL_PACK_ROOT / "references" / "vm-runtime-contract.md").read_text(encoding="utf-8")
        for marker in ("sandboxEntrypoint", "4.15.0-beta5", "SHA-256", "export", "跨命令"):
            self.assertIn(marker, vm)
        self.assertIn("sandboxEntrypoint", shared)

    def test_startup_script_guidance_is_routed_by_debug_generator_and_migration(self) -> None:
        for skill_name in (
            "fastgpt-workflow-debug",
            "fastgpt-workflow-generator",
            "fastgpt-workflow-migration",
        ):
            content = (SOURCE_ROOT / skill_name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("sandboxEntrypoint", content)
            self.assertIn("不写入", content)


if __name__ == "__main__":
    unittest.main()
