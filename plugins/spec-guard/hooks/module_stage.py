#!/usr/bin/env python3
"""Describe where the current module stands, for the phase-guard injection.

The current module is `.agent/state.json` activeModule when it names a mapped module,
otherwise the first module in Build order that is not done. A module needs a spec
(`spec/<id>.md`), then a plan (`tasks/<id>/plan.md`), then has open work while
`tasks/<id>/todo.md` has unchecked items; it is done once a plan exists and no
unchecked item remains. A formal deferral (`- [ ] 延期：<item>；恢复条件：<condition>`) is
not an unchecked item: it is listed apart and does not keep the module open.
Read-only: this never writes a file.
"""
from __future__ import annotations
import difflib
import json
import unicodedata
from pathlib import Path
import re
import subprocess
import sys
import zlib

from capability_map import MODULE_ID, MapError, _visible_lines, parse_map
from checkout_role import role as checkout_role_of
from project_config import STRUCTURAL, load as load_config
from sibling_plugins import delegate_review_entry
import usage_draft

# formal-deferral: the one deferred-item criterion.  What follows an unchecked box: the 延期/Deferred prefix, an item
# that is neither a checkpoint nor tiered, then 恢复条件/Resume when and a non-blank condition.  Anything short of that
# stays an ordinary unchecked item.  UNCHECKED and OPEN_ITEM exclude it, so every caller counts the same way.
DEFERRED_TAIL = (r"[ \t]+(?i:延期|deferred)[ \t]*[：:][ \t]*"
                 r"(?!(?i:检查点|checkpoint(?![a-z])))(?![^：:；;\n]*[（(][ \t]*(?i:gate|report)[ \t]*[）)])"
                 r"(?P<item>[^\n]*?[^\s；;][^\n]*?)[ \t]*[；;][ \t]*(?i:恢复条件|resume[ \t]+when)[ \t]*[：:]"
                 r"[ \t]*(?P<resume>\S[^\n]*?)[ \t\r]*$")
DEFERRED = re.compile(r"^\s*[-*+]\s+\[ \]" + DEFERRED_TAIL, re.MULTILINE)
UNCHECKED = re.compile(r"^\s*[-*+]\s+\[ \](?!" + DEFERRED_TAIL + ")", re.MULTILINE)
CHECKED = re.compile(r"^\s*[-*+]\s+\[[xX]\]", re.MULTILINE)
NO_TODO_MARKER = "<!-- spec-guard: no-todo -->"
# module-suspend: one exact line in todo.md parks a started module until the user resumes it.
SUSPEND_MARKER = "<!-- spec-guard: suspended -->"
# review-approval-marker: one exact line in spec/<id>.md or tasks/<id>/plan.md records where its review stands.
# A Spec approval carries the digest of the Spec's text, so an edit after approval shows up as `revised`.
REVIEW_PREFIX = "<!-- spec-guard: review"
REVIEW_PENDING = "<!-- spec-guard: review pending -->"
REVIEW_APPROVED = "<!-- spec-guard: review approved -->"
# plugin-interface: published in interface.json; scripts/check-interface.py keeps the two in step.
REVIEW_STATES = ("none", "pending", "approved", "codex-approved", "revised", "invalid")
REVIEW_APPROVED_DIGEST = re.compile(r"<!-- spec-guard: review approved ([0-9a-f]{12}) -->")
# codex-approval: Codex's approval under the module's takeover, kept apart from the user's; Spec and Plan both carry the
# digest, so an edit afterwards reads as `revised`.  Each review round is one line under the external review section.
REVIEW_CODEX_DIGEST = re.compile(r"<!-- spec-guard: review codex-approved ([0-9a-f]{12}) -->")
CODEX_ROUND = re.compile(r"<!-- spec-guard: codex-review round=(\d+) blocking=(\d+) sha256=([0-9a-f]{12}) -->")
# design-review: tasks/<id>/design.md of a new-flow module carries the same marker line (the user's `approved`, or a
# second reviewer's `reviewer-approved`), both over the text without its external review section, plus one round line
# per review.  vendor=none records a report in which no reviewer was available (selection "none").
DESIGN_REVIEW_STATES = ("none", "pending", "approved", "reviewer-approved", "revised", "invalid")
REVIEW_REVIEWER_DIGEST = re.compile(r"<!-- spec-guard: review reviewer-approved ([0-9a-f]{12}) -->")
DESIGN_ROUND = re.compile(r"<!-- spec-guard: design-review round=(\d+) blocking=(\d+) sha256=([0-9a-f]{12}) "
                          r"vendor=([a-z0-9][a-z0-9-]*) same-vendor=(true|false) criteria=([a-z0-9][a-z0-9.-]*) "
                          r"report=([0-9a-f]{64}|none) -->")
# sg-review-rules (design section 3): report=none only for a host subsession's round or a no-reviewer round
NO_REPORT_VENDORS = ("host", "none")


def design_round_match(line: str):
    """The DESIGN_ROUND match of a valid round line, else None (report=none with any other vendor is malformed)."""
    match = DESIGN_ROUND.fullmatch(line.strip())
    if match is None or (match.group(7) == "none" and match.group(4) not in NO_REPORT_VENDORS):
        return None
    return match
_DIGEST_MODULE = None


# flow-doc-skeletons: a new-flow (S110) module carries this line in spec/<id>.md; without it the old Spec -> Plan
# flow applies unchanged.  references/doc-skeletons.md is the human-readable copy of DOC_SECTIONS.
FLOW_MARKER = re.compile(r"<!-- spec-guard: flow v2 tier=(\S+) -->")
TIERS = ("bug", "small", "normal", "important")
# sg-gate-flow (rules 1-3): the user's answer to "release when done?", one line of its own under the flow marker, inside
# the requirement's approval digest (review_body only drops the review marker lines).  Only `yes` means anything.
RELEASE_PREAUTH = re.compile(r"<!-- spec-guard: release-preauth (\S+) -->")
RELEASE_AUTO = ("auto-confirm", "auto")
# sg-gate-flow (rules 6-8): a requirement that needs an overall design names the one file its modules share.
OVERALL_DESIGN = re.compile(r"<!-- spec-guard: overall-design (\S+) -->")
OVERALL_PATH = re.compile(r"spec/overall/[a-z0-9]+(?:-[a-z0-9]+)*\.md")
OVERALL_PREFIX = "<!-- spec-guard: overall-design"
OVERALL_STATUSES = ("approved", "missing", "pending", "revised", "invalid")  # release items that hand the release to autopilot and allow pre-authorisation
SHORT_TIERS = ("bug", "small")  # one document: no design, no separate regression document
DOC_SECTIONS = {
    "requirement": {"zh": ("目标", "给谁用", "使用场景", "业务规则和异常情形", "不做什么", "成功标准", "待定问题"),
                    "en": ("Objective", "Users", "Scenarios", "Rules and exceptions", "Out of scope", "Success criteria",
                           "Open questions")},
    "small": {"zh": ("做法", "回归用例"), "en": ("Approach", "Regression cases")},
    "bug": {"zh": ("复现步骤", "预期结果", "回归用例"), "en": ("Steps to reproduce", "Expected result", "Regression cases")},
    "design": {"zh": ("现状调研", "影响面", "实现方案", "接口和数据改动", "风险与回滚", "方案取舍"),
               "en": ("Current state", "Impact", "Implementation", "Interface and data changes", "Risks and rollback",
                      "Alternatives")},
    # sg-design-outline: a new project or module adds these four to the design; a multi-module one draws its interfaces
    "design-new": {"zh": ("技术选型", "架构图", "目录结构", "数据模型"),
                   "en": ("Technology choices", "Architecture diagram", "Directory layout", "Data model")},
    "design-interfaces": {"zh": ("模块接口",), "en": ("Module interfaces",)},
    "regression": {"zh": ("用例清单", "成功标准对照", "受影响的老功能"),
                   "en": ("Cases", "Success criteria coverage", "Affected existing features")},
    "plan": {"zh": ("任务", "检查点"), "en": ("Tasks", "Checkpoints")},
}


