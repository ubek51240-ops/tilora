import re
import os
import json
from typing import List, Dict, Any

def analyze_l1_interference(text: str) -> List[Dict[str, Any]]:
    """
    Ona tili (o'zbek/qoraqalpoq) ta'siridagi xatolarni qidirish.
    AI kalitisiz ham ishlaydi va darhol aniq sabab ko'rsatadi.
    """
    patterns_file = os.path.join(os.path.dirname(__file__), "..", "content", "l1_patterns.json")
    if not os.path.exists(patterns_file):
        return []
        
    with open(patterns_file, "r", encoding="utf-8") as f:
        patterns = json.load(f)
        
    findings = []
    
    for item in patterns:
        pattern = item.get("regex")
        if not pattern:
            continue
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                findings.append({
                    "category": item.get("category", "grammar"),
                    "issue_short": item.get("issue_short", "L1 interferensiyasi"),
                    "issue_reason": item.get("issue_reason", "Ona tili ta'siri aniqlandi."),
                    "suggestion": item.get("suggestion", ""),
                    "l1_interference": True,
                    "matched_text": match.group(0),
                    "feedback_level": "task" # Hattie-Timperley task darajasi
                })
        except Exception:
            continue
            
    return findings
