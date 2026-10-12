from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import re

from app.database import get_db
from app.models.entities import (
    TeacherSubject, SyllabusTopic, TeacherMaterial, MaterialAttempt, User,
    DiagnosticTest, DiagnosticQuestion, DiagnosticAttempt, DiagnosticAnswer,
    SubjectBook, TeacherProposal, Group
)
from app.schemas.all_schemas import ProposalAction, SubjectBookCreate, SubjectBookUpdate, SubjectBookResponse, MaterialGenerateRequest
from app.core.deps import get_current_user, require_role
from app.services.ai_service import ai_service
from app.services import materials as matsvc
from app.services.syllabus_parser import parse_syllabus_document

router = APIRouter(prefix="/teacher", tags=["O'qituvchi"], dependencies=[Depends(require_role(["teacher", "admin"]))])

# Pydantic sxemalar
class SubjectCreateRequest(BaseModel):
    name: str
    code: Optional[str] = None
    semester: Optional[str] = "5-semestr"
    course_year: Optional[int] = 3
    group_name: Optional[str] = "302-guruh"
    description: Optional[str] = None
    syllabus_text: Optional[str] = None

class SyllabusUploadRequest(BaseModel):
    syllabus_text: str
    topics: Optional[List[str]] = None


# Namunaviy fanlar (Agar o'qituvchining bazasida hali fan bo'lmasa avtomatik yuklanadi)
DEFAULT_TEACHER_SUBJECTS = [
    {
        "name": "Pedagogik diskurs va nutq madaniyati",
        "code": "PED-301",
        "semester": "5-semestr",
        "course_year": 3,
        "group_name": "302-guruh (Tajriba)",
        "description": "Bo'lajak chet tili o'qituvchilarining auditoriyadagi pedagogik muloqot va ko'rsatmalar berish mahorati.",
        "topics": [
            "1. Introduction to Pedagogical Discourse & Classroom Interaction",
            "2. Teacher Talk Time (TTT) vs. Student Talk Time (STT) Balance",
            "3. Giving Clear Instructions & Checking Understanding (ICQs)",
            "4. Constructive Error Correction & Oral Feedback Techniques",
            "5. Scaffolding Strategies for Mixed-Ability Language Learners",
            "6. Questioning Techniques: Display vs. Referential Questions",
            "7. Managing Affective Filter & FL Anxiety in Speaking Tasks",
            "8. Midterm Formative Assessment: Peer Observation & Teaching Analysis",
            "9. Facilitating Group Work & Cooperative Learning in EFL",
            "10. Non-Verbal Communication & Body Language in the Classroom",
            "11. Elicitation Techniques vs. Direct Explanations",
            "12. Teaching Pronunciation & Suprasegmental Features Contextually",
            "13. Metacognitive Prompting & Student Reflection Strategies",
            "14. Handling Classroom Disruptions with Constructive Language",
            "15. Designing Communicative Tasks without Premature AI Reliance",
            "16. Final Teaching Portfolio Defense & Pedagogical Synthesis"
        ]
    },
    {
        "name": "Ingliz tili akademik yozuvi (EAP)",
        "code": "EAP-302",
        "semester": "5-semestr",
        "course_year": 3,
        "group_name": "304-guruh (Nazorat)",
        "description": "Akademik maqola, annotatsiya, argumentativ insho va ilmiy tadqiqot hisobotlarini yozish mezonlari.",
        "topics": [
            "1. Principles of Academic Style, Tone & Formality",
            "2. Analyzing Paragraph Structure & Topic Sentences",
            "3. Formulating Clear & Defensible Thesis Statements",
            "4. Argumentative Essay: Claims, Counterarguments & Rebuttals",
            "5. Synthesizing Literature & Integrating Direct Quotes Contextually",
            "6. Paraphrasing & Avoiding Unintentional Plagiarism",
            "7. Cohesion & Coherence: Transitional Markers & Pronoun Reference",
            "8. Midterm Portfolio Review: Diagnostic Essay Revision",
            "9. Writing Effective Abstract, Introduction & Methodology",
            "10. Reporting Data, Tables & Graphical Trends in English",
            "11. Discussion Section: Interpreting Empirical Findings with Hedging",
            "12. Conclusion & Pedagogical Implications of Research",
            "13. Peer Review Mechanics using Analytic Rubrics",
            "14. Common L1 Interference in Complex Uzbek-English Syntax",
            "15. Proofreading, Concordancing Tools & Citation Formats (APA 7)",
            "16. Final Academic Paper Presentation & Peer Defense"
        ]
    }
]


# ============================================================
# 1. FANLAR RO'YXATI (SUBJECTS MANAGEMENT)
# ============================================================

