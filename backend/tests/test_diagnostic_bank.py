"""
O'qituvchi diagnostika/anketa savollari banki: yuklash, audio, import va
talaba tomonida ko'rinishi. Alohida vaqtinchalik SQLite bazasi va audio papkasida ishlaydi,
shuning uchun asosiy tilora.db ga tegmaydi.
"""
import io
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
from app.services import diagnostic_bank as bank
from app.models.entities import User, Group


@pytest.fixture()
def env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="tilora_test_")
    db_path = os.path.join(tmp, "test.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    audio_dir = os.path.join(tmp, "audio")
    monkeypatch.setattr(bank, "AUDIO_DIR", audio_dir)

    # O'qituvchi, guruh va shu guruhdagi talaba
    db = TestSession()
    teacher = User(id="t-1", email="ustoz@test.uz", password_hash="x", full_name="Ustoz", role="teacher", is_approved=True)
    grp = Group(id="g-1", name="302", teacher_id="t-1")
    student = User(id="s-1", email="talaba@test.uz", password_hash="x", full_name="Talaba", role="student", group_id="g-1", is_approved=True)
    db.add_all([teacher, grp, student])
    db.commit()
    db.close()

    client = TestClient(app)
    teacher_h = {"Authorization": f"Bearer {create_access_token({'id': 't-1', 'role': 'teacher'})}"}
    student_h = {"Authorization": f"Bearer {create_access_token({'id': 's-1', 'role': 'student', 'group_id': 'g-1'})}"}
    yield client, teacher_h, student_h, audio_dir

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def _q(**over):
    base = {
        "skill": "reading", "cefr_level": "B1",
        "question": "What does 'tailor' mean?",
        "options": ["Sew", "Adapt", "Shorten", "Evaluate"],
        "correct_index": 1, "rationale": "Contextual meaning."
    }
    base.update(over)
    return base


def test_bosh_bank_standart_savollarni_qaytaradi(env):
    client, teacher_h, student_h, _ = env
    res = client.get("/api/teacher/diagnostic/questions", headers=teacher_h)
    assert res.status_code == 200
    assert res.json()["using_defaults"] is True
    n_diag = len(bank.default_diagnostic_questions())
    n_surv = len(bank.default_survey_questions())
    assert res.json()["defaults_count"] == n_diag

    res = client.get("/api/student/diagnostic/questions", headers=student_h)
    assert res.status_code == 200
    assert len(res.json()) == n_diag and res.json()[0]["id"] == "diag_01"

    res = client.get("/api/student/survey/questions")  # mehmon ham ko'ra oladi
    assert res.status_code == 200 and len(res.json()) == n_surv


def test_talaba_rolida_bankka_kirish_taqiqlanadi(env):
    client, _, student_h, _ = env
    assert client.get("/api/teacher/diagnostic/questions", headers=student_h).status_code == 403
    assert client.post("/api/teacher/survey/questions", headers=student_h, json={"prompt_uz": "x"}).status_code == 403


def test_oqituvchi_savol_qoshsa_talaba_uni_koradi(env):
    client, teacher_h, student_h, _ = env
    res = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q())
    assert res.status_code == 200, res.text
    qid = res.json()["question"]["id"]

    res = client.post("/api/teacher/survey/questions", headers=teacher_h,
                      json={"dimension": "anxiety", "prompt_uz": "Hayajonlanaman.", "weight": 1.2})
    assert res.status_code == 200, res.text
    sid = res.json()["question"]["id"]

    diag = client.get("/api/student/diagnostic/questions", headers=student_h).json()
    assert [q["id"] for q in diag] == [qid]
    assert diag[0]["options"] == ["Sew", "Adapt", "Shorten", "Evaluate"]
    survey = client.get("/api/student/survey/questions", headers=student_h).json()
    assert [s["id"] for s in survey] == [sid]

    # Yuborish: to'g'ri javob + anketa -> profil hisoblanadi
    res = client.post("/api/student/diagnostic/submit", headers=student_h, json={
        "diagnostic_answers": [{"question_id": qid, "selected_option_index": 1}],
        "survey_answers": [{"question_id": sid, "rating": 5}],
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["correct_count"] == 1 and body["total_questions"] == 1
    assert body["cefr_levels"]["reading"] == "C1"       # 1/1 -> yuqori pog'ona
    assert body["cefr_levels"]["listening"] == "B1"     # savol yo'q -> neytral
    assert body["cognitive_affective"]["anxiety_level"] == 100  # 5*1.2 / 5 -> 100%

    # O'chirib qo'yilgan savol talabaga ko'rinmaydi, bank bo'shasa standartga qaytadi
    client.patch(f"/api/teacher/diagnostic/questions/{qid}/toggle", headers=teacher_h)
    assert client.get("/api/student/diagnostic/questions", headers=student_h).json()[0]["id"] == "diag_01"


def test_validatsiya_xatolari(env):
    client, teacher_h, _, _ = env
    r = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q(correct_index=7))
    assert r.status_code == 400 and "correct_index" in r.json()["detail"]
    r = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q(options=["only one"]))
    assert r.status_code == 400
    r = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q(skill="grammar"))
    assert r.status_code == 400
    r = client.post("/api/teacher/survey/questions", headers=teacher_h, json={"prompt_uz": "x", "dimension": "mood"})
    assert r.status_code == 400
    r = client.post("/api/teacher/survey/questions", headers=teacher_h, json={"prompt_uz": "x", "weight": 9})
    assert r.status_code == 400


