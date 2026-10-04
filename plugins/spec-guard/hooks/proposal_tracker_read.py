"""Recover one Proposal Issue from already-read, platform-normalized candidates."""
import json
import re
import subprocess
from urllib.parse import urlencode, urlparse

from capability_map import _visible_lines
from proposal_contract import ContractError, validate_tracker


PAGE_SIZE = 100
MAX_PAGES = 10
# The Local container is a committed Epiq project id; the same expression validates it
# in local_ledger_runtime, so the two cannot drift apart.
LOCAL_PROJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
# Open/closed is read per platform.  GitLab says "opened", not "open".
CLOSED_STATES = {"github": {"open": False, "closed": True},
                 "gitlab": {"opened": False, "closed": True}}


class TrackerRead(object):
    def __init__(self, state, issue_id=None, stage=None, diagnostic=None, proposal_id=None,
                 platform=None, target=None, closed=None):
        self.state = state
        self.issue_id = issue_id
        self.stage = stage
        self.closed = closed
        self.diagnostic = diagnostic
        self.proposal_id = proposal_id
        self.platform = platform
        self.target = target


def as_json(result, platform, target):
    """Serialize only caller-safe tracker facts, never raw responses or errors."""
    data = {"state": result.state, "platform": platform, "target": target}
    if result.state == "verified":
        data["issueId"] = result.issue_id
        data["stage"] = result.stage
        data["closed"] = result.closed
    elif result.state == "invalid":
        data["diagnostic"] = "tracker-contract-invalid"
    elif result.state == "unknown":
        data["diagnostic"] = "tracker-read-unavailable"
    return data


def _unknown(message):
    return TrackerRead("unknown", diagnostic=message)


def _invalid(message):
    return TrackerRead("invalid", diagnostic=message)


def _closed(platform, issue):
    """The open/closed fact, or None when the response does not carry it.

    A caller cannot report `already-closed` without this, and guessing "open" would
    make a closed item look writable, so a missing or unexpected value is a failure to
    read rather than a default.
    """
    if platform == "local":
        value = issue.get("isClosed")
        return value if isinstance(value, bool) else None
    return CLOSED_STATES[platform].get(issue.get("state"))


def _labels(platform, issue):
    value = issue.get("labels")
    if not isinstance(value, list):
        return None
    if platform == "github":
        if any(not isinstance(label, dict) or not isinstance(label.get("name"), str)
               for label in value):
            return None
        return [label["name"] for label in value]
    if any(not isinstance(label, str) for label in value):
        return None
    return value


def _issue_fields(platform, issue):
    if not isinstance(issue, dict):
        return None
    if platform == "github":
        issue_id = issue.get("number")
        repository = issue.get("repository")
        container = repository.get("full_name") if isinstance(repository, dict) else None
        if container is None:
            repository_url = issue.get("repository_url")
            parsed = urlparse(repository_url) if isinstance(repository_url, str) else None
            parts = parsed.path.strip("/").split("/") if parsed is not None else []
            container = ("%s/%s" % (parts[1], parts[2])
                         if (parsed is not None and parsed.scheme == "https" and
                             parsed.netloc == "api.github.com" and
                             len(parts) == 3 and parts[0] == "repos" and
                             all(parts)) else None)
        body = issue.get("body")
    elif platform == "gitlab":
        issue_id = issue.get("iid")
        container = issue.get("project_id")
        body = issue.get("description")
    else:
        issue_id = issue.get("id")
        container = issue.get("projectId")
        body = issue.get("description")
    labels = _labels(platform, issue)
    closed = _closed(platform, issue)
    identified = (
        (platform == "local" and isinstance(issue_id, str) and issue_id) or
        (platform != "local" and isinstance(issue_id, int) and issue_id > 0))
    if (not identified or
            not ((platform == "github" and isinstance(container, str) and container) or
                 (platform == "gitlab" and isinstance(container, int) and container > 0) or
                 (platform == "local" and isinstance(container, str) and container)) or
            not isinstance(body, str) or labels is None or closed is None):
        return None
    return issue_id, container, body, labels, closed


def _has_marker(body, marker):
    return any(line.strip() == marker for line in _visible_lines(body.splitlines()))


