---
name: scaffold-app
description: Initialize the ArchIntel Next.js 15 project with all dependencies, folder structure, and configuration files. Run this FIRST before any other build skills.
user_invocable: true
---

# Scaffold ArchIntel App

You are initializing the ArchIntel hackathon project from scratch. Follow these steps EXACTLY.

## Step 1: Create Next.js App

```bash
npx create-next-app@latest archintel --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

## Step 2: Install Dependencies

```bash
cd archintel
npm install ai @ai-sdk/google @ai-sdk/react zod @supabase/supabase-js @google/generative-ai
npm install -D @types/node
```

## Step 3: Install Shadcn UI

```bash
npx shadcn@latest init -d
npx shadcn@latest add button card tabs textarea badge separator scroll-area dialog dropdown-menu tooltip
```

## Step 4: Install Additional UI Dependencies

```bash
npm install lucide-react react-dropzone react-markdown react-syntax-highlighter
npm install -D @types/react-syntax-highlighter
```

## Step 5: Configure next.config.ts

Set `output: 'standalone'` for Cloud Run deployment:

```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {
    serverActions: {
      bodySizeLimit: '10mb',
    },
  },
};

export default nextConfig;
```

## Step 6: Create .env.local

```
GOOGLE_GENERATIVE_AI_API_KEY=AIzaSyCNvQtMjBdow_RChx8eVeSSZG1jjBJaqrM
NEXT_PUBLIC_SUPABASE_URL=<get-from-supabase-dashboard>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<get-from-supabase-dashboard>
```

## Step 7: Create Folder Structure

```bash
mkdir -p app/api/threat-model app/api/cost-estimate app/api/chat app/api/ephemeral-token
mkdir -p components/ui lib
```

## Step 8: Create lib/supabase.ts

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

## Step 9: Create lib/pricing-data.ts

```typescript
export const CLOUD_PRICING: Record<string, { perHour: number; perGB: number; description: string }> = {
  'cloud-run': { perHour: 0.00002400, perGB: 0.00000250, description: 'Google Cloud Run' },
  'cloud-sql': { perHour: 0.0150, perGB: 0.170, description: 'Cloud SQL (PostgreSQL)' },
  'gke': { perHour: 0.10, perGB: 0.040, description: 'Google Kubernetes Engine' },
  'cloud-storage': { perHour: 0, perGB: 0.020, description: 'Cloud Storage' },
  'bigquery': { perHour: 0, perGB: 5.00, description: 'BigQuery (per TB scanned)' },
  'pub-sub': { perHour: 0, perGB: 0.040, description: 'Pub/Sub' },
  'load-balancer': { perHour: 0.025, perGB: 0.008, description: 'Cloud Load Balancer' },
  'memorystore-redis': { perHour: 0.049, perGB: 0, description: 'Memorystore (Redis)' },
  'cloud-functions': { perHour: 0.00001650, perGB: 0.00000250, description: 'Cloud Functions' },
  'api-gateway': { perHour: 0, perGB: 0.003, description: 'API Gateway (per M calls)' },
  'ec2': { perHour: 0.0416, perGB: 0, description: 'AWS EC2 (t3.medium)' },
  's3': { perHour: 0, perGB: 0.023, description: 'AWS S3' },
  'rds': { perHour: 0.034, perGB: 0.115, description: 'AWS RDS (PostgreSQL)' },
  'lambda': { perHour: 0.0000166667, perGB: 0.00000000167, description: 'AWS Lambda' },
  'elb': { perHour: 0.0225, perGB: 0.008, description: 'AWS Elastic Load Balancer' },
  'dynamodb': { perHour: 0, perGB: 0.25, description: 'AWS DynamoDB' },
  'elasticache': { perHour: 0.034, perGB: 0, description: 'AWS ElastiCache (Redis)' },
  'sqs': { perHour: 0, perGB: 0.00000040, description: 'AWS SQS (per request)' },
  'cloudfront': { perHour: 0, perGB: 0.085, description: 'AWS CloudFront' },
};
```

## Step 10: Create Dockerfile

```dockerfile
FROM node:20-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

## Step 11: Copy CLAUDE.md

Copy the CLAUDE.md from the prep workspace into the project root:
```bash
cp /llm_models_python_code_src/GoogleDeepMindVercelHackathon/output/CLAUDE.md ./CLAUDE.md
```

## Step 12: Verify

```bash
npm run dev
```

Confirm the app starts on localhost:3000 before proceeding to feature skills.
