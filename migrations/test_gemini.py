# test_gemini.py
import google.generativeai as genai
import os
import logging

# Konfiguriere einfaches Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Konfiguration ---
# Ersetze dies durch deinen API Key oder lade ihn sicher, z.B. aus einer Umgebungsvariable
# api_key = os.getenv('GEMINI_API_KEY') 
api_key = 'AIzaSyB0CXn0Vx4_N1P9ZKDwbrZ3i7ygevVbPO4' # NUR FÜR LOKALEN TEST!

# Das zu testende Modell
model_name = 'models/gemini-2.0-flash' 
# --- Ende Konfiguration ---

if not api_key:
    logging.error("API Key nicht gefunden. Setze ihn im Skript oder als Umgebungsvariable GEMINI_API_KEY.")
else:
    logging.info("API Key gefunden.")
    try:
        logging.info(f"Konfiguriere Gemini mit API Key...")
        genai.configure(api_key=api_key)
        logging.info("Konfiguration abgeschlossen.")

        logging.info(f"Initialisiere Modell: {model_name}...")
        # Versuche, das spezifische Modell zu laden
        model = genai.GenerativeModel(model_name)
        logging.info(f"Modell '{model_name}' erfolgreich initialisiert.")

        logging.info("Starte einfachen 'generate_content'-Aufruf...")
        # Mache einen einfachen Text-Aufruf
        response = model.generate_content("Gib 'Hallo Welt' zurück.")
        logging.info("Aufruf abgeschlossen.")

        if response and response.text:
            logging.info(f"Erfolgreiche Antwort erhalten: {response.text}")
        elif response:
             logging.warning(f"Antwort erhalten, aber ohne Textinhalt: {response}")
        else:
            logging.error("Keine Antwort vom Modell erhalten.")

    except Exception as e:
        logging.error(f"Ein Fehler ist aufgetreten: {e}", exc_info=True)