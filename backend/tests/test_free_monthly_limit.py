"""
Tekin (free) tarif limiti: test + slayd (AI so'rovlari) uchun UMUMIY oylik limit — oyiga 3 ta.
O'tgan oydagi materiallar hisobga olinmaydi; PRO uchun cheksiz.
Vaqtinchalik SQLite bazasida ishlaydi; AI chaqiruvlari monkeypatch bilan almashtiriladi.
"""
import os
import tempfile
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core.security import create_access_token
from app.models.entities import User, TeacherSubject, SyllabusTopic, TeacherMaterial
from app.services.ai_service import ai_service
from app.api.teacher import FREE_MONTHLY_AI_LIMIT, check_material_limit, monthly_material_counts


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_limit_")
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
    free_t = User(id="t-free", email="free@test.uz", password_hash="x", full_name="Tekin ustoz", role="teacher", is_approved=True, subscription_tier="free")
    pro_t = User(id="t-pro", email="pro@test.uz", password_hash="x", full_name="PRO ustoz", role="teacher", is_approved=True, subscription_tier="pro")
    db.add_all([
        free_t, pro_t,
        TeacherSubject(id="sub-f", teacher_id="t-free", name="Fan F", code="F", group_name="302-guruh"),
        TeacherSubject(id="sub-p", teacher_id="t-pro", name="Fan P", code="P", group_name="302-guruh"),
        SyllabusTopic(id="tp-f", subject_id="sub-f", week_number=1, title="Mavzu", hours=2),
        SyllabusTopic(id="tp-p", subject_id="sub-p", week_number=1, title="Mavzu", hours=2),
        # O'tgan oyda yaratilgan 3 ta material — joriy oy limitiga kirmasligi kerak
        *[TeacherMaterial(id=f"old-{i}", teacher_id="t-free", subject_id="sub-f", topic_title="Eski", material_type="test",
                          title="Eski test", content_json={}, created_at=datetime.utcnow().replace(day=1) - timedelta(days=5))
          for i in range(3)],
    ])
    db.commit()
    db.close()

    async def fake_test(**kw):
        return {"title": "T", "questions": [{"id": "q_1", "question": "?", "options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "a"}]}

    async def fake_pres(**kw):
        return {"title": "P", "slides": [{"slide_number": 1, "title": "S", "content": ["x"]}]}

    monkeypatch.setattr(ai_service, "generate_topic_test", fake_test)
    monkeypatch.setattr(ai_service, "generate_topic_presentation", fake_pres, raising=False)

    client = TestClient(app)
    h = lambda uid, tier: {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': 'teacher', 'subscription_tier': tier})}"}
    yield client, S, h("t-free", "free"), h("t-pro", "pro")

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_otgan_oy_materiallari_hisobga_olinmaydi(env):
    client, S, free_h, _ = env
    db = S()
    m = monthly_material_counts(db, "t-free")
    assert m["ai_total"] == 0 and m["remaining"] == FREE_MONTHLY_AI_LIMIT
    ok, msg = check_material_limit(db, "t-free", "test", {"subscription_tier": "free"})
    assert ok and f"{FREE_MONTHLY_AI_LIMIT}/{FREE_MONTHLY_AI_LIMIT}" in msg
    db.close()

    r = client.get("/api/teacher/materials/stats", headers=free_h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["is_pro"] is False
    assert d["limits"]["test"] == FREE_MONTHLY_AI_LIMIT and d["limits"]["presentation"] == FREE_MONTHLY_AI_LIMIT
    assert d["monthly"]["ai_total"] == 0 and d["monthly"]["limit"] == FREE_MONTHLY_AI_LIMIT
    assert d["counts"]["test"] == 3  # umumiy son (o'tgan oy bilan)


def test_free_oylik_umumiy_limit_3(env):
    client, S, free_h, _ = env
    body = {"subject_id": "sub-f", "topic_id": "tp-f", "topic_title": "Mavzu", "material_type": "test", "num_questions": 1}

    # 1-2: test, 3: slayd — umumiy 3 ta
    for i in range(FREE_MONTHLY_AI_LIMIT):
        body["material_type"] = "presentation" if i == FREE_MONTHLY_AI_LIMIT - 1 else "test"
        r = client.post("/api/teacher/generate-material", json=body, headers=free_h)
        assert r.status_code == 200, r.text

    r = client.get("/api/teacher/materials/stats", headers=free_h)
    d = r.json()
    assert d["monthly"]["ai_total"] == FREE_MONTHLY_AI_LIMIT and d["monthly"]["remaining"] == 0
    assert d["remaining"]["test"] == 0 and d["remaining"]["presentation"] == 0

    # 4-chi so'rov (test ham, slayd ham) — 403
    for mt in ("test", "presentation"):
        body["material_type"] = mt
        r = client.post("/api/teacher/generate-material", json=body, headers=free_h)
        assert r.status_code == 403, r.text
        assert "oylik limit" in r.json()["detail"].lower()

    # Dars rejasi limitga kirmaydi
    body["material_type"] = "lesson_plan"
    db = S()
    ok, _ = check_material_limit(db, "t-free", "lesson_plan", {"subscription_tier": "free"})
    db.close()
    assert ok


def test_pro_cheksiz(env):
    client, S, _, pro_h = env
    body = {"subject_id": "sub-p", "topic_id": "tp-p", "topic_title": "Mavzu", "material_type": "test", "num_questions": 1}
    for _ in range(FREE_MONTHLY_AI_LIMIT + 2):
        r = client.post("/api/teacher/generate-material", json=body, headers=pro_h)
        assert r.status_code == 200, r.text
    d = client.get("/api/teacher/materials/stats", headers=pro_h).json()
    assert d["is_pro"] is True and d["limits"]["test"] is None and d["remaining"]["test"] is None
