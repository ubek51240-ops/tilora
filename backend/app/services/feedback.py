import re
from typing import Dict, Any, List, Optional
from app.services.l1 import analyze_l1_interference
from app.services.scoring import score_writing_production
from app.services.text_quality import analyze_text_quality, apply_quality_cap, quality_prompt_hint
from app.services.ai_service import ai_service

COMMON_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "can", "could", "may", "might", "must", "it", "its", "they",
    "them", "their", "we", "us", "our", "you", "your", "he", "him", "his",
    "she", "her", "i", "me", "my", "this", "that", "these", "those", "from",
    "up", "down", "in", "out", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t"
}

ACADEMIC_TRANSITIONS = [
    "furthermore", "moreover", "however", "in addition", "consequently",
    "therefore", "on the other hand", "in contrast", "nevertheless",
    "for instance", "for example", "firstly", "secondly", "finally",
    "in conclusion", "to sum up", "specifically", "additionally",
    "meanwhile", "subsequently", "as a result"
]

ASSESSMENT_TOPIC_KEYWORDS = [
    "assessment", "criteria", "criterion", "rubric", "evaluation",
    "validity", "reliability", "scoring", "feedback", "formative",
    "summative", "accuracy", "fluency", "coherence", "lexical", "proficiency"
]

def analyze_production_heuristics(text: str) -> Dict[str, Any]:
    """
    Talabaning haqiqiy matnini to'liq o'qib, mahalliy pedagogik va lingvistik mezonlar
    (L1 interferensiyasi, so'z takrorlari, xatboshi ko'priklari, hajm va terminologiya)
    asosida dinamik tahlil o'tkazish.
    """
    clean_text = text.strip()
    words = re.findall(r"\b[A-Za-z'-]+\b", clean_text)
    word_count = len(words)
    paragraphs = [p.strip() for p in clean_text.split("\n") if p.strip()]
    num_paragraphs = len(paragraphs)
    
    # 0. Matn sifati: ma'nosiz harflar, tushunarsiz so'z va gaplar (har doim birinchi)
    quality = analyze_text_quality(clean_text)
    feedback_items = []
    if quality["suspicious_tokens"]:
        toks = quality["suspicious_tokens"]
        listed = ", ".join(f"'{t['token']}' ({t['reason']})" for t in toks[:10])
        more = f" va yana {len(toks) - 10} ta" if len(toks) > 10 else ""
        feedback_items.append({
            "id": "fb_q_tokens",
            "cat": "lexis",
            "badge": "Matn sifati · Ma'nosiz harflar",
            "title": f"{quality['nonsense_count']} ta tushunarsiz so'z / harf ketma-ketligi topildi",
            "matched_text": ", ".join(t["token"] for t in toks[:8]),
            "reason": f"Quyidagi belgilar ketma-ketligi inglizcha so'z emas: {listed}{more}. Bunday so'zlar matn ma'nosini buzadi va mazmun, grammatika hamda leksika ballarini pasaytiradi.",
            "suggestion": "Har bir so'zni qayta o'qib chiqing; tasodifiy bosilgan harflarni o'chiring yoki to'g'ri so'z bilan almashtiring."
        })
    for i, ns in enumerate(quality["nonsense_sentences"][:3], 1):
        feedback_items.append({
            "id": f"fb_q_sent_{i}",
            "cat": "coherence",
            "badge": "Matn sifati · Tushunarsiz gap",
            "title": "Ma'nosi tushunarsiz gap",
            "matched_text": ns["text"][:90],
            "reason": f"Ushbu gap o'quvchiga tushunarli emas: {ns['reason']}. Baholovchi bunday gapni bajarilmagan deb hisoblaydi.",
            "suggestion": "Gapni ega, kesim va bog'lovchilar bilan qayta tuzing; har bir so'z ma'noli bo'lsin."
        })

    # 1. L1 interferensiya xatolarini tekshirish
    l1_findings = analyze_l1_interference(clean_text)
    
    for idx, item in enumerate(l1_findings, 1):
        cat = item.get("category", "grammar")
        badge = f"{cat.capitalize()} · L1 interferensiyasi"
        matched = item.get("matched_text", "")
        feedback_items.append({
            "id": f"fb_l1_{idx}",
            "cat": cat,
            "badge": badge,
            "title": item.get("issue_short", "L1 interferensiyasi aniqlandi"),
            "matched_text": matched,
            "reason": item.get("issue_reason", "Ona tili sintaktik ta'siri."),
            "suggestion": item.get("suggestion", "")
        })
        
    # 2. Takroriy so'zlar (Lexical repetitiveness) - haqiqiy matndan sanash
    lower_words = [w.lower() for w in words if len(w) > 3 and w.lower() not in COMMON_STOPWORDS]
    freq_map: Dict[str, int] = {}
    for w in lower_words:
        freq_map[w] = freq_map.get(w, 0) + 1
        
    repeated = [(w, c) for w, c in freq_map.items() if c >= 3]
    repeated.sort(key=lambda x: x[1], reverse=True)
    
    for r_word, r_count in repeated[:2]:
        feedback_items.append({
            "id": f"fb_rep_{r_word}",
            "cat": "lexis",
            "badge": "Leksika · Akademik uslub",
            "title": f"'{r_word}' so'zi {r_count} marta takrorlangan",
            "matched_text": r_word,
            "reason": f"Akademik inshoda bitta so'zning qisqa hajmda {r_count} marta takror qo'llanilishi leksik rang-baranglik (Lexical Resource) darajasini pasaytiradi.",
            "suggestion": f"'{r_word}' so'zi o'rniga sinonimlardan va akademik muqobil iboralardan foydalaning."
        })
        
    # 3. Izchillik va bog'lovchi ko'priklar (Coherence & Cohesion)
    text_lower = clean_text.lower()
    used_transitions = [tr for tr in ACADEMIC_TRANSITIONS if tr in text_lower]
    
    if num_paragraphs >= 2 and len(used_transitions) < 2:
        feedback_items.append({
            "id": "fb_coh_trans",
            "cat": "coherence",
            "badge": "Izchillik · Mantiqiy ko'prik",
            "title": "Xatboshilar o'rtasida mantiqiy bog'lovchilar yetishmaydi",
            "matched_text": "",
            "reason": "Fikrlar va abzaslar o'rtasida transitional so'zlar (Furthermore, However, Consequently, In addition) qo'llanilmaganda, argumentlar o'rtasidagi sabab-oqibat mantiqi zaiflashadi.",
            "suggestion": "Har bir yangi fikr yoki argument boshlanishida munosib bog'lovchi so'zlardan foydalaning."
        })
    elif num_paragraphs <= 1 and word_count >= 80:
        feedback_items.append({
            "id": "fb_coh_para",
            "cat": "coherence",
            "badge": "Izchillik · Matn tuzilishi",
            "title": "Matn xatboshilarga (abzaslarga) ajratilmagan",
            "matched_text": "",
            "reason": "Yozma nutq baholash tahlili yaxlit bir blokda emas, kirish, tahlil va xulosa kabi aniq xatboshilarda bayon etilishi lozim.",
            "suggestion": "Matningizni kamida 2 yoki 3 ta mantiqiy xatboshiga ajrating."
        })
        
    # 4. Topshiriq sharti va hajm tahlili (Task Achievement)
    if word_count < 100:
        feedback_items.append({
            "id": "fb_cnt_short",
            "cat": "content",
            "badge": "Mazmun · Topshiriq hajmi",
            "title": f"Matn hajmi talabdan ancha qisqa ({word_count} so'z)",
            "matched_text": "",
            "reason": f"Topshiriq shartida 150–180 so'z talab qilingan. Hozirgi {word_count} ta so'z barcha baholash mezonlarini to'liq ochib berish uchun yetarli emas.",
            "suggestion": "Baholash mezonlari (Accuracy, Fluency, Coherence) bo'yicha aniq misollar qo'shib, fikringizni rivojlantiring."
        })
    elif word_count > 250:
        feedback_items.append({
            "id": "fb_cnt_long",
            "cat": "content",
            "badge": "Mazmun · Ixchamlik",
            "title": f"Matn hajmi me'yordan ortiq ({word_count} so'z)",
            "matched_text": "",
            "reason": "Talab etilgan hajm 150–180 so'z. Qisqa va lo'nda tahlil yozish akademik kompetensiyaning muhim qismidir.",
            "suggestion": "Ortiqcha takroriy jumlalarni qisqartirib, eng asosiy fikrlarga e'tibor qarating."
        })
        
    # 5. Mavzuga oid kasbiy leksika (Topic Keywords)
    used_keywords = [kw for kw in ASSESSMENT_TOPIC_KEYWORDS if kw in text_lower]
    if len(used_keywords) < 2 and word_count >= 30:
        feedback_items.append({
            "id": "fb_lex_topic",
            "cat": "content",
            "badge": "Mazmun · Kasbiy terminologiya",
            "title": "Baholash mezonlariga oid maxsus terminlar yetarli emas",
            "matched_text": "",
            "reason": "Ushbu darsning asosiy maqsadi yozma nutqni baholash rubrikalari va mezonlarini tahlil qilishdir. Matnda soha terminlari deyarli ishlatilmagan.",
            "suggestion": "'rubric', 'formative assessment', 'validity', 'scoring criteria' kabi terminlarni matningizga kiriting."
        })

    # Agar umuman kamchilik topilmasa (mukammal matn):
    if not feedback_items:
        feedback_items.append({
            "id": "fb_pos_1",
            "cat": "content",
            "badge": "Mazmun va Uslub · Ijobiy",
            "title": "Akademik mezonlarga to'liq muvofiq",
            "matched_text": "",
            "reason": "Matnda jiddiy L1 interferensiyasi kuzatilmadi, hajm talabi bajarilgan va mantiqiy bog'lanish saqlangan.",
            "suggestion": "Keyingi bosqichlarda yanada murakkab sintaktik tuzilmalarni sinab ko'rishingiz mumkin."
        })
        
    # Haqiqiy hisoblangan ball (matn sifati jarimasi bilan)
    score_data = score_writing_production(clean_text, len(l1_findings), quality=quality)
    
    # Izchillik balini xatboshilar va transitional connectors ga qarab moslash
    if len(used_transitions) >= 2 and num_paragraphs >= 2:
        coh = 5
    elif num_paragraphs >= 2 or len(used_transitions) >= 1:
        coh = 4
    else:
        coh = 3
    score_data["rubric"]["coherence"] = max(1, coh - quality["penalty"].get("coherence", 0))
        
    # Total scoreni yangilash
    rub = score_data["rubric"]
    score_data["total_score"] = int(((rub["content"] + rub["grammar"] + rub["lexis"] + rub["coherence"]) / 20) * 100)
    
    return {
        "score_data": score_data,
        "feedback_items": feedback_items,
        "text_quality": quality
    }

