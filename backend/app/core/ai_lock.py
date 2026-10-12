from fastapi import Request, Depends, status
from app.core.errors import TiloraException

class AILockGuard:
    """
    1-QOIDA: Mustaqil bajarish bosqichida sun'iy intellekt yordami majburiy ravishda o'chiriladi.
    Server tomondan tekshiriladi va 403 AI_LOCKED qaytaradi.
    """
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.blocked_tools = {"generate", "translate", "complete", "answer"}

    async def __call__(self, request: Request):
        # Agar vosita bloklanadiganlar ro'yxatida bo'lmasa, ruxsat
        if self.tool_name not in self.blocked_tools:
            return True
            
        # Joriy sessiya / bosqich holatini tekshirish
        # Foydalanuvchi hozir mustaqil bosqichdami va ai_locked yoqilganmi?
        state = getattr(request.state, "lesson_state", None)
        headers = request.headers
        
        # Test va jonli so'rovlar uchun header yoki state tekshiruvi
        is_independent_stage = False
        ai_locked = True # Standart holatda mustaqil bosqichda yoqilgan
        
        if state:
            is_independent_stage = (state.get("stage") == "independent")
            ai_locked = state.get("ai_locked", True)
        elif headers.get("X-Lesson-Stage") == "independent":
            is_independent_stage = True
            ai_locked = (headers.get("X-AI-Locked", "true").lower() == "true")
            
        if is_independent_stage and ai_locked:
            raise TiloraException(
                code="AI_LOCKED",
                status_code=status.HTTP_403_FORBIDDEN,
                details={
                    "tool": self.tool_name,
                    "stage": "independent",
                    "reason": "1-qoida: Talaba o'z javobini o'zi yaratmaguncha tayyor javob yoki generatsiya berilmaydi."
                }
            )
            
        return True

def blocked_tool(tool_name: str):
    """FastAPI Depends uchun helper."""
    return Depends(AILockGuard(tool_name))
