from app import db
from datetime import datetime
import decimal

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Grundlegende Buchinformationen
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(20), nullable=True) # Erhöht von 13 auf 20 Zeichen
    
    # Erweiterte Metadaten
    publisher = db.Column(db.String(255), nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    edition = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    genre = db.Column(db.String(100), nullable=True)
    page_count = db.Column(db.Integer, nullable=True)
    format = db.Column(db.String(50), nullable=True)  # Hardcover/Paperback
    dimensions = db.Column(db.JSON, nullable=True)  # Format: {"length": x, "width": y, "height": z}
    weight = db.Column(db.Float, nullable=True)  # Gewicht in Gramm
    condition = db.Column(db.String(50), nullable=False)
    
    # Preise und Kategorisierung
    price = db.Column(db.Numeric(10, 2), nullable=True, default=0.0)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Bildverarbeitung
    image_urls = db.Column(db.JSON, nullable=False, default=list)
    image_analysis_results = db.Column(db.JSON, nullable=True)
    processing_status = db.Column(db.String(50), nullable=True)
    last_analysis_date = db.Column(db.DateTime, nullable=True)
    
    # Analysedaten
    metadata_confidence = db.Column(db.JSON, nullable=True)
    price_analysis = db.Column(db.JSON, nullable=True)
    market_data = db.Column(db.JSON, nullable=True)
    validation_results = db.Column(db.JSON, nullable=True)
    shipping_options = db.Column(db.Text, nullable=False, default='{"method": "Flat Shipping", "cost": "EUR 5.00"}')
    return_policy = db.Column(db.Text, nullable=False, default='{"accepted": true, "days": 30}')
    summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    price_details = db.Column(db.JSON, nullable=True)
    
    # eBay spezifische Felder
    ebay_listing_id = db.Column(db.String(50), nullable=True)
    ebay_listing_status = db.Column(db.String(20), nullable=True)
    ebay_listing_url = db.Column(db.String(255), nullable=True)
    ebay_listing_error = db.Column(db.Text, nullable=True)
    ebay_last_sync = db.Column(db.DateTime, nullable=True)
    
    # Booklooker spezifische Felder
    booklooker_listing_id = db.Column(db.String(255), nullable=True)
    booklooker_status = db.Column(db.String(50), nullable=True)
    booklooker_last_sync = db.Column(db.DateTime, nullable=True)
    booklooker_listing_error = db.Column(db.Text, nullable=True)
    booklooker_upload_file = db.Column(db.String(255), nullable=True)
    booklooker_import_status = db.Column(db.String(50), nullable=True, default='PENDING')
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Versandpreise als Klassenvariablen
    DHL_PRICES = {
        'DE': {  # Deutschland
            'Büchersendung': {  # Maße max. 60×30×15cm
                500: decimal.Decimal('2.00'),   # bis 500g
                1000: decimal.Decimal('2.40'),  # bis 1000g
                2000: decimal.Decimal('3.20')   # bis 2000g
            },
            'Paket': {  # Maße max. 60×30×15cm
                2000: decimal.Decimal('5.49'),   # bis 2kg
                5000: decimal.Decimal('6.49'),   # bis 5kg
                10000: decimal.Decimal('8.49'),  # bis 10kg
                31500: decimal.Decimal('12.49')  # bis 31.5kg
            }
        },
        'EU': {  # Europaversand
            'Paket': {
                5000: decimal.Decimal('15.89'),   # bis 5kg
                10000: decimal.Decimal('19.89'),  # bis 10kg
                20000: decimal.Decimal('29.89')   # bis 20kg
            }
        },
        'INT': {  # Internationaler Versand
            'Paket': {
                5000: decimal.Decimal('29.99'),   # bis 5kg
                10000: decimal.Decimal('49.99'),  # bis 10kg
                20000: decimal.Decimal('89.99')   # bis 20kg
            }
        }
    }

    HERMES_PRICES = {
        'DE': {  # Deutschland
            'Paket': {
                2000: decimal.Decimal('4.50'),   # bis 2kg
                5000: decimal.Decimal('5.50'),   # bis 5kg
                10000: decimal.Decimal('7.50'),  # bis 10kg
                25000: decimal.Decimal('14.50')  # bis 25kg
            }
        },
        'EU': {  # Europaversand
            'Paket': {
                2000: decimal.Decimal('12.99'),   # bis 2kg
                5000: decimal.Decimal('14.99'),   # bis 5kg
                10000: decimal.Decimal('18.99'),  # bis 10kg
                20000: decimal.Decimal('24.99')   # bis 20kg
            }
        },
        'INT': {  # Internationaler Versand
            'Paket': {
                2000: decimal.Decimal('24.99'),   # bis 2kg
                5000: decimal.Decimal('34.99'),   # bis 5kg
                10000: decimal.Decimal('54.99'),  # bis 10kg
                20000: decimal.Decimal('94.99')   # bis 20kg
            }
        }
    }

    def _check_book_dimensions(self):
        """Prüft ob die Buchmaße für Büchersendung geeignet sind"""
        if not self.dimensions or not isinstance(self.dimensions, dict):
            return False

        max_dims = {
            'length': 60,
            'width': 30,
            'height': 15
        }

        for key, max_value in max_dims.items():
            try:
                value = float(self.dimensions.get(key, 0))
                if value > max_value:
                    return False
            except (ValueError, TypeError):
                return False

        return True

    def _get_weight_category(self, prices, weight_in_grams):
        """Ermittelt die passende Gewichtskategorie"""
        for weight_limit in sorted(prices.keys()):
            if weight_in_grams <= weight_limit:
                return weight_limit
        return max(prices.keys())

    def calculate_shipping_cost(self):
        """Berechnet den günstigsten Versandpreis für Deutschland"""
        try:
            options = self.calculate_shipping_costs()
            if 'error' in options:
                return options['fallback_price']
            
            # Sammle alle verfügbaren Preise für Deutschland
            de_prices = []
            
            # DHL Deutschland Optionen
            if 'DHL' in options and 'DE' in options['DHL']:
                de_prices.extend(options['DHL']['DE'].values())
            
            # Hermes Deutschland Optionen
            if 'Hermes' in options and 'DE' in options['Hermes']:
                de_prices.extend(options['Hermes']['DE'].values())
            
            # Günstigste Option zurückgeben oder Fallback
            return min(de_prices) if de_prices else decimal.Decimal('5.00')
            
        except Exception as e:
            print(f"Fehler bei der Versandkostenberechnung: {str(e)}")
            return decimal.Decimal('5.00')  # Fallback auf Standard-Versandpreis

    def calculate_shipping_costs(self):
        """Berechnet alle Versandoptionen mit Preisen"""
        try:
            if not self.weight or not isinstance(self.weight, (int, float)) or self.weight <= 0:
                return {
                    'error': 'Ungültiges Gewicht',
                    'fallback_price': decimal.Decimal('5.00')
                }

            weight = float(self.weight)
            shipping_options = {
                'DHL': {},
                'Hermes': {}
            }

            # DHL Optionen
            for region in ['DE', 'EU', 'INT']:
                shipping_options['DHL'][region] = {}
                
                # Für Deutschland prüfen ob Büchersendung möglich
                if region == 'DE' and weight <= 2000 and self._check_book_dimensions():
                    weight_cat = self._get_weight_category(self.DHL_PRICES['DE']['Büchersendung'], weight)
                    shipping_options['DHL'][region]['Büchersendung'] = self.DHL_PRICES['DE']['Büchersendung'][weight_cat]

                # Normale Paketpreise
                prices = self.DHL_PRICES[region]['Paket']
                weight_cat = self._get_weight_category(prices, weight)
                shipping_options['DHL'][region]['Paket'] = prices[weight_cat]

            # Hermes Optionen
            for region in ['DE', 'EU', 'INT']:
                shipping_options['Hermes'][region] = {}
                prices = self.HERMES_PRICES[region]['Paket']
                weight_cat = self._get_weight_category(prices, weight)
                shipping_options['Hermes'][region]['Paket'] = prices[weight_cat]

            return shipping_options

        except Exception as e:
            print(f"Fehler bei der Versandkostenberechnung: {str(e)}")
            return {
                'error': str(e),
                'fallback_price': decimal.Decimal('5.00')
            }

    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'

    def to_dict(self):
        """Konvertiert das Buchobjekt in ein Dictionary für die API-Nutzung"""
        # Berechne alle Versandoptionen
        shipping_costs = self.calculate_shipping_costs()
        cheapest_de = self.calculate_shipping_cost()

        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'publication_year': self.publication_year,
            'isbn': self.isbn,
            'publisher': self.publisher,
            'edition': self.edition,
            'format': self.format,
            'page_count': self.page_count,
            'dimensions': self.dimensions,
            'weight': self.weight,
            'language': self.language,
            'genre': self.genre,
            'condition': self.condition,
            'price': float(self.price) if self.price else None,
            'shipping': {
                'all_options': shipping_costs,  # Alle Versandoptionen mit Details
                'cheapest_de': float(cheapest_de),  # Günstigste Option für Deutschland
                'calculated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            },
            'total_price': float(self.price or 0) + float(cheapest_de),
            'description': self.description,
            'category': self.category,
            'image_urls': self.image_urls,
            'shipping_options': self.shipping_options,
            'return_policy': self.return_policy,
            'summary': self.summary,
            'status': self.status,
            'price_details': self.price_details,
            'image_analysis_results': self.image_analysis_results,
            'metadata_confidence': self.metadata_confidence,
            'price_analysis': self.price_analysis,
            'market_data': self.market_data,
            'ebay_listing_id': self.ebay_listing_id,
            'ebay_listing_status': self.ebay_listing_status,
            'ebay_listing_url': self.ebay_listing_url,
            'ebay_listing_error': self.ebay_listing_error,
            'ebay_last_sync': datetime.strftime(self.ebay_last_sync, '%Y-%m-%d %H:%M:%S') if self.ebay_last_sync else None,
            'booklooker_listing_id': self.booklooker_listing_id,
            'booklooker_status': self.booklooker_status,
            'booklooker_listing_error': self.booklooker_listing_error,
            'booklooker_last_sync': datetime.strftime(self.booklooker_last_sync, '%Y-%m-%d %H:%M:%S') if self.booklooker_last_sync else None,
            'created_at': datetime.strftime(self.created_at, '%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': datetime.strftime(self.updated_at, '%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }

    @staticmethod
    def from_dict(data):
        """Erstellt ein Buchobjekt aus einem Dictionary"""
        if 'created_at' in data:
            del data['created_at']
        if 'updated_at' in data:
            del data['updated_at']
        return Book(**data)
