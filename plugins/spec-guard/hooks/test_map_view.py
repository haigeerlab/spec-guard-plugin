"""map-view: the read-only module progress table and its JSON. No network."""
import json
import re
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from module_stage import SUSPEND_MARKER

SCRIPT = str(Path(__file__).with_name("map_view.py"))
PLUGIN_JSON = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
REASON_PREFIX = "<!-- spec-guard: suspended-reason: "
PENDING = "<!-- spec-guard: review pending -->"
APPROVED_PLAN = "<!-- spec-guard: review approved -->"

TOP_KEYS = {"schemaVersion", "generatedAt", "generator", "project", "head", "stage", "activeModule",
            "nextGate", "totals", "bottlenecks", "awaitingReview", "modules", "history", "reviewCadence"}
MODULE_KEYS = {"id", "position", "responsibility", "dependsOn", "status", "step", "progress",
               "suspendedReason", "blockedOn", "missingDeps", "blocks", "review", "lastTickAt", "suspendedAt",
               "firstTickAt", "tickCommits", "externalReview", "uncommittedTicks", "startedAt", "gates"}
HEAD_KEYS = {"sha", "branch", "unmerged", "unpushed", "committedAt"}
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def spec_approved(module):
    """A Spec carrying a valid digest approval, made with the plugin's own marker tool."""
    return "# %s\n\nbody\n" % module


class Project:
    """Writes a capability map and per-module files into a temporary directory."""

    def __init__(self, rows, order, files, active=None):
        self.rows, self.order, self.files, self.active = rows, order, files, active

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "proj"
        (self.root / "spec").mkdir(parents=True)
        table = "".join("| %s | %s | %s |\n" % row for row in self.rows)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(
            "# Capability Map: 测试项目\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n"
            + table + "\nBuild order: " + " → ".join(self.order) + "\n", encoding="utf-8")
        for rel, text in self.files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        if self.active:
            (self.root / ".agent").mkdir()
            (self.root / ".agent" / "state.json").write_text(json.dumps({"activeModule": self.active}),
                                                            encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def run(self, *args, project=True, env=None, cwd=None):
        cmd = [sys.executable, "-B", SCRIPT, *args]
        if project:
            cmd += ["--project", str(self.root)]
        full_env = dict(os.environ)
        full_env.pop("CLAUDE_PROJECT_DIR", None)
        full_env.update(env or {})
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=full_env,
                              cwd=cwd or self.tmp.name)

    def json(self, *args):
        done = self.run("--json", *args)
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    def git(self, *args):
        subprocess.run(GIT + list(args), cwd=self.root, check=True, capture_output=True, timeout=30)


def approve_spec(root, module):
    """Approve a Spec with the real marker tool so the digest is right."""
    tool = Path(__file__).with_name("review_mark.py")
    subprocess.run([sys.executable, "-B", str(tool), "--project", str(root), "--module", module,
                    "--target", "spec", "--state", "approved", "--confirm"],
                   check=True, capture_output=True, timeout=30)


# a done; b suspended (reason) under a; c, d blocked through b; e ready; f waits on e;
# g has only a pending Spec; h is the current module mid-build; i depends on c and e (diamond).
ROWS = [("a", "基础", "—"), ("b", "质量门禁", "a"), ("c", "下游一", "b"), ("d", "下游二", "c"),
        ("e", "可开工", "a"), ("f", "等 e", "e"), ("g", "写 Plan 中", "a"), ("h", "构建中", "a"),
        ("i", "两路依赖", "c, e")]
ORDER = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
FILES = {
    "spec/a.md": spec_approved("a"), "tasks/a/plan.md": "# Plan\n\n" + APPROVED_PLAN + "\n",
    "tasks/a/todo.md": "- [x] one\n- [x] Checkpoint 1（gate）：评审\n",
    "spec/b.md": "# b\n", "tasks/b/plan.md": "# Plan\n",
    "tasks/b/todo.md": "- [x] one\n- [ ] two\n" + SUSPEND_MARKER + "\n" + REASON_PREFIX + "上游漏洞 -->\n",
    "spec/g.md": "# g\n\n" + PENDING + "\n",
    "spec/h.md": "# h\n", "tasks/h/plan.md": "# Plan\n\n" + PENDING + "\n",
    "tasks/h/todo.md": "- [x] t1\n- [ ] t2\n- [ ] Checkpoint 1（gate）：模块评审\n",
}


def fixture():
    project = Project(ROWS, ORDER, FILES, active="h")
    return project


class StatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = fixture().__enter__()
        approve_spec(cls.project.root, "a")
        cls.data = cls.project.json()
        cls.by_id = {m["id"]: m for m in cls.data["modules"]}

    @classmethod
    def tearDownClass(cls):
        cls.project.__exit__(None, None, None)

    def test_six_states(self):
        got = {m: self.by_id[m]["status"] for m in ORDER}
        self.assertEqual(got, {"a": "done", "b": "suspended", "c": "blocked", "d": "blocked", "e": "ready",
                               "f": "not_ready", "g": "in_progress", "h": "in_progress", "i": "blocked"})
        self.assertEqual(self.data["totals"], {"done": 1, "in_progress": 2, "suspended": 1, "blocked": 3,
                                               "ready": 1, "not_ready": 1})

    def test_position_and_fields(self):
        self.assertEqual([m["position"] for m in self.data["modules"]], list(range(1, 10)))
        self.assertEqual(self.by_id["i"]["dependsOn"], ["c", "e"])
        self.assertEqual(self.by_id["b"]["responsibility"], "质量门禁")

    def test_blocked_on_follows_the_chain_and_dedupes(self):
        self.assertEqual(self.by_id["c"]["blockedOn"], ["b"])
        self.assertEqual(self.by_id["d"]["blockedOn"], ["b"])
        self.assertEqual(self.by_id["i"]["blockedOn"], ["b"])
        self.assertEqual(self.by_id["e"]["blockedOn"], [])

    def test_missing_deps_are_direct_only(self):
        self.assertEqual(self.by_id["f"]["missingDeps"], ["e"])
        self.assertEqual(self.by_id["c"]["missingDeps"], [])

    def test_blocks_count_transitive_not_done(self):
        self.assertEqual(self.by_id["b"]["blocks"], {"count": 3, "ids": ["c", "d", "i"]})
        self.assertEqual(self.by_id["e"]["blocks"], {"count": 2, "ids": ["f", "i"]})
        self.assertEqual(self.by_id["a"]["blocks"]["count"], 8)
        self.assertEqual(self.by_id["d"]["blocks"], {"count": 0, "ids": []})

    def test_bottlenecks(self):
        self.assertEqual(self.data["bottlenecks"],
                         [{"id": "b", "suspendedReason": "上游漏洞", "blocks": ["c", "d", "i"]}])

    def test_step_and_progress(self):
        self.assertEqual(self.by_id["g"]["step"], "plan")
        self.assertEqual(self.by_id["h"]["step"], "build")
        self.assertEqual(self.by_id["h"]["progress"], {"done": 1, "total": 3})
        self.assertEqual(self.by_id["g"]["progress"], {"done": 0, "total": 0})
        for module in ("a", "b", "c", "e", "f"):
            self.assertIsNone(self.by_id[module]["step"], module)

    def test_review_values_and_awaiting(self):
        self.assertEqual(self.by_id["a"]["review"], {"spec": "approved", "plan": "approved"})
        self.assertEqual(self.by_id["c"]["review"], {"spec": "none", "plan": "none"})
        self.assertEqual(self.data["awaitingReview"], [{"id": "g", "kind": "spec", "review": "pending"},
                                                       {"id": "h", "kind": "plan", "review": "pending"}])

    def test_project_level_fields(self):
        self.assertEqual(self.data["stage"], "BUILDING")
        self.assertEqual(self.data["activeModule"], "h")
        self.assertEqual(self.data["nextGate"], "Checkpoint 1（gate）：模块评审")
        self.assertEqual(self.data["project"], {"root": str(self.project.root.resolve()), "title": "Capability Map: 测试项目"})
        self.assertEqual(self.by_id["b"]["suspendedReason"], "上游漏洞")

    def test_key_sets_are_fixed(self):
        self.assertEqual(set(self.data), TOP_KEYS)
        self.assertEqual(self.data["schemaVersion"], 1)
        for module in self.data["modules"]:
            self.assertEqual(set(module), MODULE_KEYS)
        self.assertEqual(set(self.data["head"]), HEAD_KEYS)
        self.assertEqual(set(self.data["totals"]),
                         {"done", "in_progress", "suspended", "blocked", "ready", "not_ready"})

    def test_generator_and_time(self):
        version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
        self.assertEqual(self.data["generator"], {"name": "spec-guard", "version": version})
        self.assertRegex(self.data["generatedAt"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_not_a_git_repository(self):
        self.assertEqual(self.data["head"], {"sha": None, "branch": None, "unmerged": None, "unpushed": None,
                                             "committedAt": None})
        self.assertEqual(self.data["history"], "unavailable")
        self.assertTrue(all(m["lastTickAt"] is None and m["suspendedAt"] is None and m["firstTickAt"] is None
                            and m["tickCommits"] is None and m["uncommittedTicks"] is None
                            and m["startedAt"] is None for m in self.data["modules"]))
        self.assertIn("（没有 git 历史：不显示勾选与挂起时间）", self.project.run().stdout)

    def test_table_header_and_rows(self):
        out = self.project.run().stdout
        lines = out.splitlines()
        self.assertIn("Capability Map: 测试项目 · 9 个模块 · ✅ 1 🔨 2 ⏸ 1 ⛔ 3 🟢 1 ○ 1 · ", lines[0])
        self.assertIn("关键卡点：b 挂起（上游漏洞）→ 挡住 3 个：c、d、i", out)
        self.assertIn("待批准：g Spec（待批准）、h Plan（待批准）", out)
        self.assertIn("下一个 gate：Checkpoint 1（gate）：模块评审", out)
        self.assertIn("未合入主线：判断不了；未推送：判断不了", out)
        self.assertIn("| 2 | b | 质量门禁 | ⏸ 挂起（上游漏洞），挡住 3 个 | Spec 无标记 Plan 无标记 |", out)
        self.assertIn("| 3 | c | 下游一 | ⛔ 阻塞：等 b | — |", out)
        self.assertIn("| 5 | e | 可开工 | 🟢 可以开始 | — |", out)
        self.assertIn("| 7 | g | 写 Plan 中 | 🔨 写 Plan | Spec 待批准 |", out)
        self.assertIn("| 8 | h | 构建中 | 🔨 进行中 1/3 | Spec 无标记 Plan 待批准 |", out)
        self.assertIn("| 1 | a | 基础 | ✅ 已完成 | Spec ✔ Plan ✔ |", out)
        self.assertIn("| 6 | 1 个未就绪 | | ○ | |", out)
        self.assertNotIn("| 6 | f |", out)

    def test_all_expands(self):
        out = self.project.run("--all").stdout
        self.assertIn("| 6 | f | 等 e | ○ 未就绪：缺 e | — |", out)
        self.assertNotIn("个未就绪", out)


class FoldTest(unittest.TestCase):
    ROWS = [("p1", "x" * 60, "—"), ("p2", "y", "p1"), ("p3", "z", "p2"), ("q", "w", "p3")]
    DONE = "- [x] one\n"

    def make(self):
        files = {}
        for module in ("p1", "p2", "p3"):
            files["spec/%s.md" % module] = "# %s\n" % module
            files["tasks/%s/plan.md" % module] = "# Plan\n"
            files["tasks/%s/todo.md" % module] = self.DONE
        files["spec/q.md"] = "# q\n\n<!-- spec-guard: review approved 000000000000 -->\n"
        return Project(self.ROWS, ["p1", "p2", "p3", "q"], files)

    def test_done_rows_fold_except_the_last(self):
        with self.make() as project:
            out = project.run().stdout
            self.assertIn("| 1–2 | 其余 2 个已完成 | | ✅ | |", out)
            self.assertIn("| 3 | p3 |", out)
            self.assertNotIn("| 1 | p1 |", out)
            full = project.run("--all").stdout
            self.assertIn("| 1 | p1 | " + "x" * 40 + "… |", full)

    def test_revised_and_invalid_reviews_are_awaiting(self):
        with self.make() as project:
            data = project.json()
            self.assertEqual(data["awaitingReview"], [{"id": "q", "kind": "spec", "review": "revised"}])
            self.assertIn("待批准：q Spec（改过待重审）", project.run().stdout)
            (project.root / "spec" / "q.md").write_text("# q\n\n%s\n%s\n" % (PENDING, PENDING), encoding="utf-8")
            data = project.json()
            self.assertEqual(data["awaitingReview"], [{"id": "q", "kind": "spec", "review": "invalid"}])
            self.assertIn("Spec 标记无效", project.run().stdout)

    def test_stage_done_and_no_bottleneck(self):
        with self.make() as project:
            (project.root / "spec" / "q.md").write_text("# q\n", encoding="utf-8")
            (project.root / "tasks" / "q").mkdir()
            (project.root / "tasks" / "q" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (project.root / "tasks" / "q" / "todo.md").write_text(self.DONE, encoding="utf-8")
            data = project.json()
            self.assertEqual(data["stage"], "DONE")
            self.assertEqual(data["bottlenecks"], [])
            out = project.run().stdout
            self.assertIn("关键卡点：无", out)
            self.assertIn("待批准：无", out)

    def test_control_characters_are_cleaned(self):
        with self.make() as project:
            todo = project.root / "tasks" / "p3" / "todo.md"
            todo.write_text("- [x] one\n- [ ] two\n%s\n%s\x1b[31m红|字 -->\n" % (SUSPEND_MARKER, REASON_PREFIX),
                            encoding="utf-8")
            out = project.run().stdout
            self.assertIn("⏸ 挂起（[31m红字）", out)
            self.assertNotIn("\x1b", out)
            self.assertEqual(project.json()["modules"][2]["suspendedReason"], "\x1b[31m红|字")

    def test_suspended_without_reason(self):
        with self.make() as project:
            todo = project.root / "tasks" / "p3" / "todo.md"
            todo.write_text("- [x] one\n- [ ] two\n%s\n" % SUSPEND_MARKER, encoding="utf-8")
            self.assertIsNone(project.json()["modules"][2]["suspendedReason"])
            self.assertIn("⏸ 挂起（未记原因），挡住 1 个", project.run().stdout)

    def test_reason_written_by_module_suspend_round_trips(self):
        with self.make() as project:
            (project.root / "tasks" / "p3" / "todo.md").write_text("- [x] one\n- [ ] two\n", encoding="utf-8")
            tool = Path(__file__).with_name("module_suspend.py")
            subprocess.run([sys.executable, "-B", str(tool), "--project", str(project.root), "--suspend", "p3",
                            "--reason", "等上游修复", "--confirm"], check=True, capture_output=True, timeout=30)
            self.assertEqual(project.json()["bottlenecks"], [{"id": "p3", "suspendedReason": "等上游修复",
                                                              "blocks": ["q"]}])

    def test_reason_line_without_marker_is_ignored(self):
        with self.make() as project:
            todo = project.root / "tasks" / "p3" / "todo.md"
            todo.write_text("- [x] one\n- [ ] two\n%s旧原因 -->\n" % REASON_PREFIX, encoding="utf-8")
            module = project.json()["modules"][2]
            self.assertEqual(module["status"], "in_progress")
            self.assertIsNone(module["suspendedReason"])


class ExternalReviewTest(unittest.TestCase):
    """plugin-interface: externalReview per module, read from the Spec and the todo (delegate-review-hint)."""

    ROWS = [("a", "x", "—"), ("b", "y", "—"), ("c", "z", "—"), ("d", "w", "—")]

    def test_values(self):
        files = {
            "spec/a.md": "# a\n\n## 外部审查意见\n\n- delegate（codex）：completed，findings，2 条\n",
            "spec/b.md": "# b\n", "tasks/b/plan.md": "# Plan\n",
            "tasks/b/todo.md": "- [ ] t\n\n## External review\n- recorded\n",
            "spec/c.md": "# c\n\n<!-- spec-guard: external-review declined -->\n",
            "spec/d.md": "# d\n\n## 外部审查意见\n\n",
        }
        with Project(self.ROWS, ["a", "b", "c", "d"], files) as project:
            got = {m["id"]: m["externalReview"] for m in project.json()["modules"]}
        self.assertEqual(got, {"a": "recorded", "b": "recorded", "c": "declined", "d": "none"})

    def test_unreadable_todo_is_exit_4(self):
        files = {"spec/a.md": "# a\n", "tasks/a/plan.md": "# Plan\n", "tasks/a/todo.md": "- [ ] t\n"}
        with Project(self.ROWS[:1], ["a"], files) as project:
            todo = project.root / "tasks" / "a" / "todo.md"
            todo.chmod(0)
            try:
                done = project.run("--json")
            finally:
                todo.chmod(0o644)
            self.assertEqual(done.returncode, 4, done.stdout)
            self.assertEqual(json.loads(done.stdout)["error"], "unreadable")


class ExitCodeTest(unittest.TestCase):
    def test_no_capability_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", tmp, "--json"],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 3)
            self.assertEqual(json.loads(done.stdout), {"schemaVersion": 1, "error": "no-capability-map"})
            self.assertTrue(done.stderr.strip())
            plain = subprocess.run([sys.executable, "-B", SCRIPT, "--project", tmp],
                                   capture_output=True, text=True, timeout=30)
            self.assertEqual((plain.returncode, plain.stdout), (3, ""))

    def test_unreadable_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "spec").mkdir()
            (Path(tmp) / "spec" / "CAPABILITY-MAP.md").write_text("# Map\n\nno table here\n", encoding="utf-8")
            done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", tmp, "--json"],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 4)
            data = json.loads(done.stdout)
            self.assertEqual((data["schemaVersion"], data["error"]), (1, "unreadable"))
            self.assertTrue(data["detail"])

    def test_bad_project_path_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            for target in (str(Path(tmp) / "missing"), __file__):
                done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", target, "--json"],
                                      capture_output=True, text=True, timeout=30)
                self.assertEqual(done.returncode, 2, target)
                self.assertEqual(done.stdout, "")

    def test_project_from_environment(self):
        with fixture() as project:
            done = project.run("--json", project=False, env={"CLAUDE_PROJECT_DIR": str(project.root)})
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["activeModule"], "h")


