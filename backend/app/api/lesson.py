"""
5 bosqichli mashg'ulot API + metakognitiv sikl (dissertatsiya 3.3):
  Rejalashtirish (1-bosqich: maqsad, strategiya) -> Monitoring (3-bosqich: o'z-o'zini tekshirish, yordam so'rovlari, vaqt)
  -> Baholash (4–5-bosqich: izohlarni asoslab qabul/rad etish, qiyosiy usul, o'z bahosi) -> Refleksiya (farq sababi, keyingi maqsad).

Mashg'ulot holati har bir foydalanuvchi uchun ALOHIDA saqlanadi (xotirada, user_id bo'yicha);
yakunlangach LessonRecord jadvaliga yoziladi (dinamika va o'qituvchi kuzatuv paneli manbai).
"""
import copy
import threading
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import LessonRecord, User
from app.schemas.all_schemas import ProductionSubmit, SelfRatingSubmit, ReflectionSubmit
from app.core.deps import get_current_user
from app.core.errors import TiloraException
from app.services.feedback import generate_production_feedback, analyze_production_feedback_async
from app.services.ai_service import ai_service
from app.services.lesson_tasks import get_task, list_tasks, DEFAULT_SKILL
from app.services.differentiation import effective_variant
from pydantic import BaseModel, Field


class AiEvaluateRequest(BaseModel):
    content_text: Optional[str] = Field(None, max_length=20000)


class PlanRequest(BaseModel):
    goal: str = Field(..., min_length=5, max_length=1000)
    strategy: Optional[str] = Field("", max_length=1000)
    skill: Optional[str] = None


class MonitorEvent(BaseModel):
    event: str = Field(..., pattern="^(help_request|self_check|tick)$")
    seconds: Optional[int] = Field(0, ge=0, le=36000)


class FeedbackDecisionIn(BaseModel):
    item_id: str = Field(..., max_length=100)
    title: Optional[str] = Field("", max_length=300)
    accepts: bool
    justification: Optional[str] = Field("", max_length=1000)


class ComparisonIn(BaseModel):
    note: str = Field(..., min_length=5, max_length=2000)


router = APIRouter(prefix="/lesson", tags=["Mashg'ulot"])

MAX_PRODUCTION_CHARS = 20000

_DEFAULT_STATE: Dict[str, Any] = {
    "current_stage": "intro",
    "ai_locked": False,
    "skill": DEFAULT_SKILL,
    "variant": None,
    "scaffold_level": None,
    "plan": None,                 # {goal, strategy}
    "help_requests": 0,
    "self_checks": 0,
    "independent_seconds": 0,
    "started_at": None,
    "production_text": "",
    "self_rating": None,
    "actual_rating": None,
    "score": None,
    "feedback_items": [],
    "feedback_decisions": {},     # item_id -> {title, accepts, justification}
    "l1_pattern_ids": [],
    "alternative_text": None,
    "comparison_note": None,
    "ai_powered": False,
    "ai_evaluation": None,
    "reflection": None,
}

_STATES: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()
_MAX_STATES = 5000

STAGES = ["intro", "preparation", "independent", "analysis", "reflection"]


def get_lesson_state(user_id: str) -> Dict[str, Any]:
    """Foydalanuvchining mashg'ulot holati (bo'lmasa yaratiladi)."""
    with _LOCK:
        st = _STATES.get(user_id)
        if st is None:
            if len(_STATES) >= _MAX_STATES:
                _STATES.pop(next(iter(_STATES)))
            st = copy.deepcopy(_DEFAULT_STATE)
            st["started_at"] = time.time()
            _STATES[user_id] = st
        return st


def peek_lesson_state(user_id: str) -> Optional[Dict[str, Any]]:
    """Holat mavjud bo'lsa qaytaradi, aks holda None (AI-lock qo'riqchisi uchun)."""
    with _LOCK:
        return _STATES.get(user_id)


def reset_lesson_state(user_id: str) -> None:
    with _LOCK:
        _STATES.pop(user_id, None)


def _uid(user: dict) -> str:
    uid = user.get("id") or user.get("sub")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi aniqlanmadi.")
    return str(uid)


