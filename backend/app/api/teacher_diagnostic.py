"""
O'qituvchi va super admin uchun diagnostika testi va anketa savollari banki
(yuklash, tahrirlash, audio, fanga biriktirish).

- O'qituvchi: faqat o'z savollari va o'z fanlari.
- Admin: barcha o'qituvchilarning savollari va fanlari (qo'lda kerakli fanga qo'shadi).
- subject_id = NULL -> "umumiy" savol, barcha fanlarda ko'rinadi.

Talaba tomonidagi /student/diagnostic/questions va /student/survey/questions
shu bankdan o'qiydi (app/services/diagnostic_bank.py).
"""
import json
from typing import Optional, List, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.entities import CustomDiagnosticQuestion, CustomSurveyQuestion, TeacherSubject, User
from app.services import diagnostic_bank as bank
from app.services import tts_service as tts

router = APIRouter(
    prefix="/teacher",
    tags=["O'qituvchi: Diagnostika banki"],
    dependencies=[Depends(require_role(["teacher", "admin"]))],
)


def _tid(user: dict) -> str:
    return user.get("id") or user.get("sub")


def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


# ================================================================
# Sxemalar
# ================================================================

class DiagQuestionIn(BaseModel):
    skill: str = "reading"
    cefr_level: str = "B1"
    instruction: Optional[str] = None
    question: str
    options: List[str]
    correct_index: int = 0
    rationale: Optional[str] = None
    is_audio: bool = False
    audio_text: Optional[str] = None
    audio_url: Optional[str] = None
    is_active: Optional[bool] = True
    question_order: Optional[int] = None
    subject_id: Optional[str] = None  # None / "" -> umumiy


class SurveyQuestionIn(BaseModel):
    dimension: str = "anxiety"
    prompt_uz: str
    prompt_en: Optional[str] = None
    weight: float = 1.0
    is_active: Optional[bool] = True
    question_order: Optional[int] = None
    subject_id: Optional[str] = None


class ReorderIn(BaseModel):
    ids: List[str]


class AssignSubjectIn(BaseModel):
    subject_id: Optional[str] = None  # None -> umumiy


class BulkAssignIn(BaseModel):
    ids: List[str]
    subject_id: Optional[str] = None


# ================================================================
# Yordamchilar
# ================================================================

def _owned(query, model, user: dict):
    """Admin hamma savolni ko'radi, o'qituvchi faqat o'zinikini."""
    if _is_admin(user):
        return query
    return query.filter(model.teacher_id == _tid(user))


def _next_order(db: Session, model, teacher_id: str) -> int:
    last = db.query(model).filter(model.teacher_id == teacher_id).order_by(model.question_order.desc()).first()
    return (last.question_order or 0) + 1 if last else 1


def _get_diag(db: Session, qid: str, user: dict) -> CustomDiagnosticQuestion:
    q = _owned(db.query(CustomDiagnosticQuestion).filter(CustomDiagnosticQuestion.id == qid), CustomDiagnosticQuestion, user).first()
    if not q:
        raise HTTPException(status_code=404, detail="Diagnostika savoli topilmadi yoki sizga tegishli emas.")
    return q


def _get_survey(db: Session, sid: str, user: dict) -> CustomSurveyQuestion:
    s = _owned(db.query(CustomSurveyQuestion).filter(CustomSurveyQuestion.id == sid), CustomSurveyQuestion, user).first()
    if not s:
        raise HTTPException(status_code=404, detail="Anketa savoli topilmadi yoki sizga tegishli emas.")
    return s


def _resolve_subject(db: Session, subject_id: Optional[str], user: dict) -> Optional[str]:
    """Fan mavjudligini va (admin bo'lmasa) o'qituvchiga tegishliligini tekshiradi. Bo'sh -> None (umumiy)."""
    if not subject_id or not str(subject_id).strip():
        return None
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi.")
    if not _is_admin(user) and subj.teacher_id != _tid(user):
        raise HTTPException(status_code=403, detail="Bu fan sizga tegishli emas. Faqat o'z fanlaringizga savol biriktira olasiz.")
    return subj.id


async def _read_json_list(file: UploadFile) -> List[Dict[str, Any]]:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Fayl bo'sh.")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"JSON fayl o'qilmadi: {e}")
    if isinstance(data, dict):
        data = data.get("questions") or data.get("items") or []
    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=400, detail="JSON ichida savollar ro'yxati (massiv) topilmadi.")
    return data


