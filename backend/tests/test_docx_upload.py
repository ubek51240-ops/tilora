import os
import glob
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)
teacher_token = create_access_token({'sub': 'teacher_1', 'role': 'teacher', 'username': 'nodira_ustoz'})
headers = {'Authorization': f'Bearer {teacher_token}'}

def test_docx_parsing_and_upload():
    downloads_dir = r"C:\Users\HP\Downloads\Telegram Desktop"
    if not os.path.exists(downloads_dir):
        import pytest
        pytest.skip("Local Telegram Desktop test docx directory not found")

    target_file = None
    for f in os.listdir(downloads_dir):
        if "boshlang" in f.lower() and f.endswith(".docx"):
            target_file = os.path.join(downloads_dir, f)
            break

    if target_file is None:
        import pytest
        pytest.skip("Test docx file not found!")

    # 1. Parse syllabus file endpoint
    with open(target_file, "rb") as fp:
        res = client.post(
            "/api/teacher/parse-syllabus-file",
            headers=headers,
            files={"file": (os.path.basename(target_file), fp, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert res.status_code == 200
    pdata = res.json()
    assert pdata["subject_name"] == "Umumiy psixologiya"
    assert pdata["lecture_count"] == 30

    # 2. Create subject and upload docx directly
    sub_res = client.post("/api/teacher/subjects", headers=headers, json={
        "name": "Umumiy Psixologiya Test",
        "code": "TEST101",
        "semester": "1-semestr"
    })
    assert sub_res.status_code == 200
    subj_id = sub_res.json()["subject_id"]

    with open(target_file, "rb") as fp:
        up_res = client.post(
            f"/api/teacher/subjects/{subj_id}/upload-syllabus-file",
            headers=headers,
            files={"file": ("Dastur.docx", fp, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"category": "lecture"}
        )
    assert up_res.status_code == 200
    udata = up_res.json()
    assert udata["topics_count"] == 30

    # 3. Verify topics from database
    top_res = client.get(f"/api/teacher/subjects/{subj_id}/topics", headers=headers)
    assert top_res.status_code == 200
    topics = top_res.json()["topics"]
    assert len(topics) == 30

    # Clean up test subject
    del_res = client.delete(f"/api/teacher/subjects/{subj_id}", headers=headers)
    assert del_res.status_code == 200
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_docx_parsing_and_upload()
