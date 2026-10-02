"""Hosted daily Issue instructions are discoverable without reviving the bridge."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HostedEntryTests(unittest.TestCase):
    def test_both_hosts_route_explicit_hosted_target_to_new_skill(self):
        command = (ROOT / "commands/ticket.md").read_text(encoding="utf-8")
        checkpoint = (ROOT / "references/workflow-checkpoints.md").read_text(encoding="utf-8")
        for name in ("claude-block-local.md", "codex-block-local.md"):
            text = (ROOT / "templates" / name).read_text(encoding="utf-8")
            self.assertIn("hosted-ticket-workflow", text)
        self.assertIn("hosted-ticket-workflow", command)
        self.assertIn("hosted-ticket-workflow", checkpoint)
        self.assertNotIn("只整理经查重的可审阅交接清单", checkpoint)

    def test_skill_keeps_read_only_review_and_explicit_write_boundaries(self):
        text = (ROOT / "skills/hosted-ticket-workflow/SKILL.md").read_text(
            encoding="utf-8")
        for phrase in ("Local", "GitHub", "GitLab", "rootCauseReviewRequired",
                       "hosted_ticket_read.py", "hosted_ticket.py",
                       "hosted_ticket_action.py", "--expected-digest",
                       "--confirm", "结果未知", "逐项", "读回", "授权"):
            self.assertIn(phrase, text)
        self.assertIn("不凭 Git remote", text)
        self.assertIn("Proposal Issue", text)

    def test_workflow_distinguishes_semantic_review_from_exact_marker_lookup(self):
        text = (ROOT.parents[1] / "docs/workflow.md").read_text(encoding="utf-8")
        self.assertIn("rootCauseReviewRequired", text)
        self.assertIn("托管日常事项", text)
        self.assertIn("不自动重发", text)
        self.assertIn("CI／验收", text)


if __name__ == "__main__":
    unittest.main()