def _subject_names(db: Session, rows) -> Dict[str, str]:
    ids = {r.subject_id for r in rows if r.subject_id}
    if not ids:
        return {}
    return {s.id: s.name for s in db.query(TeacherSubject).filter(TeacherSubject.id.in_(ids)).all()}


def _teacher_names(db: Session, rows) -> Dict[str, str]:
    ids = {r.teacher_id for r in rows if r.teacher_id}
    if not ids:
        return {}
    return {u.id: u.full_name for u in db.query(User).filter(User.id.in_(ids)).all()}


def _scoped_rows(db: Session, model, user: dict, subject_id: Optional[str], all_subjects: bool):
    q = _owned(db.query(model), model, user)
    if not all_subjects:
        q = bank._subject_scope(q, model, subject_id)
    return q.order_by(model.question_order, model.created_at).all()


def _summary(db: Session, model, user: dict, subject_id: Optional[str], all_subjects: bool, to_dict, defaults_count: int) -> Dict[str, Any]:
    rows = _scoped_rows(db, model, user, subject_id, all_subjects)
    snames = _subject_names(db, rows)
    tnames = _teacher_names(db, rows) if _is_admin(user) else {}
    items = []
    for r in rows:
        d = to_dict(r)
        d["subject_name"] = snames.get(r.subject_id) if r.subject_id else None
        if tnames:
            d["teacher_name"] = tnames.get(r.teacher_id, "")
        items.append(d)
    active = [r for r in rows if r.is_active]
    return {
        "questions": items,
        "total": len(rows),
        "active_count": len(active),
        "using_defaults": len(active) == 0,
        "defaults_count": defaults_count,
        "subject_id": subject_id,
    }


def _diag_summary(db, user, subject_id=None, all_subjects=False):
    return _summary(db, CustomDiagnosticQuestion, user, subject_id, all_subjects, bank.diag_to_dict, len(bank.default_diagnostic_questions()))


def _survey_summary(db, user, subject_id=None, all_subjects=False):
    return _summary(db, CustomSurveyQuestion, user, subject_id, all_subjects, bank.survey_to_dict, len(bank.default_survey_questions()))


# ================================================================
# 0. FANLAR RO'YXATI (o'qituvchi: o'z fanlari, admin: barcha)
# ================================================================

