import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pathlib import Path
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if not os.path.exists(dotenv_path):
    raise FileNotFoundError(f"Die .env Datei wurde nicht gefunden in: {dotenv_path}")

load_dotenv(dotenv_path, override=True)

# Überprüfe ob wichtige Umgebungsvariablen gesetzt sind
required_env_vars = ['GEMINI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Fehlende Umgebungsvariablen: {', '.join(missing_vars)}")

# Initialisiere Flask-Erweiterungen
db = SQLAlchemy()
migrate = Migrate()

def create_app(test_config=None):
    # Erstelle Flask-App
    app = Flask(__name__)
    
    # Standard-Konfiguration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    
    # Stelle sicher, dass das instance-Verzeichnis existiert
    instance_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
    Path(instance_path).mkdir(parents=True, exist_ok=True)
    
    # Setze den absoluten Pfad für die Datenbank
    db_path = os.path.join(instance_path, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max für Mehrfach-Uploads
    app.config['MAX_FILE_SIZE'] = 20 * 1024 * 1024  # 20MB pro Datei
    app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif']
    
    # Test-Konfiguration überschreiben falls vorhanden
    if test_config is not None:
        app.config.update(test_config)
    
    # Stelle sicher, dass das Upload-Verzeichnis existiert
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    # Initialisiere Datenbank
    db.init_app(app)
    migrate.init_app(app, db)
    
    with app.app_context():
        # Importiere Modelle vor der Datenbankerstellung
        from . import models
        
        # Erstelle alle Datenbank-Tabellen
        db.create_all()
        
        # Importiere und registriere Routen
        from . import routes
        routes.init_routes(app)  # Hier registrieren wir die Routen
        
        # Erstelle Cache-Verzeichnisse
        cache_path = os.path.join(app.root_path, 'cache')
        Path(os.path.join(cache_path, 'prices')).mkdir(parents=True, exist_ok=True)
        Path(os.path.join(cache_path, 'metadata')).mkdir(parents=True, exist_ok=True)
    
    return app