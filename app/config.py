from google.cloud import secretmanager
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def access_secret_version(project_id, secret_id):
    """
    Greift auf die aktuelle Version eines Secrets in Google Secret Manager zu.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully accessed secret: {secret_id}")
        return secret_value
    except Exception as e:
        logger.error(f"Fehler beim Zugriff auf Secret {secret_id}: {e}")
        return None

def load_secrets():
    """
    Lädt alle benötigten Secrets aus dem Google Secret Manager.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.warning("GOOGLE_CLOUD_PROJECT nicht gesetzt")
        return {}

    secrets_to_load = [
        "SECRET_KEY",
        "GEMINI_API_KEY",
        "EBAY_APP_ID",
        "EBAY_CERT_ID",
        "EBAY_DEV_ID",
        "EBAY_AUTH_TOKEN",
        "BOOKLOOKER_API_KEY",
        "DB_PASSWORD" # Load DB_PASSWORD from secrets
    ]

    loaded_secrets = {}
    for secret_id in secrets_to_load:
        value = access_secret_version(project_id, secret_id)
        if value:
            loaded_secrets[secret_id] = value
        else:
            logger.warning(f"Secret {secret_id} konnte nicht geladen werden")

    return loaded_secrets

def init_app(app):
    """
    Initialisiert die Anwendungskonfiguration.
    """
    # Lade Secrets aus dem Secret Manager (außer DB-Verbindung)
    secrets = load_secrets()

    # Grundlegende Flask-Konfiguration
    app.config["SECRET_KEY"] = secrets.get("SECRET_KEY", "dev-key-fallback")

    # Datenbank-Konfiguration für Cloud SQL via Unix Socket
    # Cloud Run sets INSTANCE_UNIX_SOCKET when Cloud SQL instance is connected
    # Explicitly strip potential problematic characters like \r
    instance_connection_raw = os.environ.get("INSTANCE_CONNECTION_NAME", "")
    instance_connection = instance_connection_raw.strip()
    logger.info(f"Raw INSTANCE_CONNECTION_NAME: '{instance_connection_raw}'")
    logger.info(f"Cleaned INSTANCE_CONNECTION_NAME: '{instance_connection}'")

    db_user = os.getenv("DB_USER", "cloud-run-user").strip()
    db_pass = secrets.get("DB_PASSWORD", "").strip() # Get password from secrets, default to empty if not found
    db_name = os.getenv("DB_NAME", "buchdb").strip()

    if not db_pass:
         logger.warning("DB_PASSWORD secret not found or empty.")
         # Decide how to handle missing password - raise error or use default?
         # For now, let's try connecting without it, maybe IAM auth is intended
         # raise RuntimeError("DB_PASSWORD secret not found or empty.")


    if instance_connection:
        socket_dir = "/cloudsql"
        # Construct the URI using the cleaned instance connection name
        db_uri = (
            f"postgresql+psycopg2://{db_user}:{db_pass}@/{db_name}"
            f"?host={socket_dir}/{instance_connection}"
        )
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
        logger.info(f"Using Cloud SQL Unix socket.SQLALCHEMY_DATABASE_URI: {db_uri}")
    else:
        # Fallback or raise error if not running in Cloud Run with SQL connection
        logger.error("INSTANCE_CONNECTION_NAME environment variable not found or empty.")
        # Optionally, load a local DB URL from .env for local development
        local_db_url = os.getenv('DATABASE_URL_LOCAL')
        if local_db_url:
             app.config['SQLALCHEMY_DATABASE_URI'] = local_db_url
             logger.info("Using local database URL from DATABASE_URL_LOCAL")
        else:
             raise RuntimeError("Database connection not configured (INSTANCE_CONNECTION_NAME missing).")


    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Upload Konfiguration
    app.config["MAX_CONTENT_LENGTH"] = 21 * 1024 * 1024  # 21MB (Angepasst an MAX_FILE_SIZE + Puffer)
    # app.config["UPLOAD_FOLDER"] = "app/static/uploads" # Nicht mehr benötigt für GCS
    app.config["MAX_FILE_SIZE"] = 20 * 1024 * 1024  # 20MB pro Datei
    app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".jpeg", ".png", ".gif"]
    app.config["GCS_BUCKET_NAME"] = os.getenv("GCS_BUCKET_NAME", "buchanalyse-prod-buchanalyse-uploads") # Standard auf erstellten Bucket gesetzt

    # API Konfigurationen
    app.config["GEMINI_API_KEY"] = secrets.get("GEMINI_API_KEY")
    app.config["EBAY_APP_ID"] = secrets.get("EBAY_APP_ID")
    app.config["EBAY_CERT_ID"] = secrets.get("EBAY_CERT_ID")
    app.config["EBAY_DEV_ID"] = secrets.get("EBAY_DEV_ID")
    app.config["EBAY_AUTH_TOKEN"] = secrets.get("EBAY_AUTH_TOKEN")
    app.config["EBAY_SANDBOX"] = "True"

    app.config["BOOKLOOKER_API_KEY"] = secrets.get("BOOKLOOKER_API_KEY")
    app.config["BOOKLOOKER_API_URL"] = "https://api.booklooker.de/2.0"
    app.config["BOOKLOOKER_SYNC_INTERVAL"] = 3600  # 1 Stunde

    # Cache Konfiguration
    app.config["CACHE_TYPE"] = "filesystem"
    app.config["CACHE_DIR"] = "app/cache"
    app.config["CACHE_DEFAULT_TIMEOUT"] = 86400  # 24 Stunden

    return app