@router.get("/diagnostic/subjects")
def list_bank_subjects(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Savol biriktirish uchun fanlar ro'yxati va har birida nechta savol borligi."""
    q = db.query(TeacherSubject)
    if not _is_admin(current_user):
        q = q.filter(TeacherSubject.teacher_id == _tid(current_user))
    subjects = q.order_by(TeacherSubject.created_at.desc()).all()
    tnames = _teacher_names(db, subjects)

    def _count(model, sid):
        return db.query(model).filter(model.subject_id == sid).count()

    out = []
    for s in subjects:
        out.append({
            "id": s.id,
            "name": s.name,
            "code": s.code or "",
            "group_name": s.group_name or "",
            "teacher_id": s.teacher_id,
            "teacher_name": tnames.get(s.teacher_id, ""),
            "diag_count": _count(CustomDiagnosticQuestion, s.id),
            "survey_count": _count(CustomSurveyQuestion, s.id),
        })
    general_scope = _owned(db.query(CustomDiagnosticQuestion), CustomDiagnosticQuestion, current_user)
    general_survey = _owned(db.query(CustomSurveyQuestion), CustomSurveyQuestion, current_user)
    return {
        "subjects": out,
        "general": {
            "diag_count": general_scope.filter(CustomDiagnosticQuestion.subject_id.is_(None)).count(),
            "survey_count": general_survey.filter(CustomSurveyQuestion.subject_id.is_(None)).count(),
        },
        "is_admin": _is_admin(current_user),
    }


# ================================================================
# 1. DIAGNOSTIKA TEST SAVOLLARI
# ================================================================

@router.get("/diagnostic/questions")
def list_diag_questions(
    subject_id: Optional[str] = Query(None, description="Fan ID; bo'sh -> umumiy savollar"),
    all_subjects: bool = Query(False, description="true -> barcha fanlar va umumiy"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return _diag_summary(db, current_user, subject_id or None, all_subjects)


@router.get("/diagnostic/questions/defaults")
def get_default_diag_questions():
    return {"questions": bank.default_diagnostic_questions()}


@router.post("/diagnostic/questions")
def create_diag_question(payload: DiagQuestionIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    teacher_id = _tid(current_user)
    subject_id = _resolve_subject(db, payload.subject_id, current_user)
    try:
        data = bank.normalize_diag_payload(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    q = CustomDiagnosticQuestion(
        teacher_id=teacher_id,
        subject_id=subject_id,
        question_order=payload.question_order or _next_order(db, CustomDiagnosticQuestion, teacher_id),
        is_active=payload.is_active if payload.is_active is not None else True,
        **data,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"status": "success", "message": "Savol qo'shildi.", "question": bank.diag_to_dict(q)}


@router.put("/diagnostic/questions/{qid}")
def update_diag_question(qid: str, payload: DiagQuestionIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    q = _get_diag(db, qid, current_user)
    try:
        data = bank.normalize_diag_payload(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data.pop("audio_url", None)  # audio faqat upload endpointi orqali
    for k, v in data.items():
        setattr(q, k, v)
    if payload.is_active is not None:
        q.is_active = payload.is_active
    if payload.question_order is not None:
        q.question_order = payload.question_order
    if "subject_id" in payload.model_fields_set:
        q.subject_id = _resolve_subject(db, payload.subject_id, current_user)
    db.commit()
    db.refresh(q)
    return {"status": "success", "message": "Savol yangilandi.", "question": bank.diag_to_dict(q)}


@router.patch("/diagnostic/questions/{qid}/subject")
def assign_diag_subject(qid: str, payload: AssignSubjectIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Savolni boshqa fanga ko'chirish (yoki umumiy qilish)."""
    q = _get_diag(db, qid, current_user)
    q.subject_id = _resolve_subject(db, payload.subject_id, current_user)
    db.commit()
    db.refresh(q)
    return {"status": "success", "message": "Savol fanga biriktirildi." if q.subject_id else "Savol umumiy qilindi.", "question": bank.diag_to_dict(q)}


@router.post("/diagnostic/questions/assign-subject")
def bulk_assign_diag_subject(payload: BulkAssignIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    subject_id = _resolve_subject(db, payload.subject_id, current_user)
    n = 0
    for qid in payload.ids:
        q = _owned(db.query(CustomDiagnosticQuestion).filter(CustomDiagnosticQuestion.id == qid), CustomDiagnosticQuestion, current_user).first()
        if q:
            q.subject_id = subject_id
            n += 1
    db.commit()
    return {"status": "success", "message": f"{n} ta savol {'fanga biriktirildi' if subject_id else 'umumiy qilindi'}.", "updated": n}


@router.patch("/diagnostic/questions/{qid}/toggle")
def toggle_diag_question(qid: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    q = _get_diag(db, qid, current_user)
    q.is_active = not bool(q.is_active)
    db.commit()
    return {"status": "success", "is_active": q.is_active}


@router.delete("/diagnostic/questions/{qid}")
def delete_diag_question(qid: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    q = _get_diag(db, qid, current_user)
    bank.delete_audio_file(q.audio_url)
    db.delete(q)
    db.commit()
    return {"status": "success", "message": "Savol o'chirildi."}


@router.delete("/diagnostic/questions")
def delete_all_diag_questions(
    subject_id: Optional[str] = Query(None),
    all_subjects: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Joriy ko'rinishdagi (tanlangan fan yoki umumiy) savollarni o'chirish."""
    rows = _scoped_rows(db, CustomDiagnosticQuestion, current_user, subject_id or None, all_subjects)
    if subject_id and not all_subjects:
        rows = [r for r in rows if r.subject_id == subject_id]  # umumiylarga tegmaymiz
    for r in rows:
        bank.delete_audio_file(r.audio_url)
        db.delete(r)
    db.commit()
    return {"status": "success", "message": f"{len(rows)} ta savol o'chirildi.", "deleted": len(rows)}


@router.post("/diagnostic/questions/reorder")
def reorder_diag_questions(payload: ReorderIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    for idx, qid in enumerate(payload.ids, 1):
        _owned(db.query(CustomDiagnosticQuestion).filter(CustomDiagnosticQuestion.id == qid), CustomDiagnosticQuestion, current_user) \
            .update({"question_order": idx}, synchronize_session=False)
    db.commit()
    return {"status": "success"}


@router.post("/diagnostic/questions/{qid}/audio")
async def upload_diag_audio(
    qid: str,
    file: UploadFile = File(...),
    audio_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Savolga audio fayl biriktirish (mp3/wav/ogg/m4a/aac/webm/flac, 15 MB gacha)."""
    q = _get_diag(db, qid, current_user)
    content = await file.read()
    try:
        saved = bank.save_audio_file(content, file.filename, q.teacher_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    bank.delete_audio_file(q.audio_url)
    q.audio_url = saved["url"]
    q.audio_filename = saved["filename"]
    q.is_audio = True
    if audio_text is not None and audio_text.strip():
        q.audio_text = audio_text.strip()
    db.commit()
    db.refresh(q)
    return {"status": "success", "message": f"Audio '{saved['filename']}' biriktirildi.", "question": bank.diag_to_dict(q)}


@router.delete("/diagnostic/questions/{qid}/audio")
def remove_diag_audio(qid: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    q = _get_diag(db, qid, current_user)
    bank.delete_audio_file(q.audio_url)
    q.audio_url = None
    q.audio_filename = None
    if q.skill != "listening":
        q.is_audio = False
    db.commit()
    db.refresh(q)
    return {"status": "success", "message": "Audio olib tashlandi.", "question": bank.diag_to_dict(q)}


class TTSIn(BaseModel):
    text: str
    voice: Optional[str] = None


@router.get("/diagnostic/tts/voices")
def list_tts_voices(current_user: dict = Depends(get_current_user)):
    """AI ovozga aylantirish uchun mavjud ovozlar ro'yxati."""
    return {"voices": tts.list_voices(), "default": tts.DEFAULT_VOICE, "max_chars": tts.MAX_TTS_CHARS}


@router.post("/diagnostic/tts/preview")
async def preview_tts(payload: TTSIn, current_user: dict = Depends(get_current_user)):
    """Matnni saqlamasdan ovozga aylantirib, mp3 qaytaradi (o'qituvchi tinglab ko'radi)."""
    try:
        audio = await tts.synthesize(payload.text, payload.voice)
    except tts.TTSError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@router.post("/diagnostic/questions/{qid}/tts")
async def generate_diag_audio(
    qid: str,
    payload: TTSIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """O'qituvchi yozgan matnni AI ovozga aylantirib, savolga audio sifatida biriktiradi.

    Yuklangan fayl bilan bir xil saqlanadi (/uploads/audio/*.mp3), shuning uchun
    talaba tomoni uchun farqi yo'q. Matn transkripsiya (audio_text) sifatida ham saqlanadi.
    """
    q = _get_diag(db, qid, current_user)
    try:
        audio = await tts.synthesize(payload.text, payload.voice)
    except tts.TTSError as e:
        raise HTTPException(status_code=502, detail=str(e))
    voice_id = payload.voice or tts.DEFAULT_VOICE
    try:
        saved = bank.save_audio_file(audio, f"ai_{voice_id}.mp3", q.teacher_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    bank.delete_audio_file(q.audio_url)
    q.audio_url = saved["url"]
    q.audio_filename = f"AI ovoz ({tts.voice_label(voice_id)}).mp3"
    q.audio_text = payload.text.strip()
    q.is_audio = True
    db.commit()
    db.refresh(q)
    return {"status": "success", "message": "Matn AI ovoziga aylantirildi va savolga biriktirildi.", "question": bank.diag_to_dict(q)}


@router.post("/diagnostic/questions/import")
async def import_diag_questions(
    file: UploadFile = File(...),
    replace: bool = Form(False),
    subject_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    JSON fayldan ko'plab savollarni yuklash (format diagnostic_questions.json bilan bir xil).
    subject_id berilsa, barcha savollar shu fanga biriktiriladi. replace=true bo'lsa shu ko'rinishdagi eski savollar o'chiriladi.
    """
    teacher_id = _tid(current_user)
    subj = _resolve_subject(db, subject_id, current_user)
    items = await _read_json_list(file)

    prepared, errors = [], []
    for i, raw in enumerate(items, 1):
        if not isinstance(raw, dict):
            errors.append(f"{i}-element lug'at emas.")
            continue
        try:
            prepared.append(bank.normalize_diag_payload(raw))
        except ValueError as e:
            errors.append(f"{i}-savol: {e}")
    if not prepared:
        raise HTTPException(status_code=400, detail="Birorta ham yaroqli savol topilmadi. " + " | ".join(errors[:5]))

    if replace:
        old = _owned(db.query(CustomDiagnosticQuestion), CustomDiagnosticQuestion, current_user)
        old = old.filter(CustomDiagnosticQuestion.subject_id == subj) if subj else old.filter(CustomDiagnosticQuestion.subject_id.is_(None))
        for r in old.all():
            bank.delete_audio_file(r.audio_url)
            db.delete(r)
        db.flush()

    order = _next_order(db, CustomDiagnosticQuestion, teacher_id)
    for data in prepared:
        db.add(CustomDiagnosticQuestion(teacher_id=teacher_id, subject_id=subj, question_order=order, is_active=True, **data))
        order += 1
    db.commit()

    msg = f"{len(prepared)} ta savol yuklandi."
    if errors:
        msg += f" {len(errors)} tasi o'tkazib yuborildi."
    return {"status": "success", "message": msg, "imported": len(prepared), "skipped": errors, **_diag_summary(db, current_user, subj)}


@router.post("/diagnostic/questions/load-defaults")
def load_default_diag_questions(
    subject_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Standart 8 ta savolni bankka (tanlangan fanga yoki umumiyga) nusxalash."""
    teacher_id = _tid(current_user)
    subj = _resolve_subject(db, subject_id, current_user)
    order = _next_order(db, CustomDiagnosticQuestion, teacher_id)
    added = 0
    for raw in bank.default_diagnostic_questions():
        try:
            data = bank.normalize_diag_payload(raw)
        except ValueError:
            continue
        db.add(CustomDiagnosticQuestion(teacher_id=teacher_id, subject_id=subj, question_order=order, is_active=True, **data))
        order += 1
        added += 1
    db.commit()
    return {"status": "success", "message": f"{added} ta standart savol nusxalandi.", **_diag_summary(db, current_user, subj)}


@router.get("/diagnostic/questions/export")
def export_diag_questions(
    subject_id: Optional[str] = Query(None),
    all_subjects: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = _scoped_rows(db, CustomDiagnosticQuestion, current_user, subject_id or None, all_subjects)
    out = []
    for r in rows:
        d = bank.diag_to_dict(r)
        for k in ("teacher_id", "source", "is_active", "question_order", "audio_filename", "subject_id"):
            d.pop(k, None)
        out.append(d)
    return out


# ================================================================
# 2. ANKETA (FLCAS) SAVOLLARI
# ================================================================

@router.get("/survey/questions")
def list_survey_questions(
    subject_id: Optional[str] = Query(None),
    all_subjects: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return _survey_summary(db, current_user, subject_id or None, all_subjects)


@router.get("/survey/questions/defaults")
def get_default_survey_questions():
    return {"questions": bank.default_survey_questions()}


@router.post("/survey/questions")
def create_survey_question(payload: SurveyQuestionIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    teacher_id = _tid(current_user)
    subject_id = _resolve_subject(db, payload.subject_id, current_user)
    try:
        data = bank.normalize_survey_payload(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    s = CustomSurveyQuestion(
        teacher_id=teacher_id,
        subject_id=subject_id,
        question_order=payload.question_order or _next_order(db, CustomSurveyQuestion, teacher_id),
        is_active=payload.is_active if payload.is_active is not None else True,
        **data,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"status": "success", "message": "Anketa savoli qo'shildi.", "question": bank.survey_to_dict(s)}


@router.put("/survey/questions/{sid}")
def update_survey_question(sid: str, payload: SurveyQuestionIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    s = _get_survey(db, sid, current_user)
    try:
        data = bank.normalize_survey_payload(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    for k, v in data.items():
        setattr(s, k, v)
    if payload.is_active is not None:
        s.is_active = payload.is_active
    if payload.question_order is not None:
        s.question_order = payload.question_order
    if "subject_id" in payload.model_fields_set:
        s.subject_id = _resolve_subject(db, payload.subject_id, current_user)
    db.commit()
    db.refresh(s)
    return {"status": "success", "message": "Anketa savoli yangilandi.", "question": bank.survey_to_dict(s)}


@router.patch("/survey/questions/{sid}/subject")
def assign_survey_subject(sid: str, payload: AssignSubjectIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    s = _get_survey(db, sid, current_user)
    s.subject_id = _resolve_subject(db, payload.subject_id, current_user)
    db.commit()
    db.refresh(s)
    return {"status": "success", "message": "Savol fanga biriktirildi." if s.subject_id else "Savol umumiy qilindi.", "question": bank.survey_to_dict(s)}


@router.post("/survey/questions/assign-subject")
def bulk_assign_survey_subject(payload: BulkAssignIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    subject_id = _resolve_subject(db, payload.subject_id, current_user)
    n = 0
    for sid in payload.ids:
        s = _owned(db.query(CustomSurveyQuestion).filter(CustomSurveyQuestion.id == sid), CustomSurveyQuestion, current_user).first()
        if s:
            s.subject_id = subject_id
            n += 1
    db.commit()
    return {"status": "success", "message": f"{n} ta anketa savoli {'fanga biriktirildi' if subject_id else 'umumiy qilindi'}.", "updated": n}


@router.patch("/survey/questions/{sid}/toggle")
def toggle_survey_question(sid: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    s = _get_survey(db, sid, current_user)
    s.is_active = not bool(s.is_active)
    db.commit()
    return {"status": "success", "is_active": s.is_active}


@router.delete("/survey/questions/{sid}")
def delete_survey_question(sid: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    s = _get_survey(db, sid, current_user)
    db.delete(s)
    db.commit()
    return {"status": "success", "message": "Anketa savoli o'chirildi."}


@router.delete("/survey/questions")
def delete_all_survey_questions(
    subject_id: Optional[str] = Query(None),
    all_subjects: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = _scoped_rows(db, CustomSurveyQuestion, current_user, subject_id or None, all_subjects)
    if subject_id and not all_subjects:
        rows = [r for r in rows if r.subject_id == subject_id]
    for r in rows:
        db.delete(r)
    db.commit()
    return {"status": "success", "message": f"{len(rows)} ta anketa savoli o'chirildi.", "deleted": len(rows)}


@router.post("/survey/questions/reorder")
def reorder_survey_questions(payload: ReorderIn, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    for idx, sid in enumerate(payload.ids, 1):
        _owned(db.query(CustomSurveyQuestion).filter(CustomSurveyQuestion.id == sid), CustomSurveyQuestion, current_user) \
            .update({"question_order": idx}, synchronize_session=False)
    db.commit()
    return {"status": "success"}


@router.post("/survey/questions/import")
async def import_survey_questions(
    file: UploadFile = File(...),
    replace: bool = Form(False),
    subject_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    teacher_id = _tid(current_user)
    subj = _resolve_subject(db, subject_id, current_user)
    items = await _read_json_list(file)

    prepared, errors = [], []
    for i, raw in enumerate(items, 1):
        if not isinstance(raw, dict):
            errors.append(f"{i}-element lug'at emas.")
            continue
        try:
            prepared.append(bank.normalize_survey_payload(raw))
        except ValueError as e:
            errors.append(f"{i}-savol: {e}")
    if not prepared:
        raise HTTPException(status_code=400, detail="Birorta ham yaroqli anketa savoli topilmadi. " + " | ".join(errors[:5]))

    if replace:
        old = _owned(db.query(CustomSurveyQuestion), CustomSurveyQuestion, current_user)
        old = old.filter(CustomSurveyQuestion.subject_id == subj) if subj else old.filter(CustomSurveyQuestion.subject_id.is_(None))
        old.delete(synchronize_session=False)
        db.flush()

    order = _next_order(db, CustomSurveyQuestion, teacher_id)
    for data in prepared:
        db.add(CustomSurveyQuestion(teacher_id=teacher_id, subject_id=subj, question_order=order, is_active=True, **data))
        order += 1
    db.commit()

    msg = f"{len(prepared)} ta anketa savoli yuklandi."
    if errors:
        msg += f" {len(errors)} tasi o'tkazib yuborildi."
    return {"status": "success", "message": msg, "imported": len(prepared), "skipped": errors, **_survey_summary(db, current_user, subj)}


@router.post("/survey/questions/load-defaults")
def load_default_survey_questions(
    subject_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    teacher_id = _tid(current_user)
    subj = _resolve_subject(db, subject_id, current_user)
    order = _next_order(db, CustomSurveyQuestion, teacher_id)
    added = 0
    for raw in bank.default_survey_questions():
        try:
            data = bank.normalize_survey_payload(raw)
        except ValueError:
            continue
        db.add(CustomSurveyQuestion(teacher_id=teacher_id, subject_id=subj, question_order=order, is_active=True, **data))
        order += 1
        added += 1
    db.commit()
    return {"status": "success", "message": f"{added} ta standart anketa savoli nusxalandi.", **_survey_summary(db, current_user, subj)}


@router.get("/survey/questions/export")
def export_survey_questions(
    subject_id: Optional[str] = Query(None),
    all_subjects: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = _scoped_rows(db, CustomSurveyQuestion, current_user, subject_id or None, all_subjects)
    out = []
    for r in rows:
        d = bank.survey_to_dict(r)
        for k in ("teacher_id", "source", "is_active", "question_order", "subject_id"):
            d.pop(k, None)
        out.append(d)
    return out
