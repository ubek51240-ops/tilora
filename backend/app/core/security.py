"""
Parol xeshlash va JWT token.

Parol formati (yangi): ``pbkdf2_sha256$<iteratsiya>$<tuz_hex>$<xesh_hex>``
  - har bir foydalanuvchi uchun alohida tasodifiy tuz (16 bayt);
  - 600 000 iteratsiya (OWASP 2023 tavsiyasi).
Eski format (64 ta hex belgi, umumiy statik tuz) faqat tekshirish uchun qo'llab-quvvatlanadi
va foydalanuvchi muvaffaqiyatli kirganda avtomatik yangi formatga o'tkaziladi (``needs_rehash``).
"""
import hashlib
import hmac
import base64
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.config import settings

PBKDF2_ITERATIONS = 600_000
_LEGACY_SALT = "tilora_salt_2026"
_LEGACY_ITERATIONS = 100_000


def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str) -> str:
    """Xavfsiz parol xeshlash (PBKDF2-HMAC-SHA256, foydalanuvchiga xos tuz)."""
    salt = secrets.token_bytes(16)
    key = _pbkdf2(password, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${key.hex()}"


def _is_legacy_hash(hashed: str) -> bool:
    return len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed.lower())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolni tekshirish (doimiy vaqtli taqqoslash)."""
    if not plain_password or not hashed_password:
        return False
    try:
        if hashed_password.startswith("pbkdf2_sha256$"):
            _, iters, salt_hex, key_hex = hashed_password.split("$", 3)
            computed = _pbkdf2(plain_password, bytes.fromhex(salt_hex), int(iters))
            return hmac.compare_digest(computed, bytes.fromhex(key_hex))
        if _is_legacy_hash(hashed_password):
            computed = _pbkdf2(plain_password, _LEGACY_SALT.encode("utf-8"), _LEGACY_ITERATIONS)
            return hmac.compare_digest(computed.hex(), hashed_password.lower())
    except (ValueError, TypeError):
        return False
    return False


def needs_rehash(hashed_password: str) -> bool:
    """Eski formatdagi yoki kam iteratsiyali xeshni yangilash kerakmi."""
    if not hashed_password or not hashed_password.startswith("pbkdf2_sha256$"):
        return True
    try:
        iters = int(hashed_password.split("$", 2)[1])
        return iters < PBKDF2_ITERATIONS
    except (ValueError, IndexError):
        return True


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """HS256 bilan imzolangan JWT (iat, exp, jti bilan)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"iat": int(now.timestamp()), "exp": int(expire.timestamp()), "jti": secrets.token_hex(8)})
    header = {"alg": "HS256", "typ": "JWT"}

    h_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = _b64url(json.dumps(to_encode, separators=(",", ":")).encode())
    message = f"{h_b64}.{p_b64}"
    signature = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return f"{message}.{_b64url(signature)}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Imzoni, algoritmni va amal qilish muddatini tekshirib tokenni ochish."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts
        header = json.loads(_b64url_decode(h_b64).decode())
        if header.get("alg") != "HS256":
            return None  # "none" yoki boshqa algoritm qabul qilinmaydi

        message = f"{h_b64}.{p_b64}"
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        actual_sig = _b64url_decode(s_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(p_b64).decode())
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)) or exp < int(time.time()):
            return None
        return payload
    except Exception:
        return None
