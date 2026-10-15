"""
Jonli tadqiqot jadvallari: platformadagi haqiqiy baholash ma'lumotlaridan (assessments jadvali)
dissertatsiya 4-bobi jadvallarini (4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10) hisoblaydi.

Manba:
  - users (role=student) + groups.experiment_arm (experimental / control) + institutions;
  - assessments: assessment_type (pre / mid / post), skill, score, max_score.
    skill qiymatlari: listening, reading, speaking, writing (kommunikativ, 0–100),
                      meta_planning, meta_monitoring, meta_evaluation, meta_regulation (1–5 shkala),
                      anxiety (0–100, FLCAS), motivation (0–100).
Jadvallar sxemasi dissertation_export.RESEARCH_DATA bilan bir xil — eksport bir xil generator bilan ishlaydi.
"""
from collections import defaultdict
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.entities import User, Group, Institution, Assessment
from app.services import statistics as st

COMM_SKILLS = ["listening", "reading", "speaking", "writing"]
META_SKILLS = [
    ("meta_planning", "O'quv faoliyatini rejalashtirish (Planning)"),
    ("meta_monitoring", "Jarayonni nazorat qilish (Monitoring)"),
    ("meta_evaluation", "Natijani baholash (Evaluation)"),
    ("meta_regulation", "Refleksiya va o'zini boshqarish (Self-regulation)"),
]
SKILL_NAMES = {
    "listening": "Tinglab tushunish (Listening)",
    "reading": "O'qish (Reading)",
    "speaking": "Og'zaki nutq (Speaking)",
    "writing": "Yozma nutq (Writing)",
}
LEVEL_SCALE = {"title": "4.3-jadval. Talabalar natijasini baholash mezonlari va shkalasi", "rows": [
    {"level": "Yuqori", "range": "86–100 ball", "communicative": "Vazifani mustaqil va xatosiz bajaradi, fikrini asoslaydi", "metacognitive": "Faoliyatini mustaqil rejalashtiradi va tuzatadi"},
    {"level": "O'rta", "range": "71–85 ball", "communicative": "Vazifani bajaradi, ayrim xatolarga yo'l qo'yadi", "metacognitive": "Yo'naltirish bilan rejalashtiradi va baholaydi"},
    {"level": "Quyi", "range": "55–70 ball", "communicative": "Vazifani qisman bajaradi, yordamga muhtoj", "metacognitive": "Faoliyatini nazorat qilishda qiynaladi"},
    {"level": "Boshlang'ich", "range": "0–54 ball", "communicative": "Vazifani mustaqil bajara olmaydi", "metacognitive": "O'z natijasini baholay olmaydi"},
]}


def _load(db: Session):
    insts = {i.id: i for i in db.query(Institution).all()}
    groups = {g.id: g for g in db.query(Group).all()}
    students = [u for u in db.query(User).filter(User.role == "student").all()
                if u.group_id in groups and (groups[u.group_id].experiment_arm in ("experimental", "control"))]
    sid_set = {s.id for s in students}
    rows = db.query(Assessment).filter(Assessment.student_id.in_(sid_set)).all() if sid_set else []
    # eng oxirgi baho (bir talaba, bir tur, bir ko'nikma) — 0–100 ga normallashtirilgan ball
    latest: Dict[tuple, Assessment] = {}
    for a in rows:
        k = (a.student_id, a.assessment_type, a.skill)
        if k not in latest or (a.administered_at and latest[k].administered_at and a.administered_at > latest[k].administered_at):
            latest[k] = a
    scores: Dict[tuple, float] = {}
    for (sid, atype, skill), a in latest.items():
        mx = a.max_score or 100
        if skill.startswith("meta_"):
            scores[(sid, atype, skill)] = float(a.score) * (5.0 / mx) if mx != 5 else float(a.score)
        else:
            scores[(sid, atype, skill)] = float(a.score) * (100.0 / mx)
    return insts, groups, students, scores


def _overall(scores, sid, atype) -> Optional[float]:
    if (sid, atype, "overall") in scores:
        return scores[(sid, atype, "overall")]
    vals = [scores[(sid, atype, s)] for s in COMM_SKILLS if (sid, atype, s) in scores]
    return st.mean(vals) if vals else None


def _arm(groups, u) -> str:
    return groups[u.group_id].experiment_arm


def _inst_name(insts, u) -> str:
    i = insts.get(u.institution_id)
    return i.name if i else "Boshqa OTM"


def _inst_code(insts, u) -> str:
    i = insts.get(u.institution_id)
    return f"{i.direction_code} – yo'nalish" if i and i.direction_code else ""


