"""PRO to'lov arizasi: chek + izoh MAJBURIY, chekni ko'rish/almashtirish, admin rad etishda izoh majburiy."""
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
NOTE = "Click orqali bugun 10 dollar o'tkazdim"


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


def _count(uid):
    db = SessionLocal()
    try:
        return db.query(SubscriptionPayment).filter(SubscriptionPayment.user_id == uid).count()
    finally:
        db.close()


def _subscribe(headers, file=("chek.png", PNG, "image/png"), note=NOTE, **extra):
    data = {"plan": "pro", "payment_method": "click", "transaction_id": "123456", "user_note": note, **extra}
    files = {"file": file} if file else None
    return client.post(f"{API}/auth/subscribe", headers=headers, data=data, files=files)


def test_chek_va_izoh_majburiy_bolmasa_ariza_yaratilmaydi():
    h = _mk_user("rcpt_req_1", "rcpt_req_1@tilora.uz")
    try:
        # Chek yo'q
        r = _subscribe(h, file=None)
        assert r.status_code == 400 and "chek" in r.json()["detail"].lower()
        # Izoh yo'q / juda qisqa / bo'sh joylardan iborat
        for bad in ("", "   ", "ok"):
            r = _subscribe(h, note=bad)
            assert r.status_code == 400 and "izoh" in r.json()["detail"].lower(), bad
        # Izoh juda uzun
        assert _subscribe(h, note="x" * 501).status_code == 400
        # Noto'g'ri format (matn, .png kengaytmasi bilan) va bo'sh fayl
        assert _subscribe(h, file=("chek.png", b"hello world text", "image/png")).status_code == 400
        assert _subscribe(h, file=("chek.png", b"", "image/png")).status_code == 400
        # Hajm
        big = PNG + b"\x00" * (auth_api.RECEIPT_MAX_MB * 1024 * 1024)
        assert _subscribe(h, file=("big.png", big, "image/png")).status_code == 413
        # Eski JSON usuli (chek/izohsiz) endi qabul qilinmaydi
        r = client.post(f"{API}/auth/subscribe", headers=h, json={"plan": "pro", "payment_method": "click"})
        assert r.status_code in (400, 422)
        # Hech qanday ariza yoki fayl qolmagan
        assert _count("rcpt_req_1") == 0
        # To'g'ri ariza o'tadi
        r = _subscribe(h)
        assert r.status_code == 200, r.text
        assert r.json()["has_receipt"] is True and r.json()["status"] == "pending"
        assert _count("rcpt_req_1") == 1
        st = client.get(f"{API}/auth/subscription-status", headers=h).json()
        assert st["subscription_status"] == "pending"
        assert st["payments"][0]["user_note"] == NOTE and st["payments"][0]["has_receipt"] is True
    finally:
        _cleanup("rcpt_req_1")


