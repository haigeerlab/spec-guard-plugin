"""proposal_submit completes a draft from a temporary bare remote; no network is used."""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from proposal_contract import V2_MARKER, compute_revision, parse_proposal
from proposal_publication import read_published, read_published_pool


HOOKS = Path(__file__).parent
SCRIPT = HOOKS / "proposal_submit.py"
_digest_spec = importlib.util.spec_from_file_location("submit_digest", HOOKS / "spec-digest.py")
_digest = importlib.util.module_from_spec(_digest_spec)
_digest_spec.loader.exec_module(_digest)

MAP = """# Capability Map: test

## 目标

Test remote facts.

## 模块

| Module id | Responsibility | Depends on |
| --- | --- | --- |
| alpha | First | — |
| beta | Second | alpha |

Build order: alpha → beta
"""

INTENT = """## Integration intent

| Field | Value |
| --- | --- |
| Problem | P. |
| In scope | S. |
| Out of scope | O. |
| Safety boundaries | B. |
| Initial dependency assumptions | D. |
| Acceptance intent | A. |

"""

STALE_BASELINE = """## Capability map baseline

| Field | Value |
| --- | --- |
| Remote | nowhere |
| Default branch | old |
| Commit | %s |
| Capability map | spec/CAPABILITY-MAP.md |
| Goal digest | 000000000000 |
| Build order | stale |

### Module digests

| Module id | Row digest |
| --- | --- |
| stale | 000000000000 |

""" % ("1" * 40)


def draft_text(proposal_id="gamma", module_id="gamma", depends="alpha", anchor="after:alpha",
               baseline="", intent=INTENT, revision="0" * 64, summary="Gamma is separate."):
    return """# Proposal: Add %(id)s
<!-- spec-guard-proposal:v2 id=%(id)s revision=sha256:%(revision)s -->

## Summary

%(summary)s

%(intent)s%(baseline)s## Change

| Field | Value |
| --- | --- |
| Type | new-module |
| Module id | %(module)s |
| Responsibility | Gamma. |
| Depends on | %(depends)s |
| Build-order anchor | %(anchor)s |

## Tracker contract

| Field | Value |
| --- | --- |
| Proposal id | %(id)s |
| Identity label | proposal |
| Stage label namespace | proposal-stage: |
""" % {"id": proposal_id, "module": module_id, "depends": depends, "anchor": anchor,
       "baseline": baseline, "intent": intent, "revision": revision, "summary": summary}


def outside_baseline(text):
    """Text with the baseline section removed and the marker revision blanked."""
    text = re.sub(r"## Capability map baseline\n.*?(?=\n## )\n", "", text, flags=re.S)
    return re.sub(r"revision=sha256:[0-9a-f]{64}", "revision=sha256:X", text)


class ProposalSubmitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-proposal-submit-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.seed = self.root / "seed"
        self.remote = self.root / "remote.git"
        self.consumer = self.root / "consumer"
        self.git(self.root, "init", "--bare", "-b", "trunk", str(self.remote))
        self.git(self.root, "init", "-b", "trunk", str(self.seed))
        self.git(self.seed, "config", "user.email", "test@example.invalid")
        self.git(self.seed, "config", "user.name", "test")
        (self.seed / "spec").mkdir()
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(MAP, encoding="utf-8")
        self.git(self.seed, "add", "spec/CAPABILITY-MAP.md")
        self.git(self.seed, "commit", "-m", "baseline")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "trunk")
        self.git(self.root, "clone", str(self.remote), str(self.consumer))
        self.git(self.consumer, "config", "user.email", "test@example.invalid")
        self.git(self.consumer, "config", "user.name", "test")
        self.map_path = self.seed / "spec/CAPABILITY-MAP.md"

    def git(self, cwd, *args):
        result = subprocess.run(["git", "-C", str(cwd)] + list(args), text=True,
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def tip(self):
        return self.git(self.remote, "rev-parse", "trunk").strip()

    def write_draft(self, text, name="gamma"):
        path = self.consumer / "spec/proposals" / ("%s.md" % name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_submit(self, draft="spec/proposals/gamma.md", platform="github", confirm=False,
                   remote="origin"):
        args = [sys.executable, "-B", str(SCRIPT), "--project", str(self.consumer),
                "--draft", draft, "--remote", remote, "--platform", platform]
        if confirm:
            args.append("--confirm")
        result = subprocess.run(args, text=True, capture_output=True, timeout=60,
                                stdin=subprocess.DEVNULL)
        return result.returncode, result.stdout, result.stderr

    def assert_rejected(self, text, name="gamma", draft=None, **kwargs):
        path = self.write_draft(text, name)
        before = path.read_bytes()
        files = self.git(self.consumer, "status", "--short", "-uall")
        code, out, err = self.run_submit(draft or "spec/proposals/%s.md" % name, **kwargs)
        self.assertNotEqual(code, 0, out)
        self.assertIn("rejected", err)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.git(self.consumer, "status", "--short", "-uall"), files)
        return err

    def test_preview_completes_draft_without_writing(self):
        draft = self.write_draft(draft_text())
        before = draft.read_text(encoding="utf-8")
        code, out, err = self.run_submit()
        self.assertEqual(code, 0, err)
        self.assertEqual(draft.read_text(encoding="utf-8"), before)
        self.assertIn("no file written", out)
        # Reconstruct the final text from a confirmed run on a copy of the fixture state.
        code, _, err = self.run_submit(confirm=True)
        self.assertEqual(code, 0, err)
        final = draft.read_text(encoding="utf-8")
        proposal = parse_proposal(draft)
        digest = _digest.compute(str(self.map_path))
        self.assertEqual(proposal.baseline.commit, self.tip())
        self.assertEqual(proposal.baseline.remote, "origin")
        self.assertEqual(proposal.baseline.default_branch, "trunk")
        self.assertEqual(proposal.baseline.goal_digest, digest["goalDigest"])
        self.assertEqual(proposal.baseline.module_digests,
                         dict((r["id"], r["rowDigest"]) for r in digest["rows"]))
        self.assertEqual(proposal.baseline.build_order, "alpha → beta")
        self.assertEqual(proposal.revision, compute_revision(draft))
        self.assertIn("Revision: sha256:%s" % proposal.revision,
                      self.run_submit()[1])
        self.assertTrue(final.endswith("\n"))

    def test_preview_prints_revision_diff_and_issue_command_per_platform(self):
        self.write_draft(draft_text())
        code, out, err = self.run_submit(platform="github")
        self.assertEqual(code, 0, err)
        self.assertIn("+## Capability map baseline", out)
        self.assertIn("Revision: sha256:", out)
        self.assertIn("Revision of a published Proposal: no", out)
        self.assertIn("gh issue create --title 'Proposal: Add gamma'", out)
        self.assertIn("--label proposal --label proposal-stage:published", out)
        self.assertIn("gh label create proposal", out)
        self.assertIn("/spec-guard:proposal-review", out)
        self.assertIn("proposal-stage:accepted", out)
        code, out, err = self.run_submit(platform="gitlab")
        self.assertEqual(code, 0, err)
        self.assertIn("glab issue create --title 'Proposal: Add gamma'", out)
        self.assertIn("--label proposal,proposal-stage:published", out)
        self.assertIn("glab label create --name proposal", out)
        self.assertNotIn("gh issue create", out)
        marker = re.search(r"<!-- spec-guard-proposal:v2 [^>]+-->", out).group(0)
        self.assertTrue(V2_MARKER.fullmatch(marker))
        self.assertIn("Gamma is separate.", out)

    def test_stale_baseline_section_is_replaced_and_rest_is_verbatim(self):
        original = draft_text(baseline=STALE_BASELINE)
        draft = self.write_draft(original)
        code, _, err = self.run_submit(confirm=True)
        self.assertEqual(code, 0, err)
        final = draft.read_text(encoding="utf-8")
        self.assertNotIn("nowhere", final)
        self.assertEqual(final.count("## Capability map baseline"), 1)
        self.assertEqual(outside_baseline(final), outside_baseline(original))
        parse_proposal(draft)

    def test_confirm_writes_only_the_draft_and_is_idempotent(self):
        draft = self.write_draft(draft_text())
        code, preview, err = self.run_submit()
        self.assertEqual(code, 0, err)
        code, out, err = self.run_submit(confirm=True)
        self.assertEqual(code, 0, err)
        self.assertIn("Wrote spec/proposals/gamma.md", out)
        self.assertEqual(self.git(self.consumer, "status", "--short", "-uall").strip(),
                         "?? spec/proposals/gamma.md")
        self.assertEqual([p.name for p in draft.parent.iterdir()], ["gamma.md"])
        # The diff printed by the preview is exactly the change --confirm applied.
        final = draft.read_text(encoding="utf-8")
        added = [line[1:] for line in preview.splitlines()
                 if line.startswith("+") and not line.startswith("+++")]
        for line in added:
            self.assertIn(line, final.splitlines())
        code, again, err = self.run_submit()
        self.assertEqual(code, 0, err)
        self.assertIn("no changes", again)
        self.assertEqual(draft.read_text(encoding="utf-8"), final)

    def test_confirm_preserves_file_mode(self):
        draft = self.write_draft(draft_text())
        os.chmod(str(draft), 0o600)
        code, _, err = self.run_submit(confirm=True)
        self.assertEqual(code, 0, err)
        self.assertEqual(draft.stat().st_mode & 0o777, 0o600)

    def publish(self, text):
        target = self.seed / "spec/proposals/gamma.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/gamma.md")
        self.git(self.seed, "commit", "-m", "publish gamma")
        self.git(self.seed, "push", "origin", "trunk")

    def test_end_to_end_confirm_commit_push_is_published(self):
        draft = self.write_draft(draft_text())
        code, _, err = self.run_submit(confirm=True)
        self.assertEqual(code, 0, err)
        self.git(self.consumer, "add", "spec/proposals/gamma.md")
        self.git(self.consumer, "commit", "-m", "publish gamma")
        self.git(self.consumer, "push", "origin", "trunk")
        self.assertEqual(read_published(self.consumer, "gamma").state, "published")
        pool = read_published_pool(self.consumer)
        self.assertEqual(pool.state, "published")
        self.assertEqual([p.proposal.proposal_id for p in pool.publications], ["gamma"])
        self.assertEqual(draft.read_text(encoding="utf-8"),
                         self.git(self.remote, "show", "trunk:spec/proposals/gamma.md"))

    def test_same_path_already_published_is_a_revision(self):
        self.write_draft(draft_text())
        self.assertEqual(self.run_submit(confirm=True)[0], 0)
        self.git(self.consumer, "add", "spec/proposals/gamma.md")
        self.git(self.consumer, "commit", "-m", "publish gamma")
        self.git(self.consumer, "push", "origin", "trunk")
        old = parse_proposal(self.consumer / "spec/proposals/gamma.md").revision
        self.write_draft(draft_text(summary="Gamma is separate, revised."))
        code, out, err = self.run_submit()
        self.assertEqual(code, 0, err)
        self.assertIn("Revision of a published Proposal: yes", out)
        self.assertIn("update the marker line in the existing Issue", out)
        self.assertNotIn("gh issue create", out)
        self.assertNotIn(old, out.split("Revision: ")[1].split("\n")[0])

    def test_rejections_write_nothing(self):
        cases = (
            ("no marker", draft_text().replace(
                "<!-- spec-guard-proposal:v2 id=gamma revision=sha256:%s -->\n" % ("0" * 64), ""),
             "exactly one"),
            ("two markers", draft_text().replace(
                "\n## Summary", "\n<!-- spec-guard-proposal:v2 id=gamma revision=sha256:%s -->\n\n"
                "## Summary" % ("0" * 64)), "exactly one"),
            ("missing integration intent", draft_text(intent=""), "sections"),
            ("module already in map", draft_text(module_id="beta"), "already exists"),
            ("unknown dependency", draft_text(depends="nope"), "absent from the baseline"),
            ("unknown anchor", draft_text(anchor="after:nope"), "anchor is absent"),
            ("anchor before dependency", draft_text(depends="beta", anchor="after:alpha"),
             "must not precede"),
        )
        for label, text, needle in cases:
            with self.subTest(label):
                self.assertIn(needle, self.assert_rejected(text))

    def test_path_and_id_mismatch_is_rejected(self):
        err = self.assert_rejected(draft_text(proposal_id="delta", module_id="delta"),
                                   name="gamma")
        self.assertIn("draft path must be spec/proposals/delta.md", err)

    def test_missing_draft_is_rejected(self):
        code, out, err = self.run_submit(draft="spec/proposals/absent.md")
        self.assertNotEqual(code, 0)
        self.assertIn("rejected", err)

    def test_other_remote_file_declaring_the_same_id_is_rejected(self):
        self.write_draft(draft_text())
        self.assertEqual(self.run_submit(confirm=True)[0], 0)
        shipped = (self.consumer / "spec/proposals/gamma.md").read_text(encoding="utf-8")
        (self.seed / "spec/proposals").mkdir()
        (self.seed / "spec/proposals/duplicate.md").write_text(shipped, encoding="utf-8")
        self.git(self.seed, "add", "spec/proposals/duplicate.md")
        self.git(self.seed, "commit", "-m", "another file with the same id")
        self.git(self.seed, "push", "origin", "trunk")
        (self.consumer / "spec/proposals/gamma.md").write_text(draft_text(), encoding="utf-8")
        err = self.assert_rejected(draft_text())
        self.assertIn("another remote file", err)
        self.assertIn("spec/proposals/duplicate.md", err)

    def test_remote_map_without_a_goal_section_is_rejected_clearly(self):
        (self.seed / "spec/CAPABILITY-MAP.md").write_text(
            MAP.replace("## 目标\n\nTest remote facts.\n\n", ""), encoding="utf-8")
        self.git(self.seed, "commit", "-am", "drop the goal section")
        self.git(self.seed, "push", "origin", "trunk")
        err = self.assert_rejected(draft_text(), confirm=True)
        self.assertIn("## 目标", err)

    def test_unreachable_remote_is_rejected_without_writing(self):
        os.rename(str(self.remote), str(self.root / "gone.git"))
        err = self.assert_rejected(draft_text(), confirm=True)
        self.assertIn("remote default branch is unavailable", err)


if __name__ == "__main__":
    unittest.main()