class GitTest(unittest.TestCase):
    def test_unpushed_and_unmerged(self):
        with fixture() as project:
            remote = Path(project.tmp.name) / "remote.git"
            subprocess.run(GIT + ["init", "--bare", str(remote)], check=True, capture_output=True, timeout=30)
            project.git("init")
            project.git("add", "-A")
            project.git("commit", "-m", "一")
            project.git("remote", "add", "origin", str(remote))
            project.git("push", "-u", "origin", "main")
            (project.root / "extra.txt").write_text("x", encoding="utf-8")
            project.git("add", "-A")
            project.git("commit", "-m", "二")
            head = project.json()["head"]
            self.assertEqual(head["branch"], "main")
            self.assertRegex(head["sha"], r"^[0-9a-f]{40}$")
            self.assertEqual(head["unpushed"], {"count": 1, "upstream": "origin/main"})
            self.assertEqual(head["unmerged"], {"count": 1, "base": "origin/main"})
            self.assertIn("未合入主线：1 个提交（相对 origin/main）；未推送：1 个提交", project.run().stdout)
            project.git("checkout", "--detach")
            head = project.json()["head"]
            self.assertIsNone(head["branch"])
            self.assertIsNone(head["unpushed"])

    def test_branch_without_upstream(self):
        with fixture() as project:
            project.git("init")
            project.git("add", "-A")
            project.git("commit", "-m", "一")
            head = project.json()["head"]
            self.assertEqual(head["branch"], "main")
            self.assertIsNone(head["unpushed"])
            self.assertIsNone(head["unmerged"])



