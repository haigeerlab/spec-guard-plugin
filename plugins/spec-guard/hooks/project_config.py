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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from capability_map import MODULE_ID
from state_paths import ENV as STATE_ENV, legacy_in_use, state_root
from tracker_default import _write_atomic, read_default, read_text

RELATIVE_PATH = Path(".agent") / "config.json"
VERSION = 1
LANGUAGE_TAG = re.compile(r"[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?\Z")
CADENCES = ("separate", "combined")
CONCURRENCY = ("off", "on")
# autonomy-tier: what each tier allows is defined by module-crew; spec-guard only stores, reads and reports it.
TIERS = ("strict", "standard", "relaxed")
# takeover-config: who does each step, from strictest to widest.  A preset expands to all four items; a custom
# object may omit items, which read as human.  Callers (autopilot, module-crew) act on it; spec-guard only stores it.
ITEMS = {"spec": ("human", "codex"), "plan": ("human", "codex"), "merge": ("human", "auto"),
         "release": ("human", "prepare", "auto-confirm", "auto")}
HUMAN = {item: values[0] for item, values in ITEMS.items()}
PRESETS = {"none": dict(HUMAN), "plan": dict(HUMAN, plan="codex"),
           "merge": dict(HUMAN, spec="codex", plan="codex", merge="auto")}
# Q14 and 8.4 of the S101 plan: spec-guard stores these release values and only hints at the limits; autopilot enforces them.
RELEASE_LIMITS = ("note: the four pipeline plugins (spec-guard, module-crew, delegate, agent-relay) release at most at prepare",
                  "note: release=auto is only for projects that can roll back quickly; autopilot enforces both limits")
# config-per-key: a file with one of these problems is unusable as a whole; every other problem
# belongs to one key and leaves the rest of the file in effect.
STRUCTURAL = ("unreadable", "not-json", "not-an-object", "version-invalid")
DEFAULTS = {"reviewCadence": "separate", "moduleConcurrency": "off", "takeover": "none", "moduleTakeover": {},
            "takeoverNarrowed": {}}


def valid_takeover(value: Any) -> bool:
    if isinstance(value, str):
        return value in PRESETS
    return isinstance(value, dict) and all(
        isinstance(item, str) and item in ITEMS and value[item] in ITEMS[item] for item in value)


def expand(value: Any) -> dict[str, str]:
    """A valid takeover value as all four items."""
    return dict(PRESETS[value]) if isinstance(value, str) else dict(HUMAN, **value)


def takeover_wider(items: dict[str, str], than: dict[str, str]) -> bool:
    return any(ITEMS[item].index(items[item]) > ITEMS[item].index(than[item]) for item in ITEMS)


# takeover-narrow: the order a step is taken back in (Q7, r3 Q13).  A preset steps down the preset ladder; a custom
# value hands back its outermost non-human item, release first; release goes straight back to human.
PRESET_LADDER = ("none", "plan", "merge")
NARROW_ORDER = ("release", "merge", "plan", "spec")
SOURCES = ("autopilot", "module-crew", "user")
REASON_MAX = 200
SCOPE_PROJECT = "project"
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


def narrow_step(value: Any) -> Any:
    """The value one step stricter, or None when it is already the strictest."""
    if isinstance(value, str):
        index = PRESET_LADDER.index(value)
        return PRESET_LADDER[index - 1] if index else None
    items = expand(value)
    for item in NARROW_ORDER:
        if items[item] != "human":
            items[item] = "human"
            custom = {key: items[key] for key in ITEMS if items[key] != "human"}
            return custom or "none"
    return None


def narrower_or_equal(value: Any, than: Any) -> bool:
    return not takeover_wider(expand(value), expand(than))


def widen_steps(before: Any, after: Any) -> int:
    """How many narrow steps take `after` back to no wider than `before`; 0 when it is not wider."""
    steps, value = 0, after
    while not narrower_or_equal(value, before):
        value, steps = narrow_step(value), steps + 1
    return steps


