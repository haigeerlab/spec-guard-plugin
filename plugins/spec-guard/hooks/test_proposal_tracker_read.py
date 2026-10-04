"""Fixture contract for read-only Proposal tracker recovery; no live service."""
import json
import unittest

from proposal_contract import Baseline, Change, Proposal
from proposal_tracker_read import TrackerRead, as_json, read_tracker, recover_tracker_issue


MARKER = "<!-- spec-guard-proposal:v1 id=gamma -->"


def proposal():
    return Proposal("gamma", MARKER,
                    Baseline("origin", "trunk", "0" * 40, "0" * 12, {}, "alpha"),
                    Change("gamma", "Gamma.", ("alpha",), "after:alpha"))


def github_issue(number=42, body=None, labels=None, repository=None,
                 title="Proposal: gamma", state="open"):
    return {
        "number": number,
        "state": state,
        "repository": {"full_name": "octo/spec-guard"} if repository is None else repository,
        "title": title,
        "body": MARKER if body is None else body,
        "labels": [{"name": label} for label in (
            ["proposal", "proposal-stage:in-review"] if labels is None else labels)],
    }


def gitlab_issue(iid=9, body=None, labels=None, project_id=17, title="Proposal: gamma",
                 state="opened"):
    return {
        "iid": iid,
        "project_id": project_id,
        "title": title,
        "state": state,
        "description": MARKER if body is None else body,
        "labels": ["proposal", "proposal-stage:published"] if labels is None else labels,
    }


def local_issue(issue_id="01JQRS4V7XK0000000000E7V48", body=None, labels=None,
                project_id="01M38JFCSPPKPQ3CJ2VY0ZP1XM", is_closed=False,
                title="Proposal: gamma"):
    """The shape the Local adapter normalizes an Epiq issue into."""
    return {
        "id": issue_id,
        "projectId": project_id,
        "title": title,
        "isClosed": is_closed,
        "description": MARKER if body is None else body,
        "labels": ["proposal", "proposal-stage:accepted"] if labels is None else labels,
    }


class ProposalTrackerLocalTests(unittest.TestCase):
    """The Local ledger is a third backend for the same identity rules: one pure
    function, one stage namespace, only the transport differs."""

    PROJECT = "01M38JFCSPPKPQ3CJ2VY0ZP1XM"

    DEFAULT = object()

    def recover(self, issues, target=DEFAULT, complete=True):
        return recover_tracker_issue(
            proposal(), "local", self.PROJECT if target is self.DEFAULT else target,
            {"complete": complete, "issues": issues})

    def test_recovers_one_verified_local_issue_with_a_string_id(self):
        result = self.recover([local_issue()])
        self.assertEqual(result.state, "verified")
        self.assertEqual(result.issue_id, "01JQRS4V7XK0000000000E7V48")
        self.assertEqual(result.stage, "proposal-stage:accepted")
        self.assertEqual(result.target, self.PROJECT)
        self.assertFalse(result.closed)

    def test_a_closed_local_issue_reports_closed(self):
        self.assertTrue(self.recover([local_issue(is_closed=True)]).closed)

    def test_a_local_target_must_be_a_well_formed_project_id(self):
        for target in (17, "", None, "has space", "x" * 65):
            self.assertEqual(self.recover([local_issue()], target=target).state,
                             "unknown", target)

    def test_a_local_marker_outside_the_named_project_is_invalid(self):
        result = self.recover([local_issue(project_id="01OTHERPROJECT")])
        self.assertEqual(result.state, "invalid")

    def test_a_local_issue_without_a_closed_flag_is_unknown(self):
        issue = local_issue()
        del issue["isClosed"]
        self.assertEqual(self.recover([issue]).state, "unknown")
        self.assertEqual(self.recover([dict(local_issue(), isClosed="no")]).state,
                         "unknown")

    def test_local_shares_the_absent_and_duplicate_rules(self):
        self.assertEqual(self.recover([local_issue(body="no marker here")]).state,
                         "absent")
        self.assertEqual(self.recover([local_issue(issue_id="a"), local_issue(issue_id="b")]
                                      ).state, "invalid")
        self.assertEqual(self.recover([local_issue()], complete=False).state, "unknown")

    def test_local_rejects_the_legacy_bridge_marker_and_label_contract_breaks(self):
        legacy = MARKER + "\n<!-- spec-guard-sync:v2 id=gamma -->"
        self.assertEqual(self.recover([local_issue(body=legacy)]).state, "invalid")
        self.assertEqual(self.recover([local_issue(labels=["proposal"])]).state, "invalid")


