"""Parallel korpus: morfologik/semantik teglash, kollokatsiya ajratish, tekislash, ekvivalentlik, API."""
from fastapi.testclient import TestClient

from app.main import app
from app.services import corpus_tagger as ct

client = TestClient(app)


def _uz(word):
    return ct._uz_analyze_word(word, False)


def test_uzbek_nominal_morphology_ud_features():
    a = _uz("maktablarimizdan")
    assert a["stem"] == "maktab" and a["upos"] == "NOUN"
    assert a["feats"] == {"Case": "Abl", "Person[psor]": "1", "Number[psor]": "Plur", "Number": "Plur"}
    assert [s.split(":")[0] for s in a["sufs"]] == ["lar", "imiz", "dan"]
    b = _uz("matnlarining")
    assert b["stem"] == "matn" and b["feats"]["Case"] == "Gen" and b["feats"]["Person[psor]"] == "3" and b["feats"]["Number"] == "Plur"
    c = _uz("tarjimasi")
    assert c["stem"] == "tarjima" and c["feats"]["Person[psor]"] == "3"
    # fonotaktika: unlidan keyin -si, undoshdan keyin -i
    assert _uz("leksikografiyasida")["stem"] == "leksikografiya"
    assert _uz("shahardagi")["upos"] == "ADJ" and _uz("shahardagi")["stem"] == "shahar"


def test_uzbek_verbal_morphology():
    a = _uz("boradi")
    assert a["stem"] == "bor" and a["upos"] == "VERB" and a["feats"]["Tense"] == "Pres" and a["feats"]["Person"] == "3"
    b = _uz("chiqardik")
    assert b["stem"] == "chiqar" and b["feats"]["Tense"] == "Past" and b["feats"]["Person"] == "1" and b["feats"]["Number"] == "Plur"
    c = _uz("qilinadi")
    assert c["stem"] == "qil" and c["feats"]["Voice"] == "Pass"
    d = _uz("hisoblanadi")
    assert d["stem"] == "hisobla" and d["feats"]["Voice"] == "Pass"
    e = _uz("topshirgandan")
    assert e["stem"] == "topshir" and e["feats"]["VerbForm"] == "Part" and e["feats"]["Case"] == "Abl"
    f = _uz("ichayotganda")
    assert f["stem"] == "ich" and f["feats"]["Aspect"] == "Prog" and f["feats"]["Case"] == "Loc"
    g = _uz("saqlab")
    assert g["stem"] == "saqla" and g["feats"]["VerbForm"] == "Conv"
    h = _uz("uyg'otmoq")
    assert h["stem"] == "uyg'ot" and h["feats"]["VerbForm"] == "Vnoun"
    assert _uz("bormadi")["feats"]["Polarity"] == "Neg"
    assert _uz("kelsak")["feats"]["Mood"] == "Cnd"
    assert _uz("o'qimoqchiman")["feats"]["Mood"] == "Prp" and _uz("o'qimoqchiman")["feats"]["Person"] == "1"


def test_uzbek_derivation_and_unknown_stems():
    a = _uz("ahamiyatlilik")
    assert a["upos"] == "NOUN" and a["known"] is True
    # noma'lum o'zak: qo'shimcha zanjiri bo'yicha taxmin
    u = _uz("gipotezalarni")
    assert u["stem"] == "gipoteza" and u["feats"]["Case"] == "Acc"
    x = _uz("fleksiyalarning")
    assert x["stem"] == "fleksiya" and x["upos"] == "NOUN" and x["known"] is False


def test_uzbek_sentence_tagging_and_mwe():
    sents = ct.tag_uzbek("Tarjimon muhim qaror qabul qildi. Tadqiqotchi tadqiqot olib bordi.")
    assert len(sents) == 2
    t = {tok["form"]: tok for tok in sents[0]["tokens"]}
    assert t["Tarjimon"]["upos"] == "NOUN" and t["Tarjimon"]["usas"] == "Q3"
    assert t["qildi"]["mwe"] == "qabul qil" and t["qabul"]["mwe_part_of"] == "qabul qil"
    t2 = {tok["form"]: tok for tok in sents[1]["tokens"]}
    assert t2["bordi"]["mwe"] == "olib bor"
    conllu = ct.to_conllu(sents, "uz")
    assert "# sent_id = uz-1" in conllu and "Case=Nom|Number=Plur" not in conllu.split("\n")[2]
    assert "MWE=qabul_qil" in conllu


