"""Matn sifati: ma'nosiz harflar, tushunarsiz so'z/gaplar baholashda hisobga olinadi."""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.text_quality import analyze_text_quality, classify_token, apply_quality_cap
from app.services.scoring import score_writing_production
from app.services.feedback import analyze_production_heuristics
from app.services.ai_service import ai_service

client = TestClient(app)

CLEAN = ("Assessing students' writing requires clear and transparent criteria. Furthermore, teachers should consider "
         "content, grammatical accuracy, lexical resource and coherence when they evaluate essays. A well-designed rubric "
         "improves reliability and gives learners formative feedback. In conclusion, metacognitive reflection helps "
         "students improve their own writing. ") * 2
GIBBERISH = ("Assessing writing asdkjh qwerty needs criteria. Xkjrpt zzzzq lkjhgf mmmnbv. The teacher should hhhhhh use "
             "rubric. Blorpix vantrellu was fine. test test test rubric. Kjhgf poiuy trewq lkjhg mnbvc. ") * 2


def test_token_tasnifi():
    assert classify_token("metacognitive")[0] == "valid"
    assert classify_token("learners")[0] == "valid"
    assert classify_token("strengths")[0] == "valid"
    assert classify_token("Tashkent")[0] == "valid"
    assert classify_token("qwerty")[0] == "nonsense"
    assert classify_token("xkjrpt")[0] == "nonsense"
    assert classify_token("hhhhhh")[0] == "nonsense"
    assert classify_token("asdkjh")[0] == "nonsense"
    assert classify_token("bo'lgan")[0] == "unknown"


def test_toza_matn_jarimasiz_manosiz_matn_jarimali():
    q = analyze_text_quality(CLEAN)
    assert q["level"] == "ok" and q["nonsense_count"] == 0 and q["penalty"]["grammar"] == 0

    q = analyze_text_quality(GIBBERISH)
    assert q["level"] in ("high", "severe")
    assert q["nonsense_count"] >= 8 and q["gibberish_ratio"] >= 0.25
    toks = {t["token"].lower() for t in q["suspicious_tokens"]}
    assert {"asdkjh", "qwerty", "hhhhhh", "test"} <= toks
    assert len(q["nonsense_sentences"]) >= 2
    assert all(v <= 3 for v in q["max_scores"].values())

    # Ball: toza matn yuqori, ma'nosiz matn past
    good = score_writing_production(CLEAN * 2, 0)  # ~170 so'z: hajm talabga mos
    bad = score_writing_production(GIBBERISH, 0)
    assert good["total_score"] >= 80
    assert bad["total_score"] <= 55
    assert bad["rubric"]["lexis"] <= 3 and bad["valid_word_count"] < bad["word_count"]


def test_tahlil_izohlarida_manosiz_sozlar_korsatiladi():
    fb = analyze_production_heuristics(GIBBERISH)
    ids = [i["id"] for i in fb["feedback_items"]]
    assert ids[0] == "fb_q_tokens" and any(i.startswith("fb_q_sent") for i in ids)
    item = fb["feedback_items"][0]
    assert "asdkjh" in item["matched_text"] and "tushunarsiz" in item["title"]
    assert fb["score_data"]["text_quality"]["level"] in ("high", "severe")


def test_ai_yuqori_ball_bersa_ham_cheklanadi(monkeypatch):
    async def lenient_ai(messages, temperature=0.6, max_tokens=1500, timeout=None):
        # prompt ichida lokal topilmalar AI'ga uzatilganini tekshiramiz
        assert "LOKAL TEKSHIRUV NATIJASI" in messages[-1]["content"] and "asdkjh" in messages[-1]["content"]
        return {"success": True, "model": "fake", "content": json.dumps({
            "rubric": {"content": {"score": 5, "reason": "a"}, "grammar": {"score": 5, "reason": "b"},
                       "lexis": {"score": 5, "reason": "c"}, "coherence": {"score": 5, "reason": "d"}},
            "total_score": 100, "cefr_estimate": "C1", "strengths": [], "improvements": [], "overall_comment": "ok"})}
    monkeypatch.setattr(ai_service, "call_chat", lenient_ai)
    r = client.post("/api/lesson/5/ai-evaluate", json={"content_text": GIBBERISH})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ai_powered"] is True
    assert all(v["score"] <= 3 for v in d["rubric"].values())
    assert d["total_score"] <= 60
    assert "Matn sifati" in d["rubric"]["lexis"]["reason"]
    assert d["text_quality"]["nonsense_count"] >= 8


def test_text_quality_endpoint_ai_ishlatmaydi():
    r = client.post("/api/lesson/5/text-quality", json={"content_text": "hello asdkjh world qwerty"})
    assert r.status_code == 200
    d = r.json()
    assert d["ai_used"] is False and d["nonsense_count"] == 2
    assert apply_quality_cap({"content": 5, "grammar": 5, "lexis": 5, "coherence": 5}, d)["lexis"] <= 4
