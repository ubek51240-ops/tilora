"""
Dissertatsiyaga 100% moslik uchun qo'shimcha yo'llar (v2.4). Bu routerlar mos ota-routerlarga
(student / teacher_panel / research / admin / teacher_competence) include qilinadi — main.py o'zgarmaydi.

  - SILL (Oxford, 1990): til o'rganish strategiyalari so'rovnomasi, pre/post;
  - Mikroo'qitish + tengdoshlar baholashi (3.2, 14-jadval);
  - Ishonchlilik (4.1): Cronbach α (FLCAS/MSLQ/SILL), baholovchilar mosligi (tizim rubrikasi vs o'qituvchi);
  - Guskey 1-daraja (o'qituvchi munosabati) va 4-daraja (dars loyihasida vositaning maqsadga bog'langanligi);
  - Guruh qanoti va AI'siz nazorat oynasi boshqaruvi;
  - Ma'lumotlarni saqlash muddati (retention) — nofaol hisoblarni anonimlashtirish.
"""
import json
import os
import secrets
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.core.deps import get_current_user, require_role
from app.core.security import hash_password
from app.models.entities import (User, Group, Assessment, SurveyResponse, LessonRecord, Microteaching, PeerReview, ApiKey, TeacherProposal)
from app.services import statistics as st
import app.core.schema_patch  # noqa: F401 — ustunlarni ta'minlash

_CONTENT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")
RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "1095"))  # 3 yil (saqlash muddati oldindan belgilanadi — 3.1-jadval)


