from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    DATABASE = DATA_DIR / "app.db"
    SECRET_KEY = "dev-secret-key"
    JSON_AS_ASCII = False
    # Google Maps settings (can be overridden from environment)
    GOOGLE_MAPS_API_KEY = None
    USE_REAL_MAPS = False

