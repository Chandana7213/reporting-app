# Reporting App — Cloud Run + Cloud Storage + Cloud SQL

A production-ready Flask application that demonstrates a complete **3-tier cloud architecture** on Google Cloud Platform. 

The same codebase runs **identically** at every stage:
- **Locally on your laptop** with no cloud setup (Layer 1)
- **In Docker** (Layer 2)
- **Live on Cloud Run** with Cloud Storage + Cloud SQL (Layers 3–5)
- **Automatically deployed** via CI/CD on every push to main (Layer 7)

Cloud features **gracefully activate** as you set environment variables — no code rewrites needed.

---

## What This App Does

| Feature | Endpoint | Purpose |
|---------|----------|---------|
| **Home Page** | `GET /` | Upload form + live system status dashboard |
| **File Upload** | `POST /upload` | Save files to Cloud Storage or local folder |
| **Upload Records** | `GET /uploads` | View all uploaded files (name, path, size, timestamp) |
| **Database Test** | `GET /dbtest` | Query Cloud SQL — returns server timestamp |
| **Health Check** | `GET /healthz` | Returns `ok` for monitoring |

---

## Project Structure

```
reporting-app/
├── app.py                        # Flask application (all routes + database logic)
├── requirements.txt              # Python dependencies (pinned versions)
├── Dockerfile                    # Multi-stage container build
├── .dockerignore                 # Excludes build artifacts, secrets from image
├── .gitignore                    # Prevents secrets, venv from Git
├── .env.example                  # Template for environment variables
├── cloudbuild.yaml               # Cloud Build CI/CD pipeline (Layer 7)
├── templates/
│   ├── index.html                # Home page with upload form
│   └── uploads.html              # View all upload records
├── .github/workflows/
│   └── deploy.yml                # GitHub Actions CI/CD alternative
└── local_uploads/                # (Auto-created) Local file storage fallback
```

---

## Getting Started

### Layer 1: Run Locally

**Requirements:**
- Python 3.9+ installed
- pip (Python package manager)

**Steps:**

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Chandana7213/reporting-app.git
   cd reporting-app
   ```

2. **Create a virtual environment** (keeps dependencies isolated):
   ```bash
   python -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

5. **Test it:**
   - Open http://localhost:8080
   - You'll see the reporting app with a status panel
   - Cloud Storage shows "local fallback" (files save to `./local_uploads/`)
   - Cloud SQL shows "not configured" (no database yet)
   - Try uploading a file — it saves locally

**To stop:** Press `Ctrl+C` in the terminal

 **Layer 1 complete** — the app works entirely on your machine with zero cloud setup.

---

### Layer 2: Dockerize (Optional Local Test)

**Requirements:**
- Docker Desktop installed

**Steps:**

1. **Build the container image:**
   ```bash
   docker build -t reporting-app .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8080:8080 reporting-app
   ```

3. **Test it:**
   - Open http://localhost:8080
   - Same behavior as Layer 1 (still running locally, just in a container)

4. **Stop:**
   - Press `Ctrl+C`

 **Layer 2 complete** — the app runs identically inside a container (the same form Cloud Run will use).

---

## Deploy to Google Cloud (Layers 3–7)

### Prerequisites

- **Google Cloud account** with billing enabled (Cloud Run has a free tier; Cloud SQL costs ~$0.03/hour for Sandbox)
- **gcloud CLI** installed locally, or use **Cloud Shell** in the browser (recommended)
- **GitHub account** with this repo (needed for CI/CD)

### Quick Reference: Environment Variables

These control which cloud features are active. Set them on Cloud Run:

| Variable | Purpose | Example |
|----------|---------|---------|
| `BUCKET_NAME` | Activates Cloud Storage uploads (Layer 4) | `reporting-app-files-slabs2026` |
| `INSTANCE_CONNECTION_NAME` | Activates Cloud SQL (Layer 5) | `my-project:asia-south1:my-instance` |
| `DB_NAME` | Cloud SQL database name (Layer 5) | `reportdb` |
| `DB_USER` | Cloud SQL user login (Layer 5) | `reportuser` |
| `DB_PASSWORD` | Cloud SQL password (moved to Secret Manager in Layer 6) | (injected from Secret Manager) |
| `SECRET_KEY` | Flask session signing (optional) | Any string |
| `PORT` | Server port (set by Cloud Run) | `8080` |

### Detailed Deployment Steps

**For a complete, step-by-step walkthrough of Layers 3–7, see the runbook:**
📘 **[RB-2026-014: Deploy GitHub Reporting App on Cloud Run](./runbook-2026-014.docx)**

The runbook includes:
-  Click-by-click GCP Console instructions
-  Exact gcloud commands for every step
-  Creating Cloud SQL, Cloud Storage, and IAM roles
-  Wiring up Secret Manager for secure passwords
-  Setting up CI/CD to auto-deploy on push
-  Troubleshooting guide
-  Cost cleanup checklist

