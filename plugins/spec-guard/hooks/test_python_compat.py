"""Keep shipped hook modules importable on the macOS system Python (3.9).

`X | None` in an annotation is evaluated at import time before Python 3.10 unless the
module defers annotations. A failing import turns the phase injection into UNKNOWN.
"""
import ast
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HOOKS = Path(__file__).resolve().parent
SYSTEM_PYTHON = "/usr/bin/python3"


def modules():
    return sorted(path for path in HOOKS.glob("*.py") if not path.name.startswith("test"))


def _annotations(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = node.args
            for argument in (arguments.posonlyargs + arguments.args + arguments.kwonlyargs
                             + [arguments.vararg, arguments.kwarg]):
                if argument is not None and argument.annotation is not None:
                    yield argument.annotation
            if node.returns is not None:
                yield node.returns
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def needs_deferred_annotations(source):
    """True when an annotation uses `|` but the module does not defer annotations."""
    tree = ast.parse(source)
    deferred = any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
                   and any(alias.name == "annotations" for alias in node.names)
                   for node in tree.body)
    uses_union = any(isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitOr)
                     for annotation in _annotations(tree) for inner in ast.walk(annotation))
    return uses_union and not deferred


def old_system_python():
    if not os.access(SYSTEM_PYTHON, os.X_OK):
        return None
    result = subprocess.run([SYSTEM_PYTHON, "-c", "import sys; print(sys.version_info < (3, 10))"],
                            capture_output=True, text=True, check=False)
    return SYSTEM_PYTHON if result.stdout.strip() == "True" else None


class CheckerTests(unittest.TestCase):
    def test_union_annotation_without_future_import_is_flagged(self):
        self.assertTrue(needs_deferred_annotations("def f(x: int | None) -> None:\n    pass\n"))
        self.assertTrue(needs_deferred_annotations("x: tuple[int, int] | None = None\n"))

    def test_deferred_or_non_annotation_union_is_allowed(self):
        self.assertFalse(needs_deferred_annotations(
            "from __future__ import annotations\ndef f(x: int | None) -> str | None:\n    pass\n"))
        self.assertFalse(needs_deferred_annotations("flags = 1 | 2\n"))


class ShippedModuleTests(unittest.TestCase):
    def test_modules_exist(self):
        self.assertGreater(len(modules()), 10)

    def test_union_annotations_are_deferred(self):
        for path in modules():
            with self.subTest(module=path.name):
                self.assertFalse(needs_deferred_annotations(path.read_text(encoding="utf-8")),
                                 "add `from __future__ import annotations`")

    def test_every_module_imports_on_old_system_python(self):
        python = old_system_python()
        if python is None:
            self.skipTest("no Python older than 3.10 at %s" % SYSTEM_PYTHON)
        with tempfile.TemporaryDirectory() as workdir:
            for path in modules():
                with self.subTest(module=path.name):
                    result = subprocess.run(
                        [python, "-c",
                         "import importlib.util, sys; sys.path.insert(0, sys.argv[1]); "
                         "spec = importlib.util.spec_from_file_location('m', sys.argv[2]); "
                         "module = sys.modules['m'] = importlib.util.module_from_spec(spec); "
                         "spec.loader.exec_module(module)",
                         str(HOOKS), str(path)],
                        cwd=workdir, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr.strip().splitlines()[-1:])


if __name__ == "__main__":
    unittest.main()
