"""
Parallel korpus API: morfologik/semantik teglash, kollokatsiya ajratish, tekislash va eksport.
Dissertatsiya: "Tarjima va teng matnlar parallel korpusida o'zaro faol birikuvchi (kollokatsion)
so'zlar tadqiqi (o'zbek va ingliz tillari misolida)".

Ochiq (autentifikatsiyasiz) tadqiqot vositasi — IP bo'yicha so'rovlar chegaralanadi.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.core.ratelimit import SlidingWindowLimiter, client_ip
from app.services import corpus_tagger as ct

router = APIRouter(prefix="/corpus", tags=["Tadqiqotchi: Parallel korpus"])

_limiter = SlidingWindowLimiter(max_events=40, window_seconds=60)


def _guard(request: Request) -> None:
    _limiter.check_and_record(f"corpus:{client_ip(request)}", "Korpus tahlili so'rovlari chegarasi (daqiqada 40). Biroz kutib qayta urinib ko'ring.")


class TagRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=ct.MAX_TEXT_CHARS)
    lang: str = Field("auto", pattern="^(auto|en|uz)$")


class AnalyzeRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=ct.MAX_TEXT_CHARS, description="Inglizcha (asliyat yoki tarjima) matn")
    target_text: str = Field(..., min_length=1, max_length=ct.MAX_TEXT_CHARS, description="O'zbekcha parallel matn")
    min_freq: int = Field(1, ge=1, le=50)
    span: int = Field(3, ge=1, le=5)


@router.get("/tagset")
def get_tagset():
    """Teglash sxemasi: UD UPOS/belgilar, PTB, USAS 21 maydon, BBI tiplari, Mel'čuk LF, mezonlar, ekvivalentlik, adabiyotlar."""
    data = ct.tagset()
    en_single, en_multi = ct._lex_en()
    uz_single, uz_multi = ct._lex_uz()
    return {**data, "lexicon_sizes": {"en": len(en_single) + len(en_multi), "uz": len(uz_single) + len(uz_multi),
                                      "uz_multiword": len(uz_multi), "bank": len(ct.collocation_bank())}}


@router.get("/collocations")
def get_bank(q: Optional[str] = Query(None, max_length=60), bbi: Optional[str] = Query(None, max_length=4),
             equivalence: Optional[str] = Query(None, pattern="^(full|partial|zero)$"),
             domain: Optional[str] = Query(None, max_length=20), culture: Optional[bool] = Query(None)):
    """Ingliz–o'zbek kollokatsiyalar banki (tasnif, ekvivalentlik, tarjima protsedurasi, lingvomadaniy izoh)."""
    items: List[Dict[str, Any]] = list(ct.collocation_bank())
    if bbi:
        items = [i for i in items if i.get("bbi") == bbi.upper()]
    if equivalence:
        items = [i for i in items if i.get("equivalence") == equivalence]
    if domain:
        items = [i for i in items if i.get("domain") == domain]
    if culture is not None:
        items = [i for i in items if bool(i.get("culture")) == culture]
    if q:
        ql = ct._norm_apos(q).lower()
        items = [i for i in items if ql in i["en"].lower() or ql in i["uz"].lower() or ql in (i.get("note") or "").lower()]
    all_items = ct.collocation_bank()
    return {"items": items, "total": len(items),
            "facets": {"bbi": sorted({i["bbi"] for i in all_items}), "domain": sorted({i["domain"] for i in all_items}),
                       "equivalence": sorted({i["equivalence"] for i in all_items}), "lf": sorted({i["lf"] for i in all_items})}}


@router.get("/sample")
def get_sample():
    """Namuna parallel matn (10 gap, qatorma-qator tekislangan)."""
    return {"source_text": ct.SAMPLE_EN, "target_text": ct.SAMPLE_UZ, "note": "Qatorlar soni teng bo'lsa gaplar 1:1 tekislanadi; aks holda Gale–Church algoritmi qo'llanadi."}


@router.post("/tag")
def tag(req: TagRequest, request: Request, fmt: str = Query("json", pattern="^(json|conllu)$")):
    """Bir tilli matnni teglash: lemma/o'zak, UPOS, PTB/XPOS, UD belgilari, affiks zanjiri (o'zbek), USAS maydoni."""
    _guard(request)
    res = ct.tag_text(req.text, req.lang)
    if fmt == "conllu":
        return PlainTextResponse(ct.to_conllu(res["sentences"], res["lang"]), media_type="text/plain; charset=utf-8")
    return res


@router.post("/analyze")
def analyze(req: AnalyzeRequest, request: Request,
            fmt: str = Query("json", pattern="^(json|tsv_en|tsv_uz|tsv_pairs|conllu_en|conllu_uz)$")):
    """Parallel matn to'liq tahlili: ikki til teglash, kollokatsiyalar (BBI, LF, USAS, MI/t/LL/logDice),
    gaplarni tekislash, kollokatsiya juftliklari va ekvivalentlik tipi, dissertatsiya 3-bobi uchun taqsimot jadvallari."""
    _guard(request)
    try:
        res = ct.analyze_parallel(req.source_text, req.target_text, min_freq=req.min_freq, span=req.span)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Tahlil bajarilmadi: {e}")
    if fmt == "json":
        return res
    if fmt == "tsv_en":
        body = ct.collocations_tsv(res["source"]["collocations"], "en")
    elif fmt == "tsv_uz":
        body = ct.collocations_tsv(res["target"]["collocations"], "uz")
    elif fmt == "tsv_pairs":
        body = ct.pairs_tsv(res["alignment"]["collocation_pairs"])
    elif fmt == "conllu_en":
        body = ct.to_conllu(res["source"]["sentences"], "en")
    else:
        body = ct.to_conllu(res["target"]["sentences"], "uz")
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")
