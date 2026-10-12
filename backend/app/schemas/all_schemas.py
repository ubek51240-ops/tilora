from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth ---
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "student"  # "student" yoki "teacher"
    phone_number: Optional[str] = None
    institution_id: Optional[str] = "inst_buxdu"
    group_id: Optional[str] = None
    group_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class RegisterResponse(BaseModel):
    status: str
    message: str
    user: Dict[str, Any]

class SubscribeRequest(BaseModel):
    plan: str = "pro_monthly"  # pro_monthly, pro_annual, pro
    payment_method: str = "click"  # click, payme, card
    amount: float = 49000.0
    phone_number: Optional[str] = None
    transaction_id: Optional[str] = None

class AdminDecisionRequest(BaseModel):
    admin_note: Optional[str] = None

class UpdateCredentialsRequest(BaseModel):
    current_password: str
    new_login: Optional[str] = None
    new_password: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class CreateTeacherRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    institution_id: Optional[str] = "inst_buxdu"
    department: Optional[str] = None
    subject_name: Optional[str] = None
    subscription_tier: Optional[str] = "pro"


# --- Diagnostika va Profil ---
class DiagnosticAnswer(BaseModel):
    question_id: str
    selected_option_index: int

class SurveyAnswer(BaseModel):
    question_id: str
    rating: int = Field(..., ge=1, le=5)

class DiagnosticSubmissionRequest(BaseModel):
    diagnostic_answers: List[DiagnosticAnswer] = []
    survey_answers: List[SurveyAnswer] = []
    subject_id: Optional[str] = None  # Qaysi fan bo'yicha diagnostika (bo'sh -> umumiy)

class DiagnosticResultResponse(BaseModel):
    student_id: str
    cefr_levels: Dict[str, str]
    overall_cefr: Optional[str] = "B1"
    cognitive_affective: Dict[str, int]
    professional_track: str
    source: str
    correct_count: Optional[int] = None
    total_questions: Optional[int] = None
    question_reviews: Optional[List[Dict[str, Any]]] = None
    pedagogic_advice: Optional[Dict[str, Any]] = None
    ai_summary: Optional[str] = None

# --- O'quv Yo'li ---
class PathItemResponse(BaseModel):
    id: str
    week_number: int
    skill: str
    topic: str
    difficulty_level: int
    scaffold_level: str
    rationale: str
    status: str
    teacher_approved: bool

# --- Mashg'ulot ---
class ProductionSubmit(BaseModel):
    lesson_id: str
    content_text: str
    word_count: int

class SelfRatingSubmit(BaseModel):
    ratings: Dict[str, int] # {"content": 4, "grammar": 4, "lexis": 4, "coherence": 4}

class ReflectionSubmit(BaseModel):
    gap_explanation: str
    next_goal: str

# --- AI ---
class AITextRequest(BaseModel):
    prompt: str
    context: Optional[str] = None

# --- O'qituvchi ---
class ProposalAction(BaseModel):
    status: str # approved, modified, rejected
    teacher_comment: Optional[str] = None
    modified_change: Optional[Dict[str, Any]] = None


# --- Diagnostika Testi (Yangi tizim) ---
class DiagnosticQuestionCreate(BaseModel):
    question_order: int = 1
    skill: str = "reading"  # listening, reading, writing, speaking, grammar, vocabulary
    cefr_level: str = "B1"
    question_text: str
    question_type: str = "multiple_choice"  # multiple_choice, true_false, fill_blank, audio_response
    options: Optional[List[Dict[str, Any]]] = None  # [{"text": "A", "is_correct": true}, ...]
    correct_answer: Optional[str] = None
    hint_type: str = "written"  # "audio", "written", "none"
    hint_text: Optional[str] = None
    hint_audio_url: Optional[str] = None
    hint_audio_text: Optional[str] = None
    explanation: Optional[str] = None
    points: int = 1


class DiagnosticTestCreate(BaseModel):
    subject_id: str
    title: str
    description: Optional[str] = None
    hint_type: str = "written"  # "audio", "written", "mixed"
    time_limit_minutes: int = 30
    max_attempts: int = 1
    cefr_target: str = "B1"
    questions: List[DiagnosticQuestionCreate] = []


class DiagnosticTestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hint_type: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    cefr_target: Optional[str] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None


class DiagnosticQuestionResponse(BaseModel):
    id: str
    question_order: int
    skill: str
    cefr_level: str
    question_text: str
    question_type: str
    options: Optional[List[Dict[str, Any]]] = None
    hint_type: str
    hint_text: Optional[str] = None
    hint_audio_url: Optional[str] = None
    hint_audio_text: Optional[str] = None
    explanation: Optional[str] = None
    points: int
    # To'g'ri javobni yashirish (faqat o'qituvchi uchun)
    correct_answer: Optional[str] = None
    correct_option_index: Optional[int] = None


