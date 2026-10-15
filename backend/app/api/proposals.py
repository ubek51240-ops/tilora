from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.entities import TeacherProposal, User, Group
from app.core.deps import get_current_user

router = APIRouter(prefix="/proposals", tags=["Takliflar va Pedagogik Muloqot"])

class ProposalCreateRequest(BaseModel):
    receiver_id: str = Field(..., min_length=1, max_length=64)
    receiver_role: Optional[str] = "teacher"  # teacher | student | all
    direction: Optional[str] = None  # teacher_to_teacher, student_to_teacher, student_to_student, teacher_to_student
    proposal_type: str = Field("general", pattern="^(methodology|assignment|scaffolding|peer_learning|general)$")
    title: str = Field(..., min_length=3, max_length=200)
    proposal_text: str = Field(..., min_length=5, max_length=5000)
    basis: Optional[str] = Field("", max_length=2000)

class ProposalActionRequest(BaseModel):
    teacher_comment: Optional[str] = None


CATEGORY_LABELS = {
    "methodology": "📚 Metodika va Sillabus",
    "assignment": "✍️ Topshiriq va Baholash",
    "scaffolding": "🎯 Skaffolding va Yordam",
    "peer_learning": "👥 Tengdoshlararo Hamkorlik (Peer Learning)",
    "general": "💡 Umumiy Fikr-Mulohaza",
    "scaffold_change": "🎯 Skaffolding o'zgarishi (AI)",
    "difficulty_change": "📈 Murakkablik o'zgarishi (AI)",
    "deadline_change": "⏱️ Muddat o'zgarishi (AI)"
}

DIRECTION_LABELS = {
    "teacher_to_teacher": "👨‍🏫 O'qituvchidan ➔ 👨‍🏫 O'qituvchiga",
    "student_to_teacher": "👨‍🎓 Talabadan ➔ 👨‍🏫 O'qituvchiga",
    "student_to_student": "👨‍🎓 Talabadan ➔ 👨‍🎓 Talabaga",
    "teacher_to_student": "👨‍🏫 O'qituvchidan ➔ 👨‍🎓 Talabaga",
    "system": "🤖 Tizim (AI) ➔ 👨‍🏫 O'qituvchiga"
}


def _format_proposal(p: TeacherProposal, db: Session) -> dict:
    pc = p.proposed_change or {}
    
    sender_name = pc.get("sender_name")
    sender_role = pc.get("sender_role")
    if not sender_name and p.sender_id:
        u = db.query(User).filter(User.id == p.sender_id).first()
        if u:
            sender_name = u.full_name
            sender_role = u.role
            
    receiver_name = pc.get("receiver_name")
    receiver_role = pc.get("receiver_role")
    if not receiver_name and p.receiver_id:
        if p.receiver_id == "all_teachers":
            receiver_name = "Barcha o'qituvchilar"
            receiver_role = "teacher"
        elif p.receiver_id == "all_students":
            receiver_name = "Barcha talabalar"
            receiver_role = "student"
        else:
            u = db.query(User).filter(User.id == p.receiver_id).first()
            if u:
                receiver_name = u.full_name
                receiver_role = u.role

    # Agar sender yo'q bo'lsa va bu tizim taklifi bo'lsa
    if not sender_name:
        sender_name = "TILORA AI Tizimi"
        sender_role = "system"

    # Agar receiver yo'q bo'lsa
    if not receiver_name:
        if p.teacher_id:
            t = db.query(User).filter(User.id == p.teacher_id).first()
            receiver_name = t.full_name if t else "O'qituvchi"
            receiver_role = "teacher"
        else:
            receiver_name = "O'qituvchi"
            receiver_role = "teacher"

    direction = pc.get("direction")
    if not direction:
        if sender_role == "system":
            direction = "system"
        elif sender_role and receiver_role:
            direction = f"{sender_role}_to_{receiver_role}"
        else:
            direction = "system"

    title = pc.get("title") or (f"{pc.get('student_name', 'Talaba')} bo'yicha tavsiya" if pc.get("student_name") else "Taklif")
    text = pc.get("text") or pc.get("proposal_text") or ""
    cat = pc.get("category") or p.proposal_type or "general"

    return {
        "id": p.id,
        "title": title,
        "proposal_text": text,
        "proposal_type": cat,
        "proposal_type_label": CATEGORY_LABELS.get(cat, cat),
        "direction": direction,
        "direction_label": DIRECTION_LABELS.get(direction, direction),
        "sender_id": p.sender_id,
        "sender_name": sender_name,
        "sender_role": sender_role or "user",
        "receiver_id": p.receiver_id or p.teacher_id,
        "receiver_name": receiver_name,
        "receiver_role": receiver_role or "teacher",
        "student_id": p.student_id,
        "student_name": pc.get("student_name", ""),
        "teacher_id": p.teacher_id,
        "basis": p.basis or "",
        "status": p.status or "pending",
        "teacher_comment": p.teacher_comment or "",
        "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
        "decided_at": p.decided_at.strftime("%Y-%m-%d %H:%M") if p.decided_at else None,
    }


