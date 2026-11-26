"""sg-gate-flow (autopilot module 4): the autopilot preset, release pre-authorisation, the overall design gate, the
non-blocking milestone and the say-first line.  No network; every project is a temporary git repository."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import project_config  # noqa: E402

CONFIG = str(HERE / "project_config.py")


class Project:
    """A temporary git project with an optional .agent/config.json."""

    def __init__(self, config=None):
        self.config = config

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        if self.config is not None:
            self.write(".agent/config.json", json.dumps(dict({"version": 1}, **self.config)))
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run(self, script, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        done = subprocess.run([sys.executable, "-B", script, *args, "--project", str(self.root)],
                              capture_output=True, text=True, timeout=30, env=env)
        return done.returncode, done.stdout + done.stderr


AUTOPILOT = {"design": "reviewer", "merge": "auto", "release": "auto-confirm"}


class PresetConfig(unittest.TestCase):
    """R9: the autopilot preset and an object carrying a preset key."""

    def items(self, config, module="alpha"):
        with Project(config) as project:
            items, source = project_config.module_takeover(project.root, module)
            return {key: items[key] for key in ("design", "merge", "release")}, source, \
                project_config.module_preset(project.root, module)

    def test_autopilot_expands(self):
        self.assertEqual(self.items({"takeover": "autopilot"}), (AUTOPILOT, "takeover", "autopilot"))

    def test_preset_object_overrides_only_what_it_names(self):
        self.assertEqual(self.items({"takeover": {"preset": "autopilot", "release": "human"}}),
                         (dict(AUTOPILOT, release="human"), "takeover", "autopilot"))

    def test_module_entry_wins_and_names_its_preset(self):
        config = {"takeover": "none", "moduleTakeover": {"alpha": {"preset": "autopilot", "merge": "human"}}}
        self.assertEqual(self.items(config), (dict(AUTOPILOT, merge="human"), "moduleTakeover", "autopilot"))
        self.assertEqual(self.items(config, "beta")[2], "none")

    def test_object_without_preset_is_unchanged(self):
        human = {"design": "human", "merge": "human", "release": "human"}
        self.assertEqual(self.items({"takeover": {"merge": "auto"}}), (dict(human, merge="auto"), "takeover", None))

    def test_factory_default_is_still_none(self):
        human = {"design": "human", "merge": "human", "release": "human"}
        self.assertEqual(self.items(None), (human, "default", "none"))

    def test_invalid_preset_key_is_refused(self):
        for value in ({"preset": "plan"}, {"preset": "fast"}, {"preset": 1}):
            with self.subTest(value=value):
                self.assertFalse(project_config.valid_takeover(value))
                with Project() as project:
                    code, out = project.run(CONFIG, "set", "--key", "takeover", "--value", json.dumps(value),
                                            "--confirm")
                    self.assertEqual(code, 2, out)

    def test_set_writes_preset_and_object(self):
        for value in ("autopilot", {"preset": "autopilot", "release": "human"}):
            with self.subTest(value=value):
                with Project() as project:
                    raw = value if isinstance(value, str) else json.dumps(value)
                    code, out = project.run(CONFIG, "set", "--key", "takeover", "--value", raw, "--confirm")
                    self.assertEqual(code, 0, out)
                    stored = json.loads((project.root / ".agent" / "config.json").read_text(encoding="utf-8"))
                    self.assertEqual(stored["takeover"], value)

    def test_old_flow_pair_of_a_preset_object(self):
        # design review 1 #2: what the object writes for spec/plan is read as written
        cases = {json.dumps({"preset": "autopilot"}): {"spec": "codex", "plan": "codex"},
                 json.dumps({"preset": "autopilot", "plan": "human"}): {"spec": "codex", "plan": "human"},
                 json.dumps({"preset": "autopilot", "design": "human"}): {"spec": "codex", "plan": "human"},
                 json.dumps({"preset": "none", "spec": "codex"}): {"spec": "codex", "plan": "human"}}
        for raw, pair in cases.items():
            with self.subTest(value=raw):
                self.assertEqual(project_config.legacy(json.loads(raw)), pair)


class NarrowAndGates(unittest.TestCase):
    """R10: narrowing autopilot one step; the three gates never belong to a preset."""

    def test_autopilot_narrows_to_merge(self):
        self.assertEqual(project_config.narrow_step("autopilot"), "merge")

    def test_preset_object_hands_back_its_outermost_item(self):
        self.assertEqual(project_config.narrow_step({"preset": "autopilot", "merge": "human"}),
                         {"design": "reviewer"})
        self.assertEqual(project_config.narrow_step({"preset": "autopilot"}),
                         {"design": "reviewer", "merge": "auto"})

    def test_autopilot_is_wider_than_merge(self):
        self.assertTrue(project_config.takeover_wider(project_config.expand("autopilot"),
                                                      project_config.expand("merge")))
        self.assertEqual(project_config.widen_steps("merge", "autopilot"), 1)

    def test_no_gate_item_in_any_preset(self):
        for name, items in project_config.PRESETS.items():
            with self.subTest(preset=name):
                self.assertEqual(set(items), {"design", "merge", "release"})


if __name__ == "__main__":
    unittest.main()
