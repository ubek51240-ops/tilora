"""
Matn sifati tahlili: talaba yozgan matndagi ma'nosiz harf ketma-ketliklari,
tushunarsiz so'zlar va gaplarni topish hamda baholash uchun jarima hisoblash.

AI kalitisiz, lokal ishlaydi. Natija AI promptiga ham uzatiladi, AI bahosi
ustidan "shift" (cheklov) sifatida ham qo'llanadi.
"""
import os
import re
from functools import lru_cache
from typing import Dict, Any, List, Set, Tuple

_CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

VOWELS = set("aeiouy")
FUNCTION_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "as",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must", "it", "its", "they",
    "them", "their", "we", "us", "our", "you", "your", "he", "him", "his", "she", "her", "i", "me",
    "my", "this", "that", "these", "those", "from", "not", "no", "so", "if", "than", "then", "there",
    "when", "which", "who", "what", "how", "also", "such", "into", "about", "because", "while",
}
# Dars mavzusiga oid va lug'atda bo'lmasligi mumkin bo'lgan atamalar
EXTRA_WORDS = {
    "rubric", "rubrics", "formative", "summative", "scaffolding", "scaffold", "cefr", "ielts", "toefl",
    "learners", "learner", "pedagogical", "pedagogy", "metacognitive", "metacognition", "cohesion",
    "coherence", "lexical", "lexis", "syntactic", "syntax", "grammatical", "fluency", "accuracy",
    "validity", "reliability", "washback", "descriptor", "descriptors", "holistic", "analytic",
    "criteria", "criterion", "assessor", "assessors", "feedback", "self-assessment", "peer",
    "interference", "l1", "l2", "efl", "esl", "elt", "tkt", "celta", "collocation", "collocations",
    "paraphrase", "paraphrasing", "plagiarism", "citation", "citations", "hedging", "discourse",
    "intonation", "pronunciation", "morphology", "sociolinguistic", "communicative", "authentic",
    "uzbek", "uzbekistan", "tashkent", "tilora", "essay", "essays", "portfolio", "rater", "raters",
}
KEYBOARD_RUNS = ["qwert", "werty", "ertyu", "rtyui", "tyuio", "yuiop", "asdf", "sdfg", "dfgh", "fghj",
                 "ghjk", "hjkl", "zxcv", "xcvb", "cvbn", "vbnm", "qazw", "wsxe", "edcr", "rfvt",
                 "tgby", "yhnu", "ujmi", "ikol", "lkjh", "poiu", "mnbv", "fdsa"]
# Inglizchada tabiiy uchraydigan uzun undosh birikmalar (jarima berilmaydi)
OK_CONSONANT_CLUSTERS = ("ngth", "tchs", "ghts", "rths", "rtsm", "nths", "lfth", "ckst", "rldw", "ngst", "rstw")


