#!/usr/bin/env python3
"""Preview, and after explicit confirmation write, a validated quick insertion
into the capability map.

Preview (`--anchor`/`--depends-on`/... without `--confirm`) is always
read-only. `--confirm` re-runs every preview check and then writes only
`spec/CAPABILITY-MAP.md`; it never creates a spec skeleton (that would make
module_stage report NEEDS_PLAN for an unwritten, unreviewed spec) and never
touches `.agent/state.json`, `tasks/`, `spec/proposals/`, or Git. See
`spec/module-insert.md` for the full contract.
"""
import argparse
import difflib
import importlib.util
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

from capability_map import MapError, MODULE_ID, parse_map, _visible_lines
from module_stage import CHECKED, active_module, module_state, paused_modules, project_stage
from proposal_promotion_proof import _matches, preflight_as_json, promotion_base


_digest_spec = importlib.util.spec_from_file_location(
    "spec_guard_digest", Path(__file__).with_name("spec-digest.py"))
_digest_module = importlib.util.module_from_spec(_digest_spec)
_digest_spec.loader.exec_module(_digest_module)
compute = _digest_module.compute


ANCHOR_AFTER = re.compile(r"^after:(.+)$")


class InsertError(ValueError):
    """The requested insertion cannot be validated; nothing is written."""


def _parse_depends_arg(raw):
    raw = raw.strip()
    if raw in ("", "-", "—"):
        return []
    items = [item.strip() for item in raw.split(",")]
    if any(not item for item in items):
        raise InsertError("--depends-on 格式无效：包含空项")
    if len(set(items)) != len(items):
        raise InsertError("--depends-on 包含重复项")
    return items


def _current_module(project, order):
    states = [module_state(project, module_id) for module_id in order]
    by_id = {state["id"]: state for state in states}
    active = active_module(project)
    if active and active in by_id:
        return by_id[active], active
    return next((state for state in states if state["stage"] != "DONE"), None), active


def _module_table_rows(lines):
    """Locate the module table's header and rows.

    `lines` must be `capability_map._visible_lines(...)` output (fenced
    example lines blanked to ""), not raw lines, so a fenced example module
    table can never be mistaken for the real one. The returned indices are
    index-preserving, so callers can still edit the original raw lines by
    the same index.
    """
    header_index = None
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0].lower() == "module id":
            header_index = index
            break
    if header_index is None:
        raise InsertError("能力图中找不到模块表")
    rows = []
    index = header_index + 2  # skip the header separator row
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        module_id = cells[0].strip("`").strip() if cells else ""
        rows.append((index, module_id))
        index += 1
    if not rows:
        raise InsertError("能力图模块表为空")
    return rows


def _build_order_line_index(lines):
    """Locate the `Build order:` line. `lines` must be
    `capability_map._visible_lines(...)` output, for the same reason as
    `_module_table_rows`: a fenced example Build order line must not be
    mistaken for the real one."""
    for index, line in enumerate(lines):
        if re.match(r"^Build order:\s*.*$", line.strip(), re.IGNORECASE):
            return index
    raise InsertError("能力图中找不到 Build order")


def _build_order_segments(line):
    """Split a raw ``Build order:`` line into its →-separated steps, keeping
    each comma-joined step together (capability_map.parse_map unrolls those into
    solo single-module groups for validation, which loses the grouping this
    insertion needs to keep intact)."""
    raw = re.match(r"^Build order:\s*(.*)$", line.strip(), re.IGNORECASE).group(1)
    segments = re.split(r"\s*(?:→|->)\s*", raw.strip())
    return [[item.strip().strip("`") for item in segment.split(",")] for segment in segments]


def _assert_new_module_present(parsed, module_id):
    """Defensive check: the new module id must actually be in the parsed new
    map, both as a module row and in the Build order. Without this, a bug in
    the raw-line edit (or a future regression) could report success while the
    new module never lands in the capability map."""
    if module_id not in (row.module_id for row in parsed.rows):
        raise InsertError("插入后的能力图未在模块表中包含新模块: %s" % module_id)
    if module_id not in parsed.order:
        raise InsertError("插入后的能力图未在 Build order 中包含新模块: %s" % module_id)


