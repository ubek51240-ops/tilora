"""
O'qituvchi yuklagan tayyor test va slayd fayllarini (.docx, .pdf, .txt, .pptx) tahlil qilish.

- extract_text: hujjat matnini olish
- parse_test_questions: matndan test savollari (variantlar + javob kaliti) ni ajratish
- extract_slides: .pptx / .pdf / .docx / .txt faylidan slaydlar ro'yxatini tuzish
"""
import io
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

TEST_EXTENSIONS = (".docx", ".pdf", ".txt")
PRESENTATION_EXTENSIONS = (".pptx", ".pdf", ".docx", ".txt")

# Kirill variant harflari ham qabul qilinadi (А Б В Г Д / а б в г д)
_LETTER_INDEX = {
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5,
    "А": 0, "Б": 1, "В": 2, "Г": 3, "Д": 4, "Е": 5,
}
_LETTERS = "A-Fa-fА-Еа-е"
_MARK = r"[\*#✓✔\+]"

_OPTION_RE = re.compile(rf"^\s*(?P<pre>{_MARK})?\s*(?P<letter>[{_LETTERS}])\s*[\)\.\:\-–]\s*(?P<text>.+?)\s*(?P<post>{_MARK})?\s*$")
_INLINE_OPTION_RE = re.compile(rf"(?:(?<=\s)|^)({_MARK})?\s*([{_LETTERS}])\s*[\)\.]\s+")
_QUESTION_RE = re.compile(r"^\s*(?:(?:savol|question|вопрос)\s*[№#]?\s*)?(?P<num>\d{1,3})\s*[\.\)\:\-–]\s*(?P<text>.+)$", re.IGNORECASE)
_ANSWER_RE = re.compile(
    rf"^\s*(?:to['’`]?g['’`]?ri\s+javob|javob|javobi|kalit|answer|key|correct(?:\s+answer)?|ответ|правильный\s+ответ)\s*[:\-–\.]?\s*(?P<letter>[{_LETTERS}])\b",
    re.IGNORECASE,
)
_KEY_HEADER_RE = re.compile(r"^\s*(?:javob(?:lar)?\s*kaliti|kalit|javoblar|answer\s*key|answers|keys|ключ|ответы)\s*[:\-–]?\s*$", re.IGNORECASE)
_KEY_PAIR_RE = re.compile(rf"(\d{{1,3}})\s*[\-–\.\):]\s*([{_LETTERS}])(?![\w'’])")


def _norm(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("’", "'").replace("‘", "'").replace("\xa0", " ")


# ---------------------------------------------------------------
# Matn olish
# ---------------------------------------------------------------

def _docx_paragraphs(file_bytes: bytes) -> List[Tuple[str, bool]]:
    """(matn, sarlavha_mi) juftliklari — python-docx orqali, jadval kataklari ham."""
    from docx import Document  # python-docx

    doc = Document(io.BytesIO(file_bytes))
    out: List[Tuple[str, bool]] = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            style = (p.style.name or "") if p.style is not None else ""
            out.append((t, style.lower().startswith("heading") or style.lower().startswith("title")))
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            seen = set()
            for c in cells:
                if c and c not in seen:
                    seen.add(c)
                    for line in c.split("\n"):
                        if line.strip():
                            out.append((line.strip(), False))
    return out


def _pdf_pages(file_bytes: bytes) -> List[str]:
    import fitz  # PyMuPDF

    pages = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text("text") or "")
    return pages


