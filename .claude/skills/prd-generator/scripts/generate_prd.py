#!/usr/bin/env python3
"""
PRD Generator - Produces a Product Requirements Document from structured interview data.

This script is called by the prd-generator skill after gathering requirements
from the user through interactive conversation. It takes a JSON input of
gathered requirements and produces a formatted markdown PRD.

Portable: No project-specific dependencies. Works with any Claude Code project.
"""

import json
import sys
from pathlib import Path
from typing import Any


def find_output_dir() -> Path:
    """Find or create the output directory for PRDs."""
    # Walk up from script location to find project root (look for .git or .claude)
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".git").exists() or (current / ".claude").exists():
            output = current / "docs" / "coding_implementations"
            output.mkdir(parents=True, exist_ok=True)
            return output
        current = current.parent
    # Fallback: use cwd
    output = Path.cwd() / "docs" / "coding_implementations"
    output.mkdir(parents=True, exist_ok=True)
    return output


def generate_prd(data: dict[str, Any]) -> str:
    """
    Generate a PRD markdown document from structured data.

    Args:
        data: Dictionary with keys matching the interview phases:
            - product_name: str
            - elevator_pitch: str
            - problem_statement: str
            - is_new_product: bool
            - target_audience: list[dict] with 'persona' and 'description'
            - scope: dict with 'jurisdictions', 'licensing', 'deployment', 'security'
            - out_of_scope: list[str]
            - features: list[dict] with 'name', 'description', 'interaction', 'ai_models'
            - user_stories: list[str]
            - tech_stack: dict with 'backend', 'frontend', 'ai_models', 'data', 'privacy'
            - success_metrics: list[dict] with 'category' and 'target'
            - accessibility: str (optional)

    Returns:
        Formatted markdown string
    """
    sections = []

    # Title
    product_name = data.get("product_name", "Untitled Product")
    sections.append(f"# Product Requirements Document (PRD): {product_name}\n")

    # Section 1: Introduction
    sections.append("## 1. Introduction")
    pitch = data.get("elevator_pitch", "[Description needed]")
    problem = data.get("problem_statement", "")
    licensing = data.get("scope", {}).get("licensing", "")

    intro_parts = [f"**{product_name}** is {pitch}"]
    if licensing:
        intro_parts.append(f"Distributed under the **{licensing}**.")
    if problem:
        intro_parts.append(f"It addresses the following problem: {problem}")
    sections.append(" ".join(intro_parts) + "\n")

    # Section 2: Target Audience
    sections.append("## 2. Target Audience")
    audiences = data.get("target_audience", [])
    if audiences:
        for audience in audiences:
            persona = audience.get("persona", "User")
            desc = audience.get("description", "")
            sections.append(f"- **{persona}:** {desc}")
    else:
        sections.append("- [Target audience to be defined]")
    sections.append("")

    # Section 3: Scope & Constraints
    sections.append("## 3. Scope & Constraints")
    scope = data.get("scope", {})
    sections.append(f"- **Jurisdictions/Markets:** {scope.get('jurisdictions', '[TBD]')}")
    sections.append(f"- **Licensing:** **{scope.get('licensing', '[TBD]')}**.")
    sections.append(f"- **Deployment:** **{scope.get('deployment', '[TBD]')}**.")
    sections.append(f"- **Security:** {scope.get('security', '[TBD]')}")

    out_of_scope = data.get("out_of_scope", [])
    if out_of_scope:
        sections.append("\n**Out of Scope:**")
        for item in out_of_scope:
            sections.append(f"- {item}")
    sections.append("")

    # Section 4: Key Features
    sections.append("## 4. Key Features\n")
    features = data.get("features", [])
    if features:
        for i, feature in enumerate(features, 1):
            name = feature.get("name", f"Feature {i}")
            desc = feature.get("description", "")
            interaction = feature.get("interaction", "")
            ai_models = feature.get("ai_models", "")

            sections.append(f"### 4.{i}. {name}")
            if desc:
                sections.append(f"- {desc}")
            if interaction:
                sections.append(f"- **User Interaction:** {interaction}")
            if ai_models:
                sections.append(f"- **AI/Models:** {ai_models}")
            sections.append("")
    else:
        sections.append("### 4.1. [Feature to be defined]\n")

    # Section 5: User Stories
    sections.append("## 5. User Stories")
    stories = data.get("user_stories", [])
    if stories:
        for i, story in enumerate(stories, 1):
            sections.append(f"{i}.  *{story}*")
    else:
        sections.append("1.  *[User stories to be defined]*")
    sections.append("")

    # Section 6: Technical Requirements
    sections.append("## 6. Technical Requirements")
    tech = data.get("tech_stack", {})
    sections.append(f"- **Backend:** {tech.get('backend', '[TBD]')}.")
    sections.append(f"- **Frontend:** {tech.get('frontend', '[TBD]')}.")
    sections.append(f"- **AI Models:** {tech.get('ai_models', '[TBD]')}.")
    sections.append(f"- **Data:** {tech.get('data', '[TBD]')}.")
    sections.append(f"- **Privacy:** {tech.get('privacy', '[TBD]')}.")

    accessibility = data.get("accessibility", "")
    if accessibility:
        sections.append(f"- **Accessibility:** {accessibility}.")
    sections.append("")

    # Section 7: Success Metrics
    sections.append("## 7. Success Metrics")
    metrics = data.get("success_metrics", [])
    if metrics:
        for metric in metrics:
            cat = metric.get("category", "Metric")
            target = metric.get("target", "[TBD]")
            sections.append(f"- **{cat}:** {target}")
    else:
        sections.append("- [Success metrics to be defined]")
    sections.append("")

    return "\n".join(sections)


def save_prd(content: str, filename: str) -> Path:
    """Save PRD to the output directory."""
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

    prd_content = generate_prd(data)

    product_name = data.get("product_name", "untitled")
    safe_name = product_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"prd_{safe_name}.md"

    output_path = save_prd(prd_content, filename)
    print(f"PRD written to: {output_path}")
    print(prd_content)


if __name__ == "__main__":
    main()
