"""Delivery reminders report declared facts without pretending to verify content."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import documentation_verification
from documentation_verification import VerificationError, _as_json, verify_documentation


GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_ENV)
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True, env=env).stdout


BASELINE = """| Concern | Authority | Status | Rationale |
|---|---|---|---|
| product-direction | `docs/product.md` | verified | Product scope. |
| architecture | `docs/architecture.md` | target | Target architecture. |
| developer-entry | `README.md` | verified | Development entry. |
"""

SPEC = """# Spec: alpha

## Documentation impact

| Concern | Decision | Rationale |
|---|---|---|
| product-direction | follow | Existing scope applies. |
| architecture | update | Boundary changed. |
| developer-entry | follow | Commands remain valid. |
"""

PLAN = """# Plan: alpha

## Documentation delivery

| Concern | Planned artifact | Rationale |
|---|---|---|
| architecture | `docs/architecture.md` | Describe the boundary. |
"""


class DocumentationVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-doc-verify-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def project(self, outcome=""):
        self.write("docs/DOCUMENTATION-BASELINE.md", BASELINE)
        self.write("spec/alpha.md", SPEC)
        self.write("tasks/alpha/plan.md", PLAN + outcome)

    def committed_then_changed(self):
        """doc-chain: a `delivered` update is only ready once git shows the document changed after the Spec landed."""
        git(self.root, "init", "-q")
        self.write("docs/architecture.md", "goal\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "spec")
        self.write("docs/architecture.md", "goal\nadded\n")

    def created(self, artifact):
        """review-residual-fixes (C2): a `create` decision whose delivered outcome only names a planned artifact."""
        self.write("docs/DOCUMENTATION-BASELINE.md", BASELINE)
        self.write("spec/alpha.md", SPEC.replace("| developer-entry | follow |", "| developer-entry | create |"))
        self.write("tasks/alpha/plan.md", PLAN + """| developer-entry | `%s` | New guide. |

## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | deferred | — | Later. |
| developer-entry | delivered | `%s` | Guide written. |
""" % (artifact, artifact))

    def test_created_document_present_is_ready_for_it(self):
        self.created("docs/guide.md#start")
        self.write("docs/guide.md", "guide\n")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["developer-entry"].check, "present")
        self.assertFalse([item for item in result.attention if "developer-entry" in item])

    def test_created_document_missing_is_attention(self):
        self.created("docs/guide.md")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.state, "attention")
        self.assertEqual(result.outcomes["developer-entry"].check, "missing")
        self.assertTrue([item for item in result.attention if "docs/guide.md" in item and "does not exist" in item])

    def test_created_document_must_be_a_regular_file_in_the_project(self):
        self.created("docs/guide.md")
        (self.root / "docs" / "guide.md").mkdir(parents=True)
        self.assertEqual(verify_documentation(self.root, "alpha").outcomes["developer-entry"].check, "missing")
        (self.root / "docs" / "guide.md").rmdir()
        outside = tempfile.TemporaryDirectory(prefix="sg-doc-outside-")
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "guide.md").write_text("x\n", encoding="utf-8")
        os.symlink(Path(outside.name) / "guide.md", self.root / "docs" / "guide.md")
        self.assertEqual(verify_documentation(self.root, "alpha").outcomes["developer-entry"].check, "missing")
        self.created("../outside.md")
        self.assertEqual(verify_documentation(self.root, "alpha").outcomes["developer-entry"].check, "missing")

    def test_created_external_document_is_unverified(self):
        self.created("https://wiki.example.com/guide")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["developer-entry"].check, "unverified")
        self.assertFalse([item for item in result.attention if "developer-entry" in item])

    def test_absent_baseline_is_quiet(self):
        self.write("spec/alpha.md", SPEC)
        self.write("tasks/alpha/plan.md", PLAN)
        self.assertEqual(verify_documentation(self.root, "alpha").state, "absent")

    def test_missing_outcome_is_attention_not_invalid(self):
        self.project()
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.state, "attention")
        self.assertIn("architecture", result.attention[0])

    def test_delivered_outcome_with_evidence_is_ready(self):
        self.project("""
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | delivered | `docs/architecture.md#alpha` | Boundary added. |
""")
        self.committed_then_changed()
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.state, "ready")
        self.assertEqual(result.outcomes["architecture"].outcome, "delivered")

    def test_deferred_outcome_remains_attention(self):
        self.project("""
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | deferred | — | Waiting for architecture review. |
""")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.state, "attention")
        self.assertIn("deferred", result.attention[0])

    def test_delivered_without_evidence_and_unknown_outcome_are_invalid(self):
        self.project("""
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | delivered | — | Boundary added. |
""")
        with self.assertRaisesRegex(VerificationError, "evidence"):
            verify_documentation(self.root, "alpha")
        self.project("""
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | published | `docs/architecture.md` | Boundary added. |
""")
        with self.assertRaisesRegex(VerificationError, "unknown outcome"):
            verify_documentation(self.root, "alpha")

    def test_pending_decision_is_attention_even_without_a_delivery_outcome(self):
        self.project()
        self.write("spec/alpha.md", SPEC.replace("| architecture | update |", "| architecture | pending |"))
        self.write("tasks/alpha/plan.md", "# Plan: alpha\n")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.state, "attention")
        self.assertIn("pending", result.attention[0])

    def test_fenced_example_outcome_table_is_ignored(self):
        self.project("""
## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | delivered | `docs/architecture.md#alpha` | Boundary added. |

```markdown
| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| architecture | pending | — | Example only. |
```
""")
        self.committed_then_changed()
        self.assertEqual(verify_documentation(self.root, "alpha").state, "ready")


CHAIN_BASELINE = """| Concern | Authority | Status | Rationale |
|---|---|---|---|
| product-direction | `docs/product.md#scope` | verified | Current product scope. |
| architecture | `docs/architecture.md` | target | Approved target, not fully built. |
| developer-entry | `README.md` | in-progress | Development entry. |
| integration-contract | https://example.com/api | verified | External API reference. |
"""

CHAIN_SPEC = """# Spec: alpha

## Documentation impact

| Concern | Decision | Rationale |
|---|---|---|
| product-direction | update | Scope grows. |
| architecture | update | Mark the implemented part. |
| developer-entry | update | New command. |
| integration-contract | update | New endpoint. |
"""

CHAIN_PLAN = """# Plan: alpha

## Documentation delivery

| Concern | Planned artifact | Rationale |
|---|---|---|
| product-direction | `docs/product.md#scope` | Scope. |
| architecture | `docs/architecture.md` | Implemented part. |
| developer-entry | `README.md` | Command. |
| integration-contract | https://example.com/api | Endpoint. |

## Documentation outcome

