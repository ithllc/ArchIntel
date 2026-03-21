#!/usr/bin/env python3
"""
Technical Plan Generator - Produces implementation plans from PRD analysis.

Takes structured planning data (from interactive interview or PRD analysis)
and generates a phased technical implementation plan that can be ingested
by the project-manager skill.

Portable: No project-specific dependencies. Works with any Claude Code project.
"""

import json
import sys
from pathlib import Path
from typing import Any


def find_output_dir() -> Path:
    """Find or create the output directory for plans."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".git").exists() or (current / ".claude").exists():
            output = current / "docs" / "coding_implementations"
            output.mkdir(parents=True, exist_ok=True)
            return output
        current = current.parent
    output = Path.cwd() / "docs" / "coding_implementations"
    output.mkdir(parents=True, exist_ok=True)
    return output


def generate_plan(data: dict[str, Any]) -> str:
    """
    Generate a technical implementation plan from structured data.

    Args:
        data: Dictionary with keys:
            - product_name: str
            - overview: str
            - architecture: dict with 'description' and optional 'mermaid_diagram'
            - phases: list[dict] each with:
                - name: str
                - objective: str
                - depends_on: list[str]
                - steps: list[str]
                - files: list[dict] with 'path', 'purpose', 'action' (CREATE/MODIFY)
                - api_contracts: list[dict] (optional)
            - dependency_graph: str (optional, mermaid syntax)
            - risks: list[dict] with 'risk', 'impact', 'likelihood', 'mitigation'
            - success_criteria: list[str]

    Returns:
        Formatted markdown string
    """
    sections = []

    product_name = data.get("product_name", "Untitled")
    sections.append(f"# Technical Implementation Plan: {product_name}\n")

    # Overview
    sections.append("## Overview")
    sections.append(data.get("overview", "[Overview to be written]"))
    sections.append("")

    # Architecture
    sections.append("## Architecture")
    arch = data.get("architecture", {})
    sections.append(arch.get("description", "[Architecture description to be written]"))
    if arch.get("mermaid_diagram"):
        sections.append("")
        sections.append("```mermaid")
        sections.append(arch["mermaid_diagram"])
        sections.append("```")
    sections.append("")

    # Phases
    phases = data.get("phases", [])
    for i, phase in enumerate(phases, 1):
        name = phase.get("name", f"Phase {i}")
        objective = phase.get("objective", "[Objective TBD]")
        depends_on = phase.get("depends_on", [])

        sections.append(f"## Phase {i}: {name}")
        sections.append(f"**Objective:** {objective}")
        dep_text = ", ".join(depends_on) if depends_on else "None"
        sections.append(f"**Depends on:** {dep_text}")
        sections.append("")

        steps = phase.get("steps", [])
        if steps:
            sections.append("### Implementation Steps")
            for j, step in enumerate(steps, 1):
                sections.append(f"{j}. {step}")
            sections.append("")

        files = phase.get("files", [])
        if files:
            sections.append("### Files")
            for f in files:
                path = f.get("path", "")
                purpose = f.get("purpose", "")
                action = f.get("action", "CREATE")
                sections.append(f"- `{path}` - {purpose} ({action})")
            sections.append("")

        apis = phase.get("api_contracts", [])
        if apis:
            sections.append("### API Contracts")
            for api in apis:
                method = api.get("method", "GET")
                endpoint = api.get("endpoint", "/api/v1/unknown")
                desc = api.get("description", "")
                sections.append(f"- `{method} {endpoint}` - {desc}")
                if api.get("request"):
                    sections.append(f"  - Request: `{api['request']}`")
                if api.get("response"):
                    sections.append(f"  - Response: `{api['response']}`")
            sections.append("")

        sections.append("---\n")

    # Dependency graph
    if data.get("dependency_graph"):
        sections.append("## Dependency Graph")
        sections.append("```mermaid")
        sections.append(data["dependency_graph"])
        sections.append("```")
        sections.append("")
    elif len(phases) > 1:
        sections.append("## Dependency Graph")
        sections.append("```mermaid")
        sections.append("graph LR")
        for i, phase in enumerate(phases, 1):
            for dep in phase.get("depends_on", []):
                for j, other_phase in enumerate(phases, 1):
                    if other_phase["name"].lower() in dep.lower() or f"phase {j}" in dep.lower():
                        sections.append(f"    P{j}[{other_phase['name']}] --> P{i}[{phase['name']}]")
                        break
        sections.append("```")
        sections.append("")

    # Risk assessment
    risks = data.get("risks", [])
    if risks:
        sections.append("## Risk Assessment")
        sections.append("| Risk | Impact | Likelihood | Mitigation |")
        sections.append("|------|--------|------------|------------|")
        for risk in risks:
            sections.append(
                f"| {risk.get('risk', '')} | {risk.get('impact', 'Med')} "
                f"| {risk.get('likelihood', 'Med')} | {risk.get('mitigation', '')} |"
            )
        sections.append("")

    # Success criteria
    criteria = data.get("success_criteria", [])
    if criteria:
        sections.append("## Success Criteria")
        for criterion in criteria:
            sections.append(f"- [ ] {criterion}")
        sections.append("")

    return "\n".join(sections)


def save_plan(content: str, filename: str) -> Path:
    """Save the plan to the output directory."""
    output_dir = find_output_dir()
    if not filename.endswith(".md"):
        filename += ".md"
    output_path = output_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main():
    """CLI entry point. Reads JSON from stdin or file argument."""
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        if not input_path.exists():
            print(f"Error: File not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(input_path.read_text())
    else:
        data = json.load(sys.stdin)

    plan_content = generate_plan(data)

    product_name = data.get("product_name", "untitled")
    safe_name = product_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"technical_implementation_plan_{safe_name}.md"

    output_path = save_plan(plan_content, filename)
    print(f"Plan written to: {output_path}")
    print(plan_content)


if __name__ == "__main__":
    main()
