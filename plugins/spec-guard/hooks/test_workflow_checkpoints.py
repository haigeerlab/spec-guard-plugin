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
        for phrase in ("`gate`", "`report`", "没标级别的中间检查点按 `report`", "最后一个检查点", "记入 todo", "不倒计时",
                       "测试改不红", "权限被拒", "合并永远由用户"):
            self.assertIn(phrase, tiers)
        self.assertIn("`gate` 检查点写明的授权", self.section("## 阶段交接"))

    def test_checkpoint_forms_include_chinese(self):
        # cn-checkpoint-gates: the three recognised forms and what is not a checkpoint.
        tiers = self.section("## Plan 检查点分级")
        for phrase in ("`Checkpoint 1（report）`", "`检查点 1（report）`", "`最终验收（gate）`",
                       "既不以 `Checkpoint`／`检查点` 开头、冒号前又没标级别的待办项不算检查点"):
            self.assertIn(phrase, tiers)

    def test_checkpoint_default_is_report(self):
        tiers = self.section("## Plan 检查点分级")
        for phrase in ("没标级别的中间检查点按 `report`", "最后一个检查点没标级别时按 `gate`", "推送与不可逆操作的检查点必须标明 `gate`"):
            self.assertIn(phrase, tiers)
        surfaces = [self.target] + list((self.plugin / "templates").glob("*-block-local.md"))
        surfaces += [self.plugin / "skills" / "spec-guard-ops" / "SKILL.md", self.plugin / "commands" / "map.md",
                     self.plugin.parents[1] / "docs" / "workflow.md", self.plugin.parents[1] / "docs" / "convention-block.md",
                     self.plugin.parents[1] / "AGENTS.md"]
        for path in surfaces:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for retired in ("未标注的检查点按 `gate`", "未标注按 `gate`", "未标注的按 `gate`", "未标级别按 gate"):
                    self.assertNotIn(retired, text)

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
        for phrase in ("浏览器", "电脑操作", "缺失", "提前提醒", "Claude 桌面应用", "不能勾完成", "截图路径",
                       "开工时先确认", "并进最终验收"):
            self.assertIn(phrase, ui)
        self.assertNotIn("人做最后的兜底审查", ui)
        for phrase in ("不论 Plan 是否预计到", "实际改动", "在任务里验证", "开发服务", "对照", "控制台", "看到了什么",
                       "只写“已验证”不算", "UI 未验证"):
            self.assertIn(phrase, ui)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("不论 Plan 是否预计到", "UI 未验证", "不能勾完成"):
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
                for phrase in ("`gate`", "`report`", "UI 自验", "共享检查点规则", "停点规则"):
                    self.assertIn(phrase, template)

    def test_slash_commands_are_not_shell_commands(self):
        section = self.section("## 按需求批量前置审")
        for phrase in ("不带 shell 语言标签的代码块", "发到消息输入框", "不是终端命令"):
            self.assertIn(phrase, section)

    def test_review_markers(self):
        section = self.section("## 批准标记")
        for phrase in ("<!-- spec-guard: review pending -->", "<!-- spec-guard: review approved", "不是授权来源",
                       "范围内的修正", "明确批准", "review-mark", "没有标记", "先于任何代码改动",
                       "“继续”不会被记为批准", "不要等用户说了“继续”再解释", "不得依据此前含糊的答复补记",
                       "不妨碍单独记录 Plan 的批准", "批准状态只看标记", "正文不写"):
            self.assertIn(phrase, section)
        self.assertNotIn("自动批准", section)
        self.assertIn("连续执行到下一个 `gate`", self.section("## Plan 检查点分级"))
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("批准标记", "review-mark", "共享检查点规则"):
                    self.assertIn(phrase, text)

    def test_documentation_suggestions(self):
        section = self.section("## 文档建议")
        for phrase in ("能力图审阅", "Spec 交审", "能力图全部完成", "跨模块", "收尾", "是什么、给谁用", "使用者和维护者",
                       "文档基线", "会因这次的工作过时", "README", "写什么、为什么现在写", "“无”", "另开一个收尾模块",
                       "不再就同一层次重复提", "不卡验收", "有才提"):
            self.assertIn(phrase, section)
        self.assertIn("文档建议", self.section("## 批准标记"))
        self.assertIn("问是否记一份 ADR", self.section("## Plan 检查点分级"))
        for path in (self.plugin / "commands" / "review-mark.md", self.plugin / "skills" / "spec-guard-ops" / "SKILL.md"):
            with self.subTest(path=path):
                self.assertIn("文档建议", path.read_text(encoding="utf-8"))
        for title in ("## 能力图审阅", "## 最终验收"):
            with self.subTest(title=title):
                for phrase in ("文档建议", "README"):
                    self.assertIn(phrase, self.node_rules(title))
        self.assertIn("能力图全部完成", self.node_rules("## 最终验收"))
        self.assertIn("有才提", self.node_rules("## Spec 交审"))

    def test_the_final_gate_lists_the_changed_files(self):
        section = self.section("## Plan 检查点分级")
        for phrase in ("最终验收列出实际改动的文件", "最后一个 `gate`", "新增、修改、删除", "差异统计", "不凭记忆",
                       "超出 Plan 预计影响面", "未提交改动", "不算", "文件数与提交号", "不展开清单"):
            self.assertIn(phrase, section)
        for phrase in ("再列出本模块的提交", "提交号和一句话", "多时按任务归并", "写作待提交", "推上去的提交和这份清单不一致"):
            self.assertIn(phrase, section)
        for phrase in ("用表格（状态、文件、行数）", "单独一张表放在最前", "按用途判断、不按扩展名", "文档改动：无",
                       "一行写目录与文件数", "为什么加", "锁文件只写有没有改动和行数",
                       "新增依赖、锁文件改动：无", "对应任务", "放在最后一行"):
            self.assertIn(phrase, section)
        for phrase in ("最终验收的提交包含勾选与状态记录", "先勾上这个 gate", "`.agent/state.json`", "列进待批准的提交清单",
                       "批准不含提交时"):
            self.assertIn(phrase, section)
        final = self.node_rules("## 最终验收")
        for phrase in ("改了哪些文件用表格", "取自版本库", "本模块的提交", "与这份提交清单不一致的单独列出", "单独一张表放在最前",
                       "文档改动：无", "新增依赖、锁文件改动：无", "不含工作区自己的包"):
            self.assertIn(phrase, final)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("文件数与提交号", text)
                for moved in ("本模块的提交（提交号＋一句话）", "单独一张表放在最前"):
                    self.assertNotIn(moved, text)

    def test_plan_approval_authorizes_by_scope(self):
        tiers = self.section("## Plan 检查点分级")
        for phrase in ("批 Plan 按范围授权", "已批准范围", "构建需要的装包", "默认放行", "不按次数", "改本仓库文件",
                       "本地提交", "愿意写可以写", "只在这几类情况停下问用户", "改模块范围", "Spec 没覆盖的决定",
                       "删除工作区外的文件", "改全局配置", "外发凭据", "全局安装", "下载脚本直接执行",
                       "测试改不红", "权限被拒", "结果未知", "记一份 ADR", "一次列全过这个检查点所需的全部权限",
                       "新增的直接依赖", "锁文件", "工作区自己的包"):
            self.assertIn(phrase, tiers)
        host = self.section("## 权限、未知结果与取消")
        for phrase in ("宿主确认", "去哪个会话", "点什么", "不算问用户做决定"):
            self.assertIn(phrase, host)
        self.assertIn("Plan 开头列出验证所需的工具", self.section("## UI 自验"))
        retired = ("只问一次", "一条命令", "verify-artifacts` 会对照 Plan", "Plan 开头写「需要的外部条件」",
                   "Plan 没列的新依赖")
        surfaces = [("workflow-checkpoints", self.target.read_text(encoding="utf-8"))]
        surfaces += [(path.name, path.read_text(encoding="utf-8"))
                     for path in (self.plugin / "templates").glob("*-block-local.md")]
        for name, text in surfaces:
            for phrase in retired:
                with self.subTest(surface=name, phrase=phrase):
                    self.assertNotIn(phrase, text)
        for path in (self.plugin / "templates").glob("*-block-local.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("按已批准范围授权", "装包", "不按次数", "项目自己的规则更严时以项目为准", "宿主确认", "去哪个会话"):
                    self.assertIn(phrase, text)
                self.assertNotIn("需要的外部条件", text)

    def test_the_final_gate_can_carry_the_spec_revision(self):
        section = self.section("## Plan 检查点分级")
        for phrase in ("Spec 的改动差异", "同时批准修订后的 Spec", "先用 `review-mark`", "不算 Spec 复审", "当场停下复审"):
            self.assertIn(phrase, section)

    def test_the_next_spec_follows_an_accepted_module(self):
        section = self.section("## 阶段交接")
        for phrase in ("接着写", "已在能力图里", "/compact", "新插入能力图"):
            self.assertIn(phrase, section)

    def test_review_content_comes_before_a_turn_ending_box(self):
        section = self.section("## 批准标记")
        for phrase in ("结束本轮的确认框", "确认框摘要", "本轮的对话正文"):
            self.assertIn(phrase, section)

    def test_the_review_rules_reach_the_node(self):
        # rules-in-context put these three into the block; rules-at-nodes moves them into the stop rules the phase hint
        # attaches at the node, so they are still in that turn's context without sitting in every turn.
        for title in ("## Spec 交审", "## Plan 交审", "## 最终验收"):
            with self.subTest(title=title):
                self.assertIn("确认框之前", self.node_rules(title))
        final = self.node_rules("## 最终验收")
        for phrase in ("附上 Spec 的改动差异", "直接写它的 Spec"):
            self.assertIn(phrase, final)
        paths = list((self.plugin / "templates").glob("*-block-local.md"))
        paths.append(self.plugin.parents[1] / "docs" / "convention-block.md")
        for path in paths:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("确认框之前", "附上 Spec 的改动差异", "直接写它的 Spec"):
                    self.assertNotIn(phrase, text)
                self.assertIn("停在 gate 前、交审前或要停下问用户前", text)

    def test_the_stop_rules_name_sibling_plugins_conditionally(self):
        # sibling-plugin-hints: a conditional hint, no probe; the entry points differ by host. rules-at-nodes moved the
        # hints from the convention block to the nodes where they apply (review sections and the final acceptance).
        spec = self.node_rules("## Spec 交审")
        for phrase in ("若装了 delegate 插件", "只读审查", "不算用户批准", "「外部审查」一行"):
            self.assertIn(phrase, spec)
        # The stop rules reach both hosts, so they name no slash entry; the phase hint's own line names the host's.
        self.assertNotIn("/delegate:", self.node_rules())
        final = self.node_rules("## 最终验收")
        for phrase in ("若装了 agent-relay 插件", "agent-relay:session-routing", "提醒用户转告"):
            self.assertIn(phrase, final)

    def test_user_facing_text_uses_the_shared_terms(self):
        # display-terms: 审查 for technical checks, 批准 for the user's decision, 验收 for the final acceptance.
        # Current product text only; spec/, tasks/, CHANGELOG and docs/ subdirectories are records and stay as written.
        repo = self.plugin.parents[1]
        files = [path for folder in ("commands", "skills", "templates", "references")
                 for path in sorted((self.plugin / folder).rglob("*.md"))]
        files += [path for path in sorted((self.plugin / "hooks").iterdir())
                  if path.suffix in (".py", ".sh") and not path.name.startswith("test")]
        files += [repo / "README.md", repo / "README.en.md", repo / "AGENTS.md", repo / "CLAUDE.md"]
        files += sorted((repo / "docs").glob("*.md"))
        found = []
        for path in files:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for word in ("评审", "审核", "审批"):
                    if word in line:
                        found.append("%s:%d %s" % (path.relative_to(repo), number, word))
        self.assertEqual(found, [], "\n".join(found))

    def node_rules(self, title=None):
        # rules-at-nodes: the stop rules moved out of the convention block into node-rules.md, one section per node.
        text = (self.plugin / "references" / "node-rules.md").read_text(encoding="utf-8")
        if title is None:
            return text
        start = text.index(title + "\n")
        end = text.find("\n## ", start + len(title))
        return text[start:] if end < 0 else text[start:end]

    def block_surfaces(self):
        # stop-rule-and-ac: every copy of the convention block, including this repository's own AGENTS.md.
        yield from (self.plugin / "templates").glob("*-block-local.md")
        yield self.plugin.parents[1] / "docs" / "convention-block.md"
        yield self.plugin.parents[1] / "AGENTS.md"

    def test_an_external_blocker_goes_back_to_the_user(self):
        # stop-rule-and-ac: the same module and goal, not the same gate; a rewording or a new one-off permission is no new goal.
        contract = self.target.read_text(encoding="utf-8")
        section = self.section("## Plan 检查点分级")
        for phrase in ("同一模块、同一目标", "第二次过不去", "第二次为它向用户报批", "自己能修", "换一份草稿", "一次性许可",
                       "/spec-guard:map", "可以开始", "module-suspend", "没有就照实说", "接受风险", "换方案", "代价",
                       "不按默认推荐继续重试"):
            self.assertIn(phrase, section)
        self.assertNotIn("同一个 gate 因外部原因", contract)
        gate = self.node_rules("## 中途 gate")
        for phrase in ("同一模块、同一目标", "第二次", "报批", "先开可开工模块", "由用户决定"):
            self.assertIn(phrase, gate)
        for path in self.block_surfaces():
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("同一模块、同一目标", text)
                self.assertNotIn("同一个 gate 因外部原因", text)

    def test_checks_a_script_can_judge_may_be_report(self):
        # stop-rule-and-ac said the default stays gate; checkpoint-default-report (user decision 66) replaces that:
        # untiered middle checkpoints are reports, the last one is the final acceptance gate.
        tiers = self.section("## Plan 检查点分级")
        for phrase in ("没标级别的中间检查点按 `report`", "最后一个检查点没标级别时按 `gate`", "最终验收",
                       "推送与不可逆操作的检查点必须标明 `gate`", "交审 Plan 时说明哪些检查点是 `gate`"):
            self.assertIn(phrase, tiers)
        for path in self.block_surfaces():
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("没标级别的中间检查点按 `report`", "最后一个检查点按 `gate`", "推送与不可逆操作须标 `gate`"):
                    self.assertIn(phrase, text)

    def test_acceptance_criteria_are_numbered(self):
        # stop-rule-and-ac: AC1, AC2… so the final acceptance can match evidence to each one.
        self.assertIn("验收标准（按 AC1、AC2… 编号）", self.section("## 批准标记"))
        contract = self.target.read_text(encoding="utf-8")
        for phrase in ("**验收标准编号。**", "`AC<数字>`", "删掉的编号不复用", "按编号逐条给证据", "推荐写法"):
            self.assertIn(phrase, contract)
        self.assertNotIn("对未完成模块缺编号只提示", contract)  # align-upstream-rules: no verify-artifacts hint
        self.assertIn("AC1、AC2", self.node_rules("## Spec 交审"))
        self.assertIn("按 AC 编号逐条给证据", self.node_rules("## 最终验收"))
        for path in self.block_surfaces():
            with self.subTest(path=path):
                self.assertNotIn("AC1、AC2", path.read_text(encoding="utf-8"))

    def test_a_review_handoff_shows_the_content(self):
        section = self.section("## 批准标记")
        for phrase in ("交审要让用户看到内容", "目标", "总是做、先问、不做三档", "关键决策与取舍", "假设", "验收标准", "未决问题",
                       "验证方式", "检查点及其类型", "影响面", "风险", "只给链接", "不算交审", "授权什么",
                       "同时批准 Spec 与 Plan", "不记为 `approved`", "不能替代内容"):
            self.assertIn(phrase, section)
        cadence = self.section("## 批准节奏")
        for phrase in ("第一次交审时说明一次", "之后不再重复", "/spec-guard:config"):
            self.assertIn(phrase, cadence)
        for title in ("## 能力图审阅", "## Spec 交审"):
            with self.subTest(title=title):
                for phrase in ("本轮对话正文里", "只给链接"):
                    self.assertIn(phrase, self.node_rules(title))

    # review-card-sections: the sections of each kind, in the order of the decision-inbox card template.
    CARD_SECTIONS = (
        ("能力图审阅：", ("拆成哪些模块", "先后顺序", "文档建议")),
        ("Spec：", ("目标", "边界", "要你确认的假设", "验收标准", "未决问题")),
        ("Plan：", ("架构决定", "分几步", "会改哪些文件", "风险", "中途会停下来问你的地方", "未决问题")),
        ("中途 gate：", ("做到哪了", "为什么停在这", "接下来要做的那一步")),
        ("最终验收：", ("做了什么", "验收结果", "改了哪些文件", "Spec 中途改过吗")),
    )

    def handoff_item(self, title, following):
        section = self.section("## 批准标记")
        start = section.index(title)
        return section[start:section.index(following, start)]

    def test_review_sections_follow_the_card_order(self):
        item = self.handoff_item("**交审要让用户看到内容。**", "**验收标准编号。**")
        labels = [label for label, _ in self.CARD_SECTIONS]
        for index, (label, names) in enumerate(self.CARD_SECTIONS):
            with self.subTest(kind=label):
                start = item.index("  - " + label)
                end = item.index("  - " + labels[index + 1]) if index + 1 < len(labels) else item.index("\n\n", start)
                line = item[start:end]
                positions = [line.find(name) for name in names]
                self.assertNotIn(-1, positions, line)
                self.assertEqual(positions, sorted(positions), line)
        for phrase in ("逐条全列", "照旧用表格", "不为了短而删减", "新插入的标「新」", "开头的五件事落在这几项里",
                       "“注意：”", "“批了会怎样：”", "没有写“无”", "Spec 的五项再接 Plan 的六项", "`reviewKinds`",
                       "session-protocol 契约的交审小项", "总是做、先问、不做三档",
                       "旧名「做／不做」「附带的小决定」照认"):
            self.assertIn(phrase, item)

    def test_how_to_approve_uses_one_copy_block(self):
        item = self.handoff_item("**交审时说明怎么批准。**", "**没有标记的文件判定照旧**")
        for phrase in ("每个选项写清选了之后会怎样", "能不能撤回", "还要另外问用户", "“推荐理由：”", "可复制代码块",
                       "不带 shell 语言标签", "不用行内代码", "最短的可接受说法", "待定问题接在后面", "有代码块就是要用户回答",
                       "不需要回答的内容", "不用代码块", "“继续”不会被记为批准", "不能替代内容"):
            self.assertIn(phrase, item)
        # rules-at-nodes C8: session-protocol v2.6 copy blocks -- one matter per block, the shortest answer.
        for phrase in ("一块只答一件事", "“C16 A”", "“C16 A；C16-1 B”", "“批准；Q1 A”", "Q1、Q2", "另一种选择单独一块",
                       "不出带占位符的块", "推翻或重申", "不用 C、D、T、R 开头"):
            self.assertIn(phrase, item)
        self.assertNotIn("批准；D1 A", item)
        # sibling-rules-out: where the user answers is left to the installed collaboration plugin, named by no plugin.
        self.assertIn("所装协作插件对在哪里答复另有规定时", item)
        self.assertIn("复制块按它的规定放或不放", item)
        stuck = self.section("## Plan 检查点分级")
        for phrase in ("“出了什么事：”", "代价是什么", "可复制代码块"):
            self.assertIn(phrase, stuck)

    def test_mirrors_follow_the_card_sections(self):
        for relative in ("commands/review-mark.md", "skills/spec-guard-ops/SKILL.md", "../../docs/commands.md"):
            with self.subTest(path=relative):
                text = (self.plugin / relative).read_text(encoding="utf-8")
                for phrase in ("可复制代码块", "不会被记为批准", "以所装协作插件的规定为准"):
                    self.assertIn(phrase, text)
        for relative in ("commands/review-mark.md", "skills/spec-guard-ops/SKILL.md"):
            with self.subTest(path=relative):
                text = (self.plugin / relative).read_text(encoding="utf-8")
                for phrase in ("边界", "要你确认的假设", "未决问题", "架构决定", "批了会怎样", "一块只答一件事", "批准；Q1 A"):
                    self.assertIn(phrase, text)
                for retired in ("做／不做（范围内与范围外）", "附带的小决定（未决问题"):
                    self.assertNotIn(retired, text)

    def test_rework_goes_back_into_the_module(self):
        section = self.section("## 返工与小模块")
        for phrase in ("`tasks/<id>/todo.md` 追加", "`plan.md` 补一节", "不在 `tasks/<id>/` 下另建带清单的文件",
                       "不改回 `pending`", "另开模块", "下一个模块的第一个任务", "不新增行为", "并成相邻模块的一个任务",
                       "按需求批量前置审", "只留最后一个 `gate`"):
            self.assertIn(phrase, section)
        for relative in ("commands/add-module.md", "skills/spec-guard-ops/SKILL.md"):
            with self.subTest(path=relative):
                text = (self.plugin / relative).read_text(encoding="utf-8")
                for phrase in ("返工", "不新增行为"):
                    self.assertIn(phrase, text)

    def test_rules_follow_upstream_agent_skills(self):
        # align-upstream-rules (user decision 66): in-scope fixes and additions do not stop the build.
        contract = self.target.read_text(encoding="utf-8")
        for phrase in ("范围内的修正", "改范围、改方向或需要新取舍", "最终验收时附上 Spec 的改动差异", "范围内增补",
                       "启动本地开发服务、用浏览器打开本地页面验证"):
            self.assertIn(phrase, contract)
        for retired in ("把 Plan 的批准标记改回 `pending`", "人做最后的兜底审查", "构建途中的修改若会改变后续任务的做法"):
            self.assertNotIn(retired, contract)
        for path in self.block_surfaces():
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for phrase in ("范围内修正", "最终验收附差异"):
                    self.assertIn(phrase, text)

    def test_change_sources_are_recorded_and_answered(self):
        section = self.section("## 需求来源与回告")
        for phrase in ("「变更记录」", "原因：", "来源：", "会话 ID", "不贴原文", "先写记录，再呈现", "记录行不写批准状态",
                       "不等于用户批准", "`add-module` 插入新模块", "登记"):
            self.assertIn(phrase, section)
        for phrase in ("回告", "用得上", "发版之后", "合入主线之后", "「拟回告」", "批准最终 gate 即同意按这段文字发送",
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
                for phrase in ("「变更记录」一节追加一行", "其他会话的要求不算用户批准"):
                    self.assertIn(phrase, text)
        for phrase in ("拟回告", "来源是他人", "提醒用户转告"):
            self.assertIn(phrase, self.node_rules("## 最终验收"))

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
        markers = self.section("## 批准标记")
        for phrase in ("一次交审只放一个模块", "「一起发版」不等于「一起审」", "按模块分组", "Build order", "不按产物类型",
                       "不主动提议合并交审", "能力图审阅"):
            self.assertIn(phrase, markers)
        self.assertIn("只在用户明确要求时", self.section("## 按需求批量前置审"))
        rework = self.section("## 返工与小模块")
        self.assertIn("用户也要求一次审完时", rework)
        self.assertNotIn("确需各自成模块时，用「按需求批量前置审」\n  一次交审", rework)
        self.assertIn("按模块分组", self.section("## 协调会话的批准与合并（moduleConcurrency 为 on 时）"))
        spec = self.node_rules("## Spec 交审")
        for phrase in ("一次交审只放一个模块", "按模块分组", "不按产物类型横排", "一起发版不等于一起审"):
            self.assertIn(phrase, spec)
        for path in self.block_surfaces():
            with self.subTest(path=path):
                self.assertNotIn("交审一次只放一个模块", path.read_text(encoding="utf-8"))

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
        cadence = self.section("## 批准节奏")
        for phrase in ("`.agent/config.json`", "`reviewCadence`", "`separate`", "`combined`", "默认",
                       "一次批准", "新决策", "范围不清", "高风险", "合并永远由用户"):
            self.assertIn(phrase, cadence)

    def test_the_convention_block_is_short(self):
        # rules-at-nodes AC1: the block keeps the resident sentences, the stop rules sit in node-rules.md.
        for name, limit in (("claude-block-local.md", 4000), ("codex-block-local.md", 3800)):
            path = self.plugin / "templates" / name
            with self.subTest(name=name):
                self.assertLessEqual(len(path.read_bytes()), limit)
                text = path.read_text(encoding="utf-8")
                for phrase in ("`report` 检查点把验证结果记入 todo 后继续", "推送与不可逆操作须标 `gate`、到了要停",
                               "停在 gate 前、交审前或要停下问用户前", "能力图审阅、Spec 交审、Plan 交审、中途 gate、最终验收",
                               "项目自己的规则更严时以项目为准", "文件数与提交号", "`pending`", "`approved`"):
                    self.assertIn(phrase, text)

    def test_templates_point_at_project_config(self):
        for name in ("claude-block-local.md", "codex-block-local.md"):
            template = (self.plugin / "templates" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                for phrase in ("`.agent/config.json`", "/spec-guard:config", "产物语言", "批准节奏"):
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
        review = [line for line in doc.split("\n- ") if line.startswith("**能力图审阅**")]
        self.assertEqual(len(review), 1)
        self.assertIn("并行评估", review[0])

    def test_convention_blocks_never_mention_the_switch(self):
        templates = list((self.plugin / "templates").glob("*-block-*.md"))
        self.assertTrue(templates)
        for path in templates:
            with self.subTest(path=path.name):
                self.assertNotIn("moduleConcurrency", path.read_text(encoding="utf-8"))

    # batch-insert-concurrency-hint (D20): one assessment after a batch of add-module inserts.
    def test_section_covers_a_batch_insert(self):
        body = self.section(self.HEADING)
        for phrase in ("**批量插入之后。**", "2 个及以上", "同一个需求", "最后一个", "只评估一次", "不建议并行",
                       "插入单个模块不评估"):
            self.assertIn(phrase, body)
        self.assertNotIn("插入单个模块不算能力图审阅", body)

    def test_batch_insert_names_module_crew_only_when_usable(self):
        body = self.section(self.HEADING)
        for phrase in ("module-crew", "crew-coordinator", "协调会话", "角色", "只给 Build order 建议"):
            self.assertIn(phrase, body)

    def test_add_module_points_to_the_batch_assessment(self):
        command = (self.plugin / "commands" / "add-module.md").read_text(encoding="utf-8")
        skill = (self.plugin / "skills" / "spec-guard-ops" / "SKILL.md").read_text(encoding="utf-8")
        start = skill.index("## add-module")
        skill_section = skill[start:skill.index("\n## ", start + 1)]
        for name, text, config in (("add-module.md", command, "/spec-guard:config"),
                                   ("SKILL.md", skill_section, "`spec-guard-ops` 的 config")):
            with self.subTest(surface=name):
                for phrase in ("2 个及以上", "moduleConcurrency", "批量插入之后", config):
                    self.assertIn(phrase, text)

    def test_stop_rules_never_mention_the_switch(self):
        rules = (self.plugin / "references" / "node-rules.md").read_text(encoding="utf-8")
        for phrase in ("moduleConcurrency", "module-crew"):
            self.assertNotIn(phrase, rules)


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
                       "模块分支", "集成分支", "提交", "重新", "不改写已推送或已被同步的历史", "由运行时",
                       "重新取得", "推送和远端合并", "只由用户"):
            self.assertIn(phrase, body)
        self.assertNotRegex(body, r"parallel[-_]")

    def test_section_leaves_merge_steps_to_the_runtime(self):
        # sibling-rules-out (D8): how to merge, check and recover belongs to the runtime, not to spec-guard.
        body = self.section()
        for phrase in ("新提交撤回", "不 reset", "一次只合一个", "合并后跑"):
            self.assertNotIn(phrase, body)

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


class SiblingRulesOutTests(unittest.TestCase):
    """sibling-rules-out: rules that only make sense with a sibling plugin installed live in that plugin, not here (D2, D8, D9)."""

    GENERAL = "以所装协作插件的规定为准"
    SURFACES = (CONTRACT, "commands/review-mark.md", "skills/spec-guard-ops/SKILL.md", "../../docs/commands.md",
                "../../docs/workflow.md")

    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        self.text = (self.plugin / CONTRACT).read_text(encoding="utf-8")

    def test_no_hub_wording_or_relayed_approval_conditions(self):
        for rel in self.SURFACES:
            text = (self.plugin / rel).read_text(encoding="utf-8")
            with self.subTest(rel=rel):
                for phrase in ("收件枢纽", "去决策收件箱答", "经收件枢纽转来的批准"):
                    self.assertNotIn(phrase, text)
                self.assertIn(self.GENERAL, text)
        self.assertNotIn("总协调", self.text)

    def test_approved_rule_keeps_one_general_source_sentence(self):
        start = self.text.index("- **`approved` 只在用户明确批准这份 Spec 或 Plan 之后，")
        rule = self.text[start:self.text.index("\n- **", start + 1)]
        self.assertIn("批准来源以所装协作插件的规定为准；没装只认当前对话里的明确批准", rule)
        self.assertNotIn("用户于当前对话明确批准", self.text)

    def test_coordinator_section_keeps_module_sessions_out(self):
        start = self.text.index("**批准标记由协调会话写，先核对内容。**")
        body = self.text[start:self.text.index("**本地集成分支的合并。**", start)]
        self.assertIn("按所装协作插件的规定转来", body.split("\n- ")[1])
        self.assertNotIn("用户在协调会话里明确批准", self.text)
        self.assertIn("不能因此自己写 `approved`", body)

    def test_command_and_codex_skill_keep_the_current_conversation(self):
        for rel in ("commands/review-mark.md", "skills/spec-guard-ops/SKILL.md"):
            text = (self.plugin / rel).read_text(encoding="utf-8")
            with self.subTest(rel=rel):
                self.assertIn("当前对话", text)
                self.assertNotIn("用户于当前对话明确批准", text)
                self.assertNotIn("只在用户于当前对话明确批准之后写", text)

    def test_module_concurrency_does_not_control_the_coordinator(self):
        for rel in ("commands/config.md", "skills/spec-guard-ops/SKILL.md"):
            text = (self.plugin / rel).read_text(encoding="utf-8")
            line = next(line for line in text.splitlines() if "`moduleConcurrency`" in line and "`off`" in line)
            with self.subTest(rel=rel):
                self.assertIn("不控制协调会话", line)
                self.assertIn("`coordinator up`", line)

    def test_convention_blocks_carry_no_hub_wording(self):
        for path in (self.plugin / "templates").glob("*-block-*.md"):
            self.assertNotIn("收件枢纽", path.read_text(encoding="utf-8"), path.name)


class NodeRulesTests(unittest.TestCase):
    """rules-at-nodes: the stop rules the phase hint attaches at each node, kept in step with the full contract."""
    TITLES = ("## 能力图审阅", "## Spec 交审", "## Plan 交审", "## 中途 gate", "## 最终验收")
    LIMITS = {"## 最终验收": 3200}
    # What each section must say (Spec C2).
    ELEMENTS = {
        "## 能力图审阅": ("需求说完了吗？还有要补充的吗？", "拆成哪些模块", "先后顺序", "文档建议", "README", "确认框之前",
                      "只给链接", "不算合并交审", "可复制代码块", "以所装协作插件的规定为准"),
        "## Spec 交审": ("目标", "边界", "总是做", "先问", "不做", "要你确认的假设", "验收标准", "AC1、AC2", "未决问题", "确认框之前",
                       "一块只答一件事", "批准；Q1 A",
                       "只给链接", "“注意：”", "“批了会怎样：”", "`pending`", "review-mark", "一次交审只放一个模块",
                       "按模块分组", "delegate", "不算用户批准", "可复制代码块", "以所装协作插件的规定为准", "有才提"),
        "## Plan 交审": ("架构决定", "分几步", "会改哪些文件", "风险", "中途会停下来问你的地方", "`gate`", "`report`", "推送与开 PR",
                       "`combined`", "批 Plan 按范围授权", "项目自己的规则更严时，以项目为准", "只在这几类情况停下问用户",
                       "测试改不红", "权限被拒", "同一模块、同一目标"),
        "## 中途 gate": ("做到哪了", "为什么停在这", "接下来要做的那一步", "开头的五件事落在这几项里", "同一模块、同一目标",
                       "“出了什么事：”", "不按默认推荐继续重试", "宿主确认", "去哪个会话"),
        "## 最终验收": ("做了什么", "验收结果", "改了哪些文件", "Spec 中途改过吗", "按 AC 编号逐条给证据", "单独一张表放在最前",
                      "文档改动：无", "本模块的提交", "新增依赖、锁文件改动：无", "超出 Plan 预计影响面", "Spec 的改动差异",
                      "同时批准修订后的 Spec", "先用 review-mark", "拟回告", "可以原样发送的完整文字", "对外渠道同样",
                      "重新给用户看", "agent-relay", "截图", "先勾这个 gate", "直接写它的 Spec", "/compact"),
    }
    # Phrases each section shares word for word with workflow-checkpoints.md, so the summary cannot drift from the contract.
    SHARED = {
        "## 能力图审阅": ("需求说完了吗？还有要补充的吗？", "拆成哪些模块", "新插入的标「新」", "不算合并交审"),
        "## Spec 交审": ("要你确认的假设", "逐条全列", "不为了短而删减", "“继续”不会被记为批准", "一次交审只放一个模块",
                       "按模块分组", "可复制代码块", "没装只认当前对话里的明确批准"),
        "## Plan 交审": ("中途会停下来问你的地方", "没有中途 `gate` 写“无，做完直接交", "只在这几类情况停下问用户",
                       "删除工作区外的文件", "下载脚本直接执行", "测试改不红"),
        "## 中途 gate": ("接下来要做的那一步", "开头的五件事落在这几项里", "不按默认推荐继续重试", "去哪个会话"),
        "## 最终验收": ("单独一张表放在最前", "文档改动：无", "新增依赖、锁文件改动：无", "超出 Plan 预计影响面",
                      "可以原样发送的完整文字", "同意按这段文字发送", "重新给用户看", "同时批准修订后的 Spec"),
    }

    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        self.rules = (self.plugin / "references" / "node-rules.md").read_text(encoding="utf-8")
        self.contract = (self.plugin / CONTRACT).read_text(encoding="utf-8")

    def section(self, title):
        start = self.rules.index(title + "\n")
        end = self.rules.find("\n## ", start + len(title))
        return self.rules[start:] if end < 0 else self.rules[start:end]

    def test_five_sections_in_order_and_the_contract_wins(self):
        positions = [self.rules.index(title + "\n") for title in self.TITLES]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(self.rules.count("\n## "), len(self.TITLES))
        self.assertIn("[共享检查点规则](workflow-checkpoints.md)", self.rules)
        self.assertIn("以后者为准", self.rules)

    def test_each_section_stays_small(self):
        for title in self.TITLES:
            with self.subTest(title=title):
                self.assertLessEqual(len(self.section(title).encode("utf-8")), self.LIMITS.get(title, 2600))

    def test_each_section_carries_its_rules(self):
        for title, phrases in self.ELEMENTS.items():
            text = self.section(title)
            for phrase in phrases:
                with self.subTest(title=title, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_sections_share_their_wording_with_the_contract(self):
        for title, phrases in self.SHARED.items():
            text = self.section(title)
            for phrase in phrases:
                with self.subTest(title=title, phrase=phrase):
                    self.assertIn(phrase, text)
                    self.assertIn(phrase, self.contract)

    def test_each_review_item_names_its_upstream_chapter(self):
        # C105 / C7: every review item points at the agent-skills chapter it follows; unmatched ones are only appended.
        start = self.contract.index("**交审要让用户看到内容。**")
        item = self.contract[start:self.contract.index("**验收标准编号。**", start)]
        for chapter in ("Objective", "Boundaries", "ASSUMPTIONS", "Success Criteria", "Open Questions", "Capability Map",
                        "Build order", "Architecture Decisions", "Files likely touched", "Risks and Mitigations",
                        "Checkpoint", "Keeping the Spec Alive", "附加"):
            with self.subTest(chapter=chapter):
                self.assertIn(chapter, item)
        for phrase in ("对应上游的哪一节", "只能作为附加项追加", "以上游为准"):
            self.assertIn(phrase, item)
        for title, chapters in (("## Spec 交审", ("Objective", "Boundaries", "ASSUMPTIONS", "Success Criteria", "Open Questions")),
                                ("## Plan 交审", ("Architecture Decisions", "Checkpoint", "Open Questions")),
                                ("## 能力图审阅", ("Capability Map", "Build order"))):
            text = self.section(title)
            for chapter in chapters:
                with self.subTest(title=title, chapter=chapter):
                    self.assertIn("上游 " + chapter, text)

    def test_contract_points_at_the_stop_rules(self):
        head = self.contract[:self.contract.index("1. 已完成的具体成果")]
        self.assertIn("[停点规则](node-rules.md)", head)
        self.assertIn("以本文件为准", head)

    def test_plan_approval_yields_to_stricter_project_rules(self):
        # D19 1: the project's own rules win when they are stricter.
        tiers = self.contract[self.contract.index("## Plan 检查点分级"):self.contract.index("## 批准节奏")]
        item = tiers[tiers.index("**批 Plan 按范围授权。**"):tiers.index("**最终验收列出实际改动的文件。**")]
        self.assertIn("项目自己的规则（项目的 `CLAUDE.md`／`AGENTS.md`、项目约定）比这里更严时，以项目为准", item)

    def test_the_planned_answer_is_the_full_text(self):
        # D19 2: the final gate lists the exact words to send; approving the gate agrees to send them.
        section = self.contract[self.contract.index("## 需求来源与回告"):self.contract.index("## 未了的承诺")]
        for phrase in ("可以原样发送的完整文字", "不写概述", "同意按这段文字发送", "对外渠道（邮件、公开评论等）同样",
                       "重新给用户看"):
            self.assertIn(phrase, section)
        self.assertNotIn("批准最终 gate 即批准回告，到了用得上的时刻按批准的内容发", section)


class RequirementConfirmTests(unittest.TestCase):
    """requirement-confirm: summarise and ask whether the user is done before a new requirement enters the map."""
    QUESTION = "需求说完了吗？还有要补充的吗？"
    POINTER = "需求确认"

    def setUp(self):
        self.plugin = Path(__file__).resolve().parents[1]
        text = (self.plugin / CONTRACT).read_text(encoding="utf-8")
        start = text.index("## 需求确认")
        self.section = text[start:text.index("\n## ", start + 1)]
        self.order = text.index("## 需求确认") < text.index("## 阶段交接")

    def test_section_states_when_what_and_how(self):
        self.assertTrue(self.order, "the section goes before 阶段交接")
        for phrase in (self.QUESTION, "插入模块", "第一份 Spec", "目标", "给谁", "怎样算成功", "限制", "不做什么", "还没定",
                       "只认明确确认", "这一轮停下", "`interview-me`", "不用拷问", "已在别处批过"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.section)

    def test_summary_comes_first_and_map_row_goes_with_spec(self):
        # Rework 1: "already settled" before the summary still gets the summary; map row and Spec are reviewed together.
        for phrase in ("还没看过总结", "先给总结再确认", "能力图新行和 Spec 一起交审", "不为能力图新行单独停一次"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.section)
        for rel in ("commands/add-module.md", "skills/spec-guard-ops/SKILL.md"):
            with self.subTest(rel=rel):
                self.assertIn("和 Spec 一起交审", (self.plugin / rel).read_text(encoding="utf-8"))

    def test_section_names_what_does_not_trigger(self):
        for phrase in ("改 bug", "已批准范围内", "验收后接着写下一份 Spec"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.section)

    def test_templates_and_add_module_entries_point_here(self):
        for rel in ("templates/claude-block-local.md", "templates/codex-block-local.md",
                    "commands/add-module.md", "skills/spec-guard-ops/SKILL.md"):
            text = (self.plugin / rel).read_text(encoding="utf-8")
            with self.subTest(rel=rel):
                self.assertIn("「" + self.POINTER + "」", text)
                self.assertIn("说完", text)

    def test_add_module_asks_before_proposing(self):
        for rel, anchor in (("commands/add-module.md", "提出四项"),
                            ("skills/spec-guard-ops/SKILL.md", "根据用户给的需求上下文提出 id")):
            text = (self.plugin / rel).read_text(encoding="utf-8")
            with self.subTest(rel=rel):
                self.assertLess(text.index("「" + self.POINTER + "」"), text.index(anchor))


if __name__ == "__main__":
    unittest.main()
