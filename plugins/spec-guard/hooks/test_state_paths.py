"""Machine state locations: one root, an override, and whole-directory fallback. No network."""
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_paths


class Home:
    """A temporary HOME with SPEC_GUARD_STATE_DIR removed unless given."""

    def __init__(self, override=None):
        self.override = override

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        env = {key: value for key, value in os.environ.items() if key != "SPEC_GUARD_STATE_DIR"}
        env["HOME"] = str(self.home)
        if self.override is not None:
            env["SPEC_GUARD_STATE_DIR"] = self.override
        self.patch = mock.patch.dict(os.environ, env, clear=True)
        self.patch.start()
        return self.home

    def __exit__(self, *exc):
        self.patch.stop()
        self.tmp.cleanup()


class Root(unittest.TestCase):
    def test_default_root(self):
        with Home() as home:
            self.assertEqual(state_paths.state_root(), home / ".spec-guard")

    def test_override(self):
        with Home(override="/tmp/sg-state") as _:
            self.assertEqual(state_paths.state_root(), Path("/tmp/sg-state"))

    def test_empty_override_is_unset(self):
        with Home(override="") as home:
            self.assertEqual(state_paths.state_root(), home / ".spec-guard")


class Fallback(unittest.TestCase):
    def test_new_when_neither_exists(self):
        with Home() as home:
            legacy = home / ".local" / "state" / "spec-guard" / "x"
            self.assertEqual(state_paths.state_dir("x", legacy), home / ".spec-guard" / "x")

    def test_legacy_only_when_new_is_absent_and_legacy_exists(self):
        with Home() as home:
            legacy = home / ".local" / "state" / "spec-guard" / "x"
            legacy.mkdir(parents=True)
            self.assertEqual(state_paths.state_dir("x", legacy), legacy)
            (home / ".spec-guard" / "x").mkdir(parents=True)
            self.assertEqual(state_paths.state_dir("x", legacy), home / ".spec-guard" / "x")

    def test_state_dir_creates_nothing(self):
        with Home() as home:
            state_paths.state_dir("x", home / "old")
            self.assertFalse((home / ".spec-guard").exists())

    def test_legacy_in_use(self):
        with Home() as home:
            self.assertEqual(state_paths.legacy_in_use(), [])
            old = home / ".local" / "state" / "spec-guard" / "proposal-closeout"
            old.mkdir(parents=True)
            self.assertEqual(state_paths.legacy_in_use(), [old])
            (home / ".spec-guard" / "proposal-closeout").mkdir(parents=True)
            self.assertEqual(state_paths.legacy_in_use(), [])


class Callers(unittest.TestCase):
    """Defaults for users with no override are byte-for-byte today's paths."""

    def fresh(self, name):
        sys.modules.pop(name, None)
        return importlib.import_module(name)

    def test_unchanged_defaults(self):
        with Home() as home:
            self.assertEqual(self.fresh("local_ledger_runtime").default_runtime_dir(),
                             home / ".spec-guard" / "local-ticket-ledger" / "runtime")
            self.assertEqual(self.fresh("proposal_closeout_local").DEFAULT_RUNTIME,
                             home / ".spec-guard" / "local-ticket-ledger" / "runtime")
            self.assertEqual(self.fresh("local_ticket_journal").default_journal_root(),
                             home / ".spec-guard" / "local-ticket-portability")

    def test_moved_items_use_the_root_or_their_legacy_directory(self):
        with Home() as home:
            self.assertEqual(self.fresh("hosted_ticket").INTENT_ROOT, home / ".spec-guard" / "hosted-ticket-intents")
            self.assertEqual(self.fresh("proposal_closeout").JOURNAL_ROOT, home / ".spec-guard" / "proposal-closeout")
        with Home() as home:
            old = home / ".local" / "state" / "spec-guard"
            (old / "hosted-ticket-intents").mkdir(parents=True)
            (old / "proposal-closeout").mkdir(parents=True)
            self.assertEqual(self.fresh("hosted_ticket").INTENT_ROOT, old / "hosted-ticket-intents")
            self.assertEqual(self.fresh("proposal_closeout").JOURNAL_ROOT, old / "proposal-closeout")

    def tearDown(self):
        for name in ("local_ledger_runtime", "proposal_closeout_local", "local_ticket_journal",
                     "hosted_ticket", "proposal_closeout"):
            sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
