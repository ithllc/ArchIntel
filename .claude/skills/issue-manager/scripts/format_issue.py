#!/usr/bin/env python3
"""
format_issue.py - "The Formatter"
Format issue data into GitHub-compatible markdown for issue bodies.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).parent.parent


def format_github_body(issue: dict) -> str:
    """Format a single issue dict into a GitHub Issue body."""
    parts = []

    # Metadata header
    parts.append(f"**Type:** {issue.get('type', 'Unknown')}")
    parts.append(f"**Severity:** {issue.get('severity', 'Unknown')}")
    parts.append(f"**Feature:** {issue.get('feature', 'Unknown')}")

    # Dependency
    dep = issue.get("dependency", "")
    if dep and dep != "\u2014" and dep != "—":
        parts.append(f"**Dependency:** {dep}")

    parts.append("")
    parts.append("---")
    parts.append("")

    # Description
    if issue.get("description"):
        parts.append("## Description")
        parts.append(issue["description"])
        parts.append("")

    # Steps to reproduce
    if issue.get("steps_to_reproduce"):
        parts.append("## Steps to Reproduce")
        for step in issue["steps_to_reproduce"]:
            parts.append(f"1. {step}")
        parts.append("")

    # Expected behavior
    if issue.get("expected"):
        parts.append("## Expected Behavior")
        parts.append(issue["expected"])
        parts.append("")

    # Root cause
    if issue.get("root_cause"):
        parts.append("## Root Cause Analysis")
        parts.append(issue["root_cause"])
        parts.append("")

    # Impact
    if issue.get("impact"):
        parts.append("## Impact")
        parts.append(issue["impact"])
        parts.append("")

    return "\n".join(parts)


def format_local_detail(issue: dict) -> str:
    """Format a single issue dict into local issues log detail section."""
    parts = []

    title = issue.get("title", f"Issue {issue.get('number', '?')}")
    parts.append(f"### Issue {issue.get('number', '?')}: {title}")

    if issue.get("feature"):
        parts.append(f"**Feature:** {issue['feature']}")

    if issue.get("description"):
        parts.append(f"**Description:** {issue['description']}")

    if issue.get("expected"):
        parts.append(f"**Expected:** {issue['expected']}")

    if issue.get("root_cause"):
        parts.append(f"**Root Cause (suspected):** {issue['root_cause']}")

    if issue.get("impact"):
        parts.append(f"**Impact:** {issue['impact']}")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Format issue data")
    parser.add_argument("--format", choices=["github", "local"], default="github",
                        help="Output format")
    parser.add_argument("--input", required=True, help="Path to JSON issue data")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    data = json.loads(input_path.read_text())

    issues = data if isinstance(data, list) else [data]

    for issue in issues:
        if args.format == "github":
            print(format_github_body(issue))
        else:
            print(format_local_detail(issue))
        print()


if __name__ == "__main__":
    main()
