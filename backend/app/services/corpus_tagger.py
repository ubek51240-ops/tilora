"""
Parallel korpus: morfologik va semantik teglash, kollokatsiya ajratish, tekislash.

Dissertatsiya mavzusi: "Tarjima va teng matnlar parallel korpusida o'zaro faol birikuvchi
(kollokatsion) so'zlar tadqiqi (o'zbek va ingliz tillari misolida)".

Standartlar:
  * Morfologiya — Universal Dependencies (UPOS + belgilar; o'zbek uchun UD Uzbek qo'llanmasi),
    ingliz uchun qo'shimcha Penn Treebank teglari.
  * Semantika — UCREL USAS 21 diskursiv maydon (Rayson et al., 2004).
  * Kollokatsiya — BBI struktur tiplari (Benson et al.), Mel'čuk leksik funksiyalari,
    Hausmann tayanch/kollokator, Cowie–Howarth kontinuum.
  * Statistika — MI (Church & Hanks), t-score, log-likelihood (Dunning), logDice (Rychlý).
  * Tekislash — Gale & Church (1993) uzunlikka asoslangan dinamik dasturlash.
  * Tarjima — Vinay & Darbelnet protseduralari, Baker (1992) ekvivalentlik.

AI kalitisiz, to'liq lokal (deterministik) ishlaydi.
"""
import json
import math
import os
import re
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

_CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

MAX_TEXT_CHARS = 60000
NOMINAL_POS = {"NOUN", "PROPN", "ADJ", "PRON", "NUM", "DET"}
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
APOSTROPHES = "ʻʼ’‘`´′"


# ====================================================================================
# Yuklash
# ====================================================================================
def _norm_apos(s: str) -> str:
    for ch in APOSTROPHES:
        s = s.replace(ch, "'")
    return s


def _read_json(name: str):
    path = os.path.join(_CONTENT_DIR, name)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_lexicon(raw: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """-> (bir so'zli leksikon, ko'p so'zli birliklar). Kalitlar '_' bilan boshlansa/tugasa tashlab yuboriladi."""
    single: Dict[str, Dict[str, Any]] = {}
    multi: Dict[str, Dict[str, Any]] = {}
    for key, val in raw.items():
        if key.startswith("_") or key.endswith("_") or not isinstance(val, list) or len(val) < 3:
            continue
        k = _norm_apos(key).lower()
        entry = {
            "upos": val[0],
            "usas": val[1] or "Z99",
            "trans": [t.strip() for t in str(val[2]).split("|") if t.strip()],
            "alt": [val[3]] if len(val) > 3 and val[3] else [],
        }
        (multi if " " in k else single)[k] = entry
    return single, multi


@lru_cache(maxsize=1)
def _lex_en() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    return _parse_lexicon(_read_json("corpus_lexicon_en.json"))


@lru_cache(maxsize=1)
def _lex_uz() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    return _parse_lexicon(_read_json("corpus_lexicon_uz.json"))


@lru_cache(maxsize=1)
def tagset() -> Dict[str, Any]:
    return _read_json("corpus_tagset.json")


@lru_cache(maxsize=1)
def collocation_bank() -> List[Dict[str, Any]]:
    data = _read_json("corpus_collocations.json")
    items = data.get("items", []) if isinstance(data, dict) else []
    for it in items:
        it["uz"] = _norm_apos(it.get("uz", ""))
        it["uz_stems"] = [_norm_apos(s).lower() for s in it.get("uz_stems", [])]
        it["en_lemmas"] = [s.lower() for s in it.get("en_lemmas", [])]
    return items


@lru_cache(maxsize=1)
def _bank_index() -> Tuple[Dict[frozenset, List[Dict[str, Any]]], Dict[frozenset, List[Dict[str, Any]]]]:
    en_idx: Dict[frozenset, List[Dict[str, Any]]] = defaultdict(list)
    uz_idx: Dict[frozenset, List[Dict[str, Any]]] = defaultdict(list)
    for it in collocation_bank():
        en_idx[frozenset(it["en_lemmas"])].append(it)
        uz_idx[frozenset(it["uz_stems"])].append(it)
    return en_idx, uz_idx


def _uz_translations_of_en(lemma: str) -> List[str]:
    """Inglizcha lemma -> o'zbekcha o'zaklar (lug'atdagi 'tahlil qil-' -> 'tahlil qil')."""
    single, _ = _lex_en()
    e = single.get(lemma)
    if not e:
        return []
    out = []
    for t in e["trans"]:
        t = _norm_apos(t).lower().rstrip("-").strip()
        if t and not t.startswith("-"):
            out.append(t)
    return out


# ====================================================================================
# Tokenizatsiya
# ====================================================================================
_WORD_RE = re.compile(r"[A-Za-zÀ-ɏЀ-ӿ][A-Za-zÀ-ɏЀ-ӿ'\-]*|\d+(?:[.,]\d+)?|[^\sA-Za-zÀ-ɏЀ-ӿ\d]")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁÀ-Þ\"'(«\d])")


def split_sentences(text: str) -> List[str]:
    text = _norm_apos(text or "").strip()
    if not text:
        return []
    out: List[str] = []
    for para in re.split(r"\n+", text):
        para = para.strip()
        if not para:
            continue
        out.extend(s.strip() for s in _SENT_SPLIT_RE.split(para) if s.strip())
    return out


def tokenize(sentence: str) -> List[str]:
    toks = _WORD_RE.findall(_norm_apos(sentence))
    # Inglizcha qisqartmalar: don't -> do n't ; it's -> it 's
    out: List[str] = []
    for t in toks:
        low = t.lower()
        if low.endswith("n't") and len(t) > 3:
            out.extend([t[:-3], "n't"])
        elif low.endswith("'s") and len(t) > 2 and "'" not in t[:-2]:
            out.extend([t[:-2], "'s"])
        else:
            out.append(t.strip("'-") if len(t) > 1 and not t[0].isalnum() and not t[-1].isalnum() else t)
    return [t for t in out if t]


def _is_punct(tok: str) -> bool:
    return not any(ch.isalnum() for ch in tok)


# ====================================================================================
# INGLIZ TILI: lemma + UPOS + PTB + belgilar + USAS
# ====================================================================================
EN_IRREGULAR = {
    "made": "make", "took": "take", "taken": "take", "gave": "give", "given": "give", "got": "get", "gotten": "get",
    "kept": "keep", "held": "hold", "paid": "pay", "drew": "draw", "drawn": "draw", "came": "come", "went": "go",
    "gone": "go", "saw": "see", "seen": "see", "known": "know", "knew": "know", "found": "find", "shown": "show",
    "built": "build", "chosen": "choose", "chose": "choose", "broke": "break", "broken": "break", "lost": "lose",
    "caught": "catch", "told": "tell", "said": "say", "spoken": "speak", "spoke": "speak", "written": "write",
    "wrote": "write", "taught": "teach", "led": "lead", "meant": "mean", "sat": "sit", "fell": "fall", "fallen": "fall",
    "spent": "spend", "met": "meet", "was": "be", "were": "be", "is": "be", "are": "be", "am": "be", "been": "be",
    "being": "be", "has": "have", "had": "have", "does": "do", "did": "do", "done": "do", "children": "child",
    "corpora": "corpus", "criteria": "criterion", "phenomena": "phenomenon", "men": "man", "women": "woman",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "ran": "run", "put": "put", "set": "set", "read": "read",
    "began": "begin", "begun": "begin", "brought": "bring", "bought": "buy", "thought": "think", "understood": "understand",
    "felt": "feel", "left": "leave", "sent": "send", "stood": "stand", "sought": "seek", "became": "become", "become": "become",
}
EN_PAST_PART = {"made", "taken", "given", "gotten", "kept", "held", "paid", "drawn", "gone", "seen", "known", "found",
                "shown", "built", "chosen", "broken", "lost", "caught", "told", "said", "spoken", "written", "taught",
                "led", "meant", "fallen", "spent", "met", "been", "had", "done", "begun", "brought", "bought", "thought",
                "understood", "felt", "left", "sent", "stood", "sought", "become"}
EN_SUBJ_PRON = {"i", "we", "they", "he", "she", "it", "you", "who", "which", "that"}
EN_SUFFIX_POS = [
    ("ization", "NOUN"), ("isation", "NOUN"), ("tion", "NOUN"), ("sion", "NOUN"), ("ment", "NOUN"), ("ness", "NOUN"),
    ("ity", "NOUN"), ("ism", "NOUN"), ("ence", "NOUN"), ("ance", "NOUN"), ("ship", "NOUN"), ("hood", "NOUN"),
    ("ology", "NOUN"), ("ure", "NOUN"), ("ist", "NOUN"), ("ical", "ADJ"), ("ous", "ADJ"), ("ive", "ADJ"), ("ful", "ADJ"),
    ("less", "ADJ"), ("able", "ADJ"), ("ible", "ADJ"), ("ic", "ADJ"), ("ary", "ADJ"), ("al", "ADJ"), ("ly", "ADV"),
    ("ize", "VERB"), ("ise", "VERB"), ("ify", "VERB"), ("ate", "VERB"),
]
PTB_BY_UPOS = {"NOUN": "NN", "PROPN": "NNP", "VERB": "VB", "AUX": "MD", "ADJ": "JJ", "ADV": "RB", "DET": "DT",
               "ADP": "IN", "CCONJ": "CC", "SCONJ": "IN", "PRON": "PRP", "NUM": "CD", "PART": "RP", "INTJ": "UH",
               "PUNCT": "PUNCT", "SYM": "SYM", "X": "FW"}
EN_AUX_PTB = {"is": "VBZ", "are": "VBP", "was": "VBD", "were": "VBD", "be": "VB", "been": "VBN", "being": "VBG",
              "am": "VBP", "have": "VBP", "has": "VBZ", "had": "VBD", "do": "VBP", "does": "VBZ", "did": "VBD"}


