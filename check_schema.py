from app import create_app, db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    # Hole den Inspector
    inspector = inspect(db.engine)
    
    # Zeige alle Tabellen
    print("Vorhandene Tabellen:")
    for table_name in inspector.get_table_names():
        print(f"\nTabelle: {table_name}")
        print("Spalten:")
        for column in inspector.get_columns(table_name):
            print(f"  - {column['name']}: {column['type']}")