"""
Diagnostika testi va kognitiv-affektiv anketa savollari banki.

Manba ustuvorligi (talaba uchun):
  1. Talaba guruhiga biriktirilgan o'qituvchining faol savollari
  2. Har qanday o'qituvchi yuklagan faol savollar (bitta o'qituvchili joriy etish uchun)
  3. backend/app/content/*.json dagi standart to'plam (zaxira)

O'qituvchi o'zi diagnostika ekranini ochsa, o'z savollarini ko'radi.
"""
import os
import json
import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.entities import CustomDiagnosticQuestion, CustomSurveyQuestion, Group, TeacherSubject, User

_CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
AUDIO_DIR = os.path.join(UPLOADS_DIR, "audio")

ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".webm", ".flac"}
MAX_AUDIO_BYTES = 15 * 1024 * 1024  # 15 MB

VALID_SKILLS = {"listening", "reading", "writing", "speaking"}
VALID_CEFR = {"A1", "A2", "B1", "B2", "C1", "C2"}
VALID_DIMENSIONS = {"anxiety", "load_capacity", "pace", "autonomy", "motivation"}


def _read_json(name: str) -> List[Dict[str, Any]]:
    path = os.path.join(_CONTENT_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_diagnostic_questions() -> List[Dict[str, Any]]:
    return _read_json("diagnostic_questions.json")


def default_survey_questions() -> List[Dict[str, Any]]:
    return _read_json("survey_questions.json")


# ----------------------------------------------------------------
# Seriyalash (ORM -> talaba ekrani kutadigan JSON shakli)
# ----------------------------------------------------------------

def diag_to_dict(q: CustomDiagnosticQuestion) -> Dict[str, Any]:
    is_audio = bool(q.is_audio or q.audio_url)
    return {
        "id": q.id,
        "skill": q.skill or "reading",
        "cefr_level": q.cefr_level or "B1",
        "is_audio": is_audio,
        "audio_url": q.audio_url,
        "audio_filename": q.audio_filename,
        "audio_text": q.audio_text,
        "instruction": q.instruction or q.question,
        "question": q.question,
        "options": list(q.options or []),
        "correct_index": q.correct_index or 0,
        "rationale": q.rationale or "",
        "question_order": q.question_order or 0,
        "is_active": bool(q.is_active),
        "teacher_id": q.teacher_id,
        "subject_id": q.subject_id,
        "source": "teacher",
    }


def survey_to_dict(sq: CustomSurveyQuestion) -> Dict[str, Any]:
    return {
        "id": sq.id,
        "dimension": sq.dimension or "anxiety",
        "prompt_uz": sq.prompt_uz,
        "prompt_en": sq.prompt_en or "",
        "scale": "likert_5",
        "weight": float(sq.weight if sq.weight is not None else 1.0),
        "question_order": sq.question_order or 0,
        "is_active": bool(sq.is_active),
        "teacher_id": sq.teacher_id,
        "subject_id": sq.subject_id,
        "source": "teacher",
    }


# ----------------------------------------------------------------
# Talaba uchun manbani aniqlash
# ----------------------------------------------------------------

def resolve_teacher_id(db: Session, user: Optional[dict]) -> Optional[str]:
    """Talaba qaysi o'qituvchining savollarini ko'rishi kerakligini aniqlaydi."""
    if not user:
        return None
    role = user.get("role")
    uid = user.get("id") or user.get("sub")
    if role in ("teacher", "admin"):
        return uid
    group_id = user.get("group_id")
    if group_id:
        grp = db.query(Group).filter(Group.id == group_id).first()
        if grp and grp.teacher_id:
            return grp.teacher_id
    return None


def _subject_scope(query, model, subject_id: Optional[str]):
    """Fan tanlangan bo'lsa: shu fanning savollari + umumiy (subject_id NULL) savollar.
    Fan tanlanmagan bo'lsa: faqat umumiy savollar."""
    if subject_id:
        return query.filter(or_(model.subject_id == subject_id, model.subject_id.is_(None)))
    return query.filter(model.subject_id.is_(None))


def _load_bank(db: Session, model, user: Optional[dict], subject_id: Optional[str], to_dict, defaults):
    tid = resolve_teacher_id(db, user)
    base = _subject_scope(db.query(model).filter(model.is_active == True), model, subject_id)  # noqa: E712
    order = (model.question_order, model.created_at)
    if tid:
        own = base.filter(model.teacher_id == tid).order_by(*order).all()
        if own:
            return [to_dict(q) for q in own]
        if user and user.get("role") in ("teacher", "admin") and not subject_id:
            # O'qituvchi/admin o'z bankini bo'sh qoldirgan bo'lsa, standart to'plamni ko'radi
            return defaults()
    any_active = base.order_by(*order).all()
    if any_active:
        return [to_dict(q) for q in any_active]
    return defaults()


def load_diagnostic_questions(db: Session, user: Optional[dict], subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return _load_bank(db, CustomDiagnosticQuestion, user, subject_id, diag_to_dict, default_diagnostic_questions)


def load_survey_questions(db: Session, user: Optional[dict], subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return _load_bank(db, CustomSurveyQuestion, user, subject_id, survey_to_dict, default_survey_questions)


def _skill_counts(questions: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {sk: 0 for sk in sorted(VALID_SKILLS)}
    for q in questions:
        sk = (q.get("skill") or "reading").lower()
        counts[sk] = counts.get(sk, 0) + 1
    return counts


def subjects_with_questions(db: Session, user: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Talaba tanlovi uchun: barcha ochiq fanlar ro'yxati (+ umumiy to'plam).

    Har bir fan uchun diagnostika/anketa savollari soni va 4 ko'nikma bo'yicha taqsimot
    qaytariladi. Fanga savol biriktirilmagan bo'lsa ham fan ro'yxatda turadi — talaba
    tanlaganda umumiy (yoki standart) to'plam chiqadi.
    """
    from app.services.materials import student_subject_scope

    diag_rows = db.query(CustomDiagnosticQuestion.subject_id, CustomDiagnosticQuestion.skill)         .filter(CustomDiagnosticQuestion.is_active == True).all()  # noqa: E712
    surv_rows = db.query(CustomSurveyQuestion.subject_id)         .filter(CustomSurveyQuestion.is_active == True).all()  # noqa: E712

    diag_counts: Dict[Optional[str], int] = {}
    skill_counts: Dict[Optional[str], Dict[str, int]] = {}
    surv_counts: Dict[Optional[str], int] = {}
    for sid, skill in diag_rows:
        diag_counts[sid] = diag_counts.get(sid, 0) + 1
        sk = (skill or "reading").lower()
        skill_counts.setdefault(sid, {s: 0 for s in sorted(VALID_SKILLS)})
        skill_counts[sid][sk] = skill_counts[sid].get(sk, 0) + 1
    for (sid,) in surv_rows:
        surv_counts[sid] = surv_counts.get(sid, 0) + 1

    # Umumiy (subject_id NULL) to'plam. Hech narsa yuklanmagan bo'lsa, standart JSON to'plam chiqadi.
    gen_diag = diag_counts.get(None, 0)
    gen_surv = surv_counts.get(None, 0)
    gen_skills = skill_counts.get(None) or {s: 0 for s in sorted(VALID_SKILLS)}
    if gen_diag == 0:
        defaults = default_diagnostic_questions()
        gen_diag = len(defaults)
        gen_skills = _skill_counts(defaults)
    if gen_surv == 0:
        gen_surv = len(default_survey_questions())

    out = [{"id": None, "name": "Umumiy (barcha fanlar)", "teacher_name": "", "code": "",
            "diag_count": gen_diag, "survey_count": gen_surv, "skills": gen_skills}]

    scope = student_subject_scope(db, user)
    subjects = db.query(TeacherSubject).all()
    if scope is not None:
        subjects = [s for s in subjects if s.id in scope]
    teacher_cache: Dict[str, str] = {}
    for subj in sorted(subjects, key=lambda x: (x.name or "").lower()):
        if subj.teacher_id not in teacher_cache:
            teacher = db.query(User).filter(User.id == subj.teacher_id).first()
            teacher_cache[subj.teacher_id] = teacher.full_name if teacher else ""
        own_skills = skill_counts.get(subj.id) or {}
        merged = {sk: own_skills.get(sk, 0) + gen_skills.get(sk, 0) for sk in sorted(VALID_SKILLS)}
        out.append({
            "id": subj.id, "name": subj.name, "code": subj.code or "",
            "teacher_name": teacher_cache[subj.teacher_id],
            "own_diag_count": diag_counts.get(subj.id, 0),
            "own_survey_count": surv_counts.get(subj.id, 0),
            "diag_count": diag_counts.get(subj.id, 0) + gen_diag,
            "survey_count": surv_counts.get(subj.id, 0) + gen_surv,
            "skills": merged,
        })
    return out


# ----------------------------------------------------------------
# Validatsiya (import va forma uchun umumiy)
# ----------------------------------------------------------------

def normalize_diag_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Xom lug'atni tekshirib, bazaga yozishga tayyor shaklga keltiradi. Xato bo'lsa ValueError."""
    question = (raw.get("question") or raw.get("instruction") or "").strip()
    if not question:
        raise ValueError("Savol matni bo'sh bo'lishi mumkin emas.")

    options = raw.get("options") or []
    if isinstance(options, str):
        options = [o.strip() for o in options.splitlines() if o.strip()]
    options = [str(o).strip() for o in options if str(o).strip()]
    if len(options) < 2:
        raise ValueError(f"Kamida 2 ta javob varianti kerak: '{question[:40]}...'")
    if len(options) > 6:
        raise ValueError("Ko'pi bilan 6 ta javob varianti bo'lishi mumkin.")

    try:
        correct_index = int(raw.get("correct_index", 0))
    except (TypeError, ValueError):
        raise ValueError("correct_index butun son bo'lishi kerak.")
    if not (0 <= correct_index < len(options)):
        raise ValueError(f"correct_index ({correct_index}) variantlar sonidan ({len(options)}) tashqarida.")

    skill = (raw.get("skill") or "reading").strip().lower()
    if skill not in VALID_SKILLS:
        raise ValueError(f"Noto'g'ri ko'nikma '{skill}'. Ruxsat: {', '.join(sorted(VALID_SKILLS))}")

    cefr = (raw.get("cefr_level") or "B1").strip().upper()
    if cefr not in VALID_CEFR:
        raise ValueError(f"Noto'g'ri CEFR daraja '{cefr}'.")

    return {
        "skill": skill,
        "cefr_level": cefr,
        "instruction": (raw.get("instruction") or "").strip() or None,
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "rationale": (raw.get("rationale") or "").strip() or None,
        "is_audio": bool(raw.get("is_audio")) or skill == "listening",
        "audio_text": (raw.get("audio_text") or "").strip() or None,
        # audio_url faqat allaqachon /uploads/ ichida bo'lsa yoki standart /audio_*.wav bo'lsa qabul qilinadi
        "audio_url": _safe_audio_url(raw.get("audio_url")),
    }


def _safe_audio_url(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if url.startswith("/uploads/audio/") or url.startswith("/audio_"):
        return url
    return None


def normalize_survey_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    prompt_uz = (raw.get("prompt_uz") or raw.get("prompt") or "").strip()
    if not prompt_uz:
        raise ValueError("Anketa savoli (prompt_uz) bo'sh bo'lishi mumkin emas.")
    dimension = (raw.get("dimension") or "anxiety").strip().lower()
    if dimension not in VALID_DIMENSIONS:
        raise ValueError(f"Noto'g'ri o'lcham '{dimension}'. Ruxsat: {', '.join(sorted(VALID_DIMENSIONS))}")
    try:
        weight = float(raw.get("weight", 1.0))
    except (TypeError, ValueError):
        raise ValueError("weight son bo'lishi kerak (masalan 1.0).")
    if not (0.1 <= weight <= 3.0):
        raise ValueError("weight 0.1 dan 3.0 gacha bo'lishi kerak.")
    return {
        "dimension": dimension,
        "prompt_uz": prompt_uz,
        "prompt_en": (raw.get("prompt_en") or "").strip() or None,
        "weight": weight,
    }


# ----------------------------------------------------------------
# Audio fayllar
# ----------------------------------------------------------------

def save_audio_file(content: bytes, original_name: str, teacher_id: str) -> Dict[str, str]:
    ext = os.path.splitext(original_name or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXT:
        raise ValueError(f"Audio formati qo'llab-quvvatlanmaydi ({ext or 'kengaytmasiz'}). Ruxsat: {', '.join(sorted(ALLOWED_AUDIO_EXT))}")
    if not content:
        raise ValueError("Audio fayl bo'sh.")
    if len(content) > MAX_AUDIO_BYTES:
        raise ValueError(f"Audio fayl 15 MB dan katta ({len(content) // (1024*1024)} MB).")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    fname = f"diag_{teacher_id[:8]}_{uuid.uuid4().hex[:10]}{ext}"
    with open(os.path.join(AUDIO_DIR, fname), "wb") as f:
        f.write(content)
    return {"url": f"/uploads/audio/{fname}", "filename": original_name or fname}


def delete_audio_file(url: Optional[str]) -> None:
    """Faqat /uploads/audio/ ichidagi faylni o'chiradi; standart /audio_*.wav ga tegmaydi."""
    if not url or not url.startswith("/uploads/audio/"):
        return
    fname = os.path.basename(url)
    path = os.path.join(AUDIO_DIR, fname)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
