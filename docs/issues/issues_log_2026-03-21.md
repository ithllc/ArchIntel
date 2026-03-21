# ArchIntel Issues Log — 2026-03-21

> Discovered during UAT of Diagram 06 (GCP Static Website)

| # | Title | Severity | Type | Feature | GitHub |
|---|-------|----------|------|---------|--------|
| 1 | ThreatOps: AI_DownloadError on data: URL | Blocker | Bug | Security Tab | [#1](https://github.com/ithllc/ArchIntel/issues/1) |
| 2 | CostSight: UIMessage vs ModelMessage schema mismatch | Blocker | Bug | Costs Tab | [#2](https://github.com/ithllc/ArchIntel/issues/2) |
| 3 | CostSight: data: URL in sendMessage files rejected | Blocker | Bug | Costs Tab | [#3](https://github.com/ithllc/ArchIntel/issues/3) |
| 4 | Voice: ephemeral token exposes API key | Moderate | Security | Voice Tab | [#4](https://github.com/ithllc/ArchIntel/issues/4) |
| 5 | Automated Security & Cost Analysis Pipeline from Voice Analysis | Major | Missing Feature | Voice + Security + Costs | [#5](https://github.com/ithllc/ArchIntel/issues/5) |

## Logging & Observability Notes

**Where logs reside:**
- **Cloud Run stdout/stderr** → Google Cloud Logging (auto-collected)
- **Structured logs** → `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="archintel"'`
- **Supabase** → threat_models, generated_policies, cost_estimates, chat_logs tables

**What is currently logged:**
- API route errors via `console.error()` (caught by Cloud Run → Cloud Logging)
- Supabase insert results (silent failures — no explicit logging)
- Next.js build and runtime errors

**What is NOT logged (gaps):**
- No request-level logging (which endpoints are called, latency, status codes)
- No structured JSON logging (just unstructured text)
- No Supabase operation error logging
- No voice session metrics (duration, transcript length)