@lru_cache(maxsize=4)
def _read(name: str):
    with open(os.path.join(_CONTENT, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _uid(u: dict) -> str:
    return u.get("id") or u.get("sub")


# =====================================================================
# 1. SILL — talaba (/student/sill/*)
# =====================================================================
sill_router = APIRouter()
SILL_GROUPS = ["memory", "cognitive", "compensation", "metacognitive", "affective", "social"]


class SillAnswer(BaseModel):
    item_id: str
    rating: int = Field(..., ge=1, le=5)


class SillIn(BaseModel):
    answers: List[SillAnswer] = Field(..., min_length=6)
    assessment_type: Optional[str] = Field(None, pattern="^(pre|mid|post)$")


def _sill_label(avg: float) -> str:
    for r in _read("sill_questions.json")["interpretation"]:
        if r["min"] <= avg <= r["max"]:
            return r["label"]
    return "—"


@sill_router.get("/sill/questions")
def sill_questions():
    return _read("sill_questions.json")


@sill_router.post("/sill")
def sill_submit(payload: SillIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    spec = _read("sill_questions.json")
    grp_of = {it["id"]: it["group"] for it in spec["items"]}
    by: Dict[str, List[int]] = defaultdict(list)
    for a in payload.answers:
        g = grp_of.get(a.item_id)
        if g:
            by[g].append(a.rating)
    if not by:
        raise HTTPException(status_code=400, detail="Javoblar so'rovnoma bandlariga mos kelmadi.")
    atype = payload.assessment_type
    if not atype:
        has_pre = db.query(Assessment).filter(Assessment.student_id == uid, Assessment.assessment_type == "pre", Assessment.skill.like("sill_%")).first()
        atype = "post" if has_pre else "pre"
    now = datetime.utcnow()
    result = {}
    for g in SILL_GROUPS:
        if by.get(g):
            avg = round(st.mean(by[g]), 2)
            result[g] = {"name": spec["groups"][g]["name"], "avg": avg, "label": _sill_label(avg)}
            db.add(Assessment(student_id=uid, assessment_type=atype, skill=f"sill_{g}", score=int(round(avg * 20)), max_score=100, administered_at=now))
    for a in payload.answers:
        if a.item_id in grp_of:
            db.add(SurveyResponse(student_id=uid, instrument="sill", dimension=grp_of[a.item_id], question_id=a.item_id, rating=a.rating, assessment_type=atype))
    db.commit()
    overall = round(st.mean([v["avg"] for v in result.values()]), 2)
    weakest = min(result, key=lambda g: result[g]["avg"])
    return {"status": "success", "assessment_type": atype, "groups": result, "overall": overall, "overall_label": _sill_label(overall),
            "weakest": weakest, "advice": f"Eng kam qo'llanadigan strategiya guruhi: {result[weakest]['name']} — {spec['groups'][weakest]['desc']}. Keyingi mashg'ulotlarda shu guruhga e'tibor qarating."}


@sill_router.get("/sill/me")
def sill_me(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    rows = db.query(Assessment).filter(Assessment.student_id == uid, Assessment.skill.like("sill_%")).order_by(Assessment.administered_at.asc()).all()
    hist: Dict[str, Dict[str, Any]] = {}
    for a in rows:
        hist.setdefault(a.assessment_type, {"date": a.administered_at.strftime("%Y-%m-%d") if a.administered_at else "", "groups": {}})["groups"][a.skill.replace("sill_", "")] = round(a.score / 20, 2)
    for t, d in hist.items():
        vals = list(d["groups"].values())
        d["overall"] = round(st.mean(vals), 2) if vals else None
    return {"history": hist, "groups_meta": _read("sill_questions.json")["groups"]}


# =====================================================================
# 2. Mikroo'qitish + tengdoshlar baholashi — talaba (/student/microteaching/*)
# =====================================================================
micro_router = APIRouter()
PEER_RUBRIC_KEYS = ["objective", "instructions", "tool_use", "reflection"]
PEER_RUBRIC = [
    {"key": "objective", "name": "Dars maqsadining aniqligi (SWBAT)", "desc": "Maqsad kuzatiladigan natija sifatida ifodalangan"},
    {"key": "instructions", "name": "Ko'rsatmalar va ICQ", "desc": "Ko'rsatmalar aniq, tekshiruv savollari bor, TTT/STT muvozanati"},
    {"key": "tool_use", "name": "Texnologik vositaning maqsadga bog'langanligi", "desc": "Vosita muayyan bosqichda, sababi asoslangan, muqobili bor"},
    {"key": "reflection", "name": "Refleksiya va tahlil", "desc": "Kuchli/zaif tomon aniqlangan, keyingi qadam belgilangan"},
]


class MicroIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    lesson_form: str = Field("microteaching", pattern="^(microteaching|flipped|mixed|practical|lecture|independent|consultation)$")
    objective: str = Field(..., min_length=10, max_length=1000)
    stages: List[Dict[str, Any]] = Field(default_factory=list, max_length=12)
    tool_name: str = Field(..., min_length=2, max_length=120)
    tool_rationale: str = Field(..., min_length=10, max_length=1000)   # majburiy: "vositani nima uchun tanlaganini asoslay olishi"
    alternative_plan: str = Field(..., min_length=5, max_length=1000)  # majburiy: texnologiyasiz muqobil
    independent_share: int = Field(35, ge=0, le=100)
    reflection: Optional[str] = Field(None, max_length=3000)
    submit: bool = False


class PeerReviewIn(BaseModel):
    rubric: Dict[str, int]
    strengths: Optional[str] = Field("", max_length=1000)
    suggestions: Optional[str] = Field("", max_length=1000)


def _micro_dict(m: Microteaching, db: Session, with_reviews: bool = True) -> Dict[str, Any]:
    author = db.query(User).filter(User.id == m.student_id).first()
    d = {"id": m.id, "student_id": m.student_id, "author": author.full_name if author else "", "group_id": m.group_id, "title": m.title,
         "lesson_form": m.lesson_form, "objective": m.objective, "stages": m.stages or [], "tool_name": m.tool_name, "tool_rationale": m.tool_rationale,
         "alternative_plan": m.alternative_plan, "independent_share": m.independent_share, "reflection": m.reflection, "status": m.status,
         "teacher_rubric": m.teacher_rubric, "teacher_comment": m.teacher_comment,
         "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
         "checks": {"independent_share_ok": (m.independent_share or 0) >= 33, "has_alternative": bool(m.alternative_plan), "has_rationale": bool(m.tool_rationale)}}
    if with_reviews:
        revs = db.query(PeerReview).filter(PeerReview.microteaching_id == m.id).all()
        d["peer_reviews"] = [{"id": r.id, "reviewer_id": r.reviewer_id, "rubric": r.rubric, "strengths": r.strengths, "suggestions": r.suggestions,
                              "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else ""} for r in revs]
        d["peer_avg"] = {k: round(st.mean([r.rubric.get(k, 0) for r in revs if r.rubric.get(k)]), 2) for k in PEER_RUBRIC_KEYS if any(r.rubric.get(k) for r in revs)}
        d["peer_count"] = len(revs)
    return d


@micro_router.get("/microteaching/rubric")
def micro_rubric():
    return {"rubric": PEER_RUBRIC, "forms": _read("lesson_forms.json"),
            "rules": ["Mustaqil bajarish ulushi umumiy vaqtning 1/3 dan kam bo'lmasligi kerak", "Bir mashg'ulotda 2 tadan ortiq yangi vosita emas",
                      "Har vosita uchun texnologiyasiz muqobil variant", "Vositani tanlash sababi asoslanadi"]}


@micro_router.get("/microteaching")
def micro_list(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Mening mikroo'qitishlarim + guruhdoshlarning tengdoshlar baholashi uchun topshirilganlari."""
    uid = _uid(current_user)
    mine = db.query(Microteaching).filter(Microteaching.student_id == uid).order_by(Microteaching.created_at.desc()).all()
    gid = current_user.get("group_id")
    peers = []
    if gid:
        peers = db.query(Microteaching).filter(Microteaching.group_id == gid, Microteaching.student_id != uid,
                                               Microteaching.status.in_(["submitted", "reviewed", "evaluated"])).order_by(Microteaching.created_at.desc()).all()
    reviewed_ids = {r.microteaching_id for r in db.query(PeerReview).filter(PeerReview.reviewer_id == uid).all()}
    return {"mine": [_micro_dict(m, db) for m in mine], "rubric": PEER_RUBRIC,
            "peers": [{**_micro_dict(m, db, with_reviews=False), "already_reviewed": m.id in reviewed_ids} for m in peers]}


@micro_router.post("/microteaching")
def micro_create(payload: MicroIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    m = Microteaching(student_id=uid, group_id=current_user.get("group_id"), title=payload.title.strip(), lesson_form=payload.lesson_form,
                      objective=payload.objective.strip(), stages=payload.stages, tool_name=payload.tool_name.strip(), tool_rationale=payload.tool_rationale.strip(),
                      alternative_plan=payload.alternative_plan.strip(), independent_share=payload.independent_share, reflection=(payload.reflection or "").strip() or None,
                      status="submitted" if payload.submit else "draft")
    db.add(m); db.commit(); db.refresh(m)
    return {"status": "success", "microteaching": _micro_dict(m, db)}


@micro_router.put("/microteaching/{mid}")
def micro_update(mid: str, payload: MicroIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    m = db.query(Microteaching).filter(Microteaching.id == mid, Microteaching.student_id == _uid(current_user)).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mikroo'qitish topilmadi.")
    if m.status == "evaluated":
        raise HTTPException(status_code=400, detail="O'qituvchi baholagan loyihani o'zgartirib bo'lmaydi.")
    for k in ("title", "lesson_form", "objective", "stages", "tool_name", "tool_rationale", "alternative_plan", "independent_share"):
        setattr(m, k, getattr(payload, k))
    m.reflection = (payload.reflection or "").strip() or None
    if payload.submit and m.status == "draft":
        m.status = "submitted"
    db.commit(); db.refresh(m)
    return {"status": "success", "microteaching": _micro_dict(m, db)}


@micro_router.post("/microteaching/{mid}/review")
def micro_review(mid: str, payload: PeerReviewIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    m = db.query(Microteaching).filter(Microteaching.id == mid).first()
    if not m or m.student_id == uid:
        raise HTTPException(status_code=404, detail="Baholash uchun guruhdosh loyihasi topilmadi.")
    if m.group_id != current_user.get("group_id") and current_user.get("role") == "student":
        raise HTTPException(status_code=403, detail="Faqat o'z guruhingizdagi loyihalarni baholay olasiz.")
    if m.status == "draft":
        raise HTTPException(status_code=400, detail="Loyiha hali topshirilmagan.")
    for k in PEER_RUBRIC_KEYS:
        v = payload.rubric.get(k)
        if not isinstance(v, int) or not 1 <= v <= 5:
            raise HTTPException(status_code=400, detail=f"'{k}' mezoni 1–5 oralig'ida bo'lishi kerak.")
    if db.query(PeerReview).filter(PeerReview.microteaching_id == mid, PeerReview.reviewer_id == uid).first():
        raise HTTPException(status_code=400, detail="Siz bu loyihani allaqachon baholagansiz.")
    db.add(PeerReview(microteaching_id=mid, reviewer_id=uid, rubric={k: payload.rubric[k] for k in PEER_RUBRIC_KEYS},
                      strengths=(payload.strengths or "").strip(), suggestions=(payload.suggestions or "").strip()))
    if m.status == "submitted":
        m.status = "reviewed"
    db.commit()
    return {"status": "success", "message": "Tengdosh bahosi saqlandi. Tanqid emas, konstruktiv taklif (You might consider...)."}


# =====================================================================
# 3. O'qituvchi: mikroo'qitish bahosi, guruh qanoti/oynasi, ikkinchi baholovchi (/teacher/panel/*)
# =====================================================================
teacher_ext_router = APIRouter()


class MicroEvalIn(BaseModel):
    rubric: Dict[str, int]
    comment: Optional[str] = Field("", max_length=2000)


class ArmIn(BaseModel):
    arm: str = Field(..., pattern="^(experimental|control|none)$")


class WindowIn(BaseModel):
    window: str = Field(..., pattern="^(none|pre|mid|post)$")


class RubricIn(BaseModel):
    content: int = Field(..., ge=1, le=5)
    grammar: int = Field(..., ge=1, le=5)
    lexis: int = Field(..., ge=1, le=5)
    coherence: int = Field(..., ge=1, le=5)


def _teacher_group(db: Session, user: dict, group_id: str) -> Group:
    from app.api.teacher_panel import _can_see_group
    g = db.query(Group).filter(Group.id == group_id).first()
    if not g or not _can_see_group(db, user, g):
        raise HTTPException(status_code=404, detail="Guruh topilmadi yoki ruxsat yo'q.")
    return g


@teacher_ext_router.get("/microteaching")
def teacher_micro_list(group_id: Optional[str] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    q = db.query(Microteaching)
    if group_id:
        _teacher_group(db, current_user, group_id)
        q = q.filter(Microteaching.group_id == group_id)
    elif current_user.get("role") != "admin":
        from app.api.teacher_panel import _can_see_group
        visible = [g.id for g in db.query(Group).all() if _can_see_group(db, current_user, g)]
        q = q.filter(Microteaching.group_id.in_(visible)) if visible else q.filter(Microteaching.id == "__none__")
    items = [_micro_dict(m, db) for m in q.order_by(Microteaching.created_at.desc()).all()]
    evaluated = [m for m in items if m["teacher_rubric"]]
    return {"items": items, "total": len(items), "rubric": PEER_RUBRIC,
            "summary": {"submitted": sum(1 for m in items if m["status"] != "draft"), "evaluated": len(evaluated),
                        "avg_teacher": {k: round(st.mean([m["teacher_rubric"].get(k, 0) for m in evaluated if m["teacher_rubric"].get(k)]), 2) for k in PEER_RUBRIC_KEYS if evaluated and any(m["teacher_rubric"].get(k) for m in evaluated)}}}


@teacher_ext_router.post("/microteaching/{mid}/evaluate")
def teacher_micro_eval(mid: str, payload: MicroEvalIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    m = db.query(Microteaching).filter(Microteaching.id == mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="Loyiha topilmadi.")
    if m.group_id and current_user.get("role") != "admin":
        _teacher_group(db, current_user, m.group_id)
    for k in PEER_RUBRIC_KEYS:
        v = payload.rubric.get(k)
        if not isinstance(v, int) or not 1 <= v <= 5:
            raise HTTPException(status_code=400, detail=f"'{k}' mezoni 1–5 oralig'ida bo'lishi kerak.")
    m.teacher_rubric = {k: payload.rubric[k] for k in PEER_RUBRIC_KEYS}
    m.teacher_comment = (payload.comment or "").strip()
    m.status = "evaluated"
    db.commit()
    return {"status": "success", "microteaching": _micro_dict(m, db)}


@teacher_ext_router.patch("/groups/{group_id}/arm")
def set_group_arm(group_id: str, payload: ArmIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Tajriba qanoti: experimental (model) | control (an'anaviy, adaptiv va metakognitiv bloklar yopiq) | none."""
    g = _teacher_group(db, current_user, group_id)
    g.experiment_arm = payload.arm
    db.commit()
    return {"status": "success", "group": {"id": g.id, "name": g.name, "arm": g.experiment_arm}}


@teacher_ext_router.patch("/groups/{group_id}/assessment-window")
def set_assessment_window(group_id: str, payload: WindowIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """AI'siz nazorat oynasi: ochiq bo'lganda guruh talabalari uchun AI vositalari yopiladi; diagnostika natijasi shu tur bilan yoziladi."""
    g = _teacher_group(db, current_user, group_id)
    g.assessment_window = payload.window
    db.commit()
    return {"status": "success", "group": {"id": g.id, "name": g.name, "assessment_window": g.assessment_window},
            "note": "Oyna ochiq: talabalar diagnostika/nazoratni texnologik vositalarsiz bajaradi (4.1)." if payload.window != "none" else "Oyna yopildi."}


@teacher_ext_router.post("/records/{record_id}/rate")
def teacher_rate_record(record_id: str, payload: RubricIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Ikkinchi mustaqil baholovchi: o'qituvchi rubrikasi (baholovchilar mosligi — inter-rater uchun)."""
    from app.api.teacher_panel import _student_for
    r = db.query(LessonRecord).filter(LessonRecord.id == record_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Yozuv topilmadi.")
    _student_for(db, current_user, r.student_id)
    r.teacher_rubric = payload.model_dump()
    r.teacher_id = _uid(current_user)
    db.commit()
    sys_r = r.rubric or {}
    agree = st.rater_agreement([sys_r.get(k) for k in ("content", "grammar", "lexis", "coherence")], [payload.model_dump()[k] for k in ("content", "grammar", "lexis", "coherence")])
    return {"status": "success", "teacher_rubric": r.teacher_rubric, "system_rubric": sys_r, "agreement": agree}


# =====================================================================
# 4. Tadqiqot: ishonchlilik va qo'shimcha xulosa (/research/live/*)
# =====================================================================
research_ext_router = APIRouter()


def _alpha_for(db: Session, instrument: str, dimension: Optional[str], atype: str = "pre") -> Dict[str, Any]:
    q = db.query(SurveyResponse).filter(SurveyResponse.instrument == instrument, SurveyResponse.assessment_type == atype)
    if dimension:
        q = q.filter(SurveyResponse.dimension == dimension)
    rows = q.all()
    by_student: Dict[str, Dict[str, int]] = defaultdict(dict)
    items = set()
    for r in rows:
        by_student[r.student_id][r.question_id] = r.rating
        items.add(r.question_id)
    items = sorted(items)
    matrix = [[by_student[s].get(i) for i in items] for s in by_student if all(i in by_student[s] for i in items)]
    return st.cronbach_alpha(matrix)


@research_ext_router.get("/live/reliability", dependencies=[Depends(require_role(["researcher", "admin", "teacher"]))])
def reliability(db: Session = Depends(get_db)):
    """4.1: o'lchov vositalarining ishonchliligi — Cronbach α (FLCAS, MSLQ, SILL, kognitiv) va baholovchilar mosligi (tizim vs o'qituvchi)."""
    out = {"cronbach": {}, "inter_rater": {}}
    for inst, dims in (("flcas", ["anxiety"]), ("mslq", ["planning", "monitoring", "evaluation", "regulation"]),
                       ("cognitive", ["load_capacity", "pace", "autonomy", "motivation"]), ("sill", SILL_GROUPS)):
        out["cronbach"][inst] = {"overall": _alpha_for(db, inst, None), "dimensions": {d: _alpha_for(db, inst, d) for d in dims}}
    recs = db.query(LessonRecord).filter(LessonRecord.teacher_rubric.isnot(None)).all()
    for k in ("content", "grammar", "lexis", "coherence"):
        a = [(r.rubric or {}).get(k) for r in recs]; b = [(r.teacher_rubric or {}).get(k) for r in recs]
        out["inter_rater"][k] = st.rater_agreement(a, b)
    allsys = [v for r in recs for v in [(r.rubric or {}).get(k) for k in ("content", "grammar", "lexis", "coherence")]]
    allt = [v for r in recs for v in [(r.teacher_rubric or {}).get(k) for k in ("content", "grammar", "lexis", "coherence")]]
    out["inter_rater"]["overall"] = st.rater_agreement(allsys, allt)
    out["inter_rater"]["records_double_rated"] = len(recs)
    # Mikroo'qitish: tengdoshlar vs o'qituvchi
    ms = db.query(Microteaching).filter(Microteaching.teacher_rubric.isnot(None)).all()
    pa, pb = [], []
    for m in ms:
        revs = db.query(PeerReview).filter(PeerReview.microteaching_id == m.id).all()
        for k in PEER_RUBRIC_KEYS:
            vals = [r.rubric.get(k) for r in revs if r.rubric.get(k)]
            if vals and m.teacher_rubric.get(k):
                pa.append(int(round(st.mean(vals)))); pb.append(m.teacher_rubric[k])
    out["inter_rater"]["microteaching_peer_vs_teacher"] = st.rater_agreement(pa, pb)
    out["note"] = "α ≥ 0.7 qoniqarli; κ (kvadratik vaznli) ≥ 0.6 yaxshi moslik. Ma'lumot kam bo'lsa ko'rsatkich hisoblanmaydi."
    return out


@research_ext_router.get("/live/sill", dependencies=[Depends(require_role(["researcher", "admin", "teacher"]))])
def sill_summary(db: Session = Depends(get_db)):
    """SILL strategiyalari pre/post, tajriba vs nazorat."""
    groups = {g.id: g for g in db.query(Group).all()}
    users = {u.id: u for u in db.query(User).filter(User.role == "student").all()}
    rows = db.query(Assessment).filter(Assessment.skill.like("sill_%")).all()
    per: Dict[tuple, float] = {}
    for a in rows:
        per[(a.student_id, a.assessment_type, a.skill)] = a.score / 20
    out = {}
    for g in SILL_GROUPS:
        out[g] = {}
        for arm in ("experimental", "control"):
            sids = [u.id for u in users.values() if u.group_id in groups and groups[u.group_id].experiment_arm == arm]
            pre = [per[(s, "pre", f"sill_{g}")] for s in sids if (s, "pre", f"sill_{g}") in per]
            post = [per[(s, "post", f"sill_{g}")] for s in sids if (s, "post", f"sill_{g}") in per]
            out[g][arm] = {"n_pre": len(pre), "n_post": len(post), "pre": round(st.mean(pre), 2) if pre else None, "post": round(st.mean(post), 2) if post else None,
                           "growth": st.growth_percent(st.mean(pre), st.mean(post)) if pre and post else "—"}
    return {"groups": out, "meta": _read("sill_questions.json")["groups"]}


# =====================================================================
# 5. Guskey 1 va 4 — o'qituvchi (/teacher/competence/*)
# =====================================================================
guskey_router = APIRouter()
SATISFACTION_ITEMS = [
    {"id": "g1_1", "uz": "Platforma mening dars amaliyotimga foydali bo'ldi."},
    {"id": "g1_2", "uz": "Tayyorgarlik mashg'ulotlari tushunarli va amaliy edi."},
    {"id": "g1_3", "uz": "Kuzatuv paneli va takliflar tizimi qarorlarimga yordam berdi."},
    {"id": "g1_4", "uz": "Modelning bosqichlari (AI yopiq mustaqil bosqich, refleksiya) talabalarga ta'sir qildi."},
    {"id": "g1_5", "uz": "Modelni kelgusida ham qo'llashni rejalashtiryapman."},
]


class SatisfactionIn(BaseModel):
    answers: Dict[str, int]
    comment: Optional[str] = Field("", max_length=1500)


class LessonPlanCheckIn(BaseModel):
    """Guskey 4-daraja: dars loyihasida vositaning o'quv maqsadiga bog'langanligi (10-jadval, 13-jadval mezonlari)."""
    objective_in_syllabus: bool
    tool_linked_to_objective: bool
    tool_at_specific_stage: bool
    tool_rationale_written: bool
    alternative_without_tool: bool
    independent_stage_share_ok: bool      # >= 1/3
    feedback_explains_cause: bool
    max_two_new_tools: bool
    note: Optional[str] = Field("", max_length=1000)


@guskey_router.get("/satisfaction/items")
def satisfaction_items():
    return {"items": SATISFACTION_ITEMS, "scale": "likert_5", "level": "Guskey 1-daraja: ishtirokchilarning munosabati"}


@guskey_router.post("/satisfaction")
def satisfaction(payload: SatisfactionIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    vals = [v for k, v in payload.answers.items() if k in {i["id"] for i in SATISFACTION_ITEMS} and isinstance(v, int) and 1 <= v <= 5]
    if not vals:
        raise HTTPException(status_code=400, detail="Javoblar topilmadi (1–5).")
    avg = round(st.mean(vals), 2)
    db.add(Assessment(student_id=_uid(current_user), assessment_type="post", skill="guskey1_satisfaction", score=int(round(avg * 20)), max_score=100, administered_at=datetime.utcnow()))
    db.commit()
    return {"status": "success", "avg": avg, "label": "Yuqori" if avg >= 4 else "O'rta" if avg >= 3 else "Past", "comment": payload.comment}


@guskey_router.post("/lesson-plan-check")
def lesson_plan_check(payload: LessonPlanCheckIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    flags = payload.model_dump(exclude={"note"})
    met = [k for k, v in flags.items() if v]
    pct = int(round(len(met) / len(flags) * 100))
    db.add(Assessment(student_id=_uid(current_user), assessment_type="post", skill="guskey4_practice", score=pct, max_score=100, administered_at=datetime.utcnow()))
    db.commit()
    labels = {"objective_in_syllabus": "Maqsad sillabusda qayd etilgan", "tool_linked_to_objective": "Vosita o'quv maqsadiga bog'langan",
              "tool_at_specific_stage": "Vosita muayyan bosqichda", "tool_rationale_written": "Vositani tanlash sababi yozilgan",
              "alternative_without_tool": "Texnologiyasiz muqobil bor", "independent_stage_share_ok": "Mustaqil bosqich ≥ 1/3",
              "feedback_explains_cause": "Izoh xato sababini tushuntiradi", "max_two_new_tools": "2 tadan ortiq yangi vosita emas"}
    return {"status": "success", "score_percent": pct, "level": "Amaliy/Ijodiy" if pct >= 75 else "Boshlang'ich", "met": [labels[k] for k in met],
            "unmet": [labels[k] for k in flags if k not in met], "note": payload.note}


@guskey_router.get("/guskey/summary", dependencies=[Depends(require_role(["researcher", "admin", "teacher"]))])
def guskey_summary(db: Session = Depends(get_db)):
    s1 = [a.score / 20 for a in db.query(Assessment).filter(Assessment.skill == "guskey1_satisfaction").all()]
    s4 = [a.score for a in db.query(Assessment).filter(Assessment.skill == "guskey4_practice").all()]
    return {"level1_satisfaction": {"n": len(s1), "avg": round(st.mean(s1), 2) if s1 else None},
            "level4_practice": {"n": len(s4), "avg_percent": round(st.mean(s4), 1) if s4 else None},
            "note": "Guskey (2000): 1 — munosabat, 2 — bilim/malaka (SI-kompetensiya pre/post), 3 — institutsional qo'llab-quvvatlash, 4 — amaliyotdagi o'zgarish, 5 — talabalar natijasi (4.5–4.9 jadvallar)."}


# =====================================================================
# 6. Saqlash muddati — admin (/admin/retention/*)
# =====================================================================
retention_router = APIRouter()


def _anonymize(db: Session, u: User) -> None:
    short = u.id[:8]
    u.email = f"deleted_{short}@anon.tilora"; u.full_name = "O'chirilgan foydalanuvchi"; u.phone_number = None; u.is_active = False
    u.password_hash = hash_password(secrets.token_urlsafe(24))
    for r in db.query(LessonRecord).filter(LessonRecord.student_id == u.id).all():
        r.production_text = None; r.drafts = None; r.plan_goal = None; r.plan_strategy = None
        r.gap_explanation = None; r.next_goal = None; r.comparison_note = None; r.feedback_decisions = None
    db.query(ApiKey).filter(ApiKey.user_id == u.id).delete()


@retention_router.get("/retention/status")
def retention_status(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    users = db.query(User).filter(User.role != "admin", User.is_active == True).all()
    stale = [u for u in users if (u.last_login_at or u.created_at or datetime.utcnow()) < cutoff]
    return {"retention_days": RETENTION_DAYS, "cutoff": cutoff.strftime("%Y-%m-%d"), "stale_accounts": len(stale),
            "policy": f"Shaxsga doir ma'lumotlar oxirgi faollikdan {RETENTION_DAYS} kun ({RETENTION_DAYS // 365} yil) saqlanadi; muddat o'tgach anonimlashtiriladi, faqat ID-ga bog'liq raqamli natijalar ilmiy statistika uchun qoladi (O'RQ-547).",
            "stale_preview": [{"id": u.id, "email": u.email, "last": (u.last_login_at or u.created_at).strftime("%Y-%m-%d") if (u.last_login_at or u.created_at) else ""} for u in stale[:20]]}


@retention_router.post("/retention/purge")
def retention_purge(dry_run: bool = Query(True), db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    users = db.query(User).filter(User.role != "admin", User.is_active == True).all()
    stale = [u for u in users if (u.last_login_at or u.created_at or datetime.utcnow()) < cutoff]
    if not dry_run:
        for u in stale:
            _anonymize(db, u)
        db.commit()
    return {"status": "dry_run" if dry_run else "purged", "count": len(stale), "retention_days": RETENTION_DAYS}
