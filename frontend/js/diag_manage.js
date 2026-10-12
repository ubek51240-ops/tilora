/* =====================================================================
   TILORA — O'qituvchi uchun Diagnostika testi va Anketa savollari banki
   (s_diag_manage ekrani). Backend: /api/teacher/diagnostic/* va /api/teacher/survey/*
   app.js dagi STATE, showToast, showScreen global'laridan foydalanadi.
   ===================================================================== */

(function () {
  const DM = {
    diag: [],
    survey: [],
    subjects: [],        // [{id, name, code, teacher_name, diag_count, survey_count}]
    general: { diag_count: 0, survey_count: 0 },
    isAdmin: false,
    subjectId: "",       // "" = umumiy, "__all__" = barchasi, aks holda fan ID
    loaded: false
  };
  const ALL = "__all__";

  function scopeQuery() {
    if (DM.subjectId === ALL) return "?all_subjects=true";
    if (DM.subjectId) return `?subject_id=${encodeURIComponent(DM.subjectId)}`;
    return "";
  }
  function scopeSubjectId() {
    return DM.subjectId && DM.subjectId !== ALL ? DM.subjectId : null;
  }
  function subjectName(id) {
    const sb = DM.subjects.find(x => x.id === id);
    return sb ? sb.name : "";
  }
  function getLang() {
    return localStorage.getItem('tilora_lang') || 'uz';
  }

  function subjectOptionsHtml(selected) {
    const l = getLang();
    const gen = l === "ru" ? "🌐 Общий" : (l === "en" ? "🌐 General" : "🌐 Umumiy");
    return `<option value="" ${!selected ? "selected" : ""}>${gen}</option>` +
      DM.subjects.map(sb => `<option value="${sb.id}" ${sb.id === selected ? "selected" : ""}>${esc(sb.name)}${DM.isAdmin && sb.teacher_name ? " — " + esc(sb.teacher_name) : ""}</option>`).join("");
  }

  const SKILL_LABELS = {
    uz: { listening: "🎧 Tinglab tushunish", reading: "📖 O'qish", writing: "✍️ Yozma nutq", speaking: "🗣️ Og'zaki nutq" },
    en: { listening: "🎧 Listening", reading: "📖 Reading", writing: "✍️ Writing", speaking: "🗣️ Speaking" },
    ru: { listening: "🎧 Аудирование", reading: "📖 Чтение", writing: "✍️ Письменная речь", speaking: "🗣️ Устная речь" }
  };
  const SKILL_COLORS = {
    listening: "var(--teal)", reading: "#2563EB", writing: "#7C3AED", speaking: "var(--clay)"
  };
  function getSkillMeta(skill) {
    const l = getLang();
    const map = SKILL_LABELS[l] || SKILL_LABELS.uz;
    return { label: map[skill] || skill, color: SKILL_COLORS[skill] || "var(--ink-2)" };
  }

  const DIM_LABELS = {
    uz: { anxiety: "😰 Xavotir (FLCAS)", load_capacity: "🧠 Yuklama sig'imi", pace: "⏱ Sur'at", autonomy: "🧭 Avtonomiya", motivation: "🔥 Motivatsiya" },
    en: { anxiety: "😰 Anxiety (FLCAS)", load_capacity: "🧠 Cognitive Load", pace: "⏱ Pace", autonomy: "🧭 Autonomy", motivation: "🔥 Motivation" },
    ru: { anxiety: "😰 Тревожность (FLCAS)", load_capacity: "🧠 Когнитивная нагрузка", pace: "⏱ Темп", autonomy: "🧭 Автономия", motivation: "🔥 Мотивация" }
  };
  const DIM_COLORS = {
    anxiety: "var(--clay)", load_capacity: "#2563EB", pace: "#7C3AED", autonomy: "var(--teal)", motivation: "#D97706"
  };
  function getDimMeta(dim) {
    const l = getLang();
    const map = DIM_LABELS[l] || DIM_LABELS.uz;
    return { label: map[dim] || dim, color: DIM_COLORS[dim] || "var(--ink-2)" };
  }

  function esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function authHeaders(json = true) {
    const h = {};
    if (STATE.token) h["Authorization"] = `Bearer ${STATE.token}`;
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  async function api(path, opts = {}) {
    const res = await fetch(`${STATE.apiBaseUrl}${path}`, opts);
    let data = null;
    try { data = await res.json(); } catch (_) { data = {}; }
    if (!res.ok) {
      const d = data && data.detail;
      throw new Error(typeof d === "string" ? d : (Array.isArray(d) ? d.map(x => x.msg).join("; ") : `Server xatosi (${res.status})`));
    }
    return data;
  }

  // ---------------------------------------------------------------
  // Yuklash va statistika
  // ---------------------------------------------------------------
  window.loadDiagManage = async function () {
    if (!STATE.token) {
      showToast("Bu bo'lim uchun o'qituvchi sifatida tizimga kiring.", "warning");
      return;
    }
    try {
      const subj = await api("/teacher/diagnostic/subjects", { headers: authHeaders(false) });
      DM.subjects = subj.subjects || [];
      DM.general = subj.general || { diag_count: 0, survey_count: 0 };
      DM.isAdmin = !!subj.is_admin;
      renderSubjectSelect();

      const q = scopeQuery();
      const [d, s] = await Promise.all([
        api(`/teacher/diagnostic/questions${q}`, { headers: authHeaders(false) }),
        api(`/teacher/survey/questions${q}`, { headers: authHeaders(false) })
      ]);
      DM.diag = d.questions || [];
      DM.survey = s.questions || [];
      DM.loaded = true;
      renderStatus("dmDiagStatusChip", d, "test savoli");
      renderStatus("dmSurveyStatusChip", s, "anketa savoli");
      renderDiagList();
      renderSurveyList();
    } catch (err) {
      showToast(`Savollar banki yuklanmadi: ${err.message}`, "error");
    }
  };

  function renderSubjectSelect() {
    const sel = document.getElementById("dmSubjectSelect");
    const hint = document.getElementById("dmSubjectHint");
    if (!sel) return;
    const g = DM.general;
    const l = getLang();
    const testWord = l === "ru" ? "тест" : (l === "en" ? "tests" : "test");
    const surveyWord = l === "ru" ? "анкета" : (l === "en" ? "surveys" : "anketa");
    const genLabel = l === "ru" ? "🌐 Общий — для всех предметов" : (l === "en" ? "🌐 General — for all courses" : "🌐 Umumiy — barcha fanlar uchun");
    const allLabel = l === "ru" ? "📋 Показать все (общие + все предметы)" : (l === "en" ? "📋 View all (general + all courses)" : "📋 Barchasini ko'rish (umumiy + barcha fanlar)");

    let html = `<option value="">${genLabel} (${g.diag_count} ${testWord} · ${g.survey_count} ${surveyWord})</option>`;
    html += DM.subjects.map(sb => {
      const who = DM.isAdmin && sb.teacher_name ? ` — ${esc(sb.teacher_name)}` : "";
      return `<option value="${sb.id}">📚 ${esc(sb.name)}${sb.code ? " (" + esc(sb.code) + ")" : ""}${who} · ${sb.diag_count} ${testWord} · ${sb.survey_count} ${surveyWord}</option>`;
    }).join("");
    html += `<option value="${ALL}">${allLabel}</option>`;
    sel.innerHTML = html;
    sel.value = DM.subjectId;
    if (hint) {
      if (DM.subjectId === ALL) {
        hint.innerHTML = l === "ru" 
          ? `Отображаются все вопросы. Чтобы добавить вопрос, сначала выберите предмет или «Общий».`
          : (l === "en" 
            ? `All questions are shown. To add a question, first select a course or "General".`
            : `Barcha savollar ko'rsatilmoqda. Yangi savol qo'shish uchun avval fanni yoki "Umumiy"ni tanlang.`);
      } else if (DM.subjectId) {
        hint.innerHTML = l === "ru"
          ? `Новые вопросы будут привязаны к предмету <b>"${esc(subjectName(DM.subjectId))}"</b>.`
          : (l === "en"
            ? `New questions will be linked to course <b>"${esc(subjectName(DM.subjectId))}"</b>.`
            : `Yangi savollar <b>"${esc(subjectName(DM.subjectId))}"</b> faniga biriktiriladi. Ro'yxatda shu fanning va umumiy savollar ko'rinadi.`);
      } else {
        hint.innerHTML = DM.subjects.length
          ? (l === "ru"
            ? `Новые вопросы будут <b>общими</b> (доступны при выборе любого предмета). Выберите предмет из списка, чтобы привязать вопрос к нему.`
            : (l === "en"
              ? `New questions will be <b>general</b> (appear for any course). Choose a course from the list to assign questions specifically.`
              : `Yangi savollar <b>umumiy</b> bo'ladi (har qanday fan tanlanganda ham chiqadi). Muayyan fan uchun savol qo'shish uchun ro'yxatdan fanni tanlang.`))
          : (l === "ru"
            ? `У вас пока нет добавленных предметов. Создайте предмет в разделе «Предметы и силлабус».`
            : (l === "en"
              ? `No courses found yet. Create a course in "Courses & Syllabus" first.`
              : `Sizda hali fan yo'q. "Fanlar & Sillabus" bo'limida fan yarating, so'ng savollarni shu fanga biriktirishingiz mumkin.`));
      }
    }
  }

  window.dmOnSubjectChange = function () {
    const sel = document.getElementById("dmSubjectSelect");
    DM.subjectId = sel ? sel.value : "";
    window.dmCloseDiagForm();
    window.dmCloseSurveyForm();
    window.loadDiagManage();
  };

  function requireScope() {
    if (DM.subjectId === ALL) {
      showToast("Avval yuqoridan fanni yoki \"Umumiy\"ni tanlang.", "warning");
      return false;
    }
    return true;
  }

  function subjectChip(q) {
    const sid = q.subject_id;
    const name = q.subject_name || subjectName(sid);
    const l = getLang();
    const gen = l === "ru" ? "🌐 Общий" : (l === "en" ? "🌐 General" : "🌐 Umumiy");
    const subjWord = l === "ru" ? "Предмет" : (l === "en" ? "Course" : "Fan");
    const who = DM.isAdmin && q.teacher_name ? `<span style="font-size:11px;color:var(--muted)">👤 ${esc(q.teacher_name)}</span>` : "";
    return `
      <span style="display:inline-flex;align-items:center;gap:4px;font-size:11.5px;padding:2px 8px;border-radius:10px;border:1px solid var(--line);background:${sid ? "var(--teal-soft)" : "var(--card)"};color:${sid ? "var(--teal)" : "var(--muted)"}">
        ${sid ? "📚 " + esc(name || subjWord) : gen}
      </span>${who}`;
  }

  function moveSelect(kind, q) {
    const l = getLang();
    const title = l === "ru" ? "Привязать к предмету" : (l === "en" ? "Assign to course" : "Fanga biriktirish");
    return `
      <select title="${title}" onchange="window.dmAssignSubject('${kind}','${q.id}',this.value)" style="font-size:11.5px;padding:3px 6px;border-radius:6px;border:1px solid var(--line);background:var(--surface);max-width:180px">
        ${subjectOptionsHtml(q.subject_id || "")}
      </select>`;
  }

  function renderStatus(id, summary, noun) {
    const el = document.getElementById(id);
    if (!el) return;
    const l = getLang();
    const isTest = id.includes("Diag");
    if (summary.using_defaults) {
      if (l === "ru") {
        el.textContent = `Студенты видят: ${summary.defaults_count} стандартных ${isTest ? "тестовых вопросов" : "вопросов анкеты"}`;
      } else if (l === "en") {
        el.textContent = `Students see: ${summary.defaults_count} default ${isTest ? "test questions" : "survey questions"}`;
      } else {
        el.textContent = `Talabalar ko'radi: ${summary.defaults_count} ta standart ${noun}`;
      }
      el.style.background = "";
    } else {
      if (l === "ru") {
        el.textContent = `Студенты видят: ${summary.active_count} ваших ${isTest ? "тестовых вопросов" : "вопросов анкеты"}`;
      } else if (l === "en") {
        el.textContent = `Students see: ${summary.active_count} of your ${isTest ? "test questions" : "survey questions"}`;
      } else {
        el.textContent = `Talabalar ko'radi: ${summary.active_count} ta sizning ${noun}ingiz`;
      }
      el.style.background = "var(--teal-soft)";
    }
  }

  // ---------------------------------------------------------------
  // A. DIAGNOSTIKA: ro'yxat
  // ---------------------------------------------------------------
  function renderDiagList() {
    const box = document.getElementById("dmDiagList");
    if (!box) return;
    const l = getLang();
    const isRu = (l === "ru");
    const isEn = (l === "en");
    if (!DM.diag.length) {
      const emptyMsg = isRu
        ? (DM.subjectId && DM.subjectId !== ALL 
            ? `Для предмета <b>"${esc(subjectName(DM.subjectId))}"</b> пока нет вопросов.`
            : `Вопросы пока не добавлены. Студенты видят <b>стандартные 8 вопросов</b>.`)
          + `<br><span style="font-size:12.5px">Используйте «➕ Новый вопрос», «📥 Импорт JSON» или «📋 Скопировать стандарт».</span>`
        : (isEn
          ? (DM.subjectId && DM.subjectId !== ALL
              ? `No questions yet for course <b>"${esc(subjectName(DM.subjectId))}"</b>.`
              : `No questions uploaded yet. Students currently see <b>8 default questions</b>.`)
            + `<br><span style="font-size:12.5px">Use "➕ New Question", "📥 JSON Import", or "📋 Copy Defaults".</span>`
          : (DM.subjectId && DM.subjectId !== ALL 
              ? `<b>"${esc(subjectName(DM.subjectId))}"</b> fani uchun hali savol yo'q (umumiy savollar ham yo'q).` 
              : `Hali savol yuklanmagan. Talabalar hozircha <b>standart 8 ta savolni</b> ko'rmoqda.`)
            + `<br><span style="font-size:12.5px">"➕ Yangi savol" orqali qo'lda kiriting, "📥 JSON import" bilan tayyor faylni yuklang yoki "📋 Standartni nusxalash" tugmasini bosing.</span>`);
      box.innerHTML = `
        <div style="text-align:center;padding:26px;color:var(--muted);border:1px dashed var(--line);border-radius:10px">
          ${emptyMsg}
        </div>`;
      return;
    }
    const disabledText = isRu ? "ОТКЛЮЧЕНО" : (isEn ? "DISABLED" : "O'CHIRILGAN");
    const enableText = isRu ? "Включить" : (isEn ? "Enable" : "Yoqish");
    const disableText = isRu ? "Отключить" : (isEn ? "Disable" : "O'chirib turish");
    const editText = isRu ? "✏️ Редактировать" : (isEn ? "✏️ Edit" : "✏️ Tahrirlash");
    const correctText = isRu ? "✔ верно" : (isEn ? "✔ correct" : "✔ to'g'ri");
    const upTitle = isRu ? "Вверх" : (isEn ? "Up" : "Yuqoriga");
    const downTitle = isRu ? "Вниз" : (isEn ? "Down" : "Pastga");

    box.innerHTML = DM.diag.map((q, i) => {
      const meta = getSkillMeta(q.skill);
      const inactive = !q.is_active;
      const audioHtml = q.audio_url
        ? `<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:8px 0;padding:8px 12px;background:var(--card);border:1px solid var(--line);border-radius:8px">
             <audio controls controlsList="nodownload" oncontextmenu="return false;" preload="none" src="${esc(q.audio_url)}" style="height:32px;max-width:280px"></audio>
             <span style="font-size:12px;color:var(--muted)">🎧 ${esc(q.audio_filename || q.audio_url.split("/").pop())}</span>
             <label style="font-size:12px;color:var(--teal);cursor:pointer;margin-left:auto">
               ${isRu ? "♻ Заменить" : (isEn ? "♻ Replace" : "♻ Almashtirish")} <input type="file" accept="audio/*,.mp3,.wav,.ogg,.m4a,.aac,.webm,.flac" style="display:none" onchange="window.dmUploadAudio('${q.id}', this)">
             </label>
             <button type="button" onclick="window.dmRemoveAudio('${q.id}')" style="font-size:12px;background:none;border:none;color:var(--clay);cursor:pointer">${isRu ? "✕ Удалить аудио" : (isEn ? "✕ Remove audio" : "✕ Audioni olib tashlash")}</button>
           </div>`
        : (q.is_audio
          ? `<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:8px 0;padding:8px 12px;background:rgba(217,119,6,0.08);border:1px solid rgba(217,119,6,0.3);border-radius:8px;font-size:12.5px">
               ⚠️ ${isRu ? "Аудиофайл не прикреплен" : (isEn ? "Audio file not attached" : "Audio fayl biriktirilmagan")}.
               ${q.audio_text ? `<button type="button" class="btn-primary" style="padding:4px 10px;font-size:12px;margin-left:6px" onclick="window.dmGenerateTts('${q.id}')">${isRu ? "🤖 Синтез речи ИИ" : (isEn ? "🤖 Generate AI Voice" : "🤖 AI ovoz yaratish")}</button>` : ""}
               <label style="color:var(--teal);cursor:pointer;font-weight:600;margin-left:auto">
                 ${isRu ? "📎 Загрузить аудио" : (isEn ? "📎 Upload audio" : "📎 Audio yuklash")} <input type="file" accept="audio/*,.mp3,.wav,.ogg,.m4a,.aac,.webm,.flac" style="display:none" onchange="window.dmUploadAudio('${q.id}', this)">
               </label>
             </div>`
          : "");
      return `
        <div style="background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:14px;${inactive ? "opacity:0.55" : ""}">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:8px">
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
              <span style="font-size:12px;color:var(--muted)">#${i + 1}</span>
              <span style="font-size:12px;font-weight:700;color:${meta.color};background:var(--card);padding:3px 10px;border-radius:12px;border:1px solid var(--line)">${meta.label} (${esc(q.cefr_level)})</span>
              ${subjectChip(q)}
              ${q.audio_url ? `<span style="font-size:11px;color:var(--teal)">🎧 audio</span>` : ""}
              ${inactive ? `<span style="font-size:11px;color:var(--clay);font-weight:700">${disabledText}</span>` : ""}
            </div>
            <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center">
              ${moveSelect('diagnostic', q)}
              <button type="button" title="${upTitle}" onclick="window.dmMove('diagnostic','${q.id}',-1)" style="font-size:12px;padding:4px 8px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">▲</button>
              <button type="button" title="${downTitle}" onclick="window.dmMove('diagnostic','${q.id}',1)" style="font-size:12px;padding:4px 8px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">▼</button>
              <button type="button" onclick="window.dmToggle('diagnostic','${q.id}')" style="font-size:12px;padding:4px 10px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">${inactive ? enableText : disableText}</button>
              <button type="button" onclick="window.dmEditDiag('${q.id}')" style="font-size:12px;padding:4px 10px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">${editText}</button>
              <button type="button" onclick="window.dmDeleteOne('diagnostic','${q.id}')" style="font-size:12px;padding:4px 10px;background:none;border:1px solid var(--clay);color:var(--clay);border-radius:6px;cursor:pointer">🗑</button>
            </div>
          </div>
          <p style="font-size:14px;font-weight:600;color:var(--ink);margin:0 0 6px;line-height:1.5">${esc(q.question)}</p>
          ${audioHtml}
          <div style="display:flex;flex-direction:column;gap:4px;margin-top:6px">
            ${(q.options || []).map((opt, oi) => `
              <div style="font-size:13px;padding:6px 10px;border-radius:6px;background:${oi === q.correct_index ? "rgba(16,185,129,0.10)" : "var(--card)"};border:1px solid ${oi === q.correct_index ? "var(--teal)" : "var(--line)"}">
                <b>${String.fromCharCode(65 + oi)})</b> ${esc(opt)} ${oi === q.correct_index ? `<span style="color:var(--teal);font-size:11px;font-weight:700;margin-left:6px">${correctText}</span>` : ""}
              </div>`).join("")}
          </div>
          ${q.rationale ? `<div style="font-size:12px;color:var(--muted);margin-top:8px">💡 ${esc(q.rationale)}</div>` : ""}
        </div>`;
    }).join("");
  }

  // ---------------------------------------------------------------
  // A. DIAGNOSTIKA: forma
  // ---------------------------------------------------------------
  function optionRow(value = "", checked = false) {
    const idx = document.querySelectorAll("#dmDiagOptions .dm-opt-row").length;
    const row = document.createElement("div");
    row.className = "dm-opt-row";
    row.style.cssText = "display:flex;gap:8px;align-items:center";
    row.innerHTML = `
      <input type="radio" name="dmDiagCorrect" title="To'g'ri javob" ${checked ? "checked" : ""}>
      <span style="font-size:12.5px;font-weight:700;width:18px">${String.fromCharCode(65 + idx)})</span>
      <input type="text" class="dm-opt-text" value="${esc(value)}" placeholder="Variant matni" style="flex:1;padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:var(--surface);font-size:13px">
      <button type="button" onclick="this.parentElement.remove(); window.dmRelabelOptions()" title="O'chirish" style="background:none;border:none;color:var(--muted);cursor:pointer;font-size:16px">✕</button>`;
    return row;
  }

  window.dmAddOptionRow = function (value = "", checked = false) {
    const box = document.getElementById("dmDiagOptions");
    if (!box) return;
    if (box.querySelectorAll(".dm-opt-row").length >= 6) {
      showToast("Ko'pi bilan 6 ta variant.", "warning");
      return;
    }
    box.appendChild(optionRow(value, checked));
  };

  window.dmRelabelOptions = function () {
    document.querySelectorAll("#dmDiagOptions .dm-opt-row").forEach((row, i) => {
      const lbl = row.querySelector("span");
      if (lbl) lbl.textContent = String.fromCharCode(65 + i) + ")";
    });
  };

  window.dmOnSkillChange = function () {
    const skill = document.getElementById("dmDiagSkill").value;
    const chk = document.getElementById("dmDiagIsAudio");
    if (skill === "listening" && chk && !chk.checked) {
      chk.checked = true;
      window.dmOnAudioToggle();
    }
  };

  window.dmOnAudioToggle = function () {
    const chk = document.getElementById("dmDiagIsAudio");
    const fields = document.getElementById("dmDiagAudioFields");
    if (fields) fields.style.display = chk && chk.checked ? "block" : "none";
    if (chk && chk.checked) { ensureTtsVoices(); window.dmOnAudioModeChange(); }
  };

  // Audio rejimi: "ai" (matn -> AI ovoz) yoki "file" (tayyor fayl)
  function audioMode() {
    const r = document.querySelector('input[name="dmDiagAudioMode"]:checked');
    return r ? r.value : "ai";
  }
  function setAudioMode(mode) {
    const r = document.querySelector(`input[name="dmDiagAudioMode"][value="${mode}"]`);
    if (r) r.checked = true;
    window.dmOnAudioModeChange();
  }
  window.dmOnAudioModeChange = function () {
    const ai = audioMode() === "ai";
    const fileRow = document.getElementById("dmDiagAudioFileRow");
    const ttsRow = document.getElementById("dmDiagTtsRow");
    const label = document.getElementById("dmDiagAudioTextLabel");
    if (fileRow) fileRow.style.display = ai ? "none" : "flex";
    if (ttsRow) ttsRow.style.display = ai ? "flex" : "none";
    const l = getLang();
    const isRu = l === "ru";
    const isEn = l === "en";
    if (label) label.textContent = ai
      ? (isRu ? "Текст для прослушивания студентом — ИИ озвучит" : (isEn ? "Listening text for students — AI will voice it" : "Talaba tinglaydigan matn — AI ovozga aylantiradi"))
      : (isRu ? "Текст аудио (транскрипция, необязательно) — если аудио не воспроизводится, браузер прочитает этот текст" : (isEn ? "Audio transcript (optional) — browser voice reads this if audio fails" : "Audio matni (transkripsiya, ixtiyoriy) — audio ochilmasa brauzer ovozi shu matnni o'qiydi"));
  };

  let TTS_VOICES_LOADED = false;
  async function ensureTtsVoices() {
    if (TTS_VOICES_LOADED) return;
    const sel = document.getElementById("dmDiagTtsVoice");
    if (!sel) return;
    try {
      const d = await api("/teacher/diagnostic/tts/voices", { headers: authHeaders(false) });
      sel.innerHTML = (d.voices || []).map(v => `<option value="${esc(v.id)}"${v.id === d.default ? " selected" : ""}>${esc(v.label)}</option>`).join("");
      TTS_VOICES_LOADED = true;
    } catch (err) {
      sel.innerHTML = `<option value="">Ovozlar yuklanmadi</option>`;
    }
  }

  window.dmPreviewTts = async function () {
    const text = document.getElementById("dmDiagAudioText").value.trim();
    if (!text) return showToast("Avval ovozga aylantiriladigan matnni yozing.", "warning");
    const btn = document.getElementById("dmDiagTtsPreviewBtn");
    const player = document.getElementById("dmDiagTtsPreview");
    btn.disabled = true;
    btn.textContent = "⏳ AI ovoz yaratilmoqda...";
    try {
      const res = await fetch(`${STATE.apiBaseUrl}/teacher/diagnostic/tts/preview`, {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ text, voice: document.getElementById("dmDiagTtsVoice").value || null })
      });
      if (!res.ok) {
        let d = {}; try { d = await res.json(); } catch (_) {}
        throw new Error(typeof d.detail === "string" ? d.detail : `Server xatosi (${res.status})`);
      }
      const blob = await res.blob();
      if (player.dataset.url) URL.revokeObjectURL(player.dataset.url);
      const url = URL.createObjectURL(blob);
      player.dataset.url = url;
      player.src = url;
      player.style.display = "inline-block";
      player.play().catch(() => {});
    } catch (err) {
      showToast(`Ovoz yaratilmadi: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "🔊 Tinglab ko'rish";
    }
  };

  function resetDiagForm() {
    const l = getLang();
    const isRu = l === "ru";
    const isEn = l === "en";
    document.getElementById("dmDiagEditId").value = "";
    document.getElementById("dmDiagFormTitle").textContent = isRu ? "Новый диагностический вопрос" : (isEn ? "New diagnostic question" : "Yangi diagnostika savoli");
    document.getElementById("dmDiagSkill").value = "reading";
    document.getElementById("dmDiagCefr").value = "B1";
    document.getElementById("dmDiagQuestion").value = "";
    document.getElementById("dmDiagRationale").value = "";
    document.getElementById("dmDiagIsAudio").checked = false;
    document.getElementById("dmDiagAudioText").value = "";
    document.getElementById("dmDiagAudioFile").value = "";
    document.getElementById("dmDiagAudioCurrent").textContent = "";
    const pv = document.getElementById("dmDiagTtsPreview");
    if (pv) { pv.pause(); pv.removeAttribute("src"); pv.style.display = "none"; }
    setAudioMode("ai");
    const box = document.getElementById("dmDiagOptions");
    box.innerHTML = "";
    for (let i = 0; i < 4; i++) box.appendChild(optionRow("", i === 0));
    window.dmOnAudioToggle();
  }

  window.dmOpenDiagForm = function () {
    if (!requireScope()) return;
    resetDiagForm();
    const f = document.getElementById("dmDiagForm");
    f.style.display = "block";
    f.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  window.dmCloseDiagForm = function () {
    document.getElementById("dmDiagForm").style.display = "none";
  };

  window.dmEditDiag = function (id) {
    const q = DM.diag.find(x => x.id === id);
    if (!q) return;
    resetDiagForm();
    const l = getLang();
    const isRu = l === "ru";
    const isEn = l === "en";
    document.getElementById("dmDiagEditId").value = q.id;
    document.getElementById("dmDiagFormTitle").textContent = isRu ? "Редактировать вопрос" : (isEn ? "Edit question" : "Savolni tahrirlash");
    document.getElementById("dmDiagSkill").value = q.skill;
    document.getElementById("dmDiagCefr").value = q.cefr_level || "B1";
    document.getElementById("dmDiagQuestion").value = q.question || "";
    document.getElementById("dmDiagRationale").value = q.rationale || "";
    document.getElementById("dmDiagIsAudio").checked = !!(q.is_audio || q.audio_url);
    document.getElementById("dmDiagAudioText").value = q.audio_text || "";
    document.getElementById("dmDiagAudioCurrent").textContent = q.audio_url
      ? (isRu
          ? `Текущее аудио: ${q.audio_filename || q.audio_url.split("/").pop()} (при сохранении измененного текста ИИ сгенерирует заново)`
          : isEn
          ? `Current audio: ${q.audio_filename || q.audio_url.split("/").pop()} (saving edited text will regenerate AI voice)`
          : `Joriy audio: ${q.audio_filename || q.audio_url.split("/").pop()} (matnni o'zgartirib saqlasangiz, AI qayta ovoz yaratadi)`)
      : (isRu ? "Аудио не прикреплено" : isEn ? "No audio attached" : "Audio biriktirilmagan");
    // Yuklangan fayl bo'lsa "file", AI ovozi yoki hech narsa bo'lmasa "ai" rejimi
    setAudioMode(q.audio_url && !(q.audio_filename || "").startsWith("AI ovoz") ? "file" : "ai");
    const box = document.getElementById("dmDiagOptions");
    box.innerHTML = "";
    (q.options || []).forEach((o, i) => box.appendChild(optionRow(o, i === q.correct_index)));
    window.dmOnAudioToggle();
    const f = document.getElementById("dmDiagForm");
    f.style.display = "block";
    f.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  window.dmSaveDiag = async function () {
    const editId = document.getElementById("dmDiagEditId").value;
    const rows = Array.from(document.querySelectorAll("#dmDiagOptions .dm-opt-row"));
    const options = rows.map(r => r.querySelector(".dm-opt-text").value.trim());
    const correct = rows.findIndex(r => r.querySelector('input[type="radio"]').checked);
    const isAudio = document.getElementById("dmDiagIsAudio").checked;
    const audioInput = document.getElementById("dmDiagAudioFile");
    const audioFile = audioInput && audioInput.files && audioInput.files[0];

    const payload = {
      skill: document.getElementById("dmDiagSkill").value,
      cefr_level: document.getElementById("dmDiagCefr").value,
      question: document.getElementById("dmDiagQuestion").value.trim(),
      options: options,
      correct_index: correct,
      rationale: document.getElementById("dmDiagRationale").value.trim() || null,
      is_audio: isAudio,
      audio_text: document.getElementById("dmDiagAudioText").value.trim() || null
    };
    // Tahrirlashda savolning o'z fani saqlanadi; yangi savol joriy tanlangan fanga biriktiriladi
    if (editId) {
      const cur = DM.diag.find(x => x.id === editId);
      payload.subject_id = cur ? (cur.subject_id || null) : scopeSubjectId();
    } else {
      payload.subject_id = scopeSubjectId();
    }

    if (!payload.question) return showToast("Savol matnini kiriting.", "warning");
    if (options.filter(Boolean).length < 2) return showToast("Kamida 2 ta variant kiriting.", "warning");
    if (options.some(o => !o)) return showToast("Bo'sh variant qatorlarini to'ldiring yoki o'chiring.", "warning");
    if (correct < 0) return showToast("To'g'ri javobni belgilang (radio tugma).", "warning");

    const mode = audioMode();
    const cur = editId ? DM.diag.find(x => x.id === editId) : null;
    const hadAudio = !!(cur && cur.audio_url);
    // AI rejimi: matn yozilgan va (yangi savol yoki matn o'zgargan yoki audio yo'q) bo'lsa ovoz yaratiladi
    const needTts = isAudio && mode === "ai" && !!payload.audio_text &&
      (!hadAudio || (cur.audio_text || "") !== payload.audio_text);
    if (isAudio && mode === "ai" && !payload.audio_text && !hadAudio)
      return showToast("AI ovozga aylantirish uchun tinglanadigan matnni yozing yoki audio fayl yuklang.", "warning");
    if (isAudio && mode === "file" && !audioFile && !hadAudio)
      return showToast("Audio fayl tanlang yoki 'Matn yozaman' rejimini tanlang.", "warning");

    const btn = document.getElementById("dmDiagSaveBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Saqlanmoqda...";
    try {
      const res = editId
        ? await api(`/teacher/diagnostic/questions/${editId}`, { method: "PUT", headers: authHeaders(), body: JSON.stringify(payload) })
        : await api(`/teacher/diagnostic/questions`, { method: "POST", headers: authHeaders(), body: JSON.stringify(payload) });
      const qid = res.question.id;

      let audioNote = "";
      if (isAudio && mode === "file" && audioFile) {
        const fd = new FormData();
        fd.append("file", audioFile);
        if (payload.audio_text) fd.append("audio_text", payload.audio_text);
        btn.textContent = "⏳ Audio yuklanmoqda...";
        await api(`/teacher/diagnostic/questions/${qid}/audio`, { method: "POST", headers: authHeaders(false), body: fd });
        audioNote = " Audio biriktirildi.";
      } else if (needTts) {
        btn.textContent = "⏳ AI ovoz yaratilmoqda...";
        const voice = document.getElementById("dmDiagTtsVoice").value || null;
        try {
          await api(`/teacher/diagnostic/questions/${qid}/tts`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ text: payload.audio_text, voice }) });
          audioNote = " AI ovoz yaratildi va biriktirildi.";
        } catch (err) {
          // Savol saqlangan; ovoz yaratilmasa talaba tomonida brauzer ovozi transkripsiyani o'qiydi
          showToast(`Savol saqlandi, lekin AI ovoz yaratilmadi: ${err.message}. Talabaga brauzer ovozi o'qib beradi.`, "warning");
        }
      }

      showToast(`✅ ${res.message}${audioNote}`, "success");
      window.dmCloseDiagForm();
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "💾 Saqlash";
    }
  };

  window.dmUploadAudio = async function (qid, input) {
    const file = input.files && input.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      showToast("⏳ Audio yuklanmoqda...", "info");
      const res = await api(`/teacher/diagnostic/questions/${qid}/audio`, { method: "POST", headers: authHeaders(false), body: fd });
      showToast(`✅ ${res.message}`, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Audio yuklanmadi: ${err.message}`, "error");
    } finally {
      input.value = "";
    }
  };

  window.dmGenerateTts = async function (qid) {
    const q = DM.diag.find(x => x.id === qid);
    if (!q || !q.audio_text) return showToast("Bu savolda ovozga aylantiriladigan matn yo'q. Savolni tahrirlab matn kiriting.", "warning");
    try {
      showToast("⏳ AI ovoz yaratilmoqda...", "info");
      const res = await api(`/teacher/diagnostic/questions/${qid}/tts`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ text: q.audio_text, voice: null }) });
      showToast(`✅ ${res.message}`, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`AI ovoz yaratilmadi: ${err.message}`, "error");
    }
  };

  window.dmRemoveAudio = async function (qid) {
    try {
      const res = await api(`/teacher/diagnostic/questions/${qid}/audio`, { method: "DELETE", headers: authHeaders(false) });
      showToast(res.message, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    }
  };

  window.dmImportDiag = async function (input) {
    const file = input.files && input.files[0];
    if (!file) { return; }
    if (!requireScope()) { input.value = ""; return; }
    const replace = DM.diag.length > 0 && window.confirm("Avvalgi savollar o'chirilib, faqat fayldagi savollar qolsinmi?\n\nOK — almashtirish\nBekor qilish — mavjudlarga qo'shish");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("replace", replace ? "true" : "false");
    if (scopeSubjectId()) fd.append("subject_id", scopeSubjectId());
    try {
      const res = await api(`/teacher/diagnostic/questions/import`, { method: "POST", headers: authHeaders(false), body: fd });
      showToast(`✅ ${res.message}`, "success");
      if (res.skipped && res.skipped.length) console.warn("Import: o'tkazib yuborilganlar", res.skipped);
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Import xatosi: ${err.message}`, "error");
    } finally {
      input.value = "";
    }
  };

  // ---------------------------------------------------------------
  // B. ANKETA: ro'yxat va forma
  // ---------------------------------------------------------------
  function renderSurveyList() {
    const box = document.getElementById("dmSurveyList");
    if (!box) return;
    const l = getLang();
    const isRu = l === "ru";
    const isEn = l === "en";

    if (!DM.survey.length) {
      const emptyMsg = isRu
        ? "Вопросы анкеты еще не загружены. Студенты сейчас видят <b>стандартные 12 вопросов FLCAS</b>."
        : (isEn
          ? "No survey questions uploaded yet. Students currently see the <b>standard 12 FLCAS questions</b>."
          : "Hali anketa savoli yuklanmagan. Talabalar hozircha <b>standart 12 ta FLCAS savolini</b> ko'rmoqda.");
      box.innerHTML = `
        <div style="text-align:center;padding:26px;color:var(--muted);border:1px dashed var(--line);border-radius:10px">
          ${emptyMsg}
        </div>`;
      return;
    }
    box.innerHTML = DM.survey.map((sq, i) => {
      const meta = getDimMeta(sq.dimension);
      const inactive = !sq.is_active;
      const weightLabel = isRu ? `вес ${Number(sq.weight).toFixed(1)}` : (isEn ? `weight ${Number(sq.weight).toFixed(1)}` : `vazn ${Number(sq.weight).toFixed(1)}`);
      const disabledBadge = inactive ? `<span style="font-size:11px;color:var(--clay);font-weight:700">${isRu ? "ОТКЛЮЧЕНО" : (isEn ? "DISABLED" : "O'CHIRILGAN")}</span>` : "";
      const toggleBtnText = inactive ? (isRu ? "Включить" : (isEn ? "Enable" : "Yoqish")) : (isRu ? "Отключить" : (isEn ? "Disable" : "O'chirib turish"));
      const editBtnText = isRu ? "✏️ Редактировать" : (isEn ? "✏️ Edit" : "✏️ Tahrirlash");

      return `
        <div style="background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px 14px;${inactive ? "opacity:0.55" : ""}">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:6px">
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
              <span style="font-size:12px;color:var(--muted)">#${i + 1}</span>
              <span style="font-size:12px;font-weight:700;color:${meta.color};background:var(--card);padding:3px 10px;border-radius:12px;border:1px solid var(--line)">${meta.label}</span>
              <span style="font-size:11.5px;color:var(--muted)">${weightLabel}</span>
              ${subjectChip(sq)}
              ${disabledBadge}
            </div>
            <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center">
              ${moveSelect('survey', sq)}
              <button type="button" onclick="window.dmMove('survey','${sq.id}',-1)" style="font-size:12px;padding:4px 8px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">▲</button>
              <button type="button" onclick="window.dmMove('survey','${sq.id}',1)" style="font-size:12px;padding:4px 8px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">▼</button>
              <button type="button" onclick="window.dmToggle('survey','${sq.id}')" style="font-size:12px;padding:4px 10px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">${toggleBtnText}</button>
              <button type="button" onclick="window.dmEditSurvey('${sq.id}')" style="font-size:12px;padding:4px 10px;background:none;border:1px solid var(--line);border-radius:6px;cursor:pointer">${editBtnText}</button>
              <button type="button" onclick="window.dmDeleteOne('survey','${sq.id}')" style="font-size:12px;padding:4px 10px;background:none;border:1px solid var(--clay);color:var(--clay);border-radius:6px;cursor:pointer">🗑</button>
            </div>
          </div>
          <p style="font-size:13.5px;color:var(--ink);margin:0;line-height:1.5"><b>${esc(sq.prompt_uz)}</b></p>
          ${sq.prompt_en ? `<p style="font-size:12.5px;color:var(--muted);margin:4px 0 0;font-style:italic">${esc(sq.prompt_en)}</p>` : ""}
        </div>`;
    }).join("");
  }

  function resetSurveyForm() {
    const l = getLang();
    const isRu = l === "ru";
    const isEn = l === "en";
    document.getElementById("dmSurveyEditId").value = "";
    document.getElementById("dmSurveyFormTitle").textContent = isRu ? "Новый вопрос анкеты" : (isEn ? "New survey question" : "Yangi anketa savoli");
    document.getElementById("dmSurveyDimension").value = "anxiety";
    document.getElementById("dmSurveyWeight").value = "1.0";
    document.getElementById("dmSurveyPromptUz").value = "";
    document.getElementById("dmSurveyPromptEn").value = "";
  }

  window.dmOpenSurveyForm = function () {
    if (!requireScope()) return;
    resetSurveyForm();
    const f = document.getElementById("dmSurveyForm");
    f.style.display = "block";
    f.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  window.dmCloseSurveyForm = function () {
    document.getElementById("dmSurveyForm").style.display = "none";
  };

  window.dmEditSurvey = function (id) {
    const sq = DM.survey.find(x => x.id === id);
    if (!sq) return;
    resetSurveyForm();
    const l = getLang();
    const isRu = l === "ru";
    const isEn = l === "en";
    document.getElementById("dmSurveyEditId").value = sq.id;
    document.getElementById("dmSurveyFormTitle").textContent = isRu ? "Редактировать вопрос анкеты" : (isEn ? "Edit survey question" : "Anketa savolini tahrirlash");
    document.getElementById("dmSurveyDimension").value = sq.dimension;
    document.getElementById("dmSurveyWeight").value = Number(sq.weight).toFixed(1);
    document.getElementById("dmSurveyPromptUz").value = sq.prompt_uz || "";
    document.getElementById("dmSurveyPromptEn").value = sq.prompt_en || "";
    const f = document.getElementById("dmSurveyForm");
    f.style.display = "block";
    f.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  window.dmSaveSurvey = async function () {
    const editId = document.getElementById("dmSurveyEditId").value;
    const payload = {
      dimension: document.getElementById("dmSurveyDimension").value,
      weight: parseFloat(document.getElementById("dmSurveyWeight").value) || 1.0,
      prompt_uz: document.getElementById("dmSurveyPromptUz").value.trim(),
      prompt_en: document.getElementById("dmSurveyPromptEn").value.trim() || null
    };
    if (editId) {
      const cur = DM.survey.find(x => x.id === editId);
      payload.subject_id = cur ? (cur.subject_id || null) : scopeSubjectId();
    } else {
      payload.subject_id = scopeSubjectId();
    }
    if (!payload.prompt_uz) return showToast("Anketa savolini (o'zbekcha) kiriting.", "warning");

    const btn = document.getElementById("dmSurveySaveBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Saqlanmoqda...";
    try {
      const res = editId
        ? await api(`/teacher/survey/questions/${editId}`, { method: "PUT", headers: authHeaders(), body: JSON.stringify(payload) })
        : await api(`/teacher/survey/questions`, { method: "POST", headers: authHeaders(), body: JSON.stringify(payload) });
      showToast(`✅ ${res.message}`, "success");
      window.dmCloseSurveyForm();
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "💾 Saqlash";
    }
  };

  window.dmImportSurvey = async function (input) {
    const file = input.files && input.files[0];
    if (!file) { return; }
    if (!requireScope()) { input.value = ""; return; }
    const replace = DM.survey.length > 0 && window.confirm("Avvalgi anketa savollari o'chirilib, faqat fayldagilar qolsinmi?\n\nOK — almashtirish\nBekor qilish — mavjudlarga qo'shish");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("replace", replace ? "true" : "false");
    if (scopeSubjectId()) fd.append("subject_id", scopeSubjectId());
    try {
      const res = await api(`/teacher/survey/questions/import`, { method: "POST", headers: authHeaders(false), body: fd });
      showToast(`✅ ${res.message}`, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Import xatosi: ${err.message}`, "error");
    } finally {
      input.value = "";
    }
  };

  // ---------------------------------------------------------------
  // Umumiy amallar (ikkala bank uchun)
  // ---------------------------------------------------------------
  window.dmToggle = async function (kind, id) {
    try {
      await api(`/teacher/${kind}/questions/${id}/toggle`, { method: "PATCH", headers: authHeaders(false) });
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    }
  };

  window.dmDeleteOne = async function (kind, id) {
    if (!window.confirm("Ushbu savol o'chirilsinmi?")) return;
    try {
      const res = await api(`/teacher/${kind}/questions/${id}`, { method: "DELETE", headers: authHeaders(false) });
      showToast(res.message, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    }
  };

  window.dmDeleteAll = async function (kind) {
    const list = kind === "diagnostic" ? DM.diag : DM.survey;
    if (!list.length) return showToast("Bank allaqachon bo'sh.", "info");
    const scopeLabel = DM.subjectId === ALL ? "BARCHA fanlar va umumiy" : (DM.subjectId ? `"${subjectName(DM.subjectId)}" faniga biriktirilgan` : "umumiy");
    if (!window.confirm(`${scopeLabel} savollar o'chirilsinmi?`)) return;
    try {
      const res = await api(`/teacher/${kind}/questions${scopeQuery()}`, { method: "DELETE", headers: authHeaders(false) });
      showToast(res.message, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    }
  };

  window.dmLoadDefaults = async function (kind) {
    if (!requireScope()) return;
    try {
      const res = await api(`/teacher/${kind}/questions/load-defaults${scopeQuery()}`, { method: "POST", headers: authHeaders(false) });
      showToast(`✅ ${res.message}`, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
    }
  };

  window.dmMove = async function (kind, id, dir) {
    const list = (kind === "diagnostic" ? DM.diag : DM.survey).slice();
    const i = list.findIndex(x => x.id === id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= list.length) return;
    [list[i], list[j]] = [list[j], list[i]];
    try {
      await api(`/teacher/${kind}/questions/reorder`, { method: "POST", headers: authHeaders(), body: JSON.stringify({ ids: list.map(x => x.id) }) });
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Tartiblashda xatolik: ${err.message}`, "error");
    }
  };

  window.dmAssignSubject = async function (kind, id, subjectId) {
    try {
      const res = await api(`/teacher/${kind}/questions/${id}/subject`, {
        method: "PATCH", headers: authHeaders(), body: JSON.stringify({ subject_id: subjectId || null })
      });
      showToast(`✅ ${res.message}`, "success");
      await window.loadDiagManage();
    } catch (err) {
      showToast(`Xatolik: ${err.message}`, "error");
      await window.loadDiagManage();
    }
  };

  window.dmExport = async function (kind) {
    try {
      const data = await api(`/teacher/${kind}/questions/export${scopeQuery()}`, { headers: authHeaders(false) });
      if (!data.length) return showToast("Eksport qilish uchun savol yo'q.", "info");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = kind === "diagnostic" ? "diagnostic_questions.json" : "survey_questions.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      showToast(`⬇ ${data.length} ta savol JSON faylga yuklab olindi.`, "success");
    } catch (err) {
      showToast(`Eksport xatosi: ${err.message}`, "error");
    }
  };

  function updateFormSelectOptions() {
    const l = getLang();
    const skillSel = document.getElementById("dmDiagSkill");
    if (skillSel) {
      const cur = skillSel.value;
      const skills = [
        { v: "listening", l: l === "ru" ? "🎧 Аудирование (аудио)" : (l === "en" ? "🎧 Listening (audio)" : "🎧 Tinglab tushunish (audio)") },
        { v: "reading", l: l === "ru" ? "📖 Чтение" : (l === "en" ? "📖 Reading" : "📖 O'qish") },
        { v: "writing", l: l === "ru" ? "✍️ Письменная речь" : (l === "en" ? "✍️ Writing" : "✍️ Yozma nutq") },
        { v: "speaking", l: l === "ru" ? "🗣️ Устная речь" : (l === "en" ? "🗣️ Speaking" : "🗣️ Og'zaki nutq") }
      ];
      skillSel.innerHTML = skills.map(s => `<option value="${s.v}" ${s.v === cur ? "selected" : ""}>${s.l}</option>`).join("");
    }
    const dimSel = document.getElementById("dmSurveyDimension");
    if (dimSel) {
      const cur = dimSel.value;
      const dims = [
        { v: "anxiety", l: l === "ru" ? "😰 Тревожность (FLCAS)" : (l === "en" ? "😰 Anxiety (FLCAS)" : "😰 Xavotir (FLCAS)") },
        { v: "load_capacity", l: l === "ru" ? "🧠 Когнитивная нагрузка" : (l === "en" ? "🧠 Cognitive Load" : "🧠 Yuklama sig'imi") },
        { v: "pace", l: l === "ru" ? "⏱ Темп усвоения" : (l === "en" ? "⏱ Pace of learning" : "⏱ O'zlashtirish sur'ati") },
        { v: "autonomy", l: l === "ru" ? "🧭 Автономия" : (l === "en" ? "🧭 Autonomy" : "🧭 Avtonomiya") },
        { v: "motivation", l: l === "ru" ? "🔥 Мотивация" : (l === "en" ? "🔥 Motivation" : "🔥 Motivatsiya") }
      ];
      dimSel.innerHTML = dims.map(d => `<option value="${d.v}" ${d.v === cur ? "selected" : ""}>${d.l}</option>`).join("");
    }
  }

  window.dmRerender = function () {
    updateFormSelectOptions();
    if (!DM.loaded) return;
    renderSubjectSelect();
    renderDiagList();
    renderSurveyList();
  };
})();
