#!/usr/bin/env python3
"""
Project Documentation MCP Server

Provides tools for reading, writing, querying, and managing project documentation.
Serves as the shared data layer for prd-generator, technical-planner, and project-manager skills.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import run_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configuration
CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

config = load_config()

# Resolve project root
PROJECT_ROOT = Path(config.get("project_root", str(Path(__file__).resolve().parents[3])))
DOCS_DIR = PROJECT_ROOT / "docs"
CODING_IMPL_DIR = DOCS_DIR / "coding_implementations"
ARCHITECTURE_DIR = DOCS_DIR / "architecture"
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"

server = Server("project-docs-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_documents",
            description=(
                "List all project documentation files. "
                "Optionally filter by directory: 'coding_implementations', 'architecture', or 'all'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "enum": ["coding_implementations", "architecture", "all"],
                        "default": "all",
                        "description": "Which documentation directory to list"
                    }
                }
            }
        ),
        Tool(
            name="read_document",
            description="Read a project documentation file by name or relative path within docs/.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from docs/ directory (e.g., 'coding_implementations/product_requirements_document.md')"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="write_document",
            description=(
                "Create or overwrite a documentation file. "
                "Use for generating new PRDs, implementation plans, or other docs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from docs/ directory"
                    },
                    "content": {
                        "type": "string",
                        "description": "Full markdown content to write"
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "default": True,
                        "description": "Create parent directories if they don't exist"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="update_document_section",
            description=(
                "Update a specific section of a documentation file. "
                "Finds the section by heading text and replaces its content."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from docs/ directory"
                    },
                    "section_heading": {
                        "type": "string",
                        "description": "The heading text to find (e.g., '## 4. Key Features')"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New content for this section (heading + body). Must include the heading line."
                    }
                },
                "required": ["path", "section_heading", "new_content"]
            }
        ),
        Tool(
            name="query_features",
            description=(
                "Query the feature roadmap (nice_to_haves.md). "
                "Search by keyword, group name, or classification (Essential, Premium, Marketplace)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword or phrase"
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["Essential", "Premium", "Marketplace", "all"],
                        "default": "all",
                        "description": "Filter by feature classification"
                    },
                    "group": {
                        "type": "string",
                        "description": "Filter by group name (e.g., 'Security', 'Document', 'UI')"
                    }
                }
            }
        ),
        Tool(
            name="get_project_context",
            description=(
                "Get a summary of the current project state: "
                "existing PRDs, implementation plans, kanban status, and skill inventory."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_prd_template",
            description="Get the PRD template structure based on the project's standard format.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_plan_template",
            description="Get the technical implementation plan template structure.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "list_documents":
            return await _list_documents(arguments.get("directory", "all"))
        elif name == "read_document":
            return await _read_document(arguments["path"])
        elif name == "write_document":
            return await _write_document(
                arguments["path"],
                arguments["content"],
                arguments.get("create_dirs", True)
            )
        elif name == "update_document_section":
            return await _update_document_section(
                arguments["path"],
                arguments["section_heading"],
                arguments["new_content"]
            )
        elif name == "query_features":
            return await _query_features(
                arguments.get("query", ""),
                arguments.get("classification", "all"),
                arguments.get("group", "")
            )
        elif name == "get_project_context":
            return await _get_project_context()
        elif name == "get_prd_template":
            return await _get_prd_template()
        elif name == "get_plan_template":
            return await _get_plan_template()
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _list_documents(directory: str) -> list[TextContent]:
    """List documentation files."""
    results = []

    dirs_to_scan = []
    if directory in ("coding_implementations", "all"):
        dirs_to_scan.append(("coding_implementations", CODING_IMPL_DIR))
    if directory in ("architecture", "all"):
        dirs_to_scan.append(("architecture", ARCHITECTURE_DIR))
    if directory == "all":
        # Also check top-level docs
        for f in DOCS_DIR.glob("*.md"):
            results.append(f"docs/{f.name}")

    for label, dir_path in dirs_to_scan:
        if dir_path.exists():
            for f in sorted(dir_path.rglob("*.md")):
                rel = f.relative_to(DOCS_DIR)
                size_kb = f.stat().st_size / 1024
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                results.append(f"docs/{rel}  ({size_kb:.1f} KB, modified {mtime})")

    if not results:
        return [TextContent(type="text", text="No documentation files found.")]

    return [TextContent(type="text", text="\n".join(results))]


async def _read_document(path: str) -> list[TextContent]:
    """Read a documentation file."""
    # Normalize path
    if path.startswith("docs/"):
        path = path[5:]

    full_path = DOCS_DIR / path
    if not full_path.exists():
        return [TextContent(type="text", text=f"File not found: docs/{path}")]

    # Security: ensure path is within docs/
    try:
        full_path.resolve().relative_to(DOCS_DIR.resolve())
    except ValueError:
        return [TextContent(type="text", text="Error: Path traversal not allowed")]

    content = full_path.read_text(encoding="utf-8")
    return [TextContent(type="text", text=content)]


async def _write_document(path: str, content: str, create_dirs: bool) -> list[TextContent]:
    """Write a documentation file."""
    if path.startswith("docs/"):
        path = path[5:]

    full_path = DOCS_DIR / path

    # Security: ensure path is within docs/
    try:
        full_path.resolve().relative_to(DOCS_DIR.resolve())
    except ValueError:
        return [TextContent(type="text", text="Error: Path traversal not allowed")]

    if create_dirs:
        full_path.parent.mkdir(parents=True, exist_ok=True)

    full_path.write_text(content, encoding="utf-8")

    size_kb = full_path.stat().st_size / 1024
    return [TextContent(
        type="text",
        text=f"Written: docs/{path} ({size_kb:.1f} KB)"
    )]


async def _update_document_section(
    path: str, section_heading: str, new_content: str
) -> list[TextContent]:
    """Update a specific section of a document."""
    if path.startswith("docs/"):
        path = path[5:]

    full_path = DOCS_DIR / path
    if not full_path.exists():
        return [TextContent(type="text", text=f"File not found: docs/{path}")]

    try:
        full_path.resolve().relative_to(DOCS_DIR.resolve())
    except ValueError:
        return [TextContent(type="text", text="Error: Path traversal not allowed")]

    content = full_path.read_text(encoding="utf-8")

    # Find the section
    # Determine heading level from the section_heading
    heading_match = re.match(r'^(#+)\s+', section_heading)
    if not heading_match:
        return [TextContent(type="text", text=f"Invalid heading format: {section_heading}")]

    heading_level = len(heading_match.group(1))
    heading_text = section_heading.strip()

    # Find the section start
    lines = content.split('\n')
    section_start = None
    section_end = None

    for i, line in enumerate(lines):
        if line.strip() == heading_text:
            section_start = i
            continue
        if section_start is not None and section_end is None:
            # Find the next heading at the same or higher level
            line_heading_match = re.match(r'^(#+)\s+', line)
            if line_heading_match and len(line_heading_match.group(1)) <= heading_level:
                section_end = i
                break

    if section_start is None:
        return [TextContent(
            type="text",
            text=f"Section not found: '{heading_text}'"
        )]

    if section_end is None:
        section_end = len(lines)

    # Replace the section
    new_lines = lines[:section_start] + new_content.strip().split('\n') + lines[section_end:]
    full_path.write_text('\n'.join(new_lines), encoding="utf-8")

    return [TextContent(
        type="text",
        text=f"Updated section '{heading_text}' in docs/{path}"
    )]


async def _query_features(query: str, classification: str, group: str) -> list[TextContent]:
    """Query the feature roadmap."""
    roadmap_path = CODING_IMPL_DIR / "nice_to_haves.md"
    if not roadmap_path.exists():
        return [TextContent(type="text", text="Feature roadmap not found")]

    content = roadmap_path.read_text(encoding="utf-8")
    lines = content.split('\n')

    results = []
    current_group = ""

    for line in lines:
        # Track current group
        group_match = re.match(r'^## Group \d+: (.+?)(?:\s*\(|$)', line)
        if group_match:
            current_group = group_match.group(1).strip()
            continue

        # Match numbered feature lines
        feature_match = re.match(r'^\d+[a-z]?\.\s+\*\*(.+?)\*\*', line)
        if not feature_match:
            continue

        feature_name = feature_match.group(1)
        feature_line = line.strip()

        # Apply filters
        if group and group.lower() not in current_group.lower():
            continue

        if classification != "all":
            if classification == "Marketplace":
                if "marketplace candidate" not in feature_line.lower():
                    continue
            elif classification == "Premium":
                if "premium" not in feature_line.lower() and "paid" not in feature_line.lower():
                    continue
            elif classification == "Essential":
                if "essential" not in feature_line.lower() and "marketplace" in feature_line.lower():
                    continue

        if query:
            if query.lower() not in feature_line.lower() and query.lower() not in feature_name.lower():
                continue

        results.append(f"[{current_group}] {feature_name}\n  {feature_line[:200]}...")

    if not results:
        return [TextContent(type="text", text="No matching features found.")]

    return [TextContent(type="text", text=f"Found {len(results)} features:\n\n" + "\n\n".join(results))]


async def _get_project_context() -> list[TextContent]:
    """Get current project state summary."""
    context_parts = []

    # List existing PRDs and plans
    context_parts.append("## Documentation")
    if CODING_IMPL_DIR.exists():
        for f in sorted(CODING_IMPL_DIR.glob("*.md")):
            size_kb = f.stat().st_size / 1024
            context_parts.append(f"- docs/coding_implementations/{f.name} ({size_kb:.1f} KB)")

    if ARCHITECTURE_DIR.exists():
        for f in sorted(ARCHITECTURE_DIR.glob("*.md")):
            size_kb = f.stat().st_size / 1024
            context_parts.append(f"- docs/architecture/{f.name} ({size_kb:.1f} KB)")

    # Kanban state
    kanban_state = SKILLS_DIR / "project-manager" / "kanban_state.json"
    if kanban_state.exists():
        with open(kanban_state) as f:
            state = json.load(f)
        tasks = state.get("tasks", {})
        context_parts.append("\n## Kanban Board Summary")
        context_parts.append(f"- Backlog: {len(tasks.get('backlog', []))} tasks")
        context_parts.append(f"- In Progress: {len(tasks.get('in_progress', []))} tasks")
        context_parts.append(f"- Review: {len(tasks.get('review', []))} tasks")
        context_parts.append(f"- Done: {len(tasks.get('done', []))} tasks")

    # Skills inventory
    context_parts.append("\n## Skills")
    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / "SKILL.md" if skill_dir.is_dir() else None
            if skill_file and skill_file.exists():
                # Read first line of description
                skill_content = skill_file.read_text()
                desc_match = re.search(r'^## Description\n(.+?)$', skill_content, re.MULTILINE)
                desc = desc_match.group(1).strip() if desc_match else "No description"
                context_parts.append(f"- {skill_dir.name}: {desc[:100]}")

    return [TextContent(type="text", text="\n".join(context_parts))]


async def _get_prd_template() -> list[TextContent]:
    """Return the PRD template structure."""
    template = """# Product Requirements Document (PRD): [Product Name]

