#!/usr/bin/env python3
"""校验 plugins/spec-guard/interface.json 与代码一致（plugin-interface）。

interface.json 是给其他插件读的只读接口说明：接口版本、map-view 入口、JSON schemaVersion、退出码与取值含义。
这里只核对它与代码常量对得上，不运行 map_view。用法：check-interface.py [interface.json 路径]。
"""
import json
import re
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "plugins" / "spec-guard" / "hooks"
sys.path.insert(0, str(HOOKS))
import checkout_role  # noqa: E402
import map_view  # noqa: E402
import module_scope  # noqa: E402
import module_stage  # noqa: E402
import project_config  # noqa: E402

ENTRIES = ("moduleConcurrency", "scopeCheck", "checkoutRole", "reviewMark", "gateTick",
           "scopeOverlap", "declaredScope", "autonomyTier")  # crew-interface: 1.1; gate-tick: 1.7;
# scope-overlap-interface: 1.10; pre-declared-scope and autonomy-tier: 1.11
MAP_VIEW_KEYS = ("command", "schemaVersion", "contract", "exitCodes", "values")
# review-card-sections: interface 1.5; the session-protocol 【等待用户】「类型」 codes of the kinds spec-guard produces.
REVIEW_KINDS = ("capability-map", "spec", "plan", "spec-plan", "checkpoint", "final", "stuck")
COMMON_LINES = ("注意", "推荐理由", "批了会怎样")


def problems(path: Path) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return ["读不出 %s：%s" % (path, error)]
    found = []
    if not isinstance(data, dict) or not re.fullmatch(r"\d+\.\d+", str(data.get("interface", ""))):
        found.append("interface 必须是 <主>.<次> 形式的字符串")
    view = data.get("mapView") if isinstance(data, dict) else None
    if not isinstance(view, dict):
        return found + ["缺少 mapView"]
    if view.get("schemaVersion") != map_view.SCHEMA_VERSION:
        found.append("mapView.schemaVersion 为 %r，map_view.SCHEMA_VERSION 为 %r"
                     % (view.get("schemaVersion"), map_view.SCHEMA_VERSION))
    values = view.get("values") if isinstance(view.get("values"), dict) else {}
    for key, expected in (("review", module_stage.REVIEW_STATES),
                          ("externalReview", module_stage.EXTERNAL_REVIEW_STATES)):
        got = values.get(key)
        if not isinstance(got, dict) or set(got) != set(expected):
            found.append("mapView.values.%s 的取值为 %s，代码为 %s"
                         % (key, sorted(got) if isinstance(got, dict) else got, sorted(expected)))
    found += _scripts(path, "mapView.command", view.get("command"))
    return found + _progress_facts(view) + _concurrency(path, data, view) + _review_kinds(path, data)


def _progress_facts(view: dict) -> list:
    """map-progress-facts: interface 1.2 describes every progress fact and every reviewCadence value the code uses."""
    facts = view.get("progressFacts")
    if not isinstance(facts, dict):
        return ["mapView 缺少 progressFacts 说明"]
    found = []
    fields = facts.get("fields")
    if not isinstance(fields, dict) or set(fields) != set(map_view.PROGRESS_FIELDS):
        found.append("mapView.progressFacts.fields 为 %s，代码为 %s"
                     % (sorted(fields) if isinstance(fields, dict) else fields, sorted(map_view.PROGRESS_FIELDS)))
    cadence = (facts.get("values") or {}).get("reviewCadence") if isinstance(facts.get("values"), dict) else None
    if not isinstance(cadence, dict) or set(cadence) != set(project_config.CADENCES):
        found.append("mapView.progressFacts.values.reviewCadence 的取值为 %s，代码为 %s"
                     % (sorted(cadence) if isinstance(cadence, dict) else cadence, sorted(project_config.CADENCES)))
    return found


def _scripts(path: Path, label: str, command) -> list:
    scripts = [arg for arg in command if isinstance(arg, str) and arg.endswith(".py")] if isinstance(command, list) else []
    if not scripts:
        return ["%s 里没有脚本" % label]
    return ["%s 引用的 %s 不存在" % (label, script) for script in scripts if not (path.parent / script).is_file()]