def _has_legacy_marker(body):
    return any(line.strip().startswith("<!-- spec-guard-sync:v2 ")
               for line in _visible_lines(body.splitlines()))


def recover_tracker_issue(proposal, platform, target, page):
    """Return a conservative result from one complete GitHub/GitLab candidate set.

    `page` is an adapter boundary: it must be a mapping with an explicit boolean
    `complete` and an `issues` list. Transport is deliberately outside this pure
    function, so fixtures and future CLI readers share the same identity rules.
    """
    if platform not in ("github", "gitlab", "local"):
        return _unknown("unsupported tracker platform")
    if ((platform == "github" and
         (not isinstance(target, str) or not target or "/" not in target)) or
            (platform == "gitlab" and
             (not isinstance(target, int) or target <= 0)) or
            (platform == "local" and
             (not isinstance(target, str) or not LOCAL_PROJECT_ID.fullmatch(target)))):
        return _unknown("target container is not verifiable")
    if not isinstance(page, dict) or page.get("complete") is not True:
        return _unknown("tracker candidate set is incomplete")
    issues = page.get("issues")
    if not isinstance(issues, list):
        return _unknown("tracker candidate set is malformed")

    matches = []
    for issue in issues:
        fields = _issue_fields(platform, issue)
        if fields is None:
            return _unknown("tracker issue response is malformed")
        issue_id, container, body, labels, closed = fields
        if not _has_marker(body, proposal.marker):
            continue
        if container != target:
            return _invalid("Proposal marker appeared outside the target container")
        if _has_legacy_marker(body):
            return _invalid("Proposal Issue contains a legacy bridge marker")
        matches.append((issue_id, body, labels, closed))

    if not matches:
        return TrackerRead("absent")
    if len(matches) != 1:
        return _invalid("multiple Proposal Issues contain the complete marker")
    issue_id, body, labels, closed = matches[0]
    try:
        validate_tracker(proposal, body, labels)
    except ContractError as error:
        return _invalid(str(error))
    stages = [label for label in labels if label.startswith("proposal-stage:")]
    return TrackerRead("verified", issue_id=issue_id, stage=stages[0],
                       proposal_id=proposal.proposal_id, platform=platform, target=target,
                       closed=closed)


def _run(args):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _json(raw):
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _github_page(target, runner):
    response = _json(runner([
        "gh", "issue", "list", "--repo", target, "--state", "all",
        "--limit", str(PAGE_SIZE * MAX_PAGES), "--json", "number,body,labels,state",
    ]))
    if (not isinstance(response, list) or
            len(response) >= PAGE_SIZE * MAX_PAGES):
        return None
    issues = []
    for issue in response:
        if not isinstance(issue, dict) or "pull_request" in issue:
            continue
        issue = dict(issue)
        issue["repository"] = {"full_name": target}
        issues.append(issue)
    return {"complete": True, "issues": issues}


def _gitlab_page(target, runner):
    # List every Issue and match the marker locally, as for GitHub. GitLab's search= does not
    # match text inside HTML comments (GitLab 15.3.2, verified 2026-09-28), and the marker is one.
    issues = []
    for page_number in range(1, MAX_PAGES + 1):
        query = urlencode({"state": "all",
                           "per_page": str(PAGE_SIZE), "page": str(page_number)})
        response = _json(runner(["glab", "api", "projects/%s/issues?%s" %
                                 (target, query)]))
        if not isinstance(response, list) or len(response) > PAGE_SIZE:
            return None
        issues.extend(response)
        if len(response) < PAGE_SIZE:
            return {"complete": True, "issues": issues}
    return None


def read_tracker(proposal, platform, target, runner=None):
    """Read a complete candidate set through GitHub/GitLab read-only CLI calls."""
    runner = _run if runner is None else runner
    if not callable(runner):
        return _unknown("tracker runner is unavailable")
    if platform == "github":
        page = _github_page(target, runner)
    elif platform == "gitlab":
        page = _gitlab_page(target, runner)
    else:
        return _unknown("unsupported tracker platform")
    return _unknown("tracker candidate set is unavailable") if page is None else (
        recover_tracker_issue(proposal, platform, target, page))
