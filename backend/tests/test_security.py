"""
Xavfsizlik regressiya testlari: parol xeshlash, token, path traversal, brute-force chegarasi,
rolga asoslangan kirish, kontent API.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core import security
from app.core.security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token
from app.models.entities import User, Institution

client = TestClient(app)


# ---------------- Parol xeshlash ----------------

def test_parol_xeshi_foydalanuvchiga_xos_tuz_bilan():
    h1 = hash_password("Talaba2026")
    h2 = hash_password("Talaba2026")
    assert h1 != h2, "bir xil parol har safar boshqa xesh berishi kerak (tasodifiy tuz)"
    assert h1.startswith("pbkdf2_sha256$600000$")
    assert verify_password("Talaba2026", h1) and verify_password("Talaba2026", h2)
    assert not verify_password("talaba2026", h1)
    assert not needs_rehash(h1)


def test_eski_statik_tuzli_xesh_hali_tekshiriladi_va_yangilanadi():
    import hashlib
    legacy = hashlib.pbkdf2_hmac("sha256", b"OldPass123", b"tilora_salt_2026", 100000).hex()
    assert verify_password("OldPass123", legacy)
    assert needs_rehash(legacy)


# ---------------- JWT ----------------

def test_token_imzo_va_alg_tekshiruvi():
    tok = create_access_token({"id": "u1", "role": "student"})
    payload = decode_access_token(tok)
    assert payload["id"] == "u1" and "exp" in payload and "iat" in payload

    # Imzo buzilgan
    h, p, s = tok.split(".")
    assert decode_access_token(f"{h}.{p}.{s[:-2]}AA") is None

    # alg=none hujumi
    import base64, json
    none_header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    assert decode_access_token(f"{none_header}.{p}.") is None

    # Rolni o'zgartirib qayta imzosiz yuborish
    forged_p = base64.urlsafe_b64encode(json.dumps({"id": "u1", "role": "admin", "exp": 9999999999}).encode()).decode().rstrip("=")
    assert decode_access_token(f"{h}.{forged_p}.{s}") is None


def test_rolsiz_kirish_taqiqlanadi():
    student = {"Authorization": f"Bearer {create_access_token({'id': 'sec_student', 'role': 'student'})}"}
    assert client.get("/api/admin/summary", headers=student).status_code == 403
    assert client.get("/api/admin/summary").status_code == 401
    assert client.get("/api/research/export-docx").status_code == 401
    assert client.get("/api/research/export-docx", headers=student).status_code == 403
    # Jadvallarning o'zi ochiq (ma'lumot manbasi belgisi bilan)
    r = client.get("/api/research/tables")
    assert r.status_code == 200 and r.json()["data_source"] == "dissertation_dataset"


# ---------------- Path traversal va sarlavhalar ----------------

def test_path_traversal_frontend_papkasidan_chiqmaydi():
    for p in ("/..%2F..%2Fbackend%2Fapp%2Fconfig.py", "/../backend/app/config.py", "/frontend/../../.env", "/.env"):
        r = client.get(p)
        assert r.status_code in (200, 404)
        body = r.text
        assert "SECRET_KEY" not in body and "AI_API_KEY" not in body


def test_xavfsizlik_sarlavhalari():
    r = client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "SAMEORIGIN"
    assert "content-security-policy" in {k.lower() for k in r.headers.keys()}
    assert "endpoints_count" not in r.json()


def test_network_info_faqat_lokal():
    # TestClient "testclient" hostidan keladi — lokal hisoblanadi
    assert client.get("/api/network-info").status_code == 200


# ---------------- Login va ro'yxatdan o'tish ----------------

@pytest.fixture()
def tmpdb():
    tmp = tempfile.mkdtemp(prefix="tilora_sec_")
    engine = create_engine(f"sqlite:///{os.path.join(tmp, 't.db')}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    S = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override():
        db = S()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    db = S()
    db.add(Institution(id="inst_buxdu", name="BuxDU", short_name="BuxDU"))
    db.add(User(id="sec-u1", email="sec_user@tilora.uz", password_hash=hash_password("Correct1234"),
                full_name="Sec User", role="student", is_approved=True, is_active=True))
    db.commit()
    db.close()
    yield S
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_login_xabari_foydalanuvchini_oshkor_qilmaydi(tmpdb):
    r1 = client.post("/api/auth/login", json={"email": "nobody_xyz@tilora.uz", "password": "Whatever123"})
    r2 = client.post("/api/auth/login", json={"email": "sec_user@tilora.uz", "password": "WrongPass123"})
    assert r1.status_code == 401 and r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


def test_login_brute_force_chegarasi(tmpdb):
    from app.api import auth as auth_mod
    auth_mod._login_ident_limiter.reset("login:bf_target@tilora.uz")
    codes = []
    for _ in range(auth_mod.settings.LOGIN_MAX_ATTEMPTS + 2):
        codes.append(client.post("/api/auth/login", json={"email": "bf_target@tilora.uz", "password": "x"}).status_code)
    assert 429 in codes
    auth_mod._login_ident_limiter.reset("login:bf_target@tilora.uz")
    auth_mod._login_ip_limiter.reset("login_ip:testclient")


def test_muvaffaqiyatli_login_token_beradi_va_rol_mijozdan_olinmaydi(tmpdb):
    from app.api import auth as auth_mod
    auth_mod._login_ip_limiter.reset("login_ip:testclient")
    r = client.post("/api/auth/login", json={"email": "sec_user@tilora.uz", "password": "Correct1234"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "student"

    # Ro'yxatdan o'tishda role=admin yuborilsa ham talaba bo'ladi
    reg = client.post("/api/auth/register", json={
        "email": "wannabe_admin", "password": "Strong1234", "full_name": "Test Odam", "role": "admin"
    })
    assert reg.status_code == 200, reg.text
    assert reg.json()["user"]["role"] == "student"


def test_zaif_parol_rad_etiladi(tmpdb):
    for pwd in ("123", "12345678", "abcdefgh", "tilora2026!"):
        r = client.post("/api/auth/register", json={"email": f"weak_{len(pwd)}_{pwd[:2]}", "password": pwd, "full_name": "Zaif Parol"})
        assert r.status_code == 400, pwd


def test_login_identifikatori_validatsiyasi(tmpdb):
    r = client.post("/api/auth/register", json={"email": "bad email@@x", "password": "Strong1234", "full_name": "X Y"})
    assert r.status_code == 400


# ---------------- Kontent API ----------------

def test_kontent_api_ochiq_va_toliq():
    o = client.get("/api/content/overview").json()
    assert o["glossary_terms"] >= 40 and o["l1_patterns"] >= 40 and o["diagnostic_questions"] >= 24
    assert o["survey_items"] >= 20 and o["cefr_levels"] == 6 and o["lesson_tasks"] == 4
    assert client.get("/api/content/glossary?q=scaffold").json()["total"] >= 1
    assert client.get("/api/content/cefr-levels").json()["levels"][0]["level"] == "A1"
    assert len(client.get("/api/content/methodology").json()["rules"]) == 4
    assert client.get("/api/content/faq?audience=teacher").json()["total"] >= 4
    # Regex ichki — talabaga chiqmaydi
    pats = client.get("/api/content/l1-patterns").json()["patterns"]
    assert pats and "regex" not in pats[0]


def test_lesson_task_har_konikma_uchun():
    for sk in ("writing", "speaking", "listening", "reading"):
        t = client.get(f"/api/lesson/x/task?skill={sk}").json()
        assert t["skill"] == sk and t["prompt"] and len(t["rubric"]) == 4
