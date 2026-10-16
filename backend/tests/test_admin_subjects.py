"""
Super admin barcha o'qituvchilarning fanlarini ko'radi va ular uchun material yarata oladi;
o'qituvchi faqat o'z fanlarini ko'radi. Talaba fanlari ro'yxatida egasi (teacher_id) qaytadi —
"Mustaqil topshiriqlar" ekranidagi yaratish tugmalari shu maydonga tayanadi.
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
from app.models.entities import User, TeacherSubject, SyllabusTopic, TeacherMaterial
from app.services.ai_service import ai_service


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_admin_")
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
    adm = User(id="adm-1", email="adm@test.uz", password_hash="x", full_name="Admin", role="admin", is_approved=True, subscription_tier="pro")
    t1 = User(id="t-1", email="t1@test.uz", password_hash="x", full_name="Ustoz 1", role="teacher", is_approved=True)
    t2 = User(id="t-2", email="t2@test.uz", password_hash="x", full_name="Ustoz 2", role="teacher", is_approved=True)
    subA = TeacherSubject(id="sub-a", teacher_id="t-1", name="Ingliz tili A", code="ENG-A", group_name="302-guruh")
    subC = TeacherSubject(id="sub-c", teacher_id="t-2", name="Boshqa o'qituvchi fani", code="X", group_name="302-guruh")
    subAdm = TeacherSubject(id="sub-adm", teacher_id="adm-1", name="Admin fani", code="ADM", group_name="302-guruh")
    db.add_all([adm, t1, t2, subA, subC, subAdm, SyllabusTopic(id="tp-1", subject_id="sub-c", week_number=1, title="Mavzu 1", hours=2)])
    db.commit()
    db.close()

    # AI chaqiruvlari o'rniga tayyor shablon javoblar
    async def fake_test(**kw):
        return {"title": f"{kw['topic_title']} testi", "questions": [{"id": "q_1", "question": "?", "options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "a"}]}

    async def fake_plan(**kw):
        return {"title": f"Reja: {kw['topic_title']}", "stages": []}

    monkeypatch.setattr(ai_service, "generate_topic_test", fake_test)
    monkeypatch.setattr(ai_service, "generate_topic_lesson_plan", fake_plan)

    client = TestClient(app)
    h = lambda uid, role: {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': role, 'subscription_tier': 'pro'})}"}
    yield client, h("adm-1", "admin"), h("t-1", "teacher")

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_admin_barcha_fanlarni_koradi_oqituvchi_faqat_ozinikini(env):
    client, adm, t1 = env
    r = client.get("/api/teacher/subjects", headers=adm)
    assert r.status_code == 200
    subs = {s["id"]: s for s in r.json()["subjects"]}
    assert set(subs) == {"sub-a", "sub-c", "sub-adm"}
    assert subs["sub-adm"]["is_own"] is True
    assert subs["sub-c"]["is_own"] is False and subs["sub-c"]["teacher_name"] == "Ustoz 2"
    assert subs["sub-c"]["teacher_id"] == "t-2"

    r = client.get("/api/teacher/subjects", headers=t1)
    assert {s["id"] for s in r.json()["subjects"]} == {"sub-a"}
    assert r.json()["subjects"][0]["is_own"] is True


def test_admin_boshqa_oqituvchi_faniga_material_yaratadi(env):
    client, adm, t1 = env
    body = {"subject_id": "sub-c", "topic_id": "tp-1", "topic_title": "Mavzu 1", "material_type": "test", "num_questions": 1}
    r = client.post("/api/teacher/generate-material", json=body, headers=adm)
    assert r.status_code == 200, r.text
    assert r.json()["subject_name"] == "Boshqa o'qituvchi fani"

    body["material_type"] = "lesson_plan"
    r = client.post("/api/teacher/generate-material", json=body, headers=adm)
    assert r.status_code == 200, r.text

    # O'qituvchi boshqa o'qituvchining faniga yarata olmaydi
    body["material_type"] = "test"
    r = client.post("/api/teacher/generate-material", json=body, headers=t1)
    assert r.status_code == 404

    # Talaba ekranida material fan bo'yicha ko'rinadi va fanning egasi (teacher_id) qaytadi
    r = client.get("/api/student/materials?subject_id=sub-c")
    assert {m["material_type"] for m in r.json()["materials"]} == {"test", "lesson_plan"}
    r = client.get("/api/student/subjects")
    owners = {s["id"]: s["teacher_id"] for s in r.json()["subjects"]}
    assert owners["sub-c"] == "t-2" and owners["sub-adm"] == "adm-1"
