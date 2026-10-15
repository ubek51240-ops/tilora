/**
 * TILORA — Talaba tomonining kengaytmasi (v2.4 tajriba moslashuvi)
 *   1. Tajriba bannerlari: GET /student/experiment-status (nazorat guruhi / nazorat oynasi) + 403 toast (fetch o'rami).
 *   2. SILL so'rovnomasi (Oxford, 1990): GET /student/sill/questions, POST /student/sill, GET /student/sill/me.
 *   3. O'quv yo'li: nazorat guruhi uchun sabab bloki (#pathArmNotice).
 *   4. Mikroo'qitish va tengdoshlar baholashi: /student/microteaching[/rubric | /{id} | /{id}/review].
 * app.js o'zgartirilmaydi: showScreen() DOMContentLoaded da bir marta o'raladi. Barcha matnlar T() orqali (i18n_ext.js).
 * Server bergan matn (savollar, eslatmalar, izohlar) o'zgartirilmaydi; barcha dinamik matn esc() orqali.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ yordamchilar
  function esc(v) {
    if (typeof window.escapeHtml === "function") return window.escapeHtml(v);
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
  }
  function jarg(v) { return typeof window.jsArg === "function" ? window.jsArg(v) : esc(JSON.stringify(String(v === null || v === undefined ? "" : v))); }
  function T(key, fb, vars) {
    if (typeof window.T === "function") return window.T(key, fb, vars);
    let s = fb === undefined ? key : fb;
    if (vars) Object.keys(vars).forEach(k => { s = String(s).split("{" + k + "}").join(String(vars[k])); });
    return s;
  }
  function S() { return window.STATE || {}; }
  function toast(msg, type) { if (typeof window.showToast === "function") window.showToast(msg, type || "info"); }
  function num(v, d) {
    if (v === null || v === undefined || v === "" || isNaN(Number(v))) return "—";
    return d === undefined ? String(Number(v)) : Number(v).toFixed(d);
  }
  function authHeaders(json) {
    const h = { "Authorization": `Bearer ${S().token}` };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }
  async function api(path, opts) {
    const o = opts || {};
    const res = await fetch(`${S().apiBaseUrl}${path}`, {
      method: o.method || "GET",
      headers: authHeaders(!!o.body),
      body: o.body ? JSON.stringify(o.body) : undefined
    });
    const data = await res.json().catch(() => ({}));
    return { res, data };
  }
  /** Server xatosini odam o'qiydigan matnga aylantirish (string | {error_code,message} | 422 ro'yxati). */
  function errorText(data, fallback) {
    const d = data && data.detail;
    if (!d) return fallback;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return T("mt_err_422", "Shaklda xatolar bor:") + " " + d.map(e => {
        const loc = Array.isArray(e.loc) ? e.loc.filter(x => x !== "body").join(".") : "";
        return (loc ? loc + ": " : "") + (e.msg || "");
      }).join("; ");
    }
    if (typeof d === "object") return d.message || (d.details && d.details.note) || d.error_code || fallback;
    return fallback;
  }
  function loginNotice(text) {
    return `<div class="card ext-login-notice">
      <div class="ext-login-icon">🔑</div>
      <div class="ext-login-title">${esc(text)}</div>
      <button type="button" class="btn-primary" onclick="window.openLoginModal && window.openLoginModal()">${esc(T("ext_login_btn", "Tizimga kirish"))}</button>
    </div>`;
  }
  function errorBox(msg, retryFn) {
    return `<div class="card ext-error-box">⚠️ ${esc(msg)}
      ${retryFn ? `<div style="margin-top:10px"><button type="button" class="btn-primary" style="padding:7px 12px;font-size:12.5px" onclick="${retryFn}">🔄 ${esc(T("ext_retry", "Qayta urinish"))}</button></div>` : ""}</div>`;
  }
  function bar(value, max, color) {
    const pct = Math.max(0, Math.min(100, (Number(value) || 0) / (max || 5) * 100));
    return `<div class="track ext-bar"><div class="fill${color === "warn" ? " warn" : ""}" style="width:${pct.toFixed(0)}%"></div></div>`;
  }

  // ------------------------------------------------------------------ 1a. 403 toast (fetch o'rami)
  (function wrapFetchFor403() {
    const prev = window.fetch;
    let lastToastAt = 0;
    window.fetch = async function (input, init) {
      const res = await prev.call(window, input, init);
      try {
        const url = typeof input === "string" ? input : ((input && input.url) || "");
        if (res.status === 403 && url.includes("/api/")) {
          const data = await res.clone().json().catch(() => null);
          const d = data && data.detail;
          const code = (d && typeof d === "object" && !Array.isArray(d)) ? d.error_code : null;
          if (code === "CONTROL_GROUP_RESTRICTED" || code === "ASSESSMENT_WINDOW") {
            const now = Date.now();
            if (now - lastToastAt > 10000) {
              lastToastAt = now;
              toast(d.message || (d.details && d.details.note) || code, "warning");
            }
          }
        }
      } catch (_) {}
      return res;
    };
  })();

  // ------------------------------------------------------------------ 1b. Tajriba bannerlari
  const EXP = { status: null, token: null, fetchedAt: 0 };

  function bannerHost() {
    let host = document.getElementById("extBannerHost");
    if (host) return host;
    const main = document.querySelector("main.main-content") || document.querySelector("main");
    if (!main) return null;
    host = document.createElement("div");
    host.id = "extBannerHost";
    const topBar = main.querySelector(".top-bar");
    if (topBar && topBar.parentNode === main) topBar.insertAdjacentElement("afterend", host);
    else main.insertAdjacentElement("afterbegin", host);
    return host;
  }
  function dismissed(key) { try { return sessionStorage.getItem("tilora_ext_dismiss_" + key) === "1"; } catch (_) { return false; } }
  window.extDismissBanner = function (key) {
    try { sessionStorage.setItem("tilora_ext_dismiss_" + key, "1"); } catch (_) {}
    renderBanners();
  };
  function renderBanners() {
    const host = bannerHost();
    if (!host) return;
    const st = EXP.status;
    if (!S().token || !st) { host.innerHTML = ""; return; }
    const parts = [];
    if (st.experiment_arm === "control" && !dismissed("control")) {
      parts.push(`<div class="ext-banner amber" role="status">
        <span class="ext-banner-icon">🧪</span>
        <span class="ext-banner-text">${esc(T("banner_control"))}</span>
        <button type="button" class="ext-banner-close" onclick="window.extDismissBanner('control')" aria-label="${esc(T("ext_close", "Yopish"))}" title="${esc(T("ext_close", "Yopish"))}">×</button>
      </div>`);
    }
    const w = st.assessment_window || "none";
    if (w !== "none" && !dismissed("window_" + w)) {
      parts.push(`<div class="ext-banner clay" role="status">
        <span class="ext-banner-icon">📝</span>
        <span class="ext-banner-text">${esc(T("banner_window", "", { w }))}</span>
        <button type="button" class="ext-banner-close" onclick="window.extDismissBanner(${jarg("window_" + w)})" aria-label="${esc(T("ext_close", "Yopish"))}" title="${esc(T("ext_close", "Yopish"))}">×</button>
      </div>`);
    }
    host.innerHTML = parts.join("");
  }
  async function refreshExperimentBanners(force) {
    const token = S().token;
    if (!token) { EXP.status = null; EXP.token = null; renderBanners(); return; }
    if (!force && EXP.token === token && Date.now() - EXP.fetchedAt < 30000) { renderBanners(); return; }
    EXP.token = token; EXP.fetchedAt = Date.now();
    try {
      const { res, data } = await api("/student/experiment-status");
      EXP.status = res.ok ? data : null;
    } catch (_) { EXP.status = null; }
    renderBanners();
  }
  window.refreshExperimentBanners = refreshExperimentBanners;
  window.getExperimentStatus = () => EXP.status;

  // ------------------------------------------------------------------ 3. O'quv yo'li: nazorat guruhi bloki
  const PATH = { arm: null, note: "" };
  function renderPathNotice() {
    const box = document.getElementById("pathArmNotice");
    if (!box) return;
    if (!S().token || PATH.arm !== "control") { box.innerHTML = ""; return; }
    box.innerHTML = `<div class="why-box ext-path-notice">
      <b>${esc(T("path_arm_title"))}</b>
      ${PATH.note ? `<div>${esc(PATH.note)}</div>` : ""}
      <div class="ext-path-notice-sub">${esc(T("path_arm_body"))}</div>
    </div>`;
  }
  async function refreshPathArmNotice() {
    const box = document.getElementById("pathArmNotice");
    if (!box) return;
    if (!S().token) { PATH.arm = null; renderPathNotice(); return; }
    try {
      const { res, data } = await api("/student/path");
      PATH.arm = res.ok ? (data.experiment_arm || null) : null;
      PATH.note = res.ok ? (data.note || "") : "";
    } catch (_) { PATH.arm = null; }
    renderPathNotice();
  }
  window.refreshPathArmNotice = refreshPathArmNotice;

  // ------------------------------------------------------------------ 2. SILL
  const SILL = { spec: null, answers: {}, result: null, history: null, groupsMeta: null, error: null, busy: false };
  const SILL_ORDER = ["memory", "cognitive", "compensation", "metacognitive", "affective", "social"];

  function sillBtn(show) {
    const b = document.getElementById("btnSubmitSill");
    if (b) b.style.display = show ? "" : "none";
  }
  function atypeLabel(t) {
    const map = { pre: "sill_atype_pre", mid: "sill_atype_mid", post: "sill_atype_post" };
    return map[t] ? T(map[t], t) : (t || "—");
  }
  function sillGroupName(key, meta) {
    const g = (meta && meta[key]) || {};
    const lang = typeof window.getExtLang === "function" ? window.getExtLang() : "uz";
    return (lang === "en" && g.en) ? g.en : (g.name || key);
  }
  function renderSillResult() {
    const r = SILL.result;
    if (!r) return "";
    const meta = SILL.spec ? SILL.spec.groups : (SILL.groupsMeta || {});
    const rows = SILL_ORDER.filter(k => r.groups && r.groups[k]).map(k => {
      const g = r.groups[k];
      return `<div class="sill-res-row">
        <div class="sill-res-name">${esc(sillGroupName(k, meta))}</div>
        <div class="sill-res-bar">${bar(g.avg, 5, g.avg < 2.5 ? "warn" : "")}</div>
        <div class="sill-res-val"><b>${num(g.avg, 2)}</b> / 5 <span class="sill-res-label">${esc(g.label || "")}</span></div>
      </div>`;
    }).join("");
    return `<div class="sill-result">
      <div class="sill-result-head">
        <h4>📊 ${esc(T("sill_result_title"))}</h4>
        <span class="chip part">${esc(T("sill_atype"))}: ${esc(atypeLabel(r.assessment_type))}</span>
      </div>
      ${rows}
      <div class="sill-res-overall"><span>${esc(T("sill_overall"))}:</span> <b>${num(r.overall, 2)}</b> / 5 · ${esc(r.overall_label || "")}</div>
      <div class="why-box" style="margin-top:12px;padding:10px 14px">
        <b>${esc(T("sill_weakest"))}: ${esc(sillGroupName(r.weakest, meta))}</b>
        ${esc(r.advice || "")}
      </div>
    </div>`;
  }
  function renderSillHistory() {
    const h = SILL.history;
    if (!h || !h.history) return "";
    const types = ["pre", "mid", "post"].filter(t => h.history[t]);
    if (types.length < 2) return "";
    const meta = h.groups_meta || (SILL.spec && SILL.spec.groups) || {};
    const hasPrePost = h.history.pre && h.history.post;
    const th = `<tr><th>${esc(T("sill_col_group"))}</th>${types.map(t => `<th style="text-align:center">${esc(atypeLabel(t))}<div class="sill-hist-date">${esc(h.history[t].date || "")}</div></th>`).join("")}${hasPrePost ? `<th style="text-align:center">${esc(T("sill_col_delta"))}</th>` : ""}</tr>`;
    const row = (label, getter, bold) => {
      const cells = types.map(t => `<td style="text-align:center;${bold ? "font-weight:700" : ""}">${num(getter(h.history[t]), 2)}</td>`).join("");
      let delta = "";
      if (hasPrePost) {
        const a = getter(h.history.pre), b = getter(h.history.post);
        if (a !== undefined && b !== undefined && a !== null && b !== null) {
          const d = Number(b) - Number(a);
          delta = `<td style="text-align:center;font-weight:700;color:${d > 0 ? "var(--teal)" : (d < 0 ? "var(--clay)" : "var(--muted)")}">${d > 0 ? "+" : ""}${num(d, 2)}</td>`;
        } else delta = `<td style="text-align:center;color:var(--muted)">—</td>`;
      }
      return `<tr><td${bold ? ' style="font-weight:700"' : ""}>${esc(label)}</td>${cells}${delta}</tr>`;
    };
    const rows = SILL_ORDER.filter(k => types.some(t => h.history[t].groups && h.history[t].groups[k] !== undefined))
      .map(k => row(sillGroupName(k, meta), d => (d.groups || {})[k], false)).join("") + row(T("sill_overall"), d => d.overall, true);
    return `<div class="sill-history">
      <h4>🕒 ${esc(T("sill_history_title"))}</h4>
      <div style="overflow-x:auto"><table class="ext-table">${th}${rows}</table></div>
      <div class="ext-note">${esc(T("sill_history_note"))}</div>
    </div>`;
  }
  function renderSill() {
    const box = document.getElementById("sillQuestionsContainer");
    if (!box) return;
    if (!S().token) { box.innerHTML = loginNotice(T("sill_login_notice")); sillBtn(false); return; }
    if (SILL.error) { box.innerHTML = errorBox(SILL.error, "window.loadSill(true)"); sillBtn(false); return; }
    const spec = SILL.spec;
    if (!spec) { box.innerHTML = `<div class="ext-loading">⏳ ${esc(T("ext_loading"))}</div>`; sillBtn(false); return; }
    const lang = typeof window.getExtLang === "function" ? window.getExtLang() : "uz";
    const labels = spec.scale_labels_uz || [];
    const legend = `<div class="sill-legend"><b>${esc(T("sill_legend"))}:</b> ${labels.map((l, i) => `<span class="chip">${i + 1} — ${esc(l)}</span>`).join(" ")}</div>`;
    const groups = SILL_ORDER.filter(k => spec.groups && spec.groups[k]).map(k => {
      const g = spec.groups[k];
      const items = (spec.items || []).filter(it => it.group === k).map(it => {
        const text = (lang === "en" && it.en) ? it.en : it.uz;
        const cur = SILL.answers[it.id];
        const radios = [1, 2, 3, 4, 5].map(v => `<label class="sill-radio" title="${esc(labels[v - 1] || v)}">
            <input type="radio" name="sill_${esc(it.id)}" value="${v}" ${cur === v ? "checked" : ""} onchange="window.extSillAnswer(${jarg(it.id)}, ${v})"><span>${v}</span></label>`).join("");
        return `<div class="sill-item${cur ? " answered" : ""}" id="sill_item_${esc(it.id)}">
          <div class="sill-item-text">${esc(text)}</div>
          <div class="sill-item-scale">${radios}</div>
        </div>`;
      }).join("");
      return `<div class="sill-group">
        <div class="sill-group-head"><div class="sill-group-name">${esc(sillGroupName(k, spec.groups))}</div><div class="sill-group-desc">${esc(g.desc || "")}</div></div>
        ${items}
      </div>`;
    }).join("");
    const total = (spec.items || []).length, done = Object.keys(SILL.answers).length;
    box.innerHTML = `${renderSillResult()}${renderSillHistory()}${legend}${groups}
      <div class="sill-progress" id="sillProgress">${done} / ${total}</div>`;
    sillBtn(true);
    const b = document.getElementById("btnSubmitSill");
    if (b) b.disabled = !!SILL.busy;
  }
  window.extSillAnswer = function (id, v) {
    SILL.answers[id] = Number(v);
    const el = document.getElementById("sill_item_" + id);
    if (el) el.classList.add("answered");
    const p = document.getElementById("sillProgress");
    if (p && SILL.spec) p.textContent = `${Object.keys(SILL.answers).length} / ${(SILL.spec.items || []).length}`;
  };
  async function loadSillHistory() {
    try {
      const { res, data } = await api("/student/sill/me");
      SILL.history = res.ok ? data : null;
    } catch (_) { SILL.history = null; }
  }
  window.loadSill = async function (force) {
    const box = document.getElementById("sillQuestionsContainer");
    if (!box) return;
    if (!S().token) { renderSill(); return; }
    SILL.error = null;
    if (!SILL.spec || force) {
      renderSill();
      try {
        const [q] = await Promise.all([api("/student/sill/questions"), loadSillHistory()]);
        if (!q.res.ok) SILL.error = errorText(q.data, T("sill_err_load"));
        else SILL.spec = q.data;
      } catch (_) { SILL.error = T("ext_server_error"); }
    } else {
      await loadSillHistory();
    }
    renderSill();
  };
  window.submitSill = async function () {
    if (!S().token) { toast(T("sill_login_notice"), "error"); if (window.openLoginModal) window.openLoginModal(); return; }
    if (!SILL.spec || SILL.busy) return;
    const items = SILL.spec.items || [];
    const missing = items.filter(it => !SILL.answers[it.id]);
    if (missing.length) {
      toast(T("sill_need_all", "", { n: missing.length }), "error");
      const el = document.getElementById("sill_item_" + missing[0].id);
      if (el) { el.classList.add("missing"); el.scrollIntoView({ behavior: "smooth", block: "center" }); }
      return;
    }
    SILL.busy = true;
    const btn = document.getElementById("btnSubmitSill");
    const prevTxt = btn ? btn.innerHTML : "";
    if (btn) { btn.disabled = true; btn.textContent = "⏳ " + T("sill_sending"); }
    try {
      const { res, data } = await api("/student/sill", { method: "POST", body: { answers: items.map(it => ({ item_id: it.id, rating: SILL.answers[it.id] })) } });
      if (!res.ok) { toast(errorText(data, T("mt_err_save")), "error"); }
      else {
        SILL.result = data;
        toast(T("sill_sent"), "success");
        await loadSillHistory();
        renderSill();
        const card = document.getElementById("sillCard");
        if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (_) { toast(T("ext_server_error"), "error"); }
    SILL.busy = false;
    if (btn) { btn.disabled = false; btn.innerHTML = prevTxt; }
  };

  // ------------------------------------------------------------------ 4. Mikroo'qitish
  const MT = { rubric: null, forms: [], rules: [], data: null, form: null, loaded: false, error: null, busy: false };
  const LESSON_FORMS = ["microteaching", "flipped", "mixed", "practical"];
  const INDEP_RE = /mustaqil|independent|самостоят/i;

  function formName(key) {
    const f = (MT.forms || []).find(x => x.key === key);
    return T("form_" + key, f ? f.name : key);
  }
  function statusChip(st) {
    const cls = { draft: "mt-st-draft", submitted: "mt-st-submitted", reviewed: "mt-st-reviewed", evaluated: "mt-st-evaluated" }[st] || "";
    return `<span class="chip ${cls}">${esc(T("mt_status_" + st, st))}</span>`;
  }
  function checkMark(ok, label) {
    return `<span class="ext-check ${ok ? "ok" : "no"}" title="${esc(label)}">${ok ? "✓" : "✗"} ${esc(label)}</span>`;
  }
  function rubricRows(values, max) {
    const rub = MT.rubric || [];
    return rub.map(c => {
      const v = values ? values[c.key] : undefined;
      return `<div class="mt-rub-row">
        <div class="mt-rub-name" title="${esc(c.desc || "")}">${esc(c.name)}</div>
        <div class="mt-rub-bar">${bar(v || 0, max || 5)}</div>
        <div class="mt-rub-val">${v === undefined || v === null ? "—" : num(v, 2)} / ${max || 5}</div>
      </div>`;
    }).join("");
  }
  function stagesSummary(stages) {
    if (!Array.isArray(stages) || !stages.length) return "";
    return `<div class="mt-stages-summary">${stages.map(s => `<span class="chip${INDEP_RE.test(String(s.name || "")) ? " none" : ""}">${esc(s.name || "—")}${s.minutes ? ` · ${esc(s.minutes)} ${esc(T("ext_min", "daq"))}` : ""}</span>`).join("")}</div>`;
  }

  // --- rules / rubric / forms
  function renderRulesCard() {
    const rules = (MT.rules || []).map(r => `<li>${esc(r)}</li>`).join("");
    const rubric = (MT.rubric || []).map((c, i) => `<li><b>${i + 1}. ${esc(c.name)}</b> — ${esc(c.desc || "")}</li>`).join("");
    const forms = (MT.forms || []).map(f => `<tr>
        <td style="font-weight:700;white-space:nowrap">${esc(f.name)}</td>
        <td>${esc(f.traditional || "")}</td>
        <td>${esc(f.new_role || "")}</td>
        <td>${esc(f.technology_role || "")}</td>
        <td>${(f.structure || []).map(s => `<span class="chip">${esc(s)}</span>`).join(" ")}</td>
      </tr>`).join("");
    return `<div class="card mt-rules-card">
      <div class="mt-two-col">
        <div><h3>${esc(T("mt_rules_title"))}</h3><ul class="mt-rules">${rules}</ul></div>
        <div><h3>${esc(T("mt_rubric_title"))}</h3><ol class="mt-rubric-list">${rubric}</ol></div>
      </div>
      <details class="mt-forms-details">
        <summary>${esc(T("mt_forms_title"))}</summary>
        <div style="overflow-x:auto;margin-top:10px"><table class="ext-table mt-forms-table">
          <thead><tr><th>${esc(T("mt_forms_col_form"))}</th><th>${esc(T("mt_forms_col_trad"))}</th><th>${esc(T("mt_forms_col_new"))}</th><th>${esc(T("mt_forms_col_tech"))}</th><th>${esc(T("mt_forms_col_structure"))}</th></tr></thead>
          <tbody>${forms}</tbody></table></div>
      </details>
    </div>`;
  }

  // --- mening loyihalarim
  function renderMine() {
    const mine = (MT.data && MT.data.mine) || [];
    const body = mine.length ? mine.map(m => {
      const ch = m.checks || {};
      const peerRevs = (m.peer_reviews || []).filter(r => (r.strengths || r.suggestions));
      return `<div class="mt-item">
        <div class="mt-item-head">
          <div class="mt-item-title">${esc(m.title)}</div>
          <div class="mt-item-chips"><span class="chip">${esc(formName(m.lesson_form))}</span>${statusChip(m.status)}<span class="mt-date">${esc(m.created_at || "")}</span></div>
        </div>
        <div class="mt-item-obj"><b>${esc(T("mt_objective_label"))}:</b> ${esc(m.objective || "")}</div>
        <div class="mt-item-obj"><b>${esc(T("mt_tool_label"))}:</b> ${esc(m.tool_name || "")} · ${esc(T("mt_f_share"))}: <b>${num(m.independent_share)}%</b></div>
        ${stagesSummary(m.stages)}
        <div class="mt-checks">${checkMark(!!ch.independent_share_ok, T("mt_check_share"))}${checkMark(!!ch.has_alternative, T("mt_check_alt"))}${checkMark(!!ch.has_rationale, T("mt_check_rationale"))}</div>
        <div class="mt-two-col" style="margin-top:10px">
          <div>
            <div class="mt-sub-title">${esc(T("mt_peer_avg"))} <span class="chip">${esc(T("mt_peer_count"))}: ${num(m.peer_count || 0)}</span></div>
            ${m.peer_count ? rubricRows(m.peer_avg, 5) : `<div class="ext-note">${esc(T("ext_no_data"))}</div>`}
            ${peerRevs.length ? `<div class="mt-sub-title" style="margin-top:8px">${esc(T("mt_peer_comments"))}</div><ul class="mt-peer-comments">${peerRevs.map(r => `<li>${r.strengths ? `<b>+</b> ${esc(r.strengths)} ` : ""}${r.suggestions ? `<i>→ ${esc(r.suggestions)}</i>` : ""}</li>`).join("")}</ul>` : ""}
          </div>
          <div>
            <div class="mt-sub-title">${esc(T("mt_teacher_eval"))}</div>
            ${m.teacher_rubric ? rubricRows(m.teacher_rubric, 5) : `<div class="ext-note">${esc(T("ext_no_data"))}</div>`}
            ${m.teacher_comment ? `<div class="why-box" style="margin-top:8px;padding:8px 12px"><b>${esc(T("mt_teacher_comment"))}</b>${esc(m.teacher_comment)}</div>` : ""}
          </div>
        </div>
        <div class="mt-item-actions">
          <button type="button" class="btn-primary ext-btn-sm" ${m.status === "evaluated" ? `disabled title="${esc(T("mt_edit_locked"))}"` : ""} onclick="window.extMtEdit(${jarg(m.id)})">✏️ ${esc(T("mt_btn_edit"))}</button>
          ${m.status === "evaluated" ? `<span class="ext-note">${esc(T("mt_edit_locked"))}</span>` : ""}
        </div>
      </div>`;
    }).join("") : `<div class="ext-note">${esc(T("mt_mine_empty"))}</div>`;
    return `<div class="card" id="mtMineCard">
      <div class="mt-card-head"><h3>${esc(T("mt_mine_title"))}</h3>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn-primary ext-btn-sm ext-btn-ghost" onclick="window.loadMicroteaching(true)">🔄 ${esc(T("ext_refresh"))}</button>
          <button type="button" class="btn-primary ext-btn-sm" onclick="window.extMtNew()">＋ ${esc(T("mt_new_btn"))}</button>
        </div>
      </div>
      ${body}
    </div>`;
  }

  // --- forma
  function defaultStages() {
    return [
      { name: "Kirish", minutes: 2, activity: "", technology_role: "" },
      { name: "Tayyorgarlik", minutes: 4, activity: "", technology_role: "" },
      { name: "Mustaqil bajarish (AI yopiq)", minutes: 5, activity: "", technology_role: "" },
      { name: "Tahlil va yakun", minutes: 4, activity: "", technology_role: "" }
    ];
  }
  function emptyForm() {
    return { id: null, title: "", lesson_form: "microteaching", objective: "", stages: defaultStages(), tool_name: "", tool_rationale: "", alternative_plan: "", independent_share: 33, reflection: "", shareTouched: false, errors: null, status: "draft" };
  }
  function shareCalc(stages) {
    let total = 0, indep = 0;
    (stages || []).forEach(s => { const m = Number(s.minutes) || 0; total += m; if (INDEP_RE.test(String(s.name || ""))) indep += m; });
    return { total, indep, share: total > 0 ? Math.round(indep / total * 100) : null };
  }
  function collectForm() {
    const f = MT.form; if (!f) return;
    const g = id => { const el = document.getElementById(id); return el ? el.value : undefined; };
    const v = g("mtf_title"); if (v !== undefined) f.title = v;
    const lf = g("mtf_form"); if (lf !== undefined) f.lesson_form = lf;
    const ob = g("mtf_objective"); if (ob !== undefined) f.objective = ob;
    const tn = g("mtf_tool"); if (tn !== undefined) f.tool_name = tn;
    const tr = g("mtf_rationale"); if (tr !== undefined) f.tool_rationale = tr;
    const al = g("mtf_alt"); if (al !== undefined) f.alternative_plan = al;
    const sh = g("mtf_share"); if (sh !== undefined && sh !== "") f.independent_share = Number(sh);
    const rf = g("mtf_reflection"); if (rf !== undefined) f.reflection = rf;
  }
  function renderStageRows() {
    const f = MT.form; if (!f) return;
    const body = document.getElementById("mtStagesBody"); if (!body) return;
    body.innerHTML = f.stages.map((s, i) => `<div class="mt-stage-row">
      <input type="text" class="mt-stage-name" value="${esc(s.name)}" placeholder="${esc(T("mt_f_stage_name"))}" oninput="window.extMtStage(${i},'name',this.value)">
      <input type="number" class="mt-stage-min" min="0" max="180" value="${esc(s.minutes)}" placeholder="${esc(T("mt_f_stage_min"))}" oninput="window.extMtStage(${i},'minutes',this.value)">
      <input type="text" class="mt-stage-act" value="${esc(s.activity)}" placeholder="${esc(T("mt_f_stage_activity"))}" oninput="window.extMtStage(${i},'activity',this.value)">
      <input type="text" class="mt-stage-tech" value="${esc(s.technology_role)}" placeholder="${esc(T("mt_f_stage_tech"))}" oninput="window.extMtStage(${i},'technology_role',this.value)">
      <button type="button" class="mt-stage-del" onclick="window.extMtRemoveStage(${i})" title="${esc(T("mt_f_remove"))}" aria-label="${esc(T("mt_f_remove"))}">🗑</button>
    </div>`).join("");
    updateStageTotals();
  }
  function updateStageTotals() {
    const f = MT.form; if (!f) return;
    const c = shareCalc(f.stages);
    const tot = document.getElementById("mtStageTotals");
    if (tot) {
      tot.innerHTML = `${esc(T("mt_f_total_min"))}: <b>${c.total}</b> ${esc(T("ext_min", "daq"))} · ${esc(T("mt_f_indep_calc"))}: <b>${c.indep}</b> ${esc(T("ext_min", "daq"))}${c.share !== null ? ` (<b style="color:${c.share < 33 ? "var(--clay)" : "var(--teal)"}">${c.share}%</b>)` : ""}
        ${c.share !== null ? `<button type="button" class="btn-primary ext-btn-xs" onclick="window.extMtApplyShare()">${esc(T("mt_f_apply_share"))}</button>` : ""}`;
    }
    if (!f.shareTouched && c.share !== null) {
      f.independent_share = c.share;
      const sh = document.getElementById("mtf_share");
      if (sh) sh.value = c.share;
    }
    updateShareWarn();
  }
  function updateShareWarn() {
    const sh = document.getElementById("mtf_share");
    const w = document.getElementById("mtShareWarn");
    if (!sh || !w) return;
    const v = Number(sh.value);
    w.style.display = (sh.value !== "" && v < 33) ? "" : "none";
  }
  window.extMtStage = function (i, field, value) {
    const f = MT.form; if (!f || !f.stages[i]) return;
    f.stages[i][field] = field === "minutes" ? (value === "" ? "" : Number(value)) : value;
    updateStageTotals();
  };
  window.extMtAddStage = function () {
    const f = MT.form; if (!f) return;
    if (f.stages.length >= 12) return;
    f.stages.push({ name: "", minutes: 5, activity: "", technology_role: "" });
    renderStageRows();
    const rows = document.querySelectorAll("#mtStagesBody .mt-stage-name");
    if (rows.length) rows[rows.length - 1].focus();
  };
  window.extMtRemoveStage = function (i) {
    const f = MT.form; if (!f) return;
    f.stages.splice(i, 1);
    renderStageRows();
  };
  window.extMtApplyShare = function () {
    const f = MT.form; if (!f) return;
    const c = shareCalc(f.stages);
    if (c.share === null) return;
    f.independent_share = c.share; f.shareTouched = true;
    const sh = document.getElementById("mtf_share");
    if (sh) sh.value = c.share;
    updateShareWarn();
  };
  window.extMtShareInput = function (v) {
    const f = MT.form; if (!f) return;
    f.shareTouched = true;
    if (v !== "") f.independent_share = Number(v);
    updateShareWarn();
  };
  function renderForm() {
    const f = MT.form;
    if (!f) return "";
    const opts = LESSON_FORMS.map(k => `<option value="${k}" ${f.lesson_form === k ? "selected" : ""}>${esc(formName(k))}</option>`).join("");
    // Server ruxsat bergan, lekin tanlov ro'yxatida bo'lmagan shakl (eski loyiha) — saqlab qolamiz
    const extra = (f.lesson_form && !LESSON_FORMS.includes(f.lesson_form)) ? `<option value="${esc(f.lesson_form)}" selected>${esc(formName(f.lesson_form))}</option>` : "";
    const errs = f.errors ? `<div class="ext-error-box" style="margin-bottom:12px"><b>${esc(T("mt_err_422"))}</b><ul style="margin:6px 0 0 18px">${f.errors.map(e => `<li>${esc(e)}</li>`).join("")}</ul></div>` : "";
    const locked = f.status === "evaluated";
    return `<div class="card mt-form-card" id="mtFormCard">
      <div class="mt-card-head"><h3>${esc(f.id ? T("mt_edit_title") : T("mt_new_title"))}${f.id ? ` ${statusChip(f.status)}` : ""}</h3>
        <button type="button" class="btn-primary ext-btn-sm ext-btn-ghost" onclick="window.extMtCancel()">${esc(T("mt_btn_cancel"))}</button></div>
      ${errs}
      <div class="mt-grid">
        <div class="mt-field mt-span-2"><label for="mtf_title">${esc(T("mt_f_title"))} *</label><input type="text" id="mtf_title" maxlength="255" value="${esc(f.title)}" placeholder="${esc(T("mt_f_title_ph"))}"></div>
        <div class="mt-field"><label for="mtf_form">${esc(T("mt_f_form"))}</label><select id="mtf_form">${opts}${extra}</select></div>
        <div class="mt-field mt-span-3"><label for="mtf_objective">${esc(T("mt_f_objective"))} *</label><textarea id="mtf_objective" rows="2" maxlength="1000" placeholder="${esc(T("mt_f_objective_ph"))}">${esc(f.objective)}</textarea></div>
      </div>
      <div class="mt-field" style="margin-top:12px">
        <label>${esc(T("mt_f_stages"))} <span class="ext-hint">${esc(T("mt_f_stages_hint"))}</span></label>
        <div class="mt-stage-head"><span>${esc(T("mt_f_stage_name"))}</span><span>${esc(T("mt_f_stage_min"))}</span><span>${esc(T("mt_f_stage_activity"))}</span><span>${esc(T("mt_f_stage_tech"))}</span><span></span></div>
        <div id="mtStagesBody"></div>
        <div class="mt-stage-foot">
          <button type="button" class="btn-primary ext-btn-sm ext-btn-ghost" onclick="window.extMtAddStage()">${esc(T("mt_f_add_stage"))}</button>
          <div id="mtStageTotals" class="mt-stage-totals"></div>
        </div>
      </div>
      <div class="mt-grid" style="margin-top:12px">
        <div class="mt-field"><label for="mtf_tool">${esc(T("mt_f_tool"))} *</label><input type="text" id="mtf_tool" maxlength="120" value="${esc(f.tool_name)}" placeholder="${esc(T("mt_f_tool_ph"))}"></div>
        <div class="mt-field"><label for="mtf_share">${esc(T("mt_f_share"))} *</label><input type="number" id="mtf_share" min="0" max="100" value="${esc(f.independent_share)}" oninput="window.extMtShareInput(this.value)">
          <div id="mtShareWarn" class="ext-warn" style="display:none">⚠️ ${esc(T("mt_f_share_warn"))}</div></div>
        <div class="mt-field mt-span-3"><label for="mtf_rationale">${esc(T("mt_f_tool_rationale"))} * <span class="ext-hint">${esc(T("mt_f_tool_rationale_hint"))}</span></label><textarea id="mtf_rationale" rows="2" maxlength="1000">${esc(f.tool_rationale)}</textarea></div>
        <div class="mt-field mt-span-3"><label for="mtf_alt">${esc(T("mt_f_alt"))} * <span class="ext-hint">${esc(T("mt_f_alt_hint"))}</span></label><textarea id="mtf_alt" rows="2" maxlength="1000">${esc(f.alternative_plan)}</textarea></div>
        <div class="mt-field mt-span-3"><label for="mtf_reflection">${esc(T("mt_f_reflection"))} <span class="ext-hint">${esc(T("mt_f_reflection_hint"))}</span></label><textarea id="mtf_reflection" rows="3" maxlength="3000">${esc(f.reflection || "")}</textarea></div>
      </div>
      <div class="mt-form-actions">
        <button type="button" class="btn-primary ext-btn-ghost" ${locked ? "disabled" : ""} onclick="window.extMtSave(false)">💾 ${esc(T("mt_btn_draft"))}</button>
        <button type="button" class="btn-primary" ${locked ? "disabled" : ""} onclick="window.extMtSave(true)">📤 ${esc(T("mt_btn_submit"))}</button>
      </div>
    </div>`;
  }
  window.extMtNew = function () {
    if (!S().token) { if (window.openLoginModal) window.openLoginModal(); return; }
    MT.form = emptyForm();
    renderMicroteaching();
    const c = document.getElementById("mtFormCard");
    if (c) c.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  window.extMtEdit = function (id) {
    const m = ((MT.data && MT.data.mine) || []).find(x => String(x.id) === String(id));
    if (!m) return;
    if (m.status === "evaluated") { toast(T("mt_edit_locked"), "error"); return; }
    MT.form = {
      id: m.id, title: m.title || "", lesson_form: m.lesson_form || "microteaching", objective: m.objective || "",
      stages: Array.isArray(m.stages) && m.stages.length ? m.stages.map(s => ({ name: s.name || "", minutes: s.minutes === undefined ? "" : s.minutes, activity: s.activity || "", technology_role: s.technology_role || "" })) : [],
      tool_name: m.tool_name || "", tool_rationale: m.tool_rationale || "", alternative_plan: m.alternative_plan || "",
      independent_share: m.independent_share === undefined || m.independent_share === null ? 33 : m.independent_share,
      reflection: m.reflection || "", shareTouched: true, errors: null, status: m.status
    };
    renderMicroteaching();
    const c = document.getElementById("mtFormCard");
    if (c) c.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  window.extMtCancel = function () { MT.form = null; renderMicroteaching(); };
  window.extMtSave = async function (submit) {
    const f = MT.form; if (!f || MT.busy) return;
    collectForm();
    const payload = {
      title: (f.title || "").trim(), lesson_form: f.lesson_form, objective: (f.objective || "").trim(),
      stages: f.stages.filter(s => (s.name || "").trim()).map(s => ({ name: (s.name || "").trim(), minutes: Number(s.minutes) || 0, activity: (s.activity || "").trim(), technology_role: (s.technology_role || "").trim() })),
      tool_name: (f.tool_name || "").trim(), tool_rationale: (f.tool_rationale || "").trim(), alternative_plan: (f.alternative_plan || "").trim(),
      independent_share: Math.max(0, Math.min(100, Math.round(Number(f.independent_share) || 0))),
      reflection: (f.reflection || "").trim() || null, submit: !!submit
    };
    MT.busy = true; f.errors = null;
    try {
      const { res, data } = await api(f.id ? `/student/microteaching/${encodeURIComponent(f.id)}` : "/student/microteaching", { method: f.id ? "PUT" : "POST", body: payload });
      if (res.status === 422 && Array.isArray(data.detail)) {
        f.errors = data.detail.map(e => {
          const loc = Array.isArray(e.loc) ? e.loc.filter(x => x !== "body").join(".") : "";
          return (loc ? loc + ": " : "") + (e.msg || "");
        });
        MT.busy = false; renderMicroteaching();
        const c = document.getElementById("mtFormCard"); if (c) c.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      if (!res.ok) { toast(errorText(data, T("mt_err_save")), "error"); MT.busy = false; return; }
      toast(submit ? T("mt_submitted_ok") : T("mt_saved"), "success");
      MT.form = null; MT.busy = false;
      await window.loadMicroteaching(true);
    } catch (_) { toast(T("ext_server_error"), "error"); MT.busy = false; }
  };

  // --- tengdoshlar baholashi
  function renderPeers() {
    const peers = (MT.data && MT.data.peers) || [];
    const rub = MT.rubric || [];
    const body = peers.length ? peers.map(p => {
      const review = p.already_reviewed ? `<span class="chip none">✓ ${esc(T("mt_already_reviewed"))}</span>` : `<div class="mt-review-form">
          ${rub.map(c => `<div class="mt-review-row">
            <div class="mt-review-crit"><b>${esc(c.name)}</b><div class="ext-hint">${esc(c.desc || "")}</div></div>
            <div class="mt-review-scale">${[1, 2, 3, 4, 5].map(v => `<label class="sill-radio"><input type="radio" name="pr_${esc(p.id)}_${esc(c.key)}" value="${v}"><span>${v}</span></label>`).join("")}</div>
          </div>`).join("")}
          <div class="mt-grid" style="margin-top:8px">
            <div class="mt-field mt-span-3"><label>${esc(T("mt_review_strengths"))}</label><textarea id="pr_${esc(p.id)}_str" rows="2" maxlength="1000"></textarea></div>
            <div class="mt-field mt-span-3"><label>${esc(T("mt_review_suggestions"))}</label><textarea id="pr_${esc(p.id)}_sug" rows="2" maxlength="1000" placeholder="You might consider…"></textarea></div>
          </div>
          <div class="mt-form-actions"><button type="button" class="btn-primary ext-btn-sm" onclick="window.extSubmitPeerReview(${jarg(p.id)})">📤 ${esc(T("mt_review_submit"))}</button></div>
        </div>`;
      return `<div class="mt-item">
        <div class="mt-item-head">
          <div class="mt-item-title">${esc(p.title)}</div>
          <div class="mt-item-chips"><span class="chip">${esc(T("mt_author"))}: ${esc(p.author || "—")}</span><span class="chip">${esc(formName(p.lesson_form))}</span>${statusChip(p.status)}</div>
        </div>
        <div class="mt-item-obj"><b>${esc(T("mt_objective_label"))}:</b> ${esc(p.objective || "")}</div>
        <div class="mt-item-obj"><b>${esc(T("mt_tool_label"))}:</b> ${esc(p.tool_name || "")}${p.tool_rationale ? ` — <i>${esc(p.tool_rationale)}</i>` : ""}</div>
        ${p.alternative_plan ? `<div class="mt-item-obj"><b>${esc(T("mt_f_alt"))}:</b> ${esc(p.alternative_plan)}</div>` : ""}
        ${stagesSummary(p.stages)}
        ${review}
      </div>`;
    }).join("") : `<div class="ext-note">${esc(T("mt_peers_empty"))}</div>`;
    return `<div class="card" id="mtPeersCard">
      <h3>${esc(T("mt_peers_title"))}</h3>
      <div class="why-box" style="margin:0 0 12px;padding:8px 12px">${esc(T("mt_peers_hint"))}</div>
      ${body}
    </div>`;
  }
  window.extSubmitPeerReview = async function (id) {
    if (MT.busy) return;
    const rub = MT.rubric || [];
    const rubric = {};
    for (const c of rub) {
      const el = document.querySelector(`input[name="pr_${id}_${c.key}"]:checked`);
      if (!el) { toast(T("mt_choose_all_criteria"), "error"); return; }
      rubric[c.key] = Number(el.value);
    }
    const g = sid => { const el = document.getElementById(sid); return el ? el.value.trim() : ""; };
    MT.busy = true;
    try {
      const { res, data } = await api(`/student/microteaching/${encodeURIComponent(id)}/review`, { method: "POST", body: { rubric, strengths: g(`pr_${id}_str`), suggestions: g(`pr_${id}_sug`) } });
      if (!res.ok) { toast(errorText(data, T("mt_err_save")), "error"); MT.busy = false; return; }
      toast(data.message || T("mt_review_sent"), "success");
      MT.busy = false;
      await window.loadMicroteaching(true);
    } catch (_) { toast(T("ext_server_error"), "error"); MT.busy = false; }
  };

  function renderMicroteaching() {
    const root = document.getElementById("microteachingRoot");
    if (!root) return;
    if (!S().token) { root.innerHTML = loginNotice(T("mt_login_notice")); return; }
    if (MT.error) { root.innerHTML = errorBox(MT.error, "window.loadMicroteaching(true)"); return; }
    if (!MT.loaded) { root.innerHTML = `<div class="ext-loading">⏳ ${esc(T("ext_loading"))}</div>`; return; }
    root.innerHTML = renderRulesCard() + renderMine() + renderForm() + renderPeers();
    if (MT.form) { renderStageRows(); updateShareWarn(); }
  }
  window.loadMicroteaching = async function (force) {
    const root = document.getElementById("microteachingRoot");
    if (!root) return;
    if (!S().token) { renderMicroteaching(); return; }
    if (MT.loaded && !force) { renderMicroteaching(); return; }
    MT.error = null;
    if (!MT.loaded) renderMicroteaching();
    try {
      const [r, l] = await Promise.all([MT.rubric && !force ? null : api("/student/microteaching/rubric"), api("/student/microteaching")]);
      if (r) {
        if (r.res.ok) { MT.rubric = r.data.rubric || []; MT.forms = Array.isArray(r.data.forms) ? r.data.forms : []; MT.rules = r.data.rules || []; }
      }
      if (!l.res.ok) { MT.error = errorText(l.data, T("mt_err_load")); }
      else {
        MT.data = l.data;
        if (!MT.rubric && Array.isArray(l.data.rubric)) MT.rubric = l.data.rubric;
        MT.loaded = true;
      }
    } catch (_) { MT.error = T("ext_server_error"); }
    renderMicroteaching();
  };

  // ------------------------------------------------------------------ til almashganda qayta chizish
  window.rerenderStudentExt = function () {
    renderBanners();
    renderPathNotice();
    if (document.getElementById("sillQuestionsContainer") && (SILL.spec || !S().token)) renderSill();
    if (document.getElementById("microteachingRoot")) { if (MT.form) collectForm(); renderMicroteaching(); }
  };

  // ------------------------------------------------------------------ showScreen o'rami va boshlash
  function afterShow(id) {
    const active = S().activeScreen;
    refreshExperimentBanners(false);
    if (id === "s_microteaching" && active === "s_microteaching") window.loadMicroteaching(false);
    if (id === "s_diagnostic" && active === "s_diagnostic") window.loadSill(false);
    if (id === "s_path" && active === "s_path") refreshPathArmNotice();
  }
  function installShowScreenHook() {
    const orig = window.showScreen;
    if (typeof orig !== "function" || orig.__extWrapped) return;
    const wrapped = function (id) {
      const r = orig.apply(this, arguments);
      try { afterShow(id); } catch (e) { console.warn("[student_ext] afterShow:", e); }
      return r;
    };
    wrapped.__extWrapped = true;
    window.showScreen = wrapped;
  }

  let lastToken = null;
  function onTokenChange() {
    const token = S().token || null;
    if (token === lastToken) return;
    lastToken = token;
    if (!token) { MT.loaded = false; MT.data = null; MT.form = null; SILL.result = null; SILL.answers = {}; SILL.history = null; PATH.arm = null; EXP.status = null; }
    refreshExperimentBanners(true);
    const active = S().activeScreen;
    if (active === "s_microteaching" || active === "s_diagnostic" || active === "s_path") afterShow(active);
    else { renderPathNotice(); if (document.getElementById("sillQuestionsContainer")) renderSill(); renderMicroteaching(); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    installShowScreenHook();
    lastToken = S().token || null;
    refreshExperimentBanners(true);
    const active = S().activeScreen;
    if (active === "s_microteaching" || active === "s_diagnostic" || active === "s_path") afterShow(active);
    else if (document.getElementById("sillQuestionsContainer") && !S().token) renderSill();
    setInterval(onTokenChange, 2500);
  });
})();
