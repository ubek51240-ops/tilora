import re
import secrets
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import User, Institution, Group, StudentProfile, SubscriptionPayment
from app.schemas.all_schemas import LoginRequest, RegisterRequest, SubscribeRequest, UpdateCredentialsRequest
from app.core.security import hash_password, verify_password, create_access_token, needs_rehash
from app.core.deps import get_current_user
from app.core.ratelimit import SlidingWindowLimiter, client_ip

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya"])

# Brute-force himoyasi: IP va login bo'yicha alohida hisoblanadi
_login_ip_limiter = SlidingWindowLimiter(settings.LOGIN_MAX_ATTEMPTS * 3, settings.LOGIN_WINDOW_SECONDS)
_login_ident_limiter = SlidingWindowLimiter(settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_WINDOW_SECONDS)
_register_limiter = SlidingWindowLimiter(20, 3600)

_INVALID_CREDENTIALS = "Login (email/telefon) yoki parol noto'g'ri."
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_LOGIN_RE = re.compile(r"^[A-Za-z0-9._-]{3,64}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_password_strength(password: str) -> None:
    """Parol siyosati: kamida PASSWORD_MIN_LENGTH belgi, harf va raqam ishtiroki."""
    pwd = password or ""
    if len(pwd) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parol kamida {settings.PASSWORD_MIN_LENGTH} ta belgidan iborat bo'lishi kerak."
        )
    if len(pwd) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parol 128 belgidan oshmasligi kerak.")
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parolda kamida bitta harf va bitta raqam bo'lishi kerak (masalan: Talaba2026)."
        )
    weak = {"12345678", "password", "password1", "qwerty123", "tilora2026", "tilora2026!"}
    if pwd.lower() in weak:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bu parol juda keng tarqalgan. Boshqa parol tanlang.")


def validate_login_identifier(ident: str) -> str:
    """Login yoki email formatini tekshiradi va kichik harflarga keltiradi."""
    ident = (ident or "").strip().lower()
    if not ident:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login yoki email kiritilishi shart.")
    if "@" in ident:
        if not _EMAIL_RE.match(ident):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email manzili noto'g'ri formatda.")
    elif not _LOGIN_RE.match(ident):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login 3–64 ta belgidan iborat bo'lib, faqat lotin harflari, raqam, nuqta, chiziqcha va pastki chiziqdan tashkil topishi kerak."
        )
    return ident


def _user_public(user: User, group_name: Optional[str]) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "phone_number": user.phone_number,
        "group_id": user.group_id,
        "group_name": group_name,
        "institution_id": user.institution_id,
        "is_approved": bool(getattr(user, "is_approved", True)),
        "subscription_tier": getattr(user, "subscription_tier", "free") or "free",
        "subscription_status": getattr(user, "subscription_status", "active") or "active"
    }


def _group_name(db: Session, user: User) -> Optional[str]:
    if not user.group_id:
        return None
    grp = db.query(Group).filter(Group.id == user.group_id).first()
    return grp.name if grp else None


def _issue_token(user: User) -> str:
    return create_access_token({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "institution_id": user.institution_id,
        "group_id": user.group_id,
        "subscription_tier": getattr(user, "subscription_tier", "free") or "free",
        "is_approved": bool(getattr(user, "is_approved", True))
    })


