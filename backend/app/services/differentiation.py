"""
Tabaqalashtirish (dissertatsiya 3.3): guruh uch o'lchovli profil asosida shartli kichik guruhlarga
ajratiladi va har biri uchun topshiriq varianti belgilanadi. Ajratish talabaga "qobiliyat darajasi"
sifatida emas, "o'quv yo'lining varianti" sifatida taqdim etiladi.

Variantlar:  A — kengaytirilgan (yuqori daraja, ko'maksiz),  B — asosiy (o'rta, qisman ko'mak),
             C — tayanchli (quyi daraja, to'liq ko'mak).
Qoida: tizim faqat TAKLIF qiladi; o'qituvchi TaskVariantAssignment orqali o'zgartira oladi (3-qoida).
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.entities import StudentProfile, TaskVariantAssignment, User

CEFR_W = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
VARIANT_LABELS = {
    "A": {"name": "A — Kengaytirilgan variant", "scaffold": "none", "desc": "Yuqori daraja: ko'maksiz, murakkab topshiriq, tanqidiy tahlil talab qilinadi."},
    "B": {"name": "B — Asosiy variant", "scaffold": "partial", "desc": "O'rta daraja: qisman ko'mak (lug'at), standart hajm."},
    "C": {"name": "C — Tayanchli variant", "scaffold": "full", "desc": "Quyi daraja: to'liq ko'mak (namuna, tuzilma, lug'at), kichik hajm, xavfsiz muhit."},
}


def latest_profile(db: Session, student_id: str) -> Optional[StudentProfile]:
    return db.query(StudentProfile).filter(StudentProfile.student_id == student_id).order_by(StudentProfile.valid_from.desc()).first()


def level_score(profile: Optional[StudentProfile]) -> float:
    if not profile:
        return 3.0
    vals = [CEFR_W.get(x, 3) for x in (profile.cefr_listening, profile.cefr_reading, profile.cefr_speaking, profile.cefr_writing)]
    return sum(vals) / len(vals)


def system_variant(profile: Optional[StudentProfile]) -> Dict[str, Any]:
    """Uch o'lchov bo'yicha tizim taklifi (sabab bilan — 2-qoida)."""
    lvl = level_score(profile)
    anxiety = profile.anxiety_level if profile else 70
    autonomy = profile.autonomy_readiness if profile else 40
    load = profile.load_capacity if profile else 50
    if lvl >= 3.8 and autonomy >= 50:
        v = "A"
    elif lvl >= 2.8:
        v = "B"
    else:
        v = "C"
    # Affektiv tuzatish: tashvish juda yuqori bo'lsa bir pog'ona ko'proq ko'mak
    adjusted = False
    if anxiety > 75 and v == "A":
        v, adjusted = "B", True
    elif anxiety > 75 and v == "B" and load < 40:
        v, adjusted = "C", True
    reason = (f"CEFR o'rtacha og'irligi {lvl:.1f}/6, mustaqillik {autonomy}/100, tashvish {anxiety}/100, yuklama sig'imi {load}/100. "
              + ("Tashvish yuqori bo'lgani uchun ko'mak darajasi bir pog'ona oshirildi. " if adjusted else "")
              + f"Taklif: {VARIANT_LABELS[v]['name']} ({VARIANT_LABELS[v]['desc']})")
    return {"variant": v, "scaffold": VARIANT_LABELS[v]["scaffold"], "reason": reason, "level_score": round(lvl, 2),
            "anxiety": anxiety, "autonomy": autonomy, "load": load}


def effective_variant(db: Session, student_id: str) -> Dict[str, Any]:
    """O'qituvchi biriktirgan variant ustuvor; bo'lmasa tizim taklifi."""
    prof = latest_profile(db, student_id)
    sysv = system_variant(prof)
    assign = db.query(TaskVariantAssignment).filter(TaskVariantAssignment.student_id == student_id).order_by(TaskVariantAssignment.created_at.desc()).first()
    if assign:
        return {**sysv, "variant": assign.variant, "scaffold": VARIANT_LABELS.get(assign.variant, VARIANT_LABELS["B"])["scaffold"],
                "source": "teacher", "teacher_note": assign.note or "", "system_suggestion": sysv["variant"],
                "reason": f"O'qituvchi tomonidan belgilangan ({VARIANT_LABELS.get(assign.variant, {}).get('name', assign.variant)}). " + (assign.note or "")}
    return {**sysv, "source": "system", "teacher_note": "", "system_suggestion": sysv["variant"]}


def group_differentiation(db: Session, students: List[User]) -> Dict[str, Any]:
    subgroups: Dict[str, List[Dict[str, Any]]] = {"A": [], "B": [], "C": []}
    for s in students:
        ev = effective_variant(db, s.id)
        prof = latest_profile(db, s.id)
        subgroups[ev["variant"]].append({
            "id": s.id, "full_name": s.full_name, "email": s.email,
            "variant": ev["variant"], "source": ev["source"], "system_suggestion": ev["system_suggestion"], "reason": ev["reason"],
            "cefr": {"listening": prof.cefr_listening, "reading": prof.cefr_reading, "speaking": prof.cefr_speaking, "writing": prof.cefr_writing} if prof else None,
            "anxiety": ev["anxiety"], "autonomy": ev["autonomy"], "load": ev["load"], "level_score": ev["level_score"],
        })
    return {"subgroups": subgroups, "labels": VARIANT_LABELS,
            "counts": {k: len(v) for k, v in subgroups.items()},
            "rule_note": "Tizim variantni taklif qiladi (sabab bilan); yakuniy biriktirish o'qituvchida (3-qoida). Kamida uch xil variant mavjud (tabaqalashtirish ko'rsatkichi)."}
