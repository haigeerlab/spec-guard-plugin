"""Local-ledger runtime contract tests; no package installation or Git mutation."""
import io
import json
import os
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

    def test_project_id_cannot_escape_the_managed_worktree_directory(self):
        self.write_project_config()
        path = self.project_dir / ".epiq" / "project.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        for project_id in ("../other", "/tmp/other", "nested/id", ".."):
            with self.subTest(project_id=project_id):
                config["projectId"] = project_id
                path.write_text(json.dumps(config), encoding="utf-8")
                result = local_ledger_runtime.project_status(self.project_dir)
                self.assertEqual(result["state"], "invalid")

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

    # ledger-local-only: --local-only initializes with an origin without letting Epiq push.

    def test_initialization_preflight_offers_local_only_when_origin_exists(self):
        self.initialize_git_project(origin="https://example.invalid/local-ledger.git")
        code, payload = local_ledger_runtime.initialization_preflight(self.project_dir)
        self.assertEqual((code, payload["state"]), (1, "push-confirmation-required"))
        self.assertEqual(payload["localOnly"], "available")
        code, payload = local_ledger_runtime.initialization_preflight(self.project_dir, local_only=True)
        self.assertEqual((code, payload["state"]), (0, "ready"))
        self.assertEqual(payload["upstreamPush"], "disabled-local-only")
        self.assertEqual(payload["origin"], "https://example.invalid/local-ledger.git")

    def test_initialization_preflight_refuses_local_only_together_with_push_permission(self):
        self.initialize_git_project(origin="https://example.invalid/local-ledger.git")
        code, payload = local_ledger_runtime.initialization_preflight(
            self.project_dir, allow_epiq_push=True, local_only=True)
        self.assertEqual((code, payload["state"]), (1, "invalid"))
        self.assertIn("mutually exclusive", payload["diagnostic"])

    def test_initialization_preflight_without_origin_is_unchanged_by_local_only(self):
        self.initialize_git_project()
        self.assertEqual(local_ledger_runtime.initialization_preflight(self.project_dir, local_only=True),
                         local_ledger_runtime.initialization_preflight(self.project_dir))

    def run_initialize(self, preflight, **kwargs):
        with patch("local_ledger_runtime.initialization_preflight", return_value=preflight) as check, \
             patch("local_ledger_runtime.node_status", return_value={"state": "ready", "path": "/opt/node", "version": "20.0.0"}), \
             patch("local_ledger_runtime.runtime_status", return_value={"state": "ready"}), \
             patch("local_ledger_runtime.mcp_tool_call", return_value={
                 "status": "success", "value": {"projectId": "project", "stateBranch": "__epiq_state__"},
             }) as mcp_call:
            payload = local_ledger_runtime.initialize_project(
                self.runtime_dir, self.project_dir, "Vilin", "code --wait", False, **kwargs)
        return payload, check, mcp_call

    LOCAL_ONLY_PREFLIGHT = (0, {"state": "ready", "projectDir": "/repo", "origin": "https://example.invalid/r.git",
                                "upstreamPush": "disabled-local-only"})

    def test_initialize_local_only_disables_the_origin_push_for_the_epiq_process_only(self):
        with patch.dict("os.environ", {"KEEP": "1"}, clear=False):
            os.environ.pop("GIT_CONFIG_COUNT", None)
            payload, check, mcp_call = self.run_initialize(self.LOCAL_ONLY_PREFLIGHT, local_only=True)
        self.assertEqual(check.call_args.kwargs.get("local_only"), True)
        env = mcp_call.call_args.kwargs["environment"]
        self.assertEqual(env["KEEP"], "1")
        self.assertEqual(env["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(env["GIT_CONFIG_KEY_0"], "remote.origin.pushurl")
        self.assertTrue(env["GIT_CONFIG_VALUE_0"].startswith("/nonexistent/"))
        self.assertEqual(payload["upstreamPush"], "disabled-local-only")
        self.assertNotIn("GIT_CONFIG_COUNT", os.environ)

    def test_initialize_local_only_appends_after_existing_git_config_entries(self):
        with patch.dict("os.environ", {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.x",
                                       "GIT_CONFIG_VALUE_0": "y"}):
            _, _, mcp_call = self.run_initialize(self.LOCAL_ONLY_PREFLIGHT, local_only=True)
        env = mcp_call.call_args.kwargs["environment"]
        self.assertEqual((env["GIT_CONFIG_COUNT"], env["GIT_CONFIG_KEY_0"], env["GIT_CONFIG_VALUE_0"]),
                         ("2", "core.x", "y"))
        self.assertEqual(env["GIT_CONFIG_KEY_1"], "remote.origin.pushurl")

    def test_initialize_without_local_only_keeps_the_inherited_environment(self):
        _, _, mcp_call = self.run_initialize((0, {
            "state": "ready", "projectDir": "/repo", "origin": None, "upstreamPush": "will-fail-as-warning"}))
        self.assertIsNone(mcp_call.call_args.kwargs.get("environment"))

    def test_cli_passes_local_only_and_rejects_it_with_push_permission(self):
        self.initialize_git_project(origin="https://example.invalid/local-ledger.git")
        output = io.StringIO()
        with redirect_stdout(output):
            code = local_ledger_runtime.main(["preflight", "--project-dir", str(self.project_dir),
                                              "--local-only", "--format", "json"])
        self.assertEqual((code, json.loads(output.getvalue())["upstreamPush"]), (0, "disabled-local-only"))
        output = io.StringIO()
        with redirect_stdout(output):
            code = local_ledger_runtime.main(["preflight", "--project-dir", str(self.project_dir),
                                              "--local-only", "--allow-epiq-push", "--format", "json"])
        self.assertEqual((code, json.loads(output.getvalue())["state"]), (1, "invalid"))
        output = io.StringIO()
        with patch("local_ledger_runtime.initialize_project", return_value={
            "state": "initialized", "projectId": "p", "stateBranch": "__epiq_state__",
            "upstreamPush": "disabled-local-only", "warnings": True,
        }) as initialize, redirect_stdout(output):
            local_ledger_runtime.main(["initialize", "--confirm-initialize", "--local-only",
                                       "--project-dir", str(self.project_dir), "--user-name", "V",
                                       "--preferred-editor", "vim", "--auto-sync", "false"])
        self.assertIs(initialize.call_args.kwargs.get("local_only"), True)

    def test_preflight_text_names_both_choices_when_origin_exists(self):
        self.initialize_git_project(origin="https://example.invalid/local-ledger.git")
        output = io.StringIO()
        with redirect_stdout(output):
            local_ledger_runtime.main(["preflight", "--project-dir", str(self.project_dir)])
        self.assertIn("--local-only", output.getvalue())
        self.assertIn("--allow-epiq-push", output.getvalue())

    # remote-credential-redaction: credentials in the origin URL never reach the preflight output.

    def test_redact_url_hides_the_whole_userinfo_of_a_scheme_url(self):
        cases = {
            "https://user:SECRET@example.invalid/repo.git": "https://***@example.invalid/repo.git",
            "https://SECRET@example.invalid/repo.git": "https://***@example.invalid/repo.git",
            "ssh://git:SECRET@example.invalid:2222/repo.git": "ssh://***@example.invalid:2222/repo.git",
        }
        for url, redacted in cases.items():
            with self.subTest(url=url):
                self.assertEqual(local_ledger_runtime.redact_url(url), (redacted, True))

    def test_redact_url_leaves_urls_without_userinfo_unchanged(self):
        for url in ("https://example.invalid/repo.git", "git@github.com:org/repo.git", "/srv/repo.git",
                    "file:///srv/repo.git", "https://example.invalid/path@v1/repo.git", "", "::not a url::"):
            with self.subTest(url=url):
                self.assertEqual(local_ledger_runtime.redact_url(url), (url, False))

    def test_initialization_preflight_never_prints_origin_credentials(self):
        self.initialize_git_project(origin="https://user:SECRET@example.invalid/local-ledger.git")
        for allow in (False, True):
            with self.subTest(allow_epiq_push=allow):
                code, payload = local_ledger_runtime.initialization_preflight(
                    self.project_dir, allow_epiq_push=allow)
                self.assertEqual((code, payload["state"]), (0, "ready") if allow else (1, "push-confirmation-required"))
                self.assertNotIn("SECRET", json.dumps(payload))
                self.assertEqual(payload["origin"], "https://***@example.invalid/local-ledger.git")
                self.assertIs(payload["originCredentialsRedacted"], True)

    def test_initialization_preflight_marks_nothing_when_origin_has_no_credentials(self):
        self.initialize_git_project(origin="git@github.com:org/local-ledger.git")
        code, payload = local_ledger_runtime.initialization_preflight(self.project_dir)
        self.assertEqual(payload["origin"], "git@github.com:org/local-ledger.git")
        self.assertNotIn("originCredentialsRedacted", payload)

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

    def test_project_init_arguments_pass_only_the_given_user_setup_values(self):
        arguments = local_ledger_runtime.project_init_arguments(
            self.project_dir, " Vilin ", "code --wait", False)
        self.assertEqual(arguments, {
            "repoRoot": str(self.project_dir),
            "userName": "Vilin",
            "preferredEditor": "code --wait",
            "autoSync": False,
        })
        # ledger-init-machine-config: values the machine already has are left to Epiq.
        self.assertEqual(local_ledger_runtime.project_init_arguments(self.project_dir),
                         {"repoRoot": str(self.project_dir)})
        self.assertEqual(local_ledger_runtime.project_init_arguments(self.project_dir, auto_sync=True),
                         {"repoRoot": str(self.project_dir), "autoSync": True})
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "user name must not be empty"):
            local_ledger_runtime.project_init_arguments(self.project_dir, " ", "code --wait", False)
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "preferred editor must not be empty"):
            local_ledger_runtime.project_init_arguments(self.project_dir, preferred_editor="")
        with self.assertRaisesRegex(local_ledger_runtime.RuntimeContractError, "auto sync must be a boolean"):
            local_ledger_runtime.project_init_arguments(self.project_dir, auto_sync="false")

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
                 "value": {"projectId": "project", "stateBranch": "__epiq_state__",
                           "warnings": ["[init:15] do not print this", "[init:15] nor this", "no code here"]},
             }) as mcp_call:
            payload = local_ledger_runtime.initialize_project(
                self.runtime_dir, self.project_dir, "Vilin", "code --wait", False,
            )
        self.assertEqual(payload, {
            "state": "initialized", "projectId": "project", "stateBranch": "__epiq_state__",
            "upstreamPush": "will-fail-as-warning", "warnings": True,
            "warningCount": 3, "warningCodes": ["init:15"],
        })
        self.assertNotIn("print this", json.dumps(payload))
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

    def test_initialize_cli_requires_confirmation_but_not_user_setup_before_starting_epiq(self):
        output = io.StringIO()
        with patch("local_ledger_runtime.initialize_project") as initialize, redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "initialize", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 1)
        self.assertEqual(json.loads(output.getvalue())["state"], "initialization-confirmation-required")
        initialize.assert_not_called()

        output = io.StringIO()
        with patch("local_ledger_runtime.initialize_project", return_value={
            "state": "initialized", "projectId": "p", "stateBranch": "__epiq_state__", "upstreamPush": "none",
            "warnings": False, "warningCount": 0, "warningCodes": [],
        }) as initialize, redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "initialize", "--confirm-initialize", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--format", "json",
            ]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "initialized")
        initialize.assert_called_once()
        self.assertEqual(initialize.call_args.args[2:5], (None, None, None))

    def test_initialize_cli_passes_only_the_given_values_and_prints_warning_codes(self):
        output = io.StringIO()
        with patch("local_ledger_runtime.initialize_project", return_value={
            "state": "initialized", "projectId": "p", "stateBranch": "__epiq_state__",
            "upstreamPush": "none", "warnings": True, "warningCount": 2, "warningCodes": ["init:14", "init:15"],
        }) as initialize, redirect_stdout(output):
            self.assertEqual(local_ledger_runtime.main([
                "initialize", "--confirm-initialize", "--runtime-dir", str(self.runtime_dir),
                "--project-dir", str(self.project_dir), "--auto-sync", "false",
            ]), 0)
        self.assertEqual(initialize.call_args.args[2:5], (None, None, False))
        self.assertIn("Epiq 初始化有 2 条警告（init:14、init:15）", output.getvalue())


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

    def test_text_status_without_conflict_adds_only_the_pending_count_line(self):
        self.add_worktree(self.repo_a)
        code, text = self.run_text_status()
        self.assertEqual((code, text), (0, "本地事项账本状态：initialized\n未提交到状态分支的事件：0 条\n"))

    # ledger-local-only: with autoSync off Epiq leaves events as untracked ~pending files; status counts them.

    def write_events(self, name, text):
        events = self.worktree / ".epiq" / "events"
        events.mkdir(parents=True, exist_ok=True)
        (events / name).write_text(text, encoding="utf-8")
        return events

    def test_status_counts_non_empty_lines_of_pending_event_files(self):
        self.add_worktree(self.repo_a)
        self.write_events("a.jsonl", '{"committed":1}\n')
        self.write_events("a~pending.jsonl", '{"e":1}\n{"e":2}\n\n')
        self.write_events("b~pending-x1.jsonl", '{"e":3}')
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertEqual(payload["project"]["pendingEvents"], 3)
        _, text = self.run_text_status()
        self.assertIn("未提交到状态分支的事件：3 条", text)
        self.assertIn("离线归档", text)

    def test_status_reports_zero_pending_events_without_a_reminder(self):
        self.add_worktree(self.repo_a)
        self.write_events("a.jsonl", '{"committed":1}\n')
        code, payload = self.run_status()
        self.assertEqual(payload["project"]["pendingEvents"], 0)
        _, text = self.run_text_status()
        self.assertNotIn("离线归档", text)

    def test_unreadable_events_directory_reports_null_and_keeps_the_state(self):
        self.add_worktree(self.repo_a)
        events = self.write_events("a~pending.jsonl", '{"e":1}\n')
        events.chmod(0)
        self.addCleanup(events.chmod, 0o700)
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertIsNone(payload["project"]["pendingEvents"])
        _, text = self.run_text_status()
        self.assertNotIn("未提交到状态分支的事件", text)

    # ledger-local-only: the identity is committed on the branch init ran on; a checkout without it says where it is.

    def commit_identity_on_branch(self, repo, branch):
        self.git(repo, "switch", "-q", "-c", branch)
        (repo / ".epiq").mkdir(exist_ok=True)
        (repo / ".epiq" / "project.json").write_text(json.dumps({
            "projectId": self.PROJECT_ID, "stateBranch": "__epiq_state__",
            "createdAt": "2026-09-24T00:00:00.000Z"}), encoding="utf-8")
        self.git(repo, "add", ".epiq/project.json")
        self.git(repo, "-c", "user.name=t", "-c", "user.email=t@example.test", "commit", "-q", "-m", "id")
        self.git(repo, "switch", "-q", "-")

    def status_of(self, repo):
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0",
        }):
            return local_ledger_runtime.status(self.runtime_dir, repo)

    def test_uninitialized_checkout_names_the_branch_that_holds_the_identity(self):
        self.commit_identity_on_branch(self.repo_b, "ledger-setup")
        code, payload = self.status_of(self.repo_b)
        self.assertEqual((code, payload["state"]), (0, "ready"))
        self.assertEqual(payload["project"]["identityElsewhere"], "ledger-setup")
        out = io.StringIO()
        with patch("local_ledger_runtime.node_status", return_value={
            "state": "ready", "path": "/opt/node", "version": "20.0.0"}), redirect_stdout(out):
            local_ledger_runtime.main(["status", "--runtime-dir", str(self.runtime_dir),
                                       "--project-dir", str(self.repo_b)])
        self.assertIn("ledger-setup", out.getvalue())
        self.assertIn("默认分支", out.getvalue())

    def test_identity_on_the_state_branch_only_is_not_reported(self):
        self.commit_identity_on_branch(self.repo_b, "__epiq_state__")
        code, payload = self.status_of(self.repo_b)
        self.assertNotIn("identityElsewhere", payload["project"])

    def test_no_identity_anywhere_reports_nothing(self):
        code, payload = self.status_of(self.repo_b)
        self.assertEqual((code, payload["state"]), (0, "ready"))
        self.assertNotIn("identityElsewhere", payload["project"])

    def test_failed_branch_query_reports_nothing_and_keeps_the_state(self):
        self.commit_identity_on_branch(self.repo_b, "ledger-setup")
        with patch("local_ledger_runtime._git", return_value=None):
            code, payload = self.status_of(self.repo_b)
        self.assertEqual((code, payload["state"]), (0, "ready"))
        self.assertNotIn("identityElsewhere", payload["project"])

    def test_initialize_text_says_to_merge_the_identity_and_whether_it_pushed(self):
        for push, expect_local in (("disabled-local-only", True), ("permitted", False)):
            out = io.StringIO()
            with self.subTest(upstreamPush=push), patch("local_ledger_runtime.initialize_project", return_value={
                "state": "initialized", "projectId": "p", "stateBranch": "__epiq_state__",
                "upstreamPush": push, "warnings": True,
            }), redirect_stdout(out):
                local_ledger_runtime.main(["initialize", "--confirm-initialize", "--project-dir", str(self.repo_b),
                                           "--user-name", "V", "--preferred-editor", "vim", "--auto-sync", "false"])
                self.assertIn("合进默认分支", out.getvalue())
                self.assertEqual("未推送" in out.getvalue(), expect_local)

    def test_pending_count_is_only_reported_for_an_owned_worktree(self):
        self.add_worktree(self.repo_b)
        code, payload = self.run_status()
        self.assertNotIn("pendingEvents", payload["project"])

    def test_worktree_owned_by_this_repository_keeps_the_initialized_result(self):
        self.add_worktree(self.repo_a)
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertNotIn("diagnostic", payload)
        self.assertEqual(payload["project"]["stateWorktree"]["state"], "owned")

    def test_missing_worktree_directory_is_absent(self):
        self.git(self.repo_a, "branch", "__epiq_state__")
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertEqual(payload["project"]["stateWorktree"]["state"], "absent")

    def test_missing_state_branch_is_unknown_not_empty_ledger(self):
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        state = payload["project"]["stateWorktree"]
        self.assertEqual(state["state"], "unknown")
        self.assertEqual(state["diagnostic"], "ledger-state-branch-missing")

    def test_state_branch_checked_out_elsewhere_is_not_absent(self):
        detached = Path(self.tmp.name) / "detached-state"
        self.git(self.repo_a, "worktree", "add", "-q", "-b", "__epiq_state__", str(detached))
        pending = detached / ".epiq" / "events" / "fixture~pending.jsonl"
        pending.parent.mkdir(parents=True)
        pending.write_text('{"synthetic":true}\n', encoding="utf-8")
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        state = payload["project"]["stateWorktree"]
        self.assertEqual(state["state"], "unknown")
        self.assertEqual(state["diagnostic"], "ledger-state-worktree-away")
        self.assertEqual(Path(state["checkedOutAt"]).resolve(), detached.resolve())
        self.assertEqual(pending.read_text(encoding="utf-8"), '{"synthetic":true}\n')
        text_code, text = self.run_text_status()
        self.assertEqual(text_code, 0)
        self.assertIn("状态 worktree 未确认：ledger-state-worktree-away", text)
        self.assertIn("状态分支检出于：", text)

    def test_symlink_at_managed_path_is_not_absent_or_owned(self):
        target = Path(self.tmp.name) / "target"
        target.mkdir()
        self.worktree.parent.mkdir(parents=True)
        self.worktree.symlink_to(target, target_is_directory=True)
        code, payload = self.run_status()
        self.assertEqual((code, payload["state"]), (0, "initialized"))
        self.assertEqual(payload["project"]["stateWorktree"]["state"], "unknown")

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


class EpiqStorageCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-epiq-storage-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "epiq-global"

    def test_absent_and_private_directories_are_read_only(self):
        code, result = local_ledger_runtime.storage_check(self.root)
        self.assertEqual((code, result["state"]), (0, "absent"))
        self.assertFalse(self.root.exists())
        self.root.mkdir(mode=0o700)
        secret = self.root / "event.jsonl"
        secret.write_text("private ticket content\n", encoding="utf-8")
        before = (self.root.stat().st_mode, self.root.stat().st_mtime_ns, secret.read_bytes())
        code, result = local_ledger_runtime.storage_check(self.root)
        self.assertEqual((code, result["state"]), (0, "private-posix"))
        self.assertEqual(result["mode"], "0700")
        self.assertEqual((self.root.stat().st_mode, self.root.stat().st_mtime_ns,
                          secret.read_bytes()), before)
        self.assertNotIn("private ticket content", json.dumps(result))

    def test_exposed_and_unusable_modes_do_not_report_private(self):
        self.root.mkdir(mode=0o700)
        for mode, expected in ((0o755, "exposed"), (0o711, "exposed"),
                               (0o500, "unusable"), (0o111, "unusable")):
            with self.subTest(mode=mode):
                self.root.chmod(mode)
                code, result = local_ledger_runtime.storage_check(self.root)
                self.assertEqual((code, result["state"]), (1, expected))
                self.assertEqual(result["mode"], format(mode, "04o"))
        self.root.chmod(0o700)

    def test_symlink_file_and_foreign_owner_are_unsafe(self):
        target = self.root.parent / "target"
        target.mkdir(mode=0o700)
        self.root.symlink_to(target, target_is_directory=True)
        code, result = local_ledger_runtime.storage_check(self.root)
        self.assertEqual((code, result["state"]), (1, "unsafe"))
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.root.unlink()
        self.root.write_text("not a directory", encoding="utf-8")
        code, result = local_ledger_runtime.storage_check(self.root)
        self.assertEqual((code, result["state"]), (1, "unsafe"))
        self.root.unlink()
        self.root.mkdir(mode=0o700)
        with patch("local_ledger_runtime.os.getuid", return_value=os.getuid() + 1):
            code, result = local_ledger_runtime.storage_check(self.root)
        self.assertEqual((code, result["state"]), (1, "unsafe"))

    def test_relative_path_and_unreadable_metadata_are_unknown(self):
        code, result = local_ledger_runtime.storage_check(Path("relative-epiq-global"))
        self.assertEqual((code, result["state"]), (1, "unknown"))
        with patch.object(Path, "lstat", side_effect=PermissionError):
            code, result = local_ledger_runtime.storage_check(self.root)
        self.assertEqual((code, result["state"]), (1, "unknown"))

    def test_protect_preview_is_read_only_and_confirm_changes_only_root_mode(self):
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o755)
        event = self.root / "event.jsonl"
        event.write_text("private history\n", encoding="utf-8")
        event_before = (event.stat().st_mode, event.read_bytes())
        code, preview = local_ledger_runtime.storage_protect(self.root)
        self.assertEqual((code, preview["state"]), (0, "protectable"))
        self.assertEqual((preview["mode"], preview["targetMode"]), ("0755", "0700"))
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)
        code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
        self.assertEqual((code, result["state"]), (0, "protected"))
        self.assertEqual((result["previousMode"], result["mode"]), ("0755", "0700"))
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((event.stat().st_mode, event.read_bytes()), event_before)
        code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
        self.assertEqual((code, result["state"]), (0, "already-private"))

    def test_protect_rejects_absent_symlink_foreign_owner_and_writable_parent(self):
        code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
        self.assertEqual((code, result["state"]), (1, "absent"))
        target = self.root.parent / "target"
        target.mkdir(mode=0o700)
        self.root.symlink_to(target, target_is_directory=True)
        code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
        self.assertEqual((code, result["state"]), (1, "unsafe"))
        self.root.unlink()
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o755)
        with patch("local_ledger_runtime.os.getuid", return_value=os.getuid() + 1):
            code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
        self.assertEqual((code, result["state"]), (1, "unsafe"))
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)
        self.root.parent.chmod(0o777)
        try:
            code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
            self.assertEqual((code, result["state"]), (1, "unsafe"))
            self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)
        finally:
            self.root.parent.chmod(0o700)

    def test_protect_does_not_follow_path_swapped_to_symlink(self):
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o755)
        target = self.root.parent / "target"
        target.mkdir(mode=0o700)
        original_open = os.open

        def swap_then_open(path, flags):
            self.root.rename(self.root.parent / "original")
            self.root.symlink_to(target, target_is_directory=True)
            return original_open(path, flags)

        with patch("local_ledger_runtime.os.open", side_effect=swap_then_open):
            code, result = local_ledger_runtime.storage_protect(self.root, confirm=True)
        self.assertNotEqual(code, 0)
        self.assertIn(result["state"], ("unsafe", "unknown"))
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root.parent / "original").stat().st_mode & 0o777, 0o755)

    def test_cli_protect_requires_confirm(self):
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o755)
        with patch.dict(os.environ, {"EPIQ_GLOBAL_DIR": str(self.root)}):
            output = io.StringIO()
            with redirect_stdout(output):
                code = local_ledger_runtime.main(["storage-protect", "--format", "json"])
            self.assertEqual((code, json.loads(output.getvalue())["state"]), (0, "protectable"))
            self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)
            output = io.StringIO()
            with redirect_stdout(output):
                code = local_ledger_runtime.main([
                    "storage-protect", "--confirm-protect", "--format", "json",
                ])
            self.assertEqual((code, json.loads(output.getvalue())["state"]), (0, "protected"))
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_cli_checks_selected_epiq_global_dir_without_contents(self):
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o755)
        (self.root / "event.jsonl").write_text("sensitive history\n", encoding="utf-8")
        output = io.StringIO()
        with patch.dict(os.environ, {"EPIQ_GLOBAL_DIR": str(self.root)}), redirect_stdout(output):
            code = local_ledger_runtime.main(["storage-check", "--format", "json"])
        result = json.loads(output.getvalue())
        self.assertEqual((code, result["state"]), (1, "exposed"))
        self.assertEqual(result["path"], str(self.root))
        self.assertNotIn("sensitive history", output.getvalue())
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)


