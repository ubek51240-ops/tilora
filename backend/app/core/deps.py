import hashlib
from datetime import datetime
from typing import Optional, List
from fastapi import Depends, Header, HTTPException, status
from app.core.security import decode_access_token

async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> dict:
    """
    Joriy foydalanuvchini olish (2 ta xavfsiz usul):
    1. HTTP Bearer JWT token: 'Authorization: Bearer <token>'
    2. Dasturchi/Admin API Kaliti: 'X-API-Key: tilora_sk_live_...' yoki 'Authorization: ApiKey <key>'
    """
    raw_api_key = None
    if x_api_key and x_api_key.strip():
        raw_api_key = x_api_key.strip()
    elif authorization and authorization.strip().startswith("ApiKey "):
        raw_api_key = authorization.replace("ApiKey ", "").strip()

    # 1-usul: API Kalit orqali autentifikatsiya
    if raw_api_key:
        from app.database import SessionLocal
        from app.models.entities import ApiKey, User

        key_hash = hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()
        db = SessionLocal()
        try:
            api_key_obj = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
            if not api_key_obj or not api_key_obj.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Yaroqsiz yoki bekor qilingan API kalit (Invalid or revoked API key)."
                )

            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API kalitning amal qilish muddati tugagan (API key has expired)."
                )

            user = db.query(User).filter(User.id == api_key_obj.user_id).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API kalit egasi bo'lgan foydalanuvchi hisobi faol emas."
                )

            # Oxirgi ishlatilgan vaqtni yangilash
            api_key_obj.last_used_at = datetime.utcnow()
            db.commit()

            return {
                "id": user.id,
                "email": user.email,
                "role": api_key_obj.role or user.role,
                "user_role": user.role,
                "full_name": user.full_name,
                "institution_id": user.institution_id,
                "group_id": user.group_id,
                "subscription_tier": getattr(user, "subscription_tier", "pro") or "pro",
                "api_key_id": api_key_obj.id,
                "api_key_name": api_key_obj.name,
                "auth_type": "api_key"
            }
        finally:
            db.close()

    # 2-usul: JWT Bearer token orqali autentifikatsiya
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tizimga kirilmagan. Iltimos, JWT token (Bearer) yoki API kalit (X-API-Key) yuboring."
        )

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentifikatsiya muddati tugagan yoki token yaroqsiz."
        )
    payload["auth_type"] = "jwt"
    return payload

def require_role(allowed_roles: List[str]):
    """Rolni qat'iy tekshirish dependency'si (RBAC)."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Kirish taqiqlangan: Ushbu amal faqat {', '.join(allowed_roles)} rollari uchun ruxsat etilgan. Sizning rolingiz: {user_role}"
            )
        return current_user
    return role_checker

async def get_optional_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[dict]:
    """Token yoki API kalit bo'lsa foydalanuvchini olish, bo'lmasa None qaytarish (mehmon rejimi)."""
    try:
        return await get_current_user(authorization=authorization, x_api_key=x_api_key)
    except HTTPException:
        return None


