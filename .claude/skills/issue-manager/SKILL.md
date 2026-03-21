---
name: issue-manager
description: Conversational issue collection and GitHub Issues management. Conducts structured interviews to identify and document bugs/issues, then syncs them to the remote GitHub repository's Issues tab via gh CLI. Use when logging bugs, reporting issues, or managing GitHub Issues.
---

# Issue Manager Skill ("The Investigator")

## Overview

The Issue Manager conducts **structured conversational interviews** with end users to collect, document, and log issues. It then syncs those issues to the remote GitHub repository's Issues tab using the `gh` CLI. It can also pull existing GitHub Issues for any workspace's associated repository.

## When to Use

- User wants to report bugs, UX problems, or missing features through a guided interview
- User asks to log issues, create a change log, or document problems
- User wants to push locally collected issues to GitHub Issues
- User wants to pull/view existing GitHub Issues for the current repository
- User asks to sync issues between local logs and GitHub

## Quick Start

```bash
# Start an issue collection interview
/issue-manager

# Sync local issues to GitHub
/issue-manager --sync

# Pull GitHub issues for current repo
/issue-manager --pull

# View sync status
/issue-manager --status
```

## Interview Process

### Phase 1: Conversational Collection
1. **Open the interview**: Ask the user what problem they're experiencing
2. **For each issue, collect**:
   - **What's happening** (symptom / observed behavior)
   - **Where it happens** (feature, page, endpoint, component)
   - **Steps to reproduce** (if applicable)
   - **Expected behavior** (what should happen instead)
   - **Severity**: Blocker, Major, Moderate, Minor, Cosmetic
   - **Type**: Bug, Missing Feature, UX Overlap, Architecture Gap, Testing Gap, Testing Need
   - **Dependencies**: Does this issue depend on another issue being resolved first?
   - **Screenshots or error messages** (if available)
3. **Allow tangents**: If the user asks questions about the codebase mid-interview, research and answer — the answers often clarify the issue
4. **Assess technically**: Examine relevant code to confirm root cause and add technical context
5. **Summarize periodically**: Show the running issues table for user review

### Phase 2: Local Issues Log
- Save to `docs/issues/issues_log_YYYY-MM-DD.md`
- Append if log for today already exists
- Include both summary table and detailed descriptions with technical analysis

### Phase 3: GitHub Issues Sync

Requires `gh` CLI installed and authenticated.

**Push to GitHub:**
```bash
gh issue create --title "Issue title" --body "Issue body" --label "bug"
```

**Label Mapping:**

| Local Type | GitHub Labels |
|-----------|--------------|
| Bug | `bug` |
| Missing Feature | `enhancement` |
| UX Overlap | `ux`, `enhancement` |
| Architecture Gap | `architecture`, `enhancement` |
| Testing Gap | `testing` |
| Testing Need | `testing`, `enhancement` |

**Severity Labels:** `severity:blocker`, `severity:major`, `severity:moderate`, `severity:minor`, `severity:cosmetic`

**Dependency Linking:** If issue B depends on issue A, body includes "Depends on #A"

**Pull from GitHub:**
```bash
gh issue list --state open --limit 50
gh issue view <number>
```

**Resolve and View Issue Images:**

GitHub Issues often contain screenshots, wireframes, or mockups as embedded images. These provide critical context for understanding the issue. Always resolve and view them:

1. **Extract image URLs**: Pull the full issue body via REST API to get complete URLs:
   ```bash
   gh api repos/{owner}/{repo}/issues/{number} --jq '.body'
   ```
   Image URLs follow the pattern: `https://github.com/user-attachments/assets/{uuid}`

2. **Download images locally**: GitHub asset URLs redirect to S3. Use `curl -sL` to follow redirects:
   ```bash
   curl -sL -o /tmp/issue{number}_img{n}.png "https://github.com/user-attachments/assets/{uuid}"
   ```

3. **View and interpret**: Use the Read tool on the downloaded file to visually inspect the image. Claude Code is multimodal and can interpret screenshots, wireframes, and hand-drawn mockups.

4. **Incorporate context**: Describe what the image shows in your analysis — layout structure, UI elements, button labels, annotations, flow arrows, etc. This visual context is essential for accurate issue understanding and solution design.

**Why this matters**: Issue descriptions alone are often insufficient. A wireframe may reveal layout intentions, a screenshot may show the exact bug state, and a mockup may define acceptance criteria that text alone cannot convey. Always check for and resolve images before proposing solutions.

**Post Implementation Comments:**

After implementing a fix for a GitHub Issue, ALWAYS post a comment on the issue summarizing:

1. **What was done**: A concise summary of the changes made (files modified, what was added/removed/changed)
2. **How to test**: Step-by-step instructions for the user to verify the fix works as expected
3. **Format**: Use the `gh issue comment` command:
   ```bash
   gh issue comment {number} --body "$(cat <<'EOF'
   ## Implementation Summary
   - [Bullet points describing what was changed]

   ## How to Test
   1. [Step-by-step verification instructions]
   2. [What to look for to confirm the fix]
   EOF
   )"
   ```
4. **When to comment**: Comment immediately after implementation, before moving to the next issue. This ensures traceability between code changes and issue requirements.

**Why this matters**: Comments create an audit trail linking code changes to issue requirements. They enable the issue reporter (or any team member) to independently verify the fix without needing to read the code diff. This is especially critical for UI changes where visual verification is required.

### Phase 4: Project Manager Integration
After issues are logged, suggest `/project` to ingest as kanban tasks with severity-to-priority mapping:
- Blocker → P0
- Major → P1
- Moderate → P2
- Minor → P3
- Cosmetic → P4

## GitHub CLI Prerequisites

Before syncing, the skill verifies:
1. `gh` is installed: `which gh`
2. `gh` is authenticated: `gh auth status`
3. Remote origin exists: `git remote -v`

If any check fails, setup instructions are provided:
```bash
sudo apt install gh
gh auth login  # Browser-based OAuth
```

## Scripts

| Script | Role |
|--------|------|
| `scripts/sync_issues.py` | Sync local issues log to/from GitHub Issues |
| `scripts/format_issue.py` | Format issue data into GitHub-compatible markdown |

## Directory Structure

```
issue-manager/
├── SKILL.md                    # This file
├── scripts/
│   ├── sync_issues.py          # GitHub sync operations
│   └── format_issue.py         # Issue formatting
├── templates/
│   ├── issue_detail.j2         # Local issue detail template
│   └── github_issue_body.j2    # GitHub Issue body template
└── memory/
    ├── learned_context.md      # Patterns from issue sessions
    └── logs/
        └── sync_history.jsonl  # Sync operation log
```

## Integration

- **project-manager**: Issues ingested as kanban tasks via `/project`
- **feedback-helper**: Issue resolutions feed into skill evolution
- **skill-evolution-manager**: Recurring issue patterns improve skill prompts

## See Also

- `/project` — Ingest issues as development tasks
- `/feedback-helper` — Capture learning from issue resolutions
- `docs/issues/` — Local issues log directory
