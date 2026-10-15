"""
Moslashtirish bosqichi (3.3 ishlash sikli): natijaga qarab keyingi mashg'ulot uchun ko'mak darajasi
o'zgartiriladi — lekin faqat o'qituvchi tasdig'i bilan (3-qoida).

Qoida (scaffolding dinamikasi): talaba mustaqil bosqichni ketma-ket 3 mashg'ulotda muvaffaqiyatli (ball ≥ 60)
topshirsa, tizim ko'mak darajasini bir pog'ona pasaytirishni TAKLIF qiladi: C → B → A (to'liq → qisman → ko'maksiz).
Taklif teacher_proposals ga 'pending' holatda tushadi; o'qituvchi tasdiqlasa TaskVariantAssignment yoziladi.
Aksincha, 2 ketma-ket past natija (< 45) bo'lsa ko'makni oshirish taklif qilinadi.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.entities import LessonRecord, TeacherProposal, TaskVariantAssignment, User, Group
from app.services.differentiation import effective_variant, VARIANT_LABELS

SUCCESS_SCORE = 60
LOW_SCORE = 45
NEXT_UP = {"C": "B", "B": "A", "A": None}
NEXT_DOWN = {"A": "B", "B": "C", "C": None}


def maybe_create_scaffold_proposal(db: Session, student_id: str) -> Optional[Dict[str, Any]]:
    recs = db.query(LessonRecord).filter(LessonRecord.student_id == student_id).order_by(LessonRecord.created_at.desc()).limit(3).all()
    scores = [r.score for r in recs if r.score is not None]
    cur = effective_variant(db, student_id)["variant"]
    target, kind, basis = None, None, ""
    if len(scores) >= 3 and all(s >= SUCCESS_SCORE for s in scores) and NEXT_UP.get(cur):
        target, kind = NEXT_UP[cur], "decrease_support"
        basis = f"Ketma-ket 3 mashg'ulotda muvaffaqiyat ({', '.join(str(s) for s in scores)} ball ≥ {SUCCESS_SCORE}). Scaffolding dinamikasi: ko'mak bir pog'ona pasaytiriladi."
    elif len(scores) >= 2 and all(s < LOW_SCORE for s in scores[:2]) and NEXT_DOWN.get(cur):
        target, kind = NEXT_DOWN[cur], "increase_support"
        basis = f"Ketma-ket 2 mashg'ulotda past natija ({', '.join(str(s) for s in scores[:2])} ball < {LOW_SCORE}). Ko'makni oshirish tavsiya etiladi."
    if not target:
        return None
    # Takroriy kutilayotgan taklif bo'lmasin
    existing = db.query(TeacherProposal).filter(TeacherProposal.student_id == student_id, TeacherProposal.proposal_type == "scaffold_change",
                                                TeacherProposal.status == "pending").first()
    if existing:
        return {"id": existing.id, "duplicate": True}
    student = db.query(User).filter(User.id == student_id).first()
    group = db.query(Group).filter(Group.id == student.group_id).first() if student and student.group_id else None
    teacher_id = group.teacher_id if group and group.teacher_id else None
    text = (f"{VARIANT_LABELS[cur]['name']} → {VARIANT_LABELS[target]['name']}. "
            f"{'Ko‘mak kamaytiriladi' if kind == 'decrease_support' else 'Ko‘mak oshiriladi'}: {VARIANT_LABELS[target]['desc']}")
    p = TeacherProposal(
        student_id=student_id, teacher_id=teacher_id, sender_id=None, receiver_id=teacher_id or "all_teachers",
        proposal_type="scaffold_change",
        proposed_change={"student_name": student.full_name if student else "Talaba", "title": "Ko'mak darajasini o'zgartirish taklifi (tizim)",
                         "text": text, "from_variant": cur, "to_variant": target, "kind": kind, "direction": "system",
                         "sender_name": "TILORA AI Tizimi", "sender_role": "system", "receiver_role": "teacher"},
        basis=basis, status="pending", created_at=datetime.utcnow(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "from": cur, "to": target, "kind": kind, "basis": basis}


def apply_proposal_if_adaptive(db: Session, p: TeacherProposal, teacher_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Tasdiqlangan tizim taklifi (scaffold_change) kuchga kiradi: TaskVariantAssignment yoziladi."""
    if p.proposal_type != "scaffold_change" or p.status != "approved":
        return None
    pc = p.proposed_change or {}
    target = pc.get("to_variant")
    if not target or not p.student_id or target not in VARIANT_LABELS:
        return None
    db.add(TaskVariantAssignment(student_id=p.student_id, teacher_id=teacher_id, variant=target,
                                 note=f"O'qituvchi tasdiqlagan tizim taklifi: {pc.get('text', '')}"[:500], source="teacher"))
    db.commit()
    return {"student_id": p.student_id, "variant": target}
