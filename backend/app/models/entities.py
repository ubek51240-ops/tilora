import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, SmallInteger, Boolean, Text, DateTime, ForeignKey, JSON, Float
)
from sqlalchemy.orm import relationship
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Institution(Base):
    __tablename__ = "institutions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    short_name = Column(String(50), nullable=False)
    direction_code = Column(String(20), default="60110900")
    created_at = Column(DateTime, default=datetime.utcnow)

class Group(Base):
    __tablename__ = "groups"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    institution_id = Column(String(36), ForeignKey("institutions.id"))
    name = Column(String(50), nullable=False)
    course_year = Column(SmallInteger, default=3)
    teacher_id = Column(String(36), nullable=True)
    experiment_arm = Column(String(20), default="experimental") # experimental, control, none
    # AI'siz nazorat oynasi (4.1: "yakuniy nazorat shakllari texnologik vositalardan foydalanmasdan"):
    # none | pre | mid | post — oyna ochiq bo'lsa guruh talabalari uchun AI endpointlari yopiladi
    assessment_window = Column(String(10), default="none")
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), default="student") # student, teacher, researcher, admin
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=True)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True)
    locale = Column(String(5), default="uz")
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False) # Super admin tasdiqlashi lozim
    subscription_tier = Column(String(20), default="free") # "free", "pro"
    subscription_status = Column(String(30), default="active") # "active", "pending", "expired"
    phone_number = Column(String(30), nullable=True)
    last_login_at = Column(DateTime, nullable=True)  # saqlash muddati (retention) uchun
    created_at = Column(DateTime, default=datetime.utcnow)

class StudentProfile(Base):
    """3 o'lchovli profil (tarix saqlanadi, qator o'chirilmaydi)."""
    __tablename__ = "student_profiles"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    cefr_listening = Column(String(2), default="B1")
    cefr_reading = Column(String(2), default="B2")
    cefr_speaking = Column(String(2), default="A2")
    cefr_writing = Column(String(2), default="B1")
    professional_track = Column(String(100), default="Filologiya va tillarni o'qitish (ingliz tili)")
    load_capacity = Column(SmallInteger, default=50) # 1-100
    pace_index = Column(SmallInteger, default=50)    # 1-100
    error_persistence = Column(SmallInteger, default=50) # 1-100
    anxiety_level = Column(SmallInteger, default=70) # 1-100 (FLCAS)
    motivation_type = Column(String(20), default="intrinsic")
    autonomy_readiness = Column(SmallInteger, default=40)
    source = Column(String(30), default="initial_test") # initial_test, auto_update, teacher_override
    valid_from = Column(DateTime, default=datetime.utcnow)

