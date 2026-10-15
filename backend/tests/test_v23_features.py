"""v2.3: qayta ishlash (qoralamalar), xato joylari, lokal CEFR, o'qituvchi SI-kompetensiyasi, kuzatuv eksporti, hisobni o'chirish."""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.models.entities import User, Group, Institution, StudentProfile
from app.services.cefr_estimate import estimate_cefr, relevance_score
from app.api import lesson as lesson_mod


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_v23_")
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
    db.add(Group(id="g1", institution_id="inst_buxdu", name="302", experiment_arm="experimental", teacher_id="t1"))
    db.add(User(id="t1", email="t1@x.uz", password_hash="x", full_name="Ustoz", role="teacher", is_approved=True))
    db.add(User(id="s1", email="s1@x.uz", password_hash=hash_password("Student123"), full_name="Talaba", role="student", group_id="g1", is_approved=True, phone_number="+998901112233"))
    db.add(StudentProfile(student_id="s1"))
    db.commit(); db.close()
    client = TestClient(app)
    tok = lambda uid, role, gid=None: {"Authorization": f"Bearer {create_access_token({'id': uid, 'role': role, 'group_id': gid})}"}
    yield client, S, tok
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_lokal_cefr_va_moslik():
    weak = "I like teach. She have book. It good. We discuss about test. " * 4
    strong = ("Although automated assessment tools provide immediate diagnostic feedback, their pedagogical value depends on how "
              "teachers mediate the results. Furthermore, analytic rubrics enhance inter-rater reliability, whereas holistic scoring "
              "remains vulnerable to subjective drift. Consequently, formative feedback should be integrated systematically, "
              "provided that learners are trained to interpret criteria rather than merely accept corrections. In conclusion, "
              "validity and reliability must be balanced deliberately. ") * 2
    w = estimate_cefr(weak, l1_error_count=8)
    s = estimate_cefr(strong, l1_error_count=0)
    assert w["level"] in ("A1", "A2") and s["level"] in ("B2", "C1") and s["score"] > w["score"]
    assert s["reasons"] and "Taxminiy" in s["note"]
    rel = relevance_score(strong, ["rubric", "validity", "reliability", "feedback", "fluency"])
    assert rel["score"] >= 50 and "fluency" in rel["missing_keywords"]


def test_qayta_ishlash_va_belgilash(env):
    client, S, tok = env
    h = tok("s1", "student", "g1")
    lesson_mod.reset_lesson_state("s1")
    client.post("/api/lesson/5/stage/next?target_stage=independent", headers=h)
    d1 = "Assessing writing requires criteria. She have many questions and we discuss about rubrics. Teachers consider content. " * 3
    r = client.post("/api/lesson/5/production", json={"lesson_id": "5", "content_text": d1, "word_count": 50}, headers=h)
    assert r.status_code == 200
    j = r.json()
    assert j["draft_n"] == 1 and j["spans"] and j["cefr_estimate_local"]["level"] and j["relevance"]["score"] >= 0
    assert all(isinstance(s["span"], list) and len(s["span"]) == 2 for s in j["spans"])
    # o'zgarmagan matn rad etiladi
    assert client.post("/api/lesson/5/revise", json={"content_text": d1}, headers=h).status_code == 400
    d2 = d1.replace("She have", "She has").replace("discuss about", "discuss")
    r = client.post("/api/lesson/5/revise", json={"content_text": d2}, headers=h)
    assert r.status_code == 200
    j2 = r.json()
    assert j2["draft_n"] == 2 and j2["delta"]["l1_count"] < 0 and len(j2["drafts"]) == 2 and "text" not in j2["drafts"][0]
    drafts = client.get("/api/lesson/5/drafts", headers=h).json()
    assert drafts["count"] == 2 and drafts["drafts"][0]["text"] == d1.strip()
    client.post("/api/lesson/5/self-rating", json={"ratings": {"content": 4, "grammar": 4, "lexis": 4, "coherence": 4}}, headers=h)
    r = client.post("/api/lesson/5/reflection", json={"gap_explanation": "xatolarni sezmabman", "next_goal": "3-shaxs -s"}, headers=h)
    assert r.status_code == 200
    rec = client.get("/api/lesson/history", headers=h).json()["records"][0]
    assert rec["revision_count"] == 1 and rec["first_score"] is not None and rec["cefr_estimate"] and len(rec["drafts"]) == 2
    full = client.get("/api/teacher/panel/students/s1/records", headers=tok("t1", "teacher")).json()["records"][0]
    assert full["drafts"][1]["text"] == d2.strip()


def test_oqituvchi_kompetensiyasi(env):
    client, S, tok = env
    th = tok("t1", "teacher")
    q = client.get("/api/teacher/competence/questions", headers=th).json()
    assert len(q["items"]) == 16 and len(q["levels"]) == 3 and len(q["tool_evaluation_checklist"]) == 8
    ans = [{"item_id": it["id"], "rating": 2 if it["component"] == "ethical" else 4} for it in q["items"]]
    r = client.post("/api/teacher/competence/self-assess", json={"answers": ans}, headers=th)
    assert r.status_code == 200
    j = r.json()
    assert j["assessment_type"] == "pre" and j["weakest"] == "ethical" and j["components"]["ethical"]["level"].startswith("Boshlang")
    assert j["recommendations"][0]["component"] == "ethical"
    ans2 = [{"item_id": it["id"], "rating": 5} for it in q["items"]]
    j2 = client.post("/api/teacher/competence/self-assess", json={"answers": ans2}, headers=th).json()
    assert j2["assessment_type"] == "post" and j2["overall_level"]["key"] == "creative"
    me = client.get("/api/teacher/competence/me", headers=th).json()
    assert me["growth"] > 0 and me["history"]["post"]["level"].startswith("Ijodiy")
    ov = client.get("/api/research/live/overview", headers=th).json()
    assert ov["teacher_competence"]["teachers"] == 1 and ov["teacher_competence"]["components"]["ethical"]["n_paired"] == 1
    te = client.post("/api/teacher/competence/tool-evaluation", json={"tool_name": "Grammarly", "answers": {"didactic_task": True, "level": True, "feedback_quality": False, "openness": True, "data": True, "language": False, "access": True, "control": True}}, headers=th).json()
    assert te["score_percent"] == 75 and te["verdict"] == "Tavsiya etiladi" and len(te["unmet"]) == 2
    assert client.get("/api/teacher/competence/questions", headers=tok("s1", "student")).status_code == 403


def test_kuzatuv_eksport_va_hisobni_ochirish(env):
    client, S, tok = env
    th = tok("t1", "teacher")
    r = client.get("/api/teacher/panel/observation/export?group_id=g1", headers=th)
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
    h = tok("s1", "student", "g1")
    assert client.request("DELETE", "/api/auth/me", json={"password": "wrong", "confirm": "O'CHIRISH"}, headers=h).status_code == 400
    assert client.request("DELETE", "/api/auth/me", json={"password": "Student123", "confirm": "ha"}, headers=h).status_code == 422
    r = client.request("DELETE", "/api/auth/me", json={"password": "Student123", "confirm": "O'CHIRISH"}, headers=h)
    assert r.status_code == 200
    db = S(); u = db.query(User).filter(User.id == "s1").first(); db.close()
    assert u.email.startswith("deleted_") and u.phone_number is None and u.is_active is False
    # nofaol hisob bilan token endi ishlamaydi
    assert client.get("/api/auth/me", headers=h).status_code == 401
