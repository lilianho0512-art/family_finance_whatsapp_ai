import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/family_finance.db")
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
    WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Kuala_Lumpur")

    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-to-a-long-random-string-at-least-32-bytes")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    UPLOADS_DIR = BASE_DIR / "uploads"
    OUTPUT_DIR = BASE_DIR / "output"
    LOGS_DIR = BASE_DIR / "logs"


settings = Settings()

for _d in [settings.DATA_DIR, settings.UPLOADS_DIR, settings.OUTPUT_DIR, settings.LOGS_DIR]:
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