def build_live_tables(db: Session) -> Dict[str, Any]:
    insts, groups, students, scores = _load(db)
    by_inst: Dict[str, List[User]] = defaultdict(list)
    for s in students:
        by_inst[_inst_name(insts, s)].append(s)
    inst_order = sorted(by_inst.keys())

    def arm_students(lst, arm):
        return [s for s in lst if _arm(groups, s) == arm]

    # ---- 4.2 ----
    t42_rows, exp_tot, ctrl_tot = [], 0, 0
    for name in inst_order:
        lst = by_inst[name]
        e, c = len(arm_students(lst, "experimental")), len(arm_students(lst, "control"))
        exp_tot += e; ctrl_tot += c
        t42_rows.append({"institution": name, "specialty": _inst_code(insts, lst[0]) if lst else "", "experimental": e, "control": c, "total": e + c})
    table_4_2 = {"title": "4.2-jadval. Tajriba-sinov ishlariga jalb etilgan talabalar soni", "rows": t42_rows,
                 "summary": {"experimental_total": exp_tot, "control_total": ctrl_tot, "grand_total": exp_tot + ctrl_tot}}

    # ---- 4.4: pre-test darajalar taqsimoti (Yuqori / O'rta / Quyi+Boshlang'ich) ----
    def bands(lst, atype="pre"):
        hi = mid = low = 0
        for s in lst:
            o = _overall(scores, s.id, atype)
            if o is None:
                continue
            b = st.level_band(o)
            if b == "Yuqori": hi += 1
            elif b == "O'rta": mid += 1
            else: low += 1
        return hi, mid, low

    t44_rows = []
    tot_e = [0, 0, 0]; tot_c = [0, 0, 0]
    for name in inst_order:
        lst = by_inst[name]
        e = bands(arm_students(lst, "experimental")); c = bands(arm_students(lst, "control"))
        for i in range(3):
            tot_e[i] += e[i]; tot_c[i] += c[i]
        chi = st.chi_square_2xk(e, c)
        t44_rows.append({"institution": name, "exp_high": e[0], "exp_mid": e[1], "exp_low": e[2], "exp_total": sum(e),
                         "ctrl_high": c[0], "ctrl_mid": c[1], "ctrl_low": c[2], "ctrl_total": sum(c),
                         "chi2": chi["chi2"], "df": chi["df"], "p_value": round(chi["p"], 3),
                         "conclusion": "Guruhlar statistik jihatdan teng (p > 0.05)" if chi["p"] > 0.05 else "Guruhlar o'rtasida boshlang'ich farq bor (p ≤ 0.05)"})
    chi_all = st.chi_square_2xk(tot_e, tot_c)
    table_4_4 = {"title": "4.4-jadval. Tajriba boshida guruhlarning CEFR darajalari bo'yicha tenglik tekshiruvi (Pearson Chi-Square)",
                 "rows": t44_rows,
                 "overall": {"exp_high": tot_e[0], "exp_mid": tot_e[1], "exp_low": tot_e[2], "exp_total": sum(tot_e),
                             "ctrl_high": tot_c[0], "ctrl_mid": tot_c[1], "ctrl_low": tot_c[2], "ctrl_total": sum(tot_c),
                             "chi2": chi_all["chi2"], "df": chi_all["df"], "p_value": round(chi_all["p"], 3),
                             "conclusion": "Umumiy tanlanmada guruhlar tengligi tasdiqlandi" if chi_all["p"] > 0.05 else "Umumiy tanlanmada boshlang'ich farq mavjud"}}

    # ---- 4.5: guruh ichidagi o'zgarish (pre -> post, bog'langan t) ----
    def paired(lst, skill=None):
        pre, post = [], []
        for s in lst:
            a = _overall(scores, s.id, "pre") if skill is None else scores.get((s.id, "pre", skill))
            b = _overall(scores, s.id, "post") if skill is None else scores.get((s.id, "post", skill))
            if a is not None and b is not None:
                pre.append(a); post.append(b)
        return pre, post

    t45_rows = []
    all_e_pre, all_e_post, all_c_pre, all_c_post = [], [], [], []
    for name in inst_order:
        lst = by_inst[name]
        ep, eo = paired(arm_students(lst, "experimental")); cp, co = paired(arm_students(lst, "control"))
        all_e_pre += ep; all_e_post += eo; all_c_pre += cp; all_c_post += co
        te, tc = st.paired_t_test(ep, eo), st.paired_t_test(cp, co)
        t45_rows.append({"institution": name,
                         "exp_pre": round(st.mean(ep), 1), "exp_post": round(st.mean(eo), 1), "exp_growth": st.growth_percent(st.mean(ep), st.mean(eo)), "exp_t": te["t"], "exp_n": te["n"],
                         "ctrl_pre": round(st.mean(cp), 1), "ctrl_post": round(st.mean(co), 1), "ctrl_growth": st.growth_percent(st.mean(cp), st.mean(co)), "ctrl_t": tc["t"], "ctrl_n": tc["n"]})
    te_all, tc_all = st.paired_t_test(all_e_pre, all_e_post), st.paired_t_test(all_c_pre, all_c_post)
    table_4_5 = {"title": "4.5-jadval. Tajriba boshida va yakunida har bir guruh ichidagi bilim o'zgarishi dinamikasi", "rows": t45_rows,
                 "overall": {"exp_pre": round(st.mean(all_e_pre), 1), "exp_post": round(st.mean(all_e_post), 1), "exp_growth": st.growth_percent(st.mean(all_e_pre), st.mean(all_e_post)), "exp_t": te_all["t"], "p_value": st.fmt_p(te_all["p"]),
                             "ctrl_pre": round(st.mean(all_c_pre), 1), "ctrl_post": round(st.mean(all_c_post), 1), "ctrl_growth": st.growth_percent(st.mean(all_c_pre), st.mean(all_c_post)), "ctrl_t": tc_all["t"], "ctrl_p": st.fmt_p(tc_all["p"])}}

    # ---- 4.6: to'rt ko'nikma ----
    exp_all = [s for s in students if _arm(groups, s) == "experimental"]
    ctrl_all = [s for s in students if _arm(groups, s) == "control"]
    skills_out = []
    for sk in COMM_SKILLS:
        ep, eo = paired(exp_all, sk); cp, co = paired(ctrl_all, sk)
        e_post_all = [scores[(s.id, "post", sk)] for s in exp_all if (s.id, "post", sk) in scores]
        c_post_all = [scores[(s.id, "post", sk)] for s in ctrl_all if (s.id, "post", sk) in scores]
        tt = st.independent_t_test(e_post_all, c_post_all)
        skills_out.append({"skill_name": SKILL_NAMES[sk],
                           "exp_pre": round(st.mean(ep), 1), "exp_post": round(st.mean(eo), 1), "exp_growth": st.growth_percent(st.mean(ep), st.mean(eo)),
                           "ctrl_pre": round(st.mean(cp), 1), "ctrl_post": round(st.mean(co), 1), "ctrl_growth": st.growth_percent(st.mean(cp), st.mean(co)),
                           "t_stat": tt["t"], "p_val": st.fmt_p(tt["p"]), "cohens_d": st.cohens_d(e_post_all, c_post_all)})
    table_4_6 = {"title": "4.6-jadval. Tajriba yakunida to'rt nutqiy faoliyat turi bo'yicha qiyosiy ko'rsatkichlar", "skills": skills_out}

    # ---- 4.7: metakognitiv komponentlar (1–5) + tashvish ----
    comps, ds = [], []
    for key, label in META_SKILLS:
        ep, eo = paired(exp_all, key); cp, co = paired(ctrl_all, key)
        e_post_all = [scores[(s.id, "post", key)] for s in exp_all if (s.id, "post", key) in scores]
        c_post_all = [scores[(s.id, "post", key)] for s in ctrl_all if (s.id, "post", key) in scores]
        d = st.cohens_d(e_post_all, c_post_all)
        if e_post_all and c_post_all:
            ds.append(d)
        comps.append({"component": label,
                      "exp_pre": round(st.mean(ep), 2), "exp_post": round(st.mean(eo), 2), "exp_growth": st.growth_percent(st.mean(ep), st.mean(eo)),
                      "ctrl_pre": round(st.mean(cp), 2), "ctrl_post": round(st.mean(co), 2), "ctrl_growth": st.growth_percent(st.mean(cp), st.mean(co)),
                      "cohens_d": d, "effect_level": st.effect_label(d)})
    # tashvish (pasayishi kutiladi)
    ep, eo = paired(exp_all, "anxiety"); cp, co = paired(ctrl_all, "anxiety")
    anxiety_row = {"component": "Chet tili tashvishi darajasi (FLCAS, 0–100; pasayishi ijobiy)",
                   "exp_pre": round(st.mean(ep), 1), "exp_post": round(st.mean(eo), 1), "exp_growth": st.growth_percent(st.mean(ep), st.mean(eo)),
                   "ctrl_pre": round(st.mean(cp), 1), "ctrl_post": round(st.mean(co), 1), "ctrl_growth": st.growth_percent(st.mean(cp), st.mean(co)),
                   "cohens_d": st.cohens_d([scores[(s.id, "post", "anxiety")] for s in ctrl_all if (s.id, "post", "anxiety") in scores],
                                           [scores[(s.id, "post", "anxiety")] for s in exp_all if (s.id, "post", "anxiety") in scores]),
                   "effect_level": ""}
    anxiety_row["effect_level"] = st.effect_label(anxiety_row["cohens_d"])
    table_4_7 = {"title": "4.7-jadval. Talabalarning metakognitiv kompetensiyalari o'sishi va effekt hajmi (Cohen's d)",
                 "components": comps + [anxiety_row], "average_d": round(st.mean(ds), 2) if ds else 0.0}

    # ---- 4.8: Bespalko ----
    t48_rows, ek_all, ck_all = [], [], []
    for name in inst_order:
        lst = by_inst[name]
        e_post = [_overall(scores, s.id, "post") for s in arm_students(lst, "experimental")]
        c_post = [_overall(scores, s.id, "post") for s in arm_students(lst, "control")]
        e_post = [x for x in e_post if x is not None]; c_post = [x for x in c_post if x is not None]
        ek, ck = st.bespalko_k(e_post), st.bespalko_k(c_post)
        ek_all += e_post; ck_all += c_post
        ratio = round(ek / ck, 2) if ck > 0 else 0.0
        t48_rows.append({"institution": name, "exp_k": ek, "ctrl_k": ck, "ratio_k": ratio, "diff_percent": f"{(ratio - 1) * 100:+.1f}%" if ck > 0 else "—"})
    ek, ck = st.bespalko_k(ek_all), st.bespalko_k(ck_all)
    ratio = round(ek / ck, 2) if ck > 0 else 0.0
    table_4_8 = {"title": "4.8-jadval. V.P. Bespalko metodikasi bo'yicha o'zlashtirish va samaradorlik koeffitsiyenti", "rows": t48_rows,
                 "overall": {"exp_k": ek, "ctrl_k": ck, "ratio_k": ratio, "diff_percent": f"{(ratio - 1) * 100:+.1f}%" if ck > 0 else "—"}}

    # ---- 4.9: umumiy xulosa ----
    e_post_overall = [x for x in (_overall(scores, s.id, "post") for s in exp_all) if x is not None]
    c_post_overall = [x for x in (_overall(scores, s.id, "post") for s in ctrl_all) if x is not None]
    comm_t = st.independent_t_test(e_post_overall, c_post_overall)
    comm_d = st.cohens_d(e_post_overall, c_post_overall)

    def meta_overall(lst, atype):
        out = []
        for s in lst:
            vals = [scores[(s.id, atype, k)] for k, _ in META_SKILLS if (s.id, atype, k) in scores]
            if vals:
                out.append(st.mean(vals))
        return out
    e_meta_post, c_meta_post = meta_overall(exp_all, "post"), meta_overall(ctrl_all, "post")
    meta_t = st.independent_t_test(e_meta_post, c_meta_post)
    meta_d = st.cohens_d(e_meta_post, c_meta_post)
    e_meta_pre = meta_overall(exp_all, "pre")
    meta_growth = st.growth_percent(st.mean(e_meta_pre), st.mean(e_meta_post)) if e_meta_pre and e_meta_post else "—"
    table_4_9 = {"title": "4.9-jadval. Tajriba-sinov ishlarining matematik-statistik tahlili umumiy yakuniy xulosalari", "indicators": [
        {"group": "Boshlang'ich tenglik tekshiruvi (Pearson Chi-Square)", "calculated": f"χ² = {chi_all['chi2']}",
         "table_crit": f"χ²_crit = {st.CHI2_CRIT_05.get(chi_all['df'], 5.99)} (df={chi_all['df']}, α=0.05)",
         "effect_size": f"p {st.fmt_p(chi_all['p'])}", "conclusion": "Guruhlar tengligi isbotlandi" if chi_all["p"] > 0.05 else "Boshlang'ich farq mavjud — natijani ehtiyotkor talqin qiling"},
        {"group": "Kommunikativ kompetensiya (Student t-test, post, tajriba vs nazorat)", "calculated": f"t = {comm_t['t']}",
         "table_crit": f"t_crit = {st.t_crit_05(comm_t['df'])} (df={comm_t['df']}, α=0.05)",
         "effect_size": f"d = {comm_d} ({st.effect_label(comm_d)})", "conclusion": ("Nol gipoteza rad etildi, farq statistik ishonchli (p " + st.fmt_p(comm_t['p']) + ")") if comm_t["p"] < 0.05 else "Farq statistik ishonchli emas (p " + st.fmt_p(comm_t["p"]) + ")"},
        {"group": "Metakognitiv kompetensiya (Flavell/Pintrich shkalasi)", "calculated": f"t = {meta_t['t']}",
         "table_crit": f"t_crit = {st.t_crit_05(meta_t['df'])} (df={meta_t['df']}, α=0.05)",
         "effect_size": f"d = {meta_d} ({st.effect_label(meta_d)})", "conclusion": f"Tajriba guruhida metakognitiv ko'rsatkich {meta_growth} o'sdi (p {st.fmt_p(meta_t['p'])})"},
        {"group": "O'zlashtirish samaradorligi (Bespalko K_s)", "calculated": f"K_s = {ratio}", "table_crit": "K_s > 1.0 (Bespalko mezoni)",
         "effect_size": table_4_8["overall"]["diff_percent"], "conclusion": "Takomillashtirilgan metodika an'anaviy ta'limdan samaraliroq" if ratio > 1.0 else "Samaradorlik farqi aniqlanmadi"},
    ]}

    # ---- 4.10: nazariy kutilma va natija ----
    def sk_growth(i):
        return skills_out[i]["exp_growth"] if skills_out else "—"
    anx_change = anxiety_row["exp_growth"]
    table_4_10 = {"title": "4.10-jadval. Nazariy kutilma va tajriba natijasining muvofiqligi", "rows": [
        {"indicator": "Og'zaki nutq", "expectation": "Dialog tizimlari hisobiga sezilarli o'sish", "result": sk_growth(2), "match": "Muvofiq" if _pos(sk_growth(2)) else "Tekshirilmoqda"},
        {"indicator": "Yozma nutq", "expectation": "Izohli qaytar aloqa hisobiga o'rtacha o'sish", "result": sk_growth(3), "match": "Muvofiq" if _pos(sk_growth(3)) else "Tekshirilmoqda"},
        {"indicator": "O'qish", "expectation": "Materialni darajaga moslashtirish hisobiga o'sish", "result": sk_growth(1), "match": "Muvofiq" if _pos(sk_growth(1)) else "Tekshirilmoqda"},
        {"indicator": "Tinglab tushunish", "expectation": "Sur'at va variantlarni tabaqalashtirish hisobiga o'sish", "result": sk_growth(0), "match": "Muvofiq" if _pos(sk_growth(0)) else "Tekshirilmoqda"},
        {"indicator": "Metakognitiv ko'rsatkich", "expectation": "Refleksiv bosqich hisobiga yuqori o'sish", "result": meta_growth, "match": "Muvofiq" if _pos(meta_growth) else "Tekshirilmoqda"},
        {"indicator": "Tashvish darajasi", "expectation": "Mashq muhitidagi xavfsizlik hisobiga pasayish", "result": anx_change, "match": "Muvofiq" if (anx_change not in ("—",) and anx_change.startswith("-")) else "Tekshirilmoqda"},
    ]}

    # ---- to'liqlik ----
    with_pre = sum(1 for s in students if _overall(scores, s.id, "pre") is not None)
    with_post = sum(1 for s in students if _overall(scores, s.id, "post") is not None)
    with_both = sum(1 for s in students if _overall(scores, s.id, "pre") is not None and _overall(scores, s.id, "post") is not None)
    with_meta = sum(1 for s in students if any((s.id, "pre", k) in scores for k, _ in META_SKILLS))

    return {
        "data_source": "live_platform",
        "data_source_note": "Jadvallar platformadagi haqiqiy baholash ma'lumotlaridan (assessments) real vaqtda hisoblandi.",
        "completeness": {"students_in_arms": len(students), "with_pre": with_pre, "with_post": with_post, "with_both": with_both,
                         "with_metacognitive": with_meta, "institutions": len(inst_order),
                         "ready": with_both >= 10 and len(exp_all) >= 5 and len(ctrl_all) >= 5},
        "level_scale": LEVEL_SCALE,
        "table_4_2": table_4_2, "table_4_4": table_4_4, "table_4_5": table_4_5, "table_4_6": table_4_6,
        "table_4_7": table_4_7, "table_4_8": table_4_8, "table_4_9": table_4_9, "table_4_10": table_4_10,
    }


def _pos(g: str) -> bool:
    return isinstance(g, str) and g.startswith("+") and g not in ("+0.0%",)
