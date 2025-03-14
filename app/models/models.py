from app import db
from datetime import datetime
import decimal

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Grundlegende Buchinformationen
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    isbn = db.Column(db.String(13), nullable=True)
    
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

    def calculate_shipping_cost(self):
        """Berechnet den Versandpreis basierend auf Gewicht und Maßen"""
        try:
            # Standard-Versandpreis wenn keine Details vorhanden
            if not self.weight or not isinstance(self.weight, (int, float)) or self.weight <= 0:
                return decimal.Decimal('5.00')

            # Grundpreis
            base_price = decimal.Decimal('3.00')
            
            # Gewichtsaufschlag
            weight_cost = decimal.Decimal('0.00')
            if self.weight <= 500:  # bis 500g
                weight_cost = decimal.Decimal('2.00')
            elif self.weight <= 1000:  # bis 1kg
                weight_cost = decimal.Decimal('3.00')
            elif self.weight <= 2000:  # bis 2kg
                weight_cost = decimal.Decimal('4.50')
            else:  # über 2kg
                weight_cost = decimal.Decimal('7.00')
            
            # Größenaufschlag (basierend auf längstem Maß)
            size_cost = decimal.Decimal('0.00')
            if self.dimensions and isinstance(self.dimensions, dict):
                valid_dimensions = []
                for key in ['length', 'width', 'height']:
                    try:
                        value = self.dimensions.get(key)
                        if value is not None:
                            val = float(value)
                            if val > 0:
                                valid_dimensions.append(val)
                    except (ValueError, TypeError):
                        continue
                
                if valid_dimensions:
                    max_dimension = max(valid_dimensions)
                    if max_dimension > 50:  # über 50cm
                        size_cost = decimal.Decimal('3.00')
                    elif max_dimension > 30:  # über 30cm
                        size_cost = decimal.Decimal('1.50')
            
            # Gesamtkosten berechnen und runden
            total_cost = base_price + weight_cost + size_cost
            return total_cost.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
        
        except Exception as e:
            print(f"Fehler bei der Versandkostenberechnung: {str(e)}")
            return decimal.Decimal('5.00')  # Fallback auf Standard-Versandpreis

    def __repr__(self):
        return f'<Book {self.title} by {self.author}>'

    def to_dict(self):
        """Konvertiert das Buchobjekt in ein Dictionary für die API-Nutzung"""
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
            'shipping_cost': float(self.calculate_shipping_cost()),
            'total_price': float(self.price or 0) + float(self.calculate_shipping_cost()),
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