def test_audio_yuklash_va_ochirish(env):
    client, teacher_h, student_h, audio_dir = env
    qid = client.post("/api/teacher/diagnostic/questions", headers=teacher_h,
                      json=_q(skill="listening", question="Listen and choose.")).json()["question"]["id"]

    # Noto'g'ri format rad etiladi
    r = client.post(f"/api/teacher/diagnostic/questions/{qid}/audio", headers=teacher_h,
                    files={"file": ("virus.exe", b"MZ...", "application/octet-stream")})
    assert r.status_code == 400

    # To'g'ri format saqlanadi va talabaga URL keladi
    r = client.post(f"/api/teacher/diagnostic/questions/{qid}/audio", headers=teacher_h,
                    files={"file": ("prompt.mp3", b"ID3fake-mp3-bytes", "audio/mpeg")},
                    data={"audio_text": "Could you tell me the time?"})
    assert r.status_code == 200, r.text
    q = r.json()["question"]
    assert q["audio_url"].startswith("/uploads/audio/") and q["is_audio"] is True
    assert q["audio_text"] == "Could you tell me the time?"
    saved = os.path.join(audio_dir, os.path.basename(q["audio_url"]))
    assert os.path.isfile(saved)

    stu = client.get("/api/student/diagnostic/questions", headers=student_h).json()[0]
    assert stu["audio_url"] == q["audio_url"] and stu["is_audio"] is True

    # Almashtirilganda eski fayl o'chadi
    r = client.post(f"/api/teacher/diagnostic/questions/{qid}/audio", headers=teacher_h,
                    files={"file": ("prompt2.wav", b"RIFFfake", "audio/wav")})
    assert r.status_code == 200
    assert not os.path.exists(saved)
    saved2 = os.path.join(audio_dir, os.path.basename(r.json()["question"]["audio_url"]))
    assert os.path.isfile(saved2)

    # Audio olib tashlanadi, savol o'chirilganda fayl ham ketadi
    r = client.delete(f"/api/teacher/diagnostic/questions/{qid}/audio", headers=teacher_h)
    assert r.status_code == 200 and r.json()["question"]["audio_url"] is None
    assert not os.path.exists(saved2)


