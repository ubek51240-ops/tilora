from typing import Optional
from fastapi import Request, Depends, status
from app.core.errors import TiloraException
from app.core.deps import get_optional_user


class AILockGuard:
    """
    1-QOIDA: Mustaqil bajarish bosqichida sun'iy intellekt yordami majburiy ravishda o'chiriladi.

    Server tomonda tekshiriladi va 403 AI_LOCKED qaytaradi. Manba ustuvorligi:
      1. Foydalanuvchining serverdagi mashg'ulot holati (app.api.lesson.get_lesson_state) —
         mijoz uni sarlavha bilan o'zgartira olmaydi;
      2. aks holda (holat yo'q) X-Lesson-Stage / X-AI-Locked sarlavhalari (test va demo uchun).
    """
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.blocked_tools = {"generate", "translate", "complete", "answer", "dialog"}

    async def __call__(self, request: Request, user: Optional[dict] = Depends(get_optional_user)):
        if self.tool_name not in self.blocked_tools:
            return True

        is_independent_stage = False
        ai_locked = True

        server_state = None
        if user and user.get("id"):
            from app.api.lesson import peek_lesson_state
            server_state = peek_lesson_state(user["id"])

        if server_state is not None:
            is_independent_stage = (server_state.get("current_stage") == "independent")
            ai_locked = bool(server_state.get("ai_locked", True))
        else:
            headers = request.headers
            if headers.get("X-Lesson-Stage") == "independent":
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
