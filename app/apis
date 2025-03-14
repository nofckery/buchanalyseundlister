import os
import json
import logging
import requests
import tempfile
import traceback
import csv
import time
import re
from datetime import datetime
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """Decorator für Retry-Logik bei API-Aufrufen"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        sleep_time = delay * (attempt + 1)
                        logging.warning(f"Versuch {attempt + 1} fehlgeschlagen. Warte {sleep_time}s vor erneutem Versuch.")
                        time.sleep(sleep_time)
                    continue
            logging.error(f"Alle {max_retries} Versuche fehlgeschlagen.")
            raise last_exception
        return wrapper
    return decorator

class BooklookerAPI:
    def __init__(self):
        """Initialisiert die Booklooker API mit Zugangsdaten aus Umgebungsvariablen"""
        self.api_key = os.getenv('BOOKLOOKER_API_KEY', '').strip('" ')
        self.base_url = "https://api.booklooker.de/2.0"
        self.token = None
        self.session = requests.Session()
        
        if not self.api_key:
            logging.warning("Booklooker API-Key fehlt. Bitte setzen Sie BOOKLOOKER_API_KEY.")
            
    def validate_book_data(self, book, validate_price=True):
        """Validiert die Buchdaten vor dem Upload"""
        errors = []
        
        # Pflichtfelder prüfen
        required_fields = {
            'title': 'Titel',
            'condition': 'Zustand'
        }
        
        # Preis nur validieren wenn explizit angefordert
        if validate_price:
            required_fields['price'] = 'Preis'
        
        for field, name in required_fields.items():
            if not hasattr(book, field) or getattr(book, field) is None:
                errors.append(f"{name} fehlt")
            elif field == 'price' and validate_price and float(getattr(book, field)) <= 0:
                errors.append(f"{name} muss größer als 0 sein")
        
        # Zustand prüfen
        if hasattr(book, 'condition'):
            condition = getattr(book, 'condition')
            condition_map = {
                'New': 'Neu',
                'Like New': 'Wie neu',
                'Very Good': 'Sehr gut',
                'Good': 'Gut',
                'Acceptable': 'Akzeptabel'
            }
            # Übersetze englische in deutsche Zustände
            german_condition = condition_map.get(condition)
            if not german_condition:
                valid_conditions = ', '.join(condition_map.keys())
                errors.append(f"Ungültiger Zustand: {condition}. Erlaubt sind: {valid_conditions}")
        
        # Spartennummer prüfen (optional)
        if hasattr(book, 'sparte') and getattr(book, 'sparte'):
            sparte = str(getattr(book, 'sparte')).strip()
            if not self.validate_sparte(sparte):
                errors.append(f"Ungültige Spartennummer: {sparte}")
        
        if errors:
            return False, errors
        return True, []
    
    @retry_on_failure(max_retries=3, delay=1)
    def authenticate(self):
        """Authentifiziert mit dem API-Key und erhält ein Token"""
        if not self.api_key:
            logging.error("Booklooker API-Key fehlt. Authentifizierung nicht möglich.")
            return False
        
        try:
            logging.info(f"Starte Booklooker Authentifizierung")
            
            response = requests.post(f"{self.base_url}/authenticate", params={
                "apiKey": self.api_key
            })
            
            # Debug-Log für HTTP-Details
            logging.debug(f"Auth Response Status: {response.status_code}")
            logging.debug(f"Auth Response Headers: {response.headers}")
            
            response_text = response.text.strip()
            
            # Versuche als JSON zu parsen
            try:
                data = response.json()
                if data.get("status") == "OK" and "returnValue" in data:
                    self.token = data["returnValue"]
                    logging.info("Booklooker Authentifizierung erfolgreich")
                    return True
            except json.JSONDecodeError:
                # Wenn kein JSON, prüfe ob die Antwort direkt ein Token ist
                if response_text and len(response_text) == 32:  # Booklooker Tokens sind 32 Zeichen lang
                    self.token = response_text
                    logging.info("Booklooker Authentifizierung erfolgreich (Raw Token)")
                    return True
            
            logging.error(f"Unerwartetes Antwortformat: {response_text[:200]}")
            return False
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Verbindungsfehler bei der Authentifizierung: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Unerwarteter Fehler bei der Authentifizierung: {str(e)}")
            return False

    def check_token(self):
        """Prüft, ob ein gültiges Token vorhanden ist, andernfalls neu authentifizieren"""
        if self.token is None:
            return self.authenticate()
        return True

    def clean_description(self, text):
        """Bereinigt die Beschreibung für das Booklooker-Format"""
        # Entferne alle Markdown-Formatierungen
        text = re.sub(r'\*\*|\*', '', text)
        
        # Entferne eBay-spezifische Informationen
        text = re.sub(r'eBay-Kategorien:.*$', '', text, flags=re.DOTALL)
        
        # Ersetze Überschriften durch einfache Formate
        text = re.sub(r'Titel:', 'Titel:', text)
        text = re.sub(r'Autor:', '\nAutor:', text)
        text = re.sub(r'Verlagsjahr:', '\nJahr:', text)
        text = re.sub(r'Zustandsanalyse:', '\nZustand:', text)
        
        # Formatiere Zustandsbeschreibung
        text = re.sub(r'- ([^:\n]+):', '\n• \\1:', text)  # Aufzählungspunkte für Zustandsdetails
        text = re.sub(r'Zustandsbewertung:', '\nGesamtzustand:', text)
        
        # Entferne unnötige Metadaten
        text = re.sub(r'Zusätzliche Informationen:', '\nHinweis:', text)
        
        # Bereinige Whitespace und Anführungszeichen
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Entferne leere Zeilen
        text = '\n'.join(lines)
        
        # Behandle Anführungszeichen besonders
        text = text.replace('""', "'")  # Ersetze doppelte durch einfache
        text = text.replace(' "', ' ')  # Entferne führende
        text = text.replace('" ', ' ')  # Entferne nachfolgende
        text = re.sub(r'\s{2,}', ' ', text)  # Entferne mehrfache Leerzeichen
        
        # Stelle sicher, dass der Text mit einem Punkt endet
        text = text.rstrip()
        if not text.endswith('.'):
            text += '.'
        
        return text
        
    def create_booklooker_format(self, book):
        """Erstellt eine Textdatei im Booklooker-Format für ein einzelnes Buch"""
        tmp_dir = None
        file_path = None
        
        try:
            # Temporäres Verzeichnis erstellen
            tmp_dir = tempfile.mkdtemp()
            logging.debug(f"Temporäres Verzeichnis erstellt: {tmp_dir}")
            
            # Dateipfad generieren
            file_path = os.path.join(tmp_dir, f"book_{book.id}.txt")
            logging.debug(f"Temporärer Dateipfad: {file_path}")
            
            # Beschreibung bereinigen
            description = self.clean_description(
                book.description if hasattr(book, 'description') and book.description
                else "Gut erhaltenes Exemplar."
            )
            
            # Bereite die Buchdaten vor
            sparte = self.validate_sparte(getattr(book, 'sparte', ''))  # Validiere Spartennummer
            author = getattr(book, 'author', '') or ''
            author = str(author).strip()
            title = str(getattr(book, 'title', '')).strip()
            publisher = getattr(book, 'publisher', '') or ''
            publisher = str(publisher).strip()
            edition = getattr(book, 'edition', '') or ''
            edition = str(edition).strip()
            year = getattr(book, 'publication_year', '') or ''
            year = str(year).strip()
            location = getattr(book, 'publication_location', '') or ''
            location = str(location).strip()
            binding = getattr(book, 'binding', 'Gebundene Ausgabe') or 'Gebundene Ausgabe'
            binding = str(binding).strip()
            condition = self.map_condition(getattr(book, 'condition', 'Gut'))
            language = "de"
            isbn = getattr(book, 'isbn', '') or ''
            isbn = str(isbn).strip()
            pages = getattr(book, 'pages', '') or ''
            pages = str(pages).strip()
            format_info = getattr(book, 'format', '') or ''
            format_info = str(format_info).strip()
            order_nr = getattr(book, 'id', None)
            if order_nr is None:
                order_nr = f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            order_nr = str(order_nr).strip()
            weight = getattr(book, 'weight', '') or ''
            weight = str(weight).strip()
            price = f"{float(getattr(book, 'price', 0.0)):.2f}"

            # Datei schreiben
            with open(file_path, 'w', encoding='utf-8', newline='') as tmp_file:
                writer = csv.writer(tmp_file,
                                  delimiter='\t',
                                  quoting=csv.QUOTE_MINIMAL,
                                  quotechar='"')
                
                # Schreibe die Daten in der korrekten Booklooker-Reihenfolge
                writer.writerow([
                    sparte,            # Sparten-Nr.
                    author,            # Autor
                    title,             # Titel
                    publisher,         # Verlag
                    edition,           # Auflage
                    year,              # Jahr
                    location,          # Ort
                    binding,           # Einband
                    condition,         # Zustand (1-4)
                    description,       # Beschreibung
                    language,          # Sprache
                    isbn,              # ISBN
                    pages,             # Seiten
                    format_info,       # Format
                    order_nr,          # Bestell-Nr
                    weight,            # Gewicht in g
                    price,             # Ihr Preis in €
                    "",               # unbenutzt
                    "",               # unbenutzt
                    "",               # Cover-URL
                    "",               # Stichwort
                    "nein",           # unbegrenzte Stückzahl?
                    "nein",           # Neuware?
                    "nein",           # Erstausgabe?
                    "nein"            # Signiert?
                ])
                
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            
            # Überprüfe die erstellte Datei
            with open(file_path, 'r', encoding='utf-8') as test_file:
                content = test_file.read()
                logging.info(f"Erstellte Booklooker-Datei ({len(content)} Zeichen):")
                logging.info("=== Dateiinhalt Anfang ===")
                logging.info(content)
                logging.info("=== Dateiinhalt Ende ===")
                
            return file_path, tmp_dir
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen der Booklooker-Datei: {str(e)}")
            if tmp_dir and os.path.exists(tmp_dir):
                try:
                    if file_path and os.path.exists(file_path):
                        os.unlink(file_path)
                    os.rmdir(tmp_dir)
                except Exception as cleanup_error:
                    logging.error(f"Fehler beim Aufräumen: {str(cleanup_error)}")
            return None, None
    
    def validate_sparte(self, sparte):
        """Validiert eine Spartennummer für Bücher"""
        # Liste gültiger Sparten aus der Booklooker-Vorlage
        valid_sparten = {
            "2573", "886", "887", "881", "880", "1806", "2968", "2534", "873",
            "879", "878", "877", "884", "883", "693", "885", "882", "665",
            "666", "667", "960", "2648", "668", "798", "2008", "669", "670",
            "671", "672", "673", "674", "1211", "675", "874", "876", "875",
            "2561", "2597", "3031", "2932", "680"
            # Weitere Sparten können hier hinzugefügt werden
        }
        
        if not sparte:
            return ""  # Leere Sparte ist erlaubt
            
        sparte = str(sparte).strip()
        if sparte not in valid_sparten:
            logging.warning(f"Ungültige Spartennummer: {sparte}")
            return ""
            
        return sparte

    def map_condition(self, condition):
        """Konvertiert Zustandsbeschreibungen in Booklooker Zahlenwerte (1-4)"""
        # Erst englische in deutsche Zustände übersetzen
        condition_translation = {
            'New': 'Neu',
            'Like New': 'Wie neu',
            'Very Good': 'Sehr gut',
            'Good': 'Gut',
            'Acceptable': 'Akzeptabel'
        }
        # Deutsche Zustände in Booklooker Zahlenwerte konvertieren
        condition_values = {
            'Neu': '1',
            'Wie neu': '1',
            'Sehr gut': '2',
            'Gut': '3',
            'Akzeptabel': '4'
        }
        
        german_condition = condition_translation.get(condition, condition)
        return condition_values.get(german_condition, '3')  # Standardmäßig "3" (Gut)
    
    @retry_on_failure(max_retries=3, delay=1)
    def upload_book(self, book):
        """Lädt ein einzelnes Buch zu Booklooker hoch"""
        try:
            logging.info(f"Starte Upload für Buch: {book.title}")
            
            # Authentifizierung prüfen
            if not self.check_token():
                return {
                    'success': False,
                    'error': 'Authentication failed',
                    'message': 'Authentifizierung bei Booklooker fehlgeschlagen'
                }
            
            # Erstelle die Textdatei im Booklooker-Format
            file_path, tmp_dir = self.create_booklooker_format(book)
            if not file_path or not tmp_dir:
                return {
                    'success': False,
                    'error': 'File creation failed',
                    'message': 'Fehler beim Erstellen der Upload-Datei'
                }
            
            logging.debug(f"Datei erstellt und bereit zum Upload: {file_path}")
            
            try:
                # Prüfe Dateiinhalt vor dem Upload
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logging.info("=== Zu sendender Dateiinhalt ===")
                    logging.info(content)
                    logging.info("==============================")
                
                # Datei hochladen
                with open(file_path, 'rb') as file:
                    # API Parameter
                    params = {
                        "token": self.token,
                        "fileType": "article",
                        "dataType": 0,
                        "mediaType": 0,
                        "formatID": 1,
                        "encoding": "UTF-8"
                    }
                    
                    # Datei als Multipart-Form senden
                    files = {
                        'file': ('book.txt', file, 'text/plain; charset=utf-8')
                    }
                    
                    logging.debug(f"Sende Upload-Request mit Parametern: {params}")
                    
                    # Hier könnten wir optional auch multipart/form-data verwenden
                    # POST-Request senden
                    # Upload durchführen
                    logging.info("Sende Datei zu Booklooker...")
                    response = requests.post(
                        f"{self.base_url}/file_import",
                        params=params,
                        files=files
                    )
                    logging.info(f"Booklooker Response: Status={response.status_code}, Content={response.text[:200]}")
                    
                    # Upload erfolgreich
                    if response.status_code == 200 and ('OK' in response.text or 'success' in response.text.lower()):
                        logging.info("Upload erfolgreich, Datei wurde angenommen")
                        return {
                            'success': True,
                            'message': 'Buch erfolgreich zu Booklooker hochgeladen',
                            'file_status': 'FILE_RECEIVED',
                            'filename': 'book.txt'  # Speichere den Dateinamen für spätere Status-Abfragen
                        }
                    
                    # Verarbeite die Response
                    response_text = response.text.strip()
                    logging.debug(f"Upload Response: Status={response.status_code}, Content={response_text[:200]}")

                    try:
                        data = response.json()
                        if data.get("status") != "OK":
                            error = data.get('returnValue', 'Unbekannter Fehler')
                            return {
                                'success': False,
                                'error': error,
                                'message': f'Booklooker Fehler: {error}'
                            }
                    except json.JSONDecodeError:
                        if not ("OK" in response_text or "success" in response_text.lower()):
                            return {
                                'success': False,
                                'error': 'Invalid response',
                                'message': f'Unerwartete API-Antwort: {response_text[:200]}'
                            }
            finally:
                try:
                    # Aufräumen: Datei und Verzeichnis löschen
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logging.debug(f"Temporäre Datei gelöscht: {file_path}")
                    if os.path.exists(tmp_dir):
                        os.rmdir(tmp_dir)
                        logging.debug(f"Temporäres Verzeichnis gelöscht: {tmp_dir}")
                except Exception as cleanup_error:
                    logging.error(f"Fehler beim Aufräumen: {str(cleanup_error)}")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Verbindungsfehler beim Upload zu Booklooker: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'error': 'connection_error',
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Unerwarteter Fehler beim Upload: {str(e)}"
            logging.error(error_msg)
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return {
                'success': False,
                'error': 'unknown_error',
                'message': error_msg
            }
    
    @retry_on_failure(max_retries=3, delay=1)
    def check_file_status(self, filename):
        """Prüft den Status einer hochgeladenen Datei"""
        try:
            # Token prüfen
            if not self.check_token():
                return {
                    'success': False,
                    'error': 'Authentication failed',
                    'message': 'Authentifizierung bei Booklooker fehlgeschlagen'
                }
            
            # Status abfragen
            response = requests.get(
                f"{self.base_url}/file_status",
                params={
                    "token": self.token,
                    "filename": filename
                }
            )
            response.raise_for_status()
            
            data = response.json()
            if data["status"] != "OK":
                return {
                    'success': False,
                    'error': data['returnValue'],
                    'message': f"Booklooker Fehler: {data['returnValue']}"
                }
            
            return {
                'success': True,
                'file_status': data['returnValue'],
                'message': f"Dateistatus: {data['returnValue']}"
            }
            
        except Exception as e:
            logging.error(f"Fehler beim Prüfen des Dateistatus: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Fehler beim Prüfen des Dateistatus'
            }
            
    def get_status_message(self, status):
        """Gibt eine benutzerfreundliche Statusmeldung zurück"""
        status_map = {
            'FILE_RECEIVED': 'Datei empfangen',
            'QUEUED': 'In Warteschlange',
            'PROCESSING': 'Wird verarbeitet',
            'VALIDATING': 'Validiere Daten',
            'VALIDATED': 'Daten validiert',
            'IMPORTING': 'Importiere Daten',
            'IMPORTED': 'Import erfolgreich',
            'REJECTED': 'Import abgelehnt',
            'ERROR': 'Fehler beim Import',
            'UNKNOWN': 'Status unbekannt'
        }
        return status_map.get(status, status)