import os
import sys

# Windows Application Control ujson DLL bloklanishidan himoya
sys.modules['ujson'] = None

# HTTPS: tizim (Windows/macOS) sertifikat omboridan foydalanish.
# Antivirus (Avast va h.k.) yoki korporativ proksi HTTPS ni o'z sertifikati bilan
# "tekshirsa", Python'ning o'z CA ro'yxati uni tanimaydi va AI API ulanmaydi.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base
import app.models

from app.api.auth import router as auth_router
from app.api.student import router as student_router
from app.api.lesson import router as lesson_router
from app.api.ai import router as ai_router
from app.api.teacher import router as teacher_router
from app.api.teacher_diagnostic import router as teacher_diag_router
from app.api.feedback import router as feedback_router
from app.api.research import router as research_router
from app.api.admin import router as admin_router
from app.api.proposals import router as proposals_router
from app.api.api_keys import router as api_keys_router

# Ma'lumotlar bazasini yaratish
Base.metadata.create_all(bind=engine)

def _ensure_columns():
    """create_all mavjud jadvalga ustun qo'shmaydi; yetishmayotgan ustunlarni ALTER TABLE bilan qo'shamiz."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    needed = {
        "custom_diagnostic_questions": [("subject_id", "VARCHAR(36)")],
        "custom_survey_questions": [("subject_id", "VARCHAR(36)")],
        "teacher_proposals": [
            ("sender_id", "VARCHAR(36)"),
            ("receiver_id", "VARCHAR(36)"),
            ("created_at", "DATETIME")
        ]
    }
    with engine.begin() as conn:
        for table, cols in needed.items():
            if table not in insp.get_table_names():
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col, ctype in cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}"))

_ensure_columns()

tags_metadata = [
    {
        "name": "Autentifikatsiya",
        "description": "Foydalanuvchi tizimga kirishi (login), ro'yxatdan o'tishi (register), JWT token olish va obuna tekshiruvi."
    },
    {
        "name": "Talaba",
        "description": "Talabaning 3 o'lchovli profili (CEFR ko'nikmalar, ESP kasbiy yo'nalish, FLCAS kognitiv tashvish), 16 haftalik yo'l va o'quv materiallari."
    },
    {
        "name": "Mashg'ulot",
        "description": "5 bosqichli adaptiv mashg'ulot modeli: 1. Dars maqsadi, 2. Skaffolding ko'mak, 3. Mustaqil nutqiy mahsulot (AI yopiq - 1-tamoyil), 4. Sababli tahlil (2-tamoyil), 5. Metakognitiv refleksiya (4-tamoyil)."
    },
    {
        "name": "Takliflar va Pedagogik Muloqot",
        "description": "3-tamoyil: Pedagogik suverenitet. O'qituvchilar, talabalar va AI o'rtasidagi takliflar almashinuvi, tasdiqlash, o'zgartirish va rad etish boshqaruvi."
    },
    {
        "name": "O'qituvchi",
        "description": "Fanlar boshqaruvi, AI orqali 16 haftalik sillabus generatsiyasi, testlar, taqdimotlar va dars rejalari yaratish."
    },
    {
        "name": "O'qituvchi: Diagnostika banki",
        "description": "CEFR 4 ko'nikma bo'yicha diagnostik test savollari, audio/TTS yozuvlar va FLCAS anketa savollari banki boshqaruvi."
    },
    {
        "name": "Sun'iy Intellekt Vositalari",
        "description": "DeepSeek v4 va TAAM AI lingvistik tahlil mexanizmi, skaffolding tavsiyalari va matn baholash."
    },
    {
        "name": "Izohlar",
        "description": "Hattie & Timperley modeli asosidagi sababli pedagogik izohlar va ona tili (L1) interferensiyasi tahlili."
    },
    {
        "name": "Tadqiqotchi",
        "description": "DSc Dissertatsiyasi 4-bobi uchun matematik-statistik hisob-kitoblar, 4.2–4.9 jadvallar, Bespalko K ko'rsatkichi, Word (.docx) va Excel (.xlsx) eksporti."
    },
    {
        "name": "Administrator",
        "description": "Super administrator paneli: o'qituvchi va talabalarni tasdiqlash, guruhlar va tizim monitoringi."
    },
    {
        "name": "API Kalitlari (API Keys)",
        "description": "Dasturchi (developer) va Super Admin (admin) uchun maxfiy API kalitlarini yaratish, bekor qilish va boshqarish."
    }
]

app_description = """
# 🎓 TILORA Platformasi RESTful API Hujjatlari

