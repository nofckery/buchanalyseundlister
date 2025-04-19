import os
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Versuche die Datenbank zu löschen
    if os.path.exists('instance/database.db'):
        os.remove('instance/database.db')
        print("Alte Datenbank gelöscht")
    
    # Stelle sicher, dass das instance Verzeichnis existiert
    os.makedirs('instance', exist_ok=True)
    
    # Erstelle die Datenbank neu
    db.create_all()
    print("Neue Datenbank erstellt")