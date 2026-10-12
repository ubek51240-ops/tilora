import hashlib
import hmac
import base64
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings

def hash_password(password: str) -> str:
    """Xavfsiz parol xeshlash (PBKDF2-HMAC-SHA256)."""
    salt = "tilora_salt_2026"
    pwd_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    key = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
    return key.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolni tekshirish."""
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT o'xshash xavfsiz imzolangan token yaratish."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": int(expire.timestamp())})
    header = {"alg": "HS256", "typ": "JWT"}
    
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
    
    message = f"{h_b64}.{p_b64}"
    signature = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{message}.{s_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Imzoni va amal qilish muddatini tekshirib tokenni ochish."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, s_b64 = parts
        message = f"{h_b64}.{p_b64}"
        
        # Qayta imzolab solishtirish
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(s_b64 + "==")
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload_bytes = base64.urlsafe_b64decode(p_b64 + "==")
        payload = json.loads(payload_bytes.decode())
        
        # Expire vaqtini tekshirish
        if payload.get("exp") and payload["exp"] < int(time.time()):
            return None
            
        return payload
    except Exception:
        return None
