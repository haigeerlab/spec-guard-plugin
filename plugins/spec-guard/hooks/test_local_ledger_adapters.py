"""Local-ledger Claude/Codex adapter tests; never alter real host configuration."""
import json
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
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
        self.assertIn('command = "/opt/node"', fragment)
        self.assertIn(str(self.runtime_dir / "node_modules" / "epiq" / "dist" / "mcp.js"), fragment)
        self.assertNotIn("token", fragment.lower())
        self.assertNotIn("http", fragment.lower())

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

    def test_claude_install_checks_for_a_conflict_then_adds_a_user_scoped_stdio_server(self):
        with patch("local_ledger_adapters.subprocess.run", side_effect=[
            subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0),
        ]) as run:
            local_ledger_adapters.install_claude_config(
                "claude", self.runtime_dir, "/opt/node")
        add_command = run.call_args_list[1].args[0]
        self.assertEqual(add_command[:5], [
            "claude", "mcp", "add", "--scope", "user",
        ])
        self.assertIn(local_ledger_adapters.MCP_SERVER_NAME, add_command)
        self.assertIn(str(self.runtime_dir / "node_modules" / "epiq" / "dist" / "mcp.js"), add_command)
        self.assertNotIn("token", " ".join(add_command).lower())

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


if __name__ == "__main__":
    unittest.main()
