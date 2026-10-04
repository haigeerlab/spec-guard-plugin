"""Closeout provider adapters for GitHub and GitLab. Fake transports only, no network.

Read-only operations must never reach the writer: every read test asserts the writer was
not called at all, so a read path that quietly writes cannot pass.
"""
import unittest

from hosted_ticket_provider import HostedTicketError, PAGE_SIZE, ProviderRejected
from proposal_closeout_github import GitHubCloseout
from proposal_closeout_gitlab import GitLabCloseout

ACCEPTED = "proposal-stage:accepted"
PROMOTED = "proposal-stage:promoted"
MARKER = "<!-- spec-guard-proposal-closeout:v1 gamma/0123456789ab -->"


class Recorder:
    """A fake runner/writer pair that records argv and refuses surprises."""

    def __init__(self, reads=None, writes=None):
        self.reads = dict(reads or {})
        self.writes = dict(writes or {})
        self.read_calls = []
        self.write_calls = []

    def runner(self, arguments):
        self.read_calls.append(list(arguments))
        endpoint = arguments[-1]
        if endpoint not in self.reads:
            raise HostedTicketError("provider-unavailable: unexpected read " + endpoint)
        value = self.reads[endpoint]
        if isinstance(value, Exception):
            raise value
        return value

    def writer(self, arguments, body):
        self.write_calls.append((list(arguments), body))
        key = (arguments[arguments.index("--method") + 1], arguments[-1])
        if key not in self.writes:
            raise HostedTicketError("provider-unavailable: unexpected write %s" % (key,))
        value = self.writes[key]
        if isinstance(value, Exception):
            raise value
        return value


def github_raw(number=7, labels=(ACCEPTED, "proposal"), state="open", body="body"):
    return {"number": number, "state": state, "body": body,
            "labels": [{"name": name} for name in labels],
            "html_url": "https://github.com/octo/repo/issues/%d" % number}


def gitlab_raw(iid=9, labels=(ACCEPTED, "proposal"), state="opened", body="body"):
    return {"iid": iid, "project_id": 17, "state": state, "description": body,
            "labels": list(labels),
            "web_url": "https://gitlab.example.com/octo/repo/-/issues/%d" % iid}


class GitHubCloseoutTests(unittest.TestCase):
    REPO = "repos/octo/repo"
    ISSUES = REPO + "/issues"

    def provider(self, reads=None, writes=None):
        recorder = Recorder(reads, writes)
        return GitHubCloseout("github.com", "octo/repo", recorder.runner,
                              recorder.writer), recorder

    def test_target_facts_are_verified_before_anything_else(self):
        provider, recorder = self.provider({self.REPO: {
            "full_name": "octo/repo", "id": 42, "private": True, "has_issues": True}})
        self.assertEqual(provider.target_facts(), {
            "platform": "github", "host": "github.com", "target": "octo/repo",
            "targetId": 42, "visibility": "private"})
        self.assertEqual(recorder.write_calls, [])

    def test_a_target_without_issues_or_a_renamed_target_is_unavailable(self):
        for raw in ({"full_name": "octo/repo", "id": 42, "private": True,
                     "has_issues": False},
                    {"full_name": "octo/renamed", "id": 42, "private": True,
                     "has_issues": True}):
            provider, _ = self.provider({self.REPO: raw})
            with self.assertRaises(HostedTicketError):
                provider.target_facts()

    def test_list_issues_pages_to_a_short_page_and_never_writes(self):
        page_one = [github_raw(number=n) for n in range(1, PAGE_SIZE + 1)]
        provider, recorder = self.provider({
            self.ISSUES + "?state=all&per_page=100&page=1": page_one,
            self.ISSUES + "?state=all&per_page=100&page=2": [github_raw(number=999)]})
        listing = provider.list_issues()
        self.assertTrue(listing["complete"])
        self.assertEqual(len(listing["issues"]), PAGE_SIZE + 1)
        self.assertEqual(len(recorder.read_calls), 2)
        self.assertEqual(recorder.write_calls, [])

    def test_list_issues_drops_pull_requests(self):
        pull = dict(github_raw(number=8), pull_request={"url": "x"})
        provider, _ = self.provider({
            self.ISSUES + "?state=all&per_page=100&page=1": [github_raw(), pull]})
        self.assertEqual([issue["number"] for issue in
                          provider.list_issues()["issues"]], [7])

    def test_get_issue_keeps_the_identity_shape_the_recovery_rules_consume(self):
        provider, recorder = self.provider({self.ISSUES + "/7": github_raw(state="closed")})
        issue = provider.get_issue(7)
        self.assertEqual(issue["number"], 7)
        self.assertEqual(issue["state"], "closed")
        self.assertEqual(sorted(label["name"] for label in issue["labels"]),
                         ["proposal", "proposal-stage:accepted"])
        self.assertEqual(issue["url"], "https://github.com/octo/repo/issues/7")
        self.assertEqual(recorder.write_calls, [])

    def test_get_issue_rejects_a_different_number(self):
        provider, _ = self.provider({self.ISSUES + "/7": github_raw(number=8)})
        with self.assertRaises(HostedTicketError):
            provider.get_issue(7)

    def test_list_comments_pages_and_never_writes(self):
        endpoint = self.ISSUES + "/7/comments?per_page=100&page=1"
        provider, recorder = self.provider({endpoint: [{"body": MARKER}]})
        self.assertEqual(provider.list_comments(7),
                         {"complete": True, "comments": [{"body": MARKER}]})
        self.assertEqual(recorder.write_calls, [])

    def test_create_comment_posts_the_body_verbatim(self):
        provider, recorder = self.provider(
            writes={("POST", self.ISSUES + "/7/comments"): {"id": 1}})
        provider.create_comment(7, MARKER)
        arguments, body = recorder.write_calls[0]
        self.assertEqual(arguments, ["gh", "api", "--hostname", "github.com",
                                     "--method", "POST", self.ISSUES + "/7/comments"])
        self.assertEqual(body, {"body": MARKER})

    def test_set_stage_adds_the_new_label_then_removes_the_old_one(self):
        provider, recorder = self.provider(writes={
            ("POST", self.ISSUES + "/7/labels"): [{"name": PROMOTED}],
            ("DELETE", self.ISSUES + "/7/labels/" + ACCEPTED): []})
        provider.set_stage(7, ACCEPTED, PROMOTED)
        methods = [arguments[arguments.index("--method") + 1]
                   for arguments, _ in recorder.write_calls]
        # Add first: if the removal lands and the addition does not, the Issue would be
        # left with no stage label at all, which breaks the tracker contract.
        self.assertEqual(methods, ["POST", "DELETE"])
        self.assertEqual(recorder.write_calls[0][1], {"labels": [PROMOTED]})

    def test_set_stage_only_adds_when_there_is_no_old_stage_to_remove(self):
        provider, recorder = self.provider(writes={
            ("POST", self.ISSUES + "/7/labels"): [{"name": PROMOTED}]})
        provider.set_stage(7, None, PROMOTED)
        self.assertEqual(len(recorder.write_calls), 1)

    def test_set_closed_patches_the_state(self):
        provider, recorder = self.provider(
            writes={("PATCH", self.ISSUES + "/7"): github_raw(state="closed")})
        provider.set_closed(7)
        arguments, body = recorder.write_calls[0]
        self.assertEqual(arguments, ["gh", "api", "--hostname", "github.com",
                                     "--method", "PATCH", self.ISSUES + "/7"])
        self.assertEqual(body, {"state": "closed"})

    def test_a_definite_rejection_keeps_its_status_code(self):
        provider, _ = self.provider(
            writes={("PATCH", self.ISSUES + "/7"): ProviderRejected(403)})
        with self.assertRaises(ProviderRejected) as caught:
            provider.set_closed(7)
        self.assertEqual(caught.exception.status_code, 403)


