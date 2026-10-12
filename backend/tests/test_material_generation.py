"""
AI material generatori (aynan N ta savol/slayd, partiyalab, uzilgan JSON, rasmlar)
va o'qituvchi takliflari qarorining bazada saqlanishi.
AI chaqiruvi mock qilinadi — tarmoq kerak emas.
"""
import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core.security import create_access_token
from app.services.ai_service import ai_service
from app.models.entities import User


@pytest.fixture()
def env():
    tmp = tempfile.mkdtemp(prefix="tilora_gen_")
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
    db.add(User(id="t-1", email="u@t.uz", password_hash="x", full_name="Ustoz", role="teacher", is_approved=True, subscription_tier="pro"))
    db.add(User(id="s-1", email="s@t.uz", password_hash="x", full_name="Aziza K.", role="student", is_approved=True))
    db.commit()
    db.close()
    client = TestClient(app)
    h = {"Authorization": f"Bearer {create_access_token({'id': 't-1', 'role': 'teacher', 'subscription_tier': 'pro'})}"}
    r = client.post("/api/teacher/subjects", headers=h, json={"name": "EAP", "code": "EAP-1"})
    subj = r.json()["subject_id"]
    yield client, h, subj
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def _fake_chat(kind, truncate_first=False, fail=False):
    """AI'ni taqlid qiladi: so'ralgan sondagi elementni qaytaradi (offsetni promptdan o'qiydi)."""
    import re
    calls = {"n": 0}

    async def call_chat(messages, temperature=0.6, max_tokens=1500, timeout=None):
        calls["n"] += 1
        if fail:
            return {"success": False, "error_message": "quota"}
        user = messages[-1]["content"]
        m = re.search(r"AYNAN (\d+) TA", user)
        count = int(m.group(1))
        m2 = re.search(r"Bu partiya: (\d+)-", user)
        offset = int(m2.group(1)) - 1 if m2 else 0
        items = []
        for i in range(offset, offset + count):
            if kind == "test":
                items.append({"question": f"Question number {i + 1}?", "options": ["a", "b", "c", "d"],
                              "correct_index": i % 4, "explanation": "because"})
            else:
                items.append({"title": f"Slide {i + 1}", "bullets": ["x", "y"], "speaker_notes": "n",
                              "visual_badge": "B", "image_prompt": f"prompt {i + 1}"})
        raw = json.dumps(items)
        if truncate_first and calls["n"] == 1:
            raw = raw[: len(raw) - 40]  # oxirgi ob'ekt uzilib qoladi
        return {"success": True, "content": "```json\n" + raw + "\n```"}

    return call_chat, calls


def test_aynan_20_ta_savol_partiyalab(env, monkeypatch):
    client, h, subj = env
    fake, calls = _fake_chat("test", truncate_first=True)
    monkeypatch.setattr(ai_service, "call_chat", fake)
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "Thesis statements", "material_type": "test", "num_questions": 20})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["questions_count"] == 20 and len(d["questions"]) == 20
    assert d["requested_count"] == 20 and d["ai_generated"] is True
    assert d["ai_questions_count"] == 20  # uzilgan partiya qayta so'raldi, shablon kerak bo'lmadi
    assert len({q["question"] for q in d["questions"]}) == 20  # takror yo'q
    assert [q["id"] for q in d["questions"]] == [f"q_{i}" for i in range(1, 21)]
    assert calls["n"] >= 3  # 8+8+4 partiya (+ uzilgani uchun qo'shimcha)


def test_ai_ishlamasa_ham_aynan_n_ta(env, monkeypatch):
    client, h, subj = env
    fake, _ = _fake_chat("test", fail=True)
    monkeypatch.setattr(ai_service, "call_chat", fake)
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "Hedging", "material_type": "test", "num_questions": 33})
    d = r.json()["data"]
    assert d["questions_count"] == 33 and d["ai_generated"] is False
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "Hedging", "material_type": "presentation", "num_slides": 23, "image_mode": "photo"})
    d = r.json()["data"]
    assert d["slides_count"] == 23 and all(s["image_url"] for s in d["slides"])