def test_english_tagging_ptb_and_features():
    sents = ct.tag_english("The researchers conducted research on parallel corpora. She drew a conclusion.")
    toks = {t["form"]: t for s in sents for t in s["tokens"]}
    assert toks["researchers"]["upos"] == "NOUN" and toks["researchers"]["xpos"] == "NNS" and toks["researchers"]["lemma"] == "researcher"
    assert toks["conducted"]["upos"] == "VERB" and toks["conducted"]["xpos"] == "VBD" and toks["conducted"]["lemma"] == "conduct"
    assert toks["research"]["upos"] == "NOUN" and toks["research"]["usas"] == "X2.4"
    assert toks["corpora"]["lemma"] == "corpus" and toks["corpora"]["feats"]["Number"] == "Plur"
    assert toks["drew"]["lemma"] == "draw" and toks["drew"]["feats"]["Tense"] == "Past"
    assert toks["The"]["upos"] == "DET" and toks["on"]["upos"] == "ADP"


def test_association_measures():
    m = ct._association(o11=2, r1=2, c1=2, n=100)
    assert m["logdice"] == 14.0 and m["mi"] > 5 and m["t_score"] > 1.3 and m["log_likelihood"] > 10
    weak = ct._association(o11=1, r1=50, c1=50, n=100)
    assert weak["mi"] < 0 and weak["logdice"] < 14


def test_collocation_extraction_en_uz_with_bank():
    en = ct.tag_english(ct.SAMPLE_EN)
    uz = ct.tag_uzbek(ct.SAMPLE_UZ)
    en_c = {c["collocation"]: c for c in ct.collocations_from_sentences(en, "en")}
    uz_c = {c["collocation"]: c for c in ct.collocations_from_sentences(uz, "uz")}
    assert en_c["strong tea"]["bbi"] == "L3" and en_c["strong tea"]["lf"] == "Magn" and en_c["strong tea"]["in_bank"]
    assert en_c["strong tea"]["equivalence"] == "partial" and en_c["strong tea"]["counterpart"] == "achchiq choy"
    assert en_c["make decision"]["lf"] == "Oper1" and en_c["make decision"]["bbi"] == "L1"
    assert en_c["bee buzz"]["bbi"] == "L4" and en_c["bee buzz"]["lf"] == "Func0"
    assert en_c["research on"]["bbi"] == "G1"
    assert uz_c["qaror qabul qil"]["structure"] == "NOUN+VERB" and uz_c["qaror qabul qil"]["lf"] == "Oper1"
    assert uz_c["tadqiqot olib bor"]["in_bank"]
    assert uz_c["achchiq choy"]["bbi"] == "L3" and uz_c["achchiq choy"]["usas"] == "F2"
    assert uz_c["ona til"]["structure_uz"] == "ot + ot (izofa)"
    assert "statistical measure" in en_c and all(k in en_c["strong tea"]["measures"] for k in ("mi", "t_score", "log_likelihood", "logdice"))