class GitLabCloseoutTests(unittest.TestCase):
    ISSUES = "projects/17/issues"

    def provider(self, reads=None, writes=None):
        recorder = Recorder(reads, writes)
        return GitLabCloseout("gitlab.example.com", 17, recorder.runner,
                              recorder.writer), recorder

    def test_the_container_is_a_positive_integer_project_id(self):
        for target in ("octo/repo", 0, -1, None):
            with self.assertRaises(HostedTicketError, msg=repr(target)):
                GitLabCloseout("gitlab.example.com", target)

    def test_target_facts_match_the_project_metadata_host(self):
        provider, recorder = self.provider({"projects/17": {
            "id": 17, "path_with_namespace": "octo/repo", "visibility": "private",
            "issues_enabled": True,
            "web_url": "https://gitlab.example.com/octo/repo"}})
        facts = provider.target_facts()
        self.assertEqual(facts["platform"], "gitlab")
        self.assertEqual(facts["target"], 17)
        self.assertEqual(facts["visibility"], "private")
        self.assertEqual(recorder.write_calls, [])

    def test_a_project_web_url_on_another_host_is_unavailable(self):
        provider, _ = self.provider({"projects/17": {
            "id": 17, "path_with_namespace": "octo/repo", "visibility": "private",
            "issues_enabled": True, "web_url": "https://evil.example.net/octo/repo"}})
        with self.assertRaises(HostedTicketError):
            provider.target_facts()

    def test_list_issues_pages_until_a_short_page(self):
        provider, recorder = self.provider({
            self.ISSUES + "?state=all&per_page=100&page=1": [gitlab_raw()]})
        listing = provider.list_issues()
        self.assertTrue(listing["complete"])
        self.assertEqual(listing["issues"][0]["iid"], 9)
        self.assertEqual(recorder.write_calls, [])

    def test_system_notes_are_not_discussion_evidence(self):
        endpoint = self.ISSUES + "/9/notes?per_page=100&page=1"
        provider, _ = self.provider({endpoint: [
            {"body": MARKER, "system": False},
            {"body": "changed the description", "system": True}]})
        self.assertEqual(provider.list_comments(9),
                         {"complete": True, "comments": [{"body": MARKER}]})

    def test_set_stage_adds_and_removes_in_one_request(self):
        provider, recorder = self.provider(
            writes={("PUT", self.ISSUES + "/9"): gitlab_raw(labels=(PROMOTED,))})
        provider.set_stage(9, ACCEPTED, PROMOTED)
        arguments, body = recorder.write_calls[0]
        self.assertEqual(len(recorder.write_calls), 1)
        self.assertEqual(body, {"add_labels": PROMOTED, "remove_labels": ACCEPTED})

    def test_set_closed_uses_a_state_event(self):
        provider, recorder = self.provider(
            writes={("PUT", self.ISSUES + "/9"): gitlab_raw(state="closed")})
        provider.set_closed(9)
        self.assertEqual(recorder.write_calls[0][1], {"state_event": "close"})

    def test_a_definite_rejection_keeps_its_status_code(self):
        provider, _ = self.provider(
            writes={("PUT", self.ISSUES + "/9"): ProviderRejected(404)})
        with self.assertRaises(ProviderRejected) as caught:
            provider.set_closed(9)
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
