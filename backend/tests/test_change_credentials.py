import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.entities import User
from app.core.security import hash_password, create_access_token

client = TestClient(app)
API = settings.API_V1_STR

def test_change_credentials_flow():
    db = SessionLocal()
    try:
        # Test uchun foydalanuvchi yaratamiz
        test_email = "test_user_cred_change@tilora.uz"
        db.query(User).filter(User.email == test_email).delete()
        db.commit()

        user = User(
            id="cred_test_user_id",
            email=test_email,
            password_hash=hash_password("oldpassword123"),
            full_name="Eski Ism",
            role="student",
            is_approved=True,
            is_active=True,
            subscription_tier="free"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    token = create_access_token({
        "id": "cred_test_user_id",
        "email": test_email,
        "role": "student",
        "full_name": "Eski Ism"
    })
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Noto'g'ri joriy parol kiritilganda xato berishi kerak
    res_wrong_pw = client.put(f"{API}/auth/change-credentials", json={
        "current_password": "wrong_password",
        "new_password": "newpassword456"
    }, headers=headers)
    assert res_wrong_pw.status_code == 400
    assert "noto'g'ri" in res_wrong_pw.json()["detail"].lower()

    # 2. To'g'ri joriy parol bilan login va parolni o'zgartirish
    new_login = "yangi_login_alisher"
    res_success = client.put(f"{API}/auth/change-credentials", json={
        "current_password": "oldpassword123",
        "new_login": new_login,
        "new_password": "newpassword456",
        "full_name": "Alisher Navoiy"
    }, headers=headers)
    assert res_success.status_code == 200, res_success.text
    data = res_success.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == new_login
    assert data["user"]["full_name"] == "Alisher Navoiy"
    new_token = data["access_token"]
    assert new_token is not None

    # 3. Yangi login va yangi parol bilan login qilib ko'rish
    login_res = client.post(f"{API}/auth/login", json={
        "email": new_login,
        "password": "newpassword456"
    })
    assert login_res.status_code == 200
    assert login_res.json()["user"]["email"] == new_login

    # 4. Eski parol bilan kirish imkoni yo'qligini tekshirish
    old_login_res = client.post(f"{API}/auth/login", json={
        "email": new_login,
        "password": "oldpassword123"
    })
    assert old_login_res.status_code == 401

    # Tozalash
    db2 = SessionLocal()
    try:
        db2.query(User).filter(User.id == "cred_test_user_id").delete()
        db2.commit()
    finally:
        db2.close()