class HistoryTest(unittest.TestCase):
    """lastTickAt / suspendedAt / history from committed git history only."""
    ROWS = [("alpha", "甲", "—"), ("beta", "乙", "alpha")]

    def make(self):
        files = {"spec/alpha.md": "# alpha\n", "spec/beta.md": "# beta\n",
                 "tasks/alpha/plan.md": "# Plan\n", "tasks/beta/plan.md": "# Plan\n",
                 "tasks/alpha/todo.md": "- [ ] a\n- [ ] b\n", "tasks/beta/todo.md": "- [ ] x\n- [ ] y\n"}
        return Project(self.ROWS, ["alpha", "beta"], files)

    @staticmethod
    def commit(project, when, message="改"):
        env = dict(os.environ, GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
        subprocess.run(GIT + ["add", "-A"], cwd=project.root, check=True, capture_output=True, timeout=30)
        subprocess.run(GIT + ["commit", "-q", "-m", message], cwd=project.root, check=True, capture_output=True,
                       timeout=30, env=env)

    @staticmethod
    def write(project, module, text):
        (project.root / "tasks" / module / "todo.md").write_text(text, encoding="utf-8")

    def history(self, project):
        project.git("init")
        self.commit(project, "2026-10-01T10:00:00+08:00")
        self.write(project, "alpha", "* [X] a\n- [ ] b\n")
        self.commit(project, "2026-10-02T10:00:00+08:00")
        self.write(project, "alpha", "* [X] a\n- [ ] b2\n")
        self.commit(project, "2026-10-03T10:00:00+08:00")
        self.write(project, "alpha", "* [ ] a\n- [ ] b2\n")
        self.write(project, "beta", "- [x] x\n- [ ] y\n")
        self.commit(project, "2026-10-04T10:00:00+08:00")
        self.write(project, "alpha", "* [X] a\n- [ ] b2\n%s\n%s等上游 -->\n" % (SUSPEND_MARKER, REASON_PREFIX))
        self.commit(project, "2026-10-05T10:00:00+08:00")

    def test_ticks_and_suspension_times(self):
        with self.make() as project:
            self.history(project)
            data = project.json()
            by_id = {m["id"]: m for m in data["modules"]}
            self.assertEqual(data["history"], "complete")
            # the re-tick in the suspending commit counts; the text edit and the untick did not move it
            self.assertEqual(by_id["alpha"]["lastTickAt"], "2026-10-05T10:00:00+08:00")
            self.assertEqual(by_id["alpha"]["suspendedAt"], "2026-10-05T10:00:00+08:00")
            self.assertEqual(by_id["beta"]["lastTickAt"], "2026-10-04T10:00:00+08:00")
            self.assertIsNone(by_id["beta"]["suspendedAt"])
            # tick commits: alpha c2 and c5 (the untick in c4 and the text edit in c3 are not ticks)
            self.assertEqual((by_id["alpha"]["firstTickAt"], by_id["alpha"]["tickCommits"]),
                             ("2026-10-02T10:00:00+08:00", 2))
            self.assertEqual((by_id["beta"]["firstTickAt"], by_id["beta"]["tickCommits"]),
                             ("2026-10-04T10:00:00+08:00", 1))

    def test_text_edit_and_untick_do_not_count(self):
        with self.make() as project:
            project.git("init")
            self.commit(project, "2026-10-01T10:00:00+08:00")
            self.write(project, "alpha", "- [x] a\n- [ ] b\n")
            self.commit(project, "2026-10-02T10:00:00+08:00")
            self.write(project, "alpha", "- [x] a\n- [ ] b2\n")
            self.commit(project, "2026-10-03T10:00:00+08:00")
            self.write(project, "alpha", "- [ ] a\n- [ ] b2\n")
            self.commit(project, "2026-10-04T10:00:00+08:00")
            by_id = {m["id"]: m for m in project.json()["modules"]}
            self.assertEqual(by_id["alpha"]["lastTickAt"], "2026-10-02T10:00:00+08:00")
            self.assertIsNone(by_id["beta"]["lastTickAt"])
            self.assertEqual((by_id["beta"]["firstTickAt"], by_id["beta"]["tickCommits"]), (None, 0))

    def test_uncommitted_ticks_and_markers_are_invisible(self):
        with self.make() as project:
            self.history(project)
            self.write(project, "alpha", "* [X] a\n- [ ] b2\n")
            self.commit(project, "2026-10-06T10:00:00+08:00")
            self.write(project, "alpha", "* [X] a\n- [x] b2\n- [ ] c\n%s\n" % SUSPEND_MARKER)
            by_id = {m["id"]: m for m in project.json()["modules"]}
            self.assertEqual(by_id["alpha"]["status"], "suspended")
            self.assertIsNone(by_id["alpha"]["suspendedAt"])
            self.assertEqual(by_id["alpha"]["lastTickAt"], "2026-10-05T10:00:00+08:00")

    def test_suspended_at_is_the_latest_write_not_the_first(self):
        with self.make() as project:
            self.history(project)
            self.write(project, "alpha", "* [X] a\n- [ ] b2\n")
            self.commit(project, "2026-10-06T10:00:00+08:00")
            self.write(project, "alpha", "* [X] a\n- [ ] b2\n%s\n" % SUSPEND_MARKER)
            self.commit(project, "2026-10-07T10:00:00+08:00")
            by_id = {m["id"]: m for m in project.json()["modules"]}
            self.assertEqual(by_id["alpha"]["suspendedAt"], "2026-10-07T10:00:00+08:00")

    def test_table_shows_elapsed_time(self):
        with self.make() as project:
            self.history(project)
            out = project.run(env={"SPEC_GUARD_MAP_NOW": "2026-10-07T12:00:00+08:00"}).stdout
            self.assertIn("⏸ 挂起（等上游，已挂 2 天），挡住 1 个", out)
            self.assertIn("关键卡点：alpha 挂起（等上游，已挂 2 天）→ 挡住 1 个：beta", out)
            self.assertIn("🔨 进行中 1/2，上次勾选 3 天前", out)
            out = project.run(env={"SPEC_GUARD_MAP_NOW": "2026-10-04T15:30:00+08:00"}).stdout
            self.assertIn("上次勾选 5 小时前", out)
            out = project.run(env={"SPEC_GUARD_MAP_NOW": "2026-10-04T10:30:00+08:00"}).stdout
            self.assertIn("上次勾选 不到 1 小时前", out)
            self.assertNotIn("git 历史", out)

    def test_repository_without_commits_is_unavailable(self):
        with self.make() as project:
            project.git("init")
            self.assertEqual(project.json()["history"], "unavailable")

    def test_shallow_clone(self):
        with self.make() as project:
            self.history(project)
            clone = Path(project.tmp.name) / "clone"
            subprocess.run(GIT + ["clone", "-q", "--depth", "1", "file://" + str(project.root), str(clone)],
                           check=True, capture_output=True, timeout=60)
            done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(clone), "--json"],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(json.loads(done.stdout)["history"], "shallow")
            table = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(clone)],
                                   capture_output=True, text=True, timeout=30).stdout
            self.assertIn("（浅克隆：较早的勾选可能看不到）", table)


