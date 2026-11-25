"""verification-criteria: author records, the pre-merge verification report check, and the recorded verdict.  No network."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from test_flow_v2 import CASES_EN, USAGE_REGRESSION, criteria_requirement, git  # noqa: E402

SCRIPT = HERE / "verification.py"
ENV_KEYS = ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID")

TWO_CASES = CASES_EN.replace("## Success criteria coverage", """### R2: confirm by hand
- Steps: look
- Expected: same
- Method: manual
- Evidence: user quote

### R3: old export
- Steps: export
- Expected: same as before
- Method: command
- Command: `make export`
- Evidence: log

## Success criteria coverage""")


def run(root, *args, session=None, codex=None):
    env = {k: v for k, v in os.environ.items() if k not in ENV_KEYS}
    if session:
        env["CLAUDE_CODE_SESSION_ID"] = session
    if codex:
        env["CODEX_THREAD_ID"] = codex
    done = subprocess.run([sys.executable, "-B", str(SCRIPT), *args, "--project", str(root)],
                          capture_output=True, text=True, env=env)
    return done


def commit(root, message="c"):
    git(root, "add", "-A")
    git(root, "commit", "-qm", message, "--allow-empty")
    return git(root, "rev-parse", "HEAD")


def patch_id(root, base, head):
    diff = subprocess.run(["git", "-C", str(root), "diff", base, head], capture_output=True, check=True).stdout
    out = subprocess.run(["git", "-C", str(root), "patch-id", "--stable"], input=diff, capture_output=True, check=True).stdout
    return out.decode().split()[0]


class Repo:
    """A project on main with a flow v2 module `a`, then a feature branch with one change."""

    def __init__(self, modules=("a",)):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        rows = "".join("| %s | x | — |\n" % m for m in modules)
        self.write("spec/CAPABILITY-MAP.md", "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
                   "%s\nBuild order: %s\n" % (rows, " → ".join(modules)))
        for m in modules:
            self.write("spec/%s.md" % m, criteria_requirement("S1"))
            self.write("tasks/%s/regression.md" % m, TWO_CASES)
        self.write("src/x.py", "x = 1\n")
        self.base = commit(self.root, "base")
        git(self.root, "switch", "-q", "-c", "feature")
        self.write("src/x.py", "x = 2\n")
        self.head = commit(self.root, "change")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def doc_sha(self, module="a"):
        return hashlib.sha256((self.root / "tasks" / module / "regression.md").read_bytes()).hexdigest()

    def evidence(self, name="log.txt", text="ok\n"):
        path = Path(self.tmp.name + "-evidence") / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {"type": "log", "path": str(path), "sha256": hashlib.sha256(text.encode()).hexdigest(), "source": None}

    def report(self, **change):
        quote = dict(self.evidence("quote.txt", "looks the same\n"), type="user-quote", source="session x, 2026-11-26 10:00")
        doc = {"schema": "spec-guard.verification/v1", "module": "a", "usage": None,
               "regression": {"document": "tasks/a/regression.md", "sha256": self.doc_sha()},
               "base": self.base, "head": self.head, "patchId": patch_id(self.root, self.base, self.head),
               "executor": {"sessionId": "verifier-1", "host": "codex", "vendor": "openai", "sameVendorAsAuthor": False},
               "verdict": "pass-with-notes",
               "cases": [{"id": "R1", "method": "ai-operate", "result": "pass", "failCategory": None, "baselineCommit": None,
                          "evidence": [self.evidence()]},
                         {"id": "R2", "method": "manual", "result": "pass", "failCategory": None, "baselineCommit": None,
                          "evidence": [quote]},
                         {"id": "R3", "method": "command", "result": "baseline-fail", "failCategory": None,
                          "baselineCommit": self.base, "evidence": [self.evidence("base.txt", "fails on base too\n")]}],
               "notes": [{"title": "naming", "detail": "x could be clearer", "location": "src/x.py:1", "evidence": None}]}
        for key, value in change.items():
            doc[key] = value
        path = Path(self.tmp.name + "-evidence") / "report.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def close(self):
        self.tmp.cleanup()
        import shutil
        shutil.rmtree(self.tmp.name + "-evidence", ignore_errors=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.close)
        self.root = self.repo.root

    def author(self, session="author-1"):
        return run(self.root, "author", "--module", "a", session=session)

    def check(self, report, *extra):
        done = run(self.root, "check", "--module", "a", "--report", str(report), "--json", *extra)
        return done.returncode, json.loads(done.stdout) if done.stdout.strip() else done.stderr


