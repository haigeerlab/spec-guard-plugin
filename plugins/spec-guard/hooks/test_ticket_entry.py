#!/usr/bin/env python3
"""Contract tests for the daily local-ticket skill."""

from pathlib import Path
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL = PLUGIN_ROOT / "skills" / "ticket" / "SKILL.md"
COMMAND = PLUGIN_ROOT / "commands" / "ticket.md"
VALIDATE = PLUGIN_ROOT.parents[1] / "scripts" / "validate.sh"


class TicketEntryContractTest(unittest.TestCase):
    def test_short_ref_is_resolved_to_full_id_before_writing(self) -> None:
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("先用 `epiq_issue_get` 取得完整 `value.id`", text)
        self.assertIn("写操作传完整 ID", text)

    def test_slash_command_requires_full_id_and_confirmed_write(self) -> None:
        text = COMMAND.read_text(encoding="utf-8")

        self.assertIn("先用 `epiq_issue_get` 取得完整 `value.id`", text)
        self.assertIn("不得把短编号直接传给写工具", text)
        self.assertIn("写工具确认成功后才能报告成功", text)

    def test_repository_validation_runs_ticket_contract(self) -> None:
        text = VALIDATE.read_text(encoding="utf-8")

        self.assertIn("python3 -B plugins/spec-guard/hooks/test_ticket_entry.py", text)


if __name__ == "__main__":
    unittest.main()
