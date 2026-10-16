#!/usr/bin/env python3
"""Read-only module progress table for one project, as a table or as JSON (map-view).

Every fact comes from files spec-guard already owns -- the capability map, each module's
Spec / Plan / todo, `.agent/state.json` -- plus local git refs.  Stages, progress, suspension,
review markers and the next gate are taken from `module_stage`; this script only maps them to
six display states, follows the dependency graph, and renders.  It never writes, never fetches.

Exit codes: 0 ok, 2 usage, 3 no capability map, 4 map or module file unreadable.
The JSON contract (schemaVersion 1) is specified in spec/map-view.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from capability_map import MapError, parse_map
from module_stage import (SUSPEND_MARKER, _git, active_module, file_review_state, module_state,
                          next_gate, project_stage, unmerged_commits)

SCHEMA_VERSION = 1
REASON_LINE = re.compile(r"^<!-- spec-guard: suspended-reason: (.*) -->$")
STATUSES = ("done", "in_progress", "suspended", "blocked", "ready", "not_ready")
ICONS = {"done": "✅", "in_progress": "🔨", "suspended": "⏸", "blocked": "⛔", "ready": "🟢", "not_ready": "○"}
AWAITING = ("pending", "revised", "invalid")
REVIEW_WORDS = {"approved": "✔", "pending": "待审核", "revised": "改过待重审", "invalid": "标记无效", "none": "无标记"}
RESPONSIBILITY_LIMIT = 40


class Unreadable(Exception):
    """A file the table depends on cannot be read."""


def suspended_reason(text: str) -> str | None:
    """The reason line right after the suspension marker, or None."""
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line == SUSPEND_MARKER and index + 1 < len(lines):
            match = REASON_LINE.match(lines[index + 1])
            return match.group(1) if match else None
    return None


def clean(text: str) -> str:
    """Project text for a table cell: no control characters, no column separators."""
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" and ch != "|").strip()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeError) as error:
        raise Unreadable("%s: %s" % (path, error))


def _review(root: Path, module: str) -> dict:
    spec = file_review_state(root / "spec" / (module + ".md"), "spec")
    plan = file_review_state(root / "tasks" / module / "plan.md", "plan")
    for state, path in ((spec, "spec/%s.md" % module), (plan, "tasks/%s/plan.md" % module)):
        if state == "unreadable":
            raise Unreadable(path)
    return {"spec": spec, "plan": plan}


def _closure(start: str, edges: dict) -> set:
    seen, stack = set(), list(edges.get(start, ()))
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend(edges.get(node, ()))
    return seen


def _head(root: Path) -> dict:
    sha = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if not sha:
        return {"sha": None, "branch": None, "unmerged": None, "unpushed": None}
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD") or None
    merged = unmerged_commits(root)
    unpushed = None
    if branch:
        upstream = _git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        count = _git(root, "rev-list", "--count", "@{upstream}..HEAD") if upstream else None
        if upstream and count and count.isdigit():
            unpushed = {"count": int(count), "upstream": upstream}
    return {"sha": sha, "branch": branch,
            "unmerged": {"count": merged[0], "base": merged[1]} if merged else None, "unpushed": unpushed}


def _version() -> str | None:
    try:
        manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
        value = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        return value if isinstance(value, str) else None
    except (OSError, ValueError, AttributeError):
        return None


def _title(map_path: Path) -> str | None:
    for line in _read(map_path).splitlines():
        if line.startswith("# "):
            return line[2:].strip() or None
    return None


def build(root: Path) -> dict:
    map_path = root / "spec" / "CAPABILITY-MAP.md"
    parsed = parse_map(map_path)
    rows = {row.module_id: row for row in parsed.rows}
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    states = []
    for module in order:
        try:
            states.append(module_state(root, module))
        except (OSError, UnicodeError) as error:
            raise Unreadable("tasks/%s: %s" % (module, error))
    stage, current, _source, _pending = project_stage(states, active_module(root))
    by_id = {state["id"]: state for state in states}
    deps = {module: list(rows[module].depends_on) for module in order}
    dependents = {module: [] for module in order}
    for module in order:
        for dep in deps[module]:
            dependents.setdefault(dep, []).append(module)
    position = {module: index + 1 for index, module in enumerate(order)}

    status = {}
    for module in order:
        state = by_id[module]
        if state["stage"] == "DONE":
            status[module] = "done"
        elif state["suspended"]:
            status[module] = "suspended"
        elif state["spec"] or state["plan"] or (current is not None and current["id"] == module):
            status[module] = "in_progress"
    for module in order:
        if module in status:
            continue
        upstream = _closure(module, deps)
        if any(status.get(dep) == "suspended" for dep in upstream):
            status[module] = "blocked"
        elif all(status.get(dep) == "done" for dep in deps[module]):
            status[module] = "ready"
        else:
            status[module] = "not_ready"

    modules = []
    for module in order:
        state, value = by_id[module], status[module]
        todo = _read(root / "tasks" / module / "todo.md")
        done_items = len(re.findall(r"^\s*[-*+]\s+\[[xX]\]", todo, re.MULTILINE))
        blocks = sorted((m for m in _closure(module, dependents) if status[m] != "done"), key=position.get)
        upstream = _closure(module, deps)
        modules.append({
            "id": module, "position": position[module], "responsibility": rows[module].responsibility or "",
            "dependsOn": deps[module], "status": value,
            "step": (None if value != "in_progress" else
                     "spec" if not state["spec"] else "plan" if not state["plan"] else "build"),
            "progress": {"done": done_items, "total": done_items + state["open"]},
            "suspendedReason": suspended_reason(todo) if value == "suspended" else None,
            "blockedOn": (sorted((m for m in upstream if status[m] == "suspended"), key=position.get)
                          if value == "blocked" else []),
            "missingDeps": [d for d in deps[module] if status[d] != "done"] if value == "not_ready" else [],
            "blocks": {"count": len(blocks), "ids": blocks},
            "review": _review(root, module),
        })

    suspended = [m for m in modules if m["status"] == "suspended"]
    suspended.sort(key=lambda m: (-m["blocks"]["count"], m["position"]))
    awaiting = [{"id": m["id"], "kind": kind, "review": m["review"][kind]}
                for m in modules for kind in ("spec", "plan") if m["review"][kind] in AWAITING]
    active = current["id"] if current is not None and stage != "DONE" else None
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generator": {"name": "spec-guard", "version": _version()},
        "project": {"root": str(root), "title": _title(map_path)},
        "head": _head(root),
        "stage": stage,
        "activeModule": active,
        "nextGate": (next_gate(root, active) or None) if active else None,
        "totals": {key: sum(1 for m in modules if m["status"] == key) for key in STATUSES},
        "bottlenecks": [{"id": m["id"], "suspendedReason": m["suspendedReason"], "blocks": m["blocks"]["ids"]}
                        for m in suspended],
        "awaitingReview": awaiting,
        "modules": modules,
    }


def _status_cell(m: dict) -> str:
    value = m["status"]
    if value == "done":
        return "✅ 已完成"
    if value == "in_progress":
        if m["step"] == "spec":
            return "🔨 写 Spec"
        if m["step"] == "plan":
            return "🔨 写 Plan"
        return "🔨 进行中 %d/%d" % (m["progress"]["done"], m["progress"]["total"])
    if value == "suspended":
        reason = clean(m["suspendedReason"] or "") or "未记原因"
        tail = "，挡住 %d 个" % m["blocks"]["count"] if m["blocks"]["count"] else ""
        return "⏸ 挂起（%s）%s" % (reason, tail)
    if value == "blocked":
        return "⛔ 阻塞：等 " + "、".join(m["blockedOn"])
    if value == "ready":
        return "🟢 可以开始"
    return "○ 未就绪：缺 " + "、".join(m["missingDeps"])


def _review_cell(root: Path, m: dict) -> str:
    parts = []
    if (root / "spec" / (m["id"] + ".md")).is_file():
        parts.append("Spec " + REVIEW_WORDS[m["review"]["spec"]])
    if (root / "tasks" / m["id"] / "plan.md").is_file():
        parts.append("Plan " + REVIEW_WORDS[m["review"]["plan"]])
    return " ".join(parts) or "—"


def _responsibility(text: str) -> str:
    text = clean(text)
    return text if len(text) <= RESPONSIBILITY_LIMIT else text[:RESPONSIBILITY_LIMIT] + "…"


def _span(group: list) -> str:
    first, last = group[0]["position"], group[-1]["position"]
    return str(first) if first == last else "%d–%d" % (first, last)


def render(data: dict, root: Path, expand_all: bool) -> str:
    modules = data["modules"]
    totals = data["totals"]
    stamp = data["generatedAt"][:16].replace("T", " ")
    title = clean(data["project"]["title"] or root.name)
    lines = ["%s · %d 个模块 · %s · %s" % (title, len(modules),
                                         " ".join("%s %d" % (ICONS[k], totals[k]) for k in STATUSES), stamp)]
    by_id = {m["id"]: m for m in modules}
    if data["bottlenecks"]:
        parts = []
        for item in data["bottlenecks"]:
            reason = clean(item["suspendedReason"] or "") or "未记原因"
            tail = "→ 挡住 %d 个：%s" % (len(item["blocks"]), "、".join(item["blocks"])) if item["blocks"] else "→ 没有挡住其他模块"
            parts.append("%s 挂起（%s）%s" % (item["id"], reason, tail))
        lines.append("关键卡点：" + "；".join(parts))
    else:
        lines.append("关键卡点：无")
    kinds = {"spec": "Spec", "plan": "Plan"}
    lines.append("待审核：" + ("、".join("%s %s（%s）" % (a["id"], kinds[a["kind"]], REVIEW_WORDS[a["review"]])
                                       for a in data["awaitingReview"]) or "无"))
    if data["nextGate"]:
        lines.append("下一个 gate：" + clean(data["nextGate"]))
    head = data["head"]
    merged = ("%d 个提交（相对 %s）" % (head["unmerged"]["count"], head["unmerged"]["base"])
              if head["unmerged"] else "判断不了")
    pushed = "%d 个提交" % head["unpushed"]["count"] if head["unpushed"] else "判断不了"
    lines.append("未合入主线：%s；未推送：%s" % (merged, pushed))
    lines += ["", "| 位 | 模块 | 作用 | 状态 | 审查 |", "|---|---|---|---|---|"]

    done = [m for m in modules if m["status"] == "done"]
    last_done = done[-1]["id"] if done else None
    shown = []
    group = []
    for m in modules:
        expand = expand_all or m["status"] in ("in_progress", "suspended", "blocked", "ready") or m["id"] == last_done
        if expand:
            if group:
                shown.append(group)
                group = []
            shown.append(m)
            continue
        if group and group[-1]["status"] != m["status"]:
            shown.append(group)
            group = []
        group.append(m)
    if group:
        shown.append(group)
    for item in shown:
        if isinstance(item, list):
            if item[0]["status"] == "done":
                label, icon = "其余 %d 个已完成" % len(item), "✅"
            else:
                label, icon = "%d 个未就绪" % len(item), "○"
            lines.append("| %s | %s | | %s | |" % (_span(item), label, icon))
        else:
            lines.append("| %d | %s | %s | %s | %s |" % (item["position"], item["id"],
                                                         _responsibility(item["responsibility"]),
                                                         _status_cell(by_id[item["id"]]), _review_cell(root, item)))
    return "\n".join(lines) + "\n"


def _default_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        if top.returncode == 0 and top.stdout.strip():
            return Path(top.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.cwd()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="只读的单项目模块进度表")
    parser.add_argument("--project")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project) if args.project else _default_root()
    if not root.is_dir():
        print("map-view: 项目路径不存在或不是目录：%s" % root, file=sys.stderr)
        return 2
    root = root.resolve()

    def fail(code: int, error: str, message: str, detail: str | None = None) -> int:
        print("map-view: " + message, file=sys.stderr)
        if args.json:
            body = {"schemaVersion": SCHEMA_VERSION, "error": error}
            if detail is not None:
                body["detail"] = detail
            print(json.dumps(body, ensure_ascii=False))
        return code

    if not (root / "spec" / "CAPABILITY-MAP.md").is_file():
        return fail(3, "no-capability-map", "没有能力图（spec/CAPABILITY-MAP.md），这个项目没有启用 spec-guard 的多模块约定。")
    try:
        data = build(root)
    except (MapError, Unreadable, OSError, UnicodeError) as error:
        return fail(4, "unreadable", "读不出能力图或模块文件：%s" % error, str(error))
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(render(data, root, args.all))
    return 0


if __name__ == "__main__":
    sys.exit(main())