def test_json_import_standart_nusxa_va_eksport(env):
    client, teacher_h, student_h, _ = env
    payload = [_q(), _q(question="Second?", correct_index=0), {"question": "broken", "options": ["a"]}]
    r = client.post("/api/teacher/diagnostic/questions/import", headers=teacher_h,
                    files={"file": ("bank.json", json.dumps(payload).encode("utf-8"), "application/json")},
                    data={"replace": "false"})
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2 and len(r.json()["skipped"]) == 1

    # Standart to'plamni nusxalash: N ta qo'shiladi (jami N+2)
    n_def = len(bank.default_diagnostic_questions())
    r = client.post("/api/teacher/diagnostic/questions/load-defaults", headers=teacher_h)
    assert r.status_code == 200 and r.json()["total"] == n_def + 2
    # Standart audio URL (/audio_diag_01.wav) saqlanib qoladi
    exported = client.get("/api/teacher/diagnostic/questions/export", headers=teacher_h).json()
    assert len(exported) == n_def + 2
    assert any(e.get("audio_url") == "/audio_diag_01.wav" for e in exported)
    assert "teacher_id" not in exported[0]

    # replace=true bilan import: faqat fayldagilar qoladi
    r = client.post("/api/teacher/diagnostic/questions/import", headers=teacher_h,
                    files={"file": ("bank.json", json.dumps([_q(question="Only")]).encode(), "application/json")},
                    data={"replace": "true"})
    assert r.json()["total"] == 1
    assert client.get("/api/student/diagnostic/questions", headers=student_h).json()[0]["question"] == "Only"

    # Anketa importi va hammasini o'chirish
    r = client.post("/api/teacher/survey/questions/import", headers=teacher_h,
                    files={"file": ("s.json", json.dumps([{"dimension": "pace", "prompt_uz": "Tez o'rganaman."}]).encode(), "application/json")})
    assert r.status_code == 200 and r.json()["imported"] == 1
    r = client.delete("/api/teacher/survey/questions", headers=teacher_h)
    assert r.json()["deleted"] == 1
    assert len(client.get("/api/student/survey/questions", headers=student_h).json()) == len(bank.default_survey_questions())


def test_boshqa_oqituvchi_savolini_ozgartira_olmaydi(env):
    client, teacher_h, _, _ = env
    qid = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q()).json()["question"]["id"]
    other_h = {"Authorization": f"Bearer {create_access_token({'id': 't-2', 'role': 'teacher'})}"}
    assert client.delete(f"/api/teacher/diagnostic/questions/{qid}", headers=other_h).status_code == 404
    assert client.put(f"/api/teacher/diagnostic/questions/{qid}", headers=other_h, json=_q()).status_code == 404


# ================================================================
# FANGA BIRIKTIRISH VA SUPER ADMIN
# ================================================================

def _admin_h():
    return {"Authorization": f"Bearer {create_access_token({'id': 'a-1', 'role': 'admin'})}"}


def _make_subject(client, teacher_h, name="Pedagogik diskurs"):
    r = client.post("/api/teacher/subjects", headers=teacher_h, json={"name": name, "code": "PED-1"})
    assert r.status_code == 200, r.text
    return r.json()["subject_id"]


def test_fanga_biriktirilgan_savol_faqat_shu_fanda_chiqadi(env):
    client, teacher_h, student_h, _ = env
    subj_id = _make_subject(client, teacher_h)

    general = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q(question="General?")).json()["question"]
    bound = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q(question="Subject?", subject_id=subj_id)).json()["question"]
    assert general["subject_id"] is None and bound["subject_id"] == subj_id

    # Fan tanlanmagan talaba: faqat umumiy
    ids = [q["id"] for q in client.get("/api/student/diagnostic/questions", headers=student_h).json()]
    assert ids == [general["id"]]
    # Fan tanlangan talaba: fan + umumiy
    ids = [q["id"] for q in client.get(f"/api/student/diagnostic/questions?subject_id={subj_id}", headers=student_h).json()]
    assert set(ids) == {general["id"], bound["id"]}

    # Fanlar ro'yxati talaba uchun
    subs = client.get("/api/student/diagnostic/subjects").json()["subjects"]
    assert subs[0]["id"] is None and subs[0]["diag_count"] == 1
    assert subs[1]["id"] == subj_id and subs[1]["diag_count"] == 2  # fan + umumiy

    # Yuborishda subject_id bilan hisoblanadi
    r = client.post("/api/student/diagnostic/submit", headers=student_h, json={
        "subject_id": subj_id,
        "diagnostic_answers": [{"question_id": general["id"], "selected_option_index": 1},
                               {"question_id": bound["id"], "selected_option_index": 0}],
        "survey_answers": [],
    })
    assert r.status_code == 200 and r.json()["total_questions"] == 2 and r.json()["correct_count"] == 1

    # O'qituvchi ko'rinishi: fan bo'yicha, umumiy va barchasi
    assert client.get(f"/api/teacher/diagnostic/questions?subject_id={subj_id}", headers=teacher_h).json()["total"] == 2
    assert client.get("/api/teacher/diagnostic/questions", headers=teacher_h).json()["total"] == 1
    assert client.get("/api/teacher/diagnostic/questions?all_subjects=true", headers=teacher_h).json()["total"] == 2
    lst = client.get("/api/teacher/diagnostic/subjects", headers=teacher_h).json()
    assert lst["general"]["diag_count"] == 1 and lst["subjects"][0]["diag_count"] == 1

    # Savolni fanga ko'chirish va umumiy qilish
    r = client.patch(f"/api/teacher/diagnostic/questions/{general['id']}/subject", headers=teacher_h, json={"subject_id": subj_id})
    assert r.status_code == 200 and r.json()["question"]["subject_id"] == subj_id
    r = client.patch(f"/api/teacher/diagnostic/questions/{bound['id']}/subject", headers=teacher_h, json={"subject_id": None})
    assert r.json()["question"]["subject_id"] is None

    # Faqat fanga tegishlilarni o'chirish umumiylarga tegmaydi
    r = client.delete(f"/api/teacher/diagnostic/questions?subject_id={subj_id}", headers=teacher_h)
    assert r.json()["deleted"] == 1
    assert client.get("/api/teacher/diagnostic/questions?all_subjects=true", headers=teacher_h).json()["total"] == 1


