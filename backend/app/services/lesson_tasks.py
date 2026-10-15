"""Mashg'ulot topshiriqlari banki (content/lesson_tasks.json): ko'nikma bo'yicha topshiriq, skaffold lug'ati, rubrika."""
import json
import os
from functools import lru_cache
from typing import Any, Dict, List

_CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")
DEFAULT_SKILL = "writing"
VALID_SKILLS = ("writing", "speaking", "listening", "reading")


@lru_cache(maxsize=1)
def _load() -> List[Dict[str, Any]]:
    path = os.path.join(_CONTENT_DIR, "lesson_tasks.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_tasks() -> List[Dict[str, Any]]:
    return [dict(t) for t in _load()]


def get_task(skill: str) -> Dict[str, Any]:
    skill = (skill or DEFAULT_SKILL).strip().lower()
    if skill not in VALID_SKILLS:
        skill = DEFAULT_SKILL
    for t in _load():
        if t.get("skill") == skill:
            return dict(t)
    # Zaxira (fayl yo'q bo'lsa)
    return {
        "skill": skill,
        "title": "Yozma nutq: dars tahlili va baholash mezonlari",
        "prompt": "O'quvchilarning yozma nutqini baholashda qanday mezonlardan foydalanish mumkin? O'z fikringizni 150–180 so'zda ilmiy-metodik bayon eting.",
        "scaffold_level": "full",
        "word_count_min": 150,
        "word_count_max": 200,
        "duration_minutes": 30,
        "scaffold_vocabulary": [],
        "sample_structure": [],
        "rubric": [],
        "allowed_tools": [],
        "locked_tools": [],
    }
