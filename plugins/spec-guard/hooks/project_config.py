"""Read, check and set the project configuration in `.agent/config.json`.

This is the only parser of that file: the phase hint, verify-artifacts and the config
command all call `load`.  A missing file means "nothing configured" and changes no
behaviour.  Anything else that is not a valid document is reported, never read as the
defaults, so a typo can never look like a setting that took effect.

`.agent/config.json` is repository content and the phase hint injects what this module
reports into an agent's context.  So problems are a fixed vocabulary of codes: no key
name, value or parse error from the file is ever echoed.  Reading reuses
`tracker_default.read_text` (no symlink following, bounded size) and writing reuses its
atomic writer.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from tracker_default import _write_atomic, read_default, read_text

RELATIVE_PATH = Path(".agent") / "config.json"
VERSION = 1
LANGUAGE_TAG = re.compile(r"[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?\Z")
CADENCES = ("separate", "combined")
DEFAULTS = {"reviewCadence": "separate"}
VALIDATORS = {
    "artifactLanguage": lambda value: isinstance(value, str) and bool(LANGUAGE_TAG.fullmatch(value)),
    "reviewCadence": lambda value: value in CADENCES,
}
OWNED_ELSEWHERE = {
    "dispatch": "/spec-guard:setup-convention --replace --dispatch (or --no-dispatch)",
    "trackerDefault": "/spec-guard:tracker-default",
}
BLOCKS = (("CLAUDE.md", "<!-- BEGIN:agent-skills-convention -->", "<!-- END:agent-skills-convention -->"),
          ("AGENTS.md", "<!-- BEGIN:spec-guard-codex-convention -->",
           "<!-- END:spec-guard-codex-convention -->"))
DISPATCH_MARKER = "<!-- spec-guard: build-task-dispatch -->"


def load(root: Path) -> tuple[dict[str, Any], list[str]]:
    """(values, problems).  Any problem empties `values`: a half-valid file is not applied."""
    text, state = read_text(Path(root) / RELATIVE_PATH)
    if state == "absent":
        return {}, []
    if text is None:
        return {}, ["unreadable"]
    try:
        document = json.loads(text)
    except ValueError:
        return {}, ["not-json"]
    if not isinstance(document, dict):
        return {}, ["not-an-object"]
    problems = []
    version = document.get("version")
    if isinstance(version, bool) or version != VERSION:
        problems.append("version-invalid")
    if set(document) - {"version"} - set(VALIDATORS):
        problems.append("unknown-key")
    for key, valid in VALIDATORS.items():
        if key in document and not valid(document[key]):
            problems.append(key + "-invalid")
    if problems:
        return {}, problems
    return {key: document[key] for key in VALIDATORS if key in document}, []


def _dispatch(root: Path) -> dict[str, str]:
    """`on`/`off` per convention block present; the marker line is the switch."""
    found = {}
    for name, begin, end in BLOCKS:
        text, _ = read_text(Path(root) / name)
        if text is None:
            continue
        lines = [line.strip() for line in text.splitlines()]
        if begin not in lines or end not in lines or lines.index(begin) > lines.index(end):
            continue
        block = lines[lines.index(begin) + 1:lines.index(end)]
        found[name] = "on" if DISPATCH_MARKER in block else "off"
    return found


def summary(root: Path) -> list[dict[str, Any]]:
    """Every configurable item with its effective value and where that value comes from."""
    values, problems = load(root)
    items = []
    for key in VALIDATORS:
        if key in values:
            value, source = values[key], str(RELATIVE_PATH)
        else:
            value, source = DEFAULTS.get(key, "unset"), "default"
        items.append({"key": key, "value": value, "source": source,
                      "editWith": "/spec-guard:config"})
    tracker = read_default(root)
    items.append({"key": "dispatch", "value": _dispatch(root), "source": "convention block",
                  "editWith": OWNED_ELSEWHERE["dispatch"]})
    items.append({"key": "trackerDefault",
                  "value": tracker.backend if tracker.state == "configured" else tracker.state,
                  "source": ".agent/tracker.json", "editWith": OWNED_ELSEWHERE["trackerDefault"]})
    if problems:
        for item in items[:len(VALIDATORS)]:
            item["source"] = "default (config invalid)"
    return items


def _ignored(root: Path) -> bool:
    done = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(RELATIVE_PATH)],
                          capture_output=True, check=False)
    return done.returncode == 0


def render(values: dict[str, Any]) -> str:
    """Canonical text, so rewriting the same values is a no-op diff."""
    document = {"version": VERSION, **{key: values[key] for key in VALIDATORS if key in values}}
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def _show(root: Path, as_json: bool) -> int:
    values, problems = load(root)
    items = summary(root)
    ignored = (root / RELATIVE_PATH).exists() and _ignored(root)
    if as_json:
        print(json.dumps({"items": items, "problems": problems, "gitignored": ignored},
                         ensure_ascii=False, sort_keys=True))
        return 0
    for item in items:
        value = item["value"]
        if isinstance(value, dict):
            value = ", ".join("%s=%s" % pair for pair in sorted(value.items())) or "no convention block"
        print("%-16s %-24s source: %-26s edit: %s" % (item["key"], value, item["source"], item["editWith"]))
    if problems:
        print("\n%s is invalid (%s); its items fall back to defaults until it is fixed."
              % (RELATIVE_PATH, ", ".join(problems)))
    if ignored:
        print("\nwarning: %s is matched by .gitignore, so the team does not share this configuration."
              % RELATIVE_PATH)
    return 0


def _change(root: Path, key: str, value: str | None, confirm: bool) -> int:
    if key in OWNED_ELSEWHERE:
        print("%s is not stored in %s; change it with %s" % (key, RELATIVE_PATH, OWNED_ELSEWHERE[key]))
        return 2
    if key not in VALIDATORS:
        print("unknown-key: configurable keys are %s" % ", ".join(VALIDATORS))
        return 2
    if value is not None and not VALIDATORS[key](value):
        print("%s-invalid: see spec/project-config.md for the accepted values" % key)
        return 2
    values, problems = load(root)
    if problems:
        print("%s is invalid (%s); fix or remove it before changing settings" % (RELATIVE_PATH, ", ".join(problems)))
        return 2
    directory = root / RELATIVE_PATH.parent
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        print("agent-directory-unsafe: %s is not a directory in this project" % RELATIVE_PATH.parent)
        return 2
    path = root / RELATIVE_PATH
    before = render(values) if path.exists() else ""
    updated = dict(values)
    if value is None:
        updated.pop(key, None)
    else:
        updated[key] = value
    after = render(updated)
    diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                        fromfile=str(RELATIVE_PATH) + " (current)",
                                        tofile=str(RELATIVE_PATH) + " (proposed)"))
    print(diff if diff else "no change: %s already has this value" % RELATIVE_PATH)
    if not confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    try:
        directory.mkdir(exist_ok=True)
        _write_atomic(path, after)
    except OSError:
        print("config-unwritable: %s could not be written" % RELATIVE_PATH)
        return 2
    if load(root) != (updated, []):
        print("config-readback-mismatch: %s does not read back as written" % RELATIVE_PATH)
        return 2
    print("\nwrote %s" % RELATIVE_PATH)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Show, check or set the spec-guard project configuration.")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="read-only summary of every item and its source")
    show.add_argument("--format", choices=("text", "json"), default="text")
    commands.add_parser("check", help="exit 1 when the configuration file is invalid")
    setter = commands.add_parser("set", help="preview, and with --confirm write")
    setter.add_argument("--key", required=True)
    setter.add_argument("--value", required=True)
    setter.add_argument("--confirm", action="store_true")
    unsetter = commands.add_parser("unset", help="preview, and with --confirm remove one key")
    unsetter.add_argument("--key", required=True)
    unsetter.add_argument("--confirm", action="store_true")
    for sub in (show, commands.choices["check"], setter, unsetter):
        sub.add_argument("--project", default=".")
    args = parser.parse_args()
    root = Path(args.project)
    if args.command == "show":
        return _show(root, args.format == "json")
    if args.command == "check":
        _, problems = load(root)
        if problems:
            print("%s is invalid: %s" % (RELATIVE_PATH, ", ".join(problems)))
            return 1
        print("ok")
        return 0
    return _change(root, args.key, getattr(args, "value", None), args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
