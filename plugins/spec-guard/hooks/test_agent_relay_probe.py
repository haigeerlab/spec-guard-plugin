#!/usr/bin/env python3
"""The agent-relay probe reports every state truthfully and never writes."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROBE = Path(__file__).resolve().with_name("agent_relay_probe.py")
NOT_INSTALLED_TEXT = "协作能力已移到独立插件 agent-relay，当前未安装。工作流不受影响。"


class ProbeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="sg-relay-probe-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "claude"
        self.project = self.tmp / "project"
        self.plugin = self.tmp / "agent-relay"
        self.bin = self.tmp / "bin"
        for path in (self.home / "plugins", self.project, self.plugin, self.bin):
            path.mkdir(parents=True)

    # ── fixtures ──
    def write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def install_claude(self, enabled=True, project_path=None, key="agent-relay@relay-market"):
        install = {"scope": "user", "installPath": str(self.plugin), "version": "1.0.0"}
        if project_path:
            install.update(scope="project", projectPath=str(project_path))
        self.write_json(self.home / "plugins" / "installed_plugins.json",
                        {"version": 2, "plugins": {key: [install]}})
        self.write_json(self.home / "settings.json", {"enabledPlugins": {key: enabled}})

    def interface(self, data):
        self.write_json(self.plugin / "interface.json", data)

    def fake_codex(self, body):
        codex = self.bin / "codex"
        codex.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        codex.chmod(0o755)

    def codex_lists(self, plugins):
        payload = self.tmp / "codex.json"
        payload.write_text(json.dumps({"installed": plugins, "available": []}), encoding="utf-8")
        self.fake_codex(f"cat '{payload}'")

    def run_probe(self, host="claude"):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.home),
                   PATH=f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin")
        env.pop("CLAUDE_PROJECT_DIR", None)
        done = subprocess.run([sys.executable, "-B", str(PROBE), "--host", host, "--project",
                               str(self.project)], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual(set(report), {"state", "interface", "required", "message"})
        self.assertEqual(report["required"], ">=1.0,<2.0")
        return report

    # ── Claude ──
    def test_claude_without_record_is_not_installed_with_the_verbatim_message(self):
        report = self.run_probe()
        self.assertEqual(report["state"], "not-installed")
        self.assertIsNone(report["interface"])
        self.assertIn(NOT_INSTALLED_TEXT, report["message"])
        self.assertIn("docs/migrations/2026-10-07-collaboration-split.md", report["message"])

    def test_claude_ready_reports_the_interface_version(self):
        self.install_claude()
        self.interface({"interface": "1.3"})
        report = self.run_probe()
        self.assertEqual((report["state"], report["interface"]), ("ready", "1.3"))

    def test_claude_disabled_plugin_is_not_installed(self):
        self.install_claude(enabled=False)
        self.interface({"interface": "1.0"})
        self.assertEqual(self.run_probe()["state"], "not-installed")

    def test_project_settings_can_enable_the_plugin(self):
        self.install_claude(enabled=False)
        self.write_json(self.project / ".claude" / "settings.json",
                        {"enabledPlugins": {"agent-relay@relay-market": True}})
        self.interface({"interface": "1.0"})
        self.assertEqual(self.run_probe()["state"], "ready")

    def test_project_scoped_install_for_another_project_is_not_installed(self):
        self.install_claude(project_path=self.tmp / "elsewhere")
        self.interface({"interface": "1.0"})
        self.assertEqual(self.run_probe()["state"], "not-installed")

    def test_project_scoped_install_for_this_project_counts(self):
        self.install_claude(project_path=self.project)
        self.interface({"interface": "1.0"})
        self.assertEqual(self.run_probe()["state"], "ready")

    def test_a_different_plugin_with_a_similar_name_does_not_count(self):
        self.install_claude(key="agent-relay-lite@relay-market")
        self.interface({"interface": "1.0"})
        self.assertEqual(self.run_probe()["state"], "not-installed")

    def test_interface_outside_the_range_is_incompatible(self):
        self.install_claude()
        for found in ("0.9", "2.0"):
            with self.subTest(found=found):
                self.interface({"interface": found})
                report = self.run_probe()
                self.assertEqual((report["state"], report["interface"]), ("incompatible", found))
                self.assertIn(found, report["message"])
                self.assertIn(">=1.0,<2.0", report["message"])

    def test_missing_or_malformed_interface_is_incompatible_not_ready(self):
        self.install_claude()
        self.assertEqual(self.run_probe()["state"], "incompatible")
        self.interface({"interface": "one"})
        self.assertEqual(self.run_probe()["state"], "incompatible")

    def test_malformed_record_is_unknown_never_not_installed(self):
        (self.home / "plugins" / "installed_plugins.json").write_text("{", encoding="utf-8")
        report = self.run_probe()
        self.assertEqual(report["state"], "unknown")
        self.assertIn("不代表它未安装", report["message"])

    # ── runtime status (decision D4) ──
    def test_status_not_ready_points_to_agent_relay_setup(self):
        self.install_claude()
        self.interface({"interface": "1.0", "status": [sys.executable, "-c",
                        "print('{\"ready\": false, \"setup\": \"agent-relay setup\"}')"]})
        report = self.run_probe()
        self.assertEqual(report["state"], "runtime-not-ready")
        self.assertIn("agent-relay setup", report["message"])
        self.assertIn("不会代为安装", report["message"])

    def test_status_ready_is_ready(self):
        self.install_claude()
        self.interface({"interface": "1.0", "status": [sys.executable, "-c", "print('{\"ready\": true}')"]})
        self.assertEqual(self.run_probe()["state"], "ready")

    def test_status_runs_from_the_plugin_root(self):
        self.install_claude()
        (self.plugin / "status.py").write_text("print('{\"ready\": true}')\n", encoding="utf-8")
        self.interface({"interface": "1.0", "status": [sys.executable, "status.py"]})
        self.assertEqual(self.run_probe()["state"], "ready")

    def test_status_with_bad_output_is_unknown(self):
        self.install_claude()
        for command in ([sys.executable, "-c", "print('not json')"], "not-a-list",
                        [str(self.tmp / "missing-binary")]):
            with self.subTest(command=command):
                self.interface({"interface": "1.0", "status": command})
                self.assertEqual(self.run_probe()["state"], "unknown")

    # ── Codex ──
    def codex_entry(self, **overrides):
        entry = {"name": "agent-relay", "installed": True, "enabled": True,
                 "source": {"source": "local", "path": str(self.plugin)}}
        entry.update(overrides)
        return entry

    def test_codex_ready(self):
        self.codex_lists([{"name": "spec-guard", "installed": True, "enabled": True}, self.codex_entry()])
        self.interface({"interface": "1.0"})
        self.assertEqual(self.run_probe("codex")["state"], "ready")

    def test_codex_absent_or_disabled_is_not_installed(self):
        self.interface({"interface": "1.0"})
        for plugins in ([], [self.codex_entry(enabled=False)], [self.codex_entry(installed=False)]):
            with self.subTest(plugins=plugins):
                self.codex_lists(plugins)
                self.assertEqual(self.run_probe("codex")["state"], "not-installed")

    def test_codex_failures_are_unknown(self):
        cases = {
            "nonzero exit": "exit 3",
            "not json": "echo nope",
            "no installed list": "echo '{}'",
        }
        for name, body in cases.items():
            with self.subTest(name):
                self.fake_codex(body)
                self.assertEqual(self.run_probe("codex")["state"], "unknown")

    def test_codex_missing_binary_is_unknown(self):
        self.assertEqual(self.run_probe("codex")["state"], "unknown")

    # ── read-only ──
    def test_probe_writes_nothing(self):
        self.install_claude()
        self.interface({"interface": "1.0", "status": [sys.executable, "-c", "print('{\"ready\": true}')"]})
        self.codex_lists([self.codex_entry()])
        before = sorted((p, p.stat().st_mtime_ns) for p in self.tmp.rglob("*"))
        self.run_probe("claude")
        self.run_probe("codex")
        after = sorted((p, p.stat().st_mtime_ns) for p in self.tmp.rglob("*"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
