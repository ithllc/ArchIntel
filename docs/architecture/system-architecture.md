# ArchIntel System Architecture

> **Version:** 1.2
> **Last Updated:** 2026-03-21
> **Status:** Production (Google Cloud Run)

---

## 1. Overview

ArchIntel is an architecture intelligence platform that transforms static architecture diagrams into actionable security, cost, and conversational insights. Users upload a single diagram and receive three dimensions of analysis through a unified dark-mode interface.

**Live URL:** https://archintel-346168839454.us-central1.run.app

---

## 2. High-Level System Architecture

```mermaid
graph TB
    subgraph Client["Browser (Client)"]
        UI[Next.js 15 App Router<br/>React Client Components]
        Upload[Drag & Drop Upload Zone]
        Tabs[Tabbed Output Panel]
        VoiceClient[Voice Panel<br/>Web Audio API + WebSocket]
        ThreatClient[Threat Panel<br/>Stream Parser + Markdown]
        CostClient[Cost Panel<br/>useChat Hook]
    end

    subgraph Server["Next.js Server (Cloud Run)"]
        ThreatAPI["/api/threat-model<br/>POST · streamText"]
        CostAutoAPI["/api/cost-estimate-auto<br/>POST · generateText"]
        ChatAPI["/api/chat<br/>POST · streamText"]
        TokenAPI["/api/ephemeral-token<br/>GET"]
    end

    subgraph Google["Google Cloud"]
        SecretMgr[Secret Manager<br/>gemini-api-key<br/>supabase-url<br/>supabase-anon-key]
        Gemini15[Gemini 1.5 Pro<br/>Vision + Text]
        GeminiFlash[Gemini 2.5 Flash<br/>Native Audio]
        CloudRun[Cloud Run<br/>us-central1]
        AR[Artifact Registry<br/>Docker Images]
        CloudBuild[Cloud Build<br/>CI/CD Trigger]
    end

    subgraph Supabase["Supabase (PostgreSQL)"]
        ThreatTable[threat_models<br/>STRIDE analysis results]
        PolicyTable[generated_policies<br/>Terraform remediation files]
        CostTable[cost_estimates<br/>Service cost breakdowns]
        ChatTable[chat_logs<br/>Conversation history]
    end

    subgraph GitHub["GitHub"]
        Repo[ithllc/ArchIntel<br/>main branch]
    end

    Upload -->|File| Tabs
    Tabs --> VoiceClient
    Tabs --> ThreatClient
    Tabs --> CostClient

    ThreatClient -->|FormData POST| ThreatAPI
    CostClient -->|JSON POST| ChatAPI
    VoiceClient -->|GET| TokenAPI
    VoiceClient -.->|Auto-trigger on session start| ThreatAPI
    VoiceClient -.->|Auto-trigger on session start| CostAutoAPI

    ThreatAPI -->|Vercel AI SDK| Gemini15
    CostAutoAPI -->|Vercel AI SDK| Gemini15
    ChatAPI -->|Vercel AI SDK| Gemini15
    TokenAPI -->|API Key| VoiceClient

    ThreatAPI -->|Insert| ThreatTable
    ThreatAPI -->|Insert| PolicyTable
    CostAutoAPI -->|Insert| CostTable
    ChatAPI -->|Insert| CostTable
    ChatAPI -->|Insert| ChatTable

    VoiceClient -.->|Direct WebSocket<br/>PCM16 Audio + Image| GeminiFlash

    SecretMgr -->|Env Var Injection| CloudRun
    CloudRun --> Server

    Repo -->|Push to main| CloudBuild
    CloudBuild -->|Build Image| AR
    CloudBuild -->|Deploy| CloudRun
```

---

## 3. Feature Architecture

### 3.1 Voice Analysis with Automated Pipeline

The voice feature establishes a direct browser-to-Gemini WebSocket connection with zero server-side audio proxying. **On session start, it also auto-triggers STRIDE security analysis and cost estimation in parallel**, feeding structured results back into the voice conversation.

