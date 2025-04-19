import os
import shutil
from app import create_app

def reset_all():
    # Lösche die Datenbank
    if os.path.exists('instance/database.db'):
        os.remove('instance/database.db')
        print("Datenbank gelöscht")
    
    # Lösche das migrations Verzeichnis
    if os.path.exists('migrations'):
        shutil.rmtree('migrations')
        print("Migrations Verzeichnis gelöscht")

if __name__ == '__main__':
    reset_all()
    app = create_app()
    print("Setup abgeschlossen")