def _en_lookup(word: str) -> Optional[Dict[str, Any]]:
    return _lex_en()[0].get(word)


def _en_lemma_candidates(low: str) -> List[Tuple[str, str]]:
    """-> [(lemma, inflection)] inflection: '', 'pl', 'vbz', 'ed', 'ing', 'er', 'est'."""
    cands: List[Tuple[str, str]] = []
    if low in EN_IRREGULAR:
        cands.append((EN_IRREGULAR[low], "irr"))
    cands.append((low, ""))
    if low.endswith("ies") and len(low) > 4:
        cands.append((low[:-3] + "y", "s"))
    if low.endswith("es") and len(low) > 4:
        cands.append((low[:-2], "s"))
    if low.endswith("s") and not low.endswith("ss") and len(low) > 3:
        cands.append((low[:-1], "s"))
    if low.endswith("ied") and len(low) > 4:
        cands.append((low[:-3] + "y", "ed"))
    if low.endswith("ed") and len(low) > 4:
        cands.append((low[:-2], "ed"))
        cands.append((low[:-1], "ed"))
        if len(low) > 5 and low[-3] == low[-4]:
            cands.append((low[:-3], "ed"))
    if low.endswith("ing") and len(low) > 5:
        cands.append((low[:-3], "ing"))
        cands.append((low[:-3] + "e", "ing"))
        if low[-4] == low[-5]:
            cands.append((low[:-4], "ing"))
    if low.endswith("est") and len(low) > 5:
        cands.append((low[:-3], "est"))
        cands.append((low[:-2], "est"))
    if low.endswith("er") and len(low) > 4:
        cands.append((low[:-2], "er"))
        cands.append((low[:-1], "er"))
    if low.endswith("ier") and len(low) > 4:
        cands.append((low[:-3] + "y", "er"))
    return cands


def _en_guess_unknown(low: str, raw: str, sent_start: bool) -> Tuple[str, str, str]:
    """-> (upos, lemma, inflection) lug'atda bo'lmagan so'z uchun."""
    if raw[0].isupper() and not sent_start:
        return "PROPN", raw, ""
    if low.endswith("ing") and len(low) > 5:
        return "VERB", low[:-3], "ing"
    if low.endswith("ed") and len(low) > 4:
        return "VERB", low[:-2], "ed"
    for suf, pos in EN_SUFFIX_POS:
        if low.endswith(suf) and len(low) > len(suf) + 2:
            return pos, low, ""
    if low.endswith("s") and len(low) > 4 and not low.endswith("ss"):
        return "NOUN", low[:-1], "s"
    return "NOUN", low, ""


def tag_english(text: str) -> List[Dict[str, Any]]:
    """Gaplar ro'yxati: [{'text', 'tokens': [token]}]."""
    sentences = []
    for s_idx, sent in enumerate(split_sentences(text)):
        toks = tokenize(sent)
        tagged: List[Dict[str, Any]] = []
        for i, raw in enumerate(toks):
            low = raw.lower()
            if _is_punct(raw):
                tagged.append({"id": i + 1, "form": raw, "lemma": raw, "upos": "PUNCT", "xpos": raw, "feats": {}, "usas": "-", "morph": raw, "known": True})
                continue
            if re.fullmatch(r"\d+(?:[.,]\d+)?", raw):
                tagged.append({"id": i + 1, "form": raw, "lemma": raw, "upos": "NUM", "xpos": "CD", "feats": {"NumType": "Card"}, "usas": "N1", "morph": raw, "known": True})
                continue
            entry = None
            lemma, infl = low, ""
            for cand, inf in _en_lemma_candidates(low):
                e = _en_lookup(cand)
                if e:
                    entry, lemma, infl = e, cand, inf
                    break
            if entry:
                upos = entry["upos"]
                alts = entry["alt"]
                known = True
                usas = entry["usas"]
            else:
                upos, lemma, infl = _en_guess_unknown(low, raw, i == 0)
                alts, known, usas = [], False, ("Z1" if upos == "PROPN" else "Z99")
            tagged.append({"id": i + 1, "form": raw, "lemma": lemma, "upos": upos, "alts": alts, "infl": infl,
                           "feats": {}, "usas": usas, "known": known, "low": low})

        # --- Kontekstli aniqlashtirish (ikki yurish) ---
        for i, t in enumerate(tagged):
            if t["upos"] == "PUNCT" or t["upos"] == "NUM":
                continue
            prev = tagged[i - 1] if i > 0 else None
            nxt = tagged[i + 1] if i + 1 < len(tagged) else None
            opts = [t["upos"]] + t.get("alts", [])
            p_upos = prev["upos"] if prev else None
            p_low = prev.get("low", "") if prev else ""
            # "to" + fe'l
            if prev and (p_low == "to" or p_upos == "AUX") and "VERB" in opts and t["upos"] != "VERB":
                t["upos"] = "VERB"
            # aniqlovchi/sifat/egalik olmoshidan keyin -> ot (agar ot varianti bo'lsa)
            elif prev and (p_upos in ("DET", "ADJ", "NUM") or p_low in ("my", "our", "your", "his", "her", "their", "its")) and "NOUN" in opts and t["upos"] != "NOUN":
                # "the most important": DET + ADJ(most) -> keyingi so'z sifat bo'lishi mumkin
                if not (nxt and nxt["upos"] in ("NOUN",) and "ADJ" in opts):
                    t["upos"] = "NOUN"
            # ega olmoshidan keyin -> fe'l
            elif prev and p_low in EN_SUBJ_PRON and "VERB" in opts and t["upos"] != "VERB" and p_upos == "PRON":
                t["upos"] = "VERB"
            # ot + ot(-s)?: "results show" -> show fe'l
            elif prev and p_upos == "NOUN" and t["infl"] == "s" and "VERB" in opts and nxt and nxt["upos"] in ("DET", "ADJ", "NOUN", "ADV", "SCONJ", "PART", "PRON"):
                t["upos"] = "VERB"
            # "that" -> SCONJ oldidan fe'l bo'lsa, aks holda DET
            if t["low"] == "that":
                t["upos"] = "DET" if (nxt and nxt["upos"] in ("NOUN", "ADJ")) else "SCONJ"
            if t["low"] == "to":
                t["upos"] = "PART" if (nxt and nxt["upos"] == "VERB") else "ADP"

        # --- PTB + UD belgilari ---
        for i, t in enumerate(tagged):
            upos, infl, low = t["upos"], t.get("infl", ""), t.get("low", "")
            feats: Dict[str, str] = {}
            xpos = PTB_BY_UPOS.get(upos, "FW")
            prev = tagged[i - 1] if i > 0 else None
            if upos == "NOUN":
                xpos = "NNS" if infl == "s" or low in ("corpora", "criteria", "phenomena", "children", "people", "data") else "NN"
                feats["Number"] = "Plur" if xpos == "NNS" else "Sing"
            elif upos == "PROPN":
                xpos = "NNP"
            elif upos == "VERB":
                if infl == "ing":
                    xpos, feats["VerbForm"] = "VBG", "Ger"
                    if prev and prev["upos"] == "AUX":
                        feats["VerbForm"], feats["Tense"], feats["Aspect"] = "Part", "Pres", "Prog"
                elif infl == "ed" or low in EN_PAST_PART or (infl == "irr" and low != t["lemma"]):
                    if (prev and (prev["upos"] == "AUX" or prev.get("low") in ("been", "being"))) or low in EN_PAST_PART and not (prev and prev["upos"] in ("PRON", "NOUN", "PROPN")):
                        xpos, feats["VerbForm"], feats["Tense"] = "VBN", "Part", "Past"
                    else:
                        xpos, feats["VerbForm"], feats["Tense"], feats["Mood"] = "VBD", "Fin", "Past", "Ind"
                elif infl == "s":
                    xpos, feats["VerbForm"], feats["Tense"], feats["Person"], feats["Number"], feats["Mood"] = "VBZ", "Fin", "Pres", "3", "Sing", "Ind"
                elif prev and (prev.get("low") == "to" or prev["upos"] == "AUX"):
                    xpos, feats["VerbForm"] = "VB", "Inf"
                else:
                    xpos, feats["VerbForm"], feats["Tense"], feats["Mood"] = "VBP", "Fin", "Pres", "Ind"
            elif upos == "AUX":
                xpos = EN_AUX_PTB.get(low, "MD")
                if xpos == "MD":
                    feats["VerbForm"] = "Fin"
                elif low in ("was", "were", "had", "did"):
                    feats["Tense"], feats["VerbForm"] = "Past", "Fin"
                elif low in ("been",):
                    feats["VerbForm"], feats["Tense"] = "Part", "Past"
                elif low == "being":
                    feats["VerbForm"] = "Ger"
                else:
                    feats["Tense"], feats["VerbForm"] = "Pres", "Fin"
            elif upos == "ADJ":
                if infl == "er":
                    xpos, feats["Degree"] = "JJR", "Cmp"
                elif infl == "est":
                    xpos, feats["Degree"] = "JJS", "Sup"
                else:
                    xpos, feats["Degree"] = "JJ", "Pos"
            elif upos == "ADV":
                xpos = {"er": "RBR", "est": "RBS"}.get(infl, "RB")
                if low in ("how", "why", "when", "where"):
                    xpos = "WRB"
            elif upos == "PRON":
                if low in ("my", "our", "your", "his", "her", "their", "its"):
                    xpos, feats["Poss"] = "PRP$", "Yes"
                elif low in ("which", "that"):
                    xpos, feats["PronType"] = "WDT", "Rel"
                elif low in ("who", "whom", "what"):
                    xpos, feats["PronType"] = "WP", "Int"
                elif low == "whose":
                    xpos, feats["PronType"] = "WP$", "Int"
                elif low == "there":
                    xpos = "EX"
                else:
                    xpos, feats["PronType"] = "PRP", "Prs"
                    if low in ("i", "me", "we", "us", "my", "our"):
                        feats["Person"] = "1"
                    elif low in ("you", "your"):
                        feats["Person"] = "2"
                    else:
                        feats["Person"] = "3"
            elif upos == "DET":
                xpos = "WDT" if low == "which" else "DT"
                if low in ("a", "an"):
                    feats["Definite"] = "Ind"
                elif low == "the":
                    feats["Definite"] = "Def"
                elif low in ("this", "that", "these", "those"):
                    feats["PronType"] = "Dem"
            elif upos == "PART":
                xpos = "TO" if low == "to" else ("POS" if low == "'s" else "RB")
                if low in ("not", "n't"):
                    feats["Polarity"] = "Neg"
            elif upos == "SCONJ":
                xpos = "IN"
            elif upos == "ADP":
                xpos = "IN"
            t["xpos"] = xpos
            t["feats"] = feats
            t["morph"] = _en_morph_string(t)
            for k in ("alts", "infl", "low"):
                t.pop(k, None)
        sentences.append({"id": s_idx + 1, "text": sent, "tokens": tagged})
    return sentences