class ProposalTrackerClosedStateTests(unittest.TestCase):
    """Without the open/closed fact a caller cannot report `already-closed`, so a
    response that does not carry it is `unknown` rather than assumed open."""

    def test_github_open_and_closed_states_are_read(self):
        read = lambda state: recover_tracker_issue(
            proposal(), "github", "octo/spec-guard",
            {"complete": True, "issues": [github_issue(state=state)]})
        self.assertFalse(read("open").closed)
        self.assertTrue(read("closed").closed)

    def test_a_github_issue_without_a_state_is_unknown(self):
        issue = github_issue()
        del issue["state"]
        self.assertEqual(recover_tracker_issue(
            proposal(), "github", "octo/spec-guard",
            {"complete": True, "issues": [issue]}).state, "unknown")

    def test_gitlab_uses_opened_rather_than_open(self):
        read = lambda state: recover_tracker_issue(
            proposal(), "gitlab", 17,
            {"complete": True, "issues": [gitlab_issue(state=state)]})
        self.assertFalse(read("opened").closed)
        self.assertTrue(read("closed").closed)
        self.assertEqual(read("open").state, "unknown")

    def test_a_gitlab_issue_without_a_state_is_unknown(self):
        issue = gitlab_issue()
        del issue["state"]
        self.assertEqual(recover_tracker_issue(
            proposal(), "gitlab", 17, {"complete": True, "issues": [issue]}).state,
            "unknown")

    def test_safe_json_carries_the_closed_fact(self):
        result = recover_tracker_issue(
            proposal(), "local", "01M38JFCSPPKPQ3CJ2VY0ZP1XM",
            {"complete": True, "issues": [local_issue(is_closed=True)]})
        payload = as_json(result, "local", "01M38JFCSPPKPQ3CJ2VY0ZP1XM")
        self.assertTrue(payload["closed"])
        self.assertEqual(payload["issueId"], "01JQRS4V7XK0000000000E7V48")
        serialized = json.dumps(payload)
        self.assertNotIn(MARKER, serialized)
        self.assertNotIn("Proposal: gamma", serialized)


class ProposalTrackerReadFixtures(unittest.TestCase):
    def test_recovers_one_verified_issue_from_each_explicit_platform_container(self):
        github = recover_tracker_issue(proposal(), "github", "octo/spec-guard", {
            "complete": True, "issues": [github_issue()],
        })
        self.assertEqual((github.state, github.issue_id, github.stage),
                         ("verified", 42, "proposal-stage:in-review"))

        gitlab = recover_tracker_issue(proposal(), "gitlab", 17, {
            "complete": True, "issues": [gitlab_issue()],
        })
        self.assertEqual((gitlab.state, gitlab.issue_id, gitlab.stage),
                         ("verified", 9, "proposal-stage:published"))

    def test_recovers_github_search_api_repository_url_shape(self):
        issue = github_issue()
        issue.pop("repository")
        issue["repository_url"] = "https://api.github.com/repos/octo/spec-guard"
        result = recover_tracker_issue(proposal(), "github", "octo/spec-guard", {
            "complete": True, "issues": [issue],
        })
        self.assertEqual((result.state, result.issue_id, result.stage),
                         ("verified", 42, "proposal-stage:in-review"))

    def test_complete_search_without_a_full_body_marker_is_absent(self):
        title_only = github_issue(body="plain text", title=MARKER)
        partial = github_issue(number=43, body="<!-- spec-guard-proposal:v1 id=gamma")
        result = recover_tracker_issue(proposal(), "github", "octo/spec-guard", {
            "complete": True, "issues": [title_only, partial],
        })
        self.assertEqual(result.state, "absent")

    def test_multiple_or_foreign_full_markers_are_invalid(self):
        duplicate = recover_tracker_issue(proposal(), "gitlab", 17, {
            "complete": True, "issues": [gitlab_issue(), gitlab_issue(iid=10)],
        })
        self.assertEqual(duplicate.state, "invalid")

        foreign = recover_tracker_issue(proposal(), "github", "octo/spec-guard", {
            "complete": True,
            "issues": [github_issue(repository={"full_name": "other/project"})],
        })
        self.assertEqual(foreign.state, "invalid")

    def test_incomplete_or_unparseable_search_is_unknown(self):
        incomplete = recover_tracker_issue(proposal(), "github", "octo/spec-guard", {
            "complete": False, "issues": [github_issue()],
        })
        self.assertEqual(incomplete.state, "unknown")

        malformed = recover_tracker_issue(proposal(), "gitlab", 17, {
            "complete": True, "issues": [{"iid": 9, "project_id": 17}],
        })
        self.assertEqual(malformed.state, "unknown")

    def test_label_or_legacy_projection_conflicts_are_invalid(self):
        bad_labels = recover_tracker_issue(proposal(), "gitlab", 17, {
            "complete": True,
            "issues": [gitlab_issue(labels=["proposal", "proposal-stage:draft",
                                              "proposal-stage:accepted"])],
        })
        self.assertEqual(bad_labels.state, "invalid")

        legacy = recover_tracker_issue(proposal(), "github", "octo/spec-guard", {
            "complete": True,
            "issues": [github_issue(body=MARKER + "\n<!-- spec-guard-sync:v2 kind=module -->")],
        })
        self.assertEqual(legacy.state, "invalid")


