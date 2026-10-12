from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_student_get_subjects():
    res = client.get("/api/student/subjects")
    assert res.status_code == 200
    data = res.json()
    assert "subjects" in data
    assert isinstance(data["subjects"], list)

def test_student_get_materials():
    res = client.get("/api/student/materials")
    assert res.status_code == 200
    data = res.json()
    assert "materials" in data
    assert isinstance(data["materials"], list)

def test_student_submit_test():
    # Materiallar ro'yxatidan test turidagisini topish
    res = client.get("/api/student/materials?material_type=test")
    assert res.status_code == 200
    materials = res.json()["materials"]
    
    if len(materials) > 0:
        test_id = materials[0]["id"]
        # Material tafsilotini olish
        det_res = client.get(f"/api/student/materials/{test_id}")
        assert det_res.status_code == 200
        
        # Test topshirish
        sub_res = client.post(f"/api/student/materials/{test_id}/submit-test", json={
            "answers": {"q_1": 0}
        })
        assert sub_res.status_code == 200
        result = sub_res.json()
        assert "total_questions" in result
        assert "correct_answers" in result
        assert "score_percentage" in result
        assert "grade" in result
        assert "passed" in result
        assert "reviews" in result
