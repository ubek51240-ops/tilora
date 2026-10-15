/**
 * TILORA — Talaba dinamikasi (refleksiya moduli, dissertatsiya 3.3)
 * GET /api/student/dynamics -> #dynamicsRoot
 *   KPI (mashg'ulotlar, seriya, metakognitiv aniqlik, yordam so'rovlari), ballar grafigi (inline SVG),
 *   vaqt jadvali, ko'nikma kesimi, ko'mak yo'li, pre/post baholar, profil tarixi.
 * Kutubxonasiz; barcha dinamik matn escapeHtml() orqali.
 */
(function () {
  "use strict";

  const SKILL_LABELS = {
    writing: "✍️ Yozma nutq", speaking: "🎙️ Og'zaki nutq", listening: "🎧 Tinglab tushunish", reading: "📖 O'qish",
    anxiety: "😰 Xavotir (FLCAS)", motivation: "🔥 Motivatsiya",
    meta_planning: "🗺️ Rejalashtirish", meta_monitoring: "👁️ Monitoring", meta_evaluation: "⚖️ Baholash", meta_regulation: "🎛️ O'zini boshqarish"
  };
  const SKILL_ORDER = ["listening", "reading", "writing", "speaking", "anxiety", "motivation", "meta_planning", "meta_monitoring", "meta_evaluation", "meta_regulation"];
  const SCAFFOLD_LABELS = { full: "to'liq", partial: "qisman", none: "ko'maksiz" };
  const SCAFFOLD_CHIP = { full: "full", partial: "part", none: "none" };
  const ASSESS_LABELS = { pre: "Pre (kirish)", mid: "Mid (oraliq)", post: "Post (yakuniy)" };

  function esc(v) {
    if (typeof window.escapeHtml === "function") return window.escapeHtml(v);
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
  }
  function num(v, digits) {
    if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "—";
    const n = Number(v);
    return digits === undefined ? String(n) : n.toFixed(digits);
  }
  function skillLabel(k) { return SKILL_LABELS[k] || k || "—"; }

  const CELL = "padding:7px 8px;border-bottom:1px solid var(--line-2);font-size:12.5px;white-space:nowrap";
  const TH = "text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;white-space:nowrap";

  function tableWrap(headers, rowsHtml, emptyText) {
    if (!rowsHtml) return `<div style="color:var(--muted);font-size:12.5px;padding:8px 0">${esc(emptyText || "Ma'lumot yo'q.")}</div>`;
    return `<div style="overflow-x:auto;-webkit-overflow-scrolling:touch"><table style="width:100%;border-collapse:collapse;min-width:420px">
      <thead><tr>${headers.map(h => `<th style="${TH}">${esc(h)}</th>`).join("")}</tr></thead><tbody>${rowsHtml}</tbody></table></div>`;
  }

  // ---------- Inline SVG chiziqli grafik (kutubxonasiz) ----------
  function lineChart(points) {
    const W = 640, H = 210, padL = 36, padR = 14, padT = 16, padB = 32;
    const scored = points.filter(p => typeof p.y === "number" && !isNaN(p.y));
    if (!scored.length) {
      return `<div style="color:var(--muted);font-size:12.5px;padding:14px;text-align:center;border:1px dashed var(--line);border-radius:8px">Hali balli mashg'ulot yo'q — birinchi mashg'ulotni yakunlang, grafik shu yerda paydo bo'ladi.</div>`;
    }
    const n = points.length;
    const xFor = (i) => (n === 1) ? padL + (W - padL - padR) / 2 : padL + i * (W - padL - padR) / (n - 1);
    const yFor = (v) => padT + (100 - Math.max(0, Math.min(100, v))) * (H - padT - padB) / 100;
    const grid = [0, 25, 50, 75, 100].map(v =>
      `<line x1="${padL}" x2="${W - padR}" y1="${yFor(v).toFixed(1)}" y2="${yFor(v).toFixed(1)}" stroke="var(--line-2)" stroke-width="1"/>` +
      `<text x="${padL - 6}" y="${(yFor(v) + 3.5).toFixed(1)}" text-anchor="end" font-size="10" fill="var(--muted)">${v}</text>`).join("");
    const thr = yFor(60).toFixed(1);
    const pts = points.map((p, i) => (typeof p.y === "number" && !isNaN(p.y)) ? `${xFor(i).toFixed(1)},${yFor(p.y).toFixed(1)}` : null).filter(Boolean);
    const line = pts.length >= 2 ? `<polyline fill="none" stroke="var(--teal)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="${pts.join(" ")}"/>` : "";
    const dots = points.map((p, i) => (typeof p.y === "number" && !isNaN(p.y))
      ? `<circle cx="${xFor(i).toFixed(1)}" cy="${yFor(p.y).toFixed(1)}" r="${n === 1 ? 6 : 4}" fill="${p.y >= 60 ? "var(--teal)" : "var(--clay)"}" stroke="var(--card)" stroke-width="1.5"><title>${esc(p.title)}: ${esc(p.y)}</title></circle>`
      : "").join("");
    const step = Math.max(1, Math.ceil(n / 8));
    const labels = points.map((p, i) => (i % step === 0 || i === n - 1)
      ? `<text x="${xFor(i).toFixed(1)}" y="${H - 10}" text-anchor="middle" font-size="10" fill="var(--muted)">${esc(p.x)}</text>` : "").join("");
    const single = n === 1 ? `<text x="${xFor(0).toFixed(1)}" y="${(yFor(points[0].y) - 12).toFixed(1)}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--ink)">${esc(points[0].y)}</text>` : "";
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Mashg'ulot ballari dinamikasi" style="display:block;max-width:100%;height:auto">
      ${grid}
      <line x1="${padL}" x2="${W - padR}" y1="${thr}" y2="${thr}" stroke="var(--amber)" stroke-dasharray="4 4" stroke-width="1"/>
      <text x="${W - padR}" y="${(Number(thr) - 4).toFixed(1)}" text-anchor="end" font-size="10" fill="var(--amber)">60 — muvaffaqiyat chegarasi</text>
      ${line}${dots}${labels}${single}
    </svg>`;
  }

  // ---------- Bo'limlar ----------
  function kpiTile(label, value, sub, color) {
    return `<div style="background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow)">
      <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;font-weight:700">${esc(label)}</div>
      <div style="font-family:var(--serif);font-size:26px;font-weight:700;color:${color || "var(--ink)"};margin-top:4px;line-height:1.1">${esc(value)}</div>
      ${sub ? `<div style="font-size:11.5px;color:var(--muted);margin-top:4px;line-height:1.4">${esc(sub)}</div>` : ""}
    </div>`;
  }

  function renderHeader(data) {
    const u = (window.STATE && window.STATE.currentUser) || {};
    return `<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;margin-bottom:16px">
      <div>
        <h2 style="font-family:var(--serif);font-size:22px;margin:0;color:var(--ink)">📈 Mening dinamikam</h2>
        <p style="font-size:13px;color:var(--muted);margin:4px 0 0">Refleksiya moduli: mashg'ulot ballari, o'zini baholash aniqligi, ko'mak yo'li va pre/post o'lchovlar${u.full_name ? ` · ${esc(u.full_name)}` : ""}</p>
      </div>
      <button type="button" class="btn-primary" style="padding:8px 14px;font-size:12.5px" onclick="window.loadDynamicsScreen()">🔄 Yangilash</button>
    </div>`;
  }

  // Qayta ishlash (revise) ko'rsatkichi: score_improvement != null bo'lgan yozuvlar o'rtachasi
  function revisionStats(timeline) {
    const vals = (timeline || []).map(t => t.score_improvement).filter(v => v !== null && v !== undefined && !isNaN(Number(v))).map(Number);
    const revised = (timeline || []).filter(t => Number(t.revision_count || 0) > 0).length;
    if (!vals.length) return { avg: null, count: 0, revised };
    return { avg: Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10, count: vals.length, revised };
  }

  function renderKpis(data) {
    const ma = data.metacognitive_accuracy || {};
    const gap = ma.avg_rating_gap;
    const gapColor = (gap === null || gap === undefined) ? "var(--muted)" : (gap <= 0.5 ? "var(--teal)" : (gap <= 1.25 ? "var(--amber)" : "var(--clay)"));
    const trend = (ma.trend === null || ma.trend === undefined) ? "" : (ma.trend < 0 ? `Tendensiya: ${num(ma.trend, 2)} (aniqlik oshmoqda)` : (ma.trend > 0 ? `Tendensiya: +${num(ma.trend, 2)} (farq o'smoqda)` : "Tendensiya: o'zgarishsiz"));
    const rv = revisionStats(data.timeline);
    const rvValue = rv.avg === null ? "—" : `${rv.avg > 0 ? "+" : ""}${num(rv.avg, 1)}`;
    const rvSub = rv.avg === null ? "hali qayta ishlangan mashg'ulot yo'q" : `${rv.count} ta mashg'ulot · ${rv.revised} tasida qoralama qayta topshirilgan`;
    const rvColor = rv.avg === null ? "var(--muted)" : (rv.avg > 0 ? "var(--teal)" : (rv.avg < 0 ? "var(--clay)" : "var(--ink)"));
    return `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px">
      ${kpiTile("Mashg'ulotlar", num(data.lessons_completed), "yakunlangan va saqlangan", "var(--ink)")}
      ${kpiTile("Muvaffaqiyat seriyasi", num(data.success_streak), "ketma-ket ≥60 ball", (data.success_streak || 0) >= 3 ? "var(--teal)" : "var(--ink)")}
      ${kpiTile("Metakognitiv aniqlik", num(gap, 2), trend || (ma.note || ""), gapColor)}
      ${kpiTile("Yordam so'rovlari", num(data.help_requests_total), "3-bosqichdagi AI'ga urinishlar", (data.help_requests_total || 0) > 0 ? "var(--clay)" : "var(--teal)")}
      ${kpiTile("Qayta ishlashdan o'sish (o'rtacha)", rvValue, rvSub, rvColor)}
    </div>`;
  }

  function renderChart(timeline) {
    const points = (timeline || []).map((t, i) => ({
      x: t.date ? String(t.date).slice(5) : `#${i + 1}`,
      y: (t.score === null || t.score === undefined) ? null : Number(t.score),
      title: `${t.date || ""} ${skillLabel(t.skill)}`
    }));
    return `<div class="card" style="margin-bottom:16px">
      <h3>Ballar dinamikasi (0–100)</h3>
      ${lineChart(points)}
      <div style="font-size:11.5px;color:var(--muted);margin-top:8px">Nuqta: bitta yakunlangan mashg'ulot; yashil — ≥60, qizg'ish — &lt;60. Sichqoncha bilan sana va ko'nikma ko'rinadi.</div>
    </div>`;
  }

  function renderTimeline(timeline) {
    const rows = (timeline || []).slice().reverse().map(t => {
      const gap = t.rating_gap;
      const gapColor = (gap === null || gap === undefined) ? "var(--muted)" : (gap <= 0.5 ? "var(--teal)" : (gap <= 1.25 ? "var(--amber)" : "var(--clay)"));
      const sc = t.scaffold ? `<span class="chip ${SCAFFOLD_CHIP[t.scaffold] || ""}">${esc(SCAFFOLD_LABELS[t.scaffold] || t.scaffold)}</span>` : "—";
      const rc = Number(t.revision_count || 0);
      const imp = (t.score_improvement === null || t.score_improvement === undefined || isNaN(Number(t.score_improvement))) ? null : Number(t.score_improvement);
      const impColor = imp === null ? "var(--muted)" : (imp > 0 ? "var(--teal)" : (imp < 0 ? "var(--clay)" : "var(--muted)"));
      const impTxt = imp === null ? "—" : `${imp > 0 ? "+" : (imp < 0 ? "−" : "")}${num(Math.abs(imp))}`;
      const impTitle = imp === null ? "" : ` title="Birinchi qoralama: ${esc(num(t.first_score))} → yakuniy: ${esc(num(t.score))}"`;
      const cefr = t.cefr_estimate ? `<span class="chip" style="background:var(--teal-soft);color:var(--teal-deep);border-color:#BCD9D3;font-weight:700;font-size:10.5px" title="Taxminiy lokal CEFR (yakuniy darajani o'qituvchi belgilaydi)">${esc(t.cefr_estimate)}</span>` : `<span style="color:var(--muted)">—</span>`;
      return `<tr>
        <td style="${CELL}">${esc(t.date || "—")}</td>
        <td style="${CELL}">${esc(skillLabel(t.skill))}</td>
        <td style="${CELL};text-align:center;font-weight:700">${esc(t.variant || "—")}</td>
        <td style="${CELL}">${sc}</td>
        <td style="${CELL};text-align:center;font-weight:700;color:${(t.score !== null && t.score !== undefined && t.score >= 60) ? "var(--teal)" : "var(--clay)"}">${num(t.score)}</td>
        <td style="${CELL};text-align:center">${cefr}</td>
        <td style="${CELL};text-align:center;font-weight:600;color:${rc > 0 ? "var(--ink)" : "var(--muted)"}" title="Qayta ishlangan qoralamalar soni (birinchi variantdan tashqari)">${rc > 0 ? `♻️ ${rc}` : "0"}</td>
        <td style="${CELL};text-align:center;font-weight:700;color:${impColor}"${impTitle}>${impTxt}</td>
        <td style="${CELL};text-align:center;color:${gapColor};font-weight:600">${num(gap, 2)}</td>
        <td style="${CELL};text-align:center">${num(t.minutes, 1)}</td>
        <td style="${CELL};white-space:normal;min-width:180px;line-height:1.45">${esc(t.next_goal || "—")}</td>
      </tr>`;
    }).join("");
    return `<div class="card" style="margin-bottom:16px">
      <h3>Mashg'ulotlar jadvali</h3>
      ${tableWrap(["Sana", "Ko'nikma", "Variant", "Ko'mak", "Ball", "CEFR", "Qoralamalar", "O'sish", "Farq (siz−AI)", "Daqiqa", "Keyingi maqsad"], rows, "Hali yakunlangan mashg'ulot yo'q. 5-bosqichda refleksiyani saqlagach, bu yerda paydo bo'ladi.")}
      <div style="font-size:11.5px;color:var(--muted);margin-top:8px">Qoralamalar — 4-bosqichda qayta ishlab, qayta topshirilgan versiyalar soni; O'sish — yakuniy ball − birinchi qoralama bali; CEFR — taxminiy lokal baho.</div>
    </div>`;
  }

  // /student/dynamics timeline'ida qayta ishlash maydonlari yo'q — /lesson/history (LessonRecord) dan birlashtiriladi
  function mergeHistoryIntoTimeline(timeline, records) {
    const tl = Array.isArray(timeline) ? timeline : [];
    const recs = Array.isArray(records) ? records.slice().reverse() : []; // history desc -> asc
    if (!recs.length) return tl;
    const used = new Set();
    return tl.map(t => {
      if (t.revision_count !== undefined && t.score_improvement !== undefined) return t; // backend allaqachon bergan
      let idx = recs.findIndex((r, i) => !used.has(i) && String(r.created_at || "").slice(0, 10) === String(t.date || "") &&
        (r.skill || null) === (t.skill || null) && String(r.score) === String(t.score));
      if (idx === -1) idx = recs.findIndex((r, i) => !used.has(i) && String(r.created_at || "").slice(0, 10) === String(t.date || ""));
      if (idx === -1) return t;
      used.add(idx);
      const r = recs[idx];
      return Object.assign({}, t, {
        revision_count: r.revision_count || 0, first_score: r.first_score,
        score_improvement: (r.score_improvement === undefined) ? null : r.score_improvement,
        cefr_estimate: r.cefr_estimate || null, relevance_score: r.relevance_score
      });
    });
  }

  function renderBySkill(bySkill) {
    const keys = Object.keys(bySkill || {});
    if (!keys.length) {
      return `<div class="card" style="margin-bottom:16px"><h3>Ko'nikma bo'yicha</h3><div style="color:var(--muted);font-size:12.5px">Ko'nikma kesimida ma'lumot hali yo'q.</div></div>`;
    }
    keys.sort((a, b) => SKILL_ORDER.indexOf(a) - SKILL_ORDER.indexOf(b));
    const cards = keys.map(k => {
      const d = bySkill[k] || {};
      const tr = Number(d.trend || 0);
      const trColor = tr > 0 ? "var(--teal)" : (tr < 0 ? "var(--clay)" : "var(--muted)");
      const trTxt = tr > 0 ? `▲ +${num(tr)}` : (tr < 0 ? `▼ ${num(tr)}` : "■ 0");
      return `<div style="background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px 14px">
        <div style="font-weight:700;font-size:13.5px;margin-bottom:6px">${esc(skillLabel(k))}</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12.5px;color:var(--ink-2)">
          <span>Soni: <b>${num(d.count)}</b></span>
          <span>O'rtacha: <b>${num(d.avg, 1)}</b></span>
          <span>Birinchi: <b>${num(d.first)}</b></span>
          <span>Oxirgi: <b>${num(d.last)}</b></span>
          <span style="color:${trColor};font-weight:700">${trTxt}</span>
        </div>
      </div>`;
    }).join("");
    return `<div class="card" style="margin-bottom:16px">
      <h3>Ko'nikma bo'yicha</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px">${cards}</div>
      <div style="font-size:11.5px;color:var(--muted);margin-top:8px">Tendensiya = oxirgi ball − birinchi ball (shu ko'nikma bo'yicha).</div>
    </div>`;
  }

  function renderScaffoldPath(data) {
    const path = data.scaffold_path || [];
    const chips = path.length
      ? path.map((s, i) => `<span class="chip ${SCAFFOLD_CHIP[s] || ""}" title="${i + 1}-mashg'ulot">${i + 1}. ${esc(SCAFFOLD_LABELS[s] || s)}</span>`).join(`<span style="color:var(--muted)">→</span>`)
      : `<span style="color:var(--muted);font-size:12.5px">Hali ko'mak yo'li shakllanmagan.</span>`;
    const suggested = !!data.scaffold_reduction_suggested;
    return `<div class="card" style="margin-bottom:16px">
      <h3>Ko'mak yo'li (scaffolding)</h3>
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:10px">${chips}</div>
      ${suggested ? `<div style="padding:10px 12px;border-radius:8px;background:var(--teal-soft);border:1px solid #BCD9D3;color:var(--teal-deep);font-size:13px;font-weight:600;margin-bottom:8px">🎉 ${esc(String(data.success_streak || 3))} ta ketma-ket muvaffaqiyat — ko'mak darajasini bir pog'ona pasaytirish o'qituvchiga taklif qilindi. Yakuniy qaror o'qituvchida (2-qoida: sabab ochiq).</div>` : ""}
      ${data.scaffold_rule ? `<div class="why-box" style="margin-top:0;padding:10px 14px"><b>Qoida</b>${esc(data.scaffold_rule)}</div>` : ""}
    </div>`;
  }

  function renderAssessments(assess) {
    const types = ["pre", "mid", "post"].filter(t => assess && assess[t]);
    if (!types.length) {
      return `<div class="card" style="margin-bottom:16px"><h3>Pre/Post baholar</h3><div style="color:var(--muted);font-size:12.5px">Diagnostika natijalari hali yo'q. Diagnostika va anketani topshirgach (pre), keyin yakuniy o'lchov (post) shu yerda solishtiriladi.</div></div>`;
    }
    const skills = [];
    types.forEach(t => Object.keys(assess[t] || {}).forEach(k => { if (!skills.includes(k)) skills.push(k); }));
    skills.sort((a, b) => {
      const ia = SKILL_ORDER.indexOf(a), ib = SKILL_ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
    const hasPrePost = assess.pre && assess.post;
    const rows = skills.map(k => {
      const cells = types.map(t => `<td style="${CELL};text-align:center;font-weight:700">${num(assess[t][k])}</td>`).join("");
      let delta = "";
      if (hasPrePost && assess.pre[k] !== undefined && assess.post[k] !== undefined) {
        const d = Number(assess.post[k]) - Number(assess.pre[k]);
        const good = (k === "anxiety") ? d < 0 : d > 0; // xavotirning kamayishi ijobiy
        delta = `<td style="${CELL};text-align:center;font-weight:700;color:${d === 0 ? "var(--muted)" : (good ? "var(--teal)" : "var(--clay)")}">${d > 0 ? "+" : ""}${num(d)}</td>`;
      } else if (hasPrePost) {
        delta = `<td style="${CELL};text-align:center;color:var(--muted)">—</td>`;
      }
      return `<tr><td style="${CELL}">${esc(skillLabel(k))}</td>${cells}${delta}</tr>`;
    }).join("");
    const headers = ["Ko'rsatkich"].concat(types.map(t => ASSESS_LABELS[t] || t));
    if (hasPrePost) headers.push("Δ post−pre");
    return `<div class="card" style="margin-bottom:16px">
      <h3>Pre/Post baholar (0–100)</h3>
      ${tableWrap(headers, rows)}
      <div style="font-size:11.5px;color:var(--muted);margin-top:8px">Ko'nikmalar — diagnostika testi; xavotir va motivatsiya — anketa; metakognitiv komponentlar — 1–5 shkala ×20. Xavotirning kamayishi ijobiy o'zgarish sifatida belgilanadi.</div>
    </div>`;
  }

  function renderProfileHistory(hist) {
    const rows = (hist || []).slice().reverse().map(p => {
      const c = p.cefr || {};
      return `<tr>
        <td style="${CELL}">${esc(p.date || "—")}</td>
        <td style="${CELL}">${esc(p.source || "—")}</td>
        <td style="${CELL};text-align:center">${esc(c.listening || "—")}</td>
        <td style="${CELL};text-align:center">${esc(c.reading || "—")}</td>
        <td style="${CELL};text-align:center">${esc(c.writing || "—")}</td>
        <td style="${CELL};text-align:center">${esc(c.speaking || "—")}</td>
        <td style="${CELL};text-align:center">${num(p.anxiety_level)}</td>
        <td style="${CELL};text-align:center">${num(p.autonomy_readiness)}</td>
      </tr>`;
    }).join("");
    return `<div class="card" style="margin-bottom:16px">
      <h3>Profil tarixi</h3>
      ${tableWrap(["Sana", "Manba", "Tinglash", "O'qish", "Yozma", "Og'zaki", "Xavotir", "Avtonomiya"], rows, "Profil yozuvlari hali yo'q.")}
    </div>`;
  }

  function renderAll(data) {
    return renderHeader(data) + renderKpis(data) + renderChart(data.timeline) + renderTimeline(data.timeline) +
      renderBySkill(data.by_skill) + renderScaffoldPath(data) + renderAssessments(data.assessments) + renderProfileHistory(data.profile_history) +
      `<div class="why-box" style="margin-top:4px"><b>Refleksiya moduli qoidasi</b>Tizim xulosa chiqarmaydi: ko'rsatkichlar raqamli, talqin va keyingi maqsad talabaniki. Ko'mak darajasini o'zgartirish qarori o'qituvchida (sabab ochiq).</div>`;
  }

  function loginNotice() {
    return `<div class="card" style="text-align:center;padding:30px">
      <div style="font-size:30px;margin-bottom:8px">🔑</div>
      <div style="font-weight:700;font-size:15px;margin-bottom:6px">Dinamika faqat tizimga kirgan talaba uchun</div>
      <div style="font-size:13px;color:var(--muted);margin-bottom:14px">Mashg'ulot yozuvlari, o'zini baholash aniqligi va pre/post o'lchovlar shaxsiy profilga bog'lanadi.</div>
      <button type="button" class="btn-primary" onclick="window.openLoginModal && window.openLoginModal()">Tizimga kirish</button>
    </div>`;
  }

  function errorBox(msg) {
    return `<div class="card" style="padding:16px;border-color:#F87171;background:#FDF2F2;color:#991B1B;font-size:13.5px">⚠️ ${esc(msg)}
      <div style="margin-top:10px"><button type="button" class="btn-primary" style="padding:7px 12px;font-size:12.5px" onclick="window.loadDynamicsScreen()">🔄 Qayta urinish</button></div></div>`;
  }

  window.loadDynamicsScreen = async function () {
    const root = document.getElementById("dynamicsRoot");
    if (!root) return;
    const S = window.STATE || {};
    if (!S.token) { root.innerHTML = loginNotice(); return; }
    root.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">⏳ Dinamika yuklanmoqda...</div>`;
    try {
      const headers = { "Authorization": `Bearer ${S.token}` };
      const [res, histRes] = await Promise.all([
        fetch(`${S.apiBaseUrl}/student/dynamics`, { headers }),
        fetch(`${S.apiBaseUrl}/lesson/history`, { headers }).catch(() => null)
      ]);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        root.innerHTML = res.status === 401 ? loginNotice() : errorBox(typeof data.detail === "string" ? data.detail : `Dinamikani yuklab bo'lmadi (HTTP ${res.status}).`);
        return;
      }
      let records = [];
      if (histRes && histRes.ok) { const h = await histRes.json().catch(() => ({})); records = h.records || []; }
      data.timeline = mergeHistoryIntoTimeline(data.timeline, records);
      root.innerHTML = renderAll(data);
    } catch (e) {
      root.innerHTML = errorBox("Serverga ulanishda xatolik. Server ishlab turganini tekshiring.");
    }
  };
})();