class LearningPath(Base):
    __tablename__ = "learning_paths"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    profile_id = Column(String(36), ForeignKey("student_profiles.id"), nullable=True)
    status = Column(String(20), default="active") # active, completed, revised
    revision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PathItem(Base):
    __tablename__ = "path_items"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    path_id = Column(String(36), ForeignKey("learning_paths.id"), nullable=False)
    week_number = Column(SmallInteger, nullable=False)
    skill = Column(String(20), nullable=False)
    topic = Column(String(255), nullable=False)
    difficulty_level = Column(SmallInteger, default=5) # 1-10
    scaffold_level = Column(String(20), default="full") # full, partial, none
    rationale = Column(Text, nullable=False) # 2-QOIDA: bo'sh bo'lishi mumkin emas
    status = Column(String(20), default="planned") # planned, current, done
    teacher_approved = Column(Boolean, default=True)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    path_item_id = Column(String(36), ForeignKey("path_items.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="in_progress") # in_progress, completed
    final_score = Column(SmallInteger, nullable=True)

class LessonStage(Base):
    __tablename__ = "lesson_stages"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    stage = Column(String(30), nullable=False) # intro, preparation, independent, analysis, reflection
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    ai_locked = Column(Boolean, default=False)
    duration_seconds = Column(Integer, default=0)

class StudentProduction(Base):
    __tablename__ = "student_productions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    skill = Column(String(20), default="writing")
    content_text = Column(Text, nullable=True)
    audio_url = Column(String(255), nullable=True)
    word_count = Column(Integer, default=0)
    ai_assisted = Column(Boolean, default=False) # HAR DOIM False
    created_at = Column(DateTime, default=datetime.utcnow)

class FeedbackItem(Base):
    __tablename__ = "feedback_items"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    production_id = Column(String(36), ForeignKey("student_productions.id"), nullable=False)
    category = Column(String(30), nullable=False) # grammar, lexis, coherence, pronunciation, content
    issue_short = Column(String(255), nullable=False)
    issue_reason = Column(Text, nullable=False) # Sabab — majburiy
    suggestion = Column(Text, nullable=True)
    l1_interference = Column(Boolean, default=False)
    student_accepts = Column(Boolean, nullable=True)
    student_note = Column(Text, nullable=True)
    teacher_extension = Column(Text, nullable=True)
    feedback_level = Column(String(30), default="task") # task, process, self_regulation

class MetacognitiveEntry(Base):
    __tablename__ = "metacognitive_entries"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    lesson_id = Column(String(36), ForeignKey("lessons.id"), nullable=False)
    self_rating = Column(JSON, nullable=True)
    actual_rating = Column(JSON, nullable=True)
    gap_explanation = Column(Text, nullable=True)
    next_goal = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TeacherProposal(Base):
    __tablename__ = "teacher_proposals"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    proposal_type = Column(String(50), nullable=False) # difficulty_change, scaffold_change, deadline_change, path_revision, methodology, assignment, peer_learning, general
    proposed_change = Column(JSON, nullable=False)
    basis = Column(Text, nullable=False) # Qaysi ko'rsatkichga tayanilgani yoki taklif maqsadi
    status = Column(String(20), default="pending") # pending, approved, modified, rejected
    teacher_comment = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ResearchConsent(Base):
    __tablename__ = "research_consents"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    consent_given = Column(Boolean, default=True)
    consent_text_version = Column(String(20), default="1.0")
    given_at = Column(DateTime, default=datetime.utcnow)
    withdrawn_at = Column(DateTime, nullable=True)

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    assessment_type = Column(String(20), default="pre") # pre, mid, post
    skill = Column(String(20), nullable=False)
    score = Column(SmallInteger, nullable=False)
    max_score = Column(SmallInteger, default=100)
    administered_at = Column(DateTime, default=datetime.utcnow)
    is_frozen = Column(Boolean, default=False)
    ai_tools_allowed = Column(Boolean, default=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    actor_id = Column(String(36), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    payload = Column(JSON, nullable=True)
    ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TeacherSubject(Base):
    """O'qituvchiga biriktirilgan fanlar va sillabuslar."""
    __tablename__ = "teacher_subjects"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    semester = Column(String(50), default="5-semestr")
    course_year = Column(SmallInteger, default=3)
    group_name = Column(String(100), default="302-guruh")
    description = Column(Text, nullable=True)
    syllabus_filename = Column(String(255), nullable=True)
    syllabus_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SyllabusTopic(Base):
    """Sillabus ichidagi haftalik mavzular."""
    __tablename__ = "syllabus_topics"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=False)
    week_number = Column(SmallInteger, default=1)
    title = Column(String(255), nullable=False)
    hours = Column(SmallInteger, default=2)
    objectives = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TeacherMaterial(Base):
    """O'qituvchi tomonidan AI yordamida yaratilgan test, prezentatsiya va dars rejalari."""
    __tablename__ = "teacher_materials"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=False)
    topic_id = Column(String(36), nullable=True)
    topic_title = Column(String(255), nullable=False)
    material_type = Column(String(50), nullable=False)  # "test", "presentation", "lesson_plan", "writing"
    title = Column(String(255), nullable=False)
    content_json = Column(JSON, nullable=True)
    content_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialAttempt(Base):
    """Talabaning mustaqil topshiriq (test, yozma ish, slayd/reja ko'rish) natijasi.

    Har bir urinish alohida qator: test uchun ball va javoblar, yozma ish uchun matn va
    AI rubrika bahosi, slayd/dars rejasi uchun "ko'rildi" belgisi. O'qituvchi shu
    jadvaldan guruh natijalarini ko'radi.
    """
    __tablename__ = "material_attempts"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    material_id = Column(String(36), ForeignKey("teacher_materials.id"), index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    material_type = Column(String(50), nullable=False)
    status = Column(String(20), default="completed")  # completed | viewed
    score = Column(Integer, nullable=True)            # foiz (0-100) yoki rubrika bali foizda
    correct_count = Column(Integer, nullable=True)
    total_count = Column(Integer, nullable=True)
    passed = Column(Boolean, nullable=True)
    answers_json = Column(JSON, nullable=True)        # test javoblari yoki yozma matn
    result_json = Column(JSON, nullable=True)         # tekshiruv/rubrika natijasi
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class SubscriptionPayment(Base):
    """Foydalanuvchilarning PRO tarifiga to'lov arizalari (Click, Payme, Uzum)."""
    __tablename__ = "subscription_payments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    user_name = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    role = Column(String(20), default="student")
    plan = Column(String(50), default="pro_monthly")  # "pro_monthly", "pro_annual"
    amount = Column(Integer, default=10)  # USD
    payment_method = Column(String(50), default="click")  # click, payme, card
    transaction_id = Column(String(100), nullable=True)
    receipt_image = Column(String(255), nullable=True)
    user_note = Column(Text, nullable=True)  # foydalanuvchi izohi (to'lov haqida) — ariza yuborishda majburiy
    status = Column(String(30), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    admin_note = Column(Text, nullable=True)


class DiagnosticTest(Base):
    """O'qituvchi tomonidan fan bo'yicha yaratilgan diagnostika testi (audio/yozma hint bilan)."""
    __tablename__ = "diagnostic_tests"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    hint_type = Column(String(20), default="written")  # "audio", "written", "mixed"
    time_limit_minutes = Column(Integer, default=30)
    max_attempts = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)
    cefr_target = Column(String(10), default="B1")  # Maqsadlangan CEFR darajasi
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions = relationship("DiagnosticQuestion", back_populates="test", cascade="all, delete-orphan")
    attempts = relationship("DiagnosticAttempt", back_populates="test")


class DiagnosticQuestion(Base):
    """Diagnostika test savoli (audio yoki yozma hint bilan)."""
    __tablename__ = "diagnostic_questions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    test_id = Column(String(36), ForeignKey("diagnostic_tests.id"), index=True, nullable=False)
    question_order = Column(Integer, default=1)
    skill = Column(String(20), nullable=False)  # listening, reading, writing, speaking, grammar, vocabulary
    cefr_level = Column(String(2), default="B1")
    question_text = Column(Text, nullable=False)  # Asosiy savol matni
    question_type = Column(String(20), default="multiple_choice")  # multiple_choice, true_false, fill_blank, audio_response
    
    # Variantlar (JSON formatida)
    options = Column(JSON, nullable=True)  # [{"text": "A", "is_correct": true}, ...]
    correct_answer = Column(Text, nullable=True)  # To'g'ri javob matni (fill_blank uchun)
    
    # Hint (dest) tizimi
    hint_type = Column(String(20), default="written")  # "audio", "written", "none"
    hint_text = Column(Text, nullable=True)  # Yozma hint matni
    hint_audio_url = Column(String(500), nullable=True)  # Audio hint URL
    hint_audio_text = Column(Text, nullable=True)  # Audio matni (transkriptsiya)
    
    # Tushuntirish
    explanation = Column(Text, nullable=True)
    points = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    test = relationship("DiagnosticTest", back_populates="questions")
    answers = relationship("DiagnosticAnswer", back_populates="question", cascade="all, delete-orphan")


class DiagnosticAttempt(Base):
    """Talabaning diagnostika testi urinish natijasi (real vaqtda)."""
    __tablename__ = "diagnostic_attempts"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    test_id = Column(String(36), ForeignKey("diagnostic_tests.id"), index=True, nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    attempt_number = Column(Integer, default=1)
    status = Column(String(20), default="in_progress")  # in_progress, completed, timed_out
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, default=0)
    
    # Natijalar
    total_score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    percentage = Column(Integer, default=0)
    grade = Column(String(20), nullable=True)  # A, B, C, D, F yoki 5,4,3,2
    
    # Ko'nikma bo'yicha natijalar (JSON)
    skill_breakdown = Column(JSON, nullable=True)  # {"listening": {"correct": 3, "total": 5, "percentage": 60}, ...}
    cefr_estimate = Column(JSON, nullable=True)  # {"listening": "B1", "reading": "B2", ...}
    
    # Xatolik tahlili
    wrong_answers = Column(JSON, nullable=True)  # [{question_id, skill, student_answer, correct_answer, hint_used}, ...]
    hints_used = Column(JSON, nullable=True)  # {question_id: "audio"|"written", ...}

    test = relationship("DiagnosticTest", back_populates="attempts")
    answers = relationship("DiagnosticAnswer", back_populates="attempt", cascade="all, delete-orphan")


class DiagnosticAnswer(Base):
    """Talabaning bitta savolga bergan javobi."""
    __tablename__ = "diagnostic_answers"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    attempt_id = Column(String(36), ForeignKey("diagnostic_attempts.id"), index=True, nullable=False)
    question_id = Column(String(36), ForeignKey("diagnostic_questions.id"), index=True, nullable=False)
    selected_option_index = Column(Integer, nullable=True)  # Multiple choice uchun
    answer_text = Column(Text, nullable=True)  # Fill-in-the-blank, audio response uchun
    is_correct = Column(Boolean, default=False)
    hint_used = Column(String(20), nullable=True)  # "audio", "written", "none"
    time_spent_seconds = Column(Integer, default=0)
    answered_at = Column(DateTime, default=datetime.utcnow)

    attempt = relationship("DiagnosticAttempt", back_populates="answers")
    question = relationship("DiagnosticQuestion", back_populates="answers")


class SubjectBook(Base):
    """Fanga bog'liq kitoblar (asosiy va qo'shimcha adabiyot)."""
    __tablename__ = "subject_books"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    isbn = Column(String(50), nullable=True)
    publisher = Column(String(255), nullable=True)
    year = Column(SmallInteger, nullable=True)
    edition = Column(String(50), nullable=True)
    book_type = Column(String(20), default="main")  # "main", "supplementary", "reference"
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)  # PDF/EPUB fayl yo'li
    content_text = Column(Text, nullable=True)  # Matn ko'rinishida (AI uchun)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomDiagnosticQuestion(Base):
    """O'qituvchi tomonidan yuklangan kirish diagnostika savoli (talaba ekranidagi JSON shakli bilan bir xil)."""
    __tablename__ = "custom_diagnostic_questions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=True)  # NULL = umumiy (barcha fanlar)
    question_order = Column(Integer, default=1)
    skill = Column(String(20), default="reading")  # listening, reading, writing, speaking
    cefr_level = Column(String(2), default="B1")
    instruction = Column(Text, nullable=True)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # ["A matni", "B matni", ...]
    correct_index = Column(Integer, default=0)
    rationale = Column(Text, nullable=True)
    is_audio = Column(Boolean, default=False)
    audio_url = Column(String(500), nullable=True)  # /uploads/audio/<fayl>
    audio_filename = Column(String(255), nullable=True)  # asl fayl nomi
    audio_text = Column(Text, nullable=True)  # transkripsiya (audio ochilmasa TTS zaxirasi)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomSurveyQuestion(Base):
    """O'qituvchi tomonidan yuklangan kognitiv-affektiv anketa (FLCAS) savoli."""
    __tablename__ = "custom_survey_questions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    teacher_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    subject_id = Column(String(36), ForeignKey("teacher_subjects.id"), index=True, nullable=True)  # NULL = umumiy (barcha fanlar)
    question_order = Column(Integer, default=1)
    dimension = Column(String(30), default="anxiety")  # anxiety, load_capacity, pace, autonomy, motivation
    prompt_uz = Column(Text, nullable=False)
    prompt_en = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LessonRecord(Base):
    """
    Yakunlangan 5 bosqichli mashg'ulotning to'liq yozuvi (dissertatsiya 3.3: refleksiya moduli
    "o'zini baholash varaqasi va dinamika ko'rsatkichlari"; 4.1: "kuzatuv varaqasi" jarayon ko'rsatkichlari).
    Metakognitiv sikl: rejalashtirish (planning) -> monitoring -> baholash (evaluation) -> refleksiya.
    """
    __tablename__ = "lesson_records"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True)
    skill = Column(String(20), default="writing")
    task_variant = Column(String(10), nullable=True)  # A (yuqori) / B (o'rta) / C (quyi)
    scaffold_level = Column(String(20), nullable=True)
    # Rejalashtirish (1-bosqich)
    plan_goal = Column(Text, nullable=True)
    plan_strategy = Column(Text, nullable=True)
    # Monitoring (3-bosqich jarayon ko'rsatkichlari)
    help_requests = Column(Integer, default=0)        # qulflangan AI tugmasini bosish urinishlari
    self_checks = Column(Integer, default=0)          # o'z-o'zini tekshirish belgilari
    independent_seconds = Column(Integer, default=0)  # mustaqil bosqichda sarflangan vaqt
    total_seconds = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    production_text = Column(Text, nullable=True)
    # Baholash (4–5-bosqich)
    score = Column(SmallInteger, nullable=True)
    rubric = Column(JSON, nullable=True)
    self_rating = Column(JSON, nullable=True)
    rating_gap = Column(Float, nullable=True)         # |o'z bahosi - tizim bahosi| o'rtacha (metakognitiv aniqlik)
    feedback_decisions = Column(JSON, nullable=True)  # [{id, title, accepts, justification}]
    l1_pattern_ids = Column(JSON, nullable=True)      # takrorlanuvchi xatolarni kuzatish uchun
    comparison_note = Column(Text, nullable=True)     # qiyosiy usul: o'z varianti va AI varianti farqi asosi
    ai_powered = Column(Boolean, default=False)
    # Refleksiya
    gap_explanation = Column(Text, nullable=True)
    next_goal = Column(Text, nullable=True)
    # Qayta ishlash (tahliliy usul): barcha qoralama versiyalar (Write & Improve / Criterion uslubi)
    drafts = Column(JSON, nullable=True)              # [{n, text, score, rubric, word_count, l1_count, cefr}]
    revision_count = Column(Integer, default=0)
    first_score = Column(SmallInteger, nullable=True)
    cefr_estimate = Column(String(2), nullable=True)  # lokal CEFR bahosi (A2/B1/B2/C1)
    relevance_score = Column(SmallInteger, nullable=True)  # topshiriqqa moslik (0–100)
    teacher_rubric = Column(JSON, nullable=True)      # ikkinchi mustaqil baholovchi (o'qituvchi) rubrikasi — inter-rater mosligi uchun
    teacher_extension = Column(Text, nullable=True)   # o'qituvchi izohni jarayon/o'zini boshqarish darajasiga ko'taradi
    teacher_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class TaskVariantAssignment(Base):
    """Tabaqalashtirish: o'qituvchi talabaga topshiriq variantini (A/B/C) biriktiradi yoki tizim taklifini o'zgartiradi."""
    __tablename__ = "task_variant_assignments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    variant = Column(String(10), nullable=False)  # A / B / C
    note = Column(Text, nullable=True)
    source = Column(String(20), default="teacher")  # teacher | system
    created_at = Column(DateTime, default=datetime.utcnow)


class SurveyResponse(Base):
    """Anketa (FLCAS / MSLQ / SILL) xom javoblari — Cronbach α (ichki izchillik) hisoblash uchun (4.1)."""
    __tablename__ = "survey_responses"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    instrument = Column(String(20), nullable=False)       # flcas | mslq | sill | cognitive
    dimension = Column(String(30), nullable=False)
    question_id = Column(String(64), nullable=False)
    rating = Column(SmallInteger, nullable=False)
    assessment_type = Column(String(10), default="pre")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Microteaching(Base):
    """Mikroo'qitish (3.2, 14-jadval): bo'lajak o'qituvchi texnologik vositali dars parchasini loyihalaydi, o'tkazadi va tahlil qiladi."""
    __tablename__ = "microteachings"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True)
    title = Column(String(255), nullable=False)
    lesson_form = Column(String(30), default="microteaching")  # microteaching | flipped | mixed | practical ...
    objective = Column(Text, nullable=True)         # SWBAT
    stages = Column(JSON, nullable=True)            # [{name, minutes, activity, technology_role}]
    tool_name = Column(String(120), nullable=True)
    tool_rationale = Column(Text, nullable=True)    # vositani tanlash sababi (majburiy — kompetensiya mezoni)
    alternative_plan = Column(Text, nullable=True)  # texnologiyasiz muqobil variant
    independent_share = Column(SmallInteger, default=35)  # mustaqil bajarish ulushi, % (>= 33 bo'lishi kerak)
    reflection = Column(Text, nullable=True)        # o'tkazilgandan keyingi refleksiv hisobot
    status = Column(String(20), default="draft")    # draft | submitted | reviewed | evaluated
    teacher_rubric = Column(JSON, nullable=True)
    teacher_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PeerReview(Base):
    """Tengdoshlar baholashi: guruhdosh mikroo'qitishni rubrika bo'yicha baholaydi (analitik rubrika, 4 mezon × 1–5)."""
    __tablename__ = "peer_reviews"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    microteaching_id = Column(String(36), ForeignKey("microteachings.id"), index=True, nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    rubric = Column(JSON, nullable=False)           # {objective, instructions, tool_use, reflection}
    strengths = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)




class ApiKey(Base):
    """
    Dasturchi (developer) va Super Admin (admin) uchun dasturiy integratsiya API kaliti.
    X-API-Key: tilora_sk_live_... yoki Authorization: ApiKey ... orqali autentifikatsiya qilinadi.
    """
    __tablename__ = "api_keys"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String(100), nullable=False)  # masalan: "Mobil ilova integratsiyasi"
    key_prefix = Column(String(30), nullable=False)  # masalan: "tilora_sk_••••7890"
    key_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 xesh
    role = Column(String(20), default="developer")  # developer, admin
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=120)  # daqiqasiga ruxsat etilgan so'rovlar soni
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