def _find_user_by_identifier(db: Session, raw_ident: str) -> Optional[User]:
    ident = raw_ident.strip().lower()
    user = db.query(User).filter(User.email == ident).first()
    if not user and "@" not in ident and _LOGIN_RE.match(ident):
        user = db.query(User).filter(User.email == f"{ident}@tilora.uz").first()
        if not user:
            # Masalan: "ubek51240" deb kiritilganda "ubek51240@gmail.com" ni topish
            user = db.query(User).filter(User.email.like(f"{ident}@%")).first()
    if not user:
        digits = re.sub(r"\D", "", raw_ident)
        if len(digits) >= 9:
            last9 = digits[-9:]
            user = db.query(User).filter(User.phone_number.like(f"%{last9}%")).first()
    return user


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    raw_ident = (payload.email or "").strip()[:255]
    ip = client_ip(request)
    ident_key = f"login:{raw_ident.lower()}"
    ip_key = f"login_ip:{ip}"

    for limiter, key in ((_login_ip_limiter, ip_key), (_login_ident_limiter, ident_key)):
        limited, retry = limiter.is_limited(key)
        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Juda ko'p noto'g'ri urinish. {max(1, retry // 60)} daqiqadan so'ng qayta urinib ko'ring.",
                headers={"Retry-After": str(retry)},
            )

    user = _find_user_by_identifier(db, raw_ident) if raw_ident else None

    # Foydalanuvchi mavjudligi va parol xatosi bir xil xabar bilan qaytariladi (enumeration himoyasi)
    if not user or not verify_password(payload.password or "", user.password_hash):
        _login_ip_limiter.record(ip_key)
        _login_ident_limiter.record(ident_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS)

    # Super Admin tasdiqlaganlik tekshiruvi (Admin tasdiqlamasa kirish taqiqlanadi)
    is_approved = bool(getattr(user, "is_approved", True))
    if not is_approved and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizning hisobingiz hali Super Administrator tomonidan tasdiqlanmagan. Iltimos, admin arizangizni tasdiqlashini kuting!"
        )

    is_active = bool(getattr(user, "is_active", True))
    if not is_active and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizning hisobingiz nofaol holatda. Administratorga murojaat qiling."
        )

    # Eski (statik tuzli) xeshni yangi, foydalanuvchiga xos tuzli formatga ko'chirish
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    # Saqlash muddati (retention) uchun oxirgi kirish vaqti
    try:
        user.last_login_at = _utcnow()
    except Exception:
        pass
    db.commit()

    _login_ident_limiter.reset(ident_key)

    return {
        "access_token": _issue_token(user),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _user_public(user, _group_name(db, user))
    }


@router.post("/register")
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    _register_limiter.check_and_record(
        f"register:{client_ip(request)}",
        "Ro'yxatdan o'tish urinishlari ko'payib ketdi. Biroz vaqtdan so'ng qayta urinib ko'ring."
    )

    raw_ident = (payload.email or "").strip()
    email_clean = validate_login_identifier(raw_ident)
    validate_password_strength(payload.password)

    full_name = (payload.full_name or "").strip()
    if len(full_name) < 3 or len(full_name) > 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ism-sharif 3–120 belgi oralig'ida bo'lishi kerak.")

    # 1. Email yoki login bo'yicha mavjudligini tekshirish
    existing = db.query(User).filter(User.email == email_clean).first()
    if not existing and "@" not in email_clean:
        existing = db.query(User).filter(
            (User.email == f"{email_clean}@tilora.uz") | (User.email.like(f"{email_clean}@%"))
        ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"«{raw_ident}» logini / emaili bilan foydalanuvchi allaqachon ro'yxatdan o'tgan."
        )

    # 2. Agar telefon kiritilgan bo'lsa, telefon bo'yicha ham tekshirish
    phone_clean = payload.phone_number.strip()[:30] if payload.phone_number else None
    if phone_clean:
        phone_digits = re.sub(r"\D", "", phone_clean)
        if len(phone_digits) < 9 or len(phone_digits) > 15:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefon raqami noto'g'ri formatda (masalan: +998901234567).")
        last9 = phone_digits[-9:]
        existing_phone = db.query(User).filter(User.phone_number.like(f"%{last9}%")).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"«{phone_clean}» telefon raqami allaqachon boshqa foydalanuvchiga biriktirilgan."
            )

    # Talabalar login sahifasida registratsiya qiladi (o'qituvchilar esa faqat Super Admin tomonidan yaratiladi).
    # payload.role e'tiborga olinmaydi — rolni foydalanuvchi o'zi tanlay olmaydi.
    role = "student"

    # Muassasa: faqat mavjud OTM qabul qilinadi, aks holda standart
    institution_id = payload.institution_id or "inst_buxdu"
    if not db.query(Institution).filter(Institution.id == institution_id).first():
        institution_id = "inst_buxdu" if db.query(Institution).filter(Institution.id == "inst_buxdu").first() else None

    # Guruhni aniqlash yoki yaratish
    group_id = None
    if payload.group_id and db.query(Group).filter(Group.id == payload.group_id).first():
        group_id = payload.group_id
    elif payload.group_name and payload.group_name.strip():
        g_name = payload.group_name.strip()[:50]
        grp = db.query(Group).filter(Group.name == g_name).first()
        if not grp:
            grp = Group(name=g_name, institution_id=institution_id, course_year=3, experiment_arm="experimental")
            db.add(grp)
            db.commit()
            db.refresh(grp)
        group_id = grp.id

    new_user = User(
        email=email_clean,
        password_hash=hash_password(payload.password),
        full_name=full_name,
        role=role,
        institution_id=institution_id,
        group_id=group_id,
        is_approved=False,  # Super admin tasdiqlashi shart!
        subscription_tier="free",
        subscription_status="active",
        phone_number=phone_clean
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Talaba boshlang'ich profili
    prof = StudentProfile(
        student_id=new_user.id,
        cefr_listening="B1",
        cefr_reading="B2",
        cefr_speaking="A2",
        cefr_writing="B1",
        load_capacity=50,
        pace_index=50,
        anxiety_level=60,
        autonomy_readiness=40,
        source="initial_registration"
    )
    db.add(prof)
    db.commit()

    return {
        "status": "pending_approval",
        "message": f"Hurmatli {new_user.full_name}, ro'yxatdan o'tish arizangiz qabul qilindi! Super administrator tasdiqlaganidan so'ng tizimga login va parolingiz bilan kira olasiz.",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_approved": False,
            "subscription_tier": "free"
        }
    }


