from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.database import get_db
from app.models.entities import User, SubscriptionPayment, Institution, Group, TeacherSubject
from app.core.deps import require_role, get_current_user
from app.core.security import hash_password
from app.schemas.all_schemas import CreateTeacherRequest
from app.api.auth import validate_password_strength, validate_login_identifier, _receipt_path
from app.config import settings

router = APIRouter(prefix="/admin", tags=["Administrator"], dependencies=[Depends(require_role(["admin"]))])
from app.api.experiment_ext import retention_router  # noqa: E402
router.include_router(retention_router)

@router.get("/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    pending_users = db.query(User).filter(User.is_approved == False).count()
    students_count = db.query(User).filter(User.role == "student").count()
    teachers_count = db.query(User).filter(User.role == "teacher").count()
    pro_users_count = db.query(User).filter(User.subscription_tier == "pro").count()
    pending_payments = db.query(SubscriptionPayment).filter(SubscriptionPayment.status == "pending").count()

    return {
        "total_users": total_users,
        "pending_users_count": pending_users,
        "students_count": students_count,
        "teachers_count": teachers_count,
        "pro_users_count": pro_users_count,
        "pending_payments_count": pending_payments,
        "institutions": ["Buxoro davlat universiteti", "Nukus DPI", "SamDChTI"],
        "system_status": "healthy"
    }

# ============================================================
# 1. FOYDALANUVCHILARNI TASDIQLASH (APPROVAL QUEUE)
# ============================================================

@router.get("/pending-users")
def get_pending_users(db: Session = Depends(get_db)):
    """
    Ro'yxatdan o'tgan va Super Admin tasdiqlashini kutayotgan foydalanuvchilar.
    """
    users = db.query(User).filter(User.is_approved == False).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "phone_number": getattr(u, "phone_number", None) or "Mavjud emas",
            "subscription_tier": getattr(u, "subscription_tier", "free") or "free",
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
        })
    return {"pending_users": result, "total": len(result)}


@router.post("/users/{user_id}/approve")
def approve_user_registration(user_id: str, db: Session = Depends(get_db)):
    """
    Super Admin yangi ro'yxatdan o'tgan talaba yoki o'qituvchini tasdiqlaydi.
    Shundan so'ng u login va paroli bilan kira oladi.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    user.is_approved = True
    user.is_active = True
    db.commit()

    return {
        "status": "approved",
        "message": f"{user.full_name} ({user.role}) arizasi Super Admin tomonidan tasdiqlandi. Endi u tizimga kira oladi."
    }


@router.post("/users/{user_id}/reject")
def reject_user_registration(user_id: str, db: Session = Depends(get_db)):
    """
    Super Admin ro'yxatdan o'tgan nomaqbul hisobni rad etadi va o'chiradi.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Administrator hisobini rad etib bo'lmaydi.")

    full_name = user.full_name
    db.delete(user)
    db.commit()

    return {
        "status": "rejected",
        "message": f"{full_name} arizasi bekor qilindi va tizimdan o'chirildi."
    }


