"""
Pedagogik tajriba-sinov uchun matematik-statistik usullar (dissertatsiya 4.1–4.2):
deskriptiv statistika, Styudent t-mezoni (bog'langan va mustaqil tanlanmalar), Pirson xi-kvadrat,
Cohen effekt hajmi, Bespalko o'zlashtirish (K) va samaradorlik (K_s) koeffitsiyentlari.

Tashqi kutubxonasiz (numpy/scipy yo'q) — 1 GB RAM li serverda ham ishlaydi.
"""
import math
from typing import Dict, List, Sequence, Tuple, Optional, Any


# ---------------- Deskriptiv ----------------

def mean(xs: Sequence[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def variance(xs: Sequence[float], ddof: int = 1) -> float:
    xs = list(xs)
    n = len(xs)
    if n - ddof <= 0:
        return 0.0
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (n - ddof)


def std(xs: Sequence[float], ddof: int = 1) -> float:
    return math.sqrt(variance(xs, ddof))


def describe(xs: Sequence[float]) -> Dict[str, float]:
    xs = list(xs)
    if not xs:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}
    s = sorted(xs)
    n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return {"n": n, "mean": round(mean(s), 2), "sd": round(std(s), 2), "min": s[0], "max": s[-1], "median": round(med, 2)}


# ---------------- Taqsimotlar (p-qiymat uchun) ----------------

def _ln_gamma(x: float) -> float:
    return math.lgamma(x)


def _betacf(a: float, b: float, x: float) -> float:
    """Numerical Recipes: to'liqsiz beta funksiyasi uchun davomli kasr."""
    MAXIT, EPS, FPMIN = 300, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        dl = d * c
        h *= dl
        if abs(dl - 1.0) < EPS:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regulyarlashtirilgan to'liqsiz beta funksiyasi I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(_ln_gamma(a + b) - _ln_gamma(a) - _ln_gamma(b) + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_two_tailed_p(t: float, df: float) -> float:
    """Styudent taqsimoti bo'yicha ikki tomonlama p-qiymat."""
    if df <= 0:
        return 1.0
    x = df / (df + t * t)
    return max(0.0, min(1.0, _betainc(df / 2.0, 0.5, x)))


def _gammainc_upper_q(s: float, x: float) -> float:
    """Regulyarlashtirilgan yuqori to'liqsiz gamma Q(s, x) (xi-kvadrat p-qiymati uchun)."""
    if x <= 0:
        return 1.0
    if x < s + 1.0:
        # qator
        ap, summ, delta = s, 1.0 / s, 1.0 / s
        for _ in range(500):
            ap += 1.0
            delta *= x / ap
            summ += delta
            if abs(delta) < abs(summ) * 1e-14:
                break
        p = summ * math.exp(-x + s * math.log(x) - _ln_gamma(s))
        return max(0.0, 1.0 - p)
    # davomli kasr
    FPMIN = 1e-300
    b = x + 1.0 - s
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        dl = d * c
        h *= dl
        if abs(dl - 1.0) < 1e-14:
            break
    return max(0.0, min(1.0, math.exp(-x + s * math.log(x) - _ln_gamma(s)) * h))


def chi2_p(chi2: float, df: int) -> float:
    if df <= 0:
        return 1.0
    return _gammainc_upper_q(df / 2.0, chi2 / 2.0)


T_CRIT_05 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
             15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021, 60: 2.000, 80: 1.990, 100: 1.984, 120: 1.980}
CHI2_CRIT_05 = {1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488, 5: 11.070, 6: 12.592}


def t_crit_05(df: int) -> float:
    if df <= 0:
        return float("nan")
    keys = sorted(T_CRIT_05)
    for k in keys:
        if df <= k:
            return T_CRIT_05[k]
    return 1.96


# ---------------- Mezonlar ----------------