class ProgressFactsTest(unittest.TestCase):
    """map-progress-facts: uncommittedTicks, startedAt, head.committedAt and reviewCadence."""
    ROWS = [("alpha", "甲", "—"), ("beta", "乙", "alpha"), ("gamma", "丙", "alpha")]
    NOW = {"SPEC_GUARD_MAP_NOW": "2026-10-04T10:00:00+08:00"}
    BASE = "- [x] a\n- [ ] b\n- [ ] c\n- [ ] d\n- [ ] e\n"

    def make(self, extra=None):
        files = {"spec/alpha.md": "# alpha\n", "tasks/alpha/plan.md": "# Plan\n", "tasks/alpha/todo.md": self.BASE}
        files.update(extra or {})
        return Project(self.ROWS, ["alpha", "beta", "gamma"], files)

    def init(self, project):
        project.git("init")
        HistoryTest.commit(project, "2026-10-02T10:00:00+08:00")

    @staticmethod
    def by_id(project):
        return {m["id"]: m for m in project.json()["modules"]}

    def test_uncommitted_ticks_are_counted_and_shown(self):
        with self.make() as project:
            self.init(project)
            HistoryTest.write(project, "alpha", "- [x] a\n- [x] b\n- [X] c\n* [x] d\n- [ ] e\n")
            data = project.json()
            by_id = {m["id"]: m for m in data["modules"]}
            self.assertEqual(by_id["alpha"]["uncommittedTicks"], 3)
            self.assertEqual(by_id["beta"]["uncommittedTicks"], 0)
            self.assertEqual(data["head"]["committedAt"], "2026-10-02T10:00:00+08:00")
            out = project.run(env=self.NOW).stdout
            self.assertIn("🔨 进行中 4/5，上次勾选 2 天前，3 项勾选未提交（最后一次提交 2 天前）", out)

    def test_committed_ticks_leave_the_table_unchanged(self):
        with self.make() as project:
            self.init(project)
            before = project.run(env=self.NOW).stdout
            HistoryTest.write(project, "alpha", "- [x] a\n- [x] b\n- [ ] c\n- [ ] d\n- [ ] e\n")
            HistoryTest.commit(project, "2026-10-03T10:00:00+08:00")
            self.assertEqual(self.by_id(project)["alpha"]["uncommittedTicks"], 0)
            after = project.run(env=self.NOW).stdout
            self.assertNotIn("勾选未提交", after)
            self.assertEqual(STAMP.sub("", after.replace("2/5", "1/5").replace("上次勾选 1 天前", "上次勾选 2 天前")),
                             STAMP.sub("", before))

    def test_untick_is_zero_not_negative(self):
        with self.make() as project:
            self.init(project)
            HistoryTest.write(project, "alpha", "- [ ] a\n- [ ] b\n- [ ] c\n- [ ] d\n- [ ] e\n")
            self.assertEqual(self.by_id(project)["alpha"]["uncommittedTicks"], 0)
            self.assertNotIn("勾选未提交", project.run(env=self.NOW).stdout)

    def test_untracked_todo_counts_every_tick(self):
        with self.make() as project:
            self.init(project)
            for rel, text in (("spec/gamma.md", "# gamma\n"), ("tasks/gamma/plan.md", "# Plan\n"),
                              ("tasks/gamma/todo.md", "- [x] one\n- [x] two\n- [ ] three\n")):
                (project.root / rel).parent.mkdir(parents=True, exist_ok=True)
                (project.root / rel).write_text(text, encoding="utf-8")
            by_id = self.by_id(project)
            self.assertEqual(by_id["gamma"]["uncommittedTicks"], 2)
            self.assertIsNone(by_id["gamma"]["startedAt"])

    def test_started_at_is_the_first_commit_of_the_spec(self):
        with self.make() as project:
            self.init(project)
            (project.root / "spec" / "beta.md").write_text("# beta\n", encoding="utf-8")
            HistoryTest.commit(project, "2026-10-03T10:00:00+08:00")
            (project.root / "spec" / "alpha.md").write_text("# alpha\n\nmore\n", encoding="utf-8")
            HistoryTest.commit(project, "2026-10-04T09:00:00+08:00")
            data = project.json()
            by_id = {m["id"]: m for m in data["modules"]}
            self.assertEqual(by_id["alpha"]["startedAt"], "2026-10-02T10:00:00+08:00")
            self.assertEqual(by_id["beta"]["startedAt"], "2026-10-03T10:00:00+08:00")
            self.assertIsNone(by_id["gamma"]["startedAt"])
            self.assertEqual(data["head"]["committedAt"], "2026-10-04T09:00:00+08:00")

    def test_repository_without_commits(self):
        with self.make() as project:
            project.git("init")
            data = project.json()
            self.assertIsNone(data["head"]["committedAt"])
            self.assertTrue(all(m["uncommittedTicks"] is None and m["startedAt"] is None for m in data["modules"]))

    def test_review_cadence_matches_the_config_summary(self):
        from project_config import summary
        cases = (None, '{"version": 1, "reviewCadence": "combined"}', '{"version": 1, "reviewCadence": "weekly"}')
        expected = ({"value": "separate", "source": "default"},
                    {"value": "combined", "source": ".agent/config.json"},
                    {"value": "separate", "source": "default (config invalid)"})
        for body, want in zip(cases, expected):
            with self.subTest(body=body):
                extra = {".agent/config.json": body} if body else None
                with self.make(extra) as project:
                    self.assertEqual(project.json()["reviewCadence"], want)
                    item = next(i for i in summary(project.root) if i["key"] == "reviewCadence")
                    self.assertEqual({"value": item["value"], "source": item["source"]}, want)


