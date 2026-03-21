---
name: demo-prep
description: Prepare demo materials for ArchIntel — test architecture diagrams, pitch script, submission checklist, and demo video guidance.
user_invocable: true
---

# Demo Preparation

Prepare everything needed for the 3-minute live demo and hackathon submission.

## Test Architecture Diagrams

Create or source 2-3 test diagrams that showcase the product well:

### Diagram 1: AWS Web Application (Primary Demo)
A typical 3-tier web app with:
- CloudFront CDN → ALB → EC2 instances (auto-scaling)
- RDS PostgreSQL (primary + read replica)
- S3 for static assets
- ElastiCache Redis for sessions
- SQS for async processing

**Why this diagram:** It has enough services to produce a rich STRIDE analysis (public-facing endpoints, database access, caching layer) AND a meaningful cost estimate across compute, storage, and networking.

### Diagram 2: Microservices Architecture (Backup)
- API Gateway → 4 Cloud Run services
- Pub/Sub between services
- Cloud SQL shared database
- Cloud Storage for uploads
- Load Balancer

### Sourcing Diagrams
Use any publicly available architecture diagram images. Good sources:
- AWS Architecture Center example diagrams
- GCP Architecture Center example diagrams
- Draw.io / Excalidraw exported PNGs

Save test diagrams to `public/test-diagrams/` in the project.

## 3-Minute Demo Script

### Opening (0:00 - 0:15)
"What if you could talk to your architecture diagram and it talked back?"

### Voice Demo — The Wow Moment (0:15 - 0:55)
1. Drag and drop the AWS diagram onto the upload zone
2. Switch to the Voice tab. Click "Start Voice Analysis"
3. **SAY OUT LOUD**: "Analyze this architecture for security risks."
4. Let Gemini speak back — it describes the diagram and identifies threats
5. Follow up: "What about the S3 bucket?" — Gemini responds naturally
6. Point out the real-time transcript appearing below

### ThreatOps Demo (0:55 - 1:45)
1. Switch to Security tab. Click "Run Analysis"
2. Show STRIDE analysis streaming in real-time
3. Point out: "Same analysis, now in written detail with STRIDE categories"
4. Scroll to generated Terraform: "And it auto-generates the remediation policies"

### CostSight Demo (1:45 - 2:30)
1. Switch to Cost tab. Click "Estimate Costs"
2. AI identifies services from the diagram
3. Type: "1 million requests per month, 500GB storage"
4. Show cost breakdown table appearing
5. Point out the optimization suggestion

### Closing (2:30 - 3:00)
"One diagram. Three dimensions of intelligence. Talk to it. Read the threats. Understand the costs. ArchIntel.

Built today with Gemini 2.5 Flash Native Audio for voice, Gemini 1.5 Pro for vision, Vercel AI SDK, and Supabase. This is architecture intelligence."

## Submission Checklist

- [ ] Repository is **public** on GitHub
- [ ] README.md has: project name, description, tech stack, setup instructions
- [ ] Demo URL is live on Cloud Run and accessible
- [ ] 1-minute demo video recorded (screen recording of the happy path)
- [ ] All team members added to submission
- [ ] Code is clean — no .env files committed, no secrets in repo
- [ ] Submission form completed at cerebralvalley.ai

## 1-Minute Video Script (for submission)
1. Show the app loading (2s)
2. Upload a diagram (3s)
3. Voice tab — speak and get spoken response (20s)
4. Security tab — show streaming STRIDE + Terraform (15s)
5. Cost tab — show chat + breakdown (15s)
6. End showing all three tabs worked (5s)

Record with: OBS, Loom, or QuickTime. Keep it tight — no narration needed, just the UI flow. For voice, make sure audio is captured.

## Pre-Demo Checklist (5 minutes before)
- [ ] Cloud Run instance is warm (min-instances=1)
- [ ] Test diagram ready in Downloads folder
- [ ] Browser open with app loaded, no other tabs
- [ ] WiFi connected and tested
- [ ] **Microphone permission pre-granted** (visit site once, allow mic)
- [ ] **Speaker volume up** (Gemini voice responses need to be audible)
- [ ] Test voice session works (do a quick "hello" test)
- [ ] Backup: screenshot of working demo in case of WiFi issues
