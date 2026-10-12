from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User
from app.schemas.all_schemas import LoginRequest, RegisterRequest, TokenResponse, SubscribeRequest, UpdateCredentialsRequest
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya"])

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    import re
    raw_ident = payload.email.strip()
    ident = raw_ident.lower()

    # 1. To'g'ridan-to'g'ri email bo'yicha qidirish
    user = db.query(User).filter(User.email == ident).first()

    # 2. Agar @ belgisi bo'lmasa, prefiks yoki @tilora.uz bo'yicha qidirish
    if not user and "@" not in ident:
        user = db.query(User).filter(User.email == f"{ident}@tilora.uz").first()
        if not user:
            # Masalan: "ubek51240" deb kiritilganda "ubek51240@gmail.com" ni topish
            user = db.query(User).filter(User.email.like(f"{ident}@%")).first()

    # 3. Telefon raqami bo'yicha qidirish (masalan: +998949593633 yoki 949593633)
    if not user:
        digits = re.sub(r"\D", "", raw_ident)
        if len(digits) >= 7:
            last9 = digits[-9:]
            user = db.query(User).filter(User.phone_number.like(f"%{last9}%")).first()

    # 4. Foydalanuvchi mavjudligini tekshirish
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bunday login, email yoki telefon raqamli foydalanuvchi topilmadi."
        )

    # 5. Parolni tekshirish
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kiritilgan parol noto'g'ri."
        )

    # 6. Super Admin tasdiqlaganlik tekshiruvi (Admin tasdiqlamasa kirish taqiqlanadi)
    is_approved = bool(getattr(user, "is_approved", True))
    if not is_approved and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizning hisobingiz hali Super Administrator tomonidan tasdiqlanmagan. Iltimos, admin arizangizni tasdiqlashini kuting!"
        )

    # 7. Hisob faolligini tekshirish
    is_active = bool(getattr(user, "is_active", True))
    if not is_active and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizning hisobingiz nofaol holatda. Administratorga murojaat qiling."
        )
    
    subscription_tier = getattr(user, "subscription_tier", "free") or "free"

    token = create_access_token({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "institution_id": user.institution_id,
        "group_id": user.group_id,
        "subscription_tier": subscription_tier,
        "is_approved": is_approved
    })
    
    group_name = None
    if user.group_id:
        from app.models.entities import Group
        grp = db.query(Group).filter(Group.id == user.group_id).first()
        if grp:
            group_name = grp.name
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "group_id": user.group_id,
            "group_name": group_name,
            "is_approved": is_approved,
            "subscription_tier": subscription_tier,
            "subscription_status": getattr(user, "subscription_status", "active") or "active"
        }
    }

