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
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from state_paths import ENV as STATE_ENV, legacy_in_use, state_root
from tracker_default import _write_atomic, read_default, read_text

RELATIVE_PATH = Path(".agent") / "config.json"
VERSION = 1
LANGUAGE_TAG = re.compile(r"[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?\Z")
CADENCES = ("separate", "combined")
CONCURRENCY = ("off", "on")
# autonomy-tier: what each tier allows is defined by module-crew; spec-guard only stores, reads and reports it.
TIERS = ("strict", "standard", "relaxed")
# config-per-key: a file with one of these problems is unusable as a whole; every other problem
# belongs to one key and leaves the rest of the file in effect.
STRUCTURAL = ("unreadable", "not-json", "not-an-object", "version-invalid")
DEFAULTS = {"reviewCadence": "separate", "moduleConcurrency": "off", "autonomyTier": "strict"}
VALIDATORS = {
    "artifactLanguage": lambda value: isinstance(value, str) and bool(LANGUAGE_TAG.fullmatch(value)),
    "reviewCadence": lambda value: value in CADENCES,
    "moduleConcurrency": lambda value: value in CONCURRENCY,
    "autonomyTier": lambda value: value in TIERS,
}
OWNED_ELSEWHERE = {
    "trackerDefault": "/spec-guard:tracker-default",
}


def load(root: Path) -> tuple[dict[str, Any], list[str]]:
    """(values, problems).  A STRUCTURAL problem empties `values`; any other problem drops only its key."""
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
    version = document.get("version")
    if isinstance(version, bool) or version != VERSION:
        return {}, ["version-invalid"]
    problems = ["unknown-key"] if set(document) - {"version"} - set(VALIDATORS) else []
    values = {}
    for key, valid in VALIDATORS.items():
        if key in document:
            if valid(document[key]):
                values[key] = document[key]
            else:
                problems.append(key + "-invalid")
    return values, problems


def module_concurrency(root: Path) -> bool:
    """module-concurrency-switch: the only reader of the switch.  Unset, `off`, an invalid value or file is off."""
    return load(root)[0].get("moduleConcurrency") == "on"


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
    items.append({"key": "trackerDefault",
                  "value": tracker.backend if tracker.state == "configured" else tracker.state,
                  "source": ".agent/tracker.json", "editWith": OWNED_ELSEWHERE["trackerDefault"]})
    for item in items[:len(VALIDATORS)]:
        if (set(problems) & set(STRUCTURAL)) or item["key"] + "-invalid" in problems:
            item["source"] = "default (config invalid)"
    return items


def _ignored(root: Path) -> bool:
    done = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(RELATIVE_PATH)],
                          capture_output=True, check=False)
    return done.returncode == 0


def render(values: dict[str, Any], rest: dict[str, Any] | None = None) -> str:
    """Canonical text, so rewriting the same values is a no-op diff.

    config-per-key: `rest` holds the file's other keys (unknown keys, invalid values) in file order; they
    are written back unchanged after the valid known keys, so a write never drops what it did not set.
    """
    document = {"version": VERSION, **{key: values[key] for key in VALIDATORS if key in values}, **(rest or {})}
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def _rest(root: Path, values: dict[str, Any]) -> dict[str, Any]:
    """The keys `load` did not return, in file order; only called when the file has no STRUCTURAL problem."""
    text, _ = read_text(Path(root) / RELATIVE_PATH)
    document = json.loads(text) if text is not None else {}
    return {key: value for key, value in document.items() if key != "version" and key not in values}


def _structural(problems: list[str]) -> bool:
    return bool(set(problems) & set(STRUCTURAL))


def _show(root: Path, as_json: bool) -> int:
    values, problems = load(root)
    items = summary(root)
    ignored = (root / RELATIVE_PATH).exists() and _ignored(root)
    if as_json:
        print(json.dumps({"items": items, "problems": problems, "gitignored": ignored},
                         ensure_ascii=False, sort_keys=True))
        return 0
    for item in items:
        print("%-16s %-24s source: %-26s edit: %s" % (item["key"], item["value"], item["source"], item["editWith"]))
    if _structural(problems):
        print("\n%s is invalid (%s); its items fall back to defaults until it is fixed."
              % (RELATIVE_PATH, ", ".join(problems)))
    elif problems:
        print("\n%s: %s ignored; the other settings apply." % (RELATIVE_PATH, ", ".join(problems)))
    if ignored:
        print("\nwarning: %s is matched by .gitignore, so the team does not share this configuration."
              % RELATIVE_PATH)
    # runtime-state-layout: facts only; nothing here suggests deleting a directory that holds records.
    print("\nmachine state: %s%s" % (state_root(), " (from %s)" % STATE_ENV if os.environ.get(STATE_ENV) else ""))
    for legacy in legacy_in_use():
        print("legacy directory still read: %s (until %s exists)" % (legacy, state_root() / legacy.name))
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
    if _structural(problems):
        print("%s is invalid (%s); fix or remove it before changing settings" % (RELATIVE_PATH, ", ".join(problems)))
        return 2
    directory = root / RELATIVE_PATH.parent
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        print("agent-directory-unsafe: %s is not a directory in this project" % RELATIVE_PATH.parent)
        return 2
    path = root / RELATIVE_PATH
    rest = _rest(root, values) if path.exists() else {}
    before = render(values, rest) if path.exists() else ""
    rest.pop(key, None)
    updated = dict(values)
    if value is None:
        updated.pop(key, None)
    else:
        updated[key] = value
    after = render(updated, rest)
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
    if load(root)[0] != updated or _rest(root, updated) != rest:
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
        if problems == ["unknown-key"]:
            # config-per-key: most likely a key from a newer spec-guard; it is ignored, not an error.
            print("ok (ignored: unknown-key)")
            return 0
        if problems:
            print("%s is invalid: %s" % (RELATIVE_PATH, ", ".join(problems)))
            return 1
        print("ok")
        return 0
    return _change(root, args.key, getattr(args, "value", None), args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
