import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.core.security import create_access_token

client = TestClient(app)
API = settings.API_V1_STR

def test_talaba_registratsiyasi():
    # 1. Talaba registratsiyasi
    reg_data = {
        "email": "talaba_yangi_test@tilora.uz",
        "password": "password123!",
        "full_name": "Test Talaba Ali",
        "role": "student",
        "phone_number": "+998901234567",
        "group_name": "Test-301"
    }
    res = client.post(f"{API}/auth/register", json=reg_data)
    # Agar allaqachon mavjud bo'lsa yoki yangi bo'lsa
    if res.status_code == 400 and "allaqachon" in res.text:
        pass
    else:
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "pending_approval"
        assert data["user"]["role"] == "student"

    # Talaba tasdiqlanmaguncha login qila olmasligi tekshiruvi (403 Forbidden)
    login_res = client.post(f"{API}/auth/login", json={
        "email": "talaba_yangi_test@tilora.uz",
        "password": "password123!"
    })
    assert login_res.status_code == 403

def test_super_admin_oqituvchi_yaratish_va_kirish():
    admin_token = create_access_token({
        "id": "admin_uuid",
        "email": "admin@tilora.uz",
        "role": "admin",
        "full_name": "Super Admin"
    })
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Super Admin yangi o'qituvchi yaratadi
    create_payload = {
        "full_name": "Prof. Test O'qituvchi",
        "email": "oqituvchi_test_unique",
        "password": "teacherpass123",
        "phone_number": "+998971112233",
        "subject_name": "O'zbek tili va adabiyoti",
        "subscription_tier": "pro"
    }
    create_res = client.post(f"{API}/admin/teachers", json=create_payload, headers=headers)
    assert create_res.status_code == 200, create_res.text
    created_data = create_res.json()
    assert created_data["status"] == "success"
    teacher = created_data["teacher"]
    assert teacher["role"] == "teacher"
    assert teacher["is_approved"] is True
    assert teacher["subscription_tier"] == "pro"
    assert teacher["subject"]["name"] == "O'zbek tili va adabiyoti"
    teacher_id = teacher["id"]

    # 2. O'qituvchi tasdiq kutmasdan to'g'ridan-to'g'ri tizimga kira olishi tekshiruvi
    login_res = client.post(f"{API}/auth/login", json={
        "email": "oqituvchi_test_unique",
        "password": "teacherpass123"
    })
    assert login_res.status_code == 200, login_res.text
    auth_data = login_res.json()
    assert auth_data["user"]["role"] == "teacher"
    assert auth_data["user"]["is_approved"] is True

    # 3. Super Admin o'qituvchilar ro'yxatida ko'rishi
    teachers_list_res = client.get(f"{API}/admin/teachers", headers=headers)
    assert teachers_list_res.status_code == 200
    teachers_list = teachers_list_res.json()["teachers"]
    found = any(t["id"] == teacher_id for t in teachers_list)
    assert found is True

    # 4. Super Admin o'qituvchini o'chirish imkoniyati
    del_res = client.delete(f"{API}/admin/teachers/{teacher_id}", headers=headers)
    assert del_res.status_code == 200
