"""Host MCP registration goes through the Claude CLI only; never real user configuration."""
import subprocess
import unittest
from unittest.mock import patch

from host_config_removal import add_claude_server


class AddClaudeServerTests(unittest.TestCase):
    def test_registers_with_a_single_add_call(self):
        with patch("host_config_removal.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "Added", "")) as run:
            add_claude_server("claude", ["add", "--scope", "user", "x", "--", "cmd"], "x")
        self.assertEqual([call.args[0] for call in run.call_args_list],
                         [["claude", "mcp", "add", "--scope", "user", "x", "--", "cmd"]])

    def test_existing_name_and_other_failures_are_distinct_errors(self):
        for output, pattern in (
                ("MCP server x already exists in user config", "already exists; refusing"),
                ("Invalid command path", "rejected MCP registration for x: Invalid command path")):
            with self.subTest(output=output), patch(
                    "host_config_removal.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, "", output)):
                with self.assertRaisesRegex(ValueError, pattern):
                    add_claude_server("claude", ["add", "x"], "x")
        with patch("host_config_removal.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(["claude"], 30)):
            with self.assertRaisesRegex(ValueError, "unable to run"):
                add_claude_server("claude", ["add", "x"], "x")


if __name__ == "__main__":
    unittest.main()
