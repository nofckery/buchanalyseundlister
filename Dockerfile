# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Kopiere virtualenv von builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash app_user

# Create necessary directories with correct permissions
RUN mkdir -p /app && chown app_user:app_user /app
WORKDIR /app

# Switch to non-root user
USER app_user
# app/static/uploads wird nicht mehr lokal benötigt

# Copy application code
COPY --chown=app_user:app_user . .
# Berechtigungen für app/static/uploads nicht mehr benötigt

# Environment configuration - Wird jetzt zur Laufzeit von Cloud Run injiziert
ENV PORT=8080 \
    PYTHONUNBUFFERED=1

# HEALTHCHECK entfernt, da Cloud Run eigene Probes verwendet

# Start command with proper timeout and graceful shutdown
# Workers und Threads über ENV konfigurierbar machen
CMD exec gunicorn \
    --bind :${PORT} \
    --workers ${GUNICORN_WORKERS:-1} \
    --threads ${GUNICORN_THREADS:-8} \
    --timeout ${GUNICORN_TIMEOUT:-30} \
    --graceful-timeout 30 \
    --keep-alive 65 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-class gthread \
    main:app