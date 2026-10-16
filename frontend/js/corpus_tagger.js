/**
 * TILORA — Parallel korpus: kollokatsiyalarni morfologik va semantik teglash (tadqiqot vositasi).
 * Dissertatsiya: "Tarjima va teng matnlar parallel korpusida o'zaro faol birikuvchi (kollokatsion) so'zlar
 * tadqiqi (o'zbek va ingliz tillari misolida)". Barcha ma'lumotlar /api/research/corpus/* dan olinadi.
 * HTML ga faqat esc() orqali kiritiladi.
 */
(function () {
  const esc = (s) => (window.escapeHtml ? window.escapeHtml(s == null ? "" : String(s)) : String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"));
  const api = () => (window.STATE && STATE.apiBaseUrl) ? STATE.apiBaseUrl : "/api";
  const BASE = () => `${api()}/research/corpus`;
  const $ = (id) => document.getElementById(id);
  const setHtml = (id, html) => { const el = $(id); if (el) el.innerHTML = html; };

  const TH = "text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap;font-size:11px;text-transform:uppercase;color:var(--muted)";
  const TD = "padding:6px 8px;border-bottom:1px solid var(--line-2);vertical-align:top;line-height:1.45;font-size:12.5px";
  const MONO = "font-family:var(--mono);font-size:11.5px";
  const EQ_LABEL = { full: "To'liq", partial: "Qisman", zero: "Nol (lakuna)", "zero?": "Nol? (taxmin)", grammatical: "Grammatik", unaligned: "Topilmadi" };
  const EQ_STYLE = { full: "background:var(--teal-soft);color:var(--teal)", partial: "background:var(--amber-soft);color:var(--amber)", zero: "background:#FDE8E4;color:var(--clay)", "zero?": "background:#FDE8E4;color:var(--clay)", grammatical: "background:var(--surface-2);color:var(--ink-2)", unaligned: "background:var(--surface-2);color:var(--muted)" };
  const CONF_LABEL = { bank: "Bank", lexicon: "Lug'at", heuristic: "Taxmin", none: "—" };

  let lastResult = null;
  let tagsetCache = null;
  let bankCache = null;

  function table(headers, rows, minWidth) {
    if (!rows.length) return `<div style="color:var(--muted);font-size:12.5px;padding:6px 0">Ma'lumot yo'q.</div>`;
    return `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;${minWidth ? `min-width:${minWidth}px` : ""}">
      <thead><tr>${headers.map(h => `<th style="${TH}">${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${rows.map(r => `<tr>${r.map(c => `<td style="${TD}">${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }
  function chip(text, style) { return `<span style="display:inline-block;padding:1px 8px;border-radius:9px;font-size:11px;font-weight:700;white-space:nowrap;${style || "background:var(--surface-2);color:var(--ink-2)"}">${esc(text)}</span>`; }
  function featStr(f) { return Object.keys(f || {}).sort().map(k => `${k}=${f[k]}`).join("|") || "_"; }
  function distTable(obj, label) {
    const entries = Object.entries(obj || {});
    const total = entries.reduce((n, [, v]) => n + v, 0) || 1;
    return table([label, "Soni", "%"], entries.map(([k, v]) => [esc(k), esc(v), esc((100 * v / total).toFixed(1))]));
  }

  // ---------------- Yuklash / tahlil ----------------
  window.corpusLoadSample = async function () {
    try {
      const r = await fetch(`${BASE()}/sample`);
      const d = await r.json();
      $("corpusEnText").value = d.source_text; $("corpusUzText").value = d.target_text;
      setHtml("corpusStatus", `<span style="color:var(--muted)">${esc(d.note)}</span>`);
    } catch (e) { setHtml("corpusStatus", `<span style="color:var(--clay)">Namuna yuklanmadi (${esc(e.message)})</span>`); }
  };

  window.corpusAnalyze = async function () {
    const en = ($("corpusEnText").value || "").trim(), uz = ($("corpusUzText").value || "").trim();
    const minFreq = parseInt($("corpusMinFreq").value || "1", 10), span = parseInt($("corpusSpan").value || "3", 10);
    if (!en && !uz) { setHtml("corpusStatus", `<span style="color:var(--clay)">Kamida bitta matn kiriting.</span>`); return; }
    setHtml("corpusStatus", `⏳ Tahlil qilinmoqda...`);
    $("corpusResults").style.display = "none";
    try {
      if (en && uz) {
        const r = await fetch(`${BASE()}/analyze`, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ source_text: en, target_text: uz, min_freq: minFreq, span }) });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        lastResult = await r.json();
        renderAll(lastResult);
        setHtml("corpusStatus", `✅ ${esc(lastResult.meta.sentence_pairs)} gap juftligi tekislandi (${esc(lastResult.meta.alignment_method)}) · ${esc(lastResult.summary.aligned_pairs)} kollokatsiya juftligi.`);
      } else {
        const r = await fetch(`${BASE()}/tag`, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: en || uz, lang: en ? "en" : "uz" }) });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        const d = await r.json();
        lastResult = { single: d };
        renderSingle(d);
        setHtml("corpusStatus", `✅ ${esc(d.stats.tokens)} token teglandi (${esc(d.lang.toUpperCase())}). Parallel tahlil uchun ikkala matnni kiriting.`);
      }
      $("corpusResults").style.display = "block";
      window.corpusTab("overview");
    } catch (e) { setHtml("corpusStatus", `<span style="color:var(--clay)">Xato: ${esc(e.message)}</span>`); }
  };

  window.corpusTab = function (name) {
    document.querySelectorAll("[data-corpus-tab]").forEach(b => {
      const on = b.getAttribute("data-corpus-tab") === name;
      b.style.background = on ? "var(--teal)" : "var(--surface-2)"; b.style.color = on ? "#fff" : "var(--ink)";
    });
    document.querySelectorAll("[data-corpus-pane]").forEach(p => { p.style.display = p.getAttribute("data-corpus-pane") === name ? "block" : "none"; });
    if (name === "tagset" && !tagsetCache) renderTagset();
    if (name === "bank" && !bankCache) renderBank();
  };

  // ---------------- Render: parallel ----------------
  function statsTiles(st, title) {
    const tiles = [[st.sentences, "gap"], [st.tokens, "token"], [st.types, "lemma (type)"], [st.ttr, "TTR"], [Math.round(st.lexicon_coverage * 100) + "%", "lug'at qamrovi"]];
    if (st.avg_suffixes_per_token != null) tiles.push([st.avg_suffixes_per_token, "affiks / token"]);
    return `<div style="font-weight:700;margin:10px 0 6px">${esc(title)}</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px">${tiles.map(([n, l]) => `
      <div style="padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2);text-align:center">
        <div style="font-size:20px;font-weight:700;color:var(--teal)">${esc(n)}</div><div style="font-size:11px;color:var(--muted)">${esc(l)}</div></div>`).join("")}</div>`;
  }

  function renderOverview(res) {
    const s = res.summary;
    let html = statsTiles(res.source.stats, "Ingliz tili matni") + statsTiles(res.target.stats, "O'zbek tili matni");
    html += `<div style="margin-top:14px;padding:10px 12px;border-left:4px solid var(--teal);background:var(--teal-soft);border-radius:8px;font-size:12.5px;line-height:1.6">
      <b>Standartlar:</b> ${esc(res.meta.standards)}<br><b>Tekislash:</b> ${esc(res.meta.alignment_method)} · <b>Oyna (span):</b> ${esc(res.meta.span)} · <b>Min. chastota:</b> ${esc(res.meta.min_freq)}</div>`;
    html += `<h4 style="margin:16px 0 6px;font-size:14px">3.1. Semantik-struktur tasnif (kollokatsiyalar taqsimoti)</h4>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px">
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Struktur tip (EN)</div>${distTable(s.by_structure_en, "Tip")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Struktur tip (UZ)</div>${distTable(s.by_structure_uz, "Tip")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">BBI tipi (EN)</div>${distTable(s.by_bbi_en, "BBI")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">BBI tipi (UZ)</div>${distTable(s.by_bbi_uz, "BBI")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Leksik funksiya (EN)</div>${distTable(s.by_lf_en, "LF")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Leksik funksiya (UZ)</div>${distTable(s.by_lf_uz, "LF")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">USAS semantik maydon (EN, tayanch so'z)</div>${distTable(s.by_usas_en, "USAS")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">USAS semantik maydon (UZ, tayanch so'z)</div>${distTable(s.by_usas_uz, "USAS")}</div>
      </div>`;
    html += `<h4 style="margin:16px 0 6px;font-size:14px">3.2. Tarjima ekvivalentligi</h4>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px">
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Ekvivalentlik tipi</div>${distTable(Object.fromEntries(Object.entries(s.by_equivalence).map(([k, v]) => [EQ_LABEL[k] || k, v])), "Tip")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Tarjima protsedurasi (Vinay & Darbelnet / Baker)</div>${distTable(s.by_procedure, "Protsedura")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">Moslashtirish manbai</div>${distTable(Object.fromEntries(Object.entries(s.by_confidence).map(([k, v]) => [CONF_LABEL[k] || k, v])), "Manba")}</div>
      </div>`;
    html += `<h4 style="margin:16px 0 6px;font-size:14px">3.3. Lingvomadaniy xususiyatli kollokatsiyalar (${esc(s.culture_specific.length)})</h4>` +
      table(["Ingliz", "O'zbek", "Ekvivalentlik", "Izoh"], s.culture_specific.map(c => [`<b>${esc(c.en)}</b>`, esc(c.uz), chip(EQ_LABEL[c.equivalence] || c.equivalence, EQ_STYLE[c.equivalence]), esc(c.note)]), 600);
    html += `<h4 style="margin:16px 0 6px;font-size:14px">Morfologik belgilar taqsimoti (UD, o'zbek)</h4>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px">${Object.entries(res.target.stats.feature_distribution).map(([f, d]) =>
        `<div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px;${MONO}">${esc(f)}</div>${distTable(d, "Qiymat")}</div>`).join("")}</div>`;
    setHtml("corpusPaneOverview", html);
  }

  function tokenTable(sents, lang) {
    return sents.map(s => `<details ${s.id <= 2 ? "open" : ""} style="border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:8px;background:var(--card)">
      <summary style="cursor:pointer;font-size:13px"><b>${esc(lang.toUpperCase())}-${esc(s.id)}</b> · ${esc(s.text)}</summary>
      ${table(lang === "uz" ? ["#", "So'z-shakl", "O'zak / affiks zanjiri", "UPOS", "UD belgilari", "USAS", "MWE"] : ["#", "So'z-shakl", "Lemma", "UPOS", "PTB", "UD belgilari", "USAS"],
        s.tokens.map(t => lang === "uz"
          ? [esc(t.id), `<b>${esc(t.form)}</b>${t.known ? "" : ` <span title="Lug'atda yo'q" style="color:var(--amber)">?</span>`}`, `<span style="${MONO}">${esc(t.morph)}</span>`, chip(t.upos), `<span style="${MONO}">${esc(featStr(t.feats))}</span>`, `<span style="${MONO}">${esc(t.usas)}</span>`, t.mwe ? `<span style="${MONO};color:var(--teal)">${esc(t.mwe)}</span>` : (t.mwe_part_of ? `<span style="color:var(--muted);font-size:11px">↳ ${esc(t.mwe_part_of)}</span>` : "")]
          : [esc(t.id), `<b>${esc(t.form)}</b>${t.known ? "" : ` <span title="Lug'atda yo'q" style="color:var(--amber)">?</span>`}`, `<span style="${MONO}">${esc(t.lemma)}</span>`, chip(t.upos), `<span style="${MONO}">${esc(t.xpos)}</span>`, `<span style="${MONO}">${esc(featStr(t.feats))}</span>`, `<span style="${MONO}">${esc(t.usas)}</span>`]), 640)}
    </details>`).join("");
  }

  function collTable(coll) {
    return table(["Kollokatsiya", "Shakllar", "Struktur", "BBI", "LF", "USAS", "Tayanch", "f", "MI", "t", "G²", "logDice", "Kontinuum", "Bank muqobili"],
      coll.map(c => [`<b>${esc(c.collocation)}</b>${c.in_bank ? ` <span title="Kollokatsiya bankida mavjud" style="color:var(--teal)">★</span>` : ""}`,
        `<span style="color:var(--muted);font-size:11.5px">${esc(c.forms.join("; "))}</span>`, `<span style="${MONO}">${esc(c.structure)}</span><div style="font-size:10.5px;color:var(--muted)">${esc(c.structure_uz)}</div>`,
        chip(c.bbi, "background:var(--teal-soft);color:var(--teal)"), esc(c.lf), `<span style="${MONO}">${esc(c.usas)}</span>`, esc(c.base), esc(c.frequency),
        esc(c.measures.mi), esc(c.measures.t_score), esc(c.measures.log_likelihood), `<b>${esc(c.measures.logdice)}</b><div style="font-size:10.5px;color:var(--muted)">${esc(c.strength)}</div>`,
        esc(c.continuum || ""), c.counterpart ? `${esc(c.counterpart)} ${chip(EQ_LABEL[c.equivalence] || c.equivalence, EQ_STYLE[c.equivalence])}` : ""]), 1100);
  }

  function pairsTable(pairs) {
    return table(["Ingliz kollokatsiyasi", "Struktur / BBI", "LF", "USAS", "O'zbek muqobili", "Struktur (UZ)", "Ekvivalentlik", "Protsedura", "Manba", "Izoh", "Gap"],
      pairs.map(p => [`<b>${esc(p.en)}</b>${p.culture ? ` <span title="Lingvomadaniy xususiyat" style="color:var(--clay)">◆</span>` : ""}`,
        `<span style="${MONO}">${esc(p.en_structure)}</span> ${chip(p.en_bbi, "background:var(--teal-soft);color:var(--teal)")}`, esc(p.lf), `<span style="${MONO}">${esc(p.usas)}</span>`,
        p.uz ? esc(p.uz) : `<span style="color:var(--muted)">—</span>`, `<span style="${MONO}">${esc(p.uz_structure || "")}</span>`,
        chip(EQ_LABEL[p.equivalence] || p.equivalence, EQ_STYLE[p.equivalence]), esc(p.procedure), esc(CONF_LABEL[p.confidence] || p.confidence),
        `<span style="font-size:11.5px;color:var(--ink-2)">${esc(p.note || "")}</span>`, `<span style="${MONO}">${esc(p.sentence_pair.en.join(","))}↔${esc(p.sentence_pair.uz.join(","))}</span>`]), 1100);
  }

  function alignTable(pairs) {
    return table(["#", "Ingliz", "O'zbek"], pairs.map((p, i) => [esc(i + 1), `<span style="${MONO};color:var(--muted)">[${esc(p.en.join(","))}]</span> ${esc(p.en_text)}`, `<span style="${MONO};color:var(--muted)">[${esc(p.uz.join(","))}]</span> ${esc(p.uz_text)}`]), 600);
  }

  function renderAll(res) {
    renderOverview(res);
    setHtml("corpusPaneTokensEn", tokenTable(res.source.sentences, "en"));
    setHtml("corpusPaneTokensUz", tokenTable(res.target.sentences, "uz"));
    setHtml("corpusPaneCollEn", collTable(res.source.collocations));
    setHtml("corpusPaneCollUz", collTable(res.target.collocations));
    setHtml("corpusPanePairs", `<h4 style="margin:0 0 8px;font-size:14px">Tekislangan gaplar</h4>${alignTable(res.alignment.pairs)}
      <h4 style="margin:16px 0 8px;font-size:14px">Kollokatsiya juftliklari va ekvivalentlik</h4>${pairsTable(res.alignment.collocation_pairs)}`);
    $("corpusExportBar").style.display = "flex";
  }

  function renderSingle(d) {
    setHtml("corpusPaneOverview", statsTiles(d.stats, d.lang === "en" ? "Ingliz tili matni" : "O'zbek tili matni") +
      `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:12px">
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">UPOS taqsimoti</div>${distTable(d.stats.pos_distribution, "UPOS")}</div>
        <div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px">USAS maydonlari</div>${distTable(d.stats.usas_distribution, "Maydon")}</div>
        ${Object.entries(d.stats.feature_distribution).map(([f, v]) => `<div class="card" style="padding:10px"><div style="font-weight:700;font-size:12.5px;margin-bottom:4px;${MONO}">${esc(f)}</div>${distTable(v, "Qiymat")}</div>`).join("")}
      </div>`);
    const tt = tokenTable(d.sentences, d.lang);
    setHtml("corpusPaneTokensEn", d.lang === "en" ? tt : `<div style="color:var(--muted)">Inglizcha matn kiritilmagan.</div>`);
    setHtml("corpusPaneTokensUz", d.lang === "uz" ? tt : `<div style="color:var(--muted)">O'zbekcha matn kiritilmagan.</div>`);
    const none = `<div style="color:var(--muted)">Kollokatsiya va ekvivalentlik tahlili uchun ikkala tildagi matnni kiriting.</div>`;
    setHtml("corpusPaneCollEn", none); setHtml("corpusPaneCollUz", none); setHtml("corpusPanePairs", none);
    $("corpusExportBar").style.display = "none";
  }

  // ---------------- Eksport ----------------
  window.corpusExport = async function (fmt) {
    const en = ($("corpusEnText").value || "").trim(), uz = ($("corpusUzText").value || "").trim();
    if (!en || !uz) return;
    try {
      const r = await fetch(`${BASE()}/analyze?fmt=${encodeURIComponent(fmt)}`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_text: en, target_text: uz, min_freq: parseInt($("corpusMinFreq").value || "1", 10), span: parseInt($("corpusSpan").value || "3", 10) }) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = fmt.startsWith("conllu") ? `korpus_${fmt.replace("conllu_", "")}.conllu` : `kollokatsiya_${fmt.replace("tsv_", "")}.tsv`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { setHtml("corpusStatus", `<span style="color:var(--clay)">Eksport xatosi: ${esc(e.message)}</span>`); }
  };
  window.corpusExportJson = function () {
    if (!lastResult) return;
    const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "korpus_tahlil.json";
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  };

  // ---------------- Tagset ma'lumotnomasi ----------------
  async function renderTagset() {
    try {
      const r = await fetch(`${BASE()}/tagset`);
      const d = await r.json(); tagsetCache = d;
      const sec = (title, body) => `<details style="border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:8px;background:var(--card)"><summary style="cursor:pointer;font-weight:700;font-size:13.5px">${esc(title)}</summary><div style="margin-top:8px">${body}</div></details>`;
      let html = `<div style="font-size:12.5px;color:var(--ink-2);line-height:1.6;margin-bottom:10px">${esc(d.standards_note)}</div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:10px">Leksikon: ${esc(d.lexicon_sizes.en)} inglizcha · ${esc(d.lexicon_sizes.uz)} o'zbekcha o'zak (${esc(d.lexicon_sizes.uz_multiword)} ko'p so'zli fe'l) · ${esc(d.lexicon_sizes.bank)} kollokatsiya juftligi.</div>`;
      html += sec("UPOS — Universal Dependencies so'z turkumlari (17)", table(["Teg", "O'zbekcha", "Inglizcha", "Misol (EN)", "Misol (UZ)"], d.upos.map(u => [`<span style="${MONO}"><b>${esc(u.tag)}</b></span>`, esc(u.uz), esc(u.en), esc(u.example_en), esc(u.example_uz)])));
      html += sec("UD morfologik belgilari — o'zbek tili", table(["Belgi", "Qiymatlar", "Izoh"], d.ud_features_uz.map(f => [`<span style="${MONO}"><b>${esc(f.feat)}</b></span>`, `<span style="${MONO}">${esc(f.values.join(", "))}</span>`, esc(f.uz)])));
      html += sec("UD morfologik belgilari — ingliz tili", table(["Belgi", "Qiymatlar", "Izoh"], d.ud_features_en.map(f => [`<span style="${MONO}"><b>${esc(f.feat)}</b></span>`, `<span style="${MONO}">${esc(f.values.join(", "))}</span>`, esc(f.uz)])));
      html += sec("Penn Treebank (PTB) teglari — ingliz tili", table(["Teg", "Izoh"], d.ptb_tags.map(p => [`<span style="${MONO}"><b>${esc(p.tag)}</b></span>`, esc(p.uz)])));
      html += sec("USAS semantik maydonlari (Lancaster UCREL, 21 diskursiv maydon)", table(["Kod", "Maydon (EN)", "Maydon (UZ)", "Kichik toifalar"], d.usas_fields.map(u => [`<span style="${MONO}"><b>${esc(u.code)}</b></span>`, esc(u.en), esc(u.uz), `<span style="font-size:11.5px">${esc(u.sub.join(" · "))}</span>`])));
      html += sec("BBI kollokatsiya tiplari (Benson, Benson & Ilson): leksik L1–L7, grammatik G1–G8", table(["Kod", "Naqsh (EN)", "Naqsh (UZ)", "Misol (EN)", "Misol (UZ)"], d.bbi_types.map(b => [`<span style="${MONO}"><b>${esc(b.code)}</b></span>`, esc(b.pattern_en), esc(b.pattern_uz), esc(b.example_en), esc(b.example_uz)])));
      html += sec("Mel'čuk leksik funksiyalari (LF)", table(["LF", "Izoh", "Misol (EN)", "Misol (UZ)"], d.lexical_functions.map(l => [`<span style="${MONO}"><b>${esc(l.lf)}</b></span>`, esc(l.uz), esc(l.example_en), esc(l.example_uz)])));
      html += sec("Frazeologik kontinuum (Cowie 1981; Howarth 1998; Hausmann 1984)", table(["Kod", "Tip", "Mezon", "Misol"], d.phraseological_continuum.map(c => [`<span style="${MONO}">${esc(c.code)}</span>`, `<b>${esc(c.uz)}</b><div style="color:var(--muted);font-size:11px">${esc(c.en)}</div>`, esc(c.criteria), `${esc(c.example_en)} / ${esc(c.example_uz)}`])));
      html += sec("Statistik assotsiatsiya mezonlari", table(["Mezon", "Formula", "Manba", "Izoh"], d.association_measures.map(m => [`<b>${esc(m.name)}</b>`, `<span style="${MONO}">${esc(m.formula)}</span>`, esc(m.source), esc(m.uz)])));
      html += sec("Ekvivalentlik tiplari va tarjima protseduralari", table(["Kod", "Tip", "Mezon", "Misol"], d.equivalence_types.map(e => [`<span style="${MONO}">${esc(e.code)}</span>`, `<b>${esc(e.uz)}</b>`, esc(e.criteria), esc(e.example)])) +
        `<div style="margin-top:8px">${table(["Kod", "Protsedura", "Manba"], d.translation_procedures.map(p => [`<span style="${MONO}">${esc(p.code)}</span>`, `<b>${esc(p.uz)}</b> <span style="color:var(--muted)">(${esc(p.en)})</span>`, esc(p.source)]))}</div>`);
      html += sec(`Adabiyotlar (${d.references.length})`, `<ol style="padding-left:18px;font-size:12px;line-height:1.65;color:var(--ink-2)">${d.references.map(x => `<li>${esc(x)}</li>`).join("")}</ol>`);
      setHtml("corpusPaneTagset", html);
    } catch (e) { setHtml("corpusPaneTagset", `<div style="color:var(--clay)">Tagset yuklanmadi (${esc(e.message)})</div>`); }
  }

  // ---------------- Kollokatsiyalar banki ----------------
  async function renderBank() {
    try {
      const r = await fetch(`${BASE()}/collocations`);
      const d = await r.json(); bankCache = d;
      const sel = $("corpusBankBbi");
      if (sel && sel.options.length <= 1) d.facets.bbi.forEach(b => { const o = document.createElement("option"); o.value = b; o.textContent = b; sel.appendChild(o); });
      window.corpusFilterBank();
    } catch (e) { setHtml("corpusBankList", `<div style="color:var(--clay)">Bank yuklanmadi (${esc(e.message)})</div>`); }
  }
  window.corpusFilterBank = function () {
    if (!bankCache) return;
    const q = (($("corpusBankSearch") || {}).value || "").trim().toLowerCase();
    const bbi = ($("corpusBankBbi") || {}).value || "", eq = ($("corpusBankEq") || {}).value || "";
    const items = bankCache.items.filter(i => (!bbi || i.bbi === bbi) && (!eq || i.equivalence === eq) &&
      (!q || [i.en, i.uz, i.note, i.lf, i.usas, i.domain].some(x => (x || "").toLowerCase().includes(q))));
    setHtml("corpusBankList", `<div style="font-size:12px;color:var(--muted);margin-bottom:6px">${esc(items.length)} / ${esc(bankCache.items.length)} kollokatsiya</div>` +
      table(["#", "Ingliz", "O'zbek", "Struktur EN → UZ", "BBI", "LF", "USAS", "Kontinuum", "Ekvivalentlik", "Protsedura", "Soha", "Izoh"],
        items.map(i => [`<span style="${MONO};color:var(--muted)">${esc(i.id)}</span>`, `<b>${esc(i.en)}</b>${i.culture ? ` <span title="Lingvomadaniy" style="color:var(--clay)">◆</span>` : ""}`, esc(i.uz),
          `<span style="${MONO}">${esc(i.structure_en)} → ${esc(i.structure_uz)}</span>`, chip(i.bbi, "background:var(--teal-soft);color:var(--teal)"), esc(i.lf), `<span style="${MONO}">${esc(i.usas)}</span>`,
          esc(i.continuum), chip(EQ_LABEL[i.equivalence] || i.equivalence, EQ_STYLE[i.equivalence]), esc(i.procedure), esc(i.domain), `<span style="font-size:11.5px;color:var(--ink-2)">${esc(i.note || "")}</span>`]), 1100));
  };

  // "Platforma haqida" ekrani yuklanganda tagset va bankni oldindan tayyorlash
  const prevLoad = window.loadAboutScreen;
  window.loadAboutScreen = function () {
    if (typeof prevLoad === "function") prevLoad();
    if (!tagsetCache) renderTagset();
    if (!bankCache) renderBank();
  };
})();
