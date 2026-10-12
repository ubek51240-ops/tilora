"""
Mustaqil topshiriq (o'qituvchi materiallari) uchun umumiy mantiq.

- Talaba doirasi: talaba faqat o'z guruhiga tegishli fanlarni ko'radi.
- Javob kaliti: test materiallari talabaga to'g'ri javob va izohsiz yuboriladi.
- Yozma topshiriq ("writing"): AI yoki shablon asosida vazifa, so'z chegarasi,
  4 mezonli rubrika (mazmun, grammatika, leksika, bog'liqlik) va yordamchi lug'at.
- Urinishlar: talabaning har bir material bo'yicha eng yaxshi natijasi.
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models.entities import Group, TeacherSubject, TeacherMaterial, MaterialAttempt, User

MATERIAL_TYPES = ("test", "presentation", "lesson_plan", "writing")

# Yozma nutqni baholash mezonlari (5-bosqichli mashg'ulot bilan bir xil kalitlar)
WRITING_CRITERIA_UZ: List[Dict[str, str]] = [
    {"key": "content", "name": "Mazmun va vazifa bajarilishi", "description": "Topshiriq talablari to'liq bajarilgan, fikrlar dalillangan (Task achievement)."},
    {"key": "grammar", "name": "Grammatik aniqlik", "description": "Zamonlar, moslashuv, gap tuzilishi to'g'ri; L1 ta'siri kam (Accuracy)."},
    {"key": "lexis", "name": "Leksik boylik", "description": "Mavzuga oid so'z va iboralar, takrorsiz, aniq (Lexical resource)."},
    {"key": "coherence", "name": "Bog'liqlik va tuzilma", "description": "Kirish, asosiy qism, xulosa; bog'lovchilar to'g'ri ishlatilgan (Coherence)."},
]

WRITING_CRITERIA_EN: List[Dict[str, str]] = [
    {"key": "content", "name": "Task Achievement & Content", "description": "All prompt requirements fully addressed; arguments well supported and developed."},
    {"key": "grammar", "name": "Grammatical Range & Accuracy", "description": "Accurate syntax, tense harmony, variety of structures; minimal L1 interference."},
    {"key": "lexis", "name": "Lexical Resource", "description": "Precise academic terminology, natural collocations, minimal repetition."},
    {"key": "coherence", "name": "Coherence & Cohesion", "description": "Clear paragraph structure (intro, body, conclusion) with appropriate transition markers."},
]

WRITING_CRITERIA_RU: List[Dict[str, str]] = [
    {"key": "content", "name": "Содержание и выполнение задания", "description": "Требования задания выполнены в полном объеме, тезисы аргументированы (Task achievement)."},
    {"key": "grammar", "name": "Грамматическая точность", "description": "Корректные грамматические структуры, согласование, минимизация влияния L1 (Accuracy)."},
    {"key": "lexis", "name": "Лексическое богатство", "description": "Академическая терминология по теме, естественные коллокации, отсутствие тавтологии (Lexical resource)."},
    {"key": "coherence", "name": "Связность и логическая структура", "description": "Логичное деление на абзацы (введение, основная часть, заключение), верные коннекторы (Coherence)."},
]

WRITING_CRITERIA = WRITING_CRITERIA_UZ


# ---------------------------------------------------------------
# Talaba doirasi (fan <-> guruh)
# ---------------------------------------------------------------

def _group_token(name: Optional[str]) -> str:
    """'302-guruh (Tajriba)' -> '302'. Raqam bo'lmasa kichik harfli birinchi so'z."""
    if not name:
        return ""
    m = re.search(r"\d+", name)
    if m:
        return m.group(0)
    return name.strip().lower().split()[0] if name.strip() else ""


def student_subject_scope(db: Session, user: Optional[dict]) -> Optional[Set[str]]:
    """Talaba ko'rishi mumkin bo'lgan fan ID lari. None = cheklovsiz (mehmon yoki mos guruh yo'q).

    Moslik: fanning group_name dagi guruh raqami talabaning guruh raqami bilan bir xil
    bo'lsa, yoki guruhga biriktirilgan o'qituvchining fani bo'lsa.
    """
    if not user or user.get("role") in ("teacher", "admin", "researcher"):
        return None
    group_id = user.get("group_id")
    if not group_id:
        return None
    grp = db.query(Group).filter(Group.id == group_id).first()
    if not grp:
        return None
    token = _group_token(grp.name)
    ids: Set[str] = set()
    for s in db.query(TeacherSubject).all():
        if token and _group_token(s.group_name) == token:
            ids.add(s.id)
        elif grp.teacher_id and s.teacher_id == grp.teacher_id:
            ids.add(s.id)
    return ids or None


# ---------------------------------------------------------------
# Javob kalitini yashirish
# ---------------------------------------------------------------

def student_safe_content(material_type: str, content: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Testdan correct_index va explanation olib tashlanadi; boshqa turlar o'zgarmaydi."""
    content = dict(content or {})
    if material_type == "test":
        safe_qs = []
        for q in content.get("questions", []) or []:
            q2 = {k: v for k, v in (q or {}).items() if k not in ("correct_index", "explanation")}
            safe_qs.append(q2)
        content["questions"] = safe_qs
    return content


def items_count(material_type: str, content: Optional[Dict[str, Any]]) -> int:
    content = content or {}
    if material_type == "test":
        return len(content.get("questions", []) or [])
    if material_type == "presentation":
        return len(content.get("slides", []) or [])
    if material_type == "lesson_plan":
        return len(content.get("stages", []) or [])
    if material_type == "writing":
        return len(content.get("criteria", []) or [])
    return 0


# ---------------------------------------------------------------
# Yozma topshiriq generatori
# ---------------------------------------------------------------

def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.MULTILINE).strip()
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def writing_template(topic_title: str, subject_name: str, cefr: str, min_words: int, max_words: int, language: str = "uz") -> Dict[str, Any]:
    lang = (language or "uz").lower()
    if lang == "en":
        return {
            "title": f"{topic_title} — Analytical Writing Task",
            "topic": topic_title,
            "subject": subject_name,
            "cefr_level": cefr,
            "language": "en",
            "task_prompt": (
                f"Write an analytical essay ({min_words}–{max_words} words) on the topic \"{topic_title}\". "
                "State your thesis clearly, support it with two concrete pedagogical arguments or teaching examples, "
                "and conclude with an evaluative synthesis. Use appropriate linking devices and academic vocabulary."
            ),
            "min_words": min_words,
            "max_words": max_words,
            "criteria": [dict(c) for c in WRITING_CRITERIA_EN],
            "scaffold": {
                "key_vocabulary": ["pedagogical model", "formative assessment", "lexical resource", "grammatical range", "metacognitive reflection", "scaffolding"],
                "useful_phrases": ["Empirical evidence suggests that...", "A significant factor to consider is...", "From a pedagogical perspective,...", "In conclusion, it is evident that..."],
                "structure": ["Introduction: topic context and thesis statement (1–2 sentences)", "Body: 2 developed arguments with practical examples", "Conclusion: evaluative summary and pedagogical takeaway"],
            },
            "ai_generated": False,
        }
    elif lang == "ru":
        return {
            "title": f"{topic_title} — Письменное задание (эссе)",
            "topic": topic_title,
            "subject": subject_name,
            "cefr_level": cefr,
            "language": "ru",
            "task_prompt": (
                f"Напишите аналитическое эссе ({min_words}–{max_words} слов) по теме \"{topic_title}\". "
                "Четко сформулируйте авторскую позицию, подкрепите ее двумя конкретными аргументами или примерами из педагогической практики "
                "и завершите обобщающим выводом. Используйте академические коннекторы и профессиональную терминологию."
            ),
            "min_words": min_words,
            "max_words": max_words,
            "criteria": [dict(c) for c in WRITING_CRITERIA_RU],
            "scaffold": {
                "key_vocabulary": ["методическая модель", "формирующее оценивание", "лексический запас", "грамматическая точность", "метакогнитивная рефлексия", "педагогические опоры"],
                "useful_phrases": ["Исследования показывают, что...", "Важным фактором является...", "С педагогической точки зрения...", "Таким образом, можно сделать вывод, что..."],
                "structure": ["Введение: актуальность темы и тезис (1–2 предложения)", "Основная часть: 2 аргумента с практическими примерами", "Заключение: обобщающий вывод и педагогическая рефлексия"],
            },
            "ai_generated": False,
        }
    else:
        return {
            "title": f"{topic_title} — Yozma topshiriq",
            "topic": topic_title,
            "subject": subject_name,
            "cefr_level": cefr,
            "language": "uz",
            "task_prompt": (
                f"Write an analytical paragraph ({min_words}–{max_words} words) on the topic \"{topic_title}\". "
                "State your position clearly, support it with two concrete examples from your teaching practice, "
                "and finish with a short conclusion. Use at least three linking devices."
            ),
            "min_words": min_words,
            "max_words": max_words,
            "criteria": [dict(c) for c in WRITING_CRITERIA_UZ],
            "scaffold": {
                "key_vocabulary": ["criterion / criteria", "coherence", "accuracy", "lexical range", "task achievement", "feedback"],
                "useful_phrases": ["It is widely accepted that...", "One clear advantage is...", "In contrast,...", "Taking everything into account,..."],
                "structure": ["Kirish: mavzu va pozitsiya (1–2 gap)", "Asosiy qism: 2 ta dalil + misol", "Xulosa: umumlashtiruvchi fikr"],
            },
            "ai_generated": False,
        }


