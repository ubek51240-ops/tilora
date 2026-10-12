import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import ApiKey, User
from app.core.deps import get_current_user, require_role
from app.core.security import create_access_token

router = APIRouter(prefix="/keys", tags=["API Kalitlari (API Keys)"])


class CreateApiKeyRequest(BaseModel):
    name: str
    role: Optional[str] = "developer"
    target_user_id: Optional[str] = None
    expires_days: Optional[int] = 90
    rate_limit: Optional[int] = 120


class TokenExchangeRequest(BaseModel):
    api_key: str


# ============================================================
# 1. API KALITLARINI OLISH (LIST API KEYS)
# ============================================================
@router.get("")
def list_api_keys(
    my_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["developer", "admin"]))
):
    """
    Dasturchi va Super Admin uchun API kalitlarini ko'rish:
    - developer: faqat o'zi yaratgan kalitlarni ko'radi.
    - admin: barcha kalitlarni yoki o'zinikini ko'radi.
    """
    user_id = current_user.get("id")
    user_role = current_user.get("role")

    query = db.query(ApiKey)
    if user_role != "admin" or my_only:
        query = query.filter(ApiKey.user_id == user_id)

    keys = query.order_by(ApiKey.created_at.desc()).all()

    users_map = {
        u.id: {"full_name": u.full_name, "email": u.email, "role": u.role}
        for u in db.query(User).all()
    }

    result = []
    for k in keys:
        u_info = users_map.get(k.user_id, {"full_name": "Noma'lum", "email": "", "role": ""})
        is_expired = bool(k.expires_at and k.expires_at < datetime.utcnow())
        
        result.append({
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "role": k.role,
            "user_id": k.user_id,
            "user_name": u_info["full_name"],
            "user_email": u_info["email"],
            "is_active": k.is_active and not is_expired,
            "is_expired": is_expired,
            "rate_limit": k.rate_limit,
            "created_at": k.created_at.strftime("%Y-%m-%d %H:%M") if k.created_at else "",
            "last_used_at": k.last_used_at.strftime("%Y-%m-%d %H:%M") if k.last_used_at else "Hali ishlatilmagan",
            "expires_at": k.expires_at.strftime("%Y-%m-%d %H:%M") if k.expires_at else "Muddatsiz",
            "is_mine": (k.user_id == user_id)
        })

    return {
        "status": "success",
        "current_user_role": user_role,
        "total": len(result),
        "keys": result
    }


# ============================================================
# 2. YANGI API KALIT YARATISH (CREATE API KEY)
# ============================================================
@router.post("", status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: CreateApiKeyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["developer", "admin"]))
):
    """
    Yangi xavfsiz API kalit generatsiya qilish:
    - developer: o'z hisobiga 'developer' roli bilan kalit ochadi.
    - admin: o'ziga yoki istalgan dasturchi/foydalanuvchiga kalit generatsiya qila oladi.
    Kalit xavfsiz SHA-256 xeshi bilan saqlanadi va to'liq maxfiy kalit faqat bir marta qaytariladi.
    """
    user_id = current_user.get("id")
    user_role = current_user.get("role")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="API kalit nomini kiriting (masalan: Mobil ilova).")

    # Egasi kim bo'lishini aniqlash
    target_user_id = user_id
    assigned_role = "developer"

    if user_role == "admin":
        if payload.target_user_id:
            target_user = db.query(User).filter(User.id == payload.target_user_id).first()
            if not target_user:
                raise HTTPException(status_code=404, detail="Ko'rsatilgan foydalanuvchi topilmadi.")
            target_user_id = target_user.id
            assigned_role = payload.role if payload.role in ["developer", "admin", "teacher"] else target_user.role
        else:
            assigned_role = payload.role if payload.role in ["developer", "admin"] else "admin"

    # Xavfsiz sirli kalit generatsiyasi (32 bayt hex)
    raw_key = f"tilora_sk_live_{secrets.token_hex(20)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    key_prefix = f"tilora_sk_••••{raw_key[-4:]}"

    expires_at = None
    if payload.expires_days and payload.expires_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=payload.expires_days)

    new_key = ApiKey(
        user_id=target_user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        role=assigned_role,
        is_active=True,
        rate_limit=payload.rate_limit or 120,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )

    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    target_user = db.query(User).filter(User.id == target_user_id).first()

    return {
        "status": "success",
        "message": "Yangi API kalit muvaffaqiyatli yaratildi. Diqqat: Maxfiy kalit faqat bir marta ko'rsatiladi, uni xavfsiz joyga saqlab oling!",
        "key": {
            "id": new_key.id,
            "name": new_key.name,
            "api_key": raw_key,  # Faqat shu javobda ochiq qaytariladi!
            "key_prefix": new_key.key_prefix,
            "role": new_key.role,
            "rate_limit": new_key.rate_limit,
            "user_id": target_user_id,
            "user_name": target_user.full_name if target_user else "",
            "user_email": target_user.email if target_user else "",
            "created_at": new_key.created_at.strftime("%Y-%m-%d %H:%M"),
            "expires_at": new_key.expires_at.strftime("%Y-%m-%d %H:%M") if new_key.expires_at else "Muddatsiz"
        }
    }


