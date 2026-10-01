"""Local-ledger Claude/Codex adapter tests; never alter real host configuration."""
import json
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import local_ledger_adapters


class LocalLedgerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-local-ledger-adapters-")
        self.addCleanup(self.tmp.cleanup)
        self.runtime_dir = Path(self.tmp.name) / "runtime"
        package = self.runtime_dir / "node_modules" / "epiq"
        (package / "dist").mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"name": "epiq", "version": "1.11.0"}), encoding="utf-8")
        (package / "dist" / "mcp.js").write_text("export {};\n", encoding="utf-8")

    def test_codex_fragment_is_a_no_secret_stdio_entry(self):
        fragment = local_ledger_adapters.codex_toml_fragment(self.runtime_dir, "/opt/node")
        self.assertIn("[mcp_servers.spec_guard_local_ledger]", fragment)
        self.assertIn('command = "/bin/sh"', fragment)
        self.assertIn("umask 077", fragment)
        self.assertIn('/opt/node', fragment)
        self.assertIn(str(self.runtime_dir / "node_modules" / "epiq" / "dist" / "mcp.js"), fragment)
        self.assertNotIn("token", fragment.lower())
        self.assertNotIn("http", fragment.lower())

    def test_generated_mcp_command_creates_private_default_mode_files(self):
        entrypoint = self.runtime_dir / "node_modules" / "epiq" / "dist" / "mcp.js"
        entrypoint.write_text(
            "import os\nfrom pathlib import Path\n"
            "root = Path(os.environ['SG_TEST_EPIQ_GLOBAL'])\n"
            "root.mkdir()\n(root / 'event.jsonl').write_text('test')\n",
            encoding="utf-8",
        )
        command = local_ledger_adapters.mcp_command(self.runtime_dir, sys.executable)
        global_dir = Path(self.tmp.name) / "new-epiq-global"
        env = {**os.environ, "SG_TEST_EPIQ_GLOBAL": str(global_dir)}
        subprocess.run(command, env=env, check=True, capture_output=True, text=True)
        self.assertEqual(global_dir.stat().st_mode & 0o777, 0o700)
        self.assertEqual((global_dir / "event.jsonl").stat().st_mode & 0o777, 0o600)

    def test_codex_fragment_exposes_only_daily_tools(self):
        fragment = local_ledger_adapters.codex_toml_fragment(self.runtime_dir, "/opt/node")
        lines = [line for line in fragment.splitlines() if line.startswith("enabled_tools = ")]
        self.assertEqual(len(lines), 1)
        enabled = json.loads(lines[0].split(" = ", 1)[1])
        self.assertIn("epiq_issue_create", enabled)
        self.assertIn("epiq_issue_close", enabled)
        for tool in ("epiq_sync", "epiq_project_init", "epiq_skill_install", "epiq_issue_comment_delete",
                     "epiq_swimlane_delete", "epiq_tag_remove", "epiq_contributor_remove",
                     "epiq_contributor_email_link", "epiq_contributor_email_suggest",
                     "epiq_contributor_email_unlink"):
            self.assertNotIn(tool, enabled)
        self.assertEqual(sorted(enabled + list(local_ledger_adapters.GATED_TOOLS)),
                         sorted(local_ledger_adapters.LEDGER_TOOLS))

    def test_gated_tools_are_a_subset_of_the_pinned_tool_surface(self):
        tools = local_ledger_adapters.LEDGER_TOOLS
        self.assertEqual(len(tools), len(set(tools)))
        self.assertEqual(len(tools), 39)
        self.assertTrue(set(local_ledger_adapters.GATED_TOOLS) <= set(tools))

    def test_adapter_refuses_a_missing_runtime(self):
        with self.assertRaisesRegex(ValueError, "not ready"):
            local_ledger_adapters.mcp_command(Path(self.tmp.name) / "missing", "/opt/node")

    def test_codex_install_appends_atomically_and_refuses_a_conflict(self):
        config = Path(self.tmp.name) / "codex" / "config.toml"
        config.parent.mkdir()
        config.write_text('model = "test"\n', encoding="utf-8")
        local_ledger_adapters.install_codex_config(config, self.runtime_dir, "/opt/node")
        contents = config.read_text(encoding="utf-8")
        self.assertIn('model = "test"', contents)
        self.assertIn("[mcp_servers.spec_guard_local_ledger]", contents)
        with self.assertRaisesRegex(ValueError, "already exists"):
            local_ledger_adapters.install_codex_config(config, self.runtime_dir, "/opt/node")

    def test_codex_install_creates_a_missing_config_in_an_existing_directory(self):
        config = Path(self.tmp.name) / "codex" / "config.toml"
        config.parent.mkdir()
        local_ledger_adapters.install_codex_config(config, self.runtime_dir, "/opt/node")
        self.assertIn("[mcp_servers.spec_guard_local_ledger]", config.read_text(encoding="utf-8"))
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)

    def test_cli_reports_a_filesystem_error_without_a_traceback(self):
        blocker = Path(self.tmp.name) / "not-a-directory"
        blocker.write_text("x", encoding="utf-8")
        errors = io.StringIO()
        with patch("local_ledger_adapters.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(io.StringIO()), redirect_stderr(errors):
            self.assertEqual(local_ledger_adapters.main([
                "install-codex", "--runtime-dir", str(self.runtime_dir),
                "--codex-config", str(blocker / "config.toml"), "--confirm-install",
            ]), 1)
        self.assertIn("local-ledger adapter unavailable", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_claude_install_checks_for_a_conflict_then_adds_a_user_scoped_stdio_server(self):
        settings = Path(self.tmp.name) / "claude" / "settings.json"
        with patch("host_config_removal.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0)) as run:
            local_ledger_adapters.install_claude_config(
                "claude", self.runtime_dir, "/opt/node", settings)
        ask = json.loads(settings.read_text(encoding="utf-8"))["permissions"]["ask"]
        self.assertIn("mcp__spec-guard-local-ledger__epiq_sync", ask)
        self.assertEqual(run.call_count, 1)
        add_command = run.call_args_list[0].args[0]
        self.assertEqual(add_command[:5], [
            "claude", "mcp", "add", "--scope", "user",
        ])
        self.assertIn(local_ledger_adapters.MCP_SERVER_NAME, add_command)
        self.assertIn(str(self.runtime_dir / "node_modules" / "epiq" / "dist" / "mcp.js"), add_command)
        self.assertNotIn("token", " ".join(add_command).lower())

    def test_claude_install_refuses_an_existing_server_but_keeps_its_ask_rules(self):
        # 同名服务已存在时 CLI 自己拒绝；此前写入的 ask 规则只会让这些工具逐次询问，保留无害。
        settings = Path(self.tmp.name) / "claude" / "settings.json"
        with patch("host_config_removal.subprocess.run", return_value=subprocess.CompletedProcess(
                [], 1, "", "MCP server spec-guard-local-ledger already exists in user config")):
            with self.assertRaisesRegex(ValueError, "already exists; refusing to overwrite"):
                local_ledger_adapters.install_claude_config(
                    "claude", self.runtime_dir, "/opt/node", settings)
        self.assertEqual(json.loads(settings.read_text(encoding="utf-8"))["permissions"]["ask"],
                         local_ledger_adapters.claude_ask_rules())

    def test_claude_guard_merges_ask_rules_and_preserves_other_settings(self):
        settings = Path(self.tmp.name) / "settings.json"
        settings.write_text(json.dumps({
            "model": "x",
            "permissions": {"allow": ["Read"], "ask": ["Bash(git push *)", "mcp__spec-guard-local-ledger__epiq_sync"]},
        }), encoding="utf-8")
        settings.chmod(0o644)
        local_ledger_adapters.install_claude_guard(settings)
        local_ledger_adapters.install_claude_guard(settings)
        value = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(value["model"], "x")
        self.assertEqual(value["permissions"]["allow"], ["Read"])
        ask = value["permissions"]["ask"]
        self.assertEqual(ask[0], "Bash(git push *)")
        self.assertEqual(sorted(ask[1:]), sorted(local_ledger_adapters.claude_ask_rules()))
        self.assertEqual(len(ask), len(set(ask)))
        self.assertEqual(settings.stat().st_mode & 0o777, 0o644)

    def test_claude_guard_refuses_malformed_settings_without_rewriting_them(self):
        for contents in ("{not json", "[]", '{"permissions": []}', '{"permissions": {"ask": "x"}}'):
            with self.subTest(contents=contents):
                settings = Path(self.tmp.name) / "bad-settings.json"
                settings.write_text(contents, encoding="utf-8")
                with self.assertRaises(ValueError):
                    local_ledger_adapters.install_claude_guard(settings)
                self.assertEqual(settings.read_text(encoding="utf-8"), contents)

    def test_claude_guard_refuses_a_symlinked_settings_file(self):
        target = Path(self.tmp.name) / "real.json"
        target.write_text("{}", encoding="utf-8")
        link = Path(self.tmp.name) / "settings.json"
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            local_ledger_adapters.install_claude_guard(link)
        self.assertEqual(target.read_text(encoding="utf-8"), "{}")

    def test_claude_cli_prints_ask_rules_without_modifying_configuration(self):
        settings = Path(self.tmp.name) / "claude" / "settings.json"
        output = io.StringIO()
        with patch("local_ledger_adapters.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_adapters.main([
                "claude", "--runtime-dir", str(self.runtime_dir), "--claude-settings", str(settings),
            ]), 0)
        printed = json.loads(output.getvalue())
        self.assertEqual(printed["permissions"]["ask"], local_ledger_adapters.claude_ask_rules())
        self.assertFalse(settings.exists())

    def test_claude_guard_cli_requires_an_explicit_confirmation(self):
        settings = Path(self.tmp.name) / "claude" / "settings.json"
        output = io.StringIO()
        with patch("local_ledger_adapters.node_status", return_value={"state": "absent"}), \
                redirect_stdout(output):
            self.assertEqual(local_ledger_adapters.main([
                "install-claude-guard", "--claude-settings", str(settings),
            ]), 1)
            self.assertEqual(local_ledger_adapters.main([
                "install-claude-guard", "--claude-settings", str(settings), "--confirm-install",
            ]), 0)
        self.assertIn("configuration-confirmation-required", output.getvalue())
        self.assertIn("mcp__spec-guard-local-ledger__epiq_sync",
                      json.loads(settings.read_text(encoding="utf-8"))["permissions"]["ask"])

    def test_codex_cli_prints_a_fragment_without_modifying_configuration(self):
        output = io.StringIO()
        with patch("local_ledger_adapters.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_adapters.main([
                "codex", "--runtime-dir", str(self.runtime_dir),
            ]), 0)
        self.assertIn("[mcp_servers.spec_guard_local_ledger]", output.getvalue())

    def test_host_configuration_cli_requires_an_explicit_confirmation(self):
        config = Path(self.tmp.name) / "codex" / "config.toml"
        output = io.StringIO()
        with patch("local_ledger_adapters.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_adapters.main([
                "install-codex", "--runtime-dir", str(self.runtime_dir),
                "--codex-config", str(config),
            ]), 1)
        self.assertFalse(config.exists())
        self.assertIn("configuration-confirmation-required", output.getvalue())

    def test_cli_reports_a_missing_runtime_without_a_traceback(self):
        output = io.StringIO()
        errors = io.StringIO()
        with patch("local_ledger_adapters.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(local_ledger_adapters.main([
                "codex", "--runtime-dir", str(Path(self.tmp.name) / "missing"),
            ]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("local-ledger adapter unavailable", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
