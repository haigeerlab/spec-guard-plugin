#!/usr/bin/env bash
# hint-language-follow acceptance: the stage hint speaks one language.
#
# Usage: /bin/bash evals/hint-english-diff.sh
#
# Builds one set of fixture projects and runs the working tree's phase-guard on each, across stages, events and
# hosts. For every non-zh-CN configuration (none, en, ja, zh-TW, invalid) the hint must carry `Current stage: **` and
# no Chinese, Japanese or Korean character outside the stop rules (rules-at-nodes keeps their body Chinese only).
# With zh-CN it fails if a known English label is left in a Chinese hint. Until quiet-injection (D5, D6, F14) the
# English side was compared byte for byte with v0.67.0; those decisions change the English output on purpose.
# Run by hand at acceptance, not by validate.sh.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/hint-english-diff.XXXXXX")"
case "$WORK" in */hint-english-diff.*) trap 'chmod -R u+rwx "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT ;; esac

python3 - "$WORK" "$REPO/plugins/spec-guard/hooks" <<'PY'
import json, os, re, subprocess, sys
from pathlib import Path

work, new_hooks = Path(sys.argv[1]), sys.argv[2]
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@e", "-c", "commit.gpgsign=false"]
BLOCK = "<!-- BEGIN:agent-skills-convention -->\n"
MAP2 = ("# Capability Map\n| Module id | Responsibility | Depends on |\n|---|---|---|\n| alpha | x | — |\n"
        "| beta | y | alpha |\n\nBuild order: alpha → beta\n")


def w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(name, config, map_text=MAP2, cadence=None):
    root = work / "fx" / name
    root.mkdir(parents=True)
    subprocess.run(GIT + ["init", "-q", "-b", "main"], cwd=root, check=True)
    w(root / "CLAUDE.md", BLOCK)
    doc = {"version": 1}
    if config == "invalid":
        doc["artifactLanguage"] = "zh_CN"
    elif config:
        doc["artifactLanguage"] = config
    if cadence:
        doc["reviewCadence"] = cadence
    if len(doc) > 1:
        w(root / ".agent" / "config.json", json.dumps(doc) + "\n")
    if map_text is not None:
        w(root / "spec" / "CAPABILITY-MAP.md", map_text)
    return root


def alpha_done(root):
    w(root / "spec" / "alpha.md", "# Spec: alpha\n")
    w(root / "tasks" / "alpha" / "plan.md", "# Plan\n")
    w(root / "tasks" / "alpha" / "todo.md", "- [x] done\n")


def approve_spec(root, module):
    sys.path.insert(0, new_hooks)
    from module_stage import REVIEW_PENDING, review_approved_line, review_digest
    path = root / "spec" / ("%s.md" % module)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(REVIEW_PENDING, review_approved_line(review_digest(text))), encoding="utf-8")


