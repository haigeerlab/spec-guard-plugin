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

    def test_open_commitments_are_recorded_when_the_ball_moves(self):
        # open-commitments: anything someone waits on is a ledger issue, written when the ball changes hands.
        section = self.section("## 未了的承诺")
        for phrase in ("收到那一刻", "`waiting-on-me`", "`waiting-on-them`", "`waiting-on-user`", "稳定身份",
                       "会话 ID", "只作", "来路与回路", "关闭条件", "球每换一次手", "不先判断",
                       "追问一次", "`未确认`", "不设固定天数", "不挡工作", "做出承诺", "对外通道", "草稿",
                       "内部通道", "直接发", "没启用账本", "`/spec-guard:local-ticket-ledger`", "隐私",
                       "公开远端", "不写私有项目名", "证据", "todo 末项"):
            self.assertIn(phrase, section)
        surfaces = list((self.plugin / "templates").glob("*-block-local.md"))
        surfaces.append(self.plugin.parents[1] / "docs" / "convention-block.md")
        for path in surfaces:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("在球换手时记进本地事项账本", "`waiting-on-me`／`waiting-on-them`／`waiting-on-user`",
                               "稳定身份与回复通道", "会替用户做出承诺的先问用户", "对外通道一律先在正文给草稿",
                               "内部会话间的告知直接发"):
                    self.assertIn(phrase, text)

    def test_one_module_per_review_and_grouped_by_module(self):
        # review-one-module: hand in one module at a time; when several are reviewed together, group them by module.
        markers = self.section("## 评审状态标记")
        for phrase in ("一次交审只放一个模块", "「一起发版」不等于「一起审」", "按模块分组", "Build order", "不按产物类型",
                       "不主动提议合并交审", "能力图评审"):
            self.assertIn(phrase, markers)
        self.assertIn("只在用户明确要求时", self.section("## 按需求批量前置审"))
        rework = self.section("## 返工与小模块")
        self.assertIn("用户也要求一次审完时", rework)
        self.assertNotIn("确需各自成模块时，用「按需求批量前置审」\n  一次交审", rework)
        self.assertIn("按模块分组", self.section("## 协调会话的批准与合并（moduleConcurrency 为 on 时）"))
        surfaces = list((self.plugin / "templates").glob("*-block-local.md"))
        surfaces.append(self.plugin.parents[1] / "docs" / "convention-block.md")
        for path in surfaces:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("交审一次只放一个模块", "并按模块分组", "不按产物类型横排", "一起发版不等于一起审"):
                    self.assertIn(phrase, text)

    def test_recording_on_receipt_is_not_accepting(self):
        # record-on-receipt: recording that someone waits needs no approval and is not taking the work on.
        section = self.section("## 未了的承诺")
        for phrase in ("记账不是受理", "不需要用户批准", "照样先记", "传 `repoRoot`"):
            self.assertIn(phrase, section)
        surfaces = list((self.plugin / "templates").glob("*-block-local.md"))
        surfaces.append(self.plugin.parents[1] / "docs" / "convention-block.md")
        for path in surfaces:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("当场记账，不用先问用户", "不是受理需求", "不受上面「确认要实现的需求先用",
                               "调用账本工具时传 `repoRoot` 为项目根目录"):
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


class ConcurrencyBoundaryTests(unittest.TestCase):
    """module-scope-boundary: the boundary section and the overreach mark apply only when moduleConcurrency is on."""

    HEADING = "## 并行边界（moduleConcurrency 为 on 时）"

    def setUp(self):
        self.text = (Path(__file__).resolve().parents[1] / CONTRACT).read_text(encoding="utf-8")

    def section(self):
        # The section carries a fenced example with its own `## 并行边界` heading, so end at the next real section.
        start = self.text.index(self.HEADING)
        return self.text[start:self.text.index("\n## 按需求批量前置审", start)]

    def test_section_place_and_scope(self):
        self.assertLess(self.text.index("## 并行评估（moduleConcurrency 为 on 时）"), self.text.index(self.HEADING))
        self.assertLess(self.text.index(self.HEADING), self.text.index("## 按需求批量前置审"))
        first = self.section().split("\n\n")[1]
        for phrase in ("不是 `on`", "不适用"):
            self.assertIn(phrase, first)

    def test_section_covers_format_check_and_handoff(self):
        body = self.section()
        for phrase in ("## 并行边界", "## Concurrency boundary", "独占", "公共", "全局配置", "锁文件", "迁移", "测试资源",
                       "hooks/module_scope.py\" check", "--base", "超出并行边界", "Spec 交审", "未完成", "verify-artifacts"):
            self.assertIn(phrase, body)
        self.assertNotRegex(body, r"parallel[-_]")

    def test_final_acceptance_points_to_the_boundary(self):
        start = self.text.index("- **最终验收列出实际改动的文件。**")
        rule = self.text[start:self.text.index("\n- **", start + 1)]
        self.assertIn("并行边界", rule)