```mermaid
sequenceDiagram
    participant User
    participant Browser as Browser<br/>(Voice Panel)
    participant API as /api/ephemeral-token
    participant ThreatAPI as /api/threat-model
    participant CostAPI as /api/cost-estimate-auto
    participant Gemini as Gemini 2.5 Flash<br/>Native Audio

    User->>Browser: Click "Start Voice Analysis"
    Browser->>API: GET /api/ephemeral-token
    API-->>Browser: { apiKey, model }

    Browser->>Gemini: WebSocket Connect
    Browser->>Gemini: Setup Config<br/>(model, VAD, transcription, system prompt)
    Gemini-->>Browser: setupComplete

    par Automated Pipeline (concurrent)
        Browser->>ThreatAPI: POST FormData (diagram)
        Note right of ThreatAPI: STRIDE analysis +<br/>Terraform generation
        ThreatAPI-->>Browser: Streamed results
        Browser->>Browser: Update Security tab
        Browser->>Gemini: clientContent<br/>[SECURITY ANALYSIS COMPLETE]
    and
        Browser->>CostAPI: POST FormData (diagram)
        Note right of CostAPI: One-shot cost<br/>estimation
        CostAPI-->>Browser: JSON cost breakdown
        Browser->>Browser: Update Costs tab
        Browser->>Gemini: clientContent<br/>[COST ANALYSIS COMPLETE]
    end

    Browser->>Browser: getUserMedia() → Microphone
    Browser->>Gemini: realtimeInput.video<br/>(diagram image, sent once)
    Browser->>Gemini: clientContent<br/>("Analyze this diagram...")

    loop Real-time Audio Stream
        Browser->>Gemini: realtimeInput.audio<br/>(PCM16 @ 16kHz, 512-sample chunks)
        Gemini-->>Browser: serverContent.modelTurn<br/>(PCM16 @ 24kHz audio)
        Gemini-->>Browser: outputTranscription
        Browser->>Browser: AudioContext playback + transcript
    end

    User->>Browser: "What's the most critical threat?"
    Note over Gemini: References injected<br/>STRIDE data
    Gemini-->>Browser: Spoken response with<br/>specific threat details

    User->>Browser: Click "End Session"
    Browser->>Gemini: WebSocket Close
```

**Key Technical Details:**
- **Input Audio:** PCM16 @ 16kHz, downsampled from browser's native sample rate
- **Output Audio:** PCM16 @ 24kHz, sequential playback scheduling via `AudioContext`
- **VAD Config:** `START_SENSITIVITY_LOW`, `END_SENSITIVITY_HIGH`, `silenceDurationMs: 500`
- **Image Delivery:** Sent once via `realtimeInput.video` channel on session start
- **Transcription:** Both `inputAudioTranscription` and `outputAudioTranscription` enabled
- **Pipeline Trigger:** On `setupComplete`, fires concurrent requests to `/api/threat-model` and `/api/cost-estimate-auto`
- **Context Injection:** Structured analysis summaries sent via `clientContent.turns` to enrich voice responses
- **Tab Auto-Population:** Security and Costs tabs display pipeline results without manual clicks

---

### 3.2 ThreatOps (STRIDE Security Analysis)

The security feature uses Gemini 1.5 Pro's multimodal vision to analyze architecture diagrams and produce STRIDE threat models with Terraform remediation.

```mermaid
sequenceDiagram
    participant User
    participant Browser as Browser<br/>(Threat Panel)
    participant API as /api/threat-model
    participant Gemini as Gemini 1.5 Pro
    participant Tool as generateTerraform<br/>Tool

    User->>Browser: Click "Run Analysis"
    Browser->>API: POST FormData<br/>(diagram image)
    API->>API: Convert image to<br/>base64 data URL

    API->>Gemini: streamText()<br/>(image + STRIDE prompt)

    loop Streaming Response
        Gemini-->>API: Text chunks<br/>(STRIDE analysis)
        API-->>Browser: UI Message Stream
        Browser->>Browser: Render Markdown<br/>in real-time
    end

    Gemini->>Tool: generateTerraform()<br/>(threatName, filename, HCL content)
    Tool->>Tool: Save to Supabase<br/>(generated_policies table)
    Tool-->>Gemini: { saved: true, filename }
    Gemini-->>API: Continue with summary
    API->>API: Save STRIDE analysis<br/>to Supabase (threat_models)
    API-->>Browser: Tool results + text

    Browser->>Browser: Render Terraform<br/>with syntax highlighting
```

