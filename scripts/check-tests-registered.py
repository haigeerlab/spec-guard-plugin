#!/usr/bin/env python3
"""每个测试文件都必须在运行器里被点名，否则没有任何检查会跑它。

背景（2026-10-13）：`scripts/validate.sh` 的回归段是一张手写的显式列表，没有通配、也不按
文件名发现。`test_module_suspend.py`、`test_project_config.py`、`test_state_paths.py` 随各自
模块加入时都忘了加那一行，于是五天里 CI、pre-push、verify-and-commit 一次也没跑过它们，
而且什么都不报错。

**判据的自我定位**（docs/lenses.md A3）：它问「CI 会不会跑这个文件」，所以
- 运行器只认 `scripts/validate.sh` 与 CI 工作流。`scripts/verify-and-commit.sh` 不算：它只在
  本机提交时运行，只改文档的提交还会跳过它的全套。
- 必须是相对仓库根的**完整路径**，出现在**非注释行**里，且前后不是文件名字符。只写文件名、
  被注释掉的步骤、只登记了同前缀的另一个文件，都算没登记 —— 把「名字出现过」当通过的版本
  会被这三种情况喂饱而永远绿。

它不问被点名的那一步是否真的会执行（例如写在永远不成立的分支里），也不问文件里的每个
用例是否都跑了（`run_tests_parallel.py` 自己核对用例数）。

按 docs/lenses.md A5：零个测试文件、或读不到任何运行器，是「没找到」，不是「没问题」，判失败。

usage: check-tests-registered.py [repo-root]
"""
from pathlib import Path
import os
import re
import sys

# 测试文件的发现范围（含子目录）。按文件系统查而不是 git ls-files：还没 git add 的新测试
# 正是最容易漏登记的时刻。
SEARCH_ROOTS = ("plugins", "scripts", "evals")
TEST_NAME = re.compile(r"^test[-_].*\.(py|sh)$")
SKIP_DIRS = ("__pycache__", "node_modules")

# 不查的两类，各有归属：
# 文件名含 acceptance 的测试需要固定的外部运行时，不该进 CI；check-acceptance-wired.py 要求
# 它们在运行器或维护者文档里有运行指引。
ACCEPTANCE_MARK = "acceptance"
# 一道评测题目的素材（种子项目、参考答案、隐藏测试），由评测脚本在临时目录里使用，不是本仓库的回归。
EXEMPT_DIRS = ("evals/dispatch-cost/",)

RUNNERS = ("scripts/validate.sh", ".github/workflows/*.yml", ".github/workflows/*.yaml")
# 路径前后若还是这些字符，就是另一个更长的路径，不算点名。
PATH_CHARS = r"[A-Za-z0-9_./-]"


def find_tests(root: Path) -> list:
    found = []
    for top in SEARCH_ROOTS:
        for current, dirs, files in os.walk(str(root / top)):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith(".")]
            for name in files:
                relative = (Path(current) / name).relative_to(root).as_posix()
                if (TEST_NAME.match(name) and ACCEPTANCE_MARK not in name
                        and not relative.startswith(EXEMPT_DIRS)):
                    found.append(relative)
    return sorted(found)


def runner_text(root: Path) -> str:
    """运行器里所有非注释行；一个运行器都读不到时返回空串。"""
    lines = []
    for pattern in RUNNERS:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                lines.extend(line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                             if not line.lstrip().startswith("#"))
    return "\n".join(lines)


def registered(relative: str, text: str) -> bool:
    return re.search("(?<!%s)%s(?!%s)" % (PATH_CHARS, re.escape(relative), PATH_CHARS), text) is not None


def main() -> int:
    # 可传入另一个仓库根（测试夹具用），默认检查本仓库。
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]

    tests = find_tests(root)
    if not tests:
        print("  ❌ %s 下 0 个 test_*／test-* 测试文件 —— 这是没找到，不是没问题" % "、".join(SEARCH_ROOTS),
              file=sys.stderr)
        return 1

    text = runner_text(root)
    if not text.strip():
        print("  ❌ 读不到任何运行器（scripts/validate.sh 或 .github/workflows/）—— 这是没找到，不是没问题",
              file=sys.stderr)
        return 1

    missing = [relative for relative in tests if not registered(relative, text)]
    if missing:
        print("  ❌ 下列测试文件没有在 scripts/validate.sh 或 CI 工作流里被点名，没有任何检查会跑它：",
              file=sys.stderr)
        for relative in missing:
            print("     - " + relative, file=sys.stderr)
        print("     在 scripts/validate.sh 的回归段按完整路径加一步（并行组里的测试不得共享状态）；"
              "若它需要外部运行时，按验收测试命名（文件名含 acceptance）并在"
              " docs/maintainer-workflow.md 写运行指引。", file=sys.stderr)
        return 1

    print("  ✅ %d 个测试文件都在 scripts/validate.sh 或 CI 工作流里被点名" % len(tests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
