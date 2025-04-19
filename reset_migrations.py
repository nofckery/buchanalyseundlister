from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Lösche die alembic_version Tabelle falls sie existiert
    try:
        with db.engine.connect() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
            conn.commit()
        print("alembic_version Tabelle wurde zurückgesetzt")
    except Exception as e:
        print(f"Fehler beim Zurücksetzen: {str(e)}")
    
    # Erstelle die Tabellen neu
    db.drop_all()
    db.create_all()
    print("Datenbank wurde neu initialisiert")