@router.get("/subjects")
def get_teacher_subjects(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchining barcha fanlari, mavzular va saqlangan materiallar soni.
    Profilga doimiy biriktirilgan holda saqlanadi.
    """
    teacher_id = current_user.get("id")
    subjects = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id).order_by(TeacherSubject.created_at.desc()).all()

    # Agar o'qituvchida hali fanlar bo'lmasa, dastlabki 2 ta namunaviy fanni avtomatik kiritish
    if not subjects:
        for s_def in DEFAULT_TEACHER_SUBJECTS:
            new_s = TeacherSubject(
                teacher_id=teacher_id,
                name=s_def["name"],
                code=s_def["code"],
                semester=s_def["semester"],
                course_year=s_def["course_year"],
                group_name=s_def["group_name"],
                description=s_def["description"],
                syllabus_filename="standart_sillabus_16hafta.pdf",
                syllabus_text="\n".join(s_def["topics"])
            )
            db.add(new_s)
            db.commit()
            db.refresh(new_s)

            # Mavzularni kiritish
            for idx, top_title in enumerate(s_def["topics"], 1):
                t_obj = SyllabusTopic(
                    subject_id=new_s.id,
                    week_number=idx,
                    title=top_title,
                    hours=2,
                    objectives="Mavzu bo'yicha akademik va amaliy kompetensiyalarni egallash."
                )
                db.add(t_obj)
            db.commit()

        # Qayta o'qish
        subjects = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == teacher_id).order_by(TeacherSubject.created_at.desc()).all()

    result = []
    for s in subjects:
        topics_count = db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == s.id).count()
        materials_count = db.query(TeacherMaterial).filter(TeacherMaterial.subject_id == s.id).count()
        result.append({
            "id": s.id,
            "name": s.name,
            "code": s.code or "",
            "semester": s.semester or "5-semestr",
            "course_year": s.course_year or 3,
            "group_name": s.group_name or "302-guruh",
            "description": s.description or "",
            "syllabus_filename": s.syllabus_filename or "",
            "has_syllabus": bool(s.syllabus_text or s.syllabus_filename or topics_count > 0),
            "topics_count": topics_count,
            "materials_count": materials_count,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else ""
        })

    return {"subjects": result, "total": len(result)}


@router.post("/subjects")
def create_teacher_subject(
    payload: SubjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchi yangi fan qo'shishi va sillabus matnini kiritishi.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    subject = TeacherSubject(
        teacher_id=teacher_id,
        name=payload.name.strip(),
        code=payload.code.strip() if payload.code else None,
        semester=payload.semester or "5-semestr",
        course_year=payload.course_year or 3,
        group_name=payload.group_name or "302-guruh",
        description=payload.description or "",
        syllabus_text=payload.syllabus_text or ""
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)

    # Agar sillabus matni berilgan bo'lsa, qatorlardan mavzularni ajratib saqlash
    if payload.syllabus_text:
        lines = [line.strip() for line in payload.syllabus_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines, 1):
            topic = SyllabusTopic(
                subject_id=subject.id,
                week_number=idx,
                title=line,
                hours=2
            )
            db.add(topic)
        db.commit()

    return {
        "status": "success",
        "message": f"'{subject.name}' fani muvaffaqiyatli qo'shildi.",
        "subject_id": subject.id
    }


@router.delete("/subjects/{subject_id}")
def delete_teacher_subject(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fanni o'chirish (o'qituvchi ruxsati bilan).
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id, TeacherSubject.teacher_id == teacher_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi yoki sizga tegishli emas.")

    # Unga bog'liq mavzular va materiallarni tozalash
    db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == subject_id).delete()
    db.query(TeacherMaterial).filter(TeacherMaterial.subject_id == subject_id).delete()
    db.delete(subj)
    db.commit()

    return {"status": "success", "message": f"'{subj.name}' fani va unga tegishli materiallar o'chirildi."}


# ============================================================
# 2. SILLABUS VA MAVZULAR (SYLLABUS & TOPICS)
# ============================================================

@router.get("/subjects/{subject_id}/topics")
def get_subject_topics(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fanning barcha sillabus mavzulari.
    """
    topics = db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == subject_id).order_by(SyllabusTopic.week_number.asc()).all()
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id).first()

    return {
        "subject_id": subject_id,
        "subject_name": subj.name if subj else "",
        "topics": [
            {
                "id": t.id,
                "week_number": t.week_number,
                "title": t.title,
                "hours": t.hours,
                "objectives": t.objectives or ""
            }
            for t in topics
        ]
    }


@router.post("/subjects/{subject_id}/syllabus")
def upload_or_update_syllabus(
    subject_id: str,
    payload: SyllabusUploadRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Sillabus yuklash yoki mavzular ro'yxatini yangilash.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id, TeacherSubject.teacher_id == teacher_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi.")

    subj.syllabus_text = payload.syllabus_text
    subj.syllabus_filename = "yuklangan_sillabus.txt"

    # Mavzularni yangilash
    topics_list = []
    if payload.topics and len(payload.topics) > 0:
        topics_list = payload.topics
    else:
        topics_list = [t.strip() for t in payload.syllabus_text.splitlines() if t.strip()]

    # Eski mavzularni almashtirish
    db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == subject_id).delete()
    for idx, t_title in enumerate(topics_list, 1):
        clean_title = t_title
        # Agar oldida raqam bo'lmasa qo'shish
        if not any(clean_title.startswith(f"{n}.") for n in range(1, 30)):
            clean_title = f"{idx}. {clean_title}"
        t_obj = SyllabusTopic(
            subject_id=subject_id,
            week_number=idx,
            title=clean_title,
            hours=2
        )
        db.add(t_obj)

    db.commit()

    return {
        "status": "success",
        "message": f"Sillabus qabul qilindi. {len(topics_list)} ta mavzu shakllantirildi.",
        "topics_count": len(topics_list)
    }


