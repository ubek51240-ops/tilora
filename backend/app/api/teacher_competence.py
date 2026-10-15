"""
O'qituvchining SI-kompetensiyasi (dissertatsiya 2.3; UNESCO AI CFT 2024): o'z-o'zini baholash varaqasi,
daraja (boshlang'ich / amaliy / ijodiy), rivojlantirish yo'llari, pre/post dinamika (Guskey 2-daraja),
hamda AI vositasini baholash varaqasi (3.1-jadval, 8 savol).
Natijalar assessments jadvaliga yoziladi (student_id = o'qituvchi id, skill = comp_<component>).
"""
import json
import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.entities import Assessment, User
from app.services import statistics as st

router = APIRouter(prefix="/teacher/competence", tags=["O'qituvchi"], dependencies=[Depends(require_role(["teacher", "admin"]))])

_CONTENT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "teacher_competence.json")
COMPONENTS = ["cognitive", "didactic", "ethical", "reflective"]


@lru_cache(maxsize=1)
def _spec() -> Dict[str, Any]:
    with open(_CONTENT, "r", encoding="utf-8") as f:
        return json.load(f)


class Answer(BaseModel):
    item_id: str
    rating: int = Field(..., ge=1, le=5)


class SelfAssessIn(BaseModel):
    answers: List[Answer] = Field(..., min_length=4)
    assessment_type: Optional[str] = Field(None, pattern="^(pre|mid|post)$")


class ToolEvalIn(BaseModel):
    tool_name: str = Field(..., min_length=2, max_length=120)
    answers: Dict[str, bool]
    note: Optional[str] = Field("", max_length=1000)


def level_for(avg: float) -> Dict[str, Any]:
    for lv in _spec()["levels"]:
        if lv["min"] <= avg <= lv["max"] or (lv["key"] == "creative" and avg >= lv["min"]):
            return lv
    return _spec()["levels"][0]


def _uid(u: dict) -> str:
    return u.get("id") or u.get("sub")


@router.get("/questions")
def competence_questions():
    s = _spec()
    return {"title": s["title"], "basis": s["basis"], "components": s["components"], "levels": s["levels"], "items": s["items"],
            "pathways": s["pathways"], "tool_evaluation_checklist": s["tool_evaluation_checklist"]}


def _profile_from_answers(answers: List[Answer]) -> Dict[str, Any]:
    s = _spec()
    comp_of = {it["id"]: it["component"] for it in s["items"]}
    by: Dict[str, List[int]] = {c: [] for c in COMPONENTS}
    for a in answers:
        c = comp_of.get(a.item_id)
        if c:
            by[c].append(a.rating)
    comps = {}
    for c in COMPONENTS:
        avg = round(st.mean(by[c]), 2) if by[c] else None
        comps[c] = {"name": s["components"][c]["name"], "avg": avg, "n": len(by[c]), "level": level_for(avg)["name"] if avg is not None else None}
    vals = [v["avg"] for v in comps.values() if v["avg"] is not None]
    overall = round(st.mean(vals), 2) if vals else None
    weakest = min((c for c in COMPONENTS if comps[c]["avg"] is not None), key=lambda c: comps[c]["avg"], default=None)
    return {"components": comps, "overall": overall, "overall_level": level_for(overall) if overall is not None else None,
            "weakest": weakest, "recommendations": [p for p in s["pathways"] if p["component"] == weakest] if weakest else []}


@router.post("/self-assess")
def self_assess(payload: SelfAssessIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    prof = _profile_from_answers(payload.answers)
    atype = payload.assessment_type
    if not atype:
        has_pre = db.query(Assessment).filter(Assessment.student_id == uid, Assessment.assessment_type == "pre", Assessment.skill == "comp_cognitive").first()
        atype = "post" if has_pre else "pre"
    now = datetime.utcnow()
    for c in COMPONENTS:
        avg = prof["components"][c]["avg"]
        if avg is not None:
            db.add(Assessment(student_id=uid, assessment_type=atype, skill=f"comp_{c}", score=int(round(avg * 20)), max_score=100, administered_at=now))
    db.commit()
    return {"status": "success", "assessment_type": atype, **prof,
            "message": f"Natija saqlandi ({atype}). Umumiy daraja: {prof['overall_level']['name'] if prof['overall_level'] else '—'}."}


@router.get("/me")
def my_competence(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    rows = db.query(Assessment).filter(Assessment.student_id == uid, Assessment.skill.like("comp_%")).order_by(Assessment.administered_at.asc()).all()
    hist: Dict[str, Dict[str, Any]] = {}
    for a in rows:
        d = hist.setdefault(a.assessment_type, {"date": a.administered_at.strftime("%Y-%m-%d") if a.administered_at else "", "components": {}})
        d["components"][a.skill.replace("comp_", "")] = round(a.score / 20, 2)
    for t, d in hist.items():
        vals = list(d["components"].values())
        d["overall"] = round(st.mean(vals), 2) if vals else None
        d["level"] = level_for(d["overall"])["name"] if d["overall"] is not None else None
    growth = None
    if "pre" in hist and "post" in hist and hist["pre"]["overall"] and hist["post"]["overall"]:
        growth = round(hist["post"]["overall"] - hist["pre"]["overall"], 2)
    return {"history": hist, "growth": growth, "components_meta": _spec()["components"], "levels": _spec()["levels"]}


@router.post("/tool-evaluation")
def tool_evaluation(payload: ToolEvalIn, current_user: dict = Depends(get_current_user)):
    """AI vositasini baholash varaqasi (3.1-bo'lim, 8 mezon): ha/yo'q javoblar -> foiz va xulosa. Saqlanmaydi, xulosa qaytaradi."""
    checklist = _spec()["tool_evaluation_checklist"]
    yes = [c for c in checklist if payload.answers.get(c["key"])]
    no = [c for c in checklist if not payload.answers.get(c["key"])]
    pct = int(round(len(yes) / len(checklist) * 100))
    verdict = ("Tavsiya etiladi" if pct >= 75 else ("Cheklovlar bilan qo'llash mumkin" if pct >= 50 else "Qo'llash tavsiya etilmaydi"))
    return {"tool_name": payload.tool_name, "score_percent": pct, "verdict": verdict,
            "met": [c["q"] for c in yes], "unmet": [{"q": c["q"], "criterion": c["criterion"]} for c in no], "note": payload.note}


def teacher_competence_summary(db: Session) -> Dict[str, Any]:
    """Tadqiqot moduli uchun: o'qituvchilar kompetensiyasi pre/post dinamikasi (Guskey 2-daraja)."""
    rows = db.query(Assessment).filter(Assessment.skill.like("comp_%")).all()
    per: Dict[tuple, float] = {}
    for a in rows:
        per[(a.student_id, a.assessment_type, a.skill)] = a.score / 20
    teachers = {k[0] for k in per}
    out = {"teachers": len(teachers), "components": {}}
    for c in COMPONENTS:
        pre, post = [], []
        for t in teachers:
            a, b = per.get((t, "pre", f"comp_{c}")), per.get((t, "post", f"comp_{c}"))
            if a is not None and b is not None:
                pre.append(a); post.append(b)
        tt = st.paired_t_test(pre, post)
        out["components"][c] = {"name": _spec()["components"][c]["name"], "n_paired": tt["n"], "pre": round(st.mean(pre), 2), "post": round(st.mean(post), 2),
                                "growth": st.growth_percent(st.mean(pre), st.mean(post)) if pre else "—", "t": tt["t"], "p": st.fmt_p(tt["p"]) if tt["n"] >= 2 else "—"}
    return out
