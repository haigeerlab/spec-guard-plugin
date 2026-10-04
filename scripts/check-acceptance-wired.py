#!/usr/bin/env python3
"""每个可选验收测试都必须有一处告诉维护者何时、怎么跑它。

背景（2026-10-05 项目审计）：`plugins/spec-guard/hooks/test*acceptance*` 需要固定的
外部运行时（`SPEC_GUARD_EPIQ_RUNTIME`），所以它们**不该**进 `validate.sh` 或 CI ——
不在那里跑是对的。真正的洞是没有任何运行器或维护者文档提到它们，于是
`test_proposal_closeout_local_acceptance.py` 在全仓库零引用的状态下存在，而
`plugins/spec-guard/references/proposal-closeout.md` 正以「对固定的 epiq@1.11.0 实测
得出」的口气断言只有它能证明的那几个参数名。假传输测试会一直全绿，Epiq 改名时
写入路径静默失效 —— 与 v0.41.0 修掉的 GitHub `state` 大小写事故同形。

**判据的自我定位**（docs/lenses.md A3）：它问「有没有东西告诉下一个维护者跑它」，
不问「它是否在 CI 里跑」。所以接受的引用位置是运行器**或**维护者文档，不接受
`docs/reports/`、`CHANGELOG.md` 这类历史证据 —— 一次已发生的运行记录不是下一次的
运行指引。两个账本验收测试此前恰好只被 `docs/reports/2026-10-03-*.md` 提到；若把
任意引用都算通过，这条判据会被历史材料喂饱而永远绿，正是 A3 说的「太宽」。

按 docs/lenses.md A5：零个验收测试文件是「没找到」，不是「没问题」，判失败。

usage: check-acceptance-wired.py [repo-root]
"""
from pathlib import Path
import sys

# 验收测试的发现范围。两种命名都查，避免判据盖不住最典型的那个位置。
TEST_GLOBS = ("plugins/spec-guard/hooks/test*acceptance*.py",
              "plugins/spec-guard/hooks/test*acceptance*.sh")

# 可接受的引用位置：运行器，或面向维护者的工作流文档。
RUNNERS = ("scripts/validate.sh", ".github/workflows/*.yml", ".github/workflows/*.yaml")
WORKFLOW_DOCS = ("docs/maintainer-workflow.md", "docs/release-process.md",
                 "CONTRIBUTING.md", "CLAUDE.md")


def _sources(root: Path) -> list:
    found = []
    for pattern in RUNNERS:
        found.extend(sorted(root.glob(pattern)))
    for relative in WORKFLOW_DOCS:
        path = root / relative
        if path.is_file():
            found.append(path)
    return found


def main() -> int:
    # 可传入另一个仓库根（测试夹具用），默认检查本仓库。
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]

    tests = sorted({path for pattern in TEST_GLOBS for path in root.glob(pattern)
                    if path.is_file()})
    if not tests:
        print("  ❌ 0 个 plugins/spec-guard/hooks/test*acceptance* —— 这是没找到，不是没问题",
              file=sys.stderr)
        return 1

    sources = _sources(root)
    if not sources:
        print("  ❌ 读不到任何运行器或维护者文档 —— 这是没找到，不是没问题", file=sys.stderr)
        return 1
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in sources)

    orphans = [path.name for path in tests if path.name not in text]
    if orphans:
        print("  ❌ 下列验收测试没有任何运行器或维护者文档说明怎么跑，"
              "等于没有人会再跑它：", file=sys.stderr)
        for name in orphans:
            print("     - plugins/spec-guard/hooks/" + name, file=sys.stderr)
        print("     在 docs/maintainer-workflow.md 的验证矩阵里补一行（含所需的"
              " SPEC_GUARD_EPIQ_RUNTIME），或接进某个运行器。", file=sys.stderr)
        return 1

    print("  ✅ %d 个验收测试都有运行器或维护者文档的运行指引" % len(tests))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