def test_begona_fanga_biriktirish_taqiqlanadi(env):
    client, teacher_h, _, _ = env
    subj_id = _make_subject(client, teacher_h)
    other_h = {"Authorization": f"Bearer {create_access_token({'id': 't-2', 'role': 'teacher'})}"}
    r = client.post("/api/teacher/diagnostic/questions", headers=other_h, json=_q(subject_id=subj_id))
    assert r.status_code == 403
    r = client.post("/api/teacher/survey/questions", headers=teacher_h, json={"prompt_uz": "x", "subject_id": "yoq-fan"})
    assert r.status_code == 404


def test_super_admin_istalgan_fanga_qoshadi_va_tahrirlaydi(env):
    client, teacher_h, student_h, _ = env
    subj_id = _make_subject(client, teacher_h, "EAP")
    admin_h = _admin_h()

    # Admin fanlar ro'yxatida o'qituvchining fanini ko'radi
    lst = client.get("/api/teacher/diagnostic/subjects", headers=admin_h).json()
    assert lst["is_admin"] is True and any(sb["id"] == subj_id for sb in lst["subjects"])

    # Admin o'qituvchi faniga savol qo'shadi
    r = client.post("/api/teacher/survey/questions", headers=admin_h,
                    json={"dimension": "autonomy", "prompt_uz": "Mustaqil o'rganaman.", "subject_id": subj_id})
    assert r.status_code == 200, r.text
    sid = r.json()["question"]["id"]

    # Talaba shu fanni tanlasa admin qo'shgan savolni ko'radi
    survey = client.get(f"/api/student/survey/questions?subject_id={subj_id}", headers=student_h).json()
    assert [x["id"] for x in survey] == [sid]

    # O'qituvchi o'z savolini qo'shadi; admin uni tahrirlay va o'chira oladi
    tq = client.post("/api/teacher/diagnostic/questions", headers=teacher_h, json=_q(subject_id=subj_id)).json()["question"]
    all_view = client.get("/api/teacher/diagnostic/questions?all_subjects=true", headers=admin_h).json()
    assert any(q["id"] == tq["id"] and q.get("teacher_name") == "Ustoz" for q in all_view["questions"])
    r = client.put(f"/api/teacher/diagnostic/questions/{tq['id']}", headers=admin_h, json=_q(question="Admin edited", subject_id=subj_id))
    assert r.status_code == 200 and r.json()["question"]["question"] == "Admin edited"
    assert client.delete(f"/api/teacher/diagnostic/questions/{tq['id']}", headers=admin_h).status_code == 200
    # O'qituvchi esa admin savolini ko'rmaydi/o'chira olmaydi
    assert client.delete(f"/api/teacher/survey/questions/{sid}", headers=teacher_h).status_code == 404


