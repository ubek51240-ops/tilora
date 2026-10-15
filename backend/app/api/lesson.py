"""
5 bosqichli mashg'ulot API.

Mashg'ulot holati har bir foydalanuvchi uchun ALOHIDA saqlanadi (xotirada, user_id bo'yicha).
Avval bitta umumiy LESSON_CACHE barcha foydalanuvchilar uchun umumiy edi: bir talabaning matni
va bahosi boshqa talabaga ko'rinib qolardi. Endi holatga faqat token egasi kira oladi.
"""
import copy
import threading
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.all_schemas import ProductionSubmit, SelfRatingSubmit, ReflectionSubmit
from app.core.deps import get_current_user
from app.core.errors import TiloraException
from app.services.feedback import generate_production_feedback, analyze_production_feedback_async
from app.services.ai_service import ai_service
from app.services.lesson_tasks import get_task, list_tasks, DEFAULT_SKILL
from pydantic import BaseModel, Field


class AiEvaluateRequest(BaseModel):
    content_text: Optional[str] = Field(None, max_length=20000)


router = APIRouter(prefix="/lesson", tags=["Mashg'ulot"])

MAX_PRODUCTION_CHARS = 20000

_DEFAULT_STATE: Dict[str, Any] = {
    "current_stage": "intro",
    "ai_locked": False,
    "skill": DEFAULT_SKILL,
    "production_text": "",
    "self_rating": None,
    "actual_rating": None,
    "score": None,
    "feedback_items": [],
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
def get_lesson_task(lesson_id: str, skill: Optional[str] = None):
    """Topshiriq sharti — 1-qoida bo'yicha mustaqil bosqichda ham OCHIQ qoladi."""
    task = get_task(skill or DEFAULT_SKILL)
    return {"lesson_id": lesson_id, **task}


@router.get("/{lesson_id}")
def get_lesson_status(lesson_id: str, current_user: dict = Depends(get_current_user)):
    st = get_lesson_state(_uid(current_user))
    task = get_task(st.get("skill") or DEFAULT_SKILL)
    return {
        "lesson_id": lesson_id,
        "skill": st.get("skill"),
        "current_week": task.get("week_range", "5-6-hafta"),
        "stage": st["current_stage"],
        "ai_locked": st["ai_locked"],
        "duration_minutes": task.get("duration_minutes", 30),
        "has_production": bool(st.get("production_text")),
        "has_self_rating": bool(st.get("self_rating")),
    }


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
    return {
        "lesson_id": lesson_id,
        "current_stage": st["current_stage"],
        "ai_locked": st["ai_locked"]
    }


@router.post("/{lesson_id}/production")
async def submit_production(
    lesson_id: str,
    payload: ProductionSubmit,
    current_user: dict = Depends(get_current_user)
):
    st = get_lesson_state(_uid(current_user))
    text = _check_text(payload.content_text)
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Matn juda qisqa. Kamida bir necha gap yozing.")
    st["production_text"] = text
    st["self_rating"] = None  # yangi ish — eski o'z bahosi va AI bahosi bekor
    st["ai_evaluation"] = None

    # 4-bosqich: Matnni to'liq o'qib, AI va L1 izohlari hamda dinamik rubrika hisoblash
    fb = await analyze_production_feedback_async(text, lesson_id)
    st["actual_rating"] = fb["score_data"]["rubric"]
    st["score"] = fb["score_data"]["total_score"]
    st["feedback_items"] = fb["feedback_items"]
    st["ai_powered"] = fb.get("ai_powered", False)

    # Avtomatik tahlil bosqichiga o'tkazish (AI qulfi ochiladi)
    st["current_stage"] = "analysis"
    st["ai_locked"] = False

    return {
        "lesson_id": lesson_id,
        "status": "submitted",
        "word_count": payload.word_count,
        "stage": "analysis",
        "ai_powered": fb.get("ai_powered", False),
        "score_data": fb["score_data"],
        "feedback_items": fb["feedback_items"],
        "summary": fb.get("summary", "")
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

    return {
        "lesson_id": lesson_id,
        "items": items,
        "score": st.get("score"),
        "actual_rating": st.get("actual_rating"),
        "ai_powered": st.get("ai_powered", False),
        "rule_note": "Tizim tayyor tuzatilgan matn bermaydi. Har bir izoh sababi ko'rsatilgan. Qaror talabada."
    }


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
    return {
        "lesson_id": lesson_id,
        "status": "saved",
        "self_rating": ratings,
        "message": "O'z baholashingiz saqlandi. Endi haqiqiy natija ochildi."
    }


@router.post("/{lesson_id}/ai-self-rate")
def ai_self_rate(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """
    Tizim bahosini o'z bahosi sifatida nusxalash (demo/tezkor rejim).
    4-qoida nuqtai nazaridan tavsiya etilmaydi — talaba avval o'zi baholashi kerak.
    """
    st = get_lesson_state(_uid(current_user))
    actual = st.get("actual_rating")
    if not actual:
        prod_text = st.get("production_text", "")
        fb = generate_production_feedback(prod_text)
        actual = fb["score_data"]["rubric"]
        st["actual_rating"] = actual
        st["score"] = fb["score_data"]["total_score"]

    st["self_rating"] = {
        "content": actual.get("content", 4),
        "grammar": actual.get("grammar", 4),
        "lexis": actual.get("lexis", 4),
        "coherence": actual.get("coherence", 4)
    }
    return {
        "lesson_id": lesson_id,
        "status": "ai_evaluated",
        "self_rating": st["self_rating"],
        "actual_rating": actual,
        "total_score": st.get("score"),
        "message": "Tizim bahosi o'z bahosi sifatida nusxalandi (demo rejim)."
    }


@router.post("/{lesson_id}/ai-evaluate")
async def ai_evaluate_production(lesson_id: str, payload: Optional[AiEvaluateRequest] = None,
                                 current_user: dict = Depends(get_current_user)):
    """
    5-bosqich: talaba ishini AI baholaydi (4 mezon, har biriga sabab, umumiy ball, tavsiyalar).
    Talabaning o'z bahosi (1-qadam) bunga ta'sir qilmaydi va u bilan aralashtirilmaydi.
    """
    st = get_lesson_state(_uid(current_user))
    text = (payload.content_text if payload and payload.content_text else st.get("production_text", "")) or ""
    text = _check_text(text)
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Baholash uchun avval 3-bosqichda matn yozilishi kerak.")
    st["production_text"] = text
    from app.services.text_quality import analyze_text_quality
    quality = analyze_text_quality(text)
    task = get_task(st.get("skill") or DEFAULT_SKILL)
    result = await ai_service.evaluate_writing_rubric(
        text=text,
        topic=task.get("title", "Yozma nutq baholash mezonlari"),
        task_prompt=task.get("prompt", ""),
        quality=quality
    )
    result["text_quality"] = quality
    st["ai_evaluation"] = result
    st["actual_rating"] = {c: v["score"] for c, v in result["rubric"].items()}
    st["score"] = result["total_score"]
    return {"lesson_id": lesson_id, "status": "evaluated", **result}


@router.get("/{lesson_id}/actual-rating")
def get_actual_rating(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """
    4-QOIDA: Agar talaba o'z bahosini qo'ymagan bo'lsa, haqiqiy natija ko'rsatilmaydi (409 Conflict).
    Natija faqat RAQAMLI bo'ladi, tizim hech qanday xulosa matni yozmaydi!
    """
    st = get_lesson_state(_uid(current_user))
    if not st.get("self_rating"):
        raise TiloraException(
            code="SELF_RATING_REQUIRED",
            status_code=status.HTTP_409_CONFLICT,
            details={"lesson_id": lesson_id, "rule": "4-qoida: Xulosani talaba chiqarishi uchun avval o'z bahosi saqlanishi shart."}
        )
    if not st.get("actual_rating"):
        fb = generate_production_feedback(st.get("production_text", ""))
        st["actual_rating"] = fb["score_data"]["rubric"]
        st["score"] = fb["score_data"]["total_score"]

    return {
        "lesson_id": lesson_id,
        "self_rating": st["self_rating"],
        "actual_rating": st["actual_rating"],
        "final_score": st.get("score"),
        "ai_evaluation": st.get("ai_evaluation"),
        "rule_note": "Tizim xulosa chiqarmaydi. Farqni ko'rib xulosani o'zingiz yozasiz."
    }


@router.post("/{lesson_id}/reflection")
def submit_reflection(lesson_id: str, payload: ReflectionSubmit, current_user: dict = Depends(get_current_user)):
    st = get_lesson_state(_uid(current_user))
    gap = (payload.gap_explanation or "").strip()[:2000]
    goal = (payload.next_goal or "").strip()[:1000]
    if len(gap) < 5 or len(goal) < 5:
        raise HTTPException(status_code=400, detail="Farq sababi va keyingi maqsad to'ldirilishi shart (4-qoida: xulosani talaba yozadi).")
    st["reflection"] = {"gap_explanation": gap, "next_goal": goal}
    st["current_stage"] = "reflection"
    st["ai_locked"] = False
    return {
        "lesson_id": lesson_id,
        "status": "completed",
        "gap_explanation": gap,
        "next_goal": goal,
        "message": "Mashg'ulot muvaffaqiyatli yakunlandi. Profilingiz yangilandi."
    }


@router.post("/{lesson_id}/reset")
def reset_lesson(lesson_id: str, current_user: dict = Depends(get_current_user)):
    """Mashg'ulotni boshidan boshlash (faqat o'z holati)."""
    reset_lesson_state(_uid(current_user))
    return {"lesson_id": lesson_id, "status": "reset"}
