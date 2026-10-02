"""Check discoverability of the single checkpoint contract, not model behavior."""
from pathlib import Path
import re
import unittest

CONTRACT = "references/workflow-checkpoints.md"
OPS_SKILL = "spec-guard-ops"


class CheckpointContractTests(unittest.TestCase):
    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        self.target = self.plugin / CONTRACT

    def live_surfaces(self):
        yield from (self.plugin / "commands").glob("*.md")
        yield from (self.plugin / "skills").glob("*/SKILL.md")
        yield from (self.plugin / "templates").glob("*.md")

    def test_every_checkpoint_instruction_reaches_the_contract(self):
        mentions = [path for path in self.live_surfaces() if "共享检查点规则" in path.read_text(encoding="utf-8")]
        self.assertTrue(mentions, "no live surface mentions the checkpoint contract")
        for path in mentions:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(CONTRACT in text or OPS_SKILL in text,
                                "must link the contract or name the skill that links it")

    def test_ops_skill_links_an_existing_contract(self):
        skill = self.plugin / "skills" / OPS_SKILL / "SKILL.md"
        links = re.findall(r"\]\(([^)]*workflow-checkpoints\.md)\)", skill.read_text(encoding="utf-8"))
        self.assertTrue(links, "spec-guard-ops must link the checkpoint contract")
        for link in links:
            self.assertEqual((skill.parent / link).resolve(), self.target.resolve())
        self.assertTrue(self.target.is_file())

    def test_templates_carry_the_instruction_and_contract_covers_stops(self):
        templates = list((self.plugin / "templates").glob("*-block-*.md"))
        self.assertTrue(templates)
        for path in templates:
            self.assertIn("检查点", path.read_text(encoding="utf-8"), str(path))
        text = self.target.read_text(encoding="utf-8")
        for scenario in ("设计 → 计划", "计划 → 实现", "实现 → 验证", "验证失败", "交付前",
                         "权限被拒绝", "结果未知", "取消或暂停"):
            self.assertIn(scenario, text)
        for rule in ("不重复", "最近一次", "失效", "无需确认"):
            self.assertIn(rule, text)

    def test_local_ticket_is_reconciled_after_pr_merge(self):
        template = (self.plugin.parents[1] / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        checkpoint = self.target.read_text(encoding="utf-8")
        ticket = (self.plugin / "skills" / "ticket" / "SKILL.md").read_text(encoding="utf-8")
        workflow = (self.plugin.parents[1] / "docs" / "workflow.md").read_text(encoding="utf-8")
        for phrase in ("Local 事项", "本 PR 覆盖范围", "私有 Local 事项不在公开 PR"):
            self.assertIn(phrase, template)
        for phrase in ("PR 创建后", "PR 合并后", "合并提交", "保持开放", "读回关闭状态"):
            self.assertIn(phrase, checkpoint)
        for phrase in ("PR 地址", "合并提交", "全部范围", "保持开放"):
            self.assertIn(phrase, ticket)
        self.assertIn("PR 合并后", workflow)

    def test_project_audit_handoff_is_discoverable_on_both_hosts(self):
        checkpoint = self.target.read_text(encoding="utf-8")
        for name in ("claude-block-local.md", "codex-block-local.md"):
            template = (self.plugin / "templates" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIn("项目级审查", template)
                self.assertIn("共享检查点规则", template)
        for phrase in ("项目级审查", "审查批次", "审查完成", "待调查", "P0", "继续"):
            self.assertIn(phrase, checkpoint)

    def test_audit_handoff_reuses_ticket_without_reviving_remote_bridge(self):
        checkpoint = self.target.read_text(encoding="utf-8")
        ticket = (self.plugin / "skills" / "ticket" / "SKILL.md").read_text(encoding="utf-8")
        workflow = (self.plugin.parents[1] / "docs" / "workflow.md").read_text(encoding="utf-8")
        for phrase in ("审查完成", "事项已入账", "Local", "GitHub/GitLab", "待入账"):
            self.assertIn(phrase, checkpoint)
        for phrase in ("审查批次", "查重", "待调查"):
            self.assertIn(phrase, ticket)
        for phrase in ("审查完成", "debugging-and-error-recovery", "todo.md"):
            self.assertIn(phrase, workflow)


if __name__ == "__main__":
    unittest.main()
