from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/feedback", tags=["Izohlar"])

class FeedbackResponseSubmit(BaseModel):
    item_id: str
    student_accepts: bool
    student_note: Optional[str] = None

@router.post("/response")
def respond_to_feedback(payload: FeedbackResponseSubmit):
    return {
        "status": "recorded",
        "item_id": payload.item_id,
        "student_accepts": payload.student_accepts,
        "student_note": payload.student_note,
        "message": "Munosabatingiz qayd etildi. Qaror sizniki."
    }
