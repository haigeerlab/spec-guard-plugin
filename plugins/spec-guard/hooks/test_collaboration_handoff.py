#!/usr/bin/env python3
"""/spec-guard:collaboration only hands off to agent-relay and points to the migration document."""
from pathlib import Path
import unittest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO = PLUGIN_ROOT.parents[1]
COMMAND = PLUGIN_ROOT / "commands" / "collaboration.md"
MIGRATION = "docs/migrations/2026-10-07-collaboration-split.md"


class CollaborationHandoffTests(unittest.TestCase):
    def text(self):
        return COMMAND.read_text(encoding="utf-8")

    def test_runs_only_the_probe(self):
        text = self.text()
        self.assertIn('python3 -B "$ROOT/hooks/agent_relay_probe.py" --host claude', text)
        self.assertEqual(text.count("python3 -B"), 1)

    def test_every_probe_state_has_an_instruction(self):
        text = self.text()
        for state in ("`ready`", "`runtime-not-ready`", "`not-installed`", "`incompatible`", "`unknown`"):
            self.assertIn(state, text)
        self.assertIn("/agent-relay:collaboration", text)
        self.assertIn("`agent-relay:collab`", text)
        self.assertIn("不能说成未安装", text)
        self.assertIn("不代为安装", text)

    def test_points_to_the_published_migration_document(self):
        self.assertIn(MIGRATION, self.text())
        self.assertTrue((REPO / MIGRATION).is_file())
        probe = (PLUGIN_ROOT / "hooks" / "agent_relay_probe.py").read_text(encoding="utf-8")
        self.assertIn(MIGRATION, probe)

    def test_never_touches_old_data_or_host_configuration(self):
        self.assertIn("不读取、不修改旧数据，也不修改任何宿主配置或权限文件", self.text())


if __name__ == "__main__":
    unittest.main()