@router.post("/subscribe")
def create_subscription_request(
    payload: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Foydalanuvchi PRO obuna uchun to'lov arizasi topshiradi (Click, Payme, Karta).
    Admin tasdiqlagach PRO tarif faollashadi.
    """
    user_id = current_user.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    # Bir foydalanuvchida ko'p sonli kutilayotgan arizalar yig'ilib qolmasin
    pending_count = db.query(SubscriptionPayment).filter(
        SubscriptionPayment.user_id == user.id, SubscriptionPayment.status == "pending"
    ).count()
    if pending_count >= 3:
        raise HTTPException(status_code=400, detail="Sizda allaqachon ko'rib chiqilayotgan to'lov arizalari bor. Admin tasdig'ini kuting.")

    plan = (payload.plan or "pro")[:50]
    if plan not in ("pro", "pro_monthly", "pro_annual"):
        plan = "pro_monthly"
    payment_method = (payload.payment_method or "click")[:50]
    if payment_method not in ("click", "payme", "card", "uzum"):
        payment_method = "click"
    amount = 49000.0 if plan != "pro_annual" else 490000.0  # Summa serverda belgilanadi, mijoz o'zgartira olmaydi
    tx_raw = (payload.transaction_id or "").strip()[:100]
    tx_id = tx_raw or f"TX-{_utcnow().strftime('%Y%m%d%H%M%S')}"

    payment = SubscriptionPayment(
        user_id=user.id,
        user_name=user.full_name,
        user_email=user.email,
        role=user.role,
        plan=plan,
        amount=amount,
        payment_method=payment_method,
        transaction_id=tx_id,
        status="pending"
    )
    db.add(payment)
    user.subscription_status = "pending"
    db.commit()
    db.refresh(payment)

    return {
        "status": "pending",
        "message": "To'lov arizangiz qabul qilindi! Super Administrator to'lovni tekshirib tasdiqlagach, PRO profilingiz avtomatik ishga tushadi.",
        "payment_id": payment.id,
        "amount": amount,
        "plan": plan
    }


@router.get("/subscription-status")
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Joriy foydalanuvchining obuna holati (Free yoki Pro)."""
    user_id = current_user.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    recent_payments = db.query(SubscriptionPayment).filter(
        SubscriptionPayment.user_id == user_id
    ).order_by(SubscriptionPayment.created_at.desc()).limit(5).all()

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "subscription_tier": getattr(user, "subscription_tier", "free") or "free",
        "subscription_status": getattr(user, "subscription_status", "active") or "active",
        "is_pro": (getattr(user, "subscription_tier", "free") == "pro"),
        "payments": [
            {
                "id": p.id,
                "plan": p.plan,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "status": p.status,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else ""
            }
            for p in recent_payments
        ]
    }


