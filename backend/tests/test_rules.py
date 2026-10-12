try:
    import pytest
except ImportError:
    pytest = None
from fastapi.testclient import TestClient

from app.main import app
from app.services.path_builder import generate_learning_path
from app.services.l1 import analyze_l1_interference

client = TestClient(app)

def test_qoida_1_mustaqil_bosqichda_ai_403():
    """
    1-QOIDA: Mustaqil bosqichda AI vositalari bloklanadi (403 AI_LOCKED).
    Topshiriq sharti va lug'at esa ochiq qoladi (200).
    """
    headers = {"X-Lesson-Stage": "independent", "X-AI-Locked": "true"}
    
    # 4 ta bloklanadigan vosita
    res_gen = client.post("/api/ai/generate", json={"prompt": "write essay"}, headers=headers)
    assert res_gen.status_code == 403
    assert res_gen.json()["detail"]["error_code"] == "AI_LOCKED"
    
    res_trans = client.post("/api/ai/translate", json={"prompt": "tarjima qil"}, headers=headers)
    assert res_trans.status_code == 403
    
    res_comp = client.post("/api/ai/complete", json={"prompt": "davomini yoz"}, headers=headers)
    assert res_comp.status_code == 403
    
    res_ans = client.post("/api/ai/answer", json={"prompt": "javob ber"}, headers=headers)
    assert res_ans.status_code == 403
    
    # Ruxsat etilgan vositalar
    res_task = client.get("/api/lesson/les_01/task")
    assert res_task.status_code == 200
    
    res_glossary = client.get("/api/student/glossary")
    assert res_glossary.status_code == 200

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

def test_qoida_3_qaror_oqituvchida():
    """
    3-QOIDA: Tizim takliflari o'qituvchi tasdig'ini kutadi (pending).
    O'qituvchi roli bilan autentifikatsiyadan o'tib tekshiriladi.
    """
    from app.core.security import create_access_token
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
    from app.api.lesson import LESSON_CACHE
    LESSON_CACHE["self_rating"] = None
    
    res = client.get("/api/lesson/les_01/actual-rating")
    assert res.status_code == 409
    assert res.json()["detail"]["error_code"] == "SELF_RATING_REQUIRED"
    
    # O'z bahosi topshirilgandan keyin
    client.post("/api/lesson/les_01/self-rating", json={"ratings": {"grammar": 4, "lexis": 4, "content": 4, "coherence": 4}})
    res_ok = client.get("/api/lesson/les_01/actual-rating")
    assert res_ok.status_code == 200
    assert "actual_rating" in res_ok.json()

def test_qoida_4_ai_natijadan_kelib_chiqib_oz_bahosini_baholash():
    """
    1-qadam: AI natijasidan kelib chiqib o'z bahosini avtomatik shakllantirish tekshiruvi.
    """
    from app.api.lesson import LESSON_CACHE
    LESSON_CACHE["self_rating"] = None
    LESSON_CACHE["actual_rating"] = {"content": 5, "grammar": 4, "lexis": 4, "coherence": 4}
    
    res = client.post("/api/lesson/les_01/ai-self-rate")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ai_evaluated"
    assert data["self_rating"]["content"] == 5
    assert data["self_rating"]["grammar"] == 4
    
    # Endi haqiqiy natija ochiq bo'lishi kerak
    res_actual = client.get("/api/lesson/les_01/actual-rating")
    assert res_actual.status_code == 200
    assert res_actual.json()["self_rating"]["content"] == 5

def test_tashvish_qoidasi_surilishi():
    """
    Metodik qoida: Tashvish > 65 bo'lganda og'zaki nutq 1-slotdan suriladi!
    """
    # Past tashvish (30) -> speaking birinchi
    path_low = generate_learning_path("st_01", {"speaking": "A2", "listening": "B1"}, anxiety_level=30)
    assert path_low[0]["skill"] == "speaking"
    
    # Yuqori tashvish (75) -> listening birinchi, speaking ikkinchi
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
