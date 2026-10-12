import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)
teacher_token = create_access_token({'sub': 'teacher_1', 'role': 'teacher', 'username': 'nodira_ustoz'})
headers = {'Authorization': f'Bearer {teacher_token}'}

DOCX_PATH = r"C:\Users\HP\Downloads\Telegram Desktop\1_1_O'zbekistonning_eng_yangi_tarixi_O'EYT1204_fan_dasturi.docx"
PDF_PATH = r"C:\Users\HP\Downloads\Telegram Desktop\O'zbekistonning eng yangi tarixi dastur 1-kurs.pdf"


def test_yangi_tarixi_docx():
    if not os.path.exists(DOCX_PATH):
        pytest.skip("Test DOCX not found")

    with open(DOCX_PATH, "rb") as fp:
        res = client.post(
            "/api/teacher/parse-syllabus-file",
            headers=headers,
            files={"file": (os.path.basename(DOCX_PATH), fp, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert res.status_code == 200
    pdata = res.json()
    assert "tarixi" in pdata["subject_name"].lower()
    assert len(pdata["lecture_topics"]) >= 10
    assert len(pdata["seminar_topics"]) >= 10
    assert len(pdata["independent_topics"]) >= 10
    assert pdata["semester"] in ["1-semestr", "2-semestr"]
    assert "EYT" in pdata["subject_code"] or "1204" in pdata["subject_code"]


def test_camscanner_pdf():
    if not os.path.exists(PDF_PATH):
        pytest.skip("Test PDF not found")

    with open(PDF_PATH, "rb") as fp:
        res = client.post(
            "/api/teacher/parse-syllabus-file",
            headers=headers,
            files={"file": (os.path.basename(PDF_PATH), fp, "application/pdf")}
        )
    assert res.status_code == 200
    pdata = res.json()
    assert "tarixi" in pdata["subject_name"].lower()
    assert pdata["total_topics"] >= 10
    assert pdata["lecture_count"] >= 5
