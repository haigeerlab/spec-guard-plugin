#!/usr/bin/env python3
"""plugin-spec-compliance (AC5): the CI workflow keeps the shape the plugin development rules ask for.

Needs PyYAML; skipped without it (the macOS system Python has none; CI's plugin job installs it).
"""
import importlib.util
from pathlib import Path
import re
import unittest

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))
DEPENDABOT = REPO / ".github" / "dependabot.yml"
LICENSE = REPO / "LICENSE"
HAS_YAML = importlib.util.find_spec("yaml") is not None
SUMMARY = "CI required"
SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")


def load(path):
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as True.
    if True in data:
        data["on"] = data.pop(True)
    return data


@unittest.skipUnless(HAS_YAML, "PyYAML is not installed")
class WorkflowTest(unittest.TestCase):
    def test_every_workflow(self):
        self.assertTrue(WORKFLOWS)
        for path in WORKFLOWS:
            with self.subTest(path.name):
                data = load(path)
                self.assertEqual(data.get("permissions"), {}, "top-level permissions must be {}")
                triggers = data.get("on") or {}
                for event in triggers.values() if isinstance(triggers, dict) else ():
                    if isinstance(event, dict):
                        self.assertNotIn("paths", event)
                        self.assertNotIn("paths-ignore", event)
                for name, job in data["jobs"].items():
                    permissions = job.get("permissions")
                    self.assertIn(permissions, ({}, {"contents": "read"}), "%s: permissions %r" % (name, permissions))
                    for step in job.get("steps", []):
                        uses = step.get("uses")
                        if not uses:
                            continue
                        self.assertRegex(uses, SHA_PIN, "%s: %s is not pinned to a full SHA" % (name, uses))
                        if uses.startswith("actions/checkout@"):
                            self.assertIs((step.get("with") or {}).get("persist-credentials"), False,
                                          "%s: checkout must set persist-credentials: false" % name)

    def test_summary_job_needs_every_other_job(self):
        data = load(REPO / ".github" / "workflows" / "ci.yml")
        self.assertEqual(data.get("name"), "CI")
        jobs = data["jobs"]
        summary = [key for key, job in jobs.items() if job.get("name") == SUMMARY]
        self.assertEqual(len(summary), 1, "exactly one job is named %r" % SUMMARY)
        job = jobs[summary[0]]
        self.assertEqual(set(job.get("needs", [])), set(jobs) - {summary[0]})
        self.assertEqual(str(job.get("if", "")).replace(" ", ""), "always()")
        steps = repr(job.get("steps", []))
        self.assertIn("toJSON(needs)", steps)
        self.assertIn("success", steps)

    def test_checks_end_with_a_clean_diff(self):
        data = load(REPO / ".github" / "workflows" / "ci.yml")
        for name, job in data["jobs"].items():
            if job.get("name") == SUMMARY:
                continue
            with self.subTest(name):
                self.assertEqual(job["steps"][-1].get("run", "").strip(), "git diff --exit-code")

    def test_python_versions(self):
        data = load(REPO / ".github" / "workflows" / "ci.yml")
        versions = data["jobs"]["python"]["strategy"]["matrix"]["python"]
        self.assertIn("3.9", versions)
        self.assertTrue(any(version != "3.9" for version in versions))
        # actions/python-versions ships 3.9 only for Ubuntu 22.04 and 24.04, not for ubuntu-latest (26.04).
        self.assertIn(data["jobs"]["python"]["runs-on"], ("ubuntu-22.04", "ubuntu-24.04"))

    def test_shellcheck_is_pinned_release(self):
        # ci-shellcheck-pin: the npm package asks the GitHub API for "latest" anonymously (shared runner IPs hit 403),
        # so CI downloads a pinned official release and checks its sha256 instead.
        for path in WORKFLOWS:
            for name, job in load(path)["jobs"].items():
                for step in job.get("steps", []):
                    run = step.get("run", "")
                    with self.subTest(path=path.name, job=name, step=step.get("name")):
                        self.assertFalse("npx" in run and "shellcheck" in run, "ShellCheck must not come from npx")
        steps = load(REPO / ".github" / "workflows" / "ci.yml")["jobs"]["validate"]["steps"]
        install = [i for i, step in enumerate(steps) if "releases/download/${SHELLCHECK_VERSION}/" in step.get("run", "")]
        self.assertEqual(len(install), 1, "exactly one step downloads the ShellCheck release")
        step = steps[install[0]]
        env = step.get("env") or {}
        self.assertRegex(str(env.get("SHELLCHECK_VERSION", "")), r"^v\d+\.\d+\.\d+$")
        self.assertRegex(str(env.get("SHELLCHECK_SHA256", "")), r"^[0-9a-f]{64}$")
        self.assertIn("sha256sum -c", step["run"])
        checks = [i for i, step in enumerate(steps) if "shellcheck -S warning" in step.get("run", "")]
        self.assertEqual(len(checks), 1)
        self.assertGreater(checks[0], install[0], "ShellCheck runs after it is installed")

    def test_plugin_validate_is_strict(self):
        text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(text, r"@anthropic-ai/claude-code@\d+\.\d+\.\d+ plugin validate --strict plugins/spec-guard")
        self.assertRegex(text, r"plugin validate --strict \.\s*$|plugin validate --strict \.\n")
        self.assertIn("scripts/check-frontmatter.py", text)

    def test_dependabot(self):
        data = load(DEPENDABOT)
        self.assertEqual(data.get("version"), 2)
        updates = data.get("updates")
        self.assertEqual([update["package-ecosystem"] for update in updates], ["github-actions"])
        self.assertEqual(updates[0]["schedule"]["interval"], "monthly")
        self.assertEqual(updates[0]["cooldown"]["default-days"], 7)


class LicenseTest(unittest.TestCase):
    def test_copyright_line(self):
        self.assertIn("Copyright (c) 2026 haigeerlab\n", LICENSE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
