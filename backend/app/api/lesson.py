from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.entities import Lesson, LessonStage, StudentProduction, FeedbackItem, MetacognitiveEntry
from app.schemas.all_schemas import ProductionSubmit, SelfRatingSubmit, ReflectionSubmit
from app.core.deps import get_current_user
from app.core.errors import TiloraException
from app.services.feedback import generate_production_feedback, analyze_production_feedback_async
from app.services.ai_service import ai_service
from pydantic import BaseModel


class AiEvaluateRequest(BaseModel):
    content_text: Optional[str] = None



router = APIRouter(prefix="/lesson", tags=["Mashg'ulot"])

@router.post("/{lesson_id}/text-quality")
def check_text_quality(lesson_id: str, payload: AiEvaluateRequest):
    """3-bosqich: lokal (AI'siz) matn sifati tekshiruvi — ma'nosiz harflar, tushunarsiz so'z va gaplar.
    Javob bermaydi, tuzatmaydi; faqat nechta shubhali so'z borligini ko'rsatadi (1-qoida buzilmaydi)."""
    from app.services.text_quality import analyze_text_quality
    q = analyze_text_quality(payload.content_text or "")
    return {"lesson_id": lesson_id, "ai_used": False, **q}

# Vaqtinchalik xotira (test va tezkor mahalliy demonstratsiya uchun)
LESSON_CACHE = {
    "current_stage": "independent",
    "ai_locked": True,
    "production_text": "",
    "self_rating": None,
    "actual_rating": {
        "content": 4,
        "grammar": 3,
        "lexis": 4,
        "coherence": 4
    },
    "score": 75,
    "feedback_items": [],
    "ai_powered": False,
    "ai_evaluation": None
}

@router.get("/{lesson_id}")
def get_lesson_status(lesson_id: str):
    return {
        "lesson_id": lesson_id,
        "skill": "writing",
        "current_week": "5-6-hafta",
        "stage": LESSON_CACHE["current_stage"],
        "ai_locked": LESSON_CACHE["ai_locked"],
        "duration_minutes": 30,
        "time_remaining_seconds": 1104
    }

@router.get("/{lesson_id}/task")
def get_lesson_task(lesson_id: str):
    return {
        "lesson_id": lesson_id,
        "title": "Yozma nutq: dars tahlili va baholash mezonlari",
        "prompt": "O'quvchilarning yozma nutqini baholashda qanday mezonlardan foydalanish mumkin? O'z fikringizni 150–180 so'zda ilmiy-metodik bayon eting.",
        "scaffold_level": "full",
        "word_count_min": 150,
        "word_count_max": 200
    }

@router.post("/{lesson_id}/stage/next")
def next_stage(lesson_id: str, target_stage: Optional[str] = None):
    stages = ["intro", "preparation", "independent", "analysis", "reflection"]
    curr = LESSON_CACHE["current_stage"]
    if target_stage and target_stage in stages:
        LESSON_CACHE["current_stage"] = target_stage
    else:
        idx = stages.index(curr) if curr in stages else 0
        LESSON_CACHE["current_stage"] = stages[min(len(stages) - 1, idx + 1)]
        
    LESSON_CACHE["ai_locked"] = (LESSON_CACHE["current_stage"] == "independent")
    return {
        "lesson_id": lesson_id,
        "current_stage": LESSON_CACHE["current_stage"],
        "ai_locked": LESSON_CACHE["ai_locked"]
    }

@router.post("/{lesson_id}/production")
async def submit_production(
    lesson_id: str,
    payload: ProductionSubmit,
    authorization: Optional[str] = Header(None)
):
    LESSON_CACHE["production_text"] = payload.content_text
    
    # 4-bosqich: Matnni to'liq o'qib, AI va L1 izohlari hamda dinamik rubrika hisoblash
    fb = await analyze_production_feedback_async(payload.content_text, lesson_id)
    LESSON_CACHE["actual_rating"] = fb["score_data"]["rubric"]
    LESSON_CACHE["score"] = fb["score_data"]["total_score"]
    LESSON_CACHE["feedback_items"] = fb["feedback_items"]
    LESSON_CACHE["ai_powered"] = fb.get("ai_powered", False)
    
    # Avtomatik tahlil bosqichiga o'tkazish
    LESSON_CACHE["current_stage"] = "analysis"
    LESSON_CACHE["ai_locked"] = False
    
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
def get_feedback(lesson_id: str):
    items = LESSON_CACHE.get("feedback_items")
    if not items:
        fb = generate_production_feedback(LESSON_CACHE.get("production_text", ""))
        items = fb["feedback_items"]
        LESSON_CACHE["feedback_items"] = items
        LESSON_CACHE["actual_rating"] = fb["score_data"]["rubric"]
        LESSON_CACHE["score"] = fb["score_data"]["total_score"]
        
    return {
        "lesson_id": lesson_id,
        "items": items,
        "score": LESSON_CACHE.get("score", 75),
        "actual_rating": LESSON_CACHE.get("actual_rating"),
        "ai_powered": LESSON_CACHE.get("ai_powered", False),
        "rule_note": "Tizim tayyor tuzatilgan matn bermaydi. Har bir izoh sababi ko'rsatilgan. Qaror talabada."
    }

