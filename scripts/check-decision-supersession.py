#!/usr/bin/env python3
"""被取代的决策必须在自己的状态行里说出来，并指回取代它的那一份。

背景（2026-10-05）：`docs/decisions/2026-10-04-native-only-collaboration-sunset.md`
取代了 `2026-09-28-xats-sunset.md` 与 `2026-10-04-a10-single-mac-promotion-gate.md`，
但两份旧决策的状态行仍分别写着「尚未触发，XATS 仍是默认传输」和「其余条款继续有效」，
都没有指向取代它们的那一份。XATS 的产品面早在 v0.40.0 就删掉了；搜 "XATS" 的人第一眼
读到的却是一个已经不成立的现在时事实（docs/lenses.md D1：两个真相源各自自洽地发散）。

本仓库已有一对做对了的先例：`2026-09-28-single-capability-map.md` 写「取代同日的 …」，
`2026-09-28-initiative-rollover.md` 的状态行写「已被取代（…），见 …。本文件保留原方案
作为记录」。这条判据把那个先例变成可执行的约束 —— 规矩写在文档里不会生效，校验器才会
（docs/lenses.md A2b）。

判据故意只要求两件可机械判定的事：**指回去**和**状态行承认**。它不读正文、不判断
取代范围是全部还是部分条款，因为
`2026-10-04-native-only-collaboration-sunset.md` 明确要求旧决策保留原文、
「不能被改写成当时已经满足」—— 把旧正文改成已达标正是它禁止的事。

按 docs/lenses.md A5：零个决策文件、或零条取代声明，都是「没找到」，不是「没问题」；
旧决策不会重新变成未被取代，声明消失只说明那段话被改没了。

已知边界：判据按空行切块，把任何含「取代」的块里的决策链接都算成该块的取代声明。所以一句
「取代」不要和无关的决策链接挤在同一块里，否则会多出一对（只会多要求一次互链，不会漏判）。

usage: check-decision-supersession.py [repo-root]
"""
from pathlib import Path
import re
import sys

DECISIONS = "docs/decisions"
LINK = re.compile(r"\]\(\.?/?([^)\s]+\.md)\)")


def _blocks(text):
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def _status_block(text):
    # 本仓库的决策文件都以独立一段的「状态：…」开头。只认段首，不认正文里顺口提到的
    # 「状态」—— 否则一句「本文件没有状态行」就会被当成存在状态行。
    for block in _blocks(text):
        if block.startswith("状态"):
            return block
    return None


def main() -> int:
    # 可传入另一个仓库根（回归夹具用），默认检查本仓库。
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    folder = root / DECISIONS

    docs = sorted(path for path in folder.glob("*.md") if path.is_file()) if folder.is_dir() else []
    if not docs:
        print("  ❌ %s 下 0 个决策文件 —— 这是没找到，不是没问题" % DECISIONS, file=sys.stderr)
        return 1

    text = {path.name: path.read_text(encoding="utf-8", errors="replace") for path in docs}
    names = set(text)

    # (被取代者, 取代者)。两种写法都收：A 说「取代 B」，和 B 说「已被取代，见 A」。
    pairs = set()
    for name, body in text.items():
        for block in _blocks(body):
            if "取代" not in block:
                continue
            targets = [target for target in LINK.findall(block)
                       if Path(target).name in names and Path(target).name != name]
            for target in targets:
                target = Path(target).name
                if "已被取代" in block:
                    pairs.add((name, target))
                else:
                    pairs.add((target, name))

    if not pairs:
        print("  ❌ 0 条取代声明 —— 本仓库有被取代的决策，这是声明丢了，不是没问题",
              file=sys.stderr)
        return 1

    problems = []
    for old, new in sorted(pairs):
        if new not in LINK.findall(text[old]):
            problems.append("%s 没有指回取代它的 %s" % (old, new))
        status = _status_block(text[old])
        if status is None:
            problems.append("%s 没有状态行，无法声明它已被取代" % old)
        elif "已被取代" not in status:
            problems.append("%s 的状态行没有说明它已被取代（仍会被当成生效中）" % old)
        if old not in LINK.findall(text[new]):
            problems.append("%s 声明取代了 %s，却没有链接到它" % (new, old))

    if problems:
        print("  ❌ 被取代的决策必须自称已被取代并与取代者互相链接：", file=sys.stderr)
        for problem in problems:
            print("     - " + problem, file=sys.stderr)
        print("     参照 %s/2026-09-28-initiative-rollover.md 的状态行写法；"
              "不要改写旧正文去迎合新结论。" % DECISIONS, file=sys.stderr)
        return 1

    print("  ✅ %d 条取代声明都双向成立，被取代者的状态行都已承认" % len(pairs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