### Quick Deploy (Command Line)

If you're familiar with gcloud:

```bash
# 1. Build image with Cloud Build
gcloud builds submit --tag asia-south1-docker.pkg.dev/YOUR_PROJECT/reporting-app-repo/reporting-app:v1 .

# 2. Deploy to Cloud Run
gcloud run deploy reporting-app-service \
  --image asia-south1-docker.pkg.dev/YOUR_PROJECT/reporting-app-repo/reporting-app:v1 \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars BUCKET_NAME=your-bucket-name \
  --add-cloudsql-instances YOUR_PROJECT:asia-south1:your-instance \
  --set-secrets DB_PASSWORD=db-password:latest
```

Replace `YOUR_PROJECT` with your actual GCP project ID.

---

## CI/CD: Automatic Deployment

### Option A: Cloud Build (Recommended for GCP)

Once deployed manually (above), create a Cloud Build trigger:

1. In GCP Console → Cloud Build → Triggers → Create Trigger
2. Select your GitHub repo (Chandana7213/reporting-app)
3. Branch: `main`
4. Build configuration: Cloud Build configuration file (`/cloudbuild.yaml`)
5. Service account: Use the compute service account with necessary roles

Now every push to `main` auto-builds and deploys a new revision. ✅

### Option B: GitHub Actions

Use the included `.github/workflows/deploy.yml`:

1. In your GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets:
   - `GCP_PROJECT_ID` = your GCP project
   - `GCP_SA_KEY` = service account JSON (⚠️ keep this secret!)
   - `GCP_REGION` = `asia-south1`

Every push to `main` triggers the workflow.

---

## Security Best Practices (Implemented)

 **No hard-coded credentials**
- All secrets come from environment variables or Secret Manager
- Passwords are never in code or git history

 **`.gitignore` prevents secrets from leaking**
```
.env              # Local config (never commit)
key.json          # Service account keys
*.json.key        # Cloud credentials
__pycache__/      # Python cache
venv/             # Virtual environment
local_uploads/    # Local files
```

 **`.dockerignore` keeps secrets out of images**
- Build artifacts, config files, and git metadata are excluded

 **Cloud SQL Connector (no IP-based connections)**
- Uses the Cloud SQL Auth Proxy
- Service account authentication (no password in connection strings)
- Only the app's service account can connect

 **Secret Manager (Layer 6)**
- Database passwords stored in encrypted vault
- Cloud Run pulls them at runtime, never visible in config

 **IAM least-privilege roles**
- Service account has only the permissions it needs
- Cloud Run can't access resources it doesn't need

---

## Local Testing with Cloud Credentials (Advanced)

To test cloud features locally (without deploying):

