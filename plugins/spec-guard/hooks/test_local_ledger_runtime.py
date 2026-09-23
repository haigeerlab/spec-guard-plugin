"""Local-ledger runtime contract tests; no package installation or Git mutation."""
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import local_ledger_runtime


class LocalLedgerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-local-ledger-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.runtime_dir = Path(self.tmp.name) / "runtime"
        self.project_dir = Path(self.tmp.name) / "project"
        self.project_dir.mkdir()

    def write_runtime(self, version=local_ledger_runtime.PACKAGE_VERSION):
        package_dir = self.runtime_dir / "node_modules" / local_ledger_runtime.PACKAGE_NAME
        (package_dir / "dist").mkdir(parents=True)
        (package_dir / "package.json").write_text(json.dumps({
            "name": local_ledger_runtime.PACKAGE_NAME,
            "version": version,
        }), encoding="utf-8")
        (package_dir / "dist" / "mcp.js").write_text("export {};\n", encoding="utf-8")

    def write_project_config(self, **overrides):
        values = {
            "projectId": "01M37F8MKQRSB562YCBQ004QGJ",
            "stateBranch": "__epiq_state__",
            "createdAt": "2026-09-24T00:00:00.000Z",
        }
        values.update(overrides)
        config_dir = self.project_dir / ".epiq"
        config_dir.mkdir()
        (config_dir / "project.json").write_text(json.dumps(values), encoding="utf-8")

    def test_contract_pins_epiq_without_a_service_or_latest_tag(self):
        contract = local_ledger_runtime.runtime_contract()
        self.assertEqual(contract["package"], "epiq")
        self.assertEqual(contract["packageVersion"], "1.11.0")
        self.assertEqual(contract["entrypoint"], "node_modules/epiq/dist/mcp.js")
        self.assertNotIn("latest", json.dumps(contract))
        self.assertNotIn("port", contract)

    def test_absent_status_is_read_only_and_reports_separate_runtime_and_project_states(self):
        output = io.StringIO()
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "status", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["state"], "absent")
        self.assertEqual(payload["runtime"]["state"], "absent")
        self.assertEqual(payload["project"]["state"], "uninitialized")
        self.assertFalse(self.runtime_dir.exists())
        self.assertFalse((self.project_dir / ".epiq").exists())

    def test_ready_runtime_and_initialized_project_are_reported_without_git_or_package_writes(self):
        self.write_runtime()
        self.write_project_config()
        before = {
            path: path.read_bytes()
            for path in (self.runtime_dir / "node_modules" / "epiq").rglob("*")
            if path.is_file()
        }
        output = io.StringIO()
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "status", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["state"], "initialized")
        self.assertEqual(payload["runtime"]["state"], "ready")
        self.assertEqual(payload["project"]["state"], "initialized")
        self.assertEqual(payload["project"]["stateBranch"], "__epiq_state__")
        self.assertEqual(before, {
            path: path.read_bytes()
            for path in (self.runtime_dir / "node_modules" / "epiq").rglob("*")
            if path.is_file()
        })

    def test_bad_runtime_version_is_invalid_even_when_node_is_ready(self):
        self.write_runtime(version="9.9.9")
        output = io.StringIO()
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "status", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 1)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["state"], "invalid")
        self.assertEqual(payload["runtime"]["state"], "invalid")
        self.assertIn("version", payload["runtime"]["diagnostic"])

    def test_missing_or_unsupported_node_has_an_explicit_diagnostic(self):
        self.write_runtime()
        for node in (
            {"state": "missing", "diagnostic": "node executable is unavailable"},
            {"state": "unsupported", "path": "/opt/node", "version": "16.0.0"},
        ):
            with self.subTest(node=node), patch("local_ledger_runtime.node_status", return_value=node):
                code, payload = local_ledger_runtime.status(self.runtime_dir, self.project_dir)
            self.assertEqual(code, 1)
            self.assertEqual(payload["state"], "invalid")
            self.assertEqual(payload["node"]["state"], node["state"])

    def initialize_git_project(self, origin=None):
        subprocess.run(["git", "init", "-q", str(self.project_dir)], check=True)
        subprocess.run(["git", "-C", str(self.project_dir), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.project_dir), "config", "user.name", "Local Ledger Test"], check=True)
        (self.project_dir / "README.md").write_text("test\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.project_dir), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.project_dir), "commit", "-qm", "initial"], check=True)
        if origin:
            subprocess.run(["git", "-C", str(self.project_dir), "remote", "add", "origin", origin], check=True)

    def test_initialization_preflight_allows_a_clean_project_without_origin(self):
        self.initialize_git_project()
        code, payload = local_ledger_runtime.initialization_preflight(self.project_dir)
        self.assertEqual(code, 0)
        self.assertEqual(payload["state"], "ready")
        self.assertIsNone(payload["origin"])
        self.assertEqual(payload["upstreamPush"], "will-fail-as-warning")

    def test_initialization_preflight_requires_explicit_permission_before_epiq_can_push_to_origin(self):
        self.initialize_git_project(origin="https://example.invalid/local-ledger.git")
        code, payload = local_ledger_runtime.initialization_preflight(self.project_dir)
        self.assertEqual(code, 1)
        self.assertEqual(payload["state"], "push-confirmation-required")
        self.assertEqual(payload["origin"], "https://example.invalid/local-ledger.git")
        self.assertEqual(payload["upstreamPush"], "requires-explicit-confirmation")

        code, payload = local_ledger_runtime.initialization_preflight(
            self.project_dir, allow_epiq_push=True)
        self.assertEqual(code, 0)
        self.assertEqual(payload["state"], "ready")
        self.assertEqual(payload["upstreamPush"], "permitted")

    def test_initialization_preflight_refuses_a_dirty_project_before_epiq_runs(self):
        self.initialize_git_project()
        (self.project_dir / "README.md").write_text("dirty\n", encoding="utf-8")
        code, payload = local_ledger_runtime.initialization_preflight(self.project_dir)
        self.assertEqual(code, 1)
        self.assertEqual(payload["state"], "dirty")
        self.assertNotIn("origin", payload)


if __name__ == "__main__":
    unittest.main()
