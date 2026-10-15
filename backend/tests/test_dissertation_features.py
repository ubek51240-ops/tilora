"""
Dissertatsiya 3.3 / 4.1–4.2 ga mos funksiyalar: metakognitiv sikl (reja -> monitoring -> baholash -> refleksiya),
mashg'ulot yozuvi va dinamika, tabaqalashtirish (A/B/C), o'qituvchi kuzatuv paneli, jonli statistika (t, χ², d, K).
"""
import os
import tempfile
import math

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core.security import create_access_token
from app.models.entities import User, Group, Institution, StudentProfile, Assessment
from app.services import statistics as st
from app.api import lesson as lesson_mod


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_diss_")
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
    # deps._refresh_from_db va lesson reflection SessionLocal ishlatadi — ularni ham vaqtinchalik bazaga yo'naltiramiz
    import app.core.deps as deps
    import app.database as dbmod
    monkeypatch.setattr(dbmod, "SessionLocal", S)

    db = S()
    db.add(Institution(id="inst_buxdu", name="Buxoro davlat universiteti", short_name="BuxDU", direction_code="60230113"))
    db.add(Group(id="g-exp", institution_id="inst_buxdu", name="302-guruh (Tajriba)", experiment_arm="experimental", teacher_id="t-1"))
    db.add(Group(id="g-ctrl", institution_id="inst_buxdu", name="304-guruh (Nazorat)", experiment_arm="control", teacher_id="t-1"))
    db.add(User(id="t-1", email="t1@x.uz", password_hash="x", full_name="Ustoz", role="teacher", is_approved=True))
    db.add(User(id="r-1", email="r1@x.uz", password_hash="x", full_name="Tadqiqotchi", role="researcher", is_approved=True))
    for i in range(6):
        db.add(User(id=f"e{i}", email=f"e{i}@x.uz", password_hash="x", full_name=f"Exp {i}", role="student", group_id="g-exp", institution_id="inst_buxdu", is_approved=True))
        db.add(User(id=f"c{i}", email=f"c{i}@x.uz", password_hash="x", full_name=f"Ctrl {i}", role="student", group_id="g-ctrl", institution_id="inst_buxdu", is_approved=True))
    db.add(StudentProfile(student_id="e0", cefr_listening="B2", cefr_reading="C1", cefr_speaking="B2", cefr_writing="B2", anxiety_level=30, autonomy_readiness=70, load_capacity=70))
    db.add(StudentProfile(student_id="e1", cefr_listening="A2", cefr_reading="B1", cefr_speaking="A2", cefr_writing="A2", anxiety_level=80, autonomy_readiness=30, load_capacity=30))
    db.commit(); db.close()

    client = TestClient(app)
    tok = lambda uid, role, gid=None: {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': role, 'group_id': gid})}"}
    yield client, S, tok
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


# ---------------- Statistika ----------------

def test_statistika_mezonlari():
    pre = [50, 55, 48, 60, 52, 58, 49, 61]
    post = [70, 78, 69, 82, 75, 80, 71, 85]
    t = st.paired_t_test(pre, post)
    assert t["t"] > 10 and t["p"] < 0.001 and t["df"] == 7
    ind = st.independent_t_test(post, [60, 62, 58, 65, 61, 63, 59, 64])
    assert ind["t"] > 4 and ind["p"] < 0.01
    d = st.cohens_d(post, [60, 62, 58, 65, 61, 63, 59, 64])
    assert d > 0.8 and st.effect_label(d).startswith("Katta")
    chi = st.chi_square_2xk([8, 27, 11], [7, 26, 11])
    assert chi["df"] == 2 and chi["p"] > 0.05
    assert st.bespalko_k([80, 82, 78]) == 0.8
    assert st.level_band(90) == "Yuqori" and st.level_band(72) == "O'rta" and st.level_band(60) == "Quyi" and st.level_band(10) == "Boshlang'ich"
    assert st.fmt_p(0.0004) == "< 0.001" and st.fmt_p(0.2).startswith("= 0.2")
    # p-qiymat ma'lum nuqtalar: t=2.0, df=60 -> ~0.05
    assert abs(st.t_two_tailed_p(2.0, 60) - 0.0499) < 0.01
    assert abs(st.chi2_p(5.991, 2) - 0.05) < 0.002


# ---------------- Metakognitiv sikl va yozuv ----------------

def test_metakognitiv_sikl_va_yozuv(env):
    client, S, tok = env
    h = tok("e1", "student", "g-exp")
    lesson_mod.reset_lesson_state("e1")

    r = client.get("/api/lesson/5", headers=h)
    assert r.status_code == 200 and r.json()["variant"] == "C"  # A2 + yuqori tashvish -> tayanchli variant
    assert "Tayanchli" in r.json()["variant_reason"]
    assert r.json()["task"]["scaffold_level"] == "full" and r.json()["task"]["word_count_min"] == 100

    # 1. Rejalashtirish
    assert client.post("/api/lesson/5/plan", json={"goal": "Ikki mezonni misol bilan yozish", "strategy": "avval reja, keyin matn"}, headers=h).status_code == 200
    # 3. Mustaqil bosqich + monitoring
    client.post("/api/lesson/5/stage/next?target_stage=independent", headers=h)
    assert client.post("/api/ai/dialog", json={"messages": [{"role": "user", "content": "hi"}]}, headers=h).status_code == 403  # dialog ham qulflangan
    client.post("/api/lesson/5/monitor", json={"event": "help_request"}, headers=h)
    client.post("/api/lesson/5/monitor", json={"event": "self_check", "seconds": 600}, headers=h)
    text = ("Assessing learner writing requires clear criteria. She have many questions and we discuss about rubrics. "
            "Furthermore, teachers should consider content and accuracy. " * 3)
    r = client.post("/api/lesson/5/production", json={"lesson_id": "5", "content_text": text, "word_count": 60}, headers=h)
    assert r.status_code == 200 and "l1_01" in r.json()["l1_pattern_ids"] and "l1_02" in r.json()["l1_pattern_ids"]
    # 4. Baholash: izohni asoslab qabul/rad etish; qiyosiy usul
    items = r.json()["feedback_items"]
    assert client.post("/api/lesson/5/feedback-decision", json={"item_id": items[0]["id"], "title": items[0]["title"], "accepts": False, "justification": "Bu holda 'discuss about' ataylab ishlatilgan emas, lekin qoida to'g'ri."}, headers=h).status_code == 200
    alt = client.post("/api/lesson/5/alternative", headers=h)
    assert alt.status_code == 200 and alt.json()["alternative"]
    assert client.post("/api/lesson/5/comparison", json={"note": "AI varianti bog'lovchilarni ko'proq ishlatgan, meniki qisqa."}, headers=h).status_code == 200
    # 5. O'z bahosi -> haqiqiy natija -> refleksiya -> yozuv
    client.post("/api/lesson/5/self-rating", json={"ratings": {"content": 5, "grammar": 5, "lexis": 4, "coherence": 4}}, headers=h)
    ar = client.get("/api/lesson/5/actual-rating", headers=h).json()
    assert ar["rating_gap"] is not None
    r = client.post("/api/lesson/5/reflection", json={"gap_explanation": "Grammatikani yuqori baholabman, L1 xatolarini sezmabman.", "next_goal": "discuss + object"}, headers=h)
    assert r.status_code == 200 and r.json()["record_id"]

    hist = client.get("/api/lesson/history", headers=h).json()
    assert hist["total"] == 1
    rec = hist["records"][0]
    assert rec["task_variant"] == "C" and rec["help_requests"] == 1 and rec["self_checks"] == 1 and rec["independent_seconds"] == 600
    assert rec["feedback_decisions"][0]["accepts"] is False and rec["plan_goal"].startswith("Ikki")
    assert rec["comparison_note"].startswith("AI varianti")

    dyn = client.get("/api/student/dynamics", headers=h).json()
    assert dyn["lessons_completed"] == 1 and dyn["timeline"][0]["variant"] == "C" and dyn["help_requests_total"] == 1
    # boshqa talaba dinamikasini ko'ra olmaydi
    assert client.get("/api/student/dynamics?student_id=e0", headers=h).status_code == 403


# ---------------- Tabaqalashtirish va o'qituvchi paneli ----------------

def test_tabaqalashtirish_va_oqituvchi_paneli(env):
    client, S, tok = env
    th = tok("t-1", "teacher")
    r = client.get("/api/teacher/panel/groups/g-exp/differentiation", headers=th)
    assert r.status_code == 200
    d = r.json()
    assert d["counts"]["A"] >= 1 and d["counts"]["C"] >= 1  # kamida uch xil variant mantiqi
    e0 = next(s for s in d["subgroups"]["A"] if s["id"] == "e0")
    assert e0["source"] == "system" and "CEFR" in e0["reason"]

    # 3-qoida: o'qituvchi variantni o'zgartiradi
    r = client.post("/api/teacher/panel/students/e0/variant", json={"variant": "B", "note": "Birinchi haftada moslashish uchun"}, headers=th)
    assert r.status_code == 200 and r.json()["effective"]["variant"] == "B" and r.json()["effective"]["source"] == "teacher"
    sh = tok("e0", "student", "g-exp")
    lesson_mod.reset_lesson_state("e0")
    assert client.get("/api/lesson/5", headers=sh).json()["variant"] == "B"
    client.delete("/api/teacher/panel/students/e0/variant", headers=th)
    lesson_mod.reset_lesson_state("e0")
    assert client.get("/api/lesson/5", headers=sh).json()["variant"] == "A"

    # Profilni qo'lda tuzatish — sabab majburiy, tarix saqlanadi
    assert client.post("/api/teacher/panel/students/e1/profile-override", json={"cefr_speaking": "B1"}, headers=th).status_code == 422
    r = client.post("/api/teacher/panel/students/e1/profile-override", json={"cefr_speaking": "B1", "anxiety_level": 50, "note": "Og'zaki suhbatda B1 ko'rsatdi"}, headers=th)
    assert r.status_code == 200 and r.json()["profile"]["cefr"]["speaking"] == "B1"
    recs = client.get("/api/teacher/panel/students/e1/records", headers=th).json()
    assert len(recs["profile_history"]) == 2 and recs["profile_history"][0]["source"] == "teacher_override"

    # Talaba o'qituvchi paneliga kira olmaydi; boshqa o'qituvchi chet guruhni ko'ra olmaydi
    assert client.get("/api/teacher/panel/groups/g-exp/students", headers=sh).status_code == 403
    other = tok("t-9", "teacher")
    assert client.get("/api/teacher/panel/groups/g-exp/students", headers=other).status_code == 404
    assert client.get("/api/teacher/panel/observation", headers=th).status_code == 200


# ---------------- Jonli statistika va diagnostika -> assessments ----------------

def test_jonli_jadvallar_va_import(env):
    client, S, tok = env
    rh = tok("r-1", "researcher")
    import random
    random.seed(7)
    items = []
    for i in range(6):
        for sk in ("listening", "reading", "speaking", "writing"):
            items.append({"email": f"e{i}@x.uz", "assessment_type": "pre", "skill": sk, "score": 50 + random.randint(0, 10)})
            items.append({"email": f"e{i}@x.uz", "assessment_type": "post", "skill": sk, "score": 76 + random.randint(0, 10)})
            items.append({"email": f"c{i}@x.uz", "assessment_type": "pre", "skill": sk, "score": 50 + random.randint(0, 10)})
            items.append({"email": f"c{i}@x.uz", "assessment_type": "post", "skill": sk, "score": 60 + random.randint(0, 8)})
        for m in ("meta_planning", "meta_monitoring", "meta_evaluation", "meta_regulation"):
            items.append({"email": f"e{i}@x.uz", "assessment_type": "pre", "skill": m, "score": 56, "max_score": 100})
            items.append({"email": f"e{i}@x.uz", "assessment_type": "post", "skill": m, "score": 86 + random.randint(0, 6), "max_score": 100})
            items.append({"email": f"c{i}@x.uz", "assessment_type": "pre", "skill": m, "score": 56, "max_score": 100})
            items.append({"email": f"c{i}@x.uz", "assessment_type": "post", "skill": m, "score": 64 + random.randint(0, 4), "max_score": 100})
        items.append({"email": f"e{i}@x.uz", "assessment_type": "pre", "skill": "anxiety", "score": 70})
        items.append({"email": f"e{i}@x.uz", "assessment_type": "post", "skill": "anxiety", "score": 45})
    items.append({"email": "nobody@x.uz", "assessment_type": "pre", "skill": "reading", "score": 50})
    r = client.post("/api/research/live/assessments", json={"items": items}, headers=rh)
    assert r.status_code == 200 and r.json()["saved"] == len(items) - 1 and r.json()["error_count"] == 1

    t = client.get("/api/research/live/tables", headers=rh).json()
    assert t["data_source"] == "live_platform" and t["completeness"]["with_both"] == 12 and t["completeness"]["ready"]
    assert t["table_4_2"]["summary"] == {"experimental_total": 6, "control_total": 6, "grand_total": 12}
    assert t["table_4_4"]["overall"]["p_value"] > 0.05
    assert t["table_4_5"]["overall"]["exp_post"] > t["table_4_5"]["overall"]["ctrl_post"]
    assert all(sk["cohens_d"] > 0.8 for sk in t["table_4_6"]["skills"])
    assert t["table_4_7"]["average_d"] > 0.8 and t["table_4_7"]["components"][-1]["exp_growth"].startswith("-")  # tashvish pasaygan
    assert t["table_4_8"]["overall"]["ratio_k"] > 1.0
    assert "rad etildi" in t["table_4_9"]["indicators"][1]["conclusion"]
    assert t["table_4_10"]["rows"][5]["match"] == "Muvofiq"

    # Eksport jonli ma'lumotdan
    for path in ("/api/research/export-docx?source=live", "/api/research/export-excel?source=live", "/api/research/export-csv?source=live"):
        assert client.get(path, headers=rh).status_code == 200
    # CSV import
    csv_text = "email,assessment_type,skill,score,max_score\ne0@x.uz,mid,writing,70,100\n"
    r = client.post("/api/research/live/assessments/import", headers=rh, files={"file": ("a.csv", csv_text.encode(), "text/csv")})
    assert r.status_code == 200 and r.json()["saved"] == 1
    # Talaba jonli ma'lumotlarga kira olmaydi
    assert client.get("/api/research/live/tables", headers=tok("e0", "student")).status_code == 403


def test_diagnostika_assessment_yozadi_va_metakognitiv(env):
    client, S, tok = env
    h = tok("e2", "student", "g-exp")
    qs = client.get("/api/student/diagnostic/questions", headers=h).json()
    sq = client.get("/api/student/survey/questions", headers=h).json()
    assert any(q["dimension"] == "planning" for q in sq)
    payload = {"diagnostic_answers": [{"question_id": q["id"], "selected_option_index": q["correct_index"]} for q in qs[:12]],
               "survey_answers": [{"question_id": q["id"], "rating": 4} for q in sq]}
    r = client.post("/api/student/diagnostic/submit", json=payload, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["assessment_type"] == "pre" and d["metacognitive"]["planning"] == 4.0
    r2 = client.post("/api/student/diagnostic/submit", json=payload, headers=h)
    assert r2.json()["assessment_type"] == "post"
    db = S()
    rows = db.query(Assessment).filter(Assessment.student_id == "e2").all()
    db.close()
    assert {a.assessment_type for a in rows} == {"pre", "post"}
    assert any(a.skill == "meta_planning" and a.score == 80 for a in rows)
    assert any(a.skill == "anxiety" for a in rows)
