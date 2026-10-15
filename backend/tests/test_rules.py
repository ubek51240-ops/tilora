try:
    import pytest
except ImportError:
    pytest = None
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.services.path_builder import generate_learning_path
from app.services.l1 import analyze_l1_interference

client = TestClient(app)


def _student_headers(uid="rules_student_1"):
    return {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': 'student'})}"}


def test_qoida_1_mustaqil_bosqichda_ai_403():
    """
    1-QOIDA: Mustaqil bosqichda AI vositalari bloklanadi (403 AI_LOCKED).
    Topshiriq sharti va lug'at esa ochiq qoladi (200).
    """
    h = _student_headers("rules_student_lock")
    # Serverdagi holat: foydalanuvchi mustaqil bosqichga o'tadi
    r = client.post("/api/lesson/les_01/stage/next?target_stage=independent", headers=h)
    assert r.status_code == 200 and r.json()["ai_locked"] is True

    # 4 ta bloklanadigan vosita — mijoz "X-AI-Locked: false" yuborsa ham server holati ustun
    bypass = dict(h, **{"X-Lesson-Stage": "preparation", "X-AI-Locked": "false"})
    for tool in ("generate", "translate", "complete", "answer"):
        res = client.post(f"/api/ai/{tool}", json={"prompt": "write essay"}, headers=bypass)
        assert res.status_code == 403, tool
        assert res.json()["detail"]["error_code"] == "AI_LOCKED"

    # Sarlavha orqali (serverda holat bo'lmagan foydalanuvchi) ham bloklanadi
    h2 = dict(_student_headers("rules_student_hdr"), **{"X-Lesson-Stage": "independent", "X-AI-Locked": "true"})
    assert client.post("/api/ai/generate", json={"prompt": "write essay"}, headers=h2).status_code == 403

    # Ruxsat etilgan vositalar
    res_task = client.get("/api/lesson/les_01/task")
    assert res_task.status_code == 200
    assert "prompt" in res_task.json()

    res_glossary = client.get("/api/student/glossary")
    assert res_glossary.status_code == 200
    assert res_glossary.json()["total"] >= 40


def test_qoida_1_ai_endpointlar_autentifikatsiya_talab_qiladi():
    """AI endpointlar tizimga kirmagan foydalanuvchiga ochiq emas (pullik kalitni suiiste'mol qilish himoyasi)."""
    assert client.post("/api/ai/generate", json={"prompt": "x"}).status_code == 401
    assert client.post("/api/ai/chat", json={"prompt": "x"}).status_code == 401
    assert client.post("/api/ai/analyze", json={"prompt": "x"}).status_code == 401


def test_qoida_2_har_elementda_sabab_bor():
    """
    2-QOIDA: Har bir o'quv yo'li elementi asosli 'rationale' matniga ega.
    """
    path = generate_learning_path("st_01", {"speaking": "A2", "listening": "B1"}, anxiety_level=75)
    assert len(path) == 8
    for item in path:
        assert item["rationale"] is not None
        assert len(item["rationale"].strip()) > 20
        assert "tashvish" in item["rationale"].lower() or "darajangizga" in item["rationale"].lower()
    # Kengaytirilgan mavzular banki: bir mavzu takrorlanmaydi
    titles = [p["topic"] for p in path]
    assert len(titles) == len(set(titles))


def test_qoida_3_qaror_oqituvchida():
    """
    3-QOIDA: Tizim takliflari o'qituvchi tasdig'ini kutadi (pending).
    O'qituvchi roli bilan autentifikatsiyadan o'tib tekshiriladi.
    """
    from app.database import SessionLocal
    from app.models.entities import TeacherProposal
    db = SessionLocal()
    db.add(TeacherProposal(
        teacher_id="teacher_1",
        student_id="teacher_1",
        proposal_type="scaffold_change",
        proposed_change={"student_name": "Aziza K.", "text": "Og'zaki nutq ko'mak"},
        basis="FLCAS 71",
        status="pending"
    ))
    db.commit()
    db.close()

    teacher_token = create_access_token({"sub": "teacher_1", "role": "teacher", "username": "nodira_ustoz"})
    headers = {"Authorization": f"Bearer {teacher_token}"}

    res = client.get("/api/teacher/proposals", headers=headers)
    assert res.status_code == 200
    proposals = res.json()["proposals"]
    assert len(proposals) > 0
    assert proposals[0]["status"] == "pending"


def test_qoida_4_oz_bahosiz_haqiqiy_natija_409():
    """
    4-QOIDA: O'z bahosi qo'yilmaguncha haqiqiy natija ko'rsatilmaydi (409 Conflict).
    """
    h = _student_headers("rules_student_4")
    client.post("/api/lesson/les_01/reset", headers=h)

    res = client.get("/api/lesson/les_01/actual-rating", headers=h)
    assert res.status_code == 409
    assert res.json()["detail"]["error_code"] == "SELF_RATING_REQUIRED"

    # O'z bahosi topshirilgandan keyin
    r = client.post("/api/lesson/les_01/self-rating", json={"ratings": {"grammar": 4, "lexis": 4, "content": 4, "coherence": 4}}, headers=h)
    assert r.status_code == 200
    res_ok = client.get("/api/lesson/les_01/actual-rating", headers=h)
    assert res_ok.status_code == 200
    assert "actual_rating" in res_ok.json()

    # Noto'g'ri baho (0 yoki 6) qabul qilinmaydi
    bad = client.post("/api/lesson/les_01/self-rating", json={"ratings": {"grammar": 9, "lexis": 4, "content": 4, "coherence": 4}}, headers=h)
    assert bad.status_code == 400


def test_qoida_4_holat_foydalanuvchilar_orasida_umumiy_emas():
    """Bir talabaning o'z bahosi boshqa talabaga ta'sir qilmaydi (avval umumiy LESSON_CACHE edi)."""
    a = _student_headers("rules_student_A")
    b = _student_headers("rules_student_B")
    client.post("/api/lesson/les_01/reset", headers=a)
    client.post("/api/lesson/les_01/reset", headers=b)
    client.post("/api/lesson/les_01/self-rating", json={"ratings": {"grammar": 5, "lexis": 5, "content": 5, "coherence": 5}}, headers=a)
    assert client.get("/api/lesson/les_01/actual-rating", headers=a).status_code == 200
    assert client.get("/api/lesson/les_01/actual-rating", headers=b).status_code == 409
    # Tizimga kirmagan foydalanuvchi holatga umuman kira olmaydi
    assert client.get("/api/lesson/les_01/actual-rating").status_code == 401


def test_qoida_4_ai_natijadan_kelib_chiqib_oz_bahosini_baholash():
    """
    Demo rejim: tizim bahosini o'z bahosi sifatida nusxalash (faqat o'z holati uchun).
    """
    h = _student_headers("rules_student_5")
    client.post("/api/lesson/les_01/reset", headers=h)
    text = ("Assessing learner writing requires clear criteria. Furthermore, teachers should consider "
            "content, accuracy, vocabulary and coherence. " * 5)
    client.post("/api/lesson/les_01/production", json={"lesson_id": "les_01", "content_text": text, "word_count": 80}, headers=h)

    res = client.post("/api/lesson/les_01/ai-self-rate", headers=h)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ai_evaluated"
    assert set(data["self_rating"]) == {"content", "grammar", "lexis", "coherence"}

    res_actual = client.get("/api/lesson/les_01/actual-rating", headers=h)
    assert res_actual.status_code == 200
    assert res_actual.json()["self_rating"] == data["self_rating"]


def test_tashvish_qoidasi_surilishi():
    """
    Metodik qoida: Tashvish > 65 bo'lganda og'zaki nutq 1-slotdan suriladi!
    """
    path_low = generate_learning_path("st_01", {"speaking": "A2", "listening": "B1"}, anxiety_level=30)
    assert path_low[0]["skill"] == "speaking"

    path_high = generate_learning_path("st_01", {"speaking": "A2", "listening": "B1"}, anxiety_level=75)
    assert path_high[0]["skill"] == "listening"
    assert path_high[1]["skill"] == "speaking"


def test_l1_interferensiyasi_aniqlanishi():
    """
    L1 ona tili ta'siri regex tahlilchisi to'g'ri ishlashi tekshiruvi.
    """
    sample_text = "She have many problems and we should discuss about this criterias because I am agree."
    issues = analyze_l1_interference(sample_text)
    assert len(issues) >= 4
    shorts = [i["issue_short"] for i in issues]
    assert any("she/he/it have" in s for s in shorts)
    assert any("discuss about" in s for s in shorts)
    assert any("criterias" in s for s in shorts)
    assert any("I am agree" in s for s in shorts)


def test_l1_kengaytirilgan_naqshlar_va_soxta_ijobiylar():
    """Yangi naqshlar aniqlanadi; to'g'ri gaplar xato deb belgilanmaydi."""
    wrong = ("The teacher explained me the rule and said me to repeat. I have 20 years and I am interested about "
             "methodology. She teached us every days and we made our homework. If students will practise, they improve. "
             "This is an actual problem. He don't use rubrics. I am not understand the task.")
    issues = analyze_l1_interference(wrong)
    assert len(issues) >= 9

    correct = ("I am thinking about the lesson. The teacher explained the rule to us and told us to repeat. "
               "I am 20 years old and I am interested in methodology. She taught us every day. "
               "If students practise, they will improve. This is a pressing problem. I very much like it.")
    assert analyze_l1_interference(correct) == []
