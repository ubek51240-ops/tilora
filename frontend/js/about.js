/**
 * TILORA — "Platforma haqida" (ma'lumotnoma) bo'limi va mustaqil bosqichdagi ruxsat etilgan vositalar.
 * Barcha ma'lumotlar /api/content/* dan olinadi; HTML ga faqat escapeHtml orqali kiritiladi.
 */
(function () {
  const esc = (s) => (window.escapeHtml ? window.escapeHtml(s == null ? "" : String(s)) : String(s == null ? "" : s));
  const api = () => (window.STATE && STATE.apiBaseUrl) ? STATE.apiBaseUrl : "/api";
  const authHeaders = () => (window.STATE && STATE.token) ? { "Authorization": `Bearer ${STATE.token}` } : {};
  const cache = {};

  async function getJson(path) {
    if (cache[path]) return cache[path];
    const res = await fetch(`${api()}${path}`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cache[path] = data;
    return data;
  }

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  const CAT_LABELS = {
    methodology: "Metodika", theory: "Nazariya", assessment: "Baholash", feedback: "Izoh (feedback)",
    linguistics: "Lingvistika", standards: "Standartlar", technology: "Texnologiya", affective: "Affektiv omillar",
    classroom: "Dars jarayoni", academic: "Akademik yozuv", research: "Tadqiqot"
  };

  // ---------------- Bosh sahifa ko'rsatkichlari ----------------
  async function renderOverview() {
    try {
      const o = await getJson("/content/overview");
      const tiles = [
        ["📖", o.glossary_terms, "ELT glossariy atamasi"],
        ["🧭", o.l1_patterns, "O'zbek–ingliz L1 naqshi"],
        ["🧪", o.diagnostic_questions, "Diagnostika savoli (4 ko'nikma)"],
        ["📝", o.survey_items, "FLCAS anketa bandi"],
        ["🗓️", o.curriculum_topics, "16 haftalik mavzu"],
        ["📚", o.references, "Ilmiy manba"]
      ];
      setHtml("aboutOverviewTiles", tiles.map(([ic, n, lbl]) => `
        <div style="padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2);text-align:center">
          <div style="font-size:20px">${ic}</div>
          <div style="font-size:22px;font-weight:700;color:var(--teal)">${esc(n)}</div>
          <div style="font-size:11.5px;color:var(--muted)">${esc(lbl)}</div>
        </div>`).join(""));
      const stat = document.getElementById("profileContentStat");
      if (stat) stat.textContent = `${o.glossary_terms} atama · ${o.l1_patterns} L1 naqsh · ${o.diagnostic_questions} diagnostika savoli · ${o.references} ilmiy manba`;
    } catch (e) {
      setHtml("aboutOverviewTiles", `<div style="color:var(--muted);font-size:12.5px">Ma'lumot yuklanmadi (${esc(e.message)}).</div>`);
    }
  }

  // ---------------- Metodika: 4 qoida, 5 bosqich, taqqoslash ----------------
  async function renderMethodology() {
    try {
      const m = await getJson("/content/methodology");
      setHtml("aboutProblems", (m.problem || []).map(p => `
        <div class="card" style="padding:14px">
          <div style="font-weight:700;margin-bottom:4px">${esc(p.title)}</div>
          <div style="font-size:13px;color:var(--ink-2);line-height:1.6">${esc(p.text)}</div>
        </div>`).join(""));

      setHtml("aboutRules", (m.rules || []).map(r => `
        <div class="card" style="padding:16px;border-left:4px solid var(--teal)">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <span style="background:var(--teal);color:#fff;border-radius:50%;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:13px">${esc(r.n)}</span>
            <b style="font-size:14.5px">${esc(r.title)}</b>
          </div>
          <div style="font-size:12.5px;color:var(--muted);margin-bottom:6px"><b>Asos:</b> ${esc(r.basis)}</div>
          <div style="font-size:13px;color:var(--ink-2);line-height:1.6"><b>Mexanizm:</b> ${esc(r.mechanism)}</div>
          <div style="font-family:var(--mono);font-size:11.5px;color:var(--teal);margin-top:6px">${esc(r.endpoint)}</div>
        </div>`).join(""));

      setHtml("aboutStages", `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="color:var(--muted);font-size:11.5px;text-transform:uppercase">
          <th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">#</th>
          <th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Bosqich</th>
          <th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Maqsad</th>
          <th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">AI holati</th></tr></thead>
        <tbody>${(m.stages || []).map(s => `<tr>
          <td style="padding:8px;border-bottom:1px solid var(--line-2);font-weight:700">${esc(s.n)}</td>
          <td style="padding:8px;border-bottom:1px solid var(--line-2);font-weight:600">${esc(s.name)}</td>
          <td style="padding:8px;border-bottom:1px solid var(--line-2);color:var(--ink-2)">${esc(s.goal)}</td>
          <td style="padding:8px;border-bottom:1px solid var(--line-2)"><span class="chip ${/YOPIQ/.test(s.ai) ? "full" : "none"}">${esc(s.ai)}</span></td>
        </tr>`).join("")}</tbody></table></div>`);

      setHtml("aboutDimensions", (m.profile_dimensions || []).map(d => `
        <div class="card" style="padding:14px"><div style="font-weight:700;margin-bottom:4px">${esc(d.name)}</div>
        <div style="font-size:13px;color:var(--ink-2);line-height:1.6">${esc(d.text)}</div></div>`).join(""));
      setHtml("aboutScaffolding", esc(m.scaffolding_dynamics || ""));

      setHtml("aboutComparison", `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="color:var(--muted);font-size:11.5px;text-transform:uppercase">
          <th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Xususiyat</th>
          <th style="text-align:center;padding:8px;border-bottom:1px solid var(--line)">TILORA</th>
          <th style="text-align:center;padding:8px;border-bottom:1px solid var(--line)">Umumiy AI repetitorlar</th>
          <th style="text-align:left;padding:8px;border-bottom:1px solid var(--line)">Izoh</th></tr></thead>
        <tbody>${(m.comparison || []).map(c => `<tr>
          <td style="padding:8px;border-bottom:1px solid var(--line-2)">${esc(c.feature)}</td>
          <td style="padding:8px;border-bottom:1px solid var(--line-2);text-align:center">${c.tilora ? "✅" : "—"}</td>
          <td style="padding:8px;border-bottom:1px solid var(--line-2);text-align:center">${c.generic_ai_tutors ? "✅" : "✖"}</td>
          <td style="padding:8px;border-bottom:1px solid var(--line-2);color:var(--muted);font-size:12px">${esc(c.note)}</td>
        </tr>`).join("")}</tbody></table></div>`);

      setHtml("aboutReferences", `<ol style="padding-left:20px;font-size:12.5px;line-height:1.7;color:var(--ink-2)">${(m.references || []).map(r => `<li>${esc(r)}</li>`).join("")}</ol>`);
    } catch (e) {
      setHtml("aboutRules", `<div style="color:var(--muted)">Metodika yuklanmadi (${esc(e.message)}).</div>`);
    }
  }

  // ---------------- Glossariy ----------------
  let glossaryAll = [];
  function renderGlossaryList(items) {
    if (!items.length) { setHtml("aboutGlossaryList", `<div style="color:var(--muted);font-size:13px">Hech narsa topilmadi.</div>`); return; }
    setHtml("aboutGlossaryList", items.map(t => `
      <details style="border:1px solid var(--line);border-radius:8px;padding:8px 12px;background:var(--card)">
        <summary style="cursor:pointer;font-weight:600;font-size:13.5px">${esc(t.term)} <span style="font-weight:400;color:var(--muted)">— ${esc(t.uz)}</span>
          <span class="chip none" style="font-size:10.5px;margin-left:6px">${esc(CAT_LABELS[t.category] || t.category)}</span></summary>
        <div style="font-size:13px;color:var(--ink-2);line-height:1.6;margin-top:6px">${esc(t.definition_uz)}</div>
        <div style="font-size:12px;color:var(--muted);line-height:1.5;margin-top:4px;font-style:italic">${esc(t.definition_en)}</div>
      </details>`).join(""));
  }
  async function renderGlossary() {
    try {
      const g = await getJson("/content/glossary");
      glossaryAll = g.terms || [];
      const sel = document.getElementById("aboutGlossaryCat");
      if (sel && sel.options.length <= 1) {
        (g.categories || []).forEach(c => { const o = document.createElement("option"); o.value = c; o.textContent = CAT_LABELS[c] || c; sel.appendChild(o); });
      }
      window.filterAboutGlossary();
    } catch (e) {
      setHtml("aboutGlossaryList", `<div style="color:var(--muted)">Glossariy yuklanmadi (${esc(e.message)}).</div>`);
    }
  }
  window.filterAboutGlossary = function () {
    const q = (document.getElementById("aboutGlossarySearch") || {}).value || "";
    const cat = (document.getElementById("aboutGlossaryCat") || {}).value || "";
    const ql = q.trim().toLowerCase();
    renderGlossaryList(glossaryAll.filter(t => (!cat || t.category === cat) &&
      (!ql || [t.term, t.uz, t.definition_uz, t.definition_en].some(x => (x || "").toLowerCase().includes(ql)))));
  };

  // ---------------- CEFR ----------------
  async function renderCefr() {
    try {
      const d = await getJson("/content/cefr-levels");
      setHtml("aboutCefr", (d.levels || []).map(l => `
        <details class="card" style="padding:12px 16px">
          <summary style="cursor:pointer;display:flex;align-items:center;gap:10px">
            <span style="font-family:var(--mono);font-weight:700;font-size:16px;color:var(--teal);min-width:32px">${esc(l.level)}</span>
            <b>${esc(l.name_uz)}</b> <span style="color:var(--muted);font-size:12px">(${esc(l.band)})</span>
          </summary>
          <p style="font-size:13px;color:var(--ink-2);line-height:1.65;margin:8px 0">${esc(l.global_uz)}</p>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;font-size:12.5px">
            <div><b>🎧 Tinglash:</b> ${esc(l.listening)}</div>
            <div><b>📖 O'qish:</b> ${esc(l.reading)}</div>
            <div><b>🗣️ Gapirish:</b> ${esc(l.speaking)}</div>
            <div><b>✍️ Yozish:</b> ${esc(l.writing)}</div>
          </div>
          <div style="margin-top:8px;font-size:12.5px;padding:8px 10px;background:var(--teal-soft);border-radius:6px"><b>Bo'lajak o'qituvchi uchun:</b> ${esc(l.teacher_track)}</div>
          <div style="font-size:11.5px;color:var(--muted);margin-top:6px;font-style:italic">${esc(l.global_en)}</div>
        </details>`).join("") + `<div style="font-size:11.5px;color:var(--muted);margin-top:6px">Manba: ${esc(d.source)}</div>`);
    } catch (e) {
      setHtml("aboutCefr", `<div style="color:var(--muted)">CEFR yuklanmadi (${esc(e.message)}).</div>`);
    }
  }

  // ---------------- L1 naqshlari ----------------
  async function renderL1() {
    try {
      const d = await getJson("/content/l1-patterns");
      setHtml("aboutL1", `<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12.5px">
        <thead><tr style="color:var(--muted);font-size:11px;text-transform:uppercase">
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)">#</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)">Xato</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)">Sabab (L1 ta'siri)</th>
          <th style="text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)">Noto'g'ri → To'g'ri</th></tr></thead>
        <tbody>${(d.patterns || []).map((p, i) => `<tr>
          <td style="padding:6px 8px;border-bottom:1px solid var(--line-2);color:var(--muted)">${i + 1}</td>
          <td style="padding:6px 8px;border-bottom:1px solid var(--line-2);font-weight:600">${esc(p.issue_short)}<br><span class="chip ${p.category === "grammar" ? "part" : "none"}" style="font-size:10px">${esc(p.category)}</span></td>
          <td style="padding:6px 8px;border-bottom:1px solid var(--line-2);color:var(--ink-2);line-height:1.5">${esc(p.issue_reason)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid var(--line-2)"><span style="color:var(--clay);text-decoration:line-through">${esc(p.example_wrong)}</span><br><span style="color:var(--teal);font-weight:600">${esc(p.example_right)}</span></td>
        </tr>`).join("")}</tbody></table></div>`);
    } catch (e) {
      setHtml("aboutL1", `<div style="color:var(--muted)">L1 naqshlari yuklanmadi (${esc(e.message)}).</div>`);
    }
  }

  // ---------------- FAQ ----------------
  async function renderFaq() {
    try {
      const d = await getJson("/content/faq");
      const label = { student: "Talaba", teacher: "O'qituvchi", researcher: "Tadqiqotchi", all: "Hamma" };
      setHtml("aboutFaq", (d.items || []).map(f => `
        <details style="border:1px solid var(--line);border-radius:8px;padding:10px 14px;background:var(--card)">
          <summary style="cursor:pointer;font-weight:600;font-size:13.5px"><span class="chip none" style="font-size:10px;margin-right:6px">${esc(label[f.audience] || f.audience)}</span>${esc(f.q)}</summary>
          <div style="font-size:13px;color:var(--ink-2);line-height:1.65;margin-top:8px">${esc(f.a)}</div>
        </details>`).join(""));
    } catch (e) {
      setHtml("aboutFaq", `<div style="color:var(--muted)">FAQ yuklanmadi (${esc(e.message)}).</div>`);
    }
  }

  // Profil sahifasidagi kontent banki satri (hamma uchun, sahifa yuklanganda)
  document.addEventListener("DOMContentLoaded", renderOverview);

  let aboutLoaded = false;
  window.loadAboutScreen = function () {
    if (aboutLoaded) return;
    aboutLoaded = true;
    renderOverview(); renderMethodology(); renderGlossary(); renderCefr(); renderL1(); renderFaq();
  };
  window.scrollAboutTo = function (id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // ---------------- 3-bosqich: ruxsat etilgan vositalar (1-qoida) ----------------
  function toolBox(html) {
    const box = document.getElementById("allowedToolsOutput");
    if (!box) return;
    box.style.display = "block";
    box.innerHTML = html;
  }
  window.showTaskPromptTool = async function () {
    const skill = (document.querySelector(".skill-tab-btn.active") || {}).getAttribute?.("data-skill") || "writing";
    try {
      const t = await getJson(`/lesson/5/task?skill=${encodeURIComponent(skill)}`);
      toolBox(`<b>📋 ${esc(t.title)}</b><div style="margin:6px 0;line-height:1.6">${esc(t.prompt)}</div>
        ${t.word_count_min ? `<div style="font-size:12px;color:var(--muted)">So'z chegarasi: ${esc(t.word_count_min)}–${esc(t.word_count_max)} · Vaqt: ${esc(t.duration_minutes)} daqiqa</div>` : ""}
        ${(t.sample_structure || []).length ? `<div style="margin-top:8px;font-size:12.5px"><b>Tavsiya etilgan tuzilma:</b><ol style="padding-left:18px;margin:4px 0">${t.sample_structure.map(s => `<li>${esc(s)}</li>`).join("")}</ol></div>` : ""}
        ${(t.scaffold_vocabulary || []).length ? `<div style="margin-top:8px;font-size:12.5px"><b>Kalit terminlar:</b> ${t.scaffold_vocabulary.map(v => `<code>${esc(v.term)}</code> — ${esc(v.uz)}`).join("; ")}</div>` : ""}`);
    } catch (e) {
      toolBox(`Topshiriq sharti yuklanmadi (${esc(e.message)}).`);
    }
  };
  window.showGlossaryTool = async function () {
    try {
      const g = await getJson("/student/glossary");
      toolBox(`<b>📖 Shaxsiy glossariy (${esc(g.total)} atama)</b>
        <input type="text" id="toolGlossaryQ" placeholder="Atama qidirish..." oninput="window.filterGlossaryTool()" style="width:100%;margin:8px 0;padding:7px 10px;border:1px solid var(--line);border-radius:6px;font-size:12.5px">
        <div id="toolGlossaryList" style="max-height:260px;overflow-y:auto;display:flex;flex-direction:column;gap:6px"></div>`);
      window._toolGlossary = g.terms || [];
      window.filterGlossaryTool();
    } catch (e) {
      toolBox(`Glossariy yuklanmadi (${esc(e.message)}).`);
    }
  };
  window.filterGlossaryTool = function () {
    const q = ((document.getElementById("toolGlossaryQ") || {}).value || "").toLowerCase();
    const list = (window._toolGlossary || []).filter(t => !q || t.term.toLowerCase().includes(q) || (t.uz || "").toLowerCase().includes(q));
    setHtml("toolGlossaryList", list.slice(0, 60).map(t => `<div style="font-size:12.5px;line-height:1.5"><b>${esc(t.term)}</b> <span style="color:var(--muted)">(${esc(t.uz)})</span> — ${esc(t.definition)}</div>`).join("") || `<div style="color:var(--muted)">Topilmadi.</div>`);
  };
  window.showArchiveTool = async function () {
    if (!(window.STATE && STATE.token)) { toolBox("Arxivni ko'rish uchun tizimga kiring."); return; }
    try {
      const d = await getJson("/student/previous-works");
      const works = d.works || [];
      toolBox(`<b>🗂️ Oldingi ishlaringiz (${esc(works.length)})</b>` + (works.length
        ? `<table style="width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px"><tbody>${works.map(w => `<tr>
            <td style="padding:4px 6px;border-bottom:1px solid var(--line-2)">${esc(w.date)}</td>
            <td style="padding:4px 6px;border-bottom:1px solid var(--line-2)">${esc(w.title || w.topic)}</td>
            <td style="padding:4px 6px;border-bottom:1px solid var(--line-2);text-align:right;font-weight:700;color:${w.passed ? "var(--teal)" : "var(--clay)"}">${w.score == null ? "—" : esc(w.score) + "%"}</td>
          </tr>`).join("")}</tbody></table>`
        : `<div style="color:var(--muted);margin-top:6px">Hali topshirilgan ish yo'q. "O'quv fanlari & Testlar" bo'limidagi topshiriqlar shu yerda ko'rinadi.</div>`));
    } catch (e) {
      toolBox(`Arxiv yuklanmadi (${esc(e.message)}).`);
    }
  };
})();
