"""5-bosqich: AI talaba ishini baholaydi (o'z bahosi avtomatik to'ldirilmaydi)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.lesson import LESSON_CACHE
from app.services.ai_service import ai_service

client = TestClient(app)
TEXT = ("Assessing students' writing requires clear criteria. Furthermore, teachers should consider "
        "content, accuracy, vocabulary and coherence. " * 6)


def test_ai_evaluate_ai_bilan(monkeypatch):
    async def fake(messages, temperature=0.6, max_tokens=1500, timeout=None):
        return {"success": True, "model": "fake-model", "content": "```json\n" + json.dumps({
            "rubric": {"content": {"score": 4, "reason": "Vazifa bajarilgan."},
                       "grammar": {"score": 3, "reason": "Artikl xatolari."},
                       "lexis": {"score": 5, "reason": "Boy leksika."},
                       "coherence": {"score": 4, "reason": "Bog'lovchilar bor."}},
            "total_score": 80, "cefr_estimate": "B2",
            "strengths": ["Aniq tuzilma"], "improvements": ["Artikllar"],
            "overall_comment": "Yaxshi ish."}) + "\n```"}
    monkeypatch.setattr(ai_service, "call_chat", fake)
    LESSON_CACHE["self_rating"] = None

    r = client.post("/api/lesson/5/ai-evaluate", json={"content_text": TEXT})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ai_powered"] is True and d["total_score"] == 80
    assert d["rubric"]["grammar"] == {"score": 3, "reason": "Artikl xatolari."}
    assert d["strengths"] == ["Aniq tuzilma"] and d["cefr_estimate"] == "B2"
    # AI bahosi "haqiqiy natija" sifatida saqlanadi, lekin o'z bahosiga tegmaydi
    assert LESSON_CACHE["actual_rating"] == {"content": 4, "grammar": 3, "lexis": 5, "coherence": 4}
    assert LESSON_CACHE["self_rating"] is None
    # 4-qoida hamon kuchda: o'z bahosisiz haqiqiy natija 409
    assert client.get("/api/lesson/5/actual-rating").status_code == 409
    client.post("/api/lesson/5/self-rating", json={"ratings": {"content": 5, "grammar": 5, "lexis": 5, "coherence": 5}})
    ar = client.get("/api/lesson/5/actual-rating").json()
    assert ar["ai_evaluation"]["total_score"] == 80 and ar["self_rating"]["grammar"] == 5


def test_ai_evaluate_ai_ochiq_bolsa_lokal_baho(monkeypatch):
    async def fake(messages, temperature=0.6, max_tokens=1500, timeout=None):
        return {"success": False, "error_message": "credit insufficient balance", "quota_exhausted": True}
    monkeypatch.setattr(ai_service, "call_chat", fake)
    r = client.post("/api/lesson/5/ai-evaluate", json={"content_text": TEXT})
    assert r.status_code == 200
    d = r.json()
    assert d["ai_powered"] is False
    assert set(d["rubric"]) == {"content", "grammar", "lexis", "coherence"}
    assert all(1 <= v["score"] <= 5 and v["reason"] for v in d["rubric"].values())
    assert 0 <= d["total_score"] <= 100 and "balans" in d["ai_error"]


def test_ai_evaluate_matnsiz_400():
    LESSON_CACHE["production_text"] = ""
    assert client.post("/api/lesson/5/ai-evaluate", json={"content_text": "   "}).status_code == 400