async def generate_writing_material(
    ai_service,
    topic_title: str,
    subject_name: str,
    cefr: str = "B2",
    min_words: int = 150,
    max_words: int = 200,
    extra_instructions: Optional[str] = None,
    book_content: Optional[str] = None,
    language: str = "uz",
) -> Dict[str, Any]:
    """AI orqali yozma topshiriq (O'zbek, Rus yoki Ingliz tilida); AI ishlamasa shablon. Rubrika mezonlari doimo 4 ta va bir xil kalitli."""
    lang = (language or "uz").lower()
    if lang not in ("uz", "en", "ru"):
        lang = "uz"

    if min_words > max_words:
        min_words, max_words = max_words, min_words
    base = writing_template(topic_title, subject_name, cefr, min_words, max_words, language=lang)

    book_hint = f"\nUse this source excerpt for context (do not copy it):\n{book_content[:2500]}\n" if book_content else ""
    extra = f"\nTeacher's extra instructions: {extra_instructions}\n" if extra_instructions else ""

    if lang == "en":
        sys_msg = "You are an expert academic writing instructor and ELT curriculum designer for higher education. Reply with a single JSON object only."
        usr_msg = (
            f"Subject: {subject_name}\nTopic: {topic_title}\nCEFR level: {cefr}\nTarget Language: English\n"
            f"Word limit: {min_words}-{max_words} words.{extra}{book_hint}\n"
            "Return JSON with keys: title (English, short), task_prompt (English, a clear analytical writing task with 2-3 concrete requirements), "
            "key_vocabulary (6-10 English academic terms), useful_phrases (4-6 English academic transition phrases), "
            "structure (3-4 short English bullet points describing the expected structure)."
        )
    elif lang == "ru":
        sys_msg = "Вы — эксперт по академическому письму и методике преподавания в высшей школе. Ответьте только одним валидным JSON объектом."
        usr_msg = (
            f"Предмет: {subject_name}\nТема: {topic_title}\nУровень CEFR: {cefr}\nЯзык: Русский\n"
            f"Объем: {min_words}-{max_words} слов.{extra}{book_hint}\n"
            "Верните JSON со следующими ключами: title (на русском языке, краткий), task_prompt (на русском языке, четкое аналитическое задание с 2-3 требованиями), "
            "key_vocabulary (6-10 академических терминов по теме), useful_phrases (4-6 академических фраз-связок), "
            "structure (3-4 кратких пункта структуры эссе на русском языке)."
        )
    else:
        sys_msg = "You are an ESP/EFL writing-task designer for future English teachers in Uzbekistan. Reply with a single JSON object only."
        usr_msg = (
            f"Subject: {subject_name}\nTopic: {topic_title}\nCEFR level: {cefr}\n"
            f"Word limit: {min_words}-{max_words} words.{extra}{book_hint}\n"
            "Return JSON with keys: title (Uzbek, short), task_prompt (English, a clear writing task with 2-3 concrete requirements), "
            "key_vocabulary (6-10 English terms), useful_phrases (4-6 English academic phrases), "
            "structure (3-4 short Uzbek bullet points describing the expected structure)."
        )

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": usr_msg},
    ]
    try:
        res = await ai_service.call_chat(messages, temperature=0.5, max_tokens=900)
    except Exception as e:  # tarmoq
        base["ai_error"] = str(e)
        return base
    if not res or not res.get("success"):
        base["ai_error"] = (res or {}).get("error_message") or "AI javob bermadi"
        return base
    obj = _extract_json_object(res.get("content", ""))
    if not obj:
        base["ai_error"] = "AI JSON qaytarmadi"
        return base

    def _list(v, fallback):
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) and v else fallback

    base["title"] = str(obj.get("title") or base["title"]).strip()[:255]
    base["task_prompt"] = str(obj.get("task_prompt") or base["task_prompt"]).strip()
    base["scaffold"] = {
        "key_vocabulary": _list(obj.get("key_vocabulary"), base["scaffold"]["key_vocabulary"]),
        "useful_phrases": _list(obj.get("useful_phrases"), base["scaffold"]["useful_phrases"]),
        "structure": _list(obj.get("structure"), base["scaffold"]["structure"]),
    }
    base["ai_generated"] = True
    base["model"] = getattr(ai_service, "model", None)
    base["language"] = lang
    return base


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z'’\-]+|[Ѐ-ӿ]+", text or ""))