Mazkur API pedagogika fanlari doktori (DSc) ilmiy tadqiqoti doirasida yaratilgan:
- **Tadqiqotchi:** Ikramova Aziza Aminovna  
- **Ixtisoslik:** 13.00.02 – Ta'lim va tarbiya nazariyasi va metodikasi  
- **Mavzu:** «Ingliz tilini sun'iy intellekt texnologiyalari asosida o'qitish metodikasini takomillashtirish»
- **Muassasa:** Buxoro davlat universiteti, Chet tillar fakulteti

---

### 🏛️ To'rt Asosiy Pedagogik Tamoyil:
1. **1-Qoida: Mustaqil bosqichda AI yopiq** (`POST /api/lesson/save-production`) — talaba matn yaratayotganida tashqi AI qulflanadi.
2. **2-Qoida: Sabab shablonda ochiq** (`GET /api/feedback/item/{id}`) — Hattie & Timperley modeli bo'yicha xato sababi ko'rsatiladi.
3. **3-Qoida: Yakuniy qaror o'qituvchida** (`POST /api/proposals/{id}/approve`) — Pedagogik suverenitet saqlanadi.
4. **4-Qoida: Xulosani talaba chiqaradi** (`POST /api/lesson/stage5/reflection`) — Talaba o'z bahosi va AI bahosi tafovutini tahlil qiladi.

---

### 🔐 Autentifikatsiya:
Barcha himoyalangan endpointlar uchun HTTP sarlavhasi (Header) talab etiladi:
`Authorization: Bearer <access_token>`  
Token olish uchun: `POST /api/auth/login`
"""

app = FastAPI(
    title=settings.PROJECT_NAME + " - RESTful API",
    version=settings.VERSION,
    description=app_description,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (Barcha xavfsiz so'rovlar uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend fayllari (HTML/JS/CSS) brauzerda keshlanib qolmasin — har yangilanish darhol ko'rinadi
@app.middleware("http")
async def no_cache_frontend(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if not path.startswith(settings.API_V1_STR) and (
        path in ("/", "") or path.endswith((".html", ".js", ".css"))
    ):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# 1. API routerlarini ulash (51 ta endpoint)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(student_router, prefix=settings.API_V1_STR)
app.include_router(lesson_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(teacher_router, prefix=settings.API_V1_STR)
app.include_router(teacher_diag_router, prefix=settings.API_V1_STR)
app.include_router(feedback_router, prefix=settings.API_V1_STR)
app.include_router(research_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(proposals_router, prefix=settings.API_V1_STR)
app.include_router(api_keys_router, prefix=settings.API_V1_STR)

# 2. Frontend statik fayllarni ulash
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(base_dir, "frontend")
css_dir = os.path.join(frontend_dir, "css")
js_dir = os.path.join(frontend_dir, "js")

if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")

# O'qituvchi yuklagan audio va boshqa fayllar (uploads/audio/...)
uploads_dir = os.path.join(base_dir, "uploads")
os.makedirs(os.path.join(uploads_dir, "audio"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "full_python_web_server",
        "endpoints_count": 51,
        "rules_active": ["1_ai_lock", "2_rationale_transparent", "3_teacher_sovereignty", "4_student_reflection"]
    }

# 3. Tarmoq va Wi-Fi ma'lumotlari API
@app.get("/api/network-info")
def get_network_info():
    import socket
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith('127.') and not primary.startswith('169.254.'):
            ips.append(primary)
    except Exception:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    primary_ip = ips[0] if ips else "127.0.0.1"
    return {
        "primary_ip": primary_ip,
        "all_ips": ips,
        "port": 8010,
        "lan_url": f"http://{primary_ip}:8010",
        "local_url": "http://127.0.0.1:8010",
        "qr_url": "/wifi_qr.png"
    }

# 4. Saytning asosiy yuzi (Python server orqali to'liq yetkaziladi)
@app.get("/")
def serve_home():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TILORA veb-platformasi ishlab turibdi", "docs": "/docs"}

# Noma'lum /api yo'llari: har qanday metod uchun aniq 404 (SPA fallback 405 bermasin)
@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def api_not_found(rest: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={
        "detail": f"API endpoint topilmadi: /api/{rest}. Agar kod yangilangan bo'lsa, serverni qayta ishga tushiring (start.bat)."
    })

# SPA fallback va statik fayllarni yetkazish
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    # Agar API marshrut bo'lmasa, index.html ga yo'naltirish
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
        return {"error": "Not Found"}
    
    clean_path = full_path
    if clean_path.startswith("frontend/"):
        clean_path = clean_path[len("frontend/"):]
    target_file = os.path.join(frontend_dir, clean_path)
    if os.path.isfile(target_file):
        return FileResponse(target_file)
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TILORA SPA"}
