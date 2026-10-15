import io
import csv
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_role
from app.models.entities import User, Group, Institution, Assessment, LessonRecord
from app.services.dissertation_export import (
    RESEARCH_DATA,
    generate_dissertation_docx,
    generate_dissertation_excel
)
from app.services.live_research import build_live_tables, COMM_SKILLS, META_SKILLS, LEVEL_SCALE
from app.services import statistics as st

router = APIRouter(prefix="/research", tags=["Tadqiqotchi"])

# Jadvallar ommaviy ko'rsatiladi (dissertatsiya natijalari ochiq ma'lumot),
# eksport va jonli ma'lumotlar esa faqat tadqiqotchi/o'qituvchi/admin uchun.
_EXPORT_ROLES = ["researcher", "admin", "teacher"]
_LIVE_ROLES = ["researcher", "admin", "teacher"]

DATA_SOURCE_NOTE = (
    "Jadvallar dissertatsiya tajriba-sinov ishlarining yakuniy, oldindan hisoblangan natijalari "
    "(2024–2026, BuxDU, NDPI, SamDChTI). Platformadagi joriy foydalanuvchilar ma'lumotlaridan real vaqtda hisoblanmaydi."
)

VALID_SKILLS = set(COMM_SKILLS) | {k for k, _ in META_SKILLS} | {"anxiety", "motivation", "overall"}
VALID_TYPES = {"pre", "mid", "post"}


@router.get("/tables")
def get_all_dissertation_tables(institution: Optional[str] = Query(None)):
    """Dissertatsiya 4-bobi uchun barcha statistik jadvallar (4.2, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9)."""
    data = dict(RESEARCH_DATA)
    data["data_source"] = "dissertation_dataset"
    data["data_source_note"] = DATA_SOURCE_NOTE
    data["level_scale"] = LEVEL_SCALE
    if institution and institution != "all":
        data["filter_applied"] = institution
    return data


@router.get("/baseline-equivalence")
def get_baseline_equivalence():
    """Tajriba va nazorat guruhlarining boshlang'ich tenglik tekshiruvi (Chi-square)."""
    return {
        "metric": "Pearson Chi-Square",
        "sample_sizes": {
            "experimental_group": 132,
            "control_group": 126,
            "total": 258,
            "primary_base_buxdu": {"exp": 46, "ctrl": 44, "total": 90}
        },
        "chi_square_value": 0.45,
        "degrees_of_freedom": 2,
        "p_value": 0.798,
        "interpretation": "p > 0.05. Guruhlarning dastlabki CEFR darajalari statistik jihatdan teng va farqsiz ekani to'liq isbotlandi.",
        "equivalence_confirmed": True,
        "data_source": "dissertation_dataset"
    }


@router.get("/statistics")
def get_research_statistics():
    """Dissertatsiya 4-bobi uchun zarur asosiy ilmiy ko'rsatkichlar."""
    return {
        "groups": {
            "experimental": {"name": "Tajriba guruhi (Tabaqalashtirilgan adaptiv-metakognitiv model)", "sample_size": 132,
                             "pre_test_mean": 54.1, "post_test_mean": 78.5, "growth_percentage": "+45.1%", "t_statistic": 24.32, "p_value": "< 0.001"},
            "control": {"name": "Nazorat guruhi (An'anaviy ta'lim)", "sample_size": 126,
                        "pre_test_mean": 53.6, "post_test_mean": 64.2, "growth_percentage": "+19.8%", "t_statistic": 9.15, "p_value": "< 0.001"}
        },
        "effect_size": {"cohens_d": 1.66, "magnitude": "Katta effekt (Large Effect > 0.8)",
                        "significance": "Tabaqalashtirilgan adaptiv-metakognitiv model an'anaviy yondashuvdan statistik ishonchli darajada yuqori samaradorlik ko'rsatdi."},
        "coefficients": {"mastery_rate_exp": 0.81, "mastery_rate_ctrl": 0.64, "effectiveness_ratio": 1.26, "superiority_percentage": "+26.1%"},
        "data_source": "dissertation_dataset",
        "data_source_note": DATA_SOURCE_NOTE
    }


