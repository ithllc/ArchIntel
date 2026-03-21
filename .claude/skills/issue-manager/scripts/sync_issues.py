#!/usr/bin/env python3
"""
sync_issues.py - "The Courier"
Sync locally collected issues to/from GitHub Issues for the current repository.
"""

import json
import subprocess
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

SKILL_DIR = Path(__file__).parent.parent
SYNC_LOG = SKILL_DIR / "memory" / "logs" / "sync_history.jsonl"

SEVERITY_LABEL_MAP = {
    "Blocker": "severity:blocker",
    "Major": "severity:major",
    "Moderate": "severity:moderate",
    "Minor": "severity:minor",
    "Cosmetic": "severity:cosmetic",
}

TYPE_LABEL_MAP = {
    "Bug": ["bug"],
    "Missing feature": ["enhancement"],
    "Missing Feature": ["enhancement"],
    "UX overlap": ["ux", "enhancement"],
    "UX Overlap": ["ux", "enhancement"],
    "Architecture gap": ["architecture", "enhancement"],
    "Architecture Gap": ["architecture", "enhancement"],
    "Testing gap": ["testing"],
    "Testing Gap": ["testing"],
    "Testing need": ["testing", "enhancement"],
    "Testing Need": ["testing", "enhancement"],
    "Missing behavior": ["enhancement"],
    "Missing Behavior": ["enhancement"],
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
        print("Install: sudo apt install gh && gh auth login")
        return False
    except subprocess.TimeoutExpired:
        return False


def get_repo_info() -> Optional[str]:
    """Detect GitHub repository from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
        url = result.stdout.strip()
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        return match.group(1) if match else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def parse_issues_log(log_path: Path) -> list[dict]:
    """Parse a local issues log markdown file into structured issue dicts."""
    if not log_path.exists():
        print(f"Issues log not found: {log_path}")
        return []

    content = log_path.read_text()
    issues = []

    # Parse the summary table
    table_pattern = re.compile(
        r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
    )

    for match in table_pattern.finditer(content):
        num, title, issue_type, severity, dependency, status = match.groups()
        if num.strip() == "#" or num.strip() == "---":
            continue
        issues.append({
            "number": int(num.strip()),
            "title": title.strip(),
            "type": issue_type.strip(),
            "severity": severity.strip(),
            "dependency": dependency.strip(),
            "status": status.strip(),
        })

    # Parse detailed descriptions
    detail_sections = re.split(r"### Issue (\d+):", content)
    details_map = {}
    for i in range(1, len(detail_sections), 2):
        issue_num = int(detail_sections[i].strip())
        detail_text = detail_sections[i + 1].strip() if i + 1 < len(detail_sections) else ""
        details_map[issue_num] = detail_text

    for issue in issues:
        issue["detail"] = details_map.get(issue["number"], "")

    return issues


def create_github_issue(issue: dict, issue_number_map: dict[int, int]) -> Optional[int]:
    """Create a single GitHub Issue. Returns the created issue number."""
    labels = []

    # Type labels
    type_labels = TYPE_LABEL_MAP.get(issue["type"], [])
    labels.extend(type_labels)

    # Severity label
    severity_label = SEVERITY_LABEL_MAP.get(issue["severity"])
    if severity_label:
        labels.append(severity_label)

    # Build body
    body_parts = [f"**Type:** {issue['type']}", f"**Severity:** {issue['severity']}"]

    if issue["dependency"] and issue["dependency"] != "\u2014":
        dep_match = re.search(r"#(\d+)", issue["dependency"])
        if dep_match:
            local_dep = int(dep_match.group(1))
            if local_dep in issue_number_map:
                body_parts.append(f"\nDepends on #{issue_number_map[local_dep]}")
            else:
                body_parts.append(f"\nDepends on local issue #{local_dep}")

    if issue.get("detail"):
        body_parts.append(f"\n---\n\n{issue['detail']}")

    body = "\n".join(body_parts)

    # Build command
    cmd = [
        "gh", "issue", "create",
        "--title", issue["title"],
        "--body", body,
    ]
    for label in labels:
        cmd.extend(["--label", label])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        print(f"  FAILED to create issue: {result.stderr.strip()}")
        return None

    # Extract issue number from URL output
    url = result.stdout.strip()
    num_match = re.search(r"/issues/(\d+)", url)
    if num_match:
        gh_num = int(num_match.group(1))
        print(f"  Created GitHub Issue #{gh_num}: {issue['title']}")
        return gh_num

    print(f"  Created issue but couldn't parse number: {url}")
    return None


def push_issues(log_path: Path) -> None:
    """Push local issues to GitHub."""
    issues = parse_issues_log(log_path)
    if not issues:
        print("No issues found in log.")
        return

    print(f"Pushing {len(issues)} issues to GitHub...")

    # Track local→GitHub number mapping for dependencies
    number_map: dict[int, int] = {}

    for issue in issues:
        gh_num = create_github_issue(issue, number_map)
        if gh_num:
            number_map[issue["number"]] = gh_num

    # Log sync
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "push",
        "source": str(log_path),
        "issues_pushed": len(number_map),
        "mapping": {str(k): v for k, v in number_map.items()},
    }
    SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"\nDone. Pushed {len(number_map)}/{len(issues)} issues to GitHub.")


def pull_issues(limit: int = 50, state: str = "open") -> None:
    """Pull and display GitHub Issues."""
    cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return

    print(result.stdout)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "pull",
        "state": state,
        "limit": limit,
    }
    SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def sync_status() -> None:
    """Show sync status between local logs and GitHub."""
    repo = get_repo_info()
    print(f"Repository: {repo or 'unknown'}")

    if SYNC_LOG.exists():
        lines = SYNC_LOG.read_text().strip().split("\n")
        if lines:
            last = json.loads(lines[-1])
            print(f"Last sync: {last['timestamp']} ({last['action']})")
        print(f"Total sync operations: {len(lines)}")
    else:
        print("No sync history found.")


def main():
    parser = argparse.ArgumentParser(description="Issue Manager GitHub Sync")
    subparsers = parser.add_subparsers(dest="command")

    push_parser = subparsers.add_parser("push", help="Push local issues to GitHub")
    push_parser.add_argument("--log", required=True, help="Path to local issues log markdown")

    pull_parser = subparsers.add_parser("pull", help="Pull GitHub Issues")
    pull_parser.add_argument("--limit", type=int, default=50)
    pull_parser.add_argument("--state", default="open", choices=["open", "closed", "all"])

    subparsers.add_parser("status", help="Show sync status")

    args = parser.parse_args()

    if not check_gh_cli():
        sys.exit(1)

    if args.command == "push":
        push_issues(Path(args.log))
    elif args.command == "pull":
        pull_issues(limit=args.limit, state=args.state)
    elif args.command == "status":
        sync_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
