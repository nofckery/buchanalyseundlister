# Base Image
FROM python:3.9-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Erstelle notwendige Verzeichnisse
RUN mkdir -p app/cache/prices \
    app/cache/metadata \
    instance
# app/static/uploads wird nicht mehr lokal benötigt

# Anwendungscode kopieren
COPY . .

# Berechtigungen setzen
RUN chmod -R 755 app/cache/prices \
    app/cache/metadata \
    instance
# Berechtigungen für app/static/uploads nicht mehr benötigt

# Port für Cloud Run
ENV PORT 8080

# Umgebungsvariablen für Produktion
ENV FLASK_ENV=production
ENV GOOGLE_CLOUD_PROJECT=buchanalyse-prod

# Start-Befehl
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app