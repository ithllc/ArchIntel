# ArchIntel — Claude Code Project Guide

## Project Overview
ArchIntel is an architecture intelligence platform built for the Vercel x DeepMind Hackathon (March 21, 2026). Upload an architecture diagram → get instant STRIDE security threat analysis + cloud cost estimation + real-time voice conversation about your architecture.

## Tech Stack (STRICT — do not deviate)
- **Framework:** Next.js 15 (App Router ONLY, no Pages Router)
- **AI SDK:** Vercel AI SDK (`ai`, `@ai-sdk/google`, `@ai-sdk/react`)
- **LLM (Text/Vision):** Google Gemini 1.5 Pro via `google('gemini-1.5-pro')` (Vercel AI SDK)
- **LLM (Voice/Live):** Gemini 2.5 Flash Native Audio via direct WebSocket (`gemini-2.5-flash-native-audio-latest`)
- **Database:** Supabase (`@supabase/supabase-js`)
- **Styling:** Tailwind CSS + Shadcn UI + Lucide React icons
- **Deployment:** Google Cloud Run (NOT Vercel hosting)

## Critical AI SDK Rules
- For ThreatOps & CostSight: Use the unified `ai` package (`streamText`, `generateText`). Do NOT use `@google/generative-ai` for these features.
- For Voice/Live: Use `@google/generative-ai` ONLY server-side for ephemeral token generation. The actual voice connection is a direct browser→Gemini WebSocket — no SDK needed client-side.
- Use `streamText` for real-time streaming responses (threat model, chat).
- Use `generateText` for one-shot operations (cost calculation).
- Multimodal images: `{ type: 'image', image: buffer }` in messages content array.
- Tool calling: `tool({ description, parameters: z.object({...}), execute: async (...) })`.
- Use `maxSteps: 5` when the model needs to evaluate → call tool → summarize.

## Gemini Live API Rules (Voice Feature)
- Model: `gemini-2.5-flash-native-audio-latest` — the LATEST native audio model
- Audio input: PCM16 @ 16kHz, 512-sample buffers (32ms chunks)
- Audio output: PCM16 @ 24kHz, sequential playback scheduling
- Images sent via `realtimeInput.video` channel (not `realtimeInput.image`)
- Send diagram ONCE when session starts — do NOT stream continuously (causes 53s+ latency)
- VAD config: `START_SENSITIVITY_LOW`, `END_SENSITIVITY_HIGH`, `silenceDurationMs: 500`
- Enable `inputAudioTranscription` and `outputAudioTranscription` for live transcript

## Project Structure
```
archintel/
├── app/
│   ├── layout.tsx          # Root layout, dark mode, fonts
│   ├── page.tsx            # Main app page + pipeline state
│   ├── globals.css         # Tailwind + custom styles
│   └── api/
│       ├── threat-model/
│       │   └── route.ts    # STRIDE analysis endpoint
│       ├── cost-estimate-auto/
│       │   └── route.ts    # One-shot cost estimation (pipeline)
│       ├── chat/
│       │   └── route.ts    # Conversational cost chat
│       └── ephemeral-token/
│           └── route.ts    # API key for voice WebSocket
├── components/
│   ├── upload-zone.tsx     # Drag-and-drop diagram upload
│   ├── threat-panel.tsx    # STRIDE results + Terraform + auto-populate
│   ├── cost-panel.tsx      # Cost breakdown + auto-populate from pipeline
│   ├── voice-panel.tsx     # Gemini Live voice + pipeline trigger
│   └── ui/                 # Shadcn UI components
├── lib/
│   ├── supabase.ts         # Supabase client
│   ├── pricing-data.ts     # Mocked cloud pricing JSON
│   ├── parse-threat-stream.ts  # Shared AI SDK stream parser
│   ├── pipeline-types.ts       # Shared types (PipelineStatus, CostResults)
│   ├── format-voice-context.ts # Voice context injection formatters
│   └── utils.ts            # Shadcn utilities
├── Dockerfile              # Cloud Run deployment
├── .env.local              # API keys (never commit)
└── package.json
```

## Environment Variables
```
GOOGLE_GENERATIVE_AI_API_KEY=<gemini-api-key>
NEXT_PUBLIC_SUPABASE_URL=<supabase-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<supabase-service-key>
```

## Supabase Tables
```sql
-- Threat model results
CREATE TABLE threat_models (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  diagram_hash TEXT NOT NULL,
  stride_analysis JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated Terraform policies
CREATE TABLE generated_policies (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  threat_model_id UUID REFERENCES threat_models(id),
  filename TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost estimates
CREATE TABLE cost_estimates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  diagram_hash TEXT NOT NULL,
  services JSONB NOT NULL,
  total_monthly_cost NUMERIC NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat logs
CREATE TABLE chat_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id TEXT NOT NULL,
  messages JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## UI/UX Rules
- **Dark mode by default.** Enterprise DevTools aesthetic.
- Sticky header with app name and tab navigation.
- Drag-and-drop upload zone with visual feedback.
- Syntax-highlighted code blocks for Terraform output.
- Streaming text with blinking cursor effect.
- Loading skeletons during AI processing.
- The live demo is 45% of the judging score — UI must be highly reactive.

## API Route Patterns

### /api/threat-model (POST)
```typescript
import { streamText } from 'ai';
import { google } from '@ai-sdk/google';
import { tool } from 'ai';
import { z } from 'zod';

// Accept image buffer, stream STRIDE analysis
// Tool: generateTerraform → saves to Supabase
```

### /api/cost-estimate-auto (POST)
```typescript
import { generateText } from 'ai';
import { google } from '@ai-sdk/google';

// One-shot cost estimation for the automated pipeline
// Accept FormData with diagram image, return JSON with breakdown
// Uses default assumptions (730 hrs/month, 100GB/month)
// No conversational loop — returns complete result
```

### /api/chat (POST)
```typescript
import { streamText } from 'ai';
import { google } from '@ai-sdk/google';

// useChat compatible endpoint
// Conversational cost refinement with tool calling
```

### /api/ephemeral-token (GET)
```typescript
// Returns Gemini API key (hackathon shortcut) or ephemeral token
// Browser uses this to establish direct WebSocket to Gemini Live API
// No audio proxying through our server — ultra-low latency
```

## Development Priorities
1. **Happy path first.** Get the demo flow working end-to-end.
2. **Hardcode edge cases** if necessary for the 3-minute demo.
3. **Error handling:** Wrap all AI calls in try/catch. Show graceful UI errors.
4. **Do NOT over-engineer.** No auth, no user accounts, no complex state management.

## Deployment (Google Cloud Run)
- Use standalone Next.js output mode (`output: 'standalone'` in next.config.js)
- Multi-stage Dockerfile: build → minimal runtime
- Set env vars via Cloud Run service configuration
- Project ID: gdm-hacks2603-nyc-5752