def test_chekni_korish_almashtirish_va_ruxsatlar():
    owner = _mk_user("rcpt_owner_1", "rcpt_owner_1@tilora.uz")
    other = _mk_user("rcpt_other_1", "rcpt_other_1@tilora.uz")
    admin = _mk_user("rcpt_admin_1", "rcpt_admin_1@tilora.uz", role="admin")
    try:
        r = _subscribe(owner)
        assert r.status_code == 200, r.text
        pid = r.json()["payment_id"]
        path = os.path.join(auth_api.RECEIPTS_DIR, f"{pid}.png")
        assert os.path.exists(path)

        # Ko'rish: egasi 200, admin 200, begona 403, tokensiz 401
        r = client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=owner)
        assert r.status_code == 200 and r.headers["content-type"].startswith("image/png") and r.content == PNG
        assert "no-store" in r.headers.get("cache-control", "")
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=admin).status_code == 200
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=other).status_code == 403
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt").status_code == 401

        # Begona almashtira olmaydi; egasi PDF bilan almashtiradi (eski PNG o'chadi)
        assert client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=other, files={"file": ("x.jpg", JPG, "image/jpeg")}).status_code == 403
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek.pdf", PDF, "application/pdf")})
        assert r.status_code == 200 and r.json()["file_type"] == "application/pdf"
        assert not os.path.exists(path) and os.path.exists(os.path.join(auth_api.RECEIPTS_DIR, f"{pid}.pdf"))
        # Chekni o'chirish endi mavjud emas (chek majburiy)
        assert client.delete(f"{API}/auth/subscribe/{pid}/receipt", headers=owner).status_code in (404, 405)

        # Admin ro'yxatida chek va foydalanuvchi izohi
        mine = next(p for p in client.get(f"{API}/admin/payments", headers=admin).json()["payments"] if p["id"] == pid)
        assert mine["has_receipt"] is True and mine["user_note"] == NOTE

        # Tasdiqlangan arizaga chek almashtirib bo'lmaydi
        assert client.post(f"{API}/admin/payments/{pid}/approve", headers=admin).status_code == 200
        r = client.post(f"{API}/auth/subscribe/{pid}/receipt", headers=owner, files={"file": ("chek2.jpg", JPG, "image/jpeg")})
        assert r.status_code == 400
        assert client.get(f"{API}/auth/subscribe/{pid}/receipt", headers=admin).status_code == 200
        assert client.get(f"{API}/auth/subscribe/does-not-exist/receipt", headers=owner).status_code == 404
    finally:
        _cleanup("rcpt_owner_1"); _cleanup("rcpt_other_1"); _cleanup("rcpt_admin_1")


def test_admin_rad_etishda_izoh_majburiy_va_foydalanuvchiga_korinadi():
    owner = _mk_user("rcpt_owner_3", "rcpt_owner_3@tilora.uz")
    admin = _mk_user("rcpt_admin_3", "rcpt_admin_3@tilora.uz", role="admin")
    try:
        pid = _subscribe(owner, file=("chek.jpg", JPG, "image/jpeg")).json()["payment_id"]
        url = f"{API}/admin/payments/{pid}/reject"
        # Izohsiz / bo'sh / qisqa / juda uzun — rad etilmaydi
        assert client.post(url, headers=admin).status_code == 400
        assert client.post(url, headers=admin, json={}).status_code == 400
        assert client.post(url, headers=admin, json={"admin_note": "   "}).status_code == 400
        assert client.post(url, headers=admin, json={"admin_note": "ab"}).status_code == 400
        assert client.post(url, headers=admin, json={"admin_note": "x" * 501}).status_code == 400
        assert client.get(f"{API}/auth/subscription-status", headers=owner).json()["payments"][0]["status"] == "pending"
        # Begona (talaba) rad eta olmaydi
        assert client.post(url, headers=owner, json={"admin_note": "sabab bor"}).status_code in (401, 403)
        # Izoh bilan rad etiladi
        reason = "Chekdagi summa 10 dollarga to'g'ri kelmaydi, aniqroq skrinshot yuboring"
        r = client.post(url, headers=admin, json={"admin_note": reason})
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        st = client.get(f"{API}/auth/subscription-status", headers=owner).json()
        assert st["payments"][0]["status"] == "rejected" and st["payments"][0]["admin_note"] == reason
        assert st["subscription_status"] == "active" and st["is_pro"] is False
        mine = next(p for p in client.get(f"{API}/admin/payments", headers=admin).json()["payments"] if p["id"] == pid)
        assert mine["admin_note"] == reason and mine["user_note"] == NOTE
        # Qayta rad etib bo'lmaydi; rad etilgandan keyin foydalanuvchi yangi ariza yubora oladi
        assert client.post(url, headers=admin, json={"admin_note": "yana sabab"}).status_code == 400
        assert _subscribe(owner).status_code == 200
    finally:
        _cleanup("rcpt_owner_3"); _cleanup("rcpt_admin_3")