@lru_cache(maxsize=1)
def _dictionary() -> Tuple[Set[str], Set[str]]:
    """(so'zlar to'plami, so'zlardagi harf juftliklari to'plami)"""
    words: Set[str] = set(EXTRA_WORDS) | set(FUNCTION_WORDS)
    path = os.path.join(_CONTENT_DIR, "english_words_10k.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w:
                    words.add(w)
    bigrams: Set[str] = set()
    for w in words:
        w2 = re.sub(r"[^a-z]", "", w)
        for i in range(len(w2) - 1):
            bigrams.add(w2[i:i + 2])
    return words, bigrams


def _stems(token: str) -> List[str]:
    """Oddiy morfologik qisqartmalar: learners -> learner, learn; studied -> studi, study ..."""
    out = [token]
    for suf in ("'s", "s'", "es", "s", "ed", "d", "ing", "ly", "er", "est", "ness", "ment", "tion", "al", "ful", "less", "ity", "ies"):
        if token.endswith(suf) and len(token) - len(suf) >= 3:
            base = token[: -len(suf)]
            out.append(base)
            if suf == "ies":
                out.append(base + "y")
            if suf in ("ing", "ed", "er", "est") and len(base) >= 3 and base[-1] == base[-2]:
                out.append(base[:-1])  # running -> run
            if suf in ("ing", "ed", "er") :
                out.append(base + "e")  # making -> make
    return out


def classify_token(raw: str) -> Tuple[str, str]:
    """
    -> ("valid" | "unknown" | "nonsense", sabab)
    valid: lug'atda bor; unknown: lug'atda yo'q, lekin inglizcha ko'rinishda;
    nonsense: ma'nosiz harflar ketma-ketligi.
    """
    words, bigrams = _dictionary()
    t = raw.lower().strip("'-")
    letters = re.sub(r"[^a-z]", "", t)
    if not letters:
        if re.search(r"[Ѐ-ӿ]", raw):
            return "nonsense", "kirill alifbosidagi so'z (inglizcha matn kutiladi)"
        return "valid", ""
    if len(letters) <= 1:
        return ("valid", "") if letters in ("a", "i") else ("unknown", "")
    for s in _stems(t):
        if s in words:
            return "valid", ""
    if raw[0].isupper() and raw[1:].islower() and len(letters) >= 3 and all(b in bigrams for b in (letters[i:i+2] for i in range(len(letters)-1))):
        return "unknown", "atoqli ot bo'lishi mumkin"

    # --- Ma'nosizlik belgilari ---
    if re.search(r"(.)\1\1", letters):
        return "nonsense", "bir harf ketma-ket 3+ marta takrorlangan"
    if len(letters) >= 4 and not any(c in VOWELS for c in letters):
        return "nonsense", "unli harflar yo'q"
    if any(k in letters for k in KEYBOARD_RUNS):
        return "nonsense", "klaviatura qatori ketma-ketligi"
    vowel_ratio = sum(1 for c in letters if c in VOWELS) / len(letters)
    if len(letters) >= 6 and vowel_ratio < 0.2:
        return "nonsense", "unli harflar juda kam"
    if len(letters) >= 5 and vowel_ratio > 0.8:
        return "nonsense", "deyarli faqat unli harflar"
    cons_runs = re.findall(r"[^aeiouy]{5,}", letters)
    if cons_runs and not any(c in letters for c in OK_CONSONANT_CLUSTERS):
        return "nonsense", f"uzun undosh birikmasi '{cons_runs[0]}'"
    unseen = [letters[i:i+2] for i in range(len(letters) - 1) if letters[i:i+2] not in bigrams]
    if unseen:
        return "nonsense", f"inglizchada uchramaydigan harf juftligi '{unseen[0]}'"
    if len(letters) >= 16:
        return "nonsense", "g'ayrioddiy uzun so'z"
    return "unknown", "lug'atda topilmadi"


def analyze_text_quality(text: str) -> Dict[str, Any]:
    clean = (text or "").strip()
    tokens = re.findall(r"[A-Za-zЀ-ӿ][A-Za-zЀ-ӿ'-]*", clean)
    word_count = len(tokens)
    suspicious: List[Dict[str, str]] = []
    unknown: List[str] = []
    valid = 0
    seen_susp: Set[str] = set()
    for tok in tokens:
        kind, reason = classify_token(tok)
        if kind == "valid":
            valid += 1
        elif kind == "unknown":
            unknown.append(tok)
        else:
            if tok.lower() not in seen_susp:
                seen_susp.add(tok.lower())
                suspicious.append({"token": tok, "reason": reason})

    # So'z darajasida takror ("test test test")
    repeats = re.findall(r"\b(\w{2,})(?:\s+\1\b){2,}", clean, flags=re.IGNORECASE)
    for r in repeats[:3]:
        if r.lower() not in seen_susp:
            seen_susp.add(r.lower())
            suspicious.append({"token": r, "reason": "bir so'z ketma-ket 3+ marta takrorlangan"})

    nonsense_count = sum(1 for tok in tokens if tok.lower() in seen_susp)
    ratio = (nonsense_count / word_count) if word_count else 0.0

    # Gap darajasi
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", clean) if s.strip()]
    nonsense_sentences: List[Dict[str, str]] = []
    for sent in sentences:
        toks = re.findall(r"[A-Za-zЀ-ӿ][A-Za-zЀ-ӿ'-]*", sent)
        if len(toks) < 4:
            continue
        bad = sum(1 for t in toks if t.lower() in seen_susp)
        low = [t.lower() for t in toks]
        if bad / len(toks) >= 0.4:
            nonsense_sentences.append({"text": sent[:140], "reason": f"{bad}/{len(toks)} so'z ma'nosiz"})
        elif len(toks) >= 7 and not any(t in FUNCTION_WORDS for t in low):
            nonsense_sentences.append({"text": sent[:140], "reason": "gap tuzilishi yo'q (bog'lovchi/yordamchi so'zlar umuman ishlatilmagan)"})

    # Sifat darajasi va jarima (1-5 ballik mezonlardan ayiriladi)
    if word_count >= 8 and (ratio >= 0.5 or (word_count >= 40 and valid < 20)):
        level = "severe"
        penalty = {"content": 3, "grammar": 3, "lexis": 3, "coherence": 3}
    elif ratio >= 0.25:
        level = "high"
        penalty = {"content": 2, "grammar": 2, "lexis": 2, "coherence": 1}
    elif ratio >= 0.10 or nonsense_count >= 5:
        level = "warning"
        penalty = {"content": 1, "grammar": 1, "lexis": 1, "coherence": 0}
    elif nonsense_count >= 1:
        level = "minor"
        penalty = {"content": 0, "grammar": 1, "lexis": 1, "coherence": 0}
    else:
        level = "ok"
        penalty = {"content": 0, "grammar": 0, "lexis": 0, "coherence": 0}
    if nonsense_sentences:
        penalty["coherence"] = min(4, penalty["coherence"] + (2 if len(nonsense_sentences) >= 3 else 1))
        if level == "ok":
            level = "minor"

    if level == "ok":
        summary = "Ma'nosiz harf ketma-ketliklari topilmadi."
    else:
        summary = (f"{nonsense_count} ta ma'nosiz/tushunarsiz so'z ({int(ratio * 100)}%), "
                   f"{len(nonsense_sentences)} ta tushunarsiz gap aniqlandi. Bu baholarga jarima sifatida qo'shildi.")

    return {
        "word_count": word_count,
        "valid_word_count": valid,
        "unknown_words": unknown[:20],
        "nonsense_count": nonsense_count,
        "gibberish_ratio": round(ratio, 3),
        "suspicious_tokens": suspicious[:25],
        "nonsense_sentences": nonsense_sentences[:5],
        "sentence_count": len(sentences),
        "level": level,
        "penalty": penalty,
        "max_scores": {k: max(1, 5 - v) for k, v in penalty.items()},
        "summary": summary,
    }


def apply_quality_cap(rubric: Dict[str, int], quality: Dict[str, Any]) -> Dict[str, int]:
    """AI yoki lokal rubrikani matn sifati cheklovi bilan pasaytiradi (1..5)."""
    caps = quality.get("max_scores") or {}
    out = {}
    for k, v in rubric.items():
        try:
            v = int(v)
        except (TypeError, ValueError):
            v = 3
        out[k] = max(1, min(5, min(v, caps.get(k, 5))))
    return out


def quality_prompt_hint(quality: Dict[str, Any]) -> str:
    """AI promptiga qo'shiladigan lokal topilmalar."""
    if quality.get("level") == "ok":
        return ""
    toks = ", ".join(f"'{t['token']}'" for t in quality.get("suspicious_tokens", [])[:15])
    sents = "; ".join(f"\"{s['text'][:80]}\"" for s in quality.get("nonsense_sentences", [])[:3])
    hint = (f"\nLOKAL TEKSHIRUV NATIJASI: matnda {quality.get('nonsense_count', 0)} ta ma'nosiz/tushunarsiz so'z "
            f"({int(quality.get('gibberish_ratio', 0) * 100)}%) topildi")
    if toks:
        hint += f": {toks}"
    if sents:
        hint += f". Tushunarsiz gaplar: {sents}"
    hint += (". Bunday harf ketma-ketliklari va ma'nosiz gaplarni XATO deb hisoblang, ularni izohlarda ko'rsating "
             "va barcha mezon ballarini shunga yarasha PASAYTIRING. Ma'nosiz matnga yuqori ball bermang.")
    return hint