def valid_reason(reason: Any) -> bool:
    return (isinstance(reason, str) and 0 < len(reason) <= REASON_MAX and reason.isprintable()
            and "\n" not in reason)


def valid_narrowed(value: Any) -> bool:
    """takeoverNarrowed: scope (project or a module id) -> {from, to, source, reason, at}."""
    return isinstance(value, dict) and all(
        isinstance(scope, str) and (scope == SCOPE_PROJECT or MODULE_ID.fullmatch(scope))
        and isinstance(record, dict) and set(record) == {"from", "to", "source", "reason", "at"}
        and valid_takeover(record["from"]) and valid_takeover(record["to"]) and record["source"] in SOURCES
        and valid_reason(record["reason"]) and isinstance(record["at"], str) and bool(STAMP.fullmatch(record["at"]))
        for scope, record in value.items())
VALIDATORS = {
    "artifactLanguage": lambda value: isinstance(value, str) and bool(LANGUAGE_TAG.fullmatch(value)),
    "reviewCadence": lambda value: value in CADENCES,
    "moduleConcurrency": lambda value: value in CONCURRENCY,
    "takeover": valid_takeover,
    # takeover-config: module id -> takeover value; the whole key is invalid when any entry is.
    "moduleTakeover": lambda value: isinstance(value, dict) and all(
        isinstance(key, str) and MODULE_ID.fullmatch(key) and valid_takeover(value[key]) for key in value),
    # takeover-narrow: written only by narrow (and kept in step by set); config cannot set or unset it.
    "takeoverNarrowed": valid_narrowed,
}
MANAGED = ("takeoverNarrowed",)
# takeover-config: retired keys (S101, "autonomyTier 退役吧"), not mapped to takeover.  A file that still has them is
# valid (problem "retired-key"), keeps them on writes and can unset them; they cannot be set.  Only module_tier reads
# them, for /map's deprecated autonomy field.
RETIRED = {
    "autonomyTier": lambda value: value in TIERS,
    "moduleAutonomy": lambda value: isinstance(value, dict) and all(
        isinstance(key, str) and MODULE_ID.fullmatch(key) and value[key] in TIERS for key in value),
}
# Problems that leave the file in effect and do not fail `check`.
IGNORED = ("unknown-key", "retired-key")
# Per-module keys and what each entry must satisfy.
ENTRY_VALID = {"moduleTakeover": valid_takeover}
# Keys whose value is written one entry at a time with --module.
PER_MODULE = ("moduleTakeover",)
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
    problems = ["unknown-key"] if set(document) - {"version"} - set(VALIDATORS) - set(RETIRED) else []
    if set(document) & set(RETIRED):
        problems.append("retired-key")
    values = {}
    for key, valid in VALIDATORS.items():
        if key in document:
            if valid(document[key]):
                values[key] = document[key]
            else:
                problems.append(key + "-invalid")
    return values, problems


def _legacy(root: Path) -> tuple[dict[str, Any], list[str]]:
    """The retired keys as they were read before takeover-config: (valid values, ["<key>-invalid", ...] or structural)."""
    values, problems = load(root)
    if _structural(problems):
        return {}, problems
    text, _ = read_text(Path(root) / RELATIVE_PATH)
    document = json.loads(text) if text is not None else {}
    legacy, invalid = {}, []
    for key, valid in RETIRED.items():
        if key in document:
            if valid(document[key]):
                legacy[key] = document[key]
            else:
                invalid.append(key + "-invalid")
    return legacy, invalid


def _project_tier(values: dict[str, Any], problems: list[str]) -> tuple[str, str]:
    if "autonomyTier" in values:
        return values["autonomyTier"], "autonomyTier"
    if _structural(problems) or "autonomyTier-invalid" in problems:
        return "strict", "default (config invalid)"
    return "strict", "default"


def module_tier(root: Path, module_id: str) -> tuple[str, str]:
    """module-autonomy: the only reader of a module's effective tier, as (tier, source).

    A module's own entry wins; otherwise the project's autonomyTier applies.  An invalid moduleAutonomy
    sends every module back to the project tier with the source "default (config invalid)".  spec-guard
    never caps the tier: a cap from elsewhere is the caller's to apply.
    """
    return module_tiers(root, [module_id])[1][module_id]


