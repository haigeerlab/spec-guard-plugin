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

    def test_a_merged_promotion_is_closed_out_not_just_relabelled(self):
        # 2026-10-07: #221 stayed open a day after its promotion merged because the docs
        # told people to change the label by hand, which closes nothing.
        checkpoint = self.target.read_text(encoding="utf-8")
        for phrase in ("Proposal 晋级 PR 合并后", "closeoutPending", "proposal-closeout",
                       "不会关闭事项"):
            self.assertIn(phrase, checkpoint)
        closeout = (self.plugin / "commands" / "proposal-closeout.md").read_text(encoding="utf-8")
        self.assertIn("proposal_closeout.py\" scan", closeout)
        self.assertIn("扫描结果不构成写入授权", closeout)
        proof = (self.plugin / "commands" / "proposal-promotion-proof.md").read_text(encoding="utf-8")
        self.assertIn("closeoutPending", proof)
        ops = (self.plugin / "skills" / "spec-guard-ops" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("proposal_closeout.py\" scan", ops)
        repo = self.plugin.parents[1]
        surfaces = list(self.live_surfaces()) + [repo / "docs" / "workflow.md"]
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for stale in ("由人工把 Issue 标签改为", "由人工把标签改为",
                          "再把 Issue 标为 `promoted`", "也可以继续只手工改标签"):
                self.assertNotIn(stale, text, path.name)
        release = repo / "docs" / "release-process.md"
        if release.exists():  # absent in an installed copy
            self.assertIn("proposal_closeout.py scan", release.read_text(encoding="utf-8"))

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


    # checkpoint-tiers: discoverability of the rules only -- whether a host follows them is checked in real sessions.

    def section(self, title):
        text = self.target.read_text(encoding="utf-8")
        self.assertIn(title, text)
        start = text.index(title)
        end = text.find("\n## ", start + len(title))
        return text[start:] if end < 0 else text[start:end]

    def test_plan_checkpoints_are_gate_or_report(self):
        tiers = self.section("## Plan 检查点分级")
        for phrase in ("`gate`", "`report`", "未标注的检查点按 `gate`", "记入 todo", "不倒计时",
                       "测试改不红", "权限被拒", "合并永远由用户"):
            self.assertIn(phrase, tiers)
        self.assertIn("`gate` 检查点写明的授权", self.section("## 阶段交接"))

    def test_batch_review_and_continuous_build(self):
        batch = self.section("## 按需求批量前置审")
        for phrase in ("批量批准", "activeModule", "Build order", "80%", "/spec-guard:handoff", "不自行开新会话"):
            self.assertIn(phrase, batch)
        # context-hint-no-paste: one sentence, never the pasted handoff text.
        for phrase in ("/compact", "一句话", "不贴交接文本"):
            self.assertIn(phrase, batch)
        self.assertNotIn("给出 `/spec-guard:handoff` 的交接文本", batch)
        phase = (self.plugin / "commands" / "phase.md").read_text(encoding="utf-8")
        self.assertNotIn("生成可直接粘贴的交接文本", phase)
        self.assertIn("不贴交接文本", phase)

    def test_ui_self_verification(self):
        ui = self.section("## UI 自验")
        for phrase in ("浏览器", "电脑操作", "缺失", "提前提醒", "兜底", "Claude 桌面应用"):
            self.assertIn(phrase, ui)

    def test_no_remote_write_is_authorized_by_default(self):
        text = self.target.read_text(encoding="utf-8")
        for phrase in ("默认授权推送", "默认授权开 PR", "默认推送", "自动合并"):
            self.assertNotIn(phrase, text)
        self.assertIn("只有当 Plan 的 `gate` 检查点逐项写明授权", self.section("## Plan 检查点分级"))

    def test_templates_point_at_checkpoint_tiers(self):
        for name in ("claude-block-local.md", "codex-block-local.md"):
            template = (self.plugin / "templates" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                for phrase in ("`gate`", "`report`", "批量前置审", "UI 自验", "共享检查点规则"):
                    self.assertIn(phrase, template)

if __name__ == "__main__":
    unittest.main()