def _check_text(text: str) -> str:
    text = (text or "").strip()
    if len(text) > MAX_PRODUCTION_CHARS:
        raise HTTPException(status_code=400, detail=f"Matn {MAX_PRODUCTION_CHARS} belgidan oshmasligi kerak.")
    return text


def _task_for(st: Dict[str, Any], skill: Optional[str] = None) -> Dict[str, Any]:
    """Topshiriq: talabaning variantiga (A/B/C) mos prompt va ko'mak darajasi bilan."""
    task = get_task(skill or st.get("skill") or DEFAULT_SKILL)
    v = st.get("variant")
    variants = task.get("variants") or {}
    if v and v in variants:
        task.update({k: val for k, val in variants[v].items()})
        task["variant"] = v
    task["scaffold_level"] = st.get("scaffold_level") or task.get("scaffold_level", "full")
    return task


@router.get("/tasks")
def get_lesson_tasks():
    """Barcha ko'nikmalar bo'yicha mavjud mashg'ulot topshiriqlari banki (ochiq ma'lumot)."""
    return {"tasks": list_tasks()}


@router.post("/{lesson_id}/text-quality")
def check_text_quality(lesson_id: str, payload: AiEvaluateRequest):
    """3-bosqich: lokal (AI'siz) matn sifati tekshiruvi — ma'nosiz harflar, tushunarsiz so'z va gaplar.
    Javob bermaydi, tuzatmaydi; faqat nechta shubhali so'z borligini ko'rsatadi (1-qoida buzilmaydi)."""
    from app.services.text_quality import analyze_text_quality
    q = analyze_text_quality(_check_text(payload.content_text or ""))
    return {"lesson_id": lesson_id, "ai_used": False, **q}


@router.get("/{lesson_id}/task")
def get_lesson_task(lesson_id: str, skill: Optional[str] = None, variant: Optional[str] = None):
    """Topshiriq sharti — 1-qoida bo'yicha mustaqil bosqichda ham OCHIQ qoladi. variant=A|B|C (ixtiyoriy)."""
    task = get_task(skill or DEFAULT_SKILL)
    variants = task.get("variants") or {}
    if variant and variant in variants:
        task.update(variants[variant]); task["variant"] = variant
    return {"lesson_id": lesson_id, **task}


