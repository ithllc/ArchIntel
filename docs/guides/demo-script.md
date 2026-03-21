# ArchIntel Demo Script

> Verbal walkthrough for testing all 5 GCP diagrams + the multi-cloud diagram.
> Each diagram tests progressively harder analysis. Use these scripts for the Voice tab, then verify Security and Costs tabs.

---

## Diagram 06 — GCP Static Website (Easy)

**Upload:** `docs/test-diagrams/06-easy-gcp-static-site.svg`

### Voice Tab Script

> "Hey ArchIntel, I just uploaded a simple static website architecture on Google Cloud. Can you walk me through what you see?"

*(Wait for response, then follow up:)*

> "Are there any security risks with this setup? I'm particularly worried about the Cloud Storage bucket being publicly accessible."

> "What would this cost me per month if I get about 100,000 page views per day?"

### Security Tab — What to Expect
- **Architecture Overview:** Cloud DNS → Cloud CDN → Cloud Storage with an HTTPS load balancer.
- **Key Threats:** Public bucket misconfiguration (Information Disclosure), missing HTTPS enforcement (Tampering), no WAF (DoS).
- **Terraform:** Bucket IAM policy, SSL enforcement policy.

### Costs Tab Script
> Click "Estimate Costs" then type:
> "We expect 100,000 page views per day, about 5GB of static assets, serving from the US."

---

## Diagram 07 — GCP API Backend (Easy-Medium)

**Upload:** `docs/test-diagrams/07-easy-medium-gcp-api.svg`

### Voice Tab Script

> "I've uploaded our API backend architecture. It uses Cloud Run, Cloud SQL, Memorystore, and Pub/Sub. Can you analyze the security posture?"

*(Wait, then:)*

> "We're storing user data in Cloud SQL. What STRIDE threats should we be worried about for the database connection?"

> "If we switch from Cloud Run to GKE, what would change from a security perspective?"

### Security Tab — What to Expect
- **Architecture Overview:** Load Balancer → Cloud Run API + Worker → Cloud SQL + Redis + Storage + Pub/Sub.
- **Key Threats:** SQL injection via API (Tampering), unencrypted Redis traffic (Information Disclosure), over-permissive IAM on Pub/Sub (Elevation of Privilege), missing VPC connector on Cloud Run (Spoofing).
- **Terraform:** VPC connector config, Cloud SQL SSL enforcement, IAM bindings.

### Costs Tab Script
> Click "Estimate Costs" then type:
> "We expect 500,000 API requests per day, 50GB database, 10GB Redis cache, and about 200GB in Cloud Storage."

---

## Diagram 08 — GCP Three-Tier E-Commerce (Medium)

**Upload:** `docs/test-diagrams/08-medium-gcp-three-tier.svg`

### Voice Tab Script

> "This is our e-commerce platform architecture. It runs on GKE Autopilot with a Next.js frontend, Go API gateway, and Python cart service. The data tier has Cloud SQL, Memorystore, and BigQuery. Tell me about the security risks."

*(Wait, then:)*

> "What about the Cloud Functions — the email notification and payment webhook handlers? Are those properly isolated?"

> "If a bad actor compromised the cart service pod, how far could they move laterally within the GKE cluster?"

### Security Tab — What to Expect
- **Architecture Overview:** Cloud Armor → LB → GKE (3 services) + Cloud Functions → Cloud SQL + Redis + BigQuery.
- **Key Threats:** Lateral movement in GKE without NetworkPolicies (Elevation of Privilege), PCI data in Cloud SQL without CMEK (Information Disclosure), Cloud Functions with overly broad IAM (Elevation of Privilege), Pub/Sub messages not encrypted (Tampering), no pod security standards (Spoofing).
- **Terraform:** GKE NetworkPolicy, Pod Security Standards, Cloud SQL CMEK, IAM least-privilege for Cloud Functions.

### Costs Tab Script
> Click "Estimate Costs" then type:
> "This is an e-commerce site doing about 2 million page views per month, 10,000 orders per day, 100GB PostgreSQL database, 500GB product images, and we query BigQuery about 1TB per month for analytics."

---

## Diagram 09 — GCP FinTech Microservices (Hard)

**Upload:** `docs/test-diagrams/09-hard-gcp-microservices.svg`

### Voice Tab Script

