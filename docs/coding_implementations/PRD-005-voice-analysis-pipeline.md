# PRD-005: Automated Security & Cost Analysis Pipeline from Voice Analysis

**Status:** Draft
**Author:** ArchIntel Team
**Date:** 2026-03-21
**GitHub Issue:** [#5](https://github.com/ithllc/ArchIntel/issues/5)
**Priority:** High

---

## 1. Introduction

### Problem Statement
When a user starts a Voice Analysis session in ArchIntel, the ThreatOps (STRIDE security analysis) and CostSight (cost estimation) features do **not** run automatically. Users must manually navigate to each tab and click separate buttons to trigger each analysis. This creates a disjointed experience — users expect that speaking to ArchIntel about their diagram produces a complete intelligence report, not just a conversational overview.

### Elevator Pitch
When a user starts a voice session with their architecture diagram, ArchIntel should automatically run STRIDE security analysis and cloud cost estimation in the background, feed those structured results into the voice conversation, and let the user ask specific follow-up questions about threats, remediations, Terraform policies, and cost breakdowns — all through natural speech.

### Current State
- **Voice Panel** (`voice-panel.tsx`): Connects to Gemini 2.5 Flash Live via WebSocket. Discusses threats and costs conversationally using prompt engineering only — no access to structured analysis data.
- **ThreatOps** (`threat-panel.tsx`): Manual "Run Analysis" button → `POST /api/threat-model` → Gemini 1.5 Pro STRIDE analysis + Terraform generation → saves to Supabase.
- **CostSight** (`cost-panel.tsx`): Manual "Estimate Costs" button → `POST /api/chat` via `useChat` → Gemini 1.5 Pro cost analysis + tool calling → saves to Supabase.
- **No data flows between these three features.**

### Proposed State
A unified pipeline where starting a voice session triggers all three analyses concurrently, results flow between them, and the voice conversation is enriched with structured data from the backend analyses.

---

## 2. Target Audience

### Primary Persona: Cloud Architect / Solutions Architect
- Uploads architecture diagrams to evaluate security posture and cost
- Expects a "one-click" comprehensive analysis experience
- Wants to drill into specific findings via natural language conversation
- Values speed — needs results in under 30 seconds

### Secondary Persona: Engineering Manager / CTO
- Uses ArchIntel during architecture reviews
- Wants to ask high-level questions: "What's the biggest security risk?" or "Can we cut costs by 30%?"
- Doesn't want to manually trigger individual analyses

---

## 3. Scope & Constraints

### In Scope
- Auto-triggering ThreatOps and CostSight when Voice Analysis starts
- Feeding structured analysis results into the voice conversation context
- Auto-populating Security and Costs tabs with results (no manual clicks)
- Voice Q&A about specific threats, Terraform policies, and cost line items
- Progress indicators across all tabs during automated pipeline
- Graceful error handling — one analysis failing doesn't block others

### Out of Scope
- User authentication or multi-user sessions
- Persistent conversation history across sessions
- Custom analysis configurations (e.g., selecting specific STRIDE categories)
- Real-time pricing API integration (keep mocked pricing data)
- Changes to the Gemini Live voice model or WebSocket protocol

### Technical Constraints
- **Vercel AI SDK only** for ThreatOps/CostSight (no `@google/generative-ai` for these)
- **Gemini 2.5 Flash Native Audio** for voice (direct WebSocket, no server proxy)
- **Next.js 15 App Router** — all API routes must remain in `app/api/`
- **Supabase** for persistence — results must still be saved
- **Cloud Run deployment** — no Vercel hosting
- Voice session system instruction limited to text injection (no structured tool calling in Gemini Live)

---

## 4. Key Features

### Feature 1: Auto-Trigger Pipeline
**Description:** When the user clicks "Start Voice Analysis" and the WebSocket session is established (`setupComplete`), automatically fire parallel requests to `/api/threat-model` and a new `/api/cost-estimate-auto` endpoint.

**User Interaction:**
1. User uploads diagram
2. User clicks "Start Voice Analysis"
3. Voice session starts AND Security + Cost analyses begin simultaneously in background
4. User sees progress indicators on Security and Cost tabs
5. When analyses complete, tabs auto-populate with results

**Technical Notes:**
- Requires new API route `/api/cost-estimate-auto` that accepts a diagram image and returns cost analysis without requiring conversational back-and-forth (one-shot mode)
- Both API calls happen from the client after `setupComplete` WebSocket message
- Results stored in React state lifted to `page.tsx` so all panels can access them

### Feature 2: Voice Context Injection
**Description:** Once ThreatOps and CostSight results are available, inject a structured summary into the Gemini Live session via `clientContent` so the voice model can answer specific questions about the findings.

**User Interaction:**
1. Voice session is active, user is talking
2. Security analysis completes → structured summary injected into voice context
3. Cost analysis completes → structured summary injected into voice context
4. User asks: "What's the most critical security threat?" → Voice responds with data from actual STRIDE analysis
5. User asks: "How much will Cloud Run cost?" → Voice responds with data from actual cost estimation

**Technical Notes:**
- Use `clientContent.turns` to send structured text messages to Gemini Live
- Format injections as: `"[SECURITY ANALYSIS COMPLETE] Here are the findings: ..."`
- Keep injection under 2000 tokens to avoid context overflow
- Include: threat names, severities, Terraform filenames, service costs, total monthly cost

### Feature 3: Cross-Tab Auto-Population
**Description:** Lift analysis state to `page.tsx` so that when the pipeline runs from voice, the Security and Cost tabs display results without requiring separate manual triggers.

**User Interaction:**
1. User starts voice session → both analyses run
2. User switches to Security tab → sees full STRIDE analysis and Terraform files already populated
3. User switches to Costs tab → sees cost breakdown already populated
4. Manual "Run Analysis" and "Estimate Costs" buttons still work for re-running

**Technical Notes:**
- New shared state in `page.tsx`: `threatResults`, `costResults`, `pipelineStatus`
- `ThreatPanel` and `CostPanel` accept optional pre-populated results via props
- If results exist from pipeline, display them; if user clicks manual button, re-run and replace

### Feature 4: Pipeline Status Indicators
**Description:** Show real-time progress of the automated pipeline across all tabs.

**User Interaction:**
1. Voice tab shows: "Security analysis running... Cost analysis running..."
2. Security tab badge shows: "Auto-analyzing..." with spinner
3. Cost tab badge shows: "Auto-estimating..." with spinner
4. Badges switch to "Complete" with checkmark when done
5. If an analysis errors, badge shows "Failed" with retry option

**Technical Notes:**
- Pipeline status enum: `idle | running | complete | error`
- Per-analysis status tracked independently
- Status badges rendered in tab triggers (visible even when tab is not selected)

### Feature 5: Voice Q&A with Structured Data
**Description:** The voice conversation can answer specific questions grounded in actual analysis data, not just conversational guesses.

**Supported Questions:**
- "What are my top 3 security threats?" → Returns from STRIDE data
- "What Terraform should I apply first?" → References generated policy files
- "How much will this cost per month?" → Returns total from cost estimation
- "Which service costs the most?" → Returns top cost line item
- "How do I fix the spoofing vulnerability?" → Returns specific remediation from STRIDE
- "Can we reduce costs?" → Returns optimization suggestions from CostSight

**Technical Notes:**
- Achieved by injecting structured summaries into voice context (Feature 2)
- No changes to Gemini Live model or tools — purely text context injection
- Summary format designed for voice-friendly responses (concise, numbered lists)

---

## 5. User Stories

| ID | Role | Story | Acceptance Criteria |
|----|------|-------|-------------------|
| US-1 | Cloud Architect | As a user, I want starting voice analysis to automatically run security and cost analysis so I don't have to click three separate buttons | Both analyses trigger on voice session start; results populate respective tabs |
| US-2 | Cloud Architect | As a user, I want to ask the voice assistant about specific security threats and get answers based on actual STRIDE data | Voice responds with threat names, severities, and remediations from the backend analysis |
| US-3 | Cloud Architect | As a user, I want to ask about cost breakdowns via voice and get real numbers | Voice responds with actual service costs, totals, and optimization suggestions |
| US-4 | Engineering Manager | As a user, I want to see which analyses are running and when they complete | Progress indicators visible on all tabs during automated pipeline |
| US-5 | Cloud Architect | As a user, I want to still be able to manually re-run individual analyses | Manual buttons remain functional and override pipeline results |
| US-6 | Cloud Architect | As a user, I want one analysis failure to not block the others | Each analysis runs independently; errors shown per-analysis |

---

## 6. Technical Requirements

### New API Route
- **`POST /api/cost-estimate-auto`**: One-shot cost estimation (accepts image, returns cost breakdown without conversational loop). Uses `generateText` with Gemini 1.5 Pro + `identifyServices` and `calculateCost` tools.

### State Architecture Changes
```
page.tsx (lifted state)
├── diagramFile: File | null
├── pipelineStatus: { threat: Status, cost: Status }
├── threatResults: { text: string, terraformFiles: TerraformFile[] } | null
├── costResults: { text: string, breakdown: CostBreakdown[] } | null
├── triggerPipeline: (file: File) => void
│
├── VoicePanel
│   ├── receives: pipelineStatus, threatResults, costResults
│   ├── calls: triggerPipeline on setupComplete
│   └── injects: results into Gemini Live context
│
├── ThreatPanel
│   ├── receives: threatResults, pipelineStatus.threat
│   └── can: override results with manual analysis
│
└── CostPanel
    ├── receives: costResults, pipelineStatus.cost
    └── can: override results with manual analysis
```

### Performance Requirements
- ThreatOps analysis: Complete within 15 seconds
- CostSight estimation: Complete within 10 seconds
- Voice context injection: Within 1 second of analysis completion
- Both analyses run concurrently (not sequentially)

### Data Flow
```
User clicks "Start Voice Analysis"
        │
        ├──→ WebSocket to Gemini Live (voice starts immediately)
        │
        ├──→ POST /api/threat-model (parallel)
        │    └── On complete: update threatResults state + inject into voice
        │
        └──→ POST /api/cost-estimate-auto (parallel)
             └── On complete: update costResults state + inject into voice
```

---

## 7. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Pipeline trigger rate | 100% of voice sessions auto-trigger both analyses | Client-side logging |
| Analysis completion | Both analyses complete within 20s of voice start | Timestamp delta |
| Voice Q&A accuracy | Voice can answer security/cost questions with structured data | Manual testing — 5 test questions per diagram |
| Tab auto-population | Security and Cost tabs show results without manual clicks | Manual testing |
| Error isolation | One analysis failure does not affect the other two features | Fault injection testing |
| User satisfaction | Users do not need to click any additional buttons after starting voice | Demo flow testing |

---

## Appendix: Files to Modify

| File | Change |
|------|--------|
| `app/page.tsx` | Add lifted state for pipeline results and status |
| `components/voice-panel.tsx` | Add pipeline trigger on `setupComplete`, context injection on results |
| `components/threat-panel.tsx` | Accept optional pre-populated results, show auto-analysis status |
| `components/cost-panel.tsx` | Accept optional pre-populated results, show auto-analysis status |
| `app/api/cost-estimate-auto/route.ts` | **NEW** — One-shot cost estimation endpoint |
| `lib/pipeline.ts` | **NEW** — Pipeline orchestration helper (optional) |