@router.get("/history")
def my_lesson_history(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Talabaning yakunlangan mashg'ulotlari (refleksiya moduli: dinamika ko'rsatkichlari)."""
    uid = _uid(current_user)
    recs = db.query(LessonRecord).filter(LessonRecord.student_id == uid).order_by(LessonRecord.created_at.desc()).limit(50).all()
    return {"records": [_record_dict(r) for r in recs], "total": len(recs)}


def _record_dict(r: LessonRecord, with_text: bool = False) -> Dict[str, Any]:
    d = {
        "id": r.id, "student_id": r.student_id, "skill": r.skill, "task_variant": r.task_variant, "scaffold_level": r.scaffold_level,
        "plan_goal": r.plan_goal, "plan_strategy": r.plan_strategy,
        "help_requests": r.help_requests, "self_checks": r.self_checks, "independent_seconds": r.independent_seconds, "total_seconds": r.total_seconds,
        "word_count": r.word_count, "score": r.score, "rubric": r.rubric, "self_rating": r.self_rating, "rating_gap": r.rating_gap,
        "feedback_decisions": r.feedback_decisions or [], "l1_pattern_ids": r.l1_pattern_ids or [], "comparison_note": r.comparison_note,
        "ai_powered": r.ai_powered, "gap_explanation": r.gap_explanation, "next_goal": r.next_goal,
        "teacher_extension": r.teacher_extension, "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
    }
    if with_text:
        d["production_text"] = r.production_text
    return d


@router.get("/{lesson_id}")
def get_lesson_status(lesson_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = _uid(current_user)
    st = get_lesson_state(uid)
    if st.get("variant") is None and current_user.get("role") == "student":
        ev = effective_variant(db, uid)
        st["variant"], st["scaffold_level"] = ev["variant"], ev["scaffold"]
        st["variant_reason"] = ev["reason"]
    task = _task_for(st)
    return {
        "lesson_id": lesson_id,
        "skill": st.get("skill"),
        "variant": st.get("variant"),
        "variant_reason": st.get("variant_reason"),
        "scaffold_level": task.get("scaffold_level"),
        "current_week": task.get("week_range", "5-6-hafta"),
        "stage": st["current_stage"],
        "ai_locked": st["ai_locked"],
        "duration_minutes": task.get("duration_minutes", 30),
        "plan": st.get("plan"),
        "has_production": bool(st.get("production_text")),
        "has_self_rating": bool(st.get("self_rating")),
        "task": task,
    }


@router.post("/{lesson_id}/plan")
def submit_plan(lesson_id: str, payload: PlanRequest, current_user: dict = Depends(get_current_user)):
    """Metakognitiv sikl 1-qadam — REJALASHTIRISH: talaba maqsad va strategiyani belgilaydi."""
    st = get_lesson_state(_uid(current_user))
    if payload.skill:
        st["skill"] = get_task(payload.skill)["skill"]
    st["plan"] = {"goal": payload.goal.strip(), "strategy": (payload.strategy or "").strip()}
    st["started_at"] = time.time()
    return {"lesson_id": lesson_id, "status": "planned", "plan": st["plan"], "skill": st["skill"]}


@router.post("/{lesson_id}/stage/next")
def next_stage(lesson_id: str, target_stage: Optional[str] = None, skill: Optional[str] = None,
               current_user: dict = Depends(get_current_user)):
    st = get_lesson_state(_uid(current_user))
    if skill:
        st["skill"] = get_task(skill)["skill"]
    curr = st["current_stage"]
    if target_stage and target_stage in STAGES:
        st["current_stage"] = target_stage
    else:
        idx = STAGES.index(curr) if curr in STAGES else 0
        st["current_stage"] = STAGES[min(len(STAGES) - 1, idx + 1)]

    # 1-QOIDA: mustaqil bosqichga kirilgach AI serverda qulflanadi
    st["ai_locked"] = (st["current_stage"] == "independent")
    if st["ai_locked"]:
        st["independent_entered_at"] = time.time()
    return {"lesson_id": lesson_id, "current_stage": st["current_stage"], "ai_locked": st["ai_locked"]}


@router.post("/{lesson_id}/monitor")
def monitor_event(lesson_id: str, payload: MonitorEvent, current_user: dict = Depends(get_current_user)):
    """Metakognitiv sikl 2-qadam — MONITORING: o'z-o'zini tekshirish belgisi, yordamga urinish, vaqt (kuzatuv varaqasi)."""
    st = get_lesson_state(_uid(current_user))
    if payload.event == "help_request":
        st["help_requests"] = int(st.get("help_requests", 0)) + 1
    elif payload.event == "self_check":
        st["self_checks"] = int(st.get("self_checks", 0)) + 1
    if payload.seconds:
        st["independent_seconds"] = int(payload.seconds)
    return {"lesson_id": lesson_id, "help_requests": st["help_requests"], "self_checks": st["self_checks"], "independent_seconds": st["independent_seconds"]}


@router.post("/{lesson_id}/production")
async def submit_production(lesson_id: str, payload: ProductionSubmit, current_user: dict = Depends(get_current_user)):
    st = get_lesson_state(_uid(current_user))
    text = _check_text(payload.content_text)
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Matn juda qisqa. Kamida bir necha gap yozing.")
    st["production_text"] = text
    st["self_rating"] = None
    st["ai_evaluation"] = None
    st["feedback_decisions"] = {}
    st["alternative_text"] = None
    if st.get("independent_entered_at") and not st.get("independent_seconds"):
        st["independent_seconds"] = int(time.time() - st["independent_entered_at"])

    fb = await analyze_production_feedback_async(text, lesson_id)
    st["actual_rating"] = fb["score_data"]["rubric"]
    st["score"] = fb["score_data"]["total_score"]
    st["feedback_items"] = fb["feedback_items"]
    st["ai_powered"] = fb.get("ai_powered", False)
    # Takrorlanuvchi L1 xatolarini kuzatish uchun naqsh identifikatorlari
    from app.services.l1 import analyze_l1_interference
    st["l1_pattern_ids"] = sorted({i.get("pattern_id") for i in analyze_l1_interference(text) if i.get("pattern_id")})

    st["current_stage"] = "analysis"
    st["ai_locked"] = False
    return {
        "lesson_id": lesson_id, "status": "submitted", "word_count": payload.word_count, "stage": "analysis",
        "ai_powered": fb.get("ai_powered", False), "score_data": fb["score_data"], "feedback_items": fb["feedback_items"],
        "summary": fb.get("summary", ""), "l1_pattern_ids": st["l1_pattern_ids"],
    }


@router.get("/{lesson_id}/feedback")
def get_feedback(lesson_id: str, current_user: dict = Depends(get_current_user)):
    st = get_lesson_state(_uid(current_user))
    items = st.get("feedback_items")
    if not items:
        fb = generate_production_feedback(st.get("production_text", ""))
        items = fb["feedback_items"]
        st["feedback_items"] = items
        st["actual_rating"] = fb["score_data"]["rubric"]
        st["score"] = fb["score_data"]["total_score"]
    return {"lesson_id": lesson_id, "items": items, "score": st.get("score"), "actual_rating": st.get("actual_rating"),
            "ai_powered": st.get("ai_powered", False), "decisions": st.get("feedback_decisions", {}),
            "rule_note": "Tizim tayyor tuzatilgan matn bermaydi. Har bir izoh sababi ko'rsatilgan. Qaror talabada."}


@router.post("/{lesson_id}/feedback-decision")
def feedback_decision(lesson_id: str, payload: FeedbackDecisionIn, current_user: dict = Depends(get_current_user)):
    """Metakognitiv sikl 3-qadam — BAHOLASH: talaba izohni so'zsiz qabul qilmaydi, qaysi qismini qabul qilganini ASOSLAYDI."""
    st = get_lesson_state(_uid(current_user))
    st.setdefault("feedback_decisions", {})[payload.item_id] = {
        "title": (payload.title or "")[:300], "accepts": bool(payload.accepts), "justification": (payload.justification or "").strip()[:1000]}
    return {"lesson_id": lesson_id, "status": "saved", "decisions": st["feedback_decisions"]}


