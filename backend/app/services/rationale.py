def build_rationale(skill: str, level: str, anxiety: int, scaffold: str, professional_track: str) -> str:
    """
    2-QOIDA: Tizim hech qachon o'z qarorini yashirmaydi.
    Sabab LLM tomonidan emas, deterministik shablondan yig'iladi (shaffoflik va tekshiriluvchanlik).
    """
    parts = []
    
    # 1. Ko'nikma va daraja asosi
    parts.append(f"Mazkur o'quv birligi {skill.upper()} ko'nikmasi bo'yicha joriy {level} darajangizga moslashtirildi.")
    
    # 2. Tashvish darajasi ta'siri
    if anxiety > 65:
        parts.append(f"Chet tili tashvishi yuqori ({anxiety}/100) bo'lgani sababli, topshiriq kichik hajmli va xatoga yo'l qo'yish erkin bo'lgan xavfsiz muhitda rejalashtirildi.")
    else:
        parts.append(f"Affektiv xotirjamlik ({anxiety}/100) yuqori sur'atda faol kommunikativ topshiriqlarni bajarish imkonini beradi.")
        
    # 3. Ko'mak (scaffold) darajasi asosi
    if scaffold == "full":
        parts.append("Dastlabki mustahkam poydevor uchun to'liq texnologik ko'mak (namuna, lug'at va tarkibiy tuzilma) berildi.")
    elif scaffold == "partial":
        parts.append("Oldingi mashg'ulotlardagi ijobiy dinamika hisobga olinib, ko'mak qisman darajaga tushirildi (faqat leksik qo'llanma).")
    else:
        parts.append("Talaba mustaqil strategiyalarni to'liq egallagani uchun ko'mak olib tashlandi (avtonom rejim).")
        
    # 4. Kasbiy yo'nalish
    parts.append(f"Mavzu mazmuni bo'lajak kasbingiz — '{professional_track}' kontekstiga to'liq yo'naltirildi.")
    
    return " ".join(parts)
