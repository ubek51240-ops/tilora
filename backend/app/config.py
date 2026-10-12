import os
from pydantic import BaseModel

_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_default_db = f"sqlite:///{os.path.join(_base_dir, 'tilora.db').replace(chr(92), '/')}"

class Settings(BaseModel):
    PROJECT_NAME: str = "TILORA Adaptiv Ta'lim Platformasi"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "***REMOVED_SECRET***")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 kun
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = os.getenv("DATABASE_URL", _default_db)
    AI_API_KEY: str = os.getenv("AI_API_KEY", os.getenv("OPENAI_API_KEY", "***REMOVED_AI_KEY***"))
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.b.ai/v1")).rstrip("/")
    AI_MODEL: str = os.getenv("AI_MODEL", "deepseek-v4-flash-vision-exp")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "***REMOVED_AI_KEY***")
    DEFAULT_LOCALE: str = "uz"
    # Faqat oxirgi chora: AI_SSL_VERIFY=false bo'lsa AI API uchun sertifikat tekshiruvi o'chiriladi
    AI_SSL_VERIFY: bool = os.getenv("AI_SSL_VERIFY", "true").strip().lower() not in ("0", "false", "no")

settings = Settings()