def test_import_va_standart_nusxa_fanga_biriktiriladi(env):
    client, teacher_h, student_h, _ = env
    subj_id = _make_subject(client, teacher_h)
    r = client.post("/api/teacher/diagnostic/questions/import", headers=teacher_h,
                    files={"file": ("b.json", json.dumps([_q(), _q(question="2")]).encode(), "application/json")},
                    data={"replace": "false", "subject_id": subj_id})
    assert r.status_code == 200 and r.json()["imported"] == 2
    r = client.post(f"/api/teacher/survey/questions/load-defaults?subject_id={subj_id}", headers=teacher_h)
    assert r.status_code == 200
    assert all(q["subject_id"] == subj_id for q in r.json()["questions"])
    # Umumiy ko'rinish bo'sh, fan ko'rinishida hammasi bor
    assert client.get("/api/teacher/diagnostic/questions", headers=teacher_h).json()["total"] == 0
    assert client.get(f"/api/teacher/diagnostic/questions?subject_id={subj_id}", headers=teacher_h).json()["total"] == 2
    assert len(client.get(f"/api/student/survey/questions?subject_id={subj_id}", headers=student_h).json()) == len(bank.default_survey_questions())
    # Fan tanlamagan talaba umumiy bank bo'sh bo'lgani uchun standartni ko'radi
    assert client.get("/api/student/diagnostic/questions", headers=student_h).json()[0]["id"] == "diag_01"


def test_matndan_ai_ovoz_yaratish(env, monkeypatch):
    """O'qituvchi matn yozsa, TTS mp3 yaratib savolga biriktiradi; tarmoqqa chiqilmaydi."""
    from app.services import tts_service as tts
    client, teacher_h, student_h, audio_dir = env

    real_synthesize = tts.synthesize

    async def fake_synth(text, voice=None, rate=tts.DEFAULT_RATE):
        return b"ID3fake-" + text.encode()
    monkeypatch.setattr(tts, "synthesize", fake_synth)

    r = client.get("/api/teacher/diagnostic/tts/voices", headers=teacher_h)
    assert r.status_code == 200 and any(v["id"] == tts.DEFAULT_VOICE for v in r.json()["voices"])

    r = client.post("/api/teacher/diagnostic/tts/preview", headers=teacher_h,
                    json={"text": "Listen carefully.", "voice": "en-GB-RyanNeural"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == b"ID3fake-Listen carefully."

    qid = client.post("/api/teacher/diagnostic/questions", headers=teacher_h,
                      json=_q(skill="listening", question="What time is it?")).json()["question"]["id"]
    r = client.post(f"/api/teacher/diagnostic/questions/{qid}/tts", headers=teacher_h,
                    json={"text": "It is half past nine.", "voice": None})
    assert r.status_code == 200, r.text
    q = r.json()["question"]
    assert q["is_audio"] is True and q["audio_url"].endswith(".mp3")
    assert q["audio_text"] == "It is half past nine." and q["audio_filename"].startswith("AI ovoz")
    first = os.path.join(audio_dir, os.path.basename(q["audio_url"]))
    assert os.path.isfile(first)

    # Talaba AI ovozini oddiy audio kabi ko'radi
    stu = client.get("/api/student/diagnostic/questions", headers=student_h).json()[0]
    assert stu["audio_url"] == q["audio_url"]

    # Qayta yaratilganda eski mp3 o'chadi
    r = client.post(f"/api/teacher/diagnostic/questions/{qid}/tts", headers=teacher_h, json={"text": "New text."})
    assert r.status_code == 200 and not os.path.exists(first)

    # Bo'sh matn va noma'lum ovoz rad etiladi (validatsiya sintezdan oldin)
    monkeypatch.setattr(tts, "synthesize", real_synthesize)  # asl funksiyani tiklash
    r = client.post(f"/api/teacher/diagnostic/questions/{qid}/tts", headers=teacher_h, json={"text": "   "})
    assert r.status_code == 502 and "bo'sh" in r.json()["detail"]
    r = client.post("/api/teacher/diagnostic/tts/preview", headers=teacher_h, json={"text": "x", "voice": "xx-YY-Nobody"})
    assert r.status_code == 502 and "Noma'lum ovoz" in r.json()["detail"]
