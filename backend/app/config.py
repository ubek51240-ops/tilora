import os
import secrets
import warnings
from pydantic import BaseModel

_base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_default_db = f"sqlite:///{os.path.join(_base_dir, 'tilora.db').replace(chr(92), '/')}"


def _load_dotenv() -> None:
    """Loyiha ildizidagi .env faylini (bo'lsa) muhitga yuklaydi; mavjud env qiymatlari ustuvor."""
    path = os.path.join(_base_dir, ".env")
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_dotenv()


def _resolve_secret_key() -> str:
    """
    JWT imzo kaliti:
      1. SECRET_KEY muhit o'zgaruvchisi (production uchun majburiy);
      2. bo'lmasa, loyiha ildizidagi .secret_key faylidan o'qiladi;
      3. u ham bo'lmasa, tasodifiy kalit yaratilib shu faylga yoziladi.
    Kodga yozilgan doimiy kalit ishlatilmaydi (token soxtalashtirish xavfi).
    """
    env_key = os.getenv("SECRET_KEY", "").strip()
    placeholders = {"", "change_this_to_a_random_32_character_secret_string", "generate_random_secret_key_here",
                    "tilora-secret-key-default"}
    if env_key and env_key not in placeholders and len(env_key) >= 32:
        return env_key
    if env_key and env_key in placeholders:
        warnings.warn("SECRET_KEY namunaviy qiymatda qoldirilgan — avtomatik yaratilgan kalit ishlatiladi.")
    key_file = os.path.join(_base_dir, ".secret_key")
    try:
        if os.path.isfile(key_file):
            with open(key_file, "r", encoding="utf-8") as f:
                saved = f.read().strip()
            if len(saved) >= 32:
                return saved
        generated = secrets.token_urlsafe(48)
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(generated)
        return generated
    except OSError:
        # Fayl tizimi yozib bo'lmaydigan joy (masalan, read-only konteyner): vaqtinchalik kalit
        warnings.warn("SECRET_KEY saqlab bo'lmadi — server qayta ishga tushganda sessiyalar tugaydi.")
        return secrets.token_urlsafe(48)


def _resolve_database_url() -> str:
    """DATABASE_URL: SQLite yo'li mavjud bo'lmagan papkaga ko'rsatsa (boshqa kompyuterdan ko'chirilgan .env), standart yo'l."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return _default_db
    if url.startswith("sqlite:///"):
        raw_path = url[len("sqlite:///"):]
        if raw_path and raw_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(raw_path))
            if not os.path.isdir(parent):
                warnings.warn(f"DATABASE_URL papkasi topilmadi ({parent}); standart SQLite bazasi ishlatiladi.")
                return _default_db
    return url


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


class Settings(BaseModel):
    PROJECT_NAME: str = "TILORA Adaptiv Ta'lim Platformasi"
    VERSION: str = "2.2.0"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = _resolve_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 12)))  # 12 soat
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = _resolve_database_url()

    # AI kalitlari faqat muhit o'zgaruvchisidan olinadi; kodda standart kalit yo'q.
    AI_API_KEY: str = os.getenv("AI_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.b.ai/v1")).rstrip("/")
    AI_MODEL: str = os.getenv("AI_MODEL", "deepseek-v4-flash-vision-exp")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    DEFAULT_LOCALE: str = "uz"
    # Faqat oxirgi chora: AI_SSL_VERIFY=false bo'lsa AI API uchun sertifikat tekshiruvi o'chiriladi
    AI_SSL_VERIFY: bool = _env_bool("AI_SSL_VERIFY", True)

    # Xavfsizlik sozlamalari
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    # CORS: vergul bilan ajratilgan ro'yxat; "*" faqat lokal demo uchun (credentials bilan birga ishlatilmaydi)
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")
    DOCS_ENABLED: bool = _env_bool("DOCS_ENABLED", True)
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
    # Login urinishlari: bitta IP/login uchun 15 daqiqada ruxsat etilgan xato urinishlar soni
    LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "10"))
    LOGIN_WINDOW_SECONDS: int = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))
    # AI so'rovlari: bitta foydalanuvchi uchun 10 daqiqada
    AI_MAX_REQUESTS: int = int(os.getenv("AI_MAX_REQUESTS", "60"))
    AI_WINDOW_SECONDS: int = int(os.getenv("AI_WINDOW_SECONDS", "600"))
    # Demo (seed) hisoblar paroli — faqat seed.py uchun
    SEED_PASSWORD: str = os.getenv("SEED_PASSWORD", "tilora2026!")

    @property
    def allowed_origins_list(self):
        raw = (self.ALLOWED_ORIGINS or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
