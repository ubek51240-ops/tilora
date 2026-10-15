import os
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import (
    User, StudentProfile, LearningPath, PathItem,
    TeacherSubject, SyllabusTopic, TeacherMaterial, MaterialAttempt
)
from app.services import materials as matsvc
from app.services.ai_service import ai_service
from app.schemas.all_schemas import DiagnosticResultResponse, DiagnosticSubmissionRequest
from app.core.deps import get_current_user, require_role, get_optional_user
from app.services.path_builder import generate_learning_path
from app.services.diagnostic_bank import load_diagnostic_questions, load_survey_questions, subjects_with_questions
from app.core.access import check_experiment_access
from app.api.experiment_ext import sill_router, micro_router
import app.core.schema_patch  # noqa: F401

router = APIRouter(prefix="/student", tags=["Talaba"])
router.include_router(sill_router, dependencies=[Depends(get_current_user)])
router.include_router(micro_router, dependencies=[Depends(get_current_user)])

@router.get("/profile")
def get_student_profile(
    student_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_id = current_user["id"]
    if student_id and student_id != current_user["id"]:
        # Faqat o'qituvchi yoki admin boshqa talaba profilini ko'ra oladi
        if current_user.get("role") not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Xavfsizlik qoidasi: Siz faqat o'z shaxsiy profilingizni ko'ra olasiz. Boshqa talaba profilini ko'rish taqiqlanadi!"
            )
        target_id = student_id

    profile = db.query(StudentProfile).filter(StudentProfile.student_id == target_id).order_by(StudentProfile.valid_from.desc()).first()
    if not profile:
        # Default yangi profil yaratish
        profile = StudentProfile(
            student_id=target_id,
            cefr_listening="B1",
            cefr_reading="B2",
            cefr_speaking="A2",
            cefr_writing="B1",
            load_capacity=45,
            pace_index=62,
            anxiety_level=71,
            autonomy_readiness=40
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return {
        "student_id": profile.student_id,
        "cefr_levels": {
            "listening": profile.cefr_listening,
            "reading": profile.cefr_reading,
            "speaking": profile.cefr_speaking,
            "writing": profile.cefr_writing
        },
        "cognitive_affective": {
            "load_capacity": profile.load_capacity,
            "pace_index": profile.pace_index,
            "anxiety_level": profile.anxiety_level,
            "autonomy_readiness": profile.autonomy_readiness
        },
        "professional_track": profile.professional_track,
        "source": profile.source,
        "valid_from": profile.valid_from
    }

@router.get("/diagnostic/subjects")
def get_diagnostic_subjects(
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Talaba tanlovi uchun: fanlar ro'yxati (+ umumiy), har biri uchun ko'nikma taqsimoti bilan."""
    return {"subjects": subjects_with_questions(db, current_user)}

@router.get("/diagnostic/questions")
def get_diagnostic_questions(
    subject_id: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """O'qituvchi yuklagan savollar (tanlangan fan + umumiy), aks holda standart JSON to'plam."""
    return load_diagnostic_questions(db, current_user, subject_id or None)

@router.get("/survey/questions")
def get_survey_questions(
    subject_id: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    return load_survey_questions(db, current_user, subject_id or None)

@router.post("/diagnostic/submit", response_model=DiagnosticResultResponse)
def submit_diagnostic(
    payload: DiagnosticSubmissionRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    from datetime import datetime

    # 1. Diagnostika savollarini tekshirish (o'qituvchi banki yoki standart to'plam)
    diag_questions = load_diagnostic_questions(db, current_user, payload.subject_id or None)

    q_map = {q["id"]: q for q in diag_questions}
    skill_scores = {"listening": 0, "reading": 0, "writing": 0, "speaking": 0}
    skill_counts = {"listening": 0, "reading": 0, "writing": 0, "speaking": 0}
    correct_count = 0
    question_reviews = []

    for ans in payload.diagnostic_answers:
        q = q_map.get(ans.question_id)
        if q:
            sk = q.get("skill", "reading")
            skill_counts[sk] = skill_counts.get(sk, 0) + 1
            corr_idx = q.get("correct_index", 0)
            is_corr = (ans.selected_option_index == corr_idx)

            if is_corr:
                skill_scores[sk] = skill_scores.get(sk, 0) + 1
                correct_count += 1

            opts = q.get("options", [])
            sel_text = opts[ans.selected_option_index] if 0 <= ans.selected_option_index < len(opts) else ""
            corr_text = opts[corr_idx] if 0 <= corr_idx < len(opts) else ""

            question_reviews.append({
                "id": q["id"],
                "skill": sk,
                "cefr_level": q.get("cefr_level", "B1"),
                "question": q.get("instruction") or q.get("question", ""),
                "selected_index": ans.selected_option_index,
                "correct_index": corr_idx,
                "is_correct": is_corr,
                "selected_option_text": sel_text,
                "correct_option_text": corr_text,
                "rationale": q.get("rationale", "Mavzu konteksti va CEFR standartiga mos to'g'ri pedagogik javob.")
            })

    # CEFR darajalarini har bir ko'nikma bo'yicha hisoblash
    cefr_levels = {}
    cefr_weights = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
    level_weights_list = []

    # Har bir ko'nikma uchun 3 pog'onali shkala (yuqori / o'rta / past).
    # Nisbat asosida hisoblanadi, shuning uchun o'qituvchi savollar sonini
    # o'zgartirsa ham ishlaydi: 2 ta savolda 2/2 -> yuqori, 1/2 -> o'rta, 0/2 -> past.
    skill_ladder = {
        "reading":   ("C1", "B2", "B1"),
        "writing":   ("B2", "B1", "A2"),
        "speaking":  ("B2", "A2", "A1"),
        "listening": ("B2", "B1", "A2"),
    }
    for sk in ["listening", "reading", "writing", "speaking"]:
        corr = skill_scores.get(sk, 0)
        tot = skill_counts.get(sk, 0)
        high, mid, low = skill_ladder[sk]
        if tot <= 0:
            lvl = mid  # bu ko'nikma bo'yicha savol yo'q: neytral daraja
        else:
            ratio = corr / tot
            lvl = high if ratio >= 0.99 else (mid if ratio >= 0.5 else low)
        cefr_levels[sk] = lvl
        level_weights_list.append(cefr_weights.get(lvl, 3))

    avg_w = sum(level_weights_list) / len(level_weights_list) if level_weights_list else 3
    overall_cefr = "B2" if avg_w >= 3.8 else ("B1" if avg_w >= 2.8 else "A2")

    # 2. Anketa savollarini hisoblash (FLCAS va kognitiv o'lchamlar)
    survey_questions = load_survey_questions(db, current_user, payload.subject_id or None)

    s_map = {q["id"]: q for q in survey_questions}
    dim_scores = {"anxiety": [], "load_capacity": [], "pace": [], "autonomy": [], "motivation": [],
                  "planning": [], "monitoring": [], "evaluation": [], "regulation": []}

    meta_raw = {"planning": [], "monitoring": [], "evaluation": [], "regulation": []}
    for ans in payload.survey_answers:
        sq = s_map.get(ans.question_id)
        if sq:
            dim = sq.get("dimension")
            weight = sq.get("weight", 1.0)
            if dim in dim_scores:
                dim_scores[dim].append(ans.rating * weight)
            if dim in meta_raw:
                meta_raw[dim].append(ans.rating)  # metakognitiv shkala 1–5: vaznsiz (MSLQ standarti)

    def calc_dim(name, default_val):
        vals = dim_scores.get(name, [])
        if not vals:
            return default_val
        avg = sum(vals) / len(vals)
        # Vazn > 1.0 bo'lganda 100 dan oshib ketmasligi uchun 0-100 oralig'iga cheklanadi
        return max(0, min(100, int(round((avg / 5.0) * 100))))

    cog_affective = {
        "anxiety_level": calc_dim("anxiety", 68),
        "load_capacity": calc_dim("load_capacity", 50),
        "pace_index": calc_dim("pace", 60),
        "autonomy_readiness": calc_dim("autonomy", 42)
    }
    # Metakognitiv komponentlar (Flavell / Pintrich MSLQ): 1–5 shkala, 4.7-jadval uchun
    def calc_meta(name):
        vals = meta_raw.get(name, [])
        return round(sum(vals) / len(vals), 2) if vals else None
    metacognitive = {k: calc_meta(k) for k in ("planning", "monitoring", "evaluation", "regulation")}
    motivation_score = calc_dim("motivation", 0) if dim_scores.get("motivation") else None

    # 3. Pedagogik tavsiyalar va Scaffolding strategiyasi
    anx = cog_affective["anxiety_level"]
    auto = cog_affective["autonomy_readiness"]

    if anx > 65:
        anx_status = "Yuqori xavotir (High Anxiety)"
        scaffold_recommendation = "full"
        flcas_advice = "FLCAS shkalasi bo'yicha xavotir yuqori (65%+). 1-qoidaga binoan darslarda past bosimli formativ mashg'ulotlar, audiolarni bir necha bor tinglash imkoni va nutq oldidan tayyorgarlik (pre-speaking scaffolding) tavsiya etiladi."
    elif anx >= 40:
        anx_status = "O'rtacha xavotir (Moderate Anxiety)"
        scaffold_recommendation = "partial"
        flcas_advice = "Tashvish me'yoriy chegarada. Standart adaptiv o'quv oqimi va bosqichma-bosqich ko'makni kamaytirish modeli qo'llaniladi."
    else:
        anx_status = "Past xavotir / Erkin (Low Anxiety)"
        scaffold_recommendation = "none" if auto >= 50 else "partial"
        flcas_advice = "Til to'sig'i va xavotir minimal. Talaba mustaqil va avtonom topshiriqlarni tezkor o'zlashtirishga tayyor."

    weakest_skill = min(cefr_levels, key=lambda k: cefr_weights.get(cefr_levels[k], 0))
    strongest_skill = max(cefr_levels, key=lambda k: cefr_weights.get(cefr_levels[k], 0))

    pedagogic_advice = {
        "flcas_status": anx_status,
        "flcas_advice": flcas_advice,
        "scaffold_recommendation": scaffold_recommendation,
        "weakest_skill": weakest_skill,
        "strongest_skill": strongest_skill,
        "adaptive_strategy": f"Boshlang'ich ko'mak darajasi: {scaffold_recommendation.upper()}. 16 haftalik o'quv traektoriyasi ushbu profilga to'liq moslashtirildi."
    }

    ai_summary = (
        f"CEFR Diagnostika xulosasi: Umumiy daraja {overall_cefr} (O'qish: {cefr_levels['reading']}, "
        f"Tinglash: {cefr_levels['listening']}, Yozma: {cefr_levels['writing']}, Og'zaki: {cefr_levels['speaking']}). "
        f"FLCAS tashvish ko'rsatkichi {anx}% bo'lib, {flcas_advice}"
    )

    # 4. Agar talaba tizimga kirgan bo'lsa, bazadagi profilini yangilash
    student_id = current_user["id"] if current_user else "guest_student"
    if current_user:
        new_profile = StudentProfile(
            student_id=current_user["id"],
            cefr_listening=cefr_levels["listening"],
            cefr_reading=cefr_levels["reading"],
            cefr_speaking=cefr_levels["speaking"],
            cefr_writing=cefr_levels["writing"],
            load_capacity=cog_affective["load_capacity"],
            pace_index=cog_affective["pace_index"],
            anxiety_level=cog_affective["anxiety_level"],
            autonomy_readiness=cog_affective["autonomy_readiness"],
            professional_track="Filologiya va tillarni o'qitish (ingliz tili)",
            source="diagnostic_test",
            valid_from=datetime.utcnow()
        )
        db.add(new_profile)

        # 5. Tajriba-sinov o'lchovi (pre/post) — assessments jadvaliga yoziladi (4.2–4.10 jonli jadvallar manbai)
        from app.models.entities import Assessment, SurveyResponse
        # Nazorat oynasi (o'qituvchi belgilagan) ustuvor; aks holda so'rovdagi tur; aks holda avtomatik
        win = current_user.get("assessment_window") or "none"
        atype = win if win != "none" else payload.assessment_type
        if not atype:
            has_pre = db.query(Assessment).filter(Assessment.student_id == current_user["id"], Assessment.assessment_type == "pre",
                                                  Assessment.skill.in_(["listening", "reading", "writing", "speaking", "anxiety"])).first()
            atype = "post" if has_pre else "pre"
        # Xom anketa javoblari — Cronbach α uchun (FLCAS / MSLQ / kognitiv o'lchamlar)
        _inst = {"anxiety": "flcas", "planning": "mslq", "monitoring": "mslq", "evaluation": "mslq", "regulation": "mslq",
                 "load_capacity": "cognitive", "pace": "cognitive", "autonomy": "cognitive", "motivation": "cognitive"}
        for ans in payload.survey_answers:
            sq = s_map.get(ans.question_id)
            if sq and sq.get("dimension") in _inst:
                db.add(SurveyResponse(student_id=current_user["id"], instrument=_inst[sq["dimension"]], dimension=sq["dimension"],
                                      question_id=ans.question_id, rating=ans.rating, assessment_type=atype))
        now = datetime.utcnow()
        rows = []
        for sk in ["listening", "reading", "writing", "speaking"]:
            tot = skill_counts.get(sk, 0)
            if tot > 0:
                rows.append(Assessment(student_id=current_user["id"], assessment_type=atype, skill=sk,
                                       score=int(round(skill_scores.get(sk, 0) * 100 / tot)), max_score=100, administered_at=now))
        if dim_scores.get("anxiety"):
            rows.append(Assessment(student_id=current_user["id"], assessment_type=atype, skill="anxiety", score=anx, max_score=100, administered_at=now))
        if motivation_score is not None:
            rows.append(Assessment(student_id=current_user["id"], assessment_type=atype, skill="motivation", score=motivation_score, max_score=100, administered_at=now))
        for k, v in metacognitive.items():
            if v is not None:
                rows.append(Assessment(student_id=current_user["id"], assessment_type=atype, skill=f"meta_{k}", score=int(round(v * 20)), max_score=100, administered_at=now))
        db.add_all(rows)
        db.commit()
    else:
        atype = None

    return {
        "student_id": student_id,
        "cefr_levels": cefr_levels,
        "overall_cefr": overall_cefr,
        "cognitive_affective": cog_affective,
        "metacognitive": metacognitive,
        "assessment_type": atype,
        "professional_track": "Filologiya va tillarni o'qitish (ingliz tili)",
        "source": "diagnostic_test",
        "correct_count": correct_count,
        "total_questions": len(diag_questions) if diag_questions else 8,
        "question_reviews": question_reviews,
        "pedagogic_advice": pedagogic_advice,
        "ai_summary": ai_summary
    }

@router.get("/path")
def get_student_path(
    student_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_id = current_user["id"]
    if student_id and student_id != current_user["id"]:
        if current_user.get("role") not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Xavfsizlik qoidasi: Siz faqat o'z o'quv traektoriyangizni ko'ra olasiz. Boshqa talaba yo'lini ko'rish taqiqlanadi!"
            )
        target_id = student_id

    profile = db.query(StudentProfile).filter(StudentProfile.student_id == target_id).order_by(StudentProfile.valid_from.desc()).first()
    anxiety = profile.anxiety_level if profile else 71
    cefr = {
        "listening": profile.cefr_listening if profile else "B1",
        "reading": profile.cefr_reading if profile else "B2",
        "speaking": profile.cefr_speaking if profile else "A2",
        "writing": profile.cefr_writing if profile else "B1"
    }

    # Nazorat guruhi: adaptiv yo'l ko'rsatilmaydi — an'anaviy (chiziqli, bir xil) dastur (tajriba butunligi, 4.1)
    arm = current_user.get("experiment_arm") if target_id == current_user["id"] else None
    if arm is None and target_id != current_user["id"]:
        from app.models.entities import Group
        u = db.query(User).filter(User.id == target_id).first()
        g = db.query(Group).filter(Group.id == u.group_id).first() if (u and u.group_id) else None
        arm = g.experiment_arm if g else "none"
    if arm == "control":
        from app.services.path_builder import generate_learning_path as _glp
        import json as _json, os as _os
        topics_file = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "content", "curriculum_topics.json")
        topics = _json.load(open(topics_file, "r", encoding="utf-8")) if _os.path.exists(topics_file) else []
        items = []
        for idx, t in enumerate(topics[:8]):
            items.append({"week_number": (idx + 1) * 2, "skill": t["skill"], "topic_id": t["id"], "topic": t["title_uz"],
                          "pedagogical_focus": t.get("pedagogical_focus", ""), "difficulty_level": 5, "scaffold_level": "none",
                          "rationale": "Nazorat guruhi: an'anaviy dastur — barcha talabaga bir xil ketma-ketlik, profilga moslashtirilmaydi.",
                          "status": "current" if idx == 0 else "planned", "teacher_approved": True})
        return {"student_id": target_id, "total_weeks": 16, "current_week": 4, "items": items, "experiment_arm": "control",
                "note": "Nazorat guruhi an'anaviy metodika bo'yicha o'qitiladi: adaptiv yo'l, variantlar va metakognitiv blok yopiq."}

    path_items = generate_learning_path(
        student_id=target_id,
        cefr_levels=cefr,
        anxiety_level=anxiety
    )
    return {
        "student_id": target_id,
        "total_weeks": 16,
        "current_week": 4,
        "items": path_items,
        "experiment_arm": arm or "experimental"
    }

@router.get("/experiment-status")
def experiment_status(current_user: dict = Depends(get_current_user)):
    """Talabaning tajriba qanoti va nazorat oynasi (frontend bannerlari uchun)."""
    return {"experiment_arm": current_user.get("experiment_arm") or "none", "assessment_window": current_user.get("assessment_window") or "none",
            "adaptive_enabled": current_user.get("experiment_arm") != "control",
            "ai_enabled": current_user.get("experiment_arm") != "control" and (current_user.get("assessment_window") or "none") == "none"}


@router.get("/dynamics")
def get_student_dynamics(
    student_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Refleksiya moduli (3.3): talabaning dinamika ko'rsatkichlari — mashg'ulot ballari vaqt bo'yicha,
    ko'nikma kesimida, o'z bahosi aniqligi (rating_gap), yordam so'rovlari, pre/post baholar, profil tarixi.
    """
    from app.models.entities import LessonRecord, Assessment
    from app.services import statistics as stt
    target_id = current_user["id"]
    if student_id and student_id != current_user["id"]:
        if current_user.get("role") not in ["teacher", "admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Xavfsizlik qoidasi: faqat o'z dinamikangizni ko'ra olasiz.")
        target_id = student_id

    recs = db.query(LessonRecord).filter(LessonRecord.student_id == target_id).order_by(LessonRecord.created_at.asc()).all()
    timeline = [{"date": r.created_at.strftime("%Y-%m-%d") if r.created_at else "", "skill": r.skill, "score": r.score,
                 "rating_gap": r.rating_gap, "variant": r.task_variant, "scaffold": r.scaffold_level, "help_requests": r.help_requests,
                 "self_checks": r.self_checks, "minutes": round((r.independent_seconds or 0) / 60, 1), "next_goal": r.next_goal} for r in recs]
    by_skill = {}
    for r in recs:
        if r.score is None:
            continue
        d = by_skill.setdefault(r.skill, {"scores": []})
        d["scores"].append(r.score)
    for sk, d in by_skill.items():
        d["count"] = len(d["scores"]); d["avg"] = round(stt.mean(d["scores"]), 1)
        d["first"] = d["scores"][0]; d["last"] = d["scores"][-1]; d["trend"] = d["scores"][-1] - d["scores"][0]
    gaps = [r.rating_gap for r in recs if r.rating_gap is not None]
    assess = {}
    for a in db.query(Assessment).filter(Assessment.student_id == target_id).order_by(Assessment.administered_at.asc()).all():
        assess.setdefault(a.assessment_type, {})[a.skill] = a.score
    profiles = db.query(StudentProfile).filter(StudentProfile.student_id == target_id).order_by(StudentProfile.valid_from.asc()).all()
    scaffold_path = [r.scaffold_level for r in recs if r.scaffold_level]
    streak = 0
    for r in reversed(recs):
        if r.score is not None and r.score >= 60:
            streak += 1
        else:
            break
    return {
        "student_id": target_id,
        "lessons_completed": len(recs),
        "timeline": timeline,
        "by_skill": by_skill,
        "metacognitive_accuracy": {"avg_rating_gap": round(stt.mean(gaps), 2) if gaps else None,
                                   "trend": (round(gaps[-1] - gaps[0], 2) if len(gaps) >= 2 else None),
                                   "note": "0 ga yaqinlashishi o'zini baholash aniqligi oshayotganini bildiradi (metakognitiv kalibrlash)."},
        "help_requests_total": sum(r.help_requests or 0 for r in recs),
        "success_streak": streak,
        "scaffold_path": scaffold_path,
        "scaffold_rule": "3 ta ketma-ket muvaffaqiyatli (≥60) mashg'ulotdan so'ng ko'mak darajasi bir pog'ona pasaytirilishi o'qituvchiga taklif qilinadi.",
        "scaffold_reduction_suggested": streak >= 3,
        "assessments": assess,
        "profile_history": [{"date": p.valid_from.strftime("%Y-%m-%d") if p.valid_from else "", "source": p.source,
                             "cefr": {"listening": p.cefr_listening, "reading": p.cefr_reading, "speaking": p.cefr_speaking, "writing": p.cefr_writing},
                             "anxiety_level": p.anxiety_level, "autonomy_readiness": p.autonomy_readiness} for p in profiles],
    }

@router.get("/glossary")
def get_glossary(q: Optional[str] = None):
    """Shaxsiy lug'at (1-qoida bo'yicha mustaqil bosqichda ham ochiq). Umumiy ELT glossariysidan olinadi."""
    from app.api.content import _read
    items = _read("glossary.json")
    if q:
        ql = q.lower()
        items = [i for i in items if ql in i.get("term", "").lower() or ql in i.get("uz", "").lower()]
    return {
        "terms": [
            {"term": i["term"], "uz": i.get("uz", ""), "definition": i.get("definition_uz", ""), "definition_en": i.get("definition_en", ""), "category": i.get("category", "")}
            for i in items
        ],
        "total": len(items)
    }

@router.get("/previous-works")
def get_previous_works(
    student_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Talabaning haqiqiy avvalgi ishlari (material_attempts jadvalidan), oxirgi 20 tasi."""
    target_id = current_user["id"]
    if student_id and student_id != current_user["id"]:
        if current_user.get("role") not in ["teacher", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Xavfsizlik qoidasi: Boshqa talabaning avvalgi ishlarini ko'rish taqiqlanadi!"
            )
        target_id = student_id

    attempts = db.query(MaterialAttempt).filter(
        MaterialAttempt.student_id == target_id, MaterialAttempt.status == "completed"
    ).order_by(MaterialAttempt.created_at.desc()).limit(20).all()
    mats = {m.id: m for m in db.query(TeacherMaterial).filter(TeacherMaterial.id.in_([a.material_id for a in attempts])).all()} if attempts else {}
    works = []
    for a in attempts:
        m = mats.get(a.material_id)
        works.append({
            "id": a.id,
            "topic": m.topic_title if m else "",
            "title": m.title if m else "",
            "material_type": a.material_type,
            "score": a.score,
            "passed": a.passed,
            "date": a.created_at.strftime("%Y-%m-%d") if a.created_at else ""
        })
    return {"works": works, "total": len(works)}

# =========================================================================
# TALABALAR UCHUN FANLAR, MAVZULAR, SLAYDLAR VA TESTLAR ENDPOINTLARI
# =========================================================================

class StudentTestAnswer(BaseModel):
    question_id: str
    selected_index: int

class StudentTestSubmitRequest(BaseModel):
    answers: Any

@router.get("/subjects")
def get_available_subjects_for_student(
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Talabalar uchun ochiq fanlar ro'yxati, mavzular va materiallar soni.
    """
    scope = matsvc.student_subject_scope(db, current_user)
    subjects = db.query(TeacherSubject).order_by(TeacherSubject.created_at.desc()).all()
    if scope is not None:
        subjects = [s for s in subjects if s.id in scope]
    student_id = (current_user or {}).get("id") if (current_user or {}).get("role") == "student" else None
    result = []
    for s in subjects:
        teacher = db.query(User).filter(User.id == s.teacher_id).first()
        topics_count = db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == s.id).count()
        mats = db.query(TeacherMaterial).filter(TeacherMaterial.subject_id == s.id).all()
        materials_count = len(mats)
        by_type = {"test": 0, "presentation": 0, "lesson_plan": 0, "writing": 0}
        for m in mats:
            by_type[m.material_type] = by_type.get(m.material_type, 0) + 1
        done = 0
        if student_id and mats:
            done = len(matsvc.best_attempts(db, student_id, [m.id for m in mats]))
        result.append({
            "counts": by_type,
            "done_count": done,
            "progress_percent": int(round(done * 100 / materials_count)) if materials_count else 0,
            "id": s.id,
            "name": s.name,
            "title": s.name,
            "code": s.code or "",
            "semester": s.semester or "5-semestr",
            "course_year": s.course_year or 3,
            "group_name": s.group_name or "",
            "description": s.description or "",
            "teacher_name": teacher.full_name if teacher else "Kafedra o'qituvchisi",
            "topics_count": topics_count,
            "materials_count": materials_count,
            "created_at": s.created_at.strftime("%Y-%m-%d") if s.created_at else ""
        })
    return {"subjects": result, "total": len(result), "scoped": scope is not None}

@router.get("/subjects/{subject_id}/topics")
def get_subject_topics_for_student(
    subject_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Tanlangan fanning haftalik mavzulari va har bir mavzuga oid materiallar.
    """
    subj = db.query(TeacherSubject).filter(TeacherSubject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Fan topilmadi.")

    topics = db.query(SyllabusTopic).filter(SyllabusTopic.subject_id == subject_id).order_by(SyllabusTopic.week_number.asc()).all()
    result = []
    for t in topics:
        mats = db.query(TeacherMaterial).filter(TeacherMaterial.subject_id == subject_id, TeacherMaterial.topic_title == t.title).all()
        result.append({
            "id": t.id,
            "week_number": t.week_number,
            "title": t.title,
            "hours": t.hours,
            "materials_count": len(mats),
            "materials": [
                {
                    "id": m.id,
                    "material_type": m.material_type,
                    "title": m.title
                } for m in mats
            ]
        })
    return {"subject_id": subject_id, "subject_name": subj.name, "topics": result}

@router.get("/materials")
def get_student_materials(
    subject_id: Optional[str] = None,
    material_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Talabalar uchun o'qituvchilar yaratgan barcha test, taqdimot va dars rejalari ro'yxati.
    """
    query = db.query(TeacherMaterial)
    scope = matsvc.student_subject_scope(db, current_user)
    if subject_id:
        query = query.filter(TeacherMaterial.subject_id == subject_id)
    elif scope is not None:
        query = query.filter(TeacherMaterial.subject_id.in_(scope))
    if material_type:
        query = query.filter(TeacherMaterial.material_type == material_type)

    materials = query.order_by(TeacherMaterial.created_at.desc()).all()
    student_id = (current_user or {}).get("id") if (current_user or {}).get("role") == "student" else None
    progress = matsvc.best_attempts(db, student_id, [m.id for m in materials])
    result = []
    for m in materials:
        subj = db.query(TeacherSubject).filter(TeacherSubject.id == m.subject_id).first()
        teacher = db.query(User).filter(User.id == m.teacher_id).first()

        # Talabaga javob kaliti yuborilmaydi (test tekshiruvi serverda)
        content = matsvc.student_safe_content(m.material_type, m.content_json)
        items_count = matsvc.items_count(m.material_type, content)

        result.append({
            "attempt": progress.get(m.id),
            "id": m.id,
            "subject_id": m.subject_id,
            "subject_name": subj.name if subj else "Fan",
            "subject_title": subj.name if subj else "Fan",
            "topic_title": m.topic_title,
            "material_type": m.material_type,
            "title": m.title,
            "items_count": items_count,
            "content": content,
            "content_json": content,
            "teacher_name": teacher.full_name if teacher else "O'qituvchi",
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
        })
    return {"materials": result, "total": len(result)}

@router.get("/materials/{material_id}")
def get_student_material_detail(
    material_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Bitta materialning (test, slayd yoki dars rejasi) to'liq ma'lumotlarini olish.
    """
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material topilmadi.")

    subj = db.query(TeacherSubject).filter(TeacherSubject.id == m.subject_id).first()
    teacher = db.query(User).filter(User.id == m.teacher_id).first()
    content = matsvc.student_safe_content(m.material_type, m.content_json)
    student_id = (current_user or {}).get("id") if (current_user or {}).get("role") == "student" else None

    return {
        "id": m.id,
        "subject_id": m.subject_id,
        "subject_name": subj.name if subj else "Fan",
        "subject_title": subj.name if subj else "Fan",
        "topic_title": m.topic_title,
        "material_type": m.material_type,
        "title": m.title,
        "teacher_name": teacher.full_name if teacher else "O'qituvchi",
        "attempt": matsvc.best_attempts(db, student_id, [m.id]).get(m.id),
        "content": content,
        "content_json": content,
        "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
    }

@router.post("/materials/{material_id}/submit-test")
def submit_student_test(
    material_id: str,
    payload: StudentTestSubmitRequest,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Talaba tomonidan test topshirilishi va darhol to'liq pedagogik tahlil qaytarilishi.
    """
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id).first()
    if not m or m.material_type != "test":
        raise HTTPException(status_code=404, detail="Test topilmadi.")

    content = m.content_json or {}
    questions = content.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Ushbu testda savollar mavjud emas.")

    ans_map = {}
    if isinstance(payload.answers, dict):
        ans_map = {str(k): int(v) for k, v in payload.answers.items()}
    elif isinstance(payload.answers, list):
        for a in payload.answers:
            if isinstance(a, dict):
                ans_map[str(a.get("question_id"))] = int(a.get("selected_index", -1))
            elif hasattr(a, "question_id"):
                ans_map[str(a.question_id)] = int(a.selected_index)

    correct_count = 0
    reviews = []

    for q in questions:
        qid = q["id"]
        corr_idx = int(q.get("correct_index", 0))
        sel_idx = ans_map.get(qid)
        is_corr = (sel_idx is not None and sel_idx == corr_idx)

        if is_corr:
            correct_count += 1

        opts = q.get("options", [])
        sel_text = opts[sel_idx] if sel_idx is not None and 0 <= sel_idx < len(opts) else "Belgilanmagan"
        corr_text = opts[corr_idx] if 0 <= corr_idx < len(opts) else ""

        reviews.append({
            "id": qid,
            "question_id": qid,
            "question": q.get("question", ""),
            "options": opts,
            "selected_index": sel_idx,
            "student_answer_idx": sel_idx,
            "correct_index": corr_idx,
            "is_correct": is_corr,
            "selected_text": sel_text,
            "correct_text": corr_text,
            "explanation": q.get("explanation", "Mavzuga mos to'g'ri javob.")
        })

    total_q = len(questions)
    percentage = int(round((correct_count / total_q) * 100)) if total_q > 0 else 0
    grade = "A'lo (5)" if percentage >= 86 else ("Yaxshi (4)" if percentage >= 71 else ("Qoniqarli (3)" if percentage >= 55 else "Qoniqarsiz (2)"))
    passed = percentage >= 60

    attempt = matsvc.record_attempt(
        db, current_user, m, status="completed", score=percentage,
        correct_count=correct_count, total_count=total_q, passed=passed,
        answers=ans_map, result={"grade": grade, "percentage": percentage},
    )

    return {
        "attempt_id": attempt.id if attempt else None,
        "saved": attempt is not None,
        "material_id": material_id,
        "title": m.title,
        "topic_title": m.topic_title,
        "correct_count": correct_count,
        "correct_answers": correct_count,
        "total_questions": total_q,
        "percentage": percentage,
        "score_percentage": percentage,
        "grade": grade,
        "passed": percentage >= 60,
        "reviews": reviews
    }


class StudentWritingSubmitRequest(BaseModel):
    text: str
    self_rating: Optional[Dict[str, int]] = None  # {"content":1-5, "grammar":..., "lexis":..., "coherence":...}


@router.post("/materials/{material_id}/submit-writing")
async def submit_student_writing(
    material_id: str,
    payload: StudentWritingSubmitRequest,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Yozma topshiriqni topshirish: so'z chegarasi tekshiriladi, AI 4 mezon bo'yicha
    rubrika bilan baholaydi (AI ishlamasa lokal heuristika), natija saqlanadi.
    """
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id).first()
    if not m or m.material_type != "writing":
        raise HTTPException(status_code=404, detail="Yozma topshiriq topilmadi.")
    content = m.content_json or {}
    text = (payload.text or "").strip()
    wc = matsvc.word_count(text)
    min_w = int(content.get("min_words") or 0)
    max_w = int(content.get("max_words") or 0)
    if wc < max(20, min_w // 2):
        raise HTTPException(status_code=400, detail=f"Matn juda qisqa ({wc} so'z). Kamida {min_w} so'z yozing.")

    rubric = await ai_service.evaluate_writing_rubric(
        text=text, topic=m.topic_title, task_prompt=content.get("task_prompt", "")
    )
    # evaluate_writing_rubric total_score ni 0-100 shkalada qaytaradi
    try:
        percentage = int(round(float(rubric.get("total_score"))))
    except (TypeError, ValueError):
        r = rubric.get("rubric") or {}
        percentage = int(round(sum(float((r.get(k) or {}).get("score") or 0) for k in ("content", "grammar", "lexis", "coherence")) / 20 * 100))
    percentage = max(0, min(100, percentage))
    passed = percentage >= 60

    length_note = None
    if min_w and wc < min_w:
        length_note = f"So'z soni ({wc}) talabdan ({min_w}) kam."
    elif max_w and wc > max_w:
        length_note = f"So'z soni ({wc}) chegaradan ({max_w}) ko'p."

    result = {
        "word_count": wc,
        "length_note": length_note,
        "rubric": rubric.get("rubric"),
        "total_score": percentage,
        "max_score": 100,
        "cefr_estimate": rubric.get("cefr_estimate"),
        "strengths": rubric.get("strengths") or [],
        "improvements": rubric.get("improvements") or [],
        "overall_comment": rubric.get("overall_comment") or "",
        "ai_generated": bool(rubric.get("ai_powered")),
        "model": rubric.get("model"),
        "self_rating": payload.self_rating,
    }
    attempt = matsvc.record_attempt(
        db, current_user, m, status="completed", score=percentage, correct_count=None,
        total_count=None, passed=passed, answers={"text": text, "self_rating": payload.self_rating}, result=result,
    )
    return {
        "attempt_id": attempt.id if attempt else None,
        "saved": attempt is not None,
        "material_id": material_id,
        "title": m.title,
        "topic_title": m.topic_title,
        "score_percentage": percentage,
        "passed": passed,
        **result,
    }


@router.post("/materials/{material_id}/mark-viewed")
def mark_material_viewed(
    material_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """Slayd yoki dars rejasi ochilganda "ko'rildi" belgisi (tizimga kirgan talaba uchun)."""
    m = db.query(TeacherMaterial).filter(TeacherMaterial.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material topilmadi.")
    attempt = matsvc.record_attempt(db, current_user, m, status="viewed", score=None)
    return {"status": "success", "saved": attempt is not None, "material_id": material_id}


@router.get("/materials-progress")
def get_student_materials_progress(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """Talabaning mustaqil topshiriqlar bo'yicha umumiy holati (fan bo'yicha yoki barchasi)."""
    if not current_user or current_user.get("role") != "student":
        return {"total": 0, "done": 0, "by_type": {}, "attempts": []}
    q = db.query(TeacherMaterial)
    scope = matsvc.student_subject_scope(db, current_user)
    if subject_id:
        q = q.filter(TeacherMaterial.subject_id == subject_id)
    elif scope is not None:
        q = q.filter(TeacherMaterial.subject_id.in_(scope))
    mats = q.all()
    progress = matsvc.best_attempts(db, current_user.get("id"), [m.id for m in mats])
    by_type: Dict[str, Dict[str, int]] = {}
    for m in mats:
        t = by_type.setdefault(m.material_type, {"total": 0, "done": 0})
        t["total"] += 1
        if m.id in progress:
            t["done"] += 1
    scored = [p["best_score"] for p in progress.values() if p.get("best_score") is not None]
    return {
        "total": len(mats),
        "done": len(progress),
        "average_score": round(sum(scored) / len(scored)) if scored else None,
        "by_type": by_type,
    }
