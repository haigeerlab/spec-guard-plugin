"""Local closeout adapter against a faked Epiq MCP. No real ledger, no network.

Every shape asserted here was observed from the pinned epiq@1.11.0 runtime in a fully
isolated temporary ledger, not inferred from the minified bundle.
"""
import json
import pathlib
import subprocess
import tempfile
import unittest

from proposal_closeout_local import LocalCloseout, LocalCloseoutError

PROJECT_ID = "01M38JFCSPPKPQ3CJ2VY0ZP1XM"
ACCEPTED = "proposal-stage:accepted"
PROMOTED = "proposal-stage:promoted"
ISSUE_ID = "01M435DK5RM00Q3WC6SGRDJ04Z"
REF = "GRDJ04Z"
MARKER = "<!-- spec-guard-proposal-closeout:v1 gamma/0123456789ab -->"


def tag(name, identifier=None):
    return {"id": identifier or ("tag-" + name), "name": name, "color": "#5b8cff"}


def epiq_issue(tags=(ACCEPTED, "proposal"), is_closed=False, comments=(),
               description="body", identifier=ISSUE_ID):
    """The shape epiq_issue_get returns (observed, epiq@1.11.0)."""
    return {"id": identifier, "ref": REF, "title": "Proposal: gamma",
            "description": description, "isClosed": is_closed,
            "tags": [tag(name) for name in tags],
            "comments": [{"body": body} for body in comments],
            "assignees": [], "readonly": False,
            "parentNodeId": "01M435DJ993M3VZ139VCJQZSEQ"}


class Ledger:
    """Records every call so a read path that writes cannot pass unnoticed."""

    WRITES = ("epiq_issue_comment_add", "epiq_issue_tag_add", "epiq_issue_tag_remove",
              "epiq_issue_close", "epiq_sync", "epiq_project_init")

    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []

    def __call__(self, name, **arguments):
        self.calls.append((name, arguments))
        if name not in self.responses:
            raise LocalCloseoutError("unexpected call " + name)
        value = self.responses[name]
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def names(self):
        return [name for name, _ in self.calls]

    @property
    def writes(self):
        return [name for name in self.names if name in self.WRITES]


def provider(responses, project_id=PROJECT_ID):
    ledger = Ledger(responses)
    return LocalCloseout(project_id, caller=ledger), ledger


class LocalReadTests(unittest.TestCase):
    def test_listing_must_include_closed_items(self):
        """Observed: without includeClosed a closed issue is simply absent from the
        list.  A closed Proposal read as `absent` is the worst possible answer -- it
        invites recreating an item that already exists -- so the flag is mandatory."""
        closeout, ledger = provider({"epiq_issue_list": [epiq_issue(is_closed=True)]})
        listing = closeout.list_issues()
        self.assertTrue(listing["complete"])
        self.assertTrue(listing["issues"][0]["isClosed"])
        self.assertEqual(ledger.calls[0][1].get("includeClosed"), True)
        self.assertEqual(ledger.writes, [])

    def test_listing_is_normalized_for_the_shared_identity_rules(self):
        closeout, _ = provider({"epiq_issue_list": [epiq_issue(description=MARKER)]})
        issue = closeout.list_issues()["issues"][0]
        self.assertEqual(issue["id"], ISSUE_ID)
        self.assertEqual(issue["projectId"], PROJECT_ID)
        self.assertEqual(issue["description"], MARKER)
        self.assertEqual(sorted(issue["labels"]), ["proposal", ACCEPTED])
        self.assertIs(issue["isClosed"], False)

    def test_a_malformed_listing_is_an_error_not_a_guess(self):
        for payload in ({}, "nope", [None], [{"id": ISSUE_ID}],
                        [dict(epiq_issue(), tags="proposal")],
                        [dict(epiq_issue(), isClosed="no")]):
            closeout, _ = provider({"epiq_issue_list": payload})
            with self.assertRaises(LocalCloseoutError, msg=repr(payload)):
                closeout.list_issues()

    def test_get_issue_reads_by_full_id_and_keeps_tag_identities(self):
        closeout, ledger = provider({"epiq_issue_get": epiq_issue()})
        issue = closeout.get_issue(ISSUE_ID)
        self.assertEqual(issue["id"], ISSUE_ID)
        self.assertEqual(issue["ref"], REF)
        self.assertEqual(ledger.calls[0][1]["idOrRef"], ISSUE_ID)
        self.assertEqual({item["name"]: item["id"] for item in issue["tags"]}[ACCEPTED],
                         "tag-" + ACCEPTED)
        self.assertEqual(ledger.writes, [])

    def test_get_issue_rejects_a_different_identity(self):
        closeout, _ = provider({"epiq_issue_get": epiq_issue(identifier="01OTHER")})
        with self.assertRaises(LocalCloseoutError):
            closeout.get_issue(ISSUE_ID)

    def test_comments_come_from_the_issue_view_in_log_order(self):
        closeout, ledger = provider({
            "epiq_issue_get": epiq_issue(comments=("first", MARKER))})
        self.assertEqual(closeout.list_comments(ISSUE_ID),
                         {"complete": True,
                          "comments": [{"body": "first"}, {"body": MARKER}]})
        self.assertEqual(ledger.writes, [])


