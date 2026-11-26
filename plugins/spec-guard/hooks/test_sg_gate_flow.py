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


import module_stage  # noqa: E402
import map_view  # noqa: E402
from module_stage import DOC_SECTIONS, review_approved_line, review_digest  # noqa: E402

CMD = {"review-mark": "/spec-guard:review-mark", "milestone-mark": "/spec-guard:milestone-mark"}
PREAUTH = "<!-- spec-guard: release-preauth yes -->"


def requirement(extra=(), approved=True, tier="normal", body="不涉及"):
    """spec/a.md of a flow v2 module; `extra` are marker lines under the flow marker; approved binds the digest."""
    head = "# a\n\n<!-- spec-guard: flow v2 tier=%s -->\n%s" % (tier, "".join(line + "\n" for line in extra))
    text = head + "\n" + "".join("## %s\n\n%s\n\n" % (name, body) for name in DOC_SECTIONS["requirement"]["zh"])
    if approved:
        text = text.replace("# a\n\n", "# a\n\n%s\n" % review_approved_line(review_digest(text)), 1)
    return text


class MapProject(Project):
    """A project with a capability map of the given modules."""

    def __init__(self, config=None, ids=("a",)):
        super().__init__(config)
        self.ids = ids

    def __enter__(self):
        super().__enter__()
        rows = "".join("| %s | x | — |\n" % module for module in self.ids)
        self.write("spec/CAPABILITY-MAP.md", "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n"
                   "|---|---|---|\n%s\nBuild order: %s\n" % (rows, " → ".join(self.ids)))
        return self

    def takeover(self, module="a"):
        return next(m for m in map_view.build(self.root)["modules"] if m["id"] == module)["takeover"]


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


class ReleaseQuestion(unittest.TestCase):
    """R1: the release question is asked only where the takeover lets autopilot release."""

    def hint(self, config):
        with MapProject(config) as project:
            project.write("spec/a.md", requirement(approved=False))
            return module_stage.requirement_hint(project.root, "a", "pending", CMD, True)[1], \
                module_stage.requirement_hint(project.root, "a", "pending", CMD, False)[1]

    def test_asked_under_autopilot(self):
        for config in ({"takeover": "autopilot"}, {"takeover": {"release": "auto"}}):
            with self.subTest(config=config):
                zh, en = self.hint(config)
                self.assertIn("做完自动发版吗？", zh)
                self.assertIn("release-preauth yes", zh)
                self.assertIn("release-preauth yes", en)

    def test_not_asked_otherwise_and_unchanged(self):
        base = self.hint(None)
        for config in ({"takeover": {"preset": "autopilot", "release": "human"}}, {"takeover": "merge"},
                       {"takeover": {"release": "prepare"}}):
            with self.subTest(config=config):
                self.assertEqual(self.hint(config), base)
                self.assertNotIn("做完自动发版吗", base[0])


class ReleasePreauth(unittest.TestCase):
    """R2: /map --json takeover.releasePreauth."""

    def value(self, spec, config=None):
        with MapProject(config if config is not None else {"takeover": "autopilot"}) as project:
            project.write("spec/a.md", spec)
            return project.takeover()["releasePreauth"]

    def test_true_when_confirmed_and_allowed(self):
        self.assertIs(self.value(requirement([PREAUTH])), True)

    def test_false_after_an_edit_or_without_the_line(self):
        edited = requirement([PREAUTH]).replace("不涉及", "改过", 1)
        self.assertIs(self.value(edited), False)
        self.assertIs(self.value(requirement()), False)
        self.assertIs(self.value(requirement([PREAUTH], approved=False)), False)
        self.assertIs(self.value(requirement(["<!-- spec-guard: release-preauth maybe -->"])), False)

    def test_null_when_not_allowed_or_old_flow(self):
        self.assertIsNone(self.value(requirement([PREAUTH]), {"takeover": {"preset": "autopilot", "release": "human"}}))
        self.assertIsNone(self.value(requirement([PREAUTH]), {}))
        self.assertIsNone(self.value("# a\n\n" + PREAUTH + "\n"))

    def test_preset_field(self):
        with MapProject({"takeover": {"merge": "auto"}, "moduleTakeover": {"b": "autopilot"}}, ids=("a", "b")) as project:
            project.write("spec/a.md", requirement())
            project.write("spec/b.md", requirement())
            self.assertIsNone(project.takeover("a")["preset"])
            self.assertEqual(project.takeover("b")["preset"], "autopilot")


if __name__ == "__main__":
    unittest.main()