@router.post("/{lesson_id}/alternative")
async def alternative_version(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """
    Qiyosiy usul (3.2, 5-guruh): tahlil bosqichida AI talabaning matniga MUQOBIL variant taklif qiladi;
    talaba ikki variantni solishtirib farqni asoslaydi. Faqat 4-bosqichda ruxsat (1-qoida).
    """
    st = get_lesson_state(_uid(current_user))
    if st.get("current_stage") == "independent":
        raise TiloraException(code="AI_LOCKED", status_code=status.HTTP_403_FORBIDDEN, details={"tool": "alternative", "stage": "independent"})
    text = (st.get("production_text") or "").strip()
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Avval 3-bosqichda matn yozilishi kerak.")
    if st.get("alternative_text"):
        return {"lesson_id": lesson_id, "alternative": st["alternative_text"], "cached": True, "ai_powered": st.get("alternative_ai", False)}
    prompt = ("Below is a student's text. Rewrite ONLY the first paragraph as an alternative academic version at the same CEFR level, "
              "keeping the student's ideas. Do not add new content. Then list 3 bullet points: what changed and why. Answer in English.\n\n" + text[:4000])
    try:
        res = await ai_service.call_chat([{"role": "system", "content": "You are an ELT writing tutor. Never write the whole essay for the student."},
                                          {"role": "user", "content": prompt}], temperature=0.5, max_tokens=700)
    except Exception:
        res = {"success": False}
    if res.get("success") and res.get("content"):
        st["alternative_text"], st["alternative_ai"] = res["content"].strip(), True
    else:
        # AI mavjud bo'lmasa: qiyoslash uchun talabaning o'z matni + lokal takliflar ro'yxati
        tips = [i.get("suggestion") for i in st.get("feedback_items", []) if i.get("suggestion")][:5]
        st["alternative_text"] = ("AI xizmati hozir mavjud emas. Qiyoslash uchun lokal tahlil takliflari:\n- " + "\n- ".join(tips)) if tips else "AI xizmati hozir mavjud emas; lokal tahlilda muqobil taklif topilmadi."
        st["alternative_ai"] = False
    return {"lesson_id": lesson_id, "alternative": st["alternative_text"], "cached": False, "ai_powered": st["alternative_ai"],
            "instruction": "Ikki variantni solishtiring va farqning sababini o'z so'zlaringiz bilan asoslang (qiyosiy usul)."}


@router.post("/{lesson_id}/comparison")
def comparison_note(lesson_id: str, payload: ComparisonIn, current_user: dict = Depends(get_current_user)):
    st = get_lesson_state(_uid(current_user))
    st["comparison_note"] = payload.note.strip()
    return {"lesson_id": lesson_id, "status": "saved"}


@router.post("/{lesson_id}/self-rating")
def submit_self_rating(lesson_id: str, payload: SelfRatingSubmit, current_user: dict = Depends(get_current_user)):
    """4-QOIDA: Talaba avval o'zini o'zi baholaydi."""
    st = get_lesson_state(_uid(current_user))
    ratings = {}
    for k in ("content", "grammar", "lexis", "coherence"):
        v = payload.ratings.get(k)
        if v is None:
            raise HTTPException(status_code=400, detail=f"'{k}' mezoni bo'yicha baho kiritilmagan.")
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"'{k}' bahosi 1–5 oralig'idagi butun son bo'lishi kerak.")
        if not 1 <= v <= 5:
            raise HTTPException(status_code=400, detail=f"'{k}' bahosi 1–5 oralig'ida bo'lishi kerak.")
        ratings[k] = v
    st["self_rating"] = ratings
    return {"lesson_id": lesson_id, "status": "saved", "self_rating": ratings, "message": "O'z baholashingiz saqlandi. Endi haqiqiy natija ochildi."}


