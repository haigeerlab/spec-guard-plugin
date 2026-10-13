"""The link from a session directory to the project it works on: parsing, validation and the command. No network."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from project_link import LINK_PATH, resolve

SCRIPT = str(Path(__file__).with_name("project_link.py"))


class Dirs:
    """A session directory with no convention and a project directory beside it; names carry a space and CJK."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.session = base / "需求 文档"
        self.project = base / "the project"
        self.session.mkdir()
        self.project.mkdir()
        return self

    def link(self, content):
        path = self.session / LINK_PATH
        path.parent.mkdir(exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
        return path

    def __exit__(self, *exc):
        self.tmp.cleanup()


class Resolve(unittest.TestCase):
    def test_no_file_is_none(self):
        with Dirs() as dirs:
            self.assertEqual(resolve(dirs.session), ("none", None))
            (dirs.session / ".agent").mkdir()
            self.assertEqual(resolve(dirs.session), ("none", None))

    def test_absolute_path(self):
        with Dirs() as dirs:
            dirs.link({"version": 1, "project": str(dirs.project)})
            self.assertEqual(resolve(dirs.session), ("ok", dirs.project))

    def test_relative_path_is_relative_to_the_session_directory(self):
        with Dirs() as dirs:
            dirs.link({"version": 1, "project": "../the project"})
            self.assertEqual(resolve(dirs.session), ("ok", dirs.project))
            here = os.getcwd()
            os.chdir(dirs.project)
            try:
                self.assertEqual(resolve(dirs.session), ("ok", dirs.project))
            finally:
                os.chdir(here)

    def test_a_symlinked_target_resolves_to_the_real_directory(self):
        with Dirs() as dirs:
            alias = dirs.session.parent / "alias"
            alias.symlink_to(dirs.project, target_is_directory=True)
            dirs.link({"version": 1, "project": str(alias)})
            self.assertEqual(resolve(dirs.session), ("ok", dirs.project))

    def test_invalid_forms(self):
        with Dirs() as dirs:
            for content in ("{broken", "[]", '"x"', {"project": str(dirs.project)},
                            {"version": 2, "project": str(dirs.project)},
                            {"version": "1", "project": str(dirs.project)},
                            {"version": True, "project": str(dirs.project)},
                            {"version": 1, "project": ""}, {"version": 1, "project": "   "},
                            {"version": 1, "project": 3}, {"version": 1},
                            {"version": 1, "project": str(dirs.project), "extra": 1},
                            {"version": 1, "project": str(dirs.project) + "\nx"}):
                dirs.link(content)
                self.assertEqual(resolve(dirs.session), ("invalid", None), content)

    def test_a_link_that_is_not_a_readable_file_is_invalid(self):
        with Dirs() as dirs:
            (dirs.session / LINK_PATH).mkdir(parents=True)
            self.assertEqual(resolve(dirs.session), ("invalid", None))

    def test_missing_target(self):
        with Dirs() as dirs:
            dirs.link({"version": 1, "project": str(dirs.project / "gone")})
            self.assertEqual(resolve(dirs.session)[0], "missing")
            file_target = dirs.project / "file.txt"
            file_target.write_text("x", encoding="utf-8")
            dirs.link({"version": 1, "project": str(file_target)})
            self.assertEqual(resolve(dirs.session)[0], "missing")


if __name__ == "__main__":
    unittest.main()
