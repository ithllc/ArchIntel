---
name: deploy-cloud-run
description: Deploy the ArchIntel Next.js app to Google Cloud Run. Handles Docker build, push to Artifact Registry, and Cloud Run service deployment.
user_invocable: true
---

# Deploy to Google Cloud Run

Deploy the ArchIntel Next.js application to Google Cloud Run.

## Prerequisites
- The app builds successfully (`npm run build`)
- Dockerfile exists in project root (created by scaffold-app skill)
- gcloud CLI is authenticated
- Project ID: `gdm-hacks2603-nyc-5752`

## Step 1: Authenticate gcloud

```bash
gcloud auth login
gcloud config set project gdm-hacks2603-nyc-5752
```

## Step 2: Enable Required APIs

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

## Step 3: Create Artifact Registry Repository (if not exists)

```bash
gcloud artifacts repositories create archintel \
  --repository-format=docker \
  --location=us-east1 \
  --description="ArchIntel Docker images"
```

## Step 4: Build and Push with Cloud Build

This is the fastest path — no local Docker needed:

```bash
gcloud builds submit --tag us-east1-docker.pkg.dev/gdm-hacks2603-nyc-5752/archintel/app:latest .
```

## Step 5: Deploy to Cloud Run

```bash
gcloud run deploy archintel \
  --image us-east1-docker.pkg.dev/gdm-hacks2603-nyc-5752/archintel/app:latest \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --port 3000 \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --set-env-vars "GOOGLE_GENERATIVE_AI_API_KEY=AIzaSyCNvQtMjBdow_RChx8eVeSSZG1jjBJaqrM" \
  --set-env-vars "NEXT_PUBLIC_SUPABASE_URL=<FILL_IN>" \
  --set-env-vars "NEXT_PUBLIC_SUPABASE_ANON_KEY=<FILL_IN>"
```

**IMPORTANT:** Replace the Supabase values with actual values from the Supabase dashboard before deploying.

## Step 6: Verify Deployment

```bash
# Get the service URL
gcloud run services describe archintel --region us-east1 --format='value(status.url)'
```

Visit the URL in a browser and verify:
1. The app loads with the dark mode UI
2. You can upload a diagram
3. The threat analysis streams correctly
4. The cost chat works

## Quick Redeploy (after code changes)

```bash
gcloud builds submit --tag us-east1-docker.pkg.dev/gdm-hacks2603-nyc-5752/archintel/app:latest . && \
gcloud run deploy archintel \
  --image us-east1-docker.pkg.dev/gdm-hacks2603-nyc-5752/archintel/app:latest \
  --region us-east1
```

## Troubleshooting

- **Build fails:** Check that `next.config.ts` has `output: 'standalone'`
- **503 errors:** Check Cloud Run logs: `gcloud run services logs read archintel --region us-east1`
- **Timeout:** Gemini calls can take 10-30s. Cloud Run default timeout is 300s which is fine.
- **Memory issues:** Bump to `--memory 2Gi` if needed
- **Cold start slow:** Set `--min-instances 1` for always-warm (costs more but better for demo)

## For Demo Day

Set min-instances to 1 to avoid cold starts during the live demo:

```bash
gcloud run services update archintel --region us-east1 --min-instances 1
```
