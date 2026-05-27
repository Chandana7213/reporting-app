# ---- Reporting App container ----
# Small, reproducible image for Cloud Run.

FROM python:3.11-slim

# Don't buffer stdout/stderr — logs show up immediately in Cloud Run.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application.
COPY . .

# Cloud Run sends traffic to $PORT (8080). gunicorn must bind 0.0.0.0.
EXPOSE 8080

# 'app:app' = the Flask object named `app` inside app.py
# --workers 2 / --threads 8 is a sensible small default for Cloud Run.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 8 --timeout 60 app:app