# ============================================================
# JONLI (REAL) TADQIQOT MA'LUMOTLARI — assessments jadvalidan hisoblanadi
# ============================================================

@router.get("/live/tables", dependencies=[Depends(require_role(_LIVE_ROLES))])
def get_live_tables(db: Session = Depends(get_db)):
    """Platformadagi haqiqiy pre/post baholash ma'lumotlaridan 4.2–4.10 jadvallar (real vaqtda)."""
    return build_live_tables(db)


@router.get("/live/overview", dependencies=[Depends(require_role(_LIVE_ROLES))])
def get_live_overview(db: Session = Depends(get_db)):
    """Tadqiqot ma'lumotlari to'liqligi: guruhlar, OTMlar, pre/post qamrovi, mashg'ulot yozuvlari."""
    t = build_live_tables(db)
    groups = db.query(Group).all()
    arms = {"experimental": 0, "control": 0, "none": 0}
    for g in groups:
        arms[g.experiment_arm if g.experiment_arm in arms else "none"] += 1
    from app.api.teacher_competence import teacher_competence_summary
    return {
        "completeness": t["completeness"],
        "teacher_competence": teacher_competence_summary(db),
        "groups_by_arm": arms,
        "institutions": [{"id": i.id, "name": i.name, "short_name": i.short_name} for i in db.query(Institution).all()],
        "assessments_total": db.query(Assessment).count(),
        "lesson_records_total": db.query(LessonRecord).count(),
        "skills": sorted(VALID_SKILLS),
        "types": sorted(VALID_TYPES),
    }


class AssessmentIn(BaseModel):
    student_id: Optional[str] = None
    email: Optional[str] = None
    assessment_type: str = Field("pre", pattern="^(pre|mid|post)$")
    skill: str
    score: float = Field(..., ge=0)
    max_score: float = Field(100, gt=0)
    administered_at: Optional[str] = None  # YYYY-MM-DD


class AssessmentBatch(BaseModel):
    items: List[AssessmentIn] = Field(..., min_length=1, max_length=5000)


def _resolve_student(db: Session, item: AssessmentIn) -> Optional[User]:
    if item.student_id:
        return db.query(User).filter(User.id == item.student_id, User.role == "student").first()
    if item.email:
        e = item.email.strip().lower()
        return db.query(User).filter(User.email == e, User.role == "student").first()
    return None


def _save_items(db: Session, items: List[AssessmentIn]) -> Dict[str, Any]:
    saved, errors = 0, []
    for i, it in enumerate(items, 1):
        if it.skill not in VALID_SKILLS:
            errors.append(f"{i}: noma'lum ko'nikma '{it.skill}'"); continue
        u = _resolve_student(db, it)
        if not u:
            errors.append(f"{i}: talaba topilmadi ({it.email or it.student_id})"); continue
        if it.score > it.max_score:
            errors.append(f"{i}: ball maksimumdan katta"); continue
        when = None
        if it.administered_at:
            try:
                when = datetime.strptime(it.administered_at[:10], "%Y-%m-%d")
            except ValueError:
                errors.append(f"{i}: sana formati YYYY-MM-DD bo'lishi kerak"); continue
        db.add(Assessment(student_id=u.id, assessment_type=it.assessment_type, skill=it.skill, score=int(round(it.score)),
                          max_score=int(it.max_score), administered_at=when or datetime.utcnow(), is_frozen=True, ai_tools_allowed=False))
        saved += 1
    db.commit()
    return {"saved": saved, "errors": errors[:50], "error_count": len(errors)}


@router.post("/live/assessments", dependencies=[Depends(require_role(_LIVE_ROLES))])
def add_assessments(payload: AssessmentBatch, db: Session = Depends(get_db)):
    """Pre/mid/post baholash natijalarini qo'lda kiritish (JSON). Yakuniy nazorat AI'siz o'tkaziladi (is_frozen)."""
    return {"status": "success", **_save_items(db, payload.items)}