| Concern | Outcome | Evidence | Rationale |
|---|---|---|---|
| product-direction | %s | %s | Scope. |
| architecture | delivered | `docs/architecture.md` | Implemented part. |
| developer-entry | delivered | `README.md` | Command. |
| integration-contract | delivered | https://example.com/api/v2 | Endpoint. |
"""


class StatusAwareVerificationTests(unittest.TestCase):
    """doc-chain (D15): the check depends on the baseline status of each updated document."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-doc-chain-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def project(self, product="delivered", evidence="`docs/product.md#scope`", commit_spec=True):
        git(self.root, "init", "-q")
        self.write("docs/DOCUMENTATION-BASELINE.md", CHAIN_BASELINE)
        self.write("docs/product.md", "scope\n")
        self.write("docs/architecture.md", "goal one\ngoal two\n")
        self.write("README.md", "readme\n")
        self.write("tasks/alpha/plan.md", CHAIN_PLAN % (product, evidence))
        if commit_spec:
            self.write("spec/alpha.md", CHAIN_SPEC)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        if not commit_spec:
            self.write("spec/alpha.md", CHAIN_SPEC)

    def commit(self, message="change"):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", message)

    def test_current_state_update_left_unchanged_is_attention(self):
        self.project()
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "unchanged")
        self.assertEqual(result.outcomes["developer-entry"].check, "unchanged")
        self.assertEqual(result.state, "attention")
        self.assertTrue(any("docs/product.md" in item and "no change" in item for item in result.attention))

    def test_committed_and_uncommitted_changes_both_count(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        self.commit()
        self.write("README.md", "readme\nnew command\n")  # working tree only
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "changed")
        self.assertEqual(result.outcomes["developer-entry"].check, "changed")
        self.assertEqual(result.state, "ready")

    def test_target_document_need_not_change(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        self.write("README.md", "readme\nnew\n")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["architecture"].check, "target-unchanged")
        self.assertEqual(result.state, "ready")

    def test_target_additions_are_listed_without_attention(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        self.write("README.md", "readme\nnew\n")
        self.write("docs/architecture.md", "goal one\ngoal two\nimplemented: goal one\n")
        result = verify_documentation(self.root, "alpha")
        item = result.outcomes["architecture"]
        self.assertEqual((item.check, item.added, item.removed), ("target-changed", 1, 0))
        self.assertEqual(result.state, "ready")

    def test_target_deletion_is_attention(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        self.write("README.md", "readme\nnew\n")
        self.write("docs/architecture.md", "goal one\n")
        result = verify_documentation(self.root, "alpha")
        item = result.outcomes["architecture"]
        self.assertEqual((item.check, item.added, item.removed), ("target-changed", 0, 1))
        self.assertEqual(result.state, "attention")
        self.assertTrue(any("target" in a and "docs/architecture.md" in a and "approval" in a
                            for a in result.attention))

    def test_external_document_is_unverified_without_git(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        self.write("README.md", "readme\nnew\n")
        with mock.patch.object(documentation_verification.subprocess, "run",
                               wraps=documentation_verification.subprocess.run) as run:
            result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["integration-contract"].check, "unverified")
        self.assertFalse(any("example.com" in " ".join(map(str, call.args[0])) for call in run.call_args_list))
        self.assertEqual(result.state, "ready")

    def test_anchor_is_dropped_before_comparing(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "changed")

    def test_earliest_spec_commit_is_the_base(self):
        self.project()
        self.write("docs/product.md", "scope\nmore\n")
        self.commit("doc change")
        (self.root / "spec" / "alpha.md").unlink()
        self.commit("drop spec")
        self.write("spec/alpha.md", CHAIN_SPEC)
        self.commit("re-add spec")
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "changed")

    def test_uncommitted_spec_is_unknown(self):
        self.project(commit_spec=False)
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "unknown")
        self.assertEqual(result.state, "attention")
        self.assertTrue(any("cannot tell" in a and "not committed" in a for a in result.attention))

    def test_outside_git_is_unknown(self):
        self.write("docs/DOCUMENTATION-BASELINE.md", CHAIN_BASELINE)
        self.write("spec/alpha.md", CHAIN_SPEC)
        self.write("tasks/alpha/plan.md", CHAIN_PLAN % ("delivered", "`docs/product.md#scope`"))
        result = verify_documentation(self.root, "alpha")
        for concern in ("product-direction", "architecture", "developer-entry"):
            self.assertEqual(result.outcomes[concern].check, "unknown")
        self.assertEqual(result.outcomes["integration-contract"].check, "unverified")
        self.assertEqual(result.state, "attention")

    def test_git_failures_are_unknown_not_unchanged(self):
        self.project()
        with mock.patch.object(documentation_verification.subprocess, "run", side_effect=FileNotFoundError("git")):
            result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "unknown")
        failed = subprocess.CompletedProcess([], 128, "", "fatal: boom")
        with mock.patch.object(documentation_verification.subprocess, "run", return_value=failed):
            result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["product-direction"].check, "unknown")
        self.assertTrue(any("cannot tell" in a for a in result.attention))

    def test_deferred_and_pending_are_not_checked(self):
        for outcome in ("deferred", "pending"):
            with self.subTest(outcome=outcome):
                self._fresh_root()
                self.project(product=outcome, evidence="—")
                result = verify_documentation(self.root, "alpha")
                self.assertEqual(result.outcomes["product-direction"].check, "not-checked")
                self.assertIn("product-direction is declared %s" % outcome, result.attention)

    def _fresh_root(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-doc-chain-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_create_only_checks_existence(self):
        self.project()
        self.write("spec/alpha.md", CHAIN_SPEC.replace("| developer-entry | update |", "| developer-entry | create |"))
        self.write("tasks/alpha/plan.md", (CHAIN_PLAN % ("delivered", "`docs/product.md#scope`"))
                   .replace("| developer-entry | `README.md` | Command. |", "| developer-entry | `docs/dev.md` | Command. |"))
        self.commit()
        result = verify_documentation(self.root, "alpha")
        self.assertEqual(result.outcomes["developer-entry"].check, "missing")  # review-residual-fixes (C2)
        self.write("docs/dev.md", "dev\n")
        self.assertEqual(verify_documentation(self.root, "alpha").outcomes["developer-entry"].check, "present")

    def test_json_carries_check_and_line_counts(self):
        self.project()
        self.write("docs/architecture.md", "goal one\nimplemented\n")
        data = _as_json(verify_documentation(self.root, "alpha"))
        self.assertEqual(data["outcomes"]["architecture"]["check"], "target-changed")
        self.assertEqual((data["outcomes"]["architecture"]["added"], data["outcomes"]["architecture"]["removed"]), (1, 1))
        self.assertEqual(data["outcomes"]["product-direction"]["check"], "unchanged")
        self.assertIsNone(data["outcomes"]["product-direction"]["added"])
        self.assertEqual(data["outcomes"]["integration-contract"]["check"], "unverified")


if __name__ == "__main__":
    unittest.main()
