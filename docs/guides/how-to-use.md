# ArchIntel User Guide

> Upload your architecture. Talk to it. Understand its risks and costs in seconds.

---

## Getting Started

### Access the Application

Open **https://archintel-346168839454.us-central1.run.app** in a modern browser (Chrome, Edge, or Firefox recommended).

You will see a dark-mode interface with:
- An **upload zone** on the left for your architecture diagram
- A **tabbed panel** on the right with three analysis modes: Voice, Security, and Costs

---

## Step 1: Upload Your Architecture Diagram

1. **Drag and drop** an architecture diagram image onto the upload zone, or **click** to browse your files.
2. Supported formats: **PNG, JPG, JPEG, SVG, WebP** (up to 10MB).
3. Once uploaded, a preview of your diagram appears with the filename and size.
4. To replace the diagram, click the **X** button on the preview and upload a new one.

**Tips for best results:**
- Use clear, labeled diagrams with visible service names (e.g., "EC2", "S3", "Load Balancer").
- Architecture diagrams from AWS, GCP, Azure, or tools like Excalidraw, Lucidchart, and draw.io all work well.
- Higher resolution images produce better analysis.

---

## Step 2: Choose an Analysis Tab

### Voice Analysis (Purple Tab)

Talk to your architecture diagram using natural speech. Gemini sees your diagram and responds with spoken analysis.

1. Click the **Voice** tab (selected by default).
2. Click **"Start Voice Analysis"**.
3. Your browser will request **microphone permission** — click Allow.
4. Gemini will automatically analyze your diagram and begin speaking about what it sees.
5. **Ask follow-up questions naturally:**
   - "What are the biggest security risks?"
   - "How much would this cost per month?"
   - "Is the database connection secure?"
   - "What would you change about this architecture?"
6. A **real-time transcript** appears below as you converse.
7. Click **"End Session"** when you're finished.

**Controls:**
- **Mute/Unmute** — Toggle your microphone without ending the session.
- **LIVE badge** — Green pulsing indicator confirms the connection is active.

---

### Security Analysis (Red Tab)

Get a comprehensive STRIDE threat model with auto-generated Terraform remediation policies.

1. Click the **Security** tab.
2. Click **"Run Analysis"**.
3. The analysis streams in real-time with the following sections:
   - **Architecture Overview** — What Gemini sees in your diagram.
   - **Critical Threats** — High-severity vulnerabilities requiring immediate attention.
   - **Medium Threats** — Moderate risks to address.
   - **Low Threats** — Informational findings.
   - **Remediation Summary** — Prioritized list of fixes.
4. Below the analysis, **Terraform policy files** are automatically generated for each critical threat.
5. Each Terraform file shows:
   - Filename (e.g., `iam_policy.tf`)
   - Severity badge (CRITICAL, HIGH, MEDIUM)
   - Threat name it remediates
   - Full HCL code with syntax highlighting
6. Click the **copy icon** on any Terraform file to copy it to your clipboard.

**What is STRIDE?**

| Category | Question |
|----------|----------|
| **S**poofing | Can an attacker impersonate a component? |
| **T**ampering | Can data be modified in transit or at rest? |
| **R**epudiation | Are actions logged and attributable? |
| **I**nformation Disclosure | Can sensitive data leak? |
| **D**enial of Service | Can a component be overwhelmed? |
| **E**levation of Privilege | Can access controls be bypassed? |

---

### Cost Estimation (Green Tab)

Get a cloud cost breakdown through a conversational interface that asks clarifying questions.

1. Click the **Costs** tab.
2. Click **"Estimate Costs"**.
3. CostSight will identify the cloud services in your diagram and ask clarifying questions:
   - "How many requests per month do you expect?"
   - "What's your estimated data storage volume?"
   - "Which region will this be deployed in?"
4. **Type your answers** in the text input at the bottom and press Enter or click Send.
5. Once it has enough information, CostSight produces:
   - A **per-service cost breakdown** table.
   - **Total monthly and annual estimates**.
   - **Optimization suggestions** to reduce costs.
6. Continue the conversation to refine estimates with different parameters.

**Example conversation:**
```
You:       "We expect 1M requests/month with 500GB storage in us-east1"
CostSight: "Based on your parameters, here's the monthly breakdown:
            | Service          | Monthly Cost |
            |-----------------|-------------|
            | EC2 (t3.medium) | $30.37      |
            | S3 Storage      | $11.50      |
            | RDS PostgreSQL  | $24.82      |
            | Load Balancer   | $18.25      |
            | Total           | $84.94/mo   |

            Optimization: Consider using Lambda instead of EC2
            for request handling — at 1M requests/month, you'd
            save approximately $15/month."
```

---

## Supported Cloud Services (Cost Estimation)

CostSight recognizes and prices the following services:

| Provider | Services |
|----------|----------|
| **AWS** | EC2, S3, RDS, Lambda, ELB, DynamoDB, ElastiCache, SQS, CloudFront |
| **GCP** | Cloud Run, Cloud SQL, GKE, Cloud Storage, BigQuery, Pub/Sub, Load Balancer, Memorystore, Cloud Functions, API Gateway |

---

## Browser Requirements

| Feature | Requirement |
|---------|------------|
| Voice Analysis | Microphone access, Web Audio API (Chrome 66+, Firefox 76+, Edge 79+) |
| Security Analysis | Modern browser with fetch streaming support |
| Cost Estimation | Modern browser with fetch support |
| General | JavaScript enabled, screen width 768px+ recommended |

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Voice not working | Ensure microphone permissions are granted. Check that no other app is using the mic. |
| "Connection error" on Voice | Refresh the page and try again. The Gemini WebSocket session may have timed out. |
| Analysis seems stuck | Check your internet connection. The AI model may take 5-10 seconds to begin streaming. |
| Diagram not recognized | Use a clearer image with labeled components. PNG format at 1000px+ width works best. |
| Terraform not appearing | The model generates Terraform for critical threats only. If no critical threats are found, no files are generated. |
| Cost estimate seems off | Provide more specific traffic details. The pricing data covers standard configurations — actual costs may vary. |

---

## Local Development

To run ArchIntel locally:

```bash
cd archintel
cp .env.local.example .env.local
# Edit .env.local and add your Gemini API key

npm install
npm run dev
```

Open http://localhost:3000 in your browser.

**Required environment variable:**
- `GOOGLE_GENERATIVE_AI_API_KEY` — Your Google Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
