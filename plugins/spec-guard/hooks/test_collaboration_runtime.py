"""Collaboration runtime contract tests; never start a daemon or read a real token."""
import io
import json
import os
import plistlib
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

import collaboration_runtime
from collaboration_adapters import (CHANNEL_SERVER_NAME, MCP_SERVER_NAME, TOKEN_ENV_VAR,
                                    claude_mcp_config, codex_toml_fragment, install_claude_config,
                                    install_codex_config)
from collaboration_auth_header import authorization_header, main as auth_header_main
from collaboration_claude import (build_claude_command, build_tmux_command,
                                  launch_tmux_claude, write_ephemeral_mcp_config)
from collaboration_claude_stdio import (MCP_REMOTE_AUTH_ENV_VAR, MCP_REMOTE_PACKAGE,
                                        MCP_REMOTE_VERSION, mcp_remote_command)
from collaboration_runtime import (HEALTH_PROTOCOL_VERSION, LOCAL_NAMESPACE, PACKAGE_NAME, PACKAGE_VERSION, RuntimeContractError,
                                   daemon_command, initialize_runtime, main, read_runtime_config,
                                   runtime_contract)


class CollaborationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-collaboration-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.config_dir = Path(self.tmp.name) / "runtime"
        self.config_dir.mkdir(mode=0o700)

    def write_config(self, **overrides):
        config = {
            "host": "127.0.0.1",
            "port": 9100,
            "package": PACKAGE_NAME,
            "packageVersion": PACKAGE_VERSION,
            "tokenFile": "token",
        }
        config.update(overrides)
        (self.config_dir / "runtime.json").write_text(
            json.dumps(config), encoding="utf-8")
        token = self.config_dir / config["tokenFile"]
        token.write_text("test-only-token\n", encoding="utf-8")
        token.chmod(0o600)

    def test_contract_pins_the_audited_package_and_loopback_defaults(self):
        contract = runtime_contract()
        self.assertEqual(contract["package"], "cross-agent-teams-mcp")
        self.assertEqual(contract["packageVersion"], "0.8.6")
        self.assertEqual(contract["host"], "127.0.0.1")
        self.assertEqual(contract["defaultPort"], 9100)
        self.assertEqual(contract["localNamespace"], "spec-guard-local")
        self.assertEqual(HEALTH_PROTOCOL_VERSION, "0.1.0")
        self.assertNotIn("latest", json.dumps(contract))

    def test_initialization_creates_fresh_private_runtime_without_printing_token(self):
        initialized_dir = Path(self.tmp.name) / "initialized"
        config = initialize_runtime(initialized_dir, port=9191)
        self.assertEqual(config.port, 9191)
        self.assertEqual(stat.S_IMODE(initialized_dir.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(config.token_file.stat().st_mode), 0o600)
        self.assertTrue(config.token_file.read_text(encoding="utf-8").strip())
        with self.assertRaisesRegex(RuntimeContractError, "already exists"):
            initialize_runtime(initialized_dir)

        command = daemon_command(initialized_dir, config)
        self.assertIn("cross-agent-teams-mcp@0.8.6", command)
        self.assertIn("daemon", command)
        self.assertIn("127.0.0.1", command)
        self.assertNotIn(config.token_file.read_text(encoding="utf-8").strip(), command)


        cli_dir = Path(self.tmp.name) / "cli-initialized"
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["init", "--config-dir", str(cli_dir), "--format", "json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "initialized")
        self.assertNotIn("token", output.getvalue().lower())

    def test_valid_private_configuration_is_loaded_without_exposing_token(self):
        self.write_config()
        config = read_runtime_config(self.config_dir)
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 9100)
        self.assertEqual(config.token_file, self.config_dir / "token")
        self.assertNotIn("test-only-token", repr(config))

    def test_only_loopback_and_the_pinned_package_are_accepted(self):
        self.write_config(host="0.0.0.0")
        with self.assertRaisesRegex(RuntimeContractError, "loopback"):
            read_runtime_config(self.config_dir)

        self.write_config(host="127.0.0.1", packageVersion="latest")
        with self.assertRaisesRegex(RuntimeContractError, "packageVersion"):
            read_runtime_config(self.config_dir)

    def test_token_must_be_a_private_file_inside_the_runtime_directory(self):
        self.write_config()
        (self.config_dir / "token").chmod(0o644)
        with self.assertRaisesRegex(RuntimeContractError, "0600"):
            read_runtime_config(self.config_dir)

        self.write_config(tokenFile="../token")
        with self.assertRaisesRegex(RuntimeContractError, "tokenFile"):
            read_runtime_config(self.config_dir)

    def test_symlinked_private_runtime_paths_are_rejected(self):
        target = Path(self.tmp.name) / "target"
        target.mkdir(mode=0o700)
        linked_dir = Path(self.tmp.name) / "linked-runtime"
        linked_dir.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeContractError, "not be a symbolic link"):
            read_runtime_config(linked_dir)

        self.write_config()
        replacement = self.config_dir / "replacement-token"
        replacement.write_text("test-only-token\n", encoding="utf-8")
        replacement.chmod(0o600)
        (self.config_dir / "token").unlink()
        (self.config_dir / "token").symlink_to(replacement)
        with self.assertRaisesRegex(RuntimeContractError, "regular file"):
            read_runtime_config(self.config_dir)

    def test_status_cli_reports_absent_or_valid_without_creating_files_or_leaking_token(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["status", "--config-dir", str(self.config_dir), "--format", "json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "absent")
        self.assertFalse((self.config_dir / "runtime.json").exists())

        self.write_config()
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["status", "--config-dir", str(self.config_dir), "--format", "json"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["state"], "valid")
        self.assertNotIn("test-only-token", output.getvalue())

    def test_start_cli_text_output_handles_a_successful_minimal_daemon_payload(self):
        output = io.StringIO()
        with patch("collaboration_runtime.start_daemon", return_value={
            "state": "started", "pid": 1234, "host": "127.0.0.1", "port": 9100,
        }):
            with redirect_stdout(output):
                self.assertEqual(main(["start", "--config-dir", str(self.config_dir)]), 0)
        self.assertIn("cross-agent-teams-mcp@0.8.6", output.getvalue())

    def test_launch_agent_plist_has_no_token_and_uses_the_runtime_serve_command(self):
        self.write_config()
        token = (self.config_dir / "token").read_text(encoding="utf-8").strip()
        plist = collaboration_runtime.launch_agent_plist(
            self.config_dir,
            Path("/opt/spec-guard/collaboration_runtime.py"),
            "/usr/bin/python3",
            "/opt/homebrew/bin/npx",
        )
        self.assertEqual(plist["Label"], "com.specguard.collaboration")
        self.assertEqual(plist["ProgramArguments"], [
            "/usr/bin/python3", "/opt/spec-guard/collaboration_runtime.py", "serve",
            "--config-dir", str(self.config_dir), "--npx", "/opt/homebrew/bin/npx",
        ])
        self.assertTrue(plist["RunAtLoad"])
        self.assertTrue(plist["KeepAlive"])
        self.assertEqual(
            plist["EnvironmentVariables"]["PATH"],
            "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        )
        self.assertIn(str(self.config_dir / "daemon.stdout.log"), plist.values())
        self.assertIn(str(self.config_dir / "daemon.stderr.log"), plist.values())
        self.assertNotIn(token, json.dumps(plist))

    def test_launch_agent_plist_adds_tmux_directory_without_changing_npx_priority(self):
        plist = collaboration_runtime.launch_agent_plist(
            self.config_dir, Path("/opt/spec-guard/collaboration_runtime.py"),
            "/usr/bin/python3", "/opt/node/bin/npx",
            tmux_executable="/opt/homebrew/bin/tmux",
        )
        self.assertEqual(
            plist["EnvironmentVariables"]["PATH"],
            "/opt/node/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        )
        self.assertNotIn("tmux", " ".join(plist["ProgramArguments"]))

    def test_launch_agent_plist_rejects_unsafe_tmux_path(self):
        for tmux_path in ("relative/tmux", "/tmp/unsafe:dir/tmux", "/tmp/line\nbreak/tmux"):
            with self.subTest(tmux_path=tmux_path):
                with self.assertRaisesRegex(RuntimeContractError, "tmux path"):
                    collaboration_runtime.launch_agent_plist(
                        self.config_dir, Path("/opt/spec-guard/collaboration_runtime.py"),
                        "/usr/bin/python3", "/opt/homebrew/bin/npx", tmux_path,
                    )

    def test_explicit_service_enable_uses_discovered_tmux(self):
        self.write_config()
        launch_agents_dir = Path(self.tmp.name) / "Library" / "LaunchAgents"
        with patch("collaboration_runtime.shutil.which", return_value="/opt/homebrew/bin/tmux"), \
             patch("collaboration_runtime.os.getuid", return_value=501), \
             patch("collaboration_runtime.subprocess.run"):
            plist_path = collaboration_runtime.enable_background_service(
                self.config_dir, launch_agents_dir,
                Path("/opt/spec-guard/collaboration_runtime.py"), "/usr/bin/python3",
                "/opt/node/bin/npx",
            )
        with plist_path.open("rb") as handle:
            plist = plistlib.load(handle)
        self.assertIn("/opt/homebrew/bin", plist["EnvironmentVariables"]["PATH"])

    def test_enable_background_service_writes_private_logs_and_bootstraps_current_user(self):
        self.write_config()
        launch_agents_dir = Path(self.tmp.name) / "Library" / "LaunchAgents"
        token = (self.config_dir / "token").read_text(encoding="utf-8").strip()
        with patch("collaboration_runtime.os.getuid", return_value=501), \
             patch("collaboration_runtime.subprocess.run") as run:
            plist_path = collaboration_runtime.enable_background_service(
                self.config_dir, launch_agents_dir,
                Path("/opt/spec-guard/collaboration_runtime.py"), "/usr/bin/python3",
                "/opt/homebrew/bin/npx",
            )
        with plist_path.open("rb") as handle:
            plist = plistlib.load(handle)
        self.assertEqual(plist["Label"], "com.specguard.collaboration")
        self.assertNotIn(token, plist_path.read_text(encoding="utf-8"))
        self.assertEqual(stat.S_IMODE((self.config_dir / "daemon.stdout.log").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.config_dir / "daemon.stderr.log").stat().st_mode), 0o600)
        run.assert_called_once_with(
            ["launchctl", "bootstrap", "gui/501", str(plist_path)],
            check=True, capture_output=True, text=True,
        )

    def test_enable_background_service_refuses_an_unknown_same_name_plist(self):
        self.write_config()
        launch_agents_dir = Path(self.tmp.name) / "Library" / "LaunchAgents"
        launch_agents_dir.mkdir(parents=True)
        plist_path = launch_agents_dir / "com.specguard.collaboration.plist"
        plist_path.write_text("not a managed plist\n", encoding="utf-8")
        with patch("collaboration_runtime.subprocess.run") as run:
            with self.assertRaisesRegex(RuntimeContractError, "refusing to overwrite"):
                collaboration_runtime.enable_background_service(
                    self.config_dir, launch_agents_dir,
                    Path("/opt/spec-guard/collaboration_runtime.py"), "/usr/bin/python3",
                    "/opt/homebrew/bin/npx",
                )
        self.assertEqual(plist_path.read_text(encoding="utf-8"), "not a managed plist\n")
        run.assert_not_called()

    def test_serve_daemon_injects_the_token_only_into_the_exec_environment(self):
        self.write_config()
        with patch("collaboration_auth_header.read_private_token", return_value="test-only-token"), \
             patch("collaboration_runtime.os.execvpe", side_effect=RuntimeError("exec called")) as execvpe:
            with self.assertRaisesRegex(RuntimeError, "exec called"):
                collaboration_runtime.serve_daemon(self.config_dir, "/opt/homebrew/bin/npx")
        executable, command, environment = execvpe.call_args.args
        self.assertEqual(executable, "/opt/homebrew/bin/npx")
        self.assertEqual(command[0], "/opt/homebrew/bin/npx")
        self.assertIn("cross-agent-teams-mcp@0.8.6", command)
        self.assertEqual(environment["CROSS_AGENT_TEAMS_MCP_TOKEN"], "test-only-token")
        self.assertNotIn("test-only-token", " ".join(command))

    def write_database(self, mode=0o644):
        for suffix in ("", "-wal", "-shm"):
            path = self.config_dir / ("messages.sqlite" + suffix)
            path.write_bytes(b"")
            path.chmod(mode)

    def assert_private_database(self):
        for suffix in ("", "-wal", "-shm"):
            path = self.config_dir / ("messages.sqlite" + suffix)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600, path.name)

    def test_serve_daemon_makes_the_mailbox_private_and_execs_under_an_owner_only_umask(self):
        self.write_config()
        self.write_database()
        seen = {}

        def record_umask(*_args):
            seen["umask"] = os.umask(0o022)
            raise RuntimeError("exec called")

        previous = os.umask(0o022)
        self.addCleanup(os.umask, previous)
        with patch("collaboration_auth_header.read_private_token", return_value="test-only-token"), \
             patch("collaboration_runtime.os.execvpe", side_effect=record_umask):
            with self.assertRaisesRegex(RuntimeError, "exec called"):
                collaboration_runtime.serve_daemon(self.config_dir, "/opt/homebrew/bin/npx")
        self.assertEqual(seen["umask"], 0o077)
        self.assert_private_database()

    def test_start_daemon_makes_the_mailbox_private_and_spawns_under_an_owner_only_umask(self):
        self.write_config()
        self.write_database()
        process = MagicMock()
        process.poll.return_value = None
        with patch("collaboration_auth_header.read_private_token", return_value="test-only-token"), \
             patch("collaboration_runtime.health", return_value=False), \
             patch("collaboration_runtime.subprocess.Popen", return_value=process) as popen:
            collaboration_runtime.start_daemon(self.config_dir, health_attempts=0)
        self.assertEqual(popen.call_args.kwargs["umask"], 0o077)
        self.assert_private_database()

    def test_a_symlinked_mailbox_is_refused_rather_than_following_it(self):
        self.write_config()
        target = Path(self.tmp.name) / "elsewhere.sqlite"
        target.write_bytes(b"")
        target.chmod(0o644)
        (self.config_dir / "messages.sqlite").symlink_to(target)
        with patch("collaboration_runtime.subprocess.Popen") as popen:
            with self.assertRaisesRegex(RuntimeContractError, "regular file"):
                collaboration_runtime.start_daemon(self.config_dir)
        popen.assert_not_called()
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    def test_stale_daemon_pid_file_is_removed_only_after_its_process_is_confirmed_gone(self):
        self.write_config()
        pid_file = self.config_dir / "daemon.pid"
        pid_file.write_text(json.dumps({"pid": 1234, "port": 9100}), encoding="utf-8")
        with patch("collaboration_runtime.os.kill", side_effect=ProcessLookupError):
            collaboration_runtime.clear_stale_daemon_pid(self.config_dir)
        self.assertFalse(pid_file.exists())

    def test_service_enable_cli_is_explicit_and_reports_only_nonsecret_facts(self):
        self.write_config()
        output = io.StringIO()
        expected_path = Path(self.tmp.name) / "Library" / "LaunchAgents" / "com.specguard.collaboration.plist"
        with patch("collaboration_runtime.enable_background_service", return_value=expected_path):
            with redirect_stdout(output):
                self.assertEqual(main([
                    "service-enable", "--config-dir", str(self.config_dir),
                    "--launch-agents-dir", str(expected_path.parent),
                    "--runtime-script", "/opt/spec-guard/collaboration_runtime.py",
                    "--python-executable", "/usr/bin/python3", "--npx", "/opt/homebrew/bin/npx",
                    "--format", "json",
                ]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["state"], "service-enabled")
        self.assertEqual(payload["plist"], str(expected_path))
        self.assertNotIn("test-only-token", output.getvalue())

    def test_background_service_status_reports_not_enabled_without_launchctl(self):
        self.write_config()
        status = collaboration_runtime.background_service_status(
            self.config_dir, Path(self.tmp.name) / "Library" / "LaunchAgents",
        )
        self.assertEqual(status, {"state": "service-absent"})

    def test_disable_background_service_boots_out_and_deletes_only_a_managed_plist(self):
        self.write_config()
        launch_agents_dir = Path(self.tmp.name) / "Library" / "LaunchAgents"
        launch_agents_dir.mkdir(parents=True)
        plist_path = launch_agents_dir / "com.specguard.collaboration.plist"
        with plist_path.open("wb") as handle:
            plistlib.dump(collaboration_runtime.launch_agent_plist(
                self.config_dir, Path("/opt/spec-guard/collaboration_runtime.py"),
                "/usr/bin/python3", "/opt/homebrew/bin/npx",
            ), handle)
        with patch("collaboration_runtime.os.getuid", return_value=501), \
             patch("collaboration_runtime.subprocess.run") as run:
            collaboration_runtime.disable_background_service(self.config_dir, launch_agents_dir)
        self.assertFalse(plist_path.exists())
        run.assert_called_once_with(
            ["launchctl", "bootout", "gui/501", str(plist_path)],
            check=False, capture_output=True, text=True,
        )

    def test_explicit_registry_agent_removal_uses_only_a_uuid_target_and_never_prints_token(self):
        self.write_config()
        agent_id = "01234567-89ab-cdef-0123-456789abcdef"
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "deleted": True, "agent_id": agent_id, "name": "stale-test", "team": "spec-guard-local",
        }).encode("utf-8")
        with patch("collaboration_auth_header.read_private_token", return_value="test-only-token"), \
             patch("collaboration_runtime.urlopen", return_value=response) as opener:
            payload = collaboration_runtime.remove_registry_agent(self.config_dir, agent_id)
        request = opener.call_args.args[0]
        self.assertEqual(request.method, "DELETE")
        self.assertEqual(request.full_url, f"http://127.0.0.1:9100/api/agents/{agent_id}")
        self.assertEqual(payload, {
            "state": "agent-removed", "agentId": agent_id,
            "name": "stale-test", "team": "spec-guard-local",
        })
        self.assertNotIn("test-only-token", repr(payload))
        response.__enter__.return_value.read.return_value = json.dumps({
            "deleted": True, "agent_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        }).encode("utf-8")
        with patch("collaboration_auth_header.read_private_token", return_value="test-only-token"), \
             patch("collaboration_runtime.urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeContractError, "did not confirm"):
                collaboration_runtime.remove_registry_agent(self.config_dir, agent_id)
        with self.assertRaisesRegex(RuntimeContractError, "UUID"):
            collaboration_runtime.remove_registry_agent(self.config_dir, "not-an-agent")

    def test_remove_agent_cli_reports_only_confirmed_nonsecret_registry_facts(self):
        self.write_config()
        agent_id = "01234567-89ab-cdef-0123-456789abcdef"
        output = io.StringIO()
        with patch("collaboration_runtime.remove_registry_agent", return_value={
            "state": "agent-removed", "agentId": agent_id,
            "name": "stale-test", "team": "spec-guard-local",
        }):
            with redirect_stdout(output):
                self.assertEqual(main([
                    "remove-agent", "--config-dir", str(self.config_dir), "--agent-id", agent_id,
                    "--format", "json",
                ]), 0)
        self.assertEqual(json.loads(output.getvalue())["agentId"], agent_id)
        self.assertNotIn("test-only-token", output.getvalue())

    def test_codex_header_helper_reads_only_a_valid_private_token(self):
        self.write_config()
        self.assertEqual(
            authorization_header(self.config_dir),
            {"Authorization": "Bearer test-only-token"},
        )

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(auth_header_main(["--config-dir", str(self.config_dir)]), 0)
        self.assertEqual(
            json.loads(output.getvalue()),
            {"Authorization": "Bearer test-only-token"},
        )

        (self.config_dir / "token").write_text("bad\nvalue", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeContractError, "invalid bearer token"):
            authorization_header(self.config_dir)

    def test_host_fragments_are_non_secret_and_pin_the_runtime_package(self):
        self.write_config()
        config = read_runtime_config(self.config_dir)
        claude = claude_mcp_config(config, include_channel=True)
        http_server = claude["mcpServers"][MCP_SERVER_NAME]
        self.assertEqual(http_server["url"], "http://127.0.0.1:9100/mcp")
        self.assertEqual(http_server["headers"]["Authorization"],
                         "Bearer ${SPEC_GUARD_COLLABORATION_TOKEN}")
        channel = claude["mcpServers"][CHANNEL_SERVER_NAME]
        self.assertIn("cross-agent-teams-mcp@0.8.6", channel["args"])
        self.assertEqual(channel["env"]["CROSS_AGENT_TEAMS_MCP_TOKEN"],
                         "${SPEC_GUARD_COLLABORATION_TOKEN}")

        fragment = codex_toml_fragment(
            config, Path("/opt/spec-guard/collaboration_auth_header.py"), self.config_dir)
        self.assertIn(f"[mcp_servers.{MCP_SERVER_NAME.replace('-', '_')}]", fragment)
        self.assertIn("http_headers_helper", fragment)
        self.assertIn(str(self.config_dir), fragment)
        self.assertNotIn("test-only-token", fragment)
        self.assertNotIn("latest", json.dumps({"claude": claude, "codex": fragment}))
        self.assertEqual(TOKEN_ENV_VAR, "SPEC_GUARD_COLLABORATION_TOKEN")

    def test_claude_launcher_config_is_ephemeral_non_secret_and_cannot_be_overridden(self):
        self.write_config()
        generated = write_ephemeral_mcp_config(self.config_dir, include_channel=True)
        self.addCleanup(generated.unlink, missing_ok=True)
        contents = generated.read_text(encoding="utf-8")
        self.assertIn("SPEC_GUARD_COLLABORATION_TOKEN", contents)
        self.assertIn(CHANNEL_SERVER_NAME, contents)
        self.assertNotIn("test-only-token", contents)
        self.assertEqual(stat.S_IMODE(generated.stat().st_mode), 0o600)

        command = build_claude_command("claude", generated, True, ["--model", "sonnet"])
        self.assertEqual(command[:3], ["claude", "--mcp-config", str(generated)])
        self.assertIn("server:" + CHANNEL_SERVER_NAME, command)
        self.assertNotIn("test-only-token", " ".join(command))
        with self.assertRaisesRegex(ValueError, "MCP options"):
            build_claude_command("claude", generated, False, ["--mcp-config", "other.json"])

    def test_claude_launcher_rejects_equals_form_mcp_overrides(self):
        for option in (
            "--mcp-config=other.json",
            "--dangerously-load-development-channels=server:other",
        ):
            with self.subTest(option=option):
                with self.assertRaisesRegex(ValueError, "MCP options"):
                    build_claude_command("claude", Path("/tmp/selected.json"), True, [option])

    def test_claude_launcher_default_does_not_enable_channel(self):
        self.write_config()
        generated = write_ephemeral_mcp_config(self.config_dir, include_channel=False)
        self.addCleanup(generated.unlink, missing_ok=True)
        contents = generated.read_text(encoding="utf-8")
        self.assertNotIn(CHANNEL_SERVER_NAME, contents)
        self.assertNotIn("test-only-token", contents)
        command = build_claude_command("claude", generated, False, ["--model", "sonnet"])
        self.assertNotIn("--dangerously-load-development-channels", command)

    def test_claude_launcher_preserves_chrome_flag_with_optional_wake(self):
        for include_channel in (False, True):
            with self.subTest(include_channel=include_channel):
                command = build_claude_command(
                    "claude", Path("/tmp/collab.json"), include_channel,
                    ["--chrome", "--model", "sonnet"],
                )
                self.assertEqual(command[-3:], ["--chrome", "--model", "sonnet"])

    def test_tmux_launcher_uses_direct_arguments_and_unique_session_name(self):
        command = build_tmux_command(
            self.config_dir, "claude", ["--chrome", "--model", "sonnet", "a;b"],
            session_name="spec-guard-test1234",
        )
        self.assertEqual(command[:6], [
            "tmux", "new-session", "-s", "spec-guard-test1234", "-c", str(Path.cwd()),
        ])
        self.assertIn("--tmux-wake", command)
        self.assertEqual(command[-5:], ["--", "--chrome", "--model", "sonnet", "a;b"])
        self.assertNotIn("test-only-token", " ".join(command))
        self.assertNotIn("--dangerously-load-development-channels", command)

    def test_tmux_launcher_does_not_nest_inside_an_existing_pane(self):
        with patch.dict("collaboration_claude.os.environ", {"TMUX_PANE": "%1"}):
            with patch("collaboration_claude.launch_claude", return_value=7) as launch:
                with patch("collaboration_claude.subprocess.run") as run:
                    result = launch_tmux_claude(self.config_dir, "claude", ["--model", "sonnet"])
        self.assertEqual(result, 7)
        launch.assert_called_once_with(self.config_dir, "claude", False, ["--model", "sonnet"])
        run.assert_not_called()

    def test_tmux_launcher_refuses_missing_tmux_or_noninteractive_terminal(self):
        with patch.dict("collaboration_claude.os.environ", {}, clear=True):
            with patch("collaboration_claude.shutil.which", return_value=None):
                with self.assertRaisesRegex(ValueError, "tmux executable"):
                    launch_tmux_claude(self.config_dir, "claude", [])
            with patch("collaboration_claude.shutil.which", return_value="/opt/homebrew/bin/tmux"):
                with patch("collaboration_claude.sys.stdin.isatty", return_value=False):
                    with self.assertRaisesRegex(ValueError, "interactive terminal"):
                        launch_tmux_claude(self.config_dir, "claude", [])

    def test_tmux_launcher_starts_one_new_session_without_a_shell(self):
        with patch.dict("collaboration_claude.os.environ", {}, clear=True):
            with patch("collaboration_claude.shutil.which", return_value="/opt/homebrew/bin/tmux"):
                with patch("collaboration_claude.sys.stdin.isatty", return_value=True):
                    with patch("collaboration_claude.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                        self.assertEqual(launch_tmux_claude(self.config_dir, "claude", []), 0)
                        self.assertEqual(launch_tmux_claude(self.config_dir, "claude", []), 0)
        command = run.call_args_list[0].args[0]
        self.assertIsInstance(command, list)
        self.assertTrue(command[3].startswith("spec-guard-"))
        self.assertNotEqual(command[3], run.call_args_list[1].args[0][3])
        self.assertEqual(run.call_args.kwargs, {"check": False})

    def test_claude_stdio_bridge_uses_a_pinned_open_source_proxy_without_argv_token(self):
        self.write_config()
        with patch("collaboration_claude_stdio.read_private_token", return_value="test-only-token"):
            command, environment = mcp_remote_command(self.config_dir, "/bin/echo")
        self.assertEqual(command[:4], [
            "/bin/echo", "--yes", "--package", f"{MCP_REMOTE_PACKAGE}@{MCP_REMOTE_VERSION}",
        ])
        self.assertIn("mcp-remote", command)
        self.assertIn("http://127.0.0.1:9100/mcp", command)
        self.assertIn("http-only", command)
        self.assertIn(f"Authorization:${{{MCP_REMOTE_AUTH_ENV_VAR}}}", command)
        self.assertEqual(environment[MCP_REMOTE_AUTH_ENV_VAR], "Bearer test-only-token")
        self.assertNotIn("test-only-token", " ".join(command))

    def test_claude_user_configuration_is_installed_via_cli_without_a_token(self):
        self.write_config()
        helper = Path(self.tmp.name) / "collaboration_claude_stdio.py"
        helper.write_text("# helper\n", encoding="utf-8")
        with patch("host_config_removal.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(["claude", "mcp", "add"], 0)
            install_claude_config(
                helper, self.config_dir, "claude", "/usr/bin/python3", "/bin/echo",
            )
        self.assertEqual(run.call_count, 1)
        added = run.call_args_list[0].args[0]
        self.assertEqual(added[:7], [
            "claude", "mcp", "add", "--scope", "user", MCP_SERVER_NAME, "--",
        ])
        self.assertIn(str(helper.resolve()), added)
        self.assertIn(str(self.config_dir), added)
        self.assertEqual(added[-1], str(Path("/bin/echo").resolve()))
        self.assertNotIn("test-only-token", " ".join(added))

    def test_claude_user_configuration_refuses_to_replace_an_existing_server(self):
        self.write_config()
        helper = Path(self.tmp.name) / "collaboration_claude_stdio.py"
        helper.write_text("# helper\n", encoding="utf-8")
        with patch("host_config_removal.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess(
                ["claude", "mcp", "add"], 1, "",
                "MCP server spec-guard-collaboration already exists in user config")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                install_claude_config(
                    helper, self.config_dir, "claude", "/usr/bin/python3", "/bin/echo",
                )
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][:3], ["claude", "mcp", "add"])

    def test_codex_config_install_is_atomic_non_secret_and_refuses_overwrite(self):
        self.write_config()
        config = read_runtime_config(self.config_dir)
        codex_config = Path(self.tmp.name) / "codex" / "config.toml"
        codex_config.parent.mkdir(mode=0o700)
        codex_config.write_text("model = \"gpt\"\n", encoding="utf-8")
        codex_config.chmod(0o600)
        install_codex_config(
            config, Path("/opt/spec-guard/collaboration_auth_header.py"),
            self.config_dir, codex_config,
        )
        contents = codex_config.read_text(encoding="utf-8")
        self.assertIn("model = \"gpt\"", contents)
        self.assertIn("http_headers_helper", contents)
        self.assertNotIn("test-only-token", contents)
        self.assertEqual(stat.S_IMODE(codex_config.stat().st_mode), 0o600)
        with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
            install_codex_config(
                config, Path("/opt/spec-guard/collaboration_auth_header.py"),
                self.config_dir, codex_config,
            )


if __name__ == "__main__":
    unittest.main()
