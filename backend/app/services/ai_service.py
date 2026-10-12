import logging
import random
import re
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings

logger = logging.getLogger("tilora.ai")

def _randomize_question_options(q: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test variantlarini aralashtirish va to'g'ri kalitni tasodifiy A, B, C, D o'rniga joylashtirish.
    To'g'ri javob doimo A bo'lib qolmasligini kafolatlaydi.
    """
    options = q.get("options", [])
    if not options or len(options) < 2:
        return q
    c_idx = q.get("correct_index", 0)
    if not isinstance(c_idx, int) or c_idx < 0 or c_idx >= len(options):
        c_idx = 0
    correct_text = options[c_idx]

    shuffled = list(options)
    random.shuffle(shuffled)
    new_c_idx = shuffled.index(correct_text)

    q["options"] = shuffled
    q["correct_index"] = new_c_idx
    return q


def get_topic_slide_images(topic: str, subject: str, count: int) -> List[str]:
    """
    Mavzuga mos yuqori sifatli akademik/ta'limiy orqa fon rasmlari to'plami.
    Har safar bir xil eski rasmlar aylanib qolmasligi uchun mavzu bo'yicha boyitilgan
    va xilma-xil Unsplash pool'lari.
    """
    import random
    combined = (topic + " " + subject).lower()

    history_keywords = ["tarix", "history", "o'zbekiston", "ark", "yangi tarix", "madaniyat", "meros", "samarkand", "bukhara", "archeology", "ancient", "museum"]
    writing_keywords = ["writing", "yozuv", "eap", "essay", "insho", "paragraph", "thesis", "plagiarism", "citation", "apa", "abstract", "literature", "adabiyot", "academic", "maqola", "til", "tilshunoslik", "linguistics", "language"]
    discourse_keywords = ["discourse", "nutq", "muloqot", "pedagog", "talk", "classroom", "instruction", "icq", "question", "anxiety", "flcas", "filter", "peer", "teaching", "interaction", "auditoriya", "dars", "metodika", "seminar"]
    psychology_keywords = ["psixolog", "psychology", "miya", "brain", "mental", "kognitiv", "hissiyot", "xulq", "temperament", "xarakter", "shaxs", "motivation"]
    it_keywords = ["it", "kompyuter", "dastur", "algoritm", "ai", "texnologiya", "software", "code", "raqamli", "data", "sun'iy intellekt", "kiber", "tarmoq"]
    science_keywords = ["fizika", "kimyo", "biologiya", "science", "laboratoriya", "tabiat", "tibbiyot", "anatomiya", "ekologiya", "geografiya", "formula"]
    economics_keywords = ["iqtisod", "moliya", "biznes", "management", "finance", "iqtisodiyot", "bank", "marketing", "investitsiya", "menejment"]
    law_keywords = ["huquq", "qonun", "falsafa", "jamiyat", "siyosat", "law", "justice", "davlat", "konstitutsiya"]
    assessment_keywords = ["assessment", "baholash", "test", "rubric", "diagnostic", "exam", "grading", "portfolio", "nazorat", "monitoring"]

    if any(k in combined for k in history_keywords):
        pool = [
            "https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1590076215667-875d4ef2d7ee?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1518998053901-5348d3961a04?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1572953109213-3be62398eb95?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1582555172866-f73bb12a2ab3?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in psychology_keywords):
        pool = [
            "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1493612276216-ee3925520721?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in it_keywords):
        pool = [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1504639725590-34d0984388bd?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in science_keywords):
        pool = [
            "https://images.unsplash.com/photo-1532094349884-543bc11b234d?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1507668077129-56e32842fceb?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1518152006812-edab29b069ac?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in economics_keywords or k in law_keywords):
        pool = [
            "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in writing_keywords):
        pool = [
            "https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1588072432836-e10032774350?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1471107340929-a87cd0f5b5f3?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in discourse_keywords):
        pool = [
            "https://images.unsplash.com/photo-1577495508048-b635879837f1?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1571260899304-425eee4c7efc?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1600&q=80",
        ]
    elif any(k in combined for k in assessment_keywords):
        pool = [
            "https://images.unsplash.com/photo-1580894732444-8ecded7900cd?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=1600&q=80",
        ]
    else:
        pool = [
            "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1577495508048-b635879837f1?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1455390582262-044cdead277a?auto=format&fit=crop&w=1600&q=80",
            "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?auto=format&fit=crop&w=1600&q=80",
        ]

    # Har doim aynan 1-rasmdan boshlanmasligi uchun tasodifiy offset
    offset = random.randint(0, len(pool) - 1)
    return [pool[(offset + i) % len(pool)] for i in range(count)]


def _extract_json_array(raw: str) -> List[Any]:
    """
    AI javobidan JSON massivni ajratib oladi. Javob markdown ichida bo'lsa yoki
    max_tokens tufayli o'rtasida uzilib qolgan bo'lsa ham, to'liq tugagan
    ob'ektlarni qutqarib qaytaradi.
    """
    import json
    if not raw:
        return []
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    start = text.find("[")
    if start == -1:
        start = text.find("{")
        if start == -1:
            return []
    text = text[start:]
    # 1) To'liq parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("questions") or data.get("slides") or data.get("items") or [data]
        return data if isinstance(data, list) else []
    except Exception:
        pass
    # 2) Uzilgan massiv: to'liq yopilgan ob'ektlarni yig'ish
    items: List[Any] = []
    depth = 0
    obj_start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start != -1:
                chunk = text[obj_start:i + 1]
                try:
                    items.append(json.loads(chunk))
                except Exception:
                    pass
                obj_start = -1
    return items


def _friendly_ai_error(res: Dict[str, Any]) -> str:
    """AI xatosini o'qituvchiga tushunarli tilda qaytaradi."""
    msg = str(res.get("error_message") or "")
    low = msg.lower()
    if res.get("quota_exhausted") or "insufficient" in low or "balance" in low:
        return "AI xizmati hisobida balans tugagan (credit insufficient). AI_API_KEY balansini to'ldiring yoki .env da boshqa kalit bering."
    if "certificate" in low or "ssl" in low:
        return "AI serveriga xavfsiz (HTTPS) ulanish sertifikat xatosi bilan tugadi. Antivirus/proksi HTTPS ni tekshirayotgan bo'lishi mumkin."
    if res.get("error_code") == "timeout":
        return "AI serveri javob bermadi (timeout). Keyinroq qayta urinib ko'ring."
    if res.get("status_code") in (401, 403):
        return "AI kaliti (AI_API_KEY) yaroqsiz yoki ruxsat yo'q."
    return f"AI xizmati xatosi: {msg[:160]}" if msg else "AI xizmati javob qaytarmadi."


def build_ai_image_url(
    prompt: str,
    seed: Optional[int] = None,
    width: int = 1280,
    height: int = 720,
    topic: str = "",
    subject: str = ""
) -> str:
    """
    Slayd uchun AI rasm (pollinations.ai flux modeli, API kalitsiz).
    Har safar unikal tasodifiy seed beriladi, shunda server yoki brauzer keshidan
    eski rasmlar qaytmasdan, aynan mavzuga mos yangi rasm generatsiya qilinadi.
    """
    import random
    from urllib.parse import quote

    if seed is None or seed <= 0:
        seed = random.randint(100000, 9999999)

    base = (prompt or "educational academic presentation").strip()
    
    # Agar promptda mavzu nomi qatnashmagan bo'lsa, mavzu va fanni boshiga qo'shib boyitish
    context_prefix = ""
    if topic and topic.lower() not in base.lower():
        context_prefix += f"{topic}, "
    if subject and subject.lower() not in base.lower() and subject.lower() not in context_prefix.lower():
        context_prefix += f"{subject}, "

    full_prompt = f"{context_prefix}{base}".strip(", ")
    full_prompt = re.sub(r"\s+", " ", full_prompt)[:450]
    styled = f"{full_prompt}, high quality educational presentation visual, modern minimal aesthetic, 4k, clean, no text, no letters, no watermark"
    return f"https://image.pollinations.ai/prompt/{quote(styled)}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"


from app.services.ai_material_templates import get_question_pool, get_slide_pool, get_lesson_plan, _randomize_question_options


def _build_topic_question_pool(topic_title: str, subject_name: str, num_questions: int, difficulty: str, language: str = "uz") -> List[Dict[str, Any]]:
    """
    O'qituvchi tanlagan til (uz, en, ru) va son bo'yicha boyitilgan testlar banki.
    """
    return get_question_pool(topic_title, subject_name, num_questions, difficulty, language=language)


def _build_topic_slide_pool(topic_title: str, subject_name: str, num_slides: int, with_images: bool, language: str = "uz") -> List[Dict[str, Any]]:
    """
    O'qituvchi tanlagan aniq slaydlar soniga va tiliga (uz, en, ru) mos slaydlar to'plami.
    """
    return get_slide_pool(topic_title, subject_name, num_slides, with_images, language=language)


class AIService:
    """
    TILORA DeepSeek Sun'iy Intellekt integratsiya xizmati (api.b.ai / OpenAI-compatible).
    """

    def __init__(self):
        self.base_url = settings.AI_BASE_URL.rstrip("/")
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        self.timeout = 30.0

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def check_health(self) -> Dict[str, Any]:
        """
        AI provayderi bilan aloqa, avtorizatsiya va balans holatini tekshirish.
        """
        endpoint = f"{self.base_url}/models"
        health_info = {
            "provider": "api.b.ai",
            "base_url": self.base_url,
            "configured_model": self.model,
            "authenticated": False,
            "quota_status": "unknown",
            "status": "offline",
            "message": ""
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=self._get_headers())
                if resp.status_code == 200:
                    health_info["authenticated"] = True
                    health_info["status"] = "online"
                    
                    # Test completion to check quota
                    test_resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(),
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5
                        }
                    )
                    
                    if test_resp.status_code == 200:
                        health_info["quota_status"] = "active"
                        health_info["message"] = "AI xizmati faol va tayyor."
                    else:
                        err_body = test_resp.json() if test_resp.headers.get("content-type", "").startswith("application/json") else {}
                        err_msg = err_body.get("error", {}).get("message", test_resp.text)
                        if "insufficient" in err_msg.lower() or "balance" in err_msg.lower():
                            health_info["quota_status"] = "insufficient_quota"
                            health_info["message"] = f"api.b.ai hisobida balans yetarli emas (kredit kerak): {err_msg}"
                        else:
                            health_info["quota_status"] = "error"
                            health_info["message"] = f"AI API xatolik berdi ({test_resp.status_code}): {err_msg}"
                elif resp.status_code in (401, 403):
                    health_info["authenticated"] = False
                    health_info["status"] = "auth_failed"
                    health_info["message"] = "API kalit yaroqsiz yoki ruxsat yo'q."
                else:
                    health_info["status"] = "error"
                    health_info["message"] = f"HTTP {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            health_info["status"] = "unreachable"
            health_info["message"] = f"Serverga ulanib bo'lmadi: {str(e)}"

        return health_info

    async def call_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 1500,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        DeepSeek modeliga chat completion yuborish.
        """
        endpoint = f"{self.base_url}/chat/completions"
        req_timeout = timeout or self.timeout
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=req_timeout, verify=settings.AI_SSL_VERIFY) as client:
                response = await client.post(
                    endpoint,
                    headers=self._get_headers(),
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    return {
                        "success": True,
                        "content": content,
                        "model": self.model,
                        "usage": usage,
                        "provider": "api.b.ai"
                    }
                else:
                    err_json = response.json() if "application/json" in response.headers.get("content-type", "") else {}
                    err_msg = err_json.get("error", {}).get("message", response.text)
                    err_code = err_json.get("error", {}).get("code", "api_error")
                    is_quota = "insufficient" in err_msg.lower() or "balance" in err_msg.lower()
                    
                    logger.warning(f"AI API xatolik ({response.status_code}): {err_msg}")
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error_message": err_msg,
                        "error_code": err_code,
                        "quota_exhausted": is_quota,
                        "model": self.model
                    }

        except httpx.TimeoutException:
            logger.error("AI so'rovi vaqti tugadi (Timeout)")
            return {
                "success": False,
                "error_message": "AI serveriga ulanish vaqti tugadi (timeout).",
                "error_code": "timeout",
                "quota_exhausted": False,
                "model": self.model
            }
        except Exception as ex:
            logger.error(f"AI chaqiruvida kutilmagan xatolik: {ex}")
            return {
                "success": False,
                "error_message": str(ex),
                "error_code": "exception",
                "quota_exhausted": False,
                "model": self.model
            }

    async def generate_scaffold(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Tayyorgarlik (Scaffolding) bosqichida namuna va yo'riqnoma yaratish.
        """
        system = (
            "Siz TILORA platformasining ingliz tili akademik ta'lim bo'yicha sun'iy intellekt assistentisiz. "
            "Pedagogik tamoyillarga sodiq qoling: to'g'ridan-to'g'ri tayyor insho yozib bermang, balki "
            "tuzilma (outline), akademik leksika va yo'naltiruvchi namuna (scaffold) taqdim eting. "
            "Javobni o'zbek tilida, namunaviy iboralarni ingliz tilida bering."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Mavzu/Topshiriq: {prompt}\nQo'shimcha kontekst: {context or 'Mavjud emas'}"}
        ]
        res = await self.call_chat(messages, temperature=0.7)
        if res.get("success"):
            return {
                "tool": "generate",
                "result": res["content"],
                "model": res["model"],
                "ai_generated": True,
                "provider": res["provider"]
            }
        
        # Fallback (agar balans tugagan bo'lsa yoki xatolik yuz bersa)
        fallback_notice = (
            f"DIQQAT: AI API ({self.model}) hisobida balans yetarli emasligi sababli pedagogik shablon namoyish etilmoqda.\n\n"
            f"Mavzu: '{prompt}'\n"
            f"Tavsiya etilgan akademik tuzilma:\n"
            f"1. Kirish (Thesis statement & Background context)\n"
            f"2. Asosiy tahliliy qismlar (Topic sentence, Evidence, Analysis)\n"
            f"3. Xulosa (Synthesis of main points & Implications)\n\n"
            f"Tavsiya etiladigan bog'lovchi iboralar: 'Furthermore', 'Conversely', 'Empirical evidence suggests'."
        )
        return {
            "tool": "generate",
            "result": fallback_notice,
            "ai_generated": False,
            "fallback": True,
            "api_error": res.get("error_message"),
            "model": self.model
        }

    async def translate_text(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Ko'mak bosqichida terminlar va akademik iboralarni aniq tarjima qilish.
        """
        system = (
            "Siz til ta'limi bo'yicha professional tarjimonsiz. "
            "Berilgan matnni ingliz tilidan o'zbek tiliga (yoki teskarisi) akademik aniqlik bilan tarjima qiling "
            "va zarur terminlarga qisqa tushuntirish bering."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Matn: {prompt}\nKontekst: {context or ''}"}
        ]
        res = await self.call_chat(messages, temperature=0.3)
        if res.get("success"):
            return {
                "tool": "translate",
                "result": res["content"],
                "model": res["model"],
                "ai_generated": True,
                "provider": res["provider"]
            }

        return {
            "tool": "translate",
            "result": f"Lug'aviy tushuntirish (Lokal tizim): '{prompt}' bo'yicha tarjima faqat ko'mak bosqichida leksik qidiruv orqali amalga oshiriladi. (AI holati: {res.get('error_message')})",
            "ai_generated": False,
            "fallback": True,
            "model": self.model
        }

    async def complete_text(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Fikrni davom ettirish va strukturaviy bog'lash bo'yicha ko'mak.
        """
        system = (
            "Siz talabaga akademik yozuvda fikrini davom ettirishga yordam beruvchi murabbiysiz. "
            "Talabaning boshlagan jumlasi asosida 2 ta mumkin bo'lgan mantiqiy davom etish yo'lini ko'rsating."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Boshlangan jumla: {prompt}\nKontekst: {context or ''}"}
        ]
        res = await self.call_chat(messages, temperature=0.7)
        if res.get("success"):
            return {
                "tool": "complete",
                "result": res["content"],
                "model": res["model"],
                "ai_generated": True,
                "provider": res["provider"]
            }

        return {
            "tool": "complete",
            "result": f"Mantiqiy davom ettirish varianti: Talaba boshlagan fikrga akademik dalillar qo'shilishi tavsiya etiladi. (AI holati: {res.get('error_message')})",
            "ai_generated": False,
            "fallback": True,
            "model": self.model
        }

    async def answer_query(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Pedagogik savolga yo'naltiruvchi javob.
        """
        system = (
            "Siz TILORA platformasining xolis akademik konsultantisiz. "
            "Talabaning metodik yoki lingvistik savollariga aniq, asosli va konstruktiv javob bering."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Savol: {prompt}\nKontekst: {context or ''}"}
        ]
        res = await self.call_chat(messages, temperature=0.5)
        if res.get("success"):
            return {
                "tool": "answer",
                "result": res["content"],
                "model": res["model"],
                "ai_generated": True,
                "provider": res["provider"]
            }

        return {
            "tool": "answer",
            "result": f"Akademik maslahat: Mazkur masalada o'quv dasturi mezonlari va standartlariga tayanish maqsadga muvofiq. (AI holati: {res.get('error_message')})",
            "ai_generated": False,
            "fallback": True,
            "model": self.model
        }

    async def analyze_writing(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Talaba matnini DeepSeek AI orqali chuqur pedagogik va lingvistik tahlil qilish.
        """
        system = (
            "Siz ingliz tili yozma ishlarini baholash (IELTS / CEFR) bo'yicha ekspert tizimsiz. "
            "Matnni quyidagi 4 mezon bo'yicha chuqur tahlil qiling:\n"
            "1. Mazmun va vazifani bajarish (Task Achievement)\n"
            "2. Izchillik va bog'liqlik (Coherence & Cohesion)\n"
            "3. Leksik boylik va uslub (Lexical Resource)\n"
            "4. Grammatik aniqlik va xilma-xillik (Grammatical Range & Accuracy)\n"
            "Ona tili (O'zbek/Rus) interferensiyasi xatolariga alohida e'tibor qarating. "
            "Javobni aniq bo'limlar bilan, konstruktiv pedagogik tilda o'zbek tilida qaytaring."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Tahlil qilinadigan talaba matni:\n\n{text}\n\nKontekst: {context or 'Yozma nutq baholash mezonlari darsi'}"}
        ]
        res = await self.call_chat(messages, temperature=0.4, max_tokens=2000)
        if res.get("success"):
            return {
                "tool": "analyze",
                "status": "success",
                "analysis": res["content"],
                "model": res["model"],
                "ai_powered": True,
                "provider": res["provider"]
            }

        # Haqiqiy matndan kelib chiqib boyitilgan tahlil
        clean_text = text.strip()
        words = clean_text.split()
        w_count = len(words)
        unique_w = len(set(w.lower() for w in words))
        ttr_ratio = round((unique_w / w_count) * 100, 1) if w_count else 0
        from app.services.l1 import analyze_l1_interference
        l1_issues = analyze_l1_interference(clean_text)
        
        fallback_analysis = (
            f"📊 **AKADEMIK VA LINGVISTIK MATN TAHLILI (TILORA Kognitiv Moduli):**\n\n"
            f"• **1. Mazmun va Vazifa (Task Achievement):**\n"
            f"  - Matn hajmi: **{w_count} ta so'z** (Talab: 150–180 so'z).\n"
            f"  - {'✅ Matn hajmi topshiriq mezoniga to\'liq mos.' if 140 <= w_count <= 210 else '⚠️ Matn hajmi belgilangan me\'yordan farq qiladi (mazmunni kengaytirish yoki ixchamlashtirish tavsiya etiladi).'}\n\n"
            f"• **2. Izchillik va Bog\'liqlik (Coherence & Cohesion):**\n"
            f"  - Fikrlar ketma-ketligi va argumentlar o'rtasida 'Furthermore', 'Consequently', 'In addition' kabi akademik ko'priklar mavjudligi tekshirildi.\n\n"
            f"• **3. Leksik Boylik (Lexical Resource):**\n"
            f"  - Leksik rang-baranglik (TTR indeksi): **{ttr_ratio}%**.\n"
            f"  - Baholash rubrikalari va terminologiyasining qo'llanilishi o'rganildi.\n\n"
            f"• **4. Grammatik Aniqlik va Ona Tili (L1) Interferensiyasi:**\n"
            f"  - Aniqlangan L1 ta'siri: **{len(l1_issues)} ta holat**.\n"
        )
        if l1_issues:
            fallback_analysis += "  - Aniqlangan xatolar:\n"
            for iss in l1_issues[:3]:
                fallback_analysis += f"    * *{iss.get('issue_short')}*: {iss.get('suggestion')}\n"
        else:
            fallback_analysis += "  - Matnda qo'pol L1 interferensiya qoidabuzarliklari aniqlanmadi.\n"

        return {
            "tool": "analyze",
            "status": "fallback",
            "analysis": fallback_analysis,
            "ai_powered": False,
            "api_error": res.get("error_message"),
            "model": self.model
        }

    async def analyze_student_essay_structured(
        self,
        text: str,
        topic: str = "Yozma nutq baholash mezonlari (Assessment Rubrics)",
        quality_hint: str = ""
    ) -> Dict[str, Any]:
        """
        Talaba yozgan matnni DeepSeek AI orqali to'liq o'qib,
        strukturaviy pedagogik izohlar (Hattie-Timperley) va CEFR rubrikasi bilan JSON formatda tahlil qilish.
        """
        import json
        import re

        system = (
            "Siz oliy ta'limda ingliz tili yozma nutqini baholash (IELTS / CEFR / TKT) bo'yicha ekspert tizimsiz. "
            "Talaba yozgan matnni to'liq, har bir jumlasini o'qib chiqing va tahlil qiling. "
            "QAT'IY QOIDALAR:\n"
            "1. Talabaga tayyor to'g'rilangan insho YOZIB BERMANG! Faqat konstruktiv fikr-mulohaza (formative feedback) va xato sababini tushuntiring.\n"
            "2. Matndagi haqiqiy xato va uslubiy kamchiliklarni (grammatika, leksika, mantiqiy bog'lanish va ayniqsa o'zbek/rus tili interferensiyasini) aniqlang.\n"
            "3. Talabaning matnidan xato bo'lgan so'z yoki iborani 'matched_text' sifatida aniq ko'rsating.\n"
            "4. CEFR mezonlari (content, grammar, lexis, coherence) bo'yicha 1 dan 5 gacha baholang va umumiy ballni 100 ballik shkalada bering.\n"
            "4a. MATNNI TO'LIQ, HAR BIR SO'ZINI O'QING. Ma'nosiz harf ketma-ketliklari (masalan 'asdkjh', 'qwerty', 'xxxx'), "
            "mavjud bo'lmagan so'zlar, tushunarsiz yoki tugallanmagan gaplar, tasodifiy bosilgan belgilar — bularning HAR BIRINI "
            "alohida xato (category: 'lexis' yoki 'coherence', badge: 'Matn sifati') sifatida ko'rsating va ballarni sezilarli pasaytiring. "
            "Matnning katta qismi ma'nosiz bo'lsa, barcha mezonlar 1-2 ball bo'lishi kerak.\n"
            "5. Javobingizni FAQAT quyidagi JSON formatida qaytaring (qo'shimcha matn yoki izohlarsiz):\n"
            "{\n"
            '  "total_score": 75,\n'
            '  "rubric": {"content": 4, "grammar": 3, "lexis": 4, "coherence": 4},\n'
            '  "items": [\n'
            '    {\n'
            '      "category": "grammar",\n'
            '      "badge": "Grammatika · L1 interferensiyasi",\n'
            '      "title": "Xato qisqa tavsifi",\n'
            '      "matched_text": "matndagi xato so\'z yoki ibora",\n'
            '      "issue_reason": "Nima sababdan xato ekani haqida pedagogik izoh",\n'
            '      "suggestion": "Yo\'naltiruvchi taklif"\n'
            '    }\n'
            '  ],\n'
            '  "summary": "Matn haqida qisqa pedagogik xulosa"\n'
            "}"
        )

        user_prompt = (
            f"Mavzu: {topic}\n"
            f"Talaba yozgan matn:\n\"\"\"\n{text}\n\"\"\"\n"
            f"Matnni to'liq o'qib, haqiqiy xatolar va kamchiliklar bo'yicha yuqoridagi JSON formatida tahlil bering."
            + (quality_hint or "")
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt}
        ]

        res = await self.call_chat(messages, temperature=0.3, max_tokens=2200)
        if res.get("success") and res.get("content"):
            try:
                raw = res["content"].strip()
                if "```" in raw:
                    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
                    if match:
                        raw = match.group(1)
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "items" in parsed:
                    return {
                        "ai_powered": True,
                        "model": res.get("model", self.model),
                        "total_score": int(parsed.get("total_score", 70)),
                        "rubric": parsed.get("rubric", {"content": 4, "grammar": 3, "lexis": 4, "coherence": 4}),
                        "items": parsed.get("items", []),
                        "summary": parsed.get("summary", "")
                    }
            except Exception as e:
                logger.warning(f"AI essay JSON parse xatosi: {e}")

        return {
            "ai_powered": False,
            "error": res.get("error_message", "AI tahlil natijasini olib bo'lmadi")
        }

    async def evaluate_writing_rubric(
        self,
        text: str,
        topic: str = "Yozma nutq baholash mezonlari",
        task_prompt: str = "",
        quality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        5-bosqich (Refleksiya): talaba yozgan matnni AI 4 mezon bo'yicha BAHOLAYDI
        (har mezonga 1-5 ball + sabab), umumiy ball, kuchli tomonlar va tavsiyalar.
        AI ishlamasa, lokal heuristik baho (so'z soni, TTR, L1 xatolari) qaytadi.
        """
        import json
        from app.services.text_quality import analyze_text_quality, apply_quality_cap, quality_prompt_hint
        clean = (text or "").strip()
        if quality is None:
            quality = analyze_text_quality(clean)
        system = (
            "Siz oliy ta'limda ingliz tili yozma nutqini baholovchi ekspert (CEFR/IELTS rubrikalari) siz. "
            "Talaba matnini to'liq o'qib, QUYIDAGI 4 MEZON bo'yicha 1 dan 5 gacha BAHOLANG va har bir bahoga "
            "aniq, matndan misol keltirilgan sabab yozing:\n"
            "content (mazmun to'liqligi va vazifani bajarish), grammar (grammatik aniqlik), "
            "lexis (lug'aviy boylik), coherence (izchillik va bog'liqlik).\n"
            "Ona tili (o'zbek/rus) interferensiyasiga e'tibor bering. Tayyor tuzatilgan matn yozmang.\n"
            "MATNNI TO'LIQ, HAR BIR SO'ZINI O'QING: ma'nosiz harf ketma-ketliklari, mavjud bo'lmagan so'zlar, "
            "tushunarsiz yoki tugallanmagan gaplar XATO hisoblanadi — ularni reason ichida aniq ko'rsating va ballarni pasaytiring. "
            "Matnning katta qismi ma'nosiz bo'lsa, barcha mezonlar 1-2 ball.\n"
            "Javobni FAQAT JSON ko'rinishida, o'zbek tilida qaytaring:\n"
            "{\n"
            '  "rubric": {\n'
            '    "content":   {"score": 4, "reason": "..."},\n'
            '    "grammar":   {"score": 3, "reason": "..."},\n'
            '    "lexis":     {"score": 4, "reason": "..."},\n'
            '    "coherence": {"score": 4, "reason": "..."}\n'
            "  },\n"
            '  "total_score": 75,\n'
            '  "cefr_estimate": "B2",\n'
            '  "strengths": ["...", "..."],\n'
            '  "improvements": ["...", "..."],\n'
            '  "overall_comment": "2-3 gapli umumiy pedagogik xulosa"\n'
            "}"
        )
        user_prompt = (
            f"Mavzu: {topic}\n"
            + (f"Topshiriq: {task_prompt}\n" if task_prompt else "")
            + f"Talaba matni:\n\"\"\"\n{clean}\n\"\"\"\n"
            "Yuqoridagi JSON formatida baholang."
            + quality_prompt_hint(quality)
        )
        res = await self.call_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}],
            temperature=0.3, max_tokens=1800, timeout=90.0
        )

        crits = ("content", "grammar", "lexis", "coherence")
        if res.get("success") and res.get("content"):
            raw = res["content"].strip()
            m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
            if m:
                raw = m.group(1)
            else:
                m = re.search(r"(\{.*\})", raw, re.DOTALL)
                if m:
                    raw = m.group(1)
            try:
                parsed = json.loads(raw)
                rub_in = parsed.get("rubric") or {}
                rubric = {}
                for c in crits:
                    v = rub_in.get(c, {})
                    if isinstance(v, dict):
                        sc, rs = v.get("score", 3), v.get("reason", "")
                    else:
                        sc, rs = v, ""
                    try:
                        sc = int(round(float(sc)))
                    except (TypeError, ValueError):
                        sc = 3
                    rubric[c] = {"score": max(1, min(5, sc)), "reason": str(rs or "").strip()}
                total = parsed.get("total_score")
                try:
                    total = int(total)
                except (TypeError, ValueError):
                    total = None
                # Matn sifati cheklovi: AI ma'nosiz matnga yuqori ball qo'ysa ham, pasaytiriladi
                if quality.get("level") != "ok":
                    capped = apply_quality_cap({c: rubric[c]["score"] for c in crits}, quality)
                    for c in crits:
                        if capped[c] < rubric[c]["score"]:
                            rubric[c]["reason"] = (rubric[c]["reason"] + " " if rubric[c]["reason"] else "") + \
                                f"[Matn sifati: ma'nosiz so'z/gaplar tufayli ball {rubric[c]['score']} dan {capped[c]} ga tushirildi.]"
                            rubric[c]["score"] = capped[c]
                    total = int(round(sum(r["score"] for r in rubric.values()) / 20 * 100))
                if total is None or not (0 <= total <= 100):
                    total = int(round(sum(r["score"] for r in rubric.values()) / 20 * 100))
                return {
                    "ai_powered": True,
                    "model": res.get("model", self.model),
                    "rubric": rubric,
                    "total_score": total,
                    "text_quality": quality,
                    "cefr_estimate": str(parsed.get("cefr_estimate") or "B1"),
                    "strengths": [str(x) for x in (parsed.get("strengths") or [])][:5],
                    "improvements": [str(x) for x in (parsed.get("improvements") or [])][:5],
                    "overall_comment": str(parsed.get("overall_comment") or "").strip(),
                }
            except Exception as e:
                logger.warning(f"AI rubrika JSON xatosi: {e}")

        # --- Lokal zaxira baho (AI ishlamasa) ---
        from app.services.scoring import score_writing_production
        from app.services.l1 import analyze_l1_interference
        l1 = analyze_l1_interference(clean)
        sc = score_writing_production(clean, len(l1), quality=quality)
        r = sc["rubric"]
        wc = sc["word_count"]
        vwc = sc.get("valid_word_count", wc)
        size_ok = 140 <= vwc <= 210
        qnote = ""
        if quality.get("level") != "ok":
            toks = ", ".join(f"'{t['token']}'" for t in quality["suspicious_tokens"][:6])
            qnote = f" Ma'nosiz so'zlar ({quality['nonsense_count']} ta: {toks}) va {len(quality['nonsense_sentences'])} ta tushunarsiz gap jarima sifatida hisobga olindi."
        rubric = {
            "content": {"score": r["content"], "reason": f"Ma'noli so'zlar: {vwc} ta (jami {wc}; talab 150-180). " + ("Hajm talabga mos." if size_ok else "Hajm me'yordan farq qiladi.") + qnote},
            "grammar": {"score": r["grammar"], "reason": f"Lokal tekshiruvda {len(l1)} ta ona tili interferensiyasi / grammatik holat aniqlandi." + qnote},
            "lexis": {"score": r["lexis"], "reason": f"Leksik rang-baranglik (TTR) indeksi {int(sc['ttr'] * 100)}%." + qnote},
            "coherence": {"score": r["coherence"], "reason": ("Bog'lovchilar va abzats tuzilishi bo'yicha neytral baho (AI o'chiq)." if not quality["nonsense_sentences"] else f"{len(quality['nonsense_sentences'])} ta gap tushunarsiz: " + "; ".join(s['reason'] for s in quality['nonsense_sentences'][:2]))},
        }
        return {
            "ai_powered": False,
            "model": "TILORA lokal baholash moduli",
            "rubric": rubric,
            "total_score": sc["total_score"],
            "cefr_estimate": "B2" if sc["total_score"] >= 80 else ("B1" if sc["total_score"] >= 60 else "A2"),
            "strengths": ["Matn mustaqil, AI vositalarisiz yozilgan."] + (["Hajm topshiriq talabiga mos."] if size_ok else []),
            "improvements": ([f"{quality['nonsense_count']} ta ma'nosiz so'z/harf ketma-ketligini o'chiring yoki to'g'rilang."] if quality["nonsense_count"] else [])
                            + ([f"{len(l1)} ta L1 interferensiya holatini qayta ko'rib chiqing."] if l1 else ["Akademik bog'lovchilar va murakkab gaplarni ko'paytiring."]),
            "text_quality": quality,
            "overall_comment": "AI xizmati hozir mavjud emas; baho lokal mezonlar (hajm, leksik boylik, L1 xatolari) asosida berildi.",
            "ai_error": _friendly_ai_error(res) if isinstance(res, dict) else None,
        }

    # ------------------------------------------------------------
    # Partiyalab generatsiya (katta sonlar uchun): har chaqiruvda
    # ko'pi bilan BATCH ta element so'raladi, natija yig'ilib boradi.
    # ------------------------------------------------------------
    TEST_BATCH = 8
    SLIDE_BATCH = 6

    async def _collect_items(
        self,
        total: int,
        batch: int,
        make_messages,
        tokens_per_item: int,
        temperature: float,
        max_rounds_extra: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        make_messages(count, offset, done_items) -> messages.
        AI so'ralganidan kam qaytarsa, qolgani uchun qo'shimcha raund(lar) yuboriladi.
        """
        items: List[Dict[str, Any]] = []
        self._last_ai_error = None
        rounds = 0
        max_rounds = (total + batch - 1) // batch + max_rounds_extra
        while len(items) < total and rounds < max_rounds:
            rounds += 1
            need = min(batch, total - len(items))
            messages = make_messages(need, len(items), items)
            max_tokens = min(8000, 600 + need * tokens_per_item)
            res = await self.call_chat(messages, temperature=temperature, max_tokens=max_tokens, timeout=120.0)
            if not (res.get("success") and res.get("content")):
                logger.warning(f"AI partiya {rounds} muvaffaqiyatsiz: {res.get('error_message')}")
                self._last_ai_error = _friendly_ai_error(res)
                break
            parsed = _extract_json_array(res["content"])
            if not parsed:
                logger.warning(f"AI partiya {rounds}: JSON topilmadi")
                continue
            items.extend(parsed)
        return items

    async def generate_topic_test(
        self,
        topic_title: str,
        subject_name: str,
        num_questions: int = 5,
        difficulty: str = "B2",
        book_content: Optional[str] = None,
        book_title: Optional[str] = None,
        extra_instructions: Optional[str] = None,
        language: str = "uz"
    ) -> Dict[str, Any]:
        """
        O'qituvchi tanlagan mavzu bo'yicha AYNAN num_questions ta test savoli (O'zbek, Rus yoki Ingliz tilida).
        Katta sonlar partiyalab (8 tadan) so'raladi, takrorlar olib tashlanadi,
        yetishmasa pedagogik shablon bankidan to'ldiriladi, ortiqchasi kesiladi.
        """
        try:
            num_questions = max(1, min(60, int(num_questions)))
        except (TypeError, ValueError):
            num_questions = 5

        lang = (language or "uz").lower()
        if lang not in ("uz", "en", "ru"):
            lang = "uz"

        book_block = ""
        if book_content:
            if lang == "en":
                book_block = f"\nAttached reference/book ({book_title or 'Textbook'}):\n{book_content[:3000]}\nBase the questions closely on this textbook excerpt."
            elif lang == "ru":
                book_block = f"\nПрикрепленное пособие/книга ({book_title or 'Учебник'}):\n{book_content[:3000]}\nСоставляйте вопросы на основе содержания данного учебника."
            else:
                book_block = f"\nBiriktirilgan adabiyot/kitob ({book_title or 'Darslik'}):\n{book_content[:3000]}\nSavollarni ushbu darslik mazmuniga tayangan holda tuzing."

        extra_block = ""
        if extra_instructions and extra_instructions.strip():
            if lang == "en":
                extra_block = f"\nInstructor's special instructions: {extra_instructions.strip()}"
            elif lang == "ru":
                extra_block = f"\nОсобые требования преподавателя: {extra_instructions.strip()}"
            else:
                extra_block = f"\nO'qituvchining qo'shimcha talabi: {extra_instructions.strip()}"

        def make_messages(count: int, offset: int, done: List[Dict[str, Any]]):
            if lang == "en":
                system = (
                    "You are a professional assessment specialist and ELT methodologist for higher education. "
                    "Design CEFR-aligned multiple-choice test questions to assess university students on the given subject and topic.\n"
                    f"STRICT RULE 1: Formulate EXACTLY {count} questions! Neither more nor less.\n"
                    "STRICT RULE 2: Correct answers must NOT always be in the same position; randomize correct_index across 0, 1, 2, and 3.\n"
                    "STRICT RULE 3: Questions must not duplicate each other, covering diverse facets (theory, application, linguistic analysis, pedagogical context).\n"
                    "CRITICAL LANGUAGE RULE: Write ALL questions, 4 options, and explanations STRICTLY IN ENGLISH.\n"
                    "Return response ONLY as a valid JSON array (no markdown code fences, no extra text):\n"
                    "[\n"
                    "  {\n"
                    '    "question": "Question text in English",\n'
                    '    "options": ["Option A", "Option B", "Option C", "Option D"],\n'
                    '    "correct_index": 2,\n'
                    '    "explanation": "Concise pedagogical explanation of the correct answer in English"\n'
                    "  }\n"
                    "]"
                )
                user_prompt = (
                    f"Subject: {subject_name}\n"
                    f"Topic: {topic_title}\n"
                    f"CEFR Level: {difficulty}\n"
                    f"Language: English\n"
                    f"This batch: questions {offset + 1} to {offset + count} (out of {num_questions} total).\n"
                    f"FORMULATE EXACTLY {count} QUESTIONS IN ENGLISH. Each question must have 4 options, correct_index, and explanation."
                    + book_block + extra_block
                )
                if done:
                    prev = "\n".join(f"- {d.get('question', '')[:90]}" for d in done[-12:])
                    user_prompt += f"\n\nThe following questions have ALREADY been generated, do NOT duplicate them:\n{prev}"
            elif lang == "ru":
                system = (
                    "Вы — профессиональный тестолог и методист высшей школы. "
                    "Составьте тестовые вопросы с выбором ответа в соответствии со стандартами CEFR для оценки знаний студентов университета по заданной дисциплине и теме.\n"
                    f"СТРОГОЕ ПРАВИЛО 1: Составьте РОВНО {count} вопросов! Ни больше, ни меньше.\n"
                    "СТРОГОЕ ПРАВИЛО 2: Правильный ответ не должен быть всегда на одной позиции; распределяйте correct_index случайно между 0, 1, 2 и 3.\n"
                    "СТРОГОЕ ПРАВИЛО 3: Вопросы не должны дублировать друг друга, охватывая разные аспекты (теория, практика, примеры, анализ ошибок, методика).\n"
                    "КРИТИЧЕСКОЕ ПРАВИЛО ПО ЯЗЫКУ: Все вопросы, 4 варианта ответов и объяснения ДОЛЖНЫ БЫТЬ СОСТАВЛЕНЫ ИСКЛЮЧИТЕЛЬНО НА РУССКОМ ЯЗЫКЕ.\n"
                    "Верните ответ ТОЛЬКО в виде JSON массива (без лишних слов и markdown):\n"
                    "[\n"
                    "  {\n"
                    '    "question": "Текст вопроса на русском языке",\n'
                    '    "options": ["Вариант A", "Вариант B", "Вариант C", "Вариант D"],\n'
                    '    "correct_index": 2,\n'
                    '    "explanation": "Краткое научно-педагогическое объяснение правильного ответа на русском"\n'
                    "  }\n"
                    "]"
                )
                user_prompt = (
                    f"Дисциплина: {subject_name}\n"
                    f"Тема: {topic_title}\n"
                    f"Уровень: {difficulty}\n"
                    f"Язык: Русский\n"
                    f"Эта партия: с {offset + 1}-го по {offset + count}-й вопрос (из {num_questions} общих вопросов).\n"
                    f"СОСТАВЬТЕ РОВНО {count} ВОПРОСОВ НА РУССКОМ ЯЗЫКЕ с 4 вариантами, correct_index и explanation."
                    + book_block + extra_block
                )
                if done:
                    prev = "\n".join(f"- {d.get('question', '')[:90]}" for d in done[-12:])
                    user_prompt += f"\n\nСледующие вопросы УЖЕ составлены, НЕ повторяйте их:\n{prev}"
            else:
                system = (
                    "Siz oliy ta'lim muassasasi (chet tillari fakulteti) uchun professional testolog va metodistsiz. "
                    "Berilgan fan va mavzu bo'yicha talabalarning bilimini baholash uchun CEFR standartlariga mos test savollari tuzing.\n"
                    f"DIQQAT — 1-QOIDA: Aynan {count} ta savol tuzing! Kam ham, ko'p ham bo'lmasin.\n"
                    "DIQQAT — 2-QOIDA: To'g'ri javoblar har doim bir xil variantda bo'lmasin; correct_index 0, 1, 2, 3 orasida tasodifiy bo'lsin.\n"
                    "DIQQAT — 3-QOIDA: Savollar bir-birini takrorlamasin, mavzuning turli jihatlarini (nazariya, amaliyot, misol, tahlil, qo'llash) qamrab olsin.\n"
                    "Javobingizni FAQAT JSON massiv formatida qaytaring (hech qanday qo'shimcha so'zsiz, markdown'siz):\n"
                    "[\n"
                    "  {\n"
                    '    "question": "Savol matni",\n'
                    '    "options": ["Variant A", "Variant B", "Variant C", "Variant D"],\n'
                    '    "correct_index": 2,\n'
                    '    "explanation": "To\'g\'ri javobning qisqa ilmiy-pedagogik izohi"\n'
                    "  }\n"
                    "]"
                )
                user_prompt = (
                    f"Fan: {subject_name}\n"
                    f"Mavzu: {topic_title}\n"
                    f"Daraja: {difficulty}\n"
                    f"Bu partiya: {offset + 1}-savoldan {offset + count}-savolgacha (jami {num_questions} ta savolli testning bir qismi).\n"
                    f"AYNAN {count} TA SAVOL TUZING. Har birida 4 ta variant, correct_index va explanation bo'lsin."
                    + book_block + extra_block
                )
                if done:
                    prev = "\n".join(f"- {d.get('question', '')[:90]}" for d in done[-12:])
                    user_prompt += f"\n\nQuyidagi savollar ALLAQACHON tuzilgan, ularni TAKRORLAMANG:\n{prev}"
            return [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]

        raw_items = await self._collect_items(
            total=num_questions, batch=self.TEST_BATCH, make_messages=make_messages,
            tokens_per_item=260, temperature=0.55,
        )

        questions: List[Dict[str, Any]] = []
        seen = set()
        default_expl = "Correct answer corresponding to the topic." if lang == "en" else ("Правильный ответ, соответствующий теме." if lang == "ru" else "Mavzuga mos to'g'ri javob.")

        for q in raw_items:
            if not isinstance(q, dict):
                continue
            text = str(q.get("question") or "").strip()
            opts = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
            if not text or len(opts) < 2:
                continue
            key = text.lower()[:120]
            if key in seen:
                continue
            seen.add(key)
            try:
                c_idx = int(q.get("correct_index", 0))
            except (TypeError, ValueError):
                c_idx = 0
            if not (0 <= c_idx < len(opts)):
                c_idx = 0
            q_item = {
                "id": f"q_{len(questions) + 1}",
                "question": text,
                "options": opts[:4] if len(opts) >= 4 else opts,
                "correct_index": min(c_idx, min(len(opts), 4) - 1),
                "explanation": str(q.get("explanation") or default_expl).strip(),
            }
            questions.append(_randomize_question_options(q_item))
            if len(questions) >= num_questions:
                break

        is_ai = len(questions) > 0
        ai_count = len(questions)

        if len(questions) < num_questions:
            needed = num_questions - len(questions)
            for f_q in _build_topic_question_pool(topic_title, subject_name, needed, difficulty, language=lang):
                f_q["id"] = f"q_{len(questions) + 1}"
                f_q["from_template"] = True
                questions.append(f_q)

        questions = questions[:num_questions]
        for idx, q in enumerate(questions, 1):
            q["id"] = f"q_{idx}"

        test_title = f"{subject_name} — Progress Test on '{topic_title}'" if lang == "en" else (f"{subject_name} — Контрольный тест по теме '{topic_title}'" if lang == "ru" else f"{subject_name} — '{topic_title}' bo'yicha Nazorat Testi")

        return {
            "title": test_title,
            "topic": topic_title,
            "subject": subject_name,
            "difficulty": difficulty,
            "language": lang,
            "questions_count": len(questions),
            "requested_count": num_questions,
            "ai_questions_count": ai_count,
            "questions": questions,
            "ai_generated": is_ai,
            "ai_error": None if ai_count >= num_questions else getattr(self, "_last_ai_error", None),
            "model": self.model if is_ai else "Pedagogik Shablon Generator"
        }

    async def generate_topic_presentation(
        self,
        topic_title: str,
        subject_name: str,
        num_slides: int = 6,
        with_images: bool = True,
        book_content: Optional[str] = None,
        book_title: Optional[str] = None,
        image_mode: str = "ai",
        extra_instructions: Optional[str] = None,
        language: str = "uz"
    ) -> Dict[str, Any]:
        """
        AYNAN num_slides ta slayd (O'zbek, Rus yoki Ingliz tilida). image_mode:
          "ai"    -> har slayd uchun image_prompt asosida alohida AI rasm (pollinations.ai), zaxira: foto
          "photo" -> mavzuga mos tayyor fotolar (Unsplash)
          "none"  -> rasmsiz
        """
        try:
            num_slides = max(1, min(40, int(num_slides)))
        except (TypeError, ValueError):
            num_slides = 6
        image_mode = (image_mode or ("ai" if with_images else "none")).lower()
        if image_mode not in ("ai", "photo", "none"):
            image_mode = "ai"
        with_images = image_mode != "none"
        topic_images = get_topic_slide_images(topic_title, subject_name, max(num_slides, 1))

        lang = (language or "uz").lower()
        if lang not in ("uz", "en", "ru"):
            lang = "uz"

        book_block = ""
        if book_content:
            if lang == "en":
                book_block = f"\nAttached reference/book ({book_title or 'Textbook'}):\n{book_content[:3000]}\nBase slide concepts on this textbook content."
            elif lang == "ru":
                book_block = f"\nПрикрепленное пособие/книга ({book_title or 'Учебник'}):\n{book_content[:3000]}\nСоставляйте слайды на основе содержания данного учебника."
            else:
                book_block = f"\nBiriktirilgan kitob/adabiyot ({book_title or 'Darslik'}):\n{book_content[:3000]}\nSlaydlarni yuqoridagi darslik mazmuniga tayangan holda tuzing."

        extra_block = ""
        if extra_instructions and extra_instructions.strip():
            if lang == "en":
                extra_block = f"\nInstructor's special requirements: {extra_instructions.strip()}"
            elif lang == "ru":
                extra_block = f"\nОсобые требования преподавателя: {extra_instructions.strip()}"
            else:
                extra_block = f"\nO'qituvchining qo'shimcha talabi: {extra_instructions.strip()}"

        def structure_hint(offset: int, count: int) -> str:
            first = offset + 1
            last = offset + count
            parts = []
            if lang == "en":
                if first == 1:
                    parts.append("Slide 1: Introduction, Objectives, and Outline.")
                if last == num_slides:
                    parts.append(f"Slide {num_slides} (last): Summary, Autonomous Tasks, and References.")
                parts.append("Other slides: Theoretical foundations, practical scaffolding, case studies, linguistic analysis, interactive pair tasks.")
            elif lang == "ru":
                if first == 1:
                    parts.append("1-й слайд: Введение, цели и план занятия.")
                if last == num_slides:
                    parts.append(f"{num_slides}-й слайд (последний): Заключение, самостоятельное задание и список литературы.")
                parts.append("Остальные слайды: Теоретические концепции, практические примеры (Scaffolding), кейс-стади, анализ ошибок, интерактивные задания.")
            else:
                if first == 1:
                    parts.append("1-slayd: Kirish, maqsad va reja.")
                if last == num_slides:
                    parts.append(f"{num_slides}-slayd (oxirgisi): Xulosa, mustaqil topshiriq va adabiyotlar.")
                parts.append("Qolgan slaydlar: nazariy tushunchalar, amaliy misollar, keys-stadi, tahlil, interaktiv savollar.")
            return " ".join(parts)

        def make_messages(count: int, offset: int, done: List[Dict[str, Any]]):
            if lang == "en":
                system = (
                    "You are a professional university lecture and presentation designer. "
                    f"Prepare a presentation consisting of {num_slides} high-quality academic slides for university teaching.\n"
                    f"ATTENTION: Write EXACTLY {count} slides in this batch (neither more nor less).\n"
                    "CRITICAL LANGUAGE RULE: All slide titles, bullet points, speaker notes, and visual badges MUST be written entirely in ENGLISH.\n"
                    "For each slide, provide an 'image_prompt' in English describing the slide concept without text or letters "
                    "(e.g., 'university seminar, students analyzing language structures, warm light, professional minimal style').\n"
                    "Return response ONLY as a JSON array (no markdown fences, no extra text):\n"
                    "[\n"
                    "  {\n"
                    '    "title": "Slide Title in English",\n'
                    '    "bullets": ["Point 1", "Point 2", "Point 3", "Point 4"],\n'
                    '    "speaker_notes": "Oral explanation for the lecturer in English (2-4 sentences)",\n'
                    '    "visual_badge": "Short badge (e.g. THEORY, PRACTICE, CASE)",\n'
                    '    "image_prompt": "English image prompt"\n'
                    "  }\n"
                    "]"
                )
                user_prompt = (
                    f"Subject: {subject_name}\n"
                    f"Topic: {topic_title}\n"
                    f"Target Language: English\n"
                    f"This batch: slides {offset + 1} to {offset + count} (out of {num_slides} total).\n"
                    f"{structure_hint(offset, count)}\n"
                    f"WRITE EXACTLY {count} SLIDES ENTIRELY IN ENGLISH."
                    + book_block + extra_block
                )
                if done:
                    prev = "\n".join(f"- {d.get('title', '')[:80]}" for d in done[-12:])
                    user_prompt += f"\n\nThe following slides have ALREADY been written, do NOT duplicate topics:\n{prev}"
            elif lang == "ru":
                system = (
                    "Вы — профессиональный разработчик университетских академических презентаций. "
                    f"Создается презентация из {num_slides} слайдов для проведения вузовского занятия.\n"
                    f"ВНИМАНИЕ: Напишите РОВНО {count} слайдов в этой партии (ни больше, ни меньше).\n"
                    "КРИТИЧЕСКОЕ ПРАВИЛО ПО ЯЗЫКУ: Все заголовки слайдов, пункты списков (bullets), заметки докладчика (speaker_notes) и значки (visual_badge) ДОЛЖНЫ БЫТЬ НАПИСАНЫ НА РУССКОМ ЯЗЫКЕ.\n"
                    "Для каждого слайда укажите 'image_prompt' на английском языке (без надписей и букв).\n"
                    "Верните ответ ТОЛЬКО в виде JSON массива:\n"
                    "[\n"
                    "  {\n"
                    '    "title": "Заголовок слайда на русском языке",\n'
                    '    "bullets": ["Пункт 1", "Пункт 2", "Пункт 3", "Пункт 4"],\n'
                    '    "speaker_notes": "Устный комментарий преподавателя на русском языке (2-4 предложения)",\n'
                    '    "visual_badge": "Короткий значок (напр.: ТЕОРИЯ, ПРАКТИКА, КЕЙС)",\n'
                    '    "image_prompt": "English image prompt"\n'
                    "  }\n"
                    "]"
                )
                user_prompt = (
                    f"Дисциплина: {subject_name}\n"
                    f"Тема: {topic_title}\n"
                    f"Язык: Русский\n"
                    f"Эта партия: со слайда {offset + 1} по слайд {offset + count} (из {num_slides} общих).\n"
                    f"{structure_hint(offset, count)}\n"
                    f"НАПИШИТЕ РОВНО {count} СЛАЙДОВ НА РУССКОМ ЯЗЫКЕ."
                    + book_block + extra_block
                )
                if done:
                    prev = "\n".join(f"- {d.get('title', '')[:80]}" for d in done[-12:])
                    user_prompt += f"\n\nСледующие слайды УЖЕ написаны, НЕ дублируйте их темы:\n{prev}"
            else:
                system = (
                    "Siz universitet ta'limi bo'yicha professional taqdimotlar muallifisiz. "
                    f"O'qituvchi darsda namoyish etishi uchun jami {num_slides} ta slayddan iborat taqdimot tayyorlanmoqda.\n"
                    f"DIQQAT: Hozir AYNAN {count} TA slayd yozing (kam ham, ko'p ham emas).\n"
                    "Har bir slayd uchun 'image_prompt' bering: slayd mazmunini ifodalovchi, INGLIZ TILIDA, aniq va tasviriy rasm prompti "
                    "(masalan: 'university seminar, students discussing academic essay structure, warm light, clean flat illustration'). Matn yoki harflar tasvirlanmasin.\n"
                    "Javobingizni FAQAT JSON massiv formatida qaytaring (qo'shimcha so'zsiz, markdown'siz):\n"
                    "[\n"
                    "  {\n"
                    '    "title": "Slayd sarlavhasi",\n'
                    '    "bullets": ["Punkt 1", "Punkt 2", "Punkt 3", "Punkt 4"],\n'
                    '    "speaker_notes": "O\'qituvchining darsdagi og\'zaki izohi (2-4 gap)",\n'
                    '    "visual_badge": "Qisqa yorliq (masalan: NAZARIYA, AMALIYOT, KEYS)",\n'
                    '    "image_prompt": "English image prompt"\n'
                    "  }\n"
                    "]"
                )
                user_prompt = (
                    f"Fan: {subject_name}\n"
                    f"Mavzu: {topic_title}\n"
                    f"Bu partiya: {offset + 1}-slayddan {offset + count}-slaydgacha (jami {num_slides} ta).\n"
                    f"{structure_hint(offset, count)}\n"
                    f"AYNAN {count} TA SLAYD YOZING."
                    + book_block + extra_block
                )
                if done:
                    prev = "\n".join(f"- {d.get('title', '')[:80]}" for d in done[-12:])
                    user_prompt += f"\n\nQuyidagi slaydlar ALLAQACHON yozilgan, mavzularini TAKRORLAMANG, mantiqiy davom ettiring:\n{prev}"
            return [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]

        raw_items = await self._collect_items(
            total=num_slides, batch=self.SLIDE_BATCH, make_messages=make_messages,
            tokens_per_item=380, temperature=0.6,
        )

        slides: List[Dict[str, Any]] = []
        seen = set()
        default_notes = f"Lecturer's commentary on {topic_title}." if lang == "en" else (f"Комментарий преподавателя по теме {topic_title}." if lang == "ru" else f"{topic_title} mavzusi bo'yicha o'qituvchi sharhi.")
        default_badge_prefix = "SLIDE" if lang == "en" else ("СЛАЙД" if lang == "ru" else "SLAYD")

        for s in raw_items:
            if not isinstance(s, dict):
                continue
            title = str(s.get("title") or "").strip()
            if not title:
                continue
            key = title.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            bullets = [str(b).strip() for b in (s.get("bullets") or []) if str(b).strip()]
            slides.append({
                "slide_number": len(slides) + 1,
                "title": title,
                "bullets": bullets or (["Core concept", "Practical application", "Analysis"] if lang == "en" else (["Ключевая концепция", "Практический пример", "Анализ"] if lang == "ru" else ["Asosiy konseptsiya", "Amaliy misol", "Tahlil"])),
                "speaker_notes": str(s.get("speaker_notes") or default_notes).strip(),
                "visual_badge": str(s.get("visual_badge") or f"{default_badge_prefix} {len(slides) + 1}").strip(),
                "image_prompt": str(s.get("image_prompt") or f"{topic_title}, {subject_name}, academic presentation illustration").strip(),
            })
            if len(slides) >= num_slides:
                break

        is_ai = len(slides) > 0
        ai_count = len(slides)

        if len(slides) < num_slides:
            fill = _build_topic_slide_pool(topic_title, subject_name, num_slides, with_images, language=lang)
            for f_s in fill[len(slides):num_slides]:
                f_s = dict(f_s)
                f_s["from_template"] = True
                slides.append(f_s)

        slides = slides[:num_slides]

        # Rasmlar: har slaydga alohida, keshlanib qolgan eski rasmlarsiz yangi generatsiya
        import random
        for i, s in enumerate(slides, 1):
            s["slide_number"] = i
            photo = topic_images[(i - 1) % len(topic_images)]
            if image_mode == "ai":
                slide_prompt = s.get("image_prompt") or s.get("title") or topic_title
                # Har bir slayd va har bir generatsiya uchun unikal tasodifiy seed
                slide_seed = random.randint(100000, 9999999)
                s["image_url"] = build_ai_image_url(
                    prompt=slide_prompt,
                    seed=slide_seed,
                    topic=topic_title,
                    subject=subject_name
                )
                s["image_fallback_url"] = photo
                s["image_source"] = "ai"
            elif image_mode == "photo":
                s["image_url"] = photo
                s["image_fallback_url"] = ""
                s["image_source"] = "photo"
            else:
                s["image_url"] = ""
                s["image_fallback_url"] = ""
                s["image_source"] = "none"

        pres_title = f"{subject_name} — Presentation on '{topic_title}'" if lang == "en" else (f"{subject_name} — Презентация по теме '{topic_title}'" if lang == "ru" else f"{subject_name} — '{topic_title}' Taqdimoti")

        return {
            "title": pres_title,
            "topic": topic_title,
            "subject": subject_name,
            "language": lang,
            "slides_count": len(slides),
            "requested_count": num_slides,
            "ai_slides_count": ai_count,
            "image_mode": image_mode,
            "slides": slides,
            "ai_generated": is_ai,
            "ai_error": None if ai_count >= num_slides else getattr(self, "_last_ai_error", None),
            "model": self.model if is_ai else "Pedagogik Slayd Generator"
        }

    async def generate_topic_lesson_plan(
        self,
        topic_title: str,
        subject_name: str,
        book_content: Optional[str] = None,
        book_title: Optional[str] = None,
        language: str = "uz"
    ) -> Dict[str, Any]:
        """
        5 bosqichli dars ssenariysi (Lesson plan) - O'zbek, Rus yoki Ingliz tilida.
        """
        from app.services.ai_material_templates import get_lesson_plan
        return get_lesson_plan(topic_title, subject_name, book_title=book_title, language=language)

ai_service = AIService()