1. **Get a service account key** from GCP and save as `key.json`
2. **Authenticate:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=./key.json
   ```
3. **Set environment variables:**
   ```bash
   export BUCKET_NAME=your-bucket
   export INSTANCE_CONNECTION_NAME=project:region:instance
   export DB_NAME=reportdb
   export DB_USER=reportuser
   export DB_PASSWORD=your-password
   ```
4. **Run locally:**
   ```bash
   python app.py
   ```

The app now uses real Cloud Storage and Cloud SQL (not local fallbacks).

⚠️ **Never commit `key.json` or `.env` to Git** — they're already in `.gitignore`.

---

## Troubleshooting

### "Cloud Storage: local fallback"
- **Cause:** `BUCKET_NAME` env var not set
- **Fix:** Add it to Cloud Run environment variables (or set locally for testing)

### "Cloud SQL: not configured"
- **Cause:** `INSTANCE_CONNECTION_NAME` or `DB_PASSWORD` not set
- **Fix:** Set both on Cloud Run (or locally); ensure Cloud SQL instance is running

### "Database connection FAILED: password authentication failed"
- **Cause:** `DB_PASSWORD` doesn't match the database user's actual password
- **Fix:** Verify the password is correct; reset it if needed

### App won't start on Cloud Run
- **Cause:** Port mismatch (app expects 8080, Cloud Run doesn't bind it)
- **Fix:** Dockerfile already sets `EXPOSE 8080`; ensure Cloud Run port is `8080`

### Build fails with "dependency not found"
- **Cause:** Missing package in `requirements.txt`
- **Fix:** Add it and rebuild

For more troubleshooting, see the runbook (RB-2026-014).

---

## Cost Management

### What Costs Money

| Service | Cost | How to Avoid |
|---------|------|------------|
| **Cloud Run** | Free tier (2M requests/month) | Demo app uses <100K requests/month → Free |
| **Cloud SQL** | ~$0.03/hour for Sandbox | **Stop instance** when not testing |
| **Cloud Storage** | Free tier (5 GB) | Demo files <<5 GB → Free |
| **Artifact Registry** | Free tier (0.5 GB storage) | Keep only latest image |

### Cost Savings
- Stop Cloud SQL instance when not in use: `gcloud sql instances patch INSTANCE --activation-policy=NEVER`
- Delete unused Artifact Registry images
- Use Cloud Run's auto-scaling to zero (serverless = no cost when idle)

---

## Project Timeline (From Scratch)

| Layer | Task | Time | Effort |
|-------|------|------|--------|
| 1 | Run locally | 10 min | Easy — just `pip install` + `python app.py` |
| 2 | Dockerize | 15 min | Easy — `docker build` + `docker run` |
| 3 | Deploy to Cloud Run | 20 min | Medium — first GCP project setup |
| 4 | Add Cloud Storage | 15 min | Easy — create bucket + set env var |
| 5 | Add Cloud SQL | 45 min | Hard — database connection, credentials, IAM |
| 6 | Secret Manager | 10 min | Easy — move password to vault |
| 7 | CI/CD auto-deploy | 20 min | Medium — create trigger, test push |
| **Total** | **Full 3-tier + auto-deploy** | **2–3 hours** | Medium overall |

---

## Next Steps

1. **Read the runbook** (RB-2026-014) for detailed GCP instructions
2. **Run locally** (Layer 1) to confirm the code works
3. **Deploy to Cloud Run** (Layer 3) using the runbook's click-by-click steps
4. **Add Cloud Storage** (Layer 4) so uploads persist
5. **Wire Cloud SQL** (Layer 5) — the hardest but most important part
6. **Secure passwords** (Layer 6) with Secret Manager
7. **Automate with CI/CD** (Layer 7) so pushes auto-deploy

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   User's Browser                         │
│                https://...run.app                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   Cloud Run (Stateless) │  Layer 3
        │   • Flask app           │
        │   • Auto-scales         │
        │   • HTTPS / Public URL  │
        └──────┬────────┬─────────┘
               │        │
        ┌──────▼─┐  ┌───▼────────┐
        │ Cloud  │  │  Cloud SQL  │  Layers 4–5
        │Storage │  │ (PostgreSQL)│
        │ (GCS)  │  │ (Connector) │
        └────────┘  └─────┬──────┘
                          │
                    ┌─────▼──────┐
                    │   Secret    │  Layer 6
                    │   Manager   │  (passwords)
                    └─────────────┘

┌─────────────────────────────────────────────────────────┐
│                  GitHub → Cloud Build                    │  Layer 7
│        (Push to main → auto-build → auto-deploy)        │
└─────────────────────────────────────────────────────────┘
```

---

## Files Reference

### `app.py`
The Flask application with all routes:
- `home()` → render home page with status
- `upload()` → handle file upload (GCS or local)
- `view_uploads()` → show all uploaded files from database
- `dbtest()` → test Cloud SQL connection
- `healthz()` → health check

Includes graceful fallbacks for missing cloud features.

### `Dockerfile`
Multi-stage build:
1. Build stage — install dependencies
2. Runtime stage — Alpine Linux (small image)
3. Runs gunicorn (production WSGI server)
4. Binds to port 8080 for Cloud Run

### `cloudbuild.yaml`
Cloud Build pipeline:
1. Build Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run with environment variables

### `.env.example`
Template for local development. Copy to `.env` and fill in values:
```bash
BUCKET_NAME=
INSTANCE_CONNECTION_NAME=
DB_NAME=reportdb
DB_USER=reportuser
DB_PASSWORD=
SECRET_KEY=dev-only
```

---

## Common Questions

**Q: Can I use this without Cloud SQL?**  
A: Yes. Just don't set `INSTANCE_CONNECTION_NAME` — the app runs fine with only Cloud Storage. The database is optional.

**Q: What happens to my data if I delete the Cloud SQL instance?**  
A: It's gone permanently (unless you backed it up). Files in Cloud Storage remain.

**Q: How much does this cost per month?**  
A: For a demo with minimal traffic: **~$0 (free tier)** if you stop Cloud SQL. If left running 24/7: ~$20/month for Cloud SQL + minor Cloud Storage.

**Q: Can I use MySQL instead of PostgreSQL?**  
A: Yes, but requires code changes to `app.py`. Currently set for PostgreSQL.

**Q: How do I update the app after deploying?**  
A: With CI/CD: `git push origin main` and Cloud Build auto-deploys. Without CI/CD: manually push a new image and redeploy.

---

## Support & References

- **Google Cloud Documentation:** https://cloud.google.com/docs
- **Flask Documentation:** https://flask.palletsprojects.com/
- **Cloud SQL Python Connector:** https://github.com/GoogleCloudPlatform/cloud-sql-python-connector
- **Runbook (RB-2026-014):** Detailed step-by-step guide for all 7 layers

---

## License

This project is open-source for educational purposes.

---

**Last Updated:** May 2026  
**Status:** Production-ready template  
**Executed by:** D Chandana 
