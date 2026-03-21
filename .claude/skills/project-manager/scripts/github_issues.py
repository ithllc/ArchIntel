#!/usr/bin/env python3
"""
github_issues.py - "The Liaison"
Pull, ingest, and sync GitHub Issues for the current repository's kanban board.
"""

import json
import subprocess
import sys
import argparse
import re
from pathlib import Path
from typing import Any, Optional

SKILL_DIR = Path(__file__).parent.parent
STATE_FILE = SKILL_DIR / "kanban_state.json"

SEVERITY_PRIORITY_MAP = {
    "severity:blocker": "P0",
    "severity:major": "P1",
    "severity:moderate": "P2",
    "severity:minor": "P3",
    "severity:cosmetic": "P4",
}

LABEL_TYPE_MAP = {
    "bug": "bugfix",
    "enhancement": "feature",
    "testing": "test",
    "architecture": "refactor",
    "ux": "feature",
}

LABEL_DOMAIN_MAP = {
    "ux": "frontend",
    "testing": "testing",
    "architecture": "infra",
}


def check_gh_cli() -> bool:
    """Verify gh CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("ERROR: gh CLI is not installed.")
        print("Install with: sudo apt install gh")
        print("Then authenticate: gh auth login")
        return False
    except subprocess.TimeoutExpired:
        print("ERROR: gh auth status timed out.")
        return False


def get_repo_info() -> Optional[str]:
    """Detect the GitHub repository from git remote origin."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            print("ERROR: No git remote origin found.")
            return None
        url = result.stdout.strip()
        # Handle both HTTPS and SSH URLs
        # https://github.com/OWNER/REPO.git -> OWNER/REPO
        # git@github.com:OWNER/REPO.git -> OWNER/REPO
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if match:
            return match.group(1)
        print(f"ERROR: Could not parse GitHub repo from: {url}")
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("ERROR: git command failed.")
        return None


def pull_issues(label: Optional[str] = None, limit: int = 50, state: str = "open") -> list[dict]:
    """Fetch issues from the remote GitHub repository."""
    cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit), "--json",
           "number,title,body,labels,state,assignees,createdAt,updatedAt"]
    if label:
        cmd.extend(["--label", label])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"ERROR: gh issue list failed: {result.stderr}")
        return []

    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("ERROR: Could not parse gh output as JSON.")
        return []

    print(f"Pulled {len(issues)} {state} issues from GitHub.")
    return issues


def _extract_dependencies(body: str) -> list[int]:
    """Extract issue dependency references from body text."""
    deps = []
    for match in re.finditer(r"[Dd]epends on #(\d+)", body or ""):
        deps.append(int(match.group(1)))
    return deps


def _map_labels(labels: list[dict]) -> dict[str, str]:
    """Map GitHub labels to kanban task type, domain, and priority."""
    label_names = [l.get("name", "") for l in labels]
    result = {"type": "feature", "domain": "general", "priority": "P2"}

    for name in label_names:
        if name in LABEL_TYPE_MAP:
            result["type"] = LABEL_TYPE_MAP[name]
        if name in LABEL_DOMAIN_MAP:
            result["domain"] = LABEL_DOMAIN_MAP[name]
        if name in SEVERITY_PRIORITY_MAP:
            result["priority"] = SEVERITY_PRIORITY_MAP[name]

    return result


def ingest_issues(issues: list[dict]) -> list[dict]:
    """Convert GitHub Issues into kanban task format."""
    tasks = []
    for issue in issues:
        mapped = _map_labels(issue.get("labels", []))
        deps = _extract_dependencies(issue.get("body", ""))
        task = {
            "title": issue["title"],
            "github_issue": issue["number"],
            "type": mapped["type"],
            "domain": mapped["domain"],
            "priority": mapped["priority"],
            "status": "TODO",
            "description": (issue.get("body") or "")[:500],
            "dependencies": [f"gh#{d}" for d in deps],
        }
        tasks.append(task)

    print(f"Ingested {len(tasks)} issues as kanban tasks.")
    return tasks


def save_tasks(tasks: list[dict]) -> None:
    """Append tasks to kanban_state.json."""
    state = {"tasks": [], "config": {}}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass

    existing_gh_issues = {
        t.get("github_issue") for t in state.get("tasks", [])
        if t.get("github_issue")
    }

    added = 0
    max_id = max((t.get("id", 0) for t in state.get("tasks", [])), default=0)
    for task in tasks:
        if task["github_issue"] in existing_gh_issues:
            continue
        max_id += 1
        task["id"] = max_id
        state.setdefault("tasks", []).append(task)
        added += 1

    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(f"Added {added} new tasks ({len(tasks) - added} already existed).")


def sync_status(close_on_done: bool = False) -> None:
    """Sync kanban task status back to GitHub Issues."""
    if not STATE_FILE.exists():
        print("No kanban state found.")
        return

    state = json.loads(STATE_FILE.read_text())
    for task in state.get("tasks", []):
        gh_num = task.get("github_issue")
        if not gh_num:
            continue

        status = task.get("status", "TODO")
        comment = f"Kanban status updated to: **{status}**"

        if status == "DONE" and close_on_done:
            subprocess.run(
                ["gh", "issue", "close", str(gh_num), "--comment", comment],
                capture_output=True, text=True, timeout=15,
            )
            print(f"  Closed GitHub Issue #{gh_num} (task DONE)")
        elif status in ("IN_PROGRESS", "REVIEW"):
            subprocess.run(
                ["gh", "issue", "comment", str(gh_num), "--body", comment],
                capture_output=True, text=True, timeout=15,
            )
            print(f"  Commented on GitHub Issue #{gh_num}: {status}")


def main():
    parser = argparse.ArgumentParser(description="GitHub Issues ↔ Kanban sync")
    subparsers = parser.add_subparsers(dest="command")

    pull_parser = subparsers.add_parser("pull", help="Fetch issues from GitHub")
    pull_parser.add_argument("--label", help="Filter by label")
    pull_parser.add_argument("--limit", type=int, default=50, help="Max issues to fetch")
    pull_parser.add_argument("--state", default="open", choices=["open", "closed", "all"])

    subparsers.add_parser("ingest", help="Convert pulled issues to kanban tasks")

    sync_parser = subparsers.add_parser("sync-status", help="Sync task status to GitHub")
    sync_parser.add_argument("--close-on-done", action="store_true",
                             help="Close GitHub Issues when task is DONE")

    args = parser.parse_args()

    if not check_gh_cli():
        sys.exit(1)

    if args.command == "pull":
        issues = pull_issues(label=args.label, limit=args.limit, state=args.state)
        # Cache pulled issues for ingest
        cache_file = SKILL_DIR / "memory" / "logs" / "pulled_issues.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(issues, indent=2))
        print(f"Cached to {cache_file}")

    elif args.command == "ingest":
        cache_file = SKILL_DIR / "memory" / "logs" / "pulled_issues.json"
        if not cache_file.exists():
            print("No cached issues. Run 'pull' first.")
            sys.exit(1)
        issues = json.loads(cache_file.read_text())
        tasks = ingest_issues(issues)
        save_tasks(tasks)

    elif args.command == "sync-status":
        sync_status(close_on_done=args.close_on_done)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
