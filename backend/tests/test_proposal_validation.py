"""
Yangi taklif yuborishda validatsiya: qisqa mavzu/matn yoki tanlanmagan qabul qiluvchi uchun
422 (pydantic ro'yxati, frontendda "[object Object]") emas, 400 va tushunarli o'zbekcha xabar qaytadi.
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
from app.models.entities import User


@pytest.fixture()
def env():
    tmp = tempfile.mkdtemp(prefix="tilora_prop_")
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
    db.add_all([
        User(id="t-1", email="t1@test.uz", password_hash="x", full_name="Ustoz", role="teacher", is_approved=True),
        User(id="s-1", email="s1@test.uz", password_hash="x", full_name="Talaba", role="student", is_approved=True),
    ])
    db.commit()
    db.close()
    client = TestClient(app)
    h = {"Authorization": f"Bearer {create_access_token({'id': 's-1', 'role': 'student', 'subscription_tier': 'free'})}"}
    yield client, h
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_qisqa_maydonlar_400_va_ozbekcha_xabar(env):
    client, h = env
    base = {"receiver_id": "t-1", "receiver_role": "teacher", "proposal_type": "general"}

    r = client.post("/api/proposals", json={**base, "title": "ab", "proposal_text": "Yetarli uzun matn"}, headers=h)
    assert r.status_code == 400 and "mavzusi kamida 3" in r.json()["detail"]

    r = client.post("/api/proposals", json={**base, "title": "Mavzu", "proposal_text": "qis"}, headers=h)
    assert r.status_code == 400 and "matni kamida 5" in r.json()["detail"]

    r = client.post("/api/proposals", json={**base, "receiver_id": "", "title": "Mavzu", "proposal_text": "Yetarli uzun matn"}, headers=h)
    assert r.status_code == 400 and "Qabul qiluvchi" in r.json()["detail"]

    # Maydon umuman yuborilmasa ham 422 emas, 400 + matn
    r = client.post("/api/proposals", json={"receiver_id": "t-1"}, headers=h)
    assert r.status_code == 400 and isinstance(r.json()["detail"], str)


def test_togri_taklif_yuboriladi_va_notogri_tur_generalga_tushadi(env):
    client, h = env
    body = {"receiver_id": "t-1", "receiver_role": "teacher", "proposal_type": "nomalum_tur",
            "title": "  3-hafta uchun keys  ", "proposal_text": "Amaliy keys qo'shishni taklif qilaman.", "basis": ""}
    r = client.post("/api/proposals", json=body, headers=h)
    assert r.status_code == 200, r.text
    p = r.json()["proposal"]
    assert p["proposal_type"] == "general"
    assert p["title"] == "3-hafta uchun keys"
