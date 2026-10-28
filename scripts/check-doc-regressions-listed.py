#!/usr/bin/env python3
"""读仓库自己文档的测试，必须列在 `scripts/validate.sh` 的快档清单 `DOC_REGRESSIONS` 里。

背景（2026-10-28，quick-tier-doc-regressions）：只改文档的提交走快档，pre-push 又认快档记录，
所以一串只改文档的提交从提交到推送都不跑回归。`test_hosted_ticket_entry.py` 锁住了
`docs/workflow.md` 的几处说法，user-docs-align 压缩那一节时把它们删了，几次快档提交都放行，
直到跑完整 validate 才发现。现在这类测试放进快档；本检查防止以后新加的同类测试漏列。

**判据的自我定位**（docs/lenses.md A3）：它问「这个测试是否从仓库根拼出了 docs/、README、CHANGELOG 的路径」。
- 只认从仓库根拼路径的写法：Python 里 `parents[N] / "docs…"`、`ROOT / "README…"` 这类，
  shell 里 `"$ROOT/docs/…"`、`"${ROOT}/README…"`。在临时目录里建 `docs/` 当夹具的测试不算。
- 写法认不出来的会漏报；这是有意的取舍（Spec 假设 2），不追求一网打尽。
- 清单条目要写在 `DOC_REGRESSIONS=(` … `)` 之间的非注释行里，按相对仓库根的完整路径对。
- `scripts/test-checkers.sh` 把坏样本当数据，不扫它。

按 docs/lenses.md A5：读不到清单是「没找到」，不是「没问题」，判失败。

usage: check-doc-regressions-listed.py [repo-root]
"""
from pathlib import Path
import re
import sys

TEST_GLOBS = ("plugins/spec-guard/hooks/test*", "scripts/test*")
SKIP = {"scripts/test-checkers.sh"}
PY_READS_REPO_DOC = re.compile(
    r"""(?:parents\[\d+\]|\bROOT|\bREPO(?:_ROOT)?)\s*/\s*['"](?:docs/|docs['"]|README|CHANGELOG)""")
SH_READS_REPO_DOC = re.compile(r"""\$\{?(?:ROOT|REPO|REPO_ROOT)\}?/(?:docs/|README|CHANGELOG)""")


def listed(root):
    """The test paths in validate.sh's DOC_REGRESSIONS array, or None when the array is missing."""
    try:
        text = (root / "scripts/validate.sh").read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^DOC_REGRESSIONS=\($(.*?)^\)", text, re.M | re.S)
    if not match:
        return None
    paths = set()
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.update(re.findall(r"(?:plugins|scripts)/\S+?\.(?:py|sh)\b", line))
    return paths


def reads_repo_doc(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    pattern = PY_READS_REPO_DOC if path.suffix == ".py" else SH_READS_REPO_DOC
    return any(pattern.search(line) for line in text.splitlines() if not line.lstrip().startswith("#"))


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    entries = listed(root)
    if entries is None:
        print("  ❌ 读不到 scripts/validate.sh 里的 DOC_REGRESSIONS 清单 —— 这是没找到，不是没问题", file=sys.stderr)
        return 1

    tests = sorted({p.relative_to(root).as_posix() for pattern in TEST_GLOBS for p in root.glob(pattern)
                    if p.is_file() and p.suffix in (".py", ".sh")} - SKIP)
    readers = [relative for relative in tests if reads_repo_doc(root / relative)]
    missing = [relative for relative in readers if relative not in entries]
    if missing:
        print("  ❌ 下列测试读仓库自己的文档，却没列进 scripts/validate.sh 的 DOC_REGRESSIONS，"
              "只改文档的提交与推送不会跑它：", file=sys.stderr)
        for relative in missing:
            print("     - " + relative, file=sys.stderr)
        print("     把它加进 DOC_REGRESSIONS（并从全套回归段删掉那一行，免得跑两遍）。", file=sys.stderr)
        return 1

    print("  ✅ %d 个读仓库文档的测试都在快档清单 DOC_REGRESSIONS 里" % len(readers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
