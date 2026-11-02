"""formal-deferral: the deferred-item criterion and what the module stage makes of it. No network."""
import tempfile
import unittest
from pathlib import Path

from module_stage import (OPEN_ITEM, SUSPEND_MARKER, UNCHECKED, at_final_gate, deferral_lint, deferred_items,
                          first_open_is_gate, module_state)

DEFERRED_FORMS = [
    "- [ ] 延期：故障注入用例；恢复条件：Mock 服务支持故障注入",
    "- [ ] 延期: 故障注入用例; 恢复条件: Mock 服务支持故障注入",
    "- [ ] Deferred: fault injection; Resume when: the mock supports it",
    "- [ ] deferred : fault injection ; resume WHEN : the mock supports it",
    "* [ ] 延期：真实入口联调；Resume when: 后台入口上线",
    "  - [ ] DEFERRED: nested item; Resume when: later",
]
NOT_DEFERRED = [
    "- [ ] 延期：故障注入用例",                                # no resume condition
    "- [ ] 延期：故障注入用例；恢复条件：",                     # empty condition
    "- [ ] 延期：故障注入用例；恢复条件：   ",                  # blank condition
    "- [ ] 延期：；恢复条件：Mock 上线",                        # empty item
    "- [ ] 故障注入用例延期；恢复条件：Mock 上线",              # prefix not at the start
    "- [ ] 延期：检查点（gate）：最终验收；恢复条件：以后",     # a checkpoint cannot be deferred
    "- [ ] 延期：Checkpoint 2: acceptance; Resume when: later",
    "- [ ] 延期：最终验收（gate）；恢复条件：以后",
    "- [ ] Postponed: x; Resume when: y",
]


class Criterion(unittest.TestCase):
    def test_formal_forms_are_deferred_and_not_open(self):
        for line in DEFERRED_FORMS:
            with self.subTest(line=line):
                self.assertEqual(len(deferred_items(line + "\n")), 1)
                self.assertIsNone(UNCHECKED.search(line))
                self.assertIsNone(OPEN_ITEM.match(line))

    def test_other_forms_stay_open(self):
        for line in NOT_DEFERRED:
            with self.subTest(line=line):
                self.assertEqual(deferred_items(line + "\n"), [])
                self.assertIsNotNone(UNCHECKED.search(line))
                self.assertIsNotNone(OPEN_ITEM.match(line))

    def test_checked_items_are_done_not_deferred(self):
        self.assertEqual(deferred_items("- [x] 延期：a；恢复条件：b\n"), [])

    def test_item_and_condition_are_extracted_in_order(self):
        text = ("- [x] built\n- [ ] 延期：故障注入；恢复条件：Mock 上线\n- [ ] ordinary\n"
                "- [ ] Deferred: real entry; Resume when: backoffice ships\n")
        self.assertEqual(deferred_items(text), [("故障注入", "Mock 上线"), ("real entry", "backoffice ships")])

    def test_deferral_inside_a_code_block_is_still_an_ordinary_line(self):
        # The todo checklist has no code-block exemption today; a deferral there counts like any other line.
        self.assertEqual(len(deferred_items("```\n- [ ] 延期：a；恢复条件：b\n```\n")), 1)


class Lint(unittest.TestCase):
    def test_kinds_and_line_numbers(self):
        text = ("- [x] 延期：done；恢复条件：x\n"
                "- [ ] 延期：a；恢复条件：b\n"
                "- [ ] 延期：a\n"
                "- [ ] 延期：检查点 1：验收；恢复条件：b\n"
                "- [ ] Deferred: final acceptance (gate); Resume when: b\n"
                "- [ ] D1：延期未验\n"
                "- [ ] ordinary\n"
                "延期说明，不是清单项\n")
        self.assertEqual(deferral_lint(text), [("formal", 2), ("malformed", 3), ("checkpoint", 4), ("checkpoint", 5),
                                               ("informal", 6)])


class Project:
    def __init__(self, todo):
        self.text = todo

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "alpha.md").write_text("# alpha\n", encoding="utf-8")
        (self.root / "tasks" / "alpha").mkdir(parents=True)
        (self.root / "tasks" / "alpha" / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (self.root / "tasks" / "alpha" / "todo.md").write_text(self.text, encoding="utf-8")
        return self

    def state(self):
        return module_state(self.root, "alpha")

    def __exit__(self, *exc):
        self.tmp.cleanup()


class Stage(unittest.TestCase):
    def test_only_deferred_items_left_is_done(self):
        with Project("- [x] built\n- [ ] 延期：故障注入；恢复条件：Mock 上线\n") as project:
            state = project.state()
            self.assertEqual(state["stage"], "DONE")
            self.assertEqual(state["open"], 0)
            self.assertFalse(state["half"])
            self.assertEqual(state["deferred"], [("故障注入", "Mock 上线")])

    def test_deferred_beside_open_work_is_still_building(self):
        with Project("- [x] built\n- [ ] 延期：a；恢复条件：b\n- [ ] ordinary\n") as project:
            state = project.state()
            self.assertEqual(state["stage"], "BUILDING")
            self.assertEqual(state["open"], 1)
            self.assertEqual(len(state["deferred"]), 1)

    def test_deferral_without_condition_keeps_the_module_open(self):
        with Project("- [x] built\n- [ ] 延期：故障注入\n") as project:
            state = project.state()
            self.assertEqual(state["stage"], "BUILDING")
            self.assertEqual(state["deferred"], [])

    def test_removing_the_prefix_reopens_the_module(self):
        with Project("- [x] built\n- [ ] 故障注入\n") as project:
            self.assertEqual(project.state()["stage"], "BUILDING")

    def test_no_deferral_has_an_empty_list(self):
        with Project("- [x] built\n") as project:
            self.assertEqual(project.state()["deferred"], [])

    def test_suspend_marker_with_only_deferred_items_is_stale(self):
        with Project("- [x] built\n- [ ] 延期：a；恢复条件：b\n%s\n" % SUSPEND_MARKER) as project:
            state = project.state()
            self.assertFalse(state["suspended"])
            self.assertEqual(state["stage"], "DONE")


class Gates(unittest.TestCase):
    def test_deferred_item_before_the_final_gate_does_not_hide_it(self):
        todo = "- [x] Task 1\n- [ ] 延期：故障注入；恢复条件：Mock 上线\n- [ ] Checkpoint 1 (gate): final acceptance\n"
        with Project(todo) as project:
            self.assertTrue(first_open_is_gate(project.root, "alpha"))
            self.assertTrue(at_final_gate(project.root, "alpha"))


if __name__ == "__main__":
    unittest.main()