@router.post("/parse-syllabus-file")
async def parse_syllabus_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchi yuklagan (.docx, .txt) o'quv dasturi yoki sillabus faylini
    intellektual tahlil qilib, fan nomi, kodi, tavsifi va barcha mavzularni ajratib berish.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Yuklangan fayl bo'sh.")

    try:
        parsed = parse_syllabus_document(content, file.filename)
        return {
            "status": "success",
            "filename": file.filename,
            "subject_name": parsed["subject_name"],
            "subject_code": parsed["subject_code"],
            "semester": parsed["semester"],
            "description": parsed["description"],
            "lecture_topics": parsed["lecture_topics"],
            "seminar_topics": parsed["seminar_topics"],
            "independent_topics": parsed["independent_topics"],
            "all_topics": parsed["all_topics"],
            "formatted_text": parsed["formatted_text"],
            "lecture_text": parsed.get("lecture_text", ""),
            "seminar_text": parsed.get("seminar_text", ""),
            "independent_text": parsed.get("independent_text", ""),
            "total_topics": len(parsed["all_topics"]),
            "lecture_count": len(parsed["lecture_topics"]),
            "seminar_count": len(parsed["seminar_topics"]),
            "independent_count": len(parsed["independent_topics"])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Faylni tahlil qilishda xatolik: {str(e)}")


@router.post("/subjects/{subject_id}/upload-syllabus-file")
async def upload_syllabus_file_to_subject(
    subject_id: str,
    file: UploadFile = File(...),
    category: Optional[str] = Form("lecture"), # "lecture", "seminar", "independent", "all"
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchi fanga to'g'ridan-to'g'ri .docx yoki .pdf o'quv dasturi faylini yuklaydi.
    Backend mavzularni avtomatik ajratib olib, bazaga SyllabusTopic sifatida saqlaydi.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id, TeacherSubject.teacher_id == teacher_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fayl bo'sh.")

    try:
        parsed = parse_syllabus_document(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fayl tahlil qilinmadi: {str(e)}")

    # Tanlangan kategoriya bo'yicha mavzular
    chosen_topics = []
    if category == "seminar" and parsed.get("seminar_topics"):
        chosen_topics = parsed["seminar_topics"]
    elif category == "independent" and parsed.get("independent_topics"):
        chosen_topics = parsed["independent_topics"]
    elif category == "all" and parsed.get("all_topics"):
        chosen_topics = parsed["all_topics"]
    else:
        chosen_topics = parsed.get("lecture_topics") if parsed.get("lecture_topics") else parsed.get("all_topics", [])

    if not chosen_topics:
        raise HTTPException(status_code=400, detail="Ushbu fayldan o'quv mavzulari ajratib olinmadi. Iltimos, fayl strukturasini tekshiring.")

    # Fan metadatalarini yangilash (agar mavjud bo'lsa)
    if parsed["subject_name"] and (not subj.name or subj.name.startswith("Yangi")):
        subj.name = parsed["subject_name"]
    if parsed["subject_code"] and not subj.code:
        subj.code = parsed["subject_code"]
    if parsed["semester"] and not subj.semester:
        subj.semester = parsed["semester"]
    if parsed["description"] and not subj.description:
        subj.description = parsed["description"]

    subj.syllabus_filename = file.filename
    subj.syllabus_text = parsed["formatted_text"]

    # Mavzularni bazada yangilash
    db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == subject_id).delete()

    created_topics = []
    for idx, t in enumerate(chosen_topics, 1):
        clean_title = t["title"]
        if not re.match(r"^\d+\.", clean_title):
            clean_title = f"{idx}. {clean_title}"

        t_obj = SyllabusTopic(
            subject_id=subject_id,
            week_number=idx,
            title=clean_title,
            hours=t.get("hours", 2),
            objectives=t.get("subtopics", "")
        )
        db.add(t_obj)
        created_topics.append({
            "week_number": idx,
            "title": clean_title,
            "hours": t.get("hours", 2)
        })

    db.commit()

    return {
        "status": "success",
        "message": f"'{file.filename}' faylidan {len(created_topics)} ta mavzu muvaffaqiyatli ajratib olindi va '{subj.name}' faniga qo'shildi!",
        "subject_name": subj.name,
        "topics_count": len(created_topics),
        "topics": created_topics,
        "parsed_metadata": {
            "subject_name": parsed["subject_name"],
            "subject_code": parsed["subject_code"],
            "semester": parsed["semester"],
            "lecture_count": len(parsed["lecture_topics"]),
            "seminar_count": len(parsed["seminar_topics"]),
            "independent_count": len(parsed["independent_topics"])
        }
    }


# ============================================================
# 3. KITOBLAR BO'LIMI (SUBJECT BOOKS MANAGEMENT)
# ============================================================

@router.get("/subjects/{subject_id}/books")
def get_subject_books(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fanning barcha kitoblarini olish.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id, TeacherSubject.teacher_id == teacher_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi.")

    books = db.query(SubjectBook).filter(SubjectBook.subject_id == subject_id).order_by(SubjectBook.created_at.desc()).all()

    return {
        "subject_id": subject_id,
        "subject_name": subj.name,
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author or "",
                "isbn": b.isbn or "",
                "publisher": b.publisher or "",
                "year": b.year,
                "edition": b.edition or "",
                "book_type": b.book_type,
                "description": b.description or "",
                "cover_image_url": b.cover_image_url or "",
                "file_url": b.file_url or "",
                "has_content": bool(b.content_text),
                "is_active": b.is_active,
                "created_at": b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
                "updated_at": b.updated_at.strftime("%Y-%m-%d %H:%M") if b.updated_at else ""
            }
            for b in books
        ],
        "total": len(books)
    }


@router.post("/subjects/{subject_id}/books")
def create_subject_book(
    subject_id: str,
    payload: SubjectBookCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fanga yangi kitob qo'shish.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id, TeacherSubject.teacher_id == teacher_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi.")

    # Agar bu "main" kitob bo'lsa, eski asosiy kitobni faolsizlashtirish
    if payload.book_type == "main":
        db.query(SubjectBook).filter(
            SubjectBook.subject_id == subject_id,
            SubjectBook.book_type == "main",
            SubjectBook.is_active == True
        ).update({SubjectBook.is_active: False})

    book = SubjectBook(
        subject_id=subject_id,
        teacher_id=teacher_id,
        title=payload.title.strip(),
        author=payload.author.strip() if payload.author else None,
        isbn=payload.isbn.strip() if payload.isbn else None,
        publisher=payload.publisher.strip() if payload.publisher else None,
        year=payload.year,
        edition=payload.edition.strip() if payload.edition else None,
        book_type=payload.book_type,
        description=payload.description or "",
        cover_image_url=payload.cover_image_url or "",
        file_url=payload.file_url or "",
        content_text=payload.content_text or ""
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    return {
        "status": "success",
        "message": f"'{book.title}' kitobi '{subj.name}' faniga muvaffaqiyatli qo'shildi.",
        "book_id": book.id
    }


@router.get("/subjects/{subject_id}/books/{book_id}")
def get_book_detail(
    subject_id: str,
    book_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bitta kitobning to'liq ma'lumoti.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    book = db.query(SubjectBook).filter(
        SubjectBook.id == book_id,
        SubjectBook.subject_id == subject_id,
        SubjectBook.teacher_id == teacher_id
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Kitob topilmadi.")

    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id).first()

    return {
        "id": book.id,
        "subject_id": book.subject_id,
        "subject_name": subj.name if subj else "",
        "teacher_id": book.teacher_id,
        "title": book.title,
        "author": book.author or "",
        "isbn": book.isbn or "",
        "publisher": book.publisher or "",
        "year": book.year,
        "edition": book.edition or "",
        "book_type": book.book_type,
        "description": book.description or "",
        "cover_image_url": book.cover_image_url or "",
        "file_url": book.file_url or "",
        "content_text": book.content_text or "",
        "is_active": book.is_active,
        "created_at": book.created_at.strftime("%Y-%m-%d %H:%M") if book.created_at else "",
        "updated_at": book.updated_at.strftime("%Y-%m-%d %H:%M") if book.updated_at else ""
    }


@router.put("/subjects/{subject_id}/books/{book_id}")
def update_subject_book(
    subject_id: str,
    book_id: str,
    payload: SubjectBookUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Kitob ma'lumotlarini yangilash.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    book = db.query(SubjectBook).filter(
        SubjectBook.id == book_id,
        SubjectBook.subject_id == subject_id,
        SubjectBook.teacher_id == teacher_id
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Kitob topilmadi.")

    # Agar book_type "main" ga o'zgartirilayotgan bo'lsa, boshqa asosiy kitoblarni faolsizlashtirish
    if payload.book_type == "main" and book.book_type != "main":
        db.query(SubjectBook).filter(
            SubjectBook.subject_id == subject_id,
            SubjectBook.book_type == "main",
            SubjectBook.is_active == True,
            SubjectBook.id != book_id
        ).update({SubjectBook.is_active: False})

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            if isinstance(value, str):
                setattr(book, key, value.strip() if value.strip() else value)
            else:
                setattr(book, key, value)

    book.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(book)

    return {
        "status": "success",
        "message": f"'{book.title}' kitobi yangilandi.",
        "book_id": book.id
    }


@router.delete("/subjects/{subject_id}/books/{book_id}")
def delete_subject_book(
    subject_id: str,
    book_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Kitobni o'chirish.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    book = db.query(SubjectBook).filter(
        SubjectBook.id == book_id,
        SubjectBook.subject_id == subject_id,
        SubjectBook.teacher_id == teacher_id
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Kitob topilmadi.")

    title = book.title
    db.delete(book)
    db.commit()

    return {"status": "success", "message": f"'{title}' kitobi o'chirildi."}


@router.post("/subjects/{subject_id}/books/{book_id}/extract-content")
async def extract_book_content(
    subject_id: str,
    book_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Kitob faylidan (PDF/DOCX) matnni ajratib olib, kitob content_text maydoniga saqlash.
    """
    teacher_id = current_user.get("id") or current_user.get("sub")
    book = db.query(SubjectBook).filter(
        SubjectBook.id == book_id,
        SubjectBook.subject_id == subject_id,
        SubjectBook.teacher_id == teacher_id
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Kitob topilmadi.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fayl bo'sh.")

    # Fayl turini aniqlash va matn ajratish
    filename = file.filename.lower()
    extracted_text = ""

    try:
        if filename.endswith('.pdf'):
            import io
            import PyPDF2
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
        elif filename.endswith('.docx'):
            import io
            from docx import Document
            doc_file = io.BytesIO(content)
            doc = Document(doc_file)
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
        elif filename.endswith('.txt'):
            extracted_text = content.decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Qo'llab-quvvatlanmaydigan fayl formati. PDF, DOCX yoki TXT yuklang.")

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Fayldan matn ajratib bo'lmadi.")

        # Matnni tozalash (juda uzun bo'lmasligi uchun kesish)
        max_chars = 50000  # AI token limitlari uchun
        if len(extracted_text) > max_chars:
            extracted_text = extracted_text[:max_chars] + "\n\n[... matn qisqartirildi ...]"

        book.content_text = extracted_text.strip()
        book.file_url = file.filename
        book.updated_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "message": f"Kitob mazmuni muvaffaqiyatli ajratildi ({len(extracted_text)} belgilar).",
            "content_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
            "total_chars": len(extracted_text)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matn ajratishda xatolik: {str(e)}")


# ============================================================
# 4. AI BILAN TEST VA PREZENTATSIYA TAYYORLASH VA SAQLASH
# ============================================================

# Limitlar: Free obunachi uchun
FREE_LIMIT_TESTS = 5
FREE_LIMIT_PRESENTATIONS = 6

def check_material_limit(db: Session, teacher_id: str, material_type: str, current_user: dict):
    """Free obunachi uchun test va slayd limitlarini tekshirish."""
    subscription_tier = current_user.get("subscription_tier", "free")
    if subscription_tier == "pro":
        return True, None  # PRO uchun cheksiz
    
    # Free foydalanuvchi uchun limitlar
    test_count = db.query(TeacherMaterial).filter(
        TeacherMaterial.teacher_id == teacher_id,
        TeacherMaterial.material_type == "test"
    ).count()
    presentation_count = db.query(TeacherMaterial).filter(
        TeacherMaterial.teacher_id == teacher_id,
        TeacherMaterial.material_type == "presentation"
    ).count()
    
    if material_type == "test":
        if test_count >= FREE_LIMIT_TESTS:
            return False, f"Tekin tarifda test yaratish limiti tugadi (5/5). PRO tarifga o'tib cheksiz test yarating."
        return True, f"Qolgan testlar: {FREE_LIMIT_TESTS - test_count}/{FREE_LIMIT_TESTS}"
    elif material_type == "presentation":
        if presentation_count >= FREE_LIMIT_PRESENTATIONS:
            return False, f"Tekin tarifda slayd yaratish limiti tugadi (6/6). PRO tarifga o'tib cheksiz slayd yarating."
        return True, f"Qolgan slaydlar: {FREE_LIMIT_PRESENTATIONS - presentation_count}/{FREE_LIMIT_PRESENTATIONS}"
    
    return True, None


@router.post("/generate-material")
async def generate_teacher_material(
    payload: MaterialGenerateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Tanlangan mavzu bo'yicha AI (DeepSeek / Pedagogik model) orqali Test, Prezentatsiya
    yoki Dars rejasini tayyorlash va o'qituvchi profilida DOIMIY saqlash.
    Agar book_id berilgan bo'lsa, kitob mazmunidan foydalanib material yaratadi.
    """
    teacher_id = current_user.get("id")
    is_admin = current_user.get("role") == "admin"
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == payload.subject_id).first()
    if not subj or (not is_admin and subj.teacher_id != teacher_id):
        raise HTTPException(status_code=404, detail="Tanlangan fan topilmadi yoki sizga tegishli emas.")

    # Qo'shimcha fanlar: material shu fanlarga ham (nusxa sifatida) biriktiriladi
    extra_subjects = []
    for sid in dict.fromkeys(payload.subject_ids or []):
        if sid == subj.id:
            continue
        es = db.query(TeacherSubject).filter(TeacherSubject.id == sid).first()
        if not es or (not is_admin and es.teacher_id != teacher_id):
            raise HTTPException(status_code=404, detail=f"Qo'shimcha fan topilmadi yoki sizga tegishli emas: {sid}")
        extra_subjects.append(es)

    topic_title = payload.topic_title.strip()
    material_type = payload.material_type.lower()
    subject_name = subj.name

    # Kitob mazmunini olish (agar book_id berilgan bo'lsa)
    book_content = None
    book_title = None
    book_id = getattr(payload, "book_id", None)
    use_book_content = getattr(payload, "use_book_content", True)
    if book_id and use_book_content:
        book = db.query(SubjectBook).filter(
            SubjectBook.id == book_id,
            SubjectBook.subject_id == payload.subject_id,
            SubjectBook.teacher_id == teacher_id,
            SubjectBook.is_active == True
        ).first()
        if book and book.content_text:
            book_content = book.content_text
            book_title = book.title

    # Free obunachi limitlarini tekshirish
    if material_type in ["test", "presentation"]:
        allowed, limit_msg = check_material_limit(db, teacher_id, material_type, current_user)
        if not allowed:
            raise HTTPException(status_code=403, detail=limit_msg)

    result_data = None
    title_name = ""
    lang = (payload.language or "uz").lower()
    if lang not in ("uz", "en", "ru"):
        lang = "uz"

    if material_type == "test":
        num_q = getattr(payload, "num_questions", None) or 5
        result_data = await ai_service.generate_topic_test(
            topic_title=topic_title,
            subject_name=subject_name,
            num_questions=num_q,
            difficulty=payload.difficulty or "B2",
            book_content=book_content,
            book_title=book_title,
            extra_instructions=payload.extra_instructions,
            language=lang
        )
        title_name = result_data.get("title", f"{topic_title} — Nazorat Testi")

    elif material_type == "presentation":
        num_s = getattr(payload, "num_slides", None) or 6
        image_mode = payload.image_mode or ("ai" if (payload.with_images is None or payload.with_images) else "none")
        result_data = await ai_service.generate_topic_presentation(
            topic_title=topic_title,
            subject_name=subject_name,
            num_slides=num_s,
            with_images=image_mode != "none",
            book_content=book_content,
            book_title=book_title,
            image_mode=image_mode,
            extra_instructions=payload.extra_instructions,
            language=lang
        )
        title_name = result_data.get("title", f"{topic_title} — Prezentatsiya")

    elif material_type == "lesson_plan":
        result_data = await ai_service.generate_topic_lesson_plan(
            topic_title=topic_title,
            subject_name=subject_name,
            book_content=book_content,
            book_title=book_title,
            language=lang
        )
        title_name = result_data.get("title", f"{topic_title} — Dars Ishlanmasi")

    elif material_type == "writing":
        result_data = await matsvc.generate_writing_material(
            ai_service,
            topic_title=topic_title,
            subject_name=subject_name,
            cefr=payload.difficulty or "B2",
            min_words=payload.min_words or 150,
            max_words=payload.max_words or 200,
            extra_instructions=payload.extra_instructions,
            book_content=book_content,
            language=lang
        )
        title_name = result_data.get("title", f"{topic_title} — Yozma topshiriq")

    else:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri material turi: {material_type}. Faqat 'test', 'presentation', 'lesson_plan', 'writing' mumkin.")

    # 4-QOIDA: "va o'sha profilidan o'chib ketmasin" — Ma'lumotlar bazasiga yozish
    saved_material = TeacherMaterial(
        teacher_id=teacher_id,
        subject_id=subj.id,
        topic_id=payload.topic_id,
        topic_title=topic_title,
        material_type=material_type,
        title=title_name,
        content_json=result_data,
        content_text=str(result_data.get("title", ""))
    )
    db.add(saved_material)
    # Qo'shimcha fanlar uchun nusxalar (bir xil mazmun, alohida qatorlar)
    copies = []
    for es in extra_subjects:
        c = TeacherMaterial(
            teacher_id=teacher_id, subject_id=es.id, topic_id=None, topic_title=topic_title,
            material_type=material_type, title=title_name, content_json=result_data,
            content_text=str(result_data.get("title", "")),
        )
        db.add(c)
        copies.append(c)
    db.commit()
    db.refresh(saved_material)

    # Qolgan limitlarni hisoblash
    limit_info = None
    if material_type in ["test", "presentation"]:
        _, limit_info = check_material_limit(db, teacher_id, material_type, current_user)

    return {
        "status": "success",
        "message": f"'{title_name}' muvaffaqiyatli tayyorlandi va profilingizda saqlandi.",
        "material_id": saved_material.id,
        "material_type": material_type,
        "title": title_name,
        "subject_name": subject_name,
        "topic_title": topic_title,
        "book_used": book_title,
        "data": result_data,
        "created_at": saved_material.created_at.strftime("%Y-%m-%d %H:%M"),
        "limit_info": limit_info,
        "assigned_subjects": [subj.name] + [es.name for es in extra_subjects],
        "copies": [c.id for c in copies],
    }


class AssignMaterialRequest(BaseModel):
    subject_ids: List[str]


@router.post("/materials/{material_id}/assign")
def assign_material_to_subjects(
    material_id: str,
    payload: AssignMaterialRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Tayyor materialni o'qituvchining boshqa fanlariga ham biriktirish (nusxa yaratish).

    Bir fanda bir xil sarlavha va mavzuli material allaqachon bo'lsa, qayta nusxalanmaydi.
    """
    teacher_id = current_user.get("id")
    is_admin = current_user.get("role") == "admin"
    q = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id)
    if not is_admin:
        q = q.filter(TeacherMaterial.teacher_id == teacher_id)
    m = q.first()
    if not m:
        raise HTTPException(status_code=404, detail="Material topilmadi.")

    created, skipped = [], []
    for sid in dict.fromkeys(payload.subject_ids or []):
        if sid == m.subject_id:
            skipped.append(sid)
            continue
        es = db.query(TeacherSubject).filter(TeacherSubject.id == sid).first()
        if not es or (not is_admin and es.teacher_id != m.teacher_id):
            raise HTTPException(status_code=404, detail=f"Fan topilmadi yoki sizga tegishli emas: {sid}")
        dup = db.query(TeacherMaterial).filter(
            TeacherMaterial.subject_id == sid, TeacherMaterial.material_type == m.material_type,
            TeacherMaterial.title == m.title, TeacherMaterial.topic_title == m.topic_title,
        ).first()
        if dup:
            skipped.append(sid)
            continue
        c = TeacherMaterial(
            teacher_id=m.teacher_id, subject_id=sid, topic_id=None, topic_title=m.topic_title,
            material_type=m.material_type, title=m.title, content_json=m.content_json, content_text=m.content_text,
        )
        db.add(c)
        db.flush()
        created.append({"id": c.id, "subject_id": sid, "subject_name": es.name})
    db.commit()
    return {
        "status": "success",
        "message": f"{len(created)} ta fanga biriktirildi" + (f", {len(skipped)} tasida allaqachon bor edi." if skipped else "."),
        "created": created,
        "skipped": skipped,
    }


@router.get("/materials/{material_id}/results")
def get_material_results(
    material_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Material bo'yicha talabalar natijalari: har bir talabaning eng yaxshi urinishi va umumiy ko'rsatkichlar."""
    teacher_id = current_user.get("id")
    is_admin = current_user.get("role") == "admin"
    q = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id)
    if not is_admin:
        q = q.filter(TeacherMaterial.teacher_id == teacher_id)
    m = q.first()
    if not m:
        raise HTTPException(status_code=404, detail="Material topilmadi.")

    attempts = db.query(MaterialAttempt).filter(MaterialAttempt.material_id == material_id).order_by(MaterialAttempt.created_at.desc()).all()
    students = {u.id: u for u in db.query(User).filter(User.id.in_({a.student_id for a in attempts})).all()} if attempts else {}

    per_student: Dict[str, Dict[str, Any]] = {}
    for a in attempts:
        row = per_student.get(a.student_id)
        item = matsvc.serialize_attempt(a, students.get(a.student_id))
        if not row:
            item["attempts"] = 1
            per_student[a.student_id] = item
        else:
            row["attempts"] += 1
            if (a.score or 0) > (row.get("score") or 0):
                row.update({k: item[k] for k in ("id", "score", "correct_count", "total_count", "passed")})
            if a.status == "completed":
                row["status"] = "completed"

    rows = sorted(per_student.values(), key=lambda r: (-(r.get("score") or 0), r.get("student_name") or ""))
    scored = [r["score"] for r in rows if r.get("score") is not None]
    return {
        "material": {"id": m.id, "title": m.title, "material_type": m.material_type, "topic_title": m.topic_title, "subject_id": m.subject_id},
        "summary": {
            "students": len(rows),
            "attempts": len(attempts),
            "completed": sum(1 for r in rows if r.get("status") == "completed"),
            "average_score": round(sum(scored) / len(scored)) if scored else None,
            "passed": sum(1 for r in rows if r.get("passed")),
        },
        "results": rows,
    }


@router.get("/materials/{material_id}/results/{attempt_id}")
def get_material_attempt_detail(
    material_id: str,
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Bitta urinishning to'liq mazmuni (yozma matn va rubrika yoki test javoblari)."""
    teacher_id = current_user.get("id")
    is_admin = current_user.get("role") == "admin"
    a = db.query(MaterialAttempt).filter(MaterialAttempt.id == attempt_id, MaterialAttempt.material_id == material_id).first()
    if not a or (not is_admin and a.teacher_id != teacher_id):
        raise HTTPException(status_code=404, detail="Urinish topilmadi.")
    st = db.query(User).filter(User.id == a.student_id).first()
    d = matsvc.serialize_attempt(a, st)
    d["answers"] = a.answers_json
    d["result"] = a.result_json
    return d


@router.get("/materials")
def get_teacher_materials(
    subject_id: Optional[str] = None,
    material_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchining barcha tayyorlangan materiallari arxivi (profilida saqlanadi).
    """
    teacher_id = current_user.get("id")
    query = db.query(TeacherMaterial).filter(TeacherMaterial.teacher_id == teacher_id)

    if subject_id:
        query = query.filter(TeacherMaterial.subject_id == subject_id)
    if material_type:
        query = query.filter(TeacherMaterial.material_type == material_type)

    materials = query.order_by(TeacherMaterial.created_at.desc()).all()

    # Har bir material bo'yicha nechta alohida talaba bajargani
    attempt_rows = db.query(MaterialAttempt.material_id, MaterialAttempt.student_id).filter(
        MaterialAttempt.material_id.in_([m.id for m in materials])
    ).all() if materials else []
    students_by_mat: Dict[str, set] = {}
    for mid, sid in attempt_rows:
        students_by_mat.setdefault(mid, set()).add(sid)

    result = []
    for m in materials:
        subj = db.query(TeacherSubject).filter(TeacherSubject.id == m.subject_id).first()
        result.append({
            "id": m.id,
            "subject_id": m.subject_id,
            "subject_name": subj.name if subj else "Fan",
            "topic_title": m.topic_title,
            "material_type": m.material_type,
            "title": m.title,
            "content": m.content_json,
            "students_done": len(students_by_mat.get(m.id, ())),
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
        })

    return {"materials": result, "total": len(result)}


@router.get("/materials/stats")
def get_teacher_material_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchining material yaratish statistikasi va limitlari.
    """
    teacher_id = current_user.get("id")
    subscription_tier = current_user.get("subscription_tier", "free")
    
    test_count = db.query(TeacherMaterial).filter(
        TeacherMaterial.teacher_id == teacher_id,
        TeacherMaterial.material_type == "test"
    ).count()
    presentation_count = db.query(TeacherMaterial).filter(
        TeacherMaterial.teacher_id == teacher_id,
        TeacherMaterial.material_type == "presentation"
    ).count()
    lesson_plan_count = db.query(TeacherMaterial).filter(
        TeacherMaterial.teacher_id == teacher_id,
        TeacherMaterial.material_type == "lesson_plan"
    ).count()
    writing_count = db.query(TeacherMaterial).filter(
        TeacherMaterial.teacher_id == teacher_id,
        TeacherMaterial.material_type == "writing"
    ).count()
    
    is_pro = subscription_tier == "pro"
    
    return {
        "subscription_tier": subscription_tier,
        "is_pro": is_pro,
        "counts": {
            "test": test_count,
            "presentation": presentation_count,
            "lesson_plan": lesson_plan_count,
            "writing": writing_count,
            "total": test_count + presentation_count + lesson_plan_count + writing_count
        },
        "limits": {
            "test": None if is_pro else FREE_LIMIT_TESTS,
            "presentation": None if is_pro else FREE_LIMIT_PRESENTATIONS,
            "lesson_plan": None
        },
        "remaining": {
            "test": None if is_pro else max(0, FREE_LIMIT_TESTS - test_count),
            "presentation": None if is_pro else max(0, FREE_LIMIT_PRESENTATIONS - presentation_count),
            "lesson_plan": None
        }
    }


@router.get("/materials/{material_id}")
def get_material_detail(
    material_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bitta materialning to'liq ma'lumoti.
    """
    teacher_id = current_user.get("id")
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id, TeacherMaterial.teacher_id == teacher_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material topilmadi.")

    subj = db.query(TeacherSubject).filter(TeacherSubject.id == m.subject_id).first()
    return {
        "id": m.id,
        "subject_id": m.subject_id,
        "subject_name": subj.name if subj else "Fan",
        "topic_title": m.topic_title,
        "material_type": m.material_type,
        "title": m.title,
        "content": m.content_json,
        "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
    }


@router.delete("/materials/{material_id}")
def delete_material(
    material_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Materialni o'chirish.
    """
    teacher_id = current_user.get("id")
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id, TeacherMaterial.teacher_id == teacher_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material topilmadi.")

    db.delete(m)
    db.commit()
    return {"status": "success", "message": f"'{m.title}' o'chirildi."}


class RegenerateSlideImageRequest(BaseModel):
    topic: str
    subject: Optional[str] = "Fan"
    slide_title: Optional[str] = ""
    prompt: Optional[str] = None
    slide_index: Optional[int] = 0


@router.post("/materials/regenerate-slide-image")
def regenerate_slide_image(
    payload: RegenerateSlideImageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Slayd uchun yangi unikal AI rasm URL generatsiya qilish (keshni chetlab o'tish).
    """
    import random
    from app.services.ai_service import build_ai_image_url
    new_seed = random.randint(100000, 9999999)
    p = payload.prompt or payload.slide_title or payload.topic
    new_url = build_ai_image_url(
        prompt=p,
        seed=new_seed,
        topic=payload.topic,
        subject=payload.subject or ""
    )
    return {
        "status": "success",
        "image_url": new_url,
        "seed": new_seed
    }


@router.post("/materials/{material_id}/slides/{slide_number}/regenerate-image")
def regenerate_saved_slide_image(
    material_id: str,
    slide_number: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bazadagi saqlangan taqdimot slaydining rasmini yangi AI rasmiga almashtirish va saqlash.
    """
    import random
    from app.services.ai_service import build_ai_image_url

    teacher_id = current_user.get("id")
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id, TeacherMaterial.teacher_id == teacher_id).first()
    if not m or m.material_type != "presentation":
        raise HTTPException(status_code=404, detail="Taqdimot topilmadi.")

    content = dict(m.content_json or {})
    slides = content.get("slides", [])
    if slide_number < 1 or slide_number > len(slides):
        raise HTTPException(status_code=400, detail="Noto'g'ri slayd raqami.")

    s = slides[slide_number - 1]
    new_seed = random.randint(100000, 9999999)
    p = s.get("image_prompt") or s.get("title") or m.topic_title
    new_url = build_ai_image_url(
        prompt=p,
        seed=new_seed,
        topic=m.topic_title or "",
        subject=content.get("subject", "")
    )
    s["image_url"] = new_url
    s["image_source"] = "ai"
    content["slides"] = slides
    m.content_json = content
    db.commit()

    return {
        "status": "success",
        "slide_number": slide_number,
        "image_url": new_url,
        "seed": new_seed
    }


# ============================================================
# 4. GURUHLAR VA TAKLIFLAR
# ============================================================

def _proposal_dict(p: TeacherProposal) -> dict:
    pc = p.proposed_change or {}
    return {
        "id": p.id,
        "student_id": p.student_id,
        "student_name": pc.get("student_name", "Talaba"),
        "proposal_type": p.proposal_type,
        "proposal_text": pc.get("text", ""),
        "basis": p.basis,
        "status": p.status,
        "teacher_comment": p.teacher_comment,
        "decided_at": p.decided_at.strftime("%Y-%m-%d %H:%M") if p.decided_at else None,
        "created_at": "",
    }


def _get_proposal(db: Session, prop_id: str, current_user: dict) -> TeacherProposal:
    q = db.query(TeacherProposal).filter(TeacherProposal.id == prop_id)
    if current_user.get("role") != "admin":
        q = q.filter(TeacherProposal.teacher_id == (current_user.get("id") or current_user.get("sub")))
    p = q.first()
    if not p:
        raise HTTPException(status_code=404, detail="Taklif topilmadi.")
    return p


def _decide(db: Session, prop_id: str, new_status: str, current_user: dict, comment: Optional[str] = None) -> dict:
    p = _get_proposal(db, prop_id, current_user)
    p.status = new_status
    p.decided_at = datetime.utcnow()
    if comment is not None:
        p.teacher_comment = comment
    db.commit()
    db.refresh(p)
    label = {"approved": "tasdiqlandi va kuchga kirdi", "modified": "o'zgartirildi", "rejected": "bekor qilindi"}[new_status]
    return {"status": new_status, "message": f"{_proposal_dict(p)['student_name']} bo'yicha taklif {label}.", "proposal": _proposal_dict(p)}


@router.get("/groups")
def get_teacher_groups(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """O'qituvchi va tizimdagi barcha guruhlar ro'yxati (haqiqiy talabalar soni bilan)."""
    groups = db.query(Group).all()
    res = []
    for g in groups:
        st_count = db.query(User).filter(User.group_id == g.id, User.role == "student", User.is_approved == True).count()
        res.append({
            "id": g.id,
            "name": g.name,
            "course": g.course_year or 3,
            "students_count": st_count,
            "arm": g.experiment_arm or "experimental"
        })
    return {"groups": res}

@router.get("/proposals")
def get_proposals(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """O'qituvchining barcha takliflari (qaror bazada saqlanadi, sahifa yangilansa ham yo'qolmaydi)."""
    teacher_id = current_user.get("id") or current_user.get("sub")
    q = db.query(TeacherProposal)
    if current_user.get("role") != "admin":
        q = q.filter(TeacherProposal.teacher_id == teacher_id)
    rows = q.all()
    # pending birinchi, keyin qaror qilinganlar (yangi qarorlar yuqorida)
    rows.sort(key=lambda r: (0 if r.status == "pending" else 1, -(r.decided_at.timestamp() if r.decided_at else 0)))
    items = [_proposal_dict(r) for r in rows]
    return {
        "proposals": items,
        "pending_count": sum(1 for r in rows if r.status == "pending"),
        "rule_note": "3-qoida: Yakuniy pedagogik qaror sizniki. Tizim faqat taklif qiladi."
    }

@router.post("/proposal/{prop_id}/approve")
def approve_proposal(prop_id: str, payload: Optional[ProposalAction] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return _decide(db, prop_id, "approved", current_user, payload.teacher_comment if payload else None)

@router.post("/proposal/{prop_id}/modify")
def modify_proposal(prop_id: str, payload: Optional[ProposalAction] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return _decide(db, prop_id, "modified", current_user, payload.teacher_comment if payload else None)

@router.post("/proposal/{prop_id}/reject")
def reject_proposal(prop_id: str, payload: Optional[ProposalAction] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return _decide(db, prop_id, "rejected", current_user, payload.teacher_comment if payload else None)

@router.post("/proposal/{prop_id}/reopen")
def reopen_proposal(prop_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Qarorni qayta ko'rib chiqish uchun taklifni yana 'pending' holatiga qaytarish."""
    p = _get_proposal(db, prop_id, current_user)
    p.status = "pending"
    p.decided_at = None
    db.commit()
    return {"status": "pending", "message": "Taklif qayta ko'rib chiqish uchun ochildi.", "proposal": _proposal_dict(p)}

@router.post("/lesson/{lesson_id}/ai-lock")
def toggle_ai_lock(lesson_id: str, enable: bool = True):
    return {
        "lesson_id": lesson_id,
        "ai_locked": enable,
        "message": f"O'qituvchi tomonidan AI-lock {'yoqildi' if enable else 'o\'chirildi'}."
    }

