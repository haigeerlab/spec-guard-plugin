#!/usr/bin/env python3
"""Exercise release checks and packaging without a network or real host state."""
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/release.py"
VERSION = "1.2.3"
GITHUB = "example/spec-guard"
CLAUDE = "plugins/spec-guard/.claude-plugin/plugin.json"
CODEX = "plugins/spec-guard/.codex-plugin/plugin.json"
NOTES = "\n### Fixed\n\n- Release fixture.\n\n"
EXIT_CODES = {"ok": 0, "preview": 0, "refused": 2, "waiting-on-user": 3, "failed": 1}


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sg-release-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.origin = self.root / "origin.git"
        self.state = self.root / "state"
        self.responses = self.root / "responses"
        self.responses.mkdir()
        self.log = self.root / "gh.log"
        self.command_log = self.root / "commands.log"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("home", "tmp", "config"):
            (self.root / name).mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("GIT_", "GH_", "SPEC_GUARD_"))}
        self.env.update({
            "HOME": str(self.root / "home"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "SPEC_GUARD_STATE_DIR": str(self.state),
            "TMPDIR": str(self.root / "tmp"),
            "GH_FIXTURES": str(self.responses),
            "GH_LOG": str(self.log),
            "RELEASE_COMMAND_LOG": str(self.command_log),
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "TZ": "UTC",
            "SMOKE_EXIT_CODE": "0",
            "SMOKE_OUTPUT": "fixture smoke passed\n",
            "SMOKE_STDERR": "",
            "PS_OUTPUT": "Sun Nov 22 04:46:46 2026 /Applications/ChatGPT.app/Contents/MacOS/ChatGPT\n",
            "PS_EXIT_CODE": "0",
            "CODEX_VERSION": "codex-cli 0.171.0\nsecond line\n",
            "CODEX_VERSION_EXIT_CODE": "0",
        })
        fake = self.bin / "gh"
        fake.write_text("#!" + sys.executable + "\n" + '''import json
import os
from pathlib import Path
import shutil
import sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\\n")
with open(os.environ["RELEASE_COMMAND_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(["gh", *args]) + "\\n")
root = Path(os.environ["GH_FIXTURES"])
if (root / "fail").exists():
    print("fixture gh failure", file=sys.stderr)
    sys.exit(1)
if args[:1] == ["api"] and args[1].startswith("repos/") and "/pulls/" in args[1]:
    name = "pulls.json"
elif args[:2] == ["run", "list"]:
    name = "runs.json"
elif args[:2] == ["release", "create"]:
    sys.exit(0)
elif args[:2] == ["release", "download"]:
    source = json.loads((root / "download.json").read_text())["asset"]
    shutil.copyfile(source, Path(args[args.index("-D") + 1]) / args[args.index("-p") + 1])
    sys.exit(0)
elif args == ["api", "repos/example/spec-guard/releases/latest"]:
    name = "latest.json"
else:
    print("unexpected gh operation", file=sys.stderr)
    sys.exit(91)
sys.stdout.write((root / name).read_text(encoding="utf-8"))
''', encoding="utf-8")
        fake.chmod(0o755)
        self.git("init", "--bare", "-q", str(self.origin))
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        self.git("remote", "add", "origin", str(self.origin))
        self.git("config", "remote.origin.tagOpt", "--no-tags")
        manifest = json.dumps({"name": "spec-guard", "version": VERSION}) + "\n"
        files = {
            ".claude-plugin/marketplace.json": json.dumps({"plugins": [
                {"name": "spec-guard", "source": "./plugins/spec-guard"}]}),
            CLAUDE: manifest,
            CODEX: manifest,
            "README.md": "install --ref v" + VERSION + "\n",
            "README.en.md": "install --ref v" + VERSION + "\n",
            "CHANGELOG.md": "# Changelog\n\n## [" + VERSION + "] - 2026-11-22\n" +
                            NOTES + "## [1.2.2]\n\nOld notes.\n",
            "unrelated.txt": "Must not be packaged.\n",
        }
        for relative, content in files.items():
            self.write(relative, content)
        (self.repo / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/release-package.py", self.repo / "scripts/release-package.py")
        shutil.copyfile(ROOT / "scripts/release-evidence.py", self.repo / "scripts/release-evidence.py")
        smoke_code = '''import json, os, sys
with open(os.environ["RELEASE_COMMAND_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(["smoke", *sys.argv[1:]]) + "\\n")
if sys.stdin.read() != "":
    print("smoke stdin was not empty", file=sys.stderr)
    sys.exit(91)
sys.stdout.write(os.environ["SMOKE_OUTPUT"])
sys.stderr.write(os.environ["SMOKE_STDERR"])
sys.exit(int(os.environ["SMOKE_EXIT_CODE"]))
'''
        self.write("evals/codex-plugin-smoke.sh",
                   "#!/bin/bash\nexec " + shlex.join([sys.executable, "-c", smoke_code]) + ' "$@"\n')
        fake_ps = self.bin / "ps"
        fake_ps.write_text("#!" + sys.executable + "\n" + '''import json, os, sys
with open(os.environ["RELEASE_COMMAND_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(["ps", *sys.argv[1:]]) + "\\n")
sys.stdout.write(os.environ["PS_OUTPUT"])
sys.exit(int(os.environ["PS_EXIT_CODE"]))
''', encoding="utf-8")
        fake_ps.chmod(0o755)
        self.commit()
        self.fixture("runs.json", [{"conclusion": "success", "databaseId": 44986116526,
                                    "event": "push", "status": "completed", "workflowName": "Validate"}])
        real_git = shutil.which("git")
        fake_git = self.bin / "git"
        fake_git.write_text("#!" + sys.executable + "\n" +
                            "import json, os, sys\n" +
                            "with open(os.environ['RELEASE_COMMAND_LOG'], 'a') as log:\n" +
                            "    log.write(json.dumps(['git', *sys.argv[1:]]) + '\\n')\n" +
                            "os.execv(" + repr(real_git) + ", ['git', *sys.argv[1:]])\n",
                            encoding="utf-8")
        fake_git.chmod(0o755)
        for name in ("claude", "codex"):
            fake_host = self.bin / name
            fake_host.write_text("#!" + sys.executable + "\n" + '''import json
import os
from pathlib import Path
import shutil
import sys
name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ["RELEASE_COMMAND_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps([name, *args]) + "\\n")
root = Path(os.environ["GH_FIXTURES"])
if name == "codex" and args == ["--version"]:
    sys.stdout.write(os.environ["CODEX_VERSION"])
    sys.exit(int(os.environ["CODEX_VERSION_EXIT_CODE"]))
settings = json.loads((root / "hosts.json").read_text())
if settings.get("fail") == [name, *args]:
    print("fixture host failure", file=sys.stderr)
    sys.exit(1)
if name == "claude" and args == ["plugin", "marketplace", "update", "spec-guard-marketplace"]:
    sys.exit(0)
if name == "claude" and args == ["plugin", "update", "spec-guard@spec-guard-marketplace"]:
    installed = settings["claude"]["plugins"]["spec-guard@spec-guard-marketplace"][0]
    destination = Path(installed["installPath"])
    shutil.copytree(settings["claudeTree"], destination, dirs_exist_ok=True)
    (destination / ".in_use").write_text("Claude marker")
    state = Path(settings["claudeHome"]) / "plugins/installed_plugins.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(settings["claude"]))
elif name == "codex" and args == ["plugin", "marketplace", "upgrade", "spec-guard-marketplace"]:
    destination = settings["codex"]["installed"][0]["source"]["path"]
    shutil.copytree(settings["codexTree"], destination, dirs_exist_ok=True)
elif name == "codex" and args == ["plugin", "list", "--json"]:
    print(json.dumps(settings["codex"]))
else:
    print("unexpected host operation", file=sys.stderr)
    sys.exit(91)
''', encoding="utf-8")
            fake_host.chmod(0o755)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo), *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def write(self, relative, content):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def fixture(self, name, value):
        (self.responses / name).write_text(json.dumps(value), encoding="utf-8")

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "fixture")
        self.git("push", "-q", "origin", "main")
        self.sha = self.git("rev-parse", "HEAD")
        self.fixture("pulls.json", {"merge_commit_sha": self.sha, "merged": True, "state": "closed"})

    def release(self, step, *options, global_options=None):
        command = [sys.executable, "-B", str(SCRIPT)]
        command += global_options if global_options is not None else [
            "--repo", str(self.repo), "--github", GITHUB]
        command += [step, *options]
        result = subprocess.run(command, cwd=self.root, env=self.env, capture_output=True,
                                text=True, timeout=60,
                                input="inherited smoke input must be ignored\n" if step == "smoke" else None)
        self.last_stdout = result.stdout
        lines = result.stdout.splitlines()
        self.assertGreaterEqual(len(lines), 2, result.stdout + result.stderr)
        payload = json.loads(lines[-1])
        self.assertEqual(payload["schema"], "spec-guard.release/v1")
        self.assertEqual(payload["step"], step)
        self.assertIn("version", payload)
        self.assertEqual(result.returncode, EXIT_CODES[payload["status"]], result.stdout + result.stderr)
        return payload

    def record_path(self):
        return self.state / "release" / (VERSION + ".json")

    def record(self):
        return json.loads(self.record_path().read_text(encoding="utf-8"))

    def check(self, **kwargs):
        return self.release("check", "--pr", "42", **kwargs)

    def refused(self, reason):
        payload = self.check()
        self.assertEqual(payload["status"], "refused")
        self.assertEqual(payload["reason"], reason)
        self.assertFalse(self.record_path().exists())

    def test_check_refuses_unmerged_pr(self):
        self.fixture("pulls.json", {"merged": False, "state": "open", "merge_commit_sha": self.sha})
        self.refused("not-merged")

    def test_check_refuses_moved_main(self):
        old = self.sha
        self.commit()
        self.fixture("pulls.json", {"merged": True, "merge_commit_sha": old})
        self.refused("main-moved")

    def test_check_refuses_empty_failing_or_pending_ci(self):
        for runs in ([], [{"status": "completed", "conclusion": "failure"}],
                     [{"status": "in_progress", "conclusion": None}],
                     [{"status": "completed", "conclusion": "success"},
                      {"status": "completed", "conclusion": "cancelled"}]):
            with self.subTest(runs=runs):
                self.fixture("runs.json", runs)
                self.refused("ci-not-green")

    def test_check_refuses_manifest_mismatch(self):
        self.write(CODEX, json.dumps({"name": "spec-guard", "version": "1.2.4"}))
        self.commit()
        self.refused("version-mismatch")

    def test_check_refuses_readme_mismatch_in_each_language(self):
        for readme in ("README.md", "README.en.md"):
            with self.subTest(readme=readme):
                self.write(readme, "install --ref v1.2.30\n")
                self.commit()
                self.refused("version-mismatch")
                self.write(readme, "install --ref v" + VERSION + "\n")

    def test_check_refuses_local_tag(self):
        self.git("tag", "v" + VERSION)
        self.refused("tag-exists")

    def test_check_refuses_remote_tag(self):
        self.git("tag", "v" + VERSION)
        self.git("push", "-q", "origin", "v" + VERSION)
        self.git("tag", "-d", "v" + VERSION)
        self.refused("tag-exists")

    def test_check_records_ok_and_preserves_other_steps(self):
        self.assertEqual(self.check()["status"], "ok")
        record = self.record()
        self.assertEqual(record["schema"], "spec-guard.release-record/v1")
        self.assertEqual(record["version"], VERSION)
        self.assertEqual(record["pr"], 42)
        self.assertEqual(record["github"], GITHUB)
        self.assertEqual(record["mergeCommit"], self.sha)
        self.assertEqual(record["steps"]["check"]["status"], "ok")
        self.assertRegex(record["steps"]["check"]["at"], r"^\d{4}-\d\d-\d\dT.*(?:Z|\+00:00)$")
        record["steps"]["prepare"] = {"status": "ok", "sentinel": True}
        self.record_path().write_text(json.dumps(record), encoding="utf-8")
        result = self.check()
        self.assertEqual(result["mergeCommit"], self.sha)
        self.assertEqual(self.record()["steps"]["prepare"], record["steps"]["prepare"])
        self.assertEqual(list(self.record_path().parent.iterdir()), [self.record_path()])

    def test_refused_check_does_not_change_existing_record(self):
        self.check()
        before = self.record_path().read_bytes()
        self.fixture("runs.json", [])
        self.assertEqual(self.check()["reason"], "ci-not-green")
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_options_can_follow_subcommand_and_select_remote(self):
        self.git("remote", "rename", "origin", "upstream")
        result = self.release("check", "--pr", "42", "--repo", str(self.repo),
                              "--remote", "upstream", "--github", GITHUB, global_options=[])
        self.assertEqual(result["status"], "ok")

    def test_check_derives_github_from_supported_remote_urls(self):
        for url in ("git@github.com:example/spec-guard.git", "https://github.com/example/spec-guard.git",
                    "https://github.com/example/spec-guard"):
            with self.subTest(url=url):
                self.git("remote", "set-url", "origin", url)
                self.fixture("pulls.json", {"merged": False})
                result = self.check(global_options=["--repo", str(self.repo)])
                self.assertEqual(result["reason"], "not-merged")
                calls = [json.loads(line) for line in self.log.read_text().splitlines()]
                self.assertEqual(calls[-1], ["api", "repos/" + GITHUB + "/pulls/42"])

    def test_check_command_failure_is_failed_json(self):
        (self.responses / "fail").touch()
        self.assertEqual(self.check()["status"], "failed")
        self.assertFalse(self.record_path().exists())

    def test_check_invalid_pull_response_is_failed_json(self):
        for pull in (None, [], {"merged": True, "merge_commit_sha": None}):
            with self.subTest(pull=pull):
                self.fixture("pulls.json", pull)
                self.assertEqual(self.check()["status"], "failed")
                self.assertFalse(self.record_path().exists())

    def test_prepare_requires_successful_check(self):
        for record in (None, {"steps": {}}, {"steps": None}, {"steps": []},
                       {"steps": {"check": None}}, {"steps": {"check": {"status": "refused"}}}):
            with self.subTest(record=record):
                if record is not None:
                    self.record_path().parent.mkdir(parents=True, exist_ok=True)
                    self.record_path().write_text(json.dumps(record), encoding="utf-8")
                result = self.release("prepare", "--version", VERSION)
                self.assertEqual(result["status"], "refused")
                self.assertEqual(result["reason"], "check-not-ok")
        self.assertFalse(self.log.exists())

    def test_prepare_packages_checked_commit_and_exact_notes(self):
        self.check()
        check = self.record()["steps"]["check"]
        self.write(CLAUDE, "dirty checkout must not be packaged")
        self.write("CHANGELOG.md", "dirty checkout must not be used")
        calls_before = self.log.read_bytes()
        result = self.release("prepare", "--version", VERSION)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["version"], VERSION)
        prepared = self.record()["steps"]["prepare"]
        self.assertEqual(prepared["status"], "ok")
        self.assertEqual(self.record()["steps"]["check"], check)
        directory = Path(prepared["dir"])
        self.assertTrue(directory.name.startswith("spec-guard-release-"))
        asset = Path(result["asset"])
        self.assertEqual(asset.parent, directory)
        self.assertEqual(asset.name, "spec-guard-v" + VERSION + ".tar.gz")
        self.assertEqual(prepared["asset"], str(asset))
        self.assertEqual(result["size"], asset.stat().st_size)
        self.assertEqual(result["sha256"], hashlib.sha256(asset.read_bytes()).hexdigest())
        self.assertEqual(prepared["sha256"], result["sha256"])
        self.assertEqual(prepared["size"], result["size"])
        self.assertEqual(Path(prepared["notes"]).read_text(encoding="utf-8"), NOTES)
        with tarfile.open(asset, "r:gz") as archive:
            names = archive.getnames()
            self.assertEqual(names, sorted(names))
            prefix = "spec-guard-v" + VERSION
            for name in names:
                self.assertFalse(any(part.startswith("._") for part in Path(name).parts), name)
                self.assertTrue(name == prefix or name == prefix + "/ARTIFACT-MANIFEST.json" or
                                name.startswith(prefix + "/.claude-plugin/") or
                                name == prefix + "/.claude-plugin" or
                                name.startswith(prefix + "/plugins/spec-guard/") or
                                name in (prefix + "/plugins", prefix + "/plugins/spec-guard"), name)
            manifest = json.load(archive.extractfile(prefix + "/ARTIFACT-MANIFEST.json"))
            self.assertEqual(manifest, {"schemaVersion": 1, "artifactKind": "spec-guard-plugin",
                                       "version": VERSION, "files": [
                                           ".claude-plugin/marketplace.json", CLAUDE, CODEX]})
            plugin = json.load(archive.extractfile(prefix + "/" + CLAUDE))
            self.assertEqual(plugin["version"], VERSION)
        self.assertEqual(self.log.read_bytes(), calls_before)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls[0], ["api", "repos/" + GITHUB + "/pulls/42"])
        self.assertEqual(calls[1][:2], ["run", "list"])
        self.assertIn(self.sha, calls[1])
        self.assertIn(GITHUB, calls[1])
        self.assertEqual(len(calls), 2)

    def test_prepare_fails_without_changelog_section(self):
        self.write("CHANGELOG.md", "# Changelog\n\n## [1.2.2]\nOld.\n")
        self.commit()
        self.check()
        self.assertEqual(self.release("prepare", "--version", VERSION)["status"], "failed")
        self.assertNotIn("prepare", self.record()["steps"])

    def test_prepare_fails_on_appledouble_members(self):
        self.write("plugins/spec-guard/._metadata", "not a release file")
        self.commit()
        self.check()
        self.assertEqual(self.release("prepare", "--version", VERSION)["status"], "failed")
        self.assertNotIn("prepare", self.record()["steps"])

    def prepare_publish(self):
        self.assertEqual(self.check()["status"], "ok")
        self.assertEqual(self.release("prepare", "--version", VERSION)["status"], "ok")
        self.fixture("download.json", {"asset": self.record()["steps"]["prepare"]["asset"]})
        self.url = "https://github.com/" + GITHUB + "/releases/tag/v" + VERSION
        self.fixture("latest.json", {"tag_name": "v" + VERSION, "html_url": self.url})
        self.command_log.write_bytes(b"")

    def publish(self, *options):
        return self.release("publish", "--version", VERSION, *options)

    def prepare_install(self):
        self.prepare_publish()
        self.assertEqual(self.publish("--confirm")["status"], "ok")
        self.claude_home = self.root / "claude home"
        self.codex_home = self.root / "codex home"
        self.codex_home.mkdir()
        self.config_path = self.codex_home / "config.toml"
        self.config = (b'# Preserve UTF-8: \xe6\xb5\x8b\xe8\xaf\x95\r\n'
                       b'[marketplaces.other]\r\nref = "keep-before"\r\n'
                       b'[marketplaces.spec-guard-marketplace]\r\n'
                       b'url = "https://github.com/example/spec-guard"\r\n'
                       b'ref = "v1.2.2"\r\n# keep this comment\r\n'
                       b'[features]\r\nref = "keep-after"')
        self.config_path.write_bytes(self.config)
        claude_tree = self.root / "claude-tree"
        codex_tree = self.root / "codex-tree"
        for tree in (claude_tree, codex_tree):
            shutil.copytree(self.repo / "plugins/spec-guard", tree)
        self.hosts = {
            "claudeHome": str(self.claude_home), "claudeTree": str(claude_tree),
            "codexTree": str(codex_tree),
            "claude": {"version": 2, "plugins": {"spec-guard@spec-guard-marketplace": [{
                "scope": "user", "installPath": str(self.claude_home / "plugins/cache/spec-guard"),
                "version": VERSION, "installedAt": "2026-11-21T00:00:00Z",
                "lastUpdated": "2026-11-22T04:45:35.546Z", "gitCommitSha": self.sha}]}},
            "codex": {"installed": [{"pluginId": "spec-guard@spec-guard-marketplace",
                "name": "spec-guard", "version": VERSION, "installed": True, "enabled": True,
                "source": {"source": "local", "path": str(self.codex_home / "snapshot/spec-guard")}}],
                "available": []},
        }
        self.fixture("hosts.json", self.hosts)
        self.command_log.write_bytes(b"")

    def install(self, *options):
        return self.release("install", "--version", VERSION, "--claude-home", str(self.claude_home),
                            "--codex-home", str(self.codex_home), *options)

    def calls(self):
        return [json.loads(line) for line in self.command_log.read_text().splitlines()]

    def backups(self):
        return list((self.state / "release/backups").glob("*"))

    def assert_utc(self, value):
        self.assertEqual(datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset(),
                         timezone.utc.utcoffset(None))

    def installed_record(self):
        at = "2026-11-22T04:45:41.123456+00:00"
        record = {"schema": "spec-guard.release-record/v1", "version": VERSION,
                  "pr": 42, "mergeCommit": self.sha, "github": GITHUB,
                  "steps": {
                      "check": {"status": "ok", "at": at},
                      "prepare": {"status": "ok", "at": at,
                          "asset": str(self.root / ("spec-guard-v" + VERSION + ".tar.gz")),
                          "sha256": "a" * 64, "size": 12345,
                          "dir": str(self.root / "package"), "notes": str(self.root / "notes.md")},
                      "publish": {"status": "ok", "tag": "v" + VERSION,
                          "url": "https://github.com/" + GITHUB + "/releases/tag/v" + VERSION,
                          "downloadSha256": "a" * 64, "at": at},
                      "install": {"status": "ok", "at": at,
                          "claude": {"version": VERSION, "commit": self.sha, "updatedAt": at,
                              "installPath": str(self.root / "claude plugin")},
                          "codex": {"version": VERSION, "source": str(self.root / "codex plugin"),
                              "refFrom": "v1.2.2", "refTo": "v" + VERSION,
                              "upgradedAt": at, "backup": None}}}}
        self.save_record(record)
        return record

    def save_record(self, record):
        self.record_path().parent.mkdir(parents=True, exist_ok=True)
        self.record_path().write_text(json.dumps(record), encoding="utf-8")

    def smoke(self, *options):
        return self.release("smoke", "--version", VERSION, *options)

    def evidence(self, *options):
        return self.release("evidence", "--version", VERSION, *options)

    def evidence_records(self, files):
        records = {}
        self.assertEqual(len(files), 4)
        for name, filename in zip(("source", "package", "claude", "codex"), files):
            path = Path(filename)
            self.assertEqual(path.name, "v" + VERSION + "-" + name + ".json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"schemaVersion", "release", "records"})
            self.assertEqual(data["schemaVersion"], 1)
            self.assertEqual(data["release"], {"version": VERSION})
            self.assertEqual(len(data["records"]), 1)
            observed = data["records"][0]
            if observed["status"] != "not-verified":
                self.assertEqual(set(observed), {"subject", "status", "target", "observedAt", "evidence"})
                self.assertRegex(observed["observedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            validation = subprocess.run([sys.executable, "-B", str(self.repo / "scripts/release-evidence.py"),
                                         "validate", str(path)], env=self.env, capture_output=True, text=True,
                                        timeout=30)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            records[name] = observed
        return records

    def test_smoke_success_records_host_facts_and_preserves_other_steps(self):
        before = self.installed_record()
        result = self.smoke()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["chatgpt"], {"state": "restarted", "startedAt": "2026-11-22T04:46:46Z"})
        smoke = self.record()["steps"]["smoke"]
        self.assertEqual(set(smoke), {"status", "exitCode", "codexCli", "chatgpt", "at"})
        self.assertEqual(smoke["status"], "ok")
        self.assertEqual(smoke["exitCode"], 0)
        self.assertEqual(smoke["codexCli"], "codex-cli 0.171.0")
        self.assertEqual(smoke["chatgpt"], result["chatgpt"])
        self.assert_utc(smoke["at"])
        self.assertEqual(self.calls(), [
            ["smoke", "--plugin-id", "spec-guard@spec-guard-marketplace", "--expected-source",
             before["steps"]["install"]["codex"]["source"]],
            ["codex", "--version"], ["ps", "-axo", "lstart=,command="]])
        after = self.record()
        del after["steps"]["smoke"]
        self.assertEqual(after, before)

    def test_smoke_hook_approval_failure_and_other_exit_codes(self):
        self.installed_record()
        for code, output, expected in ((2, "未观察到宿主 hook 事件", "waiting-on-user"),
                                       (2, "unrelated smoke failure", "failed"),
                                       (7, "未观察到宿主 hook 事件", "failed")):
            with self.subTest(code=code, output=output):
                self.env.update(SMOKE_EXIT_CODE=str(code), SMOKE_OUTPUT="", SMOKE_STDERR=output)
                result = self.smoke()
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["exitCode"], code)
                recorded = self.record()["steps"]["smoke"]
                self.assertEqual(recorded["status"], expected)
                self.assertEqual(recorded["exitCode"], code)
                if expected == "waiting-on-user":
                    self.assertIn("Codex 升级后 hook 的批准失效了：请在新开的终端里启动命令行 `codex`，"
                                  "在 `/hooks` 里批准 spec-guard 的 hook，然后重跑本命令", self.last_stdout)

    def test_smoke_failure_shows_last_five_output_lines(self):
        self.installed_record()
        self.env.update(SMOKE_EXIT_CODE="1", SMOKE_OUTPUT="omitted-one\nomitted-two\ntail-1\ntail-2\n",
                        SMOKE_STDERR="tail-3\ntail-4\ntail-5\n")
        self.assertEqual(self.smoke()["status"], "failed")
        self.assertNotIn("omitted-", self.last_stdout)
        self.assertIn("tail-1\ntail-2\ntail-3\ntail-4\ntail-5", self.last_stdout)

    def test_smoke_expected_source_override(self):
        self.installed_record()
        source = self.root / "expected source"
        self.assertEqual(self.smoke("--expected-source", str(source))["status"], "ok")
        self.assertEqual(self.calls()[0][-2:], ["--expected-source", str(source)])

    def test_smoke_chatgpt_restart_detection_and_local_timezone(self):
        self.installed_record()
        self.env["TZ"] = "Asia/Kuala_Lumpur"
        for started, state, utc in (("12:44:46", "not-restarted", "2026-11-22T04:44:46Z"),
                                    ("12:46:46", "restarted", "2026-11-22T04:46:46Z")):
            with self.subTest(state=state):
                self.env["PS_OUTPUT"] = ("Sun Nov 22 12:47:00 2026 /Applications/ChatGPT.app/Contents/MacOS/ChatGPT Helper\n"
                    "Sun Nov 22 " + started + " 2026 /Applications/ChatGPT.app/Contents/MacOS/ChatGPT\n")
                result = self.smoke()
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["chatgpt"], {"state": state, "startedAt": utc})
                if state == "not-restarted":
                    self.assertIn("⌘Q", self.last_stdout)
                    self.assertIn("ChatGPT", self.last_stdout)

    def test_smoke_chatgpt_unknown_and_codex_version_unavailable(self):
        self.installed_record()
        for output, exit_code in (("", "0"), ("unparseable /Applications/ChatGPT.app/Contents/MacOS/ChatGPT", "0"),
                                  (self.env["PS_OUTPUT"], "1"),
                                  ("Sun Nov 22 04:46:46 2026 /Applications/ChatGPT.app/Contents/MacOS/ChatGPT Helper", "0")):
            with self.subTest(output=output, exit_code=exit_code):
                self.env.update(PS_OUTPUT=output, PS_EXIT_CODE=exit_code, CODEX_VERSION_EXIT_CODE="1")
                result = self.smoke()
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["chatgpt"], {"state": "unknown", "startedAt": None})
                self.assertIsNone(self.record()["steps"]["smoke"]["codexCli"])

    def test_smoke_refuses_without_install(self):
        for record in ({}, {"steps": None}, {"steps": {"install": None}},
                       {"steps": {"install": {"status": "failed"}}}):
            with self.subTest(record=record):
                self.save_record(record)
                before = self.record_path().read_bytes()
                self.assertEqual(self.smoke()["reason"], "install-not-ok")
                self.assertEqual(self.record_path().read_bytes(), before)
        self.assertFalse(self.command_log.exists())

    def test_evidence_verified_files_match_release_facts_and_notes(self):
        self.installed_record()
        self.assertEqual(self.smoke()["status"], "ok")
        before = self.record()
        result = self.evidence("--note", "Task 3 verified.", "--note", "Second note.")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(all(Path(path).parent == self.repo.resolve() / "docs/releases" for path in result["files"]))
        records = self.evidence_records(result["files"])
        expected = {"source": ("spec-guard-source", "source-verified", "source-checkout", "commit:" + self.sha),
                    "package": ("spec-guard-release-artifact", "package-verified", "package",
                        "release:v" + VERSION + ";asset:spec-guard-v" + VERSION + ".tar.gz;sha256:" + "a" * 64),
                    "claude": ("spec-guard-claude", "host-verified", "host-session",
                        "claude-code;plugin:spec-guard@spec-guard-marketplace;sha:" + self.sha)}
        for name, (subject, status, kind, target) in expected.items():
            self.assertEqual(records[name]["subject"], subject)
            self.assertEqual(records[name]["status"], status)
            self.assertEqual(records[name]["target"], {"kind": kind, "id": target})
        source = records["source"]["evidence"]
        for text in ("v" + VERSION, self.sha, "#42", "merged", "main", "succeeded"):
            self.assertIn(text, source[0])
        self.assertEqual(source[1:], ["result:Task 3 verified.", "result:Second note."])
        package = records["package"]["evidence"]
        self.assertEqual(package[:3], ["release:" + before["steps"]["publish"]["url"],
            "asset:spec-guard-v" + VERSION + ".tar.gz;size:12345", "source-tag:v" + VERSION + "@" + self.sha])
        for line in package:
            self.assertNotIn(str(self.repo), line)
            for path in (str(self.root), tempfile.gettempdir(), self.env["TMPDIR"],
                         before["steps"]["prepare"]["dir"]):
                self.assertNotIn(path, line)
            self.assertNotRegex(line, r"/(?:private/)?(?:tmp|var/(?:tmp|folders))/")
        self.assertEqual([line for line in package if line.startswith("command:")], [
            "command:git archive --prefix=spec-guard-v" + VERSION + "/ v" + VERSION +
            " .claude-plugin plugins/spec-guard",
            "command:python3 scripts/release-package.py validate <dir> " + VERSION])
        for text in ("git archive", "release-package.py", " validate ", "._*", "SHA-256", "CHANGELOG", "latest"):
            self.assertIn(text, "\n".join(package))
        claude = records["claude"]["evidence"]
        self.assertEqual(claude[0], "command:claude plugin marketplace update spec-guard-marketplace && "
                         "claude plugin update spec-guard@spec-guard-marketplace")
        for text in (VERSION, self.sha, before["steps"]["install"]["claude"]["updatedAt"], ".in_use"):
            self.assertIn(text, claude[1])
        codex = records["codex"]
        self.assertEqual(codex["subject"], "spec-guard-codex")
        self.assertEqual(codex["status"], "host-verified")
        self.assertEqual(codex["target"]["kind"], "host-session")
        self.assertRegex(codex["target"]["id"], r"^codex-cli;test:v1\.2\.3-upgrade-\d{8}$")
        self.assertEqual(len(codex["evidence"]), 4)
        for text in ("codex-plugin-smoke.sh", "--expected-source", "v1.2.2", "v" + VERSION,
                     "codex-cli 0.171.0", "exited 0", "2026-11-22T04:46:46Z", "restarted",
                     "enabled", before["steps"]["install"]["codex"]["upgradedAt"]):
            self.assertIn(text, "\n".join(codex["evidence"]))
        written = self.record()["steps"]["evidence"]
        self.assertEqual(written["status"], "ok")
        self.assertEqual(written["files"], result["files"])
        self.assert_utc(written["at"])
        after = self.record()
        del after["steps"]["evidence"]
        self.assertEqual(after, before)

    def test_evidence_unverified_codex_for_missing_waiting_or_failed_smoke(self):
        for state in (None, "waiting-on-user", "failed"):
            with self.subTest(state=state):
                self.installed_record()
                if state:
                    self.env.update(SMOKE_EXIT_CODE="2" if state == "waiting-on-user" else "1",
                                    SMOKE_OUTPUT="未观察到宿主 hook 事件" if state == "waiting-on-user" else "failed smoke")
                    self.assertEqual(self.smoke()["status"], state)
                output = self.root / "release evidence"
                result = self.evidence("--output-dir", str(output))
                self.assertEqual(result["status"], "ok")
                self.assertTrue(all(Path(path).parent == output for path in result["files"]))
                codex = self.evidence_records(result["files"])["codex"]
                self.assertEqual(set(codex), {"subject", "status", "target", "reason"})
                self.assertEqual(codex["status"], "not-verified")
                for text in ("installed", "v1.2.2", "v" + VERSION, "release asset",
                             self.record()["steps"]["install"]["codex"]["upgradedAt"]):
                    self.assertIn(text, codex["reason"])
                self.assertIn({None: "not run", "waiting-on-user": "hooks", "failed": "exit"}[state], codex["reason"])

    def test_evidence_reports_unknown_or_not_restarted_chatgpt_honestly(self):
        self.installed_record()
        for output, expected in (("", "not verified"),
                ("Sun Nov 22 04:44:46 2026 /Applications/ChatGPT.app/Contents/MacOS/ChatGPT", "not restarted")):
            with self.subTest(output=output):
                self.env["PS_OUTPUT"] = output
                self.assertEqual(self.smoke()["status"], "ok")
                result = self.evidence()
                codex = self.evidence_records(result["files"])["codex"]
                self.assertEqual(codex["status"], "host-verified")
                self.assertIn(expected, codex["evidence"][-1])

    def test_evidence_refuses_without_each_prerequisite(self):
        for step in ("check", "prepare", "publish", "install"):
            for facts in (None, {"status": "failed"}):
                with self.subTest(step=step, facts=facts):
                    record = self.installed_record()
                    if facts is None:
                        del record["steps"][step]
                    else:
                        record["steps"][step] = facts
                    self.save_record(record)
                    before = self.record_path().read_bytes()
                    result = self.evidence()
                    self.assertEqual(result["status"], "refused")
                    self.assertEqual(result["reason"], step + "-not-ok")
                    self.assertEqual(self.record_path().read_bytes(), before)
                    self.assertFalse((self.repo / "docs/releases").exists())

    def test_evidence_validation_failure_reports_file_and_output(self):
        self.installed_record()
        validator = self.repo / "scripts/release-evidence.py"
        original = validator.read_text(encoding="utf-8")
        names = ("source", "package", "claude", "codex")
        for name in names:
            with self.subTest(name=name):
                filename = "v" + VERSION + "-" + name + ".json"
                validator.write_text("import sys\n" +
                    "if sys.argv[0] and sys.argv[-1].endswith(" + repr(filename) + "):\n" +
                    "    print('fixture evidence rejected', file=sys.stderr)\n" +
                    "    raise SystemExit(1)\n" + original, encoding="utf-8")
                before = self.record_path().read_bytes()
                result = self.evidence()
                self.assertEqual(result["status"], "failed")
                self.assertIn(filename, self.last_stdout)
                self.assertIn("fixture evidence rejected", self.last_stdout)
                self.assertEqual(self.record_path().read_bytes(), before)

    def test_publish_preview_has_no_commands_or_record_writes(self):
        self.prepare_publish()
        before = self.record_path().read_bytes()
        temporary = set((self.root / "tmp").iterdir())
        self.assertEqual(self.publish()["status"], "preview")
        for text in ("tag -a v" + VERSION, "push origin v" + VERSION, "release create",
                     "release download", "releases/latest", self.sha):
            self.assertIn(text, self.last_stdout)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertNotIn("publish", self.record()["steps"])
        self.assertEqual(set((self.root / "tmp").iterdir()), temporary)

    def test_publish_confirm_runs_in_order_and_records_only_publish(self):
        self.prepare_publish()
        before = self.record()
        temporary = set((self.root / "tmp").iterdir())
        result = self.publish("--confirm")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["tag"], "v" + VERSION)
        self.assertEqual(result["url"], self.url)
        calls = self.calls()
        tag = "v" + VERSION
        self.assertEqual(calls[:3], [
            ["git", "-C", str(self.repo.resolve()), "tag", "-a", tag, self.sha, "-m", tag],
            ["git", "-C", str(self.repo.resolve()), "push", "origin", tag],
            ["gh", "release", "create", tag, "--repo", GITHUB, "--verify-tag", "--title", tag,
             "--notes-file", before["steps"]["prepare"]["notes"], before["steps"]["prepare"]["asset"]]])
        self.assertEqual(calls[3][:-1], ["gh", "release", "download", tag, "--repo", GITHUB,
                                       "-p", "spec-guard-v" + VERSION + ".tar.gz", "-D"])
        self.assertTrue(Path(calls[3][-1]).name.startswith("spec-guard-release-"))
        self.assertEqual(calls[4:], [["gh", "api", "repos/" + GITHUB + "/releases/latest"]])
        published = self.record()["steps"]["publish"]
        self.assertEqual(published["status"], "ok")
        self.assertEqual(published["tag"], tag)
        self.assertEqual(published["url"], self.url)
        self.assertEqual(published["downloadSha256"], before["steps"]["prepare"]["sha256"])
        self.assert_utc(published["at"])
        after = self.record()
        del after["steps"]["publish"]
        self.assertEqual(after, before)
        self.assertEqual(set((self.root / "tmp").iterdir()), temporary)

    def test_publish_refuses_without_prepare_or_with_changed_asset(self):
        for record in ({}, {"steps": None}, {"steps": {"prepare": None}},
                       {"steps": {"prepare": {"status": "failed"}}}):
            self.record_path().parent.mkdir(parents=True, exist_ok=True)
            self.record_path().write_text(json.dumps(record))
            for options in ((), ("--confirm",)):
                with self.subTest(record=record, options=options):
                    self.assertEqual(self.publish(*options)["reason"], "prepare-not-ok")
        self.prepare_publish()
        asset = Path(self.record()["steps"]["prepare"]["asset"])
        for content in (b"changed asset", None):
            if content is None:
                asset.unlink()
            else:
                asset.write_bytes(content)
            before = self.record_path().read_bytes()
            for options in ((), ("--confirm",)):
                self.assertEqual(self.publish(*options)["reason"], "asset-changed")
            self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(self.calls(), [])

    def test_publish_fails_if_download_hash_differs(self):
        self.prepare_publish()
        changed = self.root / "wrong-asset"
        changed.write_bytes(b"wrong download")
        self.fixture("download.json", {"asset": str(changed)})
        before = self.record_path().read_bytes()
        temporary = set((self.root / "tmp").iterdir())
        self.assertEqual(self.publish("--confirm")["status"], "failed")
        self.assertIn(self.record()["steps"]["prepare"]["sha256"], self.last_stdout)
        self.assertIn(hashlib.sha256(changed.read_bytes()).hexdigest(), self.last_stdout)
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(len(self.calls()), 4)
        self.assertEqual(set((self.root / "tmp").iterdir()), temporary)

    def test_publish_refuses_incomplete_asset_facts(self):
        self.prepare_publish()
        record = self.record()
        prepared = record["steps"]["prepare"].copy()
        for field in ("asset", "sha256"):
            with self.subTest(field=field):
                record["steps"]["prepare"] = {key: value for key, value in prepared.items() if key != field}
                self.record_path().write_text(json.dumps(record))
                before = self.record_path().read_bytes()
                self.assertEqual(self.publish("--confirm")["reason"], "asset-changed")
                self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(self.calls(), [])

    def test_publish_fails_if_latest_is_another_version(self):
        self.prepare_publish()
        self.fixture("latest.json", {"tag_name": "v1.2.2", "html_url": self.url})
        before = self.record_path().read_bytes()
        self.assertEqual(self.publish("--confirm")["status"], "failed")
        self.assertIn("v1.2.2", self.last_stdout)
        self.assertIn("v" + VERSION, self.last_stdout)
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_install_preview_has_no_host_or_config_or_record_writes(self):
        self.prepare_install()
        before = self.record_path().read_bytes()
        temporary = set((self.root / "tmp").iterdir())
        self.assertEqual(self.install()["status"], "preview")
        for text in ("claude plugin marketplace update spec-guard-marketplace",
                     "claude plugin update spec-guard@spec-guard-marketplace",
                     "codex plugin marketplace upgrade spec-guard-marketplace", "v1.2.2",
                     "v" + VERSION, "backups", "config.toml." + VERSION):
            self.assertIn(text, self.last_stdout)
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.config_path.read_bytes(), self.config)
        self.assertEqual(self.backups(), [])
        self.assertFalse(self.claude_home.exists())
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertNotIn("install", self.record()["steps"])
        self.assertEqual(set((self.root / "tmp").iterdir()), temporary)

    def test_install_confirm_checks_hosts_and_records_only_install(self):
        self.prepare_install()
        before = self.record()
        temporary = set((self.root / "tmp").iterdir())
        started = datetime.now(timezone.utc)
        result = self.install("--confirm")
        finished = datetime.now(timezone.utc)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(self.calls(), [
            ["claude", "plugin", "marketplace", "update", "spec-guard-marketplace"],
            ["claude", "plugin", "update", "spec-guard@spec-guard-marketplace"],
            ["codex", "plugin", "marketplace", "upgrade", "spec-guard-marketplace"],
            ["codex", "plugin", "list", "--json"]])
        expected = self.config.replace(b'ref = "v1.2.2"', b'ref = "v1.2.3"')
        self.assertEqual(self.config_path.read_bytes(), expected)
        backups = self.backups()
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].name.startswith("config.toml." + VERSION + "."))
        self.assertEqual(backups[0].read_bytes(), self.config)
        installed = self.record()["steps"]["install"]
        claude = self.hosts["claude"]["plugins"]["spec-guard@spec-guard-marketplace"][0]
        self.assertEqual(installed["status"], "ok")
        self.assertEqual(installed["claude"], {"version": VERSION, "commit": self.sha,
            "updatedAt": claude["lastUpdated"], "installPath": claude["installPath"]})
        self.assertEqual(result["claude"]["updatedAt"], claude["lastUpdated"])
        codex = installed["codex"]
        self.assertEqual(codex["version"], VERSION)
        self.assertEqual(codex["source"], self.hosts["codex"]["installed"][0]["source"]["path"])
        self.assertEqual(codex["backup"], str(backups[0]))
        self.assertEqual(codex["refFrom"], "v1.2.2")
        self.assertEqual(codex["refTo"], "v" + VERSION)
        self.assertEqual(result["codex"]["upgradedAt"], codex["upgradedAt"])
        self.assert_utc(codex["upgradedAt"])
        self.assertLessEqual(started, datetime.fromisoformat(codex["upgradedAt"]))
        self.assertLessEqual(datetime.fromisoformat(codex["upgradedAt"]), finished)
        self.assert_utc(installed["at"])
        after = self.record()
        del after["steps"]["install"]
        self.assertEqual(after, before)
        self.assertEqual(set((self.root / "tmp").iterdir()), temporary)

    def test_install_refuses_without_successful_publish(self):
        for record in ({}, {"steps": None}, {"steps": {"publish": None}},
                       {"steps": {"publish": {"status": "failed"}}}):
            self.record_path().parent.mkdir(parents=True, exist_ok=True)
            self.record_path().write_text(json.dumps(record))
            for options in ((), ("--confirm",)):
                self.assertEqual(self.release("install", "--version", VERSION,
                    "--claude-home", str(self.root / "claude"), "--codex-home", str(self.root / "codex"),
                    *options)["reason"], "publish-not-ok")
        self.assertFalse(self.command_log.exists())

    def test_install_refuses_invalid_codex_config_without_changing_bytes(self):
        self.prepare_install()
        for config in (b'[marketplaces.other]\nref = "v1.2.2"\n',
                       b'[marketplaces.spec-guard-marketplace]\nurl = "keep"\n[other]\nref = "x"\n',
                       b'[marketplaces.spec-guard-marketplace]\nref = "a"\nref = "b"\n'):
            for options in ((), ("--confirm",)):
                with self.subTest(config=config, options=options):
                    self.config_path.write_bytes(config)
                    before = self.record_path().read_bytes()
                    self.assertEqual(self.install(*options)["reason"], "codex-config-ref")
                    self.assertEqual(self.config_path.read_bytes(), config)
                    self.assertEqual(self.backups(), [])
                    self.assertEqual(self.record_path().read_bytes(), before)

    def test_install_target_ref_is_unchanged_without_backup(self):
        self.prepare_install()
        config = self.config.replace(b'v1.2.2', b'v1.2.3')
        self.config_path.write_bytes(config)
        self.assertEqual(self.install()["status"], "preview")
        self.assertEqual(self.calls(), [])
        self.assertEqual(self.install("--confirm")["status"], "ok")
        self.assertEqual(self.config_path.read_bytes(), config)
        self.assertEqual(self.backups(), [])
        installed = self.record()["steps"]["install"]["codex"]
        self.assertIsNone(installed["backup"])
        self.assertEqual(installed["refFrom"], "v" + VERSION)
        self.assertEqual(installed["refTo"], "v" + VERSION)

    def test_install_fails_for_host_metadata_mismatches(self):
        self.prepare_install()
        claude = self.hosts["claude"]["plugins"]["spec-guard@spec-guard-marketplace"][0]
        codex = self.hosts["codex"]["installed"][0]
        for entry, field, wrong, detail in ((claude, "version", "1.2.2", "version"),
                (claude, "gitCommitSha", "a" * 40, "gitCommitSha"),
                (codex, "version", "1.2.2", "version"), (codex, "enabled", False, "enabled")):
            with self.subTest(field=field, detail=detail):
                original = entry[field]
                entry[field] = wrong
                self.fixture("hosts.json", self.hosts)
                before = self.record_path().read_bytes()
                self.assertEqual(self.install("--confirm")["status"], "failed")
                self.assertIn(detail, self.last_stdout)
                self.assertEqual(self.record_path().read_bytes(), before)
                entry[field] = original

    def test_install_fails_for_missing_different_or_extra_files_on_each_host(self):
        self.prepare_install()
        for host in ("claude", "codex"):
            tree = Path(self.hosts[host + "Tree"])
            path = tree / ".codex-plugin/plugin.json"
            original = path.read_bytes()
            for defect in ("missing", "different", "extra"):
                with self.subTest(host=host, defect=defect):
                    path.write_bytes(original)
                    if defect == "missing":
                        path.unlink()
                    elif defect == "different":
                        path.write_bytes(b"different contents")
                    else:
                        (tree / ".in_use").write_bytes(b"unexpected Codex marker")
                        if host == "claude":
                            (tree / "extra.txt").write_bytes(b"extra")
                    claude = self.hosts["claude"]["plugins"]["spec-guard@spec-guard-marketplace"][0]
                    for destination in (Path(claude["installPath"]),
                                        Path(self.hosts["codex"]["installed"][0]["source"]["path"])):
                        if destination.exists():
                            shutil.rmtree(destination)
                    before = self.record_path().read_bytes()
                    self.assertEqual(self.install("--confirm")["status"], "failed")
                    self.assertIn("Claude" if host == "claude" else "Codex", self.last_stdout)
                    self.assertIn("plugin.json" if defect != "extra" else
                                  ("extra.txt" if host == "claude" else ".in_use"), self.last_stdout)
                    self.assertEqual(self.record_path().read_bytes(), before)
                    path.write_bytes(original)
                    for extra in (tree / ".in_use", tree / "extra.txt"):
                        if extra.exists():
                            extra.unlink()

    def test_prepare_validates_before_and_after_packaging(self):
        validator = self.repo / "scripts/release-package.py"
        original = validator.read_text(encoding="utf-8")
        validation_log = self.root / "validation.log"
        for fail_at in (1, 2, 0):
            with self.subTest(fail_at=fail_at):
                if validation_log.exists():
                    validation_log.unlink()
                validator.write_text(
                    "from pathlib import Path\n" +
                    "log = Path(" + repr(str(validation_log)) + ")\n" +
                    "calls = log.read_text().splitlines() if log.exists() else []\n" +
                    "calls.append(__import__('sys').argv[2])\n" +
                    "log.write_text('\\n'.join(calls) + '\\n')\n" +
                    "if len(calls) == " + str(fail_at) + ":\n    raise SystemExit(1)\n" + original,
                    encoding="utf-8")
                self.check()
                result = self.release("prepare", "--version", VERSION)
                self.assertEqual(result["status"], "failed" if fail_at else "ok")
                paths = validation_log.read_text().splitlines()
                self.assertEqual(len(paths), fail_at or 2)
                if len(paths) == 2:
                    self.assertNotEqual(paths[0], paths[1])


if __name__ == "__main__":
    unittest.main()
