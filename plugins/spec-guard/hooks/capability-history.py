#!/usr/bin/env python3
"""Validate and query spec-guard's initiative lifecycle ledger."""
import hashlib
import json
import os
import re
import sys
import tempfile


ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHECKPOINT_ID = re.compile(r"^\d{8}T\d{6}Z-\d{4}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
AUDIT_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EVENTS = {"created", "paused", "resumed", "completed", "abandoned", "superseded"}
MODULE_STATUS = {"not-started", "in-progress", "completed", "abandoned", "unknown"}
TERMINAL = {"completed", "abandoned", "superseded"}
NEXT = {
    "created": {"paused", *TERMINAL},
    "paused": {"resumed", "abandoned", "superseded"},
    "resumed": {"paused", *TERMINAL},
}


class Invalid(ValueError):
    pass


def fail(message):
    raise Invalid(message)


def require(value, description):
    if not value:
        fail("missing " + description)
    return value


def check_path(path, prefix):
    if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/"):
        fail("invalid path")
    if not path.startswith(prefix):
        fail("path outside checkpoint")


def check_artifact(value, prefix):
    if value is None:
        return
    if not isinstance(value, dict):
        fail("artifact must be object or null")
    check_path(value.get("path"), prefix)
    if value["path"] != prefix:
        fail("artifact path must match checkpoint location")
    if not isinstance(value.get("sha256"), str) or not SHA256.fullmatch(value["sha256"]):
        fail("artifact sha256 must be 64 lowercase hex characters")


def check_checkpoint(checkpoint, initiative_id):
    if not isinstance(checkpoint, dict):
        fail("checkpoint must be an object")
    checkpoint_id = checkpoint.get("id")
    if not isinstance(checkpoint_id, str) or not CHECKPOINT_ID.fullmatch(checkpoint_id):
        fail("invalid checkpoint id")
    base = "spec/history/%s/%s/" % (initiative_id, checkpoint_id)
    map_value = checkpoint.get("map")
    if not isinstance(map_value, dict):
        fail("checkpoint map must be an object")
    check_path(map_value.get("path"), base)
    if map_value.get("path") != base + "CAPABILITY-MAP.md":
        fail("checkpoint map path must be CAPABILITY-MAP.md")
    if not isinstance(map_value.get("sha256"), str) or not SHA256.fullmatch(map_value["sha256"]):
        fail("map sha256 must be 64 lowercase hex characters")

    check_artifact(checkpoint.get("state"), ".agent/history/%s/%s/state.json" % (initiative_id, checkpoint_id))

    modules = checkpoint.get("modules")
    if not isinstance(modules, list):
        fail("checkpoint modules must be an array")
    seen = set()
    for module in modules:
        if not isinstance(module, dict):
            fail("module must be an object")
        module_id = module.get("id")
        if not isinstance(module_id, str) or not ID.fullmatch(module_id) or module_id in seen:
            fail("invalid or duplicate module id")
        seen.add(module_id)
        if not isinstance(module.get("responsibility"), str) or not module["responsibility"].strip():
            fail("module responsibility is required")
        depends = module.get("dependsOn")
        if not isinstance(depends, list) or any(not isinstance(item, str) or not ID.fullmatch(item) for item in depends):
            fail("invalid module dependencies")
        if module.get("status") not in MODULE_STATUS:
            fail("invalid module status")
        if module.get("issue") is not None and (not isinstance(module["issue"], int) or module["issue"] < 1):
            fail("invalid module issue")
        check_artifact(module.get("spec"), base + module_id + ".md")
        check_artifact(module.get("plan"), "tasks/history/%s/%s/%s/plan.md" % (initiative_id, checkpoint_id, module_id))


def check_initiative(initiative):
    if not isinstance(initiative, dict):
        fail("initiative must be an object")
    initiative_id = initiative.get("id")
    if not isinstance(initiative_id, str) or not ID.fullmatch(initiative_id):
        fail("invalid initiative id")
    if not isinstance(initiative.get("title"), str) or not initiative["title"].strip():
        fail("initiative title is required")
    events = initiative.get("events")
    if not isinstance(events, list) or not events:
        fail("initiative events are required")
    previous = None
    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("type") not in EVENTS:
            fail("invalid lifecycle event")
        event_type = event["type"]
        if index == 0 and event_type != "created":
            fail("first lifecycle event must be created")
        if previous is not None and event_type not in NEXT.get(previous, set()):
            fail("invalid lifecycle transition")
        if event_type in {"created", "paused", *TERMINAL}:
            check_checkpoint(event.get("checkpoint"), initiative_id)
        elif "checkpoint" in event:
            fail("resumed event must not have checkpoint")
        previous = event_type


# Corrections can no longer be appended (audit and correct were removed); records
# already in a ledger are still validated so old ledgers keep verifying.
def check_correction(correction, initiatives):
    if not isinstance(correction, dict) or correction.get("type") != "history-correction":
        fail("invalid history correction")
    initiative_id = correction.get("initiativeId")
    if initiative_id not in initiatives:
        fail("correction initiative not found")
    event_index = correction.get("eventIndex")
    events = initiatives[initiative_id]["events"]
    if not isinstance(event_index, int) or isinstance(event_index, bool) or not 0 <= event_index < len(events):
        fail("invalid correction event index")
    checkpoint = events[event_index].get("checkpoint")
    checkpoint_id = correction.get("checkpointId")
    expected_checkpoint_id = checkpoint["id"] if checkpoint else None
    if checkpoint_id != expected_checkpoint_id:
        fail("correction checkpoint does not match event")
    module_id = correction.get("moduleId")
    field = correction.get("field")
    if field not in {"responsibility", "dependsOn", "status", "event.at"}:
        fail("invalid correction field")
    if field == "event.at":
        if module_id is not None:
            fail("event time correction must not name a module")
    elif checkpoint is None:
        fail("module correction requires a checkpoint")
    elif (not isinstance(module_id, str) or not ID.fullmatch(module_id) or
          module_id not in {module["id"] for module in checkpoint["modules"]}):
        fail("module correction requires a valid module id")
    if not AUDIT_TIME.fullmatch(correction.get("auditedAt", "")):
        fail("invalid correction audit time")
    if not isinstance(correction.get("auditReportSha256"), str) or not SHA256.fullmatch(correction["auditReportSha256"]):
        fail("invalid correction audit report digest")
    if "before" not in correction or "after" not in correction:
        fail("correction before and after are required")
    if field == "responsibility":
        if not all(isinstance(correction[key], str) and correction[key].strip()
                   for key in ("before", "after")):
            fail("responsibility correction values are invalid")
    elif field == "dependsOn":
        if any(not isinstance(correction[key], list) or
               any(not isinstance(item, str) or not ID.fullmatch(item) for item in correction[key])
               for key in ("before", "after")):
            fail("dependency correction values are invalid")
    elif field == "status":
        if correction["before"] not in MODULE_STATUS or correction["after"] != "unknown":
            fail("status correction must retain unknown")
    elif not isinstance(correction["before"], str) or correction["after"] != "unknown":
        fail("event time correction must retain unknown")
    sources = correction.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("correction sources are required")
    for source in sources:
        if (not isinstance(source, dict) or source.get("kind") != "audit-finding" or
                not isinstance(source.get("code"), str) or not source["code"]):
            fail("invalid correction source")


def validate_data(data):
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        fail("unsupported capability history schema")
    initiatives = data.get("initiatives")
    if not isinstance(initiatives, list):
        fail("initiatives must be an array")
    initiatives_by_id = {}
    for initiative in initiatives:
        check_initiative(initiative)
        if initiative["id"] in initiatives_by_id:
            fail("duplicate initiative id")
        initiatives_by_id[initiative["id"]] = initiative
    corrections = data.get("corrections", [])
    if not isinstance(corrections, list):
        fail("corrections must be an array")
    for correction in corrections:
        check_correction(correction, initiatives_by_id)
    return data


def load(path):
    with open(path, encoding="utf-8") as handle:
        return validate_data(json.load(handle))


def write_atomic(path, data):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(directory):
        fail("ledger directory does not exist")
    descriptor, temporary = tempfile.mkstemp(prefix=".capability-history-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def create(ledger_path, initiative_path):
    if os.path.exists(ledger_path):
        fail("ledger already exists")
    with open(initiative_path, encoding="utf-8") as handle:
        initiative = json.load(handle)
    check_initiative(initiative)
    write_atomic(ledger_path, {"schemaVersion": 1, "initiatives": [initiative]})


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def verify_artifact(root, artifact):
    if artifact is None:
        return
    path = os.path.realpath(os.path.join(root, artifact["path"]))
    if os.path.commonpath([root, path]) != root:
        fail("artifact resolves outside project root")
    if not os.path.isfile(path):
        fail("history artifact is missing")
    if digest(path) != artifact["sha256"]:
        fail("history artifact digest differs")


def verify(data, root_path):
    root = os.path.realpath(root_path)
    if not os.path.isdir(root):
        fail("project root is not a directory")
    for initiative in data["initiatives"]:
        for event in initiative["events"]:
            checkpoint = event.get("checkpoint")
            if checkpoint is None:
                continue
            verify_artifact(root, checkpoint["map"])
            verify_artifact(root, checkpoint.get("state"))
            for module in checkpoint["modules"]:
                verify_artifact(root, module["spec"])
                verify_artifact(root, module["plan"])


def artifact_paths(data):
    """Yield the recorded path of every history artifact in the ledger.

    Covers the checkpoint map, its optional state snapshot, and each
    module's optional spec and plan — the only ledger fields that point at
    files preserved under ``spec/history``, ``tasks/history`` or
    ``.agent/history``. Callers that need to know which directories in
    those trees are accounted for should use this instead of re-deriving
    the field names.
    """
    for initiative in data["initiatives"]:
        for event in initiative["events"]:
            checkpoint = event.get("checkpoint")
            if checkpoint is None:
                continue
            yield checkpoint["map"]["path"]
            state = checkpoint.get("state")
            if state is not None:
                yield state["path"]
            for module in checkpoint["modules"]:
                spec = module.get("spec")
                if spec is not None:
                    yield spec["path"]
                plan = module.get("plan")
                if plan is not None:
                    yield plan["path"]


def initiative_by_id(data, initiative_id):
    for initiative in data["initiatives"]:
        if initiative["id"] == initiative_id:
            return initiative
    fail("initiative not found")


def main(argv):
    if len(argv) < 2 or argv[0] not in {"validate", "status", "verify", "create", "artifact-dirs"}:
        print("usage: capability-history.py validate <file> | status <file> <initiative-id> | verify <file> <project-root> | create <ledger> <initiative> | artifact-dirs <file>", file=sys.stderr)
        return 2
    try:
        if argv[0] == "create":
            if len(argv) != 3:
                return 2
            create(argv[1], argv[2])
            print("ok")
            return 0
        data = load(argv[1])
        if argv[0] == "validate":
            if len(argv) != 2:
                return 2
            print("ok")
            return 0
        if argv[0] == "verify":
            if len(argv) != 3:
                return 2
            verify(data, argv[2])
            print("ok")
            return 0
        if argv[0] == "artifact-dirs":
            if len(argv) != 2:
                return 2
            for directory in sorted({os.path.dirname(path) for path in artifact_paths(data)}):
                print(directory)
            return 0
        if len(argv) != 3:
            return 2
        initiative = initiative_by_id(data, argv[2])
        print("active" if initiative["events"][-1]["type"] == "created" else initiative["events"][-1]["type"])
        return 0
    except (OSError, json.JSONDecodeError, Invalid) as error:
        print("capability history: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
