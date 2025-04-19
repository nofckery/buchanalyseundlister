# Buch Analyse & Lister

Eine Python-basierte Webanwendung zur Analyse und Listung von Büchern auf eBay und Booklooker mit Hilfe der Gemini API.

**Live-Version:** [https://buchanalyse-382752202247.europe-west3.run.app/](https://buchanalyse-382752202247.europe-west3.run.app/)

## Features

- Foto-Upload für Buchcover und -seiten
- Automatische Analyse von Büchern mittels Google Gemini API
- Automatische Preisrecherche auf eurobuch.de
- Integration mit eBay Sandbox API für Buchlistungen
- Integration mit Booklooker API für Buchlistungen
- PostgreSQL-Datenbankunterstützung (Cloud SQL in Produktion)
- Benutzerfreundliche Weboberfläche
- Synchronisation des Buchbestands mit mehreren Plattformen

## Voraussetzungen

- Python 3.8 oder höher
- PostgreSQL (für lokale Entwicklung)
- Google Cloud SDK (`gcloud`) (für Deployment)
- Google Gemini API-Schlüssel
- eBay Entwickler-Zugangsdaten (Sandbox)
- Booklooker API-Zugangsdaten

## Installation (Lokal)

1.  Repository klonen:
    ```bash
    git clone <repository-url>
    cd buchanalyseundlister
    ```

2.  Virtuelle Umgebung erstellen und aktivieren:
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  Abhängigkeiten installieren:
    ```bash
    pip install -r requirements.txt
    ```

4.  Umgebungsvariablen konfigurieren (für lokale Entwicklung):
    ```bash
    # .env.example nach .env kopieren und anpassen
    cp .env.example .env
    ```

5.  Folgende Werte in der `.env`-Datei anpassen:
    - `DATABASE_URL`: PostgreSQL-Verbindungs-URL (z.B. `postgresql://user:password@localhost/buchdb` oder `sqlite:///instance/app.db`)
    - `SECRET_KEY`: Zufälliger Sicherheitsschlüssel für Flask
    - `GEMINI_API_KEY`: Google Gemini API-Schlüssel
    - eBay API-Zugangsdaten (für Sandbox-Umgebung)
    - `BOOKLOOKER_API_KEY`: Booklooker API-Schlüssel
    - `BOOKLOOKER_USER_TOKEN`: Booklooker Benutzer-Token (optional, wenn nicht benötigt)

6.  Lokale PostgreSQL-Datenbank erstellen (falls verwendet):
    ```bash
    # PostgreSQL-Konsole öffnen
    psql

    # Datenbank erstellen (Beispielname)
    CREATE DATABASE buchdb;
    CREATE USER buchapp WITH PASSWORD 'your_local_password';
    GRANT ALL PRIVILEGES ON DATABASE buchdb TO buchapp;
    ```

7.  Datenbank initialisieren und Anwendung starten:
    ```bash
    # Ggf. Datenbankmigrationen anwenden (falls Migrationsskripte vorhanden sind)
    # flask db upgrade 

    # Anwendung starten
    python main.py
    ```

Die Anwendung ist nun unter `http://localhost:5000` erreichbar.

## Deployment (Google Cloud Run)

Die Anwendung ist für das Deployment auf Google Cloud Run konfiguriert.

1.  **Voraussetzungen:**
    *   Google Cloud Projekt mit aktivierter Abrechnung.
    *   `gcloud` CLI installiert und konfiguriert (`gcloud init`, `gcloud auth login`).
    *   Cloud SQL Admin API, Cloud Build API, Cloud Run API, Secret Manager API aktiviert.

2.  **Konfiguration:**
    *   Eine Cloud SQL for PostgreSQL Instanz muss erstellt werden.
    *   Secrets für API-Schlüssel und Datenbankpasswort müssen im Google Secret Manager angelegt werden (siehe `create_secrets.ps1`).
    *   Ein dediziertes Service Account (`buchdb-user@...`) mit den Rollen `Cloud SQL Client` und `Secret Manager Secret Accessor` wird empfohlen.

3.  **Deployment-Schritte:**
    *   Kurzfassung der Deployment-Befehle (nach initialem Setup):
        ```bash
        # Image bauen und pushen
        gcloud builds submit --tag gcr.io/buchanalyse-prod/buchanalyse:latest

        # Service deployen/aktualisieren (Beispiel)
        # (Ersetzen Sie Platzhalter und passen Sie Umgebungsvariablen/Secrets nach Bedarf an)
        gcloud run deploy buchanalyse \
          --image gcr.io/buchanalyse-prod/buchanalyse:latest \
          --platform managed \
          --region europe-west3 \
          --allow-unauthenticated \
          --set-cloudsql-instances=buchanalyse-prod:europe-west3:buchdb-instance \
          --set-env-vars="INSTANCE_CONNECTION_NAME=buchanalyse-prod:europe-west3:buchdb-instance,DB_USER=cloud-run-user,DB_NAME=buchdb" \
          --update-secrets=DB_PASSWORD=DB_PASSWORD:latest \
          --service-account=buchdb-user@buchanalyse-prod.iam.gserviceaccount.com
        ```

4.  **Aktuelle URL:** [https://buchanalyse-382752202247.europe-west3.run.app/](https://buchanalyse-382752202247.europe-west3.run.app/)

## Nutzung

1.  **Buch hochladen**
    *   Auf der Startseite den "Neues Buch hochladen" Bereich nutzen
    *   Ein oder mehrere Fotos des Buches auswählen
    *   "Analysieren & Hochladen" klicken

2.  **Buchdaten bearbeiten**
    *   In der Buchliste auf "Bearbeiten" klicken
    *   Automatisch erkannte Daten überprüfen und anpassen
    *   Versandoptionen und Rückgaberichtlinie festlegen
    *   Änderungen speichern

3.  **Auf Verkaufsplattformen hochladen**
    *   Nach dem Bearbeiten und Speichern erscheint der "Auf eBay hochladen" Button
    *   Optional "Auf Booklooker hochladen" wählen
    *   Status der Listungen wird in der Übersicht angezeigt

## Projektstruktur

```
buchanalyseundlister/
├── app/
│   ├── __init__.py          # Flask-App-Initialisierung
│   ├── config.py            # Konfigurationslogik (lädt Secrets in Cloud Run)
│   ├── models.py            # Datenbankmodelle
│   ├── routes.py            # API-Routen und Hauptlogik
│   ├── ebay_api.py          # eBay API Integration
│   ├── booklooker_api.py    # Booklooker API Integration
│   ├── controllers/         # Controller-Logik
│   │   └── ...
│   ├── static/             # Statische Dateien
│   │   └── uploads/        # Hochgeladene Bilder
│   └── templates/          # HTML-Templates
│       ├── base.html       # Basis-Template
│       └── index.html      # Hauptseiten-Template
├── migrations/             # Alembic Migrationsskripte (optional)
├── instance/               # Instanz-Ordner (z.B. für lokale SQLite DB)
├── .env.example           # Beispiel-Umgebungsvariablen für lokale Entwicklung
├── .env                   # Lokale Umgebungsvariablen (nicht versioniert)
├── app.yaml               # Konfiguration für Google App Engine (alternativ zu Cloud Run)
├── Dockerfile             # Docker-Konfiguration für Cloud Run
├── .dockerignore          # Dateien, die im Docker-Image ignoriert werden
├── main.py               # Anwendungs-Einstiegspunkt
├── requirements.txt      # Python-Abhängigkeiten
├── create_secrets.ps1     # PowerShell-Skript zum Erstellen von Secrets (Beispiel)
└── README.md            # Diese Datei
```

## API-Endpunkte

- `GET /`: Hauptseite mit Upload-Formular und Buchliste
- `POST /upload`: Verarbeitet Buchupload mit Bildern
- `GET /books/<id>`: Ruft Details eines spezifischen Buchs ab
- `PUT /books/<id>`: Aktualisiert Buchdetails
- `POST /books/<id>/ebay`: Lädt Buch auf eBay hoch
- `POST /books/<id>/booklooker`: Lädt Buch auf Booklooker hoch
- `GET /books/<id>/booklooker/status`: Prüft den Upload-Status bei Booklooker

## Entwicklungshinweise

- Die Anwendung verwendet die Gemini API mit Google Search Grounding für präzise Bucherkennung und Preisrecherche
- Bilder werden im `static/uploads` Verzeichnis gespeichert
- Die eBay-Integration ist zunächst auf die Sandbox-Umgebung beschränkt
- Booklooker-Integration nutzt das TSV-Upload-Format für Massenupload von Büchern
- Die Synchronisation des Buchbestands erfolgt asynchron

## Sicherheitshinweise

- API-Schlüssel und sensible Daten werden über Umgebungsvariablen (lokal) oder Secret Manager (Cloud Run) verwaltet
- Uploads sind auf Bilddateien beschränkt
- Maximale Dateigröße: 16MB pro Bild
- Automatische Token-Erneuerung für Booklooker API

## Todo

- [ ] Verbesserte Fehlerbehandlung bei API-Ausfällen
- [ ] Implementierung von Unit-Tests
- [ ] Unterstützung für mehrere Bücher gleichzeitig
- [x] Integration mit weiteren Verkaufsplattformen (Booklooker)
- [ ] Automatische Synchronisation von Bestandsmengen
- [ ] Batch-Verarbeitung für Massenupload
- [ ] Erweiterte Statistiken und Reporting

## Lizenz

[MIT License](https://opensource.org/licenses/MIT)