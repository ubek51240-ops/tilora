"""v2.4: nazorat guruhi cheklovi, nazorat oynasi, avtomatik ko'mak taklifi, SILL, Cronbach α / inter-rater,
mikroo'qitish + tengdoshlar baholashi, Guskey 1/4, saqlash muddati."""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core.security import create_access_token
from app.models.entities import User, Group, Institution, StudentProfile, LessonRecord, TeacherProposal
from app.services import statistics as st
from app.api import lesson as lesson_mod


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_v24_")
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
    import app.database as dbmod
    monkeypatch.setattr(dbmod, "SessionLocal", S)
    db = S()
    db.add(Institution(id="inst_buxdu", name="BuxDU", short_name="BuxDU"))
    db.add(Group(id="g-exp", institution_id="inst_buxdu", name="302", experiment_arm="experimental", teacher_id="t1"))
    db.add(Group(id="g-ctrl", institution_id="inst_buxdu", name="304", experiment_arm="control", teacher_id="t1"))
    db.add(User(id="t1", email="t1@x.uz", password_hash="x", full_name="Ustoz", role="teacher", is_approved=True))
    db.add(User(id="r1", email="r1@x.uz", password_hash="x", full_name="Tadqiqotchi", role="researcher", is_approved=True))
    db.add(User(id="a1", email="a1@x.uz", password_hash="x", full_name="Admin", role="admin", is_approved=True))
    for i in range(3):
        db.add(User(id=f"e{i}", email=f"e{i}@x.uz", password_hash="x", full_name=f"Exp {i}", role="student", group_id="g-exp", is_approved=True))
    db.add(User(id="c0", email="c0@x.uz", password_hash="x", full_name="Ctrl 0", role="student", group_id="g-ctrl", is_approved=True))
    db.add(StudentProfile(student_id="e0", cefr_listening="A2", cefr_reading="B1", cefr_speaking="A2", cefr_writing="A2", anxiety_level=80, autonomy_readiness=30, load_capacity=30))
    db.commit(); db.close()
    client = TestClient(app)
    tok = lambda uid, role, gid=None: {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': role, 'group_id': gid})}"}
    yield client, S, tok
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_ishonchlilik_statistikasi():
    m = [[4, 5, 4, 5], [2, 2, 3, 2], [5, 4, 5, 5], [3, 3, 2, 3], [4, 4, 4, 5], [1, 2, 1, 2]]
    a = st.cronbach_alpha(m)
    assert a["alpha"] > 0.8 and a["n_items"] == 4
    assert st.cronbach_alpha([[1, 2]])["alpha"] is None
    ag = st.rater_agreement([4, 3, 5, 2, 4, 3], [4, 3, 4, 2, 5, 3])
    assert ag["exact"] >= 0.6 and ag["adjacent"] == 1.0 and ag["kappa"] > 0.6
    assert st.pearson_r([1, 2, 3], [2, 4, 6]) == 1.0


def test_nazorat_guruhi_cheklovi_va_oynasi(env):
    client, S, tok = env
    ch = tok("c0", "student", "g-ctrl")
    r = client.get("/api/student/path", headers=ch)
    assert r.status_code == 200 and r.json()["experiment_arm"] == "control" and all(i["scaffold_level"] == "none" for i in r.json()["items"])
    for p in ("/api/lesson/5/plan", "/api/lesson/5/self-rating", "/api/lesson/5/alternative"):
        rr = client.post(p, json={"goal": "maqsad kerak emas", "ratings": {"content": 4, "grammar": 4, "lexis": 4, "coherence": 4}}, headers=ch)
        assert rr.status_code == 403 and rr.json()["detail"]["error_code"] == "CONTROL_GROUP_RESTRICTED", p
    rr = client.post("/api/ai/generate", json={"prompt": "x"}, headers=ch)
    assert rr.status_code == 403 and rr.json()["detail"]["error_code"] == "CONTROL_GROUP_RESTRICTED"
    # Mahsulot va lokal izoh nazorat guruhiga ham ochiq (an'anaviy: o'qituvchi ko'radi)
    client.post("/api/lesson/5/stage/next?target_stage=independent", headers=ch)
    assert client.post("/api/lesson/5/production", json={"lesson_id": "5", "content_text": "Assessing writing requires clear criteria and feedback. " * 5, "word_count": 40}, headers=ch).status_code == 200
    st_ = client.get("/api/student/experiment-status", headers=ch).json()
    assert st_["adaptive_enabled"] is False and st_["ai_enabled"] is False

    # Tajriba guruhi: AI ochiq; o'qituvchi nazorat oynasini ochsa — yopiladi, diagnostika 'post' deb yoziladi
    eh = tok("e1", "student", "g-exp")
    th = tok("t1", "teacher")
    assert client.get("/api/student/experiment-status", headers=eh).json()["ai_enabled"] is True
    assert client.patch("/api/teacher/panel/groups/g-exp/assessment-window", json={"window": "post"}, headers=th).status_code == 200
    rr = client.post("/api/ai/generate", json={"prompt": "x"}, headers=eh)
    assert rr.status_code == 403 and rr.json()["detail"]["error_code"] == "ASSESSMENT_WINDOW"
    qs = client.get("/api/student/diagnostic/questions", headers=eh).json()
    sq = client.get("/api/student/survey/questions", headers=eh).json()
    d = client.post("/api/student/diagnostic/submit", json={"diagnostic_answers": [{"question_id": q["id"], "selected_option_index": 0} for q in qs[:6]],
                                                             "survey_answers": [{"question_id": q["id"], "rating": 3} for q in sq]}, headers=eh).json()
    assert d["assessment_type"] == "post"
    client.patch("/api/teacher/panel/groups/g-exp/assessment-window", json={"window": "none"}, headers=th)
    assert client.get("/api/student/experiment-status", headers=eh).json()["ai_enabled"] is True
    # qanotni o'zgartirish
    assert client.patch("/api/teacher/panel/groups/g-ctrl/arm", json={"arm": "experimental"}, headers=th).json()["group"]["arm"] == "experimental"
    assert client.get("/api/student/experiment-status", headers=ch).json()["adaptive_enabled"] is True


def test_komak_taklifi_avtomatik_va_tasdiqlash(env):
    client, S, tok = env
    h = tok("e0", "student", "g-exp")
    th = tok("t1", "teacher")
    text = "Assessing learner writing requires clear criteria. Furthermore, teachers should consider content, accuracy, vocabulary and coherence. " * 6
    for i in range(3):
        lesson_mod.reset_lesson_state("e0")
        client.post("/api/lesson/5/stage/next?target_stage=independent", headers=h)
        client.post("/api/lesson/5/production", json={"lesson_id": "5", "content_text": text, "word_count": 100}, headers=h)
        client.post("/api/lesson/5/self-rating", json={"ratings": {"content": 4, "grammar": 4, "lexis": 4, "coherence": 4}}, headers=h)
        r = client.post("/api/lesson/5/reflection", json={"gap_explanation": "sabab sabab", "next_goal": "maqsad maqsad"}, headers=h).json()
    assert r["adaptation_proposal"] and r["adaptation_proposal"]["from"] == "C" and r["adaptation_proposal"]["to"] == "B"
    props = client.get("/api/proposals?tab=system", headers=th).json()["proposals"]
    p = next(x for x in props if x["proposal_type"] == "scaffold_change")
    assert p["status"] == "pending" and p["sender_role"] == "system"
    # O'qituvchi tasdiqlaydi -> variant B kuchga kiradi
    assert client.post(f"/api/proposals/{p['id']}/approve", json={"teacher_comment": "Roziman"}, headers=th).status_code == 200
    lesson_mod.reset_lesson_state("e0")
    s = client.get("/api/lesson/5", headers=h).json()
    assert s["variant"] == "B"
    # takroriy taklif yaratilmaydi (pending bo'lmasa ham, endi B dan A ga 3 ta ketma-ket kerak)
    assert client.get("/api/teacher/panel/students/e0/records", headers=th).json()["variant"]["source"] == "teacher"


def test_sill_va_cronbach_va_inter_rater(env):
    client, S, tok = env
    rh = tok("r1", "researcher")
    th = tok("t1", "teacher")
    q = client.get("/api/student/sill/questions", headers=tok("e0", "student", "g-exp")).json()
    assert len(q["items"]) == 24 and len(q["groups"]) == 6
    for i in range(3):
        h = tok(f"e{i}", "student", "g-exp")
        ans = [{"item_id": it["id"], "rating": 2 if it["group"] == "affective" else 4 + (i % 2)} for it in q["items"]]
        r = client.post("/api/student/sill", json={"answers": ans}, headers=h)
        assert r.status_code == 200 and r.json()["assessment_type"] == "pre" and r.json()["weakest"] == "affective"
    me = client.get("/api/student/sill/me", headers=tok("e0", "student", "g-exp")).json()
    assert "pre" in me["history"] and me["history"]["pre"]["groups"]["affective"] == 2.0
    # Diagnostika anketasi xom javoblari -> FLCAS/MSLQ α
    sq = client.get("/api/student/survey/questions", headers=tok("e0", "student")).json()
    import random
    random.seed(3)
    for i in range(3):
        base = random.randint(2, 4)
        client.post("/api/student/diagnostic/submit", json={"diagnostic_answers": [], "survey_answers": [{"question_id": s["id"], "rating": min(5, max(1, base + random.choice([-1, 0, 0, 1])))} for s in sq]},
                    headers=tok(f"e{i}", "student", "g-exp"))
    rel = client.get("/api/research/live/reliability", headers=rh).json()
    assert rel["cronbach"]["sill"]["overall"]["n_respondents"] == 3 and rel["cronbach"]["sill"]["overall"]["n_items"] == 24
    assert rel["cronbach"]["flcas"]["overall"]["n_respondents"] == 3 and rel["cronbach"]["mslq"]["dimensions"]["planning"]["n_items"] == 3
    assert client.get("/api/research/live/sill", headers=rh).json()["groups"]["memory"]["experimental"]["n_pre"] == 3
    # Ikkinchi baholovchi (o'qituvchi) -> inter-rater
    h = tok("e0", "student", "g-exp")
    lesson_mod.reset_lesson_state("e0")
    client.post("/api/lesson/5/stage/next?target_stage=independent", headers=h)
    client.post("/api/lesson/5/production", json={"lesson_id": "5", "content_text": "Assessing writing requires criteria. Furthermore teachers consider accuracy. " * 5, "word_count": 50}, headers=h)
    client.post("/api/lesson/5/self-rating", json={"ratings": {"content": 4, "grammar": 4, "lexis": 4, "coherence": 4}}, headers=h)
    rid = client.post("/api/lesson/5/reflection", json={"gap_explanation": "sabab sabab", "next_goal": "maqsad maqsad"}, headers=h).json()["record_id"]
    r = client.post(f"/api/teacher/panel/records/{rid}/rate", json={"content": 4, "grammar": 4, "lexis": 4, "coherence": 4}, headers=th)
    assert r.status_code == 200 and r.json()["agreement"]["n"] == 4
    rel = client.get("/api/research/live/reliability", headers=rh).json()
    assert rel["inter_rater"]["records_double_rated"] == 1 and rel["inter_rater"]["overall"]["n"] == 4


def test_mikrooqitish_va_tengdoshlar(env):
    client, S, tok = env
    h0, h1, th = tok("e0", "student", "g-exp"), tok("e1", "student", "g-exp"), tok("t1", "teacher")
    assert len(client.get("/api/student/microteaching/rubric", headers=h0).json()["forms"]) == 7
    bad = {"title": "Dars", "objective": "By the end students will be able to use ICQs", "tool_name": "Quizlet", "tool_rationale": "", "alternative_plan": "kartochkalar", "independent_share": 40}
    assert client.post("/api/student/microteaching", json=bad, headers=h0).status_code == 422  # sabab majburiy
    good = dict(bad, tool_rationale="Lug'atni tez takrorlash uchun; faqat tayyorgarlik bosqichida", submit=True,
                stages=[{"name": "Kirish", "minutes": 2, "activity": "maqsad", "technology_role": "yo'q"}, {"name": "Mustaqil", "minutes": 6, "activity": "dialog", "technology_role": "cheklangan"}])
    m = client.post("/api/student/microteaching", json=good, headers=h0).json()["microteaching"]
    assert m["status"] == "submitted" and m["checks"]["independent_share_ok"]
    # o'zini baholay olmaydi; guruhdosh baholaydi; ikki marta emas
    assert client.post(f"/api/student/microteaching/{m['id']}/review", json={"rubric": {"objective": 5, "instructions": 4, "tool_use": 4, "reflection": 3}}, headers=h0).status_code == 404
    assert client.post(f"/api/student/microteaching/{m['id']}/review", json={"rubric": {"objective": 5, "instructions": 4, "tool_use": 4, "reflection": 3}, "strengths": "aniq maqsad"}, headers=h1).status_code == 200
    assert client.post(f"/api/student/microteaching/{m['id']}/review", json={"rubric": {"objective": 5, "instructions": 4, "tool_use": 4, "reflection": 3}}, headers=h1).status_code == 400
    lst = client.get("/api/student/microteaching", headers=h1).json()
    assert lst["peers"][0]["already_reviewed"] is True
    mine = client.get("/api/student/microteaching", headers=h0).json()["mine"][0]
    assert mine["peer_count"] == 1 and mine["peer_avg"]["objective"] == 5.0 and mine["status"] == "reviewed"
    # o'qituvchi baholaydi
    r = client.post(f"/api/teacher/panel/microteaching/{m['id']}/evaluate", json={"rubric": {"objective": 5, "instructions": 4, "tool_use": 5, "reflection": 3}, "comment": "Yaxshi"}, headers=th)
    assert r.status_code == 200 and r.json()["microteaching"]["status"] == "evaluated"
    assert client.get("/api/teacher/panel/microteaching?group_id=g-exp", headers=th).json()["summary"]["evaluated"] == 1
    assert client.get("/api/research/live/reliability", headers=th).json()["inter_rater"]["microteaching_peer_vs_teacher"]["n"] == 4
    # baholangan loyihani o'zgartirib bo'lmaydi
    assert client.put(f"/api/student/microteaching/{m['id']}", json=good, headers=h0).status_code == 400


def test_guskey_va_retention(env):
    client, S, tok = env
    th, ah = tok("t1", "teacher"), tok("a1", "admin")
    assert len(client.get("/api/teacher/competence/satisfaction/items", headers=th).json()["items"]) == 5
    r = client.post("/api/teacher/competence/satisfaction", json={"answers": {"g1_1": 5, "g1_2": 4, "g1_3": 5, "g1_4": 4, "g1_5": 5}}, headers=th).json()
    assert r["avg"] == 4.6 and r["label"] == "Yuqori"
    r = client.post("/api/teacher/competence/lesson-plan-check", json={"objective_in_syllabus": True, "tool_linked_to_objective": True, "tool_at_specific_stage": True,
                                                                        "tool_rationale_written": False, "alternative_without_tool": True, "independent_stage_share_ok": True,
                                                                        "feedback_explains_cause": True, "max_two_new_tools": True}, headers=th).json()
    assert r["score_percent"] == 88 and len(r["unmet"]) == 1
    g = client.get("/api/teacher/competence/guskey/summary", headers=th).json()
    assert g["level1_satisfaction"]["n"] == 1 and g["level4_practice"]["avg_percent"] == 88
    s = client.get("/api/admin/retention/status", headers=ah).json()
    assert s["retention_days"] >= 365 and "O'RQ-547" in s["policy"]
    assert client.post("/api/admin/retention/purge?dry_run=true", headers=ah).json()["status"] == "dry_run"
    assert client.get("/api/admin/retention/status", headers=th).status_code == 403
    assert len(client.get("/api/content/lesson-forms").json()["forms"]) == 7
