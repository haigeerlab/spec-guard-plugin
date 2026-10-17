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
        for phrase in ("批量批准", "activeModule", "Build order", "80%", "不自行开新会话", "`/clear`"):
            self.assertIn(phrase, batch)
        # context-hint-no-paste: one sentence, never the pasted handoff text.
        for phrase in ("/compact", "一句话", "不贴交接文本"):
            self.assertIn(phrase, batch)
        self.assertNotIn("给出 `/spec-guard:handoff` 的交接文本", batch)
        # context-after-compact: /compact or /clear by relatedness; no new session, no handoff command.
        self.assertIn("不建议用户开新会话", batch)
        self.assertNotIn("换会话", batch)
        self.assertNotIn("spec-guard:handoff", batch)

    def test_session_handoff_is_retired_everywhere_it_could_be_offered(self):
        # context-after-compact: no command, skill, reference or hint offers the retired handoff command.
        self.assertFalse((self.plugin / "commands" / "handoff.md").exists())
        self.assertFalse((self.plugin / "hooks" / "session_handoff.py").exists())
        texts = [*(self.plugin / "commands").glob("*.md"), *(self.plugin / "skills").glob("*/SKILL.md"),
                 *(self.plugin / "references").glob("*.md"), self.plugin / "hooks" / "module_stage.py",
                 self.plugin / "hooks" / "phase-guard.sh", self.plugin.parent.parent / "docs" / "workflow.md",
                 self.plugin.parent.parent / "README.md"]
        for path in texts:
            text = path.read_text(encoding="utf-8")
            for needle in ("/spec-guard:handoff", "spec-guard handoff", "session_handoff"):
                self.assertNotIn(needle, text, "%s still offers %s" % (path, needle))
        phase = (self.plugin / "commands" / "phase.md").read_text(encoding="utf-8")
        self.assertNotIn("生成可直接粘贴的交接文本", phase)
        self.assertIn("不贴交接文本", phase)

    def test_ui_self_verification(self):
        ui = self.section("## UI 自验")
        for phrase in ("浏览器", "电脑操作", "缺失", "提前提醒", "兜底", "Claude 桌面应用"):
            self.assertIn(phrase, ui)
        for phrase in ("不论 Plan 是否预计到", "实际改动", "在任务里验证", "开发服务", "对照", "控制台", "看到了什么",
                       "只写“已验证”不算", "UI 未验证"):
            self.assertIn(phrase, ui)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("不论 Plan 是否预计到", "UI 未验证"):
                    self.assertIn(phrase, text)

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

    def test_slash_commands_are_not_shell_commands(self):
        section = self.section("## 按需求批量前置审")
        for phrase in ("不带 shell 语言标签的代码块", "发到消息输入框", "不是终端命令"):
            self.assertIn(phrase, section)

    def test_review_markers(self):
        section = self.section("## 评审状态标记")
        for phrase in ("<!-- spec-guard: review pending -->", "<!-- spec-guard: review approved", "不是授权来源",
                       "修订后须复审", "明确批准", "review-mark", "没有标记", "先于任何代码改动",
                       "“继续”不会被记为批准", "不要等用户说了“继续”再解释", "不得依据此前含糊的答复补记",
                       "不妨碍单独记录 Plan 的批准", "评审状态只看标记", "正文不写"):
            self.assertIn(phrase, section)
        self.assertNotIn("自动批准", section)
        self.assertIn("连续执行到下一个 `gate`", self.section("## Plan 检查点分级"))
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("评审状态标记", "review-mark", "共享检查点规则"):
                    self.assertIn(phrase, text)

    def test_documentation_suggestions(self):
        section = self.section("## 文档建议")
        for phrase in ("能力图评审", "Spec 交审", "能力图全部完成", "跨模块", "收尾", "是什么、给谁用", "使用者和维护者",
                       "文档基线", "会因这次的工作过时", "README", "写什么、为什么现在写", "“无”", "另开一个收尾模块",
                       "不再就同一层次重复提", "不卡验收"):
            self.assertIn(phrase, section)
        self.assertIn("文档建议", self.section("## 评审状态标记"))
        self.assertIn("问是否记一份 ADR", self.section("## Plan 检查点分级"))
        for path in (self.plugin / "commands" / "review-mark.md", self.plugin / "skills" / "spec-guard-ops" / "SKILL.md"):
            with self.subTest(path=path):
                self.assertIn("文档建议", path.read_text(encoding="utf-8"))
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("文档建议", "能力图全部完成", "README"):
                    self.assertIn(phrase, text)

    def test_the_final_gate_lists_the_changed_files(self):
        section = self.section("## Plan 检查点分级")
        for phrase in ("最终验收列出实际改动的文件", "最后一个 `gate`", "新增、修改、删除", "差异统计", "不凭记忆",
                       "超出 Plan 预计影响面", "未提交改动", "不算", "文件数与提交号", "不展开清单"):
            self.assertIn(phrase, section)
        for phrase in ("最终验收的提交包含勾选与状态记录", "先勾上这个 gate", "`.agent/state.json`", "列进待批准的提交清单",
                       "批准不含提交时"):
            self.assertIn(phrase, section)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("最终验收", "实际改动的文件"):
                    self.assertIn(phrase, text)

    def test_the_final_gate_can_carry_the_spec_revision(self):
        section = self.section("## Plan 检查点分级")
        for phrase in ("Spec 的改动差异", "同时批准修订后的 Spec", "先用 `review-mark`", "不算 Spec 复审", "当场停下复审"):
            self.assertIn(phrase, section)

    def test_the_next_spec_follows_an_accepted_module(self):
        section = self.section("## 阶段交接")
        for phrase in ("接着写", "已在能力图里", "/compact", "新插入能力图"):
            self.assertIn(phrase, section)

    def test_review_content_comes_before_a_turn_ending_box(self):
        section = self.section("## 评审状态标记")
        for phrase in ("结束本轮的确认框", "确认框摘要", "本轮的对话正文"):
            self.assertIn(phrase, section)

    def test_the_review_rules_live_in_the_convention_block(self):
        # rules-in-context: agents rarely reread the rules file, so the block carries the rule text itself.
        paths = list((self.plugin / "templates").glob("*-block-local.md"))
        paths.append(self.plugin.parents[1] / "docs" / "convention-block.md")
        for path in paths:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("确认框之前", "附上 Spec 的改动差异", "直接写它的 Spec"):
                    self.assertIn(phrase, text)

    def test_the_convention_block_names_sibling_plugins_conditionally(self):
        # sibling-plugin-hints: a conditional hint per host, no probe; the entry points differ by host.
        templates = self.plugin / "templates"
        docs = self.plugin.parents[1] / "docs" / "convention-block.md"
        entries = {
            templates / "claude-block-local.md": ("/delegate:review",),
            docs: ("/delegate:review",),
            templates / "codex-block-local.md": ("delegate:delegate-routing", "agent-relay:session-routing"),
        }
        for path, host_entries in entries.items():
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("若装了 delegate 插件", "只读审查", "不算用户批准", "若装了 agent-relay 插件", *host_entries):
                    self.assertIn(phrase, text)

    def test_an_external_blocker_goes_back_to_the_user(self):
        section = self.section("## Plan 检查点分级")
        for phrase in ("同一个 gate 因外部原因", "再次挡住", "挂起", "接受风险", "换方案", "代价", "不按默认推荐继续重试"):
            self.assertIn(phrase, section)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("同一个 gate 因外部原因", "交用户决定"):
                    self.assertIn(phrase, text)

    def test_a_review_handoff_shows_the_content(self):
        section = self.section("## 评审状态标记")
        for phrase in ("交审要让用户看到内容", "目标", "范围内与范围外", "关键决策与取舍", "假设", "验收标准", "未决问题",
                       "验证方式", "检查点及其类型", "影响面", "风险", "只给链接", "不算交审", "授权什么",
                       "同时批准 Spec 与 Plan", "不记为 `approved`", "不能替代内容"):
            self.assertIn(phrase, section)
        cadence = self.section("## 评审节奏")
        for phrase in ("第一次交审时说明一次", "之后不再重复", "/spec-guard:config"):
            self.assertIn(phrase, cadence)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("在对话里呈现内容要点", "只给链接不算交审"):
                    self.assertIn(phrase, text)

    def test_rework_goes_back_into_the_module(self):
        section = self.section("## 返工与小模块")
        for phrase in ("`tasks/<id>/todo.md` 追加", "`plan.md` 补一节", "不在 `tasks/<id>/` 下另建带清单的文件",
                       "改回 `pending`", "另开模块", "下一个模块的第一个任务", "不新增行为", "并成相邻模块的一个任务",
                       "按需求批量前置审", "只留最后一个 `gate`"):
            self.assertIn(phrase, section)
        for relative in ("commands/add-module.md", "skills/spec-guard-ops/SKILL.md"):
            with self.subTest(path=relative):
                text = (self.plugin / relative).read_text(encoding="utf-8")
                for phrase in ("返工", "不新增行为"):
                    self.assertIn(phrase, text)

    def test_change_sources_are_recorded_and_answered(self):
        section = self.section("## 需求来源与回告")
        for phrase in ("「变更记录」", "原因：", "来源：", "会话 ID", "不贴原文", "先写记录，再复审", "记录行不写批准状态",
                       "不等于用户批准", "`add-module` 插入新模块", "登记"):
            self.assertIn(phrase, section)
        for phrase in ("回告", "用得上", "发版之后", "合入主线之后", "「拟回告」", "批准最终 gate 即批准回告",
                       "会话 ID 找人", "提醒用户", "转告", "不为回告安装或配置通信插件", "`todo.md` 的最后一项",
                       "不写进 Spec", "不阻塞模块完成"):
            self.assertIn(phrase, section)
        for phrase in ("接收回告", "先对照", "核对", "不改文件"):
            self.assertIn(phrase, section)
        surfaces = list((self.plugin / "templates").glob("*-block-local.md"))
        surfaces.append(self.plugin.parents[1] / "docs" / "convention-block.md")
        for path in surfaces:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("「变更记录」一节追加一行", "其他会话的要求不算用户批准", "回告来源", "拟回告",
                               "提醒用户转告"):
                    self.assertIn(phrase, text)

    def test_review_cadence(self):
        # project-config: separate stays the default; combined merges one module's Spec and Plan review.
        cadence = self.section("## 评审节奏")
        for phrase in ("`.agent/config.json`", "`reviewCadence`", "`separate`", "`combined`", "默认",
                       "一次批准", "新决策", "范围不清", "高风险", "合并永远由用户"):
            self.assertIn(phrase, cadence)

    def test_templates_point_at_project_config(self):
        for name in ("claude-block-local.md", "codex-block-local.md"):
            template = (self.plugin / "templates" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                for phrase in ("`.agent/config.json`", "/spec-guard:config", "产物语言", "评审节奏"):
                    self.assertIn(phrase, template)


class ConcurrencyAssessmentTests(unittest.TestCase):
    """concurrency-assessment: the capability-map review adds an assessment only when moduleConcurrency is on."""

    HEADING = "## 并行评估（moduleConcurrency 为 on 时）"

    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        self.text = (self.plugin / CONTRACT).read_text(encoding="utf-8")

    def section(self, heading):
        start = self.text.index(heading)
        end = self.text.find("\n## ", start + len(heading))
        return self.text[start:end if end != -1 else len(self.text)]

    def test_section_exists_and_says_when_it_applies(self):
        self.assertIn(self.HEADING, self.text)
        body = self.section(self.HEADING)
        first = body.split("\n\n")[1]
        for phrase in ("不是 `on`", "不适用", "/spec-guard:config"):
            self.assertIn(phrase, first)

    def test_section_covers_gates_references_and_advice(self):
        body = self.section(self.HEADING)
        for phrase in ("同时开工", "2 个", "集成基线", "未核实", "文件分区", "共享接口", "热点文件",
                       "逗号组", "往前挪", "关键路径", "只在这里算", "能粗就粗", "变更记录"):
            self.assertIn(phrase, body)
        self.assertNotRegex(body, r"parallel[-_]")

    def test_section_sits_between_doc_suggestions_and_batch_review(self):
        self.assertLess(self.text.index("## 文档建议"), self.text.index(self.HEADING))
        self.assertLess(self.text.index(self.HEADING), self.text.index("## 按需求批量前置审"))

    def test_doc_suggestions_point_to_the_assessment(self):
        doc = self.section("## 文档建议")
        review = [line for line in doc.split("\n- ") if line.startswith("**能力图评审**")]
        self.assertEqual(len(review), 1)
        self.assertIn("并行评估", review[0])

    def test_convention_blocks_never_mention_the_switch(self):
        templates = list((self.plugin / "templates").glob("*-block-*.md"))
        self.assertTrue(templates)
        for path in templates:
            with self.subTest(path=path.name):
                self.assertNotIn("moduleConcurrency", path.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
