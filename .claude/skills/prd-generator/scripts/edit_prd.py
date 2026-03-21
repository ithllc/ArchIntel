#!/usr/bin/env python3
"""
PRD Editor - Section-level editing of existing PRD documents.

Parses a PRD into sections, allows targeted edits, and reassembles the document.
Used by the prd-generator skill when updating existing PRDs.

Portable: No project-specific dependencies. Works with any Claude Code project.
"""

import re
import sys
from pathlib import Path
from typing import Optional


class PRDEditor:
    """Parse and edit PRD documents at the section level."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"PRD not found: {file_path}")

        self.content = self.file_path.read_text(encoding="utf-8")
        self.sections = self._parse_sections()

    def _parse_sections(self) -> list[dict]:
        """Parse the PRD into sections based on markdown headings."""
        sections = []
        lines = self.content.split('\n')
        current_section = {"heading": "", "level": 0, "start": 0, "lines": []}

        for i, line in enumerate(lines):
            heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
            if heading_match:
                if current_section["heading"] or current_section["lines"]:
                    sections.append(current_section)

                level = len(heading_match.group(1))
                heading = line.strip()
                current_section = {
                    "heading": heading,
                    "level": level,
                    "start": i,
                    "lines": [line]
                }
            else:
                current_section["lines"].append(line)

        if current_section["heading"] or current_section["lines"]:
            sections.append(current_section)

        return sections

    def list_sections(self) -> list[str]:
        """Return a list of section headings with their indices."""
        result = []
        for i, section in enumerate(self.sections):
            if section["heading"]:
                indent = "  " * (section["level"] - 1)
                result.append(f"{i}: {indent}{section['heading']}")
        return result

    def get_section(self, heading_query: str) -> Optional[dict]:
        """Find a section by heading text (partial match)."""
        query_lower = heading_query.lower().strip('#').strip()
        for section in self.sections:
            heading_text = section["heading"].lower().strip('#').strip()
            if query_lower in heading_text:
                return section
        return None

    def replace_section(self, heading_query: str, new_content: str) -> bool:
        """Replace a section's content (keeping its heading)."""
        section = self.get_section(heading_query)
        if not section:
            return False

        new_lines = new_content.strip().split('\n')
        idx = self.sections.index(section)
        self.sections[idx]["lines"] = new_lines
        return True

    def add_to_section(self, heading_query: str, additional_content: str) -> bool:
        """Append content to an existing section."""
        section = self.get_section(heading_query)
        if not section:
            return False

        additional_lines = additional_content.strip().split('\n')
        idx = self.sections.index(section)
        self.sections[idx]["lines"].extend([""] + additional_lines)
        return True

    def add_section(self, heading: str, content: str, after_heading: Optional[str] = None) -> None:
        """Add a new section. If after_heading is specified, insert after that section."""
        new_section = {
            "heading": heading,
            "level": len(re.match(r'^(#+)', heading).group(1)) if re.match(r'^(#+)', heading) else 2,
            "start": -1,
            "lines": [heading, ""] + content.strip().split('\n')
        }

        if after_heading:
            target = self.get_section(after_heading)
            if target:
                idx = self.sections.index(target) + 1
                self.sections.insert(idx, new_section)
                return

        self.sections.append(new_section)

    def render(self) -> str:
        """Reassemble the document from sections."""
        all_lines = []
        for section in self.sections:
            all_lines.extend(section["lines"])
        return '\n'.join(all_lines)

    def save(self, output_path: Optional[str] = None) -> Path:
        """Save the edited PRD."""
        path = Path(output_path) if output_path else self.file_path
        content = self.render()
        path.write_text(content, encoding="utf-8")
        return path

    def diff_summary(self) -> str:
        """Show what changed compared to the original."""
        new_content = self.render()
        if new_content == self.content:
            return "No changes."

        original_lines = set(self.content.split('\n'))
        new_lines = set(new_content.split('\n'))

        added = new_lines - original_lines
        removed = original_lines - new_lines

        parts = []
        if added:
            parts.append(f"Added {len(added)} lines")
        if removed:
            parts.append(f"Removed {len(removed)} lines")
        return "; ".join(parts) if parts else "Content reordered"


def main():
    """CLI entry point for quick section listing."""
    if len(sys.argv) < 2:
        print("Usage: edit_prd.py <prd_file> [list|get <heading>]", file=sys.stderr)
        sys.exit(1)

    editor = PRDEditor(sys.argv[1])
    command = sys.argv[2] if len(sys.argv) > 2 else "list"

    if command == "list":
        for line in editor.list_sections():
            print(line)
    elif command == "get" and len(sys.argv) > 3:
        section = editor.get_section(sys.argv[3])
        if section:
            print('\n'.join(section["lines"]))
        else:
            print(f"Section not found: {sys.argv[3]}")


if __name__ == "__main__":
    main()
