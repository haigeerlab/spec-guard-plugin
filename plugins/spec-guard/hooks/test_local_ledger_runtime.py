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

REAL_LOCK_DIR = (
    Path(__file__).resolve().parents[1] / "locks" / "local-ticket-ledger"
)


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

    def test_install_command_pins_epiq_and_keeps_it_out_of_the_project(self):
        command = local_ledger_runtime.install_command(
            self.runtime_dir, npm_executable="/opt/homebrew/bin/npm")
        self.assertEqual(command, [
            "/opt/homebrew/bin/npm", "install", "--ignore-scripts", "--prefix",
            str(self.runtime_dir), "epiq@1.11.0",
        ])
        self.assertNotIn(str(self.project_dir), command)

    def test_install_refuses_to_overwrite_an_existing_runtime(self):
        self.write_runtime()
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "already installed"):
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable="/opt/npm")

    def test_install_cli_requires_explicit_confirmation_without_creating_runtime_files(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "install", "--runtime-dir", str(self.runtime_dir), "--format", "json",
            ]), 1)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["state"], "install-confirmation-required")
        self.assertFalse(self.runtime_dir.exists())

    def test_install_runs_the_pinned_command_then_validates_the_result(self):
        with patch("local_ledger_runtime.subprocess.run", return_value=subprocess.CompletedProcess([], 0)), \
             patch("local_ledger_runtime.runtime_status", side_effect=[
                 {"state": "absent"}, {"state": "ready"},
             ]) as runtime_status:
            result = local_ledger_runtime.install_runtime(
                self.runtime_dir, npm_executable="/opt/homebrew/bin/npm")
        self.assertEqual(result["state"], "ready")
        self.assertTrue(self.runtime_dir.is_dir())
        self.assertEqual(runtime_status.call_count, 2)

    def fake_npm(self, script):
        """A stand-in npm that really writes under --prefix, so install uses real directories."""
        npm = Path(self.tmp.name) / "fake-npm"
        npm.write_text("#!/bin/sh\n" + '[ "$3" = --prefix ] || exit 9\nprefix="$4"\n' + script, encoding="utf-8")
        npm.chmod(0o755)
        return str(npm)

    def installed_files(self, version="1.11.0"):
        return (
            'mkdir -p "$prefix/node_modules/epiq/dist"\n'
            'printf \'{"name":"epiq","version":"%s"}\' > "$prefix/node_modules/epiq/package.json"\n'
            % version +
            ': > "$prefix/node_modules/epiq/dist/mcp.js"\n')

    def leftovers(self):
        return sorted(path.name for path in Path(self.tmp.name).iterdir()
                      if path.name.startswith("runtime.installing-"))

    def test_install_moves_a_verified_runtime_into_place(self):
        result = local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()))
        self.assertEqual((result["state"], result["directory"]), ("ready", str(self.runtime_dir)))
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir)["state"], "ready")
        self.assertEqual(self.leftovers(), [])

    def test_failed_npm_leaves_no_runtime_and_can_be_retried(self):
        npm = self.fake_npm('echo "npm ERR! code E404" >&2\nexit 1\n')
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError,
                                    "npm install failed: npm ERR! code E404"):
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir), {"state": "absent"})
        self.assertEqual(self.leftovers(), [])
        result = local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()))
        self.assertEqual(result["state"], "ready")

    def test_wrong_package_is_discarded_without_creating_the_runtime(self):
        npm = self.fake_npm(self.installed_files(version="9.9.9"))
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "audited contract"):
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir), {"state": "absent"})
        self.assertEqual(self.leftovers(), [])

    def test_install_takes_over_an_empty_directory_left_by_an_older_failed_install(self):
        self.runtime_dir.mkdir()
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir)["state"], "invalid")
        result = local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()))
        self.assertEqual(result["state"], "ready")

    def test_install_still_refuses_a_nonempty_invalid_runtime(self):
        (self.runtime_dir / "node_modules").mkdir(parents=True)
        (self.runtime_dir / "keep.txt").write_text("user data\n", encoding="utf-8")
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "refusing to overwrite"):
            local_ledger_runtime.install_runtime(
                self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()))
        self.assertEqual((self.runtime_dir / "keep.txt").read_text(encoding="utf-8"), "user data\n")
        self.assertEqual(self.leftovers(), [])

    def test_install_cli_reports_the_npm_failure_reason(self):
        output = io.StringIO()
        npm = self.fake_npm('echo "npm ERR! network timeout" >&2\nexit 1\n')
        with redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "install", "--runtime-dir", str(self.runtime_dir), "--npm", npm,
                "--confirm-install", "--format", "json",
            ]), 1)
        payload = json.loads(output.getvalue())
        self.assertIn("npm ERR! network timeout", payload["diagnostic"])
        self.assertFalse(self.runtime_dir.exists())

    def test_acceptance_without_a_runtime_reports_not_run_instead_of_passing(self):
        import os
        import test_local_ledger_acceptance
        output = io.StringIO()
        environment = {key: value for key, value in os.environ.items()
                       if key != "SPEC_GUARD_EPIQ_RUNTIME"}
        with patch.dict(os.environ, environment, clear=True), redirect_stdout(output):
            self.assertEqual(test_local_ledger_acceptance.main(), 2)
        self.assertEqual(json.loads(output.getvalue())["state"], "skipped")

    def test_project_init_arguments_require_user_setup_values_without_using_agent_identity(self):
        arguments = local_ledger_runtime.project_init_arguments(
            self.project_dir, "Vilin", "code --wait", False)
        self.assertEqual(arguments, {
            "repoRoot": str(self.project_dir),
            "userName": "Vilin",
            "preferredEditor": "code --wait",
            "autoSync": False,
        })
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "user name"):
            local_ledger_runtime.project_init_arguments(self.project_dir, "", "code --wait", False)

    def test_mcp_tool_result_reader_requires_a_successful_json_tool_payload(self):
        response = io.StringIO(
            '{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text",'
            '"text":"{\\"status\\": \\"success\\", \\"value\\": {\\"projectId\\": \\"project\\"}}"}]}}\n')
        self.assertEqual(local_ledger_runtime.read_mcp_tool_result(response, 1), {
            "status": "success", "value": {"projectId": "project"},
        })
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "MCP server returned invalid JSON"):
            local_ledger_runtime.read_mcp_tool_result(io.StringIO("not json\n"), 1)

    def test_initialize_requires_push_permission_and_returns_sanitized_epiq_facts(self):
        ready_preflight = (0, {
            "state": "ready", "projectDir": str(self.project_dir), "origin": None,
            "upstreamPush": "will-fail-as-warning",
        })
        with patch("local_ledger_runtime.initialization_preflight", return_value=ready_preflight), \
             patch("local_ledger_runtime.node_status", return_value={"state": "ready", "path": "/opt/node", "version": "20.0.0"}), \
             patch("local_ledger_runtime.runtime_status", return_value={"state": "ready"}), \
             patch("local_ledger_runtime.mcp_tool_call", return_value={
                 "status": "success",
                 "value": {"projectId": "project", "stateBranch": "__epiq_state__", "warnings": ["do not print this"]},
             }) as mcp_call:
            payload = local_ledger_runtime.initialize_project(
                self.runtime_dir, self.project_dir, "Vilin", "code --wait", False,
            )
        self.assertEqual(payload, {
            "state": "initialized", "projectId": "project", "stateBranch": "__epiq_state__",
            "upstreamPush": "will-fail-as-warning", "warnings": True,
        })
        self.assertEqual(mcp_call.call_args.args[1], "epiq_project_init")
        self.assertEqual(mcp_call.call_args.args[2]["userName"], "Vilin")

    def test_initialize_refuses_before_starting_mcp_when_origin_has_not_been_confirmed(self):
        with patch("local_ledger_runtime.initialization_preflight", return_value=(1, {
            "state": "push-confirmation-required", "origin": "https://example.invalid/repo.git",
        })), patch("local_ledger_runtime.mcp_tool_call") as mcp_call:
            with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "push-confirmation-required"):
                local_ledger_runtime.initialize_project(
                    self.runtime_dir, self.project_dir, "Vilin", "code --wait", False,
                )
        mcp_call.assert_not_called()

    def test_initialize_cli_requires_confirmation_and_user_setup_before_starting_epiq(self):
        output = io.StringIO()
        with patch("local_ledger_runtime.initialize_project") as initialize, redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "initialize", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 1)
        self.assertEqual(json.loads(output.getvalue())["state"], "initialization-confirmation-required")
        initialize.assert_not_called()

        output = io.StringIO()
        with patch("local_ledger_runtime.initialize_project") as initialize, redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "initialize", "--confirm-initialize", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 1)
        self.assertEqual(json.loads(output.getvalue())["state"], "user-setup-required")
        initialize.assert_not_called()


    def copy_lock_files(self, drop=()):
        lock_dir = Path(self.tmp.name) / "lock-copy"
        lock_dir.mkdir()
        for name in ("package.json", "package-lock.json"):
            if name not in drop:
                (lock_dir / name).write_bytes((REAL_LOCK_DIR / name).read_bytes())
        return lock_dir

    def edit_json(self, path, mutate):
        data = json.loads(path.read_text(encoding="utf-8"))
        mutate(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_shipped_lock_files_match_the_version_constant_and_are_fully_hashed(self):
        self.assertEqual(local_ledger_runtime.validate_lock_files(REAL_LOCK_DIR), [])
        package = json.loads((REAL_LOCK_DIR / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"], {
            local_ledger_runtime.PACKAGE_NAME: local_ledger_runtime.PACKAGE_VERSION,
        })
        lock = json.loads((REAL_LOCK_DIR / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["packages"][""]["dependencies"], package["dependencies"])
        self.assertEqual(
            lock["packages"]["node_modules/epiq"]["version"], local_ledger_runtime.PACKAGE_VERSION,
        )
        entries = {key: value for key, value in lock["packages"].items() if key}
        self.assertGreater(len(entries), 1)
        for key, entry in entries.items():
            self.assertTrue(entry.get("resolved"), key)
            self.assertRegex(entry.get("integrity", ""), r"^(sha512|sha1)-.+", key)

    def test_lock_check_fails_when_package_json_version_drifts_from_the_constant(self):
        lock_dir = self.copy_lock_files()
        self.edit_json(lock_dir / "package.json", lambda d: d["dependencies"].update(epiq="1.11.1"))
        problems = local_ledger_runtime.validate_lock_files(lock_dir)
        self.assertTrue(any("package.json" in problem for problem in problems), problems)

    def test_lock_check_fails_when_the_lockfile_root_or_package_drifts(self):
        lock_dir = self.copy_lock_files()
        self.edit_json(
            lock_dir / "package-lock.json",
            lambda d: d["packages"]["node_modules/epiq"].update(version="1.11.1"),
        )
        self.assertTrue(local_ledger_runtime.validate_lock_files(lock_dir))

    def test_lock_check_fails_when_a_package_lacks_integrity(self):
        lock_dir = self.copy_lock_files()

        def drop_integrity(data):
            key = next(k for k in data["packages"] if k)
            del data["packages"][key]["integrity"]

        self.edit_json(lock_dir / "package-lock.json", drop_integrity)
        problems = local_ledger_runtime.validate_lock_files(lock_dir)
        self.assertTrue(any("integrity" in problem for problem in problems), problems)

    def test_lock_check_fails_when_a_lock_file_is_missing(self):
        for name in ("package.json", "package-lock.json"):
            with self.subTest(missing=name):
                lock_dir = Path(self.tmp.name) / ("without-" + name)
                lock_dir.mkdir()
                other = "package-lock.json" if name == "package.json" else "package.json"
                (lock_dir / other).write_bytes((REAL_LOCK_DIR / other).read_bytes())
                problems = local_ledger_runtime.validate_lock_files(lock_dir)
                self.assertTrue(any(name in problem for problem in problems), problems)
        self.assertTrue(local_ledger_runtime.validate_lock_files(Path(self.tmp.name) / "nowhere"))


if __name__ == "__main__":
    unittest.main()
