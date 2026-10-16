"""map-view: the read-only module progress table and its JSON. No network."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from module_stage import SUSPEND_MARKER

SCRIPT = str(Path(__file__).with_name("map_view.py"))
PLUGIN_JSON = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
REASON_PREFIX = "<!-- spec-guard: suspended-reason: "
PENDING = "<!-- spec-guard: review pending -->"
APPROVED_PLAN = "<!-- spec-guard: review approved -->"

TOP_KEYS = {"schemaVersion", "generatedAt", "generator", "project", "head", "stage", "activeModule",
            "nextGate", "totals", "bottlenecks", "awaitingReview", "modules"}
MODULE_KEYS = {"id", "position", "responsibility", "dependsOn", "status", "step", "progress",
               "suspendedReason", "blockedOn", "missingDeps", "blocks", "review"}
HEAD_KEYS = {"sha", "branch", "unmerged", "unpushed"}
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
        self.assertEqual(self.data["head"], {"sha": None, "branch": None, "unmerged": None, "unpushed": None})

    def test_table_header_and_rows(self):
        out = self.project.run().stdout
        lines = out.splitlines()
        self.assertIn("Capability Map: 测试项目 · 9 个模块 · ✅ 1 🔨 2 ⏸ 1 ⛔ 3 🟢 1 ○ 1 · ", lines[0])
        self.assertIn("关键卡点：b 挂起（上游漏洞）→ 挡住 3 个：c、d、i", out)
        self.assertIn("待审核：g Spec（待审核）、h Plan（待审核）", out)
        self.assertIn("下一个 gate：Checkpoint 1（gate）：模块评审", out)
        self.assertIn("未合入主线：判断不了；未推送：判断不了", out)
        self.assertIn("| 2 | b | 质量门禁 | ⏸ 挂起（上游漏洞），挡住 3 个 | Spec 无标记 Plan 无标记 |", out)
        self.assertIn("| 3 | c | 下游一 | ⛔ 阻塞：等 b | — |", out)
        self.assertIn("| 5 | e | 可开工 | 🟢 可以开始 | — |", out)
        self.assertIn("| 7 | g | 写 Plan 中 | 🔨 写 Plan | Spec 待审核 |", out)
        self.assertIn("| 8 | h | 构建中 | 🔨 进行中 1/3 | Spec 无标记 Plan 待审核 |", out)
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
            self.assertIn("待审核：q Spec（改过待重审）", project.run().stdout)
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
            self.assertIn("待审核：无", out)

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

    def test_reason_line_without_marker_is_ignored(self):
        with self.make() as project:
            todo = project.root / "tasks" / "p3" / "todo.md"
            todo.write_text("- [x] one\n- [ ] two\n%s旧原因 -->\n" % REASON_PREFIX, encoding="utf-8")
            module = project.json()["modules"][2]
            self.assertEqual(module["status"], "in_progress")
            self.assertIsNone(module["suspendedReason"])


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


if __name__ == "__main__":
    unittest.main()