class GateCountTest(unittest.TestCase):
    """map-gate-count: per-module gates {total, done} from the working-tree todo, by the next-gate criterion."""
    ROWS = [("alpha", "甲", "—"), ("beta", "乙", "alpha"), ("gamma", "丙", "alpha")]
    TODO = ("- [x] Task 1\n"
            "- [x] Checkpoint 1（gate）：先停\n"
            "- [ ] Checkpoint 2（report）：记入 todo\n"
            "- [ ] Task 2\n"
            "- [ ] Checkpointing is not a checkpoint\n"
            "- [ ] Checkpoint 3：最终验收\n")

    def gates(self, files):
        with Project(self.ROWS, ["alpha", "beta", "gamma"], files) as project:
            return {m["id"]: m["gates"] for m in project.json()["modules"]}

    def test_gate_and_untiered_count_report_does_not(self):
        got = self.gates({"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": self.TODO})
        self.assertEqual(got["alpha"], {"total": 2, "done": 1})

    def test_all_checked_and_upper_case_x(self):
        todo = self.TODO.replace("- [ ] Checkpoint 3", "- [X] Checkpoint 3")
        got = self.gates({"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": todo})
        self.assertEqual(got["alpha"], {"total": 2, "done": 2})

    def test_no_checkpoint_is_zero_and_no_todo_is_null(self):
        got = self.gates({"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": "- [ ] one\n",
                          "spec/beta.md": "# b\n", "tasks/beta/plan.md": "# P\n"})
        self.assertEqual(got, {"alpha": {"total": 0, "done": 0}, "beta": None, "gamma": None})

    def test_present_without_git_history(self):
        with Project(self.ROWS, ["alpha", "beta", "gamma"],
                     {"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": self.TODO}) as project:
            data = project.json()
        self.assertEqual(data["history"], "unavailable")
        self.assertEqual(data["modules"][0]["gates"], {"total": 2, "done": 1})

    def test_untiered_middle_checkpoints_are_reports(self):
        todo = ("- [ ] Checkpoint 1：中途\n- [x] Checkpoint 2（gate）：已过\n- [ ] Task\n"
                "- [ ] Checkpoint 3：最终验收\n- [ ] 发版后的核对\n")
        got = self.gates({"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": todo})
        self.assertEqual(got["alpha"], {"total": 2, "done": 1})

    def test_single_untiered_checkpoint_and_report_last(self):
        got = self.gates({"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n",
                          "tasks/alpha/todo.md": "- [ ] Task\n- [ ] Checkpoint：验收\n",
                          "spec/beta.md": "# b\n", "tasks/beta/plan.md": "# P\n",
                          "tasks/beta/todo.md": "- [ ] Checkpoint 1：中途\n- [ ] Checkpoint 2（report）：收尾\n"})
        self.assertEqual(got["alpha"], {"total": 1, "done": 0})
        self.assertEqual(got["beta"], {"total": 0, "done": 0})

    def test_next_gate_skips_untiered_middle_checkpoints(self):
        todo = "- [ ] Checkpoint 1：中途\n- [ ] Task\n- [ ] Checkpoint 2：最终验收\n"
        with Project(self.ROWS, ["alpha", "beta", "gamma"],
                     {"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": todo},
                     active="alpha") as project:
            self.assertEqual(project.json()["nextGate"], "Checkpoint 2：最终验收")

    def test_next_gate_uses_the_same_criterion(self):
        with Project(self.ROWS, ["alpha", "beta", "gamma"],
                     {"spec/alpha.md": "# a\n", "tasks/alpha/plan.md": "# P\n", "tasks/alpha/todo.md": self.TODO},
                     active="alpha") as project:
            data = project.json()
        self.assertEqual(data["nextGate"], "Checkpoint 3：最终验收")


# map-startable: setup done; billing and report in progress with overlapping boundaries; shop ready (comma group
# with billing); later waits on billing.
CON_ROWS = [("setup", "公共预置", "—"), ("billing", "账单", "setup"), ("shop", "商城", "setup"),
            ("report", "报表", "setup"), ("later", "之后", "billing")]
CON_ORDER = ["setup", "billing, shop", "report", "later"]
CON_FILES = {
    "spec/setup.md": "# setup\n", "tasks/setup/plan.md": "# Plan\n", "tasks/setup/todo.md": "- [x] one\n",
    "spec/billing.md": "# billing\n\n## 并行边界\n\n- 独占：`apps/billing/`、`apps/shared/`\n- 公共：锁文件\n",
    "tasks/billing/plan.md": "# Plan\n", "tasks/billing/todo.md": "- [ ] one\n",
    "spec/report.md": "# report\n\n## 并行边界\n\n- 独占：`apps/shared/report/`、`apps/reporting/`\n",
    "tasks/report/plan.md": "# Plan\n", "tasks/report/todo.md": "- [ ] one\n",
}
STAMP = re.compile(r" · \d{4}-\d{2}-\d{2} \d{2}:\d{2}$", re.MULTILINE)