class AuthorTest(Base):
    """Task 1: the author record (AC4 second half)."""

    def test_needs_a_session_id(self):
        done = run(self.root, "author", "--module", "a")
        self.assertEqual(done.returncode, 2)
        self.assertIn("no-session-id", done.stdout + done.stderr)

    def test_one_entry_per_session(self):
        import verification
        for session in ("author-1", "author-1", "author-2"):
            self.assertEqual(self.author(session).returncode, 0)
        self.assertEqual([a["sessionId"] for a in verification.authors(self.root, "a")], ["author-1", "author-2"])
        self.assertEqual(git(self.root, "status", "--porcelain"), "")  # never in the work tree

    def test_codex_thread(self):
        import verification
        self.assertEqual(run(self.root, "author", "--module", "a", codex="thread-9").returncode, 0)
        self.assertEqual(verification.authors(self.root, "a")[0]["host"], "codex")

    def test_old_flow_module_refused(self):
        self.repo.write("spec/a.md", "# a\n")
        self.assertEqual(self.author().returncode, 2)


class PatchIdTest(Base):
    """Task 1: the current patch (AC5 first half)."""

    def test_changes_with_a_commit_and_survives_a_rebase(self):
        import verification
        first = verification.current_patch_id(self.root)
        self.assertEqual(first, patch_id(self.root, self.repo.base, self.repo.head))
        git(self.root, "switch", "-q", "main")
        self.repo.write("docs/other.md", "unrelated\n")
        commit(self.root, "main moves on")
        git(self.root, "switch", "-q", "feature")
        git(self.root, "-c", "user.name=t", "-c", "user.email=t@t", "rebase", "-q", "main")
        self.assertEqual(verification.current_patch_id(self.root), first)
        self.repo.write("src/y.py", "y = 1\n")
        commit(self.root, "more")
        self.assertNotEqual(verification.current_patch_id(self.root), first)


class CheckTest(Base):
    """Task 2: the report check (AC1-AC5)."""

    def setUp(self):
        super().setUp()
        self.author()

    def test_good_report_is_established(self):
        code, out = self.check(self.repo.report())
        self.assertEqual((code, out["established"], out["verdict"], out["problems"]), (0, True, "pass-with-notes", []))
        self.assertEqual(out["patchId"], patch_id(self.root, self.repo.base, self.repo.head))

    def codes(self, **change):
        code, out = self.check(self.repo.report(**change))
        return code, [p["code"] for p in out["problems"]]

    def cases(self, edit):
        cases = json.loads(self.repo.report().read_text())["cases"]
        edit(cases)
        return cases

    def test_each_problem(self):
        def drop_r3(cases):
            del cases[2]

        def extra(cases):
            cases.append(dict(cases[0], id="R9"))

        def method(cases):
            cases[0]["method"] = "command"

        def manual(cases):
            cases[1]["evidence"] = [dict(cases[1]["evidence"][0], type="log")]

        def fail_no_category(cases):
            cases[0].update(result="fail")

        def fail_no_evidence(cases):
            cases[0].update(result="fail", failCategory="run-failure", evidence=[])

        def baseline(cases):
            cases[2]["baselineCommit"] = None

        def sha(cases):
            cases[0]["evidence"][0]["sha256"] = "0" * 64

        for code, change in (("report-invalid", {"schema": "other/v1"}),
                             ("regression-changed", {"regression": {"document": "tasks/a/regression.md", "sha256": "0" * 64}}),
                             ("case-missing", {"cases": self.cases(drop_r3)}),
                             ("case-unknown", {"cases": self.cases(extra)}),
                             ("method-mismatch", {"cases": self.cases(method)}),
                             ("manual-without-user", {"cases": self.cases(manual)}),
                             ("fail-category-missing", {"cases": self.cases(fail_no_category), "verdict": "fail"}),
                             ("fail-evidence-missing", {"cases": self.cases(fail_no_evidence), "verdict": "fail"}),
                             ("baseline-evidence-missing", {"cases": self.cases(baseline)}),
                             ("evidence-sha-mismatch", {"cases": self.cases(sha)}),
                             ("patch-mismatch", {"patchId": "0" * 40}),
                             ("executor-is-author", {"executor": {"sessionId": "author-1", "host": "claude-code",
                                                                  "vendor": "anthropic", "sameVendorAsAuthor": True}})):
            with self.subTest(code=code):
                exit_code, codes = self.codes(**change)
                self.assertEqual(exit_code, 1)
                self.assertIn(code, codes)

    def test_verdict_must_follow_the_cases(self):
        self.assertIn("verdict-inconsistent", self.codes(verdict="pass")[1])  # there is a note
        failing = self.cases(lambda c: c[0].update(result="fail", failCategory="run-failure"))
        self.assertIn("verdict-inconsistent", self.codes(cases=failing, verdict="pass-with-notes")[1])
        self.assertEqual(self.codes(cases=failing, verdict="fail"), (0, []))
        self.assertEqual(self.codes(notes=[], verdict="pass"), (0, []))

    def test_patch_id_wrong_and_unreadable_head(self):
        git(self.root, "switch", "-q", "-c", "other", self.repo.base)
        self.repo.write("src/z.py", "z = 1\n")
        other = commit(self.root, "a different change")
        git(self.root, "switch", "-q", "feature")
        _code, out = self.check(self.repo.report(head=other))
        self.assertIn("patch-id-wrong", [p["code"] for p in out["problems"]])
        code, out = self.check(self.repo.report(head="f" * 40))
        self.assertEqual((code, out["problems"]), (0, []))
        self.assertIn("patch-id", " ".join(out["unverified"]))

    def test_rebase_keeps_it_and_a_doc_edit_breaks_it(self):
        report = self.repo.report()
        git(self.root, "switch", "-q", "main")
        self.repo.write("docs/other.md", "unrelated\n")
        commit(self.root, "main moves on")
        git(self.root, "switch", "-q", "feature")
        git(self.root, "-c", "user.name=t", "-c", "user.email=t@t", "rebase", "-q", "main")
        self.assertEqual(self.check(report)[0], 0)
        self.repo.write("tasks/a/regression.md", TWO_CASES.replace("saved", "saved!"))
        commit(self.root, "doc")
        self.assertIn("regression-changed", [p["code"] for p in self.check(report)[1]["problems"]])

    def test_missing_evidence_file_is_unverified_only(self):
        cases = self.cases(lambda c: c[0]["evidence"][0].update(path="/nonexistent/log.txt"))
        code, out = self.check(self.repo.report(cases=cases))
        self.assertEqual((code, out["problems"]), (0, []))
        self.assertTrue(out["unverified"])


