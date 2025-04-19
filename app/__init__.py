import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pathlib import Path
from dotenv import load_dotenv

# Initialisiere Flask-Erweiterungen
db = SQLAlchemy()
migrate = Migrate()

def create_app(test_config=None):
    # Erstelle Flask-App
    app = Flask(__name__)
    
    # Unterscheide zwischen lokaler und Cloud-Umgebung
    is_cloud = bool(os.getenv('GOOGLE_CLOUD_PROJECT'))
    
    if is_cloud:
        # Cloud-Umgebung: Nutze Google Cloud Logging
        import google.cloud.logging
        client = google.cloud.logging.Client()
        client.setup_logging()
        
        # Lade Konfiguration aus Secret Manager
        from .config import init_app
        app = init_app(app)
    else:
        # Lokale Entwicklung: Lade .env
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if not os.path.exists(dotenv_path):
            raise FileNotFoundError(f"Die .env Datei wurde nicht gefunden in: {dotenv_path}")
        load_dotenv(dotenv_path, override=True)
        
        # Standard-Konfiguration für lokale Entwicklung
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 
            f'sqlite:///{os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "app.db")}')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', os.path.join('app', 'static', 'uploads'))
        app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))
        app.config['MAX_FILE_SIZE'] = int(os.environ.get('MAX_FILE_SIZE', 20 * 1024 * 1024))
        app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif']
    
    # Überprüfe ob wichtige Umgebungsvariablen gesetzt sind
    required_env_vars = ['GEMINI_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Fehlende Umgebungsvariablen: {', '.join(missing_vars)}")
    
    # Test-Konfiguration überschreiben falls vorhanden
    if test_config is not None:
        app.config.update(test_config)
    
    # Stelle sicher, dass notwendige Verzeichnisse existieren
    for directory in [
        # app.config['UPLOAD_FOLDER'], # Entfernt, da für GCS nicht benötigt
        os.path.join(app.root_path, 'cache', 'prices'),
        os.path.join(app.root_path, 'cache', 'metadata')
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
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
        routes.init_routes(app)
        
        # Füge 'float' zur Jinja2-Umgebung hinzu
        app.jinja_env.globals.update(float=float)
        
    return app