def preview(project, module_id, responsibility, depends_on_raw, anchor, interrupt=False):
    """Validate a quick insertion and describe it; never writes a file."""
    project = Path(project)
    map_path = project / "spec" / "CAPABILITY-MAP.md"
    if not map_path.is_file():
        raise InsertError("能力图不存在: %s" % map_path)
    try:
        parsed = parse_map(map_path)
    except MapError as error:
        raise InsertError("能力图无效: %s" % error)

    order = list(parsed.order)
    current, active = _current_module(project, order)
    interrupted = None
    if current is not None and current["half"]:
        if not interrupt:
            raise InsertError("当前模块 `%s` 做到一半（既有已勾选项又有未勾选项）；请先完成它"
                              "；如确需先做新模块，可加 --interrupt 显式插队。" % current["id"])
        todo = project / "tasks" / current["id"] / "todo.md"
        checked = len(CHECKED.findall(todo.read_text(encoding="utf-8")))
        interrupted = {"id": current["id"], "checked": checked, "total": checked + current["open"]}

    if not MODULE_ID.fullmatch(module_id):
        raise InsertError("id 不是合法的 kebab-case: %s" % module_id)

    responsibility = responsibility.strip()
    if not responsibility:
        raise InsertError("职责不能为空")
    if "\n" in responsibility or "\r" in responsibility:
        raise InsertError("职责必须是单行")

    depends_on = _parse_depends_arg(depends_on_raw)

    existing_ids = set(row.module_id for row in parsed.rows)
    if anchor == "end":
        anchor_id = None
    else:
        match = ANCHOR_AFTER.match(anchor)
        if not match:
            raise InsertError("anchor 格式无效，必须是 end 或 after:<module-id>")
        anchor_id = match.group(1)
        if anchor_id not in existing_ids:
            raise InsertError("anchor 指向的模块不存在于能力图: %s" % anchor_id)

    existing_spec = (project / "spec" / ("%s.md" % module_id)).exists()

    old_text = map_path.read_text(encoding="utf-8")
    ends_with_newline = old_text.endswith("\n")
    old_lines = old_text.splitlines()
    # Locate rows/Build order on the fence-stripped view (index-preserving)
    # so a fenced example table or Build order line is never mistaken for the
    # real one; the raw lines are still what gets edited, by the same index.
    visible_lines = _visible_lines(old_lines)

    table_rows = _module_table_rows(visible_lines)
    if anchor_id is None:
        row_after_index = table_rows[-1][0]
    else:
        matches = [index for index, row_id in table_rows if row_id == anchor_id]
        if not matches:
            raise InsertError("anchor 指向的模块不在模块表中: %s" % anchor_id)
        row_after_index = matches[0]

    build_order_index = _build_order_line_index(visible_lines)

    deps_text = ", ".join(depends_on) if depends_on else "—"
    row_text = "| %s | %s | %s |" % (module_id, responsibility, deps_text)

    segments = _build_order_segments(old_lines[build_order_index])
    if anchor_id is None:
        insert_segment_index = len(segments)
    else:
        segment_index = next((i for i, segment in enumerate(segments) if anchor_id in segment), None)
        if segment_index is None:
            raise InsertError("anchor 指向的模块不在 Build order 中: %s" % anchor_id)
        insert_segment_index = segment_index + 1
    new_segments = (segments[:insert_segment_index] + [[module_id]] +
                    segments[insert_segment_index:])
    new_build_order_line = "Build order: " + " → ".join(
        ", ".join(segment) for segment in new_segments)

    new_lines = []
    for index, line in enumerate(old_lines):
        new_lines.append(new_build_order_line if index == build_order_index else line)
        if index == row_after_index:
            new_lines.append(row_text)
    new_text = "\n".join(new_lines) + ("\n" if ends_with_newline else "")

    tmp_fd, tmp_path_str = tempfile.mkstemp(prefix="spec-guard-module-insert-", suffix=".md")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(new_text)
        try:
            new_parsed = parse_map(tmp_path)
        except MapError as error:
            raise InsertError("插入后的能力图未通过严格校验: %s" % error)
        _assert_new_module_present(new_parsed, module_id)

        old_digest = compute(str(map_path))
        new_digest = compute(str(tmp_path))
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    if old_digest["goalDigest"] != new_digest["goalDigest"]:
        raise InsertError("插入改变了 `## 目标` 摘要，拒绝插入")
    new_row_digests = dict((row["id"], row["rowDigest"]) for row in new_digest["rows"])
    for row in old_digest["rows"]:
        if new_row_digests.get(row["id"]) != row["rowDigest"]:
            raise InsertError("插入改变了已有模块的行摘要: %s" % row["id"])
    filtered_new_order = [module_id_ for module_id_ in new_digest["order"] if module_id_ in existing_ids]
    if filtered_new_order != old_digest["order"]:
        raise InsertError("插入改变了已有模块在模块表中的相对顺序")
    # Proposal 评审按 Build order 判断锚点与依赖的先后，所以这里比对的是 Build order，不是表格行序。
    if [module_id_ for module_id_ in new_parsed.order if module_id_ in existing_ids] != order:
        raise InsertError("插入改变了已有模块在 Build order 中的相对顺序")

    new_current, _ = _current_module(project, list(new_parsed.order))

    proposal_path = project / "spec" / "proposals" / ("%s.md" % module_id)

    return {
        "row_text": row_text,
        "build_order_line": new_build_order_line,
        "diff": list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile="spec/CAPABILITY-MAP.md", tofile="spec/CAPABILITY-MAP.md",
            lineterm="")),
        "old_current": current["id"] if current else None,
        "new_current": new_current["id"] if new_current else None,
        "proposal_conflict": proposal_path.is_file(),
        "module_id": module_id,
        "existing_spec": existing_spec,
        "interrupted": interrupted,
        "responsibility": responsibility,
        "new_text": new_text,
    }