class CoordinatorApprovalTests(unittest.TestCase):
    """concurrency-rule-wording: the coordinator's approval and local-merge exception, only when moduleConcurrency is on."""

    HEADING = "## 协调会话的批准与合并（moduleConcurrency 为 on 时）"
    ORIGINALS = (
        "- **`approved` 只在用户明确批准这份 Spec 或 Plan 之后，",
        "合并永远由用户进行，任何 Plan 都不能授权 agent 合并。",
        "两种节奏下人工闸门都在，合并永远由用户进行。",
    )

    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        self.text = (self.plugin / CONTRACT).read_text(encoding="utf-8")

    def section(self):
        start = self.text.index(self.HEADING)
        return self.text[start:self.text.index("\n## 按需求批量前置审", start)]

    def test_original_sentences_are_kept_verbatim(self):
        for sentence in self.ORIGINALS:
            self.assertEqual(self.text.count(sentence), 1, sentence)

    def test_section_place_and_scope(self):
        self.assertLess(self.text.index("## 并行边界（moduleConcurrency 为 on 时）"), self.text.index(self.HEADING))
        self.assertLess(self.text.index(self.HEADING), self.text.index("## 按需求批量前置审"))
        first = self.section().split("\n\n")[1]
        for phrase in ("不是 `on`", "不适用"):
            self.assertIn(phrase, first)

    def test_section_states_every_floor(self):
        body = self.section()
        for phrase in ("唯一例外", "三个条件", "同一时刻只有一个", "集成基线", "交审", "一致", "转达",
                       "模块分支", "集成分支", "提交", "重新", "一次只合一个", "Build order",
                       "不变基", "不压缩", "不强推", "新提交撤回", "不 reset", "停止后续合并", "不自动重试",
                       "不算完成", "冲突", "退回", "重新取得", "推送和远端合并", "只由用户"):
            self.assertIn(phrase, body)
        self.assertNotRegex(body, r"parallel[-_]")

    def test_coordinator_is_marked_by_checkout_role(self):
        body = self.section()
        for phrase in ("/spec-guard:checkout-role", "`coordinator`", "外部审查", "模块会话不提"):
            self.assertIn(phrase, body)

    def test_three_pointers(self):
        approved = self.text.index(self.ORIGINALS[0])
        rule_end = self.text.index("\n- **", approved + 1)
        self.assertIn("协调会话的批准与合并", self.text[approved:rule_end])
        for sentence in self.ORIGINALS[1:]:
            at = self.text.index(sentence) + len(sentence)
            self.assertIn("协调会话的批准与合并", self.text[at:self.text.index("\n", at)], sentence)

    def test_convention_blocks_untouched_by_the_switch(self):
        for path in (self.plugin / "templates").glob("*-block-*.md"):
            self.assertNotIn("moduleConcurrency", path.read_text(encoding="utf-8"), path.name)


class HubRelayedApprovalTests(unittest.TestCase):
    """hub-relayed-approval: `approved` accepts the user's words relayed in the session-protocol format, no lower bar."""

    HEADING = "## 经收件枢纽转来的批准"
    POINTER = "经收件枢纽转来的批准"

    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        self.text = (self.plugin / CONTRACT).read_text(encoding="utf-8")

    def section(self):
        start = self.text.index(self.HEADING)
        return self.text[start:self.text.index("\n## ", start + 1)]

    def test_section_sits_before_the_coordinator_section(self):
        self.assertLess(self.text.index(self.HEADING),
                        self.text.index("## 协调会话的批准与合并（moduleConcurrency 为 on 时）"))

    def test_section_states_every_condition(self):
        body = self.section()
        for phrase in ("【用户答复】", "事项号", "原消息号", "登记", "转自", "用户原话", "明确批准这一份",
                       "回显核对", "`#H`", "指纹", "重新交审", "不解析"):
            self.assertIn(phrase, body)

    def test_section_lists_what_does_not_count(self):
        body = self.section()
        for phrase in ("【答复告知】", "【协调通知】", "自称", "没有契约格式", "含糊", "模块会话"):
            self.assertIn(phrase, body)

    def test_approved_rule_names_both_sources(self):
        start = self.text.index("- **`approved` 只在用户明确批准这份 Spec 或 Plan 之后，")
        rule = self.text[start:self.text.index("\n- **", start + 1)]
        self.assertIn("当前对话", rule)
        self.assertIn(self.POINTER, rule)
        self.assertNotIn("用户于当前对话明确批准", self.text)

    def test_coordinator_section_points_here_and_keeps_module_sessions_out(self):
        start = self.text.index("**评审标记由协调会话写，先核对内容。**")
        body = self.text[start:self.text.index("**本地集成分支的合并。**", start)]
        first = body.split("\n- ")[1]
        self.assertIn(self.POINTER, first)
        self.assertNotIn("用户在协调会话里明确批准", self.text)
        self.assertIn("不能因此自己写 `approved`", body)

    def test_command_and_codex_skill_name_both_sources(self):
        for rel in ("commands/review-mark.md", "skills/spec-guard-ops/SKILL.md"):
            text = (self.plugin / rel).read_text(encoding="utf-8")
            with self.subTest(rel=rel):
                self.assertIn(self.POINTER, text)
                self.assertIn("当前对话", text)
                self.assertNotIn("用户于当前对话明确批准", text)
                self.assertNotIn("只在用户于当前对话明确批准之后写", text)


if __name__ == "__main__":
    unittest.main()