> "I uploaded our FinTech platform architecture. It's a complex setup with Apigee API Gateway, GKE with Istio service mesh, four microservices handling accounts, payments, ledger, and notifications. We also have Cloud Run workers for fraud detection and compliance, Vertex AI for ML models, Cloud Spanner for global transactions, Bigtable for time-series data, and BigQuery for analytics. Can you do a thorough STRIDE analysis?"

*(Wait for the analysis, then:)*

> "We're PCI-DSS compliant. Does the payment service architecture look right for PCI scope isolation? Is there anything in the Istio mesh config that concerns you?"

> "What's the single biggest security risk you see in this entire architecture?"

### Security Tab — What to Expect
- **Architecture Overview:** Apigee + Cloud Armor → GKE Istio mesh (4 services) + Cloud Run (4 workers) + Vertex AI → Spanner + Bigtable + BigQuery.
- **Key Threats:** PCI scope creep if payment service shares namespace (Elevation of Privilege), Vertex AI model poisoning (Tampering), Spanner cross-region access without VPC SC (Information Disclosure), Pub/Sub dead-letter queue data exposure (Information Disclosure), binary authorization bypass (Spoofing), insufficient audit logging on Spanner writes (Repudiation), DDoS on Apigee if rate limits misconfigured (DoS).
- **Terraform:** VPC Service Controls perimeter, Binary Authorization policy, Workload Identity bindings, KMS CMEK for Spanner, Pub/Sub DLQ encryption.

### Costs Tab Script
> Click "Estimate Costs" then type:
> "This is a FinTech platform processing 50,000 transactions per day, 500GB in Spanner, 2TB in Bigtable, 5TB scanned in BigQuery monthly, 20 Vertex AI prediction endpoints running 24/7, and the GKE cluster averages 30 nodes."

---

## Diagram 05 — Multi-Cloud Event-Driven (Hard)

**Upload:** `docs/test-diagrams/05-hard-event-driven-multi-cloud.svg`

### Voice Tab Script

> "This is our multi-cloud architecture spanning AWS and GCP. On the AWS side we have Lambda functions with CQRS pattern, EventBridge, SQS queues, DynamoDB as an event store, Aurora for read models, and S3 data lake. On the GCP side we have Cloud Pub/Sub, Cloud Run for ML inference and data pipelines, Vertex AI for model training, BigQuery for analytics, and Cloud SQL. There's a VPN tunnel connecting both clouds. Can you analyze the full security posture across both environments?"

*(Wait, then:)*

> "The VPN tunnel between AWS and GCP — what specific threats does that cross-cloud connection introduce?"

> "If we had to choose one thing to fix first across this entire architecture, what would you recommend?"

### Security Tab — What to Expect
- **Architecture Overview:** AWS (Lambda + EventBridge + DynamoDB + Aurora + S3) ←VPN→ GCP (Cloud Run + Vertex AI + BigQuery + Cloud SQL).
- **Key Threats:** VPN tunnel as single point of attack (Tampering + Information Disclosure), inconsistent IAM policies across clouds (Elevation of Privilege), cross-cloud data sovereignty issues (Information Disclosure), EventBridge → Pub/Sub event replay without deduplication (Repudiation), Lambda cold-start timing attacks (DoS), unencrypted Kinesis stream (Information Disclosure), ML model exfiltration from Vertex AI (Information Disclosure).
- **Terraform:** AWS VPN config with encryption, cross-cloud IAM federation, S3 bucket policies, GCP VPC Service Controls.

### Costs Tab Script
> Click "Estimate Costs" then type:
> "The AWS side handles 2 million Lambda invocations per day, 100GB DynamoDB, 500GB Aurora, 2TB S3 data lake. The GCP side runs 10 Cloud Run instances 24/7, trains ML models weekly on Vertex AI, scans 3TB in BigQuery monthly, and the VPN tunnel transfers about 500GB per month between clouds."

---

## Testing Checklist

For each diagram, verify:
- [ ] **Voice tab:** Gemini responds with spoken analysis. Transcript appears.
- [ ] **Security tab:** STRIDE analysis streams in. Terraform files generated for critical threats.
- [ ] **Costs tab:** CostSight identifies services, asks clarifying questions, produces cost table.
- [ ] **Supabase:** Check the Supabase dashboard — records should appear in `threat_models`, `generated_policies`, `cost_estimates`, and `chat_logs` tables.
