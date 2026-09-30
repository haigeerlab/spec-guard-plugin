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

    def test_install_command_is_a_locked_npm_ci_without_package_spec_or_prefix(self):
        command = local_ledger_runtime.install_command(npm_executable="/opt/homebrew/bin/npm")
        self.assertEqual(command, [
            "/opt/homebrew/bin/npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund",
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
                 {"state": "absent"}, {"state": "ready", "lock": "locked"},
             ]) as runtime_status:
            result = local_ledger_runtime.install_runtime(
                self.runtime_dir, npm_executable="/opt/homebrew/bin/npm")
        self.assertEqual(result["state"], "ready")
        self.assertTrue(self.runtime_dir.is_dir())
        self.assertEqual(runtime_status.call_count, 2)

    def fake_npm(self, script):
        """A stand-in `npm ci`: works in its cwd (the staging dir), records argv/pwd/ls."""
        npm = Path(self.tmp.name) / "fake-npm"
        self.npm_record = Path(self.tmp.name) / "npm-record"
        npm.write_text(
            "#!/bin/sh\n"
            'record="%s"\n' % self.npm_record +
            'printf "%s\\n" "$*" > "$record"\npwd -P >> "$record"\nls >> "$record"\n'
            '[ "$1" = ci ] || exit 9\nprefix="$PWD"\n' + script, encoding="utf-8")
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
        self.assertEqual(
            (self.runtime_dir / "package-lock.json").read_bytes(),
            (REAL_LOCK_DIR / "package-lock.json").read_bytes())

    def test_install_runs_npm_ci_in_the_staging_dir_with_both_lock_files_present(self):
        npm = self.fake_npm(self.installed_files())
        local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        argv, cwd, *listing = self.npm_record.read_text(encoding="utf-8").splitlines()
        self.assertEqual(argv, "ci --ignore-scripts --no-audit --no-fund")
        self.assertEqual(Path(cwd).parent, Path(self.tmp.name).resolve())
        self.assertTrue(Path(cwd).name.startswith("runtime.installing-"))
        self.assertIn("package.json", listing)
        self.assertIn("package-lock.json", listing)

    def test_missing_or_invalid_lock_dir_is_refused_before_staging_or_npm(self):
        npm = self.fake_npm(self.installed_files())
        broken = self.copy_lock_files(name="lock-drift")
        self.edit_json(broken / "package.json", lambda d: d["dependencies"].update(epiq="1.11.1"))
        for lock_dir in (Path(self.tmp.name) / "no-such-lock-dir",
                         self.copy_lock_files(drop=("package-lock.json",), name="lock-partial"),
                         broken):
            with self.subTest(lock_dir=lock_dir.name):
                with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "lock"):
                    local_ledger_runtime.install_runtime(
                        self.runtime_dir, npm_executable=npm, lock_dir=lock_dir)
                self.assertEqual(self.leftovers(), [])
                self.assertFalse(self.runtime_dir.exists())
                self.assertFalse(self.npm_record.exists())

    def test_failed_npm_leaves_no_runtime_and_can_be_retried(self):
        npm = self.fake_npm('echo "npm ERR! code E404" >&2\nexit 1\n')
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError,
                                    "npm ci failed: npm ERR! code E404"):
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir), {"state": "absent"})
        self.assertEqual(self.leftovers(), [])
        result = local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()))
        self.assertEqual(result["state"], "ready")

    def test_fresh_install_that_ends_up_unlocked_is_refused_and_cleaned_up(self):
        npm = self.fake_npm(self.installed_files() + 'rm -f "$prefix/package-lock.json"\n')
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "audited contract"):
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir), {"state": "absent"})
        self.assertEqual(self.sibling_leftovers(), [])

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

    def test_install_reports_the_npm_error_code_instead_of_the_log_pointer(self):
        # npm 11 prints the error code first and "A complete log ..." last; the last line alone hides EINTEGRITY.
        npm = self.fake_npm(
            'echo "npm error code EINTEGRITY" >&2\n'
            'echo "npm error sha512-AAAA integrity checksum failed when using sha512: wanted sha512-AAAA but got sha512-BBBB. (123 bytes)" >&2\n'
            'echo "npm error A complete log of this run can be found in: /tmp/_logs/debug-0.log" >&2\n'
            'exit 1\n')
        with self.assertRaises(local_ledger_runtime.RuntimeContractError) as raised:
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        message = str(raised.exception)
        self.assertIn("EINTEGRITY", message)
        self.assertIn("integrity checksum failed", message)
        self.assertNotIn("A complete log of this run", message)
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


    def copy_lock_files(self, drop=(), name="lock-copy"):
        lock_dir = Path(self.tmp.name) / name
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


    # ---- L3: lock status and replacing an unlocked runtime ----

    def snapshot(self, root):
        """Paths + bytes (and symlink targets) of a tree, for byte-identical assertions."""
        root = Path(root)
        result = {}
        for path in sorted(root.rglob("*")):
            key = str(path.relative_to(root))
            if path.is_symlink():
                result[key] = ("link", str(path.readlink()))
            elif path.is_dir():
                result[key] = ("dir", None)
            else:
                result[key] = ("file", path.read_bytes())
        return result

    def sibling_leftovers(self):
        return sorted(path.name for path in Path(self.tmp.name).iterdir()
                      if ".installing-" in path.name or ".replaced-" in path.name)

    def write_unlocked_runtime(self):
        self.write_runtime()
        (self.runtime_dir / "node_modules" / "epiq" / "old-marker.txt").write_text(
            "old\n", encoding="utf-8")

    def write_locked_runtime(self):
        self.write_runtime()
        (self.runtime_dir / "package-lock.json").write_bytes(
            (REAL_LOCK_DIR / "package-lock.json").read_bytes())

    def test_status_reports_locked_when_the_lockfile_matches_the_shipped_one(self):
        self.write_locked_runtime()
        status = local_ledger_runtime.runtime_status(self.runtime_dir)
        self.assertEqual((status["state"], status["lock"]), ("ready", "locked"))

    def test_status_reports_unlocked_when_the_lockfile_is_missing_or_different(self):
        self.write_runtime()
        status = local_ledger_runtime.runtime_status(self.runtime_dir)
        self.assertEqual((status["state"], status["lock"]), ("ready", "unlocked"))
        (self.runtime_dir / "package-lock.json").write_text("{}\n", encoding="utf-8")
        status = local_ledger_runtime.runtime_status(self.runtime_dir)
        self.assertEqual((status["state"], status["lock"]), ("ready", "unlocked"))
        other = self.copy_lock_files(name="lock-other")
        self.edit_json(other / "package-lock.json", lambda d: d.update(name="changed"))
        (self.runtime_dir / "package-lock.json").write_bytes(
            (REAL_LOCK_DIR / "package-lock.json").read_bytes())
        status = local_ledger_runtime.runtime_status(self.runtime_dir, lock_dir=other)
        self.assertEqual((status["state"], status["lock"]), ("ready", "unlocked"))

    def test_status_has_no_lock_field_for_absent_or_invalid_runtimes(self):
        self.assertNotIn("lock", local_ledger_runtime.runtime_status(self.runtime_dir))
        self.write_runtime(version="9.9.9")
        invalid = local_ledger_runtime.runtime_status(self.runtime_dir)
        self.assertEqual(invalid["state"], "invalid")
        self.assertNotIn("lock", invalid)

    def test_install_refuses_a_locked_runtime_even_with_replace_unlocked(self):
        self.write_locked_runtime()
        before = self.snapshot(self.runtime_dir)
        npm = self.fake_npm(self.installed_files())
        for flag in (False, True):
            with self.subTest(replace_unlocked=flag):
                with self.assertRaisesRegex(
                        local_ledger_runtime.RuntimeContractError, "already installed"):
                    local_ledger_runtime.install_runtime(
                        self.runtime_dir, npm_executable=npm, replace_unlocked=flag)
        self.assertEqual(self.snapshot(self.runtime_dir), before)
        self.assertFalse(self.npm_record.exists())

    def test_install_refuses_an_unlocked_runtime_without_the_flag_and_says_how_to_replace(self):
        self.write_unlocked_runtime()
        before = self.snapshot(self.runtime_dir)
        npm = self.fake_npm(self.installed_files())
        with self.assertRaisesRegex(
                local_ledger_runtime.RuntimeContractError, "unlocked.*--replace-unlocked"):
            local_ledger_runtime.install_runtime(self.runtime_dir, npm_executable=npm)
        self.assertEqual(self.snapshot(self.runtime_dir), before)
        self.assertFalse(self.npm_record.exists())
        self.assertEqual(self.sibling_leftovers(), [])

    def test_replace_unlocked_installs_locked_and_leaves_no_staging_or_backup(self):
        self.write_unlocked_runtime()
        result = local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()),
            replace_unlocked=True)
        self.assertEqual(result["state"], "ready")
        status = local_ledger_runtime.runtime_status(self.runtime_dir)
        self.assertEqual((status["state"], status["lock"]), ("ready", "locked"))
        self.assertFalse((self.runtime_dir / "node_modules" / "epiq" / "old-marker.txt").exists())
        self.assertEqual(self.sibling_leftovers(), [])
        self.assertEqual(sorted(path.name for path in Path(self.tmp.name).iterdir()
                                if path.name.startswith("runtime")), ["runtime"])

    def test_replace_unlocked_on_an_absent_runtime_is_a_normal_install(self):
        result = local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()),
            replace_unlocked=True)
        self.assertEqual(result["state"], "ready")
        self.assertEqual(local_ledger_runtime.runtime_status(self.runtime_dir)["lock"], "locked")

    def test_failed_install_during_replace_keeps_the_old_runtime_byte_identical(self):
        self.write_unlocked_runtime()
        before = self.snapshot(self.runtime_dir)
        for script in ('echo "npm ERR! code E404" >&2\nexit 1\n',
                       self.installed_files(version="9.9.9")):
            with self.subTest(script=script[:20]):
                with self.assertRaises(local_ledger_runtime.RuntimeContractError):
                    local_ledger_runtime.install_runtime(
                        self.runtime_dir, npm_executable=self.fake_npm(script),
                        replace_unlocked=True)
                self.assertEqual(self.snapshot(self.runtime_dir), before)
                self.assertEqual(self.sibling_leftovers(), [])

    def test_failure_during_the_swap_restores_the_old_runtime_byte_identical(self):
        self.write_unlocked_runtime()
        before = self.snapshot(self.runtime_dir)
        real_rename = Path.rename

        def flaky(path, target):
            if ".installing-" in path.name:
                raise OSError("simulated rename failure")
            return real_rename(path, target)

        with patch.object(Path, "rename", flaky):
            with self.assertRaisesRegex(
                    local_ledger_runtime.RuntimeContractError, "unable to replace"):
                local_ledger_runtime.install_runtime(
                    self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()),
                    replace_unlocked=True)
        self.assertEqual(self.snapshot(self.runtime_dir), before)
        self.assertEqual(self.sibling_leftovers(), [])

    def test_replace_never_touches_paths_outside_the_runtime_directory(self):
        self.write_unlocked_runtime()
        self.write_project_config()
        (self.project_dir / "notes.txt").write_text("keep\n", encoding="utf-8")
        before = self.snapshot(self.project_dir)
        local_ledger_runtime.install_runtime(
            self.runtime_dir, npm_executable=self.fake_npm(self.installed_files()),
            replace_unlocked=True)
        self.assertEqual(self.snapshot(self.project_dir), before)
        self.assertEqual(self.sibling_leftovers(), [])

    def test_cli_replace_unlocked_requires_the_confirmation_flag_and_changes_nothing(self):
        self.write_unlocked_runtime()
        before = self.snapshot(self.runtime_dir)
        npm = self.fake_npm(self.installed_files())
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "install", "--runtime-dir", str(self.runtime_dir), "--npm", npm,
                "--replace-unlocked", "--format", "json",
            ]), 1)
        self.assertEqual(json.loads(output.getvalue())["state"], "install-confirmation-required")
        self.assertEqual(self.snapshot(self.runtime_dir), before)
        self.assertFalse(self.npm_record.exists())

    def test_cli_replace_unlocked_with_confirmation_replaces_the_runtime(self):
        self.write_unlocked_runtime()
        npm = self.fake_npm(self.installed_files())
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "install", "--runtime-dir", str(self.runtime_dir), "--npm", npm,
                "--confirm-install", "--replace-unlocked", "--format", "json",
            ]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual((payload["state"], payload["lock"]), ("ready", "locked"))

    def test_cli_status_json_includes_the_lock_field(self):
        self.write_runtime()
        output = io.StringIO()
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "status", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["runtime"]["state"], "ready")
        self.assertEqual(payload["runtime"]["lock"], "unlocked")


