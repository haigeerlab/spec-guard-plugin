#!/usr/bin/env bash
# Create the local agent-relay repository from this repository's history (collaboration-extraction).
#
# usage: extract-collaboration.sh <base-commit> <target-dir>
#
# Fetches only <base-commit> into a new repository at <target-dir> (no tags, no remote), keeps the paths in
# scripts/collaboration-extraction-paths.txt with git filter-repo, and then proves the result: every kept file
# is byte-identical to the base, nothing else exists, sampled files keep their full history, and the moved
# collaboration tests give the expected result (spec/collaboration-extraction.md, requirement 3).
# It never writes inside this repository. Exit 0 only when every check passes.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <base-commit> <target-dir>" >&2
  exit 2
fi
BASE_ARG="$1"
TARGET="$2"
REPO="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"

command -v git-filter-repo >/dev/null 2>&1 || { echo "git-filter-repo is not installed" >&2; exit 2; }
BASE="$(git -C "$REPO" rev-parse --verify --quiet "${BASE_ARG}^{commit}")" \
  || { echo "base commit not found: ${BASE_ARG}" >&2; exit 2; }
if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "target is not empty: ${TARGET}" >&2
  exit 2
fi
case "$(cd "$(dirname "$TARGET")" 2>/dev/null && pwd -P)/" in
  "$(cd "$REPO" && pwd -P)/"*) echo "target must be outside this repository: ${TARGET}" >&2; exit 2 ;;
esac

# Take the path file from the base commit, so the run is reproducible from the commit alone.
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git -C "$REPO" show "${BASE}:scripts/collaboration-extraction-paths.txt" > "$WORK/paths.txt"

mkdir -p "$TARGET"
git -C "$TARGET" init -q -b main
git -C "$TARGET" fetch -q --no-tags "$REPO" "$BASE"
git -C "$TARGET" update-ref refs/heads/main FETCH_HEAD
git -C "$TARGET" reset -q --hard main
(cd "$TARGET" && git filter-repo --quiet --force --paths-from-file "$WORK/paths.txt")
git -C "$TARGET" remote remove origin 2>/dev/null || true

python3 - "$REPO" "$BASE" "$TARGET" "$WORK/paths.txt" <<'PY'
import re
import subprocess
import sys
from pathlib import Path

repo, base, target, paths_file = sys.argv[1:]
EXPECTED_ERRORS = {  # decision D7: these read files that stay in Spec Guard or are re-rooted
    ("test_skill_entrypoints.py", "test_optional_feature_docs_explain_smooth_preapproval_and_limits"),
    ("test_skill_entrypoints.py", "test_repository_validation_runs_the_entry_contract"),
    ("test_native_only_collaboration.py", "test_current_decision_declares_native_only_without_a_rollback_gate"),
    ("test_native_only_collaboration.py", "test_current_entry_contracts_do_not_offer_xats"),
}
SAMPLES = ("plugins/spec-guard/hooks/native_collaboration_runtime.py",
           "spec/collaboration-messaging.md", "docs/collaboration-interface.md")


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True).stdout


keep, renames = [], []
for raw in Path(paths_file).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if "==>" in line:
        renames.append(tuple(line.split("==>", 1)))
    else:
        keep.append(line)


def kept(path):
    return any(path.startswith(p) if p.endswith("/") else path == p for p in keep)


def rerooted(path):
    for old, new in renames:
        if old.endswith("/") and path.startswith(old):
            return new + path[len(old):]
        if path == old:
            return new
    return path


failures = []
expected = {rerooted(p): p for p in git(repo, "ls-tree", "-r", "--name-only", base).splitlines() if kept(p)}
actual = set(git(target, "ls-files").splitlines())
if set(expected) != actual:
    failures.append(f"file set differs: missing {sorted(set(expected) - actual)}, extra {sorted(actual - set(expected))}")
for new, old in sorted(expected.items()):
    if new in actual and git(repo, "rev-parse", f"{base}:{old}") != git(target, "rev-parse", f"HEAD:{new}"):
        failures.append(f"content differs: {old} -> {new}")

for old in SAMPLES:
    before = git(repo, "log", "--format=%H", base, "--", old).split()
    after = git(target, "log", "--follow", "--format=%H", "--", rerooted(old)).split()
    if len(before) != len(after) or len(after) < 2:
        failures.append(f"history of {old}: {len(before)} commits at base, {len(after)} after")
    print(f"history  {rerooted(old)}: {len(after)} commits (base {len(before)})")

hooks = Path(target) / "plugins/agent-relay/hooks"
suite = (hooks / "test-collaboration-suite.sh").read_text(encoding="utf-8")
tests = re.findall(r"hooks/(test_\w+\.py)", suite)
ran, errors = 0, set()
for name in tests:
    done = subprocess.run([sys.executable, "-B", name, "-v"], cwd=hooks, capture_output=True, text=True)
    match = re.search(r"^Ran (\d+) tests?", done.stderr, re.M)
    ran += int(match.group(1)) if match else 0
    for test, verdict in re.findall(r"^(test\w+) \(.*?\)(?:\n.*?)?\s\.\.\. (ERROR|FAIL)$", done.stderr, re.M):
        errors.add((name, test))
    if done.returncode != 0 and not any(n == name for n, _ in errors):
        failures.append(f"{name} failed without a parsable test result")
print(f"suite    {len(tests)} files, {ran} tests, {ran - len(errors)} pass, {len(errors)} errors")
for name, test in sorted(errors):
    print(f"         error {name}::{test}")
if errors != EXPECTED_ERRORS:
    failures.append(f"suite errors differ from D7: unexpected {sorted(errors - EXPECTED_ERRORS)}, "
                    f"missing {sorted(EXPECTED_ERRORS - errors)}")

print(f"base     {base}")
print(f"head     {git(target, 'rev-parse', 'HEAD').strip()}")
print(f"commits  {git(target, 'rev-list', '--count', 'HEAD').strip()}")
print(f"files    {len(actual)} (expected {len(expected)})")
print(f"refs     {' '.join(git(target, 'for-each-ref', '--format=%(refname)').split())}")
print(f"remotes  {' '.join(git(target, 'remote').split()) or 'none'}")
for failure in failures:
    print(f"FAIL     {failure}")
print("extraction verified" if not failures else "extraction NOT verified")
sys.exit(1 if failures else 0)
PY
