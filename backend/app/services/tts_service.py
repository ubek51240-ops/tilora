"""
Matnni ovozga aylantirish (TTS) xizmati.

O'qituvchi ovozli diagnostika savoli uchun audio fayl yuklash o'rniga matn yozsa,
shu modul matnni mp3 ga aylantiradi. Asosiy provayder — Microsoft Edge neyron
ovozlari (`edge-tts` paketi): API kalit talab qilmaydi, faqat internet kerak.

Chat-AI provayderi (api.b.ai) faqat /chat/completions va /images yo'llarini
ochgan, /audio/speech 403 qaytaradi, shuning uchun u bu yerda ishlatilmaydi.
"""
import asyncio
from typing import Dict, List, Optional

# Ovozlar ro'yxati: qiymat — edge-tts ovoz nomi, label — UI da ko'rinadigan nom.
VOICES: List[Dict[str, str]] = [
    {"id": "en-US-AriaNeural", "label": "Aria — AQSh ingliz (ayol)", "lang": "en"},
    {"id": "en-US-GuyNeural", "label": "Guy — AQSh ingliz (erkak)", "lang": "en"},
    {"id": "en-GB-SoniaNeural", "label": "Sonia — Britaniya ingliz (ayol)", "lang": "en"},
    {"id": "en-GB-RyanNeural", "label": "Ryan — Britaniya ingliz (erkak)", "lang": "en"},
    {"id": "en-AU-NatashaNeural", "label": "Natasha — Avstraliya ingliz (ayol)", "lang": "en"},
    {"id": "uz-UZ-MadinaNeural", "label": "Madina — o'zbek (ayol)", "lang": "uz"},
    {"id": "uz-UZ-SardorNeural", "label": "Sardor — o'zbek (erkak)", "lang": "uz"},
    {"id": "ru-RU-SvetlanaNeural", "label": "Svetlana — rus (ayol)", "lang": "ru"},
]
DEFAULT_VOICE = "en-US-AriaNeural"
VOICE_IDS = {v["id"] for v in VOICES}

MAX_TTS_CHARS = 3000
# Tinglab tushunish savollari uchun biroz sekinroq nutq qulay
DEFAULT_RATE = "-5%"


class TTSError(Exception):
    """Foydalanuvchiga ko'rsatiladigan TTS xatosi."""


def list_voices() -> List[Dict[str, str]]:
    return list(VOICES)


def voice_label(voice_id: str) -> str:
    for v in VOICES:
        if v["id"] == voice_id:
            return v["label"].split(" — ")[0]
    return voice_id


def _validate(text: str, voice: Optional[str]) -> str:
    text = (text or "").strip()
    if not text:
        raise TTSError("Ovozga aylantirish uchun matn bo'sh.")
    if len(text) > MAX_TTS_CHARS:
        raise TTSError(f"Matn juda uzun ({len(text)} belgi). Chegara: {MAX_TTS_CHARS} belgi.")
    v = voice or DEFAULT_VOICE
    if v not in VOICE_IDS:
        raise TTSError(f"Noma'lum ovoz: {v}")
    return v


async def synthesize(text: str, voice: Optional[str] = None, rate: str = DEFAULT_RATE) -> bytes:
    """Matnni mp3 baytlariga aylantiradi. Xato bo'lsa TTSError ko'taradi."""
    voice_id = _validate(text, voice)
    try:
        import edge_tts  # noqa: WPS433 — ixtiyoriy bog'liqlik, faqat kerak bo'lganda yuklanadi
    except ImportError:
        raise TTSError("TTS moduli o'rnatilmagan. Serverda `pip install edge-tts` bajaring.")

    chunks: List[bytes] = []
    try:
        communicate = edge_tts.Communicate(text.strip(), voice_id, rate=rate)
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                chunks.append(chunk["data"])
    except asyncio.TimeoutError:
        raise TTSError("TTS xizmati javob bermadi (vaqt tugadi). Internetni tekshiring.")
    except Exception as e:  # tarmoq / xizmat xatolari
        raise TTSError(f"Ovoz yaratib bo'lmadi: {e.__class__.__name__}: {e}")

    audio = b"".join(chunks)
    if not audio:
        raise TTSError("TTS xizmati bo'sh audio qaytardi. Matnni yoki ovozni o'zgartirib ko'ring.")
    return audio