@router.post("/{lesson_id}/ai-self-rate")
def ai_self_rate(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Demo rejim: tizim bahosini o'z bahosi sifatida nusxalash. 4-qoida nuqtai nazaridan tavsiya etilmaydi."""
    st = get_lesson_state(_uid(current_user))
    actual = st.get("actual_rating")
    if not actual:
        fb = generate_production_feedback(st.get("production_text", ""))
        actual = fb["score_data"]["rubric"]
        st["actual_rating"] = actual
        st["score"] = fb["score_data"]["total_score"]
    st["self_rating"] = {k: actual.get(k, 4) for k in ("content", "grammar", "lexis", "coherence")}
    return {"lesson_id": lesson_id, "status": "ai_evaluated", "self_rating": st["self_rating"], "actual_rating": actual,
            "total_score": st.get("score"), "message": "Tizim bahosi o'z bahosi sifatida nusxalandi (demo rejim)."}


@router.post("/{lesson_id}/ai-evaluate")
async def ai_evaluate_production(lesson_id: str, payload: Optional[AiEvaluateRequest] = None, current_user: dict = Depends(get_current_user)):
    """5-bosqich: talaba ishini AI baholaydi (4 mezon, sabab, umumiy ball). O'z bahosiga ta'sir qilmaydi."""
    st = get_lesson_state(_uid(current_user))
    text = (payload.content_text if payload and payload.content_text else st.get("production_text", "")) or ""
    text = _check_text(text)
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Baholash uchun avval 3-bosqichda matn yozilishi kerak.")
    st["production_text"] = text
    from app.services.text_quality import analyze_text_quality
    quality = analyze_text_quality(text)
    task = _task_for(st)
    result = await ai_service.evaluate_writing_rubric(text=text, topic=task.get("title", "Yozma nutq baholash mezonlari"),
                                                      task_prompt=task.get("prompt", ""), quality=quality)
    result["text_quality"] = quality
    st["ai_evaluation"] = result
    st["actual_rating"] = {c: v["score"] for c, v in result["rubric"].items()}
    st["score"] = result["total_score"]
    return {"lesson_id": lesson_id, "status": "evaluated", **result}


@router.get("/{lesson_id}/actual-rating")
def get_actual_rating(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """4-QOIDA: o'z bahosi qo'yilmaguncha haqiqiy natija ko'rsatilmaydi (409). Natija faqat RAQAMLI."""
    st = get_lesson_state(_uid(current_user))
    if not st.get("self_rating"):
        raise TiloraException(code="SELF_RATING_REQUIRED", status_code=status.HTTP_409_CONFLICT,
                              details={"lesson_id": lesson_id, "rule": "4-qoida: Xulosani talaba chiqarishi uchun avval o'z bahosi saqlanishi shart."})
    if not st.get("actual_rating"):
        fb = generate_production_feedback(st.get("production_text", ""))
        st["actual_rating"] = fb["score_data"]["rubric"]
        st["score"] = fb["score_data"]["total_score"]
    gap = _rating_gap(st["self_rating"], st["actual_rating"])
    return {"lesson_id": lesson_id, "self_rating": st["self_rating"], "actual_rating": st["actual_rating"], "rating_gap": gap,
            "final_score": st.get("score"), "ai_evaluation": st.get("ai_evaluation"),
            "rule_note": "Tizim xulosa chiqarmaydi. Farqni ko'rib xulosani o'zingiz yozasiz."}


def _rating_gap(self_r: Dict[str, Any], actual: Dict[str, Any]) -> Optional[float]:
    keys = [k for k in ("content", "grammar", "lexis", "coherence") if k in (self_r or {}) and k in (actual or {})]
    if not keys:
        return None
    return round(sum(abs(float(self_r[k]) - float(actual[k])) for k in keys) / len(keys), 2)


@router.post("/{lesson_id}/reflection")
def submit_reflection(lesson_id: str, payload: ReflectionSubmit, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Metakognitiv sikl 4-qadam — REFLEKSIYA: farq sababi va keyingi maqsad; mashg'ulot yozuvi bazaga saqlanadi."""
    uid = _uid(current_user)
    st = get_lesson_state(uid)
    gap = (payload.gap_explanation or "").strip()[:2000]
    goal = (payload.next_goal or "").strip()[:1000]
    if len(gap) < 5 or len(goal) < 5:
        raise HTTPException(status_code=400, detail="Farq sababi va keyingi maqsad to'ldirilishi shart (4-qoida: xulosani talaba yozadi).")
    if payload.comparison_note:
        st["comparison_note"] = payload.comparison_note.strip()[:2000]
    st["reflection"] = {"gap_explanation": gap, "next_goal": goal}
    st["current_stage"] = "reflection"
    st["ai_locked"] = False

    user = db.query(User).filter(User.id == uid).first()
    decisions = [{"id": k, **v} for k, v in (st.get("feedback_decisions") or {}).items()]
    total_seconds = int(time.time() - st["started_at"]) if st.get("started_at") else 0
    rec = LessonRecord(
        student_id=uid, group_id=user.group_id if user else None, skill=st.get("skill"), task_variant=st.get("variant"),
        scaffold_level=st.get("scaffold_level"), plan_goal=(st.get("plan") or {}).get("goal"), plan_strategy=(st.get("plan") or {}).get("strategy"),
        help_requests=st.get("help_requests", 0), self_checks=st.get("self_checks", 0),
        independent_seconds=st.get("independent_seconds", 0), total_seconds=min(total_seconds, 36000),
        word_count=len((st.get("production_text") or "").split()), production_text=(st.get("production_text") or "")[:20000],
        score=st.get("score"), rubric=st.get("actual_rating"), self_rating=st.get("self_rating"),
        rating_gap=_rating_gap(st.get("self_rating") or {}, st.get("actual_rating") or {}),
        feedback_decisions=decisions, l1_pattern_ids=st.get("l1_pattern_ids") or [], comparison_note=st.get("comparison_note"),
        ai_powered=bool(st.get("ai_powered")), gap_explanation=gap, next_goal=goal,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    reset_lesson_state(uid)
    return {"lesson_id": lesson_id, "status": "completed", "record_id": rec.id, "gap_explanation": gap, "next_goal": goal,
            "message": "Mashg'ulot yakunlandi va yozuv saqlandi. Dinamika bo'limida ko'rishingiz mumkin."}


@router.post("/{lesson_id}/reset")
def reset_lesson(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Mashg'ulotni boshidan boshlash (faqat o'z holati)."""
    reset_lesson_state(_uid(current_user))
    return {"lesson_id": lesson_id, "status": "reset"}