def _decode_txt(file_bytes: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", "replace")


def _pptx_slides_raw(file_bytes: bytes) -> List[Dict[str, Any]]:
    """python-pptx'siz: pptx zip ichidagi slide XML'laridan sarlavha, matn va notes."""
    ns = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    }
    out = []
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
        names = z.namelist()
        slide_files = sorted(
            [n for n in names if re.match(r"^ppt/slides/slide\d+\.xml$", n)],
            key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)),
        )
        for n in slide_files:
            num = int(re.search(r"(\d+)\.xml$", n).group(1))
            root = ET.fromstring(z.read(n))
            title, paras = "", []
            for sp in root.iter(f"{{{ns['p']}}}sp"):
                ph = sp.find(f".//{{{ns['p']}}}nvPr/{{{ns['p']}}}ph")
                is_title = ph is not None and (ph.get("type") in ("title", "ctrTitle"))
                for p in sp.iter(f"{{{ns['a']}}}p"):
                    t = "".join((r.text or "") for r in p.iter(f"{{{ns['a']}}}t")).strip()
                    if not t:
                        continue
                    if is_title and not title:
                        title = t
                    elif not is_title:
                        paras.append(t)
            notes = ""
            nn = f"ppt/notesSlides/notesSlide{num}.xml"
            if nn in names:
                nroot = ET.fromstring(z.read(nn))
                chunks = []
                for p in nroot.iter(f"{{{ns['a']}}}p"):
                    t = "".join((r.text or "") for r in p.iter(f"{{{ns['a']}}}t")).strip()
                    if t and not t.isdigit():
                        chunks.append(t)
                notes = " ".join(chunks)
            out.append({"title": title, "paragraphs": paras, "notes": notes})
    return out


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Hujjatdan oddiy matn (satrlar) olish."""
    name = (filename or "").lower()
    if name.endswith(".docx"):
        return "\n".join(t for t, _ in _docx_paragraphs(file_bytes))
    if name.endswith(".pdf"):
        return "\n".join(_pdf_pages(file_bytes))
    if name.endswith(".pptx"):
        parts = []
        for s in _pptx_slides_raw(file_bytes):
            parts.append(s["title"])
            parts.extend(s["paragraphs"])
        return "\n".join(p for p in parts if p)
    return _decode_txt(file_bytes)


# ---------------------------------------------------------------
# Test savollarini ajratish
# ---------------------------------------------------------------

def _split_inline_options(line: str) -> Optional[List[Tuple[str, str, bool]]]:
    """'A) foo B) bar C) baz' ko'rinishidagi bir qatorli variantlar. [(harf, matn, to'g'ri_mi)]"""
    matches = list(_INLINE_OPTION_RE.finditer(line))
    if len(matches) < 2:
        return None
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        text = line[m.end():end].strip()
        correct = bool(m.group(1))
        if text.endswith(("*", "✓", "✔", "#")):
            text, correct = text[:-1].strip(), True
        if text:
            out.append((m.group(2).upper(), text, correct))
    return out if len(out) >= 2 else None


def parse_test_questions(text: str) -> Dict[str, Any]:
    """
    Matndan test savollarini ajratadi. Qo'llab-quvvatlanadigan ko'rinishlar:
      1. Savol matni?
      A) variant   B) variant*  (yulduzcha / # / ✓ — to'g'ri javob)
      Javob: B     (yoki Answer: B, Ответ: B)
    Fayl oxirida "Javoblar kaliti: 1-B, 2-A ..." bloki ham tushuniladi.
    """
    lines = [l.rstrip() for l in _norm(text).split("\n")]
    questions: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    key_block: Dict[int, int] = {}
    in_key_block = False

    def close():
        nonlocal cur
        if cur and cur["options"]:
            questions.append(cur)
        cur = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if _KEY_HEADER_RE.match(line):
            close()
            in_key_block = True
            continue
        if in_key_block:
            pairs = _KEY_PAIR_RE.findall(line)
            if pairs:
                for num, letter in pairs:
                    key_block[int(num)] = _LETTER_INDEX.get(letter.upper(), 0)
                continue
            in_key_block = False  # kalit bloki tugadi

        m_ans = _ANSWER_RE.match(line)
        if m_ans and cur:
            cur["correct_index"] = _LETTER_INDEX.get(m_ans.group("letter").upper())
            continue

        m_opt = _OPTION_RE.match(line)
        # Yangi savol qatori ("3) Savol ... A) x B) y" bir qatorli ko'rinish ham) — variantlardan oldin tekshiriladi
        m_q = None if m_opt else _QUESTION_RE.match(line)
        if m_q and (cur is None or cur["options"]):
            close()
            qtext = m_q.group("text").strip()
            inline_q = _split_inline_options(qtext)
            cur = {"num": int(m_q.group("num")), "question": qtext, "options": [], "correct_index": None}
            if inline_q:
                # Savol va variantlar bitta qatorda: "1. Savol? A) x B) y"
                first = _INLINE_OPTION_RE.search(qtext)
                cur["question"] = qtext[: first.start()].strip() if first else qtext
                for letter, otext, correct in inline_q:
                    cur["options"].append(otext)
                    if correct:
                        cur["correct_index"] = len(cur["options"]) - 1
            continue

        inline = _split_inline_options(line) if not m_opt else None
        if cur is not None and (m_opt or inline):
            items = inline or [(m_opt.group("letter").upper(), m_opt.group("text").strip(), bool(m_opt.group("pre") or m_opt.group("post")))]
            for letter, otext, correct in items:
                cur["options"].append(otext)
                if correct:
                    cur["correct_index"] = len(cur["options"]) - 1
            continue

        # Davom etuvchi qator: savol matniga yoki oxirgi variantga qo'shiladi
        if cur is not None:
            if cur["options"]:
                cur["options"][-1] = (cur["options"][-1] + " " + line).strip()
            else:
                cur["question"] = (cur["question"] + " " + line).strip()
    close()

    out, missing = [], 0
    for i, q in enumerate(questions, 1):
        if len(q["options"]) < 2:
            continue
        ci = q["correct_index"]
        if ci is None and q["num"] in key_block:
            ci = key_block[q["num"]]
        if ci is None or ci >= len(q["options"]):
            missing += 1
            ci = 0
        out.append({
            "id": f"q_{i}",
            "question": q["question"][:1000],
            "options": [o[:500] for o in q["options"][:6]],
            "correct_index": int(ci),
            "explanation": "",
        })
    return {"questions": out, "missing_keys": missing}


