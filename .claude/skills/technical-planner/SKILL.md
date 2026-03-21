# Skill: technical-planner

## Description
Interactive technical implementation planner. Takes a PRD (or user-described requirements) and produces a phased, actionable implementation plan with task breakdowns, dependency graphs, and architecture decisions. Interacts with the user to resolve ambiguities and confirm technical choices.

## When to Use
Invoke this skill when:
- User wants to create a technical implementation plan from a PRD or feature set
- User says "plan the implementation", "create a tech plan", "how should we build this"
- User wants to break a large feature into phased implementation steps
- User asks to update or extend an existing implementation plan
- User wants to analyze dependencies between features

## User Invocation
- "Create an implementation plan for [feature/PRD]"
- "Plan the technical architecture"
- "Break this down into phases"
- "Update the tech plan"
- "/technical-plan"

## Behavior

### Input Analysis
The skill starts by identifying its input source:
1. **From PRD**: Read a specified PRD document and extract features, constraints, tech stack
2. **From roadmap**: Read a feature roadmap document and plan specific features
3. **From conversation**: User describes what they want built; skill asks clarifying questions

### Interactive Technical Interview
After analyzing the input, the skill conducts a focused technical interview:

**Phase 1: Architecture Decisions**
1. What is the target architecture? (Monolith, microservices, serverless, local-first)
2. Which components already exist vs. need to be built?
3. What are the integration points with existing systems?
4. What models/APIs are involved and how do they connect?

**Phase 2: Implementation Phasing**
5. What is the logical build order? (Dependencies, risk, value)
6. Which features can be parallelized?
7. What are the MVP milestones vs. polish milestones?
8. Are there any hard deadlines or external dependencies?

**Phase 3: Technical Specifications**
9. For each phase: What files/modules need to be created or modified?
10. What are the API contracts (endpoints, request/response shapes)?
11. What database schema changes are needed?
12. What are the test requirements?

**Phase 4: Risk & Constraints**
13. What are the technical risks? (Model limitations, API rate limits, browser compat)
14. What are the security considerations?
15. What is the rollback strategy if something fails?

### Plan Generation
Produces a structured implementation plan with:
- **Phase breakdown**: Numbered phases with clear objectives
- **Task lists**: Actionable items within each phase (numbered, with dependencies noted)
- **Dependency graph**: Which phases/tasks block others (Mermaid syntax)
- **File manifest**: Expected files to create/modify per phase
- **API contracts**: Endpoint definitions where applicable
- **Architecture decisions**: Documented choices with rationale

### Output Format
```
# Technical Implementation Plan: [Feature/Product]

## Overview
## Architecture
## Phase N: [Name]
### Objectives
### Implementation Steps
### Files
### Dependencies
## Risk Assessment
## Success Criteria
```

### Handoff
After plan creation, suggest:
- "Run `/project` to ingest this plan into the kanban board"
- The project-manager's `ingest_plan.py` can parse the output directly

## Scripts
- `scripts/generate_plan.py`: Plan generation from structured data
- `scripts/analyze_prd.py`: PRD parser that extracts features, constraints, and tech stack
- `templates/implementation_plan.md.j2`: Jinja2 template for plan output

## Integration
- Reads PRDs created by the `prd-generator` skill
- Output plans are directly ingestible by `project-manager` via `ingest_plan.py`
- Part of the planning pipeline: `prd-generator -> technical-planner -> project-manager`

## Files
- `memory/learned_context.md`: Patterns and decisions learned from previous planning sessions
