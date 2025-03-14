import os
import re
import json
import traceback
import logging
from datetime import datetime
from flask import render_template, request, jsonify, current_app, url_for
from werkzeug.utils import secure_filename
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
            # Bilder validieren und speichern
            image_paths = []
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
                new_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                file.save(filepath)
                image_paths.append(filepath)
                app.logger.debug(f"Bild gespeichert: {filepath}")

            if not image_paths:
                return jsonify({'error': 'Keine gültigen Bilder hochgeladen. Bitte laden Sie mindestens ein Bild hoch.'}), 400

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
                image_urls=[
                    url_for('static', filename=f"uploads/{os.path.basename(path)}", _external=True)
                    for path in image_paths
                ],
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
                app.logger.debug(f"Starte Analyse von {len(image_paths)} Bildern")
                analysis_results = image_analyzer.analyze_book_images(book.id, image_paths)
                app.logger.debug(f"Bildanalyse abgeschlossen: {analysis_results}")
                
                # Aktualisiere den Bucheintrag mit den Analyseergebnissen
                metadata = analysis_results.get('metadata', {})
                book.title = metadata.get('deutscher_titel', metadata.get('title', 'Unbekannter Titel'))
                book.author = metadata.get('autor', metadata.get('author', 'Unbekannter Autor'))
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
                    book.dimensions = {
                        'length': dimensions['length'],
                        'width': dimensions['width'],
                        'height': dimensions['height']
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
                price_range = market_data.get('gebrauchtpreise', {})
                # Extrahiere Preise aus den Marktdaten
                if market_data and market_data.get('gebrauchtpreise'):
                    gebrauchtpreise = market_data['gebrauchtpreise']
                    recommended_str = market_data.get('empfohlener_verkaufspreis', '0-0 EUR')
                    min_str = gebrauchtpreise.get('zustand_akzeptabel', '0-0 EUR')
                    max_str = gebrauchtpreise.get('zustand_sehr_gut', '0-0 EUR')
                    
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
                        'market_data': {
                            'gebrauchtpreise': market_data['gebrauchtpreise'],
                            'sammlerwert': market_data.get('sammlerwert', 'nicht verfügbar'),
                            'marktverfügbarkeit': market_data.get('marktverfügbarkeit', 'unbekannt'),
                            'empfohlener_verkaufspreis': market_data.get('empfohlener_verkaufspreis', 'nicht verfügbar')
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
                db.session.commit()
                
                return jsonify({
                    'message': 'Buch erfolgreich analysiert und gespeichert',
                    'book': book.to_dict()
                }), 201
                
            except Exception as analysis_error:
                app.logger.error(f"Fehler bei der Analyse: {str(analysis_error)}")
                book.processing_status = 'ERROR'
                book.image_analysis_results = {'error': str(analysis_error)}
                db.session.commit()
                raise

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
                # Lösche die zugehörigen Bilder
                for image_url in book.image_urls:
                    image_path = os.path.join(
                        app.root_path,
                        'static',
                        'uploads',
                        os.path.basename(image_url)
                    )
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        app.logger.debug(f"Bild gelöscht: {image_path}")

                # Lösche den Datenbankeintrag
                db.session.delete(book)
                db.session.commit()
                app.logger.debug(f"Buch gelöscht: {book.title}")
                
                return jsonify({'message': 'Buch erfolgreich gelöscht'}), 200
            except Exception as e:
                app.logger.error(f"Fehler beim Löschen des Buchs: {str(e)}")
                db.session.rollback()
                return jsonify({'error': str(e)}), 500