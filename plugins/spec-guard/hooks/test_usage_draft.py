import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import usage_draft  # noqa: E402

MAP = """# Capability Map

## Goal

Test.

| Module id | Responsibility | Depends on |
|---|---|---|
| alpha | A | — |
| beta | B | alpha |
| gamma | C | beta |
| delta | D | beta |
| epsilon | E | gamma, delta |

Build order: alpha → beta → gamma, delta → epsilon
"""

GOOD = """# Usage draft: demo

## Entry points

| Entry | Does | Module |
|---|---|---|
| `/demo run` | runs it | alpha |
| `/demo show` | shows it | gamma, delta |

## Typical usage

### U1: run once
Type `/demo run`, get a result.

### U2: show
Type `/demo show`.

## Milestones

| Milestone | Usage | Modules |
|---|---|---|
| M1 | U1 | alpha, beta |
| M2 | U1, U2 | gamma, delta |
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def draft(self, text, name="demo.md"):
        folder = self.root / "spec" / "usage"
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8")

    def result(self):
        return usage_draft.validate(str(self.root))

    def assertFails(self, text, *phrases):
        self.draft(text)
        result = self.result()
        self.assertEqual(result["status"], "fail", result)
        joined = "\n".join(result["failures"])
        self.assertIn("spec/usage/demo.md", joined)
        for phrase in phrases:
            self.assertIn(phrase, joined)
        return result


class ValidateTest(Base):
    def test_absent_without_folder(self):
        self.assertEqual(self.result()["status"], "absent")

    def test_absent_with_empty_folder(self):
        (self.root / "spec" / "usage").mkdir()
        self.assertEqual(self.result()["status"], "absent")

    def test_good_draft_passes(self):
        self.draft(GOOD)
        result = self.result()
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["files"], ["spec/usage/demo.md"])
        self.assertEqual(result["failures"], [])
        # beta has no entry: reminder only
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("beta", result["warnings"][0])

    def test_fenced_example_ignored(self):
        self.draft(GOOD + "\n```\n## Milestones\n| Milestone | Usage | Modules |\n```\n")
        self.assertEqual(self.result()["status"], "pass")

    def test_missing_section(self):
        self.assertFails(GOOD.replace("## Entry points", "## Entries"), "Entry points")

    def test_malformed_table_is_failure_not_traceback(self):
        cases = {
            "header only": GOOD.replace("|---|---|---|\n| M1", "| M1").replace("| M1 | U1 | alpha, beta |\n| M2 | U1, U2 | gamma, delta |\n", ""),
            "no separator": GOOD.replace("| Milestone | Usage | Modules |\n|---|---|---|\n", "| Milestone | Usage | Modules |\n"),
            "short row": GOOD.replace("| M2 | U1, U2 | gamma, delta |", "| M2 | U1, U2 |"),
            "wrong header": GOOD.replace("| Milestone | Usage | Modules |", "| Stage | Usage | Modules |"),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.draft(text)
                result = self.result()
                self.assertEqual(result["status"], "fail", result)
                self.assertTrue(any("Milestones" in item for item in result["failures"]), result)

    def test_usage_heading_must_be_numbered(self):
        self.assertFails(GOOD.replace("### U2: show", "### show"), "U<n>")

    def test_no_usage(self):
        text = GOOD.split("## Typical usage")[0] + "## Typical usage\n\nnone\n\n## Milestones" + GOOD.split("## Milestones")[1]
        self.assertFails(text, "典型用法")

    def test_unknown_usage(self):
        self.assertFails(GOOD.replace("| M2 | U1, U2 |", "| M2 | U1, U2, U9 |"), "U9")

    def test_unreferenced_usage(self):
        text = GOOD.replace("### U2: show", "### U3: extra\nx\n\n### U2: show")
        self.assertFails(text, "U3")

    def test_last_milestone_must_cover_all(self):
        self.assertFails(GOOD.replace("| M2 | U1, U2 |", "| M2 | U2 |"), "M2", "U1")

    def test_duplicate_milestone_id(self):
        self.assertFails(GOOD.replace("| M2 | U1, U2 |", "| M1 | U1, U2 |"), "M1")

    def test_bad_milestone_id(self):
        self.assertFails(GOOD.replace("| M2 | U1, U2 |", "| Two | U1, U2 |"), "Two")

    def test_module_not_in_map(self):
        self.assertFails(GOOD.replace("| M2 | U1, U2 | gamma, delta |", "| M2 | U1, U2 | gamma, delta, zeta |"), "zeta")

    def test_module_in_two_milestones(self):
        self.assertFails(GOOD.replace("| M2 | U1, U2 | gamma, delta |", "| M2 | U1, U2 | beta, gamma, delta |"), "beta")

    def test_module_in_two_drafts(self):
        self.draft(GOOD)
        other = ("# Usage draft: other\n\n## Entry points\n\n| Entry | Does | Module |\n|---|---|---|\n"
                 "| `/other` | x | epsilon |\n\n## Typical usage\n\n### U1: x\nx\n\n## Milestones\n\n"
                 "| Milestone | Usage | Modules |\n|---|---|---|\n| M1 | U1 | alpha, epsilon |\n")
        self.draft(other, "other.md")
        result = self.result()
        self.assertEqual(result["status"], "fail", result)
        self.assertTrue(any("alpha" in item and "other.md" in item for item in result["failures"]), result)

    def test_entry_module_outside_milestones(self):
        self.assertFails(GOOD.replace("| `/demo show` | shows it | gamma, delta |", "| `/demo show` | shows it | epsilon |"), "epsilon")

    def test_build_order_inversion(self):
        text = GOOD.replace("| M1 | U1 | alpha, beta |", "| M1 | U1 | alpha, gamma |").replace("| M2 | U1, U2 | gamma, delta |", "| M2 | U1, U2 | beta, delta |")
        self.assertFails(text, "Build order", "M2")

    def test_comma_group_across_milestones(self):
        text = GOOD.replace("| M1 | U1 | alpha, beta |", "| M1 | U1 | alpha, beta, gamma |").replace("| M2 | U1, U2 | gamma, delta |", "| M2 | U1, U2 | delta |")
        self.assertFails(text, "Build order")

    def test_unreadable_map_is_unverified(self):
        self.draft(GOOD)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text("broken", encoding="utf-8")
        self.assertEqual(self.result()["status"], "unverified")


    def test_duplicate_reports_once(self):
        result = self.assertFails(GOOD.replace("| M2 | U1, U2 | gamma, delta |", "| M2 | U1, U2 | beta, gamma, delta |"), "beta")
        self.assertFalse(any("Build order" in item for item in result["failures"]), result)

    def test_confirmation_ok(self):
        self.draft(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha, beta -->\n")
        result = self.result()
        self.assertEqual(result["status"], "pass", result)

    def test_confirmation_bad_format(self):
        self.assertFails(GOOD + "\n<!-- spec-guard: milestone M1 ok -->\n", "M1")

    def test_confirmation_unknown_milestone(self):
        self.assertFails(GOOD + "\n<!-- spec-guard: milestone M7 confirmed alpha -->\n", "M7")

    def test_confirmation_twice(self):
        self.assertFails(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha, beta -->\n"
                         "<!-- spec-guard: milestone M1 confirmed alpha, beta -->\n", "M1")

    def test_confirmation_stale_is_warning(self):
        self.draft(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha -->\n")
        result = self.result()
        self.assertEqual(result["status"], "pass", result)
        self.assertTrue(any("M1" in item and "确认后" in item for item in result["warnings"]), result)


MAPPED = {"alpha", "beta", "gamma", "delta", "epsilon"}


class StopTest(Base):
    def stop(self, done, mapped=MAPPED):
        return usage_draft.stop(str(self.root), set(done), set(mapped))

    def test_no_drafts(self):
        self.assertIsNone(self.stop(MAPPED))

    def test_not_complete(self):
        self.draft(GOOD)
        self.assertIsNone(self.stop({"alpha"}))

    def test_complete_unconfirmed_stops(self):
        self.draft(GOOD)
        found = self.stop({"alpha", "beta"})
        self.assertEqual(found["status"], "stop")
        self.assertEqual((found["file"], found["milestone"]), ("spec/usage/demo.md", "M1"))
        self.assertEqual(found["modules"], ["alpha", "beta"])
        self.assertEqual(found["usages"], ["U1"])

    def test_confirmed_does_not_stop(self):
        self.draft(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha, beta -->\n")
        self.assertIsNone(self.stop({"alpha", "beta"}))

    def test_last_milestone_stops(self):
        self.draft(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha, beta -->\n")
        found = self.stop(MAPPED)
        self.assertEqual(found["milestone"], "M2")
        self.assertEqual(found["usages"], ["U1", "U2"])

    def test_stale_confirmation_stops_again(self):
        self.draft(GOOD + "\n<!-- spec-guard: milestone M1 confirmed alpha -->\n")
        self.assertEqual(self.stop({"alpha", "beta"})["milestone"], "M1")

    def test_first_stop_across_drafts(self):
        self.draft(GOOD)
        other = ("# Usage draft: a\n\n## Entry points\n\n| Entry | Does | Module |\n|---|---|---|\n"
                 "| `/a` | x | epsilon |\n\n## Typical usage\n\n### U1: x\nx\n\n## Milestones\n\n"
                 "| Milestone | Usage | Modules |\n|---|---|---|\n| M1 | U1 | epsilon |\n")
        self.draft(other, "a.md")
        self.assertEqual(self.stop(MAPPED)["file"], "spec/usage/a.md")

    def test_broken_draft_unverified(self):
        self.draft("# nothing\n")
        found = self.stop(MAPPED)
        self.assertEqual(found["status"], "unverified")
        self.assertIn("spec/usage/demo.md", found["reason"])

    def test_unmapped_module_unverified(self):
        self.draft(GOOD)
        found = self.stop({"alpha", "beta"}, mapped={"alpha", "gamma", "delta"})
        self.assertEqual(found["status"], "unverified")
        self.assertIn("beta", found["reason"])


class MilestonesTest(Base):
    def test_lookup(self):
        self.draft(GOOD)
        found = usage_draft.milestones(str(self.root))
        self.assertEqual(found["gamma"], ("spec/usage/demo.md", "M2"))
        self.assertEqual(found["alpha"], ("spec/usage/demo.md", "M1"))
        self.assertEqual(usage_draft.draft_files(str(self.root)), ["spec/usage/demo.md"])

    def test_integration_regression_is_not_a_draft(self):
        # regression-doc-check: spec/usage/<name>.regression.md is the requirement's integration regression, not a draft
        self.draft(GOOD)
        (self.root / "spec" / "usage" / "demo.regression.md").write_text("## 用例清单\n\n不涉及\n", encoding="utf-8")
        self.assertEqual(usage_draft.draft_files(str(self.root)), ["spec/usage/demo.md"])
        self.assertEqual(usage_draft.milestones(str(self.root))["alpha"], ("spec/usage/demo.md", "M1"))

    def test_no_drafts(self):
        self.assertEqual(usage_draft.draft_files(str(self.root)), [])
        self.assertEqual(usage_draft.milestones(str(self.root)), {})

    def test_broken_draft_raises(self):
        self.draft("# nothing\n")
        with self.assertRaises(usage_draft.UsageDraftError):
            usage_draft.milestones(str(self.root))


class CliTest(Base):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(HERE / "usage_draft.py")] + list(args),
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def test_lines_and_exit_codes(self):
        out = self.run_cli("validate", "--project", str(self.root))
        self.assertEqual(out.returncode, 0)
        self.assertEqual(out.stdout.strip(), "absent")
        self.draft(GOOD)
        out = self.run_cli("validate", "--project", str(self.root))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.splitlines()[0], "ok 1")
        self.assertTrue(out.stdout.splitlines()[1].startswith("warn "))
        self.draft(GOOD.replace("| M2 | U1, U2 |", "| M2 | U2 |"))
        out = self.run_cli("validate", "--project", str(self.root))
        self.assertEqual(out.returncode, 1)
        self.assertTrue(out.stdout.startswith("bad "))

    def test_json_format(self):
        self.draft(GOOD)
        out = self.run_cli("validate", "--project", str(self.root), "--format", "json")
        self.assertEqual(json.loads(out.stdout)["status"], "pass")

    def test_missing_project(self):
        out = self.run_cli("validate", "--project", str(self.root / "nope"))
        self.assertEqual(out.returncode, 2)


GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def _map(*ids):
    rows = "".join("| %s | x | — |\n" % module for module in ids)
    return ("# Capability Map\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n%s\nBuild order: %s\n"
            % (rows, " → ".join(ids)))


class Missing(unittest.TestCase):
    """usage-draft-gate (C1): a batch of 2+ modules inserted in one commit, not done, with no draft covering them."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()

    def git(self, *args):
        subprocess.run(GIT + list(args), cwd=self.root, check=True, capture_output=True, timeout=30)

    def write_map(self, *ids):
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(_map(*ids), encoding="utf-8")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True, text=True,
                              check=True).stdout.strip()

    def base(self):
        self.git("init", "-q")
        self.write_map("alpha")
        self.commit("first")

    def test_batch_without_a_draft(self):
        self.base()
        self.write_map("alpha", "beta", "gamma")
        sha = self.commit("two at once")
        found = usage_draft.missing(str(self.root), {"alpha"})
        self.assertEqual(found["status"], "missing", found)
        self.assertEqual(found["batches"], [{"commit": sha, "modules": ["beta", "gamma"], "uncovered": ["beta", "gamma"]}])

    def test_draft_covers_the_batch(self):
        self.base()
        self.write_map("alpha", "beta", "gamma")
        self.commit("two at once")
        usage = self.root / "spec" / "usage"
        usage.mkdir()
        (usage / "demo.md").write_text(GOOD, encoding="utf-8")  # its milestones list beta (M1) and gamma (M2)
        found = usage_draft.missing(str(self.root), {"alpha"})
        self.assertEqual(found["status"], "ok", found)

    def test_one_module_per_commit_is_fine(self):
        self.base()
        self.write_map("alpha", "beta")
        self.commit("one")
        self.write_map("alpha", "beta", "gamma")
        self.commit("another")
        self.assertEqual(usage_draft.missing(str(self.root), set())["status"], "ok")

    def test_finished_batches_are_left_alone(self):
        self.base()
        self.write_map("alpha", "beta", "gamma")
        self.commit("two at once")
        self.assertEqual(usage_draft.missing(str(self.root), {"alpha", "beta", "gamma"})["status"], "ok")

    def test_uncommitted_rows_are_a_batch(self):
        self.base()
        self.write_map("alpha", "beta", "gamma")
        found = usage_draft.missing(str(self.root), set())
        self.assertEqual(found["status"], "missing", found)
        self.assertEqual(found["batches"][0]["commit"], "uncommitted")

    def test_outside_git_is_unverified(self):
        self.write_map("alpha", "beta", "gamma")
        found = usage_draft.missing(str(self.root), set())
        self.assertEqual(found["status"], "unverified")
        self.assertTrue(found["reason"])


if __name__ == "__main__":
    unittest.main()