class ProposalTrackerTransportTests(unittest.TestCase):
    def runner(self, *responses):
        replies = iter(responses)
        calls = []

        def run(args):
            calls.append(args)
            return next(replies)

        return run, calls

    def test_github_reads_complete_repository_issue_set_using_read_only_argv(self):
        issues = [github_issue(number=index, body="plain text")
                  for index in range(1, 101)]
        pull_request = github_issue(number=102)
        pull_request["pull_request"] = {"url": "https://api.github.com/repos/octo/spec-guard/pulls/102"}
        runner, calls = self.runner(
            json.dumps(issues + [pull_request, github_issue(number=101)]),
        )
        result = read_tracker(proposal(), "github", "octo/spec-guard", runner=runner)
        self.assertEqual((result.state, result.issue_id), ("verified", 101))
        self.assertEqual(calls, [[
            "gh", "issue", "list", "--repo", "octo/spec-guard", "--state", "all",
            "--limit", "1000", "--json", "number,body,labels,state",
        ]])

    def test_github_result_at_the_read_limit_is_unknown(self):
        runner, _ = self.runner(json.dumps([
            github_issue(number=index, body="plain text") for index in range(1, 1001)
        ]))
        result = read_tracker(proposal(), "github", "octo/spec-guard", runner=runner)
        self.assertEqual(result.state, "unknown")

    def test_gitlab_reads_until_a_short_page_using_get_argv(self):
        first_page = [gitlab_issue(iid=index, body="plain text")
                      for index in range(1, 101)]
        runner, calls = self.runner(
            json.dumps(first_page), json.dumps([gitlab_issue(iid=101, state="closed")]))
        result = read_tracker(proposal(), "gitlab", 17, runner=runner)
        self.assertEqual((result.state, result.issue_id), ("verified", 101))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call[:2] == ["glab", "api"] for call in calls))
        self.assertTrue(all(call[2].startswith("projects/17/issues?") for call in calls))
        self.assertTrue(all("search=" not in call[2] and "page=" in call[2] and "state=all" in call[2]
                            for call in calls))
        self.assertTrue(all("-X" not in call and "--method" not in call for call in calls))

    def test_gitlab_finds_the_marker_even_when_search_ignores_html_comments(self):
        # GitLab 15.3.2 (verified 2026-09-28): search= never matched text inside HTML
        # comments, so a marker search always came back empty. The reader must list and match locally.
        issues = [gitlab_issue(iid=index, body="plain text") for index in range(1, 40)]
        issues.append(gitlab_issue(iid=77))
        calls = []

        def search_blind_gitlab(argv):
            calls.append(argv)
            return "[]" if "search=" in argv[2] else json.dumps(issues)

        result = read_tracker(proposal(), "gitlab", 17, runner=search_blind_gitlab)
        self.assertEqual((result.state, result.issue_id), ("verified", 77))
        self.assertEqual(len(calls), 1)

    def test_gitlab_result_filling_every_page_is_unknown(self):
        full_page = json.dumps([gitlab_issue(iid=index, body="plain text") for index in range(1, 101)])
        runner, calls = self.runner(*([full_page] * 10))
        result = read_tracker(proposal(), "gitlab", 17, runner=runner)
        self.assertEqual(result.state, "unknown")
        self.assertEqual(len(calls), 10)

    def test_transport_failure_or_incomplete_github_response_is_unknown(self):
        failed, _ = self.runner(None)
        self.assertEqual(read_tracker(proposal(), "github", "octo/spec-guard",
                                      runner=failed).state, "unknown")

        incomplete, _ = self.runner(json.dumps({
            "total_count": 1, "incomplete_results": True, "items": [github_issue()],
        }))
        self.assertEqual(read_tracker(proposal(), "github", "octo/spec-guard",
                                      runner=incomplete).state, "unknown")


