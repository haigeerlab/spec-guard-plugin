#!/usr/bin/env python3
"""The Local ticket modules must not import the top-level CLI (2026-10-08 audit F15).

`local_ticket_portability.py` is the command-line entry point and imports the ticket modules; when they imported
`InventoryError` and the inventory helpers back from it, every pair formed an import cycle. The shared code lives in
`local_ticket_inventory.py`; the CLI re-exports its names so existing callers keep working.
"""
import ast
import subprocess
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
CLI = "local_ticket_portability"


def ticket_modules():
    return sorted(path for path in HOOKS.glob("local_ticket_*.py")
                  if path.stem != CLI and not path.name.startswith("test_"))


def imports_cli(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == CLI:
            return True
        if isinstance(node, ast.Import) and any(alias.name == CLI for alias in node.names):
            return True
    return False


class LocalTicketImportTests(unittest.TestCase):
    def test_modules_found(self):
        # Zero modules would make the other tests pass vacuously.
        self.assertGreaterEqual(len(ticket_modules()), 10)

    def test_no_ticket_module_imports_the_cli(self):
        offenders = [path.name for path in ticket_modules() if imports_cli(path)]
        self.assertEqual(offenders, [])

    def test_importing_a_ticket_module_does_not_load_the_cli(self):
        for path in ticket_modules():
            with self.subTest(module=path.stem):
                code = ("import sys; sys.path.insert(0, %r); import %s; print(%r in sys.modules)"
                        % (str(HOOKS), path.stem, CLI))
                result = subprocess.run([sys.executable, "-B", "-c", code],
                                        capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "False")

    def test_cli_still_exports_the_inventory_names(self):
        sys.path.insert(0, str(HOOKS))
        import local_ticket_inventory
        import local_ticket_portability
        for name in ("InventoryError", "inventory_project", "worktree_roots", "_event_lines"):
            with self.subTest(name=name):
                self.assertIs(getattr(local_ticket_portability, name), getattr(local_ticket_inventory, name))


if __name__ == "__main__":
    unittest.main()
