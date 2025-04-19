from datetime import datetime
from typing import Dict, Any, Optional
import logging
from decimal import Decimal
import statistics

class PriceAnalysisController:
    def __init__(self):
        """
        Initialisiert den Price Analysis Controller.
        """
        self.condition_factors = {
            'New': 1.0,
            'Like New': 0.9,
            'Very Good': 0.8,
            'Good': 0.7,
            'Fair': 0.6,
            'Poor': 0.4
        }

    async def analyze_book_price(self, book_id: int) -> Dict[str, Any]:
        """
        Führt eine detaillierte Preisanalyse für ein Buch durch.
        """
        from app.models import Book
        
        book = Book.query.get(book_id)
        if not book:
            raise ValueError(f"Buch mit ID {book_id} nicht gefunden")

        try:
            # Sammle Marktdaten
            market_data = await self._collect_market_data(book)
            
            # Analysiere historische Daten
            try:
                historical_data = {
                    'price_trends': {},
                    'seasonal_patterns': {},
                    'long_term_trend': {}
                }
            except Exception as e:
                logging.error(f"Fehler bei der historischen Analyse: {str(e)}")
                historical_data = {}
            
            # Bewerte den Zustand
            condition_impact = self._analyze_condition_impact(book.condition)
            
            # Analysiere die Seltenheit
            rarity_analysis = self._analyze_rarity(book, market_data)
            
            # Regionale Preisanalyse
            regional_analysis = self._analyze_regional_prices(market_data)
            
            # Berechne den Schätzwert
            value_estimation = self._estimate_value(
                book,
                market_data,
                condition_impact,
                rarity_analysis
            )

            analysis_results = {
                'market_prices': market_data,
                'historical_data': historical_data,
                'condition_impact': condition_impact,
                'rarity_analysis': rarity_analysis,
                'regional_analysis': regional_analysis,
                'value_estimation': value_estimation,
                'collector_indicators': self._get_collector_indicators(book),
                'timestamp': datetime.utcnow().isoformat()
            }

            # Aktualisiere das Buch mit den Analyseergebnissen
            book.price_analysis = analysis_results
            book.price = value_estimation['price_range']['recommended']
            book.price_details = {
                'last_analysis': datetime.utcnow().isoformat(),
                'confidence_score': value_estimation['confidence_score'],
                'price_range': value_estimation['price_range']
            }

            from app import db
            db.session.commit()

            return analysis_results

        except Exception as e:
            logging.error(f"Fehler bei der Preisanalyse: {str(e)}")
            return self._get_default_analysis()

    async def _collect_market_data(self, book) -> Dict[str, Any]:
        """
        Sammelt aktuelle Marktdaten von verschiedenen Quellen.
        """
        market_data = {
            'booklooker': await self._get_booklooker_prices(book),
            'zvab': await self._get_zvab_prices(book),
            'abebooks': await self._get_abebooks_prices(book),
            'eurobuch': await self._get_eurobuch_prices(book)
        }
        
        # Füge Statistiken für jede Quelle hinzu
        for source, data in market_data.items():
            if data.get('prices'):
                prices = [float(p) for p in data['prices']]
                data['stats'] = {
                    'min': min(prices),
                    'max': max(prices),
                    'avg': statistics.mean(prices),
                    'median': statistics.median(prices),
                    'count': len(prices)
                }
            else:
                data['stats'] = {}
            
            data['timestamp'] = datetime.utcnow().isoformat()
            
        return market_data

    def _analyze_condition_impact(self, condition: Optional[str]) -> Dict[str, Any]:
        """
        Analysiert den Einfluss des Buchzustands auf den Preis.
        """
        condition = condition or 'Good'
        condition_factor = self.condition_factors.get(
            condition,
            self.condition_factors['Good']
        )
        
        return {
            'condition_factor': condition_factor,
            'condition_description': condition,
            'estimated_impact': {
                'percentage': (1 - condition_factor) * 100,
                'description': self._get_condition_description(condition)
            }
        }

    def _analyze_rarity(self, book, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert die Seltenheit des Buches.
        """
        # Berechne Verfügbarkeit
        availability_count = sum(
            len(source.get('prices', [])) 
            for source in market_data.values()
        )
        
        # Berechne Altersfaktor (je älter, desto seltener)
        current_year = datetime.now().year
        age_factor = min(
            1.0,
            (current_year - (book.publication_year or current_year)) / 100 + 0.5
        )
        
        # Bewerte Edition
        edition_info = self._analyze_edition(book)
        
        rarity_score = self._calculate_rarity_score(
            availability_count,
            age_factor,
            edition_info
        )
        
        return {
            'rarity_score': rarity_score,
            'collector_value': self._estimate_collector_value(book, rarity_score),
            'rarity_indicators': {
                'market_availability': {
                    'count': availability_count,
                    'rating': 'High' if availability_count < 5 else 'Medium' if availability_count < 20 else 'Low'
                },
                'edition_info': edition_info,
                'age_factor': age_factor,
                'special_features': self._get_special_features(book)
            }
        }

    def _analyze_regional_prices(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert regionale Preisunterschiede.
        """
        regional_prices = {
            'DE': self._get_regional_stats(market_data, 'DE'),
            'AT': self._get_regional_stats(market_data, 'AT'),
            'CH': self._get_regional_stats(market_data, 'CH'),
            'EU': self._get_regional_stats(market_data, 'EU')
        }
        
        return {
            'regional_prices': regional_prices,
            'price_variations': self._calculate_price_variations(regional_prices),
            'recommended_markets': self._get_recommended_markets(regional_prices)
        }

    def _estimate_value(self, book, market_data: Dict[str, Any],
                       condition_impact: Dict[str, Any],
                       rarity_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Berechnet den geschätzten Wert des Buches.
        """
        # Sammle alle verfügbaren Preise
        all_prices = []
        for source in market_data.values():
            all_prices.extend(float(p) for p in source.get('prices', []))
            
        if not all_prices:
            return self._get_default_value_estimation()
            
        # Berechne Basiswert
        base_value = statistics.median(all_prices)
        
        # Passe basierend auf Zustand an
        condition_factor = condition_impact['condition_factor']
        
        # Passe basierend auf Seltenheit an
        rarity_factor = rarity_analysis['rarity_score']
        
        # Berücksichtige Markttrends
        market_trend_factor = self._calculate_market_trend(market_data)
        
        # Berechne angepassten Wert
        adjusted_value = base_value * condition_factor * rarity_factor * market_trend_factor
        
        # Berechne Preisspanne
        price_range = {
            'min': max(1.0, adjusted_value * 0.8),
            'max': adjusted_value * 1.2,
            'recommended': adjusted_value
        }
        
        return {
            'base_value': base_value,
            'adjusted_value': adjusted_value,
            'price_range': price_range,
            'adjustment_factors': {
                'condition': condition_factor,
                'rarity': rarity_factor,
                'market_trend': market_trend_factor
            },
            'confidence_score': self._calculate_confidence_score(
                all_prices,
                condition_impact,
                rarity_analysis
            )
        }

    def _get_default_analysis(self) -> Dict[str, Any]:
        """
        Liefert eine Standard-Analyse wenn keine Daten verfügbar sind.
        """
        return {
            'market_prices': {
                source: {
                    'prices': [],
                    'stats': {},
                    'timestamp': datetime.utcnow().isoformat()
                }
                for source in ['booklooker', 'zvab', 'abebooks', 'eurobuch']
            },
            'historical_data': {
                'price_trends': {},
                'seasonal_patterns': {},
                'long_term_trend': {}
            },
            'condition_impact': {
                'condition_factor': 0.5,
                'condition_description': 'Good',
                'estimated_impact': {}
            },
            'rarity_analysis': {
                'rarity_score': 1.0,
                'collector_value': {},
                'rarity_indicators': {
                    'market_availability': {},
                    'edition_info': {},
                    'age_factor': 1.0,
                    'special_features': []
                }
            },
            'regional_analysis': {
                'regional_prices': {
                    region: {}
                    for region in ['DE', 'AT', 'CH', 'EU']
                },
                'price_variations': {},
                'recommended_markets': []
            },
            'value_estimation': {
                'base_value': 0.0,
                'adjusted_value': 0.0,
                'price_range': {
                    'min': 0.0,
                    'max': 0.0,
                    'recommended': 0.0
                },
                'adjustment_factors': {
                    'condition': 0.5,
                    'rarity': 1.0,
                    'market_trend': 1.0
                },
                'confidence_score': 0.8
            },
            'collector_indicators': {},
            'timestamp': datetime.utcnow().isoformat()
        }

    # Hilfsmethoden

    async def _get_booklooker_prices(self, book) -> Dict[str, Any]:
        """Sammelt Preise von Booklooker."""
        # TODO: Implementiere Booklooker API Integration
        return {'prices': [], 'stats': {}}

    async def _get_zvab_prices(self, book) -> Dict[str, Any]:
        """Sammelt Preise von ZVAB."""
        # TODO: Implementiere ZVAB API Integration
        return {'prices': [], 'stats': {}}

    async def _get_abebooks_prices(self, book) -> Dict[str, Any]:
        """Sammelt Preise von AbeBooks."""
        # TODO: Implementiere AbeBooks API Integration
        return {'prices': [], 'stats': {}}

    async def _get_eurobuch_prices(self, book) -> Dict[str, Any]:
        """Sammelt Preise von Eurobuch."""
        # TODO: Implementiere Eurobuch API Integration
        return {'prices': [], 'stats': {}}

    def _get_condition_description(self, condition: str) -> str:
        """Liefert eine detaillierte Beschreibung des Zustands."""
        descriptions = {
            'New': 'Neu und ungebraucht',
            'Like New': 'Wie neu, minimale Gebrauchsspuren',
            'Very Good': 'Sehr gut erhalten, leichte Gebrauchsspuren',
            'Good': 'Gut erhalten, normale Gebrauchsspuren',
            'Fair': 'Akzeptabler Zustand, deutliche Gebrauchsspuren',
            'Poor': 'Stark gebraucht, möglicherweise beschädigt'
        }
        return descriptions.get(condition, 'Zustand unbekannt')

    def _analyze_edition(self, book) -> Dict[str, Any]:
        """Analysiert Informationen zur Edition."""
        return {
            'is_first_edition': False,  # TODO: Implementiere Erkennung
            'is_special_edition': False,
            'edition_number': self._parse_edition_number(book.edition),
            'significance': 'Standard'
        }

    def _parse_edition_number(self, edition_str: Optional[str]) -> Optional[int]:
        """Extrahiert die Auflagennummer aus einem String."""
        if not edition_str:
            return None
        try:
            # Suche nach Zahlen im String
            import re
            numbers = re.findall(r'\d+', edition_str)
            return int(numbers[0]) if numbers else None
        except Exception:
            return None

    def _calculate_rarity_score(self, availability: int,
                              age_factor: float,
                              edition_info: Dict[str, Any]) -> float:
        """Berechnet einen Seltenheitswert."""
        # Basis-Seltenheit basierend auf Verfügbarkeit
        base_rarity = 1.0 - min(1.0, availability / 100)
        
        # Gewichtete Summe der Faktoren
        weighted_score = (
            base_rarity * 0.4 +  # Verfügbarkeit
            age_factor * 0.3 +   # Alter
            (0.3 if edition_info['is_first_edition'] else 0.0)  # Edition
        )
        
        return round(weighted_score, 2)

    def _calculate_market_trend(self, market_data: Dict[str, Any]) -> float:
        """Berechnet den aktuellen Markttrend."""
        # TODO: Implementiere Trendanalyse
        return 1.0

    def _calculate_confidence_score(self,
                                 prices: list,
                                 condition_impact: Dict[str, Any],
                                 rarity_analysis: Dict[str, Any]) -> float:
        """Berechnet einen Konfidenzwert für die Preisschätzung."""
        if not prices:
            return 0.5
            
        # Preisvarianz
        try:
            variance = statistics.variance(prices)
            price_confidence = 1.0 - min(1.0, variance / (max(prices) ** 2))
        except statistics.StatisticsError:
            price_confidence = 0.5
            
        # Gewichteter Durchschnitt der Faktoren
        confidence = (
            price_confidence * 0.4 +
            condition_impact['condition_factor'] * 0.3 +
            rarity_analysis['rarity_score'] * 0.3
        )
        
        return round(confidence, 2)

    def _get_collector_indicators(self, book) -> Dict[str, Any]:
        """Identifiziert Sammlerrelevante Merkmale."""
        return {}  # TODO: Implementiere Sammleranalyse

    def _get_special_features(self, book) -> list:
        """Identifiziert besondere Merkmale des Buches."""
        features = []
        
        if book.edition and 'erste' in book.edition.lower():
            features.append('Erstausgabe')
            
        if book.condition == 'New':
            features.append('Neuwertig')
            
        return features

    def _get_regional_stats(self, market_data: Dict[str, Any],
                           region: str) -> Dict[str, Any]:
        """Berechnet regionale Statistiken."""
        return {}  # TODO: Implementiere regionale Statistiken

    def _calculate_price_variations(self,
                                 regional_prices: Dict[str, Any]) -> Dict[str, Any]:
        """Berechnet Preisvariationen zwischen Regionen."""
        return {}  # TODO: Implementiere Preisvariationsanalyse

    def _get_recommended_markets(self,
                              regional_prices: Dict[str, Any]) -> list:
        """Bestimmt die besten Märkte für den Verkauf."""
        return []  # TODO: Implementiere Marktempfehlungen

    def _get_default_value_estimation(self) -> Dict[str, Any]:
        """Liefert eine Standard-Wertschätzung."""
        return {
            'base_value': 0.0,
            'adjusted_value': 0.0,
            'price_range': {
                'min': 0.0,
                'max': 0.0,
                'recommended': 0.0
            },
            'adjustment_factors': {
                'condition': 0.5,
                'rarity': 1.0,
                'market_trend': 1.0
            },
            'confidence_score': 0.8
        }