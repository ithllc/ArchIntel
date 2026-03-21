# ArchIntel — Architecture Intelligence Platform

## Decision: ThreatOps + CostSight Combined

**Tagline:** "Upload your architecture. Talk to it. Understand its risks and costs in seconds."

## Why This Combo

- **Same input, triple output:** One architecture diagram → STRIDE threat model + cost breakdown + voice conversation
- **Live Demo (45%):** Streaming STRIDE analysis + Terraform gen is visually stunning. Cost breakdown adds a second act. Voice conversation is the jaw-dropper — *talk to your architecture diagram*.
- **Creativity (35%):** Nobody else will combine security + cost + voice from a single diagram. The voice interaction is unprecedented.
- **Impact (20%):** Every engineering team needs security review AND cost estimation. Voice makes it accessible to non-technical stakeholders.
- **Problem Statements:** Hits ALL THREE — **Chat-Based Agents** (voice conversation), **Multi-Modal Agents** (diagram vision + audio), **AI Applications** (useful dev tool)

## Core Features

### Tab 1: ThreatOps — Security Analysis
- Upload architecture diagram (image/Excalidraw/Mermaid)
- Gemini 1.5 Pro analyzes diagram via multimodal vision
- Streams a full STRIDE threat model in real-time
- Tool calls to generate Terraform `.tf` remediation policies
- Results saved to Supabase for audit trail

### Tab 2: CostSight — Cost Estimation
- Same diagram, parsed for cloud service components
- Conversational chat: AI asks clarifying questions (MAU, traffic, region)
- Tool calls to calculate costs from pricing data
- Visual cost breakdown with optimization suggestions
- Results saved to Supabase

### Tab 3: Voice Analysis — Talk to Your Architecture
- Gemini 2.5 Flash Native Audio Live API (latest model)
- Direct browser→Gemini WebSocket (zero server-side audio proxying)
- User speaks naturally: "What are the security risks?" / "How much will this cost?"
- Gemini sees the diagram AND hears the user simultaneously
- Real-time transcript displayed below
- Ephemeral token auth for low-latency connection

### Shared Infrastructure
- Single drag-and-drop upload zone
- Tabbed output panel (Security | Cost | Voice)
- Dark mode enterprise UI
- Supabase persistence for all analyses
- Google Cloud Run deployment

## Architecture

```
┌─────────────────────────────────────────────────┐
│                Next.js 15 App Router             │
├──────────┬──────────┬───────────────────────────┤
│  Upload  │  Tabs    │  Voice / Chat Panels      │
│  Zone    │  UI      │                           │
├──────────┴──────────┴───────────────────────────┤
│                API Routes                        │
│  /api/threat-model     (Vercel AI SDK)          │
│  /api/chat             (Vercel AI SDK)          │
│  /api/ephemeral-token  (Gemini Live API auth)   │
├─────────────────────────────────────────────────┤
│  Text/Vision: Vercel AI SDK → Gemini 1.5 Pro   │
│  Voice/Live:  Direct WS → Gemini 2.5 Flash     │
│               Native Audio (LATEST)             │
├─────────────────────────────────────────────────┤
│  Tools: generateTerraform, calculateCost,       │
│         identifyServices                        │
├─────────────────────────────────────────────────┤
│  Supabase: threat_models, cost_estimates,       │
│            generated_policies, chat_logs        │
└─────────────────────────────────────────────────┘
│  Deploy: Google Cloud Run                        │
└─────────────────────────────────────────────────┘
```

## Gemini Models Used

| Model | Purpose | Connection |
|-------|---------|------------|
| `gemini-1.5-pro` | STRIDE analysis + cost estimation (vision + text) | Vercel AI SDK |
| `gemini-2.5-flash-native-audio-latest` | Real-time voice conversation with diagram | Direct WebSocket |

## 3-Minute Demo Script

1. **0:00-0:20** — "Every architecture diagram is drawn once and forgotten. What if you could talk to it?"
2. **0:20-0:50** — Upload AWS diagram. Switch to Voice tab. Click "Start Voice Analysis." Say: "Tell me about the security risks in this architecture." Gemini speaks back about STRIDE threats.
3. **0:50-1:30** — Switch to Security tab. Show STRIDE analysis streaming in real-time. Scroll to generated Terraform remediation.
4. **1:30-2:15** — Switch to Cost tab. Chat: "We expect 1M requests/month, 500GB storage." Show cost breakdown table. Point out optimization suggestion.
5. **2:15-2:45** — Switch back to Voice. Ask: "What's the single biggest risk?" Gemini responds naturally.
6. **2:45-3:00** — "One diagram. Three dimensions of intelligence. Security. Cost. Voice. That's ArchIntel."

## Time Budget (2.5 hours)

| Phase | Time | Deliverable |
|-------|------|-------------|
| Scaffold + deps | 15 min | Working Next.js app with all packages |
| Upload UI + layout | 15 min | Dark mode, drag-drop, 3-tab layout |
| ThreatOps API + UI | 30 min | Streaming STRIDE + Terraform gen |
| CostSight API + UI | 25 min | Cost estimation + chat |
| Voice panel + Live API | 25 min | Gemini 2.5 Flash voice interaction |
| Supabase integration | 10 min | Tables + persistence |
| Cloud Run deploy | 15 min | Live URL |
| Demo prep + polish | 10 min | Test diagrams, pitch practice |
| Buffer | 5 min | Bug fixes |