**AI Tool — `generateTerraform`:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `threatName` | string | Name of the threat being remediated |
| `filename` | string | Terraform filename (e.g., `iam_policy.tf`) |
| `content` | string | Complete Terraform HCL content |
| `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |

---

### 3.3 CostSight (Cloud Cost Estimation)

The cost feature provides a conversational interface powered by Gemini 1.5 Pro with tool-calling for structured cost calculations.

```mermaid
sequenceDiagram
    participant User
    participant Browser as Browser<br/>(Cost Panel)
    participant API as /api/chat
    participant Gemini as Gemini 1.5 Pro
    participant ID as identifyServices<br/>Tool
    participant Calc as calculateCost<br/>Tool

    User->>Browser: Click "Estimate Costs"
    Browser->>API: POST { messages, files }<br/>(diagram + prompt)

    API->>Gemini: streamText()<br/>(system prompt + messages)
    Gemini->>ID: identifyServices()<br/>(services found in diagram)
    ID-->>Gemini: { services with pricing }

    Gemini-->>Browser: "I found N services.<br/>What's your expected traffic?"

    User->>Browser: "1M requests/month,<br/>500GB storage"
    Browser->>API: POST { messages }

    Gemini->>Calc: calculateCost()<br/>(services + traffic params)
    Calc->>Calc: Compute per-service costs<br/>from pricing data
    Calc-->>Gemini: { breakdown, totalMonthlyCost }

    Gemini-->>Browser: Formatted cost table<br/>+ optimization suggestions
```

**AI Tools:**

| Tool | Purpose | Key Inputs |
|------|---------|------------|
| `identifyServices` | Catalog cloud services from diagram | services array (name, type, count) |
| `calculateCost` | Calculate monthly costs | services with hoursPerMonth, gbPerMonth |

**Pricing Data:** 19 cloud services covered (AWS + GCP) including EC2, S3, RDS, Lambda, Cloud Run, Cloud SQL, GKE, BigQuery, and more.

---

### 3.4 Automated Analysis Pipeline

The pipeline orchestrates all three features from a single user action (starting voice analysis).

```mermaid
graph LR
    A["User clicks<br/>Start Voice Analysis"] --> B["WebSocket<br/>setupComplete"]
    B --> C["triggerPipeline()"]
    C --> D["POST /api/threat-model<br/>(concurrent)"]
    C --> E["POST /api/cost-estimate-auto<br/>(concurrent)"]
    D --> F["threatResults state"]
    E --> G["costResults state"]
    F --> H["Security tab<br/>auto-populated"]
    F --> I["Voice context injection<br/>[SECURITY ANALYSIS COMPLETE]"]
    G --> J["Costs tab<br/>auto-populated"]
    G --> K["Voice context injection<br/>[COST ANALYSIS COMPLETE]"]

    style A fill:#7c3aed,color:#fff
    style D fill:#dc2626,color:#fff
    style E fill:#16a34a,color:#fff
```

**State Architecture:**

| State Variable | Owner | Description |
|---------------|-------|-------------|
| `pipelineStatus.threat` | `page.tsx` | `idle` \| `running` \| `complete` \| `error` |
| `pipelineStatus.cost` | `page.tsx` | `idle` \| `running` \| `complete` \| `error` |
| `threatResults` | `page.tsx` | `{ text, terraformFiles }` from STRIDE analysis |
| `costResults` | `page.tsx` | `{ text, breakdown, totalMonthlyCost, annualEstimate }` from cost estimation |

**New API Route — `/api/cost-estimate-auto` (POST):**

One-shot cost estimation that accepts a diagram via FormData and returns a complete JSON response (no conversational loop). Uses `generateText` with Gemini 1.5 Pro and inline pricing data.

```
POST /api/cost-estimate-auto
Content-Type: multipart/form-data
Body: { diagram: File }

