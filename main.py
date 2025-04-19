import os
from pathlib import Path
from app import create_app, db
from app.routes import init_routes

def setup_directories():
    """Erstellt alle benötigten Verzeichnisse"""
    base_dir = Path(__file__).parent
    
    dirs = [
        base_dir / 'instance',
        base_dir / 'app' / 'static' / 'uploads',
        base_dir / 'app' / 'cache' / 'prices',
        base_dir / 'app' / 'cache' / 'metadata'
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)

# Erstelle und konfiguriere App auf Modulebene für Gunicorn
setup_directories()
app = create_app()

# Initialisiere Datenbank wenn möglich
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    app.logger.error(f"Fehler bei der Datenbankinitialisierung: {e}")

def main():
    """Hauptfunktion zum Starten der Anwendung im Entwicklungsmodus"""
    # Starte Anwendung
    app.run(debug=True)

if __name__ == '__main__':
    main()