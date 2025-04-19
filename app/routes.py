import os
import re
import json
import traceback
import logging
from datetime import datetime
from flask import render_template, request, jsonify, current_app, url_for
from werkzeug.utils import secure_filename
from google.cloud import storage  # GCS Import hinzugefügt
from . import db
from .models import Book
from .controllers.booklooker_controller import BooklookerController
from .controllers.image_analysis_controller import ImageAnalysisController
from .controllers.price_analysis_controller import PriceAnalysisController

def init_routes(app):
    def allowed_file(filename):
        """Überprüft, ob die Dateiendung erlaubt ist und die Dateigröße im Limit liegt"""
        if '.' not in filename:
            return False
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in app.config['UPLOAD_EXTENSIONS']:
            return False
        
        return True
        
    def validate_file_size(file):
        """Überprüft, ob die Dateigröße im erlaubten Bereich liegt"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        return size <= app.config['MAX_FILE_SIZE']

    @app.route('/')
    def index():
        """Hauptseite mit Upload-Formular und Buchliste"""
        books = Book.query.order_by(Book.created_at.desc()).all()
        return render_template('index.html', books=books)

    @app.route('/upload', methods=['POST'])
    async def upload_book():
        """Verarbeitet den Buchupload mit Bildern und führt Analyse durch"""
        if 'images' not in request.files:
            return jsonify({'error': 'Keine Bilder hochgeladen'}), 400
        
        files = request.files.getlist('images')
        if not files or not files[0].filename:
            return jsonify({'error': 'Keine Bilder ausgewählt'}), 400

        try:
            # Bilder validieren und in GCS hochladen
            image_urls = [] # Liste für GCS URLs
            gcs_client = storage.Client()
            bucket_name = current_app.config.get('GCS_BUCKET_NAME')
            if not bucket_name:
                 app.logger.error("GCS_BUCKET_NAME ist nicht konfiguriert!")
                 return jsonify({'error': 'Serverkonfigurationsfehler: GCS Bucket nicht definiert.'}), 500
            bucket = gcs_client.bucket(bucket_name)

            for file in files:
                if not file or not file.filename:
                    continue

                if not allowed_file(file.filename):
                    return jsonify({'error': f'Ungültiges Dateiformat: {file.filename}. Erlaubte Formate: {", ".join(app.config["UPLOAD_EXTENSIONS"])}'}), 400

                if not validate_file_size(file):
                    max_size_mb = app.config['MAX_FILE_SIZE'] / (1024 * 1024)
                    return jsonify({'error': f'Datei zu groß: {file.filename}. Maximale Größe: {max_size_mb:.1f}MB'}), 400

                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # Eindeutigen Blob-Namen erstellen (z.B. im Ordner 'uploads/')
                blob_name = f"uploads/{timestamp}_{filename}"
                blob = bucket.blob(blob_name)

                try:
                    # Dateiinhalt direkt in GCS hochladen
                    blob.upload_from_file(file, content_type=file.content_type)
                    # Öffentliche URL generieren (Bucket muss öffentlich lesbar sein oder signierte URLs verwenden)
                    public_url = blob.public_url
                    image_urls.append(public_url)
                    app.logger.debug(f"Bild hochgeladen nach GCS: {public_url}")
                except Exception as gcs_error:
                    app.logger.error(f"Fehler beim GCS Upload für {filename}: {gcs_error}")
                    return jsonify({'error': f'Fehler beim Speichern von {filename}.'}), 500

            if not image_urls:
                return jsonify({'error': 'Keine gültigen Bilder hochgeladen oder gespeichert. Bitte laden Sie mindestens ein Bild hoch.'}), 400

            # Hole das Gewicht aus dem Formular
            weight = request.form.get('weight')
            if not weight or not weight.isdigit() or int(weight) <= 0:
                return jsonify({'error': 'Bitte geben Sie ein gültiges Gewicht in Gramm ein'}), 400

            # Erstelle temporären Bucheintrag für die Analyse
            book = Book(
                title='Wird analysiert...',
                author='Wird analysiert...',
                condition='Good',
                price=0.0,
                description='Wird analysiert...',
                category='Books',
                weight=float(weight),  # Speichere das Gewicht
                image_urls=image_urls, # Verwende die GCS URLs direkt
                processing_status='PROCESSING'
            )
            db.session.add(book)
            db.session.commit()
            
            try:
                # Debug: API-Key ausgeben
                api_key = os.getenv('GEMINI_API_KEY')
                app.logger.debug(f"GEMINI_API_KEY: {api_key}")
                
                # Initialisiere Controller
                image_analyzer = ImageAnalysisController(api_key)
                price_analyzer = PriceAnalysisController()
                
                # Führe Bildanalyse durch
                app.logger.debug(f"Starte Analyse von {len(image_urls)} Bildern")
                analysis_results = image_analyzer.analyze_book_images(book.id, image_urls)
                app.logger.debug(f"Bildanalyse abgeschlossen: {analysis_results}")
                
                # Aktualisiere den Bucheintrag mit den Analyseergebnissen
                metadata = analysis_results.get('metadata', {})
                # Sichere Titel-Extraktion mit Fallback
                book.title = metadata.get('deutscher_titel') or metadata.get('title') or metadata.get('originaltitel') or 'Unbekannter Titel'
                # Sichere Autor-Extraktion mit Fallback
                book.author = metadata.get('autor') or metadata.get('author') or metadata.get('verfasser') or 'Unbekannter Autor'
                book.publication_year = metadata.get('erscheinungsjahr')
                book.publisher = metadata.get('verlag')
                book.isbn = metadata.get('isbn', metadata.get('isbn_ean'))
                book.edition = metadata.get('auflage', metadata.get('auflage_edition'))
                book.language = metadata.get('sprache', 'de')
                book.page_count = metadata.get('seitenanzahl')
                book.format = metadata.get('format')
                
                # Extrahiere die Maße aus der Bildanalyse
                physical_properties = analysis_results.get('physical_properties', {})
                dimensions = physical_properties.get('dimensions', {})
                if dimensions and all(key in dimensions for key in ['length', 'width', 'height']):
                    # Weise das Dictionary direkt zu, SQLAlchemy sollte den Typ handhaben
                    # Stelle sicher, dass die Werte Floats sind, bevor sie dem Dictionary zugewiesen werden
                    book.dimensions = {
                        'length': float(dimensions.get('length', 0.0)),
                        'width': float(dimensions.get('width', 0.0)),
                        'height': float(dimensions.get('height', 0.0))
                    }
                else:
                    book.dimensions = None
                
                book.genre = metadata.get('genre', metadata.get('genre_kategorie', 'Books'))
                
                # Zustand aus der Condition-Analyse
                condition_analysis = analysis_results.get('condition_analysis', {})
                zustand = condition_analysis.get('zustand_einschätzung', '').lower()
                
                # Standardisiere den Zustand
                if 'neu' in zustand:
                    book.condition = 'New'
                elif 'sehr gut' in zustand:
                    book.condition = 'Very Good'
                elif 'gut' in zustand:
                    book.condition = 'Good'
                elif 'akzeptabel' in zustand:
                    book.condition = 'Fair'
                else:
                    book.condition = 'Good'  # Standardwert
                
                book.description = '\n'.join(filter(None, [
                    condition_analysis.get('beschreibung', ''),
                    condition_analysis.get('maengel_besonderheiten', '')
                ]))
                
                # Zusatzinformationen
                additional_info = analysis_results.get('additional_info', {})
                book.summary = additional_info.get('inhaltszusammenfassung', '')
                book.category = 'Books'  # Standard-Kategorie

                # Speichere die vollständigen Analyseergebnisse
                book.image_analysis_results = analysis_results
                book.metadata_confidence = analysis_results.get('confidence_scores', {})
                
                # Verarbeite die Marktdaten
                market_data = analysis_results.get('market_data', {})
                # Korrigiere die Extraktion basierend auf der Prompt-Struktur
                preisanalyse = market_data.get('preisanalyse', {})
                zustands_preise = preisanalyse.get('zustandsbasierte_preise', {})
                empfehlung = preisanalyse.get('empfehlung', {})
                verkaufspreis_empfehlung = empfehlung.get('verkaufspreis', {})

                # Extrahiere Preise aus der korrekten Struktur
                if zustands_preise and verkaufspreis_empfehlung:
                    # Empfohlener Preis (optimal)
                    recommended_str = verkaufspreis_empfehlung.get('optimal', '0-0 EUR')
                    # Minimalpreis (aus Zustand "akzeptabel")
                    min_str = zustands_preise.get('akzeptabel', {}).get('preis', '0-0 EUR')
                    # Maximalpreis (aus Zustand "sehr_gut" oder "neuwertig")
                    max_str = zustands_preise.get('sehr_gut', {}).get('preis') or zustands_preise.get('neuwertig', {}).get('preis', '0-0 EUR')
                    
                    def extract_price_range(price_str):
                        if not price_str:
                            return 0.0, 0.0
                        # Extrahiere nur die Zahlen
                        numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', price_str)]
                        if len(numbers) >= 2:
                            return numbers[0], numbers[1]
                        return numbers[0], numbers[0] if numbers else (0.0, 0.0)
                    
                    rec_min, rec_max = extract_price_range(recommended_str)
                    min_price, _ = extract_price_range(min_str)
                    _, max_price = extract_price_range(max_str)
                    
                    recommended_price = (rec_min + rec_max) / 2

                    price_results = {
                        'value_estimation': {
                            'price_range': {
                                'recommended': recommended_price,
                                'min': min_price,
                                'max': max_price
                            },
                            'confidence_score': market_data.get('confidence_score', 0.8)
                        },
                        # Speichere die relevanten Teile der Analyse
                        'market_data': {
                            'zustandsbasierte_preise': zustands_preise,
                            'empfehlung': empfehlung,
                            # Füge weitere relevante Marktdaten hinzu, falls vorhanden
                            'vergleichsangebote': market_data.get('vergleichsangebote', {}),
                            'marktanalyse': market_data.get('marktanalyse', {})
                        }
                    }
                else:
                    # Fallback wenn keine Marktdaten verfügbar sind
                    price_results = {
                        'value_estimation': {
                            'price_range': {
                                'recommended': 0.0,
                                'min': 0.0,
                                'max': 0.0
                            },
                            'confidence_score': 0.0
                        },
                        'market_data': {}
                    }

                book.price_analysis = price_results
                book.price = price_results['value_estimation']['price_range']['recommended']
                book.price_details = {
                    'range': price_results['value_estimation']['price_range'],
                    'confidence': price_results['value_estimation']['confidence_score'],
                    'market_data': market_data,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                book.processing_status = 'COMPLETED'
                # Zusätzliches Logging vor dem Commit
                app.logger.info(f"COMMITTING results for book ID {book.id}. Title: {book.title}, ISBN: {book.isbn}, Price: {book.price}")
                app.logger.debug(f"Full analysis data being committed for book ID {book.id}: {analysis_results}")
                db.session.commit()
                # Logging AFTER commit to verify
                committed_book = Book.query.get(book.id)
                if committed_book and committed_book.processing_status == 'COMPLETED':
                     app.logger.info(f"Successfully committed and verified book ID {book.id}. Status: {committed_book.processing_status}")
                     app.logger.debug(f"Verified dimensions in DB for book ID {book.id}: {committed_book.dimensions}")
                else:
                     app.logger.error(f"Commit for book ID {book.id} seemed to succeed, but verification failed! Status: {committed_book.processing_status if committed_book else 'Not Found'}")
                
                return jsonify({
                    'message': 'Buch erfolgreich analysiert und gespeichert',
                    'book': book.to_dict()
                }), 201
                
            except Exception as analysis_error:
                # Logge den Fehler detailliert
                tb_str = traceback.format_exc()
                app.logger.error(f"Fehler bei der Analyse für Buch ID {book.id}: {str(analysis_error)}\nTraceback:\n{tb_str}")
                
                # Setze Status auf ERROR, aber löse keinen Worker-Crash aus
                book.processing_status = 'ERROR'
                # Speichere nur die Fehlermeldung, nicht den ganzen Traceback in der DB (optional)
                book.image_analysis_results = {'error': f"Analyse fehlgeschlagen: {str(analysis_error)}"}
                db.session.commit()
                
                # Gib eine Fehlermeldung an den Client zurück
                return jsonify({
                    'error': f'Fehler während der Bildanalyse: {str(analysis_error)}',
                    'book_id': book.id, # Gib die ID zurück, damit der Client den Status verfolgen kann
                    'status': 'ERROR'
                }), 500 # Interner Serverfehler

        except Exception as e:
            app.logger.error(f"Fehler beim Upload: {str(e)}")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/books/<int:book_id>/upload-to-booklooker', methods=['POST'])
    @app.route('/books/<int:book_id>/booklooker-status', methods=['GET'])
    def booklooker_operations(book_id):
        """Verwaltet Booklooker-Operationen (Upload und Status-Abfrage)"""
        book = Book.query.get_or_404(book_id)
        booklooker = BooklookerController()

        if request.method == 'GET':
            # Status abfragen
            if not book.booklooker_status or book.booklooker_status == 'error':
                return jsonify({
                    'success': False,
                    'message': 'Kein aktiver Upload vorhanden'
                }), 400

            try:
                result = booklooker.check_file_status(book.booklooker_upload_file)
                if result['success']:
                    status = result.get('file_status', 'UNKNOWN')
                    status_message = booklooker.api.get_status_message(status)
                    return jsonify({
                        'success': True,
                        'status': status,
                        'message': status_message
                    })
                else:
                    return jsonify(result), 400
            except Exception as e:
                app.logger.error(f"Fehler bei Status-Abfrage: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': str(e)
                }), 500

        # POST Methode (Upload)
        """Lädt ein Buch zu Booklooker hoch"""
        book = Book.query.get_or_404(book_id)
        booklooker = BooklookerController()
        
        # Validiere nur beim Upload
        if not book.price or float(book.price) <= 0:
            return jsonify({
                'success': False,
                'message': 'Bitte setzen Sie einen gültigen Preis für das Buch (größer als 0)'
            }), 400
            
        try:
            # Upload durchführen
            result = booklooker.upload_book(book)
            
            if result['success']:
                book.booklooker_upload_file = result.get('filename')
                book.booklooker_status = 'pending'
                book.booklooker_last_sync = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Buch erfolgreich zu Booklooker hochgeladen',
                    'filename': result.get('filename')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', 'Unbekannter Fehler beim Upload')
                }), 400
                
        except Exception as e:
            app.logger.error(f"Fehler beim Booklooker Upload: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @app.route('/books/<int:book_id>', methods=['GET', 'PUT', 'DELETE'])
    def manage_book(book_id):
        """Verwaltet einzelne Bucheinträge"""
        book = Book.query.get_or_404(book_id)
        
        if request.method == 'GET':
            return jsonify(book.to_dict())
        
        if request.method == 'PUT':
            data = request.get_json()
            for key, value in data.items():
                if hasattr(book, key) and key not in ['created_at', 'updated_at']:
                    setattr(book, key, value)
            
            book.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify(book.to_dict())

        if request.method == 'DELETE':
            try:
                # Lösche die zugehörigen Bilder aus GCS
                gcs_client = storage.Client()
                bucket_name = current_app.config.get('GCS_BUCKET_NAME')
                if bucket_name:
                    bucket = gcs_client.bucket(bucket_name)
                    for image_url in book.image_urls:
                        try:
                            # Extrahiere den Blob-Namen aus der URL
                            # Annahme: URL ist https://storage.googleapis.com/BUCKET_NAME/BLOB_NAME
                            if image_url.startswith(f"https://storage.googleapis.com/{bucket_name}/"):
                                blob_name = image_url.split(f"https://storage.googleapis.com/{bucket_name}/", 1)[1]
                                blob = bucket.blob(blob_name)
                                if blob.exists():
                                    blob.delete()
                                    app.logger.debug(f"Bild aus GCS gelöscht: {blob_name}")
                                else:
                                     app.logger.warning(f"Bild nicht in GCS gefunden zum Löschen: {blob_name}")
                            else:
                                app.logger.warning(f"Konnte Blob-Namen nicht aus URL extrahieren: {image_url}")
                        except Exception as gcs_del_error:
                            app.logger.error(f"Fehler beim Löschen von Bild aus GCS ({image_url}): {gcs_del_error}")
                else:
                    app.logger.error("GCS_BUCKET_NAME nicht konfiguriert, Bilder können nicht gelöscht werden.")

                # Lösche den Datenbankeintrag
                db.session.delete(book)
                db.session.commit()
                app.logger.debug(f"Buch gelöscht: {book.title}")
                
                return jsonify({'message': 'Buch erfolgreich gelöscht'}), 200
            except Exception as e:
                app.logger.error(f"Fehler beim Löschen des Buchs: {str(e)}")
                db.session.rollback()
                return jsonify({'error': str(e)}), 500

    @app.route('/books/<int:book_id>/status', methods=['GET'])
    def get_book_status(book_id):
        """Gibt den Verarbeitungsstatus eines Buches zurück."""
        book = Book.query.get(book_id)
        if not book:
            return jsonify({'error': 'Buch nicht gefunden'}), 404
        
        return jsonify({
            'book_id': book.id,
            'status': book.processing_status or 'UNKNOWN' # Fallback, falls Status null ist
        })