# ledger-init-machine-config: Epiq's refusal message is reported, cleaned.
class EpiqRefusalMessageTests(unittest.TestCase):
    def read(self, payload):
        text = json.dumps(json.dumps(payload))
        return io.StringIO('{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":%s}]}}\n' % text)

    def refusal(self, payload):
        with self.assertRaises(local_ledger_runtime.RuntimeContractError) as caught:
            local_ledger_runtime.read_mcp_tool_result(self.read(payload), 1)
        return str(caught.exception)

    def test_refusal_reports_epiq_message(self):
        message = 'This machine is already set up with userName "A"; epiq_project_init does not change it.'
        self.assertEqual(self.refusal({"status": "error", "message": message}), "Epiq refused: " + message)

    def test_refusal_message_is_cleaned(self):
        diagnostic = self.refusal({"status": "error", "message":
                                   "push https://user:SECRET@example.invalid/r.git\n\tthen ssh://TOKEN@host/x  failed\x1b[0m"})
        self.assertNotIn("SECRET", diagnostic)
        self.assertNotIn("TOKEN", diagnostic)
        self.assertIn("https://***@example.invalid/r.git", diagnostic)
        self.assertIn("ssh://***@host/x", diagnostic)
        self.assertNotRegex(diagnostic, r"[\x00-\x1f\x7f]")
        self.assertNotIn("  ", diagnostic)

    def test_refusal_message_is_truncated(self):
        diagnostic = self.refusal({"status": "error", "message": "x" * 1000})
        self.assertEqual(diagnostic, "Epiq refused: " + "x" * 300 + "…")

    def test_refusal_without_a_string_message_keeps_the_old_text(self):
        for payload in ({"status": "error"}, {"status": "error", "message": 3}, {"status": "error", "message": "  "}):
            self.assertEqual(self.refusal(payload), "MCP tool response is unsuccessful")


