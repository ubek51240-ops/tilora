"""
Mustaqil topshiriq oqimi: o'qituvchi materialni bir nechta fanga biriktiradi,
talaba faqat o'z guruhi fanlarini ko'radi, test javob kaliti sizib chiqmaydi,
natijalar (test, yozma ish, ko'rish) bazaga yoziladi va o'qituvchi ularni ko'radi.
Vaqtinchalik SQLite bazasida ishlaydi; AI chaqiruvlari monkeypatch bilan almashtiriladi.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core.security import create_access_token
from app.models.entities import User, Group, TeacherSubject, TeacherMaterial
from app.services import materials as matsvc


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_assign_")
    engine = create_engine(f"sqlite:///{os.path.join(tmp, 't.db')}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    S = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = S()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = S()
    t1 = User(id="t-1", email="t1@test.uz", password_hash="x", full_name="Ustoz 1", role="teacher", is_approved=True)
    t2 = User(id="t-2", email="t2@test.uz", password_hash="x", full_name="Ustoz 2", role="teacher", is_approved=True)
    g302 = Group(id="g-302", name="302-guruh (Tajriba)")
    g304 = Group(id="g-304", name="304-guruh (Nazorat)")
    s302 = User(id="s-302", email="s302@test.uz", password_hash="x", full_name="Talaba 302", role="student", group_id="g-302", is_approved=True)
    s304 = User(id="s-304", email="s304@test.uz", password_hash="x", full_name="Talaba 304", role="student", group_id="g-304", is_approved=True)
    subA = TeacherSubject(id="sub-a", teacher_id="t-1", name="Ingliz tili A", code="ENG-A", group_name="302-guruh")
    subB = TeacherSubject(id="sub-b", teacher_id="t-1", name="Ingliz tili B", code="ENG-B", group_name="304-guruh")
    subC = TeacherSubject(id="sub-c", teacher_id="t-2", name="Boshqa o'qituvchi fani", code="X", group_name="302-guruh")
    db.add_all([t1, t2, g302, g304, s302, s304, subA, subB, subC])
    db.commit()
    test_mat = TeacherMaterial(
        id="m-test", teacher_id="t-1", subject_id="sub-a", topic_title="Modal verbs", material_type="test",
        title="Modal verbs testi", content_json={"questions": [
            {"id": "q_1", "question": "Pick", "options": ["a", "b", "c", "d"], "correct_index": 2, "explanation": "c is right"},
            {"id": "q_2", "question": "Pick2", "options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "a"},
        ]}, content_text="Modal verbs testi")
    writing = TeacherMaterial(
        id="m-writing", teacher_id="t-1", subject_id="sub-a", topic_title="Yozma nutq", material_type="writing",
        title="Yozma topshiriq", content_json=matsvc.writing_template("Yozma nutq", "Ingliz tili A", "B2", 30, 80), content_text="w")
    pres = TeacherMaterial(
        id="m-pres", teacher_id="t-1", subject_id="sub-b", topic_title="Slides", material_type="presentation",
        title="Slaydlar", content_json={"slides": [{"slide_number": 1, "title": "x", "bullets": []}]}, content_text="p")
    db.add_all([test_mat, writing, pres])
    db.commit()
    db.close()

    client = TestClient(app)
    h = lambda uid, role, gid=None: {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': role, 'group_id': gid})}"}
    yield client, h("t-1", "teacher"), h("t-2", "teacher"), h("s-302", "student", "g-302"), h("s-304", "student", "g-304")

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_talaba_faqat_oz_guruhi_fanlarini_koradi(env):
    client, t1, t2, s302, s304 = env
    r = client.get("/api/student/subjects", headers=s302)
    ids = {s["id"] for s in r.json()["subjects"]}
    assert ids == {"sub-a", "sub-c"} and r.json()["scoped"] is True  # 302 guruhga mos fanlar (ikki o'qituvchi)
    r = client.get("/api/student/subjects", headers=s304)
    assert {s["id"] for s in r.json()["subjects"]} == {"sub-b"}
    # Fan kartasida tur bo'yicha sonlar bor
    a = next(s for s in client.get("/api/student/subjects", headers=s302).json()["subjects"] if s["id"] == "sub-a")
    assert a["counts"]["test"] == 1 and a["counts"]["writing"] == 1 and a["done_count"] == 0

    # Materiallar ham doira bo'yicha: 304 talabasi A fanidagi testni ko'rmaydi
    r = client.get("/api/student/materials", headers=s304)
    assert {m["id"] for m in r.json()["materials"]} == {"m-pres"}
    # Mehmon (tokensiz) hamma narsani ko'radi (eski xatti-harakat saqlanadi)
    r = client.get("/api/student/materials")
    assert len(r.json()["materials"]) == 3


def test_javob_kaliti_talabaga_sizmaydi_va_natija_saqlanadi(env):
    client, t1, t2, s302, s304 = env
    r = client.get("/api/student/materials?subject_id=sub-a&material_type=test", headers=s302)
    q = r.json()["materials"][0]["content"]["questions"][0]
    assert "correct_index" not in q and "explanation" not in q and q["options"]
    q = client.get("/api/student/materials/m-test", headers=s302).json()["content_json"]["questions"][0]
    assert "correct_index" not in q

    r = client.post("/api/student/materials/m-test/submit-test", headers=s302, json={"answers": {"q_1": 2, "q_2": 1}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["correct_answers"] == 1 and d["score_percentage"] == 50 and d["saved"] is True
    assert d["reviews"][0]["correct_index"] == 2  # tekshiruvdan keyin kalit ko'rsatiladi
    # Ikkinchi urinish yaxshiroq
    client.post("/api/student/materials/m-test/submit-test", headers=s302, json={"answers": {"q_1": 2, "q_2": 0}})

    # Talaba ro'yxatida eng yaxshi natija va urinishlar soni
    m = next(x for x in client.get("/api/student/materials?subject_id=sub-a", headers=s302).json()["materials"] if x["id"] == "m-test")
    assert m["attempt"]["attempts"] == 2 and m["attempt"]["best_score"] == 100 and m["attempt"]["passed"] is True
    a = next(s for s in client.get("/api/student/subjects", headers=s302).json()["subjects"] if s["id"] == "sub-a")
    assert a["done_count"] == 1 and a["progress_percent"] == 50

    # Mehmon uchun saqlanmaydi
    r = client.post("/api/student/materials/m-test/submit-test", json={"answers": {"q_1": 2}})
    assert r.status_code == 200 and r.json()["saved"] is False

    # O'qituvchi natijalarni ko'radi (har talaba uchun eng yaxshi urinish)
    r = client.get("/api/teacher/materials/m-test/results", headers=t1)
    assert r.status_code == 200
    d = r.json()
    assert d["summary"]["students"] == 1 and d["summary"]["attempts"] == 2 and d["summary"]["average_score"] == 100
    row = d["results"][0]
    assert row["student_name"] == "Talaba 302" and row["score"] == 100 and row["attempts"] == 2
    det = client.get(f"/api/teacher/materials/m-test/results/{row['id']}", headers=t1).json()
    assert det["answers"] == {"q_1": 2, "q_2": 0}
    # Boshqa o'qituvchi ko'ra olmaydi
    assert client.get("/api/teacher/materials/m-test/results", headers=t2).status_code == 404
    # Arxivda bajargan talabalar soni
    arch = next(x for x in client.get("/api/teacher/materials", headers=t1).json()["materials"] if x["id"] == "m-test")
    assert arch["students_done"] == 1


def test_yozma_topshiriq_rubrika_bilan_baholanadi(env, monkeypatch):
    client, t1, t2, s302, s304 = env
    from app.services import ai_service as ai_mod

    async def fake_rubric(self, text, topic="", task_prompt=""):
        return {"ai_powered": True, "model": "fake", "total_score": 80, "cefr_estimate": "B2",
                "rubric": {k: {"score": 4, "reason": "ok"} for k in ("content", "grammar", "lexis", "coherence")},
                "strengths": ["clear"], "improvements": ["more linkers"], "overall_comment": "Good."}
    monkeypatch.setattr(ai_mod.AIService, "evaluate_writing_rubric", fake_rubric)

    # Juda qisqa matn rad etiladi
    r = client.post("/api/student/materials/m-writing/submit-writing", headers=s302, json={"text": "Too short."})
    assert r.status_code == 400

    text = " ".join(["word"] * 40)
    r = client.post("/api/student/materials/m-writing/submit-writing", headers=s302,
                    json={"text": text, "self_rating": {"content": 4, "grammar": 3, "lexis": 4, "coherence": 4}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["score_percentage"] == 80 and d["passed"] is True and d["saved"] is True
    assert d["word_count"] == 40 and d["rubric"]["grammar"]["score"] == 4 and d["ai_generated"] is True
    assert d["length_note"] is None

    # O'qituvchi matn va rubrikani ko'radi
    res = client.get("/api/teacher/materials/m-writing/results", headers=t1).json()
    att = client.get(f"/api/teacher/materials/m-writing/results/{res['results'][0]['id']}", headers=t1).json()
    assert att["answers"]["text"] == text and att["result"]["rubric"]["content"]["score"] == 4

    # Test turidagi materialga yozma ish topshirib bo'lmaydi
    assert client.post("/api/student/materials/m-test/submit-writing", headers=s302, json={"text": text}).status_code == 404


def test_korildi_belgisi_va_progress(env):
    client, t1, t2, s302, s304 = env
    r = client.post("/api/student/materials/m-pres/mark-viewed", headers=s304)
    assert r.status_code == 200 and r.json()["saved"] is True
    client.post("/api/student/materials/m-pres/mark-viewed", headers=s304)  # takror yozilmaydi
    res = client.get("/api/teacher/materials/m-pres/results", headers=t1).json()
    assert res["summary"]["attempts"] == 1 and res["results"][0]["status"] == "viewed"
    p = client.get("/api/student/materials-progress", headers=s304).json()
    assert p["total"] == 1 and p["done"] == 1 and p["by_type"]["presentation"] == {"total": 1, "done": 1}


def test_oqituvchi_materialni_bir_nechta_fanga_biriktiradi(env, monkeypatch):
    client, t1, t2, s302, s304 = env
    # Tayyor materialni boshqa fanga biriktirish
    r = client.post("/api/teacher/materials/m-test/assign", headers=t1, json={"subject_ids": ["sub-b", "sub-a"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["created"]) == 1 and d["created"][0]["subject_id"] == "sub-b" and d["skipped"] == ["sub-a"]
    # Takror biriktirilmaydi
    d = client.post("/api/teacher/materials/m-test/assign", headers=t1, json={"subject_ids": ["sub-b"]}).json()
    assert d["created"] == [] and d["skipped"] == ["sub-b"]
    # Boshqa o'qituvchining faniga mumkin emas
    assert client.post("/api/teacher/materials/m-test/assign", headers=t1, json={"subject_ids": ["sub-c"]}).status_code == 404
    # 304 talabasi endi nusxani ko'radi va javob kaliti yo'q
    mats = client.get("/api/student/materials?subject_id=sub-b&material_type=test", headers=s304).json()["materials"]
    assert len(mats) == 1 and mats[0]["title"] == "Modal verbs testi" and "correct_index" not in mats[0]["content"]["questions"][0]

    # Generatorda bir vaqtning o'zida bir nechta fanga (AI chaqiruvi shablon bilan almashtiriladi)
    async def fake_writing(ai, topic_title, subject_name, **kw):
        return matsvc.writing_template(topic_title, subject_name, kw.get("cefr", "B2"), kw.get("min_words", 150), kw.get("max_words", 200))
    monkeypatch.setattr(matsvc, "generate_writing_material", fake_writing)
    r = client.post("/api/teacher/generate-material", headers=t1, json={
        "subject_id": "sub-a", "subject_ids": ["sub-b"], "topic_title": "Essay planning",
        "material_type": "writing", "difficulty": "B2", "min_words": 120, "max_words": 160})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["assigned_subjects"] == ["Ingliz tili A", "Ingliz tili B"] and len(d["copies"]) == 1
    assert d["data"]["min_words"] == 120 and len(d["data"]["criteria"]) == 4
    for hdr, sid in ((s302, "sub-a"), (s304, "sub-b")):
        w = client.get(f"/api/student/materials?subject_id={sid}&material_type=writing", headers=hdr).json()["materials"]
        assert any(m["topic_title"] == "Essay planning" for m in w)
    # Boshqa o'qituvchi faniga generatsiya qilib bo'lmaydi
    r = client.post("/api/teacher/generate-material", headers=t1, json={"subject_id": "sub-c", "topic_title": "x", "material_type": "writing"})
    assert r.status_code == 404
