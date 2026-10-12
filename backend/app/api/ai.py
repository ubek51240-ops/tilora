from fastapi import APIRouter, Depends
from app.schemas.all_schemas import AITextRequest
from app.core.ai_lock import blocked_tool
from app.services.ai_service import ai_service
from typing import Dict, Any

router = APIRouter(prefix="/ai", tags=["Sun'iy Intellekt Vositalari"])

@router.get("/status")
async def get_ai_status():
    """
    Uланган Sun'iy Intellekt (api.b.ai / DeepSeek) xizmati holatini tekshirish.
    """
    health = await ai_service.check_health()
    return health

@router.post("/generate", dependencies=[blocked_tool("generate")])
async def ai_generate(payload: AITextRequest):
    """
    Matn va pedagogik ko'mak (scaffolding) generatsiyasi.
    1-qoida: Mustaqil bosqichda 403 bloklanadi.
    """
    res = await ai_service.generate_scaffold(payload.prompt, payload.context)
    return res

@router.post("/translate", dependencies=[blocked_tool("translate")])
async def ai_translate(payload: AITextRequest):
    """
    Terminlar va iboralar tarjimasi.
    1-qoida: Mustaqil bosqichda 403 bloklanadi.
    """
    res = await ai_service.translate_text(payload.prompt, payload.context)
    return res

@router.post("/complete", dependencies=[blocked_tool("complete")])
async def ai_complete(payload: AITextRequest):
    """
    Matn davomini yozish / mantiqiy davom ettirish.
    1-qoida: Mustaqil bosqichda 403 bloklanadi.
    """
    res = await ai_service.complete_text(payload.prompt, payload.context)
    return res

@router.post("/answer", dependencies=[blocked_tool("answer")])
async def ai_answer(payload: AITextRequest):
    """
    Pedagogik savollarga javob berish.
    1-qoida: Mustaqil bosqichda 403 bloklanadi.
    """
    res = await ai_service.answer_query(payload.prompt, payload.context)
    return res

@router.post("/analyze")
async def ai_analyze(payload: AITextRequest):
    """
    Tahlil bosqichida AI orqali yozma matnni chuqur lingvistik baholash (Ruxsat etilgan).
    """
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
async def ai_chat(payload: Dict[str, Any]):
    """
    Erkin pedagogik muloqot va AI bilan maslahatlashish (Test va ta'limiy yordamchi).
    """
    messages = payload.get("messages", [])
    if not messages and "prompt" in payload:
        messages = [{"role": "user", "content": payload["prompt"]}]
    
    res = await ai_service.call_chat(messages)
    return res