def module_tiers(root: Path, module_ids) -> tuple[str, dict[str, tuple[str, str]]]:
    """(project tier, {id: (tier, source)}) from one read of the file; module_tier is this for one id."""
    values, problems = _legacy(root)
    entries = values.get("moduleAutonomy", {})
    project, source = _project_tier(values, problems)
    if "moduleAutonomy-invalid" in problems:
        source = "default (config invalid)"
    return project, {module: (entries[module], "moduleAutonomy") if module in entries else (project, source)
                     for module in module_ids}


def wider(tier: str, than: str) -> bool:
    """TIERS runs from strict to relaxed."""
    return TIERS.index(tier) > TIERS.index(than)


def module_takeover(root: Path, module_id: str) -> tuple[dict[str, str], str]:
    """takeover-config: the only reader of a module's effective takeover, as (four items, source)."""
    return module_takeovers(root, [module_id])[1][module_id]


def module_takeovers(root: Path, module_ids) -> tuple[dict[str, str], dict[str, tuple[dict[str, str], str]]]:
    """(project items, {id: (items, source)}) from one read of the file.

    A module's own entry wins; otherwise the project's takeover applies, else none.  An invalid key falls back to the
    next layer with the source "default (config invalid)".  spec-guard never caps a module at the project's value.
    """
    values, problems = load(root)
    if "takeover" in values:
        project, source = expand(values["takeover"]), "takeover"
    elif _structural(problems) or "takeover-invalid" in problems:
        project, source = dict(HUMAN), "default (config invalid)"
    else:
        project, source = dict(HUMAN), "default"
    entries = values.get("moduleTakeover", {})
    if "moduleTakeover-invalid" in problems:
        source = "default (config invalid)"
    return project, {module: (expand(entries[module]), "moduleTakeover") if module in entries
                     else (dict(project), source) for module in module_ids}


def _items_line(items: dict[str, str]) -> str:
    return " ".join("%s=%s" % (item, items[item]) for item in ITEMS)


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
    if "retired-key" in problems:
        text, _ = read_text(root / RELATIVE_PATH)
        document = json.loads(text) if text is not None else {}
        for key in RETIRED:
            if key in document:
                print("%-16s retired, not in effect; set takeover instead (spec/takeover-config.md); "
                      "remove it with unset --key %s" % (key, key))
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