class LocalStageTests(unittest.TestCase):
    def test_the_new_tag_is_added_before_the_old_one_is_removed(self):
        closeout, ledger = provider({
            "epiq_issue_get": epiq_issue(),
            "epiq_issue_tag_add": {"id": ISSUE_ID, "ref": REF,
                                   "tag": tag(PROMOTED)},
            "epiq_issue_tag_remove": {"id": ISSUE_ID, "ref": REF}})
        closeout.set_stage(ISSUE_ID, ACCEPTED, PROMOTED)
        self.assertEqual(ledger.writes, ["epiq_issue_tag_add", "epiq_issue_tag_remove"])
        removal = next(arguments for name, arguments in ledger.calls
                       if name == "epiq_issue_tag_remove")
        # Removal is by tagId, not by name: epiq_issue_tag_remove takes tagId.
        self.assertEqual(removal["tagId"], "tag-" + ACCEPTED)
        self.assertEqual(removal["issueId"], ISSUE_ID)

    def test_a_missing_old_tag_identity_stops_rather_than_guessing(self):
        closeout, ledger = provider({
            "epiq_issue_get": epiq_issue(tags=("proposal",)),
            "epiq_issue_tag_add": {"id": ISSUE_ID, "ref": REF, "tag": tag(PROMOTED)}})
        with self.assertRaises(LocalCloseoutError):
            closeout.set_stage(ISSUE_ID, ACCEPTED, PROMOTED)
        self.assertNotIn("epiq_issue_tag_remove", ledger.names)

    def test_only_adds_when_there_is_no_old_stage(self):
        closeout, ledger = provider({
            "epiq_issue_tag_add": {"id": ISSUE_ID, "ref": REF, "tag": tag(PROMOTED)}})
        closeout.set_stage(ISSUE_ID, None, PROMOTED)
        self.assertEqual(ledger.writes, ["epiq_issue_tag_add"])

    def test_adding_the_same_stage_twice_is_not_a_removal(self):
        closeout, ledger = provider({
            "epiq_issue_tag_add": {"id": ISSUE_ID, "ref": REF, "tag": tag(PROMOTED)}})
        closeout.set_stage(ISSUE_ID, PROMOTED, PROMOTED)
        self.assertEqual(ledger.writes, ["epiq_issue_tag_add"])


class LocalWriteTests(unittest.TestCase):
    def test_comment_and_close_use_the_full_issue_id(self):
        closeout, ledger = provider({
            "epiq_issue_comment_add": {"id": ISSUE_ID},
            "epiq_issue_close": {"id": ISSUE_ID}})
        closeout.create_comment(ISSUE_ID, MARKER)
        closeout.set_closed(ISSUE_ID)
        self.assertEqual(ledger.writes, ["epiq_issue_comment_add", "epiq_issue_close"])
        for _name, arguments in ledger.calls:
            self.assertEqual(arguments["issueId"], ISSUE_ID)

    def test_the_adapter_never_calls_a_gated_epiq_tool(self):
        """`epiq_sync` publishes ticket contents to a Git remote and is gated per call.
        Closeout must never reach for it, so no call list may contain it."""
        closeout, ledger = provider({
            "epiq_issue_get": epiq_issue(),
            "epiq_issue_list": [epiq_issue()],
            "epiq_issue_comment_add": {"id": ISSUE_ID},
            "epiq_issue_tag_add": {"id": ISSUE_ID, "ref": REF, "tag": tag(PROMOTED)},
            "epiq_issue_tag_remove": {"id": ISSUE_ID, "ref": REF},
            "epiq_issue_close": {"id": ISSUE_ID}})
        closeout.list_issues()
        closeout.get_issue(ISSUE_ID)
        closeout.list_comments(ISSUE_ID)
        closeout.create_comment(ISSUE_ID, MARKER)
        closeout.set_stage(ISSUE_ID, ACCEPTED, PROMOTED)
        closeout.set_closed(ISSUE_ID)
        for gated in ("epiq_sync", "epiq_project_init", "epiq_skill_install",
                      "epiq_issue_comment_delete", "epiq_swimlane_delete",
                      "epiq_tag_remove", "epiq_contributor_remove"):
            self.assertNotIn(gated, ledger.names)


