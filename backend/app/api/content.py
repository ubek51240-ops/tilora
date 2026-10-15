"""
Ochiq ma'lumotnoma (kontent) API: glossariy, CEFR deskriptorlari, L1 interferensiya naqshlari,
metodik asoslar, FAQ. Autentifikatsiya talab qilinmaydi — bu ma'lumotlar platformaning
"Platforma haqida" bo'limida hammaga ko'rsatiladi.
"""
import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/content", tags=["Ma'lumotnoma (Kontent)"])

_CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")


@lru_cache(maxsize=16)
def _read(name: str):
    path = os.path.join(_CONTENT_DIR, name)
    if not os.path.exists(path):
        return [] if name != "methodology.json" else {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/overview")
def content_overview():
    """Kontent banki hajmi (bosh sahifa va ma'lumotnoma statistikasi uchun)."""
    diag = _read("diagnostic_questions.json")
    skills = {}
    for q in diag:
        skills[q.get("skill", "reading")] = skills.get(q.get("skill", "reading"), 0) + 1
    return {
        "glossary_terms": len(_read("glossary.json")),
        "cefr_levels": len(_read("cefr_levels.json")),
        "l1_patterns": len(_read("l1_patterns.json")),
        "diagnostic_questions": len(diag),
        "diagnostic_by_skill": skills,
        "survey_items": len(_read("survey_questions.json")),
        "curriculum_topics": len(_read("curriculum_topics.json")),
        "lesson_tasks": len(_read("lesson_tasks.json")),
        "faq_items": len(_read("faq.json")),
        "references": len((_read("methodology.json") or {}).get("references", [])),
    }


@router.get("/glossary")
def get_glossary(q: Optional[str] = Query(None, max_length=60), category: Optional[str] = Query(None, max_length=30)):
    """ELT metodikasi glossariysi (qidiruv va toifa filtri bilan)."""
    items: List[Dict[str, Any]] = _read("glossary.json")
    if category:
        items = [i for i in items if i.get("category") == category]
    if q:
        ql = q.lower()
        items = [i for i in items if ql in i.get("term", "").lower() or ql in i.get("uz", "").lower()
                 or ql in i.get("definition_uz", "").lower() or ql in i.get("definition_en", "").lower()]
    cats = sorted({i.get("category", "") for i in _read("glossary.json")})
    return {"terms": items, "total": len(items), "categories": cats}


@router.get("/cefr-levels")
def get_cefr_levels():
    """CEFR A1–C2 global va ko'nikma bo'yicha tavsiflar (Council of Europe, 2001/2020 asosida)."""
    return {"levels": _read("cefr_levels.json"), "source": "Council of Europe, CEFR Global Scale (2001); Companion Volume (2020) — o'zbekcha moslashtirilgan."}


@router.get("/l1-patterns")
def get_l1_patterns():
    """O'zbek–ingliz interferensiya naqshlari (regex ichki; talabaga sabab, misol va tuzatish ko'rsatiladi)."""
    out = []
    for p in _read("l1_patterns.json"):
        out.append({k: p.get(k) for k in ("id", "category", "issue_short", "issue_reason", "suggestion", "example_wrong", "example_right")})
    return {"patterns": out, "total": len(out)}


@router.get("/methodology")
def get_methodology():
    """Modelning ilmiy-pedagogik asoslari, 4 qoida, 5 bosqich, o'xshash tizimlar bilan taqqoslash, adabiyotlar."""
    return _read("methodology.json")


@router.get("/faq")
def get_faq(audience: Optional[str] = Query(None, pattern="^(student|teacher|researcher|all)$")):
    items = _read("faq.json")
    if audience:
        items = [i for i in items if i.get("audience") in (audience, "all")]
    return {"items": items, "total": len(items)}


@router.get("/curriculum")
def get_curriculum():
    """16 haftalik mavzular banki (ko'nikma, hafta, kutilayotgan natijalar)."""
    return {"topics": _read("curriculum_topics.json")}