@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    raw_ident = payload.email.strip()
    email_clean = raw_ident.lower()
    if not email_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login yoki email kiritilishi shart."
        )

    # 1. Email yoki login bo'yicha mavjudligini tekshirish
    existing = db.query(User).filter(User.email == email_clean).first()
    if not existing and "@" not in email_clean:
        # Agar oddiy login kiritilgan bo'lsa (masalan: nazira_safayeva), f"{login}@tilora.uz" ham tekshiriladi
        existing = db.query(User).filter(
            (User.email == f"{email_clean}@tilora.uz") | (User.email.like(f"{email_clean}@%"))
        ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"«{raw_ident}» logini / emaili bilan foydalanuvchi allaqachon ro'yxatdan o'tgan."
        )

    # 2. Agar telefon kiritilgan bo'lsa, telefon bo'yicha ham tekshirish
    import re
    phone_clean = payload.phone_number.strip() if payload.phone_number else None
    if phone_clean:
        phone_digits = re.sub(r"\D", "", phone_clean)
        if len(phone_digits) >= 9:
            last9 = phone_digits[-9:]
            existing_phone = db.query(User).filter(User.phone_number.like(f"%{last9}%")).first()
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"«{phone_clean}» telefon raqami allaqachon boshqa foydalanuvchiga biriktirilgan."
                )

    # Talabalar login sahifasida registratsiya qiladi (o'qituvchilar esa faqat Super Admin tomonidan yaratiladi)
    role = "student"

    # Guruhni aniqlash yoki yaratish
    group_id = payload.group_id
    if not group_id and payload.group_name and payload.group_name.strip():
        from app.models.entities import Group
        g_name = payload.group_name.strip()
        grp = db.query(Group).filter(Group.name == g_name).first()
        if not grp:
            grp = Group(
                name=g_name,
                institution_id=payload.institution_id or "inst_buxdu",
                course_year=3,
                experiment_arm="experimental"
            )
            db.add(grp)
            db.commit()
            db.refresh(grp)
        group_id = grp.id

    new_user = User(
        email=email_clean,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=role,
        institution_id=payload.institution_id or "inst_buxdu",
        group_id=group_id,
        is_approved=False,  # Super admin tasdiqlashi shart!
        subscription_tier="free",  # Boshlang'ich bepul tarif
        subscription_status="active",
        phone_number=payload.phone_number
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Talaba boshlang'ich profili
    from app.models.entities import StudentProfile
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

    plan = payload.plan or "pro"
    amount = payload.amount or 49000.0
    payment_method = payload.payment_method or "click"
    tx_id = payload.transaction_id or f"TX-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    from app.models.entities import SubscriptionPayment
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
    """
    Joriy foydalanuvchining obuna holati (Free yoki Pro).
    """
    user_id = current_user.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    from app.models.entities import SubscriptionPayment
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
    
    group_name = None
    if user.group_id:
        from app.models.entities import Group
        grp = db.query(Group).filter(Group.id == user.group_id).first()
        if grp:
            group_name = grp.name

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "phone_number": user.phone_number,
        "group_id": user.group_id,
        "group_name": group_name,
        "institution_id": user.institution_id,
        "subscription_tier": getattr(user, "subscription_tier", "free") or "free",
        "subscription_status": getattr(user, "subscription_status", "active") or "active",
        "is_approved": bool(getattr(user, "is_approved", True))
    }

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi."
        )

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
        if len(new_login) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yangi login kamida 3 ta belgidan iborat bo'lishi kerak."
            )
        # Boshqa foydalanuvchida bor-yo'qligini tekshirish
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
        if len(new_pass) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yangi parol kamida 4 ta belgidan iborat bo'lishi kerak."
            )
        user.password_hash = hash_password(new_pass)
        changes_made.append("parol")

    # 4. Ism-sharif (agar yuborilgan bo'lsa)
    if payload.full_name is not None and payload.full_name.strip() and payload.full_name.strip() != user.full_name:
        user.full_name = payload.full_name.strip()
        changes_made.append("ism-sharif")

    # 5. Telefon raqam (agar yuborilgan bo'lsa)
    if payload.phone_number is not None and payload.phone_number.strip() != (user.phone_number or ""):
        user.phone_number = payload.phone_number.strip()
        changes_made.append("telefon raqami")

    if not changes_made:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hech qanday o'zgarish kiritilmadi. Yangi login yoki yangi parol kiriting."
        )

    db.commit()
    db.refresh(user)

    # Yangi JWT token yaratish (yangi email/login bilan)
    subscription_tier = getattr(user, "subscription_tier", "free") or "free"
    is_approved = bool(getattr(user, "is_approved", True))
    token = create_access_token({
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "institution_id": user.institution_id,
        "group_id": user.group_id,
        "subscription_tier": subscription_tier,
        "is_approved": is_approved
    })

    group_name = None
    if user.group_id:
        from app.models.entities import Group
        grp = db.query(Group).filter(Group.id == user.group_id).first()
        if grp:
            group_name = grp.name

    summary = ", ".join(changes_made)
    return {
        "status": "success",
        "message": f"Sizning {summary} ma'lumotlaringiz muvaffaqiyatli o'zgartirildi!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "phone_number": user.phone_number,
            "group_id": user.group_id,
            "group_name": group_name,
            "is_approved": is_approved,
            "subscription_tier": subscription_tier,
            "subscription_status": getattr(user, "subscription_status", "active") or "active"
        }
    }

@router.post("/logout")
def logout():
    """Foydalanuvchi tizimdan chiqishi (sessiyani yakunlash)"""
    return {"message": "Tizimdan muvaffaqiyatli chiqildi", "status": "logged_out"}


