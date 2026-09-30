#!/usr/bin/env python3
"""Contract tests for the daily local-ticket skill."""

from pathlib import Path
import unittest

from local_ledger_adapters import GATED_TOOLS


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL = PLUGIN_ROOT / "skills" / "ticket" / "SKILL.md"
COMMAND = PLUGIN_ROOT / "commands" / "ticket.md"
LOCAL_TEMPLATES = (
    PLUGIN_ROOT / "templates" / "claude-block-local.md",
    PLUGIN_ROOT / "templates" / "codex-block-local.md",
)
VALIDATE = PLUGIN_ROOT.parents[1] / "scripts" / "validate.sh"


class TicketEntryContractTest(unittest.TestCase):
    def test_accepted_work_has_an_early_identity_and_unknown_does_not_create(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("`includeClosed: true`", text)
        self.assertIn("`found`／`absent`／`unknown`", text)
        self.assertIn("动代码前", text)
        self.assertIn("读取失败或列表是否完整无法确定时不创建", text)
        self.assertIn("两个 Agent 同时查重仍可能重复", text)

    def test_material_change_and_closure_have_readback_rules(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("先追加决定评论", text)
        self.assertIn("决定待应用", text)
        self.assertIn("验证未通过时保持开放", text)
        self.assertIn("读回关闭状态", text)

    def test_ticket_write_requires_safe_state_worktree(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("`project.stateWorktree`", text)
        self.assertIn("`foreign`／`unknown`", text)
        self.assertIn("不调用 Epiq 写工具", text)

    def test_local_convention_mentions_early_ticket_only_when_ledger_is_enabled(self) -> None:
        for path in LOCAL_TEMPLATES:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("若项目已启用 Local 事项账本", text)
                self.assertIn("在动代码前先用 `spec-guard:ticket`", text)
                self.assertIn("探索和无需追踪的小操作例外", text)

    def test_short_ref_is_resolved_to_full_id_before_writing(self) -> None:
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("先用 `epiq_issue_get` 取得完整 `value.id`", text)
        self.assertIn("写操作传完整 ID", text)

    def test_slash_command_requires_full_id_and_confirmed_write(self) -> None:
        text = COMMAND.read_text(encoding="utf-8")

        self.assertIn("先用 `epiq_issue_get` 取得完整 `value.id`", text)
        self.assertIn("不得把短编号直接传给写工具", text)
        self.assertIn("写工具确认成功后才能报告成功", text)

    def test_daily_entries_name_every_gated_tool_as_confirmation_only(self) -> None:
        for path in (SKILL, COMMAND):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("每次调用单独确认", text)
                self.assertIn("不构成授权", text)
                for tool in GATED_TOOLS:
                    self.assertIn(f"`{tool}`", text)

    def test_repository_validation_runs_ticket_contract(self) -> None:
        text = VALIDATE.read_text(encoding="utf-8")

        self.assertIn("python3 -B plugins/spec-guard/hooks/test_ticket_entry.py", text)
        self.assertIn("python3 -B plugins/spec-guard/hooks/test_local_ledger_adapters.py", text)
        self.assertIn("python3 -B plugins/spec-guard/hooks/test_local_ledger_runtime.py", text)


if __name__ == "__main__":
    unittest.main()
