"""
Reporting App - a small Flask service that demonstrates a production-style
Cloud Run deployment wired to Google Cloud Storage and Cloud SQL.

Design principle (important for the 7-layer build order):
  - The app ALWAYS runs, even with no cloud configured.
  - Cloud features switch on automatically when their env vars are present.
    * Set BUCKET_NAME           -> the /upload route writes to GCS
    * Set INSTANCE_CONNECTION_NAME (+ DB_* vars) -> /dbtest hits Cloud SQL
  - This lets you prove Layer 1 (local) before adding Layers 4 & 5.

All configuration comes from environment variables. NOTHING secret is
hard-coded, which satisfies the "nothing sensitive committed to Git" rule.
"""

import os
import datetime

from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
# SECRET_KEY is only used for flash messages. A dev default is fine locally;
# in the cloud you can override it with an env var.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# ---------------------------------------------------------------------------
# Configuration read from the environment (all optional for local running)
# ---------------------------------------------------------------------------
BUCKET_NAME = os.environ.get("BUCKET_NAME")          # GCS bucket (Layer 4)
INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")  # Cloud SQL (Layer 5)
DB_NAME = os.environ.get("DB_NAME", "reportdb")
DB_USER = os.environ.get("DB_USER", "reportuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD")          # from Secret Manager (Layer 6)

# Where uploads go when running locally without a bucket configured.
LOCAL_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "local_uploads")


# ===========================================================================
# Helper functions  (defined BEFORE the routes / __main__ block on purpose)
# A function used before it is defined raises NameError at runtime — keeping
# every helper up here avoids that whole class of bug.
# ===========================================================================

def cloud_storage_enabled():
    """True only when a bucket name has been configured."""
    return bool(BUCKET_NAME)


def cloud_sql_enabled():
    """True only when Cloud SQL connection details have been configured."""
    return bool(INSTANCE_CONNECTION_NAME and DB_PASSWORD)


def save_file(file_storage):
    """
    Save an uploaded file.
    - If a GCS bucket is configured, upload there and return a gs:// path.
    - Otherwise save to a local folder so the route still works on a laptop.
    Returns a human-readable location string.
    """
    filename = file_storage.filename

    if cloud_storage_enabled():
        # Imported lazily so the app still starts without the library locally.
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        # Upload the file stream directly — no temp file needed.
        blob.upload_from_file(file_storage.stream, content_type=file_storage.content_type)
        return f"gs://{BUCKET_NAME}/{filename}"

    # ---- local fallback ----
    os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(LOCAL_UPLOAD_DIR, filename)
    file_storage.save(dest)
    return dest


def get_db_connection():
    """
    Open a Cloud SQL (PostgreSQL) connection using the official connector.
    The connector handles auth via the attached service account, so there is
    NO host/IP and NO password in a connection string.
    """
    from google.cloud.sql.connector import Connector

    connector = Connector()
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,   # e.g. "project:asia-south1:reporting-app-sql"
        "pg8000",                   # pure-python driver, easy to install
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
    )
    return conn


def run_db_query():
    """Run a trivial query and return a status string."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT NOW();")
        row = cursor.fetchone()
        cursor.close()
        return f"Database connection OK. Server time: {row[0]}"
    finally:
        conn.close()


# ===========================================================================
# Routes
# ===========================================================================

@app.route("/")
def home():
    """Landing page + a live status panel showing which features are on."""
    status = {
        "storage": "enabled" if cloud_storage_enabled() else "local fallback",
        "bucket": BUCKET_NAME or "(none — saving to ./local_uploads)",
        "database": "enabled" if cloud_sql_enabled() else "not configured",
        "instance": INSTANCE_CONNECTION_NAME or "(none)",
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return render_template("index.html", status=status)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle a file upload (Layer 4 once a bucket is configured)."""
    if "report" not in request.files or request.files["report"].filename == "":
        flash("Please choose a file first.", "error")
        return redirect(url_for("home"))

    try:
        location = save_file(request.files["report"])
        flash(f"Uploaded successfully to: {location}", "success")
    except Exception as exc:  # noqa: BLE001 - surface the real error to the page
        flash(f"Upload failed: {exc}", "error")

    return redirect(url_for("home"))


@app.route("/dbtest")
def dbtest():
    """Run the Cloud SQL connectivity check (Layer 5)."""
    if not cloud_sql_enabled():
        return (
            "Cloud SQL is not configured yet. Set INSTANCE_CONNECTION_NAME, "
            "DB_USER, DB_NAME and DB_PASSWORD to enable this route.",
            200,
        )
    try:
        return run_db_query(), 200
    except Exception as exc:  # noqa: BLE001
        return f"Database connection FAILED: {exc}", 500


@app.route("/healthz")
def healthz():
    """Plain health check for Cloud Run / load balancers."""
    return "ok", 200


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    # Cloud Run injects PORT=8080. Locally we default to 8080 too.
    port = int(os.environ.get("PORT", 8080))
    # host=0.0.0.0 is REQUIRED so the container is reachable from outside.
    app.run(host="0.0.0.0", port=port, debug=True)