## 1. Introduction
**[Product Name]** is [one-sentence description]. [Licensing info]. [Key technology summary].

## 2. Target Audience
- **[Persona 1]:** [Description and needs]
- **[Persona 2]:** [Description and needs]
- **[Persona 3]:** [Description and needs]

## 3. Scope & Constraints
- **Jurisdictions/Markets:** [Geographic or market scope]
- **Licensing:** [License type and implications]
- **Deployment:** [Deployment model -- local-first, cloud, hybrid]
- **Security:** [Key security constraints]

## 4. Key Features

### 4.1. [Feature Name]
- [Feature description]
- [Key capabilities]
- [User interaction model]

### 4.2. [Feature Name]
- [Feature description]
- [Key capabilities]
- [User interaction model]

(Continue for all features...)

## 5. User Stories
1. *As a [persona], I want [action] so that [benefit].*
2. *As a [persona], I want [action] so that [benefit].*
(Continue for all stories...)

## 6. Technical Requirements
- **Backend:** [Technology choices]
- **Frontend:** [Technology choices]
- **AI Models:** [Model names and purposes]
- **Data:** [Storage, APIs, integrations]
- **Privacy:** [Privacy implementation approach]

## 7. Success Metrics
- **[Metric Category]:** [Specific measurable target]
- **[Metric Category]:** [Specific measurable target]
- **[Metric Category]:** [Specific measurable target]
"""
    return [TextContent(type="text", text=template)]


async def _get_plan_template() -> list[TextContent]:
    """Return the technical implementation plan template."""
    template = """# Technical Implementation Plan: [Feature/Product Name]

