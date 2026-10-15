/* ============================================================
   TILORA — O'qituvchi kuzatuv paneli (teacher_panel.js)
   Dissertatsiya 3.3: "O'qituvchi paneli guruh va alohida talaba bo'yicha
   ma'lumotni ko'rsatadi hamda topshiriq variantini o'zgartirish imkonini beradi".
   4.1: kuzatuv varaqasi (jarayon ko'rsatkichlari).
   Backend: GET/POST/DELETE /api/teacher/panel/*  (rollar: teacher, admin)
   Global: window.loadTeacherPanel()
   ============================================================ */
(function () {
  'use strict';

  const esc = (s) => (typeof window.escapeHtml === 'function' ? window.escapeHtml(s) : String(s == null ? '' : s));
  const arg = (v) => (typeof window.jsArg === 'function' ? window.jsArg(v) : esc(JSON.stringify(String(v == null ? '' : v))));
  const toast = (m, t) => { if (typeof window.showToast === 'function') window.showToast(m, t || 'info'); };

  const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
  const SKILL_LABELS = { listening: 'Tinglash', reading: "O'qish", speaking: "Og'zaki", writing: 'Yozma' };
  const SKILL_SHORT = { listening: 'L', reading: 'R', speaking: 'S', writing: 'W' };
  const VARIANT_COLOR = { A: 'var(--teal)', B: 'var(--amber)', C: 'var(--clay)' };
  const VARIANT_BG = { A: 'var(--teal-soft)', B: 'var(--amber-soft)', C: 'var(--clay-soft, #F6E7E2)' };
  const ARM_LABEL = { experimental: 'Tajriba', control: 'Nazorat' };

  // Panel holati
  const TP = {
    groups: [], groupId: null, group: null,
    tab: 'students',
    students: null, diff: null, obs: null, records: null,
    recordsStudentId: null,
    overrideFor: null,          // profil tuzatish formasi ochiq talaba id
    noteFor: null,              // {id, variant} — variant biriktirish izohi formasi
    busy: false,
  };

  // ---------- API ----------
  function apiBase() { return (window.STATE && window.STATE.apiBaseUrl) ? window.STATE.apiBaseUrl : '/api'; }
  function token() { return (window.STATE && window.STATE.token) ? window.STATE.token : (localStorage.getItem('tilora_token') || ''); }
  function role() { return (window.STATE && window.STATE.currentUser) ? (window.STATE.currentUser.role || '') : ''; }

  function detailText(data, status) {
    if (!data) return 'HTTP ' + status;
    const d = data.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map(x => ((x.loc && x.loc.length) ? x.loc[x.loc.length - 1] + ': ' : '') + (x.msg || '')).join('; ');
    return data.message || ('HTTP ' + status);
  }

  async function req(path, opts) {
    opts = opts || {};
    const headers = { 'Authorization': 'Bearer ' + token() };
    let body;
    if (opts.body !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(opts.body); }
    const res = await fetch(apiBase() + path, { method: opts.method || 'GET', headers, body });
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const err = new Error(detailText(data, res.status));
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // ---------- Yordamchilar ----------
  function root() { return document.getElementById('teacherPanelRoot'); }
  function armLabel(arm) { return ARM_LABEL[arm] || "Qanot belgilanmagan"; }
  function armChip(arm) {
    if (arm === 'experimental') return '<span class="chip none">Tajriba</span>';
    if (arm === 'control') return '<span class="chip part">Nazorat</span>';
    return '<span class="chip" style="background:var(--surface-2);color:var(--muted);border-color:var(--line)">Qanot yo\'q</span>';
  }
  function fmt(v, d) { return (v === null || v === undefined || v === '') ? '—' : (typeof v === 'number' && d !== undefined ? v.toFixed(d) : String(v)); }
  function mean(arr) { const a = arr.filter(x => typeof x === 'number' && !isNaN(x)); return a.length ? a.reduce((s, x) => s + x, 0) / a.length : null; }
  function overallOf(block) {
    if (!block) return null;
    if (typeof block.overall === 'number') return block.overall;
    return mean(['listening', 'reading', 'speaking', 'writing'].map(k => block[k]));
  }

  function variantBadge(v, source, reason, sys) {
    const vv = v || '—';
    const src = source === 'teacher' ? "o'qituvchi" : 'tizim';
    const sysTxt = (source === 'teacher' && sys && sys !== v) ? ' · tizim taklifi: ' + esc(sys) : '';
    return '<span style="display:inline-flex;align-items:center;gap:5px;white-space:nowrap">'
      + '<span style="display:inline-block;min-width:22px;text-align:center;padding:2px 7px;border-radius:7px;font-weight:800;font-size:12.5px;color:' + VARIANT_COLOR[vv] + ';background:' + VARIANT_BG[vv] + ';border:1px solid ' + VARIANT_COLOR[vv] + '">' + esc(vv) + '</span>'
      + '<span style="font-size:11px;color:var(--muted)">' + esc(src) + sysTxt + '</span>'
      + (reason ? '<span title="' + esc(reason) + '" style="cursor:help;font-size:12px">ℹ️</span>' : '')
      + '</span>';
  }

  function cefrChips(cefr) {
    if (!cefr) return '<span style="font-size:12px;color:var(--muted)">Profil yo\'q</span>';
    return '<div style="display:flex;gap:4px;flex-wrap:wrap">' + ['listening', 'reading', 'speaking', 'writing'].map(k =>
      '<span class="chip" title="' + esc(SKILL_LABELS[k]) + '" style="background:var(--teal-soft);color:var(--teal);border-color:#BCD9D3;padding:2px 7px;font-weight:600">' + SKILL_SHORT[k] + ' ' + esc(cefr[k] || '—') + '</span>'
    ).join('') + '</div>';
  }

  function miniBar(label, val, warnHigh) {
    const v = (typeof val === 'number') ? Math.max(0, Math.min(100, val)) : null;
    const warn = warnHigh && v !== null && v > 75;
    return '<div style="display:flex;align-items:center;gap:6px;font-size:11px;line-height:1.3;white-space:nowrap">'
      + '<span style="width:76px;color:var(--muted)">' + esc(label) + '</span>'
      + '<span class="track" style="width:70px;flex:0 0 70px"><span class="fill' + (warn ? ' warn' : '') + '" style="display:block;width:' + (v === null ? 0 : v) + '%"></span></span>'
      + '<span style="width:28px;text-align:right;font-weight:600;color:' + (warn ? 'var(--clay)' : 'var(--ink)') + '">' + (v === null ? '—' : v) + '</span></div>';
  }

  function profileBars(p) {
    if (!p) return '<span style="font-size:12px;color:var(--muted)">—</span>';
    return '<div style="display:flex;flex-direction:column;gap:3px">'
      + miniBar('Tashvish', p.anxiety_level, true)
      + miniBar("Yuklama sig'imi", p.load_capacity, false)
      + miniBar("Sur'at", p.pace_index, false)
      + miniBar('Mustaqillik', p.autonomy_readiness, false)
      + '</div>';
  }

  function btn(label, onclick, style) {
    return '<button class="btn-primary" onclick="' + onclick + '" style="padding:6px 11px;font-size:12px;' + (style || '') + '">' + label + '</button>';
  }
  function ghostStyle() { return 'background:var(--surface-2);color:var(--ink);border:1px solid var(--line);'; }
  const TH = 'padding:8px 10px;white-space:nowrap;font-size:12px;text-align:left';
  const TD = 'padding:8px 10px;vertical-align:top;font-size:13px';

  function loadingBox(txt) { return '<div style="text-align:center;padding:26px;color:var(--muted)">' + esc(txt || 'Yuklanmoqda...') + '</div>'; }
  function errorBox(msg) { return '<div class="why-box" style="margin-top:0;color:var(--clay)"><b>Xatolik</b>' + esc(msg) + '</div>'; }

  // ---------- Asosiy kirish ----------
  window.loadTeacherPanel = async function () {
    const r = root();
    if (!r) return;
    const rl = role();
    if (!token() || !(rl === 'teacher' || rl === 'admin')) {
      r.innerHTML = '<div class="card" style="text-align:center;padding:30px">'
        + '<div style="font-size:32px;margin-bottom:8px">🧭</div>'
        + '<h3 style="font-family:var(--serif);font-size:18px;text-transform:none;letter-spacing:0;margin-bottom:6px">Guruh kuzatuv paneli</h3>'
        + '<p style="font-size:13.5px;color:var(--muted);margin:0 0 12px">Bu bo\'lim faqat <b>o\'qituvchi</b> yoki <b>administrator</b> roli uchun ochiq. '
        + (token() ? 'Sizning rolingiz: <b>' + esc(rl || 'noma\'lum') + '</b>.' : 'Iltimos, avval tizimga kiring.') + '</p>'
        + (token() ? '' : btn('Kirish', 'window.openLoginModal && window.openLoginModal()'))
        + '</div>';
      return;
    }
    r.innerHTML = loadingBox('Kuzatuv paneli yuklanmoqda...');
    try {
      const data = await req('/teacher/panel/groups');
      TP.groups = data.groups || [];
      if (!TP.groupId || !TP.groups.some(g => g.id === TP.groupId)) {
        const mine = TP.groups.find(g => g.is_mine) || TP.groups[0];
        TP.groupId = mine ? mine.id : null;
      }
      TP.group = TP.groups.find(g => g.id === TP.groupId) || null;
      renderShell();
      await loadTab();
    } catch (e) {
      r.innerHTML = errorBox('Guruhlarni yuklab bo\'lmadi: ' + e.message);
    }
  };

  window.tpSelectGroup = async function (gid) {
    TP.groupId = gid || null;
    TP.group = TP.groups.find(g => g.id === gid) || null;
    TP.students = TP.diff = TP.obs = null;
    TP.overrideFor = TP.noteFor = null;
    if (TP.tab === 'records') TP.tab = 'students';
    renderShell();
    await loadTab();
  };

  window.tpSwitchTab = async function (tab) {
    TP.tab = tab;
    renderShell();
    await loadTab();
  };

  window.tpRefresh = async function () {
    TP.students = TP.diff = TP.obs = TP.records = null;
    await loadTab(true);
  };

  // ---------- Qobiq: sarlavha + guruh tanlash + tablar ----------
  function renderShell() {
    const r = root();
    if (!r) return;
    const g = TP.group;
    const tabs = [
      ['students', "👥 Talabalar (3 o'lchovli profil)"],
      ['diff', '🧩 Tabaqalashtirish (A/B/C)'],
      ['obs', '📋 Kuzatuv varaqasi'],
      ['records', '📝 Talaba yozuvlari'],
    ];
    let html = '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:14px">'
      + '<div><h2 style="font-family:var(--serif);font-size:24px;margin-bottom:4px">🧭 Guruh kuzatuv paneli</h2>'
      + '<p style="font-size:13.5px;color:var(--muted);margin:0">Guruh va alohida talaba bo\'yicha uch o\'lchovli profil, tabaqalashtirish (A/B/C) va kuzatuv varaqasi. Tizim variantni <b>taklif</b> qiladi, yakuniy qaror — o\'qituvchida (3-qoida).</p></div>'
      + btn('🔄 Yangilash', 'window.tpRefresh()', ghostStyle())
      + '</div>';

    // Guruh tanlash
    html += '<div class="card" style="padding:14px;margin-bottom:14px">'
      + '<div style="font-size:11.5px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px">Guruh tanlang</div>';
    if (!TP.groups.length) {
      html += '<p style="font-size:13px;color:var(--muted);margin:0">Sizga biriktirilgan guruhlar topilmadi. Administrator guruhga o\'qituvchi sifatida biriktirishi yoki fan nomi guruh nomiga mos kelishi kerak.</p>';
    } else {
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap">';
      TP.groups.forEach(gr => {
        const active = gr.id === TP.groupId;
        html += '<button onclick="window.tpSelectGroup(' + arg(gr.id) + ')" style="cursor:pointer;border-radius:10px;padding:8px 12px;text-align:left;border:1.5px solid ' + (active ? 'var(--teal)' : 'var(--line)') + ';background:' + (active ? 'var(--teal-soft)' : 'var(--surface-2)') + ';color:var(--ink);min-width:150px">'
          + '<div style="font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">' + esc(gr.name) + (gr.is_mine ? '<span class="chip none" style="padding:1px 7px">mening</span>' : '') + '</div>'
          + '<div style="font-size:11.5px;color:var(--muted);margin-top:3px;display:flex;gap:6px;align-items:center;flex-wrap:wrap">' + armChip(gr.arm) + '<span>' + esc(gr.students_count) + ' talaba · ' + esc(gr.records) + ' yozuv' + (gr.course_year ? ' · ' + esc(gr.course_year) + '-kurs' : '') + '</span></div>'
          + '</button>';
      });
      html += '</div>';
    }
    html += '</div>';

    // Tablar
    html += '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;border-bottom:1.5px solid var(--line);padding-bottom:8px">';
    tabs.forEach(([k, label]) => {
      const active = TP.tab === k;
      html += '<button class="res-tab-btn' + (active ? ' active' : '') + '" onclick="window.tpSwitchTab(' + arg(k) + ')" style="' + (active ? 'background:var(--teal);color:#fff;border-color:var(--teal)' : '') + '">' + esc(label) + '</button>';
    });
    html += '</div>';

    html += '<div id="tpTabContent">' + loadingBox() + '</div>';
    r.innerHTML = html;
  }

  function content() { return document.getElementById('tpTabContent'); }

  async function loadTab(force) {
    const c = content();
    if (!c) return;
    try {
      if (TP.tab === 'students') {
        if (!TP.groupId) { c.innerHTML = loadingBox('Avval guruhni tanlang.'); return; }
        if (!TP.students || force) { c.innerHTML = loadingBox(); TP.students = await req('/teacher/panel/groups/' + encodeURIComponent(TP.groupId) + '/students'); }
        renderStudents();
      } else if (TP.tab === 'diff') {
        if (!TP.groupId) { c.innerHTML = loadingBox('Avval guruhni tanlang.'); return; }
        if (!TP.diff || force) { c.innerHTML = loadingBox(); TP.diff = await req('/teacher/panel/groups/' + encodeURIComponent(TP.groupId) + '/differentiation'); }
        renderDiff();
      } else if (TP.tab === 'obs') {
        if (!TP.obs || force) { c.innerHTML = loadingBox(); TP.obs = await req('/teacher/panel/observation' + (TP.groupId ? '?group_id=' + encodeURIComponent(TP.groupId) : '')); }
        renderObservation();
      } else if (TP.tab === 'records') {
        if (!TP.recordsStudentId) { c.innerHTML = '<div class="card" style="text-align:center;color:var(--muted);padding:26px">Talabani tanlang: «Talabalar» yoki «Kuzatuv varaqasi» bo\'limida <b>Yozuvlar</b> tugmasini bosing.</div>'; return; }
        if (!TP.records || TP.records.student.id !== TP.recordsStudentId || force) { c.innerHTML = loadingBox(); TP.records = await req('/teacher/panel/students/' + encodeURIComponent(TP.recordsStudentId) + '/records'); }
        renderRecords();
      }
    } catch (e) {
      c.innerHTML = errorBox(e.message);
    }
  }

  // ---------- 1-TAB: Talabalar ----------
  function renderStudents() {
    const c = content();
    const d = TP.students;
    if (!c || !d) return;
    const g = d.group || {};
    let html = '<div class="card" style="padding:16px">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">'
      + '<div style="font-weight:700;font-size:14px">' + esc(g.name || '') + ' ' + armChip(g.arm) + ' <span style="font-size:12px;color:var(--muted);font-weight:400">' + esc(d.total || (d.students || []).length) + ' talaba</span></div>'
      + '<span style="font-size:12px;color:var(--muted)">Pre → Post: to\'rt ko\'nikma o\'rtachasi (0–100)</span></div>';
    if (!(d.students || []).length) {
      html += '<p style="color:var(--muted);font-size:13px;margin:0">Guruhda tasdiqlangan talabalar yo\'q.</p></div>';
      c.innerHTML = html; return;
    }
    html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;min-width:900px">'
      + '<thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">'
      + '<th style="' + TH + '">Talaba</th><th style="' + TH + '">CEFR</th><th style="' + TH + '">Affektiv / kognitiv</th><th style="' + TH + '">Variant</th><th style="' + TH + ';text-align:center">Pre → Post</th><th style="' + TH + ';text-align:center">Mashg\'ulotlar</th><th style="' + TH + '">Amallar</th>'
      + '</tr></thead><tbody>';
    d.students.forEach(s => {
      const p = s.profile;
      const pre = overallOf((s.assessments || {}).pre), post = overallOf((s.assessments || {}).post);
      let pp = '—';
      if (pre !== null || post !== null) {
        const diff = (pre !== null && post !== null) ? post - pre : null;
        pp = '<span>' + (pre === null ? '—' : pre.toFixed(0)) + ' → <b>' + (post === null ? '—' : post.toFixed(0)) + '</b></span>'
          + (diff === null ? '' : '<div style="font-size:11.5px;font-weight:700;color:' + (diff >= 0 ? '#16A34A' : 'var(--clay)') + '">' + (diff >= 0 ? '+' : '') + diff.toFixed(0) + '</div>');
      }
      const L = s.lessons || {};
      html += '<tr style="border-bottom:1px solid var(--line)">'
        + '<td style="' + TD + '"><div style="font-weight:600">' + esc(s.full_name) + '</div><div style="font-size:11.5px;color:var(--muted)">' + esc(s.email) + '</div>'
        + (p ? '<div style="font-size:11px;color:var(--muted);margin-top:2px">Profil: ' + esc(p.source === 'teacher_override' ? "o'qituvchi tuzatgan" : p.source) + (p.valid_from ? ' · ' + esc(p.valid_from) : '') + '</div>' : '') + '</td>'
        + '<td style="' + TD + '">' + cefrChips(p ? p.cefr : null) + '</td>'
        + '<td style="' + TD + '">' + profileBars(p) + '</td>'
        + '<td style="' + TD + '">' + variantBadge(s.variant, s.variant_source, s.variant_reason, s.system_suggestion) + '</td>'
        + '<td style="' + TD + ';text-align:center">' + pp + '</td>'
        + '<td style="' + TD + ';text-align:center"><div><b>' + esc(L.count || 0) + '</b> ta' + (L.avg_score !== null && L.avg_score !== undefined ? ' · o\'rt. <b>' + esc(L.avg_score) + '</b>' : '') + '</div>'
        + '<div style="font-size:11px;color:var(--muted)">' + (L.last ? 'oxirgi: ' + esc(L.last) : 'hali yo\'q') + (L.avg_rating_gap !== null && L.avg_rating_gap !== undefined ? ' · farq ' + esc(L.avg_rating_gap) : '') + (L.help_requests ? ' · yordam ' + esc(L.help_requests) : '') + '</div></td>'
        + '<td style="' + TD + '"><div style="display:flex;gap:6px;flex-wrap:wrap">'
        + btn('📝 Yozuvlar', 'window.tpOpenRecords(' + arg(s.id) + ')')
        + btn(TP.overrideFor === s.id ? '✖ Yopish' : '🛠 Profilni tuzatish', 'window.tpToggleOverride(' + arg(s.id) + ')', ghostStyle())
        + '</div></td></tr>';
      if (TP.overrideFor === s.id) {
        html += '<tr style="border-bottom:1.5px solid var(--line);background:var(--surface-2)"><td colspan="7" style="padding:12px 14px">' + overrideForm(s) + '</td></tr>';
      }
    });
    html += '</tbody></table></div></div>';
    c.innerHTML = html;
  }

  function overrideForm(s) {
    const p = s.profile || { cefr: {} };
    const cefr = p.cefr || {};
    const sel = (key, cur) => '<label style="font-size:11.5px;font-weight:600;display:flex;flex-direction:column;gap:3px">' + esc(SKILL_LABELS[key]) + '<select id="tpOv_cefr_' + key + '" style="padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:12.5px">'
      + CEFR_LEVELS.map(l => '<option value="' + l + '"' + (l === cur ? ' selected' : '') + '>' + l + '</option>').join('') + '</select></label>';
    const num = (key, label, cur) => '<label style="font-size:11.5px;font-weight:600;display:flex;flex-direction:column;gap:3px">' + esc(label) + ' (0–100)<input type="number" min="0" max="100" id="tpOv_' + key + '" value="' + esc(cur === null || cur === undefined ? '' : cur) + '" style="padding:6px 8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:12.5px;width:100%;box-sizing:border-box"></label>';
    return '<div style="font-weight:700;font-size:13px;margin-bottom:6px">🛠 Profilni qo\'lda tuzatish — ' + esc(s.full_name) + '</div>'
      + '<p style="font-size:12px;color:var(--muted);margin:0 0 10px">Yangi profil qatori <b>teacher_override</b> manbasi bilan saqlanadi, eski qator o\'chirilmaydi (tarix). Sabab (izoh) majburiy — 2-qoida.</p>'
      + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:8px">'
      + sel('listening', cefr.listening || 'B1') + sel('reading', cefr.reading || 'B1') + sel('speaking', cefr.speaking || 'A2') + sel('writing', cefr.writing || 'B1')
      + '</div>'
      + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:8px">'
      + num('anxiety_level', 'Tashvish', p.anxiety_level) + num('load_capacity', "Yuklama sig'imi", p.load_capacity) + num('pace_index', "Sur'at", p.pace_index) + num('autonomy_readiness', 'Mustaqillik', p.autonomy_readiness)
      + '</div>'
      + '<label style="font-size:11.5px;font-weight:600;display:block;margin-bottom:8px">Sabab / izoh <span style="color:var(--clay)">*</span> (kamida 3 belgi)'
      + '<textarea id="tpOv_note" rows="2" placeholder="Masalan: Og\'zaki javoblar B1 dan yuqori; darsdagi kuzatuv asosida tuzatildi" style="width:100%;box-sizing:border-box;margin-top:3px;padding:8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:12.5px;font-family:inherit"></textarea></label>'
      + '<div id="tpOvError" style="display:none;margin-bottom:8px;font-size:12.5px;color:var(--clay)"></div>'
      + '<div style="display:flex;gap:8px;flex-wrap:wrap">' + btn('💾 Saqlash', 'window.tpSubmitOverride(' + arg(s.id) + ')') + btn('Bekor qilish', 'window.tpToggleOverride(' + arg(s.id) + ')', ghostStyle()) + '</div>';
  }

  window.tpToggleOverride = function (sid) {
    TP.overrideFor = (TP.overrideFor === sid) ? null : sid;
    renderStudents();
  };

  window.tpSubmitOverride = async function (sid) {
    if (TP.busy) return;
    const errBox = document.getElementById('tpOvError');
    const showErr = (m) => { if (errBox) { errBox.style.display = 'block'; errBox.textContent = m; } toast(m, 'error'); };
    const note = (document.getElementById('tpOv_note') || {}).value || '';
    if (note.trim().length < 3) { showErr('Izoh majburiy (kamida 3 belgi).'); return; }
    const payload = { note: note.trim() };
    ['listening', 'reading', 'speaking', 'writing'].forEach(k => { const el = document.getElementById('tpOv_cefr_' + k); if (el && el.value) payload['cefr_' + k] = el.value; });
    let bad = null;
    ['anxiety_level', 'load_capacity', 'pace_index', 'autonomy_readiness'].forEach(k => {
      const el = document.getElementById('tpOv_' + k);
      if (!el || el.value === '') return;
      const n = Number(el.value);
      if (isNaN(n) || n < 0 || n > 100) { bad = k; return; }
      payload[k] = Math.round(n);
    });
    if (bad) { showErr('Qiymat 0–100 oralig\'ida bo\'lishi kerak: ' + bad); return; }
    TP.busy = true;
    try {
      const res = await req('/teacher/panel/students/' + encodeURIComponent(sid) + '/profile-override', { method: 'POST', body: payload });
      toast(res.message || 'Profil yangilandi.', 'success');
      TP.overrideFor = null;
      TP.students = null; TP.diff = null;
      await loadTab(true);
    } catch (e) {
      showErr((e.status === 422 || e.status === 400) ? 'Tekshiruv xatosi: ' + e.message : e.message);
    } finally { TP.busy = false; }
  };

  // ---------- 2-TAB: Tabaqalashtirish ----------
  function renderDiff() {
    const c = content();
    const d = TP.diff;
    if (!c || !d) return;
    const labels = d.labels || {};
    const counts = d.counts || {};
    let html = '<div class="why-box" style="margin:0 0 14px"><b>Tabaqalashtirish qoidasi</b>' + esc(d.rule_note || '') + '</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px">';
    ['A', 'B', 'C'].forEach(k => {
      const lab = labels[k] || {};
      const list = (d.subgroups && d.subgroups[k]) || [];
      html += '<div class="card" style="padding:14px;border-top:4px solid ' + VARIANT_COLOR[k] + '">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px">'
        + '<div style="font-weight:800;font-size:14px;color:' + VARIANT_COLOR[k] + '">' + esc(lab.name || k) + '</div>'
        + '<span class="chip" style="background:' + VARIANT_BG[k] + ';color:' + VARIANT_COLOR[k] + ';border-color:' + VARIANT_COLOR[k] + ';font-weight:700">' + esc(counts[k] !== undefined ? counts[k] : list.length) + ' talaba</span></div>'
        + '<div style="font-size:12px;color:var(--muted);margin-bottom:10px">' + esc(lab.desc || '') + ' <span class="chip ' + esc(lab.scaffold === 'full' ? 'full' : (lab.scaffold === 'partial' ? 'part' : 'none')) + '">ko\'mak: ' + esc(lab.scaffold || '') + '</span></div>';
      if (!list.length) html += '<div style="font-size:12.5px;color:var(--muted);padding:10px;border:1px dashed var(--line);border-radius:8px;text-align:center">Bu variantda talaba yo\'q</div>';
      list.forEach(s => { html += diffCard(s, k); });
      html += '</div>';
    });
    html += '</div>';
    c.innerHTML = html;
  }

  function diffCard(s, k) {
    const cefr = s.cefr || {};
    const noteOpen = TP.noteFor && TP.noteFor.id === s.id;
    let html = '<div style="border:1px solid var(--line);border-radius:9px;padding:10px;margin-bottom:8px;background:var(--surface)">'
      + '<div style="display:flex;justify-content:space-between;gap:6px;align-items:flex-start;flex-wrap:wrap">'
      + '<div style="font-weight:700;font-size:13px">' + esc(s.full_name) + '</div>'
      + '<span style="font-size:11px;color:var(--muted)">' + (s.source === 'teacher' ? "o'qituvchi biriktirgan" : 'tizim taklifi') + (s.source === 'teacher' && s.system_suggestion && s.system_suggestion !== s.variant ? ' (tizim: ' + esc(s.system_suggestion) + ')' : '') + '</span></div>'
      + '<div style="display:flex;gap:4px;flex-wrap:wrap;margin:6px 0;font-size:11px">'
      + ['listening', 'reading', 'speaking', 'writing'].map(x => '<span class="chip" style="background:var(--teal-soft);color:var(--teal);border-color:#BCD9D3;padding:1px 6px">' + SKILL_SHORT[x] + ' ' + esc(cefr[x] || '—') + '</span>').join('')
      + '<span class="chip" style="background:var(--surface-2);color:var(--ink);border-color:var(--line);padding:1px 6px">daraja ' + esc(fmt(s.level_score)) + '/6</span></div>'
      + '<div style="font-size:11.5px;color:var(--muted)">Tashvish <b style="color:' + (s.anxiety > 75 ? 'var(--clay)' : 'var(--ink)') + '">' + esc(fmt(s.anxiety)) + '</b> · Mustaqillik <b>' + esc(fmt(s.autonomy)) + '</b> · Yuklama <b>' + esc(fmt(s.load)) + '</b></div>'
      + '<div style="font-size:11.5px;color:var(--ink-2);margin-top:5px;line-height:1.45">' + esc(s.reason || '') + '</div>'
      + '<div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:8px;align-items:center">';
    ['A', 'B', 'C'].forEach(v => {
      const cur = v === s.variant;
      html += '<button ' + (cur ? 'disabled' : 'onclick="window.tpAskVariant(' + arg(s.id) + ',' + arg(v) + ')"') + ' title="' + esc((TP.diff && TP.diff.labels && TP.diff.labels[v]) ? TP.diff.labels[v].name : v) + '" style="cursor:' + (cur ? 'default' : 'pointer') + ';min-width:34px;padding:4px 9px;border-radius:7px;font-weight:800;font-size:12.5px;border:1.5px solid ' + VARIANT_COLOR[v] + ';background:' + (cur ? VARIANT_COLOR[v] : VARIANT_BG[v]) + ';color:' + (cur ? '#fff' : VARIANT_COLOR[v]) + '">' + v + '</button>';
    });
    if (s.source === 'teacher') {
      html += '<button onclick="window.tpClearVariant(' + arg(s.id) + ')" style="cursor:pointer;font-size:11.5px;padding:4px 9px;border-radius:7px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink)">↩ Tizim taklifiga qaytarish</button>';
    }
    html += '<button onclick="window.tpOpenRecords(' + arg(s.id) + ')" style="cursor:pointer;font-size:11.5px;padding:4px 9px;border-radius:7px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink)">📝 Yozuvlar</button>';
    html += '</div>';
    if (noteOpen) {
      html += '<div style="margin-top:8px;padding:8px;border-radius:8px;background:var(--amber-soft);border:1px solid #E7D9AE">'
        + '<div style="font-size:12px;font-weight:700;margin-bottom:4px">' + esc(s.full_name) + ' → <span style="color:' + VARIANT_COLOR[TP.noteFor.variant] + '">' + esc(TP.noteFor.variant) + '</span> varianti. Qisqa izoh (ixtiyoriy):</div>'
        + '<input type="text" id="tpVarNote" maxlength="500" placeholder="Masalan: darsdagi faollik yuqori, ko\'maksiz bajara oladi" style="width:100%;box-sizing:border-box;padding:7px 9px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:12.5px;margin-bottom:6px">'
        + '<div style="display:flex;gap:6px;flex-wrap:wrap">' + btn('✔ Tasdiqlash', 'window.tpConfirmVariant()') + btn('Bekor', 'window.tpCancelVariant()', ghostStyle()) + '</div></div>';
    }
    html += '</div>';
    return html;
  }

  window.tpAskVariant = function (sid, v) {
    TP.noteFor = { id: sid, variant: v };
    renderDiff();
    const inp = document.getElementById('tpVarNote');
    if (inp) inp.focus();
  };
  window.tpCancelVariant = function () { TP.noteFor = null; renderDiff(); };

  window.tpConfirmVariant = async function () {
    if (!TP.noteFor || TP.busy) return;
    const { id, variant } = TP.noteFor;
    const note = ((document.getElementById('tpVarNote') || {}).value || '').trim();
    TP.busy = true;
    try {
      const res = await req('/teacher/panel/students/' + encodeURIComponent(id) + '/variant', { method: 'POST', body: { variant, note } });
      toast(res.message || 'Variant biriktirildi.', 'success');
      TP.noteFor = null;
      TP.diff = null; TP.students = null; TP.obs = null;
      await loadTab(true);
    } catch (e) {
      toast(e.message, 'error');
    } finally { TP.busy = false; }
  };

  window.tpClearVariant = async function (sid) {
    if (TP.busy) return;
    TP.busy = true;
    try {
      await req('/teacher/panel/students/' + encodeURIComponent(sid) + '/variant', { method: 'DELETE' });
      toast('Tizim taklifiga qaytarildi.', 'success');
      TP.noteFor = null;
      TP.diff = null; TP.students = null; TP.obs = null;
      await loadTab(true);
    } catch (e) {
      toast(e.message, 'error');
    } finally { TP.busy = false; }
  };

  // ---------- 3-TAB: Kuzatuv varaqasi ----------
  function trendCell(t) {
    if (t === null || t === undefined) return '<span style="color:var(--muted)">—</span>';
    const up = t > 0, down = t < 0;
    const col = up ? '#16A34A' : (down ? 'var(--clay)' : 'var(--muted)');
    return '<span style="font-weight:700;color:' + col + '">' + (up ? '↑ +' : (down ? '↓ ' : '→ ')) + esc(Math.round(t * 10) / 10) + '</span>';
  }

  function renderObservation() {
    const c = content();
    const d = TP.obs;
    if (!c || !d) return;
    const rows = d.rows || [];
    const leg = d.legend || {};
    let html = '<div class="card" style="padding:16px">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">'
      + '<div style="font-weight:700;font-size:14px">📋 Kuzatuv varaqasi ' + (TP.group ? '— ' + esc(TP.group.name) + ' ' + armChip(TP.group.arm) : '(barcha ko\'rinadigan guruhlar)') + ' <span style="font-size:12px;color:var(--muted);font-weight:400">' + esc(d.total || rows.length) + ' talaba</span></div>'
      + '<div style="font-size:11.5px;color:var(--muted);display:flex;gap:10px;flex-wrap:wrap"><span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:var(--clay);vertical-align:middle"></span> takror L1 xato (≥2)</span><span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:var(--amber);vertical-align:middle"></span> o\'z bahosi farqi &gt; 1.5</span></div></div>';
    if (!rows.length) {
      html += '<p style="color:var(--muted);font-size:13px;margin:0">Talabalar topilmadi.</p></div>'; c.innerHTML = html; return;
    }
    html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;min-width:1100px;font-size:12.5px">'
      + '<thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">'
      + '<th style="' + TH + '">Talaba</th><th style="' + TH + ';text-align:center">Yozuv</th><th style="' + TH + ';text-align:center">Birinchi → oxirgi</th><th style="' + TH + ';text-align:center">O\'rt. ball</th>'
      + '<th style="' + TH + ';text-align:center" title="Mustaqil bosqichda sarflangan o\'rtacha vaqt">Mustaqil (daq)</th><th style="' + TH + ';text-align:center">So\'zlar</th>'
      + '<th style="' + TH + ';text-align:center" title="' + esc(leg.help_requests || '') + '">Yordam so\'rovi</th><th style="' + TH + ';text-align:center">O\'z tekshiruvi</th>'
      + '<th style="' + TH + ';text-align:center" title="' + esc(leg.avg_rating_gap || '') + '">O\'z bahosi farqi</th><th style="' + TH + ';text-align:center">Izoh qabul %</th>'
      + '<th style="' + TH + '" title="' + esc(leg.recurring_l1 || '') + '">Takror L1</th><th style="' + TH + '">Variantlar</th><th style="' + TH + '">Oxirgi</th><th style="' + TH + '"></th>'
      + '</tr></thead><tbody>';
    rows.forEach(r => {
      if (!r.records) {
        html += '<tr style="border-bottom:1px solid var(--line);color:var(--muted)"><td style="' + TD + '"><b style="color:var(--ink)">' + esc(r.full_name) + '</b></td><td style="' + TD + ';text-align:center">0</td><td colspan="11" style="' + TD + ';font-style:italic">Hali mashg\'ulot yozuvi yo\'q</td><td style="' + TD + '">' + btn('📝', 'window.tpOpenRecords(' + arg(r.id) + ')', ghostStyle()) + '</td></tr>';
        return;
      }
      const gapHi = typeof r.avg_rating_gap === 'number' && r.avg_rating_gap > 1.5;
      const l1 = (r.recurring_l1 || []).filter(x => x.count >= 2);
      html += '<tr style="border-bottom:1px solid var(--line)">'
        + '<td style="' + TD + '"><b>' + esc(r.full_name) + '</b></td>'
        + '<td style="' + TD + ';text-align:center">' + esc(r.records) + '</td>'
        + '<td style="' + TD + ';text-align:center;white-space:nowrap">' + esc(fmt(r.first_score)) + ' → <b>' + esc(fmt(r.last_score)) + '</b> ' + trendCell(r.trend) + '</td>'
        + '<td style="' + TD + ';text-align:center;font-weight:700">' + esc(fmt(r.avg_score)) + '</td>'
        + '<td style="' + TD + ';text-align:center">' + esc(fmt(r.avg_independent_minutes)) + '</td>'
        + '<td style="' + TD + ';text-align:center">' + esc(fmt(r.avg_words)) + '</td>'
        + '<td style="' + TD + ';text-align:center;' + (r.help_requests > 0 ? 'color:var(--amber);font-weight:700' : '') + '">' + esc(fmt(r.help_requests)) + '</td>'
        + '<td style="' + TD + ';text-align:center">' + esc(fmt(r.self_checks)) + '</td>'
        + '<td style="' + TD + ';text-align:center">' + (gapHi ? '<span style="background:var(--amber-soft);color:var(--amber);font-weight:800;padding:2px 8px;border-radius:8px;border:1px solid #E7D9AE">' + esc(r.avg_rating_gap) + '</span>' : esc(fmt(r.avg_rating_gap))) + '</td>'
        + '<td style="' + TD + ';text-align:center">' + (typeof r.feedback_accept_rate === 'number' ? esc(Math.round(r.feedback_accept_rate * 100)) + '%' : '—') + '</td>'
        + '<td style="' + TD + '">' + (l1.length ? '<div style="display:flex;gap:3px;flex-wrap:wrap">' + l1.map(x => '<span class="chip full" style="padding:1px 7px;font-weight:700" title="' + esc(x.count) + ' marta">' + esc(x.pattern_id) + ' ×' + esc(x.count) + '</span>').join('') + '</div>' : '<span style="color:var(--muted)">—</span>') + '</td>'
        + '<td style="' + TD + '">' + ((r.variants || []).length ? r.variants.map(v => '<span style="font-weight:800;color:' + (VARIANT_COLOR[v] || 'var(--ink)') + ';margin-right:4px">' + esc(v) + '</span>').join('') : '—') + '</td>'
        + '<td style="' + TD + ';white-space:nowrap">' + esc(r.last || '—') + '</td>'
        + '<td style="' + TD + '">' + btn('📝', 'window.tpOpenRecords(' + arg(r.id) + ')', ghostStyle()) + '</td>'
        + '</tr>';
    });
    html += '</tbody></table></div>';
    // Legenda
    html += '<div class="why-box" style="margin-top:12px"><b>Legenda</b><ul style="margin:0;padding-left:18px">'
      + Object.keys(leg).map(k => '<li><b style="display:inline;text-transform:none;letter-spacing:0;font-size:12.5px">' + esc({ avg_rating_gap: "O'z bahosi farqi", help_requests: 'Yordam so\'rovi', recurring_l1: 'Takror L1' }[k] || k) + ':</b> ' + esc(leg[k]) + '</li>').join('')
      + '<li><b style="display:inline;text-transform:none;letter-spacing:0;font-size:12.5px">Birinchi → oxirgi:</b> birinchi va oxirgi mashg\'ulot bali, yo\'nalish (↑ o\'sish, ↓ pasayish).</li>'
      + '</ul></div></div>';
    c.innerHTML = html;
  }

  // ---------- 4-TAB: Talaba yozuvlari ----------
  window.tpOpenRecords = async function (sid) {
    TP.recordsStudentId = sid;
    TP.tab = 'records';
    renderShell();
    await loadTab();
  };

  function renderRecords() {
    const c = content();
    const d = TP.records;
    if (!c || !d) return;
    const s = d.student || {};
    const ev = d.variant || {};
    const recs = d.records || [];
    let html = '<div class="card" style="padding:16px">'
      + '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:10px">'
      + '<div><div style="font-weight:800;font-size:16px;font-family:var(--serif)">📝 ' + esc(s.full_name) + '</div><div style="font-size:12px;color:var(--muted)">' + esc(s.email) + ' · ' + esc(recs.length) + ' ta mashg\'ulot yozuvi</div>'
      + '<div style="margin-top:6px">' + variantBadge(ev.variant, ev.source, ev.reason, ev.system_suggestion) + '</div></div>'
      + btn('← Talabalar', 'window.tpSwitchTab(' + arg('students') + ')', ghostStyle()) + '</div>';

    // Pre/post va profil tarixi
    const a = d.assessments || {};
    const types = Object.keys(a);
    if (types.length) {
      html += '<div style="overflow-x:auto;margin-bottom:10px"><table style="border-collapse:collapse;font-size:12.5px;min-width:420px"><thead><tr style="background:var(--surface-2)"><th style="' + TH + '">Baholash</th>' + ['listening', 'reading', 'speaking', 'writing'].map(k => '<th style="' + TH + ';text-align:center">' + esc(SKILL_LABELS[k]) + '</th>').join('') + '<th style="' + TH + ';text-align:center">O\'rtacha</th></tr></thead><tbody>';
      ['pre', 'mid', 'post'].filter(t => a[t]).forEach(t => {
        const o = overallOf(a[t]);
        html += '<tr style="border-bottom:1px solid var(--line)"><td style="' + TD + ';font-weight:700">' + esc(t) + '</td>' + ['listening', 'reading', 'speaking', 'writing'].map(k => '<td style="' + TD + ';text-align:center">' + esc(fmt(a[t][k])) + '</td>').join('') + '<td style="' + TD + ';text-align:center;font-weight:700">' + (o === null ? '—' : esc(o.toFixed(1))) + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }
    const ph = d.profile_history || [];
    if (ph.length) {
      html += '<details style="margin-bottom:10px;font-size:12.5px"><summary style="cursor:pointer;font-weight:600;color:var(--teal)">Profil tarixi (' + esc(ph.length) + ')</summary><div style="overflow-x:auto"><table style="border-collapse:collapse;min-width:520px;margin-top:6px"><thead><tr style="background:var(--surface-2)"><th style="' + TH + '">Sana</th><th style="' + TH + '">Manba</th><th style="' + TH + '">CEFR (L/R/S/W)</th><th style="' + TH + ';text-align:center">Tashvish</th><th style="' + TH + ';text-align:center">Mustaqillik</th></tr></thead><tbody>';
      ph.forEach(p => {
        const cf = p.cefr || {};
        html += '<tr style="border-bottom:1px solid var(--line)"><td style="' + TD + '">' + esc(p.valid_from) + '</td><td style="' + TD + '">' + esc(p.source === 'teacher_override' ? "o'qituvchi tuzatgan" : p.source) + '</td><td style="' + TD + '">' + esc([cf.listening, cf.reading, cf.speaking, cf.writing].map(x => x || '—').join(' / ')) + '</td><td style="' + TD + ';text-align:center">' + esc(fmt(p.anxiety_level)) + '</td><td style="' + TD + ';text-align:center">' + esc(fmt(p.autonomy_readiness)) + '</td></tr>';
      });
      html += '</tbody></table></div></details>';
    }
    html += '</div>';

    if (!recs.length) {
      html += '<div class="card" style="margin-top:12px;text-align:center;color:var(--muted);padding:24px">Bu talabada hali mashg\'ulot yozuvlari yo\'q.</div>';
      c.innerHTML = html; return;
    }
    recs.forEach(r => { html += recordCard(r); });
    c.innerHTML = html;
  }

  function recordCard(r) {
    const gapHi = typeof r.rating_gap === 'number' && Math.abs(r.rating_gap) > 1.5;
    let html = '<div class="card" style="margin-top:12px;padding:16px">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">'
      + '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
      + '<span style="font-weight:700;font-size:13px">' + esc(r.created_at) + '</span>'
      + '<span class="chip" style="background:var(--surface-2);color:var(--ink);border-color:var(--line)">' + esc(SKILL_LABELS[r.skill] || r.skill || '—') + '</span>'
      + '<span style="display:inline-block;padding:1px 7px;border-radius:7px;font-weight:800;font-size:12px;color:' + (VARIANT_COLOR[r.task_variant] || 'var(--ink)') + ';background:' + (VARIANT_BG[r.task_variant] || 'var(--surface-2)') + ';border:1px solid ' + (VARIANT_COLOR[r.task_variant] || 'var(--line)') + '">' + esc(r.task_variant || '—') + '</span>'
      + (r.scaffold_level ? '<span class="chip ' + esc(r.scaffold_level === 'full' ? 'full' : (r.scaffold_level === 'partial' ? 'part' : 'none')) + '">ko\'mak: ' + esc(r.scaffold_level) + '</span>' : '')
      + (r.ai_powered ? '<span class="chip none">AI baho</span>' : '<span class="chip part">lokal baho</span>')
      + '</div>'
      + '<div style="display:flex;gap:12px;font-size:12.5px;flex-wrap:wrap">'
      + '<span>Ball: <b style="font-size:15px;color:var(--teal)">' + esc(fmt(r.score)) + '</b></span>'
      + '<span>O\'z bahosi: <b>' + esc(fmt(r.self_rating)) + '</b></span>'
      + '<span>Farq: <b style="color:' + (gapHi ? 'var(--amber)' : 'var(--ink)') + '">' + esc(fmt(r.rating_gap)) + '</b></span>'
      + '<span style="color:var(--muted)">' + esc(fmt(r.word_count)) + ' so\'z · mustaqil ' + esc(r.independent_seconds ? Math.round(r.independent_seconds / 60) : 0) + ' daq · yordam ' + esc(r.help_requests || 0) + ' · tekshiruv ' + esc(r.self_checks || 0) + '</span>'
      + '</div></div>';

    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;font-size:12.5px;margin-bottom:8px">'
      + '<div style="background:var(--surface-2);padding:8px 10px;border-radius:8px"><div style="font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase">Reja maqsadi</div>' + esc(r.plan_goal || '—') + (r.plan_strategy ? '<div style="color:var(--muted);margin-top:3px">Strategiya: ' + esc(r.plan_strategy) + '</div>' : '') + '</div>'
      + '<div style="background:var(--surface-2);padding:8px 10px;border-radius:8px"><div style="font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase">Keyingi maqsad</div>' + esc(r.next_goal || '—') + '</div>'
      + '</div>';

    if (r.production_text) {
      html += '<details style="margin-bottom:8px"><summary style="cursor:pointer;font-size:12.5px;font-weight:600;color:var(--teal)">Talaba matni (' + esc(fmt(r.word_count)) + ' so\'z)</summary>'
        + '<div style="white-space:pre-wrap;font-size:13px;line-height:1.6;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:6px">' + esc(r.production_text) + '</div></details>';
    }
    const fds = r.feedback_decisions || [];
    if (fds.length) {
      html += '<div style="font-size:12px;font-weight:700;margin:6px 0 4px">Izohlar bo\'yicha qarorlar (' + esc(fds.filter(x => x.accepts).length) + '/' + esc(fds.length) + ' qabul qilindi)</div><ul style="margin:0 0 8px;padding-left:18px;font-size:12.5px;line-height:1.5">';
      fds.forEach(f => {
        html += '<li>' + (f.accepts ? '✅' : '❌') + ' <b>' + esc(f.title || f.id || '') + '</b>' + (f.justification ? ' — <span style="color:var(--ink-2)">' + esc(f.justification) + '</span>' : '') + '</li>';
      });
      html += '</ul>';
    }
    if ((r.l1_pattern_ids || []).length) {
      html += '<div style="font-size:12px;margin-bottom:6px">L1 naqshlar: ' + r.l1_pattern_ids.map(p => '<span class="chip full" style="padding:1px 7px">' + esc(p) + '</span>').join(' ') + '</div>';
    }
    if (r.comparison_note) html += '<div style="font-size:12.5px;color:var(--ink-2);margin-bottom:6px"><b>Taqqoslash:</b> ' + esc(r.comparison_note) + '</div>';
    if (r.gap_explanation) html += '<div style="font-size:12.5px;color:var(--ink-2);margin-bottom:6px"><b>Farq izohi:</b> ' + esc(r.gap_explanation) + '</div>';

    // O'qituvchi kengaytmasi (Hattie & Timperley: vazifa → jarayon / o'zini boshqarish darajasi)
    html += '<div style="margin-top:10px;padding:10px;border:1px dashed var(--teal);border-radius:9px;background:var(--teal-soft)">'
      + '<div style="font-size:11.5px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--teal);margin-bottom:4px">O\'qituvchi izohi — jarayon / o\'zini boshqarish darajasi</div>';
    if (r.teacher_extension) html += '<div style="font-size:13px;line-height:1.55;margin-bottom:6px;white-space:pre-wrap"><b>Saqlangan:</b> ' + esc(r.teacher_extension) + '</div>';
    html += '<textarea id="tpExt_' + esc(r.id) + '" rows="2" placeholder="Texnologiya vazifa darajasida izoh berdi; siz uni strategiya va o\'zini boshqarish darajasiga ko\'taring (kamida 3 belgi)" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:12.5px;font-family:inherit;margin-bottom:6px">' + esc(r.teacher_extension || '') + '</textarea>'
      + btn('💬 Izohni jarayon darajasiga ko\'tarish (saqlash)', 'window.tpExtend(' + arg(r.id) + ')')
      + '</div></div>';
    return html;
  }

  window.tpExtend = async function (rid) {
    if (TP.busy) return;
    const ta = document.getElementById('tpExt_' + rid);
    const txt = ta ? ta.value.trim() : '';
    if (txt.length < 3) { toast('Izoh kamida 3 belgidan iborat bo\'lsin.', 'error'); return; }
    TP.busy = true;
    try {
      const res = await req('/teacher/panel/records/' + encodeURIComponent(rid) + '/extend', { method: 'POST', body: { teacher_extension: txt } });
      toast('Izoh saqlandi.', 'success');
      if (TP.records && res && res.record) {
        TP.records.records = TP.records.records.map(r => r.id === rid ? Object.assign({}, r, { teacher_extension: res.record.teacher_extension }) : r);
        renderRecords();
      }
    } catch (e) {
      toast(e.message, 'error');
    } finally { TP.busy = false; }
  };
})();
