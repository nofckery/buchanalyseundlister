import os
from dotenv import load_dotenv
import google.generativeai as genai

def list_available_models():
    """Listet alle verfügbaren Gemini-Modelle auf."""
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY nicht in .env gefunden")
        return
    
    genai.configure(api_key=api_key)
    
    try:
        models = genai.list_models()
        print("\nVerfügbare Modelle:")
        print("==================")
        for model in models:
            print(f"Name: {model.name}")
            print(f"Unterstützte Generierungsmethoden: {model.supported_generation_methods}")
            print("-------------------")
    except Exception as e:
        print(f"Fehler beim Abrufen der Modelle: {str(e)}")

if __name__ == "__main__":
    list_available_models()