class ProposalTrackerInvalidCodeTests(unittest.TestCase):
    """`invalid` covers three different problems. A caller that cannot tell them apart
    cannot react differently -- several items carrying the marker is a conflict to
    resolve, a legacy bridge marker is a migration, a foreign container is a wrong
    argument -- and matching on the prose diagnostic would be guessing at a sentence."""

    def recover(self, issues, target="octo/spec-guard"):
        return recover_tracker_issue(proposal(), "github", target,
                                     {"complete": True, "issues": issues})

    def test_several_items_carrying_the_marker_are_marker_ambiguous(self):
        result = self.recover([github_issue(number=1), github_issue(number=2)])
        self.assertEqual(result.state, "invalid")
        self.assertEqual(result.code, "tracker-marker-ambiguous")

    def test_a_marker_outside_the_container_names_the_container(self):
        result = self.recover([github_issue(repository={"full_name": "other/repo"})])
        self.assertEqual(result.code, "tracker-marker-foreign-container")

    def test_a_legacy_bridge_marker_is_named_as_such(self):
        body = MARKER + "\n<!-- spec-guard-sync:v2 id=gamma -->"
        self.assertEqual(self.recover([github_issue(body=body)]).code,
                         "tracker-legacy-marker")

    def test_a_contract_breach_keeps_the_generic_code(self):
        result = self.recover([github_issue(labels=["proposal"])])
        self.assertEqual(result.code, "tracker-contract-invalid")

    def test_each_code_reaches_the_safe_json(self):
        result = self.recover([github_issue(number=1), github_issue(number=2)])
        payload = as_json(result, "github", "octo/spec-guard")
        self.assertEqual(payload["diagnostic"], "tracker-marker-ambiguous")
        self.assertNotIn("multiple", json.dumps(payload))

    def test_a_result_without_a_code_still_reports_the_generic_one(self):
        payload = as_json(TrackerRead("invalid", diagnostic="raw prose"),
                          "github", "octo/spec-guard")
        self.assertEqual(payload["diagnostic"], "tracker-contract-invalid")


class ProposalTrackerOutputTests(unittest.TestCase):
    def test_json_exposes_only_safe_verified_facts(self):
        result = TrackerRead("verified", issue_id=42, stage="proposal-stage:in-review",
                             closed=False)
        data = as_json(result, "github", "octo/spec-guard")
        self.assertEqual(data, {
            "state": "verified", "platform": "github", "target": "octo/spec-guard",
            "issueId": 42, "stage": "proposal-stage:in-review", "closed": False,
        })
        self.assertNotIn(MARKER, json.dumps(data))

    def test_json_sanitizes_invalid_or_unknown_diagnostics(self):
        invalid = as_json(TrackerRead("invalid", diagnostic="token=secret " + MARKER),
                          "gitlab", 17)
        self.assertEqual(invalid["diagnostic"], "tracker-contract-invalid")
        self.assertNotIn("secret", json.dumps(invalid))
        self.assertNotIn(MARKER, json.dumps(invalid))

        unknown = as_json(TrackerRead("unknown", diagnostic="https://token@example.invalid"),
                          "github", "octo/spec-guard")
        self.assertEqual(unknown["diagnostic"], "tracker-read-unavailable")
        self.assertNotIn("example.invalid", json.dumps(unknown))


if __name__ == "__main__":
    unittest.main()
