"""important-requirement (C1): an important requirement is decided by rules, never by the agent's own judgement."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from module_stage import important, risk_hit  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def _map(*ids):
    rows = "".join("| %s | x | — |\n" % module for module in ids)
    return ("# Capability Map\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n%s\nBuild order: %s\n"
            % (rows, " → ".join(ids)))


def _spec(exclusive="`src/a/`", shared=None):
    boundary = "## 并行边界\n\n- 独占：%s\n%s" % (exclusive, "- 公共：%s\n" % shared if shared else "")
    return "# Spec\n\n## Objective\n\nx\n\n%s" % boundary


class Important(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "spec").mkdir()
        (self.root / ".agent").mkdir()
        self.git("init", "-q")
        self.config({"takeover": {"spec": "codex"}})
        self.risk({"schema": "autopilot.risk-paths/v1", "category": "plugin", "default": "T2",
                   "T4": [".github/**", "**/*.lock"], "T3": ["src/auth/*.py"]})

    def git(self, *args):
        subprocess.run(GIT + list(args), cwd=self.root, check=True, capture_output=True, timeout=30)

    def config(self, values):
        (self.root / ".agent" / "config.json").write_text(json.dumps(dict(version=1, **values)), encoding="utf-8")

    def risk(self, document):
        folder = self.root / ".github" / "autopr"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "risk-paths.json").write_text(json.dumps(document), encoding="utf-8")

    def insert(self, *ids, specs=None):
        existing = (self.root / "spec" / "CAPABILITY-MAP.md")
        before = [] if not existing.exists() else [line.split("|")[1].strip() for line in
                                                   existing.read_text(encoding="utf-8").splitlines()
                                                   if line.startswith("| ") and "Module id" not in line]
        existing.write_text(_map(*(before + list(ids))), encoding="utf-8")
        for module in ids:
            (self.root / "spec" / ("%s.md" % module)).write_text((specs or {}).get(module, _spec("`src/%s/`" % module)),
                                                                 encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "insert %s" % ",".join(ids))

    def test_alone_and_clear_is_not_important(self):
        self.insert("alpha")
        self.assertEqual(important(self.root, "alpha"), [])

    def test_inserted_together_is_multi_module(self):
        self.insert("alpha", "beta")
        self.assertIn("multi-module", important(self.root, "alpha"))

    def test_shared_files_or_overlap_is_cross_module(self):
        self.insert("alpha", specs={"alpha": _spec(shared="锁文件")})
        self.assertIn("cross-module", important(self.root, "alpha"))
        self.insert("beta", specs={"beta": _spec("`src/`")})
        self.assertIn("cross-module", important(self.root, "beta"))

    def test_no_boundary_counts_only_when_spec_is_codex(self):
        self.insert("alpha", specs={"alpha": "# Spec\n\nx\n"})
        self.assertIn("cross-unknown", important(self.root, "alpha"))
        self.config({})
        self.assertEqual(important(self.root, "alpha"), [])

    def test_risk_paths_t3_and_t4(self):
        self.insert("alpha", specs={"alpha": _spec("`.github/workflows/`")})
        self.assertIn("risk-path", important(self.root, "alpha"))
        self.insert("beta", specs={"beta": _spec("`src/auth/login.py`")})
        self.assertIn("risk-path", important(self.root, "beta"))

    def test_missing_list_is_risk_unknown_only_when_spec_is_codex(self):
        (self.root / ".github" / "autopr" / "risk-paths.json").unlink()
        self.insert("alpha")
        self.assertEqual(important(self.root, "alpha"), ["risk-unknown"])
        self.config({})
        self.assertEqual(important(self.root, "alpha"), [])
        self.config({"takeover": {"spec": "codex"}})
        self.risk({"schema": "something-else/v9"})
        self.assertEqual(important(self.root, "alpha"), ["risk-unknown"])


class RiskHit(unittest.TestCase):
    def test_wildcards(self):
        cases = [(".github/**", ".github/workflows/ci.yml", True), (".github/**", ".github/", True),
                 ("src/*.py", "src/a.py", True), ("src/*.py", "src/a/b.py", False), ("src/*.py", "src/", True),
                 ("**/*.lock", "deep/dir/yarn.lock", True), ("docs/*.md", "src/", False),
                 ("src/auth/*.py", "src/", True), ("src/auth/*.py", "src/other/", False),
                 # A pattern that starts with a wildcard only matches named files: a directory says nothing about them.
                 ("**/*.lock", "src/", False), ("*.toml", "src/", False)]
        for pattern, path, expected in cases:
            with self.subTest(pattern=pattern, path=path):
                self.assertEqual(risk_hit(pattern, path), expected)


if __name__ == "__main__":
    unittest.main()
