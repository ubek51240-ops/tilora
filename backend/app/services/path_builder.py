import json
import os
from typing import List, Dict, Any
from app.services.rationale import build_rationale

def generate_learning_path(
    student_id: str,
    cefr_levels: Dict[str, str],
    anxiety_level: int,
    professional_track: str = "Filologiya va tillarni o'qitish (ingliz tili)"
) -> List[Dict[str, Any]]:
    """
    16 haftalik shaxsiy o'quv yo'lini tuzish.
    METODIK QOIDA: Agar tashvish > 65 bo'lsa, og'zaki nutq birinchi slotdan suriladi!
    """
    topics_file = os.path.join(os.path.dirname(__file__), "..", "content", "curriculum_topics.json")
    topics_data = []
    if os.path.exists(topics_file):
        with open(topics_file, "r", encoding="utf-8") as f:
            topics_data = json.load(f)
            
    # Boshlang'ich slotlar tartibi
    if anxiety_level > 65:
        # Tashvishi yuqori talabaga eng qiyin ko'nikma (speaking) 1-haftada berilmaydi,
        # tinglash (listening) bilan boshlanadi!
        skills_order = ["listening", "speaking", "listening", "speaking", "writing", "reading", "integrated", "writing"]
    else:
        # Standart tartib
        skills_order = ["speaking", "listening", "speaking", "listening", "writing", "reading", "integrated", "writing"]
        
    path_items = []
    used_topic_ids = set()  # bir mavzu ikki haftaga takror tushmasligi uchun
    
    for idx, skill in enumerate(skills_order):
        week_num = (idx + 1) * 2 # 2, 4, 6, 8, 10, 12, 14, 16-haftalar
        skill_level = cefr_levels.get(skill, "B1")
        
        # Scaffold darajasini belgilash
        if week_num <= 4:
            scaffold = "none" if anxiety_level < 40 and skill_level in ["B2", "C1"] else "full"
        elif week_num <= 10:
            scaffold = "partial"
        else:
            scaffold = "none"
            
        # Mos mavzuni tanlash
        matched_topic = next((t for t in topics_data if t["skill"] == skill and t["id"] not in used_topic_ids), None)             or next((t for t in topics_data if t["skill"] == skill), None)
        repeated = bool(matched_topic) and matched_topic["id"] in used_topic_ids
        if matched_topic:
            used_topic_ids.add(matched_topic["id"])
        topic_title = matched_topic["title_uz"] if matched_topic else f"{skill.capitalize()} bo'yicha kasbiy amaliyot"
        if repeated:
            topic_title += " (2-qism)"
        
        rationale_text = build_rationale(
            skill=skill,
            level=skill_level,
            anxiety=anxiety_level,
            scaffold=scaffold,
            professional_track=professional_track
        )
        
        if anxiety_level > 65 and idx == 1:
            rationale_text += " Eslatma: og'zaki mashqlar birdan emas, tayyorgarlikdan so'ng asta-sekin kiritildi."
            
        path_items.append({
            "week_number": week_num,
            "skill": skill,
            "topic_id": matched_topic["id"] if matched_topic else None,
            "topic": topic_title,
            "pedagogical_focus": matched_topic.get("pedagogical_focus", "") if matched_topic else "",
            "difficulty_level": min(10, max(1, 3 + idx)),
            "scaffold_level": scaffold,
            "rationale": rationale_text,
            "status": "current" if idx == 0 else "planned",
            "teacher_approved": True
        })
        
    return path_items
