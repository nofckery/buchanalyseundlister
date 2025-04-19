import os
import re
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List
import google.generativeai as genai
from PIL import Image
from flask import current_app as app
import requests # Hinzugefügt für URL-Downloads
import io # Hinzugefügt für BytesIO

class ImageAnalysisController:
    def __init__(self, api_key: str):
            """Initialisiert den Image Analysis Controller mit dem Gemini API Key."""
            try:
                # Initialisiere das Gemini-Modell
                genai.configure(api_key=api_key)
                
                # Verwende das Pro-Modell für Multimodal-Analyse
                model_name = 'gemini-2.5-pro-exp-03-25'
                app.logger.info(f"Initialisiere Gemini-Modell: {model_name}")
                
                self.model = genai.GenerativeModel(model_name)
                
            except Exception as e:
                error_msg = f"Fehler bei der Modell-Initialisierung: {str(e)}"
                app.logger.error(f"{error_msg}\n{traceback.format_exc()}")
                raise ValueError(error_msg)


    def analyze_book_images(self, book_id: int, image_urls: List[str]) -> Dict[str, Any]: # Parameter umbenannt
        """
        Analysiert mehrere Buchbilder von URLs und extrahiert relevante Metadaten.
        """
        try:
            # Lade alle Bilder von URLs
            images = []
            for url in image_urls:
                try:
                    response = requests.get(url, stream=True, timeout=10) # Timeout hinzugefügt
                    response.raise_for_status() # Fehler bei schlechtem Status werfen
                    # Bildinhalt in BytesIO-Objekt laden, damit PIL es öffnen kann
                    image_data = io.BytesIO(response.content)
                    images.append(Image.open(image_data))
                    app.logger.debug(f"Bild von URL geladen: {url}")
                except requests.exceptions.RequestException as req_err:
                    app.logger.error(f"Fehler beim Herunterladen von Bild {url}: {req_err}")
                    # Optional: Fehler werfen oder mit den restlichen Bildern fortfahren
                    # Hier fahren wir fort, aber loggen den Fehler
                    continue # Zum nächsten Bild springen
                except Exception as img_err:
                     app.logger.error(f"Fehler beim Öffnen von Bild von URL {url}: {img_err}")
                     continue # Zum nächsten Bild springen

            if not images:
                 app.logger.error("Keine Bilder konnten erfolgreich von URLs geladen werden.")
                 # Rückgabe eines Fehlerobjekts, das dem bestehenden Fehlerhandling entspricht
                 raise ValueError("Keine Bilder konnten erfolgreich von URLs geladen werden.")
            
            # Erstelle den Analyse-Prompt
            prompt = self._create_analysis_prompt()
            app.logger.info(f"Gemini-Prompt wird gesendet:\n{prompt[:500]}...") # Log Prompt Start
            
            # Führe Gemini-Analyse mit allen Bildern durch
            app.logger.info("Starte Gemini-Analyse...")
            response = self.model.generate_content([prompt, *images])
            
            if not response or not response.text:
                raise ValueError("Keine Antwort vom Gemini-Modell")
                
            app.logger.info(f"Rohe Gemini-Antwort empfangen (Länge: {len(response.text)} Zeichen). Start:\n{response.text[:500]}...") # Log Raw Response Start
            
            # Extrahiere strukturierte Daten
            app.logger.info("Parse Gemini-Antwort...")
            analysis_results = self._parse_gemini_response(response.text)
            app.logger.info(f"Geparste Analyse-Ergebnisse (Auszug): {str(analysis_results)[:500]}...") # Log Parsed Results
            
            # Validiere und ergänze die Daten
            self._enrich_metadata(analysis_results)
            
            return analysis_results

        except Exception as e:
            error_msg = f"Fehler bei der Bildanalyse: {str(e)}"
            app.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return {
                'error': error_msg,
                'metadata': {},
                'condition_analysis': {},
                'market_data': {},
                'additional_info': {},
                'confidence_scores': {},
                'processing_timestamp': datetime.utcnow().isoformat()
            }

    def _create_analysis_prompt(self) -> str:
        """
        Erstellt einen detaillierten Prompt für die Gemini-Analyse.
        """
        return """
        Analysiere die bereitgestellten Buchbilder und führe eine umfassende Recherche durch.
        Beachte dabei alle sichtbaren Details auf den Bildern (Cover, Rückseite, Impressum etc.).

        1. Grundinformationen extrahieren:
        - Deutscher Titel und Originaltitel (falls abweichend)
        - Autor(en)
        - ISBN/EAN
        - Verlag
        - Erscheinungsjahr
        - Auflage/Edition (mit Details wie "Erstausgabe", "limitiert" etc.)
        - Format (Hardcover/Paperback/Sonderformat)
        - Seitenanzahl
        - Sprache
        - Genre/Kategorie
        
        2. Maße und physische Eigenschaften:
        - WICHTIG: Suche auf den Bildern nach einem Zollstock/Maßband
        - Miss die Länge, Breite und Höhe des Buches anhand des Zollstocks/Maßbands
        - Gib die Maße in Zentimetern an (Länge x Breite x Höhe)
        - Achte auf korrekte Perspektive und Ausrichtung bei der Messung
        - Vermerke wenn kein Maßstab im Bild erkennbar ist

        3. Zustandsanalyse (basierend auf allen Bildern):
        - Detaillierte Beschreibung des Zustands
        - Vorhandene Mängel oder Besonderheiten
        - Gebrauchsspuren
        - Zustandseinschätzung (Neu/Wie neu/Sehr gut/Gut/Akzeptabel)
        - Vollständigkeit (falls erkennbar)
        - Besondere Merkmale oder Schäden

        3. Preisrecherche und Marktanalyse:
        - Neupreis (wenn verfügbar, z.B. von Rückseite oder Verlagsangabe)

        - Marktrecherche (basierend auf aktuellen Online-Angeboten):
          * Vergleichbare AKTUELLE Angebote der GLEICHEN Auflage:
            - Mindestens 5 Angebote wenn möglich
            - Exakte Links zu den Angeboten
            - Detaillierte Zustandsbeschreibung aus den Angeboten
            - Aktuelle Verkaufspreise
            - Besonderheiten der Angebote (z.B. signiert, Schutzumschlag)
          
          * Vergleichbare Angebote ANDERER Auflagen:
            - Mindestens 3 Angebote pro relevante andere Auflage
            - Auflagenangabe und Jahr
            - Preise im Verhältnis zur analysierten Auflage
            
          
          * Angebote OHNE Auflagenangabe:
            - Mindestens 3 Angebote
            - Preise
        
        - Detaillierte Preisempfehlung:
          * Vorgeschlagener Verkaufspreis (Format: "X-Y EUR")
          * Ausführliche Begründung basierend auf:
            - Konkrete Vergleiche mit aktuellen Angeboten (mit Links)
            - Spezifischer Zustand des vorliegenden Exemplars
            - Besonderheiten dieser Auflage
            - Aktuelle Marktsituation (Angebot/Nachfrage)
            - Verkaufsplattform-spezifische Faktoren
          * Preisstrategie:
            - Schneller Verkauf vs. optimaler
            - Saisonale Faktoren
            - Aktuelle Markttrends

        4. Zusatzinformationen:
        - Kurze Inhaltszusammenfassung
        - Zielgruppe
        - Besonderheiten der Edition
        - Auszeichnungen/Rezensionen
        - Sammlungsrelevanz
        - Historische oder kulturelle Bedeutung

        Formatiere die Ausgabe als JSON mit folgender Struktur:
        {
            "metadata": {
                "deutscher_titel": string,
                "originaltitel": string,
                "autor": string,
                "isbn": string,
                "verlag": string,
                "erscheinungsjahr": number,
                "auflage": string,
                "format": string,
                "seitenanzahl": number,
                "sprache": string,
                "genre": string
            },
            "physical_properties": {
                "dimensions": {
                    "length": number,  // Länge in cm
                    "width": number,   // Breite in cm
                    "height": number,  // Höhe in cm
                    "measurement_confidence": number,  // Konfidenz der Messung (0-1)
                    "measurement_method": string,  // z.B. "Zollstock im Bild"
                    "notes": string    // Zusätzliche Bemerkungen zur Messung
                }
            },
            "condition_analysis": {
                "zustand_beschreibung": string,
                "maengel_besonderheiten": string,
                "zustand_einschätzung": string,
                "confidence_score": number
            },
            "market_data": {
                "neupreis": {
                    "preis": string (format: "X.XX EUR"),
                    "quelle": string
                },
                "vergleichsangebote": {
                    "aktuelle_auflage": [
                        {
                            "preis": string (format: "X.XX EUR"),
                            "zustand": string,
                            "zustand_details": string,
                            "anbieter": string,
                            "plattform": string,
                            "link": string,
                            "besonderheiten": string[],
                            "verkaeufer_bewertung": string
                        }
                    ],
                    "andere_auflagen": [
                        {
                            "auflage": string,
                            "erscheinungsjahr": number,
                            "preis": string (format: "X.XX EUR"),
                            "zustand": string,
                            "zustand_details": string,
                            "anbieter": string,
                            "plattform": string,
                            "link": string,
                            "preisdifferenz_begruendung": string
                        }
                    ],
                    "ohne_auflage": [
                        {
                            "preis": string (format: "X.XX EUR"),
                            "zustand": string,
                            "anbieter": string,
                            "plattform": string,
                            "link": string,
                            "relevanz_einschaetzung": string
                        }
                    ],
                    "statistik": {
                        "durchschnittspreis": {
                            "aktuelle_auflage": string (format: "X.XX EUR"),
                            "andere_auflagen": string (format: "X.XX EUR"),
                            "gesamt": string (format: "X.XX EUR")
                        },
                        "preisspanne": {
                            "min": string (format: "X.XX EUR"),
                            "max": string (format: "X.XX EUR")
                        },
                        "angebotsmenge": {
                            "aktuelle_auflage": number,
                            "andere_auflagen": number,
                            "ohne_auflage": number
                        }
                    }
                },
                "preisanalyse": {
                    "empfehlung": {
                        "verkaufspreis": {
                            "optimal": string (format: "X-Y EUR"),
                            "schnellverkauf": string (format: "X-Y EUR")
                        },
                        "begruendung": {
                            "hauptfaktoren": string[],
                            "referenzangebote": string[],
                            "marktposition": string
                        },
                        "verkaufsstrategie": {
                            "plattform_empfehlungen": {
                                "booklooker": string,
                                "ebay": string
                            },
                            "optimale_laufzeit": string,
                            "saisonale_aspekte": string
                        }
                    },
                    "preisvergleich": {
                        "aktuelle_auflage": {
                            "durchschnitt": string (format: "X.XX EUR"),
                            "spanne": string,
                            "trend": string,
                            "vergleichsangebote": string[]
                        },
                        "andere_auflagen": {
                            "preisdifferenz": string,
                            "begruendung": string,
                            "empfehlung": string
                        }
                    },
                    "zustandsbasierte_preise": {
                        "neuwertig": {
                            "preis": string (format: "X-Y EUR"),
                            "marktlage": string,
                            "vergleichsangebote": string[]
                        },
                        "sehr_gut": {
                            "preis": string (format: "X-Y EUR"),
                            "marktlage": string,
                            "vergleichsangebote": string[]
                        },
                        "gut": {
                            "preis": string (format: "X-Y EUR"),
                            "marktlage": string,
                            "vergleichsangebote": string[]
                        },
                        "akzeptabel": {
                            "preis": string (format: "X-Y EUR"),
                            "marktlage": string,
                            "vergleichsangebote": string[]
                        }
                    }
                },
                "marktanalyse": {
                    "verfuegbarkeit": {
                        "aktuelle_auflage": number,
                        "andere_auflagen": number,
                        "ohne_auflage": number,
                        "beschreibung": string
                    },
                    "sammlerwert": {
                        "einschaetzung": string,
                        "begruendung": string
                    },
                    "preisfaktoren": {
                        "auflagenunterschiede": string,
                        "zustandseinfluss": string,
                        "saisonale_faktoren": string,
                        "nachfragesituation": string
                    }
                },
                "confidence_score": number
            },
            "additional_info": {
                "inhaltszusammenfassung": string,
                "zielgruppe": string,
                "besonderheiten": string,
                "auszeichnungen": string,
                "sammlungsrelevanz": string,
                "confidence_score": number
            }
        }

        Setze für unbekannte Werte null ein. Bewerte die Konfidenz deiner Einschätzungen mit Werten zwischen 0 und 1.
        """

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parst die Gemini API Antwort und strukturiert die Daten.
        """
        # Versuche, JSON aus Markdown-Code-Block zu extrahieren
        match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            json_str = match.group(1)
            app.logger.debug(f"JSON aus Markdown extrahiert: {json_str[:200]}...")
            try:
                parsed_data = json.loads(json_str)
                app.logger.info(f"Erfolgreich aus Markdown geparst. Ergebnis (Auszug): {str(parsed_data)[:200]}...")
                return parsed_data
            except json.JSONDecodeError as e:
                app.logger.error(f"Fehler beim Parsen von JSON aus Markdown: {e}")
                # Statt Fallback: Fehler auslösen, um das Problem anzuzeigen
                raise ValueError(f"Ungültiges JSON im Markdown-Block: {e}") from e

        # Fallback: Versuche, das äußerste JSON-Objekt zu finden
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            app.logger.debug(f"JSON durch Klammernsuche extrahiert: {json_str[:200]}...")
            try:
                # Versuche, das extrahierte JSON zu parsen
                parsed_data = json.loads(json_str)
                app.logger.info(f"Erfolgreich aus Klammernsuche geparst. Ergebnis (Auszug): {str(parsed_data)[:200]}...")
                return parsed_data
            except json.JSONDecodeError as e:
                app.logger.error(f"Fehler beim Parsen von JSON aus Klammernsuche: {e}")
                # Statt Fallback: Fehler auslösen
                raise ValueError(f"Ungültiges JSON bei Klammernsuche: {e}") from e

        # Wenn keine der Methoden einen JSON-String findet
        app.logger.warning("Kein JSON-String in der Gemini-Antwort gefunden.")
        raise ValueError("Kein JSON-String in der Gemini-Antwort gefunden.")
            
        # Entferne den allgemeinen Exception-Handler, um Fehler nach oben durchzureichen
        # except Exception as e:
        #     error_msg = f"Fehler beim Parsen der Gemini-Antwort: {str(e)}"
        #     app.logger.error(f"{error_msg}\n{traceback.format_exc()}")
        #     # Statt {} zurückzugeben, Fehler weiterleiten
        #     raise ValueError(f"Unerwarteter Fehler beim Parsen: {e}") from e

    def _enrich_metadata(self, analysis_results: Dict[str, Any]):
        """
        Ergänzt die Metadaten durch externe Quellen und Validierung.
        """
        try:
            isbn = analysis_results.get('metadata', {}).get('isbn')
            if isbn:
                # OpenLibrary API Abfrage
                ol_data = self._query_open_library(isbn)
                if ol_data:
                    analysis_results['validation_sources'] = {
                        'open_library': ol_data
                    }
                    app.logger.info(f"OpenLibrary-Daten ergänzt für ISBN {isbn}")

        except Exception as e:
            error_msg = f"Fehler bei der Metadaten-Anreicherung: {str(e)}"
            app.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            analysis_results['error_log'] = analysis_results.get('error_log', []) + [error_msg]

    def _query_open_library(self, isbn: str) -> Dict[str, Any]:
        """
        Fragt die OpenLibrary API nach zusätzlichen Buchinformationen ab.
        """
        try:
            import requests
            response = requests.get(
                f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json().get(f"ISBN:{isbn}", {})
                
            return {}
            
        except Exception as e:
            app.logger.error(f"OpenLibrary API Fehler: {str(e)}")
            return {}