def snapshot(project):
    """JSON without generatedAt, and the table without its minute stamp."""
    data = project.json()
    data.pop("generatedAt")
    data.pop("reviewCadence")  # map-progress-facts: its source reports an invalid config; checked in ProgressFactsTest
    done = project.run()
    assert done.returncode == 0, done.stderr
    return json.dumps(data, ensure_ascii=False, sort_keys=True), STAMP.sub("", done.stdout)


class ConcurrencyOff(unittest.TestCase):
    """map-startable: off, unset or an invalid config reads exactly like no config at all."""

    def test_off_unset_and_invalid_match_no_config(self):
        with Project(CON_ROWS, CON_ORDER, CON_FILES) as project:
            plain = snapshot(project)
            (project.root / ".agent").mkdir(exist_ok=True)
            config = project.root / ".agent" / "config.json"
            for body in ('{"version": 1, "moduleConcurrency": "off"}', '{"version": 1}',
                         '{"version": 1, "moduleConcurrency": "on", "x": 1}', '{"version": 1, "moduleConcurrency": "yes"}'):
                with self.subTest(body=body):
                    config.write_text(body, encoding="utf-8")
                    self.assertEqual(snapshot(project), plain)

    def test_off_keeps_the_fixed_key_sets(self):
        with Project(CON_ROWS, CON_ORDER, CON_FILES) as project:
            data = project.json()
        self.assertEqual(set(data), TOP_KEYS)
        for module in data["modules"]:
            self.assertEqual(set(module), MODULE_KEYS)


ON = {".agent/config.json": '{"version": 1, "moduleConcurrency": "on"}'}


class ConcurrencyOnJson(unittest.TestCase):
    """map-startable: the additive JSON fields when moduleConcurrency is on."""

    def data(self, extra=None):
        files = dict(CON_FILES, **ON, **(extra or {}))
        with Project(CON_ROWS, CON_ORDER, files) as project:
            return project.json()

    def test_switch_and_groups(self):
        data = self.data()
        self.assertEqual(data["schemaVersion"], 1)
        self.assertEqual(data["moduleConcurrency"], "on")
        self.assertEqual(data["buildOrderGroups"], [["setup"], ["billing", "shop"], ["report"], ["later"]])
        self.assertEqual(set(data) - TOP_KEYS, {"moduleConcurrency", "buildOrderGroups", "startable"})
        for module in data["modules"]:
            self.assertEqual(set(module) - MODULE_KEYS, {"scope", "worktree"})  # worktree: checkout-role

    def test_scope_values(self):
        by_id = {m["id"]: m["scope"] for m in self.data({"spec/later.md": "# later\n\n## 并行边界\n\n- 独占：apps/later/\n"})["modules"]}
        self.assertEqual(by_id["billing"], {"exclusive": ["apps/billing/", "apps/shared/"], "shared": ["lockfile"]})
        self.assertEqual(by_id["report"], {"exclusive": ["apps/shared/report/", "apps/reporting/"], "shared": []})
        self.assertIsNone(by_id["setup"])
        self.assertIsNone(by_id["shop"])
        self.assertEqual(by_id["later"], {"error": "bad-path"})

    def test_startable_lists_every_ready_module_in_build_order(self):
        data = self.data()
        self.assertEqual(data["startable"]["modules"], ["shop"])
        # d comes first and is therefore the current module (in progress), so it is not listed.
        rows = [("a", "x", "—"), ("b", "x", "—"), ("c", "x", "a"), ("d", "x", "—")]
        with Project(rows, ["d", "b, a", "c"], dict(ON)) as project:
            data = project.json()
        self.assertEqual(data["startable"]["modules"], ["b", "a"])
        self.assertEqual(data["buildOrderGroups"], [["d"], ["b", "a"], ["c"]])

    def test_conflicts_between_unfinished_modules(self):
        self.assertEqual(self.data()["startable"]["conflicts"],
                         [{"modules": ["billing", "report"], "paths": ["apps/shared/report/"]}])

    def test_done_and_suspended_modules_do_not_conflict(self):
        extra = {"spec/setup.md": "# setup\n\n## 并行边界\n\n- 独占：`apps/billing/`\n",
                 "tasks/report/todo.md": "- [ ] one\n" + SUSPEND_MARKER + "\n"}
        self.assertEqual(self.data(extra)["startable"]["conflicts"], [])

    def test_same_name_prefix_is_not_an_overlap(self):
        extra = {"spec/report.md": "# report\n\n## 并行边界\n\n- 独占：`apps/bill/`、`apps/shared`\n"}
        self.assertEqual(self.data(extra)["startable"]["conflicts"], [])

    def test_overlap_paths_and_order(self):
        from map_view import _overlap
        from module_scope import Scope
        a = Scope(("apps/x/", "docs/a.md", "lib/"), ())
        b = Scope(("apps/x/y/", "docs/a.md", "libs/", "lib/z.py"), ())
        self.assertEqual(_overlap(a, b), ["apps/x/y/", "docs/a.md", "lib/z.py"])
        self.assertEqual(_overlap(b, a), ["apps/x/y/", "docs/a.md", "lib/z.py"])


class ConcurrencyOnTable(unittest.TestCase):
    """map-startable: the table marks ready modules and lists overlaps above the header, only when on."""

    def table(self, extra=None, switch=True):
        files = dict(CON_FILES, **(ON if switch else {}), **(extra or {}))
        with Project(CON_ROWS, CON_ORDER, files) as project:
            done = project.run()
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.splitlines()

    def test_ready_module_is_marked(self):
        lines = self.table()
        self.assertTrue(any("| shop |" in line and "🟢 可以开始 · 可同时开工" in line for line in lines), lines)

    def test_overlap_line_sits_before_the_mainline_line(self):
        lines = self.table()
        overlap = [i for i, line in enumerate(lines) if line.startswith("并行边界重叠：")]
        mainline = [i for i, line in enumerate(lines) if line.startswith("未合入主线：")]
        self.assertEqual(len(overlap), 1, lines)
        self.assertEqual(lines[overlap[0]], "并行边界重叠：billing 与 report（apps/shared/report/）")
        self.assertEqual(overlap[0] + 1, mainline[0])

    def test_no_overlap_no_line(self):
        extra = {"spec/report.md": "# report\n\n## 并行边界\n\n- 独占：`apps/reporting/`\n"}
        self.assertFalse(any(line.startswith("并行边界重叠") for line in self.table(extra)))

    def test_off_has_neither(self):
        lines = self.table(switch=False)
        self.assertFalse(any("可同时开工" in line or line.startswith("并行边界重叠") for line in lines))