# ---------------------------------------------------------------
# Slaydlarni tuzish
# ---------------------------------------------------------------

def _slide(num: int, title: str, bullets: List[str], notes: str = "") -> Dict[str, Any]:
    return {
        "slide_number": num,
        "title": (title or f"Slayd {num}")[:200],
        "bullets": [b[:400] for b in bullets if b][:12],
        "speaker_notes": (notes or "")[:2000],
        "visual_badge": "",
        "image_url": None,
    }


def _chunks_to_slides(blocks: List[Tuple[str, bool]]) -> List[Dict[str, Any]]:
    """Sarlavhalar bo'yicha bo'lish; sarlavha bo'lmasa har 6 ta abzasdan bitta slayd."""
    slides: List[Dict[str, Any]] = []
    has_headings = any(h for _, h in blocks) or any(re.match(r"^(\d{1,2}[\.\)]|#+)\s", t) for t, _ in blocks)
    title, bullets = "", []

    def flush():
        nonlocal title, bullets
        if title or bullets:
            slides.append(_slide(len(slides) + 1, title, bullets))
        title, bullets = "", []

    for t, is_heading in blocks:
        heading = is_heading or (has_headings and bool(re.match(r"^(\d{1,2}[\.\)]|#+)\s", t)) and len(t) <= 120)
        if heading:
            flush()
            title = re.sub(r"^#+\s*", "", t)
        else:
            if not has_headings and len(bullets) >= 6:
                flush()
            bullets.append(t)
    flush()
    return slides


def extract_slides(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    name = (filename or "").lower()
    if name.endswith(".pptx"):
        return [_slide(i, s["title"] or (s["paragraphs"][0] if s["paragraphs"] else ""), s["paragraphs"][1:] if not s["title"] and s["paragraphs"] else s["paragraphs"], s["notes"])
                for i, s in enumerate(_pptx_slides_raw(file_bytes), 1)]
    if name.endswith(".pdf"):
        slides = []
        for page in _pdf_pages(file_bytes):
            lines = [l.strip() for l in page.split("\n") if l.strip()]
            if not lines:
                continue
            title = lines[0] if len(lines[0]) <= 120 else ""
            body = lines[1:] if title else lines
            slides.append(_slide(len(slides) + 1, title, body))
        return slides
    if name.endswith(".docx"):
        return _chunks_to_slides(_docx_paragraphs(file_bytes))
    txt = _decode_txt(file_bytes)
    return _chunks_to_slides([(l.strip(), False) for l in _norm(txt).split("\n") if l.strip()])
