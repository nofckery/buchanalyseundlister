import os
import json
import base64
import logging
import traceback
import requests
from datetime import datetime
from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError

class EbayAPI:
    def __init__(self):
        try:
            is_sandbox = os.getenv('EBAY_SANDBOX', 'True').lower() == 'true'
            domain = 'api.sandbox.ebay.com' if is_sandbox else 'api.ebay.com'
            
            # Basis-Konfiguration
            config = {
                'domain': domain,
                'appid': os.getenv('EBAY_APP_ID', '').strip('" '),
                'devid': os.getenv('EBAY_DEV_ID', '').strip('" '),
                'certid': os.getenv('EBAY_CERT_ID', '').strip('" '),
                'token': os.getenv('EBAY_TOKEN', '').strip('" '),
                'version': '1199',  # Aktuellste Trading API Version
                'siteid': '77',     # Deutschland (eBay.de)
                'warnings': True,
                'timeout': 20,
                'https': True,
                'debug': True
            }
            
            logging.debug("Initializing eBay API...")
            logging.debug(f"Domain: {domain}")
            logging.debug(f"APP_ID: {config['appid'][:8]}...")  # Erste 8 Zeichen für Sicherheit
            
            # API Initialisierung mit User Token
            self.api = Trading(
                domain=domain,
                config_file=None,
                appid=config['appid'],
                devid=config['devid'],
                certid=config['certid'],
                token=config['token'],
                version=config['version'],
                siteid=config['siteid']
            )
            logging.debug("eBay API initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize eBay API: {str(e)}")
            raise

    def find_best_category(self, category, description):
        """Findet die beste passende eBay-Kategorie basierend auf der Buchkategorie und Beschreibung"""
        try:
            # GetCategories API-Aufruf
            response = self.api.execute('GetCategories', {
                'DetailLevel': 'ReturnAll',
                'CategorySiteID': 77,  # Deutschland
                'LevelLimit': 4,       # Bis zu 4 Ebenen tief suchen
            })
            
            # Extrahiere alle Kategorien
            categories = response.dict().get('CategoryArray', {}).get('Category', [])
            
            # Keywords für die Suche
            keywords = ['antiquarisch', 'antik', 'gebraucht', 'historisch']
            if 'kinder' in description.lower():
                keywords.extend(['kinder', 'jugend'])
            if 'theater' in description.lower():
                keywords.extend(['theater', 'bühne'])
            
            # Finde beste Übereinstimmung
            best_match = None
            best_score = 0
            
            for cat in categories:
                score = 0
                cat_name = cat.get('CategoryName', '').lower()
                
                # Prüfe Keywords
                for keyword in keywords:
                    if keyword in cat_name:
                        score += 1
                
                # Prüfe ob es eine Leaf-Kategorie ist
                if cat.get('LeafCategory', 'false') == 'true':
                    score += 2
                
                if score > best_score:
                    best_score = score
                    best_match = cat.get('CategoryID')
            
            # Fallback-Kategorie für Bücher
            return best_match if best_match else '267'
            
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Kategorien: {str(e)}")
            return '267'  # Fallback zur Bücher-Kategorie

    def get_condition_id(self, condition):
        """Konvertiert unsere Zustandsbeschreibungen in eBay Condition IDs für antiquarische Bücher"""
        # Für antiquarische Bücher verwenden wir nur 7000 (Used)
        logging.debug(f"Verwende ConditionID 7000 (Used) für Zustand: {condition}")
        return 7000

    def get_payment_info(self):
        """Generiert die Zahlungsinformationen basierend auf dem Kontentyp"""
        # Für Managed Payment Accounts keine Zahlungsinformationen angeben
        return {
            'AutoPay': True
        }

    def get_sandbox_payment_info(self):
        """Liefert spezielle Zahlungsinformationen für die Sandbox"""
        if os.getenv('EBAY_SANDBOX', 'True').lower() == 'true':
            return {
                'IntegratedMerchantCreditCardEnabled': 'true',
                'PaymentMethod': 'CreditCard'
            }
        return {}

    def verify_credentials(self):
        """Überprüft, ob die API-Credentials gültig sind"""
        try:
            # Prüfe erforderliche Umgebungsvariablen
            required_env = ['EBAY_APP_ID', 'EBAY_CERT_ID', 'EBAY_DEV_ID', 'EBAY_TOKEN']
            missing_env = [env for env in required_env if not os.getenv(env)]
            if missing_env:
                return {
                    'success': False,
                    'error': 'Missing credentials',
                    'message': f'Fehlende eBay Credentials: {", ".join(missing_env)}'
                }
            
            # Nutze GetUser zur Validierung
            response = self.api.execute('GetUser')
            response_dict = response.dict()
            
            if not hasattr(response.reply, 'User'):
                return {
                    'success': False,
                    'error': 'Invalid response',
                    'message': 'Benutzerinformationen konnten nicht abgerufen werden'
                }
            
            return {
                'success': True,
                'message': f'Verbindung erfolgreich, Benutzer: {response.reply.User.UserID}',
                'details': response_dict
            }
            
        except ConnectionError as e:
            error_msg = str(e)
            logging.error(f"eBay API Connection Error: {error_msg}")
            if hasattr(e, 'response'):
                logging.error(f"Response: {e.response.dict() if hasattr(e.response, 'dict') else e.response}")
            return {
                'success': False,
                'error': error_msg,
                'message': 'Fehler bei der Verbindung zu eBay',
                'details': e.response.dict() if hasattr(e, 'response') and hasattr(e.response, 'dict') else None
            }
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Unexpected error during credential verification: {error_msg}")
            return {
                'success': False,
                'error': 'Unexpected error',
                'message': f'Unerwarteter Fehler bei der Validierung: {error_msg}'
            }

    def create_listing(self, book):
        """Erstellt ein eBay Listing für ein Buch"""
        try:
            logging.debug("Creating eBay listing for book: %s", book.title)
            
            # Kürze den Titel wenn nötig
            title = book.title[:80]
            
            # Erstelle detaillierte Beschreibung und ersetze Sonderzeichen
            description = f"""
{book.description.replace('&', '&amp;')}

Zustand: Antiquarisches Buch in gutem Zustand
Verlag: {book.publisher if hasattr(book, 'publisher') else 'J.F. Schreiber'}
Erscheinungsjahr: {book.publication_year if book.publication_year else 'Nicht angegeben'}

Bitte beachten Sie: Dies ist ein historisches Buch aus dem Verlag J.F. Schreiber.
""".replace('&', '&amp;')
            
            # Finde beste passende Kategorie
            category_id = self.find_best_category(book.category, book.description)
            
            # Standard Item-Spezifikationen für antiquarische Bücher
            item_specifics = [
                {'Name': 'Format', 'Value': 'Gebundene Ausgabe'},
                {'Name': 'Erscheinungsjahr', 'Value': str(book.publication_year) if book.publication_year else 'Nicht angegeben'},
                {'Name': 'Sprache', 'Value': 'Deutsch'},
                {'Name': 'Autor', 'Value': book.author},
                {'Name': 'Produktart', 'Value': 'Antiquarisches Buch'},
                {'Name': 'Verlag', 'Value': 'J.F. Schreiber'},
                {'Name': 'Original/Reproduktion', 'Value': 'Original'},
                {'Name': 'Genre', 'Value': 'Antiquarische Bücher'},
                {'Name': 'Besonderheiten', 'Value': 'Historische Ausgabe'},
                {'Name': 'Marke', 'Value': 'J.F. Schreiber'},
                {'Name': 'Herausgeber', 'Value': 'J.F. Schreiber'}
            ]
            
            # Basis Item-Daten
            item_data = {
                'Item': {
                    'Title': title,
                    'Description': description,
                    'PrimaryCategory': {'CategoryID': category_id},
                    'StartPrice': str(book.price),
                    'ConditionID': self.get_condition_id(book.condition),
                    'Country': 'DE',
                    'Currency': 'EUR',
                    'DispatchTimeMax': '3',
                    'ListingDuration': 'GTC',  # Good Till Cancelled
                    'ListingType': 'FixedPriceItem',
                    'Location': os.getenv('POSTAL_CODE', '10115'),
                    'PostalCode': os.getenv('POSTAL_CODE', '10115'),
                    'Quantity': '1',
                    'Site': 'Germany',
                    'AutoPay': True,
                    'ItemSpecifics': {
                        'NameValueList': item_specifics
                    },
                    'ShippingDetails': {
                        'ShippingType': 'Flat',
                        'ShippingServiceOptions': [{
                            'ShippingServicePriority': '1',
                            'ShippingService': 'DE_DHLPaket',
                            'ShippingServiceCost': '4.99',
                            'ShippingServiceAdditionalCost': '0.00'
                        }]
                    },
                    'ReturnPolicy': {
                        'ReturnsAcceptedOption': 'ReturnsAccepted',
                        'ReturnsWithinOption': 'Days_30',
                        'Description': 'Rückgabe innerhalb von 30 Tagen möglich. Das Buch muss im gleichen Zustand zurückgesendet werden.',
                        'ShippingCostPaidByOption': 'Buyer'
                    }
                }
            }
            
            # Füge Test-Bild für Sandbox hinzu
            if os.getenv('EBAY_SANDBOX', 'True').lower() == 'true':
                item_data['Item']['PictureDetails'] = {
                    'PictureURL': ['https://ir.ebaystatic.com/pictures/aw/pics/stockphoto/Stock_Photo_1.jpg']
                }
            
            # Validiere Request
            required_fields = {
                'Title': item_data['Item'].get('Title'),
                'StartPrice': item_data['Item'].get('StartPrice'),
                'ConditionID': item_data['Item'].get('ConditionID'),
                'CategoryID': item_data['Item'].get('PrimaryCategory', {}).get('CategoryID'),
                'Description': item_data['Item'].get('Description')
            }
            
            for field, value in required_fields.items():
                if not value:
                    error_msg = f"Fehlendes Pflichtfeld: {field}"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                logging.debug("%s: %s", field, value)
            
            # Füge Zahlungsinformationen hinzu
            item_data['Item'].update(self.get_payment_info())
            
            # Sende Request
            logging.debug("Sende eBay API Request...")
            response = self.api.execute('AddFixedPriceItem', item_data)
            response_dict = response.dict()
            
            # Validiere die Antwort
            if not hasattr(response.reply, 'ItemID'):
                error_msg = "Keine Item-ID in der API-Antwort"
                logging.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'details': response_dict
                }
            
            # Update Zahlungsinformationen für Sandbox
            item_data = self.update_sandbox_payment(item_data)

            # Prüfe auf Warnungen
            warnings = response_dict.get('Warnings', [])
            if warnings:
                logging.warning("eBay API Warnungen: %s", warnings)
            
            return {
                'success': True,
                'listing_id': response.reply.ItemID,
                'message': 'Artikel erfolgreich bei eBay eingestellt',
                'warnings': warnings if warnings else None,
                'details': response_dict
            }
            
        except ConnectionError as e:
            logging.error("eBay API Connection Error:")
            logging.error("Full Stack Trace: %s", traceback.format_exc())
            
            error_dict = {}
            if hasattr(e, 'response'):
                error_dict = e.response.dict() if hasattr(e.response, 'dict') else {}
                logging.error("Response Dict: %s", error_dict)
                
            # Extrahiere detaillierte API Fehler
            api_errors = error_dict.get('Errors', [])
            error_message = str(e)
            
            # Spezielle Fehlermeldung für Kreditkartenproblem
            if api_errors and isinstance(api_errors, dict) and api_errors.get('ErrorCode') == '10117':
                error_message = """
                Der eBay Sandbox-Account benötigt Kreditkarteninformationen.
                Bitte folgen Sie diesen Schritten:
                1. Melden Sie sich im eBay Seller Hub Sandbox an: https://signin.sandbox.ebay.de/ws/eBayISAPI.dll
                2. Gehen Sie zu den Kontoeinstellungen
                3. Hinterlegen Sie Kreditkarteninformationen für den Test-Account
                4. Versuchen Sie den Upload erneut
                """
            elif api_errors:
                if isinstance(api_errors, dict):
                    api_errors = [api_errors]
                error_message = (
                    api_errors[0].get('LongMessage') or
                    api_errors[0].get('ShortMessage') or
                    str(e)
                )
            
            return {
                'success': False,
                'error': str(e),
                'message': error_message,
                'details': error_dict
            }
            
        except Exception as e:
            logging.error("Unexpected error: %s", str(e))
            logging.error("Stack trace: %s", traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'message': 'Unerwarteter Fehler beim Erstellen des eBay Listings',
                'stack_trace': traceback.format_exc()
            }