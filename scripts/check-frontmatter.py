#!/usr/bin/env python3
"""Check the YAML frontmatter of every plugin skill, agent and command (plugin development rule C7).

Usage: check-frontmatter.py [repo root]   (default: the repository this script lives in)

`claude plugin validate` does not check that the frontmatter parses as YAML, so this script does, with PyYAML:
skills (plugins/*/skills/*/SKILL.md) and agents (plugins/*/agents/*.md) need a non-empty `name` and `description`;
commands (plugins/*/commands/*.md) need a non-empty `description` -- their name is the file name.
Exit 0 when every file passes, 1 with one `path: reason` line per problem, 2 when PyYAML is missing.
"""
from __future__ import annotations

from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print("check-frontmatter: PyYAML is not installed (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

KINDS = (("plugins/*/skills/*/SKILL.md", ("name", "description")),
         ("plugins/*/agents/*.md", ("name", "description")),
         ("plugins/*/commands/*.md", ("description",)))


def frontmatter(text: str):
    """The parsed frontmatter mapping, or a reason string when there is none or it does not parse."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "no frontmatter (the file must start with ---)"
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return "frontmatter is not closed with ---"
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        return "frontmatter is not valid YAML%s" % (" (line %d)" % (mark.line + 2) if mark else "")
    if not isinstance(data, dict):
        return "frontmatter is not a mapping"
    return data


def problems(root: Path) -> tuple:
    found, checked = [], 0
    for pattern, required in KINDS:
        for path in sorted(root.glob(pattern)):
            checked += 1
            relative = path.relative_to(root).as_posix()
            try:
                data = frontmatter(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as error:
                found.append("%s: unreadable (%s)" % (relative, error.__class__.__name__))
                continue
            if isinstance(data, str):
                found.append("%s: %s" % (relative, data))
                continue
            for field in required:
                value = data.get(field)
                if not isinstance(value, str) or not value.strip():
                    found.append("%s: missing or empty `%s`" % (relative, field))
    return found, checked


def main(argv: list) -> int:
    root = Path(argv[0]).resolve() if argv else Path(__file__).resolve().parent.parent
    found, checked = problems(root)
    for line in found:
        print("  ❌ " + line)
    if found:
        return 1
    print("  ✅ frontmatter: %d skill/agent/command file(s) parse as YAML and carry the required fields" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