## Overview
[Brief description of what is being built and why. Reference the source PRD if applicable.]

## Architecture
[High-level architecture description. Include component diagram in Mermaid if complex.]

```mermaid
graph TB
    A[Component A] --> B[Component B]
    B --> C[Component C]
```

## Phase 1: [Phase Name]
**Objective:** [What this phase achieves]
**Depends on:** [Previous phases or external dependencies, or "None"]

### Implementation Steps
1. [Actionable step with specific file/module references]
2. [Actionable step]
3. [Actionable step]

### Files
- `path/to/new_file.py` - [Purpose] (CREATE)
- `path/to/existing_file.py` - [What changes] (MODIFY)

### API Contracts (if applicable)
- `POST /api/v1/endpoint` - [Description]
  - Request: `{ field: type }`
  - Response: `{ field: type }`

---

## Phase 2: [Phase Name]
(Same structure as Phase 1...)

---

## Dependency Graph
```mermaid
graph LR
    P1[Phase 1] --> P2[Phase 2]
    P2 --> P3[Phase 3]
    P1 --> P4[Phase 4]
```

## Risk Assessment
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk description] | High/Med/Low | High/Med/Low | [Mitigation strategy] |

## Success Criteria
- [ ] [Measurable criterion 1]
- [ ] [Measurable criterion 2]
- [ ] [Measurable criterion 3]
"""
    return [TextContent(type="text", text=template)]


async def main():
    """Run the MCP server."""
    await run_server(server)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