def _change(root: Path, key: str, value: str | None, confirm: bool, module: str | None = None) -> int:
    if key in OWNED_ELSEWHERE:
        print("%s is not stored in %s; change it with %s" % (key, RELATIVE_PATH, OWNED_ELSEWHERE[key]))
        return 2
    if key in RETIRED and (value is not None or module is not None):
        print("%s is retired (takeover-config); set takeover or moduleTakeover instead" % key)
        return 2
    if key in MANAGED:
        print("%s is kept by narrow and by set; it cannot be set or unset directly" % key)
        return 2
    if key not in VALIDATORS and key not in RETIRED:
        print("unknown-key: configurable keys are %s" % ", ".join(VALIDATORS))
        return 2
    if module is not None and key not in PER_MODULE:
        print("--module only applies to %s" % ", ".join(PER_MODULE))
        return 2
    if key in PER_MODULE and value is not None and module is None:
        print("%s is set one module at a time: add --module <module-id>" % key)
        return 2
    if module is not None and not MODULE_ID.fullmatch(module):
        print("%s-invalid: --module takes a kebab-case module id" % key)
        return 2
    if isinstance(value, str) and value.startswith("{") and key in ("takeover", "moduleTakeover"):
        try:
            value = json.loads(value)
        except ValueError:
            print("%s-invalid: --value takes a preset name or a JSON object" % key)
            return 2
    if module is not None and value is not None and not ENTRY_VALID[key](value):
        print("%s-invalid: see spec/%s.md for the accepted values"
              % (key, "module-autonomy" if key == "moduleAutonomy" else "takeover-config"))
        return 2
    if module is None and value is not None and not VALIDATORS[key](value):
        print("%s-invalid: see spec/project-config.md for the accepted values" % key)
        return 2
    prepared = _prepare(root)
    if isinstance(prepared, int):
        return prepared
    values, rest, before = prepared
    rest.pop(key, None)
    updated = dict(values)
    if module is not None:
        entries = dict(values.get(key, {}))
        if value is None:
            entries.pop(module, None)
        else:
            entries[module] = value
        value = entries if entries else None
    if value is None:
        updated.pop(key, None)
    else:
        updated[key] = value
    if key in ("takeover", "moduleTakeover"):
        refused = _keep_narrowed(values, updated)
        if refused:
            print(refused)
            return 2
        rest.pop("takeoverNarrowed", None)
    after = render(updated, rest)
    _print_diff(before, after)
    shown = (value or {}).get(module) if module is not None else value
    if key in ("takeover", "moduleTakeover") and shown is not None:
        items = expand(shown)
        print("takeover: %s" % _items_line(items))
        if module is not None:
            project = expand(values["takeover"]) if "takeover" in values else dict(HUMAN)
            if takeover_wider(items, project):
                print("note: %s 的接管档位宽于项目（%s）；spec-guard 不截断，按项目截断由调用方做"
                      % (module, _items_line(project)))
        if items["release"] in ("auto-confirm", "auto"):
            print("\n".join(RELEASE_LIMITS))
        retired = [name for name in RETIRED if name in rest]
        if retired:  # M3 rework: the takeover replaces them; say so where the user sets it
            print("note: %s %s retired and not in effect; the takeover above replaces them. Remove with %s"
                  % (", ".join(retired), "is" if len(retired) == 1 else "are",
                     " and ".join("unset --key %s" % name for name in retired)))
    return _commit(root, updated, rest, after, confirm)


def _scope_value(values: dict[str, Any], scope: str) -> Any:
    project = values.get("takeover", DEFAULTS["takeover"])
    return project if scope == SCOPE_PROJECT else values.get("moduleTakeover", {}).get(scope, project)


def _keep_narrowed(values: dict[str, Any], updated: dict[str, Any]) -> str | None:
    """takeover-narrow: a narrowed scope widens one step at a time; the record goes once it is back at `from`.

    Edits `updated` in place and returns the refusal text, or None.
    """
    records = dict(values.get("takeoverNarrowed", {}))
    for scope, record in list(records.items()):
        before, after = _scope_value(values, scope), _scope_value(updated, scope)
        if expand(before) == expand(after):
            continue
        if widen_steps(before, after) > 1:
            return ("takeover-narrowed: %s was narrowed (from %s); widen it one step at a time"
                    % (scope, _items_line(expand(record["from"]))))
        if narrower_or_equal(record["from"], after):
            del records[scope]
        else:
            records[scope] = dict(record, to=after)
    if records:
        updated["takeoverNarrowed"] = records
    else:
        updated.pop("takeoverNarrowed", None)
    return None


def _print_diff(before: str, after: str) -> None:
    diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                        fromfile=str(RELATIVE_PATH) + " (current)",
                                        tofile=str(RELATIVE_PATH) + " (proposed)"))
    print(diff if diff else "no change: %s already has this value" % RELATIVE_PATH)


def _commit(root: Path, updated: dict[str, Any], rest: dict[str, Any], after: str, confirm: bool) -> int:
    """Preview stops here; --confirm writes atomically and reads back."""
    if not confirm:
        print("\npreview only; nothing was written. Re-run with --confirm to apply.")
        return 0
    path = root / RELATIVE_PATH
    try:
        path.parent.mkdir(exist_ok=True)
        _write_atomic(path, after)
    except OSError:
        print("config-unwritable: %s could not be written" % RELATIVE_PATH)
        return 2
    if load(root)[0] != updated or _rest(root, updated) != rest:
        print("config-readback-mismatch: %s does not read back as written" % RELATIVE_PATH)
        return 2
    print("\nwrote %s" % RELATIVE_PATH)
    return 0