class StateWorktreeOwnerTests(unittest.TestCase):
    PROJECT_ID = "01M37F8MKQRSB562YCBQ004QGJ"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-state-worktree-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.repo_a = root / "repo-a"
        self.repo_b = root / "repo-b"
        self.global_dir = root / "global"
        self.runtime_dir = root / "runtime"
        for repo in (self.repo_a, self.repo_b):
            self.git(root, "init", "-q", str(repo))
            self.git(repo, "-c", "user.name=t", "-c", "user.email=t@example.test",
                     "commit", "-q", "--allow-empty", "-m", "init")
        (self.repo_a / ".epiq").mkdir()
        (self.repo_a / ".epiq" / "project.json").write_text(json.dumps({
            "projectId": self.PROJECT_ID, "stateBranch": "__epiq_state__",
            "createdAt": "2026-09-24T00:00:00.000Z",
        }), encoding="utf-8")
        package_dir = self.runtime_dir / "node_modules" / local_ledger_runtime.PACKAGE_NAME
        (package_dir / "dist").mkdir(parents=True)
        (package_dir / "package.json").write_text(json.dumps({
            "name": local_ledger_runtime.PACKAGE_NAME,
            "version": local_ledger_runtime.PACKAGE_VERSION,
        }), encoding="utf-8")
        (package_dir / "dist" / "mcp.js").write_text("export {};\n", encoding="utf-8")
        self.worktree = self.global_dir / "worktrees" / self.PROJECT_ID
        env = patch.dict("os.environ", {"EPIQ_GLOBAL_DIR": str(self.global_dir)})
        env.start()
        self.addCleanup(env.stop)

    @staticmethod
    def git(cwd, *arguments):
        subprocess.run(["git", "-C", str(cwd), *arguments], check=True, capture_output=True)

    def add_worktree(self, repo):
        self.worktree.parent.mkdir(parents=True)
        self.git(repo, "worktree", "add", "-q", str(self.worktree), "-b", "__epiq_state__")

    def run_status(self):
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }):
            return local_ledger_runtime.status(self.runtime_dir, self.repo_a)

    def test_worktree_owned_by_another_repository_is_a_conflict(self):
        self.add_worktree(self.repo_b)
        code, payload = self.run_status()
        self.assertEqual(code, 1)
        self.assertEqual(payload["state"], "conflict")
        self.assertEqual(payload["diagnostic"], "ledger-state-worktree-foreign")
        state = payload["project"]["stateWorktree"]
        self.assertEqual(state["state"], "foreign")
        self.assertEqual(state["owner"], str(self.repo_b))
        self.assertEqual(Path(state["path"]).resolve(), self.worktree.resolve())

    def run_text_status(self):
        out = io.StringIO()
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }), redirect_stdout(out):
            code = local_ledger_runtime.main([
                "status", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.repo_a), "--format", "text"])
        return code, out.getvalue()

    def test_text_status_names_the_owner_and_path_of_a_conflict(self):
        self.add_worktree(self.repo_b)
        code, text = self.run_text_status()
        self.assertEqual(code, 1)
        lines = text.splitlines()
        self.assertEqual(lines[0], "本地事项账本状态：conflict")
        self.assertIn("占用仓库：" + str(self.repo_b), lines)
        self.assertTrue(any(line.startswith("状态 worktree：") and
                            Path(line.split("：", 1)[1]).resolve() == self.worktree.resolve()
                            for line in lines), lines)
        self.assertTrue(any("local-ticket-ledger-runtime.md" in line for line in lines), lines)

    def test_text_status_without_conflict_keeps_one_line(self):
        self.add_worktree(self.repo_a)
        code, text = self.run_text_status()
        self.assertEqual((code, text), (0, "本地事项账本状态：initialized\n"))

    def test_worktree_owned_by_this_repository_keeps_the_initialized_result(self):
        self.add_worktree(self.repo_a)
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertNotIn("diagnostic", payload)
        self.assertEqual(payload["project"]["stateWorktree"]["state"], "owned")

    def test_missing_worktree_directory_is_absent(self):
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertEqual(payload["project"]["stateWorktree"]["state"], "absent")

    def test_unparsable_git_file_is_unknown_not_a_conflict(self):
        self.worktree.mkdir(parents=True)
        (self.worktree / ".git").write_text("garbage\n", encoding="utf-8")
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        state = payload["project"]["stateWorktree"]
        self.assertEqual(state["state"], "unknown")
        self.assertEqual(state["diagnostic"], "ledger-state-worktree-unreadable")

    def test_git_directory_instead_of_file_is_unknown(self):
        (self.worktree / ".git").mkdir(parents=True)
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertEqual(payload["project"]["stateWorktree"]["state"], "unknown")

    def test_uninitialized_project_has_no_state_worktree_field(self):
        (self.repo_a / ".epiq" / "project.json").unlink()
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "ready"))
        self.assertNotIn("stateWorktree", payload["project"])

    def test_status_is_read_only_for_worktrees_and_global_dir(self):
        self.add_worktree(self.repo_b)

        def snapshot():
            tree = sorted(str(p.relative_to(self.global_dir)) for p in self.global_dir.rglob("*"))
            listing = [
                subprocess.run(["git", "-C", str(r), "worktree", "list", "--porcelain"],
                               check=True, capture_output=True, text=True).stdout
                for r in (self.repo_a, self.repo_b)
            ]
            return tree, listing
        before = snapshot()
        self.run_status()
        self.assertEqual(before, snapshot())


if __name__ == "__main__":
    unittest.main()