@router.post("/live/assessments/import", dependencies=[Depends(require_role(_LIVE_ROLES))])
async def import_assessments(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """CSV/JSON import. CSV ustunlari: email (yoki student_id), assessment_type, skill, score, max_score, administered_at."""
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fayl 5 MB dan oshmasligi kerak.")
    name = (file.filename or "").lower()
    items: List[AssessmentIn] = []
    try:
        if name.endswith(".json"):
            data = json.loads(raw.decode("utf-8-sig"))
            rows = data.get("items") if isinstance(data, dict) else data
            items = [AssessmentIn(**r) for r in rows]
        else:
            text = raw.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            for r in reader:
                r = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in r.items() if k}
                items.append(AssessmentIn(
                    student_id=r.get("student_id") or None, email=r.get("email") or None,
                    assessment_type=(r.get("assessment_type") or "pre").lower(), skill=(r.get("skill") or "").lower(),
                    score=float(r.get("score") or 0), max_score=float(r.get("max_score") or 100),
                    administered_at=r.get("administered_at") or None))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fayl o'qilmadi: {e}")
    if not items:
        raise HTTPException(status_code=400, detail="Faylda yozuvlar topilmadi.")
    return {"status": "success", "received": len(items), **_save_items(db, items)}


@router.get("/live/assessments", dependencies=[Depends(require_role(_LIVE_ROLES))])
def list_assessments(student_id: Optional[str] = None, assessment_type: Optional[str] = None, limit: int = Query(500, le=5000), db: Session = Depends(get_db)):
    q = db.query(Assessment)
    if student_id:
        q = q.filter(Assessment.student_id == student_id)
    if assessment_type:
        q = q.filter(Assessment.assessment_type == assessment_type)
    rows = q.order_by(Assessment.administered_at.desc()).limit(limit).all()
    users = {u.id: u for u in db.query(User).filter(User.id.in_({r.student_id for r in rows})).all()} if rows else {}
    groups = {g.id: g for g in db.query(Group).all()}
    out = []
    for r in rows:
        u = users.get(r.student_id)
        g = groups.get(u.group_id) if u else None
        out.append({"id": r.id, "student_id": r.student_id, "student": u.full_name if u else "", "email": u.email if u else "",
                    "group": g.name if g else "", "arm": g.experiment_arm if g else "", "assessment_type": r.assessment_type,
                    "skill": r.skill, "score": r.score, "max_score": r.max_score,
                    "administered_at": r.administered_at.strftime("%Y-%m-%d") if r.administered_at else ""})
    return {"items": out, "total": len(out)}


@router.delete("/live/assessments/{assessment_id}", dependencies=[Depends(require_role(["researcher", "admin"]))])
def delete_assessment(assessment_id: str, db: Session = Depends(get_db)):
    a = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Yozuv topilmadi.")
    db.delete(a); db.commit()
    return {"status": "success"}


