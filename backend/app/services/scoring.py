import re
from typing import Dict, Any

def score_writing_production(text: str, error_count: int, quality: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Yozma ishni ob'ektiv baholash.
    Mezonlar: Mazmun, Grammatik aniqlik, Lug'aviy boylik, Izchillik.
    Matn sifati (ma'nosiz harflar, tushunarsiz so'z/gaplar) jarima sifatida hisobga olinadi:
    faqat haqiqiy so'zlar sanaladi, keyin har mezondan jarima BIR MARTA ayiriladi.
    """
    from app.services.text_quality import analyze_text_quality
    if quality is None:
        quality = analyze_text_quality(text)
    all_words = re.findall(r'\b\w+\b', text)
    bad = {t["token"].lower() for t in quality.get("suspicious_tokens", [])}
    words = [w for w in all_words if w.lower() not in bad]  # faqat ma'noli so'zlar
    word_count = len(words)
    unique_words = set(w.lower() for w in words)

    # Type-Token Ratio (TTR) - leksik rang-baranglik
    ttr = (len(unique_words) / word_count) if word_count > 0 else 0

    # Grammatika bali (1-5)
    if error_count == 0:
        grammar_score = 5
    elif error_count <= 2:
        grammar_score = 4
    elif error_count <= 4:
        grammar_score = 3
    else:
        grammar_score = 2

    # Lug'at bali (1-5)
    if ttr > 0.65:
        lexis_score = 5
    elif ttr > 0.50:
        lexis_score = 4
    elif ttr > 0.35:
        lexis_score = 3
    else:
        lexis_score = 2

    # Mazmun to'liqligi (1-5)
    if word_count >= 150:
        content_score = 5
    elif word_count >= 100:
        content_score = 4
    elif word_count >= 50:
        content_score = 3
    else:
        content_score = 2

    # Izchillik (agar LLM bo'lmasa o'rtacha neytral 4)
    coherence_score = 4

    # Matn sifati jarimasi — bir marta qo'llanadi, 1 dan past tushmaydi
    # (avvalgi versiyada bu blok 4 marta takrorlanib, jarima 4 karra ayirilar edi)
    pen = quality.get("penalty", {})
    content_score = max(1, content_score - pen.get("content", 0))
    grammar_score = max(1, grammar_score - pen.get("grammar", 0))
    lexis_score = max(1, lexis_score - pen.get("lexis", 0))
    coherence_score = max(1, coherence_score - pen.get("coherence", 0))

    total_percentage = int(((grammar_score + lexis_score + content_score + coherence_score) / 20) * 100)

    return {
        "word_count": len(all_words),
        "valid_word_count": word_count,
        "ttr": round(ttr, 2),
        "text_quality": quality,
        "total_score": total_percentage,
        "rubric": {
            "content": content_score,
            "grammar": grammar_score,
            "lexis": lexis_score,
            "coherence": coherence_score
        }
    }
