"""Project default tracker backend: parsing and resolution. No network, no real project."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tracker_default import as_json, normalize_target, read_default, render, resolve


GITHUB = {"host": "github.com", "repo": "team/repo"}
GITLAB = {"host": "gitlab.example.com", "projectId": 17}
LOCAL = {"projectId": "01M38JFCSPPKPQ3CJ2VY0ZP1XM"}


class ProjectDir:
    """A temporary project root, optionally carrying .agent/tracker.json."""

    def __init__(self, payload=None, raw=None):
        self.payload, self.raw = payload, raw

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / ".agent").mkdir()
        if self.raw is not None:
            (root / ".agent" / "tracker.json").write_text(self.raw, encoding="utf-8")
        elif self.payload is not None:
            (root / ".agent" / "tracker.json").write_text(
                json.dumps(self.payload), encoding="utf-8")
        return root

    def __exit__(self, *exc):
        self.tmp.cleanup()
        return False


def document(backend, target):
    return {"version": 1, "defaultBackend": backend, "defaultTarget": target}


class ReadDefaultTests(unittest.TestCase):
    def read(self, payload=None, raw=None):
        with ProjectDir(payload, raw) as root:
            return read_default(root)

    # ── positive: one per backend ──────────────────────────────────────────
    def test_github_default_is_configured(self):
        result = self.read(document("github", GITHUB))
        self.assertEqual(result.state, "configured")
        self.assertEqual(result.backend, "github")
        self.assertEqual(result.target, GITHUB)

    def test_gitlab_default_keeps_numeric_project_id(self):
        result = self.read(document("gitlab", GITLAB))
        self.assertEqual(result.state, "configured")
        self.assertEqual(result.target["projectId"], 17)
        self.assertIsInstance(result.target["projectId"], int)

    def test_local_default_needs_only_project_id(self):
        result = self.read(document("local", LOCAL))
        self.assertEqual(result.state, "configured")
        self.assertEqual(result.target, LOCAL)

    # ── absent is not an error ─────────────────────────────────────────────
    def test_missing_file_is_absent_not_invalid(self):
        result = self.read()
        self.assertEqual(result.state, "absent")
        self.assertIsNone(result.diagnostic)

    def test_missing_agent_directory_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_default(Path(tmp)).state, "absent")

    # ── invalid must never degrade to absent ───────────────────────────────
    def assert_invalid(self, payload=None, raw=None):
        result = self.read(payload, raw)
        self.assertEqual(result.state, "invalid")
        self.assertEqual(result.diagnostic, "tracker-default-invalid")
        return result

    def test_unparsable_json_is_invalid(self):
        self.assert_invalid(raw="{not json")

    def test_non_object_document_is_invalid(self):
        self.assert_invalid(raw="[]")

    def test_unknown_version_is_invalid(self):
        self.assert_invalid({"version": 2, "defaultBackend": "github",
                             "defaultTarget": GITHUB})

    def test_unknown_backend_is_invalid(self):
        self.assert_invalid(document("none", GITHUB))
        self.assert_invalid(document("bitbucket", GITHUB))

    def test_extra_top_level_key_is_invalid(self):
        payload = document("github", GITHUB)
        payload["activeModule"] = "alpha"
        self.assert_invalid(payload)

    def test_github_target_must_carry_host_and_owner_slash_name(self):
        self.assert_invalid(document("github", {"host": "github.com"}))
        self.assert_invalid(document("github", {"host": "github.com", "repo": "repo"}))
        self.assert_invalid(document("github", {"host": "github.com", "repo": "a/b/c"}))
        self.assert_invalid(document("github", {"host": "", "repo": "team/repo"}))
        self.assert_invalid(document("github", {"host": "github.com", "repo": "team/.."}))

    def test_gitlab_project_id_must_be_a_positive_integer(self):
        self.assert_invalid(document("gitlab", {"host": "gitlab.example.com",
                                                "projectId": "17"}))
        self.assert_invalid(document("gitlab", {"host": "gitlab.example.com",
                                                "projectId": 0}))
        self.assert_invalid(document("gitlab", {"host": "gitlab.example.com",
                                                "projectId": -1}))
        self.assert_invalid(document("gitlab", {"projectId": 17}))

    def test_local_target_must_carry_a_well_formed_project_id(self):
        self.assert_invalid(document("local", {}))
        self.assert_invalid(document("local", {"projectId": ""}))
        self.assert_invalid(document("local", {"projectId": "has space"}))
        self.assert_invalid(document("local", {"projectId": "x" * 65}))

    def test_extra_target_key_is_invalid(self):
        self.assert_invalid(document("github", {**GITHUB, "visibility": "private"}))
        self.assert_invalid(document("local", {**LOCAL, "host": "github.com"}))

    def test_wrong_target_shape_for_backend_is_invalid(self):
        self.assert_invalid(document("github", GITLAB))
        self.assert_invalid(document("local", GITHUB))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root bypasses the permission bit")
    def test_unreadable_file_is_invalid_not_absent(self):
        with ProjectDir(document("github", GITHUB)) as root:
            path = root / ".agent" / "tracker.json"
            os.chmod(path, 0o000)
            try:
                result = read_default(root)
            finally:
                os.chmod(path, 0o600)
        self.assertEqual(result.state, "invalid")

    # ── safe JSON ──────────────────────────────────────────────────────────
    def test_as_json_omits_paths_and_raw_errors(self):
        with ProjectDir(raw="{not json") as root:
            payload = as_json(read_default(root))
            self.assertEqual(payload, {"state": "invalid",
                                       "diagnostic": "tracker-default-invalid"})
            serialized = json.dumps(payload)
            self.assertNotIn(str(root), serialized)
            self.assertNotIn("Expecting", serialized)

    def test_as_json_of_configured_names_backend_and_target(self):
        with ProjectDir(document("github", GITHUB)) as root:
            self.assertEqual(as_json(read_default(root)),
                             {"state": "configured", "backend": "github",
                              "target": GITHUB})


class ResolveTests(unittest.TestCase):
    """Spec T6: the default only pre-fills; it never decides."""

    def setUp(self):
        with ProjectDir(document("github", GITHUB)) as root:
            self.configured = read_default(root)
        with ProjectDir() as root:
            self.absent = read_default(root)
        with ProjectDir(raw="{not json") as root:
            self.invalid = read_default(root)

    def test_explicit_both_is_resolved_from_explicit(self):
        result = resolve("local", LOCAL, self.configured)
        self.assertEqual(result.state, "resolved")
        self.assertEqual(result.source, "explicit")
        self.assertEqual(result.backend, "local")
        self.assertEqual(result.target, LOCAL)

    def test_explicit_differing_from_default_is_not_a_conflict(self):
        result = resolve("gitlab", GITLAB, self.configured)
        self.assertEqual(result.state, "resolved")
        self.assertEqual(result.source, "explicit")

    def test_neither_explicit_uses_project_default(self):
        result = resolve(None, None, self.configured)
        self.assertEqual(result.state, "resolved")
        self.assertEqual(result.source, "project-default")
        self.assertEqual(result.target, GITHUB)

    def test_neither_explicit_without_default_is_unselected(self):
        result = resolve(None, None, self.absent)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "tracker-default-absent")

    def test_invalid_default_never_silently_falls_back(self):
        result = resolve(None, None, self.invalid)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "tracker-default-invalid")

    def test_backend_only_matching_default_borrows_its_target(self):
        result = resolve("github", None, self.configured)
        self.assertEqual(result.state, "resolved")
        self.assertEqual(result.source, "project-default-target")
        self.assertEqual(result.target, GITHUB)

    def test_backend_only_differing_from_default_is_unselected(self):
        result = resolve("gitlab", None, self.configured)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "tracker-default-backend-differs")

    def test_backend_only_without_default_is_unselected(self):
        result = resolve("github", None, self.absent)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "tracker-default-absent")

    def test_target_without_backend_is_unselected(self):
        result = resolve(None, GITHUB, self.configured)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "backend-unselected")

    def test_explicit_target_of_wrong_shape_is_rejected(self):
        result = resolve("github", {"host": "github.com"}, self.configured)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "explicit-target-invalid")

    def test_unknown_explicit_backend_is_rejected(self):
        result = resolve("bitbucket", GITHUB, self.configured)
        self.assertEqual(result.state, "target-unselected")
        self.assertEqual(result.diagnostic, "explicit-target-invalid")

    def test_resolution_as_json_is_safe_and_names_its_source(self):
        payload = as_json(resolve(None, None, self.configured))
        self.assertEqual(payload, {"state": "resolved", "backend": "github",
                                   "target": GITHUB, "source": "project-default"})


class EntryTests(unittest.TestCase):
    """Spec T7: `show` is read-only and only `--confirm` writes, and only one file."""

    HOOKS = Path(__file__).resolve().parent

    def run_cli(self, root, *arguments):
        return subprocess.run(
            [sys.executable, "-B", "tracker_default.py", *arguments,
             "--project", str(root)],
            cwd=str(self.HOOKS), capture_output=True, text=True, timeout=30)

    def state_file(self, root):
        path = root / ".agent" / "state.json"
        path.write_text('{"activeModule":"alpha"}\n', encoding="utf-8")
        return path

    def test_show_reports_the_configured_default_as_json(self):
        with ProjectDir(document("gitlab", GITLAB)) as root:
            done = self.run_cli(root, "show")
            self.assertEqual(done.returncode, 0)
            self.assertEqual(json.loads(done.stdout),
                             {"state": "configured", "backend": "gitlab",
                              "target": GITLAB})

    def test_show_reports_absent_without_failing(self):
        with ProjectDir() as root:
            done = self.run_cli(root, "show")
            self.assertEqual(done.returncode, 0)
            self.assertEqual(json.loads(done.stdout), {"state": "absent"})

    def test_set_without_confirm_writes_nothing(self):
        with ProjectDir(document("github", GITHUB)) as root:
            path = root / ".agent" / "tracker.json"
            before, stamp = path.read_text(encoding="utf-8"), path.stat().st_mtime_ns
            done = self.run_cli(root, "set", "--backend", "local",
                                "--project-id", LOCAL["projectId"])
            self.assertEqual(done.returncode, 0)
            self.assertIn("preview only", done.stdout)
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            self.assertEqual(path.stat().st_mtime_ns, stamp)

    def test_set_with_confirm_writes_exactly_what_the_preview_showed(self):
        arguments = ("set", "--backend", "gitlab", "--host", "gitlab.example.com",
                     "--project-id", "17")
        with ProjectDir(document("github", GITHUB)) as root:
            path = root / ".agent" / "tracker.json"
            preview = self.run_cli(root, *arguments)
            done = self.run_cli(root, *arguments, "--confirm")
            self.assertEqual(done.returncode, 0)
            # The write run prints the same diff as the preview run, so what landed is
            # what was shown; re-previewing afterwards then reports nothing left to do.
            shown = preview.stdout.split("\npreview only")[0]
            self.assertIn("defaultBackend", shown)  # 否则下一行会退化成 assertIn("", …)
            self.assertIn(shown, done.stdout)
            self.assertEqual(path.read_text(encoding="utf-8"), render("gitlab", GITLAB))
            self.assertIn("no change", self.run_cli(root, *arguments).stdout)
            self.assertEqual(read_default(root).target, GITLAB)

    def test_set_creates_the_document_when_absent(self):
        with ProjectDir() as root:
            done = self.run_cli(root, "set", "--backend", "github",
                                "--host", "github.com", "--repo", "team/repo", "--confirm")
            self.assertEqual(done.returncode, 0)
            self.assertEqual(read_default(root).target, GITHUB)
            self.assertEqual((root / ".agent" / "tracker.json").stat().st_mode & 0o777,
                             0o644)

    def test_set_preserves_the_existing_file_mode(self):
        with ProjectDir(document("github", GITHUB)) as root:
            path = root / ".agent" / "tracker.json"
            os.chmod(path, 0o600)
            done = self.run_cli(root, "set", "--backend", "github", "--host",
                                "github.com", "--repo", "team/other", "--confirm")
            self.assertEqual(done.returncode, 0)
            # Assert the write happened, so a `set` that stopped writing could not pass
            # this case by leaving the original mode untouched.
            self.assertEqual(read_default(root).target["repo"], "team/other")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_set_rejects_a_wrong_shape_without_writing(self):
        with ProjectDir() as root:
            path = root / ".agent" / "tracker.json"
            for arguments in (("set", "--backend", "github", "--host", "github.com"),
                              ("set", "--backend", "github", "--host", "github.com",
                               "--repo", "repo"),
                              ("set", "--backend", "gitlab", "--host",
                               "gitlab.example.com", "--project-id", "seventeen"),
                              ("set", "--backend", "local", "--project-id", "has space")):
                done = self.run_cli(root, *arguments, "--confirm")
                self.assertEqual(done.returncode, 2, arguments)
                self.assertFalse(path.exists(), arguments)

    def test_set_never_touches_the_module_bookmark(self):
        with ProjectDir(document("github", GITHUB)) as root:
            state = self.state_file(root)
            before, stamp = state.read_text(encoding="utf-8"), state.stat().st_mtime_ns
            done = self.run_cli(root, "set", "--backend", "local",
                                "--project-id", LOCAL["projectId"], "--confirm")
            self.assertEqual(done.returncode, 0)
            # The write must actually have happened, otherwise an unrelated early exit
            # would satisfy the two assertions below vacuously.
            self.assertEqual(read_default(root).backend, "local")
            self.assertEqual(state.read_text(encoding="utf-8"), before)
            self.assertEqual(state.stat().st_mtime_ns, stamp)

    def test_set_leaves_no_temporary_file_behind(self):
        with ProjectDir() as root:
            self.run_cli(root, "set", "--backend", "local",
                         "--project-id", LOCAL["projectId"], "--confirm")
            self.assertEqual(sorted(p.name for p in (root / ".agent").iterdir()),
                             ["tracker.json"])


class HostileDocumentTests(unittest.TestCase):
    """`.agent/tracker.json` is repository content, so every byte and the inode itself
    are attacker-controlled: a hostile repo ships whatever it likes there."""

    HOOKS = Path(__file__).resolve().parent

    def run_cli(self, root, *arguments):
        return subprocess.run(
            [sys.executable, "-B", "tracker_default.py", *arguments,
             "--project", str(root)],
            cwd=str(self.HOOKS), capture_output=True, text=True, timeout=30)

    def scene(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "project"
        (root / ".agent").mkdir(parents=True)
        outside = Path(tmp.name) / "outside"
        outside.mkdir()
        secret = outside / "secret"
        secret.write_text("AWS_SECRET_ACCESS_KEY=hunter2\nsecond-line\n", encoding="utf-8")
        return tmp, root, outside, secret

    # ── the document is a symlink ──────────────────────────────────────────
    def test_symlinked_document_is_invalid_and_discloses_nothing(self):
        tmp, root, _outside, secret = self.scene()
        with tmp:
            (root / ".agent" / "tracker.json").symlink_to(secret)
            result = read_default(root)
            self.assertEqual(result.state, "invalid")
            self.assertNotIn("hunter2", json.dumps(as_json(result)))

    def test_set_preview_never_echoes_a_foreign_document(self):
        tmp, root, _outside, secret = self.scene()
        with tmp:
            (root / ".agent" / "tracker.json").symlink_to(secret)
            done = self.run_cli(root, "set", "--backend", "local",
                                "--project-id", LOCAL["projectId"])
            self.assertNotIn("hunter2", done.stdout + done.stderr)
            self.assertNotIn("second-line", done.stdout + done.stderr)

    def test_confirm_does_not_write_through_a_symlinked_document(self):
        tmp, root, _outside, secret = self.scene()
        with tmp:
            path = root / ".agent" / "tracker.json"
            path.symlink_to(secret)
            self.run_cli(root, "set", "--backend", "local",
                         "--project-id", LOCAL["projectId"], "--confirm")
            self.assertIn("hunter2", secret.read_text(encoding="utf-8"))
            self.assertFalse(path.is_symlink())

    # ── a pre-planted temporary name ───────────────────────────────────────
    def test_a_planted_temporary_name_cannot_capture_the_write(self):
        tmp, root, _outside, secret = self.scene()
        with tmp:
            agent = root / ".agent"
            # The attacker cannot know the exclusive name, so blanket the plausible
            # space: every pid-shaped temp name this process could pick.
            base = os.getpid()
            for pid in range(base, base + 600):
                (agent / ("tracker.json.%d.tmp" % pid)).symlink_to(secret)
            self.run_cli(root, "set", "--backend", "local",
                         "--project-id", LOCAL["projectId"], "--confirm")
            self.assertIn("hunter2", secret.read_text(encoding="utf-8"))
            self.assertEqual(read_default(root).target, LOCAL)

    # ── the .agent directory is a symlink ──────────────────────────────────
    def test_confirm_refuses_to_write_through_a_symlinked_agent_directory(self):
        tmp, root, outside, _secret = self.scene()
        with tmp:
            agent = root / ".agent"
            for child in agent.iterdir():
                child.unlink()
            agent.rmdir()
            agent.symlink_to(outside, target_is_directory=True)
            done = self.run_cli(root, "set", "--backend", "github",
                                "--host", "github.com", "--repo", "o/n", "--confirm")
            self.assertEqual(done.returncode, 2)
            self.assertFalse((outside / "tracker.json").exists())

    # ── bytes that are not a document at all ───────────────────────────────
    def test_non_utf8_bytes_are_invalid_rather_than_a_traceback(self):
        tmp, root, _outside, _secret = self.scene()
        with tmp:
            (root / ".agent" / "tracker.json").write_bytes(b'\xff\xfe{"version":1}')
            self.assertEqual(read_default(root).state, "invalid")
            show = self.run_cli(root, "show")
            self.assertEqual(show.returncode, 0)
            self.assertEqual(json.loads(show.stdout),
                             {"state": "invalid", "diagnostic": "tracker-default-invalid"})
            self.assertNotIn("Traceback", show.stderr)
            setter = self.run_cli(root, "set", "--backend", "local",
                                  "--project-id", LOCAL["projectId"])
            self.assertNotIn("Traceback", setter.stderr)

    def test_an_oversized_document_is_invalid(self):
        tmp, root, _outside, _secret = self.scene()
        with tmp:
            payload = dict(document("local", LOCAL), padding="x" * 70000)
            (root / ".agent" / "tracker.json").write_text(json.dumps(payload),
                                                          encoding="utf-8")
            self.assertEqual(read_default(root).state, "invalid")

    def test_a_non_regular_document_is_invalid(self):
        tmp, root, _outside, _secret = self.scene()
        with tmp:
            path = root / ".agent" / "tracker.json"
            path.mkdir()
            self.assertEqual(read_default(root).state, "invalid")

    # ── bounded identifiers ────────────────────────────────────────────────
    def test_overlong_host_and_repo_parts_are_invalid(self):
        self.assertIsNone(normalize_target("github", {"host": "a" * 300,
                                                      "repo": "team/repo"}))
        self.assertIsNone(normalize_target("github", {"host": "github.com",
                                                      "repo": "t" * 200 + "/repo"}))
        self.assertIsNone(normalize_target("gitlab", {"host": "a" * 300,
                                                      "projectId": 17}))


if __name__ == "__main__":
    unittest.main()
