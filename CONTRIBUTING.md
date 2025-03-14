# Beitragen zum Projekt

Vielen Dank für Ihr Interesse, zum Buch Analyse & Lister Projekt beizutragen! 

## Entwicklungsumgebung einrichten

1. Repository klonen:
```bash
git clone https://github.com/nofckery/buchanalyseundlister.git
cd buchanalyseundlister
```

2. Virtuelle Umgebung erstellen und aktivieren:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

4. Umgebungsvariablen konfigurieren:
```bash
cp .env.example .env
# Passen Sie die Werte in .env an
```

## Pull Requests

1. Fork das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committen Sie Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Pushen Sie den Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

## Commit-Konventionen

- Verwenden Sie aussagekräftige Commit-Messages
- Beginnen Sie die Commit-Message mit einem der folgenden Tags:
  - `feat:` - Neue Features
  - `fix:` - Fehlerbehebungen
  - `docs:` - Dokumentationsänderungen
  - `style:` - Formatierung, fehlende Semikolons, etc.
  - `refactor:` - Code-Refactoring
  - `test:` - Tests hinzufügen/aktualisieren
  - `chore:` - Wartungsarbeiten

## Code-Style

- Befolgen Sie PEP 8
- Verwenden Sie aussagekräftige Variablen- und Funktionsnamen
- Kommentieren Sie komplexe Logik
- Schreiben Sie Docstrings für Funktionen und Klassen

## Tests

- Schreiben Sie Tests für neue Funktionalitäten
- Stellen Sie sicher, dass alle Tests bestehen
- Führen Sie Tests aus mit:
```bash
python -m pytest
```

## Probleme melden

- Nutzen Sie die Issue-Templates für Bug Reports und Feature Requests
- Seien Sie so detailliert wie möglich
- Fügen Sie Reproduktionsschritte hinzu
- Screenshots sind hilfreich

## Review-Prozess

1. Mindestens ein Code-Review ist erforderlich
2. Alle Tests müssen bestehen
3. Code muss den Style-Guidelines entsprechen
4. Dokumentation muss aktuell sein

## Lizenz

Mit Ihrem Beitrag stimmen Sie zu, dass Ihr Code unter der MIT-Lizenz veröffentlicht wird.

## Fragen?

Bei Fragen öffnen Sie bitte ein Issue mit dem Label "question".