class DiagnosticTestResponse(BaseModel):
    id: str
    teacher_id: str
    subject_id: str
    subject_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    hint_type: str
    time_limit_minutes: int
    max_attempts: int
    is_active: bool
    is_published: bool
    cefr_target: str
    questions_count: int
    total_points: int
    created_at: datetime
    updated_at: datetime


class DiagnosticTestDetailResponse(DiagnosticTestResponse):
    questions: List[DiagnosticQuestionResponse] = []


# Talaba uchun diagnostika savoli (javob yashirilgan)
class StudentDiagnosticQuestionResponse(BaseModel):
    id: str
    question_order: int
    skill: str
    cefr_level: str
    question_text: str
    question_type: str
    options: Optional[List[Dict[str, Any]]] = None  # is_correct yashirilgan
    hint_type: str
    hint_text: Optional[str] = None
    hint_audio_url: Optional[str] = None
    hint_audio_text: Optional[str] = None
    points: int


class StudentDiagnosticTestResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    hint_type: str
    time_limit_minutes: int
    max_attempts: int
    cefr_target: str
    questions: List[StudentDiagnosticQuestionResponse] = []


# Talaba javob berish
class DiagnosticAnswerSubmit(BaseModel):
    question_id: str
    selected_option_index: Optional[int] = None
    answer_text: Optional[str] = None
    hint_used: Optional[str] = None  # "audio", "written", "none"
    time_spent_seconds: int = 0


class DiagnosticAttemptSubmit(BaseModel):
    answers: List[DiagnosticAnswerSubmit]


class SkillBreakdown(BaseModel):
    correct: int
    total: int
    percentage: int


# --- Kitoblar (Subject Books) ---
class SubjectBookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    edition: Optional[str] = None
    book_type: str = "main"  # main, supplementary, reference
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    file_url: Optional[str] = None
    content_text: Optional[str] = None


class SubjectBookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    edition: Optional[str] = None
    book_type: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    file_url: Optional[str] = None
    content_text: Optional[str] = None
    is_active: Optional[bool] = None


class SubjectBookResponse(BaseModel):
    id: str
    subject_id: str
    teacher_id: str
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    edition: Optional[str] = None
    book_type: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    file_url: Optional[str] = None
    content_text: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SubjectBookDetailResponse(SubjectBookResponse):
    pass


# MaterialGenerateRequest yangilash - book_id va num_questions maydonlari
class MaterialGenerateRequest(BaseModel):
    subject_id: str
    subject_ids: Optional[List[str]] = None  # Qo'shimcha fanlar: material shu fanlarga ham biriktiriladi
    topic_title: str
    topic_id: Optional[str] = None
    material_type: str = "test"  # "test", "presentation", "lesson_plan", "writing"
    min_words: Optional[int] = Field(150, ge=30, le=2000)   # writing uchun
    max_words: Optional[int] = Field(200, ge=30, le=3000)   # writing uchun
    difficulty: Optional[str] = "B2"
    extra_instructions: Optional[str] = None
    num_questions: Optional[int] = Field(5, ge=1, le=60)  # O'qituvchi tanlagan test savollari soni (1-60)
    num_slides: Optional[int] = Field(6, ge=1, le=40)  # O'qituvchi tanlagan slaydlar soni (1-40)
    with_images: Optional[bool] = True
    image_mode: Optional[str] = None  # "ai" (har slaydga AI rasm), "photo" (tayyor foto), "none" (rasmsiz)
    book_id: Optional[str] = None  # Yangi: kitob IDsi
    use_book_content: Optional[bool] = True  # Kitob mazmunidan foydalanish
    language: Optional[str] = "uz"  # "uz" (O'zbek), "ru" (Rus), "en" (Ingliz)


class DiagnosticAttemptResponse(BaseModel):
    id: str
    test_id: str
    test_title: str
    attempt_number: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    time_spent_seconds: int
    total_score: int
    max_score: int
    percentage: int
    grade: Optional[str] = None
    skill_breakdown: Dict[str, SkillBreakdown] = {}
    cefr_estimate: Dict[str, str] = {}
    wrong_answers: List[Dict[str, Any]] = []
    hints_used: Dict[str, str] = {}


class DiagnosticAttemptListResponse(BaseModel):
    attempts: List[DiagnosticAttemptResponse]
    total: int
    best_percentage: int
    latest_attempt: Optional[DiagnosticAttemptResponse] = None
