"""
Yozma matn uchun lokal (AI'siz) CEFR bahosi va topshiriqqa moslik ko'rsatkichi.

Write & Improve (Cambridge) kabi tizimlar har topshiriqdan so'ng CEFR darajasini va "prompt relevance"
ko'rsatkichini beradi. Bu modul shunga o'xshash, lekin shaffof (sabablari ko'rsatiladi) va deterministik
heuristika: hajm, gap uzunligi, leksik rang-baranglik (TTR), akademik bog'lovchilar, uzun so'zlar ulushi,
L1 xatolar zichligi. Natija "taxminiy" deb belgilanadi — yakuniy darajani o'qituvchi belgilaydi (3-qoida).
"""
import re
from typing import Dict, Any, List, Optional

ACADEMIC_MARKERS = ["furthermore", "moreover", "however", "therefore", "consequently", "nevertheless", "in addition",
                    "in contrast", "whereas", "although", "thus", "hence", "for instance", "in conclusion", "to sum up",
                    "on the other hand", "as a result", "in particular", "specifically", "subsequently"]
COMPLEX_MARKERS = ["which", "that", "because", "while", "whereas", "although", "unless", "provided", "despite", "in spite of",
                   "not only", "so that", "in order to", "rather than", "would", "could", "might", "should"]

LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1"]


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def estimate_cefr(text: str, l1_error_count: int = 0, quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    words = re.findall(r"\b[A-Za-z'-]+\b", text)
    n = len(words)
    if n < 15:
        return {"level": "A1", "confidence": "past", "score": 0, "reasons": ["Matn juda qisqa (15 so'zdan kam) — baholash uchun yetarli emas."], "metrics": {"words": n}, "note": "Taxminiy lokal baho."}
    sents = _sentences(text)
    avg_sent = n / max(1, len(sents))
    unique = {w.lower() for w in words}
    ttr = len(unique) / n
    long_ratio = sum(1 for w in words if len(w) >= 8) / n
    low = text.lower()
    acad = sum(1 for m in ACADEMIC_MARKERS if m in low)
    complex_ = sum(1 for m in COMPLEX_MARKERS if re.search(r"\b" + re.escape(m) + r"\b", low))
    err_density = l1_error_count / max(1, n / 100)  # 100 so'zga xatolar
    nonsense = (quality or {}).get("nonsense_count", 0)

    # 0–100 ball: har mezon o'z hissasini qo'shadi
    score = 0.0
    reasons = []
    # hajm
    if n >= 180: score += 20; reasons.append(f"Hajm yetarli ({n} so'z).")
    elif n >= 120: score += 15; reasons.append(f"Hajm o'rtacha ({n} so'z).")
    elif n >= 60: score += 8; reasons.append(f"Hajm kichik ({n} so'z).")
    else: score += 3; reasons.append(f"Hajm juda kichik ({n} so'z).")
    # gap uzunligi (B2+: 15–22 so'z)
    if 14 <= avg_sent <= 24: score += 18; reasons.append(f"Gap uzunligi akademik me'yorda (o'rtacha {avg_sent:.0f} so'z).")
    elif 10 <= avg_sent < 14 or 24 < avg_sent <= 30: score += 11; reasons.append(f"Gap uzunligi o'rtacha {avg_sent:.0f} so'z.")
    else: score += 5; reasons.append(f"Gaplar juda qisqa yoki juda uzun (o'rtacha {avg_sent:.0f} so'z).")
    # TTR
    if ttr >= 0.6: score += 18; reasons.append(f"Leksik rang-baranglik yuqori (TTR {ttr:.2f}).")
    elif ttr >= 0.45: score += 12; reasons.append(f"Leksik rang-baranglik o'rtacha (TTR {ttr:.2f}).")
    else: score += 5; reasons.append(f"So'zlar ko'p takrorlanadi (TTR {ttr:.2f}).")
    # akademik bog'lovchilar
    if acad >= 4: score += 15; reasons.append(f"Akademik bog'lovchilar faol ({acad} ta).")
    elif acad >= 2: score += 10; reasons.append(f"Bir nechta akademik bog'lovchi ({acad} ta).")
    else: score += 3; reasons.append("Akademik bog'lovchilar deyarli yo'q.")
    # murakkab sintaksis
    if complex_ >= 5: score += 14; reasons.append(f"Murakkab sintaksis belgilari ({complex_} ta).")
    elif complex_ >= 2: score += 8; reasons.append(f"Qisman murakkab sintaksis ({complex_} ta).")
    else: score += 2; reasons.append("Asosan sodda gaplar.")
    # uzun so'zlar
    if long_ratio >= 0.22: score += 10; reasons.append(f"Akademik (uzun) so'zlar ulushi yuqori ({long_ratio:.0%}).")
    elif long_ratio >= 0.14: score += 6; reasons.append(f"Uzun so'zlar ulushi o'rtacha ({long_ratio:.0%}).")
    else: score += 2
    # xatolar jarimasi
    pen = min(30, err_density * 6 + nonsense * 3)
    if pen:
        reasons.append(f"Xatolar jarimasi: L1 xatolar {l1_error_count} ta (100 so'zga {err_density:.1f}), tushunarsiz so'zlar {nonsense} ta.")
    score = max(0.0, score - pen)

    if score >= 78: level = "C1"
    elif score >= 58: level = "B2"
    elif score >= 36: level = "B1"
    elif score >= 18: level = "A2"
    else: level = "A1"
    conf = "yuqori" if n >= 120 and nonsense == 0 else ("o'rta" if n >= 60 else "past")
    return {"level": level, "confidence": conf, "score": int(round(score)), "reasons": reasons,
            "metrics": {"words": n, "sentences": len(sents), "avg_sentence_len": round(avg_sent, 1), "ttr": round(ttr, 2),
                        "academic_markers": acad, "complex_markers": complex_, "long_word_ratio": round(long_ratio, 2),
                        "l1_errors_per_100": round(err_density, 1)},
            "note": "Taxminiy lokal baho (AI'siz, deterministik). Yakuniy CEFR darajasini o'qituvchi belgilaydi."}


def relevance_score(text: str, task_keywords: List[str], task_prompt: str = "") -> Dict[str, Any]:
    """Topshiriqqa moslik (prompt relevance): kalit so'zlar va topshiriq matnidagi muhim so'zlarning qamrovi."""
    low = text.lower()
    kws = [k.lower() for k in (task_keywords or []) if k]
    prompt_words = {w for w in re.findall(r"\b[a-z]{6,}\b", (task_prompt or "").lower())} - {"should", "students", "learners", "writing", "between"}
    hit_k = [k for k in kws if k in low]
    hit_p = [w for w in prompt_words if w in low]
    k_part = (len(hit_k) / len(kws)) if kws else 0.5
    p_part = (len(hit_p) / len(prompt_words)) if prompt_words else 0.5
    score = int(round((0.65 * k_part + 0.35 * p_part) * 100))
    return {"score": max(0, min(100, score)), "matched_keywords": hit_k, "missing_keywords": [k for k in kws if k not in hit_k][:8],
            "note": "Topshiriq mavzusiga moslik: kasbiy terminlar va topshiriq so'zlarining qamrovi."}