class LocalTargetTests(unittest.TestCase):
    def owned(self):
        """Pretend this checkout owns the state worktree; ownership has its own case."""
        import proposal_closeout_local as module
        original = module.state_worktree_status
        module.state_worktree_status = lambda *a, **k: {"state": "owned"}
        self.addCleanup(setattr, module, "state_worktree_status", original)

    def initialized(self, tmp, project_id=PROJECT_ID):
        root = pathlib.Path(tmp)
        (root / ".epiq").mkdir(exist_ok=True)
        (root / ".epiq" / "project.json").write_text(json.dumps(
            {"projectId": project_id, "stateBranch": "__epiq_state__",
             "createdAt": "2026-01-01T00:00:00.000Z"}), encoding="utf-8")
        return root

    def test_a_project_id_must_be_well_formed(self):
        for identifier in ("", "has space", "x" * 65, 17, None):
            with self.assertRaises(LocalCloseoutError, msg=repr(identifier)):
                LocalCloseout(identifier, caller=lambda *a, **k: None)

    def test_target_facts_come_from_the_ledger_not_from_our_own_argument(self):
        """`exactTarget` is what the operator reads before authorizing, so echoing the
        caller's own `--target` back makes it a restatement of the request rather than
        a fact. The project actually written to is decided by `.epiq/project.json` in
        the project root; a repo shipping one id in `.agent/tracker.json` and another
        in `.epiq/project.json` would show one destination and write to the other."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".epiq").mkdir()
            (root / ".epiq" / "project.json").write_text(json.dumps(
                {"projectId": PROJECT_ID, "stateBranch": "__epiq_state__",
                 "createdAt": "2026-01-01T00:00:00.000Z"}), encoding="utf-8")
            self.owned()
            closeout = LocalCloseout(PROJECT_ID, project=root,
                                     caller=Ledger({}))
            facts = closeout.target_facts()
            self.assertEqual(facts["platform"], "local")
            self.assertEqual(facts["target"], PROJECT_ID)
            self.assertEqual(facts["stateBranch"], "__epiq_state__")
            self.assertNotIn("url", facts)

    def test_a_ledger_identity_that_differs_from_the_named_target_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".epiq").mkdir()
            (root / ".epiq" / "project.json").write_text(json.dumps(
                {"projectId": "01SOMEOTHERPROJECT", "stateBranch": "__epiq_state__",
                 "createdAt": "2026-01-01T00:00:00.000Z"}), encoding="utf-8")
            closeout = LocalCloseout(PROJECT_ID, project=root, caller=Ledger({}))
            with self.assertRaises(LocalCloseoutError):
                closeout.target_facts()

    def test_a_state_worktree_owned_by_another_checkout_refuses_to_write(self):
        """Every other Local writer in this repo gates on ownership. A second checkout
        of the same project can own the `__epiq_state__` worktree; without this check
        closeout would comment, retag and close through a worktree this checkout does
        not own, and the preview would give no warning."""
        import proposal_closeout_local as module
        with tempfile.TemporaryDirectory() as tmp:
            root = self.initialized(tmp)
            original = module.state_worktree_status
            module.state_worktree_status = lambda *a, **k: {"state": "foreign"}
            try:
                with self.assertRaises(LocalCloseoutError):
                    LocalCloseout(PROJECT_ID, project=root, caller=Ledger({})
                                  ).target_facts()
            finally:
                module.state_worktree_status = original

    def test_the_preview_states_whether_the_ledger_publishes_to_a_remote(self):
        """The ledger's state branch can be pushed to a Git remote, which on a public
        repository makes the closeout record public. The operator authorizes the write
        from the preview, so that has to be in it rather than left to be guessed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.initialized(tmp)
            self.owned()
            facts = LocalCloseout(PROJECT_ID, project=root,
                                  caller=Ledger({})).target_facts()
            self.assertIn("publishesTo", facts)
            self.assertIsNone(facts["publishesTo"])
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(root), "remote", "add", "origin",
                            "https://example.invalid/x.git"], check=True)
            with_remote = LocalCloseout(PROJECT_ID, project=root,
                                        caller=Ledger({})).target_facts()
            self.assertEqual(with_remote["publishesTo"], "origin")

    def test_an_uninitialized_project_cannot_report_a_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            closeout = LocalCloseout(PROJECT_ID, project=pathlib.Path(tmp),
                                     caller=Ledger({}))
            with self.assertRaises(LocalCloseoutError):
                closeout.target_facts()


if __name__ == "__main__":
    unittest.main()
