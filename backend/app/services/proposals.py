from typing import Dict, Any, List

def create_system_proposal(
    student_id: str,
    teacher_id: str,
    proposal_type: str,
    change_payload: Dict[str, Any],
    basis_metric: str
) -> Dict[str, Any]:
    """
    3-QOIDA: Yakuniy pedagogik qaror har doim o'qituvchida.
    Tizim faqat asoslangan TAKLIF beradi, status har doim 'pending'.
    """
    return {
        "student_id": student_id,
        "teacher_id": teacher_id,
        "proposal_type": proposal_type,
        "proposed_change": change_payload,
        "basis": basis_metric,
        "status": "pending"
    }

def evaluate_scaffold_transition(recent_scores: List[int], current_scaffold: str) -> str:
    """
    Scaffold darajasini o'zgartirish qoidasi:
    - Agar oxirgi 3 ta mashg'ulotda natija >= 75 bo'lsa: full -> partial -> none
    - Agar oxirgi 2 ta mashg'ulotda natija < 60 bo'lsa: none -> partial -> full
    """
    if len(recent_scores) >= 3 and all(s >= 75 for s in recent_scores[-3:]):
        if current_scaffold == "full":
            return "partial"
        elif current_scaffold == "partial":
            return "none"
            
    if len(recent_scores) >= 2 and all(s < 60 for s in recent_scores[-2:]):
        if current_scaffold == "none":
            return "partial"
        elif current_scaffold == "partial":
            return "full"
            
    return current_scaffold