Response: {
  text: string,           // Markdown analysis with optimization suggestions
  breakdown: CostBreakdownItem[],  // Per-service cost data
  totalMonthlyCost: number,
  annualEstimate: number
}
```

**Voice Context Injection:**

When analysis results arrive, structured summaries are injected into the Gemini Live session via `clientContent.turns`:
- `formatThreatSummaryForVoice()` — Top threats, severities, Terraform filenames
- `formatCostSummaryForVoice()` — Total cost, per-service breakdown, optimization hints

This enables the voice model to answer specific questions like "What's my biggest security risk?" or "How much will Cloud Run cost?" using real analysis data.

---

## 4. Infrastructure & Deployment

### 4.1 CI/CD Pipeline

```mermaid
graph LR
    A[Developer pushes<br/>to main] --> B[GitHub Webhook]
    B --> C[Cloud Build Trigger<br/>archintel-deploy]
    C --> D[Docker Build<br/>archintel/Dockerfile]
    D --> E[Push to<br/>Artifact Registry]
    E --> F[Deploy to<br/>Cloud Run]
    F --> G[Secret Manager<br/>injects API key]
    G --> H[Live at<br/>archintel-*.run.app]

    style A fill:#24292e,color:#fff
    style C fill:#4285f4,color:#fff
    style F fill:#34a853,color:#fff
    style H fill:#0f9d58,color:#fff
```

### 4.2 Secrets Management

```mermaid
graph TD
    SM[Google Cloud<br/>Secret Manager] -->|"gemini-api-key:latest"| CR[Cloud Run Service]
    SM -->|"supabase-url:latest"| CR
    SM -->|"supabase-anon-key:latest"| CR
    CR -->|"GOOGLE_GENERATIVE_AI_API_KEY"| App[Next.js Application]
    CR -->|"NEXT_PUBLIC_SUPABASE_URL"| App
    CR -->|"NEXT_PUBLIC_SUPABASE_ANON_KEY"| App
    App --> ThreatRoute[/api/threat-model<br/>Vercel AI SDK + Supabase]
    App --> ChatRoute[/api/chat<br/>Vercel AI SDK + Supabase]
    App --> TokenRoute[/api/ephemeral-token<br/>Returns key for WebSocket]

    CB[Cloud Build] -->|"--update-secrets flag"| CR

    style SM fill:#fbbc04,color:#000
    style CR fill:#34a853,color:#fff
