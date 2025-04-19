import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CacheManager:
    """
    Cache-Manager für die Zwischenspeicherung von API-Antworten und Analyseergebnissen.
    """
    
    def __init__(self, cache_dir: str = 'app/cache'):
        self.cache_dir = cache_dir
        self.price_cache_duration = timedelta(hours=24)  # Preise 24 Stunden cachen
        self.metadata_cache_duration = timedelta(days=7)  # Metadaten 7 Tage cachen
        
        # Erstelle Cache-Verzeichnis falls nicht vorhanden
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(os.path.join(cache_dir, 'prices'), exist_ok=True)
        os.makedirs(os.path.join(cache_dir, 'metadata'), exist_ok=True)
        
    def get_cached_price_data(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Holt gecachte Preisdaten für ein Buch, falls vorhanden und nicht veraltet.
        """
        cache_file = os.path.join(self.cache_dir, 'prices', f'book_{book_id}.json')
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                
            # Prüfe ob Cache noch gültig ist
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.utcnow() - cached_time > self.price_cache_duration:
                return None
                
            return cached_data['data']
            
        except Exception:
            return None
            
    def cache_price_data(self, book_id: int, data: Dict[str, Any]):
        """
        Speichert Preisdaten im Cache.
        """
        cache_file = os.path.join(self.cache_dir, 'prices', f'book_{book_id}.json')
        
        cache_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Fehler beim Caching loggen aber nicht die Hauptfunktion beeinträchtigen
            pass
            
    def get_cached_metadata(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Holt gecachte Metadaten für ein Buch, falls vorhanden und nicht veraltet.
        """
        cache_file = os.path.join(self.cache_dir, 'metadata', f'book_{book_id}.json')
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                
            # Prüfe ob Cache noch gültig ist
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.utcnow() - cached_time > self.metadata_cache_duration:
                return None
                
            return cached_data['data']
            
        except Exception:
            return None
            
    def cache_metadata(self, book_id: int, data: Dict[str, Any]):
        """
        Speichert Metadaten im Cache.
        """
        cache_file = os.path.join(self.cache_dir, 'metadata', f'book_{book_id}.json')
        
        cache_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Fehler beim Caching loggen aber nicht die Hauptfunktion beeinträchtigen
            pass
            
    def clear_expired_cache(self):
        """
        Bereinigt abgelaufene Cache-Einträge.
        """
        # Bereinige Preis-Cache
        self._clear_expired_directory(
            os.path.join(self.cache_dir, 'prices'),
            self.price_cache_duration
        )
        
        # Bereinige Metadaten-Cache
        self._clear_expired_directory(
            os.path.join(self.cache_dir, 'metadata'),
            self.metadata_cache_duration
        )
        
    def _clear_expired_directory(self, directory: str, max_age: timedelta):
        """
        Löscht abgelaufene Cache-Dateien in einem Verzeichnis.
        """
        now = datetime.utcnow()
        
        for filename in os.listdir(directory):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    
                cached_time = datetime.fromisoformat(cached_data['timestamp'])
                if now - cached_time > max_age:
                    os.remove(file_path)
            except Exception:
                # Bei Fehlern die Datei sicherheitshalber löschen
                try:
                    os.remove(file_path)
                except Exception:
                    pass