@router.get("/me")
def get_me(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return current_user
    return _user_public(user, _group_name(db, user))


@router.put("/change-credentials")
@router.post("/change-credentials")
def change_credentials(
    payload: UpdateCredentialsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Foydalanuvchi o'z loginini va/yoki parolini o'zgartiradi.
    Xavfsizlik uchun amaldagi parol (current_password) tekshiriladi.
    """
    user_id = current_user.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")

    # 1. Amaldagi parolni tekshirish (majburiy)
    if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amaldagi parolingiz noto'g'ri kiritildi! Iltimos, joriy parolingizni tekshirib qayta kiriting."
        )

    changes_made = []

    # 2. Yangi login tekshiruvi va o'zgartirish
    new_login = (payload.new_login or "").strip().lower()
    if new_login and new_login != user.email.lower():
        new_login = validate_login_identifier(new_login)
        existing = db.query(User).filter(
            User.id != user.id,
            (User.email == new_login) |
            (User.email == f"{new_login}@tilora.uz") |
            (User.email.like(f"{new_login}@%"))
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"«{payload.new_login.strip()}» logini allaqachon boshqa foydalanuvchi tomonidan band qilingan. Boshqa login tanlang."
            )
        user.email = new_login
        changes_made.append("login")

    # 3. Yangi parol tekshiruvi va o'zgartirish
    new_pass = (payload.new_password or "").strip()
    if new_pass:
        validate_password_strength(new_pass)
        if verify_password(new_pass, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Yangi parol joriy paroldan farq qilishi kerak.")
        user.password_hash = hash_password(new_pass)
        changes_made.append("parol")

    # 4. Ism-sharif (agar yuborilgan bo'lsa)
    if payload.full_name is not None and payload.full_name.strip() and payload.full_name.strip() != user.full_name:
        user.full_name = payload.full_name.strip()[:120]
        changes_made.append("ism-sharif")

    # 5. Telefon raqam (agar yuborilgan bo'lsa)
    if payload.phone_number is not None and payload.phone_number.strip() != (user.phone_number or ""):
        user.phone_number = payload.phone_number.strip()[:30]
        changes_made.append("telefon raqami")

    if not changes_made:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hech qanday o'zgarish kiritilmadi. Yangi login yoki yangi parol kiriting."
        )

    db.commit()
    db.refresh(user)

    summary = ", ".join(changes_made)
    return {
        "status": "success",
        "message": f"Sizning {summary} ma'lumotlaringiz muvaffaqiyatli o'zgartirildi!",
        "access_token": _issue_token(user),
        "token_type": "bearer",
        "user": _user_public(user, _group_name(db, user))
    }


class DeleteMeRequest(BaseModel):
    password: str
    confirm: str = Field(..., pattern="^O'CHIRISH$")


@router.delete("/me")
def delete_my_data(payload: DeleteMeRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Ma'lumotlar himoyasi (3.1-jadval: "to'planadigan ma'lumot zaruriy hajmdan oshmasligi", talaba avtonomiyasi):
    foydalanuvchi o'z hisobini o'chiradi. Shaxsiy identifikatorlar anonimlashtiriladi (ism, email, telefon, matnlar),
    ilmiy statistika uchun faqat ID-ga bog'liq raqamli natijalar saqlanadi (O'RQ-547 ga muvofiq).
    """
    from app.models.entities import LessonRecord, ApiKey
    uid = current_user.get("id")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Administrator hisobini bu yo'l bilan o'chirib bo'lmaydi.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Parol noto'g'ri.")
    short = uid[:8]
    user.email = f"deleted_{short}@anon.tilora"
    user.full_name = "O'chirilgan foydalanuvchi"
    user.phone_number = None
    user.is_active = False
    user.password_hash = hash_password(secrets.token_urlsafe(24))
    for r in db.query(LessonRecord).filter(LessonRecord.student_id == uid).all():
        r.production_text = None; r.drafts = None; r.plan_goal = None; r.plan_strategy = None
        r.gap_explanation = None; r.next_goal = None; r.comparison_note = None; r.feedback_decisions = None
    db.query(ApiKey).filter(ApiKey.user_id == uid).delete()
    db.commit()
    return {"status": "deleted", "message": "Hisobingiz o'chirildi: shaxsiy ma'lumotlar va matnlar anonimlashtirildi; faqat ID-ga bog'liq raqamli natijalar ilmiy statistika uchun saqlanadi."}


@router.post("/logout")
def logout():
    """Foydalanuvchi tizimdan chiqishi (sessiyani yakunlash). Token mijoz tomonida o'chiriladi."""
    return {"message": "Tizimdan muvaffaqiyatli chiqildi", "status": "logged_out"}
