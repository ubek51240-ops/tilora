"""
Tajriba butunligi (4.1) va AI'siz nazorat oynasi.

- Nazorat guruhi (experiment_arm = control) talabasiga adaptiv yo'l, metakognitiv blok va AI ko'mak
  ko'rsatilmaydi — u an'anaviy metodika bo'yicha o'qitiladi (403 CONTROL_GROUP_RESTRICTED).
- Nazorat oynasi (group.assessment_window != none) ochiq bo'lsa, guruhning barcha talabalari uchun
  AI vositalari yopiladi: "yakuniy nazorat shakllari texnologik vositalardan foydalanmasdan bajariladi".
"""
from typing import Optional
from fastapi import Depends, status
from app.core.errors import TiloraException
from app.core.deps import get_current_user

ADAPTIVE_FEATURES = {"adaptive_path", "metacognitive_block", "ai_scaffold", "differentiation", "dialog", "alternative"}


def check_experiment_access(user_arm: str, feature: str):
    """Nazorat guruhidagi talabaga adaptiv yo'l, metakognitiv blok va AI ko'mak ko'rsatilmaydi."""
    if user_arm == "control" and feature in ADAPTIVE_FEATURES:
        raise TiloraException(
            code="CONTROL_GROUP_RESTRICTED",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"experiment_arm": "control", "feature": feature,
                     "note": "Nazorat guruhi an'anaviy metodika bo'yicha o'qitiladi; bu funksiya tajriba guruhi uchun."}
        )
    return True


def check_assessment_window(user: dict, feature: str = "ai"):
    """Nazorat oynasi ochiq bo'lsa AI vositalari (va ko'mak) yopiq."""
    win = (user or {}).get("assessment_window") or "none"
    if (user or {}).get("role") == "student" and win != "none":
        raise TiloraException(
            code="ASSESSMENT_WINDOW",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"assessment_window": win, "feature": feature,
                     "note": f"Guruhingizda '{win}' nazorat o'tkazilmoqda: nazorat texnologik vositalarsiz bajariladi."}
        )
    return True


def experimental_only(feature: str):
    """FastAPI dependency: faqat tajriba guruhi (yoki o'qituvchi/admin) uchun; nazorat oynasida ham yopiq."""
    async def _dep(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") == "student":
            check_experiment_access(current_user.get("experiment_arm") or "none", feature)
            if feature in ("ai_scaffold", "dialog", "alternative"):
                check_assessment_window(current_user, feature)
        return current_user
    return _dep


def ai_allowed(current_user: dict = Depends(get_current_user)) -> dict:
    """AI endpointlari uchun: nazorat guruhi va nazorat oynasi cheklovi."""
    if current_user.get("role") == "student":
        check_experiment_access(current_user.get("experiment_arm") or "none", "ai_scaffold")
        check_assessment_window(current_user, "ai")
    return current_user
