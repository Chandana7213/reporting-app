# Reporting App

A small Flask service that demonstrates a production-style Google Cloud Run
deployment integrated with Cloud Storage and Cloud SQL, deployed via CI/CD.

It is written so the **same code** carries through all seven build layers with
no rewrites: it runs fully on your laptop with zero cloud setup, and the cloud
features switch on automatically as you supply their environment variables.

## What it does

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Landing page with an upload form and a live status panel |
| `/upload` | POST | Saves an uploaded file (to GCS, or locally if no bucket set) |
| `/dbtest` | GET | Runs `SELECT NOW();` against Cloud SQL |
| `/healthz` | GET | Plain health check (returns `ok`) |

## Project layout

```
reporting-app/
├── app.py                      # Flask app (all routes + helpers)
├── requirements.txt            # Pinned Python dependencies
├── Dockerfile                  # Container build (Layer 2)
├── .dockerignore               # Keeps secrets/junk out of the image
├── .gitignore                  # Keeps secrets out of Git
├── .env.example                # Documents the configurable env vars
├── cloudbuild.yaml             # CI/CD Option A — Cloud Build (Layer 7)
├── templates/
│   └── index.html              # Landing page
└── .github/workflows/
    └── deploy.yml              # CI/CD Option B — GitHub Actions (Layer 7)
```

## Run it locally (Layer 1)

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:8080 . With no env vars set:
- uploads are saved to a local `local_uploads/` folder,
- `/dbtest` reports that Cloud SQL is not configured (it does not error).

## Run it in Docker (Layer 2)

```bash
docker build -t reporting-app .
docker run -p 8080:8080 reporting-app
```

## Environment variables

Copy `.env.example` to `.env` for local testing (never commit `.env`).

| Variable | Activates | Notes |
|----------|-----------|-------|
| `BUCKET_NAME` | Layer 4 — GCS uploads | Name of your bucket |
| `INSTANCE_CONNECTION_NAME` | Layer 5 — Cloud SQL | `project:region:instance` |
| `DB_NAME`, `DB_USER` | Layer 5 | Default `reportdb` / `reportuser` |
| `DB_PASSWORD` | Layer 5/6 | Injected from Secret Manager in the cloud |
| `SECRET_KEY` | optional | Flask flash-message signing |
| `PORT` | set by Cloud Run | Defaults to 8080 |

## Deploy & CI/CD

Follow the runbook (RB-2026-014). In short:
1. Build & push with `gcloud builds submit`.
2. `gcloud run deploy` with the env vars, `--add-cloudsql-instances`,
   and `--set-secrets DB_PASSWORD=db-password:latest`.
3. Add the Cloud Build trigger (`cloudbuild.yaml`) so a push to `main`
   auto-deploys — or use the GitHub Actions workflow instead.

## Security notes

- No credentials are hard-coded; everything comes from env vars / Secret Manager.
- `.env`, `key.json`, and service-account JSON files are git-ignored.
- The Cloud SQL connector authenticates via the attached service account —
  there is no host/IP or password in any connection string.