```

**Managed Secrets:**
| Secret Name | Environment Variable | Purpose |
|------------|---------------------|---------|
| `gemini-api-key` | `GOOGLE_GENERATIVE_AI_API_KEY` | Gemini API access for all AI features |
| `supabase-url` | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project endpoint |
| `supabase-anon-key` | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous client key |

**Secret Flow:**
1. All secrets stored in Google Cloud Secret Manager
2. Cloud Run mounts secrets as environment variables at runtime
3. Cloud Build's deploy step uses `--update-secrets` to ensure bindings persist across deployments
4. Secrets are **never** stored in source code, environment files, or build configurations

---

## 5. Project Structure

```
archintel/
├── app/
│   ├── layout.tsx              # Root layout, dark mode, Geist fonts
│   ├── page.tsx                # Main page with upload + 3-tab layout + pipeline state
│   ├── globals.css             # Tailwind v4 + shadcn theme + custom styles
│   └── api/
│       ├── threat-model/
│       │   └── route.ts        # STRIDE analysis (streamText + tool)
│       ├── cost-estimate-auto/
│       │   └── route.ts        # One-shot cost estimation (generateText, pipeline)
│       ├── chat/
│       │   └── route.ts        # Conversational cost chat (streamText + tools)
│       └── ephemeral-token/
│           └── route.ts        # API key for browser WebSocket
├── components/
│   ├── upload-zone.tsx         # Drag-and-drop with preview
│   ├── voice-panel.tsx         # Gemini Live WebSocket + audio + pipeline trigger
│   ├── threat-panel.tsx        # STRIDE results + Terraform + auto-populate
│   ├── cost-panel.tsx          # Cost chat + auto-populate from pipeline
│   └── ui/                     # Shadcn UI components
├── lib/
│   ├── supabase.ts             # Supabase client
│   ├── pricing-data.ts         # Cloud pricing reference (19 services)
│   ├── parse-threat-stream.ts  # Shared AI SDK stream parser for threat results
│   ├── pipeline-types.ts       # Shared TypeScript types (PipelineStatus, CostResults)
│   ├── format-voice-context.ts # Formats analysis results for voice injection
│   └── utils.ts                # Shadcn utilities
├── Dockerfile                  # Multi-stage build for Cloud Run
├── cloudbuild.yaml             # CI/CD pipeline definition
└── next.config.ts              # standalone output for containerization
```

---

## 6. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router) | 16.2.1 |
| Language | TypeScript | 5.x |
| AI SDK | Vercel AI SDK | 6.x |
| AI Provider | @ai-sdk/google | Latest |
| LLM (Vision/Text) | Gemini 1.5 Pro | Latest |
| LLM (Voice) | Gemini 2.5 Flash Native Audio | Latest |
| UI Components | Shadcn UI | v4 |
| Styling | Tailwind CSS | v4 |
| Icons | Lucide React | Latest |
| Markdown | react-markdown | Latest |
| Code Highlighting | react-syntax-highlighter | Latest |
| File Upload | react-dropzone | Latest |
| Deployment | Google Cloud Run | Managed |
| CI/CD | Google Cloud Build | Managed |
| Secrets | Google Cloud Secret Manager | Managed |
| Container Registry | Google Artifact Registry | Managed |
| Database | Supabase (PostgreSQL) | Managed |

---

## 7. Data Persistence (Supabase)

All analysis results are persisted to Supabase PostgreSQL for audit trails and history.

| Table | Purpose | Written By |
|-------|---------|-----------|
| `threat_models` | STRIDE analysis text per diagram | `/api/threat-model` (onFinish) |
| `generated_policies` | Terraform .tf files with threat name + severity | `generateTerraform` tool |
| `cost_estimates` | Service breakdown + total monthly cost | `calculateCost` tool, `/api/cost-estimate-auto` |
| `chat_logs` | Conversation summaries | `/api/chat` (onFinish) |

```mermaid
erDiagram
    threat_models {
        uuid id PK
        text diagram_hash
        jsonb stride_analysis
        timestamptz created_at
    }
    generated_policies {
        uuid id PK
        uuid threat_model_id FK
        text threat_name
        text severity
        text filename
        text content
        timestamptz created_at
    }
    cost_estimates {
        uuid id PK
        text diagram_hash
        jsonb services
        numeric total_monthly_cost
        timestamptz created_at
    }
    chat_logs {
        uuid id PK
        text session_id
        jsonb messages
        timestamptz created_at
    }
    threat_models ||--o{ generated_policies : "has many"
```

---

## 8. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| API Key Exposure | Stored in Secret Manager, injected at runtime. Never in source code or build configs. |
| CORS / Origin | Cloud Run handles HTTPS termination. WebSocket to Gemini is origin-restricted by API key scope. |
| File Upload | Max 10MB, image MIME types only, validated client-side via react-dropzone. |
| Audio Data | PCM16 audio streams directly to Gemini — no server-side storage or logging of audio. |
| Environment Variables | `.env.local` excluded from git via `.gitignore`. Production uses Secret Manager exclusively. |