def paired_t_test(pre: Sequence[float], post: Sequence[float]) -> Dict[str, float]:
    """Bog'langan tanlanmalar uchun t-mezon (guruh ichidagi o'zgarish)."""
    pairs = [(a, b) for a, b in zip(pre, post)]
    n = len(pairs)
    if n < 2:
        return {"n": n, "t": 0.0, "df": max(0, n - 1), "p": 1.0, "mean_diff": 0.0}
    diffs = [b - a for a, b in pairs]
    md = mean(diffs)
    sd = std(diffs)
    t = md / (sd / math.sqrt(n)) if sd > 0 else (float("inf") if md != 0 else 0.0)
    if math.isinf(t):
        t = 99.0
    return {"n": n, "t": round(t, 2), "df": n - 1, "p": t_two_tailed_p(abs(t), n - 1), "mean_diff": round(md, 2)}


def independent_t_test(a: Sequence[float], b: Sequence[float]) -> Dict[str, float]:
    """Mustaqil tanlanmalar uchun t-mezon (guruhlararo farq, teng dispersiya)."""
    a, b = list(a), list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return {"t": 0.0, "df": max(0, na + nb - 2), "p": 1.0}
    va, vb = variance(a), variance(b)
    sp2 = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    se = math.sqrt(sp2 * (1.0 / na + 1.0 / nb)) if sp2 > 0 else 0.0
    t = (mean(a) - mean(b)) / se if se > 0 else 0.0
    df = na + nb - 2
    return {"t": round(t, 2), "df": df, "p": t_two_tailed_p(abs(t), df)}


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    a, b = list(a), list(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    sp = math.sqrt(((na - 1) * variance(a) + (nb - 1) * variance(b)) / (na + nb - 2))
    return round((mean(a) - mean(b)) / sp, 2) if sp > 0 else 0.0


def effect_label(d: float) -> str:
    ad = abs(d)
    if ad >= 0.8:
        return "Katta effekt (Large > 0.8)"
    if ad >= 0.5:
        return "O'rta effekt (Medium 0.5–0.8)"
    if ad >= 0.2:
        return "Kichik effekt (Small 0.2–0.5)"
    return "Ahamiyatsiz (< 0.2)"


def chi_square_2xk(row_a: Sequence[int], row_b: Sequence[int]) -> Dict[str, float]:
    """2 × k kontingent jadvali uchun Pirson xi-kvadrat (masalan, tajriba/nazorat × daraja)."""
    k = len(row_a)
    if k != len(row_b) or k < 2:
        return {"chi2": 0.0, "df": max(0, k - 1), "p": 1.0}
    total = sum(row_a) + sum(row_b)
    if total == 0:
        return {"chi2": 0.0, "df": k - 1, "p": 1.0}
    ra, rb = sum(row_a), sum(row_b)
    chi2 = 0.0
    for j in range(k):
        col = row_a[j] + row_b[j]
        for obs, rt in ((row_a[j], ra), (row_b[j], rb)):
            exp = rt * col / total
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp
    df = k - 1
    return {"chi2": round(chi2, 2), "df": df, "p": chi2_p(chi2, df)}


def bespalko_k(scores: Sequence[float], max_score: float = 100.0) -> float:
    """O'zlashtirish koeffitsiyenti K = o'rtacha to'g'ri bajarilgan / maksimal; K >= 0.7 — o'zlashtirilgan."""
    scores = list(scores)
    if not scores or max_score <= 0:
        return 0.0
    return round(mean(scores) / max_score, 2)


def level_band(score: float, scale: Tuple[float, float, float] = (86, 71, 55)) -> str:
    """4.3-jadval: ball oralig'iga ko'ra daraja (Yuqori / O'rta / Quyi / Boshlang'ich)."""
    hi, mid, low = scale
    if score >= hi:
        return "Yuqori"
    if score >= mid:
        return "O'rta"
    if score >= low:
        return "Quyi"
    return "Boshlang'ich"


def growth_percent(pre: float, post: float) -> str:
    if pre <= 0:
        return "—"
    return f"{(post - pre) / pre * 100:+.1f}%"


# ---------------- Ishonchlilik (4.1: Cronbach α, baholovchilar mosligi) ----------------

def cronbach_alpha(matrix: List[List[float]]) -> Dict[str, float]:
    """
    Ichki izchillik (Cronbach, 1951). matrix: har qator — bitta respondent, har ustun — bitta band.
    α = k/(k-1) * (1 - Σ var_item / var_total). Talqin: ≥0.9 a'lo, ≥0.8 yaxshi, ≥0.7 qoniqarli, <0.7 past.
    """
    rows = [r for r in matrix if r and all(x is not None for x in r)]
    if len(rows) < 2:
        return {"alpha": None, "n_respondents": len(rows), "n_items": len(rows[0]) if rows else 0, "label": "Ma'lumot yetarli emas"}
    k = len(rows[0])
    rows = [r for r in rows if len(r) == k]
    if k < 2 or len(rows) < 2:
        return {"alpha": None, "n_respondents": len(rows), "n_items": k, "label": "Kamida 2 band va 2 respondent kerak"}
    item_vars = [variance([r[j] for r in rows]) for j in range(k)]
    totals = [sum(r) for r in rows]
    vt = variance(totals)
    if vt == 0:
        return {"alpha": None, "n_respondents": len(rows), "n_items": k, "label": "Dispersiya nol (barcha javoblar bir xil)"}
    alpha = (k / (k - 1)) * (1 - sum(item_vars) / vt)
    alpha = round(alpha, 3)
    label = "A'lo (≥0.9)" if alpha >= 0.9 else "Yaxshi (≥0.8)" if alpha >= 0.8 else "Qoniqarli (≥0.7)" if alpha >= 0.7 else "Past (<0.7) — bandlarni qayta ko'rib chiqing"
    return {"alpha": alpha, "n_respondents": len(rows), "n_items": k, "label": label}


def pearson_r(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    a, b = list(a), list(b)
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[:n], b[:n]
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return round(num / den, 3) if den > 0 else None


def weighted_kappa(a: Sequence[int], b: Sequence[int], categories: int = 5) -> Optional[float]:
    """Kvadratik vaznli Cohen kappa (tartibli 1–k shkalalar, ikki baholovchi)."""
    pairs = [(int(x), int(y)) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n < 2:
        return None
    k = categories
    obs = [[0.0] * k for _ in range(k)]
    for x, y in pairs:
        if 1 <= x <= k and 1 <= y <= k:
            obs[x - 1][y - 1] += 1
    ra = [sum(obs[i]) for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    so = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k)) / n
    se = sum(w[i][j] * ra[i] * rb[j] / n for i in range(k) for j in range(k)) / n
    if se == 0:
        return None
    return round(1 - so / se, 3)


def rater_agreement(a: Sequence[int], b: Sequence[int]) -> Dict[str, Any]:
    """Ikki mustaqil baholovchi (tizim rubrikasi va o'qituvchi) mosligi: aniq moslik %, ±1 moslik %, Pearson r, vaznli kappa."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return {"n": 0, "exact": None, "adjacent": None, "r": None, "kappa": None, "label": "Ma'lumot yo'q"}
    exact = sum(1 for x, y in pairs if x == y) / n
    adj = sum(1 for x, y in pairs if abs(x - y) <= 1) / n
    kap = weighted_kappa([p[0] for p in pairs], [p[1] for p in pairs])
    lbl = "—"
    if kap is not None:
        lbl = "Juda yaxshi (κ≥0.8)" if kap >= 0.8 else "Yaxshi (κ≥0.6)" if kap >= 0.6 else "O'rtacha (κ≥0.4)" if kap >= 0.4 else "Zaif (κ<0.4)"
    return {"n": n, "exact": round(exact, 2), "adjacent": round(adj, 2), "r": pearson_r([p[0] for p in pairs], [p[1] for p in pairs]), "kappa": kap, "label": lbl}


def fmt_p(p: float) -> str:
    if p < 0.001:
        return "< 0.001"
    if p < 0.01:
        return "< 0.01"
    if p < 0.05:
        return "< 0.05"
    return f"= {p:.3f}"
