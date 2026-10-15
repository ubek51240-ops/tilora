"""
O'qituvchi kuzatuv paneli (dissertatsiya 3.3: "O'qituvchi paneli guruh va alohida talaba bo'yicha ma'lumotni
ko'rsatadi hamda topshiriq variantini o'zgartirish imkonini beradi"; 4.1: kuzatuv varaqasi — jarayon ko'rsatkichlari).

- Guruh talabalari: uch o'lchovli profil, pre/post, variant (A/B/C), mashg'ulot statistikasi;
- Tabaqalashtirish: tizim taklifi + o'qituvchi biriktirishi (3-qoida);
- Profilni qo'lda tuzatish (teacher_override) — sabab bilan;
- Talaba mashg'ulot yozuvlari va izohni jarayon/o'zini boshqarish darajasiga ko'tarish (Hattie & Timperley);
- Kuzatuv varaqasi: sur'at, yordam so'rovlari, o'z-o'zini tekshirish, takrorlanuvchi L1 xatolar, o'z bahosi aniqligi.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.entities import User, Group, StudentProfile, Assessment, LessonRecord, TaskVariantAssignment
from app.services.differentiation import group_differentiation, effective_variant, latest_profile, VARIANT_LABELS, system_variant
from app.services import statistics as st
from app.api.lesson import _record_dict

router = APIRouter(prefix="/teacher/panel", tags=["O'qituvchi"], dependencies=[Depends(require_role(["teacher", "admin"]))])

VALID_CEFR = {"A1", "A2", "B1", "B2", "C1", "C2"}


class VariantIn(BaseModel):
    variant: str = Field(..., pattern="^(A|B|C)$")
    note: Optional[str] = Field("", max_length=500)


class ProfileOverrideIn(BaseModel):
    cefr_listening: Optional[str] = None
    cefr_reading: Optional[str] = None
    cefr_speaking: Optional[str] = None
    cefr_writing: Optional[str] = None
    anxiety_level: Optional[int] = Field(None, ge=0, le=100)
    load_capacity: Optional[int] = Field(None, ge=0, le=100)
    pace_index: Optional[int] = Field(None, ge=0, le=100)
    autonomy_readiness: Optional[int] = Field(None, ge=0, le=100)
    note: str = Field(..., min_length=3, max_length=500)  # 2-qoida: o'zgartirish sababi majburiy


class ExtendIn(BaseModel):
    teacher_extension: str = Field(..., min_length=3, max_length=2000)


def _tid(u: dict) -> str:
    return u.get("id") or u.get("sub")


def _can_see_group(db: Session, user: dict, group: Group) -> bool:
    if user.get("role") == "admin":
        return True
    tid = _tid(user)
    if group.teacher_id == tid:
        return True
    # O'qituvchi fanlari guruh nomi bilan mos kelsa ham ko'ra oladi (materials.student_subject_scope mantiqi)
    from app.services.materials import _group_token
    from app.models.entities import TeacherSubject
    tok = _group_token(group.name)
    return any(_group_token(s.group_name) == tok for s in db.query(TeacherSubject).filter(TeacherSubject.teacher_id == tid).all()) if tok else False


def _student_for(db: Session, user: dict, student_id: str) -> User:
    s = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not s:
        raise HTTPException(status_code=404, detail="Talaba topilmadi.")
    if user.get("role") != "admin":
        g = db.query(Group).filter(Group.id == s.group_id).first() if s.group_id else None
        if not g or not _can_see_group(db, user, g):
            raise HTTPException(status_code=403, detail="Bu talaba sizning guruhingizda emas.")
    return s


def _assess(db: Session, sid: str) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for a in db.query(Assessment).filter(Assessment.student_id == sid).order_by(Assessment.administered_at.asc()).all():
        out.setdefault(a.assessment_type, {})[a.skill] = a.score
    return out


@router.get("/groups")
def panel_groups(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """O'qituvchi ko'ra oladigan guruhlar (talabalar soni, tajriba qanoti, mashg'ulot yozuvlari)."""
    out = []
    for g in db.query(Group).all():
        if not _can_see_group(db, current_user, g):
            continue
        n = db.query(User).filter(User.group_id == g.id, User.role == "student", User.is_approved == True).count()
        out.append({"id": g.id, "name": g.name, "arm": g.experiment_arm, "course_year": g.course_year, "students_count": n,
                    "records": db.query(LessonRecord).filter(LessonRecord.group_id == g.id).count(), "is_mine": g.teacher_id == _tid(current_user)})
    return {"groups": out}


@router.get("/groups/{group_id}/students")
def panel_students(group_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Guruh talabalari: uch o'lchovli profil, variant, pre/post, mashg'ulot statistikasi."""
    g = db.query(Group).filter(Group.id == group_id).first()
    if not g or not _can_see_group(db, current_user, g):
        raise HTTPException(status_code=404, detail="Guruh topilmadi yoki ruxsat yo'q.")
    students = db.query(User).filter(User.group_id == group_id, User.role == "student", User.is_approved == True).order_by(User.full_name).all()
    out = []
    for s in students:
        prof = latest_profile(db, s.id)
        ev = effective_variant(db, s.id)
        recs = db.query(LessonRecord).filter(LessonRecord.student_id == s.id).order_by(LessonRecord.created_at.desc()).all()
        scores = [r.score for r in recs if r.score is not None]
        a = _assess(db, s.id)
        out.append({
            "id": s.id, "full_name": s.full_name, "email": s.email,
            "profile": {"cefr": {"listening": prof.cefr_listening, "reading": prof.cefr_reading, "speaking": prof.cefr_speaking, "writing": prof.cefr_writing},
                        "anxiety_level": prof.anxiety_level, "load_capacity": prof.load_capacity, "pace_index": prof.pace_index,
                        "autonomy_readiness": prof.autonomy_readiness, "source": prof.source,
                        "valid_from": prof.valid_from.strftime("%Y-%m-%d") if prof.valid_from else ""} if prof else None,
            "variant": ev["variant"], "variant_source": ev["source"], "system_suggestion": ev["system_suggestion"], "variant_reason": ev["reason"],
            "assessments": a,
            "lessons": {"count": len(recs), "avg_score": round(st.mean(scores), 1) if scores else None,
                        "last": recs[0].created_at.strftime("%Y-%m-%d") if recs else None,
                        "avg_rating_gap": round(st.mean([r.rating_gap for r in recs if r.rating_gap is not None]), 2) if any(r.rating_gap is not None for r in recs) else None,
                        "help_requests": sum(r.help_requests or 0 for r in recs)},
        })
    return {"group": {"id": g.id, "name": g.name, "arm": g.experiment_arm}, "students": out, "total": len(out)}


@router.get("/groups/{group_id}/differentiation")
def panel_differentiation(group_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Tabaqalashtirish: guruhni profil bo'yicha A/B/C kichik guruhlarga ajratish (tizim taklifi + o'qituvchi qarori)."""
    g = db.query(Group).filter(Group.id == group_id).first()
    if not g or not _can_see_group(db, current_user, g):
        raise HTTPException(status_code=404, detail="Guruh topilmadi yoki ruxsat yo'q.")
    students = db.query(User).filter(User.group_id == group_id, User.role == "student", User.is_approved == True).order_by(User.full_name).all()
    return {"group": {"id": g.id, "name": g.name}, **group_differentiation(db, students)}


@router.post("/students/{student_id}/variant")
def set_variant(student_id: str, payload: VariantIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """3-qoida: o'qituvchi topshiriq variantini biriktiradi (tizim taklifini o'zgartiradi)."""
    _student_for(db, current_user, student_id)
    db.add(TaskVariantAssignment(student_id=student_id, teacher_id=_tid(current_user), variant=payload.variant, note=(payload.note or "").strip(), source="teacher"))
    db.commit()
    return {"status": "success", "message": f"Talabaga {VARIANT_LABELS[payload.variant]['name']} biriktirildi.", "effective": effective_variant(db, student_id)}


@router.delete("/students/{student_id}/variant")
def clear_variant(student_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """O'qituvchi biriktiruvini bekor qilish — tizim taklifiga qaytish."""
    _student_for(db, current_user, student_id)
    db.query(TaskVariantAssignment).filter(TaskVariantAssignment.student_id == student_id).delete()
    db.commit()
    return {"status": "success", "effective": effective_variant(db, student_id)}


@router.post("/students/{student_id}/profile-override")
def override_profile(student_id: str, payload: ProfileOverrideIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """O'qituvchi profilni qo'lda tuzatadi (source=teacher_override); tarix saqlanadi — eski qator o'chirilmaydi."""
    _student_for(db, current_user, student_id)
    prev = latest_profile(db, student_id)
    for k in ("cefr_listening", "cefr_reading", "cefr_speaking", "cefr_writing"):
        v = getattr(payload, k)
        if v is not None and v.upper() not in VALID_CEFR:
            raise HTTPException(status_code=400, detail=f"{k}: noto'g'ri CEFR daraja '{v}'.")
    new = StudentProfile(
        student_id=student_id,
        cefr_listening=(payload.cefr_listening or (prev.cefr_listening if prev else "B1")).upper(),
        cefr_reading=(payload.cefr_reading or (prev.cefr_reading if prev else "B1")).upper(),
        cefr_speaking=(payload.cefr_speaking or (prev.cefr_speaking if prev else "A2")).upper(),
        cefr_writing=(payload.cefr_writing or (prev.cefr_writing if prev else "B1")).upper(),
        anxiety_level=payload.anxiety_level if payload.anxiety_level is not None else (prev.anxiety_level if prev else 60),
        load_capacity=payload.load_capacity if payload.load_capacity is not None else (prev.load_capacity if prev else 50),
        pace_index=payload.pace_index if payload.pace_index is not None else (prev.pace_index if prev else 50),
        autonomy_readiness=payload.autonomy_readiness if payload.autonomy_readiness is not None else (prev.autonomy_readiness if prev else 40),
        professional_track=prev.professional_track if prev else "Filologiya va tillarni o'qitish (ingliz tili)",
        source="teacher_override", valid_from=datetime.utcnow(),
    )
    db.add(new)
    db.commit()
    sysv = system_variant(new)
    return {"status": "success", "message": "Profil o'qituvchi tomonidan yangilandi (tarix saqlandi).", "note": payload.note,
            "profile": {"cefr": {"listening": new.cefr_listening, "reading": new.cefr_reading, "speaking": new.cefr_speaking, "writing": new.cefr_writing},
                        "anxiety_level": new.anxiety_level, "load_capacity": new.load_capacity, "pace_index": new.pace_index, "autonomy_readiness": new.autonomy_readiness},
            "system_variant": sysv}


@router.get("/students/{student_id}/records")
def student_records(student_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Talabaning mashg'ulot yozuvlari (matn bilan), profil tarixi va pre/post baholari."""
    s = _student_for(db, current_user, student_id)
    recs = db.query(LessonRecord).filter(LessonRecord.student_id == student_id).order_by(LessonRecord.created_at.desc()).all()
    profiles = db.query(StudentProfile).filter(StudentProfile.student_id == student_id).order_by(StudentProfile.valid_from.desc()).limit(10).all()
    return {
        "student": {"id": s.id, "full_name": s.full_name, "email": s.email},
        "records": [_record_dict(r, with_text=True) for r in recs],
        "profile_history": [{"source": p.source, "valid_from": p.valid_from.strftime("%Y-%m-%d %H:%M") if p.valid_from else "",
                             "cefr": {"listening": p.cefr_listening, "reading": p.cefr_reading, "speaking": p.cefr_speaking, "writing": p.cefr_writing},
                             "anxiety_level": p.anxiety_level, "autonomy_readiness": p.autonomy_readiness} for p in profiles],
        "assessments": _assess(db, student_id),
        "variant": effective_variant(db, student_id),
    }


@router.post("/records/{record_id}/extend")
def extend_feedback(record_id: str, payload: ExtendIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Hattie & Timperley: texnologiya 'vazifa' darajasida izoh beradi, o'qituvchi uni 'jarayon' va 'o'zini boshqarish' darajasiga ko'taradi."""
    r = db.query(LessonRecord).filter(LessonRecord.id == record_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Yozuv topilmadi.")
    _student_for(db, current_user, r.student_id)
    r.teacher_extension = payload.teacher_extension.strip()
    r.teacher_id = _tid(current_user)
    db.commit()
    return {"status": "success", "record": _record_dict(r)}


@router.get("/observation/export")
def observation_export(group_id: Optional[str] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Kuzatuv varaqasini Excel (.xlsx) ga eksport qilish (dissertatsiya ilovasi uchun)."""
    import io
    import openpyxl
    from fastapi.responses import StreamingResponse
    data = observation_sheet(group_id, db, current_user)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Kuzatuv varaqasi"
    ws.append(["Talaba", "Mashg'ulotlar", "Birinchi ball", "Oxirgi ball", "O'rtacha", "Dinamika", "Mustaqil bosqich (daq)", "O'rtacha so'z",
               "Yordam so'rovlari", "O'z-o'zini tekshirish", "O'z bahosi farqi", "Izohni qabul ulushi", "Takrorlanuvchi L1", "Variantlar", "Oxirgi"])
    for r in data["rows"]:
        ws.append([r["full_name"], r["records"], r.get("first_score"), r.get("last_score"), r.get("avg_score"), r.get("trend"),
                   r.get("avg_independent_minutes"), r.get("avg_words"), r.get("help_requests"), r.get("self_checks"), r.get("avg_rating_gap"),
                   r.get("feedback_accept_rate"), ", ".join(f"{x['pattern_id']}×{x['count']}" for x in r.get("recurring_l1", [])),
                   ", ".join(r.get("variants", [])), r.get("last")])
    ws2 = wb.create_sheet("Izoh"); ws2.append(["Ko'rsatkich", "Ma'nosi"])
    for k, v in data["legend"].items():
        ws2.append([k, v])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=TILORA_kuzatuv_varaqasi.xlsx"})


@router.get("/observation")
def observation_sheet(group_id: Optional[str] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Kuzatuv varaqasi (4.1): har talaba bo'yicha jarayon ko'rsatkichlari — sur'at, yordam so'rovlari, o'z-o'zini tekshirish,
    takrorlanuvchi L1 xatolar, o'z bahosi aniqligi (rating_gap), izohlarni qabul qilish ulushi."""
    q = db.query(User).filter(User.role == "student", User.is_approved == True)
    if group_id:
        g = db.query(Group).filter(Group.id == group_id).first()
        if not g or not _can_see_group(db, current_user, g):
            raise HTTPException(status_code=404, detail="Guruh topilmadi yoki ruxsat yo'q.")
        q = q.filter(User.group_id == group_id)
    elif current_user.get("role") != "admin":
        visible = [g.id for g in db.query(Group).all() if _can_see_group(db, current_user, g)]
        q = q.filter(User.group_id.in_(visible)) if visible else q.filter(User.id == "__none__")
    rows = []
    for s in q.order_by(User.full_name).all():
        recs = db.query(LessonRecord).filter(LessonRecord.student_id == s.id).order_by(LessonRecord.created_at.asc()).all()
        if not recs:
            rows.append({"id": s.id, "full_name": s.full_name, "records": 0}); continue
        pat: Dict[str, int] = {}
        for r in recs:
            for pid in (r.l1_pattern_ids or []):
                pat[pid] = pat.get(pid, 0) + 1
        acc = tot = 0
        for r in recs:
            for d in (r.feedback_decisions or []):
                tot += 1; acc += 1 if d.get("accepts") else 0
        scores = [r.score for r in recs if r.score is not None]
        rows.append({
            "id": s.id, "full_name": s.full_name, "records": len(recs),
            "first_score": scores[0] if scores else None, "last_score": scores[-1] if scores else None,
            "avg_score": round(st.mean(scores), 1) if scores else None,
            "trend": (scores[-1] - scores[0]) if len(scores) >= 2 else None,
            "avg_independent_minutes": round(st.mean([r.independent_seconds or 0 for r in recs]) / 60, 1),
            "avg_words": round(st.mean([r.word_count or 0 for r in recs])),
            "help_requests": sum(r.help_requests or 0 for r in recs), "self_checks": sum(r.self_checks or 0 for r in recs),
            "avg_rating_gap": round(st.mean([r.rating_gap for r in recs if r.rating_gap is not None]), 2) if any(r.rating_gap is not None for r in recs) else None,
            "feedback_accept_rate": round(acc / tot, 2) if tot else None,
            "recurring_l1": [{"pattern_id": k, "count": v} for k, v in sorted(pat.items(), key=lambda x: -x[1]) if v >= 2][:5],
            "variants": sorted({r.task_variant for r in recs if r.task_variant}),
            "last": recs[-1].created_at.strftime("%Y-%m-%d") if recs[-1].created_at else "",
        })
    return {"rows": rows, "total": len(rows),
            "legend": {"avg_rating_gap": "O'z bahosi va tizim bahosi farqi (0 — aniq o'zini baholash)",
                       "help_requests": "Mustaqil bosqichda qulflangan AI ga urinishlar",
                       "recurring_l1": "Ikki va undan ko'p mashg'ulotda takrorlangan ona tili xatosi (fossilizatsiya xavfi)"}}