def _prepare(root: Path):
    """(values, rest, before text) for a write, or an exit code when the file or directory is unusable."""
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
    return values, rest, render(values, rest) if path.exists() else ""


def _narrow(root: Path, module: str | None, source: str, reason: str, confirm: bool) -> int:
    """takeover-narrow: one step stricter for the project or one module; no user words needed."""
    if source not in SOURCES:
        print("narrow-invalid: --source is one of %s" % ", ".join(SOURCES))
        return 2
    if not valid_reason(reason):
        print("narrow-invalid: --reason is one printable line of at most %d characters" % REASON_MAX)
        return 2
    if module is not None and not MODULE_ID.fullmatch(module):
        print("narrow-invalid: --module takes a kebab-case module id")
        return 2
    prepared = _prepare(root)
    if isinstance(prepared, int):
        return prepared
    values, rest, before = prepared
    project = values.get("takeover", DEFAULTS["takeover"])
    entries = dict(values.get("moduleTakeover", {}))
    scope = SCOPE_PROJECT if module is None else module
    current = project if module is None else entries.get(module, project)
    new = narrow_step(current)
    if new is None:
        print("already the strictest: %s is %s; nothing to narrow" % (scope, _items_line(expand(current))))
        return 0
    updated = dict(values)
    if module is None:
        updated["takeover"] = new
    else:
        entries[module] = new
        updated["moduleTakeover"] = entries
    records = dict(values.get("takeoverNarrowed", {}))
    first = records.get(scope, {}).get("from", current)
    records[scope] = {"from": first, "to": new, "source": source, "reason": reason,
                      "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    updated["takeoverNarrowed"] = records
    for key in ("takeover", "moduleTakeover", "takeoverNarrowed"):
        rest.pop(key, None)
    after = render(updated, rest)
    _print_diff(before, after)
    print("narrow %s: %s -> %s" % (scope, _items_line(expand(current)), _items_line(expand(new))))
    print("takeover: %s" % _items_line(expand(new)))
    return _commit(root, updated, rest, after, confirm)


def main() -> int:
    parser = argparse.ArgumentParser(description="Show, check or set the spec-guard project configuration.")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("show", help="read-only summary of every item and its source")
    show.add_argument("--format", choices=("text", "json"), default="text")
    commands.add_parser("check", help="exit 1 when the configuration file is invalid")
    setter = commands.add_parser("set", help="preview, and with --confirm write")
    setter.add_argument("--key", required=True)
    setter.add_argument("--value", required=True)
    setter.add_argument("--module")
    setter.add_argument("--confirm", action="store_true")
    unsetter = commands.add_parser("unset", help="preview, and with --confirm remove one key")
    unsetter.add_argument("--key", required=True)
    unsetter.add_argument("--module")
    unsetter.add_argument("--confirm", action="store_true")
    narrower = commands.add_parser("narrow", help="one step stricter (takeover-narrow); preview unless --confirm")
    narrower.add_argument("--module")
    narrower.add_argument("--source", required=True)
    narrower.add_argument("--reason", required=True)
    narrower.add_argument("--confirm", action="store_true")
    for sub in (show, commands.choices["check"], setter, unsetter, narrower):
        sub.add_argument("--project", default=".")
    args = parser.parse_args()
    root = Path(args.project)
    if args.command == "show":
        return _show(root, args.format == "json")
    if args.command == "check":
        _, problems = load(root)
        if problems and set(problems) <= set(IGNORED):
            # config-per-key: an unknown key is most likely from a newer spec-guard, a retired one from an older one;
            # both are ignored, not errors.
            print("ok (ignored: %s)" % ", ".join(problems))
            return 0
        if problems:
            print("%s is invalid: %s" % (RELATIVE_PATH, ", ".join(problems)))
            return 1
        print("ok")
        return 0
    if args.command == "narrow":
        return _narrow(root, args.module, args.source, args.reason, args.confirm)
    return _change(root, args.key, getattr(args, "value", None), args.confirm, args.module)


if __name__ == "__main__":
    raise SystemExit(main())
