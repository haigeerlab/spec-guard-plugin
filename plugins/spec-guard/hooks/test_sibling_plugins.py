#!/usr/bin/env python3
"""delegate-review-hint: whether delegate is installed and enabled, read from local records only."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sibling_plugins  # noqa: E402


class Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="sg-sibling-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.claude = self.tmp / "claude"
        self.codex = self.tmp / "codex"
        self.project = self.tmp / "project"
        for path in (self.claude, self.codex, self.project):
            path.mkdir()
        env = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.claude), "CODEX_HOME": str(self.codex)})
        env.start()
        self.addCleanup(env.stop)

    def write_json(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def install_claude(self, enabled=True, project_path=None, key="delegate@delegate-marketplace"):
        install = {"scope": "user", "installPath": str(self.tmp / "delegate"), "version": "0.5.2"}
        if project_path:
            install.update(scope="project", projectPath=str(project_path))
        self.write_json(self.claude / "plugins" / "installed_plugins.json", {"version": 2, "plugins": {key: [install]}})
        self.write_json(self.claude / "settings.json", {"enabledPlugins": {key: enabled}})

    def codex_config(self, text, cache=True, market="delegate-marketplace"):
        (self.codex / "config.toml").write_text(text, encoding="utf-8")
        if cache:
            (self.codex / "plugins" / "cache" / market / "delegate").mkdir(parents=True)


class DelegateEnabledTests(Fixture):
    # ── Claude ──
    def test_claude_installed_and_enabled(self):
        self.install_claude()
        self.assertTrue(sibling_plugins.delegate_enabled(self.project, None))
        self.assertTrue(sibling_plugins.delegate_enabled(self.project, "claude"))

    def test_claude_installed_but_disabled(self):
        self.install_claude(enabled=False)
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, None))

    def test_claude_install_scoped_to_another_project(self):
        self.install_claude(project_path=self.tmp / "elsewhere")
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, None))

    def test_claude_corrupt_record(self):
        (self.claude / "plugins").mkdir()
        (self.claude / "plugins" / "installed_plugins.json").write_text("{not json", encoding="utf-8")
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, None))

    def test_claude_record_does_not_count_on_codex(self):
        self.install_claude()
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, "codex"))

    def test_claude_enabled_only_in_the_main_checkouts_local_settings(self):
        self.install_claude(enabled=False)
        main = self.tmp / "main"
        gitdir = main / ".git" / "worktrees" / "wt"
        gitdir.mkdir(parents=True)
        (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
        (self.project / ".git").write_text("gitdir: %s\n" % gitdir, encoding="utf-8")
        self.write_json(main / ".claude" / "settings.local.json",
                        {"enabledPlugins": {"delegate@delegate-marketplace": True}})
        self.assertTrue(sibling_plugins.delegate_enabled(self.project, None))

    # ── Codex ──
    def test_codex_enabled_with_cache(self):
        self.codex_config('[plugins."other@m"]\nenabled = false\n\n[plugins."delegate@delegate-marketplace"]\n'
                          'enabled = true\n\n[projects."/x"]\ntrust_level = "trusted"\n')
        self.assertTrue(sibling_plugins.delegate_enabled(self.project, "codex"))

    def test_codex_disabled(self):
        self.codex_config('[plugins."delegate@delegate-marketplace"]\nenabled = false\n')
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, "codex"))

    def test_codex_enabled_without_cache(self):
        self.codex_config('[plugins."delegate@delegate-marketplace"]\nenabled = true\n', cache=False)
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, "codex"))

    def test_codex_enabled_key_belongs_to_the_next_table(self):
        self.codex_config('[plugins."delegate@delegate-marketplace"]\n\n[plugins."other@m"]\nenabled = true\n')
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, "codex"))

    def test_codex_unreadable_config(self):
        (self.codex / "config.toml").mkdir()
        self.assertFalse(sibling_plugins.delegate_enabled(self.project, "codex"))



class DelegateReviewEntryTests(Fixture):
    """delegate-interface-check: commands from delegate's interface.json, version range >=1.0,<2.0."""

    DEFAULT = {"review": "/delegate:review", "doctor": "/delegate:doctor", "source": "default"}

    def interface(self, root, data):
        root.mkdir(parents=True, exist_ok=True)
        (root / "interface.json").write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def declared(self, version="1.0", review="/delegate:review", doctor="/delegate:doctor"):
        return {"interface": version, "review": {"command": review, "readOnly": True},
                "doctor": {"command": doctor}}

    def entry(self, host=None):
        return sibling_plugins.delegate_review_entry(self.project, host)

    # ── Claude ──
    def test_claude_compatible_takes_the_commands(self):
        self.install_claude()
        self.interface(self.tmp / "delegate", self.declared(review="/delegate:review-two", doctor="/delegate:check"))
        self.assertEqual(self.entry(), {"review": "/delegate:review-two", "doctor": "/delegate:check",
                                        "source": "interface"})

    def test_claude_minor_versions_stay_compatible(self):
        self.install_claude()
        self.interface(self.tmp / "delegate", self.declared("1.7"))
        self.assertEqual(self.entry()["source"], "interface")

    def test_claude_other_major_versions_give_no_hint(self):
        self.install_claude()
        for version in ("2.0", "0.9"):
            self.interface(self.tmp / "delegate", self.declared(version))
            self.assertIsNone(self.entry(), version)

    def test_claude_missing_file_keeps_the_defaults(self):
        self.install_claude()
        self.assertEqual(self.entry(), self.DEFAULT)

    def test_claude_unreadable_file_keeps_the_defaults(self):
        self.install_claude()
        self.interface(self.tmp / "delegate", "{not json")
        self.assertEqual(self.entry(), self.DEFAULT)
        self.interface(self.tmp / "delegate", {"interface": "one"})
        self.assertEqual(self.entry(), self.DEFAULT)

    def test_claude_malformed_commands_fall_back_one_by_one(self):
        self.install_claude()
        self.interface(self.tmp / "delegate", self.declared(review="rm -rf /", doctor="/delegate:doctor-now"))
        self.assertEqual(self.entry(), {"review": "/delegate:review", "doctor": "/delegate:doctor-now",
                                        "source": "interface"})
        self.interface(self.tmp / "delegate", self.declared(review="/other:review"))
        self.assertEqual(self.entry()["review"], "/delegate:review")

    def test_claude_not_installed(self):
        self.assertIsNone(self.entry())

    def test_claude_disabled(self):
        self.install_claude(enabled=False)
        self.interface(self.tmp / "delegate", self.declared())
        self.assertIsNone(self.entry())

    # ── Codex ──
    def codex_enabled(self, versions):
        self.codex_config('[plugins."delegate@delegate-marketplace"]\nenabled = true\n')
        base = self.codex / "plugins" / "cache" / "delegate-marketplace" / "delegate"
        for version, data in versions.items():
            if data is None:
                (base / version).mkdir(parents=True)
            else:
                self.interface(base / version, data)

    def test_codex_single_version_compatible(self):
        self.codex_enabled({"0.5.3": self.declared(review="/delegate:review-two")})
        self.assertEqual(self.entry("codex")["source"], "interface")

    def test_codex_single_version_incompatible(self):
        self.codex_enabled({"0.6.0": self.declared("2.0")})
        self.assertIsNone(self.entry("codex"))

    def test_codex_several_versions_keep_the_defaults(self):
        self.codex_enabled({"0.5.2": None, "0.5.3": self.declared("2.0")})
        self.assertEqual(self.entry("codex"), self.DEFAULT)

    def test_codex_no_version_directory(self):
        self.codex_enabled({})
        self.assertIsNone(self.entry("codex"))


if __name__ == "__main__":
    unittest.main()
