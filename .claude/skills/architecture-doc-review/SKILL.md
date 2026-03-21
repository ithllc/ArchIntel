# Skill: Architecture Documentation Review

## Description
Automatically reviews and updates architecture documentation after every development request. Ensures that new features, workflows, and state changes are accurately reflected in the project's technical documentation.

## When to Use
Run this skill after completing any development task that adds, modifies, or removes features, endpoints, workflows, or state management patterns.

## User Invocation
- "Update the architecture docs"
- "Review docs after this change"
- "Sync documentation with the codebase"
- "/architecture-doc-review"

## Process

### 1. Inventory Current Documentation
Read all files in `docs/architecture/` (or the project's equivalent documentation directory):
- System overview documents (architecture diagrams, core components)
- Workflow documents (sequence diagrams, workflow descriptions)
- State management documents (data structures, context lifecycle)

### 2. Analyze Changes
Compare the completed development work against the existing documentation:
- **New components or services** - Do they appear in the system overview?
- **New or modified workflows** - Are they documented with sequence/flow diagrams?
- **State changes** - Are new data structures, session fields, or client-side state documented?
- **Port, URL, or configuration changes** - Are references in all docs up to date?

### 3. Determine Action
For each document, decide one of:
- **No change needed** - Documentation already reflects the current state
- **Update existing content** - Modify diagrams, descriptions, or tables in place
- **Add new section** - Append a new section to an existing document
- **Create new document** - Only when a major new subsystem warrants its own file

### 4. Apply Updates
- Use Mermaid syntax for all diagrams (sequence, graph, flowchart)
- Keep descriptions concise and technical
- Maintain consistent heading hierarchy (H2 for sections, H3 for subsections)
- Update tables and lists to reflect current implementation
- Do NOT add author attribution lines referencing any AI tool or company

### 5. Verify Consistency
- Ensure port numbers, endpoint paths, and model names are consistent across all docs
- Ensure the README.md installation section is consistent with architecture docs
- Cross-reference any implementation plan documents if they exist

## Output
Report what was updated, added, or left unchanged for each architecture document.

## Files
- `memory/learned_context.md`: Patterns learned from previous documentation reviews