def flow_marker(root: Path, module: str) -> dict:
    """flow-doc-skeletons: the raw flow marker of spec/<id>.md -- never consults important(), so module_state may use it."""
    try:
        text = (root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {"v2": False, "tier": None, "problems": []}
    for line in _visible_lines(text.splitlines()):
        match = FLOW_MARKER.fullmatch(line.strip())
        if match:
            tier = match.group(1)
            if tier in TIERS:
                return {"v2": True, "tier": tier, "problems": []}
            return {"v2": True, "tier": "normal", "problems": ["tier-invalid"]}
    return {"v2": False, "tier": None, "problems": []}


def release_preauth_line(text: str) -> str | None:
    """sg-gate-flow: "yes", "invalid" (a release-preauth line with any other value) or None (no such line)."""
    for line in _visible_lines(text.splitlines()):
        match = RELEASE_PREAUTH.fullmatch(line.strip())
        if match:
            return "yes" if match.group(1) == "yes" else "invalid"
    return None


def release_allowed(root: Path, module: str) -> bool:
    """sg-gate-flow (rule 1): the module's effective takeover hands the release to autopilot."""
    from project_config import module_takeover  # late: project_config is imported by callers of this module
    return module_takeover(root, module)[0]["release"] in RELEASE_AUTO


def release_preauth(root: Path, module: str) -> bool | None:
    """sg-gate-flow (rule 3): /map --json takeover.releasePreauth.

    None for an old-flow module or a takeover that does not let autopilot release; True when the requirement carries
    `release-preauth yes` and its confirmation stands (the line is inside the digest, so an edit voids both); else False.
    """
    if not _v2(root, module) or not release_allowed(root, module):
        return None
    try:
        text = (root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    confirmed = requirement_wait(root, module) is None and review_state(text, "spec") != "invalid"
    return confirmed and release_preauth_line(text) == "yes"


def overall_design(root: Path, module: str) -> dict | None:
    """sg-gate-flow: {"path", "status"} of the overall design a flow v2 module points to; None without the line.

    Only the user approves it (rule 8): a Codex or reviewer marker counts as pending.  `invalid` covers a bad line or
    path (path then None) and a malformed marker; `revised` an approval whose digest no longer matches the file.
    """
    if not _v2(root, module):
        return None
    try:
        text = (root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    visible = [line.strip() for line in _visible_lines(text.splitlines())]
    lines = [match.group(1) for line in visible if (match := OVERALL_DESIGN.fullmatch(line))]
    # sg-design-outline: a line that starts like the marker but does not match it (no path, extra fields) is invalid,
    # not absent
    broken = any(line.startswith(OVERALL_PREFIX) and not OVERALL_DESIGN.fullmatch(line) for line in visible)
    if not lines and not broken:
        return None
    if broken:
        return {"path": None, "status": "invalid"}
    if len(lines) > 1 or not OVERALL_PATH.fullmatch(lines[0]):
        return {"path": None, "status": "invalid"}
    path = lines[0]
    try:
        design = (root / path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"path": path, "status": "missing"}
    except (OSError, UnicodeError):
        return {"path": path, "status": "invalid"}
    state = review_state(design, "spec")
    status = {"approved": "approved", "revised": "revised", "invalid": "invalid"}.get(state, "pending")
    if state == "revised" and REVIEW_CODEX_DIGEST.fullmatch(_review_split(design)[0][0]):
        status = "pending"  # a Codex marker never approved it, edited or not
    return {"path": path, "status": status}


def overall_problems(root: Path, module: str) -> list:
    """sg-gate-flow (verify-artifacts): [(level, message)] about a module's overall-design line and file.

    A bad line or path, or a missing file, fails.  An approval that is not in effect fails once the requirement is
    confirmed (the gate is then holding work back) and only warns before.  Modules of one usage draft pointing to
    different files warn (rule 7: one requirement shares one overall design).
    """
    found = overall_design(root, module)
    if found is None:
        return []
    spec = "`spec/%s.md`" % module
    if found["path"] is None:
        return [("fail", "%s 的 overall-design 行写坏了：只能有一行，路径只能是 `spec/overall/<kebab-case>.md`" % spec)]
    if found["status"] == "missing":
        return [("fail", "%s 指向的总体技术方案 `%s` 不存在" % (spec, found["path"]))]
    problems = []
    if found["status"] != "approved":
        level = "warn" if requirement_wait(root, module) else "fail"
        problems.append((level, "%s 指向的总体技术方案 `%s` 没有生效的用户批准（%s）" % (spec, found["path"], found["status"])))
    try:
        owners = usage_draft.milestones(str(root))
    except Exception:  # an unreadable draft is reported by the usage-draft check itself
        owners = {}
    draft = owners.get(module, (None,))[0]
    if draft:
        others = sorted({(other, seen["path"]) for other, (label, _m) in owners.items() if label == draft and other != module
                         for seen in (overall_design(root, other),) if seen and seen["path"] and seen["path"] != found["path"]})
        if others:
            problems.append(("warn", "%s 与同一份用法草案 `%s` 里的 %s 指向不同的总体技术方案" % (
                spec, draft, "、".join("`%s`（%s）" % pair for pair in others))))
    return problems


def overall_wait(root: Path, module: str) -> dict | None:
    """sg-gate-flow (rule 8): the overall design a confirmed requirement still waits for; None when nothing holds."""
    found = overall_design(root, module)
    if found is None or found["status"] == "approved" or requirement_wait(root, module):
        return None
    return found


def overall_hint(found: dict, module: str, stage: str, cmd: dict, zh: bool) -> tuple:
    """sg-gate-flow: (review line, next step) while the overall design holds the module."""
    path = found["path"] or "spec/overall/<name>.md"
    hold = _hold(None, module, stage, zh)
    mark = "%s --target overall --module %s" % (cmd["review-mark"], module)
    if zh:
        why = {"missing": "还没写", "pending": "等用户批", "revised": "批准后又改过，要用户重新批",
               "invalid": "标记行或文件写坏了（路径只能是 `spec/overall/<kebab-case>.md`）"}[found["status"]]
        return ("- 批准: 总体技术方案 `%s` %s（只由用户批，Codex 的批准不算）。" % (path, why),
                "写或改好总体技术方案（章节见插件 `references/doc-skeletons.md`），在对话正文里写出要点交用户批；用户在对话里批准后用 "
                "%s --state approved 记下来。批准前%s。" % (mark, hold))
    why = {"missing": "is not written yet", "pending": "waits for the user's approval",
           "revised": "was edited after it was approved; the user approves it again",
           "invalid": "has a malformed line or file (the path must be `spec/overall/<kebab-case>.md`)"}[found["status"]]
    return ("- Review: the overall design `%s` %s (only the user approves it; Codex's approval does not count)." % (path, why),
            "write or fix the overall design (sections in the plugin's `references/doc-skeletons.md`), put its points in "
            "the conversation and ask the user to approve; once they do, record it with %s --state approved. Until "
            "then %s." % (mark, hold))


def effective_tier(root: Path, module: str) -> dict:
    """flow-doc-skeletons: the marker's tier, lifted to important when the rules say the requirement is important."""
    flow = flow_marker(root, module)
    if flow["v2"] and flow["tier"] != "important" and important(root, module):
        return {"v2": True, "tier": "important", "problems": flow["problems"] + ["tier-below-rule"]}
    return flow


def review_approved_line(digest: str) -> str:
    return "<!-- spec-guard: review approved %s -->" % digest


def review_codex_line(digest: str) -> str:
    return "<!-- spec-guard: review codex-approved %s -->" % digest


REQUIREMENT_REVIEW_PREFIX = "<!-- spec-guard: requirement-review"
REQUIREMENT_HOST = re.compile(r"<!-- spec-guard: requirement-review reviewer=host blocking=(\d+) sha256=([0-9a-f]{12}) -->")
REQUIREMENT_NONE = re.compile(r"<!-- spec-guard: requirement-review reviewer=none sha256=([0-9a-f]{12}) reason=(.+?) -->")
REASON_LIMIT = 200


def requirement_reason_problem(reason: str) -> str | None:
    """sg-review-rules (rule 2): why a no-reviewer reason cannot be recorded, None when it can (one line, at most
    REASON_LIMIT characters, no `--` or `>`, which would end the record line's comment)."""
    if "\n" in reason or "\r" in reason:
        return "it spans more than one line"
    reason = reason.strip()
    if not reason:
        return "it is empty"
    if len(reason) > REASON_LIMIT:
        return "it is longer than %d characters" % REASON_LIMIT
    if "--" in reason or ">" in reason:
        return "it contains -- or >"
    return None


def requirement_review_records(text: str) -> list:
    """sg-review-rules (rule 2): [{"reviewer": codex|host|none, "blocking", "sha256", "reason"}] of a requirement's
    review records outside code fences, in file order: Codex rounds, host subsession reviews and no-reviewer lines."""
    found = []
    for line in _visible_lines(text.splitlines()):
        line = line.strip()
        codex, host, none = CODEX_ROUND.fullmatch(line), REQUIREMENT_HOST.fullmatch(line), REQUIREMENT_NONE.fullmatch(line)
        if codex:
            found.append({"reviewer": "codex", "blocking": int(codex.group(2)), "sha256": codex.group(3), "reason": None})
        elif host:
            found.append({"reviewer": "host", "blocking": int(host.group(1)), "sha256": host.group(2), "reason": None})
        elif none and requirement_reason_problem(none.group(2)) is None:
            found.append({"reviewer": "none", "blocking": 0, "sha256": none.group(1), "reason": none.group(2).strip()})
    return found


def requirement_review_broken(text: str) -> int:
    """sg-review-rules: requirement-review lines outside code fences that are not a valid record."""
    return sum(1 for line in _visible_lines(text.splitlines()) if line.strip().startswith(REQUIREMENT_REVIEW_PREFIX)
               and not (REQUIREMENT_HOST.fullmatch(line.strip()) or (REQUIREMENT_NONE.fullmatch(line.strip()) and
                        requirement_reason_problem(REQUIREMENT_NONE.fullmatch(line.strip()).group(2)) is None)))


def codex_round_records(text: str) -> list:
    """review-rounds-in-map: [{"round", "blocking", "sha256"}] from the round lines outside code fences, in file order.
    sha256 is the 12-hex prefix the round line keeps of the reviewed file's sha256 (its value in the report's scope.files)."""
    return [{"round": int(match.group(1)), "blocking": int(match.group(2)), "sha256": match.group(3)}
            for match in (CODEX_ROUND.fullmatch(line.strip()) for line in _visible_lines(text.splitlines()))
            if match]


def review_reviewer_line(digest: str) -> str:
    return "<!-- spec-guard: review reviewer-approved %s -->" % digest


def design_round_records(text: str) -> list:
    """design-review: [{"round", "blocking", "sha256", "vendor", "sameVendor", "criteria", "report"}] from the round
    lines outside code fences, in file order.  vendor "none" is a round in which no reviewer was available; vendor "host"
    a host subsession's round (sg-review-rules), which has no report (report None)."""
    return [{"round": int(match.group(1)), "blocking": int(match.group(2)), "sha256": match.group(3),
             "vendor": match.group(4), "sameVendor": match.group(5) == "true", "criteria": match.group(6),
             "report": None if match.group(7) == "none" else match.group(7)}
            for match in (design_round_match(line) for line in _visible_lines(text.splitlines()))
            if match]


def codex_rounds(text: str) -> list:
    """codex-approval: [(round, blocking)] from the round lines outside code fences, in file order."""
    return [(record["round"], record["blocking"]) for record in codex_round_records(text)]


def review_marker_lines(text: str) -> list:
    """Indexes (into `splitlines(keepends=True)`) of the marker lines.  A fenced code block holds examples, not markers."""
    return [index for index, line in enumerate(_visible_lines(text.splitlines(keepends=True)))
            if line.strip().startswith(REVIEW_PREFIX)]


def _review_split(text: str) -> tuple:
    """(marker lines, text without them)."""
    lines, marked = text.splitlines(keepends=True), set(review_marker_lines(text))
    return ([lines[index].strip() for index in sorted(marked)],
            "".join(line for index, line in enumerate(lines) if index not in marked))


def review_body(text: str) -> str:
    return _review_split(text)[1]


def review_digest(text: str) -> str:
    """Digest of the text without its marker line; the algorithm lives in spec-digest.py only.

    regression-doc-check Task 8: a flow v2 bug requirement leaves the body of its regression cases section out, so the
    case added once the bug is fixed does not undo the user's confirmation.  `whole_review_digest` is the digest
    0.96.0 and earlier wrote; review_state accepts both."""
    return whole_review_digest(_without_bug_cases(review_body(text)))


def whole_review_digest(body: str) -> str:
    global _DIGEST_MODULE
    if _DIGEST_MODULE is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("spec_guard_digest", Path(__file__).with_name("spec-digest.py"))
        _DIGEST_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_DIGEST_MODULE)
    return _DIGEST_MODULE.text_digest(body)


BUG_CASE_SECTIONS = ("回归用例", "Regression cases")  # DOC_SECTIONS["bug"]'s last section, in both languages


def _without_bug_cases(body: str) -> str:
    """The body with a bug requirement's regression cases section emptied (its heading kept); other text unchanged."""
    lines = body.splitlines(keepends=True)
    visible = _visible_lines(lines)
    if not any((m := FLOW_MARKER.fullmatch(line.strip())) and m.group(1) == "bug" for line in visible):
        return body
    kept, inside = [], False
    for raw, seen in zip(lines, visible):
        heading = SECTION_HEADING.match(seen.rstrip("\r\n"))
        if heading:
            inside = heading.group(1) in BUG_CASE_SECTIONS
            kept.append(raw)
        elif not inside:
            kept.append(raw)
    return "".join(kept)


def _text_digest(text: str) -> str:
    """Digest of the whole text (`spec-digest.py text`); the algorithm lives in spec-digest.py only."""
    return whole_review_digest(text)


def review_codex_digest(text: str) -> str:
    """codex-approval (M3 second rework): `review_digest` without the external review section.

    The rule asks for a reason per Codex suggestion in that section, after the approval; it records the review, it is
    not what Codex approved.  The section runs from its heading to the next `## ` heading.
    """
    kept, inside = [], False
    for line in text.splitlines(keepends=True):
        if EXTERNAL_REVIEW_HEADING.match(line.rstrip("\r\n")):
            inside = True
            continue
        if inside and line.startswith("## "):
            inside = False
        if not inside:
            kept.append(line)
    return review_digest("".join(kept))


def review_state(text: str, kind: str) -> str:
    """`none`, `pending`, `approved`, `revised` (Spec only) or `invalid`; `kind` is `spec` or `plan`.

    `kind` `design` (design-review) reads tasks/<id>/design.md: DESIGN_REVIEW_STATES, never `codex-approved`."""
    markers = _review_split(text)[0]
    if not markers:
        return "none"
    if len(markers) > 1:
        return "invalid"
    if markers[0] == REVIEW_PENDING:
        return "pending"
    if kind == "design":
        # design-review: both approvals leave out the external review section, where the rounds and reasons go.
        match = REVIEW_APPROVED_DIGEST.fullmatch(markers[0]) or REVIEW_REVIEWER_DIGEST.fullmatch(markers[0])
        if not match:
            return "invalid"
        if match.group(1) != review_codex_digest(text):
            return "revised"
        return "approved" if match.re is REVIEW_APPROVED_DIGEST else "reviewer-approved"
    codex = REVIEW_CODEX_DIGEST.fullmatch(markers[0])
    if codex:
        # 0.91.0/0.91.1 wrote the digest of the whole text; it still counts.
        return "codex-approved" if codex.group(1) in (review_codex_digest(text), review_digest(text)) else "revised"
    if kind == "plan":
        return "approved" if markers[0] == REVIEW_APPROVED else "invalid"
    match = REVIEW_APPROVED_DIGEST.fullmatch(markers[0])
    if not match:
        return "invalid"
    return "approved" if match.group(1) in (review_digest(text), whole_review_digest(review_body(text))) else "revised"


def deferred_items(text: str) -> list:
    """[(item, resume condition)] of the todo's formal deferrals, in order (see DEFERRED_TAIL)."""
    return [(match.group("item").strip(), match.group("resume").strip()) for match in DEFERRED.finditer(text)]


DEFERRAL_PREFIX = re.compile(r"^\s*[-*+]\s+\[ \][ \t]+(?i:延期|deferred)[ \t]*[：:]")
DEFERRAL_WORD = re.compile(r"(?i:延期|deferred)")
CHECKPOINT_DEFERRAL = re.compile(DEFERRAL_PREFIX.pattern + r"[ \t]*(?:(?i:检查点|checkpoint(?![a-z]))"
                                 r"|[^：:；;\n]*[（(][ \t]*(?i:gate|report)[ \t]*[）)])")


def deferral_lint(text: str) -> list:
    """[(kind, line number)] for verify-artifacts: formal, checkpoint, malformed (prefix without the full form),
    informal (an unchecked item that mentions a deferral in free text).  The criterion itself is DEFERRED."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if DEFERRED.match(line):
            found.append(("formal", number))
        elif CHECKPOINT_DEFERRAL.match(line):
            found.append(("checkpoint", number))
        elif DEFERRAL_PREFIX.match(line):
            found.append(("malformed", number))
        elif UNCHECKED.match(line) and DEFERRAL_WORD.search(line):
            found.append(("informal", number))
    return found


# flow-doc-skeletons: the stages between an approved requirement and the Plan.  NEEDS_DESIGN and NEEDS_REGRESSION
# occur only on flow v2 modules; every "Spec written, Plan not yet" test reads BEFORE_PLAN.
BEFORE_PLAN = ("NEEDS_DESIGN", "NEEDS_REGRESSION", "NEEDS_PLAN")
SKELETONS_REF = "references/doc-skeletons.md"


def doc_step(module: str, stage: str, zh: bool) -> str:
    """flow-doc-skeletons: what a flow v2 module writes at a before-the-Plan stage, with its skeleton; no final period."""
    if zh:
        return {"NEEDS_DESIGN": "写技术方案 `tasks/%s/design.md`（章节见 spec-guard 插件的 `%s`「技术方案」一节）" % (module, SKELETONS_REF),
                "NEEDS_REGRESSION": "写回归测试文档 `tasks/%s/regression.md`（章节见 spec-guard 插件的 `%s`「回归测试文档」一节）"
                                    % (module, SKELETONS_REF),
                "NEEDS_PLAN": "写 `tasks/%s/plan.md`（只留任务列表与检查点，章节见 spec-guard 插件的 `%s`「Plan」一节）和 `tasks/%s/todo.md`"
                              % (module, SKELETONS_REF, module)}[stage]
    return {"NEEDS_DESIGN": "write the design `tasks/%s/design.md` (sections: the design part of the spec-guard plugin's `%s`)"
                            % (module, SKELETONS_REF),
            "NEEDS_REGRESSION": "write the regression document `tasks/%s/regression.md` (sections: the regression part of the "
                                "spec-guard plugin's `%s`)" % (module, SKELETONS_REF),
            "NEEDS_PLAN": "write `tasks/%s/plan.md` (tasks and checkpoints only; sections: the Plan part of the spec-guard "
                          "plugin's `%s`) and `tasks/%s/todo.md`" % (module, SKELETONS_REF, module)}[stage]


def flow_tier_line(root: Path, module: str, zh: bool) -> str:
    """flow-doc-skeletons: one line when the flow marker's tier is invalid or below what the rules say; else empty."""
    flow = effective_tier(root, module)
    if not flow["problems"]:
        return ""
    if zh:
        why = "、".join({"tier-invalid": "档位不是 bug／small／normal／important 之一", "tier-below-rule": "规则判为重要需求"}[p]
                       for p in flow["problems"])
        return "- 档位: `spec/%s.md` 的流程标记%s，按 `%s` 处理。" % (module, why, flow["tier"])
    why = " and ".join({"tier-invalid": "names no known tier (bug, small, normal, important)",
                        "tier-below-rule": "is below what the rules decide (an important requirement)"}[p]
                       for p in flow["problems"])
    return "- Tier: the flow marker in `spec/%s.md` %s; treated as `%s`." % (module, why, flow["tier"])


FLOW_DOCS = (("requirement", "spec/%s.md"), ("design", "tasks/%s/design.md"), ("regression", "tasks/%s/regression.md"),
             ("plan", "tasks/%s/plan.md"))
SECTION_HEADING = re.compile(r"^##\s+(.+?)\s*$")


def _sections(text: str) -> set:
    return {match.group(1) for match in (SECTION_HEADING.match(line) for line in _visible_lines(text.splitlines()))
            if match}


def project_sections(root: Path) -> dict:
    """project-sections: {requirement, design, regression: (section name, ...)} from the project config; empty when unset or invalid."""
    try:
        declared = load_config(root)[0].get("projectSections", {})
    except Exception:  # a failed read changes nothing: verify-artifacts reports the config
        declared = {}
    return {doc: tuple(name.strip() for name in declared.get(doc, ())) for doc in ("requirement", "design", "regression")}


def sections_sentence(root: Path, stage: str, zh: bool) -> str:
    """project-sections: the sentence after the next step naming this project's extra sections; empty when none apply."""
    doc = {"NEEDS_SPEC": "requirement", "NEEDS_DESIGN": "design", "NEEDS_REGRESSION": "regression"}.get(stage)
    names = project_sections(root).get(doc, ()) if doc else ()
    if not names:
        return ""
    if stage == "NEEDS_SPEC":
        return ("按新流程写需求文档时，另加本项目要求的章节：%s。" % "、".join(names) if zh else
                " When writing the requirement in the new flow, also add this project's sections: %s." % ", ".join(names))
    return ("另加本项目要求的章节：%s。" % "、".join(names) if zh else
            " Also add this project's sections: %s." % ", ".join(names))


def requirement_review(root: Path, module: str) -> dict | None:
    """sg-review-rules (rules 1-5): {"required", "status", "records"} of a flow v2 requirement; None for an old module.

    required: the effective tier is normal or important (a lifted bug or small included).  status: not-required,
    missing (required and no record) or reviewed (one record is enough: one round only, later edits do not undo it).
    """
    flow = effective_tier(root, module)
    if not flow["v2"]:
        return None
    try:
        text = (root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        text = ""
    required = flow["tier"] in ("normal", "important")
    records = requirement_review_records(text)
    status = "not-required" if not required else ("reviewed" if records else "missing")
    return {"required": required, "status": status, "records": records}


_BATCH_CACHE: dict = {}


def _cached_batches(root: Path) -> list:
    """usage_draft.batches, read once per project state (root, HEAD, the capability map's mtime and size) within this
    process (sg-design-outline); raises UsageDraftError like it, and a failure is not cached."""
    try:
        stat = (root / "spec" / "CAPABILITY-MAP.md").stat()
        mapped = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        mapped = None
    key = (str(root.resolve()), _git(root, "rev-parse", "--verify", "--quiet", "HEAD"), mapped)
    if key not in _BATCH_CACHE:
        _BATCH_CACHE[key] = usage_draft.batches(str(root))
    return _BATCH_CACHE[key]


def design_outline_case(root: Path, module: str) -> dict | None:
    """sg-design-outline (rules 1-4): {"new", "important", "cross"} of a flow v2 module with a design; None otherwise.

    new: exactly one well-formed overall-design line with a valid path, whatever the overall design's state.
    important: the effective tier.  cross: inserted into the capability map in one batch with another module; False
    when git cannot tell.
    """
    flow = effective_tier(root, module)
    if not flow["v2"] or flow["tier"] in SHORT_TIERS:
        return None
    overall = overall_design(root, module)
    try:
        cross = any(module in modules and len(modules) > 1 for _, modules in _cached_batches(root))
    except usage_draft.UsageDraftError:
        cross = False
    return {"new": overall is not None and overall["path"] is not None, "important": flow["tier"] == "important",
            "cross": cross}


def flow_doc_problems(root: Path, module: str) -> list:
    """flow-doc-skeletons: [(level, message)] for a flow v2 module's documents; [] for an old-flow module.

    A document is required once a later one exists (a module still writing its design lacks nothing); every document
    that exists must carry its skeleton sections, in Chinese or English, possibly saying "不涉及".
    """
    flow = effective_tier(root, module)
    if not flow["v2"]:
        return []
    found = [("warn", "`spec/%s.md` 的流程标记%s" % (module, {"tier-invalid": "档位无效，按 normal 处理",
                                                          "tier-below-rule": "档位低于规则判定，按 important 处理"}[p]))
             for p in flow["problems"]]
    short = flow["tier"] in SHORT_TIERS
    docs = [(kind, pattern % module) for kind, pattern in FLOW_DOCS if not (short and kind in ("design", "regression"))]
    present = [(root / path).is_file() for _, path in docs]
    extra = project_sections(root)
    last = max((index for index, here in enumerate(present) if here), default=-1)
    for index, (kind, path) in enumerate(docs):
        if not present[index]:
            if index < last:
                found.append(("fail", "`%s` 缺失（档位 %s，后面的文档已经写了）" % (path, flow["tier"])))
            continue
        wanted = {"requirement": ("bug",) if flow["tier"] == "bug" else
                  (("requirement", "small") if flow["tier"] == "small" else ("requirement",))}.get(kind, (kind,))
        if kind == "design" and (design_outline_case(root, module) or {}).get("new"):
            wanted = ("design", "design-new")  # sg-design-outline (rule 5): missing ones fail like any skeleton section
        try:
            have = _sections((root / path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            found.append(("fail", "`%s` 读不了" % path))
            continue
        missing = [zh for group in wanted for zh, en in zip(DOC_SECTIONS[group]["zh"], DOC_SECTIONS[group]["en"])
                   if zh not in have and en not in have]
        missing += [name for name in extra.get(kind, ()) if name not in have]
        if missing:
            found.append(("fail", "`%s` 缺章节：%s" % (path, "、".join(missing))))
        text = (root / path).read_text(encoding="utf-8")
        empty = [name for name in extra.get(kind, ()) if name in have and not _section_has_content(text, name)]
        if empty:  # regression-doc-check: a declared project section needs content or 不涉及 (Q2 A: only these)
            found.append(("fail", "`%s` 章节没有内容（section-empty）：%s" % (path, "、".join(empty))))
        if kind == "requirement" and requirement_review_broken(text):  # sg-review-rules
            found.append(("fail", "`%s` 有 %d 行需求文档审查记录写坏了" % (path, requirement_review_broken(text))))
        if kind == "regression" or (kind == "requirement" and short and any(n in have for n in SHORT_CASES_SECTION)):
            found += regression_problems(root, module, flow["tier"], path)
    return found


SHORT_CASES_SECTION = ("回归用例", "Regression cases")
COMMENT_LINE = re.compile(r"^\s*<!--.*-->\s*$")


def _section_has_content(text: str, name: str) -> bool:
    """regression-doc-check: a line under the section that is neither blank nor a lone HTML comment (fenced text counts)."""
    import regression_view
    lines = regression_view._section_lines(text, (name,)) or []
    return any(line.strip() and (in_fence or not COMMENT_LINE.match(line)) for _n, line, in_fence, _m in lines)


VERIFICATION_SCRIPT = Path(__file__).resolve().parent / "verification.py"


def author_line(root: Path, module: str | None, stage: str, zh: bool) -> tuple:
    """verification-criteria (assumption 3): (fact, line) while a flow v2 module is built and no author is recorded."""
    if stage != "BUILDING" or not module or not _v2(root, module):
        return None, ""
    import verification
    if verification.authors(root, module):
        return None, ""
    command = "`python3 -B %s author --project <project-root> --module %s`" % (VERIFICATION_SCRIPT, module)
    if zh:
        return ("author", "none"), ("- 作者记录：本模块还没有记下作者会话。写代码的会话先运行 %s（会话 id 取自环境变量，"
                                    "记在 git 目录里、不进提交），合并前验证据此判断执行者不是作者。" % command)
    return ("author", "none"), ("- Author record: no authoring session is recorded for this module yet. The session writing "
                                "the code runs %s first (the session id comes from the environment; the record stays in the "
                                "git directory, uncommitted); the pre-merge verification uses it to tell the executor is "
                                "not an author." % command)


def verification_line(root: Path, module: str | None, stage: str, zh: bool) -> tuple:
    """verification-criteria (assumption 7): (fact, line) at a flow v2 module's final gate: none, stale, fail or passed."""
    if stage not in ("BUILDING", "DONE") or not module or not _v2(root, module):
        return None, ""
    try:
        text = (root / "tasks" / module / "todo.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, ""
    if not final_gate_text(text):
        return None, ""
    import verification
    from project_config import module_takeover
    auto = module_takeover(root, module)[0].get("merge") == "auto"
    state = verification.verification_state(root, module)
    if state is None:
        kind = "none"
    elif not state["current"]:
        kind = "stale"
    else:
        kind = state["verdict"]
    notes = len(state["notes"]) if state else 0
    zh_words = {"none": "还没有结论；等非作者照回归文档执行（autopilot 的 ⑦），校验成立后用 `verification.py record` 记下"
                        + ("" if auto else "。没有结论时由用户在最终验收里决定是否合并，验收消息里写明没有结论"),
                "stale": "结论已过期（补丁或回归文档变了），要重新验证",
                "fail": "不通过，不要合并；失败的用例与证据见报告",
                "pass": "通过" + ("，最终 gate 已算过，合并后补勾" if auto else "，验收消息里写明结论"),
                "pass-with-notes": "通过但附意见（%d 条）" % notes + ("，最终 gate 已算过，合并后补勾" if auto else "，验收消息里写明结论与意见")}
    en_words = {"none": "no verdict yet; a non-author runs the regression document (autopilot's step 7) and records a "
                        "standing report with `verification.py record`" + ("" if auto else "; without one the user decides "
                        "at the final acceptance, and the acceptance message says there is no verdict"),
                "stale": "the verdict is stale (the patch or the regression document changed); verify again",
                "fail": "failed; do not merge -- the failing cases and their evidence are in the report",
                "pass": "passed" + ("; the final gate counts as passed, tick it after the merge" if auto else
                                    "; state the verdict in the acceptance message"),
                "pass-with-notes": "passed with notes (%d)" % notes + ("; the final gate counts as passed, tick it after "
                                   "the merge" if auto else "; state the verdict and the notes in the acceptance message")}
    line = ("- 合并前验证：%s。" % zh_words[kind]) if zh else ("- Pre-merge verification: %s." % en_words[kind])
    return ("verification", kind, notes, auto), line


REGRESSION_SHOWN = 3


def regression_line(root: Path, module: str | None, stage: str, zh: bool) -> tuple:
    """regression-doc-check: (fact, line) for a flow v2 module writing its Plan or building; (None, "") otherwise.

    Fixed words, problem codes, case ids and paths only -- never the document's text.
    """
    if not module or stage not in ("NEEDS_PLAN", "BUILDING"):
        return None, ""
    flow = effective_tier(root, module)
    if not flow["v2"]:
        return None, ""
    short = flow["tier"] in SHORT_TIERS
    path = "spec/%s.md" % module if short else "tasks/%s/regression.md" % module
    if not (root / path).is_file():
        return None, ""
    problems = regression_problems(root, module, flow["tier"], path)
    if not problems:
        return None, ""
    marker = "` 回归问题："
    parts = [message.split(marker, 1)[1] for _level, message in problems if marker in message]
    if flow["tier"] == "bug" and parts == ["no-cases（%s）" % path]:
        return ("regression", "bug-no-case"), ("- 回归用例：修完在 `%s` 的回归用例一节补一条用例。" % path if zh else
                                              "- Regression: once fixed, add a case to the regression cases section of `%s`." % path)
    shown = parts[:REGRESSION_SHOWN]
    if zh:
        line = "- 回归文档：`%s` 有 %d 处问题：%s%s；完整列表跑 verify-artifacts。" % (
            path, len(parts), "、".join(shown), "等" if len(parts) > len(shown) else "")
    else:
        line = "- Regression: `%s` has %d problem(s): %s%s; run verify-artifacts for the full list." % (
            path, len(parts), ", ".join(p.replace("（", " (").replace("）", ")") for p in shown),
            ", ..." if len(parts) > len(shown) else "")
    return ("regression", len(parts)), line


def regression_problems(root: Path, module: str, tier: str, path: str) -> list:
    """regression-doc-check: [(level, message)] from regression_view for a flow v2 module's regression cases.

    bug: no case yet is a warning while the work goes on and a failure once the module is done with a real todo
    (R1-3, R2-3); every other problem fails.
    """
    import regression_view
    try:
        report = regression_view.module_report(root, module)
    except regression_view.ViewError:
        return []  # not v2 or the document is gone: the section checks above already said so
    found = []
    for problem in report["problems"]:
        level = "fail"
        if tier == "bug" and problem["code"] == "no-cases":
            state = _base_state(root, module)
            todo = root / "tasks" / module / "todo.md"
            text = todo.read_text(encoding="utf-8") if todo.is_file() else ""
            ticked = bool(CHECKED.search(text)) or bool(state["deferred"])
            if state["stage"] == "DONE" and state["todo"] and ticked:
                level = "fail"
            elif state["stage"] in ("BUILDING", "DONE"):
                level = "warn"
            else:
                continue
        found.append((level, "`%s` 回归问题：%s（%s）" % (path, problem["code"], problem["where"])))
    return found


def _v2(root: Path, module: str) -> bool:
    return flow_marker(root, module)["v2"]


# requirement-confirm-gate: why a flow v2 requirement still waits for the user; published as requirementConfirm.status.
REQUIREMENT_WAITS = ("pending", "codex", "revised")


def requirement_wait(root: Path, module: str) -> str | None:
    """requirement-confirm-gate: `pending`, `codex` or `revised` while a v2 requirement waits for the user, else None.

    No marker counts as pending (a v2 requirement is always confirmed by the user).  `codex` is a Codex marker, its
    digest matching or not: Codex never confirms a requirement, so an edit after it is not a revision of a
    confirmation.  None for an old-flow module, a confirmed requirement, and an invalid or unreadable marker (those are
    reported by the review line and verify-artifacts).
    """
    if not module or not _v2(root, module):
        return None
    try:
        text = (root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    state = review_state(text, "spec")
    if state in ("none", "pending"):
        return "pending"
    if state == "codex-approved":
        return "codex"
    if state == "revised":
        markers = _review_split(text)[0]
        return "codex" if markers and REVIEW_CODEX_DIGEST.fullmatch(markers[0]) else "revised"
    return None


# interface.json mapView.flow.requirementConfirmStatus (requirement-confirm-gate, interface 1.19).
REQUIREMENT_STATUSES = ("confirmed", "pending", "revised", "invalid")
REQUIREMENT_AT_LIMIT = 50  # commits of spec/<id>.md walked back to date a confirmation; beyond it `at` is null


def requirement_confirm(root: Path, module: str) -> dict | None:
    """requirement-confirm-gate: {status, by, at, sha256} of a v2 requirement; None for an old-flow module."""
    if not module or not _v2(root, module):
        return None
    try:
        text = (root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None  # /map --json fails as a whole on an unreadable Spec before it gets here
    wait = requirement_wait(root, module)
    if review_state(text, "spec") == "invalid":
        status = "invalid"
    else:
        status = "confirmed" if wait is None else ("revised" if wait == "revised" else "pending")
    markers = _review_split(text)[0]
    return {"status": status, "by": "user" if status == "confirmed" else None,
            "at": _confirmed_at(root, module, markers[0]) if status == "confirmed" else None,
            "sha256": _text_digest(text)}  # the whole file, as `spec-digest.py text` prints it (AC5)


def _confirmed_at(root: Path, module: str, line: str) -> str | None:
    """Commit time of the earliest commit in the unbroken run, back from HEAD, whose Spec carries this marker line."""
    relative = "spec/%s.md" % module

    def carries(commit: str) -> bool:
        blob = _git(root, "show", "%s:%s" % (commit, relative))
        return blob is not None and line in _review_split(blob)[0]

    if not carries("HEAD"):
        return None  # not committed yet, or written back after a committed removal
    log = _git(root, "log", "-n", str(REQUIREMENT_AT_LIMIT + 1), "--format=%H%x09%cI", "--", relative)
    rows = [row.split("\t") for row in (log or "").splitlines() if "\t" in row]
    earliest = None
    for sha, when in rows[:REQUIREMENT_AT_LIMIT]:
        if not carries(sha):
            return earliest
        earliest = when
    return earliest if len(rows) <= REQUIREMENT_AT_LIMIT else None


DIFF_HINT_LINES = 60  # sg-review-rules: lines of the since-review diff the phase hint shows; the preview shows all


def requirement_review_diff(root: Path, module: str) -> dict:
    """sg-review-rules (rule 2, S9): what changed in spec/<id>.md since its review record.

    The reviewed text is the newest of the last REQUIREMENT_AT_LIMIT commits of the file whose whole text has the
    record's digest.  Both sides are compared without the approval marker and the external review section, which hold
    the review records and findings rather than the requirement: {"status": "unchanged"} when the rest is the same,
    {"status": "found", "commit", "diff"} with a unified diff of the rest otherwise, {"status": "unavailable",
    "reason"} when there is no record, no such commit, or git cannot be read.  Read-only.
    """
    review = requirement_review(root, module)
    relative = "spec/%s.md" % module
    if not review or not review["records"]:
        return {"status": "unavailable", "reason": "no review record"}
    target = review["records"][-1]["sha256"]
    try:
        current = (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return {"status": "unavailable", "reason": "%s: %s" % (relative, type(error).__name__)}
    if _text_digest(current) == target:
        return {"status": "unchanged"}
    now = _requirement_body(current)

    def run(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=5)

    try:
        log = run("log", "-n", str(REQUIREMENT_AT_LIMIT), "--format=%H", "--", relative)
        if log.returncode != 0:
            return {"status": "unavailable", "reason": "git log failed (not a git repository, or no commit yet)"}
        for sha in log.stdout.decode("ascii", "replace").split():
            shown = run("show", "%s:./%s" % (sha, relative))
            if shown.returncode != 0:
                continue
            try:
                text = shown.stdout.decode("utf-8")
            except UnicodeError:
                continue
            if _text_digest(text) == target:
                then = _requirement_body(text)
                if then == now:
                    return {"status": "unchanged"}
                diff = "".join(difflib.unified_diff(then.splitlines(keepends=True), now.splitlines(keepends=True),
                                                    fromfile="%s (reviewed, %s)" % (relative, sha[:7]),
                                                    tofile="%s (now)" % relative))
                return {"status": "found", "commit": sha, "diff": diff}
    except (OSError, subprocess.SubprocessError) as error:
        return {"status": "unavailable", "reason": "git could not be read (%s)" % type(error).__name__}
    return {"status": "unavailable", "reason": "the reviewed text is not in the last %d commits of %s (reviewed before "
                                               "it was committed, or too far back)" % (REQUIREMENT_AT_LIMIT, relative)}


def _requirement_body(text: str) -> str:
    """The requirement without its approval marker and its external review section (sg-review-rules)."""
    kept, inside = [], False
    for line in text.splitlines(keepends=True):
        if EXTERNAL_REVIEW_HEADING.match(line.rstrip("\r\n")):
            inside = True
            continue
        if inside and line.startswith("## "):
            inside = False
        if not inside:
            kept.append(line)
    return review_body("".join(kept)).rstrip("\n") + "\n"  # the section's leading blank line is not a change


def _review_diff_text(root: Path, module: str, zh: bool) -> str:
    """The since-review part of the confirmation step: the diff, at most DIFF_HINT_LINES lines, or why there is none."""
    got = requirement_review_diff(root, module)
    if got["status"] == "unchanged":
        return " 审查后没有改动。" if zh else " Nothing changed since the review."
    if got["status"] == "unavailable":
        return (" 审查以来的改动取不到：%s；交用户时说明这一点，给出整份需求。" % got["reason"] if zh else
                " The changes since the review cannot be shown: %s; say so and give the user the whole requirement."
                % got["reason"])
    lines = got["diff"].splitlines()
    shown = "\n".join(lines[:DIFF_HINT_LINES])
    more = len(lines) - DIFF_HINT_LINES
    tail = ""
    if more > 0:
        tail = ("\n还有 %d 行，`review-mark --target spec --state approved` 的预览里有全文。" % more if zh else
                "\n%d more line(s); the preview of `review-mark --target spec --state approved` prints them all." % more)
    return ((" 审查以来的改动（照原样给用户看）：\n```diff\n%s\n```%s" if zh else
             " Changes since the review (show them to the user verbatim):\n```diff\n%s\n```%s") % (shown, tail))


def _review_first_step(module: str, cmd: dict, zh: bool) -> str:
    """sg-review-rules (rules 2-4, S2): the next step while a required requirement has no review record."""
    path, mark = "spec/%s.md" % module, cmd["review-mark"]
    review = "/delegate:review --backend auto --author-host %s --paths %s" % (cmd["author-host"], path)
    if zh:
        return ("需求文档要先审一轮，再交用户确认。三条路选一条：装了 delegate 就用 `%s` 审，把标准输出的 JSON 存成仓库外的文件，"
                "用 %s `--target spec --state codex-reviewed --review <文件>` 记下；没装 delegate 就开一个不带本会话上下文的全新子会话审，"
                "把它的结论原话写进「外部审查意见」一节，用 %s `--target spec --state host-reviewed --blocking <阻断数>` 记下；"
                "都不行就用 %s `--target spec --state no-reviewer --reason \"<一行原因>\"` 写明原因。只审一轮：按意见改完直接复述交用户，"
                "附上审查提了什么、改了哪些、哪些没采纳及原因。记下之前不要请用户确认。" % (review, mark, mark, mark))
    return ("Review the requirement once before the user confirms it. Pick one way: with delegate installed, review it with "
            "`%s`, save the standard-output JSON to a file outside the repository and record it with %s `--target spec "
            "--state codex-reviewed --review <file>`; without delegate, have a fresh host subsession with none of this "
            "conversation's context review it, write its findings verbatim into the external review section and record "
            "it with %s `--target spec --state host-reviewed --blocking <count>`; when neither works, record why with %s "
            "`--target spec --state no-reviewer --reason \"<one line>\"`. One round only: fix it from the findings and hand "
            "it to the user, saying what the review raised, what you changed and what you did not take and why. Do not "
            "ask the user to confirm before it is recorded." % (review, mark, mark, mark))


def requirement_review_fact(root: Path, module: str) -> tuple | None:
    """sg-review-rules: what of the requirement's review changes the confirmation step, for the state code."""
    if not module or not requirement_wait(root, module):
        return None
    review = requirement_review(root, module)
    if review is None or not review["required"]:
        return None
    try:
        current = _text_digest((root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        current = None
    return ("requirement-review", review["status"], current)


def requirement_hint(root: Path, module: str, wait: str, cmd: dict, zh: bool) -> tuple:
    """requirement-confirm-gate: (review line, next step) while a v2 requirement waits for the user's confirmation.

    sg-review-rules: a normal or important requirement with no review record is reviewed first; once it has one, the
    restatement carries what the review raised and the changes since it."""
    line, step = _requirement_hint(root, module, wait, cmd, zh)
    review = requirement_review(root, module)
    if review is None or not review["required"]:
        return line, step
    if review["status"] == "missing":
        return line, _review_first_step(module, cmd, zh)
    extra = ("交用户时附上审查提了什么、改了哪些、哪些没采纳及原因。" if zh else
             " With it, tell the user what the review raised, what you changed and what you did not take and why.")
    return line, step + extra + _review_diff_text(root, module, zh)


def _requirement_hint(root: Path, module: str, wait: str, cmd: dict, zh: bool) -> tuple:
    tier = effective_tier(root, module)["tier"]
    lang = "zh" if zh else "en"
    names = DOC_SECTIONS["bug" if tier == "bug" else "requirement"][lang] + (
        DOC_SECTIONS["small"][lang] if tier == "small" else ())
    reasons = ", ".join(important(root, module))
    combined = load_config(root)[0].get("reviewCadence") == "combined"
    path = "spec/%s.md" % module
    ask = release_allowed(root, module)  # sg-gate-flow (rule 1): only then is "release when done?" asked
    if zh:
        why = {"pending": "等用户确认", "codex": "只有 Codex 的批准，需求要用户在对话里确认",
               "revised": "确认后又改过，要用户重新确认"}[wait]
        return ("- 批准: 需求文档 `%s` %s%s。" % (path, why, "（批准节奏 combined 不适用于需求确认）" if combined else ""),
                "在对话正文里复述需求（%s，加上档位），问用户是否说完；给谁用、为什么做、怎样算做成、不做什么有一项写不出来、"
                "有你自己补的假设，或是重要需求%s时，先用 agent-skills 的 interview-me 一次问一个问题，问清再复述。%s"
                "用户在对话里确认后，用 %s 记下来；接管档位不能代替，Codex 的批准不算。确认前不要往下写。"
                % ("、".join(names), "（本需求是重要需求：%s）" % reasons if reasons else "",
                   "本模块的档位把发版交给 autopilot：复述时一并问「做完自动发版吗？」，答是就在流程标记行下面写一行 "
                   "`<!-- spec-guard: release-preauth yes -->` 再记确认，答否不写。" if ask else "", cmd["review-mark"]))
    why = {"pending": "is waiting for the user's confirmation",
           "codex": "has only Codex's approval; the user confirms requirements in the conversation",
           "revised": "was edited after it was confirmed; the user confirms it again"}[wait]
    return ("- Review: the requirement `%s` %s%s." % (path, why, " (reviewCadence combined does not apply to it)"
                                                    if combined else ""),
            "restate the requirement in the conversation (%s, plus the tier) and ask the user whether that is everything; "
            "when who it is for, why, what counts as done or what is out of scope cannot be written, when you filled in "
            "an assumption yourself, or when it is an important requirement%s, first interview the user with "
            "agent-skills' interview-me, one question at a time, then restate it.%s When the user confirms in the "
            "conversation, record that with %s; the takeover cannot stand in and Codex's approval does not count. Do not "
            "write further documents until it is confirmed."
            % (", ".join(names), " (this one is: %s)" % reasons if reasons else "",
               " This module's takeover hands the release to autopilot: with the restatement, ask \"release when done?\"; "
               "on yes write `<!-- spec-guard: release-preauth yes -->` under the flow marker before recording the "
               "confirmation, on no write nothing." if ask else "", cmd["review-mark"]))


# design-review: whether a v2 module's design is reviewed, and where that stands (published as designApproval).
DESIGN_STATUSES = ("not-required", "pending-review", "in-review", "pending-user", "approved", "unreviewed", "revised")
IMPACT_SECTIONS = (DOC_SECTIONS["design"]["zh"][1], DOC_SECTIONS["design"]["en"][1])
QUOTED = re.compile(r"`([^`\s]+)`")
PATHLIKE = re.compile(r"[\w@+-][\w./@+-]*")
LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?$")


def impact_paths(text: str) -> list:
    """design-review: the paths quoted in backticks under the design's impact section, `:line` suffixes dropped."""
    found, inside = [], False
    for line in _visible_lines(text.splitlines()):
        heading = SECTION_HEADING.match(line)
        if heading:
            inside = heading.group(1) in IMPACT_SECTIONS
            continue
        if inside:
            for token in QUOTED.findall(line):
                token = LINE_SUFFIX.sub("", token).rstrip("/")
                if PATHLIKE.fullmatch(token) and ("/" in token or "." in token) and ".." not in token.split("/"):
                    found.append(token)
    return found


def module_baseline(root: Path, module: str) -> str | None:
    """The commit before spec/<id>.md was first committed; "" when that was the first commit; HEAD when the Spec is
    not committed; None outside git (then the working tree stands in)."""
    log = _git(root, "log", "--diff-filter=A", "--format=%H", "--", "spec/%s.md" % module)
    first = log.splitlines()[-1] if log else None
    if first:
        return _git(root, "rev-parse", "--verify", "--quiet", first + "^") or ""
    return _git(root, "rev-parse", "--verify", "--quiet", "HEAD")


def impact_has_old_files(root: Path, module: str, text: str) -> bool | None:
    """design-review, regression-doc-check: True when the design's impact section lists a file that existed before the
    module started; None when it names no path at all (callers decide what an unknown impact means)."""
    paths = impact_paths(text)
    if not paths:
        return None
    base = module_baseline(root, module)
    for path in paths:
        if base is None:
            old = (root / path).exists()
        else:
            old = bool(base) and _git(root, "cat-file", "-e", "%s:%s" % (base, path)) is not None
        if old:
            return True
    return False


INTERFACE_SECTIONS = (DOC_SECTIONS["design"]["zh"][3], DOC_SECTIONS["design"]["en"][3])
# sg-review-rules (rule 6): a whole interface section of just one of these says "nothing changes" (case-insensitive)
EMPTY_INTERFACE = frozenset(("不涉及", "无", "没有", "none", "n/a", "not applicable", "no changes"))
LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
INLINE_COMMENT = re.compile(r"<!--.*?-->")
# sg-review-rules (rule 6): dependency manifests and lock files, by file name
DEPENDENCY_FILES = frozenset(("package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
                              "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock", "go.mod", "go.sum",
                              "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock"))
REQUIREMENTS_FILE = re.compile(r"requirements[^/]*\.txt")
DESIGN_REASONS = ("risk-path", "irreversible", "new-dependency")


def interface_has_content(text: str) -> bool:
    """sg-review-rules (rule 6): the design's interface and data section says something changes.

    Blank lines, comments, list marks and closing punctuation are dropped; a section left empty, or holding only one
    item from EMPTY_INTERFACE, has no content.  A missing section has none either.
    """
    import regression_view
    items = []
    for _n, line, in_fence, _m in regression_view._section_lines(text, INTERFACE_SECTIONS) or []:
        if not in_fence:
            line = INLINE_COMMENT.sub("", line)
        item = LIST_MARK.sub("", line).strip().rstrip("。.！!；;，,、").strip()
        if item:
            items.append(item)
    return bool(items) and not (len(items) == 1 and items[0].lower() in EMPTY_INTERFACE)


def is_dependency_file(path: str) -> bool:
    """sg-review-rules (rule 6): a dependency manifest or lock file, by its file name."""
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return name in DEPENDENCY_FILES or bool(REQUIREMENTS_FILE.fullmatch(name))


def design_requirement(root: Path, module: str) -> dict | None:
    """design-review, sg-review-rules (rules 6-9): {"need": "review" | "none", "reason", "reasons", "riskList"}.

    A design is reviewed on risk-path (an impact path, its own documents left out, on the T3/T4 list), irreversible
    (the interface and data section says something changes) or new-dependency (the impact lists a dependency
    manifest or lock file); `reason` is the first that applies, `reasons` all of them.  Without any, designReview: on
    still reviews it (configured).  riskList is "no-list" when no risk-path list is readable: then risk-path is not
    checked, neither a hit nor a miss.  Old-flow, bug and small modules have no design (None).
    """
    flow = effective_tier(root, module)
    if not flow["v2"] or flow["tier"] in SHORT_TIERS:
        return None
    try:
        text = (root / "tasks" / module / "design.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        text = ""
    paths = [path for path in impact_paths(text) if not own_doc(module, path) and path != "tasks/%s" % module]
    patterns = _risk_patterns(root)
    found = {"risk-path": patterns is not None and any(risk_hit(pattern, path) for pattern in patterns for path in paths),
             "irreversible": interface_has_content(text) if text else False,
             "new-dependency": any(is_dependency_file(path) for path in paths)}
    reasons = [reason for reason in DESIGN_REASONS if found[reason]]
    if not reasons and load_config(root)[0].get("designReview") == "on":
        reasons = ["configured"]
    return {"need": "review" if reasons else "none", "reason": reasons[0] if reasons else None, "reasons": reasons,
            "riskList": "ok" if patterns is not None else "no-list"}


def design_approver(root: Path, module: str) -> str:
    """takeover-redefine (assumption 2), sg-review-rules (rule 10): who lets a flow v2 design through -- "user" or
    "reviewer", from the module's takeover item `design` alone (an important requirement included)."""
    from project_config import module_takeover  # late: project_config is imported by callers of this module
    return "reviewer" if module_takeover(root, module)[0]["design"] == "reviewer" else "user"


def design_approval(root: Path, module: str) -> dict | None:
    """design-review (assumption 8): the designApproval object of /map --json; None without a design step.

    takeover-redefine: under design=human a reviewer's clean round (reviewer-approved, bound to the text by its
    digest) still waits for the user; a design that needs no review goes straight to the user (Q2 A).
    """
    need = design_requirement(root, module)
    if need is None:
        return None
    approver = design_approver(root, module)
    try:
        text = (root / "tasks" / module / "design.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        text = ""
    state = review_state(text, "design") if text else "none"
    records = design_round_records(text)
    reviewed = [record for record in records if record["vendor"] != "none"]
    last = records[-1] if records and records[-1]["vendor"] != "none" else None
    if state == "approved":
        status, by = "approved", "user"
    elif state == "reviewer-approved" and approver == "reviewer":
        status, by = "approved", "reviewer"
    elif need["need"] == "none" and approver == "reviewer":
        status, by = "not-required", None
    elif state == "revised":
        status, by = "revised", None
    elif need["need"] == "none":
        status, by = "pending-user", None
    elif records and records[-1]["vendor"] == "none":
        status, by = "unreviewed", None
    elif state == "reviewer-approved":
        status, by = "pending-user", None  # takeover-redefine: reviewed and clean, the user approves it
    elif reviewed and reviewed[-1]["blocking"]:
        exhausted = sum(1 for record in reviewed if record["blocking"]) >= 2
        status, by = ("pending-user" if exhausted else "in-review"), None
    else:
        status, by = "pending-review", None
    return {"status": status, "approvedBy": by, "need": need["need"], "reason": need["reason"],
            "reasons": need["reasons"], "riskList": need["riskList"],
            "approver": approver, "marker": state,
            "reviewerVendor": last["vendor"] if last else None, "sameVendor": last["sameVendor"] if last else None,
            "reportSha256": last["report"] if last else None,
            "rounds": [{"round": record["round"], "blocking": record["blocking"], "sha256": record["sha256"],
                        "vendor": None if record["vendor"] == "none" else record["vendor"],
                        "sameVendor": None if record["vendor"] == "none" else record["sameVendor"],
                        "reportSha256": record["report"]}
                       for record in records]}


DESIGN_ROUND_PREFIX = "<!-- spec-guard: design-review"


def design_review_problems(root: Path, module: str) -> list:
    """design-review (assumption 11): [(level, message)] for verify-artifacts; [] without a design step or design."""
    need = design_requirement(root, module)
    path = "tasks/%s/design.md" % module
    if need is None or not (root / path).is_file():
        return []
    try:
        text = (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [("fail", "`%s` 读不了" % path)]
    found = []
    if review_state(text, "design") == "invalid":
        found.append(("fail", "`%s` 的批准标记无效（只能有一行：review pending、approved <指纹> 或 reviewer-approved <指纹>）" % path))
    broken = [line.strip() for line in _visible_lines(text.splitlines())
              if line.strip().startswith(DESIGN_ROUND_PREFIX) and not design_round_match(line)]
    if broken:
        found.append(("fail", "`%s` 有 %d 行技术方案审查轮次行写坏了" % (path, len(broken))))
    criteria = sorted({record["criteria"] for record in design_round_records(text)})
    if len(criteria) > 1:
        found.append(("fail", "`%s` 的审查轮次用了不同的 criteria：%s" % (path, "、".join(criteria))))
    if review_state(text, "design") == "reviewer-approved" and design_approver(root, module) == "user":
        # sg-review-rules (rule 10): an important requirement follows the takeover like any other
        found.append(("warn", "`%s` 只有第二审查者的放行：接管档位 design=human的技术方案要用户批" % path))
    return found


def plan_auto_problems(root: Path, module: str) -> list:
    """plan-auto-approve (assumptions 2, 4, 10): [(level, message)] for verify-artifacts on an unfinished v2 module.

    The scope is read by the same module_scope.flow_scope the build checks use; changes themselves are not checked here.
    """
    if not _v2(root, module) or module_state(root, module)["stage"] == "DONE":
        return []
    from module_scope import flow_scope  # late: module_scope imports this module
    found, problems = flow_scope(root, module), []
    if found is not None and found["status"] == "invalid":
        problems.append(("fail", "`spec/%s.md` 的并行边界写坏了或读不了，新流程模块的越界检查无法运行" % module))
    elif found is not None and found["status"] == "unknown":
        problems.append(("warn", "`spec/%s.md` 没有并行边界，`tasks/%s/design.md` 的影响面也没写出路径：构建时越界检查会停下" % (module, module)))
    try:
        plan = (root / "tasks" / module / "plan.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        plan = ""
    if plan and _review_split(plan)[0]:
        problems.append(("warn", "`tasks/%s/plan.md` 带批准标记：新流程 Plan 写完即自动批准，标记不起作用" % module))
    return problems


def design_waits(root: Path, module: str, stage: str) -> dict | None:
    """design-review: the designApproval while the design holds the module back, else None.

    It holds at NEEDS_REGRESSION until it is approved or needs no review; later stages only for a revision (a design
    written before this check existed, with the regression document after it, is not stopped retroactively).
    """
    if stage not in ("NEEDS_REGRESSION", "NEEDS_PLAN", "BUILDING"):
        return None
    approval = design_approval(root, module)
    if approval is None or approval["status"] in ("approved", "not-required"):
        return None
    # takeover-redefine (R1-5): a reviewer's pass that no longer counts (the takeover became design=human, or the
    # requirement became important) holds every later stage too.
    lapsed = approval["status"] == "pending-user" and approval["marker"] == "reviewer-approved"
    if stage != "NEEDS_REGRESSION" and approval["status"] != "revised" and not lapsed:
        return None
    return approval


def design_fact(root: Path, module: str, stage: str) -> tuple | None:
    """takeover-redefine (R2-3): what of a waiting design changes the next step, for the state code."""
    approval = design_waits(root, module, stage)
    return None if approval is None else (approval["status"], approval["approver"], len(approval["rounds"]))


def design_to_user(approval: dict | None) -> bool:
    """design-review: the design waits for the user (the design-review stop node)."""
    return approval is not None and (approval["status"] in ("pending-user", "unreviewed")
                                     or (approval["status"] == "revised" and approval["need"] != "review"))


ORIGIN_ZH = {"moduleTakeover": "模块的 moduleTakeover", "takeover": "项目的 takeover", "default": "默认，没设 takeover",
             "takeover-invalid": "默认，takeover 无效", "moduleTakeover-invalid": "继承项目的 takeover，模块的 moduleTakeover 无效"}
ORIGIN_EN = {"moduleTakeover": "the module's moduleTakeover", "takeover": "the project's takeover",
             "default": "the default, no takeover set", "takeover-invalid": "the default, takeover is invalid",
             "moduleTakeover-invalid": "the project's takeover, the module's moduleTakeover is invalid"}


def _design_route(root: Path, module: str, approval: dict, zh: bool) -> str:
    """takeover-redefine (assumption 8): which takeover route the design is on, and where that comes from."""
    from project_config import takeover_origin  # late: project_config is imported by callers of this module
    origin = (ORIGIN_ZH if zh else ORIGIN_EN)[takeover_origin(root, module)]
    value = "reviewer" if approval["approver"] == "reviewer" else "human"
    return ("接管档位 design=%s（%s）" if zh else "takeover design=%s (%s)") % (value, origin)


DESIGN_REASON_ZH = {"risk-path": "影响面碰了高风险路径", "irreversible": "有接口和数据改动",
                    "new-dependency": "影响面列了依赖清单或锁文件", "configured": "项目开关 designReview 为 on"}
DESIGN_REASON_EN = {"risk-path": "its impact touches a high-risk path", "irreversible": "it changes interfaces or data",
                    "new-dependency": "its impact lists a dependency manifest or lock file",
                    "configured": "designReview is on"}
NO_RISK_LIST_ZH = "- T4 路径：没有可读的风险路径清单，`risk-path` 未检查；补上 `.github/autopr/risk-paths.json` 才能按风险路径判定。"
NO_RISK_LIST_EN = ("- T4 paths: no readable risk-path list, `risk-path` not checked; add `.github/autopr/risk-paths.json` "
                   "to judge by risk paths.")


LIST_ITEM = re.compile(r"^(?:[-*+]|\d+\.)\s+")
COMMENT_ONLY = re.compile(r"^(?:<!--.*?-->\s*)+$")


def _outline_items(text: str, names) -> list | None:
    """sg-design-outline: the section's list items (not indented, outside code fences, a list mark followed by more
    than a comment); None when there is no such section."""
    import regression_view
    lines = regression_view._section_lines(text, names)
    if lines is None:
        return None
    items = []
    for _n, line, in_fence, _m in lines:
        match = LIST_ITEM.match(line)
        if in_fence or not match:
            continue
        rest = line[match.end():].strip()
        if rest and not COMMENT_ONLY.match(rest):
            items.append(rest)
    return items


def _outline_has_content(text: str, names) -> bool:
    """sg-design-outline: the section holds something besides blank lines and comments (a list mark around a lone
    comment does not count)."""
    import regression_view
    for _n, line, in_fence, _m in regression_view._section_lines(text, names) or []:
        rest = LIST_ITEM.sub("", line.strip(), count=1).strip()
        if rest and (in_fence or not COMMENT_ONLY.match(rest)):
            return True
    return False


def design_outline_findings(root: Path, module: str) -> list:
    """sg-design-outline (rules 8-10a): [(kind, detail)] -- ("alternatives", count) for an important requirement whose
    design compares fewer than two approaches, ("interfaces", "missing" | "empty") for a multi-module one without
    module interfaces.  [] without a design or a case."""
    case = design_outline_case(root, module)
    try:
        text = (root / "tasks" / module / "design.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    if case is None:
        return []
    found = []
    if case["important"]:
        count = len(_outline_items(text, (DOC_SECTIONS["design"]["zh"][5], DOC_SECTIONS["design"]["en"][5])) or [])
        if count < 2:
            found.append(("alternatives", count))
    if case["cross"]:
        names = (DOC_SECTIONS["design-interfaces"]["zh"][0], DOC_SECTIONS["design-interfaces"]["en"][0])
        if not _sections(text) & set(names):
            found.append(("interfaces", "missing"))
        elif not _outline_has_content(text, names):
            found.append(("interfaces", "empty"))
    return found


def _outline_message(module: str, finding: tuple, zh: bool) -> str:
    path = "tasks/%s/design.md" % module
    kind, detail = finding
    if kind == "alternatives":
        return ("`%s` 是重要需求，「方案取舍」只列了 %d 种做法，至少比较两种" % (path, detail) if zh else
                "`%s` is an important requirement; its alternatives list %d approach(es), compare at least two"
                % (path, detail))
    what = "缺「模块接口」一节" if detail == "missing" else "「模块接口」一节没有内容"
    return ("`%s` 所在需求一次插入了多个模块，%s（画出与同批模块之间的接口；没有直接接口写「无直接接口」并说明原因）"
            % (path, what) if zh else
            "`%s` belongs to a multi-module requirement; its module interfaces section is %s (draw the interfaces "
            "with the modules inserted with it; with none, write that there is no direct interface and why)"
            % (path, "missing" if detail == "missing" else "empty"))


def design_outline_problems(root: Path, module: str) -> list:
    """sg-design-outline: [(level, message)] for verify-artifacts -- warnings only, never a failure."""
    return [("warn", _outline_message(module, finding, True)) for finding in design_outline_findings(root, module)]


def design_outline_line(root: Path, module: str | None, stage: str, zh: bool) -> tuple:
    """sg-design-outline (rules 8, 10, 10a): (fact, lines) at NEEDS_REGRESSION, one line per finding; the fact carries
    every finding with its count or kind, so the state code follows what the lines say.  (None, "") otherwise."""
    if not module or stage != "NEEDS_REGRESSION":
        return None, ""
    findings = design_outline_findings(root, module)
    if not findings:
        return None, ""
    head = "- 技术方案大纲：" if zh else "- Design outline: "
    return ("design-outline", tuple(findings)), "\n".join(head + _outline_message(module, f, zh) for f in findings)


def risk_list_line(root: Path, module: str | None, stage: str, zh: bool) -> tuple:
    """sg-review-rules (rule 9, S6): (fact, line) at NEEDS_REGRESSION when no risk-path list is readable, whether or
    not the design still waits (a design=reviewer design that needs no review included); (None, "") otherwise."""
    if not module or stage != "NEEDS_REGRESSION":
        return None, ""
    need = design_requirement(root, module)
    if need is None or need["riskList"] != "no-list":
        return None, ""
    return ("risk-list", "no-list"), NO_RISK_LIST_ZH if zh else NO_RISK_LIST_EN


def design_hint(root: Path, module: str, stage: str, cmd: dict, zh: bool) -> tuple:
    """design-review (assumptions 4, 7): (review line, next step) while the design waits; ("", "") otherwise.

    takeover-redefine: under design=human the reviewer's clean round is recorded as before and then goes to the
    user; a design that needs no review goes to the user at once (Q2 A).  Both routes name the takeover's origin.
    """
    approval = design_waits(root, module, stage)
    if approval is None:
        return "", ""
    path = "tasks/%s/design.md" % module
    review = ("/delegate:review --profile design --backend auto --author-host %s --paths %s --spec spec/%s.md"
              % (cmd["author-host"], path, module))
    mark, status = cmd["review-mark"], approval["status"]
    hold = _hold(root, module, stage, zh)
    last = approval["rounds"][-1] if approval["rounds"] else None
    user = approval["approver"] == "user"
    route = _design_route(root, module, approval, zh)
    exhausted = sum(1 for record in approval["rounds"] if record["blocking"] and record["vendor"]) >= 2
    if zh:
        reason = "、".join(DESIGN_REASON_ZH[r] for r in approval["reasons"]) or "不需要第二审查者"
        why = "%s；%s" % (reason, route) if route else reason
        run = ("用 `%s` 审一轮（影响面里列的已有文件各加一个 `--spec`；开工前可用 `/delegate:doctor --reviewers --json` "
               "看有没有可用的审查者），把它标准输出的 JSON 存成仓库外的文件（例如 `$TMPDIR` 下）" % review)
        to_user = ("在对话正文里写出技术方案六节的要点、第二审查者的意见与你的处理，交用户批；用户在对话里批准后，用 %s "
                   "`--target design --state approved` 记下来" % mark)
        clean = ("没有阻断就用 %s `--target design --state reviewer-approved --review <文件>` 记下，这不算放行，接着交用户批"
                 % mark if user else
                 "没有阻断就用 %s `--target design --state reviewer-approved --review <文件>` 记下，不用用户批" % mark)
        if status == "pending-review":
            return ("- 批准: 技术方案 `%s` 待审（第二审查者；%s）。" % (path, why),
                    "%s。%s；有阻断就用 `--state reviewer-reviewed` 记下这一轮、改完再审，第二轮加 `--previous-report <上一轮报告>`，"
                    "两轮仍有阻断就交用户批。放行前%s。" % (run, clean, hold))
        if status == "in-review":
            return ("- 批准: 技术方案 `%s` 第 %d 轮审查有 %d 条阻断（%s）。" % (path, last["round"], last["blocking"], why),
                    "改完后用 `%s --previous-report <上一轮报告>` 复审，第二轮只核对上一轮；%s，仍有阻断就用 `--state reviewer-reviewed` "
                    "记下并交用户批。放行前%s。" % (review, clean, hold))
        if status == "unreviewed":
            return ("- 批准: 技术方案 `%s` 没有可用的第二审查者（未审），交用户批。" % path,
                    "%s；说明这一轮没有第二审查者。批准前%s。" % (to_user, hold))
        if status == "revised":
            if approval["need"] != "review":
                return ("- 批准: 技术方案 `%s` 批准后又改过，要用户重新批（%s）。" % (path, why), "%s。批准前%s。" % (to_user, hold))
            return ("- 批准: 技术方案 `%s` 放行后又改过，要重新审（%s）。" % (path, why),
                    "%s，按结果用 %s `--target design` 记下（没有阻断 `--state reviewer-approved`，有阻断 `--state reviewer-reviewed`）%s。"
                    "放行前%s。" % (run, mark, "，审完交用户批" if user else "", hold))
        if approval["need"] == "none":
            cause = "不需要第二审查者；%s" % route
        elif exhausted:
            cause = "两轮审查仍有阻断；%s" % route
        else:
            cause = "第二审查者已审完；%s" % route
        return ("- 批准: 技术方案 `%s` 待用户批（%s）。" % (path, cause), "%s。批准前%s。" % (to_user, hold))
    reason = ", ".join(DESIGN_REASON_EN[r] for r in approval["reasons"]) or "no second reviewer is needed"
    why = "%s; %s" % (reason, route) if route else reason
    run = ("review it once with `%s` (add one `--spec` per existing file the impact section lists; `/delegate:doctor "
           "--reviewers --json` tells beforehand whether a reviewer is available) and save its standard output, the JSON "
           "report, to a file outside the repository (for example under `$TMPDIR`)" % review)
    to_user = ("present it to the user in the conversation -- the points of its six sections, the second reviewer's "
               "findings and what you did with them; when the user approves it, record that with %s `--target design "
               "--state approved`" % mark)
    clean = ("With no blocking item record it with %s `--target design --state reviewer-approved --review <file>`; that "
             "does not let it through, the user approves it next" % mark if user else
             "With no blocking item record it with %s `--target design --state reviewer-approved --review <file>`; the "
             "user need not approve it" % mark)
    if status == "pending-review":
        return ("- Review: the design `%s` awaits a second reviewer (%s)." % (path, why),
                "%s. %s. With blocking items record the round with `--state reviewer-reviewed`, fix "
                "them and review again with `--previous-report <the previous report>`; after two blocking rounds the user "
                "approves it. Until it passes, %s." % (run[0].upper() + run[1:], clean, hold))
    if status == "in-review":
        return ("- Review: round %d of the design `%s` has %d blocking item(s) (%s)." % (last["round"], path,
                                                                                     last["blocking"], why),
                "fix them and review again with `%s --previous-report <the previous report>`; the second round only "
                "checks the first. %s; record a blocking one with `--state reviewer-reviewed`, and then hand it to the "
                "user. Until it passes, %s." % (review, clean, hold))
    if status == "unreviewed":
        return ("- Review: no second reviewer was available for the design `%s` (unreviewed); the user approves it." % path,
                "%s, saying that no second reviewer saw it. Until it is approved, %s." % (to_user, hold))
    if status == "revised":
        if approval["need"] != "review":
            return ("- Review: the design `%s` was edited after it was approved; the user approves it again (%s)." % (path, why),
                    "%s. Until it is approved, %s." % (to_user, hold))
        return ("- Review: the design `%s` was edited after it passed; review it again (%s)." % (path, why),
                "%s, and record the round with %s `--target design` (`--state reviewer-approved` when clean, "
                "`--state reviewer-reviewed` otherwise)%s. Until it passes, %s."
                % (run, mark, ", then hand it to the user" if user else "", hold))
    if approval["need"] == "none":
        cause = "no second reviewer is needed; %s" % route
    elif exhausted:
        cause = "two review rounds still blocking; %s" % route
    else:
        cause = "the second reviewer has reviewed it; %s" % route
    return ("- Review: the design `%s` awaits the user's approval (%s)." % (path, cause),
            "%s. Until it is approved, %s." % (to_user[0].upper() + to_user[1:], hold))


def _hold(root: Path, module: str, stage: str, zh: bool) -> str:
    """What not to do yet while a review is open: the document the stage would write next."""
    if stage == "BUILDING":
        return "不要继续构建" if zh else "do not continue the build"
    doc = {"NEEDS_DESIGN": ("技术方案", "design"), "NEEDS_REGRESSION": ("回归测试文档", "regression document"),
           "NEEDS_PLAN": (" Plan", "Plan")}[stage]
    return ("先不要写%s" % doc[0]) if zh else ("do not write the %s yet" % doc[1])


def module_state(root: Path, module_id: str) -> dict:
    """The module's stage; a flow v2 bug/small module the rules call important needs the full documents."""
    state = _base_state(root, module_id)
    if state["stage"] in ("NEEDS_PLAN", "BUILDING", "DONE"):
        flow = flow_marker(root, module_id)
        if flow["v2"] and flow["tier"] in SHORT_TIERS and effective_tier(root, module_id)["tier"] == "important":
            state = _base_state(root, module_id, full=True)
    return state


def _base_state(root: Path, module_id: str, full: bool | None = None) -> dict:
    """module_state without the important() correction: important() reads other modules through this, never recursing.

    full: True asks for the design and regression documents whatever the tier says; None reads the raw flow marker."""
    if full is None:
        flow = flow_marker(root, module_id)
        full = flow["v2"] and flow["tier"] not in SHORT_TIERS
    has_spec = (root / "spec" / f"{module_id}.md").is_file()
    plan = root / "tasks" / module_id / "plan.md"
    has_plan = plan.is_file()
    todo = root / "tasks" / module_id / "todo.md"
    text = todo.read_text(encoding="utf-8") if todo.is_file() else ""
    open_items = len(UNCHECKED.findall(text))
    if open_items and has_plan_files(root, module_id) and final_gate_accepted(root, module_id, text):
        open_items -= 1  # codex-final-acceptance: ticked after the merge; until then the record stands for it
    half = bool(open_items) and bool(CHECKED.search(text))
    # A marker on a module with nothing left open is stale: the module simply counts as done.
    suspended = bool(open_items) and any(line.strip() == SUSPEND_MARKER for line in text.splitlines())
    if not has_spec:
        stage = "NEEDS_SPEC"
    elif full and not (root / "tasks" / module_id / "design.md").is_file():
        stage = "NEEDS_DESIGN"
    elif full and not (root / "tasks" / module_id / "regression.md").is_file():
        stage = "NEEDS_REGRESSION"
    elif not has_plan:
        stage = "NEEDS_PLAN"
    elif open_items:
        stage = "BUILDING"
    else:
        stage = "DONE"
    return {"id": module_id, "stage": stage, "spec": has_spec, "plan": has_plan, "open": open_items,
            "half": half and not suspended, "suspended": suspended, "todo": todo.is_file(),
            "deferred": deferred_items(text),
            "no_todo_declared": has_plan and not todo.is_file() and any(
                line.strip() == NO_TODO_MARKER for line in plan.read_text(encoding="utf-8").splitlines())}


def plan_without_todo(state: dict) -> bool:
    """A plan with no todo.md that the plan does not declare intentional; still counted as done."""
    return state["plan"] and not state["todo"] and not state["no_todo_declared"]


FRAGMENT_LIMIT = 200
STRUCTURE_CHARS = str.maketrans("", "", "`\\")


def _printable(value: str) -> str:
    """Drop control and format codepoints, keeping the whitespace `split()` collapses.

    Cc and Cf survive every other step here: they are not Markdown structure, so they
    cannot forge a block, but they do reach the agent's context and the terminal that
    `/spec-guard:phase` prints to.  ESC is the concrete one -- `json.dumps` escapes it
    in transit and the host unescapes it again -- and zero-width characters can split a
    token so the diagnostic no longer matches what the user searches the map for.
    """
    return "".join(character for character in value
                   if character.isspace()
                   or unicodedata.category(character) not in ("Cc", "Cf"))


def safe_fragment(value, limit: int = FRAGMENT_LIMIT) -> str:
    """Make a value from the repository safe to name in the injected phase context.

    `describe()` output reaches an agent every turn, so a value carrying a newline can
    forge a heading and one carrying a backtick can forge a code fence.  This keeps the
    words -- the point is a usable diagnostic, not redaction -- while removing the
    characters that let a value pretend to be structure, and bounds the length so a
    long one cannot bury the real message.

    The bound caps injected volume; it is not a promise that nothing is ever cut.
    `MODULE_ID` has no length bound, so a long enough id still truncates.  What 200 is
    measured against is the `MapError` *message*, not a bare id: the longest template
    carries two ids plus a prefix, which is 85 characters for this repository's own ids
    and 163 for a 68-character one.  An earlier 80 was measured against bare ids and
    cut this repository's own Build-order diagnostic in half.

    No HTML or Markdown escaping: the destination is an agent's context, not a browser,
    and escapes would only make the diagnostic harder to read.
    """
    if not isinstance(value, str) or not value:
        return ""
    cleaned = " ".join(_printable(value).translate(STRUCTURE_CHARS).split())
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "\u2026"


def _state(root: Path) -> dict:
    try:
        value = json.loads((root / ".agent" / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def active_module_state(root: Path) -> tuple:
    """(value, state) where state is `absent`, `invalid` or `present`.

    `invalid` is kept distinct from `absent` on purpose: the user did set something, and
    silently ignoring it would let them believe it took effect.  The value itself is a
    repository-controlled string, so only this state -- never the string -- is safe to
    report without passing through `safe_fragment`.
    """
    active = _state(root).get("activeModule")
    if not isinstance(active, str) or not active:
        return None, "absent"
    # fullmatch, not match: MODULE_ID is `$`-anchored, and `$` matches before a final
    # newline, so `.match` would call "alpha\\n" present and then fail the `by_id`
    # lookup -- naming a module that is plainly in the map and saying it is not.
    if not MODULE_ID.fullmatch(active):
        return active, "invalid"
    return active, "present"


def active_module(root: Path) -> str | None:
    """The current module pointer, or None when unset or not a module id."""
    value, state = active_module_state(root)
    return value if state == "present" else None


def project_stage(states: list, active: str | None) -> tuple:
    """Project-level stage: (stage, current, source, pending).

    `pending` is the first module in Build order that is not done, or None when all are.
    `current` is the activeModule's state when it names a mapped module, else `pending`.
    `stage` is DONE only when every module is done; MODULE_DONE when the current module
    is done but `pending` is not None; otherwise the current module's own stage.
    """
    by_id = {state["id"]: state for state in states}
    pending = next((state for state in states if state["stage"] != "DONE" and not state["suspended"]), None)
    if active and active in by_id and not by_id[active]["suspended"]:
        current, source = by_id[active], "activeModule"
    else:
        current, source = pending, "next in Build order"
    if pending is None:
        return "DONE", current, source, None
    return ("MODULE_DONE" if current["stage"] == "DONE" else current["stage"]), current, source, pending


def paused_modules(states: list, current: dict | None) -> list:
    """Modules other than `current` whose todo is half done, in Build order."""
    return [state for state in states if state["half"] and state is not current]


def _git(root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def unmerged_commits(root: Path) -> tuple | None:
    """(count, ref short name) of HEAD commits not in the locally known origin default branch, else None.

    Read-only and offline: only compares local remote-tracking refs, never fetches.
    """
    ref = _git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if not ref:
        ref = next((c for c in ("refs/remotes/origin/main", "refs/remotes/origin/master")
                    if _git(root, "rev-parse", "--verify", "--quiet", c)), None)
    if not ref:
        return None
    count = _git(root, "rev-list", "--count", ref + "..HEAD")
    if count is None or not count.isdigit():
        return None
    prefix = "refs/remotes/"
    return int(count), ref[len(prefix):] if ref.startswith(prefix) else ref


# codex-command-wording: the commands the injection names, per host. None (host unknown) keeps the wording from
# before the change, word for word. Codex plugins expose skills, not slash commands ($name mentions them), and
# Codex's /compact takes no inline text (codex-rs/tui/src/slash_command.rs, supports_inline_args); Claude Code's
# `/compact [instructions]` does (code.claude.com/docs/en/commands).
COMMANDS = {
    None: {
        "add-module": "/spec-guard:add-module (Codex: spec-guard-ops add-module)",
        "verify": "/spec-guard:verify-artifacts",
        "verify-quoted": "`/spec-guard:verify-artifacts`",
        "config": "/spec-guard:config",
        "resume": "`/spec-guard:module-suspend --resume %s` (Codex: spec-guard-ops module-suspend)",
        "review-mark": "`/spec-guard:review-mark` (Codex: spec-guard-ops review-mark)",
        "milestone-mark": "`/spec-guard:milestone-mark` (Codex: spec-guard-ops milestone-mark)",
        "plan": "`/plan`",
        "build": "`/build`",
        # delegate-interface-check: %(review)s and %(doctor)s come from delegate's interface.json or its defaults.
        "delegate-review": ("`%(review)s` (Codex: `delegate:delegate-routing`) (whether it can run is decided by "
                            "`%(doctor)s`)"),
        "checkout-role": "`/spec-guard:checkout-role` (Codex: spec-guard-ops checkout-role)",
        "map": "`/spec-guard:map` (Codex: spec-guard-ops map)",
        "doc-verify": "`/spec-guard:documentation-verification %s` (Codex: spec-guard-ops documentation)",
    },
}
COMMANDS["claude"] = dict(COMMANDS[None], **{
    "milestone-mark": "`/spec-guard:milestone-mark`",
    "delegate-review": "`%(review)s` (whether it can run is decided by `%(doctor)s`)",
    "doc-verify": "`/spec-guard:documentation-verification %s`",
})
COMMANDS["codex"] = {
    "add-module": "`$spec-guard-ops` add-module",
    "verify": "`$spec-guard-ops` verify-artifacts",
    "verify-quoted": "`$spec-guard-ops` verify-artifacts",
    "config": "`$spec-guard-ops` config",
    "resume": "`$spec-guard-ops` module-suspend --resume %s",
    "review-mark": "`$spec-guard-ops` review-mark",
    "milestone-mark": "`$spec-guard-ops` milestone-mark",
    "plan": "`$planning-and-task-breakdown`",
    "build": "`$incremental-implementation`",
    "delegate-review": "`delegate:delegate-routing` (whether it can run is decided by delegate's own doctor check)",
    "checkout-role": "`$spec-guard-ops` checkout-role",
    "map": "`$spec-guard-ops` map",
    "doc-verify": "`$spec-guard-ops` documentation verification for `%s`",
}

# hint-language-follow: the same entries with Chinese prose, used only when hint_language is zh-CN.  Commands,
# skill names and paths are unchanged; only the words around them are translated.
COMMANDS_ZH = {
    None: dict(COMMANDS[None], **{
        "delegate-review": "`%(review)s`（Codex: `delegate:delegate-routing`）（能不能运行由 `%(doctor)s` 判定）",
    }),
}
COMMANDS_ZH["claude"] = dict(COMMANDS_ZH[None], **{
    "delegate-review": "`%(review)s`（能不能运行由 `%(doctor)s` 判定）",
})
COMMANDS_ZH["codex"] = dict(COMMANDS["codex"], **{
    "doc-verify": "`$spec-guard-ops` 的 documentation 核验（模块 `%s`）",
    "delegate-review": "`delegate:delegate-routing`（能不能运行以 delegate 自己的体检为准）",
})


# design-review: the delegate review command names the host the design was written in.
for _table in (COMMANDS, COMMANDS_ZH):
    for _host, _name in ((None, "<claude-code|codex>"), ("claude", "claude-code"), ("codex", "codex")):
        _table[_host]["author-host"] = _name


def commands(host: str | None, zh: bool = False) -> dict:
    return (COMMANDS_ZH if zh else COMMANDS)[host]


def unreadable_map(reason: str, zh: bool = False) -> str:
    if zh:
        return ("当前阶段: **UNKNOWN**\n\n- 能力图: 已有但读不了（%s）\n\n"
                "建议下一步: 让 `spec/CAPABILITY-MAP.md` 成为可读的文件（检查它的权限），然后再发下一条消息；"
                "这是读取故障，不是能力图的状态。" % reason)
    return ("Current stage: **UNKNOWN**\n\n- Capability map: present but unreadable (%s)\n\n"
            "Suggested next step: make `spec/CAPABILITY-MAP.md` a readable file (check its permissions), then send the "
            "next prompt; this is a read failure, not a state of the map." % reason)


def config_lines(root: Path, host: str | None = None) -> list:
    """project-config: one line per set item that changes the agent's behaviour.

    `separate` is the default and adds nothing.  A file unusable as a whole yields only its fixed problem
    codes -- never a key or value from the file -- and no setting from it is applied.  config-per-key: any
    other problem drops only its key; the valid settings keep their lines and one line names what was ignored.
    """
    values, problems = load_config(root)
    if set(problems) & set(STRUCTURAL):
        return ["- Project config: invalid (%s) — run %s." % (", ".join(problems), COMMANDS[host]["config"])]
    # takeover-config: a retired key (autonomyTier, moduleAutonomy) never changed the hint, so it adds no line;
    # /spec-guard:config and verify-artifacts report it.
    problems = [problem for problem in problems if problem != "retired-key"]
    zh = values.get("artifactLanguage") == "zh-CN"
    lines = []
    if "artifactLanguage" in values:
        lines.append(("- 产物语言: `%s` — 新写的 spec、plan、todo 正文用这种语言；结构关键字保持原定义。" if zh else
                      "- Artifact language: `%s` — write new spec, plan and todo prose in it; "
                      "structural keywords stay as defined.") % values["artifactLanguage"])
    if values.get("reviewCadence") == "combined":
        lines.append("- 批准节奏: combined — 能力图写好后，把 Spec 和 Plan 一起交给用户一次批准；出现新的决定、范围不清"
                     "或高风险改动时，分开交审。" if zh else
                     "- Review cadence: combined — after the capability map is written, present the Spec "
                     "and the Plan together for one approval; split them when a new decision, unclear "
                     "scope or a high-risk change appears.")
    if problems:
        lines.append(("- 项目配置: 已忽略 (%s)——其余设置照常生效；用 %s 查看。" if zh else
                      "- Project config: ignored (%s) — the other settings apply; run %s.")
                     % (", ".join(problems), COMMANDS[host]["config"]))
    return lines


def hint_language(root: Path) -> str:
    """hint-language-follow: "zh-CN" when artifactLanguage is valid and exactly zh-CN, else "en".

    The one criterion for the language of the stage hint; phase-guard.sh asks for it with --hint-language.
    """
    return "zh-CN" if load_config(root)[0].get("artifactLanguage") == "zh-CN" else "en"


CHECKPOINT = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(\S.*)$")
CHECKPOINT_KEYWORD = re.compile(r"(?:Checkpoint(?![A-Za-z])|检查点)")
CHECKPOINT_TIER = re.compile(r"[（(]\s*(gate|report)\s*[）)]", re.IGNORECASE)
GATE_TITLE_LIMIT = 80


def next_gate(root: Path, module: str) -> str:
    """Title of the first unchecked `gate` checkpoint in the module's todo.md, or "" when there is none.

    Which checkpoints are gates is decided by `gate_checkpoints`.  Anything that cannot be read or recognised
    yields "": the line is a convenience, not a verdict.
    """
    try:
        text = (root / "tasks" / module / "todo.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""
    for _, title, checked in gate_checkpoints(text):
        if not checked:
            return safe_fragment(title, GATE_TITLE_LIMIT)
    return ""


def gate_checkpoints(text: str) -> list:
    """[(line index, title, checked)] of the todo's `gate` checkpoints, in order.

    The one gate criterion (next gate, final gate, map-gate-count's `gates`).  cn-checkpoint-gates: a checkbox
    item is a checkpoint when it starts with `Checkpoint` or `检查点`, or when the part before its first colon (the
    whole item when there is none) carries a tier, e.g. 最终验收（gate）.  The tier is read from that part: `gate`
    counts, `report` does not.  checkpoint-default-report: an untiered checkpoint is a report, except the last
    checkpoint of the todo, which is the final acceptance.
    """
    found = []
    for index, line in enumerate(text.splitlines()):
        match = CHECKPOINT.match(line)
        if not match:
            continue
        title = match.group(2)
        tier = CHECKPOINT_TIER.search(re.split("[：:]", title, maxsplit=1)[0])
        if tier or CHECKPOINT_KEYWORD.match(title):
            found.append((index, title, match.group(1) != " ", tier.group(1).lower() if tier else None))
    last = len(found) - 1
    return [(index, title, checked) for position, (index, title, checked, tier) in enumerate(found)
            if tier == "gate" or (tier is None and position == last)]


OPEN_ITEM = re.compile(r"^\s*[-*+]\s+\[ \](?!" + DEFERRED_TAIL + r")\s+")


def at_final_gate(root: Path, module: str) -> bool:
    """True when the module's first unchecked item is a `gate` checkpoint and no other gate follows it.

    rules-in-context: that is the final acceptance, where a revised Spec may be re-reviewed together with it.
    Items after it that are not gates (a post-release check, a report) do not count.  Unreadable is False.
    """
    try:
        text = (root / "tasks" / module / "todo.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return final_gate_text(text) and not final_gate_accepted(root, module, text)


def final_gate_text(text: str) -> bool:
    """`at_final_gate` on the todo's text alone, before any acceptance record is considered."""
    lines = text.splitlines()
    open_gates = {index for index, _, checked in gate_checkpoints(text) if not checked}
    open_items = [index for index, line in enumerate(lines) if OPEN_ITEM.match(line)]
    if not open_items or open_items[0] not in open_gates:
        return False
    return not any(index in open_gates for index in open_items[1:])


def has_plan_files(root: Path, module: str) -> bool:
    return (root / "spec" / ("%s.md" % module)).is_file() and (root / "tasks" / module / "plan.md").is_file()


ACCEPTANCE_SHA = re.compile(r"[0-9a-f]{40}\Z")


def acceptance_record(root: Path, module: str) -> dict | None:
    """codex-final-acceptance: {marker, sha} of a merge=auto module's Codex acceptance record, else None.

    The record lives in the common git directory (`acceptance_path`), with fallback to the legacy checkout path;
    only review-mark --target acceptance writes it. A module without merge=auto has none that counts.
    """
    from project_config import module_takeover  # late: project_config is imported by callers of this module
    if _v2(root, module) or module_takeover(root, module)[0].get("merge") != "auto":
        return None  # verification-criteria: not used for flow v2 modules
    for path in (acceptance_path(root, module), legacy_acceptance_path(root, module)):
        try:
            document = json.loads(path.read_text(encoding="utf-8")) if path is not None and path.is_file() else None
        except (OSError, UnicodeError, ValueError):
            continue
        if (not isinstance(document, dict) or document.get("marker") != "codex-approved" or document.get("module") != module
                or not isinstance(document.get("sha"), str) or not ACCEPTANCE_SHA.match(document["sha"])):
            continue
        return {"marker": document["marker"], "sha": document["sha"]}
    return None


def final_gate_accepted(root: Path, module: str, text: str) -> bool:
    """The module waits at its final gate and Codex accepted HEAD or an ancestor of it (assumption 5)."""
    if not final_gate_text(text):
        return False
    if _v2(root, module):
        # verification-criteria (assumption 7): a flow v2 module's final gate passes on a current, passing pre-merge
        # verification, and only when its merge is automatic; Codex's acceptance record does not count for it.
        from project_config import module_takeover
        if module_takeover(root, module)[0].get("merge") != "auto":
            return False
        import verification
        return verification.passed(verification.verification_state(root, module))
    record = acceptance_record(root, module)
    return record is not None and _git(root, "merge-base", "--is-ancestor", record["sha"], "HEAD") is not None


# rules-at-nodes: the stop rules the phase hint attaches at a node, one `## ` section per node in this file.
NODE_RULES = Path(__file__).resolve().parent.parent / "references" / "node-rules.md"
NODE_TITLES = {"map-review": "能力图审阅", "spec-review": "Spec 交审", "plan-review": "Plan 交审",
               "mid-gate": "中途 gate", "final-gate": "最终验收", "milestone-stop": "里程碑停点",
               "design-review": "技术方案交审"}
NODE_LABELS_EN = {"map-review": "capability map review", "spec-review": "Spec review", "plan-review": "Plan review",
                  "mid-gate": "middle gate", "final-gate": "final acceptance", "milestone-stop": "milestone stop",
                  "design-review": "design review"}


def first_open_is_gate(root: Path, module: str) -> bool:
    """True when the module's first unchecked item is a `gate` checkpoint (the same criterion as `at_final_gate`)."""
    try:
        text = (root / "tasks" / module / "todo.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    open_gates = {index for index, _, checked in gate_checkpoints(text) if not checked}
    open_items = [index for index, line in enumerate(text.splitlines()) if OPEN_ITEM.match(line)]
    return bool(open_items) and open_items[0] in open_gates and not final_gate_accepted(root, module, text)


def stop_node(root: Path, module: str, stage: str, spec_review: str, plan_review: str) -> str | None:
    """The node the current module is at: map-review, spec-review, design-review, plan-review, mid-gate, final-gate, or None.

    Only existing facts are combined (review states, `at_final_gate`); when two apply the later one in that list wins.
    A Spec waiting for review holds the Plan back unless the project reviews both at once.  map-review is
    answered by phase-guard.sh itself (no capability map yet).
    """
    if requirement_wait(root, module):
        return "spec-review"  # requirement-confirm-gate: the requirement comes before the Plan and the final gate
    if stage in BEFORE_PLAN + ("BUILDING",) and overall_wait(root, module):
        return "design-review"  # sg-gate-flow: the user approves the overall design like a design
    if design_to_user(design_waits(root, module, stage)):
        return "design-review"  # design-review: the user approves the design before the regression document
    kind = None
    final = stage == "BUILDING" and at_final_gate(root, module)
    # pre-build-spec-batch: a revised Spec with a baseline waits for the Plan's review instead of its own.
    batched = (spec_review == "revised" and not final
               and (pre_build_batch(root, module, stage, spec_review, plan_review) or {}).get("status") == "found")
    if stage == "NEEDS_SPEC" or spec_review == "pending" or (spec_review == "revised" and not final and not batched):
        kind = "spec-review"
    spec_waits = kind == "spec-review" and not cadence_combined(root, module)
    auto = codex_route(root, module, "plan") == "auto"  # plan-auto-approve: a v2 Plan is never reviewed
    if not auto and ((stage == "NEEDS_PLAN" and not spec_waits) or plan_review == "pending"):
        kind = "plan-review"
    if final:
        kind = "final-gate"
    elif stage == "BUILDING" and kind is None and first_open_is_gate(root, module):
        kind = "mid-gate"
    return kind


def node_rules(kind: str) -> str:
    """The `## ` section of node-rules.md for a node kind, up to the next section; "" when it cannot be had."""
    title = NODE_TITLES.get(kind)
    if title is None:
        return ""
    try:
        text = NODE_RULES.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""
    head = "## %s\n" % title
    start = text.find(head) if text.startswith(head) else text.find("\n" + head) + 1
    if start <= 0 and not text.startswith(head):
        return ""
    end = text.find("\n## ", start + len(head))
    return (text[start:] if end < 0 else text[start:end + 1]).strip() + "\n"


def stop_rules_block(kind: str | None, zh: bool) -> str:
    """The paragraph appended after the suggested next step at a node; empty when there is none to attach."""
    section = node_rules(kind) if kind else ""
    if not section:
        return ""
    label = ("停点规则（%s）：" % NODE_TITLES[kind]) if zh else ("Stop rules (%s):" % NODE_LABELS_EN[kind])
    return "\n\n%s\n\n%s" % (label, section.rstrip("\n"))


def file_review_state(path: Path, kind: str) -> str:
    """A file's review state; `none` when it is absent, `unreadable` when it cannot be read."""
    if not path.is_file():
        return "none"
    try:
        return review_state(path.read_text(encoding="utf-8"), kind)
    except (OSError, UnicodeError):
        return "unreadable"


def _takeover_item(root: Path, module: str, kind: str) -> str:
    from project_config import module_takeover  # late: project_config is light, but keep the hook's import list as it was
    return module_takeover(root, module)[0][kind]


def _declared_nonempty(root: Path, module: str) -> bool:
    """codex-approval Q6: the Plan's pre-declared section lists something (a malformed section counts as listing)."""
    from module_scope import ScopeError, parse_declared  # late: module_scope imports this module
    try:
        declared = parse_declared((root / "tasks" / module / "plan.md").read_text(encoding="utf-8"))
    except ScopeError:
        return True
    except (OSError, UnicodeError):
        return False
    return declared is not None and any(declared)


# important-requirement: the high-risk path list autopilot writes into the project (S101 Q8 A; autopr-design #21976).
RISK_PATHS = Path(".github") / "autopr" / "risk-paths.json"
RISK_SCHEMA = "autopilot.risk-paths/v1"
RISK_TIERS = ("T4", "T3")  # Q9 A: both count
# interface.json mapView.values.importantReasons (important-requirement, interface 1.15)
IMPORTANT_REASONS = ("multi-module", "cross-module", "cross-unknown", "risk-path", "risk-unknown")


def _segment(pattern: str, name: str) -> bool:
    return re.fullmatch("".join("[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char)
                                for char in pattern), name) is not None


def risk_hit(pattern: str, path: str) -> bool:
    """`**` spans directories, `*` one segment.  A path ending in `/` is a directory: it hits when it may hold a match,
    which only a pattern starting with a literal segment can say (`**/*.lock` names files, not where they live)."""
    pattern_parts, path_parts = pattern.split("/"), path.rstrip("/").split("/")
    if path.endswith("/"):
        if "*" in pattern_parts[0] or "?" in pattern_parts[0]:
            return False
        for index, part in enumerate(path_parts):
            if index >= len(pattern_parts):
                return False
            if pattern_parts[index] == "**":
                return True
            if not _segment(pattern_parts[index], part):
                return False
        return True

    def walk(p: int, q: int) -> bool:
        if p == len(pattern_parts):
            return q == len(path_parts)
        if pattern_parts[p] == "**":
            return any(walk(p + 1, k) for k in range(q, len(path_parts) + 1))
        return q < len(path_parts) and _segment(pattern_parts[p], path_parts[q]) and walk(p + 1, q + 1)
    return walk(0, 0)


def _risk_patterns(root: Path, tiers: tuple = RISK_TIERS) -> list | None:
    try:
        document = json.loads((root / RISK_PATHS).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if not isinstance(document, dict) or document.get("schema") != RISK_SCHEMA:
        return None
    patterns = []
    for tier in tiers:
        items = document.get(tier, [])
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            return None
        patterns += items
    return patterns


def important(root: Path, module: str) -> list:
    """important-requirement: the reasons this module's requirement is important by rule, [] when none.

    multi-module: inserted in one batch with another module; cross-module: its Spec's boundary lists shared files or
    overlaps another unfinished module's; risk-path: a boundary path or a pre-declared public path is on the T3/T4
    list.  cross-unknown (no boundary) and risk-unknown (no readable list) count only where the Spec is Codex's.
    """
    from module_scope import ScopeError, overlap, parse, parse_declared  # late: module_scope imports this module
    # takeover-redefine (R2-1): a flow v2 requirement is always the user's, so the unknowns never count for it --
    # otherwise design=reviewer would make every module of a project without a risk list important.
    v2 = _v2(root, module)
    codex = not v2 and _takeover_item(root, module, "spec") == "codex"
    reasons = []
    try:
        # sg-review-rules (rule 14): a flow v2 module is important on a risk path only
        if not v2 and any(module in modules and len(modules) > 1 for _, modules in usage_draft.batches(str(root))):
            reasons.append("multi-module")
    except usage_draft.UsageDraftError:
        pass  # without git there are no batches to tell; the other rules still apply

    def read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""
    try:
        scope = parse(read(root / "spec" / ("%s.md" % module)))
    except ScopeError:
        scope = None
    if scope is None:
        if codex:
            reasons.append("cross-unknown")
    else:
        others = []
        try:
            others = [row.module_id for row in parse_map(root / "spec" / "CAPABILITY-MAP.md").rows
                      if row.module_id != module]
        except (OSError, MapError, UnicodeError):
            pass
        clash = False
        for other in others:
            if _base_state(root, other)["stage"] == "DONE":  # flow-doc-skeletons: not module_state, which calls here
                continue
            try:
                theirs = parse(read(root / "spec" / ("%s.md" % other)))
            except ScopeError:
                continue
            if theirs is not None and overlap(scope, theirs):
                clash = True
                break
        if not v2 and (scope.shared or clash):
            reasons.append("cross-module")
    paths = list(scope.exclusive) if scope is not None else []
    try:
        declared = parse_declared(read(root / "tasks" / module / "plan.md"))
    except ScopeError:
        declared = None
    if declared is not None:
        paths += list(declared.public_paths)
    if v2:
        # plan-auto-approve: a v2 design's impact section names what the module changes (old modules: unchanged)
        paths += impact_paths(read(root / "tasks" / module / "design.md"))
        # rework (assumption 13): its own documents, or its tasks/<id>/ directory entry, are not risk paths
        paths = [path for path in paths if not own_doc(module, path) and path != "tasks/%s/" % module]
    patterns = _risk_patterns(root)
    if patterns is None:
        if codex:
            reasons.append("risk-unknown")
    elif any(risk_hit(pattern, path) for pattern in patterns for path in paths):
        reasons.append("risk-path")
    return reasons


def codex_route(root: Path, module: str, kind: str) -> str:
    """codex-approval: "" when Codex may approve this file under the module's takeover, else why the user must."""
    if kind == "spec" and _v2(root, module):
        return "requirement"  # requirement-confirm-gate: a v2 requirement is confirmed by the user, whatever the takeover
    if kind == "plan" and _v2(root, module):
        return "auto"  # plan-auto-approve: a v2 Plan is approved by being written; nobody reviews it
    if _takeover_item(root, module, kind) != "codex":
        return "takeover"
    if kind == "spec" and important(root, module):
        return "important"
    if kind == "plan" and _declared_nonempty(root, module):
        return "pre-declared"
    return ""


def codex_rounds_exhausted(root: Path, path: str) -> bool:
    try:
        rounds = codex_rounds((root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return False
    return sum(1 for _, blocking in rounds if blocking) >= 2 and bool(rounds) and rounds[-1][1] > 0


def effective_review(root: Path, module: str, kind: str, raw: str) -> tuple:
    """codex-approval: (state, approved by) where Codex's approval counts only when the takeover gives it this step.

    plan-auto-approve: a v2 Plan is ("approved", "auto") once tasks/<id>/plan.md exists, whatever marker it carries.
    """
    if kind == "plan" and _v2(root, module):
        return ("approved", "auto") if (root / "tasks" / module / "plan.md").is_file() else ("none", None)
    if raw == "codex-approved":
        return ("approved", "codex") if not codex_route(root, module, kind) else ("pending", None)
    return raw, ("user" if raw == "approved" else None)


def cadence_combined(root: Path, module: str) -> bool:
    """reviewCadence=combined, except where the Spec and the Plan have different approvers (codex-approval Q5)."""
    if load_config(root)[0].get("reviewCadence") != "combined":
        return False
    return (codex_route(root, module, "spec") == "") == (codex_route(root, module, "plan") == "")


def codex_hint(root: Path, module: str, stage: str, cmd: dict, zh: bool, raw: dict) -> tuple | None:
    """(Review line, next step) where Codex approves a step under the takeover, or where its approval does not count."""
    paths = {"spec": "spec/%s.md" % module, "plan": "tasks/%s/plan.md" % module}
    names = {"spec": "Spec", "plan": "Plan"}
    for kind in ("spec", "plan"):
        state, path = raw[kind], paths[kind]
        if kind == "plan" and stage != "BUILDING":
            continue
        route = codex_route(root, module, kind)
        if route == "important" and state in ("pending", "codex-approved"):
            reasons = ", ".join(important(root, module))
            if zh:
                return ("- 批准: Spec `%s` 是重要需求（%s），不论接管档位都由用户批。" % (path, reasons),
                        "先用 agent-skills 的 interview-me 一次一个问题向用户拷问需求，按答复改好 `%s`，再交用户审；Codex 的批准在这里不算数。"
                        "用户批准后，用 %s 记下来。" % (path, cmd["review-mark"]))
            return ("- Review: Spec `%s` is an important requirement (%s), so the user approves it whatever the takeover."
                    % (path, reasons),
                    "first interview the user with agent-skills' interview-me, one question at a time, revise `%s` from the "
                    "answers, then have the user review it; Codex's approval does not count here. When the user approves "
                    "it, record that with %s." % (path, cmd["review-mark"]))
        if state == "codex-approved" and route:
            why = (("本模块的接管档位要求人批" if route == "takeover" else "Plan 的「预先声明」有内容，按规则由用户批") if zh else
                   ("this module's takeover gives this step to the user" if route == "takeover"
                    else "the Plan pre-declares shared changes, which the user approves"))
            if zh:
                return ("- 批准: %s `%s` 经 Codex 审过，但%s。" % (names[kind], path, why),
                        "把 `%s` 交给用户审；Codex 的批准在这里不算数。用户批准后，用 %s 记下来。" % (path, cmd["review-mark"]))
            return ("- Review: %s `%s` was reviewed by Codex, but %s." % (names[kind], path, why),
                    "have the user review `%s`; Codex's approval does not count here. When the user approves it, record "
                    "that with %s." % (path, cmd["review-mark"]))
        if state == "pending" and route == "pre-declared":
            # M3 rework: say why this Plan skips Codex instead of only "waiting for the user".
            if zh:
                return ("- 批准: Plan `%s` 的「预先声明」有内容或格式不对，按规则由用户批，不交 Codex。" % path,
                        "把 `%s` 交给用户审，交审时逐条列出预先声明的四行；格式不对就先按 verify-artifacts 的提示改好。"
                        "用户批准后，用 %s 记下来。" % (path, cmd["review-mark"]))
            return ("- Review: Plan `%s`'s pre-declared section lists shared changes or is malformed, so the user "
                    "approves it, not Codex." % path,
                    "have the user review `%s`, listing the four pre-declared lines; if the section is malformed, fix it "
                    "as verify-artifacts says first. When the user approves it, record that with %s."
                    % (path, cmd["review-mark"]))
        if state != "pending" or route:
            continue
        if codex_rounds_exhausted(root, path):
            if zh:
                return ("- 批准: %s `%s` 经 Codex 审了两轮仍有阻断意见。" % (names[kind], path),
                        "停下，把两轮的阻断意见和你的改法交给用户决定；之后只能由用户批准（%s `--state approved`）。"
                        % cmd["review-mark"])
            return ("- Review: %s `%s` still has blocking findings after two Codex rounds." % (names[kind], path),
                    "stop and hand both rounds' blocking findings, with how you would fix them, to the user; from here only "
                    "the user approves it (%s `--state approved`)." % cmd["review-mark"])
        if zh:
            return ("- 批准: %s `%s` 按接管档位由 Codex 审。" % (names[kind], path),
                    "用 /delegate:review（后端 codex）审 `%s`，把它标准输出的 JSON 存成仓库外的文件（例如 `$TMPDIR` 下），免得报告本身被当成改动；没有阻断意见就用 %s `--state codex-approved "
                    "--review <文件>` 记下并接着往下做；有阻断就用 `--state codex-reviewed` 记下这一轮、改完再审，两轮仍有阻断就交用户。"
                    "建议类意见由你决定是否采纳，在「外部审查意见」一节逐条写一句理由。Codex 不可用时停下等，不要自己审自己。"
                    % (path, cmd["review-mark"]))
        return ("- Review: %s `%s` is reviewed by Codex under the takeover." % (names[kind], path),
                "review `%s` with /delegate:review (backend codex) and save its standard-output JSON to a file outside the repository (for example under `$TMPDIR`), so the report is not taken for a change; with no "
                "blocking finding record it with %s `--state codex-approved --review <file>` and go on; with blocking "
                "findings record the round with `--state codex-reviewed`, fix them and review again, and hand it to the user "
                "after two blocking rounds. Decide on each suggestion yourself and give one line of reason under the external "
                "review section. If Codex is unavailable, stop and wait; never review it yourself."
                % (path, cmd["review-mark"]))
    return None


BASELINE_COMMITS = 50  # pre-build-spec-batch: how far back the approved baseline is looked for


def spec_baseline(root: Path, module: str) -> dict:
    """pre-build-spec-batch: the Spec text the current approval marker was given for, read from git history.

    {"status": "found", "commit", "text"} for the newest of the last BASELINE_COMMITS commits touching the Spec whose
    text (marker line left out) has the marker's digest; {"status": "absent"} when there is no such commit or no
    digest approval; {"status": "unverified", "reason"} when git cannot be read -- a failed probe is never "absent".
    Read-only.
    """
    relative = "spec/%s.md" % module
    try:
        current = (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return {"status": "unverified", "reason": "%s: %s" % (relative, type(error).__name__)}
    markers = _review_split(current)[0]
    match = REVIEW_APPROVED_DIGEST.fullmatch(markers[0]) if len(markers) == 1 else None
    if match is None:
        return {"status": "absent"}

    def run(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=5)

    try:
        if run("rev-parse", "--is-inside-work-tree").returncode != 0:
            return {"status": "unverified", "reason": "not a git work tree"}
        if run("rev-parse", "--verify", "-q", "HEAD").returncode != 0:
            return {"status": "absent"}
        log = run("log", "-n", str(BASELINE_COMMITS), "--format=%H", "--", relative)
        if log.returncode != 0:
            return {"status": "unverified", "reason": "git log failed"}
        for sha in log.stdout.decode("ascii", "replace").split():
            shown = run("show", "%s:./%s" % (sha, relative))
            if shown.returncode != 0:
                continue
            try:
                text = shown.stdout.decode("utf-8")
            except UnicodeError:
                continue
            if match.group(1) in (review_digest(text), whole_review_digest(review_body(text))):
                return {"status": "found", "commit": sha, "text": text}
    except (OSError, subprocess.SubprocessError) as error:
        return {"status": "unverified", "reason": type(error).__name__}
    return {"status": "absent"}


def pre_build_batch(root: Path, module: str, stage: str, spec: str, plan: str) -> dict | None:
    """pre-build-spec-batch: the baseline when a revised Spec is waiting for the Plan's review, else None.

    "Before the build" is NEEDS_PLAN, or BUILDING with the Plan still pending; once the Plan is approved (or carries
    no marker, as in older projects) the build rules apply unchanged.
    """
    if spec != "revised" or not (stage in BEFORE_PLAN or (stage == "BUILDING" and plan == "pending")):
        return None
    return spec_baseline(root, module)


def review_hint(root: Path, module: str, stage: str, cmd: dict, zh: bool = False) -> tuple:
    """(Review line, replacement next step, Spec state, Plan state) for the current module; empty strings when nothing to say.

    design-review: with nothing else open, a design that has not passed takes the review line (design_hint).
    """
    line, step, spec, plan = _review_hint(root, module, stage, cmd, zh)
    if not line and not step:
        line, step = design_hint(root, module, stage, cmd, zh)
    return line, step, spec, plan


def _review_hint(root: Path, module: str, stage: str, cmd: dict, zh: bool = False) -> tuple:
    """review_hint for the Spec and the Plan.

    Only a marker changes anything: a module with no marker keeps today's output.  Fixed wording and
    the validated module id only -- never text from the files.
    """
    # requirement-confirm-gate: a waiting v2 requirement comes before every other review branch, also once the todo is done.
    wait = requirement_wait(root, module) if stage in BEFORE_PLAN + ("BUILDING", "MODULE_DONE") else None
    if wait:
        line, step = requirement_hint(root, module, wait, cmd, zh)
        plan = "none"
        if stage == "BUILDING":
            plan = effective_review(root, module, "plan", file_review_state(root / "tasks" / module / "plan.md", "plan"))[0]
        return line, step, "revised" if wait == "revised" else "pending", plan
    if stage not in BEFORE_PLAN + ("BUILDING",):
        return "", "", "none", "none"
    overall = overall_wait(root, module)
    if overall:  # sg-gate-flow (rule 8): the overall design comes right after the requirement
        line, step = overall_hint(overall, module, stage, cmd, zh)
        return line, step, "approved", "none"
    spec_path, plan_path = "spec/%s.md" % module, "tasks/%s/plan.md" % module
    spec = file_review_state(root / spec_path, "spec")
    plan = file_review_state(root / plan_path, "plan") if stage == "BUILDING" else "none"
    if _v2(root, module):
        plan = "none"  # plan-auto-approve: a v2 Plan's marker does nothing; effective_review approves it below
    for state, path in ((spec, spec_path), (plan, plan_path)):
        if state == "invalid" and zh:
            return ("- 批准: `%s` 里的批准标记无效。" % path,
                    "运行 %s 查看标记哪里不对；批准状态未知，修好之前不要继续。" % cmd["verify"], spec, plan)
        if state == "unreadable" and zh:
            return ("- 批准: `%s` 读不了，批准状态未知（这是读取故障，不是批准状态）。" % path, "", spec, plan)
        if state == "invalid":
            return ("- Review: the review marker in `%s` is invalid." % path,
                    "run %s to see what is wrong with the marker; the review state is unknown, so do not "
                    "continue until it is fixed." % cmd["verify"], spec, plan)
        if state == "unreadable":
            return ("- Review: `%s` could not be read, so its review state is unknown (a read failure, "
                    "not a review state)." % path, "", spec, plan)
    raw = {"spec": spec, "plan": plan}
    spec, plan = effective_review(root, module, "spec", spec)[0], effective_review(root, module, "plan", plan)[0]
    codex = codex_hint(root, module, stage, cmd, zh, raw)
    if codex is not None:
        return codex[0], codex[1], spec, plan
    if zh:
        return review_hint_zh(root, module, stage, cmd, spec, plan, spec_path, plan_path)
    hold = _hold(root, module, stage, False)
    record = " When the user approves it, record that with %s." % cmd["review-mark"]
    v2 = stage in BEFORE_PLAN and _v2(root, module)
    if spec == "pending":
        line = "- Review: Spec `%s` is awaiting the user's review." % spec_path
        if stage in BEFORE_PLAN and cadence_combined(root, module) and v2:
            return (line, "%s; once the documents up to the Plan are written, present them with the Spec together for one "
                    "approval.%s" % (doc_step(module, stage, False), record), spec, plan)
        if stage == "NEEDS_PLAN" and cadence_combined(root, module):
            return (line, "write `tasks/%s/plan.md` and `tasks/%s/todo.md`, then present the Spec and the Plan "
                    "together for one approval.%s" % (module, module, record), spec, plan)
        return line, "wait for the user to review `%s`; %s.%s" % (spec_path, hold, record), spec, plan
    batch = pre_build_batch(root, module, stage, spec, plan)
    if batch is not None and batch["status"] == "found":
        return ("- Review: Spec `%s` was edited after it was approved (baseline %s)." % (spec_path, batch["commit"][:7]),
                "the revision may wait for the Plan's review: record the revision in the Spec's change log and %s as "
                "usual; when presenting the Plan, show the Spec's cumulative diff against the baseline verbatim and "
                "say that approving the Plan also approves the revised Spec, then record both with %s (`--target both`). "
                "Stop and ask at once if the revision weakens an approved acceptance criterion, makes a decision the Spec "
                "does not cover, touches an ask-first item in the Spec's Boundaries, or is high-risk or irreversible."
                % (doc_step(module, stage, False) if v2 else "write the Plan", cmd["review-mark"]), spec, plan)
    if batch is not None and stage in BEFORE_PLAN:
        why = ("the approved text is not in git (commit the Spec right after approval)" if batch["status"] == "absent"
               else "the baseline could not be checked (%s)" % batch["reason"])
        return ("- Review: Spec `%s` was edited after it was approved." % spec_path,
                "show the user the revised `%s` for another review; %s.%s It cannot wait for the Plan's review: %s."
                % (spec_path, hold, record, why), spec, plan)
    if spec == "revised" and stage == "BUILDING" and at_final_gate(root, module):
        return ("- Review: Spec `%s` was edited after it was approved." % spec_path,
                "at the final gate, show the diff of the revised `%s` verbatim in the acceptance message and say that "
                "approving the acceptance also approves the revised Spec; once approved, record the Spec approval with "
                "%s before ticking and committing." % (spec_path, cmd["review-mark"]), spec, plan)
    if spec == "revised" and stage == "BUILDING":
        # align-upstream-rules: an in-scope fix waits for the final acceptance; only a change of scope stops.
        return ("- Review: Spec `%s` was edited after it was approved." % spec_path,
                "an in-scope fix to the approved `%s` may go on: record it in the Spec's change log and show its diff at "
                "the final gate for one approval; if it changes the scope or the direction or needs a new trade-off, stop "
                "and show the user the revised Spec for another review." % spec_path, spec, plan)
    if spec == "revised":
        return ("- Review: Spec `%s` was edited after it was approved." % spec_path,
                "show the user the revised `%s` for another review; %s.%s" % (spec_path, hold, record), spec, plan)
    if plan == "pending":
        return ("- Review: Plan `%s` is awaiting the user's review." % plan_path,
                "wait for the user to review `%s`; %s.%s" % (plan_path, hold, record), spec, plan)
    return "", "", spec, plan


def review_hint_zh(root: Path, module: str, stage: str, cmd: dict, spec: str, plan: str, spec_path: str,
                   plan_path: str) -> tuple:
    """review_hint's Chinese wording (hint-language-follow); the same decisions in the same order."""
    hold = _hold(root, module, stage, True)
    record = "用户批准后，用 %s 记下来。" % cmd["review-mark"]
    v2 = stage in BEFORE_PLAN and _v2(root, module)
    if spec == "pending":
        line = "- 批准: Spec `%s` 正在等用户批准。" % spec_path
        if stage in BEFORE_PLAN and cadence_combined(root, module) and v2:
            return (line, "%s；Plan 之前的文档写齐后，连同 Spec 一起交给用户一次批准。%s" % (doc_step(module, stage, True), record),
                    spec, plan)
        if stage == "NEEDS_PLAN" and cadence_combined(root, module):
            return (line, "写 `tasks/%s/plan.md` 和 `tasks/%s/todo.md`，然后把 Spec 和 Plan 一起交给用户一次批准。%s"
                    % (module, module, record), spec, plan)
        return line, "等用户审阅 `%s`；%s。%s" % (spec_path, hold, record), spec, plan
    batch = pre_build_batch(root, module, stage, spec, plan)
    if batch is not None and batch["status"] == "found":
        return ("- 批准: Spec `%s` 批准后又改过（基线 %s）。" % (spec_path, batch["commit"][:7]),
                "开工前的修订可以攒到 Plan 交审一次批：记进 Spec 末尾的变更记录，照常%s；交审 Plan 时原样附上 Spec 相对基线的"
                "累计差异，说明批准 Plan 也就批准了修订后的 Spec，批准后用 %s（`--target both`）一起记下。修订削弱了已批准的验收标准、"
                "做了 Spec 没覆盖的决定、碰到 Spec 的 Boundaries 里的「先问」项，或是高风险、不可逆的操作时，当场停下问用户。"
                % (doc_step(module, stage, True) if v2 else "写 Plan", cmd["review-mark"]), spec, plan)
    if batch is not None and stage in BEFORE_PLAN:
        why = ("取不到批准时的原文（Spec 获批后先提交再改）" if batch["status"] == "absent"
               else "基线未判定（%s）" % batch["reason"])
        return ("- 批准: Spec `%s` 批准后又改过。" % spec_path,
                "把改过的 `%s` 再给用户审一次；%s。%s不能攒到 Plan 交审：%s。" % (spec_path, hold, record, why), spec, plan)
    if spec == "revised" and stage == "BUILDING" and at_final_gate(root, module):
        return ("- 批准: Spec `%s` 批准后又改过。" % spec_path,
                "在最终 gate，把改过的 `%s` 的 diff 原样放进验收消息，并说明批准验收也就批准了改过的 Spec；批准后，"
                "先用 %s 记下 Spec 的批准，再勾选并提交。" % (spec_path, cmd["review-mark"]), spec, plan)
    if spec == "revised" and stage == "BUILDING":
        return ("- 批准: Spec `%s` 批准后又改过。" % spec_path,
                "范围内修正已批准的 `%s` 可以继续：记进 Spec 末尾的变更记录，最终验收时附差异一并批准；改了范围、方向或"
                "需要新取舍时，停下把修订后的 Spec 交用户复审。" % spec_path, spec, plan)
    if spec == "revised":
        return ("- 批准: Spec `%s` 批准后又改过。" % spec_path,
                "把改过的 `%s` 再给用户审一次；%s。%s" % (spec_path, hold, record), spec, plan)
    if plan == "pending":
        return ("- 批准: Plan `%s` 正在等用户批准。" % plan_path,
                "等用户审阅 `%s`；%s。%s" % (plan_path, hold, record), spec, plan)
    return "", "", spec, plan


# delegate-review-hint: where an external review is recorded, and the line the user's decline leaves behind.
EXTERNAL_REVIEW_HEADING = re.compile(r"^##\s+(?:外部审查意见|External review)\s*$")
EXTERNAL_REVIEW_DECLINED = "<!-- spec-guard: external-review declined -->"
EXTERNAL_REVIEW_STATES = ("none", "recorded", "declined")


def external_review_state(root: Path, module: str) -> str | None:
    """`recorded`, `declined` or `none` from the module's Spec and todo; None when either cannot be read.

    Recorded: an external-review section with any non-blank line.  Declined: the exact decline line anywhere.
    """
    recorded = declined = False
    for path in (root / "spec" / ("%s.md" % module), root / "tasks" / module / "todo.md"):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            return None
        inside = False
        for line in lines:
            if line.strip() == EXTERNAL_REVIEW_DECLINED:
                declined = True
            elif EXTERNAL_REVIEW_HEADING.match(line):
                inside = True
            elif line.startswith("#"):
                inside = False
            elif inside and line.strip():
                recorded = True
    return "recorded" if recorded else "declined" if declined else "none"


def external_review_hint(root: Path, module: str, stage: str, spec: str, plan: str, host: str | None,
                         zh: bool = False) -> str:
    """The optional line proposing a read-only review by delegate at a review checkpoint; empty when not due.

    Fixed wording and the validated module id only.  The plugin records are read only at a checkpoint.
    """
    if stage in BEFORE_PLAN and spec in ("pending", "none"):
        what, where = "Spec", "spec/%s.md" % module
    elif stage == "BUILDING" and plan == "pending":
        what, where = "Plan", "tasks/%s/todo.md" % module
    elif stage == "BUILDING" and at_final_gate(root, module):
        what, where = "final acceptance", "tasks/%s/todo.md" % module
    else:
        return ""
    if external_review_state(root, module) != "none":
        return ""
    entry = delegate_review_entry(root, host)
    if entry is None:
        return ""
    if zh:
        return ("- 外部审查（delegate，已安装）: 如果%s值得另一个 agent 做一次只读复核（跨模块、有取舍、不可逆、信息缺失、"
                "接口提案、任务很多），可以提议用 %s；用户同意后才启动。审查结论只作参考，不算用户的批准。把结论记在 `%s` 的 "
                "`## 外部审查意见`（或 `## External review`）小节下；用户不需要时，在那里加上 `%s`。两者有其一，"
                "这个模块就不再出这一行。"
                % ({"Spec": "这份 Spec ", "Plan": "这份 Plan "}.get(what, "这次最终验收"),
                   COMMANDS_ZH[host]["delegate-review"] % entry, where, EXTERNAL_REVIEW_DECLINED))
    return ("- External review (from delegate, installed): if this %s deserves a second agent's read-only review "
            "(cross-module, trade-offs, irreversible, missing information, an interface proposal, many tasks), you "
            "may propose %s; start it only after the user agrees. Findings are advisory, not the user's approval. "
            "Record them under `## External review` in `%s`, or add `%s` there if the user "
            "declines; either one stops this line for the module."
            % (what, COMMANDS[host]["delegate-review"] % entry, where, EXTERNAL_REVIEW_DECLINED))


def documentation_baseline_present(root: Path) -> bool:
    """doc-chain: the project keeps a documentation baseline (a symlink counts; the check itself reports it invalid)."""
    path = root / "docs" / "DOCUMENTATION-BASELINE.md"
    return path.is_symlink() or path.exists()


def documentation_check_line(module: str, cmd: dict, zh: bool) -> str:
    """doc-chain (D15): the line a final gate gets when the project has a baseline -- run the check, report it."""
    entry = cmd["doc-verify"] % module
    if zh:
        return ("- 文档核验：项目有文档基线，最终验收前跑 %s，把结果写进验收消息的「验收结果」：现状类 update 没改过、"
                "target 文档有删改、外部文档未核验的，逐条写明；attention 不卡验收。" % entry)
    return ("- Documentation check: this project has a documentation baseline; before the final acceptance run %s "
            "and put the result under the acceptance results: name each current-state update left unchanged, each "
            "target document with deletions, and each external document as unverified; attention does not block the "
            "acceptance." % entry)


def role_view(root: Path, kind: str, module: str | None, by_id: dict, cmd: dict, review_step: str = "",
              zh: bool = False) -> tuple:
    """checkout-role: (lines, next step) for a checkout with a role; the project-wide selection is not touched.

    A module checkout is told only about its own module; a coordinator keeps any review constraint and is never
    told to build.  Fixed wording and validated module ids only; Chinese follows hint-language-follow.
    """
    if kind == "coordinator":
        lines = ["- checkout 角色: 协调 — 这个 checkout 负责协调各模块，不在这里开发模块。" if zh else
                 "- Checkout role: coordinator — this checkout coordinates the modules; do not develop modules here."]
        if review_step:
            return lines, review_step + ("作为协调会话，在这里呈现给用户并在这里记录结果。" if zh else
                                         " As the coordinating session, present it to the user here and record the decision here.")
        return lines, (("统筹各模块：用 %s 查看可开工的模块、各模块的 worktree 与并行边界重叠，按共享规则「协调会话的批准与合并」"
                        "处理交回与合并；不在这里开发模块。" if zh else
                        "coordinate the modules: use %s to see startable modules, module worktrees and boundary overlaps, and "
                        "handle hand-backs and merges by the shared rule for the coordinating session's approvals and merges; "
                        "do not build modules here.") % cmd["map"])
    lines = [("- checkout 角色: 模块 `%s` — 这个 checkout 只做 `%s`；做完后交回协调会话（不在这里合并或推送）。" if zh else
              "- Checkout role: module `%s` — this checkout works only on `%s`; when it is done, hand it back to the "
              "coordinating session (no merge or push here).") % (module, module)]
    state = by_id.get(module)
    if state is None:
        return lines, (("这个 checkout 的角色指向 `%s`，但能力图里没有这个模块；用 %s 重新指定或清除角色。不要在这里做别的模块。" if zh else
                        "this checkout's role names `%s`, which is not in the capability map; set or clear the role "
                        "with %s. Do not work on other modules here.") % (module, cmd["checkout-role"]))
    if state["suspended"]:
        lines.append(("- 本 checkout 的模块 `%s`: 已挂起（%d 个未勾选项）" if zh else
                      "- This checkout's module `%s`: suspended (%d unchecked item(s))") % (module, state["open"]))
        return lines, (("`%s` 已挂起；用 %s 恢复它，或请协调会话重新指定或清除这个 checkout 的角色。不要在这里开始别的模块。" if zh else
                        "`%s` is suspended; resume it with %s, or ask the coordinating session to reassign or clear this "
                        "checkout's role. Do not start other modules here.") % (module, cmd["resume"] % module))
    stage = state["stage"]
    if stage == "DONE" and requirement_wait(root, module):
        stage = "MODULE_DONE"  # requirement-confirm-gate: the requirement still waits, so hand it on like any review
    if stage == "DONE":
        lines.append(("- 本 checkout 的模块 `%s`: DONE" if zh else "- This checkout's module `%s`: DONE") % module)
        return lines, (("`%s` 在这个 checkout 里已完成；交回协调会话做最终验收与合并。不要在这里开始别的模块，也不要在这里合并或推送。"
                        if zh else
                        "`%s` is done in this checkout; hand it back to the coordinating session for its final acceptance "
                        "and merge. Do not start another module here, and do not merge or push from here.") % module)
    open_note = (("（%d 个未勾选项）" if zh else " (%d unchecked item(s))") % state["open"]) if stage == "BUILDING" else ""
    lines.append(("- 本 checkout 的模块 `%s`: %s%s" if zh else "- This checkout's module `%s`: %s%s")
                 % (module, stage, open_note))
    review_line, own_step, _spec, _plan = review_hint(root, module, stage, cmd, zh)
    if review_line:
        lines.append(review_line)
    approval = design_waits(root, module, stage)
    if own_step and approval is not None and not design_to_user(approval) and own_step == design_hint(
            root, module, stage, cmd, zh)[1]:
        # takeover-redefine (R2-4): the second reviewer, not the user, lets this design through; do it here.
        return lines, (("`%s` 的技术方案待第二审查者审（见上面的批准行）：在这个 checkout 里照批准行发起审查并记下结果；"
                        "放行前不要继续。审完要用户批的，再交给协调会话。" if zh else
                        "`%s`'s design awaits the second reviewer (see the Review line above): run the review in this "
                        "checkout as the Review line says and record it; do not continue until it passes. Where the user "
                        "approves it after the review, hand it to the coordinating session then.") % module)
    if own_step:
        return lines, (("`%s` 有待处理的批准（见上面的批准行）：交给协调会话请用户审，批准经集成分支到达这个 checkout 之前不要继续。"
                        if zh else
                        "`%s` has a review step open (see the Review line above): hand it to the coordinating session for "
                        "the user's review, and do not continue until the approval reaches this checkout through the "
                        "integration branch.") % module)
    if stage == "NEEDS_SPEC":
        return lines, (("写 `spec/%s.md`，交给协调会话请用户审。" if zh else
                        "write `spec/%s.md` and hand it to the coordinating session for review.") % module)
    if stage in BEFORE_PLAN and _v2(root, module):
        return lines, (("%s，写好后交给协调会话。" if zh else "%s, then hand it to the coordinating session.")
                       % doc_step(module, stage, zh)) + sections_sentence(root, stage, zh)
    if stage == "NEEDS_PLAN":
        return lines, (("写 `tasks/%s/plan.md` 和 `tasks/%s/todo.md`（例如用 %s），交给协调会话请用户审。" if zh else
                        "create `tasks/%s/plan.md` and `tasks/%s/todo.md` (for example with %s) and hand them to the "
                        "coordinating session for review.") % (module, module, cmd["plan"]))
    if stop_node(root, module, stage, _spec, _plan) == "final-gate" and documentation_baseline_present(root):
        lines.append(documentation_check_line(module, cmd, zh))
    gate = next_gate(root, module)
    if gate:
        lines.append(("- `%s` 的下一个 gate: %s — 到那里停下，把模块交回协调会话。" if zh else
                      "- Next gate of `%s`: %s — stop there and hand the module back to the coordinating session.")
                     % (module, gate))
    return lines, (("继续用 %s 构建 `%s`：`tasks/%s/todo.md` 里还有 %d 个未勾选项。" if zh else
                    "continue %s on `%s`: %d unchecked item(s) in `tasks/%s/todo.md`.")
                   % ((cmd["build"], module, module, state["open"]) if zh else (cmd["build"], module, state["open"], module)))


# quiet-injection (D5): the hint ends with a state code over the facts whose change calls for the full text; the
# hook compares it with the code of its last injection in the transcript and otherwise gives one line.  The number of
# unchecked items and the context size are left out: they change every turn without changing what to do.
STATE_MARK = "<!-- spec-guard-state: %s -->"


def state_key(*facts) -> str:
    """Eight hex digits over `facts` (any reprs); equal facts give the same code in every process.

    A checksum, not a fingerprint: spec-digest.py stays the only fingerprint algorithm.
    """
    return "%08x" % zlib.crc32(repr(facts).encode("utf-8"))


def _role_facts(root: Path, kind: str, module: str | None, by_id: dict, cmd: dict, zh: bool) -> tuple:
    """What a role checkout is told about, without the counts its lines carry."""
    state = by_id.get(module) if kind == "module" else None
    if state is None:
        return kind, module
    stage = state["stage"]
    if stage == "DONE" or state["suspended"]:
        return kind, module, stage, state["suspended"], requirement_wait(root, module)
    _line, _step, spec_review, plan_review = review_hint(root, module, stage, cmd, zh)
    return (kind, module, stage, spec_review, plan_review, stop_node(root, module, stage, spec_review, plan_review),
            next_gate(root, module) if stage == "BUILDING" else None, requirement_wait(root, module),
            design_fact(root, module, stage), regression_line(root, module, stage, zh)[0],
            author_line(root, module, stage, zh)[0], verification_line(root, module, stage, zh)[0])


def brief_line(root: Path, stage: str, module: str | None, open_items: int | None, code: str, zh: bool) -> str:
    """quiet-injection: the one line given while the state code is unchanged -- stage, module, unchecked, branch."""
    parts = [stage, "`%s`" % module if module else "—",
             "—" if open_items is None else (("未勾选 %d" if zh else "%d unchecked") % open_items)]
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    sha = None if branch else _git(root, "rev-parse", "--short", "HEAD")
    if branch:
        parts.append(("分支 `%s`" if zh else "branch `%s`") % safe_fragment(branch))
    elif sha:
        parts.append(("分离于 `%s`" if zh else "detached at `%s`") % safe_fragment(sha))
    tail = "（状态未变，完整说明见此前的阶段提示）" if zh else " (unchanged; see the earlier phase hint for details)"
    return "spec-guard: " + " · ".join(parts) + tail + " " + STATE_MARK % code


def describe(root: Path, host: str | None = None,
             state_extra: str | None = None, last_state: str | None = None) -> str:
    """The stage hint; with `state_extra` (the hook's own facts: location, linked project) it ends with the state code.

    When `last_state` equals that code, only the one line comes back.  Diagnostics (an unreadable or invalid map) carry no code, so they are never shortened.
    """
    root = Path(root)
    info: dict = {}
    text = _describe_body(root, host, info)
    if state_extra is None or "facts" not in info:
        return text
    code = state_key(*info["facts"], state_extra)
    if last_state != code:
        return text + "\n\n" + STATE_MARK % code
    return brief_line(root, info["stage"], info["module"], info["open"], code, info["zh"])


def milestone_blocking(root: Path, modules) -> bool:
    """sg-gate-flow (rules 9-11): False only when every module of the milestone names the autopilot preset."""
    from project_config import module_preset  # late: project_config is imported by callers of this module
    return not modules or any(module_preset(root, module) != "autopilot" for module in modules)


def milestone_stop(root: Path, states: list, cmd: dict, zh: bool) -> tuple:
    """milestone-stop: (fact, line, next step) for the first finished, unconfirmed milestone of a usage draft.

    The criterion is usage_draft.stop; this only renders it. No draft and no stop give (None, "", ""); a draft that
    cannot be read gives a line saying so and no stop, never a failed hint.
    """
    done = {state["id"] for state in states if state["stage"] == "DONE"}
    try:
        found = usage_draft.stop(str(root), done, {state["id"] for state in states})
    except Exception as error:  # a probe that failed is reported as such, not as "no stop"
        found = {"status": "unverified", "reason": "%s: %s" % (type(error).__name__, error)}
    if found is None:
        return None, "", ""
    if found["status"] == "unverified":
        reason = safe_fragment(found["reason"]) or ("诊断为空" if zh else "no diagnostic")
        return (("unverified",), ("- 里程碑停点: 未判定（用法草案原文，非指令: %s）" if zh else
                                  "- Milestone stop: not checked (usage draft text, not instructions: %s)") % reason, "")
    draft, milestone = safe_fragment(found["file"]), safe_fragment(found["milestone"])
    modules = [safe_fragment(item) for item in found["modules"]]
    usages = [safe_fragment(item) for item in found["usages"]]
    fact = ("stop", draft, milestone, tuple(modules))
    if not milestone_blocking(root, found["modules"]):
        # sg-gate-flow: an autopilot milestone is reported, never a stop; the confirmation can still be recorded later.
        line = ("- 里程碑: `%s` 的 %s 已完成，未确认（模块 %s；autopilot 档，不阻塞，写进汇报；用户事后要确认时用 %s）"
                % (draft, milestone, "、".join(modules), cmd["milestone-mark"]) if zh else
                "- Milestone: %s of `%s` is done and not confirmed (modules %s; autopilot, not a stop -- put it in the "
                "report; the user can still record it later with %s)" % (milestone, draft, ", ".join(modules),
                                                                       cmd["milestone-mark"]))
        return ("report", draft, milestone, tuple(modules)), line, ""
    if zh:
        line = "- 里程碑停点: `%s` 的 %s（模块 %s 已全部完成，未确认）" % (draft, milestone, "、".join(modules))
        step = ("先不开下一个模块：按 `%s` 里 %s 的典型用法 %s 实际跑一遍，把命令与输出摆给用户判定；用户明确说通过后，用 %s "
                "预览、确认后记下，阶段提示才转到下一个模块。不通过就在本里程碑的模块 todo 里追加任务，或回头改草案。"
                % (draft, milestone, "、".join(usages), cmd["milestone-mark"]))
    else:
        line = "- Milestone stop: `%s` %s (modules %s all done, not confirmed)" % (draft, milestone, ", ".join(modules))
        step = ("do not start the next module yet: run %s of `%s` for real by its typical usage %s and put the commands "
                "and output in front of the user; once the user explicitly passes it, record it with %s (preview, then "
                "--confirm), and only then does the hint move on. If it does not pass, add tasks to this milestone's "
                "module todos or revise the draft." % (milestone, draft, ", ".join(usages), cmd["milestone-mark"]))
    return fact, line, step


def draft_gate(root: Path, states: list, module: str, stage: str, zh: bool) -> tuple:
    """usage-draft-gate: (fact, line, next step) when the current module waits for its Spec in a batch with no draft.

    The criterion is usage_draft.missing; git is read only at NEEDS_SPEC.  Unverified (no git, git failing) leaves the
    hint as it was: verify-artifacts reports it.
    """
    if stage != "NEEDS_SPEC" or not module:
        return None, "", ""
    done = {state["id"] for state in states if state["stage"] == "DONE"}
    try:
        found = usage_draft.missing(str(root), done)
    except Exception:  # a failed probe changes nothing here; verify-artifacts says it could not tell
        return None, "", ""
    batch = next((item for item in found.get("batches", []) if module in item["modules"]), None)
    if batch is None:
        return None, "", ""
    modules = [safe_fragment(item) for item in batch["modules"]]
    fact = ("draft-gate", tuple(modules))
    if zh:
        line = "- 用法草案: 模块 %s 是同一批插入的，还没有用法草案把它们写进里程碑。" % "、".join(modules)
        step = ("先写用法草案 `spec/usage/<需求>.md`（入口清单、典型用法、里程碑，覆盖这批全部模块：%s），交用户审，再写 `spec/%s.md`。"
                "已完成的模块也列进里程碑；其中已完成的里程碑在交审时请用户逐个三选一（照常跑一遍／凭已有证据判定通过／不记确认），"
                "不自动记确认。" % ("、".join(modules), module))
    else:
        line = "- Usage draft: modules %s were inserted together and no usage draft puts them in milestones yet." % (
            ", ".join(modules))
        step = ("write the usage draft `spec/usage/<requirement>.md` first (entry points, typical usage, milestones, covering "
                "every module of this batch: %s), have the user review it, then write `spec/%s.md`. List finished modules "
                "in the milestones too; for each finished milestone the user picks one: run it as usual, pass it on the "
                "evidence already there, or leave it unconfirmed. Never record a confirmation on your own."
                % (", ".join(modules), module))
    return fact, line, step


SCOPE_SHOWN = 5  # takeover-scope-check: how many out-of-scope files the line names


ACCEPTANCE_DIR = "spec-guard/acceptance"


def acceptance_path(root: Path, module: str) -> Path | None:
    """The shared Codex acceptance record: in the common git directory, never tracked."""
    found = _git(root, "rev-parse", "--git-common-dir")
    if not found:
        return None
    path = Path(found)
    common = path if path.is_absolute() else Path(root) / path
    return common / ACCEPTANCE_DIR / ("%s.json" % module)


def legacy_acceptance_path(root: Path, module: str) -> Path | None:
    """The pre-1.16 checkout-local location, read only as a compatibility fallback."""
    found = _git(root, "rev-parse", "--git-path", "%s/%s.json" % (ACCEPTANCE_DIR, module))
    if not found:
        return None
    path = Path(found)
    return path if path.is_absolute() else Path(root) / path


def acceptance_step(root: Path, module: str, stage: str, cmd: dict, zh: bool) -> tuple:
    """codex-final-acceptance (assumption 6): (fact, next step) at the final gate of a merge=auto module, else (None, "")."""
    if stage != "BUILDING" or not module or not at_final_gate(root, module) or _v2(root, module):
        return None, ""  # verification-criteria: a flow v2 module is verified against its regression document instead
    from project_config import module_takeover
    if module_takeover(root, module)[0].get("merge") != "auto":
        return None, ""
    entry = "--target acceptance --state codex-approved --review <report>"
    from module_scope import FLOW_DIRS, FLOW_FILES, scope_base  # late: module_scope imports this module
    base = scope_base(root, module)  # rework-scope-baseline: a rework is reviewed from its own start
    flow_files = ("、" if zh else ", ").join("`%s`" % path for path in FLOW_FILES + FLOW_DIRS)
    # M3 second rework: name the start of the review range instead of leaving the agent to work it out.
    start_zh = "（`%s`，即 `--base %s`）" % (base[:12], base[:12]) if base else ""
    start_en = "`%s` (the commit before this module; `--base %s`)" % (base[:12], base[:12]) if base else "the commit before this module"
    if zh:
        return ("acceptance", "auto", base), (
            "本模块合并是自动的，最终验收交 Codex：用 `/delegate:review`（后端 codex）审本模块开工前的提交%s到 HEAD 的补丁，"
            "`--spec spec/%s.md`；任务说明里列出流程文件（%s），写明它们不算实现范围，并附上 "
            "`~/.autopilot/evidence/<owner>__<repo>/<HEAD>.json` 里每条检查的命令、退出码、`output_sha256` 与 `tail`；"
            "报告存到仓库外；等 autopilot 在 HEAD 上的检查证据；两样齐了、工作区干净，用 %s（%s）"
            "记下验收，记录在 git 目录里、不进提交，最终 gate 合并后再补勾。缺任一样、或被拒绝，就停下等用户，不要自己验收。"
            "拟回告写进 todo，不发出，等用户确认。" % (start_zh, module, flow_files, cmd["review-mark"], entry))
    return ("acceptance", "auto", base), (
        "this module merges automatically, so Codex does the final acceptance: review the patch from %s to HEAD with "
        "`/delegate:review` (backend codex) and `--spec spec/%s.md`; in the task description, list the flow files (%s) "
        "as outside the implementation scope and attach each check's command, exit code, `output_sha256` and `tail` from "
        "`~/.autopilot/evidence/<owner>__<repo>/<HEAD>.json`; save the report outside "
        "the repository; wait for autopilot's check evidence on HEAD; with both and a clean working tree, record the "
        "acceptance with %s (%s) -- the record stays in the git directory, uncommitted, and the final gate is ticked "
        "after the merge. If either is missing or it is refused, stop and wait for the user; never accept it yourself. "
        "Write the drafted reply into the todo and do not send it until the user confirms." % (start_en, module, flow_files, cmd["review-mark"], entry))


OWN_DOCS = ("design.md", "regression.md", "plan.md", "todo.md")  # plan-auto-approve rework: the v2 documents in tasks/<id>/
# plan-auto-approve rework (Q1 A, Q3 A): flow bookkeeping a v2 module writes as it starts.  Not module_scope.FLOW_FILES:
# that one holds .agent/config.json (takeover levels) and goes with spec/usage/, which both stay T4.
T4_FLOW_FILES = ("spec/CAPABILITY-MAP.md", ".agent/state.json")


def own_doc(module: str, path: str) -> bool:
    """plan-auto-approve rework: the path is one of the module's own five documents (names only, nothing is read)."""
    return path == "spec/%s.md" % module or any(path == "tasks/%s/%s" % (module, name) for name in OWN_DOCS)


def t4_hits(root: Path, module: str, base: str | None = None) -> dict:
    """plan-auto-approve: {"status", "hits", "stops"} -- the changed files on the T4 list since the module's baseline.

    status `ok`, `no-list` (no readable risk-path list: not checked) or `no-base` (no baseline or git unreadable: not
    checked, never taken for "no change").  stops: hits and the module is not an important requirement -- an important
    one listed the path in its design, which the user approved.
    """
    from module_scope import changed_files, scope_base  # late: module_scope imports this module
    patterns = _risk_patterns(root, ("T4",))
    if patterns is None:
        return {"status": "no-list", "hits": [], "stops": False}
    base = base or scope_base(root, module)
    files = changed_files(root, base) if base else None
    if files is None:
        return {"status": "no-base", "hits": [], "stops": False}
    if _v2(root, module):  # rework (assumption 12): its own documents and the flow bookkeeping are not T4
        files = [(status, path) for status, path in files if not own_doc(module, path) and path not in T4_FLOW_FILES]
    hits = sorted({path for _, path in files if any(risk_hit(pattern, path) for pattern in patterns)})
    return {"status": "ok", "hits": hits, "stops": bool(hits) and not important(root, module)}


def _t4_part(root: Path, module: str, zh: bool) -> tuple:
    """(fact, line, next step) of the T4 check for a v2 build; ("", "", "") without anything to say."""
    found = t4_hits(root, module)
    if found["status"] == "no-list":
        return (("t4", "no-list"), "- T4 路径：没有可读的风险路径清单，未检查。" if zh else
                "- T4 paths: no readable risk-path list, not checked.", "")
    if found["status"] == "no-base":
        return (("t4", "no-base"), "- T4 路径：没有开工基线可比（需求文档还没提交，或 git 读不了），未检查。" if zh else
                "- T4 paths: no baseline to compare with (the requirement is not committed, or git is unreadable); not "
                "checked.", "")
    if not found["stops"]:
        return None, "", ""
    shown = ", ".join("`%s`" % safe_fragment(path) for path in found["hits"][:SCOPE_SHOWN]) + (
        "…" if len(found["hits"]) > SCOPE_SHOWN else "")
    if zh:
        return (("t4", tuple(found["hits"])), "- T4 路径：改到 %d 个 T4 文件（%s），本模块不是重要需求。" % (len(found["hits"]), shown),
                "停下，说明为什么要改这些高风险文件，交用户决定：同意就把它们补进技术方案影响面或并行边界——模块随之成为重要需求，按重要需求由用户批；"
                "不同意就撤回这些改动。")
    return (("t4", tuple(found["hits"])), "- T4 paths: %d T4 file(s) changed (%s), and the module is not an important "
            "requirement." % (len(found["hits"]), shown), "stop and tell the user why these high-risk files change: if "
            "they agree, add them to the design's impact section or the boundary -- the module then becomes an important "
            "requirement, which the user approves; if not, undo those changes.")


def _rework_note(root: Path, module: str, zh: bool) -> str:
    """rework-scope-baseline (assumption 4): how a rework's overreach is counted; "" for a first build."""
    from module_scope import _trim, rework_info  # late: module_scope imports this module
    rework = rework_info(root, module)
    if rework is None:
        return ""
    if rework["start"] is None:
        return "；返工：还没提交，与 HEAD 比较" if zh else "; rework: not committed yet, compared with HEAD"
    note = ("；返工：从提交 `%s` 起算" if zh else "; rework: counted from commit `%s`") % rework["start"][:12]
    if _trim(root, rework["base"]):  # assumption 9: commits already on the default branch were left out
        note += "（已扣除默认分支上的提交）" if zh else " (commits already on the default branch left out)"
    return note


def _flow_overreach(root: Path, module: str, found: dict, zh: bool) -> tuple:
    """plan-auto-approve: the scope part and the T4 part of a v2 build check, joined (assumptions 4, 5)."""
    facts, lines, steps = [], [], []
    for fact, line, step in (_scope_part(root, module, found, zh), _t4_part(root, module, zh)):
        if fact is not None:
            facts.append(fact)
        if line:
            lines.append(line)
        if step:
            steps.append(step)
    return (tuple(facts) or None), "\n".join(lines), ("" if not steps else steps[0] if len(steps) == 1 else
                                                   (("；另外，" if zh else "; also, ").join(steps)))


def _scope_part(root: Path, module: str, found: dict, zh: bool) -> tuple:
    """plan-auto-approve: (fact, line, next step) for a v2 module's build, whatever its takeover (assumption 4)."""
    from module_scope import classify, scope_base  # late: module_scope imports this module
    status = found["status"]
    if status == "none":
        return (("scope", "none"), "- 越界：没有并行边界，未检查。" if zh else
                "- Out of scope: no concurrency boundary, not checked.", "")
    if status in ("unknown", "invalid"):
        if zh:
            why = ("需求文档的并行边界写坏了或读不了" if status == "invalid" else "没有并行边界，技术方案影响面也没写出路径")
            return (("scope", status), "- 越界：%s，无法检查改动是否越界。" % why,
                    "停下，修好需求文档的并行边界或在技术方案影响面写出要改的文件（技术方案按 design-review 重新审或批），再继续构建。")
        why = ("the requirement's concurrency boundary is malformed or unreadable" if status == "invalid"
               else "there is no concurrency boundary and the design's impact section names no path")
        return (("scope", status), "- Out of scope: %s, so the changes cannot be checked." % why,
                "stop; fix the requirement's concurrency boundary or list the files in the design's impact section (the "
                "design is then reviewed or approved again under design-review), then continue the build.")
    base = scope_base(root, module)
    rows = classify(root, module, found["scope"], base) if base else None
    if rows is None:
        line = ("- 越界：没有开工基线可比（`spec/%s.md` 没有更早的提交，或 git 读不了），未检查。" % module if zh else
                "- Out of scope: no baseline to compare with (no commit before `spec/%s.md`, or git unreadable); not "
                "checked." % module)
        return ("scope", "unknown-base"), line, ""
    outside = [safe_fragment(row["path"]) for row in rows if row["scope"] == "outside"]
    if not outside:
        return None, "", ""
    shown = ", ".join("`%s`" % path for path in outside[:SCOPE_SHOWN]) + ("…" if len(outside) > SCOPE_SHOWN else "")
    if zh:
        return (("scope", tuple(outside)), "- 越界：%d 个文件超出需求文档的并行边界与技术方案影响面（%s）%s。"
                % (len(outside), shown, _rework_note(root, module, zh)),
                "停下，逐个说明这些文件为什么要改，交用户决定：同意就补进技术方案影响面或并行边界（技术方案按 design-review 重新审或批），"
                "不同意就撤回这些改动。")
    return (("scope", tuple(outside)), "- Out of scope: %d file(s) outside the requirement's boundary and the design's "
            "impact section (%s)%s." % (len(outside), shown, _rework_note(root, module, zh)), "stop and show the user why each of these files has to change: "
            "if they agree, add them to the design's impact section or the boundary (the design is then reviewed or "
            "approved again under design-review); if not, undo those changes.")


def scope_overreach(root: Path, module: str, stage: str, zh: bool) -> tuple:
    """takeover-scope-check: (fact, line, next step) when a takeover module's build goes outside its declared scope.

    Only a module whose takeover hands a step to codex or automation, while building.  No boundary stops too (Q11 A);
    a base that cannot be found or read is reported, not taken as clean.
    """
    if stage != "BUILDING" or not module:
        return None, "", ""
    from module_scope import ScopeError, classify, flow_scope, parse, scope_base  # late: module_scope imports this
    found = flow_scope(root, module)
    if found is not None:
        return _flow_overreach(root, module, found, zh)
    from project_config import module_takeover
    if all(value == "human" for value in module_takeover(root, module)[0].values()):
        return None, "", ""
    try:
        scope = parse((root / "spec" / ("%s.md" % module)).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ScopeError):
        scope = None
    if scope is None:
        if zh:
            return (("scope", "no-boundary"), "- 越界：`spec/%s.md` 没有可用的「并行边界」一节，无法检查改动是否越界。" % module,
                    "停下，把这个模块要改的文件交用户；用户同意后在 Spec 补上并行边界并复审，再继续构建。")
        return (("scope", "no-boundary"), "- Out of scope: `spec/%s.md` has no usable concurrency boundary, so the changes "
                "cannot be checked." % module, "stop and show the user which files this module changes; once they agree, "
                "add the concurrency boundary to the Spec, have it reviewed again, then continue the build.")
    base = scope_base(root, module)
    rows = classify(root, module, scope, base) if base else None
    if rows is None:
        line = ("- 越界：基线未判定（`spec/%s.md` 没有更早的提交可比），越界检查没有运行。" % module if zh else
                "- Out of scope: not checked (no commit before `spec/%s.md` to compare with)." % module)
        return ("scope", "unknown"), line, ""
    outside = [safe_fragment(row["path"]) for row in rows if row["scope"] == "outside"]
    if not outside:
        return None, "", ""
    shown = ", ".join("`%s`" % path for path in outside[:SCOPE_SHOWN]) + ("…" if len(outside) > SCOPE_SHOWN else "")
    if zh:
        return (("scope", tuple(outside)), "- 越界：%d 个文件超出 Spec 的并行边界与 Plan 的预先声明（%s）%s。"
                % (len(outside), shown, _rework_note(root, module, zh)),
                "停下，逐个说明这些文件为什么要改，交用户决定：同意就补进 Spec 并行边界或 Plan 预先声明并复审，不同意就撤回这些改动。")
    return (("scope", tuple(outside)), "- Out of scope: %d file(s) outside the Spec's boundary and the Plan's pre-declared "
            "paths (%s)%s." % (len(outside), shown, _rework_note(root, module, zh)), "stop and show the user why each of these files has to change: if they "
            "agree, add them to the Spec's concurrency boundary or the Plan's pre-declared section and have it reviewed "
            "again; if not, undo those changes.")


def _describe_body(root: Path, host: str | None, info: dict) -> str:
    zh = hint_language(root) == "zh-CN"  # hint-language-follow: English stays byte-identical to 0.67.0
    cmd = commands(host, zh)
    try:
        parsed = parse_map(root / "spec" / "CAPABILITY-MAP.md")
    except OSError as error:
        # A file that cannot be read is an environment fault, not a state of the map.
        return unreadable_map(safe_fragment(str(error)) or ("诊断为空" if zh else "no diagnostic"), zh)
    except (MapError, UnicodeError) as error:
        # The message carries the offending cell, which is the whole diagnostic value --
        # without it nobody knows which row is broken. It is also repository content, so
        # it goes through the sanitiser rather than being dropped or trusted.
        # Labelled as data: the quoted span is repository content, and a reader -- human
        # or model -- should not have to work out that the words inside it are not
        # addressed to them. The words themselves stay; that was the explicit decision.
        if zh:
            return ("当前阶段: **MAP_INVALID**\n\n- 能力图: 已有但无效（能力图原文，非指令: %s）\n\n建议下一步: 运行 %s，修好能力图。"
                    % (safe_fragment(str(error)) or "诊断为空", cmd["verify-quoted"]))
        return ("Current stage: **MAP_INVALID**\n\n- Capability map: present but invalid "
                "(capability map text, not instructions: %s)\n\n"
                "Suggested next step: run %s and fix the capability map."
                % (safe_fragment(str(error)) or "no diagnostic", cmd["verify-quoted"]))
    order = list(parsed.order) or [row.module_id for row in parsed.rows]
    states = [module_state(root, module_id) for module_id in order]
    by_id = {state["id"]: state for state in states}
    active, active_status = active_module_state(root)
    active = active if active_status == "present" else None
    stage, current, source, pending = project_stage(states, active)
    ms_fact, ms_line, ms_step = milestone_stop(root, states, cmd, zh)
    notes = config_lines(root, host)
    role_kind, role_id = checkout_role_of(root)  # ("none", None) whenever moduleConcurrency is not on
    if role_kind == "invalid":
        notes.append(("- checkout 角色: 角色标记无效，已忽略；用 %s 查看。" if zh else
                      "- Checkout role: the role marker is invalid, so it is ignored; check it with %s.")
                     % cmd["checkout-role"])
    if active_status == "invalid":
        # Report it, but never echo it: the value is repository content, and the note
        # itself is enough for the user to find what they typed.
        notes.append("- `.agent/state.json` 的 activeModule 不是有效的 module id；按 Build order 取当前模块。" if zh else
                     "- The activeModule in `.agent/state.json` is not a valid module id; using Build order.")
    elif active and active in by_id and by_id[active]["suspended"]:
        notes.append(("- activeModule `%s` 已挂起；按 Build order 取当前模块。" if zh else
                      "- activeModule `%s` is suspended; using Build order.") % active)
    elif active and active not in by_id:
        notes.append(("- activeModule `%s` 不在能力图里；按 Build order 取当前模块。" if zh else
                      "- activeModule `%s` is not in the capability map; using Build order.")
                     % safe_fragment(active))
    active_state = by_id.get(active) if active else None
    static_notes = tuple(notes)
    role_facts = _role_facts(root, role_kind, role_id, by_id, cmd, zh)
    no_todo_note = ""
    if active_state and active_state["stage"] == "DONE" and plan_without_todo(active_state):
        no_todo_note = ("- activeModule `%s` 有 Plan 但没有 `tasks/%s/todo.md`，所以按已完成计；还有工作要做就补上 todo。"
                        if zh else "- activeModule `%s` has a plan but no `tasks/%s/todo.md`, so it counts as done; "
                        "add the todo if work remains.") % (active, active)
    counts = ("- 模块 %d · Spec %d · Plan %d · 进行中 %d · 已完成 %d" if zh else
              "- Modules %d · Specs %d · Plans %d · In progress %d · Done %d") % (
        len(states), sum(s["spec"] for s in states), sum(s["plan"] for s in states),
        sum(s["stage"] == "BUILDING" and not s["suspended"] for s in states),
        sum(s["stage"] == "DONE" for s in states))
    suspended = [s for s in states if s["suspended"]]
    if suspended:
        counts += (" · 挂起 %d" if zh else " · Suspended %d") % len(suspended)
    deferred = sum(len(s["deferred"]) for s in states)
    if deferred:
        counts += (" · 延期 %d" if zh else " · Deferred %d") % deferred
    suspended_lines = [("- 挂起: `%s`（%d 个未勾选项）；用 %s 恢复。" if zh else
                        "- Suspended: `%s` (%d unchecked item(s)); resume with %s.")
                       % (s["id"], s["open"], cmd["resume"] % s["id"]) for s in suspended]
    if stage == "DONE":
        missing_todo = sum(plan_without_todo(s) for s in states)
        if missing_todo:
            counts += (("\n- 有 Plan 没 todo: %d 个模块按已完成计；运行 %s 检查。" if zh else
                        "\n- Plan without todo: %d module(s) counted as done; "
                        "run %s to review.") % (missing_todo, cmd["verify"]))
    paused = paused_modules(states, current) if stage != "DONE" else []
    unmerged = unmerged_commits(root) if stage in ("DONE", "MODULE_DONE") else None
    push_first = ""
    if unmerged and unmerged[0] > 0:
        count, ref = unmerged[0], safe_fragment(unmerged[1])
        hint = ("- 这个分支有 %d 个提交还不在 `%s` 里（按上次 fetch 的结果）。" if zh else
                "- This branch has %d commit(s) not yet in `%s` (as last fetched).") % (count, ref)
        push_first = ("先推送这个分支，把它的 %d 个提交合并进 `%s`；然后" if zh else
                      "push this branch and merge its %d commit(s) into `%s` first; then ") % (count, ref)
    else:
        hint = ""
    suspended_ids = tuple(s["id"] for s in suspended)
    if stage == "DONE":
        # requirement-confirm-gate: a finished v2 module whose requirement was never confirmed still waits.
        waiting = next(((m, w) for m in order for w in (requirement_wait(root, m),) if w), None)
        info.update(facts=["DONE", current["id"] if current else None, zh, static_notes, role_facts, suspended_ids,
                           bool(unmerged and unmerged[0] > 0), deferred, waiting] + ([ms_fact] if ms_fact else []),
                    stage="DONE", module=None, open=None, zh=zh)
        notes.extend(suspended_lines)
        if no_todo_note:
            notes.append(no_todo_note)
        if current is not None:
            notes.append(("- activeModule `%s` 已完成，可以清除。" if zh else
                          "- activeModule `%s` is already done and can be cleared.") % current["id"])
        if hint:
            notes.append(hint)
        if ms_line:
            notes.append(ms_line)
        if ms_step and role_kind not in ("module", "coordinator"):
            head = "当前阶段: **DONE**\n\n- 能力图: 已有\n" if zh else "Current stage: **DONE**\n\n- Capability map: present\n"
            return (head + counts + "\n" + "".join(n + "\n" for n in notes)
                    + ("\n建议下一步: " if zh else "\nSuggested next step: ") + ms_step
                    + stop_rules_block("milestone-stop", zh))
        if waiting:
            wait_line, wait_step = requirement_hint(root, waiting[0], waiting[1], cmd, zh)
            notes.append(wait_line)
            if role_kind not in ("module", "coordinator"):
                head = "当前阶段: **DONE**\n\n- 能力图: 已有\n" if zh else "Current stage: **DONE**\n\n- Capability map: present\n"
                return (head + counts + "\n" + "".join(n + "\n" for n in notes)
                        + ("\n建议下一步: " if zh else "\nSuggested next step: ") + wait_step
                        + stop_rules_block("spec-review", zh))
        if role_kind in ("module", "coordinator"):
            role_lines, role_step = role_view(root, role_kind, role_id, by_id, cmd, zh=zh)
            head = "当前阶段: **DONE**\n\n- 能力图: 已有\n" if zh else "Current stage: **DONE**\n\n- Capability map: present\n"
            return (head + counts + "\n" + "".join(n + "\n" for n in notes + role_lines)
                    + ("\n建议下一步: " if zh else "\nSuggested next step: ") + role_step)
        # formal-deferral: with deferred items left, "no open todo item" would read as nothing left at all.
        all_done = (("能力图里每个模块都有 Plan，除 %d 项延期（用 %s 查看）外没有未勾选的 todo 项" % (deferred, cmd["map"])
                     if deferred else "能力图里每个模块都有 Plan，且没有未勾选的 todo 项") if zh else
                    ("every mapped module has a plan and no open todo item apart from %d deferred item(s) waiting to "
                     "resume (list them with %s)" % (deferred, cmd["map"])
                     if deferred else "every mapped module has a plan and no open todo item"))
        also_deferred = ((("；另有 %d 项延期待恢复（用 %s 查看）" if zh else
                           "; %d deferred item(s) waiting to resume (list them with %s)") % (deferred, cmd["map"]))
                         if deferred else "")
        if zh:
            head = "当前阶段: **DONE**\n\n- 能力图: 已有\n" + counts + "\n" + "".join(n + "\n" for n in notes)
            proposal = "新增需要留下经过审查的决定记录时，用 Proposal。"
            if push_first:
                return (head + "\n建议下一步: " + ("除挂起的模块外都已完成；挂起 %d 个%s；" % (len(suspended), also_deferred)
                                                if suspended else all_done + "；") + push_first +
                        "要做新工作，先总结需求、问用户是否说完，确认后再用 " + cmd["add-module"] + " 插入一个模块；" + proposal)
            if suspended:
                return (head + "\n建议下一步: 除挂起的模块外都已完成；挂起 %d 个（等待结束后恢复其中一个）%s。要做新工作，"
                        "先总结需求、问用户是否说完，确认后再在这个检查点用 %s 插入一个模块；%s" % (len(suspended), also_deferred,
                                                                          cmd["add-module"], proposal))
            return (head + "\n建议下一步: " + all_done + "。要做新工作，先总结需求、问用户是否说完，确认后再在这个检查点用 "
                    + cmd["add-module"] + " 插入一个模块；" + proposal)
        if push_first:
            return ("Current stage: **DONE**\n\n- Capability map: present\n" + counts + "\n" + "".join(n + "\n" for n in notes) +
                    "\nSuggested next step: " + ("every module that is not suspended is done; %d suspended%s; "
                                                 % (len(suspended), also_deferred) if suspended else
                                                 all_done + "; ") + push_first +
                    "for new work, first summarise the requirement and ask the user whether it is complete, then insert a module with " + cmd["add-module"] + "; "
                    "use a Proposal when the addition needs a recorded, reviewed decision.")
        if suspended:
            return ("Current stage: **DONE**\n\n- Capability map: present\n" + counts + "\n" + "".join(n + "\n" for n in notes) +
                    "\nSuggested next step: every module that is not suspended is done; %d suspended (resume one "
                    "when its wait is over)%s. For new work, first summarise the requirement and ask the user whether it is complete, then insert a module with %s at this checkpoint; "
                    "use a Proposal when the addition needs a recorded, reviewed decision." % (len(suspended), also_deferred,
                                                                                              cmd["add-module"]))
        return ("Current stage: **DONE**\n\n- Capability map: present\n" + counts + "\n" + "".join(n + "\n" for n in notes) +
                "\nSuggested next step: " + all_done + ". "
                "For new work, first summarise the requirement and ask the user whether it is complete, then insert a module with " + cmd["add-module"] + " at this checkpoint; "
                "use a Proposal when the addition needs a recorded, reviewed decision.")
    module = current["id"]
    if no_todo_note:
        counts += "\n" + no_todo_note
    if hint:
        counts += "\n" + hint
    counts += "".join("\n" + line for line in suspended_lines)
    counts += "".join(("\n- 暂停: `%s`（%d 个未勾选项）；`%s` 之后恢复它。" if zh else
                       "\n- Paused: `%s` (%d unchecked item(s)); resume it after `%s`.") % (p["id"], p["open"], module)
                      for p in paused)
    if zh and stage == "MODULE_DONE" and paused:
        resume = paused[0]
        module_done = ("`%s` 已完成；恢复暂停的模块 `%s`（%s），把 activeModule 设为它。"
                       % (module, resume["id"], resume["stage"]))
    elif zh:
        module_done = ("`%s` 已完成；Build order 中下一个未完成的模块是 `%s`（%s）。开始构建前把 activeModule 设为它。"
                       % (module, pending["id"], pending["stage"]))
    elif stage == "MODULE_DONE" and paused:
        resume = paused[0]
        module_done = ("`%s` is done; resume paused module `%s` (%s). Set activeModule to it."
                       % (module, resume["id"], resume["stage"]))
    else:
        module_done = ("`%s` is done; next unfinished module in Build order is `%s` (%s). "
                       "Set activeModule to it before building." % (module, pending["id"], pending["stage"]))
    review_line, review_step, spec_review, plan_review = review_hint(root, module, stage, cmd, zh)
    if review_line and role_kind != "module":
        counts += "\n" + review_line
    tier_line = flow_tier_line(root, module, zh)
    if tier_line:
        counts += "\n" + tier_line
    external_line = (external_review_hint(root, module, stage, spec_review, plan_review, host, zh)
                     if role_kind != "module" else "")
    if external_line:
        counts += "\n" + external_line
    next_step = {
        "NEEDS_SPEC": "写 `spec/%s.md` 并交审。" % module,
        "NEEDS_DESIGN": doc_step(module, "NEEDS_DESIGN", True) + "。",
        "NEEDS_REGRESSION": doc_step(module, "NEEDS_REGRESSION", True) + "。",
        "NEEDS_PLAN": (doc_step(module, "NEEDS_PLAN", True) + "（例如用 %s）。Plan 写完即自动批准，不交审，接着用 %s 开始构建。" % (
            cmd["plan"], cmd["build"])) if _v2(root, module) else
        "写 `tasks/%s/plan.md` 和 `tasks/%s/todo.md`（例如用 %s）%s。" % (
            module, module, cmd["plan"], "；前提是用户已批准 Spec" if spec_review == "none" else ""),
        "BUILDING": "继续用 %s 构建 `%s`：`tasks/%s/todo.md` 里还有 %d 个未勾选项。" % (cmd["build"], module, module,
                                                                                     current["open"]),
        "MODULE_DONE": push_first + module_done,
    }[stage] if zh else {
        "NEEDS_SPEC": "write and review `spec/%s.md`." % module,
        # No marker says nothing about approval either way, so the suggestion names the condition.
        "NEEDS_DESIGN": doc_step(module, "NEEDS_DESIGN", False) + ".",
        "NEEDS_REGRESSION": doc_step(module, "NEEDS_REGRESSION", False) + ".",
        "NEEDS_PLAN": (doc_step(module, "NEEDS_PLAN", False) + " (for example with %s). The Plan is approved automatically "
                       "once written and is not reviewed; then start the build with %s." % (cmd["plan"], cmd["build"]))
        if _v2(root, module) else
        "create `tasks/%s/plan.md` and `tasks/%s/todo.md` (for example with %s)%s." % (
            module, module, cmd["plan"], " once the Spec is approved by the user" if spec_review == "none" else ""),
        "BUILDING": "continue %s on `%s`: %d unchecked item(s) in `tasks/%s/todo.md`." % (cmd["build"], module,
                                                                                         current["open"], module),
        "MODULE_DONE": push_first + module_done,
    }[stage]
    if stage == "BUILDING" and not review_step and role_kind == "coordinator":
        gate = next_gate(root, module)
        if gate:
            counts += (("\n- `%s` 的下一个 gate: %s — 由它的模块会话推进；到了在这里审。" if zh else
                        "\n- Next gate of `%s`: %s — the module session builds toward it; review it here when it arrives.")
                       % (module, gate))
    elif stage == "BUILDING" and not review_step and role_kind != "module":
        gate = next_gate(root, module)
        # A Plan with no marker may still be waiting for the user, so only an approved one is told to keep going.
        auto = plan_review == "approved" and codex_route(root, module, "plan") == "auto"  # plan-auto-approve
        if gate and auto and zh:
            counts += "\n- 下一个 gate: %s — Plan 已自动批准；一直做到它为止，`report` 检查点记进 todo 后直接通过，不停下。" % gate
        elif gate and auto:
            counts += ("\n- Next gate: %s — Plan approved automatically; keep going until it, a `report` checkpoint is "
                       "recorded in the todo and passed without stopping." % gate)
        elif gate and plan_review == "approved" and zh:
            counts += "\n- 下一个 gate: %s — 一直做到它为止；`report` 检查点记进 todo 后直接通过，不停下。" % gate
        elif gate and plan_review == "none" and zh:
            counts += ("\n- 下一个 gate: %s — todo 里第一个未勾选的 `gate` 检查点。Plan 没有批准标记：如果用户还没批准它，"
                       "先等批准再构建。" % gate)
        elif gate and plan_review == "approved":
            counts += ("\n- Next gate: %s — keep going until it; a `report` checkpoint is recorded in the todo "
                       "and passed without stopping." % gate)
        elif gate and plan_review == "none":
            counts += ("\n- Next gate: %s — the first unchecked `gate` checkpoint in the todo. The Plan has no review "
                       "marker: if the user has not approved it yet, wait for that approval before building." % gate)
    if not review_step and (stage == "NEEDS_SPEC" or (stage in ("NEEDS_DESIGN", "NEEDS_REGRESSION") and _v2(root, module))):
        next_step += sections_sentence(root, stage, zh)  # project-sections
    next_step = review_step or next_step
    if role_kind in ("module", "coordinator"):
        role_lines, next_step = role_view(root, role_kind, role_id, by_id, cmd, review_step, zh)
        notes = notes + role_lines
    # rules-at-nodes: a serial project at a node gets that node's stop rules; role views follow the collaboration plugin.
    node = stop_node(root, module, stage, spec_review, plan_review)
    if ms_line:
        counts += "\n" + ms_line
    if ms_step and role_kind not in ("module", "coordinator"):
        # milestone-stop: the stop comes before whatever the current module would do next.
        node, next_step = "milestone-stop", ms_step
    ac_fact, ac_step = acceptance_step(root, module, stage, cmd, zh)
    if ac_step and node == "final-gate" and role_kind not in ("module", "coordinator"):
        next_step = ac_step
    sc_fact, sc_line, sc_step = scope_overreach(root, module, stage, zh)
    if sc_line:
        counts += "\n" + sc_line
    if sc_step and not ms_step and not requirement_wait(root, module) and role_kind not in ("module", "coordinator"):
        # takeover-scope-check: a change outside the declared scope is a decision the Spec does not cover.
        node, next_step = "mid-gate", sc_step
    dg_fact, dg_line, dg_step = draft_gate(root, states, module, stage, zh)
    if dg_line:
        counts += "\n" + dg_line
    rg_fact, rg_line = regression_line(root, module, stage, zh)
    if rg_line:
        counts += "\n" + rg_line
    rl_fact, rl_line = risk_list_line(root, module, stage, zh)
    if rl_line:
        counts += "\n" + rl_line
    do_fact, do_line = design_outline_line(root, module, stage, zh)
    if do_line:
        counts += "\n" + do_line
    au_fact, au_line = author_line(root, module, stage, zh)
    if au_line:
        counts += "\n" + au_line
    vf_fact, vf_line = verification_line(root, module, stage, zh)
    if vf_line:
        counts += "\n" + vf_line
    if dg_step and not ms_step and role_kind not in ("module", "coordinator"):
        # usage-draft-gate: a multi-module batch reviews its usage draft before its first Spec.
        node, next_step = "map-review", dg_step
    if (node is None and not review_step and stage in ("NEEDS_REGRESSION", "NEEDS_PLAN", "BUILDING")
            and _v2(root, module) and role_kind not in ("module", "coordinator")):
        # sg-gate-flow (rule 24): the next steps run on without a stop, so the user hears what comes before it starts.
        next_step += (" 接着要连着做几步时，先用一句话告诉用户接下来做什么，再开始；这不是停点，不等回答。" if zh else
                      " Before going on through several steps, tell the user in one sentence what comes next, then "
                      "start; this is not a stop and needs no answer.")
    stop = stop_rules_block(node, zh) if role_kind not in ("module", "coordinator") else ""
    if node == "final-gate" and role_kind not in ("module", "coordinator") and documentation_baseline_present(root):
        notes = notes + [documentation_check_line(module, cmd, zh)]
    # review-residual-fixes (C4): the final gate's documentation-check line depends on the baseline, so its presence is a fact.
    rr_fact = requirement_review_fact(root, module)  # sg-review-rules: the confirmation step follows the review
    info.update(facts=[stage, module, spec_review, plan_review, node, zh, static_notes, role_facts, suspended_ids,
                       tuple(p["id"] for p in paused), bool(unmerged and unmerged[0] > 0),
                       documentation_baseline_present(root), project_sections(root), requirement_wait(root, module),
                       design_fact(root, module, stage) if module else None,
                       overall_wait(root, module) if module else None]
                      + ([rr_fact] if rr_fact else [])
                      + ([ms_fact] if ms_fact else [])
                      + ([dg_fact] if dg_fact else []) + ([sc_fact] if sc_fact else [])
                      + ([ac_fact] if ac_fact else []) + ([rg_fact] if rg_fact else [])
                      + ([rl_fact] if rl_fact else []) + ([do_fact] if do_fact else [])
                      + ([au_fact] if au_fact else []) + ([vf_fact] if vf_fact else []),
                stage=stage, module=module, open=current["open"], zh=zh)
    if zh:
        return ("当前阶段: **%s**\n\n- 能力图: 已有\n- 当前模块: `%s`（%s）\n%s\n%s\n建议下一步: %s%s"
                % (stage, module, "Build order 中下一个" if source == "next in Build order" else source, counts,
                   "".join(n + "\n" for n in notes), next_step, stop))
    return ("Current stage: **%s**\n\n- Capability map: present\n- Current module: `%s` (%s)\n%s\n%s"
            "\nSuggested next step: %s%s" % (stage, module, source, counts,
                                            "".join(n + "\n" for n in notes), next_step, stop))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--host", choices=["claude", "codex"])
    # phase-hint-gaps: IDLE and MAP_ONLY are answered by phase-guard.sh itself; it asks for the project-config lines
    # here so they come from the one implementation.
    parser.add_argument("--config-lines", action="store_true")
    parser.add_argument("--hint-language", action="store_true")
    parser.add_argument("--node-rules", metavar="KIND")  # rules-at-nodes: phase-guard.sh asks for IDLE / MAP_ONLY
    # quiet-injection: phase-guard.sh passes its own facts (location, linked project) to end the hint with the state
    # code; for IDLE / MAP_ONLY, which it answers itself, --state-key prints the code alone for --stage and --node.
    parser.add_argument("--state-extra")
    parser.add_argument("--last-state")
    parser.add_argument("--state-key", action="store_true")
    parser.add_argument("--stage")
    parser.add_argument("--node")
    args = parser.parse_args()
    if args.state_key:
        root = Path(args.root)
        zh = hint_language(root) == "zh-CN"
        code = state_key(args.stage, args.node, zh, tuple(config_lines(root, args.host)), args.state_extra or "")
        print(code)
        print(brief_line(root, args.stage, None, None, code, zh))  # phase-guard.sh gives it when the code is unchanged
        raise SystemExit(0)
    if args.node_rules is not None:
        sys.stdout.write(node_rules(args.node_rules))
        raise SystemExit(0)
    if args.hint_language:
        print(hint_language(Path(args.root)))
        raise SystemExit(0)
    if args.config_lines:
        print("\n".join(config_lines(Path(args.root), args.host)))
        raise SystemExit(0)
    print(describe(Path(args.root), args.host, args.state_extra, args.last_state))