async def analyze_production_feedback_async(text: str, lesson_id: str = "5") -> Dict[str, Any]:
    """
    Talaba yozma ishini AI va L1 interferensiya moduli orqali chuqur tahlil qilish.
    """
    # 1. Matnni so'zma-so'z to'liq o'qib chiqish (Lokal mezonlar va L1)
    heuristics = analyze_production_heuristics(text)
    
    # 2. DeepSeek AI ga ulanib ko'rish
    quality = heuristics["text_quality"]
    try:
        ai_result = await ai_service.analyze_student_essay_structured(
            text=text,
            topic="Yozma nutq baholash mezonlari (Writing Assessment Rubrics)",
            quality_hint=quality_prompt_hint(quality)
        )
    except Exception:
        ai_result = {"ai_powered": False}
        
    if ai_result.get("ai_powered") and ai_result.get("items"):
        ai_items = []
        for idx, it in enumerate(ai_result["items"], 1):
            ai_items.append({
                "id": f"fb_ai_{idx}",
                "cat": it.get("category", "grammar"),
                "badge": it.get("badge", "DeepSeek AI · Lingvistik tahlil"),
                "title": it.get("title", "Uslubiy tavsiya"),
                "matched_text": it.get("matched_text", ""),
                "reason": it.get("issue_reason", it.get("reason", "")),
                "suggestion": it.get("suggestion", "")
            })
            
        # Matn sifati topilmalari (ma'nosiz so'z/gaplar) har doim ro'yxat boshida turadi
        quality_items = [h for h in heuristics["feedback_items"] if h["id"].startswith("fb_q_")]
        ai_items = quality_items + ai_items

        # L1 interferensiya qoidalaridan ham qo'shish (agar AI e'tibor bermagan bo'lsa)
        for h_item in heuristics["feedback_items"]:
            if "l1" in h_item["id"]:
                already = any(
                    h_item.get("matched_text", "").lower() in a_it.get("matched_text", "").lower()
                    for a_it in ai_items if a_it.get("matched_text")
                )
                if not already:
                    ai_items.append(h_item)
                    
        # AI rubrikasi matn sifati cheklovi bilan (ma'nosiz matnga yuqori ball bo'lmaydi)
        rub = apply_quality_cap(ai_result.get("rubric", heuristics["score_data"]["rubric"]), quality)
        tot = int(round(sum(rub.values()) / 20 * 100)) if quality["level"] != "ok" else ai_result.get("total_score", heuristics["score_data"]["total_score"])
        
        return {
            "ai_powered": True,
            "model": ai_result.get("model", ai_service.model),
            "score_data": {
                "total_score": tot,
                "word_count": len(re.findall(r"\b\w+\b", text)),
                "rubric": rub,
                "text_quality": quality
            },
            "feedback_items": ai_items,
            "summary": ai_result.get("summary", "DeepSeek AI matnni to'liq o'qib tahlil qildi.")
        }
        
    # Agar AI bo'sh bo'lsa (masalan API balans 0 yoki oflayn), to'liq o'qilgan dinamik tahlil qaytariladi
    return {
        "ai_powered": False,
        "score_data": heuristics["score_data"],
        "feedback_items": heuristics["feedback_items"],
        "summary": "Matn barcha mezonlar (L1 interferensiyasi, so'z boyligi, takrorlar va izchillik) bo'yicha to'liq o'qib chiqildi."
    }

def generate_production_feedback(text: str) -> Dict[str, Any]:
    """
    Sinxron chaqiruvlar uchun dinamik tahlil.
    """
    return analyze_production_heuristics(text)
