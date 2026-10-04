"""Project default tracker backend: parsing and resolution. No network, no real project."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from tracker_default import as_json, read_default, resolve


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


if __name__ == "__main__":
    unittest.main()