def test_parallel_analysis_alignment_and_equivalence():
    res = ct.analyze_parallel(ct.SAMPLE_EN, ct.SAMPLE_UZ)
    assert res["meta"]["sentence_pairs"] == 10 and res["meta"]["alignment_method"].startswith("1:1")
    pairs = {p["en"]: p for p in res["alignment"]["collocation_pairs"]}
    assert pairs["strong tea"]["uz"] == "achchiq choy" and pairs["strong tea"]["equivalence"] == "partial" and pairs["strong tea"]["confidence"] == "bank"
    assert pairs["mother tongue"]["equivalence"] == "full"
    assert pairs["heavy traffic"]["equivalence"] == "zero" and pairs["heavy traffic"]["procedure"] == "transposition"
    assert pairs["catch cold"]["equivalence"] == "zero" and pairs["catch cold"]["culture"] is True
    assert pairs["green tea"]["culture"] is True
    assert pairs["central problem"]["uz"] == "markaziy muammo" and pairs["central problem"]["confidence"] == "lexicon"
    assert pairs["research on"]["equivalence"] == "grammatical"
    s = res["summary"]
    assert s["by_equivalence"]["full"] >= 10 and s["by_equivalence"]["partial"] >= 8 and s["by_equivalence"]["zero"] >= 2
    assert len(s["culture_specific"]) >= 3
    assert res["target"]["stats"]["feature_distribution"]["Case"]["Nom"] > 0
    # Gale–Church: gaplar soni farq qilsa ham tekislanadi
    pairs2, method = ct.align_sentences(["A short one.", "The second sentence is considerably longer than the first one here."],
                                        ["Qisqa gap.", "Ikkinchi gap birinchisidan ancha uzun.", "Yana bir gap."])
    assert method.startswith("Gale") and len(pairs2) >= 2 and sum(len(p["uz"]) for p in pairs2) == 3


def test_exports():
    res = ct.analyze_parallel("Strong tea is popular.", "Achchiq choy mashhur.")
    tsv = ct.collocations_tsv(res["source"]["collocations"], "en")
    assert tsv.split("\n")[0].startswith("lang\tcollocation") and "strong tea" in tsv
    ptsv = ct.pairs_tsv(res["alignment"]["collocation_pairs"])
    assert "achchiq choy" in ptsv
    conllu = ct.to_conllu(res["source"]["sentences"], "en")
    assert "\tStrong\tstrong\tADJ\tJJ\tDegree=Pos\t" in conllu


def test_api_endpoints():
    r = client.get("/api/research/corpus/tagset")
    assert r.status_code == 200
    d = r.json()
    assert len(d["upos"]) == 17 and len(d["usas_fields"]) == 21 and len(d["bbi_types"]) == 16
    assert d["lexicon_sizes"]["en"] > 500 and d["lexicon_sizes"]["uz"] > 500 and d["lexicon_sizes"]["bank"] == 100
    assert len(d["references"]) >= 25

    r = client.get("/api/research/corpus/collocations", params={"equivalence": "zero"})
    assert r.status_code == 200 and r.json()["total"] >= 5 and all(i["equivalence"] == "zero" for i in r.json()["items"])
    r = client.get("/api/research/corpus/collocations", params={"q": "choy"})
    assert r.json()["total"] >= 3

    r = client.get("/api/research/corpus/sample")
    assert r.status_code == 200 and "source_text" in r.json()

    r = client.post("/api/research/corpus/tag", json={"text": "Kollokatsiyalarning tarjimasi o'rganildi.", "lang": "auto"})
    assert r.status_code == 200 and r.json()["lang"] == "uz"
    tok = r.json()["sentences"][0]["tokens"][0]
    assert tok["lemma"] == "kollokatsiya" and tok["feats"]["Case"] == "Gen"

    r = client.post("/api/research/corpus/tag?fmt=conllu", json={"text": "Collocations matter.", "lang": "en"})
    assert r.status_code == 200 and r.text.startswith("# sent_id = en-1")

    r = client.post("/api/research/corpus/analyze", json={"source_text": ct.SAMPLE_EN, "target_text": ct.SAMPLE_UZ})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["aligned_pairs"] >= 30 and body["source"]["stats"]["tokens"] > 100
    r = client.post("/api/research/corpus/analyze?fmt=tsv_pairs", json={"source_text": ct.SAMPLE_EN, "target_text": ct.SAMPLE_UZ})
    assert r.status_code == 200 and r.text.startswith("en\ten_structure")
    r = client.post("/api/research/corpus/analyze", json={"source_text": "", "target_text": "x"})
    assert r.status_code == 422