@router.get("/users")
def get_all_users(role: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Barcha ro'yxatdagi foydalanuvchilar (roli, tasdiq holati va obuna darajasi bilan).
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.order_by(User.created_at.desc()).all()

    result = []
    for u in users:
        result.append({
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_approved": getattr(u, "is_approved", True),
            "subscription_tier": getattr(u, "subscription_tier", "free") or "free",
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
        })
    return {"users": result, "total": len(result)}


@router.post("/users/{user_id}/set-tier")
def set_user_subscription_tier(
    user_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Admin tomonidan foydalanuvchini bevosita PRO yoki Free tarifiga o'tkazish.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    tier = payload.get("subscription_tier", "pro")
    if tier not in ["free", "pro"]:
        raise HTTPException(status_code=400, detail="Noto'g'ri tarif. Faqat 'free' yoki 'pro' mumkin.")

    user.subscription_tier = tier
    user.subscription_status = "active"
    db.commit()

    return {
        "status": "success",
        "message": f"{user.full_name} ning obunasi '{tier.upper()}' tarifiga o'tkazildi."
    }


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Super Admin istalgan foydalanuvchining (talaba yoki o'qituvchi) parolini yangilaydi.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    new_pwd = str(payload.get("password") or "").strip()
    validate_password_strength(new_pwd)

    user.password_hash = hash_password(new_pwd)
    # Tasdiqlanmagan bo'lsa avtomatik tasdiqlash
    user.is_approved = True
    user.is_active = True
    db.commit()

    # Yangi parol javobda qaytarilmaydi (loglar va brauzer tarixida qolmasligi uchun)
    return {
        "status": "success",
        "message": f"{user.full_name} ning paroli muvaffaqiyatli yangilandi.",
        "user_email": user.email
    }


# ============================================================
# 2. TO'LOVLAR VA PRO OBUNALAR (PAYMENTS & PRO UPGRADE)
# ============================================================

@router.get("/payments")
def get_subscription_payments(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Barcha to'lov arizalari (Super Admin tekshirishi va PRO faollashtirishi uchun).
    """
    query = db.query(SubscriptionPayment)
    if status_filter:
        query = query.filter(SubscriptionPayment.status == status_filter)
    payments = query.order_by(SubscriptionPayment.created_at.desc()).all()

    result = []
    for p in payments:
        result.append({
            "id": p.id,
            "user_id": p.user_id,
            "user_name": p.user_name,
            "user_email": p.user_email,
            "role": p.role,
            "plan": p.plan,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "transaction_id": p.transaction_id,
            "status": p.status,
            "user_note": getattr(p, "user_note", None),
            "admin_note": p.admin_note,
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            "approved_at": p.approved_at.strftime("%Y-%m-%d %H:%M") if p.approved_at else "",
            # Chek (foydalanuvchi yuklagan skrinshot/PDF) — admin /auth/subscribe/{id}/receipt orqali ko'radi
            "has_receipt": bool(_receipt_path(p)),
            "receipt_url": f"{settings.API_V1_STR}/auth/subscribe/{p.id}/receipt" if _receipt_path(p) else None,
        })
    return {"payments": result, "total": len(result)}


@router.post("/payments/{payment_id}/approve")
def approve_subscription_payment(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """
    Super Admin to'lovni tasdiqlaydi:
    To'lov holati 'approved' bo'ladi va foydalanuvchi 'pro' darajasiga o'tadi!
    """
    payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="To'lov arizasi topilmadi.")

    payment.status = "approved"
    payment.approved_at = datetime.utcnow()

    # Foydalanuvchini PRO tarifga o'tkazish
    user = db.query(User).filter(User.id == payment.user_id).first()
    if user:
        user.subscription_tier = "pro"
        user.subscription_status = "active"

    db.commit()

    return {
        "status": "approved",
        "message": f"{payment.user_name} ning {payment.amount:,} $ lik to'lovi tasdiqlandi va uning hisobi '👑 PRO' tarifiga o'tkazildi!"
    }


@router.post("/payments/{payment_id}/reject")
def reject_subscription_payment(
    payment_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Super Admin soxta yoki yetib kelmagan to'lovni rad etadi.
    Rad etish sababi (admin_note, kamida 3 belgi) MAJBURIY — foydalanuvchiga ko'rsatiladi.
    """
    payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="To'lov arizasi topilmadi.")
    note = str((payload or {}).get("admin_note") or "").strip()
    if len(note) < 3:
        raise HTTPException(status_code=400, detail="Rad etish sababini izohda yozing (kamida 3 belgi): foydalanuvchi shuni ko'radi.")
    if len(note) > 500:
        raise HTTPException(status_code=400, detail="Izoh 500 belgidan oshmasligi kerak.")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Faqat ko'rib chiqilayotgan (pending) ariza rad etiladi.")

    payment.status = "rejected"
    payment.admin_note = note

    user = db.query(User).filter(User.id == payment.user_id).first()
    if user and user.subscription_tier != "pro":
        user.subscription_status = "active"

    db.commit()

    return {
        "status": "rejected",
        "message": f"{payment.user_name} to'lov arizasi rad etildi."
    }


# ============================================================
# 3. O'QITUVCHILARNI BOSHQARISH VA YARATISH (TEACHER MANAGEMENT)
# ============================================================

@router.get("/teachers")
def get_all_teachers(db: Session = Depends(get_db)):
    """
    Super Admin uchun barcha o'qituvchilar ro'yxati va ularning fanlari.
    """
    teachers = db.query(User).filter(User.role == "teacher").order_by(User.created_at.desc()).all()
    result = []
    for t in teachers:
        subjects = db.query(TeacherSubject).filter(TeacherSubject.teacher_id == t.id).all()
        subj_list = [{"id": s.id, "name": s.name, "semester": s.semester} for s in subjects]
        result.append({
            "id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "phone_number": t.phone_number or "Ko'rsatilmagan",
            "subscription_tier": getattr(t, "subscription_tier", "pro") or "pro",
            "is_approved": getattr(t, "is_approved", True),
            "subjects": subj_list,
            "subjects_count": len(subj_list),
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
        })
    return {"teachers": result, "total": len(result)}


@router.post("/teachers")
def create_teacher(payload: CreateTeacherRequest, db: Session = Depends(get_db)):
    """
    Super Admin yangi o'qituvchi yaratadi.
    Yangi o'qituvchi avtomatik tasdiqlangan (is_approved=True) va 'pro' tarif bilan faollashadi.
    """
    email_clean = validate_login_identifier(payload.email)
    validate_password_strength(payload.password.strip())
    if payload.subscription_tier not in (None, "free", "pro"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tarif faqat 'free' yoki 'pro' bo'lishi mumkin.")

    # Email yoki login band emasligini tekshirish
    existing = db.query(User).filter(User.email == email_clean).first()
    if not existing and "@" not in email_clean:
        existing = db.query(User).filter(User.email == f"{email_clean}@tilora.uz").first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{payload.email}' login yoki emaili bilan foydalanuvchi allaqachon mavjud!"
        )

    # Yangi o'qituvchini yaratish
    new_teacher = User(
        email=email_clean,
        password_hash=hash_password(payload.password.strip()),
        full_name=payload.full_name.strip(),
        role="teacher",
        institution_id=payload.institution_id or "inst_buxdu",
        is_approved=True,  # Super admin yaratgani uchun to'g'ridan-to'g'ri faol
        is_active=True,
        subscription_tier=payload.subscription_tier or "pro",
        subscription_status="active",
        phone_number=payload.phone_number.strip() if payload.phone_number else None
    )
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)

    # Agar biriktirilgan fan nomi ko'rsatilgan bo'lsa, TeacherSubject jadvaliga ham qo'shamiz
    subject_created = None
    if payload.subject_name and payload.subject_name.strip():
        subj_name = payload.subject_name.strip()
        new_subj = TeacherSubject(
            teacher_id=new_teacher.id,
            name=subj_name,
            code="ENG-101",
            semester="5-semestr"
        )
        db.add(new_subj)
        db.commit()
        db.refresh(new_subj)
        subject_created = {"id": new_subj.id, "name": new_subj.name}

    return {
        "status": "success",
        "message": f"O'qituvchi {new_teacher.full_name} muvaffaqiyatli yaratildi va hisobi faollashtirildi.",
        "teacher": {
            "id": new_teacher.id,
            "full_name": new_teacher.full_name,
            "email": new_teacher.email,
            "role": "teacher",
            "phone_number": new_teacher.phone_number,
            "subscription_tier": new_teacher.subscription_tier,
            "is_approved": True,
            "subject": subject_created,
            "created_at": new_teacher.created_at.strftime("%Y-%m-%d %H:%M") if new_teacher.created_at else ""
        }
    }


@router.delete("/teachers/{teacher_id}")
def delete_teacher(teacher_id: str, db: Session = Depends(get_db)):
    """
    Super Admin o'qituvchi hisobini o'chiradi.
    """
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404, detail="O'qituvchi topilmadi.")

    full_name = teacher.full_name
    db.delete(teacher)
    db.commit()

    return {
        "status": "success",
        "message": f"O'qituvchi {full_name} hisobi muvaffaqiyatli o'chirildi."
    }