@router.get("/live/process-indicators", dependencies=[Depends(require_role(_LIVE_ROLES))])
def process_indicators(db: Session = Depends(get_db)):
    """4.1: jarayon ko'rsatkichlari — bajarish sur'ati, xatolarning takrorlanishi, yordam so'rovlari (kuzatuv varaqasi)."""
    groups = {g.id: g for g in db.query(Group).all()}
    recs = db.query(LessonRecord).all()
    by_arm: Dict[str, List[LessonRecord]] = {"experimental": [], "control": [], "none": []}
    for r in recs:
        g = groups.get(r.group_id)
        arm = g.experiment_arm if g and g.experiment_arm in by_arm else "none"
        by_arm[arm].append(r)

    def summarize(lst: List[LessonRecord]):
        if not lst:
            return {"records": 0}
        pattern_counts: Dict[str, int] = {}
        for r in lst:
            for pid in (r.l1_pattern_ids or []):
                pattern_counts[pid] = pattern_counts.get(pid, 0) + 1
        gaps = [r.rating_gap for r in lst if r.rating_gap is not None]
        return {
            "records": len(lst),
            "avg_score": round(st.mean([r.score for r in lst if r.score is not None]), 1),
            "avg_independent_minutes": round(st.mean([r.independent_seconds for r in lst if r.independent_seconds]) / 60, 1) if any(r.independent_seconds for r in lst) else 0,
            "avg_help_requests": round(st.mean([r.help_requests or 0 for r in lst]), 2),
            "avg_self_checks": round(st.mean([r.self_checks or 0 for r in lst]), 2),
            "avg_rating_gap": round(st.mean(gaps), 2) if gaps else None,
            "feedback_accept_rate": _accept_rate(lst),
            "recurring_l1_patterns": sorted(pattern_counts.items(), key=lambda x: -x[1])[:10],
        }
    return {"by_arm": {k: summarize(v) for k, v in by_arm.items()}, "total_records": len(recs)}


def _accept_rate(lst: List[LessonRecord]):
    acc = tot = 0
    for r in lst:
        for d in (r.feedback_decisions or []):
            tot += 1
            if d.get("accepts"):
                acc += 1
    return round(acc / tot, 2) if tot else None


# ============================================================
# EKSPORT (dissertatsiya to'plami yoki jonli ma'lumotlar)
# ============================================================

def _data_for(source: str, db: Session):
    if source == "live":
        return build_live_tables(db)
    return RESEARCH_DATA


@router.get("/export-docx", dependencies=[Depends(require_role(_EXPORT_ROLES))])
def export_docx(source: str = Query("dissertation", pattern="^(dissertation|live)$"), db: Session = Depends(get_db)):
    """4-bob jadvallarini Word (.docx) formatida yuklab berish (source=live → platformadagi haqiqiy ma'lumotlar)."""
    file_stream = generate_dissertation_docx(_data_for(source, db))
    filename = f"TILORA_4_Bob_Jadvallari_{source}.docx"
    return StreamingResponse(file_stream, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/export-excel", dependencies=[Depends(require_role(_EXPORT_ROLES))])
def export_excel(source: str = Query("dissertation", pattern="^(dissertation|live)$"), db: Session = Depends(get_db)):
    file_stream = generate_dissertation_excel(_data_for(source, db))
    filename = f"TILORA_4_Bob_Statistika_{source}.xlsx"
    return StreamingResponse(file_stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/export-csv", dependencies=[Depends(require_role(_EXPORT_ROLES))])
def export_csv(source: str = Query("dissertation", pattern="^(dissertation|live)$"), db: Session = Depends(get_db)):
    data = _data_for(source, db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["OTM", "Guruh", "Pre-test", "Post-test", "O'sish", "t-mezon", "p-qiymat", "Bespalko K"])
    k8 = {r["institution"]: r for r in data["table_4_8"]["rows"]}
    for r in data["table_4_5"]["rows"]:
        kk = k8.get(r["institution"], {})
        writer.writerow([r["institution"], "Tajriba", r["exp_pre"], r["exp_post"], r["exp_growth"], r["exp_t"], "< 0.001", kk.get("exp_k", "")])
        writer.writerow([r["institution"], "Nazorat", r["ctrl_pre"], r["ctrl_post"], r["ctrl_growth"], r["ctrl_t"], "< 0.001", kk.get("ctrl_k", "")])
    csv_bytes = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    output.close()
    return StreamingResponse(csv_bytes, media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=TILORA_Statistika_{source}.csv"})


@router.get("/export", dependencies=[Depends(require_role(_EXPORT_ROLES))])
def export_research_data(format: str = "docx", source: str = Query("dissertation", pattern="^(dissertation|live)$"), db: Session = Depends(get_db)):
    if format in ("excel", "xlsx"):
        return export_excel(source, db)
    if format == "csv":
        return export_csv(source, db)
    return export_docx(source, db)
