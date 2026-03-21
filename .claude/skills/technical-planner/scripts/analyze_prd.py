#!/usr/bin/env python3
"""
PRD Analyzer - Extracts implementation requirements from PRD documents.

Parses a PRD markdown file and extracts structured data that can be used
to generate a technical implementation plan. Bridges prd-generator output
to technical-planner input.

Portable: No project-specific dependencies. Works with any Claude Code project.
"""

import re
import json
import sys
from pathlib import Path
from typing import Any, Optional


class PRDAnalyzer:
    """Parse PRD documents into structured planning data."""

    def __init__(self, prd_path: str):
        self.path = Path(prd_path)
        if not self.path.exists():
            raise FileNotFoundError(f"PRD not found: {prd_path}")

        self.content = self.path.read_text(encoding="utf-8")
        self.sections = self._parse_sections()

    def _parse_sections(self) -> dict[str, str]:
        """Parse the PRD into named sections."""
        sections = {}
        lines = self.content.split('\n')
        current_key = "preamble"
        current_lines = []

        for line in lines:
            heading_match = re.match(r'^##\s+\d*\.?\s*(.+)$', line)
            if heading_match:
                if current_lines:
                    sections[current_key] = '\n'.join(current_lines).strip()
                current_key = heading_match.group(1).strip().lower()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_key] = '\n'.join(current_lines).strip()

        return sections

    def extract_product_name(self) -> str:
        """Extract the product name from the title."""
        title_match = re.match(r'^#\s+.*?:\s*(.+)$', self.content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        return "Unknown Product"

    def extract_features(self) -> list[dict[str, str]]:
        """Extract features from Section 4."""
        features = []

        feature_content = ""
        for key, value in self.sections.items():
            if "feature" in key:
                feature_content = value
                break

        if not feature_content:
            return features

        subsections = re.split(r'###\s+\d+\.\d+\.?\s+', feature_content)
        headings = re.findall(r'###\s+\d+\.\d+\.?\s+(.+)', feature_content)

        for name, body in zip(headings, subsections[1:]):
            feature = {"name": name.strip(), "details": body.strip()}

            bullets = re.findall(r'^-\s+(.+)$', body, re.MULTILINE)
            if bullets:
                feature["description"] = bullets[0] if bullets else ""
                feature["bullets"] = bullets

            model_refs = re.findall(
                r'\*\*(?:AI|Models?|Powered by)\*\*[:\s]*(.+?)(?:\.|$)',
                body, re.IGNORECASE
            )
            if model_refs:
                feature["ai_models"] = model_refs[0].strip()

            features.append(feature)

        return features

    def extract_tech_stack(self) -> dict[str, str]:
        """Extract technical requirements from Section 6."""
        tech = {}
        for key, value in self.sections.items():
            if "technical" in key:
                items = re.findall(r'-\s+\*\*(.+?)\*\*[:\s]*(.+?)(?:\.|$)', value, re.MULTILINE)
                for item_key, item_value in items:
                    tech[item_key.lower().strip()] = item_value.strip()
                break
        return tech

    def extract_target_audience(self) -> list[dict[str, str]]:
        """Extract target audience from Section 2."""
        audiences = []
        for key, value in self.sections.items():
            if "audience" in key:
                items = re.findall(r'-\s+\*\*(.+?)\*\*[:\s]*(.+?)$', value, re.MULTILINE)
                for persona, desc in items:
                    audiences.append({"persona": persona.strip(), "description": desc.strip()})
                break
        return audiences

    def extract_scope(self) -> dict[str, str]:
        """Extract scope & constraints from Section 3."""
        scope = {}
        for key, value in self.sections.items():
            if "scope" in key or "constraint" in key:
                items = re.findall(r'-\s+\*\*(.+?)\*\*[:\s]*(.+?)$', value, re.MULTILINE)
                for item_key, item_value in items:
                    scope[item_key.lower().strip()] = item_value.strip().strip('*').strip('.')
                break
        return scope

    def extract_user_stories(self) -> list[str]:
        """Extract user stories from Section 5."""
        stories = []
        for key, value in self.sections.items():
            if "user stor" in key:
                items = re.findall(r'\d+\.\s+\*(.+?)\*', value)
                stories.extend(items)
                break
        return stories

    def extract_success_metrics(self) -> list[dict[str, str]]:
        """Extract success metrics from Section 7."""
        metrics = []
        for key, value in self.sections.items():
            if "success" in key or "metric" in key:
                items = re.findall(r'-\s+\*\*(.+?)\*\*[:\s]*(.+?)$', value, re.MULTILINE)
                for cat, target in items:
                    metrics.append({"category": cat.strip(), "target": target.strip()})
                break
        return metrics

    def to_planning_input(self) -> dict[str, Any]:
        """
        Convert the analyzed PRD into a structure suitable for the technical planner.

        Returns a dict that can be enriched with phase/architecture data
        during the interactive planning session.
        """
        return {
            "product_name": self.extract_product_name(),
            "features": self.extract_features(),
            "tech_stack": self.extract_tech_stack(),
            "target_audience": self.extract_target_audience(),
            "scope": self.extract_scope(),
            "user_stories": self.extract_user_stories(),
            "success_metrics": self.extract_success_metrics(),
            "source_prd": str(self.path),
            # Filled during interactive planning session:
            "overview": "",
            "architecture": {},
            "phases": [],
            "risks": [],
            "success_criteria": []
        }


def main():
    """CLI entry point. Analyze a PRD and output JSON or summary."""
    if len(sys.argv) < 2:
        print("Usage: analyze_prd.py <prd_file> [--json|--summary]", file=sys.stderr)
        sys.exit(1)

    analyzer = PRDAnalyzer(sys.argv[1])
    output_format = sys.argv[2] if len(sys.argv) > 2 else "--summary"

    if output_format == "--json":
        result = analyzer.to_planning_input()
        print(json.dumps(result, indent=2))
    else:
        print(f"Product: {analyzer.extract_product_name()}")
        print(f"\nFeatures ({len(analyzer.extract_features())}):")
        for f in analyzer.extract_features():
            print(f"  - {f['name']}")
        print(f"\nTech Stack:")
        for k, v in analyzer.extract_tech_stack().items():
            print(f"  - {k}: {v}")
        print(f"\nUser Stories: {len(analyzer.extract_user_stories())}")
        print(f"Success Metrics: {len(analyzer.extract_success_metrics())}")
        print(f"\nScope:")
        for k, v in analyzer.extract_scope().items():
            print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
