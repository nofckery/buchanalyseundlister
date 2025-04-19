import os
from datetime import datetime, timedelta
from typing import List, Set
from app import db
from app.models import Book
from app.utils.cache_manager import CacheManager
import logging

class CleanupService:
    """
    Service zum Aufräumen alter Dateien und nicht mehr benötigter Ressourcen.
    """
    
    def __init__(self, upload_dir: str = 'app/static/uploads',
                 max_orphan_age: timedelta = timedelta(days=7)):
        self.upload_dir = upload_dir
        self.max_orphan_age = max_orphan_age
        self.cache_manager = CacheManager()
        
    def cleanup(self) -> dict:
        """
        Führt alle Cleanup-Operationen durch.
        """
        results = {
            'images_cleaned': 0,
            'cache_cleaned': 0,
            'errors': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Bereinige verwaiste Bilder
            results['images_cleaned'] = self._cleanup_orphaned_images()
            
            # Bereinige abgelaufenen Cache
            self.cache_manager.clear_expired_cache()
            results['cache_cleaned'] = 1
            
        except Exception as e:
            results['errors'].append(str(e))
            logging.error(f"Fehler beim Cleanup: {str(e)}")
            
        return results
        
    def _cleanup_orphaned_images(self) -> int:
        """
        Löscht Bilddateien, die nicht mehr mit Büchern verknüpft sind.
        """
        # Hole alle aktiven Bild-URLs aus der Datenbank
        active_images: Set[str] = set()
        try:
            books = Book.query.all()
            for book in books:
                if book.image_urls:
                    active_images.update(
                        os.path.basename(url) for url in book.image_urls
                    )
        except Exception as e:
            logging.error(f"Fehler beim Laden der Buchbilder: {str(e)}")
            return 0
            
        deleted_count = 0
        now = datetime.utcnow()
        
        # Überprüfe alle Dateien im Upload-Verzeichnis
        for filename in os.listdir(self.upload_dir):
            file_path = os.path.join(self.upload_dir, filename)
            
            # Überspringe .gitkeep und andere spezielle Dateien
            if filename.startswith('.'):
                continue
                
            try:
                # Wenn die Datei nicht in aktiven Bildern ist und alt genug
                if (filename not in active_images and 
                    self._is_file_old_enough(file_path)):
                    os.remove(file_path)
                    deleted_count += 1
                    logging.info(f"Gelöschte verwaiste Bilddatei: {filename}")
                    
            except Exception as e:
                logging.error(f"Fehler beim Löschen von {filename}: {str(e)}")
                
        return deleted_count
        
    def _is_file_old_enough(self, file_path: str) -> bool:
        """
        Prüft, ob eine Datei alt genug ist, um gelöscht zu werden.
        """
        try:
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            return datetime.utcnow() - file_time > self.max_orphan_age
        except Exception:
            # Im Zweifelsfall die Datei behalten
            return False
            
    def get_storage_stats(self) -> dict:
        """
        Sammelt Statistiken über den Speicherverbrauch.
        """
        stats = {
            'upload_dir_size': 0,
            'cache_dir_size': 0,
            'orphaned_images': 0,
            'total_images': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Berechne Upload-Verzeichnisgröße
        for path, _, files in os.walk(self.upload_dir):
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(path, file)
                    stats['upload_dir_size'] += os.path.getsize(file_path)
                    stats['total_images'] += 1
                    
        # Berechne Cache-Verzeichnisgröße
        for path, _, files in os.walk(self.cache_manager.cache_dir):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(path, file)
                    stats['cache_dir_size'] += os.path.getsize(file_path)
                    
        # Zähle verwaiste Bilder
        active_images = set()
        try:
            books = Book.query.all()
            for book in books:
                if book.image_urls:
                    active_images.update(
                        os.path.basename(url) for url in book.image_urls
                    )
                    
            for filename in os.listdir(self.upload_dir):
                if not filename.startswith('.') and filename not in active_images:
                    stats['orphaned_images'] += 1
                    
        except Exception as e:
            logging.error(f"Fehler beim Sammeln der Statistiken: {str(e)}")
            
        # Konvertiere Bytes in MB
        stats['upload_dir_size'] = round(stats['upload_dir_size'] / (1024 * 1024), 2)
        stats['cache_dir_size'] = round(stats['cache_dir_size'] / (1024 * 1024), 2)
        
        return stats