# ledger-init-machine-config: status reads which of the three setup values the machine already has.
class MachineSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-machine-setup-")
        self.addCleanup(self.tmp.cleanup)
        self.global_dir = Path(self.tmp.name) / ".epiq-global"
        self.global_dir.mkdir()
        self.config = self.global_dir / "config.json"

    def setup_of(self):
        return local_ledger_runtime.machine_setup(self.global_dir)

    def test_absent_config(self):
        self.assertEqual(self.setup_of(), {"state": "absent"})

    def test_read_config_reports_only_the_three_values(self):
        self.config.write_text(json.dumps({
            "userName": "A", "preferredEditor": "code --wait", "autoSync": False, "userId": "secret-id",
        }), encoding="utf-8")
        before = self.config.stat().st_mtime_ns
        self.assertEqual(self.setup_of(), {
            "state": "read", "userName": "A", "preferredEditor": "code --wait", "autoSync": False,
        })
        self.assertEqual(self.config.stat().st_mtime_ns, before)

    def test_missing_blank_or_mistyped_values_are_null(self):
        self.config.write_text(json.dumps({"userName": "  ", "autoSync": "yes"}), encoding="utf-8")
        self.assertEqual(self.setup_of(), {
            "state": "read", "userName": None, "preferredEditor": None, "autoSync": None,
        })

    def test_unreadable_config_is_unknown_not_unset(self):
        cases = {
            "invalid-json": lambda: self.config.write_text("{", encoding="utf-8"),
            "not-object": lambda: self.config.write_text("[]", encoding="utf-8"),
            "too-large": lambda: self.config.write_text(" " * (64 * 1024 + 1) + "{}", encoding="utf-8"),
            "directory": lambda: self.config.mkdir(),
            "symlink": lambda: self.config.symlink_to(self.global_dir),
        }
        for name, make in cases.items():
            with self.subTest(name):
                if self.config.is_symlink() or self.config.is_file():
                    self.config.unlink()
                elif self.config.is_dir():
                    self.config.rmdir()
                make()
                setup = self.setup_of()
                self.assertEqual(setup["state"], "unknown")
                self.assertIsInstance(setup.get("diagnostic"), str)

    def test_status_uses_epiq_global_dir_and_keeps_its_state(self):
        self.config.write_text(json.dumps({"userName": "A"}), encoding="utf-8")
        project = Path(self.tmp.name) / "project"
        project.mkdir()
        output = io.StringIO()
        with patch.dict(os.environ, {"EPIQ_GLOBAL_DIR": str(self.global_dir)}), redirect_stdout(output):
            code = local_ledger_runtime.main([
                "status", "--runtime-dir", str(Path(self.tmp.name) / "runtime"),
                "--project-dir", str(project), "--format", "json",
            ])
        payload = json.loads(output.getvalue())
        self.assertEqual((code, payload["state"]), (0, "absent"))
        self.assertEqual(payload["machineSetup"], {
            "state": "read", "userName": "A", "preferredEditor": None, "autoSync": None,
        })

    def test_status_text_names_the_set_and_missing_values(self):
        self.config.write_text(json.dumps({"userName": "A", "autoSync": False}), encoding="utf-8")
        output = io.StringIO()
        with patch.dict(os.environ, {"EPIQ_GLOBAL_DIR": str(self.global_dir)}), redirect_stdout(output):
            local_ledger_runtime.main(["status", "--runtime-dir", str(Path(self.tmp.name) / "runtime"),
                                       "--project-dir", self.tmp.name])
        text = output.getvalue()
        self.assertIn('本机 Epiq 已设置：userName="A"、autoSync=false', text)
        self.assertIn("未设置：preferredEditor", text)


if __name__ == "__main__":
    unittest.main()