class NoAuthorTest(Base):
    def test_without_an_author_record_it_cannot_judge(self):
        code, out = self.check(self.repo.report())
        self.assertEqual(code, 3)
        self.assertIn("author-unknown", [p["code"] for p in out["problems"]])


class RecordTest(Base):
    """Task 3: record and read back (AC6, AC9 half)."""

    def setUp(self):
        super().setUp()
        self.author()

    def test_preview_writes_nothing_and_confirm_writes_outside_the_tree(self):
        import verification
        report = self.repo.report()
        self.assertEqual(run(self.root, "record", "--module", "a", "--report", str(report)).returncode, 0)
        self.assertIsNone(verification.verification_state(self.root, "a"))
        self.assertEqual(run(self.root, "record", "--module", "a", "--report", str(report), "--confirm").returncode, 0)
        state = verification.verification_state(self.root, "a")
        self.assertEqual((state["verdict"], state["current"], state["notes"]), ("pass-with-notes", True, ["naming"]))
        self.assertEqual(state["reportSha256"], hashlib.sha256(report.read_bytes()).hexdigest())
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.repo.write("src/y.py", "y = 1\n")
        commit(self.root, "more")
        self.assertFalse(verification.verification_state(self.root, "a")["current"])

    def test_refuses_an_unestablished_report(self):
        import verification
        done = run(self.root, "record", "--module", "a", "--report", str(self.repo.report(patchId="0" * 40)), "--confirm")
        self.assertEqual(done.returncode, 1)
        self.assertIsNone(verification.verification_state(self.root, "a"))


class UsageTest(unittest.TestCase):
    """Task 3, Q2 A: the integration regression of a multi-module requirement."""

    def setUp(self):
        self.repo = Repo(("a", "b"))
        self.addCleanup(self.repo.close)
        self.root = self.repo.root
        self.repo.write("spec/usage/demo.md", "# Usage draft: demo\n\n## 成功标准\n\n- **S2** y\n")
        self.repo.write("spec/usage/demo.regression.md", USAGE_REGRESSION)
        commit(self.root, "usage")
        self.repo.head = git(self.root, "rev-parse", "HEAD")

    def report(self, executor="verifier-1"):
        doc = self.root / "spec" / "usage" / "demo.regression.md"
        path = self.repo.report(module=None, usage="demo", notes=[], verdict="pass",
                                regression={"document": "spec/usage/demo.regression.md",
                                            "sha256": hashlib.sha256(doc.read_bytes()).hexdigest()},
                                patchId=patch_id(self.root, self.repo.base, self.repo.head),
                                executor={"sessionId": executor, "host": "codex", "vendor": "openai",
                                          "sameVendorAsAuthor": False},
                                cases=[{"id": "R1", "method": "script", "result": "pass", "failCategory": None,
                                        "baselineCommit": None, "evidence": [self.repo.evidence()]}])
        return path

    def test_authors_are_the_union_and_record_works(self):
        import verification
        run(self.root, "author", "--module", "a", session="author-a")
        done = run(self.root, "check", "--usage", "demo", "--report", str(self.report()), "--json")
        self.assertEqual(done.returncode, 3)  # module b has no author record yet
        run(self.root, "author", "--module", "b", session="author-b")
        self.assertEqual(run(self.root, "check", "--usage", "demo", "--report", str(self.report("author-b")),
                             "--json").returncode, 1)
        self.assertEqual(run(self.root, "record", "--usage", "demo", "--report", str(self.report()), "--confirm").returncode, 0)
        self.assertEqual(verification.verification_state(self.root, usage="demo")["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
