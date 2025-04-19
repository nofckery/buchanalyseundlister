import logging
import os
from datetime import datetime
from ..booklooker_api import BooklookerAPI

class BooklookerController:
    def __init__(self):
        self.api = BooklookerAPI()
        
    def verify_connection(self):
        """Überprüft die Verbindung zu Booklooker"""
        return self.api.authenticate()
    
    def upload_book(self, book):
        """Lädt ein Buch auf Booklooker hoch"""
        logging.debug(f"Starte Upload für Buch: {book.title}")
        
        # Authentifizierung prüfen
        if not self.api.check_token():
            logging.error("Booklooker Authentifizierung fehlgeschlagen")
            return {
                'success': False,
                'message': 'Booklooker Authentifizierung fehlgeschlagen'
            }
        
        # Validiere Buchdaten (mit Preisvalidierung für Upload)
        is_valid, errors = self.api.validate_book_data(book, validate_price=True)
        if not is_valid:
            error_msg = ', '.join(errors)
            logging.error(f"Validierungsfehler: {error_msg}")
            return {
                'success': False,
                'message': f'Validierungsfehler: {error_msg}',
                'errors': errors
            }
        
        # Buch hochladen
        result = self.api.upload_book(book)
        
        if result['success']:
            logging.info(f"Buch wurde erfolgreich zu Booklooker hochgeladen")
            # Status aktualisieren
            book.booklooker_status = 'pending'
            book.booklooker_last_sync = datetime.utcnow()
        else:
            logging.error(f"Fehler beim Hochladen zu Booklooker: {result.get('message', '')}")
            book.booklooker_listing_error = result.get('message', 'Unbekannter Fehler')
            book.booklooker_status = 'error'
        
        return result
        
    def check_file_status(self, filename):
        """Überprüft den Status einer hochgeladenen Datei"""
        if not self.api.check_token():
            logging.error("Booklooker Authentifizierung fehlgeschlagen")
            return {
                'success': False,
                'message': 'Booklooker Authentifizierung fehlgeschlagen'
            }
            
        try:
            result = self.api.check_file_status(filename)
            if result['success']:
                logging.info(f"Status für {filename}: {result.get('file_status')}")
            else:
                logging.error(f"Fehler bei Statusabfrage: {result.get('message')}")
            return result
        except Exception as e:
            logging.error(f"Fehler bei Statusabfrage: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    