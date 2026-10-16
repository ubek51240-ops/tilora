"""PRO to'lov cheki: yuklash (egasi, pending), ko'rish (egasi/admin), o'chirish, format va hajm tekshiruvi, admin ro'yxati."""
import os

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.entities import User, SubscriptionPayment
from app.core.security import hash_password, create_access_token
from app.api import auth as auth_api

client = TestClient(app)
API = settings.API_V1_STR
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.4\n%fake\n" + b"0" * 32


def _mk_user(uid, email, role="student"):
    db = SessionLocal()
    try:
        db.query(SubscriptionPayment).filter(SubscriptionPayment.user_id == uid).delete()
        db.query(User).filter(User.id == uid).delete()
        db.query(User).filter(User.email == email).delete()
        db.add(User(id=uid, email=email, password_hash=hash_password("Parol12345"), full_name=f"Test {uid}", role=role,
                    is_approved=True, is_active=True, subscription_tier="free", subscription_status="active"))
        db.commit()
    finally:
        db.close()
    return {"Authorization": f"Bearer {create_access_token({'id': uid, 'email': email, 'role': role, 'full_name': uid})}"}


def _cleanup(uid):
    db = SessionLocal()
    try:
        for p in db.query(SubscriptionPayment).filter(SubscriptionPayment.user_id == uid).all():
            path = auth_api._receipt_path(p)
            if path and os.path.exists(path):
                os.remove(path)
        db.query(SubscriptionPayment).filter(SubscriptionPayment.user_id == uid).delete()
        db.query(User).filter(User.id == uid).delete()
        db.commit()
    finally:
        db.close()


def test_receipt_upload_view_delete_flow():
    owner = _mk_user("rcpt_owner_1", "rcpt_owner_1@tilora.uz")
    other = _mk_user("rcpt_other_1", "rcpt_other_1@tilora.uz")
    admin = _mk_user("rcpt_admin_1", "rcpt_admin_1@tilora.uz", role="admin")
    try:
        r = client.post(f"{API}/auth/subscribe", json={"plan": "pro", "payment_method": "click", "transaction_id": "123456"}, headers=owner)
        assert r.status_code == 200, r.text
        pid = r.json()["payment_id"]
        assert r.json()["receipt_upload_url"].endswith(f"/auth/subscribe/{pid}/receipt")

        # Chek yo'q -> 404
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=owner).status_code == 404
        st = client.get(f"{API}/auth/subscription-status", headers=owner).json()
        assert st["payments"][0]["has_receipt"] is False and st["payments"][0]["receipt_url"] is None

        # Noto'g'ri format (matn) -> 400, mijoz kengaytmasi .png bo'lsa ham
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek.png", b"hello world text", "image/png")})
        assert r.status_code == 400

        # PNG yuklash (egasi)
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek.png", PNG, "image/png")})
        assert r.status_code == 200, r.text
        assert r.json()["file_type"] == "image/png" and r.json()["receipt_url"].endswith(f"{pid}/receipt")
        path = os.path.join(auth_api.RECEIPTS_DIR, f"{pid}.png")
        assert os.path.exists(path)
        # Ommaviy /uploads orqali ochilmasligi kerak
        assert "uploads" + os.sep not in os.path.relpath(path, os.path.dirname(auth_api.RECEIPTS_DIR))

        # Ko'rish: egasi 200 (image/png), admin 200, begona 403, tokensiz 401
        r = client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=owner)
        assert r.status_code == 200 and r.headers["content-type"].startswith("image/png") and r.content == PNG
        assert "no-store" in r.headers.get("cache-control", "")
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=admin).status_code == 200
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=other).status_code == 403
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt").status_code == 401

        # Begona yuklay olmaydi
        assert client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=other, files={"file": ("x.jpg", JPG, "image/jpeg")}).status_code == 403

        # Almashtirish: PDF -> eski PNG o'chadi
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek.pdf", PDF, "application/pdf")})
        assert r.status_code == 200 and r.json()["file_type"] == "application/pdf"
        assert not os.path.exists(path) and os.path.exists(os.path.join(auth_api.RECEIPTS_DIR, f"{pid}.pdf"))
        r = client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=owner)
        assert r.headers["content-type"].startswith("application/pdf") and "inline" in r.headers["content-disposition"]

        # Holat va admin ro'yxatida chek belgisi
        st = client.get(f"{API}/auth/subscription-status", headers=owner).json()
        assert st["payments"][0]["has_receipt"] is True and st["payments"][0]["receipt_url"].endswith(f"{pid}/receipt")
        lst = client.get(f"{API}/admin/payments", headers=admin).json()["payments"]
        mine = next(p for p in lst if p["id"] == pid)
        assert mine["has_receipt"] is True and mine["receipt_url"].endswith(f"{pid}/receipt")

        # O'chirish (egasi), keyin 404
        assert client.delete(f"{API}/auth/subscribe/{pid}/receipt", headers=owner).status_code == 200
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=owner).status_code == 404

        # Tasdiqlangan arizaga chek yuklanmaydi
        client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek.jpg", JPG, "image/jpeg")})
        assert client.post(f"{API}/admin/payments/{pid}/approve", headers=admin).status_code == 200
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek2.jpg", JPG, "image/jpeg")})
        assert r.status_code == 400
        assert client.delete(f"{API}/auth/subscribe/{pid}/receipt", headers=owner).status_code == 400
        # Tasdiqlangan arizaning cheki admin uchun ko'rinaveradi
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=admin).status_code == 200
    finally:
        _cleanup("rcpt_owner_1"); _cleanup("rcpt_other_1"); _cleanup("rcpt_admin_1")


def test_receipt_size_limit_and_webp():
    owner = _mk_user("rcpt_owner_2", "rcpt_owner_2@tilora.uz")
    try:
        pid = client.post(f"{API}/auth/subscribe", json={"plan": "pro", "payment_method": "payme"}, headers=owner).json()["payment_id"]
        big = PNG + b"\x00" * (auth_api.RECEIPT_MAX_MB * 1024 * 1024)
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("big.png", big, "image/png")})
        assert r.status_code == 413
        webp = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPVP8 " + b"\x00" * 32
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("c.webp", webp, "image/webp")})
        assert r.status_code == 200 and r.json()["file_type"] == "image/webp"
        assert client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("e.png", b"", "image/png")}).status_code == 400
        assert client.get(f"{API}/auth/subscribe/does-not-exist/receipt", headers=owner).status_code == 404
    finally:
        _cleanup("rcpt_owner_2")