def test_aynan_15_ta_slayd_har_biriga_ai_rasm(env, monkeypatch):
    client, h, subj = env
    fake, calls = _fake_chat("slides")
    monkeypatch.setattr(ai_service, "call_chat", fake)
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "Cohesion", "material_type": "presentation",
        "num_slides": 15, "image_mode": "ai"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["slides_count"] == 15 and d["requested_count"] == 15 and d["image_mode"] == "ai"
    urls = [s["image_url"] for s in d["slides"]]
    assert all(u.startswith("https://image.pollinations.ai/prompt/") for u in urls)
    assert len(set(urls)) == 15  # har slaydga alohida rasm
    assert all(s["image_fallback_url"].startswith("https://images.unsplash.com/") for s in d["slides"])
    assert [s["slide_number"] for s in d["slides"]] == list(range(1, 16))
    assert calls["n"] == 3  # 6 + 6 + 3

    # Rasmsiz rejim
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "Cohesion", "material_type": "presentation", "num_slides": 3, "image_mode": "none"})
    assert all(s["image_url"] == "" for s in r.json()["data"]["slides"])


def test_son_chegaralari(env):
    client, h, subj = env
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "X", "material_type": "test", "num_questions": 0})
    assert r.status_code == 422
    r = client.post("/api/teacher/generate-material", headers=h, json={
        "subject_id": subj, "topic_title": "X", "material_type": "presentation", "num_slides": 99})
    assert r.status_code == 422


def test_taklif_qarori_bazada_saqlanadi(env):
    client, h, _ = env
    from app.database import get_db
    from app.models.entities import TeacherProposal
    db = next(app.dependency_overrides[get_db]())
    for i in range(3):
        db.add(TeacherProposal(
            teacher_id="t-1",
            student_id="s-1",
            proposal_type="scaffold_change",
            proposed_change={"student_name": "Aziza K.", "text": f"Taklif {i+1}"},
            basis="Asos",
            status="pending"
        ))
    db.commit()

    first = client.get("/api/teacher/proposals", headers=h).json()
    assert first["pending_count"] == 3
    pid = first["proposals"][0]["id"]
    assert first["proposals"][0]["student_name"] == "Aziza K."  # real talaba nomi

    r = client.post(f"/api/teacher/proposal/{pid}/approve", headers=h, json={"status": "approved"})
    assert r.status_code == 200 and r.json()["status"] == "approved"

    # "Sahifa yangilandi": qayta so'rov — qaror saqlanib qolgan
    again = client.get("/api/teacher/proposals", headers=h).json()
    assert again["pending_count"] == 2
    p = next(x for x in again["proposals"] if x["id"] == pid)
    assert p["status"] == "approved" and p["decided_at"]

    pid2 = next(x["id"] for x in again["proposals"] if x["status"] == "pending")
    client.post(f"/api/teacher/proposal/{pid2}/modify", headers=h, json={"status": "modified", "teacher_comment": "Muddat 30 daqiqa"})
    p2 = next(x for x in client.get("/api/teacher/proposals", headers=h).json()["proposals"] if x["id"] == pid2)
    assert p2["status"] == "modified" and p2["teacher_comment"] == "Muddat 30 daqiqa"

    # Qayta ochish
    client.post(f"/api/teacher/proposal/{pid}/reopen", headers=h)
    assert client.get("/api/teacher/proposals", headers=h).json()["pending_count"] == 2

    # Boshqa o'qituvchi bu taklifni ko'rmaydi va o'zgartira olmaydi
    other = {"Authorization": f"Bearer {create_access_token({'id': 't-9', 'role': 'teacher'})}"}
    assert client.post(f"/api/teacher/proposal/{pid}/reject", headers=other).status_code == 404
