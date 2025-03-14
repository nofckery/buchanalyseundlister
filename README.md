# Buch Analyse & Lister

Eine Python-basierte Webanwendung zur Analyse und Listung von Büchern auf eBay und Booklooker mit Hilfe der Gemini API.

## Features

- Foto-Upload für Buchcover und -seiten
- Automatische Analyse von Büchern mittels Google Gemini API
- Automatische Preisrecherche auf eurobuch.de
- Integration mit eBay Sandbox API für Buchlistungen
- Integration mit Booklooker API für Buchlistungen
- PostgreSQL-Datenbankunterstützung
- Benutzerfreundliche Weboberfläche
- Synchronisation des Buchbestands mit mehreren Plattformen

## Voraussetzungen

- Python 3.8 oder höher
- PostgreSQL
- Google Gemini API-Schlüssel
- eBay Entwickler-Zugangsdaten (Sandbox)
- Booklooker API-Zugangsdaten

## Installation

1. Repository klonen:
```bash
git clone <repository-url>
cd buchanalyseundlister
```

2. Virtuelle Umgebung erstellen und aktivieren:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

4. Umgebungsvariablen konfigurieren:
```bash
# .env.example nach .env kopieren und anpassen
cp .env.example .env
```

5. Folgende Werte in der .env-Datei anpassen:
- `DATABASE_URL`: PostgreSQL-Verbindungs-URL
- `SECRET_KEY`: Zufälliger Sicherheitsschlüssel für Flask
- `GEMINI_API_KEY`: Google Gemini API-Schlüssel
- eBay API-Zugangsdaten (für Sandbox-Umgebung)
- `BOOKLOOKER_API_KEY`: Booklooker API-Schlüssel
- `BOOKLOOKER_USER_TOKEN`: Booklooker Benutzer-Token

6. PostgreSQL-Datenbank erstellen:
```bash
# PostgreSQL-Konsole öffnen
psql

# Datenbank erstellen
CREATE DATABASE buchdb;
```

7. Datenbank initialisieren und Anwendung starten:
```bash
python main.py
```

Die Anwendung ist nun unter `http://localhost:5000` erreichbar.

## Nutzung

1. **Buch hochladen**
   - Auf der Startseite den "Neues Buch hochladen" Bereich nutzen
   - Ein oder mehrere Fotos des Buches auswählen
   - "Analysieren & Hochladen" klicken

2. **Buchdaten bearbeiten**
   - In der Buchliste auf "Bearbeiten" klicken
   - Automatisch erkannte Daten überprüfen und anpassen
   - Versandoptionen und Rückgaberichtlinie festlegen
   - Änderungen speichern

3. **Auf Verkaufsplattformen hochladen**
   - Nach dem Bearbeiten und Speichern erscheint der "Auf eBay hochladen" Button
   - Optional "Auf Booklooker hochladen" wählen
   - Status der Listungen wird in der Übersicht angezeigt

## Projektstruktur

```
buchanalyseundlister/
├── app/
│   ├── __init__.py        # Flask-App-Initialisierung
│   ├── routes.py          # API-Routen und Hauptlogik
│   ├── apis/             # API-Integrationen
│   │   ├── ebay_api.py
│   │   └── booklooker_api.py
│   ├── models/           # Datenbankmodelle
│   │   └── models.py
│   ├── services/         # Geschäftslogik
│   │   ├── book/        # Buchbezogene Services
│   │   ├── image/       # Bildverarbeitungs-Services
│   │   ├── price/       # Preisanalyse-Services
│   │   └── cache/       # Caching-Services
│   ├── static/          # Statische Dateien
│   │   └── uploads/     # Hochgeladene Bilder
│   │       ├── raw/     # Original-Uploads
│   │       └── processed/ # Verarbeitete Bilder
│   ├── templates/       # HTML-Templates
│   │   ├── base.html
│   │   └── index.html
│   └── utils/           # Hilfsfunktionen
│       ├── cleanup_service.py
│       └── image/       # Bildverarbeitung-Utilities
├── migrations/          # Alembic Migrationsskripte
├── .env.example        # Beispiel-Umgebungsvariablen
├── main.py            # Anwendungs-Einstiegspunkt
├── requirements.txt   # Python-Abhängigkeiten
└── README.md         # Diese Datei
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
- Bilder werden im `static/uploads` Verzeichnis gespeichert, getrennt nach Original (`raw`) und verarbeitet (`processed`)
- Die eBay-Integration ist zunächst auf die Sandbox-Umgebung beschränkt
- Booklooker-Integration nutzt das TSV-Upload-Format für Massenupload von Büchern
- Die Synchronisation des Buchbestands erfolgt asynchron

## Sicherheitshinweise

- API-Schlüssel und sensible Daten werden über Umgebungsvariablen verwaltet
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