def _en_morph_string(t: Dict[str, Any]) -> str:
    low, lemma, infl = t.get("low", t["form"].lower()), t["lemma"], t.get("infl", "")
    if infl in ("", "irr") or low == lemma:
        return lemma if low == lemma else f"{lemma} (→ {low})"
    suf = {"s": "-s", "ed": "-ed", "ing": "-ing", "er": "-er", "est": "-est"}.get(infl, "")
    return f"{lemma} + {suf}"


# ====================================================================================
# O'ZBEK TILI: morfologik analizator (affiks ajratish, UD belgilari)
# ====================================================================================
UZ_CASE = [("ning", "Gen"), ("dan", "Abl"), ("ni", "Acc"), ("ga", "Dat"), ("ka", "Dat"), ("qa", "Dat"), ("da", "Loc")]
UZ_POSS = [("ingiz", "2", "Plur"), ("imiz", "1", "Plur"), ("ngiz", "2", "Plur"), ("miz", "1", "Plur"),
           ("ing", "2", "Sing"), ("im", "1", "Sing"), ("si", "3", "Sing"), ("ng", "2", "Sing"), ("m", "1", "Sing"), ("i", "3", "Sing")]
UZ_PLUR = "lar"
# (tense/mood marker, person endings {ending: (Person, Number)}, feats)
_P_DI = {"m": ("1", "Sing"), "ng": ("2", "Sing"), "": ("3", "Sing"), "k": ("1", "Plur"), "ngiz": ("2", "Plur"), "lar": ("3", "Plur")}
_P_MAN = {"man": ("1", "Sing"), "san": ("2", "Sing"), "di": ("3", "Sing"), "miz": ("1", "Plur"), "siz": ("2", "Plur"), "dilar": ("3", "Plur")}
_P_MAN0 = {"man": ("1", "Sing"), "san": ("2", "Sing"), "": ("3", "Sing"), "miz": ("1", "Plur"), "siz": ("2", "Plur"), "lar": ("3", "Plur")}
_P_YAP = {"man": ("1", "Sing"), "san": ("2", "Sing"), "ti": ("3", "Sing"), "miz": ("1", "Plur"), "siz": ("2", "Plur"), "tilar": ("3", "Plur")}
UZ_FINITE = [
    ("moqda", _P_MAN0, {"Tense": "Pres", "Aspect": "Prog", "Mood": "Ind", "VerbForm": "Fin"}),
    ("moqchi", _P_MAN0, {"Mood": "Prp", "VerbForm": "Fin"}),
    ("yap", _P_YAP, {"Tense": "Pres", "Aspect": "Prog", "Mood": "Ind", "VerbForm": "Fin"}),
    ("ib", _P_MAN, {"Tense": "Past", "Evident": "Fh", "Mood": "Ind", "VerbForm": "Fin"}),
    ("gan", _P_MAN0, {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "VerbForm": "Fin"}),
    ("kan", _P_MAN0, {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "VerbForm": "Fin"}),
    ("qan", _P_MAN0, {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "VerbForm": "Fin"}),
    ("di", _P_DI, {"Tense": "Past", "Mood": "Ind", "VerbForm": "Fin"}),
    ("sa", _P_DI, {"Mood": "Cnd", "VerbForm": "Fin"}),
    ("mas", _P_MAN0, {"Polarity": "Neg", "Tense": "Fut", "Mood": "Ind", "VerbForm": "Fin"}),
    ("ar", _P_MAN0, {"Tense": "Fut", "Aspect": "Hab", "Mood": "Ind", "VerbForm": "Fin"}),
    ("a", _P_MAN, {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin"}),
    ("y", _P_MAN, {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin"}),
    ("r", _P_MAN0, {"Tense": "Fut", "Aspect": "Hab", "Mood": "Ind", "VerbForm": "Fin"}),
]
UZ_IMPERATIVE = [("ingiz", {"Mood": "Imp", "Person": "2", "Number": "Plur"}), ("aylik", {"Mood": "Opt", "Person": "1", "Number": "Plur"}),
                 ("ylik", {"Mood": "Opt", "Person": "1", "Number": "Plur"}), ("ing", {"Mood": "Imp", "Person": "2", "Number": "Plur"}),
                 ("sin", {"Mood": "Imp", "Person": "3", "Number": "Sing"}), ("ay", {"Mood": "Opt", "Person": "1", "Number": "Sing"})]
# Tuslanmagan shakllar (nominal qo'shimchalar olishi mumkin)
UZ_NONFINITE = [
    ("ayotgan", {"VerbForm": "Part", "Tense": "Pres", "Aspect": "Prog"}), ("yotgan", {"VerbForm": "Part", "Tense": "Pres", "Aspect": "Prog"}),
    ("adigan", {"VerbForm": "Part", "Tense": "Pres"}), ("ydigan", {"VerbForm": "Part", "Tense": "Pres"}),
    ("uvchi", {"VerbForm": "Part", "Tense": "Pres"}), ("ovchi", {"VerbForm": "Part", "Tense": "Pres"}), ("vchi", {"VerbForm": "Part", "Tense": "Pres"}),
    ("guncha", {"VerbForm": "Conv"}), ("kuncha", {"VerbForm": "Conv"}), ("quncha", {"VerbForm": "Conv"}),
    ("gach", {"VerbForm": "Conv"}), ("kach", {"VerbForm": "Conv"}), ("qach", {"VerbForm": "Conv"}),
    ("gani", {"VerbForm": "Conv"}), ("kani", {"VerbForm": "Conv"}), ("qani", {"VerbForm": "Conv"}),
    ("gan", {"VerbForm": "Part", "Tense": "Past", "Aspect": "Perf"}), ("kan", {"VerbForm": "Part", "Tense": "Past", "Aspect": "Perf"}), ("qan", {"VerbForm": "Part", "Tense": "Past", "Aspect": "Perf"}),
    ("moq", {"VerbForm": "Vnoun"}), ("ish", {"VerbForm": "Vnoun"}), ("sh", {"VerbForm": "Vnoun"}),
    ("uv", {"VerbForm": "Vnoun"}), ("v", {"VerbForm": "Vnoun"}),
    ("ib", {"VerbForm": "Conv"}), ("b", {"VerbForm": "Conv"}),
    ("ar", {"VerbForm": "Part", "Tense": "Fut"}), ("r", {"VerbForm": "Part", "Tense": "Fut"}),
    ("a", {"VerbForm": "Conv"}), ("y", {"VerbForm": "Conv"}),
]
UZ_VOICE = [("tir", "Cau"), ("dir", "Cau"), ("il", "Pass"), ("in", "Rfl"), ("ish", "Rcp"), ("iz", "Cau"), ("t", "Cau"), ("ir", "Cau")]
UZ_DERIV = [("chilik", "NOUN"), ("lashtir", "VERB"), ("lantir", "VERB"), ("lash", "VERB"), ("lan", "VERB"), ("lik", "NOUN"),
            ("chi", "NOUN"), ("dosh", "NOUN"), ("gich", "NOUN"), ("kich", "NOUN"), ("qich", "NOUN"), ("siz", "ADJ"),
            ("li", "ADJ"), ("viy", "ADJ"), ("iy", "ADJ"), ("cha", "ADV"), ("an", "ADV"), ("ona", "ADV"), ("roq", "ADJ")]
UZ_LIGHT_VERBS = {"qil", "et", "ayla", "bo'l", "ber", "ol", "qo'y", "o'tkaz", "olib bor", "qabul qil", "chiqar", "ko'tar",
                  "yetkaz", "yurit", "sodir et", "bajar", "tut", "tur", "top", "ko'rsat", "o'qi"}
UZ_INTRANSITIVE = {"yog'", "o't", "chalin", "g'ing'illa", "kel", "ket", "tuga", "o's", "osh", "kamay", "yiqil", "uxla",
                   "paydo bo'l", "uchra", "yuz ber", "o'tir", "tur", "yur", "qol", "ko'rin", "o'zgar", "rivojlan", "mavjud bo'l"}
UZ_QUANT = {"og'iz", "bo'lak", "to'da", "dona", "tup", "juft", "siqim", "qultum", "parcha", "gala", "guruh", "to'p", "qop", "piyola"}


def _uz_entry(stem: str) -> Optional[Dict[str, Any]]:
    return _lex_uz()[0].get(stem)


def _strip_nominal(word: str):
    """-> [(qoldiq, feats, suffixlar)] barcha mumkin bo'lgan kelishik→egalik→ko'plik ajratishlari (kamida bitta)."""
    results = []
    seen = set()

    def add(rest, feats, sufs):
        key = (rest, tuple(sufs))
        if key not in seen and len(rest) >= 2:
            seen.add(key)
            results.append((rest, dict(feats), list(sufs)))

    case_opts = [("", None)] + UZ_CASE
    for c_suf, c_val in case_opts:
        if c_suf and not word.endswith(c_suf):
            continue
        w1 = word[:-len(c_suf)] if c_suf else word
        f1 = {"Case": c_val} if c_val else {}
        s1 = [c_suf + ":" + c_val] if c_suf else []
        poss_opts = [("", None, None)] + UZ_POSS
        for p_suf, p_pers, p_num in poss_opts:
            if p_suf and not w1.endswith(p_suf):
                continue
            w2 = w1[:-len(p_suf)] if p_suf else w1
            # Fonotaktika: unlidan keyin -m/-ng/-si/-miz/-ngiz, undoshdan keyin -im/-ing/-i/-imiz/-ingiz
            if p_suf:
                if len(w2) < 2:
                    continue
                vowel_final = w2[-1] in "aeiou" or (w2[-1] == "'" and w2[-2] == "o")
                if p_suf in ("si", "m", "ng", "miz", "ngiz") and not vowel_final:
                    continue
                if p_suf in ("i", "im", "ing", "imiz", "ingiz") and vowel_final:
                    continue
            f2 = dict(f1)
            s2 = list(s1)
            if p_suf:
                f2["Person[psor]"], f2["Number[psor]"] = p_pers, p_num
                s2.insert(0, f"{p_suf}:Poss{p_pers}{'Pl' if p_num == 'Plur' else 'Sg'}")
            for plural in (False, True):
                if plural:
                    if not w2.endswith(UZ_PLUR) or len(w2) <= 4:
                        continue
                    w3 = w2[:-3]
                    f3 = dict(f2)
                    f3["Number"] = "Plur"
                    s3 = ["lar:Plur"] + s2
                else:
                    w3, f3, s3 = w2, f2, s2
                if s3:
                    add(w3, f3, s3)
    return results


def _strip_voice(stem: str) -> List[Tuple[str, Dict[str, str], List[str]]]:
    out = [(stem, {}, [])]
    for suf, val in UZ_VOICE:
        if stem.endswith(suf) and len(stem) - len(suf) >= 2:
            base = stem[:-len(suf)]
            if suf == "in" and base.endswith("l"):
                val = "Pass"  # qil-in-adi, ol-in-adi: majhul nisbat
            out.append((base, {"Voice": val}, [f"{suf}:{val}"]))
    # Unlidan keyingi bir harfli nisbat qo'shimchalari: hisobla-n-adi, o'qi-l-di
    for suf, val in (("n", "Pass"), ("l", "Pass")):
        if stem.endswith(suf) and len(stem) >= 4 and stem[-2] in "aeiou'":
            base = stem[:-1]
            if base.endswith("'"):
                continue
            out.append((base, {"Voice": val}, [f"{suf}:{val}"]))
    return out


def _verb_base_candidates(rest: str):
    """-> [(o'zak, feats, sufs, attested)] inkor + nisbat ajratilgan variantlar."""
    out = []
    for neg in (False, True):
        if neg:
            if not rest.endswith("ma") or len(rest) <= 4:
                continue
            r1, f1, s1 = rest[:-2], {"Polarity": "Neg"}, ["ma:Neg"]
        else:
            r1, f1, s1 = rest, {}, []
        for r2, f2, s2 in _strip_voice(r1):
            e = _uz_entry(r2)
            attested = bool(e and ("VERB" in [e["upos"]] + e["alt"]))
            out.append((r2, {**f2, **f1}, s2 + s1, attested))
    return out


def _strip_verbal(word: str):
    """Tuslangan fe'l shakllari: -> [(o'zak, feats, sufs, attested)]"""
    results = []
    for marker, persons, mfeats in UZ_FINITE:
        for p_suf, (pers, num) in persons.items():
            ending = marker + p_suf
            if not word.endswith(ending) or len(word) - len(ending) < 2:
                continue
            rest = word[:-len(ending)]
            feats = dict(mfeats)
            feats["Person"], feats["Number"] = pers, num
            sufs = [f"{marker}:{mfeats.get('Tense') or mfeats.get('Mood')}"] + ([f"{p_suf}:{pers}{'Pl' if num == 'Plur' else 'Sg'}"] if p_suf else [])
            for stem, f2, s2, att in _verb_base_candidates(rest):
                results.append((stem, {**feats, **f2}, s2 + sufs, att))
    for suf, mfeats in UZ_IMPERATIVE:
        if word.endswith(suf) and len(word) - len(suf) >= 2:
            rest = word[:-len(suf)]
            for stem, f2, s2, att in _verb_base_candidates(rest):
                results.append((stem, {**mfeats, **f2, "VerbForm": "Fin"}, s2 + [f"{suf}:{mfeats['Mood']}"], att))
    return results


def _strip_nonfinite(word: str):
    """Sifatdosh/ravishdosh/harakat nomi: -> [(o'zak, feats, sufs, attested)]"""
    results = []
    for suf, mfeats in UZ_NONFINITE:
        if word.endswith(suf) and len(word) - len(suf) >= 2:
            rest = word[:-len(suf)]
            for stem, f2, s2, att in _verb_base_candidates(rest):
                results.append((stem, {**mfeats, **f2}, s2 + [f"{suf}:{mfeats['VerbForm']}"], att))
    return results


def _strip_deriv(stem: str, depth: int = 0):
    """So'z yasovchi qo'shimchalar: -> [(asos, yasalgan UPOS, sufs, attested_base_entry)]"""
    out = []
    if depth > 2:
        return out
    for suf, pos in UZ_DERIV:
        if stem.endswith(suf) and len(stem) - len(suf) >= 3:
            base = stem[:-len(suf)]
            e = _uz_entry(base)
            if e:
                out.append((base, pos, [f"{suf}:Deriv→{pos}"], e))
            else:
                for b2, _pos2, s2, e2 in _strip_deriv(base, depth + 1):
                    out.append((b2, pos, s2 + [f"{suf}:Deriv→{pos}"], e2))
    return out


def _uz_analyze_word(raw: str, sent_start: bool) -> Dict[str, Any]:
    word = _norm_apos(raw).lower()
    # -dagi / -dagi (o'rin-payt + -gi sifat yasovchi): shahardagi = shahar + da + gi
    if word.endswith("dagi") and len(word) > 6:
        inner = _uz_analyze_word(word[:-2], sent_start)
        if inner["feats"].get("Case") == "Loc":
            inner = dict(inner)
            inner["upos"] = "ADJ"
            inner["sufs"] = list(inner["sufs"]) + ["gi:Deriv→ADJ"]
            inner["feats"] = {k: v for k, v in inner["feats"].items() if k != "Case"}
            inner["feats"]["Case"] = "Loc"
            return inner
    cands: List[Dict[str, Any]] = []  # score yuqori = yaxshi

    def push(stem, upos, feats, sufs, usas, score, known, deriv=None):
        cands.append({"stem": stem, "upos": upos, "feats": feats, "sufs": sufs, "usas": usas, "score": score, "known": known, "deriv": deriv or []})

    e = _uz_entry(word)
    if e:
        push(word, e["upos"], {}, [], e["usas"], 100, True)

    # Nominal
    for rest, feats, sufs in _strip_nominal(word):
        e = _uz_entry(rest)
        if e and (e["upos"] in NOMINAL_POS or any(a in NOMINAL_POS for a in e["alt"])):
            upos = e["upos"] if e["upos"] in NOMINAL_POS else next(a for a in e["alt"] if a in NOMINAL_POS)
            push(rest, upos, feats, sufs, e["usas"], 90 + len(rest) * 0.1 - len(sufs) * 0.5, True)
            continue
        # harakat nomi / sifatdosh + kelishik: yaratishning = yarat + ish + ning
        for stem, f2, s2, att in _strip_nonfinite(rest):
            if att:
                ee = _uz_entry(stem)
                push(stem, "VERB", {**f2, **feats}, s2 + sufs, ee["usas"], 85 + len(stem) * 0.1, True)
        # yasama so'z: ahamiyatlilik = ahamiyat + li + lik
        for base, pos, dsufs, ee in _strip_deriv(rest):
            push(rest, pos, feats, sufs, ee["usas"], 70 + len(base) * 0.1, True, deriv=dsufs)
    # Tuslangan fe'l
    for stem, feats, sufs, att in _strip_verbal(word):
        if att:
            ee = _uz_entry(stem)
            push(stem, "VERB", feats, sufs, ee["usas"], 92 + len(stem) * 0.1 - len(sufs) * 0.3, True)
    # Tuslanmagan fe'l (qo'shimchasiz)
    for stem, feats, sufs, att in _strip_nonfinite(word):
        if att:
            ee = _uz_entry(stem)
            push(stem, "VERB", feats, sufs, ee["usas"], 88 + len(stem) * 0.1, True)
    # Yasama (o'zi lug'atda yo'q)
    for base, pos, dsufs, ee in _strip_deriv(word):
        push(word, pos, {}, [], ee["usas"], 75 + len(base) * 0.1, True, deriv=dsufs)

    if cands:
        best = max(cands, key=lambda c: c["score"])
        return best

    # --- Noma'lum o'zak: qo'shimcha zanjiri bo'yicha taxmin ---
    if raw[0].isupper() and not sent_start:
        return {"stem": word, "upos": "PROPN", "feats": {}, "sufs": [], "usas": "Z1", "score": 0, "known": False, "deriv": []}
    verbal = [c for c in _strip_verbal(word) if len(c[0]) >= 3 and c[2] and c[2][-1].split(":")[0] in ("di", "yap", "moqda", "gan", "ib", "sa", "moqchi")]
    if verbal:
        stem, feats, sufs, _ = max(verbal, key=lambda c: len(c[0]))
        return {"stem": stem, "upos": "VERB", "feats": feats, "sufs": sufs, "usas": "Z99", "score": 0, "known": False, "deriv": []}
    nominal = [c for c in _strip_nominal(word) if len(c[0]) >= 3]
    if nominal:
        # Noma'lum o'zak: ko'proq (va kamida 2 harfli) qo'shimcha ajratilgan, so'ng uzunroq o'zak afzal
        rest, feats, sufs = max(nominal, key=lambda c: (sum(1 for s in c[2] if len(s.split(":")[0]) >= 2) - sum(1 for s in c[2] if len(s.split(":")[0]) < 2), len(c[0])))
        upos = "NOUN"
        for suf, pos in UZ_DERIV:
            if rest.endswith(suf) and len(rest) > len(suf) + 2:
                upos = pos if pos != "VERB" else "NOUN"
                break
        return {"stem": rest, "upos": upos, "feats": feats, "sufs": sufs, "usas": "Z99", "score": 0, "known": False, "deriv": []}
    upos = "NOUN"
    for suf, pos in UZ_DERIV:
        if word.endswith(suf) and len(word) > len(suf) + 2:
            upos = pos if pos != "VERB" else "NOUN"
            break
    if word.endswith("moq"):
        return {"stem": word[:-3], "upos": "VERB", "feats": {"VerbForm": "Vnoun"}, "sufs": ["moq:Vnoun"], "usas": "Z99", "score": 0, "known": False, "deriv": []}
    return {"stem": word, "upos": upos, "feats": {}, "sufs": [], "usas": "Z99", "score": 0, "known": False, "deriv": []}


def _uz_merge_mwe(tokens: List[Dict[str, Any]]) -> None:
    """Ko'p so'zli fe'llarni (qabul qil-, olib bor-, e'tibor ber-) bitta lemma ostida bog'laydi (MWE belgisi)."""
    _, multi = _lex_uz()
    n = len(tokens)
    i = 0
    while i < n:
        matched = False
        for L in (3, 2):
            if i + L > n:
                continue
            if any(tokens[j]["upos"] == "PUNCT" for j in range(i, i + L)):
                continue
            # "olib bor-", "qabul qil-": oldingi so'zlar shakli (olib, qabul) + oxirgi so'z o'zagi (bor, qil)
            key = " ".join([_norm_apos(tokens[j]["form"]).lower() for j in range(i, i + L - 1)] + [tokens[i + L - 1]["lemma"]])
            e = multi.get(key)
            if not e:
                key = " ".join(tokens[j]["lemma"] for j in range(i, i + L))
                e = multi.get(key)
            if e:
                head = tokens[i + L - 1]
                head["mwe"] = key
                head["mwe_upos"] = e["upos"]
                head["mwe_usas"] = e["usas"]
                for j in range(i, i + L - 1):
                    tokens[j]["mwe_part_of"] = key
                i += L
                matched = True
                break
        if not matched:
            i += 1


def tag_uzbek(text: str) -> List[Dict[str, Any]]:
    sentences = []
    for s_idx, sent in enumerate(split_sentences(text)):
        toks = tokenize(sent)
        tagged: List[Dict[str, Any]] = []
        for i, raw in enumerate(toks):
            if _is_punct(raw):
                tagged.append({"id": i + 1, "form": raw, "lemma": raw, "upos": "PUNCT", "xpos": "PUNCT", "feats": {}, "usas": "-", "morph": raw, "known": True, "sufs": []})
                continue
            if re.fullmatch(r"\d+(?:[.,]\d+)?", raw):
                tagged.append({"id": i + 1, "form": raw, "lemma": raw, "upos": "NUM", "xpos": "NUM", "feats": {"NumType": "Card"}, "usas": "N1", "morph": raw, "known": True, "sufs": []})
                continue
            a = _uz_analyze_word(raw, i == 0)
            feats = dict(a["feats"])
            upos = a["upos"]
            if upos in ("NOUN", "PROPN", "ADJ", "NUM", "PRON", "DET") and "Case" not in feats and upos in ("NOUN", "PROPN", "PRON"):
                feats["Case"] = "Nom"
            chain = " + ".join([a["stem"]] + [s.split(":")[0] for s in a["deriv"]] + [s.split(":")[0] for s in a["sufs"]])
            tagged.append({"id": i + 1, "form": raw, "lemma": a["stem"], "upos": upos, "xpos": upos, "feats": feats,
                           "usas": a["usas"], "known": a["known"], "sufs": a["deriv"] + a["sufs"], "morph": chain})
        # Kontekst: "bor"/"yo'q"/"kerak" + "edi" va h.k. — bog'lama AUX
        for i, t in enumerate(tagged):
            if t["lemma"] == "bo'l" and i > 0 and tagged[i - 1]["upos"] in ("ADJ", "NOUN") and t["upos"] == "VERB":
                t["upos"] = "AUX"
        _uz_merge_mwe(tagged)
        sentences.append({"id": s_idx + 1, "text": sent, "tokens": tagged})
    return sentences


def tag_text(text: str, lang: str = "auto") -> Dict[str, Any]:
    text = (text or "")[:MAX_TEXT_CHARS]
    if lang == "auto":
        lang = detect_language(text)
    sents = tag_english(text) if lang == "en" else tag_uzbek(text)
    return {"lang": lang, "sentences": sents, "stats": language_stats(sents, lang)}


def detect_language(text: str) -> str:
    t = _norm_apos(text or "").lower()
    uz_markers = len(re.findall(r"o'|g'|\bva\b|\bbilan\b|\buchun\b|lar\b|ning\b|\bbu\b|sh|\bham\b", t))
    en_markers = len(re.findall(r"\bthe\b|\band\b|\bof\b|\bis\b|\bare\b|\bto\b|\bin\b|\bthat\b", t))
    return "uz" if uz_markers > en_markers else "en"


def language_stats(sents: List[Dict[str, Any]], lang: str) -> Dict[str, Any]:
    tokens = [t for s in sents for t in s["tokens"] if t["upos"] != "PUNCT"]
    lemmas = [t["lemma"] for t in tokens]
    pos = Counter(t["upos"] for t in tokens)
    usas = Counter(t["usas"].split(".")[0][:1] if t["usas"] not in ("-", "Z99") else ("Z99" if t["usas"] == "Z99" else "-") for t in tokens)
    feats: Dict[str, Counter] = defaultdict(Counter)
    for t in tokens:
        for k, v in t["feats"].items():
            feats[k][v] += 1
    known = sum(1 for t in tokens if t.get("known"))
    return {
        "lang": lang,
        "sentences": len(sents),
        "tokens": len(tokens),
        "types": len(set(lemmas)),
        "ttr": round(len(set(lemmas)) / len(tokens), 3) if tokens else 0,
        "lexicon_coverage": round(known / len(tokens), 3) if tokens else 0,
        "pos_distribution": dict(pos.most_common()),
        "usas_distribution": dict(usas.most_common()),
        "feature_distribution": {k: dict(v.most_common()) for k, v in feats.items()},
        "avg_suffixes_per_token": round(sum(len(t.get("sufs", [])) for t in tokens) / len(tokens), 2) if (tokens and lang == "uz") else None,
    }


# ====================================================================================
# KOLLOKATSIYA AJRATISH + STATISTIK MEZONLAR
# ====================================================================================
EN_LIGHT_VERBS = {"make", "do", "take", "give", "have", "get", "pay", "put", "hold", "keep", "conduct", "carry", "perform",
                  "draw", "run", "raise", "pose", "commit", "reach", "achieve", "express", "provide", "offer", "set"}
EN_ERADICATION = {"break", "reject", "lose", "cancel", "fail", "lift", "withdraw", "dispel", "revoke", "destroy", "remove",
                  "abolish", "violate", "deny", "refuse", "dismiss", "drop", "kill"}
UZ_ERADICATION = {"buz", "rad et", "yo'qot", "bekor qil", "boy ber", "yiqil", "sindir", "o'ldir", "yo'q qil", "inkor et"}
MAGN = {"heavy", "strong", "deep", "high", "great", "big", "large", "huge", "intense", "severe", "bitter", "wide", "broad",
        "highly", "deeply", "strongly", "widely", "closely", "extremely", "very", "completely", "fully", "entirely", "absolutely",
        "kuchli", "qattiq", "chuqur", "yuqori", "katta", "og'ir", "achchiq", "ashaddiy", "qahraton", "keng", "juda",
        "nihoyatda", "g'oyat", "mutlaqo", "butunlay", "to'liq", "uzviy", "eng"}
ANTIMAGN = {"light", "slight", "weak", "low", "small", "little", "minor", "slightly", "partly", "partially", "mild",
            "yengil", "kichik", "kuchsiz", "zaif", "past", "oz", "biroz", "qisman", "mayda", "kam"}
BON = {"good", "great", "fruitful", "warm", "golden", "effective", "successful", "excellent", "perfect", "rich", "positive",
       "yaxshi", "samarali", "samimiy", "oltin", "iliq", "muvaffaqiyatli", "boy", "a'lo", "ijobiy"}
ANTIBON = {"poor", "bad", "false", "wrong", "inadequate", "negative", "yomon", "sifatsiz", "noto'g'ri", "salbiy"}
REAL = {"keep", "pass", "achieve", "fulfil", "fulfill", "meet", "satisfy", "solve", "realize", "fill", "bajar", "erish", "o't",
        "hal qil", "to'ldir", "tur", "qondir", "yech"}
CAUS = {"cause", "raise", "create", "produce", "generate", "provoke", "arouse", "yetkaz", "uyg'ot", "keltirib chiqar", "sabab bo'l", "yarat"}
INCEP = {"begin", "start", "open", "launch", "catch", "boshla", "kirish", "yubor"}
FIN = {"finish", "end", "close", "lose", "tugat", "yo'qot", "tuga"}
SING = {"piece", "bit", "slice", "drop", "og'iz", "bo'lak", "parcha", "qultum", "dona"}
MULT = {"swarm", "flock", "herd", "group", "series", "set", "pack", "bunch", "to'da", "gala", "guruh", "to'p"}
EN_G1_PREPS = {"in", "for", "to", "on", "towards", "toward", "with", "about", "at", "between", "against", "from"}
EN_G5_PREPS = {"of", "for", "to", "with", "at", "in", "on", "about", "from"}
EN_G8_PREPS = {"on", "upon", "for", "to", "with", "at", "in", "from", "into", "about", "against"}
UZ_POSTPOS = {"haqida", "uchun", "bilan", "bo'yicha", "orqali", "tomonidan", "sifatida", "doirasida", "asosida", "to'g'risida", "kabi", "sari", "qarshi"}
STRUCT_UZ_LABEL = {"ADJ+NOUN": "sifat + ot", "NOUN+NOUN": "ot + ot", "VERB+NOUN": "fe'l + ot", "NOUN+VERB": "ot + fe'l",
                   "ADV+ADJ": "ravish + sifat", "VERB+ADV": "fe'l + ravish", "ADV+VERB": "ravish + fe'l", "NOUN+of+NOUN": "ot + of + ot",
                   "NUM+NOUN+NOUN": "son + ot + ot", "NOUN+PREP": "ot + predlog", "ADJ+PREP": "sifat + predlog", "VERB+PREP": "fe'l + predlog",
                   "NOUN+POSTP": "ot + ko'makchi"}


def _lf_for(struct: str, collocator: str, verb: str, bbi: str) -> str:
    c = collocator
    if struct in ("ADJ+NOUN", "ADV+ADJ", "VERB+ADV", "ADV+VERB"):
        if c in MAGN:
            return "Magn"
        if c in ANTIMAGN:
            return "AntiMagn"
        if c in BON:
            return "Bon"
        if c in ANTIBON:
            return "AntiBon"
        return "-"
    if struct in ("VERB+NOUN", "NOUN+VERB") and bbi in ("L1", "L2"):
        if verb in CAUS:
            return "Caus"
        if verb in INCEP:
            return "IncepOper1"
        if verb in FIN:
            return "FinOper1"
        if verb in UZ_ERADICATION or verb in EN_ERADICATION:
            return "AntiReal1"
        if verb in REAL:
            return "Real1"
        if verb in EN_LIGHT_VERBS or verb in UZ_LIGHT_VERBS:
            return "Oper1"
        return "-"
    if bbi == "L4":
        return "Func0"
    if bbi == "L5":
        if c in SING:
            return "Sing"
        if c in MULT:
            return "Mult"
    return "-"


def _content_tokens(sent_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for t in sent_tokens:
        if t["upos"] == "PUNCT" or t.get("mwe_part_of"):
            continue
        tt = dict(t)
        if t.get("mwe"):
            tt["lemma"] = t["mwe"]
            tt["upos"] = t.get("mwe_upos", t["upos"])
            tt["usas"] = t.get("mwe_usas", t["usas"])
        out.append(tt)
    return out


def _is_nounlike(t: Dict[str, Any]) -> bool:
    return t["upos"] in ("NOUN", "PROPN") or (t["upos"] == "VERB" and t["feats"].get("VerbForm") == "Vnoun")


def extract_candidates(sents: List[Dict[str, Any]], lang: str, span: int = 3) -> List[Dict[str, Any]]:
    """Struktur naqshlar bo'yicha kollokatsiya nomzodlari (har bir uchrash alohida)."""
    cands: List[Dict[str, Any]] = []

    def add(sent_id, t1, t2, struct, bbi, base_tok, extra=None):
        base = base_tok["lemma"]
        collocator = t1["lemma"] if base_tok is t2 else t2["lemma"]
        verb = t1["lemma"] if t1["upos"] == "VERB" else (t2["lemma"] if t2["upos"] == "VERB" else "")
        cands.append({
            "sentence_id": sent_id, "w1": t1["lemma"], "w2": t2["lemma"], "forms": f"{t1['form']} {t2['form']}" if not extra else extra,
            "pos": f"{t1['upos']}+{t2['upos']}", "structure": struct, "structure_uz": STRUCT_UZ_LABEL.get(struct, struct), "bbi": bbi,
            "base": base, "collocator": collocator, "usas": base_tok.get("usas", "Z99"),
            "lf": _lf_for(struct, collocator, verb, bbi),
            "positions": [t1["id"], t2["id"]],
        })

    for s in sents:
        toks = _content_tokens(s["tokens"])
        n = len(toks)
        for i, a in enumerate(toks):
            for j in range(i + 1, min(n, i + 1 + span)):
                b = toks[j]
                between = toks[i + 1:j]
                adjacent = (j == i + 1)
                a_noun, b_noun = _is_nounlike(a), _is_nounlike(b)
                nxt = toks[j + 1] if j + 1 < n else None
                if lang == "en":
                    if a["upos"] == "ADJ" and b_noun and all(x["upos"] == "ADJ" for x in between):
                        add(s["id"], a, b, "ADJ+NOUN", "L3", b)
                    elif a_noun and b_noun and adjacent and a["upos"] != "PROPN":
                        add(s["id"], a, b, "NOUN+NOUN", "NN", b)
                    elif (a["upos"] == "VERB" and a["feats"].get("VerbForm") != "Vnoun" and b_noun
                          and all(x["upos"] in ("DET", "ADJ", "PRON", "NUM", "ADV") for x in between)
                          and not (nxt and nxt["upos"] in ("NOUN", "PROPN"))):  # ot zanjirida bosh so'z oxirgisi
                        bbi = "L2" if a["lemma"] in EN_ERADICATION else "L1"
                        add(s["id"], a, b, "VERB+NOUN", bbi, b)
                    elif (a_noun and b["upos"] == "VERB" and adjacent and b["feats"].get("VerbForm") in ("Fin", None)
                          and b["lemma"] not in EN_LIGHT_VERBS
                          and not (nxt and nxt["upos"] in ("DET", "NOUN", "PROPN", "ADJ", "PRON", "NUM"))):  # to'ldiruvchisiz (o'timsiz) fe'l
                        add(s["id"], a, b, "NOUN+VERB", "L4", a)
                    elif a_noun and b_noun and j == i + 2 and between and between[0]["lemma"] == "of" and a["lemma"] in (SING | MULT | {"range", "number", "kind", "type", "series", "cup", "glass", "lot"}):
                        add(s["id"], a, b, "NOUN+of+NOUN", "L5", b, extra=f"{a['form']} of {b['form']}")
                    elif a["upos"] == "ADV" and b["upos"] == "ADJ" and adjacent:
                        add(s["id"], a, b, "ADV+ADJ", "L6", b)
                    elif a["upos"] == "VERB" and b["upos"] == "ADV" and adjacent and b["lemma"] not in ("not", "also", "only", "then", "however", "also", "thus"):
                        add(s["id"], a, b, "VERB+ADV", "L7", a)
                    elif a["upos"] == "ADV" and b["upos"] == "VERB" and adjacent and a["lemma"] not in ("not", "also", "only", "then", "however", "thus", "therefore"):
                        add(s["id"], a, b, "ADV+VERB", "L7", b)
                    elif a_noun and b["upos"] == "ADP" and adjacent and b["lemma"] in EN_G1_PREPS:
                        add(s["id"], a, b, "NOUN+PREP", "G1", a)
                    elif a["upos"] == "ADJ" and b["upos"] == "ADP" and adjacent and b["lemma"] in EN_G5_PREPS:
                        add(s["id"], a, b, "ADJ+PREP", "G5", a)
                    elif a["upos"] == "VERB" and b["upos"] == "ADP" and adjacent and b["lemma"] in EN_G8_PREPS:
                        add(s["id"], a, b, "VERB+PREP", "G8", a)
                else:  # uz
                    a_case = a["feats"].get("Case", "Nom")
                    b_bare_or_izofa = b["feats"].get("Case", "Nom") == "Nom" or b["feats"].get("Person[psor]") == "3"
                    a_bare = a_case == "Nom" and "Person[psor]" not in a["feats"] and a["feats"].get("Number") != "Plur"
                    if a["upos"] == "ADJ" and b_noun and all(x["upos"] == "ADJ" for x in between) and a["feats"].get("Case", "Nom") == "Nom":
                        add(s["id"], a, b, "ADJ+NOUN", "L3", b)
                    elif a_noun and b_noun and adjacent and a_bare and b_bare_or_izofa and a["upos"] != "PROPN":
                        struct = "NOUN+NOUN"
                        add(s["id"], a, b, struct, "NN", b)
                        if b["feats"].get("Person[psor]") == "3":
                            cands[-1]["structure_uz"] = "ot + ot (izofa)"
                    elif a["upos"] == "NUM" and a["lemma"] == "bir" and j == i + 2 and between and between[0]["lemma"] in UZ_QUANT and b_noun:
                        add(s["id"], between[0], b, "NUM+NOUN+NOUN", "L5", b, extra=f"bir {between[0]['form']} {b['form']}")
                    elif a_noun and b["upos"] == "VERB" and b["feats"].get("VerbForm") != "Vnoun" and all(x["upos"] in ("ADV",) for x in between):
                        if b["lemma"] in UZ_ERADICATION:
                            bbi = "L2"
                        elif a_case == "Nom" and b["lemma"] in UZ_INTRANSITIVE and b["lemma"] not in UZ_LIGHT_VERBS:
                            bbi = "L4"
                        else:
                            bbi = "L1"
                        add(s["id"], a, b, "NOUN+VERB", bbi, a)
                        cands[-1]["structure_uz"] = f"ot({a_case}) + fe'l"
                    elif a["upos"] == "ADV" and b["upos"] == "ADJ" and adjacent:
                        add(s["id"], a, b, "ADV+ADJ", "L6", b)
                    elif a["upos"] == "ADV" and b["upos"] == "VERB" and adjacent:
                        add(s["id"], a, b, "ADV+VERB", "L7", b)
                    elif a_noun and b["upos"] == "ADP" and adjacent and b["lemma"] in UZ_POSTPOS:
                        add(s["id"], a, b, "NOUN+POSTP", "G1", a)
    return cands


def _association(o11: int, r1: int, c1: int, n: int) -> Dict[str, float]:
    """MI, t-score, log-likelihood (Dunning), logDice (Rychlý)."""
    n = max(n, 1)
    e11 = r1 * c1 / n
    mi = math.log2(o11 * n / (r1 * c1)) if r1 and c1 and o11 else 0.0
    t = (o11 - e11) / math.sqrt(o11) if o11 else 0.0
    logdice = 14 + math.log2(2 * o11 / (r1 + c1)) if (r1 + c1) and o11 else 0.0
    # 2x2 kontingensiya
    o12, o21 = r1 - o11, c1 - o11
    o22 = n - r1 - c1 + o11
    ll = 0.0
    for o, e in ((o11, e11), (o12, r1 * (n - c1) / n), (o21, (n - r1) * c1 / n), (o22, (n - r1) * (n - c1) / n)):
        if o > 0 and e > 0:
            ll += o * math.log(o / e)
    ll *= 2
    return {"mi": round(mi, 3), "t_score": round(t, 3), "log_likelihood": round(ll, 3), "logdice": round(logdice, 3)}


def _bank_match(lang: str, w1: str, w2: str) -> Optional[Dict[str, Any]]:
    en_idx, uz_idx = _bank_index()
    idx = en_idx if lang == "en" else uz_idx
    pair = {w1, w2}
    for key, items in idx.items():
        if len(key) >= 2 and pair <= key:
            return items[0]
    return None


def collocations_from_sentences(sents: List[Dict[str, Any]], lang: str, min_freq: int = 1, span: int = 3) -> List[Dict[str, Any]]:
    cands = extract_candidates(sents, lang, span=span)
    content = [t for s in sents for t in _content_tokens(s["tokens"])]
    n = len(content)
    lemma_freq = Counter(t["lemma"] for t in content)
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for c in cands:
        grouped[(c["w1"], c["w2"], c["structure"])].append(c)
    out = []
    for (w1, w2, struct), occ in grouped.items():
        o11 = len(occ)
        if o11 < min_freq:
            continue
        first = occ[0]
        meas = _association(o11, lemma_freq.get(w1, o11), lemma_freq.get(w2, o11), n)
        bank = _bank_match(lang, w1, w2)
        strength = "kuchli" if meas["logdice"] >= 7 else ("o'rtacha" if meas["logdice"] >= 3 else "kuchsiz")
        item = {
            "collocation": f"{w1} {w2}" if struct != "NOUN+of+NOUN" else f"{w1} of {w2}",
            "forms": sorted({o["forms"] for o in occ})[:5],
            "w1": w1, "w2": w2, "frequency": o11, "f_w1": lemma_freq.get(w1, o11), "f_w2": lemma_freq.get(w2, o11),
            "structure": struct, "structure_uz": first["structure_uz"], "pos": first["pos"], "bbi": first["bbi"],
            "base": first["base"], "collocator": first["collocator"], "usas": first["usas"], "lf": first["lf"],
            "measures": meas, "strength": strength,
            "sentence_ids": sorted({o["sentence_id"] for o in occ}),
            "in_bank": bool(bank),
        }
        if bank:
            item.update({"bank_id": bank["id"], "bbi": bank["bbi"], "lf": bank["lf"] if bank["lf"] != "-" else item["lf"],
                         "usas": bank["usas"], "continuum": bank["continuum"], "equivalence": bank["equivalence"],
                         "procedure": bank["procedure"], "counterpart": bank["uz"] if lang == "en" else bank["en"],
                         "culture": bool(bank.get("culture")), "note": bank.get("note", "")})
        else:
            item["continuum"] = "restricted" if (item["lf"] != "-" or struct in ("NOUN+NOUN", "NOUN+of+NOUN", "NUM+NOUN+NOUN")) else "free?"
        out.append(item)
    out.sort(key=lambda x: (-x["frequency"], -x["measures"]["logdice"]))
    return out


# ====================================================================================
# GAPLARNI TEKISLASH (Gale & Church uslubida) VA EKVIVALENTLIK
# ====================================================================================
def align_sentences(en_sents: List[str], uz_sents: List[str]) -> Tuple[List[Dict[str, Any]], str]:
    """-> ([{'en': [idx...], 'uz': [idx...]}], usul). Qatorlar soni teng bo'lsa 1:1 qabul qilinadi."""
    if not en_sents or not uz_sents:
        return [], "empty"
    if len(en_sents) == len(uz_sents):
        return [{"en": [i], "uz": [i]} for i in range(len(en_sents))], "1:1 (teng gaplar soni)"
    le = [len(s) for s in en_sents]
    lu = [len(s) for s in uz_sents]
    c = sum(le) / max(1, sum(lu))
    beads = [(1, 1, 0.0), (1, 2, 2.3), (2, 1, 2.3), (1, 0, 6.0), (0, 1, 6.0), (2, 2, 3.5)]
    INF = float("inf")
    m, k = len(en_sents), len(uz_sents)
    cost = [[INF] * (k + 1) for _ in range(m + 1)]
    back: List[List[Optional[Tuple[int, int]]]] = [[None] * (k + 1) for _ in range(m + 1)]
    cost[0][0] = 0.0
    for i in range(m + 1):
        for j in range(k + 1):
            if cost[i][j] == INF:
                continue
            for de, du, pen in beads:
                ni, nj = i + de, j + du
                if ni > m or nj > k:
                    continue
                l1 = sum(le[i:ni])
                l2 = sum(lu[j:nj]) * c
                delta = (l1 - l2) ** 2 / (6.8 * (l1 + l2) + 1.0)
                nc = cost[i][j] + delta + pen
                if nc < cost[ni][nj]:
                    cost[ni][nj] = nc
                    back[ni][nj] = (de, du)
    pairs = []
    i, j = m, k
    while i > 0 or j > 0:
        b = back[i][j]
        if not b:
            break
        de, du = b
        pairs.append({"en": list(range(i - de, i)), "uz": list(range(j - du, j))})
        i, j = i - de, j - du
    pairs.reverse()
    return pairs, "Gale–Church (uzunlikka asoslangan DP)"


def _canonical_struct_match(s_en: str, s_uz: str) -> bool:
    canon = {"ADJ+NOUN": {"ADJ+NOUN"}, "NOUN+NOUN": {"NOUN+NOUN"}, "VERB+NOUN": {"NOUN+VERB"}, "NOUN+VERB": {"NOUN+VERB"},
             "ADV+ADJ": {"ADV+ADJ"}, "VERB+ADV": {"ADV+VERB"}, "ADV+VERB": {"ADV+VERB"}, "NOUN+of+NOUN": {"NUM+NOUN+NOUN", "NOUN+NOUN"},
             "NOUN+PREP": {"NOUN+POSTP"}}
    return s_uz in canon.get(s_en, set())


def pair_collocations(en_sents: List[Dict[str, Any]], uz_sents: List[Dict[str, Any]], en_coll: List[Dict[str, Any]],
                      uz_coll: List[Dict[str, Any]], pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tekislangan gap juftliklarida kollokatsiyalarni moslashtirish va ekvivalentlik tipini aniqlash."""
    results = []
    uz_by_sent: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for cz in uz_coll:
        for sid in cz["sentence_ids"]:
            uz_by_sent[sid].append(cz)
    uz_stems_by_sent: Dict[int, set] = {}
    for s in uz_sents:
        stems = set()
        for t in _content_tokens(s["tokens"]):
            stems.add(t["lemma"])
            if t.get("mwe"):
                stems.update(t["mwe"].split())
        uz_stems_by_sent[s["id"]] = stems
    used_uz: set = set()

    for p in pairs:
        en_ids = [i + 1 for i in p["en"]]
        uz_ids = [i + 1 for i in p["uz"]]
        uz_cands = [c for sid in uz_ids for c in uz_by_sent.get(sid, [])]
        uz_stems = set().union(*[uz_stems_by_sent.get(sid, set()) for sid in uz_ids]) if uz_ids else set()
        for ce in en_coll:
            if not any(sid in ce["sentence_ids"] for sid in en_ids):
                continue
            rec: Dict[str, Any] = {"en": ce["collocation"], "en_structure": ce["structure"], "en_bbi": ce["bbi"], "lf": ce["lf"], "usas": ce["usas"],
                                   "sentence_pair": {"en": en_ids, "uz": uz_ids}, "uz": None, "uz_structure": None,
                                   "equivalence": "unaligned", "procedure": "-", "confidence": "none", "culture": False, "note": ""}
            bank = collocation_bank()
            bank_item = next((b for b in bank if b["id"] == ce.get("bank_id")), None)
            matched = None
            # 1) Bank: ikkala tomon ham bankda, bir xil id
            if bank_item:
                for cz in uz_cands:
                    if cz.get("bank_id") == bank_item["id"]:
                        matched = cz
                        break
                if not matched and set(bank_item["uz_stems"]) <= uz_stems:
                    rec["uz"] = bank_item["uz"]
                    rec["uz_structure"] = bank_item["structure_uz"]
                if matched or rec["uz"]:
                    rec.update({"uz": matched["collocation"] if matched else rec["uz"],
                                "uz_structure": matched["structure"] if matched else rec["uz_structure"],
                                "equivalence": bank_item["equivalence"], "procedure": bank_item["procedure"],
                                "confidence": "bank", "culture": bool(bank_item.get("culture")), "note": bank_item.get("note", ""),
                                "continuum": bank_item["continuum"], "lf": bank_item["lf"] if bank_item["lf"] != "-" else ce["lf"]})
            # 2) Lug'at asosida: inglizcha lemma -> o'zbekcha o'zaklar
            if rec["confidence"] == "none":
                tr1 = set(_uz_translations_of_en(ce["w1"]))
                tr2 = set(_uz_translations_of_en(ce["w2"]))
                tr_base = tr2 if ce["base"] == ce["w2"] else tr1
                tr_col = tr1 if ce["base"] == ce["w2"] else tr2
                grammatical = ce["bbi"].startswith("G")
                best, best_score = None, 0
                for cz in uz_cands:
                    if id(cz) in used_uz:
                        continue
                    if grammatical != cz["bbi"].startswith("G"):
                        continue  # leksik ↔ grammatik kollokatsiyalar aralashtirilmaydi
                    cz_set = {cz["w1"], cz["w2"]} | set(cz["w1"].split()) | set(cz["w2"].split())
                    score = (2 if cz_set & tr_base else 0) + (1 if cz_set & tr_col else 0)
                    if score and _canonical_struct_match(ce["structure"], cz["structure"]):
                        score += 0.5
                    if score > best_score:
                        best, best_score = cz, score
                if best and best_score >= 2:
                    used_uz.add(id(best))
                    canon = _canonical_struct_match(ce["structure"], best["structure"])
                    if best_score >= 3:
                        eq = "full" if canon else "partial"
                        proc = "calque" if canon else "transposition"
                    else:
                        eq, proc = "partial", "modulation"
                    rec.update({"uz": best["collocation"], "uz_structure": best["structure"], "equivalence": eq, "procedure": proc,
                                "confidence": "lexicon", "note": "Ikki tilli lug'at asosida avtomatik moslashtirildi; ekspert tekshiruvi lozim."})
                elif grammatical and tr_base & uz_stems:
                    base_stem = next(iter(tr_base & uz_stems))
                    rec.update({"uz": base_stem + " + kelishik/ko'makchi", "uz_structure": "NOUN(Case)", "equivalence": "grammatical",
                                "procedure": "transposition", "confidence": "heuristic",
                                "note": "Grammatik kollokatsiya: inglizcha predlog o'zbekchada kelishik qo'shimchasi yoki ko'makchi bilan beriladi (tipologik farq)."})
                elif tr_base & uz_stems:
                    base_stem = next(iter(tr_base & uz_stems))
                    rec.update({"uz": base_stem + " (…)", "uz_structure": "?", "equivalence": "zero?", "procedure": "paraphrase/transposition?",
                                "confidence": "heuristic", "note": "Tayanch so'z tarjimasi topildi, kollokator mos kelmadi — lakuna yoki tavsifiy tarjima bo'lishi mumkin."})
            results.append(rec)
    return results


# ====================================================================================
# TO'LIQ TAHLIL VA EKSPORT
# ====================================================================================
def analyze_parallel(en_text: str, uz_text: str, min_freq: int = 1, span: int = 3) -> Dict[str, Any]:
    en_text = (en_text or "")[:MAX_TEXT_CHARS]
    uz_text = (uz_text or "")[:MAX_TEXT_CHARS]
    en_sents = tag_english(en_text)
    uz_sents = tag_uzbek(uz_text)
    en_coll = collocations_from_sentences(en_sents, "en", min_freq=min_freq, span=span)
    uz_coll = collocations_from_sentences(uz_sents, "uz", min_freq=min_freq, span=span)
    pairs, method = align_sentences([s["text"] for s in en_sents], [s["text"] for s in uz_sents])
    coll_pairs = pair_collocations(en_sents, uz_sents, en_coll, uz_coll, pairs)

    def dist(items, key):
        return dict(Counter(str(i.get(key, "-")) for i in items).most_common())

    aligned = [r for r in coll_pairs if r["equivalence"] != "unaligned"]
    summary = {
        "en_collocations": len(en_coll), "uz_collocations": len(uz_coll), "aligned_pairs": len(aligned),
        "by_structure_en": dist(en_coll, "structure"), "by_structure_uz": dist(uz_coll, "structure_uz"),
        "by_bbi_en": dist(en_coll, "bbi"), "by_bbi_uz": dist(uz_coll, "bbi"),
        "by_lf_en": dist(en_coll, "lf"), "by_lf_uz": dist(uz_coll, "lf"),
        "by_usas_en": dist(en_coll, "usas"), "by_usas_uz": dist(uz_coll, "usas"),
        "by_equivalence": dist(aligned, "equivalence"), "by_procedure": dist(aligned, "procedure"),
        "by_confidence": dist(coll_pairs, "confidence"),
        "culture_specific": [r for r in aligned if r.get("culture")],
        "top_en": sorted(en_coll, key=lambda x: -x["measures"]["logdice"])[:10],
        "top_uz": sorted(uz_coll, key=lambda x: -x["measures"]["logdice"])[:10],
        "in_bank_en": sum(1 for c in en_coll if c["in_bank"]), "in_bank_uz": sum(1 for c in uz_coll if c["in_bank"]),
    }
    return {
        "meta": {"alignment_method": method, "sentence_pairs": len(pairs), "min_freq": min_freq, "span": span,
                 "standards": "UD v2 UPOS/FEATS · PTB · USAS · BBI · Mel'čuk LF · MI/t/LL/logDice · Gale–Church · Vinay–Darbelnet/Baker"},
        "source": {"lang": "en", "stats": language_stats(en_sents, "en"), "sentences": en_sents, "collocations": en_coll},
        "target": {"lang": "uz", "stats": language_stats(uz_sents, "uz"), "sentences": uz_sents, "collocations": uz_coll},
        "alignment": {"pairs": [{"en": [i + 1 for i in p["en"]], "uz": [i + 1 for i in p["uz"]],
                                 "en_text": " ".join(en_sents[i]["text"] for i in p["en"]),
                                 "uz_text": " ".join(uz_sents[i]["text"] for i in p["uz"])} for p in pairs],
                      "collocation_pairs": coll_pairs},
        "summary": summary,
    }


def to_conllu(sents: List[Dict[str, Any]], lang: str) -> str:
    lines = []
    for s in sents:
        lines.append(f"# sent_id = {lang}-{s['id']}")
        lines.append(f"# text = {s['text']}")
        for t in s["tokens"]:
            feats = "|".join(f"{k}={v}" for k, v in sorted(t["feats"].items())) or "_"
            misc = [f"Usas={t['usas']}"]
            if t.get("sufs"):
                misc.append("Morph=" + "+".join(x.split(":")[0] for x in t["sufs"]))
            if t.get("mwe"):
                misc.append("MWE=" + t["mwe"].replace(" ", "_"))
            if not t.get("known", True):
                misc.append("Lexicon=unknown")
            lines.append("\t".join([str(t["id"]), t["form"], t["lemma"], t["upos"], t.get("xpos", "_"), feats, "_", "_", "_", "|".join(misc)]))
        lines.append("")
    return "\n".join(lines)


def collocations_tsv(coll: List[Dict[str, Any]], lang: str) -> str:
    head = ["lang", "collocation", "forms", "structure", "bbi", "lf", "usas", "base", "collocator", "freq", "f_w1", "f_w2",
            "MI", "t_score", "log_likelihood", "logDice", "strength", "continuum", "in_bank", "equivalence", "procedure", "counterpart", "note"]
    rows = ["\t".join(head)]
    for c in coll:
        m = c["measures"]
        rows.append("\t".join(str(x).replace("\t", " ") for x in [
            lang, c["collocation"], "; ".join(c["forms"]), c["structure"], c["bbi"], c["lf"], c["usas"], c["base"], c["collocator"],
            c["frequency"], c["f_w1"], c["f_w2"], m["mi"], m["t_score"], m["log_likelihood"], m["logdice"], c["strength"],
            c.get("continuum", ""), c["in_bank"], c.get("equivalence", ""), c.get("procedure", ""), c.get("counterpart", ""), c.get("note", "")]))
    return "\n".join(rows)


def pairs_tsv(pairs: List[Dict[str, Any]]) -> str:
    head = ["en", "en_structure", "en_bbi", "lf", "usas", "uz", "uz_structure", "equivalence", "procedure", "confidence", "culture", "note", "en_sent", "uz_sent"]
    rows = ["\t".join(head)]
    for r in pairs:
        rows.append("\t".join(str(x).replace("\t", " ") for x in [
            r["en"], r["en_structure"], r["en_bbi"], r["lf"], r["usas"], r.get("uz") or "", r.get("uz_structure") or "", r["equivalence"],
            r["procedure"], r["confidence"], r["culture"], r.get("note", ""),
            ",".join(map(str, r["sentence_pair"]["en"])), ",".join(map(str, r["sentence_pair"]["uz"]))]))
    return "\n".join(rows)


SAMPLE_EN = """Collocations are a central problem in the translation of literary texts.
The researcher conducted research on the parallel corpus of translated texts.
We drew a conclusion that strong tea and heavy rain have no literal equivalents.
The translator made a decision to keep the mother tongue flavour of the original.
Native speakers pay attention to collocational range when they translate idioms.
The study identified a golden opportunity to fill a gap in Uzbek lexicography.
Heavy traffic in the city caused damage to the daily schedule of the students.
The old man caught a cold after he had sat an exam in a cold room.
Bees buzz in the garden while the children drink green tea with their mother.
Statistical measures such as mutual information reveal lexical collocations in large corpora."""

SAMPLE_UZ = """Kollokatsiyalar badiiy matnlar tarjimasida markaziy muammo hisoblanadi.
Tadqiqotchi tarjima matnlarining parallel korpusida tadqiqot olib bordi.
Biz achchiq choy va kuchli yomg'ir birikmalarining so'zma-so'z ekvivalenti yo'q degan xulosa chiqardik.
Tarjimon asliyatning ona tili ruhini saqlab qolishga qaror qabul qildi.
Til sohiblari idiomalarni tarjima qilganda kollokatsion doiraga e'tibor beradilar.
Tadqiqot o'zbek leksikografiyasidagi bo'shliqni to'ldirish uchun oltin imkoniyatni aniqladi.
Shahardagi tirbandlik talabalarning kunlik jadvaliga zarar yetkazdi.
Keksa odam sovuq xonada imtihon topshirgandan keyin shamolladi.
Bolalar onalari bilan ko'k choy ichayotganda bog'da arilar g'ing'illaydi.
O'zaro axborot kabi statistik ko'rsatkichlar katta korpuslarda leksik kollokatsiyalarni ochib beradi."""
