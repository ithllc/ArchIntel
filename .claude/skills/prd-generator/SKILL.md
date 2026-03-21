# Skill: prd-generator

## Description
Interactive Product Requirements Document (PRD) generator and editor. Guides the user through a structured interview to gather requirements, then produces a PRD in a standard format. Can also edit and extend existing PRDs.

## When to Use
Invoke this skill when:
- User wants to define a new product, feature, or project from scratch
- User says "create a PRD", "write requirements", "define the product"
- User wants to edit, update, or extend an existing PRD document
- User describes a product idea and needs it formalized into requirements
- User asks to add features, user stories, or constraints to an existing PRD

## User Invocation
- "Create a PRD for [product idea]"
- "Write a product requirements document"
- "Update the PRD with new features"
- "Add user stories to the PRD"
- "/prd"

## Behavior

### Interactive Data Gathering
The skill conducts a structured interview with the user, adapting questions based on prior answers. It does NOT generate a PRD from assumptions -- it asks.

**Phase 1: Product Identity**
1. What is the product/feature name?
2. One-sentence elevator pitch -- what does it do and for whom?
3. What problem does it solve? (Pain points)
4. Is this a new product or an addition to an existing product?

**Phase 2: Audience & Scope**
5. Who are the target users? (Personas or segments)
6. What jurisdictions, platforms, or environments must it support?
7. What is explicitly OUT of scope?
8. What licensing or legal constraints apply?
9. What is the deployment model? (Local-first, cloud, hybrid)

**Phase 3: Features & Requirements**
10. What are the key features? (Walk through each one)
11. For each feature: What is the expected user interaction?
12. Are there accessibility requirements?
13. What AI/ML models or external APIs are involved?
14. What data does the product ingest, store, or produce?

**Phase 4: User Stories**
15. Generate user stories from the gathered features (confirm with user)
16. Ask for additional user stories the user has in mind

**Phase 5: Technical Constraints & Success Metrics**
17. What tech stack is required or preferred?
18. What are the performance/latency requirements?
19. What are the success metrics? (Quantitative where possible)
20. Any security or privacy requirements?

### Document Generation
After gathering data, the skill produces a PRD in the standard 7-section format:
1. Introduction
2. Target Audience
3. Scope & Constraints
4. Key Features
5. User Stories
6. Technical Requirements
7. Success Metrics

Uses the template in `templates/prd_template.md.j2`. Writes the output to `docs/coding_implementations/` by default (or user-specified path).

### Document Editing
When modifying an existing PRD:
1. Read the existing document
2. Identify which sections need changes
3. Ask the user targeted questions about the changes
4. Apply edits while preserving the rest of the document
5. Show a summary of what changed

### Handoff
After PRD creation/edit, suggest:
- "Run `/technical-plan` to generate the implementation plan from this PRD"
- "Run `/project` to view the current kanban board"

## Scripts
- `scripts/generate_prd.py`: PRD generation from structured interview data
- `scripts/edit_prd.py`: Section-level PRD editing and diffing
- `templates/prd_template.md.j2`: Jinja2 template matching standard PRD format

## Integration
- Output PRDs are consumable by the `technical-planner` skill
- Output PRDs can be ingested by `project-manager` for high-level task extraction
- Part of the planning pipeline: `prd-generator -> technical-planner -> project-manager`

## Files
- `memory/learned_context.md`: Patterns learned from previous PRD sessions