WT_ROWS = "| a | x | — |\n| b | x | a |\n| c | x | a |\n"


class Worktrees:
    """A committed project (a done; b and c ready) with module worktrees around it."""

    def __init__(self, switch="on"):
        self.switch = switch

    def git(self, cwd, *args):
        return subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True, text=True, timeout=30).stdout

    def role(self, cwd, text):
        raw = self.git(cwd, "rev-parse", "--git-path", "spec-guard/role").strip()
        path = Path(raw) if os.path.isabs(raw) else Path(cwd) / raw
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.root = base / "proj"
        (self.root / "spec").mkdir(parents=True)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(
            "# Capability Map: wt\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n" + WT_ROWS
            + "\nBuild order: a → b, c\n", encoding="utf-8")
        for rel, text in {"spec/a.md": "# a\n", "tasks/a/plan.md": "# Plan\n", "tasks/a/todo.md": "- [x] one\n"}.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")
        if self.switch is not None:
            (self.root / ".agent").mkdir()
            (self.root / ".agent" / "config.json").write_text(
                json.dumps({"version": 1, "moduleConcurrency": self.switch}), encoding="utf-8")
        self.git(self.root, "init", "-q")
        self.git(self.root, "add", "-A")
        self.git(self.root, "commit", "-qm", "base")
        self.wt = {name: base / name for name in ("wt1", "wt2", "wt3", "wt4", "wt5")}
        # wt1: module b, one of two items done and committed there, plus an untracked file.
        self.git(self.root, "worktree", "add", "-q", "-b", "wt1", str(self.wt["wt1"]))
        (self.wt["wt1"] / "tasks" / "b").mkdir(parents=True)
        (self.wt["wt1"] / "tasks" / "b" / "todo.md").write_text("- [x] one\n- [ ] two\n", encoding="utf-8")
        self.git(self.wt["wt1"], "add", "-A")
        self.git(self.wt["wt1"], "commit", "-qm", "b work")
        (self.wt["wt1"] / "scratch.txt").write_text("x\n", encoding="utf-8")
        self.role(self.wt["wt1"], "module b")
        # wt2: module c, no todo yet, same commit as the project.
        self.git(self.root, "worktree", "add", "-q", "-b", "wt2", str(self.wt["wt2"]))
        self.role(self.wt["wt2"], "module c")
        # wt3: a second worktree claiming b, detached.
        self.git(self.root, "worktree", "add", "-q", "--detach", str(self.wt["wt3"]))
        self.role(self.wt["wt3"], "module b")
        # wt4: module a with an unreadable todo (a directory).
        self.git(self.root, "worktree", "add", "-q", "-b", "wt4", str(self.wt["wt4"]))
        (self.wt["wt4"] / "tasks" / "a" / "todo.md").unlink()
        (self.wt["wt4"] / "tasks" / "a" / "todo.md").mkdir()
        self.role(self.wt["wt4"], "module a")
        # wt5: claims c, then its directory disappears (prunable): skipped.
        self.git(self.root, "worktree", "add", "-q", "-b", "wt5", str(self.wt["wt5"]))
        self.role(self.wt["wt5"], "module c")
        subprocess.run(["rm", "-rf", str(self.wt["wt5"])], check=True)
        return self

    def json(self):
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--json", "--project", str(self.root)],
                              capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    def table(self):
        done = subprocess.run([sys.executable, "-B", SCRIPT, "--project", str(self.root)],
                              capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr
        return done.stdout

    def __exit__(self, *exc):
        self.tmp.cleanup()


class WorktreeField(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Worktrees()
        cls.fixture.__enter__()
        cls.data = cls.fixture.json()
        cls.by_id = {m["id"]: m["worktree"] for m in cls.data["modules"]}
        cls.text = cls.fixture.table()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.__exit__()

    def test_module_with_progress_dirty_and_unmerged(self):
        b = self.by_id["b"]
        self.assertEqual((b["path"], b["branch"]), (str(self.fixture.wt["wt1"]), "wt1"))
        self.assertEqual((b["progress"], b["todo"], b["dirty"], b["merged"]), ({"done": 1, "total": 2}, "ok", True, False))
        self.assertEqual(len(b["head"]), 40)
        self.assertEqual(b["duplicates"], [str(self.fixture.wt["wt3"])])

    def test_missing_todo_and_merged(self):
        c = self.by_id["c"]
        self.assertEqual(c["path"], str(self.fixture.wt["wt2"]))
        self.assertEqual((c["progress"], c["todo"], c["dirty"], c["merged"]), (None, "missing", False, True))
        self.assertNotIn("duplicates", c)

    def test_unreadable_todo(self):
        a = self.by_id["a"]
        self.assertEqual((a["progress"], a["todo"]), (None, "unreadable"))

    def test_table_suffixes_for_any_local_status(self):
        rows = {line.split("|")[2].strip(): line for line in self.text.splitlines() if line.startswith("| ")}
        self.assertIn("· worktree 1/2 有未提交改动 未合入", rows["b"])
        self.assertIn("· worktree 进度未知", rows["a"])
        self.assertIn("· worktree 进度未知", rows["c"])
        self.assertNotIn("未合入", rows["c"])

    def test_switch_off_never_scans(self):
        import map_view
        with Worktrees(switch="off") as fixture:
            with mock.patch.object(map_view, "scan_worktrees", wraps=map_view.scan_worktrees) as spy:
                data = map_view.build(fixture.root)
            self.assertEqual(spy.call_count, 0)
            self.assertNotIn("worktree", data["modules"][0])
            self.assertNotIn("worktree", fixture.table())

if __name__ == "__main__":
    unittest.main()