def fixtures(config):
    """name -> project root for one configuration value."""
    out = {}
    def make(name, **kw):
        root = project("%s-%s" % (config or "none", name), config, **kw)
        out[name] = root
        return root
    make("idle", map_text=None)
    make("map-only")
    r = make("needs-spec"); alpha_done(r)
    r = make("needs-plan-pending"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n\n<!-- spec-guard: review pending -->\nx\n")
    r = make("needs-plan-none"); alpha_done(r); w(r / "spec/beta.md", "# Spec\nx\n")
    r = make("needs-plan-combined", cadence="combined"); alpha_done(r)
    w(r / "spec/beta.md", "# Spec\n\n<!-- spec-guard: review pending -->\nx\n")
    r = make("building-approved"); alpha_done(r); w(r / "spec/beta.md", "# Spec\nx\n")
    w(r / "tasks/beta/plan.md", "# Plan\n\n<!-- spec-guard: review approved -->\n")
    w(r / "tasks/beta/todo.md", "- [x] a\n- [ ] report Checkpoint 0 (report): x\n- [ ] Checkpoint 1 (gate): accept\n")
    r = make("building-none"); alpha_done(r); w(r / "spec/beta.md", "# Spec\nx\n")
    w(r / "tasks/beta/plan.md", "# Plan\n"); w(r / "tasks/beta/todo.md", "- [ ] a\n- [ ] Checkpoint 1: accept\n")
    r = make("building-plan-pending"); alpha_done(r); w(r / "spec/beta.md", "# Spec\nx\n")
    w(r / "tasks/beta/plan.md", "# Plan\n\n<!-- spec-guard: review pending -->\n"); w(r / "tasks/beta/todo.md", "- [ ] a\n")
    for name, final in (("spec-revised", False), ("spec-revised-final", True)):
        r = make(name); alpha_done(r); w(r / "spec/beta.md", "# Spec\n\n<!-- spec-guard: review pending -->\nx\n")
        approve_spec(r, "beta")
        w(r / "spec/beta.md", (r / "spec/beta.md").read_text(encoding="utf-8") + "changed\n")
        w(r / "tasks/beta/plan.md", "# Plan\n\n<!-- spec-guard: review approved -->\n")
        w(r / "tasks/beta/todo.md", "- [x] a\n- [ ] Checkpoint 2 (gate): accept\n" if final else "- [ ] a\n- [ ] b\n")
    r = make("marker-invalid"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n\n<!-- spec-guard: review maybe -->\nx\n")
    r = make("module-done"); alpha_done(r); w(r / ".agent/state.json", '{"activeModule": "alpha"}\n')
    r = make("module-done-paused", map_text=MAP2.replace("| beta | y | alpha |\n", "| beta | y | alpha |\n| gamma | z | — |\n")
             .replace("alpha → beta", "alpha → beta → gamma"))
    alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
    w(r / "tasks/beta/todo.md", "- [x] a\n- [ ] b\n"); w(r / "spec/gamma.md", "# Spec\n")
    w(r / "tasks/gamma/plan.md", "# Plan\n"); w(r / "tasks/gamma/todo.md", "- [x] a\n")
    w(r / ".agent/state.json", '{"activeModule": "gamma"}\n')
    r = make("done"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
    w(r / "tasks/beta/todo.md", "- [x] a\n")
    r = make("done-active"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
    w(r / "tasks/beta/todo.md", "- [x] a\n"); w(r / ".agent/state.json", '{"activeModule": "beta"}\n')
    r = make("done-suspended"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
    w(r / "tasks/beta/todo.md", "- [x] a\n- [ ] b\n<!-- spec-guard: suspended -->\n")
    w(r / ".agent/state.json", '{"activeModule": "beta"}\n')
    r = make("done-no-todo"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
    w(r / ".agent/state.json", '{"activeModule": "beta"}\n')
    for name, suspended in (("done-unmerged", False), ("done-unmerged-suspended", True)):
        r = make(name); alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
        w(r / "tasks/beta/todo.md", "- [x] a\n- [ ] b\n<!-- spec-guard: suspended -->\n" if suspended else "- [x] a\n")
        subprocess.run(GIT + ["add", "-A"], cwd=r, check=True)
        subprocess.run(GIT + ["commit", "-qm", "a"], cwd=r, check=True)
        subprocess.run(GIT + ["update-ref", "refs/remotes/origin/main", "HEAD"], cwd=r, check=True)
        subprocess.run(GIT + ["commit", "-qm", "b", "--allow-empty"], cwd=r, check=True)
    r = make("module-done-unmerged"); alpha_done(r); w(r / ".agent/state.json", '{"activeModule": "alpha"}\n')
    subprocess.run(GIT + ["add", "-A"], cwd=r, check=True)
    subprocess.run(GIT + ["commit", "-qm", "a"], cwd=r, check=True)
    subprocess.run(GIT + ["update-ref", "refs/remotes/origin/main", "HEAD"], cwd=r, check=True)
    subprocess.run(GIT + ["commit", "-qm", "b", "--allow-empty"], cwd=r, check=True)
    r = make("active-missing"); alpha_done(r); w(r / ".agent/state.json", '{"activeModule": "gamma"}\n')
    r = make("active-invalid"); alpha_done(r); w(r / ".agent/state.json", '{"activeModule": "Bad Id"}\n')
    r = make("active-suspended"); alpha_done(r); w(r / "spec/beta.md", "# Spec\n"); w(r / "tasks/beta/plan.md", "# Plan\n")
    w(r / "tasks/beta/todo.md", "- [x] a\n- [ ] b\n<!-- spec-guard: suspended -->\n")
    w(r / ".agent/state.json", '{"activeModule": "beta"}\n')
    make("map-invalid", map_text="| alpha | x | — |\n")
    r = make("stage-fail"); w(r / "spec/alpha.md", "# Spec\n"); w(r / "tasks/alpha/plan.md", "# Plan\n")
    (r / "tasks/alpha/todo.md").write_bytes(b"\xff\xfe not utf-8\n")
    r = make("unreadable"); w(r / "spec/alpha.md", "# Spec\n"); os.chmod(r / "spec/CAPABILITY-MAP.md", 0)
    r = make("unreadable-nospec"); os.chmod(r / "spec/CAPABILITY-MAP.md", 0)
    r = make("delegate"); w(r / "spec/alpha.md", "# Spec\n\n<!-- spec-guard: review pending -->\nx\n")
    # Linked: a directory with no activation of its own that points at the needs-spec project.
    link = work / "fx" / ("%s-linked" % (config or "none"))
    w(link / ".agent" / "spec-guard-link.json", json.dumps({"version": 1, "project": str(out["needs-spec"])}) + "\n")
    out["linked"] = link
    link2 = work / "fx" / ("%s-linked-session" % (config or "none"))
    w(link2 / ".agent" / "spec-guard-link.json",
      json.dumps({"version": 2, "sessions": {"sess-x": str(out["needs-spec"])}}) + "\n")
    out["linked-session"] = link2
    return out


claude_home = work / "claude-home"
w(claude_home / "plugins" / "installed_plugins.json",
  json.dumps({"version": 2, "plugins": {"delegate@dm": [{"scope": "user", "installPath": "/x"}]}}) + "\n")
w(claude_home / "settings.json", json.dumps({"enabledPlugins": {"delegate@dm": True}}) + "\n")
codex_home = work / "codex-home"
(codex_home / "plugins" / "cache" / "dm" / "delegate" / "0.5.2").mkdir(parents=True)
w(codex_home / "config.toml", '[plugins."delegate@dm"]\nenabled = true\n')
empty_home = work / "empty-home"
empty_home.mkdir()
transcript = work / "transcript.jsonl"
w(transcript, json.dumps({"type": "assistant", "isSidechain": False, "message": {"usage": {
    "input_tokens": 1, "cache_read_input_tokens": 849999, "cache_creation_input_tokens": 0}}}) + "\n")
rollout = work / "rollout.jsonl"
w(rollout, json.dumps({"type": "event_msg", "payload": {"type": "token_count", "info": {
    "last_token_usage": {"input_tokens": 230000}, "model_context_window": 258400}}}) + "\n")

VARIANTS = {
    "claude": dict(host="claude"),
    "codex": dict(host="codex"),
    "unknown-host": dict(host=None),
    "session-start": dict(host="claude", event="SessionStart"),
    "claude-850k": dict(host="claude", stdin={"session_id": "s", "transcript_path": str(transcript), "prompt": "p"}),
    "codex-230k": dict(host="codex", stdin={"session_id": "s", "transcript_path": str(rollout), "prompt": "p"}),
    "linked-session": dict(host="claude", stdin={"session_id": "sess-x"}),
}


def run(hooks, root, name, variant):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_CODE_SESSION_ATTENDED", "PLUGIN_ROOT", "SPEC_GUARD_HOST", "CLAUDE_PROJECT_DIR")}
    delegate = name == "delegate"
    env["CLAUDE_CONFIG_DIR"] = str(claude_home if delegate else empty_home)
    env["CODEX_HOME"] = str(codex_home if delegate else empty_home)
    if variant["host"]:
        env["SPEC_GUARD_HOST"] = variant["host"]
        env["CLAUDE_PROJECT_DIR"] = str(root)
    args = ["/bin/bash", os.path.join(hooks, "phase-guard.sh")] + ([variant["event"]] if variant.get("event") else [])
    stdin = json.dumps(variant["stdin"]) if "stdin" in variant else None
    done = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True, timeout=60,
                          input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL)
    if not done.stdout:
        return ""
    return json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]


ENGLISH_LABELS = ("Suggested next step", "Capability map:", "Module specs:", "Current module:", "Artifact language",
                  "State this location", "Location:", "Review:", "Next gate", "External review (from", "Module boundary",
                  "Session context", "Linked project", "Context was just", "Modules ", "Suspended", "Paused",
                  "Plan without todo", "This branch has", "unchecked item", "is done", "Review cadence",
                  "awaiting the user", "do not paste", "slash command for the chat", "using Build order",
                  "could not be computed", "can be cleared", "counts as done")

from concurrent.futures import ThreadPoolExecutor

jobs = []
for config in (None, "en", "ja", "zh-TW", "invalid", "zh-CN"):
    for name, root in fixtures(config).items():
        for vname, variant in VARIANTS.items():
            if (vname == "linked-session") == (name == "linked-session"):
                jobs.append((config, name, root, vname, variant))


def check(job):
    config, name, root, vname, variant = job
    label = "%s/%s/%s" % (config or "none", name, vname)
    new = run(new_hooks, root, name, variant)
    if config == "zh-CN":
        left = [item for item in ENGLISH_LABELS if item in new]
        if not new or "## spec-guard local workflow" not in new or "当前阶段: **" not in new or left:
            return "zh", label + ": %s" % (left or "missing heading or stage line")
        return "zh", None
    left = english_left(new)
    if not new or "Current stage: **" not in new or left:
        return "en", label + ": %s" % (left or "missing stage line")
    return "en", None


# Chinese, Japanese and Korean scripts and their full-width punctuation.
CJK = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uff00-\uffef]")
STOP_RULES = re.compile(r"\n\nStop rules \([^)]*\):\n\n.*?(?=\n\n<!-- spec-guard-state:|\Z)", re.DOTALL)


def english_left(text):
    """Lines of an English hint that still carry CJK text, the stop rules taken out."""
    return [line for line in STOP_RULES.sub("", text).split("\n") if CJK.search(line)]


with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(check, jobs))
failures = [bad for kind, bad in results if kind == "en" and bad]
zh_bad = [bad for kind, bad in results if kind == "zh" and bad]
compared = sum(kind == "en" for kind, _ in results)
same = compared - len(failures)
zh_checked = sum(kind == "zh" for kind, _ in results)
print("English hints in English only: %d/%d" % (same, compared))
for item in failures:
    print("  CJK LEFT: " + item)
print("zh-CN hints without English labels: %d/%d" % (zh_checked - len(zh_bad), zh_checked))
for item in zh_bad:
    print("  ENGLISH LEFT: " + item)
sys.exit(1 if failures or zh_bad else 0)
PY