def write(project, module_id, responsibility, depends_on_raw, anchor, interrupt=False):
    """Re-run every preview check, then atomically write the capability map.

    Writes only `spec/CAPABILITY-MAP.md` (temp file in the same directory,
    then `os.replace`). It does not create a spec skeleton: module_stage's
    stage only looks at whether `spec/<id>.md` exists, and a placeholder file
    would jump straight to NEEDS_PLAN, skipping "write and review the spec".
    """
    project = Path(project)
    result = preview(project, module_id, responsibility, depends_on_raw, anchor, interrupt)
    map_path = project / "spec" / "CAPABILITY-MAP.md"
    mode = stat.S_IMODE(os.stat(map_path).st_mode)

    tmp_fd, tmp_path_str = tempfile.mkstemp(prefix=".module-insert-", dir=str(map_path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(result["new_text"])
        os.chmod(tmp_path_str, mode)
        os.replace(tmp_path_str, str(map_path))
    except BaseException:
        try:
            os.unlink(tmp_path_str)
        except OSError:
            pass
        raise

    final_parsed = parse_map(map_path)
    final_order = list(final_parsed.order)
    states = [module_state(project, module_id) for module_id in final_order]
    stage, final_current, _, pending = project_stage(states, active_module(project))
    paused = paused_modules(states, final_current)

    return {
        "map_path": str(map_path),
        "existing_spec": result["existing_spec"],
        "module_id": module_id,
        "stage_module": final_current["id"] if final_current else None,
        "stage_hint": stage,
        "stage_pending": (pending["id"], pending["stage"]) if pending else None,
        "stage_paused": (paused[0]["id"], paused[0]["stage"]) if paused else None,
    }


def format_stage_hint(outcome):
    if outcome["stage_hint"] == "MODULE_DONE" and outcome.get("stage_paused"):
        paused_id, paused_stage = outcome["stage_paused"]
        return ("当前阶段提示: `%s` 处于 MODULE_DONE；被暂停的模块 `%s`（%s）应先恢复"
                % (outcome["stage_module"], paused_id, paused_stage))
    if outcome["stage_hint"] == "MODULE_DONE" and outcome["stage_pending"]:
        pending_id, pending_stage = outcome["stage_pending"]
        return ("当前阶段提示: `%s` 处于 MODULE_DONE；Build order 中下一个未完成模块是 `%s`（%s）"
                % (outcome["stage_module"], pending_id, pending_stage))
    if outcome["stage_module"] and outcome["stage_hint"] != "DONE":
        return "当前阶段提示: `%s` 处于 %s" % (outcome["stage_module"], outcome["stage_hint"])
    return "当前阶段提示: DONE"


def format_existing_spec_hint(outcome):
    return ("提示: spec/%s.md 已存在：该模块阶段为 NEEDS_PLAN（视为已评审）；若尚未评审，请先评审"
            % outcome["module_id"])


def prepare_proposal(project, proposal_id, platform, target, interrupt=False,
                     tracker_reader=None):
    """Resolve a published, accepted Proposal into a validated insertion; never writes.

    Returns the insertion arguments and the preview result. Every rejection is an
    InsertError, so a caller that only writes after this returns cannot write an
    insertion that `proposal-promotion-proof` would not accept.
    """
    project = Path(project)
    ready, base_map, proposal = promotion_base(
        project, proposal_id, platform, target, tracker_reader=tracker_reader)
    if ready.state != "ready":
        data = preflight_as_json(ready)
        raise InsertError("Proposal `%s` 预检未通过: state=%s, diagnostic=%s"
                          % (proposal_id, data["state"], data.get("diagnostic", "-")))
    map_path = project / "spec" / "CAPABILITY-MAP.md"
    try:
        local_text = map_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise InsertError("无法读取本地能力图: %s" % error)
    if local_text != base_map:
        raise InsertError("本地 spec/CAPABILITY-MAP.md 与基线提交 %s 上的能力图不一致；"
                          "请先从该提交开晋级分支: git switch -c <晋级分支> %s"
                          % (ready.base_commit, ready.base_commit))
    change = proposal.change
    args = (change.module_id, change.responsibility,
            ", ".join(change.depends_on) or "—", change.anchor)
    result = preview(project, *args, interrupt=interrupt)

    tmp_fd, tmp_path_str = tempfile.mkstemp(prefix="spec-guard-module-insert-", suffix=".md")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(result["new_text"])
        try:
            new_parsed = parse_map(tmp_path)
        except MapError as error:
            raise InsertError("插入后的能力图未通过严格校验: %s" % error)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
    if not _matches(proposal, new_parsed):
        raise InsertError("按 Proposal `%s` 的声明插入后，新行或位置与声明不符"
                          "（例如锚点 `%s` 位于 Build order 的并行段中，新模块会被插到整段之后），"
                          "合并后无法被 proposal-promotion-proof 证明；未写入。"
                          % (proposal_id, change.anchor))
    result["proposal"] = {"id": proposal.proposal_id, "revision": proposal.revision,
                          "base_commit": ready.base_commit}
    result["proposal_conflict"] = False
    return args, result


def format_report(result):
    lines = []
    proposal = result.get("proposal")
    if proposal:
        lines.extend(["Proposal: %s" % proposal["id"],
                      "revision: %s" % proposal["revision"],
                      "baseCommit: %s" % proposal["base_commit"], ""])
    lines += ["新行:", "  " + result["row_text"], "", "新的 Build order:",
             "  " + result["build_order_line"], "", "能力图 diff:"]
    lines.extend(result["diff"] or ["（无变化）"])
    lines.append("")
    none_label = "无（全部完成）"
    old_current = result["old_current"] or none_label
    new_current = result["new_current"] or none_label
    if result["old_current"] == result["new_current"]:
        lines.append("插入后当前模块不变: %s" % old_current)
    else:
        lines.append("插入后当前模块将从 %s 变为 %s" % (old_current, new_current))
    interrupted = result.get("interrupted")
    if interrupted:
        lines.append("插队：被暂停的模块 `%s`，进度 已勾 %d/%d"
                     % (interrupted["id"], interrupted["checked"], interrupted["total"]))
        if result["new_current"] == interrupted["id"]:
            lines.append("插入后当前模块仍是 `%s`；请把 .agent/state.json 的 activeModule 改为 `%s` 再开始构建"
                         % (interrupted["id"], result["module_id"]))
    if result["existing_spec"]:
        lines.append("")
        lines.append("提示: spec/%s.md 已存在——插入后该模块阶段为 NEEDS_PLAN（视为已评审）；"
                     "若这份 Spec 尚未评审，先评审再 --confirm。" % result["module_id"])
    if result["proposal_conflict"]:
        lines.append("")
        lines.append("警告: 本地存在 spec/proposals/%s.md；若该 Proposal 之后发布，"
                     "将被判为 proposal-module-already-present。" % result["module_id"])
    return "\n".join(lines)


def main(argv=None, tracker_reader=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--id", dest="module_id")
    parser.add_argument("--responsibility")
    parser.add_argument("--depends-on", dest="depends_on")
    parser.add_argument("--anchor")
    parser.add_argument("--proposal",
                        help="从远端已发布且已接受的 Proposal 取出 id、职责、依赖与锚点；"
                             "不可与 --id/--responsibility/--depends-on/--anchor 同用")
    parser.add_argument("--platform", choices=("github", "gitlab", "local"),
                        help="仅与 --proposal 同用")
    parser.add_argument("--target", help="仅与 --proposal 同用")
    parser.add_argument("--interrupt", action="store_true",
                        help="允许在当前模块做到一半时显式插队")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)

    if args.proposal is None:
        missing = [flag for flag, value in (
            ("--id", args.module_id), ("--responsibility", args.responsibility),
            ("--depends-on", args.depends_on), ("--anchor", args.anchor)) if value is None]
        if missing:
            parser.error("the following arguments are required: %s" % ", ".join(missing))
        return _main_fields(args)
    return _main_proposal(args, tracker_reader)


def _main_fields(args):
    if args.confirm:
        try:
            outcome = write(args.project, args.module_id, args.responsibility,
                            args.depends_on, args.anchor, args.interrupt)
        except InsertError as error:
            print("校验失败: %s" % error, file=sys.stderr)
            return 1
        except OSError as error:
            print("写入失败: %s" % error, file=sys.stderr)
            return 1
        print("已写入: %s" % outcome["map_path"])
        print(format_stage_hint(outcome))
        if outcome["existing_spec"]:
            print(format_existing_spec_hint(outcome))
        return 0

    try:
        result = preview(args.project, args.module_id, args.responsibility,
                         args.depends_on, args.anchor, args.interrupt)
    except InsertError as error:
        print("校验失败: %s" % error, file=sys.stderr)
        return 1

    print(format_report(result))
    return 0


def _main_proposal(args, tracker_reader):
    try:
        given = [flag for flag, value in (
            ("--id", args.module_id), ("--responsibility", args.responsibility),
            ("--depends-on", args.depends_on), ("--anchor", args.anchor)) if value is not None]
        if given:
            raise InsertError("--proposal 不可与 %s 同用；这些字段全部取自 Proposal" % ", ".join(given))
        if not args.platform or not args.target:
            raise InsertError("--proposal 需要同时给出 --platform 与 --target")
        target = int(args.target) if args.platform == "gitlab" and args.target.isdigit() else args.target
        fields, result = prepare_proposal(args.project, args.proposal, args.platform, target,
                                          args.interrupt, tracker_reader)
        if not args.confirm:
            print(format_report(result))
            return 0
        outcome = write(args.project, *fields, interrupt=args.interrupt)
    except InsertError as error:
        print("校验失败: %s" % error, file=sys.stderr)
        return 1
    except OSError as error:
        print("写入失败: %s" % error, file=sys.stderr)
        return 1
    print("已写入: %s" % outcome["map_path"])
    print(format_stage_hint(outcome))
    if outcome["existing_spec"]:
        print(format_existing_spec_hint(outcome))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