# ============================================================
# 1. QABUL QILUVCHILAR RO'YXATI (RECIPIENTS LIST)
# ============================================================
@router.get("/recipients")
def get_recipients(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Taklif yuborish uchun o'qituvchilar va talabalar ro'yxati.
    Bazada yangi ro'yxatdan o'tgan yoki qo'shilgan har qanday o'qituvchi/talaba shu zahoti chiqadi.
    """
    user_id = current_user.get("id") or current_user.get("sub")

    teachers = db.query(User).filter(User.role.in_(["teacher", "admin"])).order_by(User.full_name).all()
    students = db.query(User).filter(User.role == "student").order_by(User.full_name).all()
    groups_map = {g.id: g.name for g in db.query(Group).all()}

    teachers_list = [
        {
            "id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "role": t.role,
            "role_label": "O'qituvchi" if t.role == "teacher" else "Administrator",
            "is_me": (t.id == user_id)
        }
        for t in teachers
    ]

    students_list = [
        {
            "id": s.id,
            "full_name": s.full_name,
            "email": s.email,
            "role": "student",
            "role_label": "Talaba",
            "group_name": groups_map.get(s.group_id, "302-guruh (EFL)"),
            "is_me": (s.id == user_id)
        }
        for s in students
    ]

    return {
        "teachers": teachers_list,
        "students": students_list,
        "current_user": {
            "id": user_id,
            "full_name": current_user.get("full_name") or "Foydalanuvchi",
            "role": current_user.get("role") or "student"
        }
    }


# ============================================================
# 2. TAKLIFLAR RO'YXATI (PROPOSALS LIST WITH ADVANCED FILTERING)
# ============================================================
@router.get("")
def list_proposals(
    tab: Optional[str] = "all",         # all | inbox | sent | system
    status_filter: Optional[str] = "all",# all | pending | approved | rejected | modified
    direction_filter: Optional[str] = "all", # all | teacher_to_teacher | student_to_teacher | student_to_student | teacher_to_student | system
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Foydalanuvchi uchun tegishli takliflar ro'yxati:
    - O'qituvchi: o'ziga kelgan, o'zi yuborgan, talabalaridan kelgan va tizim takliflari.
    - Talaba: o'qituvchilariga yuborgan, o'ziga kelgan, guruhdoshlari bilan takliflar.
    - Admin: barcha takliflar.
    """
    user_id = current_user.get("id") or current_user.get("sub")
    user_role = current_user.get("role") or "student"

    all_props = db.query(TeacherProposal).order_by(TeacherProposal.created_at.desc(), TeacherProposal.id.desc()).all()
    formatted = [_format_proposal(p, db) for p in all_props]

    # Rolga mos dastlabki filtratsiya
    visible = []
    for item in formatted:
        is_sender = (item["sender_id"] == user_id)
        is_receiver = (
            item.get("receiver_id") == user_id or
            (item.get("teacher_id") == user_id and user_role in ["teacher", "admin"]) or
            (item.get("student_id") == user_id and user_role == "student" and item["direction"] != "system") or
            (item.get("receiver_id") == "all_teachers" and user_role in ["teacher", "admin"]) or
            (item.get("receiver_id") == "all_students" and user_role == "student")
        )
        is_system_for_me = (
            item["direction"] == "system" and (
                (user_role in ["teacher", "admin"]) or
                (user_role == "student" and item.get("student_id") == user_id)
            )
        )

        if user_role == "admin" or is_sender or is_receiver or is_system_for_me:
            # Tab belgilash
            if is_sender:
                item["relation"] = "sent"
            elif is_system_for_me:
                item["relation"] = "system"
            else:
                item["relation"] = "inbox"
            visible.append(item)

    # Tab bo'yicha saralash
    if tab == "inbox":
        filtered = [x for x in visible if x["relation"] == "inbox"]
    elif tab == "sent":
        filtered = [x for x in visible if x["relation"] == "sent"]
    elif tab == "system":
        filtered = [x for x in visible if x["relation"] == "system"]
    else:
        filtered = visible

    # Holat (status) bo'yicha saralash
    if status_filter and status_filter != "all":
        filtered = [x for x in filtered if x["status"] == status_filter]

    # Yo'nalish (direction) bo'yicha saralash
    if direction_filter and direction_filter != "all":
        filtered = [x for x in filtered if x["direction"] == direction_filter]

    # Tartib: pending birinchi
    filtered.sort(key=lambda r: (0 if r["status"] == "pending" else 1, r.get("created_at") or ""))

    counts = {
        "all": len(visible),
        "inbox": sum(1 for x in visible if x["relation"] == "inbox"),
        "sent": sum(1 for x in visible if x["relation"] == "sent"),
        "system": sum(1 for x in visible if x["relation"] == "system"),
        "pending": sum(1 for x in visible if x["status"] == "pending")
    }

    return {
        "proposals": filtered,
        "counts": counts,
        "current_user_role": user_role,
        "rule_note": "3-Qoida: Yakuniy qaror har doim inson (o'qituvchi / qabul qiluvchi) ixtiyorida."
    }


# ============================================================
# 3. YANGI TAKLIF YUBORISH (CREATE PROPOSAL)
# ============================================================
@router.post("")
def create_proposal(
    req: ProposalCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    O'qituvchi yoki talaba tomonidan boshqa o'qituvchiga yoki talabaga taklif yuborish.
    O'qituvchilar o'zaro, talabalar o'qituvchilarga, talabalar o'zaro, o'qituvchilar talabalarga.
    """
    sender_id = current_user.get("id") or current_user.get("sub")
    sender_obj = db.query(User).filter(User.id == sender_id).first()
    sender_name = sender_obj.full_name if sender_obj else current_user.get("full_name", "Foydalanuvchi")
    sender_role = sender_obj.role if sender_obj else current_user.get("role", "student")

    receiver_id = req.receiver_id
    receiver_name = "Barcha o'qituvchilar"
    receiver_role = req.receiver_role or "teacher"

    if receiver_id == "all_teachers":
        receiver_name = "Barcha o'qituvchilar"
        receiver_role = "teacher"
    elif receiver_id == "all_students":
        receiver_name = "Barcha talabalar"
        receiver_role = "student"
    else:
        rec_obj = db.query(User).filter(User.id == receiver_id).first()
        if not rec_obj:
            raise HTTPException(status_code=404, detail="Qabul qiluvchi foydalanuvchi topilmadi.")
        receiver_name = rec_obj.full_name
        receiver_role = rec_obj.role

    # Yo'nalish serverda aniqlanadi (mijoz soxta yo'nalish yubora olmaydi)
    direction = f"{sender_role}_to_{receiver_role}"
    if direction not in DIRECTION_LABELS:
        direction = req.direction if req.direction in DIRECTION_LABELS else f"{sender_role}_to_{receiver_role}"

    # student_id va teacher_id ni moslash (mavjud jadval bilan to'liq mos bo'lishi uchun)
    st_id = sender_id if sender_role == "student" else (receiver_id if receiver_role == "student" and receiver_id not in ["all_teachers", "all_students"] else sender_id)
    tc_id = receiver_id if receiver_role in ["teacher", "admin"] and receiver_id not in ["all_teachers", "all_students"] else (sender_id if sender_role in ["teacher", "admin"] else sender_id)

    proposed_change = {
        "title": req.title.strip(),
        "text": req.proposal_text.strip(),
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_role": sender_role,
        "receiver_id": receiver_id,
        "receiver_name": receiver_name,
        "receiver_role": receiver_role,
        "direction": direction,
        "category": req.proposal_type
    }

    new_p = TeacherProposal(
        student_id=st_id,
        teacher_id=tc_id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        proposal_type=req.proposal_type,
        proposed_change=proposed_change,
        basis=req.basis.strip() if req.basis else f"{sender_name} tomonidan kiritilgan taklif.",
        status="pending",
        created_at=datetime.utcnow()
    )

    db.add(new_p)
    db.commit()
    db.refresh(new_p)

    return {
        "status": "success",
        "message": f"Taklifingiz muvaffaqiyatli yuborildi ({receiver_name}ga).",
        "proposal": _format_proposal(new_p, db)
    }


# ============================================================
# 4. TAKLIFNI QABUL QILISH / O'ZGARTIRISH / RAD ETISH
# ============================================================
def _handle_decision(db: Session, prop_id: str, new_status: str, current_user: dict, comment: Optional[str] = None):
    user_id = current_user.get("id") or current_user.get("sub")
    user_role = current_user.get("role") or "student"

    p = db.query(TeacherProposal).filter(TeacherProposal.id == prop_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Taklif topilmadi.")

    # Qaror qabul qilish huquqini tekshirish:
    # Admin, qabul qiluvchi shaxs (receiver_id) yoki o'qituvchi bo'lsa
    can_decide = (
        user_role == "admin" or
        p.receiver_id == user_id or
        p.teacher_id == user_id or
        (p.receiver_id == "all_teachers" and user_role in ["teacher", "admin"]) or
        (p.receiver_id == "all_students" and user_role == "student")
    )
    if not can_decide:
        raise HTTPException(status_code=403, detail="Siz bu taklif bo'yicha qaror qabul qilish huquqiga ega emassiz.")

    p.status = new_status
    p.decided_at = None if new_status == "pending" else datetime.utcnow()
    if comment is not None:
        p.teacher_comment = comment.strip()[:2000]

    db.commit()
    db.refresh(p)

    status_labels = {
        "approved": "qabul qilindi va tasdiqlandi",
        "modified": "o'zgartirish bilan qabul qilindi",
        "rejected": "rad etildi",
        "pending": "qayta ko'rib chiqishga ochildi"
    }

    return {
        "status": new_status,
        "message": f"Taklif {status_labels.get(new_status, new_status)}.",
        "proposal": _format_proposal(p, db)
    }


@router.post("/{prop_id}/approve")
def approve_proposal(
    prop_id: str,
    payload: Optional[ProposalActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return _handle_decision(db, prop_id, "approved", current_user, payload.teacher_comment if payload else None)


@router.post("/{prop_id}/modify")
def modify_proposal(
    prop_id: str,
    payload: Optional[ProposalActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return _handle_decision(db, prop_id, "modified", current_user, payload.teacher_comment if payload else None)


@router.post("/{prop_id}/reject")
def reject_proposal(
    prop_id: str,
    payload: Optional[ProposalActionRequest] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return _handle_decision(db, prop_id, "rejected", current_user, payload.teacher_comment if payload else None)


@router.post("/{prop_id}/reopen")
def reopen_proposal(
    prop_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Qayta ochish ham qaror qabul qilish huquqini talab qiladi (avval tekshiruvsiz edi)
    return _handle_decision(db, prop_id, "pending", current_user)


@router.delete("/{prop_id}")
def delete_proposal(
    prop_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("id") or current_user.get("sub")
    user_role = current_user.get("role") or "student"

    p = db.query(TeacherProposal).filter(TeacherProposal.id == prop_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Taklif topilmadi.")

    if user_role != "admin" and p.sender_id != user_id:
        raise HTTPException(status_code=403, detail="Faqat taklif muallifi yoki administrator taklifni o'chira oladi.")

    db.delete(p)
    db.commit()
    return {"status": "success", "message": "Taklif muvaffaqiyatli o'chirildi."}