def _concurrency(path: Path, data: dict, view: dict) -> list:
    """crew-interface: the 1.1 entries exist, name real scripts and list the values the code uses; 1.0 stays whole."""
    found = ["mapView 缺少 1.0 的 %s" % key for key in MAP_VIEW_KEYS if key not in view]
    if not isinstance(view.get("concurrency"), dict):
        found.append("mapView 缺少 concurrency 说明")
    missing = [key for key in ENTRIES if not isinstance(data.get(key), dict)]
    if missing:
        return found + ["缺少入口 %s" % key for key in missing]
    found += _scripts(path, "scopeCheck.command", data["scopeCheck"].get("command"))
    found += _scripts(path, "reviewMark.command", data["reviewMark"].get("command"))
    found += _scripts(path, "gateTick.command", data["gateTick"].get("command"))
    found += _scripts(path, "scopeOverlap.command", data["scopeOverlap"].get("command"))
    found += _scripts(path, "declaredScope.command", data["declaredScope"].get("command"))
    commands = data["checkoutRole"].get("commands")
    for name, command in (commands.items() if isinstance(commands, dict) and commands else [("commands", None)]):
        found += _scripts(path, "checkoutRole.commands.%s" % name, command)
    checks = (("scopeCheck.values.scope", data["scopeCheck"].get("values", {}).get("scope"), set(module_scope.SCOPES), None),
              ("checkoutRole.values.role", data["checkoutRole"].get("values", {}).get("role"), set(checkout_role.ROLE_KINDS),
               lambda key: key.split()[0]),
              ("moduleConcurrency.values", data["moduleConcurrency"].get("values"), set(project_config.CONCURRENCY), None),
              ("autonomyTier.values", data["autonomyTier"].get("values"), set(project_config.TIERS), None),
              ("scopeOverlap.values.error", data["scopeOverlap"].get("values", {}).get("error"),
               set(module_scope.OVERLAP_ERRORS), None),
              ("declaredScope.values.error", data["declaredScope"].get("values", {}).get("error"),
               set(module_scope.DECLARED_ERRORS), None))
    for label, got, expected, keyed in checks:
        names = {(keyed or (lambda key: key))(key) for key in got} if isinstance(got, dict) else None
        if names != expected:
            found.append("%s 的取值为 %s，代码为 %s" % (label, sorted(names) if names is not None else got, sorted(expected)))
    return found


def _review_kinds(path: Path, data: dict) -> list:
    """review-card-sections: exactly the seven kinds, and every section and common line is named in the shared rules."""
    block = data.get("reviewKinds")
    if not isinstance(block, dict):
        return ["缺少 reviewKinds"]
    kinds = block.get("kinds") if isinstance(block.get("kinds"), dict) else {}
    found = []
    if set(kinds) != set(REVIEW_KINDS):
        found.append("reviewKinds.kinds 的类别为 %s，应为 %s" % (sorted(kinds), sorted(REVIEW_KINDS)))
    rules = path.parent / str(block.get("rules", ""))
    try:
        text = rules.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return found + ["reviewKinds.rules 指向的 %s 读不出" % block.get("rules")]
    for code, kind in kinds.items():
        sections = kind.get("sections") if isinstance(kind, dict) else None
        if not isinstance(kind, dict) or not isinstance(kind.get("label"), str) or not isinstance(sections, list) or not sections:
            found.append("reviewKinds.kinds.%s 要有 label 与非空的 sections" % code)
            continue
        found += ["reviewKinds.kinds.%s 的小项「%s」在共享检查点规则里找不到" % (code, name)
                  for name in sections if not isinstance(name, str) or name not in text]
    combined = [kinds.get(code, {}).get("sections") if isinstance(kinds.get(code), dict) else None for code in ("spec", "plan")]
    if isinstance(kinds.get("spec-plan"), dict) and None not in combined \
            and kinds["spec-plan"].get("sections") != combined[0] + combined[1]:
        found.append("reviewKinds.kinds.spec-plan 的小项应为 spec 的小项再接 plan 的小项")
    lines = block.get("commonLines")
    if lines != list(COMMON_LINES):
        found.append("reviewKinds.commonLines 为 %s，应为 %s" % (lines, list(COMMON_LINES)))
    found += ["reviewKinds.commonLines 的「%s」在共享检查点规则里找不到" % name
              for name in COMMON_LINES if name not in text]
    return found


def main(argv: list) -> int:
    path = Path(argv[1]) if len(argv) > 1 else HOOKS.parent / "interface.json"
    found = problems(path)
    for item in found:
        print("  ❌ interface.json：" + item)
    if found:
        return 1
    print("  ✅ interface.json 与代码一致")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