# ---------------------------------------------------------------
# Urinishlar
# ---------------------------------------------------------------

def best_attempts(db: Session, student_id: Optional[str], material_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Har bir material uchun talabaning eng yaxshi (ball bo'yicha) urinishi va soni."""
    if not student_id or not material_ids:
        return {}
    rows = (
        db.query(MaterialAttempt)
        .filter(MaterialAttempt.student_id == student_id, MaterialAttempt.material_id.in_(material_ids))
        .order_by(MaterialAttempt.created_at.asc())
        .all()
    )
    out: Dict[str, Dict[str, Any]] = {}
    for a in rows:
        cur = out.get(a.material_id)
        entry = {
            "attempts": (cur["attempts"] + 1) if cur else 1,
            "status": a.status,
            "best_score": a.score,
            "passed": a.passed,
            "last_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
        }
        if cur:
            if (a.score or 0) < (cur.get("best_score") or 0):
                entry["best_score"] = cur["best_score"]
                entry["passed"] = cur["passed"]
            if cur["status"] == "completed":
                entry["status"] = "completed"
        out[a.material_id] = entry
    return out


def record_attempt(
    db: Session,
    user: Optional[dict],
    material: TeacherMaterial,
    status: str,
    score: Optional[int] = None,
    correct_count: Optional[int] = None,
    total_count: Optional[int] = None,
    passed: Optional[bool] = None,
    answers: Any = None,
    result: Any = None,
) -> Optional[MaterialAttempt]:
    """Faqat tizimga kirgan talaba uchun yoziladi; mehmon uchun None."""
    if not user or user.get("role") != "student":
        return None
    sid = user.get("id") or user.get("sub")
    if not sid:
        return None
    if status == "viewed":
        # Ko'rish belgisi bir marta yetarli
        exists = db.query(MaterialAttempt).filter(
            MaterialAttempt.student_id == sid, MaterialAttempt.material_id == material.id
        ).first()
        if exists:
            return exists
    a = MaterialAttempt(
        student_id=sid,
        material_id=material.id,
        subject_id=material.subject_id,
        teacher_id=material.teacher_id,
        material_type=material.material_type,
        status=status,
        score=score,
        correct_count=correct_count,
        total_count=total_count,
        passed=passed,
        answers_json=answers,
        result_json=result,
        created_at=datetime.utcnow(),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def serialize_attempt(a: MaterialAttempt, student: Optional[User] = None) -> Dict[str, Any]:
    return {
        "id": a.id,
        "student_id": a.student_id,
        "student_name": student.full_name if student else "",
        "material_id": a.material_id,
        "material_type": a.material_type,
        "status": a.status,
        "score": a.score,
        "correct_count": a.correct_count,
        "total_count": a.total_count,
        "passed": a.passed,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
    }
