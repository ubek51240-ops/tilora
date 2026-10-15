from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.config import settings
from app.schemas.all_schemas import AITextRequest
from app.core.ai_lock import blocked_tool
from app.core.deps import get_current_user, require_role
from app.core.ratelimit import SlidingWindowLimiter
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["Sun'iy Intellekt Vositalari"])

# AI so'rovlari pullik tashqi xizmatga boradi: faqat tizimga kirganlar, foydalanuvchi bo'yicha chegara bilan
_ai_limiter = SlidingWindowLimiter(settings.AI_MAX_REQUESTS, settings.AI_WINDOW_SECONDS)
MAX_PROMPT_CHARS = 12000


def ai_quota(current_user: dict = Depends(get_current_user)) -> dict:
    uid = current_user.get("id") or current_user.get("sub") or "anon"
    _ai_limiter.check_and_record(
        f"ai:{uid}",
        f"AI so'rovlari chegarasi oshdi ({settings.AI_MAX_REQUESTS} ta / {settings.AI_WINDOW_SECONDS // 60} daqiqa). Biroz kuting."
    )
    return current_user


def _check_prompt(payload: AITextRequest) -> None:
    if not (payload.prompt or "").strip():
        raise HTTPException(status_code=400, detail="So'rov matni bo'sh.")
    if len(payload.prompt or "") + len(payload.context or "") > MAX_PROMPT_CHARS:
        raise HTTPException(status_code=400, detail=f"So'rov matni {MAX_PROMPT_CHARS} belgidan oshmasligi kerak.")


class ChatMessage(BaseModel):
    role: str = Field("user", pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list, max_length=30)
    prompt: str | None = Field(None, max_length=8000)


_status_cache: Dict[str, Any] = {"at": 0.0, "data": None}


@router.get("/status")
async def get_ai_status(current_user: dict = Depends(get_current_user)):
    """
    AI xizmati holati. Natija 60 soniya keshlanadi (har sahifa yuklanishida provayderga so'rov ketmasin).
    Talaba uchun faqat umumiy holat; admin/o'qituvchi/dasturchi to'liq tafsilotni ko'radi.
    """
    import time
    if not settings.AI_API_KEY:
        data = {"status": "not_configured", "authenticated": False, "quota_status": "unknown",
                "configured_model": settings.AI_MODEL, "message": "AI_API_KEY sozlanmagan (.env)."}
    else:
        now = time.time()
        if _status_cache["data"] is None or now - _status_cache["at"] > 60:
            _status_cache["data"] = await ai_service.check_health()
            _status_cache["at"] = now
        data = _status_cache["data"]
    if current_user.get("role") in ("admin", "teacher", "developer"):
        return data
    return {"status": data.get("status"), "quota_status": data.get("quota_status"), "configured_model": data.get("configured_model")}


@router.post("/generate", dependencies=[blocked_tool("generate")])
async def ai_generate(payload: AITextRequest, current_user: dict = Depends(ai_quota)):
    """Matn va pedagogik ko'mak (scaffolding) generatsiyasi. 1-qoida: Mustaqil bosqichda 403 bloklanadi."""
    _check_prompt(payload)
    return await ai_service.generate_scaffold(payload.prompt, payload.context)


@router.post("/translate", dependencies=[blocked_tool("translate")])
async def ai_translate(payload: AITextRequest, current_user: dict = Depends(ai_quota)):
    """Terminlar va iboralar tarjimasi. 1-qoida: Mustaqil bosqichda 403 bloklanadi."""
    _check_prompt(payload)
    return await ai_service.translate_text(payload.prompt, payload.context)


@router.post("/complete", dependencies=[blocked_tool("complete")])
async def ai_complete(payload: AITextRequest, current_user: dict = Depends(ai_quota)):
    """Matn davomini yozish. 1-qoida: Mustaqil bosqichda 403 bloklanadi."""
    _check_prompt(payload)
    return await ai_service.complete_text(payload.prompt, payload.context)


@router.post("/answer", dependencies=[blocked_tool("answer")])
async def ai_answer(payload: AITextRequest, current_user: dict = Depends(ai_quota)):
    """Pedagogik savollarga javob berish. 1-qoida: Mustaqil bosqichda 403 bloklanadi."""
    _check_prompt(payload)
    return await ai_service.answer_query(payload.prompt, payload.context)


@router.post("/analyze")
async def ai_analyze(payload: AITextRequest, current_user: dict = Depends(ai_quota)):
    """Tahlil bosqichida AI orqali yozma matnni chuqur lingvistik baholash (Ruxsat etilgan)."""
    _check_prompt(payload)
    res = await ai_service.analyze_writing(payload.prompt, payload.context)
    return {
        "tool": "analyze",
        "status": res.get("status", "allowed"),
        "ai_powered": res.get("ai_powered", False),
        "model": res.get("model", ai_service.model),
        "analysis": res.get("analysis"),
        "message": "DeepSeek sun'iy intellekti orqali yozma matn tahlili yakunlandi."
    }


@router.post("/chat")
async def ai_chat(payload: ChatRequest, current_user: dict = Depends(ai_quota)):
    """Erkin pedagogik muloqot va AI bilan maslahatlashish (faqat tizimga kirganlar uchun)."""
    messages = [m.model_dump() for m in payload.messages]
    if not messages and payload.prompt:
        messages = [{"role": "user", "content": payload.prompt}]
    if not messages:
        raise HTTPException(status_code=400, detail="Xabar matni bo'sh.")
    # Mijoz "system" rolini yubora olmaydi — pedagogik yo'riqnoma serverda belgilanadi
    messages = [m for m in messages if m["role"] != "system"]
    system = {"role": "system", "content": (
        "Sen TILORA platformasining pedagogik yordamchisisan. Bo'lajak ingliz tili o'qituvchilariga metodik "
        "maslahat berasan, lekin talabaning mustaqil topshirig'ini uning o'rniga bajarmaysan."
    )}
    return await ai_service.call_chat([system] + messages)