@router.post("/{lesson_id}/self-rating")
def submit_self_rating(lesson_id: str, payload: SelfRatingSubmit):
    """
    4-QOIDA: Talaba avval o'zini o'zi baholaydi.
    """
    LESSON_CACHE["self_rating"] = payload.ratings
    return {
        "lesson_id": lesson_id,
        "status": "saved",
        "self_rating": payload.ratings,
        "message": "O'z baholashingiz saqlandi. Endi haqiqiy natija ochildi."
    }

@router.post("/{lesson_id}/ai-self-rate")
def ai_self_rate(lesson_id: str):
    """
    1-qadam · O'z bahosini (Metakognitiv baholash) AI natijasidan kelib chiqib avtomatik shakllantirish.
    """
    actual = LESSON_CACHE.get("actual_rating")
    if not actual:
        prod_text = LESSON_CACHE.get("production_text", "")
        fb = generate_production_feedback(prod_text)
        actual = fb["score_data"]["rubric"]
        LESSON_CACHE["actual_rating"] = actual
        LESSON_CACHE["score"] = fb["score_data"]["total_score"]

    LESSON_CACHE["self_rating"] = {
        "content": actual.get("content", 4),
        "grammar": actual.get("grammar", 4),
        "lexis": actual.get("lexis", 4),
        "coherence": actual.get("coherence", 4)
    }
    return {
        "lesson_id": lesson_id,
        "status": "ai_evaluated",
        "self_rating": LESSON_CACHE["self_rating"],
        "actual_rating": actual,
        "total_score": LESSON_CACHE.get("score", 75),
        "message": "1-qadam (Metakognitiv baholash) AI tahlili natijalaridan kelib chiqib muvaffaqiyatli baholandi."
    }

@router.post("/{lesson_id}/ai-evaluate")
async def ai_evaluate_production(lesson_id: str, payload: Optional[AiEvaluateRequest] = None):
    """
    5-bosqich: talaba ishini AI baholaydi (4 mezon, har biriga sabab, umumiy ball, tavsiyalar).
    Talabaning o'z bahosi (1-qadam) bunga ta'sir qilmaydi va u bilan aralashtirilmaydi.
    """
    text = (payload.content_text if payload and payload.content_text else LESSON_CACHE.get("production_text", "")) or ""
    text = text.strip()
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Baholash uchun avval 3-bosqichda matn yozilishi kerak.")
    LESSON_CACHE["production_text"] = text
    from app.services.text_quality import analyze_text_quality
    quality = analyze_text_quality(text)
    result = await ai_service.evaluate_writing_rubric(
        text=text,
        topic="Yozma nutq baholash mezonlari",
        task_prompt="O'quvchilarning yozma nutqini baholashda qanday mezonlardan foydalanish mumkin? 150–180 so'z.",
        quality=quality
    )
    result["text_quality"] = quality
    LESSON_CACHE["ai_evaluation"] = result
    LESSON_CACHE["actual_rating"] = {c: v["score"] for c, v in result["rubric"].items()}
    LESSON_CACHE["score"] = result["total_score"]
    return {"lesson_id": lesson_id, "status": "evaluated", **result}

@router.get("/{lesson_id}/actual-rating")
def get_actual_rating(lesson_id: str):
    """
    4-QOIDA: Agar talaba o'z bahosini qo'ymagan bo'lsa, haqiqiy natija ko'rsatilmaydi (409 Conflict).
    Natija faqat RAQAMLI bo'ladi, tizim hech qanday xulosa matni yozmaydi!
    """
    if not LESSON_CACHE.get("self_rating"):
        raise TiloraException(
            code="SELF_RATING_REQUIRED",
            status_code=status.HTTP_409_CONFLICT,
            details={"lesson_id": lesson_id, "rule": "4-qoida: Xulosani talaba chiqarishi uchun avval o'z bahosi saqlanishi shart."}
        )
        
    return {
        "lesson_id": lesson_id,
        "self_rating": LESSON_CACHE["self_rating"],
        "actual_rating": LESSON_CACHE["actual_rating"],
        "final_score": LESSON_CACHE.get("score", 73),
        "ai_evaluation": LESSON_CACHE.get("ai_evaluation"),
        "rule_note": "Tizim xulosa chiqarmaydi. Farqni ko'rib xulosani o'zingiz yozasiz."
    }

@router.post("/{lesson_id}/reflection")
def submit_reflection(lesson_id: str, payload: ReflectionSubmit):
    return {
        "lesson_id": lesson_id,
        "status": "completed",
        "gap_explanation": payload.gap_explanation,
        "next_goal": payload.next_goal,
        "message": "Mashg'ulot muvaffaqiyatli yakunlandi. Profilingiz yangilandi."
    }