# ============================================================
# 3. KALITNI BEKOR QILISH VA FAOL ETISH (REVOKE / ACTIVATE)
# ============================================================
@router.post("/{key_id}/revoke")
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["developer", "admin"]))
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API kalit topilmadi.")

    if current_user.get("role") != "admin" and key.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Siz faqat o'zingizning API kalitingizni bekor qila olasiz.")

    key.is_active = False
    db.commit()

    return {
        "status": "success",
        "message": f"'{key.name}' API kaliti bekor qilindi. Endi u orqali tizimga kirib bo'lmaydi."
    }


@router.post("/{key_id}/activate")
def activate_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["developer", "admin"]))
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API kalit topilmadi.")

    if current_user.get("role") != "admin" and key.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Siz faqat o'zingizning API kalitingizni faollashtira olasiz.")

    key.is_active = True
    db.commit()

    return {
        "status": "success",
        "message": f"'{key.name}' API kaliti qayta faollashtirildi."
    }


@router.delete("/{key_id}")
def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["developer", "admin"]))
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API kalit topilmadi.")

    if current_user.get("role") != "admin" and key.user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Siz faqat o'zingizning API kalitingizni o'chira olasiz.")

    db.delete(key)
    db.commit()

    return {
        "status": "success",
        "message": f"'{key.name}' API kaliti butunlay o'chirildi."
    }


# ============================================================
# 4. API KALITNI JWT TOKENGA ALMASHTIRISH (KEY TO JWT TOKEN)
# ============================================================
@router.post("/token")
def exchange_key_for_token(
    payload: TokenExchangeRequest,
    db: Session = Depends(get_db)
):
    """
    Dasturiy vositalar (masalan, Postman yoki avtomatlashtirilgan skriptlar) uchun:
    API kalitni taqdim etib, unga mos keluvchi vaqtinchalik JWT Bearer token olish.
    """
    raw_key = payload.api_key.strip()
    if not raw_key:
        raise HTTPException(status_code=400, detail="API kalitni kiriting.")

    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key_obj = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

    if not api_key_obj or not api_key_obj.is_active:
        raise HTTPException(status_code=401, detail="Yaroqsiz yoki bekor qilingan API kalit.")

    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API kalitning amal qilish muddati tugagan.")

    user = db.query(User).filter(User.id == api_key_obj.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Foydalanuvchi hisobi faol emas.")

    api_key_obj.last_used_at = datetime.utcnow()
    db.commit()

    # JWT Access Token yaratish
    token_data = {
        "id": user.id,
        "email": user.email,
        "role": api_key_obj.role or user.role,
        "full_name": user.full_name,
        "institution_id": user.institution_id,
        "group_id": user.group_id,
        "api_key_id": api_key_obj.id,
        "auth_type": "api_key_exchange"
    }

    token = create_access_token(token_data)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600 * 24,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": api_key_obj.role or user.role
        }
    }


# ============================================================
# 5. DASTURCHILAR RO'YXATI (ADMIN UCHUN)
# ============================================================
@router.get("/developers-list")
def get_developers_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin"]))
):
    """
    Super Admin boshqa foydalanuvchiga yoki dasturchiga API kalit chiqarishida tanlashi uchun.
    """
    users = db.query(User).order_by(User.full_name).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "role_label": "Dasturchi (Developer)" if u.role == "developer" else (
                "Super Admin" if u.role == "admin" else ("O'qituvchi" if u.role == "teacher" else "Talaba")
            )
        }
        for u in users
    ]
