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
import map_view  # noqa: E402
import module_stage  # noqa: E402


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
    command = view.get("command")
    scripts = [arg for arg in command if isinstance(arg, str) and arg.endswith(".py")] if isinstance(command, list) else []
    if not scripts:
        found.append("mapView.command 里没有脚本")
    for script in scripts:
        if not (path.parent / script).is_file():
            found.append("mapView.command 引用的 %s 不存在" % script)
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
