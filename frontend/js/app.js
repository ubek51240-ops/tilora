/**
 * TILORA — Asosiy Frontend Mantiqi (App Engine)
 * To'rt qoidani to'liq ta'minlaydi va gibrid rejimda (lokal yoki API) ishlaydi.
 */

const STATE = {
  activeScreen: "s_profile",
  lessonStage: 1, // Mashg'ulot har doim 1-bosqichdan (Kirish) boshlanadi
  charCount: 0,
  wordCount: 0,
  lineCount: 0,
  selfRating: {},
  currentTheme: "light",
  apiBaseUrl: window.location.protocol.startsWith("http") ? (window.location.origin + "/api") : "http://127.0.0.1:8010/api",
  token: localStorage.getItem("tilora_token") || null,
  currentUser: (function () { try { return JSON.parse(localStorage.getItem("tilora_user") || "null"); } catch (_) { return null; } })(),
  diagAnswers: {},
  surveyAnswers: {}
};
window.STATE = STATE;

// ================================================================
// SESSIYA NAZORATI: token muddati tugasa (401), foydalanuvchini "kirgan" holatda
// qoldirmaymiz — xotira tozalanadi va qayta kirish oynasi ochiladi.
// ================================================================
function tokenIsExpired(token) {
  try {
    const part = token.split(".")[1];
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((part.length + 3) % 4));
    const payload = JSON.parse(json);
    return !!payload.exp && payload.exp * 1000 < Date.now();
  } catch (_) {
    return false;
  }
}

window.handleSessionExpired = function(reason) {
  if (STATE.sessionExpiredShown) return;
  STATE.sessionExpiredShown = true;
  localStorage.removeItem("tilora_token");
  localStorage.removeItem("tilora_user");
  localStorage.setItem("tilora_logged_out", "true");
  STATE.token = null;
  STATE.currentUser = null;
  if (typeof applyUserData === "function") applyUserData(null);
  if (typeof resetScreensOnLogout === "function") resetScreensOnLogout();
  if (typeof showToast === "function") showToast(reason || "⏳ Sessiya muddati tugagan. Iltimos, qayta tizimga kiring.", "warning");
  const err = document.getElementById("loginErrorMsg");
  if (err) { err.textContent = reason || "Sessiya muddati tugagan (token 1 kun amal qiladi). Qayta kiring."; err.style.display = "block"; }
  if (window.openLoginModal) window.openLoginModal();
};

(function wrapFetchFor401() {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function(input, init) {
    const res = await nativeFetch(input, init);
    try {
      const url = typeof input === "string" ? input : ((input && input.url) || "");
      const hadAuth = !!(init && init.headers && (init.headers["Authorization"] || init.headers["authorization"]));
      if (res.status === 401 && url.includes("/api/") && !url.includes("/auth/login") && (hadAuth || STATE.token)) {
        window.handleSessionExpired();
      }
    } catch (_) {}
    return res;
  };
})();

// DOM yuklanganda
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initTextareaListener();
  initScaleButtons();
  initTheme();
  initAccessibilityPrefs();
  checkAiStatus();
  initWifiShare();
  initAuth();
  // Auth tugagach, URL hashdan ekranni tiklash (foydalanuvchi roli yuklangach)
  restoreScreenFromHash();
  initDiagnostic();
  if (typeof window.renderLearningPath === "function") window.renderLearningPath();
});


// Qat'iy rollar va sahifalarga kirish huquqlari matritsasi (RBAC)
const SCREEN_PERMISSIONS = {
  "s_profile": ["student", "teacher", "admin", "researcher", "guest", "developer"],
  "s_path": ["student", "teacher", "admin", "developer"],
  "s_lesson": ["student", "teacher", "admin", "developer"],
  "s_diagnostic": ["student", "teacher", "admin", "developer"],
  "s_student_materials": ["student", "teacher", "admin", "guest", "developer"],
  "s_teacher": ["teacher", "admin", "student"],
  "s_subjects": ["teacher", "admin"],
  "s_diag_manage": ["teacher", "admin"],
  "s_research": ["researcher", "admin", "teacher", "guest", "developer"],
  "s_admin": ["admin"],
  "s_api_docs": ["developer", "admin"],
  "s_about": ["student", "teacher", "admin", "researcher", "guest", "developer"],
  "s_dynamics": ["student", "teacher", "admin", "developer"],
  "s_teacher_panel": ["teacher", "admin"]
};

function canAccessScreen(screenId, role) {
  const currentRole = role || (STATE.currentUser ? STATE.currentUser.role : "guest");
  const allowed = SCREEN_PERMISSIONS[screenId];
  if (!allowed) return true;
  return allowed.includes(currentRole);
}

function updateRoleNavigation(role) {
  const currentRole = role || (STATE.currentUser ? STATE.currentUser.role : "guest");
  
  document.querySelectorAll(".nav-role-group").forEach(group => {
    const rolesAttr = group.getAttribute("data-nav-roles") || "";
    const allowed = rolesAttr.split(",").map(r => r.trim());
    if (allowed.includes(currentRole)) {
      group.style.display = "";
    } else {
      group.style.display = "none";
    }
  });

  // Yuqori paneldagi "API Docs" tugmasini ham boshqa rollardan (student, teacher, researcher, guest) yashirish
  const topApiBtn = document.getElementById("btnTopApiDocs");
  if (topApiBtn) {
    if (currentRole === "developer" || currentRole === "admin") {
      topApiBtn.style.display = "inline-flex";
    } else {
      topApiBtn.style.display = "none";
    }
  }
}

// Mobil ekranlarda yon menyuni ochish / yopish
window.toggleMobileSidebar = function(open) {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (!sidebar) return;
  const shouldOpen = typeof open === "boolean" ? open : !sidebar.classList.contains("mobile-open");
  if (shouldOpen) {
    sidebar.classList.add("mobile-open");
    if (backdrop) backdrop.classList.add("active");
    document.body.style.overflow = "hidden"; // Orqa fon skrollini to'xtatish
  } else {
    sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
    document.body.style.overflow = "";
  }
};

// Ekranlar navigatsiyasi
function initNavigation() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetScreen = btn.getAttribute("data-screen");
      showScreen(targetScreen);
      // Agar mobil ekranda bo'lsa, menyuni avtomatik yopish
      if (window.innerWidth <= 768 && window.toggleMobileSidebar) {
        window.toggleMobileSidebar(false);
      }
    });
  });

  // Hash o'zgarganda ekranni yangilash (brauzer "back" tugmasi uchun)
  window.addEventListener("hashchange", restoreScreenFromHash);

  // Esc tugmasi bosilganda mobil menyuni yopish
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && window.toggleMobileSidebar) {
      window.toggleMobileSidebar(false);
    }
  });
}

function restoreScreenFromHash() {
  const hash = window.location.hash.slice(1);
  const validScreens = [
    "s_profile", "s_path", "s_lesson", "s_diagnostic", "s_student_materials",
    "s_teacher", "s_subjects", "s_diag_manage", "s_research", "s_admin", "s_api_docs"
  ];
  if (hash && validScreens.includes(hash)) {
    showScreen(hash);
  } else if (!hash) {
    // Hash bo'lmasa, default ekran (s_profile) ko'rsatish
    showScreen("s_profile");
  }
}

function showScreen(screenId) {
  const userRole = STATE.currentUser ? STATE.currentUser.role : "guest";

  // 1. Qat'iy xavfsizlik va rol tekshiruvi (Role-Based Access Control)
  if (!canAccessScreen(screenId, userRole)) {
    console.warn(`[XAVFSIZLIK TO'SIQ]: '${userRole}' roli '${screenId}' ekraniga kirishga urindi. Kirish taqiqlandi!`);
    
    if (!STATE.currentUser) {
      showToast("Ushbu bo'limdan foydalanish uchun avval profilga kiring!", "error");
      if (window.openLoginModal) window.openLoginModal();
    } else {
      showToast(`⛔ Ruxsat etilmagan: Sizning rolingiz (${userRole}) ushbu bo'limga kirish huquqiga ega emas!`, "error");
    }

    // Foydalanuvchining o'z ruxsatli ekraniga yo'naltirish
    const fallback = (userRole === "teacher") ? "s_teacher" : ((userRole === "admin") ? "s_admin" : ((userRole === "researcher") ? "s_research" : ((userRole === "developer") ? "s_api_docs" : "s_profile")));
    if (screenId !== fallback) {
      showScreen(fallback);
    }
    return;
  }

  if (screenId !== "s_diagnostic" && typeof window.stopListeningAudio === "function") {
    window.stopListeningAudio();
  }
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  const target = document.getElementById(screenId);
  if (target) {
    target.classList.add("active");
    STATE.activeScreen = screenId;
  }
  if (screenId === "s_diagnostic") {
    const diagContainer = document.getElementById("diagnosticQuestionsContainer");
    const surveyContainer = document.getElementById("surveyQuestionsContainer");
    if (typeof renderDiagnosticQuestions === "function" && diagContainer) {
      renderDiagnosticQuestions(diagContainer);
    }
    if (typeof renderSurveyQuestions === "function" && surveyContainer) {
      renderSurveyQuestions(surveyContainer);
    }
    // O'qituvchi yuklagan savollar bo'lsa, ularni token bilan yangilab olamiz
    if (typeof window.reloadDiagnosticQuestions === "function") {
      window.reloadDiagnosticQuestions();
    }
  }

  if (screenId === "s_diag_manage") {
    if (typeof window.loadDiagManage === "function") {
      window.loadDiagManage();
    }
  }

  if (screenId === "s_teacher") {
    if (typeof window.loadTeacherProposals === "function") {
      window.loadTeacherProposals();
    }
  }

  if (screenId === "s_research") {
    if (typeof window.initResearchDashboard === "function") {
      window.initResearchDashboard();
    }
  }

  if (screenId === "s_about" && typeof window.loadAboutScreen === "function") {
    window.loadAboutScreen();
  }
  if (screenId === "s_dynamics" && typeof window.loadDynamicsScreen === "function") {
    window.loadDynamicsScreen();
  }
  if (screenId === "s_teacher_panel" && typeof window.loadTeacherPanel === "function") {
    window.loadTeacherPanel();
  }

  if (screenId === "s_lesson" && typeof goToStage === "function") {
    goToStage(STATE.lessonStage || 1);
    // Tabaqalashtirish: talabaning varianti (A/B/C), sababi va variantga mos topshiriq
    if (typeof loadLessonVariant === "function") loadLessonVariant();
  }

  if (screenId === "s_path" && typeof window.renderLearningPath === "function") {
    window.renderLearningPath();
  }

  if (screenId === "s_subjects") {
    if (typeof window.loadTeacherSubjects === "function") {
      window.loadTeacherSubjects();
    }
    if (typeof window.loadTeacherMaterials === "function") {
      window.loadTeacherMaterials();
    }
  }

  if (screenId === "s_student_materials") {
    if (typeof window.loadStudentSubjectsAndMaterials === "function") {
      window.loadStudentSubjectsAndMaterials();
    }
  }

  if (screenId === "s_admin") {
    if (typeof window.loadAdminDashboard === "function") {
      window.loadAdminDashboard();
    }
  }

  if (screenId === "s_api_docs") {
    if (typeof window.initApiDocs === "function") {
      window.initApiDocs();
    }
  }

  // Nav tugmalarini sinxronlash
  document.querySelectorAll(".nav-btn").forEach(b => {
    if (b.getAttribute("data-screen") === screenId) {
      b.classList.add("active");
    } else {
      b.classList.remove("active");
    }
  });

  // URL hashni yangilash (sahifa yangilanganda holat saqlanishi uchun)
  if (window.location.hash.slice(1) !== screenId) {
    // Sahifa hali yuklanayotganda hash o'rnatilsa, brauzer #screenId bo'limiga avtomatik skroll qiladi
    // (sahifa boshi yuqori panel ostida qolib ketadi). Shuning uchun hash faqat yuklanish tugagach yoziladi.
    const setHash = () => history.replaceState(null, "", `#${screenId}`);
    if (document.readyState === "complete") setHash();
    else window.addEventListener("load", () => setTimeout(setHash, 0), { once: true });
  }
}

// 1-QOIDA: Mustaqil bosqichda AI vositalarini tekshirish (Server tomondan 403 AI_LOCKED)
async function triggerAILockNotice(toolName) {
  const noticeBox = document.getElementById("aiLockNotice");
  if (noticeBox) {
    noticeBox.style.display = "block";
    noticeBox.innerHTML = `<strong>Server tekshirmoqda...</strong> [403 AI_LOCKED so'rovi]`;
  }
  // Monitoring (metakognitiv sikl): yordamga urinish kuzatuv varaqasiga yoziladi
  if (STATE.token && typeof sendMonitorEvent === "function") sendMonitorEvent("help_request");

  try {
    const lockHeaders = {
      "Content-Type": "application/json",
      "X-Lesson-Stage": "independent",
      "X-AI-Locked": "true"
    };
    if (STATE.token) lockHeaders["Authorization"] = `Bearer ${STATE.token}`;
    const res = await fetch(`${STATE.apiBaseUrl}/ai/generate`, {
      method: "POST",
      headers: lockHeaders,
      body: JSON.stringify({ prompt: toolName })
    });

    if (res.status === 401) {
      if (noticeBox) noticeBox.innerHTML = `<strong style="color:var(--clay)">● AI vositalari yopiq:</strong> 1-qoida — mustaqil bosqichda yordam berilmaydi (AI endpointlari tizimga kirgan foydalanuvchilar uchun ham bu bosqichda 403 qaytaradi).`;
    } else if (res.status === 403) {
      const data = await res.json();
      const reason = data.detail?.details?.reason || "Talaba o'z javobini o'zi yaratmaguncha tayyor javob yoki generatsiya berilmaydi.";
      if (noticeBox) {
        noticeBox.innerHTML = `
          <strong style="color:var(--clay)">● 403 FORBIDDEN — AI_LOCKED (${toolName}):</strong><br>
          1-qoida talabiga binoan, mustaqil bajarish bosqichida tayyor generatsiya va yordam server tomonidan bloklangan.<br>
          <span style="font-size:11.5px;color:var(--ink-2);margin-top:4px;display:block"><em>Sabab: ${reason}</em></span>
        `;
      }
    }
  } catch (err) {
    if (noticeBox) {
      noticeBox.innerHTML = `
        <strong style="color:var(--clay)">● 403 AI_LOCKED (${toolName}):</strong><br>
        1-qoida talabiga binoan, mustaqil bajarish bosqichida sun'iy intellekt yordami yopiq. Avval o'z matningizni yarating!
      `;
    }
  }
}

// 2-BOSQICH: DeepSeek AI orqali namuna va leksik reja olish
async function requestAiScaffold() {
  const resBox = document.getElementById("aiScaffoldResult");
  const btn = document.getElementById("btnRequestAiScaffold");
  if (!resBox) return;

  resBox.style.display = "block";
  resBox.innerHTML = "⏳ DeepSeek AI dan ta'limiy ko'mak (scaffolding) olinmoqda...";
  if (btn) btn.disabled = true;

  try {
    if (!STATE.token) {
      resBox.innerHTML = "🔑 AI yordamchisidan foydalanish uchun avval profilga kiring.";
      if (window.openLoginModal) window.openLoginModal();
      return;
    }
    const scaffoldHeaders = { "Content-Type": "application/json", "Authorization": `Bearer ${STATE.token}` };
    // Serverda holat 'preparation' bo'lishi uchun bosqichni bildiramiz (AI qulfi serverda hal qilinadi)
    await fetch(`${STATE.apiBaseUrl}/lesson/5/stage/next?target_stage=preparation`, { method: "POST", headers: scaffoldHeaders }).catch(() => {});
    const res = await fetch(`${STATE.apiBaseUrl}/ai/generate`, {
      method: "POST",
      headers: scaffoldHeaders,
      body: JSON.stringify({
        prompt: "Yozma nutqni baholash mezonlari (rubrics, syntactic complexity, formative feedback)",
        context: "BuxDU talabalari uchun akademik insho yozishga tayyorgarlik"
      })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      resBox.innerHTML = `⚠️ ${escapeHtml(data.detail || ("Server xatosi (HTTP " + res.status + ")"))}`;
      return;
    }
    resBox.innerHTML = `<strong>🤖 DeepSeek (${escapeHtml(data.model || "deepseek-v4-flash-vision-exp")}):</strong>\n\n${escapeHtml(data.result)}`;
  } catch (e) {
    resBox.innerHTML = "⚠️ Serverga ulanishda xatolik yuz berdi.";
  } finally {
    if (btn) btn.disabled = false;
  }
}

// 4-BOSQICH: DeepSeek AI orqali chuqur tahlil
async function runDeepSeekAnalysis() {
  const outBox = document.getElementById("aiAnalysisOutput");
  const btn = document.getElementById("btnRunAiAnalysis");
  const textarea = document.getElementById("productionText");
  const text = textarea ? textarea.value.trim() : "";

  if (!outBox) return;
  if (text.length < 10) {
    outBox.style.display = "block";
    outBox.innerHTML = "⚠️ Tahlil qilish uchun avval 3-bosqichda matn yozishingiz kerak (kamida 10 ta belgi).";
    return;
  }

  outBox.style.display = "block";
  outBox.innerHTML = "⏳ DeepSeek AI matningizni to'liq o'qib, 4 ta mezon bo'yicha chuqur tahlil qilmoqda...";
  if (btn) btn.disabled = true;

  try {
    if (!STATE.token) {
      outBox.innerHTML = "🔑 AI tahlili uchun avval profilga kiring.";
      if (window.openLoginModal) window.openLoginModal();
      return;
    }
    const res = await fetch(`${STATE.apiBaseUrl}/ai/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${STATE.token}` },
      body: JSON.stringify({ prompt: text, context: "Yozma nutq baholash mezonlari (5-hafta)" })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      outBox.innerHTML = `⚠️ ${escapeHtml(data.detail || ("Server xatosi (HTTP " + res.status + ")"))}`;
      return;
    }
    outBox.innerHTML = `<strong>📊 DeepSeek & Kognitiv Tahlil Natijasi:</strong>\n\n${escapeHtml(data.analysis || data.message)}`;
  } catch (e) {
    outBox.innerHTML = "⚠️ Tahlil so'rovida server bilan aloqa xatoligi yuz berdi.";
  } finally {
    if (btn) btn.disabled = false;
  }
}

// AI Holatini tekshirish
async function checkAiStatus() {
  try {
    // AI holati faqat tizimga kirganlarga ko'rsatiladi (pullik kalit holati ommaviy emas)
    if (!STATE.token) return;
    const res = await fetch(`${STATE.apiBaseUrl}/ai/status`, { headers: { "Authorization": `Bearer ${STATE.token}` } });
    if (!res.ok) return;
    const data = await res.json();
    
    // Top-bar status
    const badge = document.getElementById("aiStatusBadge");
    if (badge) {
      if (data.status === "online" && data.quota_status === "active") {
        badge.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10B981"></span><span>DeepSeek (Faol)</span>`;
      } else if (data.status === "online" && data.quota_status === "insufficient_quota") {
        badge.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#F59E0B"></span><span>DeepSeek (0 balans)</span>`;
        badge.title = `api.b.ai hisobida balans 0. Real javoblar uchun balans to'ldirilishi kerak. Hozirda adaptiv fallback ishlamoqda.`;
      }
    }

    // Admin panel status
    const adminQuota = document.getElementById("adminQuotaStatus");
    if (adminQuota) {
      if (data.quota_status === "active") {
        adminQuota.textContent = "Faol (Balans mavjud)";
        adminQuota.style.color = "var(--teal)";
      } else if (data.quota_status === "insufficient_quota") {
        adminQuota.textContent = "Balans: 0 (To'ldirish kerak)";
        adminQuota.style.color = "var(--amber)";
      } else {
        adminQuota.textContent = data.status || "Noma'lum";
      }
    }
  } catch (e) {
    console.warn("AI status tekshirishda xatolik:", e);
  }
}


// Harflar, so'zlar va qatorlar jonli hisoblagichi
// 3-bosqich: yozish paytida lokal matn sifati tekshiruvi (AI emas, faqat hisob)
let _qualityTimer = null;
function scheduleQualityCheck(text) {
  clearTimeout(_qualityTimer);
  const stat = document.getElementById("qualityStat");
  const cnt = document.getElementById("qualityCount");
  if (!stat || !cnt) return;
  if (!text || text.trim().split(/\s+/).length < 3) { stat.style.display = "none"; return; }
  _qualityTimer = setTimeout(async () => {
    try {
      const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/text-quality`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content_text: text })
      });
      if (!res.ok) return;
      const q = await res.json();
      cnt.textContent = q.nonsense_count;
      stat.style.display = "inline";
      stat.style.color = q.nonsense_count === 0 ? "var(--teal)" : (q.level === "severe" || q.level === "high" ? "var(--clay)" : "var(--amber)");
      stat.title = q.nonsense_count === 0
        ? "Ma'nosiz harf ketma-ketliklari topilmadi"
        : `Lokal tekshiruv (AI emas): ${(q.suspicious_tokens || []).slice(0, 8).map(t => t.token).join(", ")}${q.nonsense_sentences && q.nonsense_sentences.length ? ` · ${q.nonsense_sentences.length} ta tushunarsiz gap` : ""}. Bular baholashda jarima sifatida hisobga olinadi.`;
    } catch (e) { /* jim */ }
  }, 700);
}

function initTextareaListener() {
  const textarea = document.getElementById("productionText");
  const charSpan = document.getElementById("charCount");
  const wordSpan = document.getElementById("wordCount");
  const lineSpan = document.getElementById("lineCount");
  const finishBtn = document.getElementById("btnFinishProduction");
  
  if (!textarea) return;
  
  function updateCounts() {
    const raw = textarea.value;
    const trimmed = raw.trim();
    
    // 1. Harflar/belgilar soni (har bir harf yozilganda 1, 2, 3... darhol oshadi)
    const chars = raw.length;
    // 2. So'zlar soni
    const words = trimmed ? trimmed.split(/\s+/).filter(Boolean).length : 0;
    // 3. Qatorlar soni
    const lines = raw ? raw.split("\n").length : 0;
    
    STATE.charCount = chars;
    STATE.wordCount = words;
    STATE.lineCount = lines;
    
    if (charSpan) charSpan.textContent = chars;
    if (wordSpan) wordSpan.textContent = words;
    if (lineSpan) lineSpan.textContent = lines;
    
    if (finishBtn) {
      // Kamida 10 ta harf yoki 3 ta so'z kiritilganda tugma faollashadi
      finishBtn.disabled = (chars < 10 && words < 3);
    }
  }

  textarea.addEventListener("input", updateCounts);
  textarea.addEventListener("keyup", updateCounts);
  textarea.addEventListener("paste", () => setTimeout(updateCounts, 50));
  updateCounts();
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Inline onclick="fn(${jsArg(x)})" uchun: JSON-string + HTML-escape (apostrof va qo'shtirnoq xavfsiz)
function jsArg(v) { return escapeHtml(JSON.stringify(v === undefined || v === null ? "" : String(v))); }
window.jsArg = jsArg;

// 3-bosqichdan 4-bosqichga (Tahlil) o'tish
async function finishProduction() {
  const textarea = document.getElementById("productionText");
  const text = textarea ? textarea.value.trim() : "";
  
  if (!text) {
    alert("Iltimos, avval mustaqil topshiriq matnini yozing.");
    return;
  }
  
  // Yangi matn: avvalgi AI bahosi eskirdi
  invalidateAiEvaluation();
  // Monitoring: mustaqil ish vaqti (tick) matn topshirilishidan OLDIN yuboriladi
  if (typeof sendMonitorTick === "function") await sendMonitorTick();
  // 4-bosqichga o'tish
  goToStage(4);
  
  // Matnni AI va L1 moduli orqali chuqur tahlil qilish
  await runL1InterferenceCheck(text);
}

async function runL1InterferenceCheck(text) {
  const container = document.getElementById("feedbackItemsList");
  if (!container) return;
  
  container.innerHTML = `
    <div style="padding:26px 20px;text-align:center;background:var(--paper-2);border:1px dashed var(--line);border-radius:8px">
      <div style="font-size:24px;margin-bottom:8px">🧠</div>
      <div style="font-weight:700;font-size:15px;color:var(--ink);margin-bottom:6px">Sun'iy intellekt va L1 moduli matningizni to'liq o'qimoqda...</div>
      <div style="font-size:13px;color:var(--muted)">Haqiqiy matningiz grammatik aniqlik, leksik boylik, mantiqiy ko'priklar va ona tili interferensiyasi bo'yicha tahlil qilinmoqda.</div>
    </div>
  `;
  
  try {
    const headers = { "Content-Type": "application/json" };
    if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;
    
    const words = text.split(/\s+/).filter(Boolean).length;
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/production`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        lesson_id: "5",
        content_text: text,
        word_count: words
      })
    });
    
    if (!res.ok) throw new Error("Server xatoligi: " + res.status);
    const data = await res.json();

    // Birinchi qoralama: tarix tozalanadi, keyin umumiy renderer (revise bilan bir xil yo'l)
    STATE.drafts = [];
    renderFeedbackResult(data, text);

  } catch (err) {
    console.error("Tahlil olishda xatolik:", err);
    container.innerHTML = `
      <div style="padding:16px;background:#FDF2F2;border:1px solid #F87171;border-radius:8px;font-size:13.5px;color:#991B1B">
        ⚠️ Server bilan bog'lanishda xatolik yuz berdi. Iltimos, server (start_server.py) ishlab turganini tekshiring.
      </div>
    `;
  }
}

// ============================================================
// 4-BOSQICH: umumiy natija renderi (production VA revise uchun bitta yo'l)
//   Write & Improve / ETS Criterion uslubi: xulosa chizig'i (taxminiy CEFR, topshiriqqa moslik),
//   so'z/gap darajasida belgilangan matn, qayta ishlash va versiyalar tarixi.
//   Dissertatsiya qoidasi saqlanadi: tuzatilgan matn HECH QACHON berilmaydi.
// ============================================================
STATE.drafts = [];           // [{n, score, rubric, word_count, l1_count, cefr, relevance, at}] (matnsiz)
STATE.lastDraftText = "";    // oxirgi topshirilgan qoralama matni (belgilash va revise uchun)
STATE.lastAnalysis = null;   // oxirgi /production yoki /revise javobi

function renderFeedbackResult(data, submittedText) {
  const container = document.getElementById("feedbackItemsList");
  if (!container || !data) return;
  const text = (typeof submittedText === "string") ? submittedText : (STATE.lastDraftText || "");
  STATE.lastDraftText = text;
  STATE.lastAnalysis = data;
  STATE.lastScoreData = data.score_data || null;
  STATE.feedbackDecisions = {};

  // 5-bosqich haqiqiy baholarini yangilash (oxirgi qoralama bo'yicha)
  if (data.score_data) updateStage5ActualRating(data.score_data);

  // Qoralama tarixi: revise javobida tayyor ro'yxat keladi; production'da birinchi yozuvni o'zimiz tuzamiz
  const spans = Array.isArray(data.spans) ? data.spans : [];
  if (Array.isArray(data.drafts) && data.drafts.length) {
    STATE.drafts = data.drafts.map(d => Object.assign({}, d));
  } else {
    const sd = data.score_data || {};
    STATE.drafts = [{
      n: data.draft_n || 1, score: sd.total_score, rubric: sd.rubric, word_count: text.split(/\s+/).filter(Boolean).length,
      l1_count: spans.length, cefr: (data.cefr_estimate_local || {}).level, relevance: (data.relevance || {}).score,
      at: new Date().toTimeString().slice(0, 8)
    }];
  }

  renderAnalysisSummaryStrip(data);
  renderTextHighlights(text, spans, data.feedback_items || []);
  renderFeedbackItems(container, data.feedback_items || [], !!data.ai_powered);
  renderReviseCard(text, data.draft_n || STATE.drafts.length);
  renderDraftHistory(STATE.drafts);
}
window.renderFeedbackResult = renderFeedbackResult;

function renderFeedbackItems(container, items, aiPowered) {
  if (!items.length) {
    container.innerHTML = `
      <div style="padding:20px;background:var(--paper-2);border:1px solid var(--line);border-radius:8px;font-size:14px;color:var(--teal)">
        ✅ <b>Ajoyib natija!</b> Matningizda jiddiy grammatik yoki ona tili interferensiyasi xatolari aniqlanmadi.
      </div>
    `;
    return;
  }

  const aiBadgeInfo = aiPowered
    ? `<div style="display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--teal);margin-bottom:12px;font-weight:600"><span>✨ DeepSeek AI talaba matnini to'liq o'qib chiqdi</span></div>`
    : `<div style="display:flex;align-items:center;gap:6px;font-size:12.5px;color:var(--muted);margin-bottom:12px"><span>🔍 Matn mazmuni va L1 interferensiyasi bo'yicha dinamik tahlil yakunlandi</span></div>`;

  container.innerHTML = aiBadgeInfo + items.map((issue, idx) => `
      <div class="fb-item ${escapeHtml(issue.cat || 'grammar')}" data-item-id="${escapeHtml(issue.id || idx)}" data-item-title="${escapeHtml(issue.title || '')}">
        <div class="fb-badge">${escapeHtml(issue.badge || "Tahlil")}</div>
        <div style="font-size:14.5px;font-weight:700;margin-bottom:4px;color:var(--ink)">${escapeHtml(issue.title)}</div>
        ${issue.matched_text ? `<div style="font-size:12.5px;color:var(--clay);margin-bottom:6px;background:rgba(217,119,87,0.08);padding:3px 8px;border-radius:4px;display:inline-block">Matndan parcha: "<b>${escapeHtml(issue.matched_text)}</b>"</div>` : ''}
        <div style="font-size:13px;color:var(--ink-2);margin-bottom:8px;line-height:1.6"><b>Sabab:</b> ${escapeHtml(issue.reason || issue.issue_reason || '')}</div>
        ${issue.suggestion ? `<div style="font-size:12.5px;color:var(--teal);margin-bottom:12px;line-height:1.5"><b>Tavsiya:</b> ${escapeHtml(issue.suggestion)}</div>` : ''}
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button class="btn-primary" style="padding:6px 14px;font-size:12px" onclick="setFeedbackDecision(this, true, ${jsArg(issue.id || idx)})">Roziman</button>
          <button class="btn-primary" style="padding:6px 14px;font-size:12px;background:var(--clay)" onclick="setFeedbackDecision(this, false, ${jsArg(issue.id || idx)})">Rozi emasman</button>
        </div>
        <!-- Metakognitiv BAHOLASH: izohni so'zsiz qabul qilmaslik — asos yoziladi -->
        <div style="margin-top:10px;border-top:1px dashed var(--line-2);padding-top:8px">
          <label style="font-size:12px;font-weight:600;color:var(--ink-2);display:block;margin-bottom:4px">Asos (nega qabul qildingiz / qilmadingiz?)</label>
          <textarea class="fb-justification" maxlength="1000" placeholder="Qisqa asos: izohning qaysi qismi to'g'ri, qaysi qismi menimcha noto'g'ri..." style="width:100%;min-height:52px;padding:8px;border:1px solid var(--line);border-radius:6px;font-size:12.5px;background:var(--surface);color:var(--ink);resize:vertical"></textarea>
          <div style="display:flex;gap:8px;align-items:center;margin-top:6px;flex-wrap:wrap">
            <button class="btn-primary" style="padding:5px 12px;font-size:12px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="saveFeedbackJustification(this, ${jsArg(issue.id || idx)})">Saqlash</button>
            <span class="fb-just-status" style="font-size:12px;color:var(--teal);font-weight:600"></span>
          </div>
        </div>
      </div>
    `).join("");
}

// ---- Xulosa chizig'i: taxminiy CEFR, topshiriqqa moslik, ball, L1, qoralama, delta ----
function deltaChip(label, v, suffix, lowerIsBetter) {
  if (v === null || v === undefined || isNaN(Number(v))) return "";
  const n = Number(v);
  const good = lowerIsBetter ? n < 0 : n > 0;
  const cls = n === 0 ? "delta-flat" : (good ? "delta-up" : "delta-down");
  const sign = n > 0 ? "+" : "";
  return `<span class="chip ${cls}" title="Oldingi qoralamaga nisbatan o'zgarish">${escapeHtml(label)}: ${sign}${escapeHtml(String(n))}${escapeHtml(suffix || "")}</span>`;
}

function renderAnalysisSummaryStrip(data) {
  const el = document.getElementById("analysisSummaryStrip");
  if (!el) return;
  const sd = data.score_data || {};
  const cefr = data.cefr_estimate_local || null;
  const rel = data.relevance || null;
  const draftN = data.draft_n || 1;
  const l1Count = Array.isArray(data.spans) ? data.spans.length : ((data.l1_pattern_ids || []).length);
  const delta = data.delta || null;
  const score = (sd.total_score !== undefined && sd.total_score !== null) ? Number(sd.total_score) : null;

  const cefrChip = cefr
    ? `<span class="chip cefr-chip" title="Lokal (AI'siz) deterministik baho — yakuniy darajani o'qituvchi belgilaydi">🎯 Taxminiy CEFR: ${escapeHtml(cefr.level || "—")} <span style="font-weight:500;opacity:.8">· ishonch: ${escapeHtml(cefr.confidence || "—")}</span></span>`
    : "";
  const scoreChip = score !== null
    ? `<span class="chip" style="background:var(--surface-2);border-color:var(--line);color:var(--ink);font-weight:700">Ball: ${escapeHtml(String(score))}/100</span>` : "";
  const l1Chip = `<span class="chip" style="background:${l1Count ? "var(--clay-soft)" : "var(--teal-soft)"};color:${l1Count ? "var(--clay)" : "var(--teal)"};border-color:${l1Count ? "#E4C6BC" : "#BCD9D3"};font-weight:600">L1 xatolar: ${escapeHtml(String(l1Count))}</span>`;

  const deltas = delta
    ? `<span style="font-size:11.5px;color:var(--muted);margin-left:4px">Δ oldingi qoralamaga nisbatan:</span>` +
      deltaChip("Ball", delta.score, "", false) + deltaChip("L1", delta.l1_count, "", true) + deltaChip("So'z", delta.words, "", false)
    : "";

  let relHtml = "";
  if (rel && rel.score !== undefined && rel.score !== null) {
    const rs = Math.max(0, Math.min(100, Number(rel.score) || 0));
    const hits = (rel.matched_keywords || []).map(k => `<span class="chip kw-hit">✓ ${escapeHtml(k)}</span>`).join("");
    const miss = (rel.missing_keywords || []).map(k => `<span class="chip kw-miss" title="Topshiriq mavzusiga oid, matnda uchramagan termin">${escapeHtml(k)}</span>`).join("");
    relHtml = `
      <div class="row" style="margin:12px 0 0">
        <div class="row-top"><b>Topshiriqqa moslik (prompt relevance)</b><span style="font-size:12.5px;font-weight:700;color:${rs >= 50 ? "var(--teal)" : "var(--clay)"}">${rs}%</span></div>
        <div class="track" role="progressbar" aria-valuenow="${rs}" aria-valuemin="0" aria-valuemax="100" aria-label="Topshiriqqa moslik"><div class="fill ${rs < 50 ? "warn" : ""}" style="width:${rs}%"></div></div>
        ${(hits || miss) ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;align-items:center">
          ${hits ? `<span style="font-size:11.5px;color:var(--muted)">Topilgan:</span>${hits}` : ""}
          ${miss ? `<span style="font-size:11.5px;color:var(--muted);margin-left:4px">Uchramagan:</span>${miss}` : ""}
        </div>` : ""}
        ${rel.note ? `<div style="font-size:11.5px;color:var(--muted);margin-top:6px">${escapeHtml(rel.note)}</div>` : ""}
      </div>`;
  }

  const reasons = cefr && Array.isArray(cefr.reasons) && cefr.reasons.length
    ? `<details style="margin-top:12px">
        <summary>Taxminiy CEFR qanday hisoblandi? (${escapeHtml(String(cefr.score !== undefined ? cefr.score : "—"))}/100 ball)</summary>
        <ul>${cefr.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
        ${cefr.note ? `<div style="font-size:12px;color:var(--amber);margin-top:8px;line-height:1.5">ℹ️ ${escapeHtml(cefr.note)}</div>` : ""}
      </details>` : "";

  el.style.display = "block";
  el.innerHTML = `
    <div class="card analysis-strip">
      <div class="strip-row">
        <span class="chip draft-badge">Qoralama ${escapeHtml(String(draftN))}</span>
        ${cefrChip}${scoreChip}${l1Chip}${deltas}
      </div>
      ${relHtml}
      ${reasons}
    </div>`;
}

// ---- So'z/gap darajasida belgilash: ASL matn kesimlari escape qilinadi, span'lar <mark> bilan o'raladi ----
function buildHighlightedHtml(text, spans, items) {
  const src = String(text || "");
  const matchedById = {};
  (items || []).forEach(it => { if (it && it.id && it.matched_text) matchedById[String(it.id)] = String(it.matched_text); });
  const valid = (spans || []).map(s => {
    const sp = Array.isArray(s && s.span) ? s.span : null;
    if (!sp) return null;
    let start = Number(sp[0]), end = Number(sp[1]);
    const id = String((s && s.id) || "");
    // Python (code point) va JS (UTF-16) indekslari farq qilsa: matched_text bo'yicha qayta joylash
    const mt = matchedById[id];
    if (mt && src.slice(start, end) !== mt) {
      const near = src.indexOf(mt, Math.max(0, start - 40));
      const idx = near >= 0 ? near : src.indexOf(mt);
      if (idx >= 0) { start = idx; end = idx + mt.length; }
    }
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start || end > src.length) return null;
    return { id, start, end, title: String((s && s.title) || "") };
  }).filter(Boolean).sort((a, b) => a.start - b.start || a.end - b.end);

  let html = "", pos = 0, used = 0;
  valid.forEach(s => {
    if (s.start < pos) return; // ustma-ust tushgan span o'tkazib yuboriladi
    html += escapeHtml(src.slice(pos, s.start));
    html += `<mark class="l1-mark" data-fb="${escapeHtml(s.id)}" title="${escapeHtml(s.title || "Izohga o'tish")}" tabindex="0" role="button" aria-label="Belgilangan joy: ${escapeHtml(s.title || "")}">${escapeHtml(src.slice(s.start, s.end))}</mark>`;
    pos = s.end; used++;
  });
  html += escapeHtml(src.slice(pos));
  return { html, count: used };
}

function renderTextHighlights(text, spans, items) {
  const card = document.getElementById("textHighlightCard");
  const box = document.getElementById("textHighlightBox");
  const empty = document.getElementById("textHighlightEmpty");
  if (!card || !box) return;
  const built = buildHighlightedHtml(text, spans, items);
  card.style.display = text ? "block" : "none";
  box.innerHTML = built.html;
  if (empty) empty.style.display = built.count ? "none" : "block";
  if (!box.dataset.bound) {
    box.dataset.bound = "1";
    const go = (e) => {
      const m = e.target && e.target.closest ? e.target.closest(".l1-mark") : null;
      if (!m) return;
      if (e.type === "keydown" && e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      focusFeedbackItem(m.getAttribute("data-fb"));
    };
    box.addEventListener("click", go);
    box.addEventListener("keydown", go);
  }
}

function focusFeedbackItem(itemId) {
  const list = document.getElementById("feedbackItemsList");
  if (!list || itemId === null || itemId === undefined) return;
  let target = null;
  list.querySelectorAll(".fb-item[data-item-id]").forEach(el => { if (!target && el.getAttribute("data-item-id") === String(itemId)) target = el; });
  if (!target) { showToast("Bu belgi uchun alohida izoh topilmadi — izohlar ro'yxatini ko'ring.", "info"); return; }
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.remove("fb-flash");
  void target.offsetWidth; // animatsiyani qayta boshlash
  target.classList.add("fb-flash");
  setTimeout(() => target.classList.remove("fb-flash"), 1700);
}
window.focusFeedbackItem = focusFeedbackItem;

// ---- Qayta ishlash (revise) kartasi ----
function renderReviseCard(text, draftN) {
  const card = document.getElementById("reviseCard");
  const ta = document.getElementById("reviseText");
  const chip = document.getElementById("reviseDraftChip");
  const msg = document.getElementById("reviseMsg");
  const btn = document.getElementById("btnRevise");
  if (!card || !ta) return;
  card.style.display = "block";
  ta.value = text || "";
  if (chip) chip.textContent = `Qoralama ${draftN}`;
  if (msg) { msg.style.display = "none"; msg.textContent = ""; }
  const limitReached = (STATE.drafts || []).length >= 5;
  if (btn) {
    btn.disabled = limitReached;
    btn.textContent = limitReached ? "Qoralamalar chegarasi (5) — refleksiyaga o'ting" : "♻️ Qayta ishlab, qayta topshirish";
  }
  if (!STATE.token && msg) {
    msg.style.display = "block"; msg.style.background = "var(--amber-soft)"; msg.style.color = "var(--amber)";
    msg.textContent = "Mehmon rejimi: qayta ishlash tarixi faqat tizimga kirgan talaba uchun saqlanadi.";
  }
  updateReviseCounter();
}

function updateReviseCounter() {
  const ta = document.getElementById("reviseText");
  const c = document.getElementById("reviseCounter");
  const ch = document.getElementById("reviseChanged");
  if (!ta) return;
  const v = ta.value;
  const words = v.trim() ? v.trim().split(/\s+/).length : 0;
  if (c) c.textContent = `${words} so'z · ${v.length} belgi`;
  if (ch) {
    const changed = v.trim() !== (STATE.lastDraftText || "").trim();
    ch.textContent = changed ? "✎ o'zgartirildi" : "matn hali o'zgarmagan";
    ch.style.color = changed ? "var(--teal)" : "var(--muted)";
  }
}
window.updateReviseCounter = updateReviseCounter;

async function submitRevision() {
  const ta = document.getElementById("reviseText");
  const btn = document.getElementById("btnRevise");
  const msg = document.getElementById("reviseMsg");
  const container = document.getElementById("feedbackItemsList");
  if (!ta) return;
  const text = ta.value.trim();
  const showMsg = (t, kind) => {
    if (!msg) return;
    msg.style.display = "block";
    msg.style.background = kind === "error" ? "#FDF2F2" : "var(--teal-soft)";
    msg.style.border = kind === "error" ? "1px solid #F87171" : "1px solid #BCD9D3";
    msg.style.color = kind === "error" ? "#991B1B" : "var(--teal-deep)";
    msg.textContent = t;
  };
  if (text.length < 10) { showMsg("Matn juda qisqa. Kamida bir necha gap yozing.", "error"); ta.focus(); return; }
  if (text === (STATE.lastDraftText || "").trim()) { showMsg("Matn o'zgarmagan. Izohlar asosida kamida bitta tuzatish kiriting.", "error"); ta.focus(); return; }
  if (!STATE.token) { showMsg("Qayta topshirish uchun tizimga kiring.", "error"); if (window.openLoginModal) window.openLoginModal(); return; }

  if (btn) { btn.disabled = true; btn.textContent = "⏳ Tahlil qilinmoqda..."; }
  if (msg) msg.style.display = "none";
  if (container) {
    container.innerHTML = `<div style="padding:22px 20px;text-align:center;background:var(--paper-2);border:1px dashed var(--line);border-radius:8px">
      <div style="font-size:22px;margin-bottom:6px">♻️</div>
      <div style="font-weight:700;font-size:14.5px;color:var(--ink)">Qayta ishlangan qoralama tahlil qilinmoqda...</div>
      <div style="font-size:12.5px;color:var(--muted)">Avvalgi versiya bilan solishtirish uchun natijalar saqlanadi.</div></div>`;
  }
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/revise`, {
      method: "POST", headers: lessonAuthHeaders(), body: JSON.stringify({ content_text: text })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = (typeof data.detail === "string") ? data.detail
        : (Array.isArray(data.detail) && data.detail[0] && data.detail[0].msg) ? data.detail[0].msg
        : `Qayta topshirishda xatolik (HTTP ${res.status}).`;
      showMsg(detail, "error");
      // Avvalgi izohlar ro'yxatini tiklash
      if (STATE.lastAnalysis) renderFeedbackItems(container, STATE.lastAnalysis.feedback_items || [], !!STATE.lastAnalysis.ai_powered);
      return;
    }
    // Server tomonida self_rating tozalandi — 5-bosqich holati ham tozalanadi; AI bahosi eskirdi
    resetStage5SelfRating();
    invalidateAiEvaluation();
    // 5-bosqich (ai-evaluate) oxirgi qoralama bilan ishlashi uchun 3-bosqich maydoni ham yangilanadi
    const prod = document.getElementById("productionText");
    if (prod) { prod.value = text; prod.dispatchEvent(new Event("input", { bubbles: true })); }

    renderFeedbackResult(data, text);
    const d = data.delta || {};
    const dScore = (d.score === undefined || d.score === null) ? "" : ` Ball: ${d.score > 0 ? "+" : ""}${d.score}.`;
    showToast(`♻️ Qoralama ${data.draft_n || ""} qabul qilindi.${dScore}`, "success");
    const strip = document.getElementById("analysisSummaryStrip");
    if (strip) strip.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    showMsg("Serverga ulanishda xatolik: qayta topshirilmadi.", "error");
    if (STATE.lastAnalysis && container) renderFeedbackItems(container, STATE.lastAnalysis.feedback_items || [], !!STATE.lastAnalysis.ai_powered);
  } finally {
    if (btn && btn.textContent.indexOf("⏳") === 0) { btn.disabled = false; btn.textContent = "♻️ Qayta ishlab, qayta topshirish"; }
  }
}
window.submitRevision = submitRevision;

// 5-bosqich: o'z bahosi holatini tozalash (server revise'da self_rating ni None qiladi)
function resetStage5SelfRating() {
  STATE.selfRating = {};
  document.querySelectorAll("#stageContent5 .scale-group .scale-btn").forEach(b => { b.classList.remove("active"); b.disabled = false; });
  ["content", "grammar", "lexis", "coherence"].forEach(c => { const el = document.getElementById(`aiCritBadge_${c}`); if (el) el.innerHTML = ""; });
  const rows = document.getElementById("aiEvalCompareRows"); if (rows) rows.innerHTML = "";
  const gapBox = document.getElementById("ratingGapBox"); if (gapBox) { gapBox.style.display = "none"; gapBox.innerHTML = ""; }
  const done = document.getElementById("lessonDoneBox"); if (done) { done.style.display = "none"; done.innerHTML = ""; }
  if (typeof checkReflectionReadiness === "function") checkReflectionReadiness();
}
window.resetStage5SelfRating = resetStage5SelfRating;

// ---- Versiyalar tarixi: jadval + mini sparkline ----
function draftSparklineSvg(scores) {
  const vals = (scores || []).map(v => (v === null || v === undefined || isNaN(Number(v))) ? null : Number(v));
  const pts = vals.map((v, i) => v === null ? null : { i, v }).filter(Boolean);
  if (!pts.length) return "";
  const W = 150, H = 36, padX = 6, padY = 5;
  const n = vals.length;
  const x = (i) => n === 1 ? W / 2 : padX + i * (W - 2 * padX) / (n - 1);
  const y = (v) => padY + (100 - Math.max(0, Math.min(100, v))) * (H - 2 * padY) / 100;
  const line = pts.length >= 2 ? `<polyline fill="none" stroke="var(--teal)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="${pts.map(p => `${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ")}"/>` : "";
  const dots = pts.map(p => `<circle cx="${x(p.i).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="4" fill="${p.v >= 60 ? "var(--teal)" : "var(--clay)"}" stroke="var(--card)" stroke-width="1.5"><title>Qoralama ${p.i + 1}: ${p.v}</title></circle>`).join("");
  const last = pts[pts.length - 1];
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Qoralamalar ballari: ${pts.map(p => p.v).join(", ")}" style="display:block;overflow:visible">
    <line x1="${padX}" x2="${W - padX}" y1="${y(60).toFixed(1)}" y2="${y(60).toFixed(1)}" stroke="var(--amber)" stroke-dasharray="3 3" stroke-width="1" opacity=".7"/>
    ${line}${dots}</svg><span style="font-weight:700;color:var(--ink)">${last.v}</span>`;
}

function renderDraftHistory(drafts) {
  const box = document.getElementById("draftHistoryBox");
  const tbl = document.getElementById("draftHistoryTable");
  const spark = document.getElementById("draftSparkline");
  const cmp = document.getElementById("draftCompareBox");
  if (!box || !tbl) return;
  const list = (drafts || []).slice().sort((a, b) => (a.n || 0) - (b.n || 0));
  if (!list.length) { box.style.display = "none"; return; }
  box.style.display = "block";
  if (cmp) { cmp.style.display = "none"; cmp.innerHTML = ""; }
  if (spark) spark.innerHTML = list.length ? `<span>Ballar:</span>${draftSparklineSvg(list.map(d => d.score))}` : "";
  const fmt = (v) => (v === null || v === undefined || v === "") ? "—" : escapeHtml(String(v));
  const dCell = (cur, prev, lowerIsBetter) => {
    if (prev === null || prev === undefined || cur === null || cur === undefined) return `<span style="color:var(--muted)">—</span>`;
    const d = Number(cur) - Number(prev);
    const good = lowerIsBetter ? d < 0 : d > 0;
    const color = d === 0 ? "var(--muted)" : (good ? "var(--teal)" : "var(--clay)");
    return `<span style="font-weight:700;color:${color}">${d > 0 ? "+" : ""}${escapeHtml(String(d))}</span>`;
  };
  const rows = list.map((d, i) => {
    const prev = i > 0 ? list[i - 1] : null;
    const isLast = i === list.length - 1;
    return `<tr class="${isLast ? "current" : ""}">
      <td style="font-weight:700">${fmt(d.n)}${isLast ? ` <span class="chip" style="font-size:10px;padding:1px 7px;background:var(--teal);color:#fff;border-color:var(--teal)">joriy</span>` : ""}</td>
      <td style="font-family:var(--mono)">${fmt(d.at)}</td>
      <td style="text-align:center">${fmt(d.word_count)}</td>
      <td style="text-align:center;color:${(d.l1_count || 0) > 0 ? "var(--clay)" : "var(--teal)"};font-weight:600">${fmt(d.l1_count)}</td>
      <td style="text-align:center;font-weight:700;color:${(d.score !== null && d.score !== undefined && d.score >= 60) ? "var(--teal)" : "var(--clay)"}">${fmt(d.score)}</td>
      <td style="text-align:center">${fmt(d.cefr)}</td>
      <td style="text-align:center">${(d.relevance === null || d.relevance === undefined) ? "—" : escapeHtml(String(d.relevance)) + "%"}</td>
      <td style="text-align:center">${prev ? dCell(d.score, prev.score, false) : `<span style="color:var(--muted)">—</span>`}</td>
      <td style="text-align:right">${prev ? `<button type="button" class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="openDraftCompare(${Number(d.n) || (i + 1)})">⇄ Solishtirish</button>` : `<span style="font-size:11px;color:var(--muted)">birinchi</span>`}</td>
    </tr>`;
  }).join("");
  tbl.innerHTML = `<div style="overflow-x:auto;-webkit-overflow-scrolling:touch"><table class="draft-table">
    <thead><tr><th>№</th><th>Vaqt</th><th style="text-align:center">So'z</th><th style="text-align:center">L1</th><th style="text-align:center">Ball</th><th style="text-align:center">CEFR</th><th style="text-align:center">Moslik</th><th style="text-align:center">Δ ball</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <div style="font-size:11.5px;color:var(--muted);margin-top:6px">Δ — oldingi qoralamaga nisbatan ball o'zgarishi. Birinchi va oxirgi qoralama farqi refleksiya yozuvida "o'sish" sifatida saqlanadi.</div>`;
}

// ---- Yonma-yon solishtirish: N-1 va N qoralama matnlari (GET /lesson/5/drafts) ----
function wordDiffHtml(text, otherText, cls) {
  const other = new Set(String(otherText || "").toLowerCase().match(/[\p{L}\p{N}'’-]+/gu) || []);
  return String(text || "").split(/(\s+)/).map(tok => {
    if (!tok || /^\s+$/.test(tok)) return escapeHtml(tok);
    const core = (tok.toLowerCase().match(/[\p{L}\p{N}'’-]+/gu) || [""])[0];
    return (core && !other.has(core)) ? `<mark class="${cls}">${escapeHtml(tok)}</mark>` : escapeHtml(tok);
  }).join("");
}

async function openDraftCompare(n) {
  const cmp = document.getElementById("draftCompareBox");
  if (!cmp) return;
  if (!STATE.token) { showToast("Solishtirish uchun tizimga kiring.", "warning"); return; }
  cmp.style.display = "block";
  cmp.innerHTML = `<div style="padding:12px;color:var(--muted);font-size:12.5px">⏳ Qoralamalar yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/drafts`, { headers: lessonAuthHeaders(false) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`);
    const drafts = (data.drafts || []).slice().sort((a, b) => (a.n || 0) - (b.n || 0));
    const cur = drafts.find(d => Number(d.n) === Number(n));
    const prev = drafts.find(d => Number(d.n) === Number(n) - 1);
    if (!cur || !prev) { cmp.innerHTML = `<div style="padding:12px;color:var(--muted);font-size:12.5px">Solishtirish uchun ikkita qoralama topilmadi.</div>`; return; }
    const head = (d, latest) => `<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:8px">
        <b style="font-size:13px">${latest ? "Qoralama" : "Qoralama"} ${escapeHtml(String(d.n))} ${latest ? "(yangi)" : "(oldingi)"}</b>
        <span style="font-size:11.5px;color:var(--muted)">${escapeHtml(String(d.word_count ?? "—"))} so'z · L1 ${escapeHtml(String(d.l1_count ?? "—"))} · ball ${escapeHtml(String(d.score ?? "—"))} · ${escapeHtml(String(d.cefr || "—"))}</span>
      </div>`;
    cmp.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
        <b style="font-size:13px">⇄ Yonma-yon solishtirish: ${escapeHtml(String(prev.n))} → ${escapeHtml(String(cur.n))}</b>
        <button type="button" class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="document.getElementById('draftCompareBox').style.display='none'">Yopish ✕</button>
      </div>
      <div class="draft-compare-grid">
        <div class="draft-compare-col">${head(prev, false)}<div class="draft-text">${wordDiffHtml(prev.text, cur.text, "diff-del")}</div></div>
        <div class="draft-compare-col latest">${head(cur, true)}<div class="draft-text">${wordDiffHtml(cur.text, prev.text, "diff-add")}</div></div>
      </div>
      <div style="font-size:11.5px;color:var(--muted);margin-top:8px">Belgilash taxminiy (so'z darajasida): <mark class="diff-del">olib tashlangan</mark> · <mark class="diff-add">yangi qo'shilgan</mark>. Tizim hech qanday tuzatilgan variant bermaydi — ikkala matn ham sizniki.</div>`;
    cmp.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    cmp.innerHTML = `<div style="padding:12px;background:#FDF2F2;border:1px solid #F87171;border-radius:8px;font-size:12.5px;color:#991B1B">⚠️ Qoralamalarni yuklab bo'lmadi: ${escapeHtml(e.message || "")}</div>`;
  }
}
window.openDraftCompare = openDraftCompare;

function invalidateAiEvaluation() {
  STATE.aiEvaluation = null;
  STATE.aiEvaluationPromise = null;
  STATE.aiEvaluationText = "";
}

function updateStage5ActualRating(scoreData) {
  const titleEl = document.getElementById("actualScoreTitle");
  const detailsEl = document.getElementById("actualRubricDetails");
  if (titleEl && scoreData.total_score !== undefined) {
    titleEl.textContent = `Haqiqiy ob'ektiv natija: ${scoreData.total_score} / 100`;
  }
  if (detailsEl && scoreData.rubric) {
    const r = scoreData.rubric;
    detailsEl.textContent = `Grammatika: ${r.grammar}/5 · Lug'at: ${r.lexis}/5 · Mazmun: ${r.content}/5 · Izchillik: ${r.coherence}/5`;
  }
}

async function setFeedbackDecision(btn, accepts, itemId) {
  const parent = btn.parentElement;
  const item = (btn.closest ? btn.closest(".fb-item") : null);
  const title = item ? (item.getAttribute("data-item-title") || "") : "";
  const justEl = item ? item.querySelector(".fb-justification") : null;
  const justification = justEl ? justEl.value.trim() : "";
  STATE.feedbackDecisions[String(itemId)] = { accepts: Boolean(accepts), title };

  parent.innerHTML = accepts
    ? `<span style="font-size:12px;color:var(--teal);font-weight:600">✓ Rozilik bildirildi (Qaror sizniki)</span>`
    : `<span style="font-size:12px;color:var(--clay);font-weight:600">✗ E'tiroz qayd etildi (Sabab yozildi)</span>`;

  try {
    await fetch(`${STATE.apiBaseUrl}/feedback/response`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        item_id: String(itemId || "fb_item"),
        student_accepts: Boolean(accepts),
        student_note: accepts ? "Talaba fikrga qo'shildi" : "Talaba o'z varianti to'g'ri deb hisobladi"
      })
    });
  } catch (e) {
    // Jim saqlash
  }

  // Metakognitiv BAHOLASH: qaror (va bo'lsa asos) mashg'ulot holatiga yoziladi
  const ok = await submitFeedbackDecision(itemId, title, accepts, justification);
  const status = item ? item.querySelector(".fb-just-status") : null;
  if (status && ok && justification) status.textContent = "✓ Qaror va asos saqlandi";
}

async function submitFeedbackDecision(itemId, title, accepts, justification) {
  if (!STATE.token) return false;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/feedback-decision`, {
      method: "POST",
      headers: lessonAuthHeaders(),
      body: JSON.stringify({
        item_id: String(itemId || "fb_item").slice(0, 100),
        title: String(title || "").slice(0, 300),
        accepts: Boolean(accepts),
        justification: String(justification || "").slice(0, 1000)
      })
    });
    return res.ok;
  } catch (_) {
    return false;
  }
}

async function saveFeedbackJustification(btn, itemId) {
  const item = btn.closest ? btn.closest(".fb-item") : null;
  if (!item) return;
  const dec = STATE.feedbackDecisions[String(itemId)];
  const justEl = item.querySelector(".fb-justification");
  const status = item.querySelector(".fb-just-status");
  const justification = justEl ? justEl.value.trim() : "";
  if (!dec) { showToast("Avval 'Roziman' yoki 'Rozi emasman' tanlang, so'ng asosni saqlang.", "warning"); return; }
  if (!justification) { showToast("Asosni yozing: nega qabul qildingiz yoki qilmadingiz?", "warning"); if (justEl) justEl.focus(); return; }
  if (!STATE.token) { if (status) status.textContent = "Mehmon rejimi: asos faqat shu sahifada saqlanadi."; return; }
  btn.disabled = true;
  const ok = await submitFeedbackDecision(itemId, dec.title, dec.accepts, justification);
  btn.disabled = false;
  if (status) status.textContent = ok ? "✓ Asos saqlandi" : "⚠️ Saqlanmadi (server)";
}

// 4-QOIDA: Metakognitiv refleksiya va o'zini baholash
function initScaleButtons() {
  document.querySelectorAll(".scale-group").forEach(group => {
    const criterion = group.getAttribute("data-criterion");
    group.querySelectorAll(".scale-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        group.querySelectorAll(".scale-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        STATE.selfRating[criterion] = parseInt(btn.textContent);
        
        // Qo'lda tanlanganda badge ni yangilash
        const badgeEl = document.getElementById(`aiCritBadge_${criterion}`);
        if (badgeEl) {
          badgeEl.innerHTML = `<span style="font-size:11.5px;color:var(--ink);font-weight:600">Sizning bahongiz: ${btn.textContent}/5</span>`;
        }

        checkReflectionReadiness();

        // Agar barcha 4 mezon belgilangan bo'lsa, serverga o'z bahosini saqlash
        const criteria = ["content", "grammar", "lexis", "coherence"];
        const allRated = criteria.every(c => STATE.selfRating[c] !== undefined);
        if (allRated) {
          try {
            const headers = { "Content-Type": "application/json" };
            if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;
            await fetch(`${STATE.apiBaseUrl}/lesson/5/self-rating`, {
              method: "POST",
              headers: headers,
              body: JSON.stringify({ ratings: STATE.selfRating })
            });
          } catch (e) {
            console.warn("Self-rating saqlashda xatolik:", e);
          }
        }
      });
    });
  });
}

function checkReflectionReadiness() {
  const criteria = ["content", "grammar", "lexis", "coherence"];
  const allRated = criteria.every(c => STATE.selfRating[c] !== undefined);
  
  const hiddenBox = document.getElementById("lockedActualRating");
  const revealedBox = document.getElementById("revealedActualRating");
  
  if (allRated) {
    if (hiddenBox) hiddenBox.style.display = "none";
    if (revealedBox) revealedBox.style.display = "block";
    renderAiEvaluation();
  } else {
    if (hiddenBox) hiddenBox.style.display = "block";
    if (revealedBox) revealedBox.style.display = "none";
  }
}

// 5-bosqich: Mashg'ulotni yakunlash va natijalarni saqlash
async function finishLessonStage5() {
  const gapInput = document.getElementById("reflectionGapInput");
  const goalInput = document.getElementById("reflectionGoalInput");
  const btn = document.getElementById("btnFinishLessonStage5");

  const gap = gapInput ? gapInput.value.trim() : "";
  const goal = goalInput ? goalInput.value.trim() : "";

  if (!gap || !goal) {
    showToast("Refleksiya uchun farq sababini va keyingi maqsadingizni o'z so'zlaringiz bilan yozing.", "warning");
    (gap ? goalInput : gapInput)?.focus();
    return;
  }

  if (btn) btn.disabled = true;
  const doneBox = document.getElementById("lessonDoneBox");

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/reflection`, {
      method: "POST",
      headers: lessonAuthHeaders(),
      body: JSON.stringify({
        gap_explanation: gap,
        next_goal: goal,
        comparison_note: STATE.comparisonNote || null
      })
    });
    const data = await res.json().catch(() => ({}));

    if (res.ok && data.record_id) {
      showToast("🎉 Mashg'ulot yakunlandi va yozuv saqlandi. Dinamika bo'limida ko'rishingiz mumkin.", "success");
      if (doneBox) {
        doneBox.style.display = "block";
        doneBox.innerHTML = `
          <div style="margin-bottom:8px"><b>✓ Mashg'ulot yakunlandi.</b> ${escapeHtml(data.message || "")}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn-primary" style="background:var(--teal)" onclick="showScreen('s_dynamics')">📈 Dinamikani ko'rish</button>
            <button class="btn-primary" style="background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="showScreen('s_profile')">Profilga o'tish</button>
          </div>`;
      }
      if (typeof resetMetacognitiveState === "function") resetMetacognitiveState();
      if (typeof loadStudentProfile === "function") loadStudentProfile();
    } else if (!res.ok) {
      const msg = (typeof data.detail === "string") ? data.detail
        : (res.status === 401 ? "Natijani saqlash uchun avval tizimga kiring (mehmon rejimida yozuv saqlanmaydi)." : `Refleksiyani saqlashda xatolik (HTTP ${res.status}).`);
      showToast(msg, "error");
      if (doneBox && res.status === 401) {
        doneBox.style.display = "block";
        doneBox.innerHTML = `<b>Mehmon rejimi:</b> refleksiya yozuvi saqlanmadi. Dinamika va kuzatuv paneli faqat tizimga kirgan talaba uchun yuritiladi.`;
      }
    } else {
      showToast("Refleksiya qabul qilindi.", "info");
    }
  } catch (err) {
    showToast("Serverga ulanishda xatolik: refleksiya yuborilmadi.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Bosqichlar bo'yicha harakatlanish
function goToStage(stageNum) {
  STATE.lessonStage = stageNum;
  document.querySelectorAll(".step-tab").forEach(tab => {
    const st = parseInt(tab.getAttribute("data-stage"));
    tab.classList.remove("active", "passed");
    if (st === stageNum) tab.classList.add("active");
    if (st < stageNum) tab.classList.add("passed");
  });
  
  document.querySelectorAll(".stage-content").forEach(c => c.style.display = "none");
  const targetContent = document.getElementById(`stageContent${stageNum}`);
  if (targetContent) targetContent.style.display = "block";

  // Monitoring: mustaqil bosqich vaqti faqat 3-bosqichda hisoblanadi
  if (typeof startStage3Timer === "function") {
    if (stageNum === 3) startStage3Timer(); else stopStage3Timer();
  }

  // 1-QOIDA: bosqichni serverga bildiramiz — mustaqil bosqichda AI qulfi serverda yoqiladi,
  // mijoz sarlavha yoki UI orqali uni chetlab o'ta olmaydi.
  if (STATE.token) {
    const stageNames = { 1: "intro", 2: "preparation", 3: "independent", 4: "analysis", 5: "reflection" };
    const target = stageNames[stageNum] || "intro";
    fetch(`${STATE.apiBaseUrl}/lesson/5/stage/next?target_stage=${target}`, {
      method: "POST", headers: { "Authorization": `Bearer ${STATE.token}` }
    }).catch(() => {});
  }

  // 5-bosqich: AI bahosini fonda tayyorlab qo'yamiz (o'z bahosi qo'yilgach ochiladi).
  // Talabaning o'z bahosi AVTOMATIK TO'LDIRILMAYDI (4-qoida).
  if (stageNum === 5) {
    prefetchAiEvaluation();
    checkReflectionReadiness();
  }
}

// ============================================================
// METAKOGNITIV SIKL (dissertatsiya 3.3):
//   Rejalashtirish (1-bosqich) -> Monitoring (3-bosqich) -> Baholash (4-bosqich) -> Refleksiya (5-bosqich)
// + Tabaqalashtirish (variant A/B/C), dialog mashqi (2-bosqich), qiyosiy usul (4-bosqich)
// ============================================================
STATE.lessonSkill = "writing";
STATE.lessonVariant = null;
STATE.lessonInfo = null;
STATE.lessonTask = null;
STATE.lessonTaskCache = {};
STATE.lessonPlan = null;
STATE.lessonPlanSaved = false;
STATE.comparisonNote = null;
STATE.feedbackDecisions = {};
STATE.dialogMessages = [];
STATE.stage3Accum = 0;
STATE.stage3EnteredAt = null;
STATE.stage3Timer = null;
STATE.listenPlayback = { count: 0, max: null, speed: 1, inProgress: false, bound: false };

const VARIANT_LABELS = { A: "Kengaytirilgan variant", B: "Asosiy variant", C: "Ko'maklashtirilgan variant" };
const SCAFFOLD_LABELS = { full: "to'liq ko'mak", partial: "qisman ko'mak", none: "ko'maksiz" };

function lessonAuthHeaders(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (STATE.token) h["Authorization"] = `Bearer ${STATE.token}`;
  return h;
}

// ---- Tabaqalashtirish: variant va topshiriq ----
async function loadLessonVariant() {
  if (!STATE.token) { renderVariantBanner(null); return; }
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5`, { headers: lessonAuthHeaders(false) });
    if (!res.ok) return;
    const data = await res.json();
    STATE.lessonInfo = data;
    STATE.lessonVariant = data.variant || null;
    if (data.plan && data.plan.goal) {
      STATE.lessonPlanSaved = true;
      STATE.lessonPlan = data.plan;
      const g = document.getElementById("planGoalInput");
      const s = document.getElementById("planStrategyInput");
      if (g && !g.value) g.value = data.plan.goal || "";
      if (s && !s.value) s.value = data.plan.strategy || "";
      showPlanSaved(data.plan);
    }
    renderVariantBanner(data);
    const uiSkill = STATE.lessonSkill || data.skill || "writing";
    if (data.task && data.task.skill === uiSkill) {
      STATE.lessonTaskCache[`${uiSkill}:${STATE.lessonVariant || ""}`] = data.task;
      applyTaskToUI(data.task);
    } else {
      refreshLessonTask(uiSkill);
    }
  } catch (e) {
    console.warn("Variant yuklanmadi:", e);
  }
}

async function refreshLessonTask(skill) {
  skill = skill || STATE.lessonSkill || "writing";
  const v = STATE.lessonVariant;
  const key = `${skill}:${v || ""}`;
  if (STATE.lessonTaskCache[key]) { applyTaskToUI(STATE.lessonTaskCache[key]); return; }
  try {
    const q = `?skill=${encodeURIComponent(skill)}` + (v ? `&variant=${encodeURIComponent(v)}` : "");
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/task${q}`, { headers: lessonAuthHeaders(false) });
    if (!res.ok) return;
    const task = await res.json();
    STATE.lessonTaskCache[key] = task;
    applyTaskToUI(task);
  } catch (_) {}
}

function applyTaskToUI(task) {
  if (!task) return;
  STATE.lessonTask = task;
  const desc = document.getElementById("lessonTaskPromptDesc");
  if (desc && task.prompt) {
    const v = task.variant || STATE.lessonVariant;
    desc.innerHTML = `<b>Savol${v ? ` (${escapeHtml(v)}-variant)` : ""}:</b> ${escapeHtml(task.prompt)}`;
  }
  const hint = document.getElementById("lessonWordHint");
  if (hint) {
    const mn = Number(task.word_count_min || 0), mx = Number(task.word_count_max || 0);
    if (mx > 0) {
      hint.style.display = "inline-block";
      hint.textContent = `🎯 Talab: ${mn}–${mx} so'z`;
    } else if (task.duration_seconds_min) {
      hint.style.display = "inline-block";
      hint.textContent = `🎯 Nutq: ${task.duration_seconds_min}–${task.duration_seconds_max || task.duration_seconds_min} soniya`;
    } else {
      hint.style.display = "none";
    }
  }
  applyListeningPlayback(task);
  applyReadingSource(task);
}

function renderVariantBanner(data) {
  const el = document.getElementById("variantBanner");
  if (!el) return;
  if (!data || !data.variant) { el.style.display = "none"; return; }
  const v = String(data.variant);
  const sc = data.scaffold_level || (data.task && data.task.scaffold_level) || "";
  const chipCls = sc === "full" ? "full" : (sc === "partial" ? "part" : "none");
  el.style.display = "block";
  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:13.5px">
      <span class="chip ${chipCls}" style="font-size:12px;font-weight:700">Sizning variantingiz: ${escapeHtml(v)} — ${escapeHtml(VARIANT_LABELS[v] || "Variant")}</span>
      ${sc ? `<span class="chip" style="background:var(--surface-2);border-color:var(--line);color:var(--ink-2)">Ko'mak: ${escapeHtml(SCAFFOLD_LABELS[sc] || sc)}</span>` : ""}
      ${data.current_week ? `<span style="font-size:12px;color:var(--muted)">${escapeHtml(data.current_week)}</span>` : ""}
    </div>
    ${data.variant_reason ? `<div class="why-box" style="margin-top:10px;padding:12px 16px"><b>2-qoida: sabab ochiq</b>${escapeHtml(data.variant_reason)}</div>` : ""}`;
}

// 3-bosqich: tinglash qutisi — variantga mos sur'at va takror limiti
function applyListeningPlayback(task) {
  const audio = document.getElementById("listeningTaskAudio");
  if (!audio || task.skill !== "listening") return;
  const pb = STATE.listenPlayback;
  if (!task.playback) { pb.max = null; renderPlaybackInfo(); return; }
  const v = task.variant || STATE.lessonVariant || "B";
  const cfg = task.playback[v] || task.playback.B || {};
  pb.max = Number(cfg.max_replays) > 0 ? Number(cfg.max_replays) : null;
  pb.speed = Number(cfg.speed) > 0 ? Number(cfg.speed) : 1;
  pb.count = 0;
  pb.inProgress = false;
  if (task.audio_url) {
    const src = String(task.audio_url).replace(/^\//, "");
    const cur = audio.querySelector("source");
    if (cur && !(cur.getAttribute("src") || "").endsWith(src)) { cur.setAttribute("src", src); audio.load(); }
  }
  audio.controls = true;
  audio.playbackRate = pb.speed;
  if (!pb.bound) {
    pb.bound = true;
    audio.addEventListener("play", () => {
      audio.playbackRate = pb.speed;
      if (pb.inProgress) return; // pauza/davom — yangi tinglash emas
      if (pb.max && pb.count >= pb.max) {
        audio.pause();
        audio.currentTime = 0;
        showToast(`Tinglash limiti tugadi (${pb.max} marta) — variantingiz shartiga ko'ra.`, "warning");
        return;
      }
      pb.count += 1;
      pb.inProgress = true;
      renderPlaybackInfo();
    });
    audio.addEventListener("ended", () => {
      pb.inProgress = false;
      if (pb.max && pb.count >= pb.max) audio.controls = false;
      renderPlaybackInfo();
    });
  }
  renderPlaybackInfo();
}

function renderPlaybackInfo() {
  const info = document.getElementById("listeningPlaybackInfo");
  const pb = STATE.listenPlayback;
  if (!info) return;
  if (!pb.max) { info.style.display = "none"; return; }
  const left = Math.max(0, pb.max - pb.count);
  info.style.display = "flex";
  info.innerHTML = `<span class="chip part">🔁 Qolgan tinglashlar: ${left} / ${pb.max}</span>` +
    `<span class="chip none">⏩ Sur'at: ${escapeHtml(String(pb.speed))}×</span>` +
    (left === 0 && !pb.inProgress ? `<span style="color:var(--clay);font-weight:600">Tinglash limiti tugadi</span>` : "");
}

// 3-bosqich: o'qish qutisi — moslashtirilgan matn belgisi (shaffoflik) va matn
function applyReadingSource(task) {
  if (task.skill !== "reading") return;
  const badge = document.getElementById("readingSourceBadge");
  const box = document.getElementById("readingTextBox");
  if (badge) {
    if (task.reading_source) {
      const rs = task.reading_source;
      badge.style.display = "block";
      badge.innerHTML = `<span class="chip part" style="display:inline-block;margin-bottom:4px">📄 Moslashtirilgan matn</span>` +
        (rs.note ? `<div style="font-size:11.5px;color:var(--ink-2);line-height:1.5">${escapeHtml(rs.note)}</div>` : "");
    } else {
      badge.style.display = "none";
    }
  }
  if (box && task.reading_text) {
    const title = (task.reading_source && task.reading_source.title) || task.title_en || task.title || "Academic Reading";
    box.innerHTML = `<b>${escapeHtml(title)}</b><br><i>${escapeHtml(task.reading_text)}</i>`;
  }
}

// ---- 1-bosqich: REJALASHTIRISH ----
function showPlanSaved(plan) {
  if (!plan) return;
  const note = document.getElementById("planSavedNote");
  if (note) { note.style.display = "block"; note.textContent = `✓ Reja saqlandi: "${plan.goal}"`; }
  const rem = document.getElementById("planReminder");
  if (rem) {
    rem.style.display = "block";
    rem.innerHTML = `<b>Rejangiz:</b> ${escapeHtml(plan.goal)}` +
      (plan.strategy ? `<br><span style="color:var(--muted)">Strategiya: ${escapeHtml(plan.strategy)}</span>` : "");
  }
}

async function saveLessonPlan() {
  const goalEl = document.getElementById("planGoalInput");
  const stratEl = document.getElementById("planStrategyInput");
  const btn = document.getElementById("btnSavePlan");
  const goal = goalEl ? goalEl.value.trim() : "";
  const strategy = stratEl ? stratEl.value.trim() : "";
  if (goal.length < 5) {
    showToast("Maqsadingizni kamida 5 ta belgi bilan yozing (rejalashtirish — birinchi qadam).", "warning");
    if (goalEl) goalEl.focus();
    return;
  }
  if (!STATE.token) {
    STATE.lessonPlan = { goal, strategy };
    showPlanSaved(STATE.lessonPlan);
    goToStage(2);
    return;
  }
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/plan`, {
      method: "POST", headers: lessonAuthHeaders(),
      body: JSON.stringify({ goal, strategy, skill: STATE.lessonSkill || "writing" })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showToast(typeof data.detail === "string" ? data.detail : "Rejani saqlab bo'lmadi.", "error");
      return;
    }
    STATE.lessonPlanSaved = true;
    STATE.lessonPlan = data.plan || { goal, strategy };
    showPlanSaved(STATE.lessonPlan);
    showToast("Reja saqlandi. Endi tayyorgarlik bosqichi.", "success");
    goToStage(2);
  } catch (e) {
    showToast("Serverga ulanishda xatolik: reja saqlanmadi.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function proceedFromIntro() {
  if (!STATE.token || STATE.lessonPlanSaved) { goToStage(2); return; }
  const goalEl = document.getElementById("planGoalInput");
  if (!goalEl || goalEl.value.trim().length < 5) {
    showToast("Avval rejangizni yozing: 'Bu mashg'ulotdagi maqsadim' maydoni bo'sh.", "warning");
    if (goalEl) goalEl.focus();
    return;
  }
  saveLessonPlan();
}

// ---- 2-bosqich: DIALOG MASHQI (jonli muloqotga tayyorgarlik) ----
const DIALOG_EMPTY_HTML = `<div style="color:var(--muted);font-size:12.5px;text-align:center">Dialogni boshlash uchun ingliz tilida birinchi xabaringizni yozing (masalan: "Good morning! Today we'll talk about...").</div>`;

function resetDialog() {
  STATE.dialogMessages = [];
  const log = document.getElementById("dialogLog");
  if (log) log.innerHTML = DIALOG_EMPTY_HTML;
  const notice = document.getElementById("dialogNotice");
  if (notice) notice.style.display = "none";
}

function appendDialogBubble(role, content, kind) {
  const log = document.getElementById("dialogLog");
  if (!log) return null;
  const div = document.createElement("div");
  if (kind === "notice") {
    div.style.cssText = "align-self:stretch;background:var(--amber-soft);border:1px solid #E7D9AE;color:#5F4A0F;padding:8px 12px;border-radius:8px;font-size:12.5px;white-space:pre-wrap";
  } else if (role === "user") {
    div.style.cssText = "max-width:85%;align-self:flex-end;background:var(--teal);color:#fff;padding:8px 12px;border-radius:12px;border-bottom-right-radius:3px;white-space:pre-wrap";
  } else {
    div.style.cssText = "max-width:85%;align-self:flex-start;background:var(--card);border:1px solid var(--line);color:var(--ink);padding:8px 12px;border-radius:12px;border-bottom-left-radius:3px;white-space:pre-wrap";
  }
  div.innerHTML = (kind === "ai" ? `<div style="font-size:10.5px;color:#4338CA;font-weight:700;margin-bottom:3px">🤖 AI tomonidan hosil qilingan</div>` : "") + escapeHtml(content);
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

async function sendDialogMessage(preset) {
  const input = document.getElementById("dialogInput");
  const btn = document.getElementById("btnDialogSend");
  const fbBtn = document.getElementById("btnDialogFeedback");
  const notice = document.getElementById("dialogNotice");
  const log = document.getElementById("dialogLog");
  const text = String(preset || (input ? input.value : "")).trim();
  if (!text) { showToast("Xabar matnini yozing.", "warning"); return; }
  if (!STATE.token) {
    if (notice) {
      notice.style.display = "block";
      notice.textContent = "🔑 Dialog mashqi faqat tizimga kirgan talabalar uchun (AI so'rovlari foydalanuvchi bo'yicha hisoblanadi).";
    }
    if (window.openLoginModal) window.openLoginModal();
    return;
  }
  if (log && STATE.dialogMessages.length === 0) log.innerHTML = "";
  if (!preset && input) input.value = "";
  STATE.dialogMessages.push({ role: "user", content: text.slice(0, 8000) });
  STATE.dialogMessages = STATE.dialogMessages.slice(-20);
  if (STATE.dialogMessages.length && STATE.dialogMessages[0].role === "assistant") STATE.dialogMessages.shift();
  appendDialogBubble("user", text);
  const typing = document.createElement("div");
  typing.style.cssText = "align-self:flex-start;color:var(--muted);font-size:12px";
  typing.textContent = "… hamsuhbat yozmoqda";
  if (log) { log.appendChild(typing); log.scrollTop = log.scrollHeight; }
  if (btn) btn.disabled = true;
  if (fbBtn) fbBtn.disabled = true;
  try {
    const scenario = (document.getElementById("dialogScenario") || {}).value || "classroom";
    const level = (document.getElementById("dialogLevel") || {}).value || "B1";
    const res = await fetch(`${STATE.apiBaseUrl}/ai/dialog`, {
      method: "POST", headers: lessonAuthHeaders(),
      body: JSON.stringify({ messages: STATE.dialogMessages, scenario, level })
    });
    const data = await res.json().catch(() => ({}));
    typing.remove();
    if (res.status === 403) {
      appendDialogBubble("assistant", "1-qoida: mustaqil bosqichda dialog tizimi yopiq. Bu mashq faqat tayyorgarlik (2) va tahlil (4) bosqichlarida ochiq.", "notice");
      return;
    }
    if (!res.ok) {
      appendDialogBubble("assistant", typeof data.detail === "string" ? data.detail : `Server xatosi (HTTP ${res.status}).`, "notice");
      return;
    }
    if (!data.success) {
      appendDialogBubble("assistant", data.content || "AI dialog xizmati hozir mavjud emas.", "notice");
      return;
    }
    const reply = String(data.content || "").trim();
    if (reply) {
      STATE.dialogMessages.push({ role: "assistant", content: reply.slice(0, 8000) });
      STATE.dialogMessages = STATE.dialogMessages.slice(-20);
    }
    appendDialogBubble("assistant", reply || "(bo'sh javob)", "ai");
    if (notice && data.marker) { notice.style.display = "block"; notice.textContent = `ℹ️ ${data.marker}`; }
  } catch (e) {
    typing.remove();
    appendDialogBubble("assistant", "Serverga ulanishda xatolik.", "notice");
  } finally {
    if (btn) btn.disabled = false;
    if (fbBtn) fbBtn.disabled = false;
    if (input && !preset) input.focus();
  }
}

// ---- 3-bosqich: MONITORING ----
function sendMonitorEvent(event, seconds) {
  if (!STATE.token) return Promise.resolve();
  const body = { event };
  if (seconds !== undefined) body.seconds = Math.max(0, Math.min(36000, Math.round(seconds)));
  return fetch(`${STATE.apiBaseUrl}/lesson/5/monitor`, {
    method: "POST", headers: lessonAuthHeaders(), body: JSON.stringify(body)
  }).catch(() => {});
}

function stage3ElapsedSeconds() {
  return Math.round((STATE.stage3Accum + (STATE.stage3EnteredAt ? Date.now() - STATE.stage3EnteredAt : 0)) / 1000);
}

function renderStage3Elapsed() {
  const el = document.getElementById("stage3Elapsed");
  if (!el) return;
  const s = stage3ElapsedSeconds();
  el.textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function startStage3Timer() {
  if (!STATE.stage3EnteredAt) STATE.stage3EnteredAt = Date.now();
  if (STATE.lessonPlan) showPlanSaved(STATE.lessonPlan);
  renderStage3Elapsed();
  if (!STATE.stage3Timer) STATE.stage3Timer = setInterval(renderStage3Elapsed, 1000);
}

function stopStage3Timer() {
  if (STATE.stage3EnteredAt) {
    STATE.stage3Accum += Date.now() - STATE.stage3EnteredAt;
    STATE.stage3EnteredAt = null;
  }
  if (STATE.stage3Timer) { clearInterval(STATE.stage3Timer); STATE.stage3Timer = null; }
}

async function sendMonitorTick() {
  if (!STATE.token) return;
  const secs = stage3ElapsedSeconds();
  if (secs <= 0) return;
  try { await sendMonitorEvent("tick", secs); } catch (_) {}
}

function onSelfCheck(cb) {
  if (!cb || !cb.checked || cb.dataset.sent === "1") return;
  cb.dataset.sent = "1"; // har bir belgi faqat birinchi marta hisoblanadi
  sendMonitorEvent("self_check");
}

// ---- 4-bosqich: BAHOLASH — qiyosiy usul (muqobil variant) ----
async function requestAlternative() {
  const out = document.getElementById("alternativeOutput");
  const btn = document.getElementById("btnRequestAlternative");
  const noteBox = document.getElementById("comparisonNoteBox");
  if (!out) return;
  out.style.display = "block";
  if (!STATE.token) {
    out.innerHTML = `<div style="padding:12px;background:var(--amber-soft);border-radius:6px;font-size:13px">🔑 Muqobil variant olish uchun tizimga kiring.</div>`;
    if (window.openLoginModal) window.openLoginModal();
    return;
  }
  out.innerHTML = `<div style="padding:12px;color:var(--muted);font-size:13px">⏳ AI muqobil variantni tayyorlamoqda (faqat birinchi xatboshi, mazmun saqlanadi)...</div>`;
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/alternative`, { method: "POST", headers: lessonAuthHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      let msg = `Server xatosi (HTTP ${res.status}).`;
      if (typeof data.detail === "string") msg = data.detail;
      else if (data.detail && data.detail.code === "AI_LOCKED") msg = "1-qoida: mustaqil bosqichda muqobil variant berilmaydi. Avval ishni yakunlang.";
      out.innerHTML = `<div style="padding:12px;background:var(--amber-soft);border-radius:6px;font-size:13px">⚠️ ${escapeHtml(msg)}</div>`;
      return;
    }
    const badge = data.ai_powered
      ? `<span style="font-size:11px;color:#4338CA;font-weight:700">🤖 AI tomonidan hosil qilingan</span>`
      : `<span style="font-size:11px;color:var(--amber);font-weight:700">⚙️ Lokal tahlil (AI o'chiq)</span>`;
    const instruction = data.instruction || "Ikki variantni solishtiring va farqning sababini o'z so'zlaringiz bilan asoslang (qiyosiy usul).";
    out.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:6px">
        ${badge}${data.cached ? `<span class="chip" style="background:var(--surface-2);border-color:var(--line);color:var(--muted)">avval olingan</span>` : ""}
      </div>
      <div style="padding:14px;background:var(--paper-2);border:1px solid var(--line);border-radius:8px;font-size:13.5px;line-height:1.7;white-space:pre-wrap">${escapeHtml(data.alternative || "")}</div>
      <div class="why-box" style="margin-top:10px;padding:10px 14px"><b>Qiyosiy usul</b>${escapeHtml(instruction)}</div>`;
    if (noteBox) noteBox.style.display = "block";
  } catch (e) {
    out.innerHTML = `<div style="padding:12px;background:var(--amber-soft);border-radius:6px;font-size:13px">⚠️ Serverga ulanishda xatolik.</div>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function saveComparisonNote() {
  const el = document.getElementById("comparisonNoteInput");
  const st = document.getElementById("comparisonSavedNote");
  const btn = document.getElementById("btnSaveComparison");
  const note = el ? el.value.trim() : "";
  if (note.length < 5) {
    showToast("Farq sababini kamida bir gap bilan asoslang.", "warning");
    if (el) el.focus();
    return;
  }
  STATE.comparisonNote = note;
  if (!STATE.token) { if (st) st.textContent = "Mehmon rejimi: izoh refleksiya bilan birga yuboriladi."; return; }
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/comparison`, {
      method: "POST", headers: lessonAuthHeaders(), body: JSON.stringify({ note })
    });
    if (st) st.textContent = res.ok ? "✓ Asos saqlandi" : "⚠️ Saqlanmadi (server)";
  } catch (_) {
    if (st) st.textContent = "⚠️ Serverga ulanishda xatolik";
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ---- 5-bosqich: REFLEKSIYA — metakognitiv aniqlik (rating_gap) ----
async function loadRatingGap(retry) {
  const box = document.getElementById("ratingGapBox");
  if (!box) return;
  if (!STATE.token) { box.style.display = "none"; return; }
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/lesson/5/actual-rating`, { headers: lessonAuthHeaders(false) });
    if (res.status === 409 && !retry) { setTimeout(() => loadRatingGap(true), 900); return; } // o'z bahosi hali yozilmagan bo'lishi mumkin
    if (!res.ok) { box.style.display = "none"; return; }
    const data = await res.json();
    if (data.rating_gap === null || data.rating_gap === undefined) { box.style.display = "none"; return; }
    const g = Number(data.rating_gap);
    const hint = g <= 0.5
      ? "o'z bahoyingiz AI bahosiga juda yaqin — metakognitiv kalibrlash yuqori."
      : (g <= 1.25 ? "farq o'rtacha — qaysi mezonda farq kattaligiga e'tibor bering." : "farq katta — o'zini baholash mezonlarini qayta ko'rib chiqing.");
    box.style.display = "block";
    box.innerHTML = `<b>🧭 Metakognitiv aniqlik (farq): ${escapeHtml(String(g))}</b><br>` +
      `<span>4 mezon bo'yicha |siz − AI| o'rtacha farqi; 0 ga yaqinlashishi o'zini baholash aniqligini bildiradi — ${escapeHtml(hint)}</span>`;
  } catch (_) {}
}

function resetMetacognitiveState() {
  STATE.lessonPlanSaved = false;
  STATE.lessonPlan = null;
  STATE.comparisonNote = null;
  STATE.feedbackDecisions = {};
  STATE.dialogMessages = [];
  stopStage3Timer();
  STATE.stage3Accum = 0;
  STATE.lessonInfo = null;
  STATE.lessonVariant = null;
  STATE.lessonTaskCache = {};
  document.querySelectorAll(".self-check-box").forEach(cb => { cb.checked = false; delete cb.dataset.sent; });
  const note = document.getElementById("planSavedNote"); if (note) note.style.display = "none";
  const rem = document.getElementById("planReminder"); if (rem) rem.style.display = "none";
  const cn = document.getElementById("comparisonNoteInput"); if (cn) cn.value = "";
  const cs = document.getElementById("comparisonSavedNote"); if (cs) cs.textContent = "";
  const alt = document.getElementById("alternativeOutput"); if (alt) { alt.style.display = "none"; alt.innerHTML = ""; }
  const cb = document.getElementById("comparisonNoteBox"); if (cb) cb.style.display = "none";
  // 4-bosqich: xulosa chizig'i, belgilangan matn, qayta ishlash kartasi va qoralama tarixi tozalanadi
  STATE.drafts = []; STATE.lastDraftText = ""; STATE.lastAnalysis = null;
  ["analysisSummaryStrip", "textHighlightCard", "reviseCard"].forEach(id => { const el = document.getElementById(id); if (el) el.style.display = "none"; });
  const dh = document.getElementById("draftHistoryTable"); if (dh) dh.innerHTML = "";
  // Server holati tozalangan — keyingi mashg'ulot uchun variant va topshiriq qayta olinadi
  loadLessonVariant();
}

// switchLessonSkill (dissertation_features.js) dan keyin variantga mos topshiriqni qayta yuklash
document.addEventListener("DOMContentLoaded", () => {
  const install = (attempt) => {
    const orig = window.switchLessonSkill;
    if (typeof orig !== "function") { if (attempt < 20) setTimeout(() => install(attempt + 1), 150); return; }
    if (orig.__tiloraVariantHook) return;
    const wrapped = function (skill) {
      const r = orig.apply(this, arguments);
      STATE.lessonSkill = skill || "writing";
      if (STATE.token && STATE.lessonInfo) refreshLessonTask(STATE.lessonSkill);
      return r;
    };
    wrapped.__tiloraVariantHook = true;
    window.switchLessonSkill = wrapped;
  };
  install(0);
});

// ---- 5-bosqich: AI bahosi ----
STATE.aiEvaluation = null;
STATE.aiEvaluationPromise = null;
STATE.aiEvaluationText = "";

function prefetchAiEvaluation() {
  const textEl = document.getElementById("productionText");
  const text = textEl ? textEl.value.trim() : "";
  if (text.length < 10) return null;
  if (STATE.aiEvaluationPromise && STATE.aiEvaluationText === text) return STATE.aiEvaluationPromise;
  STATE.aiEvaluationText = text;
  STATE.aiEvaluation = null;
  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;
  STATE.aiEvaluationPromise = fetch(`${STATE.apiBaseUrl}/lesson/5/ai-evaluate`, {
    method: "POST", headers, body: JSON.stringify({ content_text: text })
  })
    .then(async r => {
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || "AI baholay olmadi");
      STATE.aiEvaluation = d;
      return d;
    })
    .catch(err => { STATE.aiEvaluation = { error: err.message }; return STATE.aiEvaluation; });
  return STATE.aiEvaluationPromise;
}

const CRIT_LABELS = { content: "Mazmun to'liqligi", grammar: "Grammatik aniqlik", lexis: "Lug'aviy boylik", coherence: "Izchillik va bog'liqlik" };

async function renderAiEvaluation() {
  const loading = document.getElementById("aiEvalLoading");
  const panel = document.getElementById("aiEvalPanel");
  if (!panel) return;
  const textEl = document.getElementById("productionText");
  const text = textEl ? textEl.value.trim() : "";
  if (text.length < 10) {
    panel.style.display = "block";
    if (loading) loading.style.display = "none";
    panel.innerHTML = `<div style="padding:14px;background:var(--amber-soft);border-radius:6px;font-size:13px">⚠️ Baholash uchun avval 3-bosqichda matn yozing.</div>`;
    return;
  }
  if (loading) loading.style.display = "block";
  panel.style.display = "none";
  const data = await (prefetchAiEvaluation() || Promise.resolve(STATE.aiEvaluation));
  if (loading) loading.style.display = "none";
  panel.style.display = "block";
  if (!data || data.error || !data.rubric) {
    panel.innerHTML = `<div style="padding:14px;background:var(--amber-soft);border-radius:6px;font-size:13px">⚠️ AI bahosi olinmadi: ${escapeHtml((data && data.error) || "server javob bermadi")}</div>`;
    return;
  }
  const esc = escapeHtml;
  const title = document.getElementById("actualScoreTitle");
  const badge = document.getElementById("aiEvalSourceBadge");
  const details = document.getElementById("actualRubricDetails");
  if (title) title.textContent = `AI bahosi: ${data.total_score} / 100 · taxminiy CEFR ${data.cefr_estimate || "—"}`;
  if (badge) {
    badge.textContent = data.ai_powered ? `🤖 ${data.model || "AI"}` : "⚙️ Lokal baholash (AI o'chiq)";
    badge.style.color = data.ai_powered ? "var(--teal)" : "var(--amber)";
  }
  const crits = ["content", "grammar", "lexis", "coherence"];
  if (details) details.textContent = crits.map(c => `${CRIT_LABELS[c]}: ${data.rubric[c].score}/5`).join(" · ");

  const rows = document.getElementById("aiEvalCompareRows");
  if (rows) {
    rows.innerHTML = crits.map(c => {
      const mine = STATE.selfRating[c];
      const ai = data.rubric[c].score;
      const diff = (mine !== undefined) ? mine - ai : null;
      const diffTxt = diff === null ? "—" : (diff === 0 ? "✓ mos" : (diff > 0 ? `+${diff} (o'zingizni yuqori baholadingiz)` : `${diff} (o'zingizni past baholadingiz)`));
      const color = diff === null ? "var(--muted)" : (diff === 0 ? "var(--teal)" : (Math.abs(diff) >= 2 ? "var(--clay)" : "var(--amber)"));
      return `<tr>
        <td style="padding:7px 4px;border-bottom:1px solid var(--line-2)">${CRIT_LABELS[c]}</td>
        <td style="text-align:center;padding:7px 4px;border-bottom:1px solid var(--line-2);font-weight:700">${mine ?? "—"}</td>
        <td style="text-align:center;padding:7px 4px;border-bottom:1px solid var(--line-2);font-weight:700;color:var(--teal)">${ai}</td>
        <td style="text-align:center;padding:7px 4px;border-bottom:1px solid var(--line-2);font-size:12px;color:${color}">${diffTxt}</td>
      </tr>`;
    }).join("");
  }
  // Metakognitiv aniqlik (rating_gap) — jadval yonida
  if (typeof loadRatingGap === "function") loadRatingGap();
  const reasons = document.getElementById("aiEvalReasons");
  if (reasons) {
    reasons.innerHTML = crits.filter(c => data.rubric[c].reason).map(c => `
      <div style="font-size:12.5px;line-height:1.55;padding:8px 10px;background:var(--surface-2);border-radius:6px">
        <b style="color:var(--teal)">${CRIT_LABELS[c]} — ${data.rubric[c].score}/5:</b> ${esc(data.rubric[c].reason)}
      </div>`).join("");
  }
  const lists = document.getElementById("aiEvalLists");
  if (lists) {
    const li = (arr) => (arr || []).map(x => `<li style="margin-bottom:4px">${esc(x)}</li>`).join("");
    lists.innerHTML = `
      <div style="font-size:12.5px"><b style="color:var(--teal)">💪 Kuchli tomonlar</b><ul style="padding-left:18px;margin:6px 0 0">${li(data.strengths) || "<li>—</li>"}</ul></div>
      <div style="font-size:12.5px"><b style="color:var(--clay)">🎯 Rivojlantirish</b><ul style="padding-left:18px;margin:6px 0 0">${li(data.improvements) || "<li>—</li>"}</ul></div>`;
  }
  const qBox = document.getElementById("aiEvalQuality");
  const q = data.text_quality;
  if (qBox) {
    if (q && q.level && q.level !== "ok") {
      const toks = (q.suspicious_tokens || []).slice(0, 12).map(t => `<span title="${esc(t.reason)}" style="display:inline-block;padding:1px 7px;margin:2px;border-radius:10px;background:var(--card);border:1px solid var(--line);font-family:var(--mono);font-size:11.5px">${esc(t.token)}</span>`).join("");
      const sents = (q.nonsense_sentences || []).slice(0, 3).map(s => `<li>"${esc(s.text)}" — <i>${esc(s.reason)}</i></li>`).join("");
      qBox.style.display = "block";
      qBox.innerHTML = `<b>🔤 Matn sifati:</b> ${esc(q.summary)}<br>
        <span style="color:var(--muted)">Ma'noli so'zlar: ${q.valid_word_count} / ${q.word_count}</span>
        ${toks ? `<div style="margin-top:6px">${toks}</div>` : ""}
        ${sents ? `<ul style="margin:6px 0 0;padding-left:18px">${sents}</ul>` : ""}`;
    } else {
      qBox.style.display = "none";
    }
  }
  const comment = document.getElementById("aiEvalComment");
  if (comment) { comment.textContent = data.overall_comment || ""; comment.style.display = data.overall_comment ? "block" : "none"; }
  const errBox = document.getElementById("aiEvalError");
  if (errBox) {
    if (data.ai_error) { errBox.style.display = "block"; errBox.textContent = `⚠️ ${data.ai_error}`; }
    else errBox.style.display = "none";
  }
}

// ============================================================
// 3-QOIDA: TAKLIFLAR VA PEDAGOGIK MULOQOT MARKAZI
// ============================================================
STATE.proposalTab = STATE.proposalTab || "all";
STATE.proposalDirectionFilter = STATE.proposalDirectionFilter || "all";
STATE.proposalStatusFilter = STATE.proposalStatusFilter || "all";
STATE.proposalSearchQuery = STATE.proposalSearchQuery || "";
STATE.cachedRecipients = null;
STATE.currentProposalAction = null;

const PROPOSAL_STATUS = {
  pending:  { label: "⏳ Kutilmoqda",   color: "var(--teal)",  bg: "var(--teal-soft)" },
  approved: { label: "✓ Qabul qilindi",  color: "#15803D",      bg: "rgba(21,128,61,0.12)" },
  modified: { label: "✎ O'zgartirildi",  color: "#7C3AED",      bg: "rgba(124,58,237,0.12)" },
  rejected: { label: "✕ Bekor qilindi",  color: "var(--clay)",  bg: "rgba(192,86,33,0.12)" }
};

const PROPOSAL_CATEGORIES = {
  methodology: "📚 Metodika va sillabus",
  assignment: "✍️ Topshiriq va baholash",
  scaffolding: "🎯 Skaffolding va yordam",
  peer_learning: "👥 Tengdoshlararo o'rganish (Peer)",
  general: "💡 Umumiy taklif / fikr",
  scaffold_change: "🎯 Skaffolding o'zgarishi (AI)",
  difficulty_change: "📈 Murakkablik o'zgarishi (AI)",
  deadline_change: "⏱️ Muddat o'zgarishi (AI)"
};

const PROPOSAL_DIRECTIONS = {
  teacher_to_teacher: { label: "👨‍🏫 O'qituvchilar o'zaro", color: "#0284c7", bg: "rgba(2,132,199,0.1)" },
  student_to_teacher: { label: "👨‍🎓 Talabadan ➔ 👨‍🏫 O'qituvchiga", color: "#16a34a", bg: "rgba(22,163,74,0.1)" },
  student_to_student: { label: "👨‍🎓 Talabalar o'zaro (Peer)", color: "#9333ea", bg: "rgba(147,51,234,0.1)" },
  teacher_to_student: { label: "👨‍🏫 O'qituvchidan ➔ 👨‍🎓 Talabaga", color: "#d97706", bg: "rgba(217,119,6,0.1)" },
  system: { label: "🤖 Tizim (AI) taklifi", color: "var(--teal)", bg: "var(--teal-soft)" }
};

window.setProposalTab = function(tabName) {
  STATE.proposalTab = tabName;
  document.querySelectorAll("#proposalTabs .prop-tab").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
      btn.style.background = "var(--teal)";
      btn.style.color = "#fff";
      btn.style.borderColor = "var(--teal)";
    } else {
      btn.classList.remove("active");
      btn.style.background = "none";
      btn.style.color = "var(--ink)";
      btn.style.borderColor = "var(--line)";
    }
  });
  window.loadTeacherProposals();
};

window.onProposalFilterChange = function() {
  const dirSel = document.getElementById("propDirectionFilter");
  const stSel = document.getElementById("propStatusFilter");
  if (dirSel) STATE.proposalDirectionFilter = dirSel.value;
  if (stSel) STATE.proposalStatusFilter = stSel.value;
  window.loadTeacherProposals();
};

window.onProposalSearchInput = function() {
  const input = document.getElementById("propSearchInput");
  const q = input ? input.value.trim().toLowerCase() : "";
  STATE.proposalSearchQuery = q;
  const cards = document.querySelectorAll("#teacherProposalsList .proposal-card-item");
  cards.forEach(card => {
    const text = card.textContent.toLowerCase();
    card.style.display = (!q || text.includes(q)) ? "block" : "none";
  });
};

window.loadTeacherProposals = async function() {
  const box = document.getElementById("teacherProposalsList");
  const chip = document.getElementById("teacherProposalsChip");
  const pTitle = document.getElementById("proposalsPageTitle");
  const pSubtitle = document.getElementById("proposalsPageSubtitle");
  const subjBanner = document.getElementById("teacherSubjectsBanner");
  if (!box) return;

  const currentRole = (STATE.currentUser && STATE.currentUser.role) ? STATE.currentUser.role : "student";
  const currentUserId = (STATE.currentUser && STATE.currentUser.id) ? STATE.currentUser.id : "";
  const lang = typeof window.getCurrentLang === "function" ? window.getCurrentLang() : "uz";

  // Foydalanuvchi roliga mos ravishda sarlavhalarni moslash
  if (pTitle && pSubtitle) {
    if (currentRole === "student") {
      pTitle.textContent = lang === "ru" ? "💡 Центр предложений и мнений" : (lang === "en" ? "💡 Proposals & Feedback Center" : "💡 Takliflar va Fikr-mulohazalar Markazi");
      pSubtitle.textContent = lang === "ru" ? "Отправка предложений преподавателям и однокурсникам, обмен идеями и рекомендации ИИ" : (lang === "en" ? "Share proposals with instructors & peers, exchange ideas and review AI recommendations" : "O'qituvchilarga va guruhdoshlarga taklif yuborish, o'zaro fikr almashish hamda AI tavsiyalari");
      if (subjBanner) subjBanner.style.display = "none";
    } else {
      pTitle.textContent = lang === "ru" ? "💡 Центр предложений и педагогического контроля" : (lang === "en" ? "💡 Proposals & Pedagogical Control Center" : "💡 Takliflar va Pedagogik Muloqot Markazi");
      pSubtitle.textContent = lang === "ru" ? "Обмен предложениями между преподавателями и студентами, рекомендации ИИ и педагогические решения (Правило 3)" : (lang === "en" ? "Peer teacher proposals, student suggestions, AI recommendations & pedagogical decisions (Rule 3)" : "O'qituvchilar va talabalar o'rtasida taklif almashish, AI tavsiyalari va pedagogik qarorlar (3-Qoida)");
      if (subjBanner) subjBanner.style.display = "flex";
    }
  }

  if (!STATE.token) {
    const notLoggedIn = lang === "ru" ? "Для просмотра и отправки предложений войдите в свой профиль." : (lang === "en" ? "Please sign in to view and send proposals." : "Takliflarni ko'rish va yuborish uchun profilingizga kiring.");
    box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">${notLoggedIn}</div>`;
    return;
  }

  box.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">Takliflar yuklanmoqda...</div>`;

  try {
    const qParams = new URLSearchParams({
      tab: STATE.proposalTab || "all",
      status_filter: STATE.proposalStatusFilter || "all",
      direction_filter: STATE.proposalDirectionFilter || "all"
    });

    let res = await fetch(`${STATE.apiBaseUrl}/proposals?${qParams.toString()}`, {
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });

    if (!res.ok) {
      // Fallback
      res = await fetch(`${STATE.apiBaseUrl}/teacher/proposals`, {
        headers: { "Authorization": `Bearer ${STATE.token}` }
      });
    }

    if (!res.ok) throw new Error("Takliflarni yuklab bo'lmadi");
    const data = await res.json();
    const items = data.proposals || [];
    const counts = data.counts || {
      all: items.length,
      inbox: items.filter(p => p.relation === "inbox").length,
      sent: items.filter(p => p.relation === "sent").length,
      system: items.filter(p => p.relation === "system" || p.direction === "system").length,
      pending: items.filter(p => p.status === "pending").length
    };

    // Hisoblagichlarni yangilash
    const cAll = document.getElementById("propCountAll");
    const cInbox = document.getElementById("propCountInbox");
    const cSent = document.getElementById("propCountSent");
    const cSystem = document.getElementById("propCountSystem");
    if (cAll) cAll.textContent = counts.all;
    if (cInbox) cInbox.textContent = counts.inbox;
    if (cSent) cSent.textContent = counts.sent;
    if (cSystem) cSystem.textContent = counts.system;

    if (chip) {
      chip.textContent = `${counts.pending} ta qaror kutilmoqda · jami ${counts.all}`;
    }

    if (!items.length) {
      const emptyMsg = STATE.proposalTab === "inbox" 
        ? "Sizga kelgan yangi takliflar mavjud emas."
        : (STATE.proposalTab === "sent" ? "Siz hali birorta taklif yubormagansiz." : "Hech qanday taklif topilmadi.");
      box.innerHTML = `
        <div class="card" style="text-align:center;padding:40px 20px;color:var(--muted)">
          <div style="font-size:36px;margin-bottom:10px">📭</div>
          <div style="font-size:15px;font-weight:600;margin-bottom:6px">${emptyMsg}</div>
          <div style="font-size:13px">Yuqoridagi "➕ Yangi taklif yuborish" tugmasi orqali o'qituvchi yoki talabalarga taklif jo'natishingiz mumkin.</div>
        </div>
      `;
      return;
    }

    const esc = escapeHtml;

    box.innerHTML = items.map(p => {
      const st = PROPOSAL_STATUS[p.status] || PROPOSAL_STATUS.pending;
      const catLabel = PROPOSAL_CATEGORIES[p.proposal_type] || p.proposal_type_label || "💡 Taklif";
      const dirInfo = PROPOSAL_DIRECTIONS[p.direction] || { label: p.direction_label || "Taklif", color: "var(--teal)", bg: "var(--teal-soft)" };

      // Huquqlar:
      // Qabul qiluvchi, o'qituvchi yoki admin taklif bo'yicha qaror qabul qila oladi
      const isReceiver = (p.receiver_id === currentUserId || (p.receiver_id === "all_teachers" && currentRole !== "student") || (p.receiver_id === "all_students" && currentRole === "student") || p.teacher_id === currentUserId);
      const isSender = (p.sender_id === currentUserId);
      const isAdmin = (currentRole === "admin");
      const canDecide = (isAdmin || isReceiver || currentRole === "teacher");
      const canDelete = (isAdmin || isSender);

      let actionHtml = "";
      if (p.status === "pending") {
        if (canDecide) {
          actionHtml = `
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <button class="btn-primary" style="padding:6px 14px;font-size:12px;background:#15803D" onclick="window.promptProposalAction('${p.id}', 'approve')">✓ Qabul qilish</button>
              <button class="btn-primary" style="padding:6px 12px;font-size:12px;background:none;color:var(--ink);border:1px solid var(--line)" onclick="window.promptProposalAction('${p.id}', 'modify')">✎ O'zgartirish</button>
              <button class="btn-primary" style="padding:6px 12px;font-size:12px;background:var(--clay)" onclick="window.promptProposalAction('${p.id}', 'reject')">✕ Rad etish</button>
            </div>
          `;
        } else {
          actionHtml = `<span style="font-size:12px;color:var(--muted);font-style:italic">⏳ Ko'rib chiqilmoqda</span>`;
        }
      } else {
        // Qaror qilingan holat
        actionHtml = `
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px">
            <span style="font-size:12px;font-weight:700;color:${st.color};background:${st.bg};padding:4px 10px;border-radius:12px">${st.label}</span>
            ${p.decided_at ? `<span style="font-size:11px;color:var(--muted)">Qaror vaqti: ${esc(p.decided_at)}</span>` : ""}
            ${canDecide ? `<button type="button" onclick="window.promptProposalAction('${p.id}', 'reopen')" style="font-size:11px;background:none;border:1px solid var(--line);border-radius:6px;padding:3px 8px;cursor:pointer;color:var(--muted)">↺ Qayta ko'rib chiqish</button>` : ""}
          </div>
        `;
      }

      const deleteBtn = canDelete ? `
        <button type="button" onclick="window.deleteProposal('${p.id}')" title="Taklifni o'chirish" style="background:none;border:none;color:var(--clay);font-size:14px;cursor:pointer;padding:4px 6px;border-radius:4px" onmouseover="this.style.background='var(--surface-2)'" onmouseout="this.style.background='none'">🗑️</button>
      ` : "";

      return `
        <div class="card proposal-card-item" style="margin:0;border-left:4px solid ${dirInfo.color};transition:all 0.2s">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:10px;flex-wrap:wrap">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span style="font-size:11.5px;font-weight:700;color:${dirInfo.color};background:${dirInfo.bg};padding:3px 9px;border-radius:6px">
                ${esc(dirInfo.label)}
              </span>
              <span style="font-size:11.5px;font-weight:600;color:var(--ink-2);background:var(--surface-2);padding:3px 9px;border-radius:6px;border:1px solid var(--line)">
                ${esc(catLabel)}
              </span>
              ${p.created_at ? `<span style="font-size:11px;color:var(--muted)">📅 ${esc(p.created_at)}</span>` : ""}
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              ${deleteBtn}
              ${actionHtml}
            </div>
          </div>

          <div style="margin-bottom:8px">
            <h4 style="margin:0 0 6px;font-size:15.5px;font-family:var(--serif);color:var(--ink)">
              ${esc(p.title || "Taklif")}
            </h4>
            <div style="font-size:13.5px;color:var(--ink-2);line-height:1.55;white-space:pre-wrap;background:var(--surface);padding:10px 14px;border-radius:8px;border:1px solid var(--line)">
              ${esc(p.proposal_text || "")}
            </div>
          </div>

          <!-- Yuboruvchi, Qabul qiluvchi va Asos -->
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:8px;font-size:12px;color:var(--muted);background:var(--surface-2);padding:10px 14px;border-radius:8px;margin-top:8px">
            <div>
              <b>📤 Yuboruvchi:</b> <span style="color:var(--ink)">${esc(p.sender_name)}</span>
              ${p.sender_role ? `<span style="font-size:10.5px;padding:1px 5px;border-radius:4px;background:var(--line);margin-left:4px">${esc(p.sender_role)}</span>` : ""}
            </div>
            <div>
              <b>📥 Qabul qiluvchi:</b> <span style="color:var(--ink)">${esc(p.receiver_name)}</span>
              ${p.receiver_role ? `<span style="font-size:10.5px;padding:1px 5px;border-radius:4px;background:var(--line);margin-left:4px">${esc(p.receiver_role)}</span>` : ""}
            </div>
            ${p.basis ? `<div style="grid-column:1/-1"><b>🎯 Sabab / Asos:</b> <i>${esc(p.basis)}</i></div>` : ""}
            ${p.teacher_comment ? `<div style="grid-column:1/-1;border-top:1px dashed var(--line);padding-top:6px;color:#0284c7"><b>💬 Qaror izohi:</b> ${esc(p.teacher_comment)}</div>` : ""}
          </div>
        </div>
      `;
    }).join("");

    // Qidiruv mavjud bo'lsa uni qo'llash
    if (STATE.proposalSearchQuery) {
      window.onProposalSearchInput();
    }
  } catch (err) {
    console.error("Takliflarni yuklashda xatolik:", err);
    box.innerHTML = `<div style="text-align:center;padding:24px;color:var(--clay)">Xatolik: ${escapeHtml(err.message)}</div>`;
  }
};

// ============================================================
// YANGI TAKLIF YUBORISH MODALI HANDLERLARI
// ============================================================
window.openNewProposalModal = async function() {
  const modal = document.getElementById("proposalModal");
  if (!modal) return;

  if (!STATE.token) {
    showToast("Taklif yuborish uchun tizimga kiring.", "warning");
    if (typeof window.openLoginModal === "function") window.openLoginModal();
    return;
  }

  // Qabul qiluvchilar ro'yxatini yuklash (O'qituvchilar va Talabalar)
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/proposals/recipients`, {
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (res.ok) {
      STATE.cachedRecipients = await res.json();
    }
  } catch (err) {
    console.warn("Qabul qiluvchilar ro'yxatini yuklashda ogohlantirish:", err);
  }

  // Formani tozalash
  const titleIn = document.getElementById("propTitleInput");
  const textIn = document.getElementById("propTextInput");
  const basisIn = document.getElementById("propBasisInput");
  if (titleIn) titleIn.value = "";
  if (textIn) textIn.value = "";
  if (basisIn) basisIn.value = "";

  // Dastlabki qabul qiluvchi turini o'rnatish
  const recTypeSel = document.getElementById("propRecipientType");
  const currentRole = (STATE.currentUser && STATE.currentUser.role) ? STATE.currentUser.role : "student";
  if (recTypeSel) {
    recTypeSel.value = "teacher"; // Talaba ham, o'qituvchi ham dastlab o'qituvchini ko'radi
  }

  window.onPropRecipientTypeChange();
  modal.style.display = "flex";
};

window.closeProposalModal = function() {
  const modal = document.getElementById("proposalModal");
  if (modal) modal.style.display = "none";
};

window.onPropRecipientTypeChange = function() {
  const recTypeSel = document.getElementById("propRecipientType");
  const recPersonWrap = document.getElementById("propRecipientPersonWrap");
  const recPersonLabel = document.getElementById("propRecipientPersonLabel");
  const recSelect = document.getElementById("propRecipientSelect");
  const dirBadge = document.getElementById("propDirectionBadge");
  if (!recTypeSel || !recSelect) return;

  const currentRole = (STATE.currentUser && STATE.currentUser.role) ? STATE.currentUser.role : "student";
  const type = recTypeSel.value;
  const recipients = STATE.cachedRecipients || { teachers: [], students: [] };

  if (type === "all_teachers") {
    if (recPersonWrap) recPersonWrap.style.display = "none";
    recSelect.removeAttribute("required");
    recSelect.innerHTML = `<option value="all_teachers" selected>Barcha o'qituvchilar</option>`;
    if (dirBadge) dirBadge.innerHTML = `🌐 Barcha o'qituvchilarga umumiy taklif`;
    return;
  }

  if (type === "all_students") {
    if (recPersonWrap) recPersonWrap.style.display = "none";
    recSelect.removeAttribute("required");
    recSelect.innerHTML = `<option value="all_students" selected>Barcha talabalar</option>`;
    if (dirBadge) dirBadge.innerHTML = `👥 Barcha talabalarga umumiy tavsiya`;
    return;
  }

  // Muayyan shaxs tanlanganda
  if (recPersonWrap) recPersonWrap.style.display = "block";
  recSelect.setAttribute("required", "required");

  if (type === "teacher") {
    if (recPersonLabel) recPersonLabel.textContent = "👤 O'qituvchini tanlang:";
    const teachers = recipients.teachers || [];
    if (!teachers.length) {
      recSelect.innerHTML = `<option value="">O'qituvchilar topilmadi</option>`;
    } else {
      recSelect.innerHTML = `<option value="" disabled selected>-- O'qituvchini tanlang (${teachers.length} nafar) --</option>` +
        teachers.map(t => `<option value="${escapeHtml(t.id)}">👨‍🏫 ${escapeHtml(t.full_name)} (${escapeHtml(t.email)})${t.is_me ? " [Siz]" : ""}</option>`).join("");
    }
    if (dirBadge) {
      dirBadge.innerHTML = (currentRole === "student") 
        ? "👨‍🎓 Talabadan ➔ 👨‍🏫 O'qituvchiga"
        : "👨‍🏫 O'qituvchilar o'zaro (Hamkasbga taklif)";
    }
  } else if (type === "student") {
    if (recPersonLabel) recPersonLabel.textContent = "👤 Talabani tanlang:";
    const students = recipients.students || [];
    if (!students.length) {
      recSelect.innerHTML = `<option value="">Talabalar topilmadi</option>`;
    } else {
      recSelect.innerHTML = `<option value="" disabled selected>-- Talabani tanlang (${students.length} nafar) --</option>` +
        students.map(s => `<option value="${escapeHtml(s.id)}">👨‍🎓 ${escapeHtml(s.full_name)} · ${escapeHtml(s.group_name)}${s.is_me ? " [Siz]" : ""}</option>`).join("");
    }
    if (dirBadge) {
      dirBadge.innerHTML = (currentRole === "student") 
        ? "👨‍🎓 Talabalar o'zaro (Tengdoshga / Peer)"
        : "👨‍🏫 O'qituvchidan ➔ 👨‍🎓 Talabaga (Individual tavsiya)";
    }
  }
};

window.submitNewProposal = async function(e) {
  if (e && e.preventDefault) e.preventDefault();

  const recTypeSel = document.getElementById("propRecipientType");
  const recSelect = document.getElementById("propRecipientSelect");
  const catSel = document.getElementById("propCategorySelect");
  const titleIn = document.getElementById("propTitleInput");
  const textIn = document.getElementById("propTextInput");
  const basisIn = document.getElementById("propBasisInput");
  const btnSubmit = document.getElementById("btnSubmitNewProposal");

  if (!recTypeSel || !titleIn || !textIn) return;

  let receiverId = recTypeSel.value;
  let receiverRole = "teacher";

  if (receiverId === "all_teachers") {
    receiverRole = "teacher";
  } else if (receiverId === "all_students") {
    receiverRole = "student";
  } else {
    receiverId = recSelect ? recSelect.value : "";
    receiverRole = recTypeSel.value; // teacher or student
  }

  if (!receiverId) {
    showToast("Iltimos, qabul qiluvchi shaxsni tanlang.", "error");
    return;
  }

  const title = titleIn.value.trim();
  const proposalText = textIn.value.trim();
  const basis = basisIn ? basisIn.value.trim() : "";
  const category = catSel ? catSel.value : "general";

  if (!title || !proposalText) {
    showToast("Mavzu va taklif matnini kiritish majburiy.", "error");
    return;
  }

  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.textContent = "Yuborilmoqda...";
  }

  try {
    const payload = {
      receiver_id: receiverId,
      receiver_role: receiverRole,
      proposal_type: category,
      title: title,
      proposal_text: proposalText,
      basis: basis
    };

    const res = await fetch(`${STATE.apiBaseUrl}/proposals`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Taklifni yuborib bo'lmadi");

    showToast("✅ Taklifingiz muvaffaqiyatli yuborildi!", "success");
    window.closeProposalModal();
    window.loadTeacherProposals();
  } catch (err) {
    console.error("Taklif yuborishda xatolik:", err);
    showToast(`Xatolik: ${err.message}`, "error");
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.textContent = "📤 Taklifni yuborish";
    }
  }
};

// ============================================================
// TAKLIF BO'YICHA QAROR (APPROVE / MODIFY / REJECT / REOPEN)
// ============================================================
window.promptProposalAction = function(propId, action) {
  STATE.currentProposalAction = { propId, action };

  if (action === "reopen") {
    window.decideProposal(propId, "reopen", null);
    return;
  }

  const modal = document.getElementById("proposalActionModal");
  const titleEl = document.getElementById("propActionModalTitle");
  const descEl = document.getElementById("propActionModalDesc");
  const commentIn = document.getElementById("propActionComment");
  const confirmBtn = document.getElementById("btnConfirmPropAction");
  if (!modal) return;

  if (commentIn) commentIn.value = "";

  if (action === "approve") {
    if (titleEl) titleEl.textContent = "Taklifni qabul qilish va tasdiqlash";
    if (descEl) descEl.textContent = "Taklifni qabul qilasiz. Ixtiyoriy ravishda pedagogik sharh yoki izoh qoldirishingiz mumkin.";
    if (confirmBtn) {
      confirmBtn.textContent = "✓ Qabul qilish";
      confirmBtn.style.background = "#15803D";
    }
  } else if (action === "modify") {
    if (titleEl) titleEl.textContent = "Taklifni o'zgartirish bilan qabul qilish";
    if (descEl) descEl.textContent = "Taklif qanday o'zgartirilishini izoh maydoniga yozing.";
    if (confirmBtn) {
      confirmBtn.textContent = "✎ O'zgartirishni kiritish";
      confirmBtn.style.background = "#7C3AED";
    }
  } else if (action === "reject") {
    if (titleEl) titleEl.textContent = "Taklifni rad etish";
    if (descEl) descEl.textContent = "Taklif nega rad etilayotganini tushuntirib izoh qoldirishingiz mumkin.";
    if (confirmBtn) {
      confirmBtn.textContent = "✕ Rad etish";
      confirmBtn.style.background = "var(--clay)";
    }
  }

  modal.style.display = "flex";
};

window.closeProposalActionModal = function() {
  const modal = document.getElementById("proposalActionModal");
  if (modal) modal.style.display = "none";
  STATE.currentProposalAction = null;
};

window.submitProposalDecision = function() {
  if (!STATE.currentProposalAction) return;
  const { propId, action } = STATE.currentProposalAction;
  const commentIn = document.getElementById("propActionComment");
  const comment = commentIn ? commentIn.value.trim() : "";
  window.closeProposalActionModal();
  window.decideProposal(propId, action, comment || null);
};

window.decideProposal = async function(propId, action, comment) {
  try {
    let url = `${STATE.apiBaseUrl}/proposals/${propId}/${action}`;
    let res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${STATE.token}` },
      body: action === "reopen" ? null : JSON.stringify({ teacher_comment: comment || null })
    });

    if (!res.ok && res.status === 404) {
      // Fallback to teacher router
      url = `${STATE.apiBaseUrl}/teacher/proposal/${propId}/${action}`;
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${STATE.token}` },
        body: action === "reopen" ? null : JSON.stringify({ status: action, teacher_comment: comment || null })
      });
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Qaror saqlanmadi");
    showToast(`✅ ${data.message || "Qaror saqlandi"}`, "success");
    window.loadTeacherProposals();
  } catch (err) {
    showToast(`Xatolik: ${err.message}`, "error");
  }
};

window.deleteProposal = async function(propId) {
  if (!confirm("Haqiqatan ham bu taklifni butunlay o'chirmoqchimisiz?")) return;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/proposals/${propId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Taklifni o'chirib bo'lmadi");
    showToast("🗑️ Taklif muvaffaqiyatli o'chirildi.", "info");
    window.loadTeacherProposals();
  } catch (err) {
    showToast(`Xatolik: ${err.message}`, "error");
  }
};

// Mavzuni almashtirish (Dark / Light mode)
function initTheme() {
  const toggleBtn = document.getElementById("btnToggleTheme");
  if (!toggleBtn) return;
  
  toggleBtn.addEventListener("click", () => {
    STATE.currentTheme = (STATE.currentTheme === "light") ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", STATE.currentTheme);
    toggleBtn.textContent = (STATE.currentTheme === "light") ? "◑" : "◐";
  });
}

// ============================================================
// INKLYUZIVLIK: shrift o'lchami (A+) va yuqori kontrast (◐ Kontrast)
//   <html> klasslari: fs-large / fs-xlarge, high-contrast; localStorage: tilora_fontsize, tilora_contrast
// ============================================================
const FONT_SIZE_STEPS = ["normal", "large", "xlarge"];
const FONT_SIZE_LABELS = { normal: "oddiy", large: "katta", xlarge: "juda katta" };

function applyFontSize(step) {
  const root = document.documentElement;
  root.classList.remove("fs-large", "fs-xlarge");
  if (step === "large") root.classList.add("fs-large");
  if (step === "xlarge") root.classList.add("fs-xlarge");
  const btn = document.getElementById("btnFontSize");
  if (btn) {
    btn.textContent = step === "xlarge" ? "A++" : (step === "large" ? "A+" : "A");
    btn.title = `Shrift o'lchami: ${FONT_SIZE_LABELS[step] || "oddiy"} (bosib o'zgartiring)`;
    btn.classList.toggle("on", step !== "normal");
  }
}

function cycleFontSize() {
  let cur = "normal";
  try { cur = localStorage.getItem("tilora_fontsize") || "normal"; } catch (_) {}
  const next = FONT_SIZE_STEPS[(FONT_SIZE_STEPS.indexOf(cur) + 1) % FONT_SIZE_STEPS.length];
  try { localStorage.setItem("tilora_fontsize", next); } catch (_) {}
  applyFontSize(next);
  showToast(`Shrift o'lchami: ${FONT_SIZE_LABELS[next]}`, "info");
}
window.cycleFontSize = cycleFontSize;

function applyHighContrast(on) {
  document.documentElement.classList.toggle("high-contrast", !!on);
  const btn = document.getElementById("btnContrast");
  if (btn) { btn.setAttribute("aria-pressed", on ? "true" : "false"); btn.classList.toggle("on", !!on); }
}

function toggleHighContrast() {
  const on = !document.documentElement.classList.contains("high-contrast");
  try { localStorage.setItem("tilora_contrast", on ? "1" : "0"); } catch (_) {}
  applyHighContrast(on);
  showToast(on ? "Yuqori kontrast rejimi yoqildi" : "Yuqori kontrast rejimi o'chirildi", "info");
}
window.toggleHighContrast = toggleHighContrast;

function initAccessibilityPrefs() {
  let fs = "normal", hc = false;
  try { fs = localStorage.getItem("tilora_fontsize") || "normal"; hc = localStorage.getItem("tilora_contrast") === "1"; } catch (_) {}
  applyFontSize(FONT_SIZE_STEPS.includes(fs) ? fs : "normal");
  applyHighContrast(hc);
}

// Wi-Fi va Lokal Tarmoq ulanish modali
function initWifiShare() {
  const btnShare = document.getElementById("btnWifiShare");
  const modal = document.getElementById("wifiModal");
  const btnClose = document.getElementById("btnCloseWifiModal");
  const urlText = document.getElementById("wifiUrlText");
  const btnCopy = document.getElementById("btnCopyWifiUrl");
  const qrImg = document.getElementById("wifiQrImage");

  if (!btnShare || !modal) return;

  // Tarmoq ma'lumotlarini yuklash
  async function loadNetworkInfo() {
    try {
      const res = await fetch(`${STATE.apiBaseUrl}/network-info`);
      if (res.ok) {
        const data = await res.json();
        if (data.lan_url) {
          urlText.textContent = data.lan_url;
          if (qrImg) qrImg.src = (data.qr_url || "/wifi_qr.png") + "?t=" + Date.now();
          return;
        }
      }
    } catch (e) {
      console.warn("Tarmoq ma'lumotlarini olishda xatolik:", e);
    }
    // Fallback: Agar olingan bo'lmasa
    if (urlText) urlText.textContent = window.location.origin;
  }

  btnShare.addEventListener("click", () => {
    modal.style.display = "flex";
    loadNetworkInfo();
  });

  if (btnClose) {
    btnClose.addEventListener("click", () => {
      modal.style.display = "none";
    });
  }

  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.style.display = "none";
    }
  });

  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      const text = urlText.textContent;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
          btnCopy.textContent = "Nusxalandi! ✓";
          setTimeout(() => { btnCopy.textContent = "Nusxalash"; }, 2000);
        });
      } else {
        const input = document.createElement("input");
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        document.body.removeChild(input);
        btnCopy.textContent = "Nusxalandi! ✓";
        setTimeout(() => { btnCopy.textContent = "Nusxalash"; }, 2000);
      }
    });
  }
}

// ============================================================
// FOYDALANUVCHI PROFILI VA AUTENTIFIKATSIYA (LOGIN & PAROL)
// ============================================================

function cefrToPercent(lvl) {
  switch((lvl || "").toUpperCase()) {
    case "A1": return 20;
    case "A2": return 38;
    case "B1": return 56;
    case "B2": return 74;
    case "C1": return 88;
    case "C2": return 98;
    default: return 50;
  }
}

function showToast(message, type = "info") {
  let container = document.getElementById("tiloraToastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "tiloraToastContainer";
    container.style.cssText = "position:fixed;top:20px;right:20px;z-index:9999999;display:flex;flex-direction:column;gap:10px;pointer-events:none;";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  const bg = type === "success" ? "#10B981" : (type === "error" ? "#EF4444" : "#2563EB");
  toast.style.cssText = `background:${bg};color:#fff;padding:12px 18px;border-radius:10px;font-size:13.5px;font-weight:600;box-shadow:0 8px 20px rgba(0,0,0,0.2);display:flex;align-items:center;gap:8px;pointer-events:auto;transition:all 0.3s ease;transform:translateY(-10px);opacity:0;`;
  
  const icon = type === "success" ? "✓" : (type === "error" ? "⚠️" : "ℹ️");
  const iconSpan = document.createElement("span");
  iconSpan.textContent = icon;
  const msgSpan = document.createElement("span");
  msgSpan.textContent = message === undefined || message === null ? "" : String(message);
  toast.appendChild(iconSpan);
  toast.appendChild(msgSpan);
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.transform = "translateY(0)";
    toast.style.opacity = "1";
  });

  setTimeout(() => {
    toast.style.transform = "translateY(-10px)";
    toast.style.opacity = "0";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 350);
  }, 3200);
}

function initAuth() {
  const modal = document.getElementById("loginModal");
  const subModal = document.getElementById("subscribeModal");
  const accModal = document.getElementById("accountSettingsModal");
  const btnClose = document.getElementById("btnCloseLoginModal");
  const btnLoginLogout = document.getElementById("btnLoginLogout");
  const profileBadge = document.getElementById("userProfileBadge");

  // Global funksiyalarni ochiq qilish (HTML onclick / form submit uchun)
  window.handleLoginSubmit = handleLoginSubmit;
  window.quickFillLogin = quickFillLogin;
  window.logout = logout;
  window.switchAuthTab = switchAuthTab;
  window.handleRegisterSubmit = handleRegisterSubmit;
  window.openSubscribeModal = openSubscribeModal;
  window.closeSubscribeModal = closeSubscribeModal;
  window.submitSubscribePayment = submitSubscribePayment;
  window.openAccountSettingsModal = openAccountSettingsModal;
  window.closeAccountSettingsModal = closeAccountSettingsModal;
  window.submitAccountSettings = submitAccountSettings;
  window.submitDeleteAccount = submitDeleteAccount;

  window.handleAuthAction = () => {
    if (STATE.currentUser) {
      logout();
    } else {
      window.openLoginModal();
    }
  };
  window.openLoginModal = () => { if (modal) modal.style.display = "flex"; };
  window.closeLoginModal = () => { if (modal) modal.style.display = "none"; };

  if (btnClose) {
    btnClose.addEventListener("click", () => {
      if (modal) modal.style.display = "none";
    });
  }

  // Faqat orqa qora fonga aniq bosilgandagina yopish (input ichida matn tanlash yoki belgilashda yopilib ketmasligi uchun)
  if (modal) {
    let modalMouseDownTarget = null;
    modal.addEventListener("mousedown", (e) => {
      modalMouseDownTarget = e.target;
    });
    modal.addEventListener("mouseup", (e) => {
      if (modalMouseDownTarget === modal && e.target === modal) {
        modal.style.display = "none";
      }
      modalMouseDownTarget = null;
    });
  }

  if (subModal) {
    let subMouseDownTarget = null;
    subModal.addEventListener("mousedown", (e) => {
      subMouseDownTarget = e.target;
    });
    subModal.addEventListener("mouseup", (e) => {
      if (subMouseDownTarget === subModal && e.target === subModal) {
        subModal.style.display = "none";
      }
      subMouseDownTarget = null;
    });
  }

  if (accModal) {
    let accMouseDownTarget = null;
    accModal.addEventListener("mousedown", (e) => {
      accMouseDownTarget = e.target;
    });
    accModal.addEventListener("mouseup", (e) => {
      if (accMouseDownTarget === accModal && e.target === accModal) {
        accModal.style.display = "none";
      }
      accMouseDownTarget = null;
    });
  }

  if (profileBadge) {
    profileBadge.addEventListener("click", () => {
      if (STATE.currentUser) {
        showScreen("s_profile");
      } else {
        window.openLoginModal();
      }
    });
  }

  if (btnLoginLogout) {
    btnLoginLogout.addEventListener("click", (e) => {
      e.preventDefault();
      window.handleAuthAction();
    });
  }

  // Sahifa ochilganda saqlangan foydalanuvchini yuklash
  let savedUser = null;
  try { savedUser = JSON.parse(localStorage.getItem("tilora_user") || "null"); } catch (_) { savedUser = null; }
  const wasLoggedOut = localStorage.getItem("tilora_logged_out") === "true";

  const savedToken = localStorage.getItem("tilora_token");
  if (savedUser && !wasLoggedOut && savedToken && tokenIsExpired(savedToken)) {
    // Token eskirgan: "kirgan" ko'rinishda qoldirmaymiz
    STATE.currentUser = null;
    STATE.token = null;
    applyUserData(null);
    resetScreensOnLogout();
    setTimeout(() => window.handleSessionExpired(), 400);
  } else if (savedUser && !wasLoggedOut) {
    STATE.currentUser = savedUser;
    STATE.token = savedToken;
    applyUserData(savedUser);
    loadUserProfile();
  } else {
    // Foydalanuvchi profilga kirmagan (Mehmon holati) — faqat "Profilga kirish" deb tursin
    STATE.currentUser = null;
    STATE.token = null;
    applyUserData(null);
    resetScreensOnLogout();
  }
}

function switchAuthTab(tab) {
  const loginBtn = document.getElementById("tabAuthLoginBtn");
  const regBtn = document.getElementById("tabAuthRegisterBtn");
  const loginBox = document.getElementById("authLoginTabContainer");
  const regBox = document.getElementById("authRegisterTabContainer");
  const loginErr = document.getElementById("loginErrorMsg");
  const regErr = document.getElementById("regErrorMsg");

  if (loginErr) loginErr.style.display = "none";
  if (regErr) regErr.style.display = "none";

  if (tab === "login") {
    if (loginBtn) {
      loginBtn.style.borderBottom = "2px solid var(--teal)";
      loginBtn.style.color = "var(--teal)";
      loginBtn.style.fontWeight = "700";
    }
    if (regBtn) {
      regBtn.style.borderBottom = "2px solid transparent";
      regBtn.style.color = "var(--muted)";
      regBtn.style.fontWeight = "600";
    }
    if (loginBox) loginBox.style.display = "block";
    if (regBox) regBox.style.display = "none";
  } else {
    if (regBtn) {
      regBtn.style.borderBottom = "2px solid var(--teal)";
      regBtn.style.color = "var(--teal)";
      regBtn.style.fontWeight = "700";
    }
    if (loginBtn) {
      loginBtn.style.borderBottom = "2px solid transparent";
      loginBtn.style.color = "var(--muted)";
      loginBtn.style.fontWeight = "600";
    }
    if (loginBox) loginBox.style.display = "none";
    if (regBox) regBox.style.display = "block";
  }
}

async function handleLoginSubmit() {
  const userInput = document.getElementById("loginUsername");
  const passInput = document.getElementById("loginPassword");
  const errorBox = document.getElementById("loginErrorMsg");
  const submitBtn = document.getElementById("btnSubmitLogin");

  if (!userInput || !passInput) return;
  const username = userInput.value.trim();
  const password = passInput.value.trim();

  if (!username || !password) {
    if (errorBox) {
      errorBox.textContent = "Iltimos, login va parolni kiriting.";
      errorBox.style.display = "block";
    }
    return;
  }

  if (errorBox) errorBox.style.display = "none";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Tekshirilmoqda...";
  }

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: username, password: password })
    });

    const data = await res.json();

    if (!res.ok) {
      if (res.status === 403) {
        throw new Error(data.detail || "Sizning hisobingiz hali Super Administrator tomonidan tasdiqlanmagan. Iltimos, admin tasdiqlashini kuting.");
      }
      throw new Error(data.detail || "Login yoki parol noto'g'ri");
    }

    // Muvaffaqiyatli kirish
    localStorage.removeItem("tilora_logged_out");
    STATE.sessionExpiredShown = false;
    STATE.token = data.access_token;
    STATE.currentUser = data.user;
    localStorage.setItem("tilora_token", data.access_token);
    localStorage.setItem("tilora_user", JSON.stringify(data.user));

    applyUserData(data.user);
    await loadUserProfile();

    showToast(`Xush kelibsiz, ${data.user.full_name || 'foydalanuvchi'}!`, "success");

    // Modalni yopish
    const modal = document.getElementById("loginModal");
    if (modal) modal.style.display = "none";

    // Rolga qarab mos oynaga o'tkazish
    if (data.user.role === "teacher") {
      showScreen("s_teacher");
    } else if (data.user.role === "admin") {
      showScreen("s_admin");
    } else if (data.user.role === "researcher") {
      showScreen("s_research");
    } else if (data.user.role === "developer") {
      showScreen("s_api_docs");
    } else {
      showScreen("s_profile");
    }

  } catch (err) {
    if (errorBox) {
      errorBox.textContent = err.message || "Kirishda xatolik yuz berdi.";
      errorBox.style.display = "block";
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Profilga kirish →";
    }
  }
}

async function handleRegisterSubmit() {
  const fullName = document.getElementById("regFullName")?.value.trim();
  const email = document.getElementById("regEmail")?.value.trim();
  const role = document.getElementById("regRole")?.value || "student";
  const groupName = document.getElementById("regGroup")?.value.trim() || "";
  const phoneNumber = document.getElementById("regPhone")?.value.trim() || "";
  const password = document.getElementById("regPassword")?.value.trim();
  const errorBox = document.getElementById("regErrorMsg");
  const submitBtn = document.getElementById("btnSubmitRegister");

  if (!fullName || !email || !password) {
    if (errorBox) {
      errorBox.textContent = "Iltimos, ism, email va parolni to'liq kiriting.";
      errorBox.style.display = "block";
    }
    return;
  }

  if (password.length < 6) {
    if (errorBox) {
      errorBox.textContent = "Parol kamida 6 ta belgidan iborat bo'lishi kerak.";
      errorBox.style.display = "block";
    }
    return;
  }

  if (errorBox) errorBox.style.display = "none";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Arizangiz yuborilmoqda...";
  }

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email,
        password: password,
        full_name: fullName,
        role: role,
        phone_number: phoneNumber,
        group_name: groupName
      })
    });

    let data;
    try {
      data = await res.json();
    } catch (_) {
      data = { detail: "Serverdan kutilmagan javob qaytdi." };
    }

    if (!res.ok) {
      let errMsg = "Ro'yxatdan o'tishda xatolik yuz berdi.";
      if (data && data.detail) {
        if (typeof data.detail === "string") {
          errMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errMsg = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
        } else if (typeof data.detail === "object") {
          errMsg = data.detail.msg || JSON.stringify(data.detail);
        }
      }
      throw new Error(errMsg);
    }

    // Muvaffaqiyatli ro'yxatdan o'tdi
    showToast("Arizangiz Super Adminga yuborildi! Admin tasdiqlagach hisobingiz faollashadi.", "success");

    // Login tabiga o'tkazish va emailni to'ldirish
    switchAuthTab("login");
    const loginUser = document.getElementById("loginUsername");
    const loginPass = document.getElementById("loginPassword");
    if (loginUser) loginUser.value = email;
    if (loginPass) loginPass.value = "";

    const loginErr = document.getElementById("loginErrorMsg");
    if (loginErr) {
      loginErr.innerHTML = `
        <div style="color:var(--teal);font-weight:700;margin-bottom:2px">✓ Arizangiz muvaffaqiyatli yuborildi!</div>
        <div style="font-size:12px;color:var(--ink-2)">Super Administrator tasdiqlaganidan keyin ushbu login va parolingiz bilan tizimga kira olasiz.</div>
      `;
      loginErr.style.display = "block";
      loginErr.style.background = "var(--teal-soft)";
      loginErr.style.borderColor = "var(--teal)";
    }

  } catch (err) {
    if (errorBox) {
      let displayError = err.message || "Ro'yxatdan o'tishda xatolik";
      if (displayError.includes("[object Object]")) {
        displayError = "Ma'lumotlar to'g'ri kiritilganligini tekshiring.";
      }
      errorBox.textContent = displayError;
      errorBox.style.display = "block";
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ro'yxatdan o'tish (Arizani yuborish) →";
    }
  }
}

function openSubscribeModal() {
  if (!STATE.currentUser) {
    showToast("Obuna bo'lish uchun avval profilga kiring!", "info");
    if (window.openLoginModal) window.openLoginModal();
    return;
  }
  const modal = document.getElementById("subscribeModal");
  if (modal) modal.style.display = "flex";
}

function closeSubscribeModal() {
  const modal = document.getElementById("subscribeModal");
  if (modal) modal.style.display = "none";
}

async function submitSubscribePayment() {
  if (!STATE.currentUser || !STATE.token) {
    showToast("Iltimos, avval profilga kiring!", "error");
    return;
  }

  const methodEl = document.querySelector('input[name="payMethod"]:checked');
  const payMethod = methodEl ? methodEl.value : "click";
  const txInput = document.getElementById("subTxId");
  const txId = txInput ? txInput.value.trim() : "";
  const submitBtn = document.getElementById("btnSubmitPaymentReq");

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Ariza yuborilmoqda...";
  }

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/auth/subscribe`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({
        plan: "pro",
        amount: 10.0, // USD (summa serverda belgilanadi)
        payment_method: payMethod,
        transaction_id: txId
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "To'lov arizasini yuborishda xatolik");
    }

    closeSubscribeModal();
    if (txInput) txInput.value = "";

    showToast("👑 To'lov arizangiz qabul qilindi! Super Admin tasdiqlashi bilan hisobingiz PRO ga o'tadi.", "success");

  } catch (err) {
    showToast(err.message || "To'lov arizasini yuborishda xatolik", "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "💳 To'lov qildim, PRO arizasini yuborish →";
    }
  }
}

function quickFillLogin(user, pass) {
  const userInput = document.getElementById("loginUsername");
  const passInput = document.getElementById("loginPassword");
  if (userInput) userInput.value = user;
  if (passInput) passInput.value = pass;
  handleLoginSubmit();
}

function openAccountSettingsModal() {
  if (!STATE.currentUser) {
    if (window.openLoginModal) window.openLoginModal();
    return;
  }
  const modal = document.getElementById("accountSettingsModal");
  if (!modal) return;

  const currentLoginEl = document.getElementById("settingsCurrentLoginDisplay");
  const currentRoleEl = document.getElementById("settingsCurrentRoleDisplay");
  const fullNameEl = document.getElementById("settingsFullName");
  const newLoginEl = document.getElementById("settingsNewLogin");
  const phoneEl = document.getElementById("settingsPhone");
  const newPassEl = document.getElementById("settingsNewPassword");
  const confirmPassEl = document.getElementById("settingsConfirmPassword");
  const currentPassEl = document.getElementById("settingsCurrentPassword");
  const msgBox = document.getElementById("settingsMsgBox");

  if (currentLoginEl) currentLoginEl.textContent = STATE.currentUser.email || "-";
  if (currentRoleEl) currentRoleEl.textContent = STATE.currentUser.role || "-";
  if (fullNameEl) fullNameEl.value = STATE.currentUser.full_name || "";
  if (newLoginEl) newLoginEl.value = "";
  if (phoneEl) phoneEl.value = STATE.currentUser.phone_number || "";
  if (newPassEl) newPassEl.value = "";
  if (confirmPassEl) confirmPassEl.value = "";
  if (currentPassEl) currentPassEl.value = "";
  if (msgBox) {
    msgBox.style.display = "none";
    msgBox.textContent = "";
  }

  modal.style.display = "flex";
}

function closeAccountSettingsModal() {
  const modal = document.getElementById("accountSettingsModal");
  if (modal) modal.style.display = "none";
  // Hisobni o'chirish bo'limini yig'ib, maydonlarni tozalash
  const det = document.getElementById("deleteAccountDetails"); if (det) det.open = false;
  ["deleteAccountPassword", "deleteAccountConfirm"].forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });
  const dm = document.getElementById("deleteAccountMsg"); if (dm) { dm.style.display = "none"; dm.textContent = ""; }
}

// Ma'lumotlar himoyasi (O'RQ-547): hisobni o'chirish — DELETE /auth/me {password, confirm:"O'CHIRISH"}
async function submitDeleteAccount() {
  const passEl = document.getElementById("deleteAccountPassword");
  const confEl = document.getElementById("deleteAccountConfirm");
  const msg = document.getElementById("deleteAccountMsg");
  const btn = document.getElementById("btnDeleteAccount");
  const showMsg = (t, isError) => {
    if (!msg) return;
    msg.style.display = "block";
    msg.style.background = isError ? "#FDF2F2" : "var(--teal-soft)";
    msg.style.border = isError ? "1px solid #F87171" : "1px solid #BCD9D3";
    msg.style.color = isError ? "#991B1B" : "var(--teal-deep)";
    msg.textContent = t;
  };
  if (!STATE.token || !STATE.currentUser) { showMsg("Avval tizimga kiring.", true); return; }
  const password = passEl ? passEl.value : "";
  const confirm = confEl ? confEl.value.trim() : "";
  if (!password) { showMsg("Joriy parolingizni kiriting.", true); if (passEl) passEl.focus(); return; }
  if (confirm !== "O'CHIRISH") { showMsg("Tasdiqlash uchun aynan O'CHIRISH so'zini (katta harflarda, oddiy apostrof bilan) yozing.", true); if (confEl) confEl.focus(); return; }
  if (btn) { btn.disabled = true; btn.textContent = "⏳ O'chirilmoqda..."; }
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/auth/me`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${STATE.token}` },
      body: JSON.stringify({ password, confirm })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = (typeof data.detail === "string") ? data.detail
        : (Array.isArray(data.detail) && data.detail[0] && data.detail[0].msg) ? data.detail[0].msg
        : `Hisobni o'chirib bo'lmadi (HTTP ${res.status}).`;
      showMsg(detail, true);
      return;
    }
    showToast(data.message || "Hisobingiz o'chirildi: shaxsiy ma'lumotlar anonimlashtirildi.", "success");
    closeAccountSettingsModal();
    if (typeof logout === "function") await logout();
  } catch (e) {
    showMsg("Serverga ulanishda xatolik. Keyinroq qayta urinib ko'ring.", true);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "🗑️ Hisobni butunlay o'chirish"; }
  }
}
window.submitDeleteAccount = submitDeleteAccount;

async function submitAccountSettings() {
  const msgBox = document.getElementById("settingsMsgBox");
  const saveBtn = document.getElementById("btnSaveAccountSettings");
  const currentPassEl = document.getElementById("settingsCurrentPassword");
  const newLoginEl = document.getElementById("settingsNewLogin");
  const newPassEl = document.getElementById("settingsNewPassword");
  const confirmPassEl = document.getElementById("settingsConfirmPassword");
  const fullNameEl = document.getElementById("settingsFullName");
  const phoneEl = document.getElementById("settingsPhone");

  const showMsg = (text, isError = true) => {
    if (!msgBox) return;
    msgBox.textContent = text;
    msgBox.style.display = "block";
    if (isError) {
      msgBox.style.background = "var(--clay-soft)";
      msgBox.style.color = "var(--clay)";
      msgBox.style.border = "1px solid rgba(168,80,58,0.3)";
    } else {
      msgBox.style.background = "var(--teal-soft)";
      msgBox.style.color = "var(--teal)";
      msgBox.style.border = "1px solid rgba(13,110,110,0.3)";
    }
  };

  const currentPassword = (currentPassEl ? currentPassEl.value : "").trim();
  const newLogin = (newLoginEl ? newLoginEl.value : "").trim();
  const newPassword = (newPassEl ? newPassEl.value : "").trim();
  const confirmPassword = (confirmPassEl ? confirmPassEl.value : "").trim();
  const fullName = (fullNameEl ? fullNameEl.value : "").trim();
  const phone = (phoneEl ? phoneEl.value : "").trim();

  if (!currentPassword) {
    showMsg("Iltimos, o'zgarishlarni tasdiqlash uchun amaldagi joriy parolingizni kiriting!");
    return;
  }

  if (newPassword) {
    if (newPassword.length < 4) {
      showMsg("Yangi parol kamida 4 ta belgidan iborat bo'lishi kerak!");
      return;
    }
    if (newPassword !== confirmPassword) {
      showMsg("Yangi parol va uni tasdiqlash maydoni bir-biriga mos kelmadi!");
      return;
    }
  }

  if (newLogin && newLogin.length < 3) {
    showMsg("Yangi login kamida 3 ta belgidan iborat bo'lishi kerak!");
    return;
  }

  const currUser = STATE.currentUser || {};
  const isSameLogin = !newLogin || newLogin.toLowerCase() === (currUser.email || "").toLowerCase();
  const isSameName = fullName === (currUser.full_name || "");
  const isSamePhone = phone === (currUser.phone_number || "");
  if (isSameLogin && !newPassword && isSameName && isSamePhone) {
    showMsg("Hech qanday o'zgarish kiritilmadi. Yangi login yoki yangi parol kiriting.");
    return;
  }

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Saqlanmoqda...";
  }

  try {
    const payload = {
      current_password: currentPassword
    };
    if (newLogin && !isSameLogin) payload.new_login = newLogin;
    if (newPassword) payload.new_password = newPassword;
    if (fullName && !isSameName) payload.full_name = fullName;
    if (phone !== (currUser.phone_number || "")) payload.phone_number = phone;

    const res = await fetch(`${STATE.apiBaseUrl}/auth/change-credentials`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Ma'lumotlarni yangilashda xatolik yuz berdi.");
    }

    STATE.token = data.access_token;
    STATE.currentUser = data.user;
    localStorage.setItem("tilora_token", data.access_token);
    localStorage.setItem("tilora_user", JSON.stringify(data.user));

    applyUserData(data.user);
    showMsg(data.message || "Hisob ma'lumotlari muvaffaqiyatli yangilandi!", false);
    showToast("Profil va hisob ma'lumotlari muvaffaqiyatli saqlandi!", "success");

    setTimeout(() => {
      closeAccountSettingsModal();
    }, 1300);

  } catch (err) {
    showMsg(err.message || "Xatolik yuz berdi");
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "💾 O'zgarishlarni saqlash";
    }
  }
}

function applyUserData(user) {
  const navName = document.getElementById("userNavName");
  const navRole = document.getElementById("userNavRole");
  const navAvatar = document.getElementById("userAvatarLetter");
  const btnLoginLogout = document.getElementById("btnLoginLogout");
  const userProfileBadge = document.getElementById("userProfileBadge");
  const subBadge = document.getElementById("userSubscriptionNavBadge");
  const bannerTierBadge = document.getElementById("bannerTierBadge");
  const bannerTierDesc = document.getElementById("bannerTierDesc");
  const btnOpenSub = document.getElementById("btnOpenSubscribeModal");
  const btnOpenSettings = document.getElementById("btnOpenAccountSettings");
  const profAccountCard = document.getElementById("profileAccountSettingsCard");
  const profAccountBadge = document.getElementById("profAccountLoginBadge");

  // Rol bo'yicha navigatsiya menyusini sinxronlash
  updateRoleNavigation(user ? user.role : "guest");

  if (!user) {
    // 1. Profilga kirmagan holatda (mehmonga) - profil kartochkasi butunlay yashiriladi
    if (userProfileBadge) {
      userProfileBadge.style.display = "none";
    }
    if (btnOpenSettings) {
      btnOpenSettings.style.display = "none";
    }
    if (profAccountCard) {
      profAccountCard.style.display = "none";
    }
    if (navName) navName.textContent = "Mehmon";
    if (navRole) navRole.textContent = "Kirilmagan";
    if (navAvatar) navAvatar.textContent = "?";
    if (subBadge) {
      subBadge.textContent = "GUEST";
      subBadge.style.background = "var(--surface-2)";
      subBadge.style.color = "var(--muted)";
      subBadge.style.border = "none";
    }

    // 2. Faqat "Profilga kirish" deb bitta tugma tursin
    if (btnLoginLogout) {
      btnLoginLogout.innerHTML = '<span style="font-size:13px;margin-right:5px">🔑</span><span>Profilga kirish</span>';
      btnLoginLogout.style.display = "inline-flex";
      btnLoginLogout.style.alignItems = "center";
      btnLoginLogout.style.background = "var(--teal)";
      btnLoginLogout.style.color = "#ffffff";
      btnLoginLogout.style.borderColor = "var(--teal)";
      btnLoginLogout.style.borderRadius = "20px";
      btnLoginLogout.style.padding = "6px 16px";
      btnLoginLogout.style.fontSize = "12.5px";
      btnLoginLogout.style.fontWeight = "600";
      btnLoginLogout.setAttribute("title", "Tizimga / Shaxsiy profilga kirish");
    }
    if (window.applyTranslations) window.applyTranslations();
    return;
  }

  // Profilga kirilgan holatda — profil belgisi va sozlamalar ko'rinadi
  if (userProfileBadge) {
    userProfileBadge.style.display = "flex";
  }
  if (btnOpenSettings) {
    btnOpenSettings.style.display = "inline-flex";
  }
  if (profAccountCard) {
    profAccountCard.style.display = "flex";
  }
  if (profAccountBadge) {
    profAccountBadge.textContent = user.email || "-";
  }
  if (navName) navName.textContent = user.full_name || user.email;
  if (navAvatar) navAvatar.textContent = (user.full_name || user.email).charAt(0).toUpperCase();


  let roleLabel = "Foydalanuvchi";
  if (user.role === "student") {
    roleLabel = `Talaba · ${user.group_name || 'Guruh'}`;
  } else if (user.role === "teacher") {
    roleLabel = "O'qituvchi";
  } else if (user.role === "researcher") {
    roleLabel = "Tadqiqotchi";
  } else if (user.role === "developer") {
    roleLabel = "💻 Dasturchi (API)";
  } else if (user.role === "admin") {
    roleLabel = "Administrator";
  }

  if (navRole) navRole.textContent = roleLabel;

  // Obuna holatini aks ettirish (Free / PRO)
  const isPro = (user.subscription_tier === "pro");
  if (subBadge) {
    if (isPro) {
      subBadge.textContent = "👑 PRO";
      subBadge.style.background = "var(--amber-soft)";
      subBadge.style.color = "var(--amber)";
      subBadge.style.border = "1px solid rgba(138,106,23,0.3)";
    } else {
      subBadge.textContent = "FREE";
      subBadge.style.background = "var(--teal-soft)";
      subBadge.style.color = "var(--teal)";
      subBadge.style.border = "none";
    }
  }

  if (bannerTierBadge) {
    if (isPro) {
      bannerTierBadge.textContent = "👑 PRO (Faol obuna)";
      bannerTierBadge.style.background = "var(--amber)";
      bannerTierBadge.style.color = "#ffffff";
      if (bannerTierDesc) {
        bannerTierDesc.textContent = "Barcha AI vositalari, testlar, taqdimotlar va to'liq tahlildan cheksiz foydalanishingiz mumkin.";
      }
      if (btnOpenSub) {
        btnOpenSub.innerHTML = "👑 PRO Faol";
        btnOpenSub.style.background = "var(--teal)";
        btnOpenSub.onclick = () => showToast("Sizning hisobingiz allaqachon PRO tarifida!", "success");
      }
    } else {
      bannerTierBadge.textContent = "Free (Tekin tarif)";
      bannerTierBadge.style.background = "var(--surface-2)";
      bannerTierBadge.style.color = "var(--ink)";
      if (bannerTierDesc) {
        bannerTierDesc.textContent = "PRO tarif bilan cheksiz AI testlar, taqdimotlar va to'liq tahlildan foydalaning.";
      }
      if (btnOpenSub) {
        btnOpenSub.innerHTML = "👑 PRO ga o'tish (To'lov)";
        btnOpenSub.style.background = "var(--amber)";
        btnOpenSub.onclick = () => window.openSubscribeModal();
      }
    }
  }

  if (btnLoginLogout) {
    btnLoginLogout.innerHTML = '<span>Chiqish</span>';
    btnLoginLogout.style.display = "inline-flex";
    btnLoginLogout.style.alignItems = "center";
    btnLoginLogout.style.background = "none";
    btnLoginLogout.style.color = "var(--ink)";
    btnLoginLogout.style.borderColor = "var(--line)";
    btnLoginLogout.style.borderRadius = "6px";
    btnLoginLogout.style.padding = "5px 12px";
    btnLoginLogout.style.fontSize = "12px";
    btnLoginLogout.style.fontWeight = "500";
    btnLoginLogout.setAttribute("title", "Tizimdan chiqish");
  }
  if (window.applyTranslations) window.applyTranslations();
}


async function loadUserProfile() {
  if (!STATE.currentUser) return;
  try {
    const headers = { "Content-Type": "application/json" };
    if (STATE.token) {
      headers["Authorization"] = `Bearer ${STATE.token}`;
    }

    const res = await fetch(`${STATE.apiBaseUrl}/student/profile`, { headers });
    if (!res.ok) return;
    const prof = await res.json();

    // 1. CEFR darajalari
    if (prof.cefr_levels) {
      const l = prof.cefr_levels.listening || "B1";
      const r = prof.cefr_levels.reading || "B2";
      const s = prof.cefr_levels.speaking || "A2";
      const w = prof.cefr_levels.writing || "B1";

      const lEl = document.getElementById("profListeningLvl");
      const lFill = document.getElementById("profListeningFill");
      if (lEl) lEl.textContent = l;
      if (lFill) lFill.style.width = cefrToPercent(l) + "%";

      const rEl = document.getElementById("profReadingLvl");
      const rFill = document.getElementById("profReadingFill");
      if (rEl) rEl.textContent = r;
      if (rFill) rFill.style.width = cefrToPercent(r) + "%";

      const sEl = document.getElementById("profSpeakingLvl");
      const sFill = document.getElementById("profSpeakingFill");
      if (sEl) sEl.textContent = s;
      if (sFill) sFill.style.width = cefrToPercent(s) + "%";

      const wEl = document.getElementById("profWritingLvl");
      const wFill = document.getElementById("profWritingFill");
      if (wEl) wEl.textContent = w;
      if (wFill) wFill.style.width = cefrToPercent(w) + "%";
    }

    // 2. Kasbiy yo'nalish
    if (prof.professional_track) {
      const trackEl = document.getElementById("profTrackTitle");
      if (trackEl) trackEl.textContent = prof.professional_track;
    }

    // 3. Kognitiv-affektiv
    if (prof.cognitive_affective) {
      const ca = prof.cognitive_affective;
      const loadVal = document.getElementById("profLoadVal");
      const loadFill = document.getElementById("profLoadFill");
      if (loadVal) loadVal.textContent = `${ca.load_capacity || 45}/100`;
      if (loadFill) loadFill.style.width = `${ca.load_capacity || 45}%`;

      const paceVal = document.getElementById("profPaceVal");
      const paceFill = document.getElementById("profPaceFill");
      if (paceVal) paceVal.textContent = `${ca.pace_index || 62}/100`;
      if (paceFill) paceFill.style.width = `${ca.pace_index || 62}%`;

      const anxVal = document.getElementById("profAnxietyVal");
      const anxFill = document.getElementById("profAnxietyFill");
      const anx = ca.anxiety_level || 70;
      const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
      let anxStatus = "";
      if (lang === "ru") {
        anxStatus = anx > 65 ? "Высокий" : (anx > 40 ? "Средний" : "Низкий");
      } else if (lang === "en") {
        anxStatus = anx > 65 ? "High" : (anx > 40 ? "Moderate" : "Low");
      } else {
        anxStatus = anx > 65 ? "Yuqori" : (anx > 40 ? "O'rtacha" : "Past");
      }
      if (anxVal) anxVal.textContent = `${anx}/100 (${anxStatus})`;
      if (anxFill) anxFill.style.width = `${anx}%`;

      const autoVal = document.getElementById("profAutonomyVal");
      const autoFill = document.getElementById("profAutonomyFill");
      if (autoVal) autoVal.textContent = `${ca.autonomy_readiness || 40}/100`;
      if (autoFill) autoFill.style.width = `${ca.autonomy_readiness || 40}%`;

      // 2-Qoida asosi tushuntirishini ham dinamik qilish
      const whyBox = document.getElementById("profWhyBox");
      if (whyBox) {
        const studentName = (STATE.currentUser && STATE.currentUser.full_name) ? STATE.currentUser.full_name : (lang === "ru" ? "Студент" : (lang === "en" ? "Student" : "Talaba"));
        const spkLvl = prof.cefr_levels ? prof.cefr_levels.speaking : "A2";
        if (lang === "ru") {
          whyBox.innerHTML = `
            <b>Основание Правила 2: Почему профиль и траектория сформированы именно так?</b><br>
            Уровень устной речи ${escapeHtml(studentName)} (${spkLvl}), а языковая тревожность ${anxStatus.toLowerCase()} (${anx}/100).
            Поэтому учебная траектория персонализирована с учётом допустимой учебной нагрузки (${ca.load_capacity || 45}/100) и темпа усвоения (${ca.pace_index || 62}/100).
          `;
        } else if (lang === "en") {
          whyBox.innerHTML = `
            <b>Rule 2 Rationale: Why was this profile and learning trajectory generated this way?</b><br>
            ${escapeHtml(studentName)}'s speaking proficiency is (${spkLvl}), with ${anxStatus.toLowerCase()} foreign language anxiety (${anx}/100).
            Therefore, the learning trajectory is personalized according to their cognitive load capacity (${ca.load_capacity || 45}/100) and learning pace (${ca.pace_index || 62}/100).
          `;
        } else {
          whyBox.innerHTML = `
            <b>2-Qoida Asosi: Nima uchun profil va o'quv yo'li aynan shunday shakllantirildi?</b><br>
            ${escapeHtml(studentName)}ning og'zaki nutq ko'rsatkichi (${spkLvl}), chet tili tashvishi esa ${anxStatus.toLowerCase()} (${anx}/100).
            Shu sababli o'quv yo'li uning yuklama sig'imi (${ca.load_capacity || 45}/100) va sur'atiga (${ca.pace_index || 62}/100) mos ravishda shaxsiylashtirilgan.
          `;
        }
      }
    }
  } catch (e) {
    console.warn("Profil ma'lumotlarini yuklashda xatolik:", e);
  }
}

function resetScreensOnLogout() {
  updateRoleNavigation("guest");
  showScreen("s_profile");

  const lEl = document.getElementById("profListeningLvl");
  const rEl = document.getElementById("profReadingLvl");
  const sEl = document.getElementById("profSpeakingLvl");
  const wEl = document.getElementById("profWritingLvl");
  if (lEl) lEl.textContent = "-";
  if (rEl) rEl.textContent = "-";
  if (sEl) sEl.textContent = "-";
  if (wEl) wEl.textContent = "-";

  const lFill = document.getElementById("profListeningFill");
  const rFill = document.getElementById("profReadingFill");
  const sFill = document.getElementById("profSpeakingFill");
  const wFill = document.getElementById("profWritingFill");
  if (lFill) lFill.style.width = "0%";
  if (rFill) rFill.style.width = "0%";
  if (sFill) sFill.style.width = "0%";
  if (wFill) wFill.style.width = "0%";

  const trackEl = document.getElementById("profTrackTitle");
  if (trackEl) trackEl.textContent = "Mehmon holati (Profilga kiring)";

  const whyBox = document.getElementById("profWhyBox");
  if (whyBox) {
    whyBox.innerHTML = `<b>Tizimga kirish:</b> Shaxsiy ta'lim traektoriyasi va CEFR ko'rsatkichlaringizni ko'rish uchun yuqoridagi <i>"Profilga kirish"</i> tugmasi orqali hisobingizga kiring.`;
  }
}

async function logout() {
  // 1. Backend sessiyasiga chiqish so'rovi
  try {
    fetch(`${STATE.apiBaseUrl}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    }).catch(() => {});
  } catch (e) {}

  // 2. Mahalliy xotirani tozalash va chiqqanlik belgisini qo'yish
  localStorage.removeItem("tilora_token");
  localStorage.removeItem("tilora_user");
  localStorage.setItem("tilora_logged_out", "true");
  STATE.token = null;
  STATE.currentUser = null;

  // 3. UI ni Mehmon holatiga o'tkazish
  applyUserData(null);
  resetScreensOnLogout();

  // 4. Bildirishnoma (Toast)
  showToast("Tizimdan muvaffaqiyatli chiqdingiz!", "info");

  // 5. Kirish modalini ochish
  if (window.openLoginModal) {
    window.openLoginModal();
  }
}


// ============================================================
// DIAGNOSTIKA TESTI VA ANKETA BOSHQARUVI
// ============================================================

const DEFAULT_DIAG_QUESTIONS = [
  {
    "id": "diag_01",
    "skill": "listening",
    "cefr_level": "A2",
    "is_audio": true,
    "audio_url": "/audio_diag_01.wav",
    "audio_text": "Could you tell me what time the staff meeting starts?",
    "instruction": "Audioni diqqat bilan tinglang va berilgan so'rovga eng mos javobni tanlang:",
    "question": "Audioni diqqat bilan tinglang va berilgan so'rovga eng mos javobni tanlang:",
    "options": [
      "At 10:00 AM in Room 204.",
      "Yes, I was at the meeting yesterday.",
      "Because the manager is busy.",
      "The meeting was very long."
    ],
    "correct_index": 0
  },
  {
    "id": "diag_02",
    "skill": "listening",
    "cefr_level": "B1",
    "is_audio": true,
    "audio_url": "/audio_diag_02.wav",
    "audio_text": "In your initial weeks of school placement, I strongly encourage you to establish meaningful rapport with your pupils before you enforce strict grading protocols.",
    "instruction": "Audioni diqqat bilan tinglang. Professor talaba-o'qituvchilarga nima bo'yicha asosiy tavsiya bermoqda?",
    "question": "Audioni diqqat bilan tinglang. Professor talaba-o'qituvchilarga nima bo'yicha asosiy tavsiya bermoqda?",
    "options": [
      "Strict discipline is essential in week 1.",
      "Establishing positive connection with pupils precedes rigorous assessment.",
      "Grading should be completely avoided in pedagogical practice.",
      "Rapport is only necessary in elementary schools."
    ],
    "correct_index": 1
  },
  {
    "id": "diag_03",
    "skill": "reading",
    "cefr_level": "B1",
    "question": "Read: 'Differentiated instruction requires teachers to tailor learning pace and content to individual needs rather than adopting a one-size-fits-all paradigm.' What does 'tailor' mean here?",
    "options": [
      "To sew educational uniforms",
      "To adapt and customize specifically",
      "To shorten curriculum hours",
      "To evaluate uniformly"
    ],
    "correct_index": 1
  },
  {
    "id": "diag_04",
    "skill": "reading",
    "cefr_level": "B2",
    "question": "In academic writing, which sentence best exemplifies objective evaluation of teaching methodologies?",
    "options": [
      "I personally think communicative language teaching is the only awesome method.",
      "Empirical findings suggest communicative approaches enhance oral fluency, though grammatical precision may require explicit scaffolding.",
      "Everyone knows traditional grammar translation is totally useless nowadays.",
      "My teacher told us that audiolingualism is the absolute best."
    ],
    "correct_index": 1
  },
  {
    "id": "diag_05",
    "skill": "writing",
    "cefr_level": "A2",
    "question": "Which sentence correctly uses past tense for a lesson observation report?",
    "options": [
      "The teacher begin the lesson with a quick warm-up game.",
      "The teacher begun the lesson yesterday morning.",
      "The teacher began the lesson with a five-minute interactive warmer.",
      "The teacher is beginning the lesson yesterday."
    ],
    "correct_index": 2
  },
  {
    "id": "diag_06",
    "skill": "writing",
    "cefr_level": "B1",
    "question": "Select the sentence with accurate cohesion and transitional phrasing for essay writing:",
    "options": [
      "Formative assessment guides learners. Furthermore, it supplies teachers with actionable diagnostic feedback.",
      "Formative assessment guides learners but also because it supplies teachers.",
      "Formative assessment guides learners, so therefore teachers are happy.",
      "Formative assessment guides learners however it supplies teachers."
    ],
    "correct_index": 0
  },
  {
    "id": "diag_07",
    "skill": "speaking",
    "cefr_level": "A2",
    "question": "In a peer feedback session, which phrase politely introduces a constructive suggestion?",
    "options": [
      "Your pronunciation is very bad.",
      "You might consider varying your intonation during storytelling.",
      "Stop speaking like that immediately.",
      "You must speak without any pause."
    ],
    "correct_index": 1
  },
  {
    "id": "diag_08",
    "skill": "speaking",
    "cefr_level": "B1",
    "question": "When presenting a mini-lesson, which opening phrase best frames lesson objectives for learners?",
    "options": [
      "Today we do something because syllabus says so.",
      "By the end of today's lesson, you will be able to distinguish between active and passive voice in news headlines.",
      "I will talk for 45 minutes about English grammar.",
      "Listen carefully to me."
    ],
    "correct_index": 1
  }
];

const DEFAULT_SURVEY_QUESTIONS = [
  { "id": "sq_01", "dimension": "anxiety", "prompt_uz": "Ingliz tilida auditoriya oldida nutq so'zlashdan oldin kuchli hayajon va xavotir sezaman." },
  { "id": "sq_02", "dimension": "anxiety", "prompt_uz": "Ingliz tilida gapirayotganimda boshqa talabalar mening xatolarim ustidan kulyapti deb o'ylayman." },
  { "id": "sq_03", "dimension": "anxiety", "prompt_uz": "O'qituvchi ingliz tilida kutilmaganda mendan javob so'rasa, o'zimni yo'qotib qo'yaman." },
  { "id": "sq_04", "dimension": "anxiety", "prompt_uz": "Darsda murakkab matn yoki audiomaterial berilganda darhol taslim bo'lish hissi paydo bo'ladi." },
  { "id": "sq_05", "dimension": "load_capacity", "prompt_uz": "Bir mashg'ulotda 15-20 ta yangi kasbiy atama va murakkab sintaktik tuzilmani o'zlashtirish menga qiyinchilik tug'dirmaydi." },
  { "id": "sq_06", "dimension": "load_capacity", "prompt_uz": "Uzoq (400-500 so'zli) ilmiy-pedagogik maqolalarni o'qib, asosiy tezislarini ajratib olishga sabrim yetadi." },
  { "id": "sq_07", "dimension": "pace", "prompt_uz": "Yozma yoki og'zaki topshiriqlarni belgilangan vaqtdan oldinroq, tez va dadil bajarishga odatlanganman." },
  { "id": "sq_08", "dimension": "pace", "prompt_uz": "Javob berishdan oldin uzoq o'ylanib qolmayman, fikrimni tezkor ifoda eta olaman." },
  { "id": "sq_09", "dimension": "autonomy", "prompt_uz": "Topshiriq bajarishda tayyor namuna yoki o'qituvchi yordamisiz mustaqil strategiya tanlay olaman." },
  { "id": "sq_10", "dimension": "autonomy", "prompt_uz": "O'z xatolarimni mustaqil tahlil qilish va o'zlashtirish kamchiliklarini to'ldirish menga qulay." },
  { "id": "sq_11", "dimension": "motivation", "prompt_uz": "Ingliz tilini yaxshi o'rganishimdan maqsad — kelajakda kuchli, xalqaro tajribaga ega metodist-o'qituvchi bo'lish." },
  { "id": "sq_12", "dimension": "motivation", "prompt_uz": "Men uchun faqat imtihondan yuqori baho olish emas, balki tilni chuqur his qilish muhim." }
];

let DIAG_QUESTIONS = [...DEFAULT_DIAG_QUESTIONS];
let SURVEY_QUESTIONS = [...DEFAULT_SURVEY_QUESTIONS];

function initDiagnostic() {
  const diagContainer = document.getElementById("diagnosticQuestionsContainer");
  const surveyContainer = document.getElementById("surveyQuestionsContainer");
  const btnCloseModal = document.getElementById("btnCloseDiagResultModal");
  const btnGoProfile = document.getElementById("btnGoToProfile");
  const resultModal = document.getElementById("diagResultModal");

  window.submitDiagnosticForm = submitDiagnosticForm;

  if (btnCloseModal && resultModal) {
    btnCloseModal.addEventListener("click", () => {
      resultModal.style.display = "none";
    });
  }

  if (btnGoProfile && resultModal) {
    btnGoProfile.addEventListener("click", () => {
      resultModal.style.display = "none";
      showScreen("s_profile");
    });
  }

  if (resultModal) {
    resultModal.addEventListener("click", (e) => {
      if (e.target === resultModal) resultModal.style.display = "none";
    });
  }

  // 1. Darhol (0 ms kutishsiz) savollarni ekranga chiqaramiz!
  renderDiagnosticQuestions(diagContainer);
  renderSurveyQuestions(surveyContainer);

  // 2. Orqa fonda serverdan savollarni yangilab olamiz (o'qituvchi yuklagan bo'lishi mumkin)
  window.reloadDiagnosticQuestions();
}

// Serverdan diagnostika va anketa savollarini yuklash.
// Token yuborilsa, backend talaba guruhiga biriktirilgan o'qituvchining savollarini qaytaradi;
// o'qituvchi hech narsa yuklamagan bo'lsa, standart to'plam keladi.
STATE.diagSubjectId = STATE.diagSubjectId || "";
STATE.diagSubjects = STATE.diagSubjects || [];

// ================================================================
// 16 HAFTALIK O'QUV YO'LI: qatorlar dinamik chiziladi, har qator o'z mashg'ulotiga olib boradi
// ================================================================
const PATH_TOPICS = [
  { id: "top_01", skill: "speaking", weeks: [1, 2], title: "Og'zaki nutq: Kasbiy tanishuv va darsdagi oddiy dialog",
    goal: "Ushbu mashg'ulotda siz past bosimli pedagogik vaziyatda o'zingizni o'qituvchi sifatida tanishtirish, hamkasb va o'quvchilar bilan qulay og'zaki muloqot o'rnatishni o'rganasiz.",
    task: "O'zingizni yangi jamoaga o'qituvchi sifatida tanishtiring va birinchi darsdagi qisqa dialogni ingliz tilida yozing. Hajmi: 100–130 so'z." },
  { id: "top_02", skill: "speaking", weeks: [3, 4], title: "Og'zaki nutq: Kasbiy vaziyatdagi muloqot va ko'rsatma berish",
    goal: "Ushbu mashg'ulotda siz buyruq va modal tuzilmalar (imperative, should, could) orqali topshiriqlarni aniq, qisqa va tushunarli ko'rsatmalar bilan berishni o'rganasiz.",
    task: "Guruh ishi uchun 5 bosqichli ko'rsatma matnini ingliz tilida tuzing: har bosqich bir jumla, buyruq va modal fe'llardan foydalaning. Hajmi: 120–150 so'z." },
  { id: "top_03", skill: "writing", weeks: [5, 6], title: "Yozma nutq: O'quvchilar yozma ishini baholash mezonlari tahlili",
    goal: "Ushbu darsda siz o'quvchilarning ingliz tilidagi yozma ishlarini ob'ektiv baholash mezonlari (Accuracy, Fluency, Coherence, Lexical Resource) bo'yicha tahlil qilishni va kasbiy taqriz yozishni o'rganasiz.",
    task: "O'quvchilarning yozma nutqini baholashda qanday mezonlardan foydalanish mumkin? O'z fikringizni 150–180 so'zda akademik va metodik tilda bayon eting." },
  { id: "top_04", skill: "reading", weeks: [7, 8], title: "O'qish: Metodik ilmiy maqolalarni tanqidiy tahlil qilish",
    goal: "Ushbu mashg'ulotda siz empirik ELT maqolasidan tezis, dalil va pedagogik xulosalarni ajratib olish hamda ularni tanqidiy baholashni o'rganasiz.",
    task: "Tanlagan metodik maqolaning asosiy tezisi, empirik dalillari va amaliy pedagogik xulosalarini tanqidiy tahlil qiling. Hajmi: 150–180 so'z." },
  { id: "top_05", skill: "listening", weeks: [9, 10], title: "Tinglash: Dars kuzatuvi audio va turli talaffuz variantlari",
    goal: "Ushbu mashg'ulotda siz tez sur'atli pedagogik nutqni, turli mintaqaviy talaffuz variantlarini va o'quvchilar savollarini tinglab tushunishni o'rganasiz.",
    task: "Dars kuzatuvi audiosidagi o'qituvchi ko'rsatmalari va o'quvchi savollarini o'z so'zlaringiz bilan ingliz tilida qayta bayon qiling. Hajmi: 120–150 so'z." },
  { id: "top_06", skill: "integrated", weeks: [11, 12], title: "Integratsiyalashgan: Dars rejasi (Lesson Plan) tuzish va himoya qilish",
    goal: "Ushbu mashg'ulotda siz kommunikativ til o'qitish (CLT) tamoyillarini yaxlit qo'llab dars rejasi tuzish va uni asoslab himoya qilishni o'rganasiz.",
    task: "45 daqiqalik kommunikativ dars rejasini tuzing va har bir bosqichning maqsadini metodik asoslang. Hajmi: 180–220 so'z." },
  { id: "top_07", skill: "writing", weeks: [13, 14], title: "Yozma nutq: Metakognitiv reflektiv o'qituvchi kundaligi",
    goal: "Ushbu mashg'ulotda siz reflektiv o'qituvchi kundaligi orqali o'z darsingizni metakognitiv tahlil qilish va keyingi qadamlarni rejalashtirishni o'rganasiz.",
    task: "O'tgan darsingiz haqida reflektiv kundalik yozuvi yozing: nima ishladi, nima ishlamadi va keyingi safar nimani o'zgartirasiz. Hajmi: 150–180 so'z." },
  { id: "top_08", skill: "integrated", weeks: [15, 16], title: "Yakuniy loyiha: Mikrodars taqdimoti va ekspert muhokamasi",
    goal: "Yakuniy mashg'ulotda siz mikrodars taqdimoti va ekspert muhokamasida kasbiy nutqni yaxlit namoyish etasiz: maqsadni bayon qilish, savollarga javob berish, o'z qarorlarini asoslash.",
    task: "Mikrodars taqdimotingiz uchun kirish nutqi va kutilayotgan ekspert savollariga javob tezislarini ingliz tilida yozing. Hajmi: 180–220 so'z." }
];

STATE.pathCurrentWeek = STATE.pathCurrentWeek || 4;
STATE.pathItems = STATE.pathItems || null;      // serverdan kelgan shaxsiy yo'l (bo'lsa)
STATE.currentPathKey = STATE.currentPathKey || "top_03";

function pathSkillBadge(skill) {
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  if (skill === "integrated") {
    const label = lang === "ru" ? "🧩 Интегрированный" : (lang === "en" ? "🧩 Integrated" : "🧩 Integratsiyalashgan");
    return { label, color: "var(--amber)" };
  }
  return getSkillBadge(skill);
}

function pathScaffoldChip(level) {
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  if (level === "none") {
    const label = lang === "ru" ? "без поддержки" : (lang === "en" ? "no support" : "ko'mak yo'q");
    return `<span class="chip none">${label}</span>`;
  }
  if (level === "partial") {
    const label = lang === "ru" ? "частичная поддержка" : (lang === "en" ? "partial support" : "qisman ko'mak");
    return `<span class="chip part">${label}</span>`;
  }
  const label = lang === "ru" ? "полная поддержка" : (lang === "en" ? "full support" : "to'liq ko'mak");
  return `<span class="chip full">${label}</span>`;
}

function pathStatusFor(weeks) {
  const cur = STATE.pathCurrentWeek || 4;
  if (weeks[1] < cur) return { status: "done", progress: 100 };
  if (weeks[0] <= cur && cur <= weeks[1]) return { status: "active", progress: 55 };
  return { status: "planned", progress: 0 };
}

// Har bir qator o'z KEY'iga ega: standart yo'lda mavzu id, shaxsiy (server) yo'lda hafta raqami.
// Shu key orqali bosilgan qator o'z mashg'ulotiga aniq bog'lanadi.
function buildPathRows() {
  const items = Array.isArray(STATE.pathItems) && STATE.pathItems.length ? STATE.pathItems : null;

  if (!items) {
    return PATH_TOPICS.map((t, idx) => {
      const scaffold = idx === 0 ? "none" : (idx === 1 ? "partial" : (t.weeks[0] <= 10 ? "full" : "partial"));
      return { ...t, key: t.id, scaffold, ...pathStatusFor(t.weeks), rationale: "" };
    });
  }

  // Shaxsiy yo'l: server tartibi (hafta, ko'nikma, ko'mak) + mavzu kartasi (maqsad, topshiriq)
  const used = new Set();
  return items.slice().sort((a, b) => (a.week_number || 0) - (b.week_number || 0)).map(it => {
    const w = it.week_number || 2;
    const weeks = [w - 1, w];
    let base = it.topic_id ? PATH_TOPICS.find(t => t.id === it.topic_id) : null;
    if (!base) base = PATH_TOPICS.find(t => t.skill === it.skill && !used.has(t.id)) || PATH_TOPICS.find(t => t.skill === it.skill) || null;
    if (base) used.add(base.id);
    const title = it.topic || (base ? base.title : `${it.skill} bo'yicha kasbiy amaliyot`);
    return {
      key: `w${w}`,
      id: base ? base.id : `path_w${w}`,
      skill: it.skill || (base ? base.skill : "reading"),
      weeks,
      title,
      goal: base ? base.goal : (it.pedagogical_focus || `Ushbu mashg'ulotda siz "${title}" mavzusi bo'yicha kasbiy ko'nikmani rivojlantirasiz.`),
      task: base ? base.task : `"${title}" mavzusi bo'yicha 150–180 so'zli akademik matn yozing.`,
      scaffold: it.scaffold_level || "full",
      rationale: it.rationale || "",
      ...pathStatusFor(weeks)
    };
  });
}

window.renderLearningPath = function() {
  const box = document.getElementById("pathRowsContainer");
  if (!box) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const rows = buildPathRows();
  box.innerHTML = rows.map(r => {
    const badge = pathSkillBadge(r.skill);
    const sel = r.key === STATE.currentPathKey ? " selected" : "";
    const weekStr = lang === "ru" ? `${r.weeks[0]}–${r.weeks[1]} недели` : (lang === "en" ? `Weeks ${r.weeks[0]}–${r.weeks[1]}` : `${r.weeks[0]}–${r.weeks[1]}-hafta`);
    const statusDone = lang === "ru" ? " · ✅ завершено" : (lang === "en" ? " · ✅ completed" : " · ✅ yakunlangan");
    const statusActive = lang === "ru" ? " · ▶ текущее" : (lang === "en" ? " · ▶ active" : " · ▶ hozirgi");
    const actionLabel = lang === "ru" ? "Занятие →" : (lang === "en" ? "Lesson →" : "Mashg'ulot →");
    const rowTitle = lang === "ru" ? "Открыть страницу занятия" : (lang === "en" ? "Open lesson page" : "Mashg'ulot sahifasini ochish");

    return `
      <div class="path-row ${r.status === "done" ? "done" : (r.status === "active" ? "active" : "")}${sel}" data-topic="${r.key}" role="button" tabindex="0"
           title="${escapeHtml(r.rationale || rowTitle)}"
           onclick="window.openPathLesson('${r.key}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();window.openPathLesson('${r.key}')}">
        <div class="path-week">${weekStr}</div>
        <div class="path-name">
          <div>${escapeHtml(r.title)}</div>
          <div style="font-size:11.5px;color:${badge.color};font-weight:600;margin-top:2px">${badge.label}${r.status === "done" ? statusDone : (r.status === "active" ? statusActive : "")}</div>
        </div>
        <div style="width:160px"><div class="track"><div class="fill" style="width:${r.progress}%"></div></div></div>
        ${pathScaffoldChip(r.scaffold)}
        <span class="path-go">${actionLabel}</span>
      </div>`;
  }).join("");

  const sub = document.getElementById("pathSubtitle");
  if (sub) {
    if (lang === "ru") {
      sub.textContent = `Идёт ${STATE.pathCurrentWeek || 4}-я неделя обучения · Нажмите на строку, чтобы открыть занятие`;
    } else if (lang === "en") {
      sub.textContent = `Currently in Week ${STATE.pathCurrentWeek || 4} · Click any row to open the lesson page`;
    } else {
      sub.textContent = `Hozirda ${STATE.pathCurrentWeek || 4}-hafta davom etmoqda · Qatorni bosing — mavzuning mashg'ulot sahifasi ochiladi`;
    }
  }

  // Kirgan foydalanuvchi uchun shaxsiy yo'lni orqa fonda yangilaymiz (bir marta)
  if (STATE.token && STATE.pathItems === null) {
    STATE.pathItems = [];   // qayta so'rov ketmasin
    fetch(`${STATE.apiBaseUrl}/student/path`, { headers: { "Authorization": `Bearer ${STATE.token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data || !Array.isArray(data.items) || !data.items.length) return;
        STATE.pathItems = data.items;
        if (data.current_week) STATE.pathCurrentWeek = data.current_week;
        window.renderLearningPath();
      })
      .catch(() => {});
  }
};

// Qator bosilganda: mashg'ulot sahifasini shu qatorning mavzusi bilan to'ldirib ochish
window.openPathLesson = function(key) {
  const rows = buildPathRows();
  const t = rows.find(r => r.key === key) || rows.find(r => r.id === key);
  if (!t) return;
  STATE.currentPathKey = t.key;
  STATE.lessonStage = 1;

  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const badge = pathSkillBadge(t.skill);
  const title = document.getElementById("lessonTitle");
  const sub = document.getElementById("lessonSubtitle");
  const goal = document.getElementById("lessonGoalText");
  const task = document.getElementById("lessonTaskText");
  const cleanTitle = t.title.replace(/^[^:]+:\s*/, "");

  if (lang === "ru") {
    if (title) title.textContent = `Занятие: ${cleanTitle}`;
    if (sub) sub.textContent = `${t.weeks[0]}–${t.weeks[1]} недели · ${badge.label} · 5-этапный адаптивно-метакогнитивный цикл`;
    if (goal) goal.textContent = t.goal;
    if (task) task.innerHTML = `<b>Задание:</b> ${escapeHtml(t.task)}`;
  } else if (lang === "en") {
    if (title) title.textContent = `Lesson: ${cleanTitle}`;
    if (sub) sub.textContent = `Weeks ${t.weeks[0]}–${t.weeks[1]} · ${badge.label} · 5-Stage Adaptive-Metacognitive Flow`;
    if (goal) goal.textContent = t.goal;
    if (task) task.innerHTML = `<b>Task:</b> ${escapeHtml(t.task)}`;
  } else {
    if (title) title.textContent = `Mashg'ulot: ${cleanTitle}`;
    if (sub) sub.textContent = `${t.weeks[0]}–${t.weeks[1]}-hafta · ${badge.label} · Besh bosqichli adaptiv-metakognitiv oqim`;
    if (goal) goal.textContent = t.goal;
    if (task) task.innerHTML = `<b>Savol:</b> ${escapeHtml(t.task)}`;
  }

  const editor = document.getElementById("productionText");
  if (editor) {
    if (lang === "ru") {
      editor.placeholder = `Напишите текст по теме "${t.title}" исключительно самостоятельно. На этом этапе инструменты ИИ отключены...`;
    } else if (lang === "en") {
      editor.placeholder = `Write the text on "${t.title}" completely on your own. AI tools are locked during this stage...`;
    } else {
      editor.placeholder = `"${t.title}" mavzusi bo'yicha matnni faqat o'zingiz yozing. Ushbu bosqichda sun'iy intellekt vositalari o'chirilgan...`;
    }
  }

  document.querySelectorAll("#pathRowsContainer .path-row").forEach(el => el.classList.toggle("selected", el.dataset.topic === t.key));
  showScreen("s_lesson");
  window.scrollTo({ top: 0, behavior: "smooth" });
};

// Fan tanlagichni to'ldirish: barcha ochiq fanlar ro'yxati (+ umumiy to'plam)
STATE.diagSkillFilter = STATE.diagSkillFilter || "";
const DIAG_SKILL_ORDER = ["listening", "reading", "writing", "speaking"];

function renderDiagSubjectBar() {
  const bar = document.getElementById("diagSubjectBar");
  const sel = document.getElementById("diagSubjectSelect");
  const hint = document.getElementById("diagSubjectHint");
  if (!bar || !sel) return;
  const subjects = STATE.diagSubjects || [];
  const withSubjects = subjects.filter(sb => sb.id);
  if (!withSubjects.length) {
    bar.style.display = "none";
    return;
  }
  bar.style.display = "flex";
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  sel.innerHTML = subjects.map(sb => {
    let countBadge = "";
    if (sb.id) {
      const own = sb.own_diag_count || 0;
      if (lang === "ru") {
        countBadge = own > 0 ? ` · ${own} спец. вопросов` : ` · (общий банк вопросов)`;
      } else if (lang === "en") {
        countBadge = own > 0 ? ` · ${own} specific questions` : ` · (general pool)`;
      } else {
        countBadge = own > 0 ? ` · ${own} ta maxsus test` : ` · (maxsus savol yo'q, umumiy to'plam)`;
      }
    } else {
      if (lang === "ru") {
        countBadge = ` · ${sb.diag_count} тестов · ${sb.survey_count} анкет`;
      } else if (lang === "en") {
        countBadge = ` · ${sb.diag_count} tests · ${sb.survey_count} surveys`;
      } else {
        countBadge = ` · ${sb.diag_count} test · ${sb.survey_count} anketa`;
      }
    }
    const generalLabel = lang === "ru" ? "🌐 Общий банк" : (lang === "en" ? "🌐 General Pool" : "🌐 Umumiy to'plam");
    const label = sb.id
      ? `${sb.name}${sb.code ? " (" + sb.code + ")" : ""}${sb.teacher_name ? " — " + sb.teacher_name : ""}${countBadge}`
      : `${generalLabel}${countBadge}`;
    return `<option value="${sb.id || ""}" ${(sb.id || "") === STATE.diagSubjectId ? "selected" : ""}>${escapeHtml(label)}</option>`;
  }).join("");
  if (hint) {
    const cur = subjects.find(sb => (sb.id || "") === STATE.diagSubjectId);
    if (cur && cur.id) {
      const own = cur.own_diag_count || 0;
      const canManage = STATE.user && ["teacher", "admin"].includes(STATE.user.role);
      const manageText = lang === "ru" ? "⚙️ Перейти в банк вопросов (+ Добавить вопрос)" : (lang === "en" ? "⚙️ Go to Question Bank (+ Add Question)" : "⚙️ Savollar bankiga o'tish (+ Savol qo'shish)");
      const manageLink = canManage
        ? ` <a href="#" onclick="showScreen('s_diag_manage');return false;" style="color:var(--teal);font-weight:700;text-decoration:underline;margin-left:6px">${manageText}</a>`
        : "";
      if (lang === "ru") {
        hint.innerHTML = own
          ? `<span style="color:#059669;font-weight:600">✅ Для этого предмета загружено ${own} специальных вопросов.</span>`
          : `<span style="color:#d97706;font-weight:600">⚠️ Для этого предмета ещё нет специальных вопросов</span> — отображается общий банк.${manageLink}`;
      } else if (lang === "en") {
        hint.innerHTML = own
          ? `<span style="color:#059669;font-weight:600">✅ ${own} specific questions loaded for this course.</span>`
          : `<span style="color:#d97706;font-weight:600">⚠️ No specific questions for this course yet</span> — displaying general pool.${manageLink}`;
      } else {
        hint.innerHTML = own
          ? `<span style="color:#059669;font-weight:600">✅ Ushbu fan uchun ${own} ta maxsus savol yuklandi.</span>`
          : `<span style="color:#d97706;font-weight:600">⚠️ Ushbu fanga hali maxsus diagnostika savoli kiritilmagan</span> — umumiy to'plam ko'rsatilmoqda.${manageLink}`;
      }
    } else {
      if (lang === "ru") {
        hint.textContent = "При выборе предмета отображаются соответствующие навыки и вопросы.";
      } else if (lang === "en") {
        hint.textContent = "Select a course to display its skills and diagnostic questions.";
      } else {
        hint.textContent = "Fan tanlansa, shu fanga tegishli ko'nikmalar va savollar chiqadi.";
      }
    }
  }
  renderDiagSkillBar();
}

// Tanlangan fan ko'nikmalari: yuklangan savollardan aniq hisoblanadi (server sonlari — zaxira)
function renderDiagSkillBar() {
  const skillBar = document.getElementById("diagSkillBar");
  const chips = document.getElementById("diagSkillChips");
  if (!skillBar || !chips) return;

  const counts = {};
  DIAG_SKILL_ORDER.forEach(sk => counts[sk] = 0);
  if (DIAG_QUESTIONS.length) {
    DIAG_QUESTIONS.forEach(q => { const sk = (q.skill || "reading").toLowerCase(); counts[sk] = (counts[sk] || 0) + 1; });
  } else {
    const cur = (STATE.diagSubjects || []).find(sb => (sb.id || "") === STATE.diagSubjectId);
    Object.assign(counts, (cur && cur.skills) || {});
  }
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (!total) { skillBar.style.display = "none"; return; }
  skillBar.style.display = "flex";

  // Filtr tanlangan ko'nikmada savol qolmasa (fan o'zgarganda), "Barchasi"ga qaytamiz
  if (STATE.diagSkillFilter && !counts[STATE.diagSkillFilter]) STATE.diagSkillFilter = "";

  const chip = (value, label, color, n) => {
    const active = STATE.diagSkillFilter === value;
    const disabled = n === 0;
    return `<button type="button" ${disabled ? "disabled" : ""} onclick="window.setDiagSkillFilter('${value}')"
      style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:16px;font-size:12.5px;font-weight:600;cursor:${disabled ? "not-allowed" : "pointer"};
             border:1.5px solid ${active ? color : "var(--line)"};background:${active ? color : "var(--card)"};color:${active ? "#fff" : (disabled ? "var(--muted)" : color)};opacity:${disabled ? 0.5 : 1};transition:all .15s">
      ${label} <span style="font-size:11px;padding:1px 7px;border-radius:10px;background:${active ? "rgba(255,255,255,0.25)" : "var(--surface-2)"};color:${active ? "#fff" : "var(--ink-2)"}">${n}</span>
    </button>`;
  };
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const allLabel = lang === "ru" ? "📋 Все" : (lang === "en" ? "📋 All" : "📋 Barchasi");
  chips.innerHTML = chip("", allLabel, "var(--ink)", total)
    + DIAG_SKILL_ORDER.map(sk => { const b = getSkillBadge(sk); return chip(sk, b.label, b.color, counts[sk] || 0); }).join("");
}

window.setDiagSkillFilter = function(skill) {
  STATE.diagSkillFilter = skill || "";
  renderDiagSkillBar();
  renderDiagnosticQuestions(document.getElementById("diagnosticQuestionsContainer"));
};

window.onDiagSubjectChange = function() {
  const sel = document.getElementById("diagSubjectSelect");
  STATE.diagSubjectId = sel ? sel.value : "";
  STATE.diagSkillFilter = "";
  STATE.diagAnswers = {};
  STATE.surveyAnswers = {};
  renderDiagSubjectBar();
  window.reloadDiagnosticQuestions(true);
};

window.reloadDiagnosticQuestions = function(skipSubjects) {
  const diagContainer = document.getElementById("diagnosticQuestionsContainer");
  const surveyContainer = document.getElementById("surveyQuestionsContainer");
  const headers = {};
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  if (!skipSubjects) {
    fetch(`${STATE.apiBaseUrl}/student/diagnostic/subjects`, { headers })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return;
        STATE.diagSubjects = data.subjects || [];
        // Oldin tanlangan fan endi ro'yxatda yo'q bo'lsa (masalan, o'chirilgan), umumiyga qaytamiz
        if (STATE.diagSubjectId && !STATE.diagSubjects.some(sb => sb.id === STATE.diagSubjectId)) {
          STATE.diagSubjectId = "";
          window.reloadDiagnosticQuestions(true);
        }
        renderDiagSubjectBar();
        // Zaxira: diagnostika endpointi fanlarni bermasa, umumiy fanlar ro'yxatidan to'ldiramiz
        if (!STATE.diagSubjects.some(sb => sb.id)) {
          const general = STATE.diagSubjects.find(sb => !sb.id) || { diag_count: DIAG_QUESTIONS.length, survey_count: SURVEY_QUESTIONS.length };
          fetch(`${STATE.apiBaseUrl}/student/subjects`, { headers })
            .then(r => r.ok ? r.json() : null)
            .then(d2 => {
              const list = (d2 && d2.subjects) || [];
              if (!list.length) return;
              STATE.diagSubjects = [general].concat(list.map(sb => ({
                id: sb.id, name: sb.name || sb.title, code: sb.code || "", teacher_name: sb.teacher_name || "",
                own_diag_count: 0, own_survey_count: 0,
                diag_count: general.diag_count || 0, survey_count: general.survey_count || 0, skills: general.skills || {}
              })));
              renderDiagSubjectBar();
            })
            .catch(() => {});
        }
      })
      .catch(() => {});
  }

  const qs = STATE.diagSubjectId ? `?subject_id=${encodeURIComponent(STATE.diagSubjectId)}` : "";

  const updateChip = () => {
    const chip = document.getElementById("diagProgressChip");
    const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
    if (chip) {
      if (lang === "ru") {
        chip.textContent = `${DIAG_QUESTIONS.length} вопросов теста · ${SURVEY_QUESTIONS.length} вопросов анкеты`;
      } else if (lang === "en") {
        chip.textContent = `${DIAG_QUESTIONS.length} test questions · ${SURVEY_QUESTIONS.length} survey questions`;
      } else {
        chip.textContent = `${DIAG_QUESTIONS.length} ta test savoli · ${SURVEY_QUESTIONS.length} ta anketa`;
      }
    }
  };

  fetch(`${STATE.apiBaseUrl}/student/diagnostic/questions${qs}`, { headers })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (Array.isArray(data)) {
        const changed = JSON.stringify(data.map(q => q.id)) !== JSON.stringify(DIAG_QUESTIONS.map(q => q.id));
        DIAG_QUESTIONS = data;
        if (changed) {
          // Savollar to'plami o'zgargan bo'lsa, eski javoblar yaroqsiz
          Object.keys(STATE.diagAnswers).forEach(k => { if (!data.some(q => q.id === k)) delete STATE.diagAnswers[k]; });
        }
        renderDiagnosticQuestions(diagContainer);
        renderDiagSkillBar();
        updateChip();
      }
    })
    .catch(() => {});

  fetch(`${STATE.apiBaseUrl}/student/survey/questions${qs}`, { headers })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (Array.isArray(data)) {
        const changed = JSON.stringify(data.map(q => q.id)) !== JSON.stringify(SURVEY_QUESTIONS.map(q => q.id));
        SURVEY_QUESTIONS = data;
        if (changed) {
          Object.keys(STATE.surveyAnswers).forEach(k => { if (!data.some(q => q.id === k)) delete STATE.surveyAnswers[k]; });
        }
        renderSurveyQuestions(surveyContainer);
        updateChip();
      }
    })
    .catch(() => {});
};

function getSkillBadge(skill) {
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  if (lang === "ru") {
    switch (skill) {
      case "listening": return { label: "🎧 Аудирование", color: "var(--teal)" };
      case "reading": return { label: "📖 Чтение", color: "#2563EB" };
      case "writing": return { label: "✍️ Письмо", color: "#7C3AED" };
      case "speaking": return { label: "🗣️ Говорение", color: "var(--clay)" };
      default: return { label: "📘 Языковой навык", color: "var(--ink-2)" };
    }
  }
  if (lang === "en") {
    switch (skill) {
      case "listening": return { label: "🎧 Listening", color: "var(--teal)" };
      case "reading": return { label: "📖 Reading", color: "#2563EB" };
      case "writing": return { label: "✍️ Writing", color: "#7C3AED" };
      case "speaking": return { label: "🗣️ Speaking", color: "var(--clay)" };
      default: return { label: "📘 Language Skill", color: "var(--ink-2)" };
    }
  }
  switch (skill) {
    case "listening": return { label: "🎧 Tinglab tushunish", color: "var(--teal)" };
    case "reading": return { label: "📖 O'qish", color: "#2563EB" };
    case "writing": return { label: "✍️ Yozma nutq", color: "#7C3AED" };
    case "speaking": return { label: "🗣️ Og'zaki nutq", color: "var(--clay)" };
    default: return { label: "📘 Til ko'nikmasi", color: "var(--ink-2)" };
  }
}

function renderDiagnosticQuestions(container) {
  if (!container) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const countLabel = document.getElementById("diagCountLabel");
  if (!DIAG_QUESTIONS.length) {
    if (countLabel) countLabel.textContent = lang === "ru" ? "0 вопросов" : (lang === "en" ? "0 questions" : "0 ta savol");
    const emptyTitle = lang === "ru" ? "Специальные диагностические вопросы по этому предмету не найдены." : (lang === "en" ? "No diagnostic questions found for this subject." : "Ushbu fan bo'yicha maxsus diagnostika savollari topilmadi.");
    const emptySub = lang === "ru" ? "Выберите другой предмет или «Общий банк» выше." : (lang === "en" ? "Select another course or 'General Pool' above." : "Yuqoridagi tanlagichdan boshqa fanni yoki \"🌐 Umumiy to'plam\"ni tanlang.");
    container.innerHTML = `<div style="text-align:center;padding:30px 20px;color:var(--muted);background:var(--surface-2);border-radius:10px;border:1px dashed var(--line)">
      <div style="font-size:24px;margin-bottom:8px">📭</div>
      <b style="color:var(--ink)">${emptyTitle}</b>
      <p style="font-size:13px;margin:6px 0 0">${emptySub}</p>
    </div>`;
    return;
  }

  const filter = STATE.diagSkillFilter || "";
  const visible = filter ? DIAG_QUESTIONS.filter(q => (q.skill || "reading").toLowerCase() === filter) : DIAG_QUESTIONS;
  if (countLabel) {
    const qWord = lang === "ru" ? "вопросов" : (lang === "en" ? "questions" : "ta savol");
    countLabel.textContent = filter
      ? `${visible.length} / ${DIAG_QUESTIONS.length} ${qWord} (${getSkillBadge(filter).label})`
      : `${DIAG_QUESTIONS.length} ${qWord}`;
  }
  if (!visible.length) {
    const noQMsg = lang === "ru" ? "По этому навыку вопросов нет." : (lang === "en" ? "No questions for this skill." : "Bu ko'nikma bo'yicha savol yo'q.");
    const showAllMsg = lang === "ru" ? "Показать все" : (lang === "en" ? "Show all" : "Barchasini ko'rsatish");
    container.innerHTML = `<div style="text-align:center;padding:20px;color:var(--muted)">${noQMsg} <a href="#" onclick="window.setDiagSkillFilter('');return false;" style="color:var(--teal);font-weight:600">${showAllMsg}</a></div>`;
    return;
  }

  const audioPlayLabel = lang === "ru" ? "Прослушать аудио" : (lang === "en" ? "Play Audio" : "Audioni tinglash");
  const audioInst = lang === "ru" ? "🎧 Прослушайте аудио и выберите правильный вариант" : (lang === "en" ? "🎧 Listen to the audio and choose the correct answer" : "🎧 Matnni eshitib, to'g'ri variantni belgilang");
  const questionWord = lang === "ru" ? "Вопрос" : (lang === "en" ? "Question" : "Savol");

  container.innerHTML = visible.map((q) => {
    const qIdx = DIAG_QUESTIONS.indexOf(q);
    const badge = getSkillBadge(q.skill);
    const selected = STATE.diagAnswers[q.id];
    const isAudio = q.is_audio || q.skill === "listening";

    const audioPlayerHtml = isAudio ? `
      <div style="background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:14px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <button type="button" id="btnAudio_${q.id}" onclick="window.playListeningAudio('${q.id}')" style="display:inline-flex;align-items:center;gap:8px;padding:9px 18px;border-radius:24px;font-weight:600;font-size:13px;cursor:pointer;background:linear-gradient(135deg, #10b981 0%, #059669 100%);color:#fff;border:none;box-shadow:0 2px 6px rgba(16,185,129,0.3);transition:all 0.2s">
          <span id="iconAudio_${q.id}">▶</span> <span id="labelAudio_${q.id}">${audioPlayLabel}</span>
        </button>
        <div id="audioWave_${q.id}" style="display:none;align-items:center;gap:4px">
          <span class="sound-wave-bar"></span>
          <span class="sound-wave-bar"></span>
          <span class="sound-wave-bar"></span>
          <span class="sound-wave-bar"></span>
          <span class="sound-wave-bar"></span>
          <span style="font-size:12px;color:var(--teal);margin-left:6px;font-weight:600">${lang === "ru" ? "Воспроизведение..." : (lang === "en" ? "Playing..." : "Ijro etilmoqda...")}</span>
        </div>
        <div style="margin-left:auto;font-size:12px;color:var(--muted);display:flex;align-items:center;gap:4px">
          <span>${audioInst}</span>
        </div>
      </div>
    ` : "";

    return `
      <div style="background:var(--surface-2);padding:16px;border-radius:10px;border:1px solid var(--line)" id="diag_box_${q.id}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
          <span style="font-size:12px;font-weight:700;color:${badge.color};background:var(--card);padding:3px 10px;border-radius:12px;border:1px solid var(--line)">
            ${badge.label} (${q.cefr_level || "B1"})
          </span>
          <span style="font-size:12px;color:var(--muted)">${questionWord} ${qIdx + 1} / ${DIAG_QUESTIONS.length}</span>
        </div>
        <p style="font-size:14.5px;color:var(--ink);font-weight:600;margin-bottom:${isAudio ? '10px' : '14px'};line-height:1.6">
          ${escapeHtml(q.instruction || q.question)}
        </p>
        ${audioPlayerHtml}
        <div style="display:flex;flex-direction:column;gap:8px">
          ${q.options.map((opt, optIdx) => `
            <label id="opt_label_${q.id}_${optIdx}" style="display:flex;gap:10px;align-items:center;padding:10px 14px;background:${selected === optIdx ? "rgba(16, 185, 129, 0.08)" : "var(--card)"};border-radius:8px;border:1px solid ${selected === optIdx ? "var(--teal)" : "var(--line)"};cursor:pointer;font-size:13.5px;transition:all 0.2s">
              <input type="radio" name="diag_${q.id}" value="${optIdx}" ${selected === optIdx ? "checked" : ""} onchange="window.setDiagAnswer('${q.id}', ${optIdx})">
              <span><b>${String.fromCharCode(65 + optIdx)})</b> ${escapeHtml(opt)}</span>
            </label>
          `).join("")}
        </div>
      </div>
    `;
  }).join("");
}

window.currentListeningAudio = null;
window.currentListeningQid = null;

window.playListeningAudio = function(qid) {
  const q = DIAG_QUESTIONS.find(item => item.id === qid);
  if (!q) return;

  const btn = document.getElementById(`btnAudio_${qid}`);
  const icon = document.getElementById(`iconAudio_${qid}`);
  const label = document.getElementById(`labelAudio_${qid}`);
  const wave = document.getElementById(`audioWave_${qid}`);

  // Agar ayni shu audio hozir ijro etilayotgan bo'lsa - to'xtatish (toggle pause)
  if (window.currentListeningQid === qid && window.currentListeningAudio) {
    if (window.currentListeningAudio.pause) {
      window.currentListeningAudio.pause();
      if (window.currentListeningAudio.currentTime !== undefined) {
        window.currentListeningAudio.currentTime = 0;
      }
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    window.resetListeningAudioUI(qid);
    window.currentListeningAudio = null;
    window.currentListeningQid = null;
    return;
  }

  // Agar boshqa biror audio ijro etilayotgan bo'lsa, uni to'xtatamiz
  if (window.currentListeningQid && window.currentListeningQid !== qid) {
    if (window.currentListeningAudio && window.currentListeningAudio.pause) {
      window.currentListeningAudio.pause();
      if (window.currentListeningAudio.currentTime !== undefined) {
        window.currentListeningAudio.currentTime = 0;
      }
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    window.resetListeningAudioUI(window.currentListeningQid);
    window.currentListeningAudio = null;
    window.currentListeningQid = null;
  }

  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  // UI ni ijro holatiga o'tkazish
  if (icon) icon.textContent = "⏹";
  if (label) label.textContent = lang === "ru" ? "Остановить" : (lang === "en" ? "Stop" : "To'xtatish");
  if (wave) wave.style.display = "inline-flex";
  if (btn) btn.style.background = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)";

  window.currentListeningQid = qid;

  const onEnd = () => {
    window.resetListeningAudioUI(qid);
    window.currentListeningAudio = null;
    window.currentListeningQid = null;
  };

  // 1. Audio fayl orqali ijro etishga harakat qilamiz
  if (q.audio_url) {
    const audio = new Audio(q.audio_url);
    window.currentListeningAudio = audio;

    audio.onended = onEnd;
    audio.onerror = (e) => {
      console.warn("Audio fayli ochilmadi, brauzer ovoziga o'tilmoqda (TTS):", e);
      window.playTtsFallback(q.audio_text || q.question, onEnd);
    };

    audio.play().catch(err => {
      console.warn("Audio play() cheklandi, TTS ga o'tilmoqda:", err);
      window.playTtsFallback(q.audio_text || q.question, onEnd);
    });
  } else if (q.audio_text) {
    window.playTtsFallback(q.audio_text, onEnd);
  } else {
    onEnd();
  }
};

window.resetListeningAudioUI = function(qid) {
  const btn = document.getElementById(`btnAudio_${qid}`);
  const icon = document.getElementById(`iconAudio_${qid}`);
  const label = document.getElementById(`labelAudio_${qid}`);
  const wave = document.getElementById(`audioWave_${qid}`);
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";

  if (icon) icon.textContent = "▶";
  if (label) label.textContent = lang === "ru" ? "🔄 Слушать снова" : (lang === "en" ? "🔄 Replay" : "🔄 Qayta tinglash");
  if (wave) wave.style.display = "none";
  if (btn) btn.style.background = "linear-gradient(135deg, #10b981 0%, #059669 100%)";
};

window.playTtsFallback = function(text, onEnd) {
  if (!window.speechSynthesis) {
    if (onEnd) onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "en-US";
  utter.rate = 0.9;
  utter.pitch = 1.0;
  utter.onend = () => { if (onEnd) onEnd(); };
  utter.onerror = () => { if (onEnd) onEnd(); };
  window.currentListeningAudio = { pause: () => window.speechSynthesis.cancel() };
  window.speechSynthesis.speak(utter);
};

window.stopListeningAudio = function() {
  if (window.currentListeningAudio && window.currentListeningAudio.pause) {
    window.currentListeningAudio.pause();
    if (window.currentListeningAudio.currentTime !== undefined) {
      window.currentListeningAudio.currentTime = 0;
    }
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  if (window.currentListeningQid) {
    window.resetListeningAudioUI(window.currentListeningQid);
  }
  window.currentListeningAudio = null;
  window.currentListeningQid = null;
};

window.setDiagAnswer = function(qid, optIdx) {
  STATE.diagAnswers[qid] = optIdx;
  const labels = document.querySelectorAll(`label[id^="opt_label_${qid}_"]`);
  labels.forEach((lbl, idx) => {
    if (idx === optIdx) {
      lbl.style.background = "rgba(16, 185, 129, 0.08)";
      lbl.style.borderColor = "var(--teal)";
    } else {
      lbl.style.background = "var(--card)";
      lbl.style.borderColor = "var(--line)";
    }
  });
};

const SURVEY_TRANSLATIONS = {
  sq_01: {
    ru: "Я испытываю сильное волнение и тревогу перед публичным выступлением на английском языке.",
    en: "I feel strong anxiety and nervousness before speaking English in front of an audience."
  },
  sq_02: {
    ru: "Когда я говорю по-английски, мне кажется, что другие студенты смеются над моими ошибками.",
    en: "When speaking English, I worry that other students might laugh at my mistakes."
  },
  sq_03: {
    ru: "Если преподаватель неожиданно обращается ко мне на английском языке, я теряюсь.",
    en: "I get confused and lost when the teacher unexpectedly asks me a question in English."
  },
  sq_04: {
    ru: "При получении сложного текста или аудиозаписи на уроке у меня сразу возникает желание сдаться.",
    en: "When given complex reading or listening material in class, I feel an urge to give up immediately."
  },
  sq_05: {
    ru: "Освоение 15–20 новых профессиональных терминов и сложных синтаксических конструкций за одно занятие не вызывает у меня затруднений.",
    en: "Mastering 15–20 new professional terms and complex syntactic structures in a single lesson is not difficult for me."
  },
  sq_06: {
    ru: "У меня достаточно терпения, чтобы читать длинные научно-педагогические статьи (400–500 слов) и выделять ключевые тезисы.",
    en: "I have the patience to read long academic-pedagogical articles (400–500 words) and extract key theses."
  },
  sq_07: {
    ru: "Я привык выполнять письменные или устные задания быстрее установленного времени, уверенно и оперативно.",
    en: "I am used to completing written or oral assignments ahead of the deadline with speed and confidence."
  },
  sq_08: {
    ru: "Я не задумываюсь подолгу перед ответом, могу быстро и чётко сформулировать свою мысль.",
    en: "I do not hesitate for long before responding; I can formulate and express my thoughts quickly."
  },
  sq_09: {
    ru: "При выполнении задания я могу самостоятельно выбрать стратегию без готового образца или подсказки преподавателя.",
    en: "When doing assignments, I can choose an independent strategy without relying on templates or teacher guidance."
  },
  sq_10: {
    ru: "Мне комфортно самостоятельно анализировать свои ошибки и устранять пробелы в знаниях.",
    en: "I find it comfortable to independently analyze my mistakes and fill learning gaps."
  },
  sq_11: {
    ru: "Моя цель изучения английского языка — стать высококвалифицированным преподавателем-методистом с международным опытом.",
    en: "My goal in learning English is to become a proficient, internationally experienced teacher and methodologist."
  },
  sq_12: {
    ru: "Для меня важно не просто получить высокую оценку на экзамене, а глубоко чувствовать язык и его тонкости.",
    en: "For me, deeply understanding the language matters more than simply getting a high exam score."
  }
};

function renderSurveyQuestions(container) {
  if (!container) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  if (!SURVEY_QUESTIONS.length) {
    const emptyMsg = lang === "ru" ? "Для этого предмета нет специальных анкетных вопросов." : (lang === "en" ? "No specific survey questions for this course." : "Ushbu fan uchun maxsus anketa savollari mavjud emas.");
    container.innerHTML = `<div style="text-align:center;padding:24px 20px;color:var(--muted);background:var(--surface-2);border-radius:10px;border:1px dashed var(--line)">
      ${emptyMsg}
    </div>`;
    return;
  }

  const surveyWord = lang === "ru" ? "Анкета" : (lang === "en" ? "Survey" : "Anketa");
  const likertLabels = lang === "ru"
    ? ["Полностью не согласен", "Скорее не согласен", "Нейтрально", "Согласен", "Полностью согласен"]
    : (lang === "en"
      ? ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
      : ["Mutlaqo qo'shilmayman", "Qisman qo'shilmayman", "Neytral", "Qo'shilaman", "To'liq qo'shilaman"]);

  container.innerHTML = SURVEY_QUESTIONS.map((sq, sIdx) => {
    const currentRating = STATE.surveyAnswers[sq.id];
    let promptText = sq.prompt_uz || sq.prompt || "";
    if (lang === "ru") {
      promptText = sq.prompt_ru || (SURVEY_TRANSLATIONS[sq.id] && SURVEY_TRANSLATIONS[sq.id].ru) || promptText;
    } else if (lang === "en") {
      promptText = sq.prompt_en || (SURVEY_TRANSLATIONS[sq.id] && SURVEY_TRANSLATIONS[sq.id].en) || promptText;
    }

    return `
      <div style="background:var(--surface-2);padding:14px 16px;border-radius:10px;border:1px solid var(--line);transition:border 0.3s" id="survey_box_${sq.id}">
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px">${surveyWord} ${sIdx + 1} / ${SURVEY_QUESTIONS.length}</div>
        <p style="font-size:14px;color:var(--ink);margin-bottom:12px;line-height:1.5">
          <b>"${escapeHtml(promptText)}"</b>
        </p>
        <div class="scale-group" style="display:flex;gap:8px;flex-wrap:wrap">
          ${[1, 2, 3, 4, 5].map(val => {
            return `
              <button type="button" class="scale-btn ${currentRating === val ? "active" : ""}" style="width:auto;padding:6px 12px;font-size:12px" onclick="window.setSurveyAnswer('${sq.id}', ${val}, this)">
                ${likertLabels[val-1]} (${val})
              </button>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }).join("");
}

window.setSurveyAnswer = function(sqid, rating, btn) {
  STATE.surveyAnswers[sqid] = rating;
  const parent = btn.parentElement;
  if (parent) {
    parent.querySelectorAll(".scale-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
  }
};

async function submitDiagnosticForm() {
  if (typeof window.stopListeningAudio === "function") {
    window.stopListeningAudio();
  }

  // 1. Diagnostika test savollari to'liq belgilanganligini tekshirish
  const totalDiag = DIAG_QUESTIONS.length;
  const answeredDiag = DIAG_QUESTIONS.filter(q => STATE.diagAnswers[q.id] !== undefined);
  if (answeredDiag.length < totalDiag) {
    const missingQ = DIAG_QUESTIONS.find(q => STATE.diagAnswers[q.id] === undefined);
    showToast(`Diagnostika testining barcha savollarini belgilang! (${answeredDiag.length} / ${totalDiag} ta belgilandi)`, "warning");
    if (missingQ) {
      const box = document.getElementById(`diag_box_${missingQ.id}`);
      if (box) {
        box.scrollIntoView({ behavior: "smooth", block: "center" });
        box.style.border = "2px solid var(--clay)";
        setTimeout(() => { box.style.border = "1px solid var(--line)"; }, 2500);
      }
    }
    return;
  }

  // 2. Anketa savollari to'liq baholanganligini tekshirish
  const totalSurvey = SURVEY_QUESTIONS.length;
  const answeredSurvey = SURVEY_QUESTIONS.filter(sq => STATE.surveyAnswers[sq.id] !== undefined);
  if (answeredSurvey.length < totalSurvey) {
    const missingSq = SURVEY_QUESTIONS.find(sq => STATE.surveyAnswers[sq.id] === undefined);
    showToast(`Iltimos, psixologik-akademik anketaning barcha savollarini baholang! (${answeredSurvey.length} / ${totalSurvey} ta baholandi)`, "warning");
    if (missingSq) {
      const box = document.getElementById(`survey_box_${missingSq.id}`);
      if (box) {
        box.scrollIntoView({ behavior: "smooth", block: "center" });
        box.style.border = "2px solid var(--clay)";
        setTimeout(() => { box.style.border = "1px solid var(--line)"; }, 2500);
      }
    }
    return;
  }

  const submitBtn = document.getElementById("btnSubmitDiagnostic");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>⏳</span> <span>Natijalar tahlil qilinmoqda va saqlanmoqda...</span>`;
  }

  try {
    // 1. Diagnostika javoblarini tayyorlash
    const diagAnswersArray = Object.keys(STATE.diagAnswers).map(qid => ({
      question_id: qid,
      selected_option_index: STATE.diagAnswers[qid]
    }));

    // 2. Anketa javoblarini tayyorlash
    const surveyAnswersArray = Object.keys(STATE.surveyAnswers).map(sqid => ({
      question_id: sqid,
      rating: STATE.surveyAnswers[sqid]
    }));

    const payload = {
      diagnostic_answers: diagAnswersArray,
      survey_answers: surveyAnswersArray,
      subject_id: STATE.diagSubjectId || null
    };

    const headers = { "Content-Type": "application/json" };
    if (STATE.token) {
      headers["Authorization"] = `Bearer ${STATE.token}`;
    }

    const res = await fetch(`${STATE.apiBaseUrl}/student/diagnostic/submit`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Diagnostika natijalarini yuborishda xatolik yuz berdi");
    }

    // Natijalarni modalda ko'rsatish
    const modal = document.getElementById("diagResultModal");

    // 1. Umumiy CEFR va to'g'ri javoblar soni
    const overallBadge = document.getElementById("resOverallCefrBadge");
    if (overallBadge) {
      overallBadge.textContent = `🎯 Umumiy CEFR: ${data.overall_cefr || "B1"}`;
    }

    const countBadge = document.getElementById("resCorrectCountBadge");
    if (countBadge) {
      countBadge.textContent = `✅ Test natijasi: ${data.correct_count !== undefined ? data.correct_count : 0} / ${data.total_questions || 8}`;
    }

    // 2. 4 ta ko'nikma
    if (data.cefr_levels) {
      const l = document.getElementById("resListening");
      const r = document.getElementById("resReading");
      const w = document.getElementById("resWriting");
      const s = document.getElementById("resSpeaking");
      if (l) l.textContent = data.cefr_levels.listening || "B1";
      if (r) r.textContent = data.cefr_levels.reading || "B2";
      if (w) w.textContent = data.cefr_levels.writing || "B1";
      if (s) s.textContent = data.cefr_levels.speaking || "A2";
    }

    // 3. FLCAS va Kognitiv profil
    if (data.cognitive_affective) {
      const ca = data.cognitive_affective;
      const anxEl = document.getElementById("resAnxiety");
      const loadEl = document.getElementById("resLoad");
      const paceEl = document.getElementById("resPace");
      const autoEl = document.getElementById("resAutonomy");

      const anx = ca.anxiety_level || 71;
      const anxStatus = anx > 65 ? "Yuqori (65%+)" : (anx >= 40 ? "O'rtacha" : "Past");
      if (anxEl) anxEl.textContent = `${anx}/100 (${anxStatus})`;
      if (loadEl) loadEl.textContent = `${ca.load_capacity || 50}/100`;
      if (paceEl) paceEl.textContent = `${ca.pace_index || 60}/100`;
      if (autoEl) autoEl.textContent = `${ca.autonomy_readiness || 42}/100`;
    }

    // 3b. Metakognitiv komponentlar (1–5, MSLQ) va o'lchov turi (pre/post)
    const metaBox = document.getElementById("resMetaBox");
    if (metaBox) {
      const m = data.metacognitive;
      const keys = ["planning", "monitoring", "evaluation", "regulation"];
      const has = m && keys.some(k => m[k] !== null && m[k] !== undefined);
      if (has) {
        const f = (v) => (v === null || v === undefined) ? "—" : String(v);
        metaBox.style.display = "block";
        metaBox.innerHTML = `🧠 <b>Metakognitiv komponentlar (1–5):</b> Rejalashtirish ${escapeHtml(f(m.planning))} · Monitoring ${escapeHtml(f(m.monitoring))} · Baholash ${escapeHtml(f(m.evaluation))} · O'zini boshqarish ${escapeHtml(f(m.regulation))}`;
      } else {
        metaBox.style.display = "none";
      }
    }
    const atChip = document.getElementById("resAssessTypeChip");
    if (atChip) {
      if (data.assessment_type) {
        const at = String(data.assessment_type);
        atChip.style.display = "inline-block";
        atChip.textContent = `📏 O'lchov: ${at === "pre" ? "pre (kirish)" : (at === "post" ? "post (yakuniy)" : at)}`;
      } else {
        atChip.style.display = "none";
      }
    }

    // 4. Pedagogik va FLCAS tavsiyasi
    const adviceEl = document.getElementById("resAdviceText");
    if (adviceEl && data.pedagogic_advice) {
      const pa = data.pedagogic_advice;
      adviceEl.innerHTML = `
        <div style="margin-bottom:6px"><b>${escapeHtml(pa.flcas_status || '')}:</b> ${escapeHtml(pa.flcas_advice || '')}</div>
        <div style="font-size:12px;color:var(--teal);font-weight:600">🎯 ${escapeHtml(pa.adaptive_strategy || '')}</div>
      `;
    }

    // 5. Savollar tahlili va to'g'ri variantlar (Rationale)
    const revContainer = document.getElementById("diagReviewListContainer");
    if (revContainer && data.question_reviews && data.question_reviews.length) {
      revContainer.innerHTML = data.question_reviews.map((r, i) => `
        <div style="background:var(--surface-2);border:1px solid ${r.is_correct ? 'var(--teal)' : 'var(--clay)'};border-radius:8px;padding:12px;margin-bottom:8px;text-align:left">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-weight:700;font-size:12.5px">${i + 1}-savol · ${getSkillBadge(r.skill).label} (${escapeHtml(r.cefr_level)})</span>
            <span style="font-size:12px;font-weight:700;color:${r.is_correct ? 'var(--teal)' : 'var(--clay)'}">${r.is_correct ? '✅ To\'g\'ri' : '❌ Noto\'g\'ri'}</span>
          </div>
          <div style="font-size:13px;color:var(--ink);margin-bottom:6px;font-weight:600">${escapeHtml(r.question)}</div>
          <div style="font-size:12px;color:var(--ink-2);margin-bottom:4px">
            Sizning javobingiz: <b style="color:${r.is_correct ? 'var(--teal)' : 'var(--clay)'}">${escapeHtml(r.selected_option_text || 'Belgilanmagan')}</b>
          </div>
          ${!r.is_correct ? `<div style="font-size:12px;color:var(--teal);margin-bottom:4px">To'g'ri javob: <b>${escapeHtml(r.correct_option_text)}</b></div>` : ''}
          <div style="font-size:12px;color:var(--muted);border-top:1px dashed var(--line);padding-top:4px;margin-top:4px;line-height:1.5">
            💡 <b>Metodik izoh (Rationale):</b> ${escapeHtml(r.rationale)}
          </div>
        </div>
      `).join("");
    }

    // Profilni qayta yangilash
    await loadUserProfile();

    if (modal) modal.style.display = "flex";

  } catch (err) {
    alert("Xatolik: " + (err.message || "Diagnostikani yuborib bo'lmadi"));
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>📤</span> <span>Diagnostika va anketa natijalarini yuborish (Profilni yangilash) →</span>`;
    }
  }
}

window.toggleDiagReviews = function() {
  const box = document.getElementById("diagReviewListContainer");
  const btn = document.getElementById("btnToggleDiagReviews");
  if (!box) return;
  const isHidden = (box.style.display === "none" || !box.style.display);
  box.style.display = isHidden ? "block" : "none";
  if (btn) {
    btn.innerHTML = isHidden 
      ? "🔼 Tahlilni yashirish ▴"
      : "🔍 Savollar tahlili va to'g'ri variantlar (Rationale) ▾";
  }
};

// =========================================================================
// O'QITUVCHI: FANLAR, SILLABUS VA AI MATERIAL GENERATORI
// =========================================================================

STATE.teacherSubjects = [];
STATE.teacherMaterials = [];
STATE.currentPresentation = null;
STATE.currentSlideIndex = 0;
STATE.currentTest = null;
STATE.showAnswerKeys = true;

// Tab almashtirish
window.switchSubjectTab = function(tabName) {
  const tabSubjects = document.getElementById("subTabSubjectsContent");
  const tabGen = document.getElementById("subTabGeneratorContent");
  const tabMat = document.getElementById("subTabMaterialsContent");

  const btnSub = document.getElementById("tabBtnSubjects");
  const btnGen = document.getElementById("tabBtnGenerator");
  const btnMat = document.getElementById("tabBtnMaterials");

  if (!tabSubjects || !tabGen || !tabMat) return;

  tabSubjects.style.display = tabName === "subjects" ? "block" : "none";
  tabGen.style.display = tabName === "generator" ? "block" : "none";
  tabMat.style.display = tabName === "materials" ? "block" : "none";

  [btnSub, btnGen, btnMat].forEach(b => {
    if (b) {
      b.style.background = "none";
      b.style.color = "var(--ink)";
      b.style.border = "1px solid var(--line)";
    }
  });

  if (tabName === "subjects" && btnSub) {
    btnSub.style.background = "var(--teal)";
    btnSub.style.color = "#fff";
    btnSub.style.border = "none";
    window.loadTeacherSubjects();
  } else if (tabName === "generator" && btnGen) {
    btnGen.style.background = "var(--teal)";
    btnGen.style.color = "#fff";
    btnGen.style.border = "none";
  } else if (tabName === "materials" && btnMat) {
    btnMat.style.background = "var(--teal)";
    btnMat.style.color = "#fff";
    btnMat.style.border = "none";
    window.loadTeacherMaterials();
  }
};

// Material Statistikalarini Yuklash (Limitlar va Foydalanish)
window.loadTeacherMaterialStats = async function() {
  if (!STATE.token) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/materials/stats`, {
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (!res.ok) return;

    const data = await res.json();
    STATE.teacherMaterialStats = data;

    // Stats kartasini ko'rsatish
    const statsCard = document.getElementById("materialStatsCard");
    if (statsCard) statsCard.style.display = "block";

    // Tier badge
    const tierBadge = document.getElementById("materialTierBadge");
    const isPro = data.is_pro;
    if (tierBadge) {
      if (isPro) {
        tierBadge.textContent = "👑 PRO (Cheksiz)";
        tierBadge.style.background = "var(--amber-soft)";
        tierBadge.style.color = "var(--amber)";
        tierBadge.style.border = "1px solid rgba(138,106,23,0.3)";
      } else {
        tierBadge.textContent = "FREE (Cheklovli)";
        tierBadge.style.background = "var(--surface-2)";
        tierBadge.style.color = "var(--ink)";
        tierBadge.style.border = "1px solid var(--line)";
      }
    }

    // Free tarif: test + slayd uchun UMUMIY oylik limit (3 ta/oy). PRO: cheksiz, umumiy sonlar ko'rsatiladi.
    const monthly = data.monthly || {};
    const monthLimit = monthly.limit || data.limits?.test || 3;
    const monthUsed = monthly.ai_total || 0;
    const monthRemaining = (monthly.remaining !== undefined) ? monthly.remaining : Math.max(0, monthLimit - monthUsed);
    const monthPercent = Math.min(100, Math.round((monthUsed / monthLimit) * 100));
    const limitsSub = document.getElementById("materialLimitsSub");
    if (limitsSub) {
      limitsSub.textContent = isPro
        ? "PRO tarif: barcha materiallar cheksiz"
        : `Tekin tarif: oyiga ${monthLimit} ta AI material (test + slayd birgalikda). Bu oy ishlatildi: ${monthUsed}/${monthLimit}`;
    }

    // Testlar
    const testCount = isPro ? (data.counts?.test || 0) : (monthly.test || 0);
    const testLimit = isPro ? null : monthLimit;
    const testRemaining = monthRemaining;
    const testPercent = isPro ? 0 : monthPercent;

    const testCountBadge = document.getElementById("testCountBadge");
    const testProgressBar = document.getElementById("testProgressBar");
    const testLimitText = document.getElementById("testLimitText");

    if (testCountBadge) {
      testCountBadge.textContent = `${testCount}/${testLimit === null ? '∞' : testLimit}`;
      if (isPro) {
        testCountBadge.style.background = "var(--teal-soft)";
        testCountBadge.style.color = "var(--teal)";
      } else if (monthUsed >= testLimit) {
        testCountBadge.style.background = "rgba(217,119,87,0.15)";
        testCountBadge.style.color = "var(--clay)";
      }
    }
    if (testProgressBar) testProgressBar.style.width = `${testPercent}%`;
    if (testLimitText) {
      if (isPro) {
        testLimitText.textContent = "Cheksiz (PRO)";
        testLimitText.style.color = "var(--teal)";
      } else if (monthUsed >= testLimit) {
        testLimitText.textContent = "Oylik limit tugagan! Keyingi oy yangilanadi";
        testLimitText.style.color = "var(--clay)";
      } else {
        testLimitText.textContent = `Bu oy qolgan (test + slayd): ${testRemaining}`;
        testLimitText.style.color = "var(--muted)";
      }
    }

    // Prezentatsiyalar (free tarifda testlar bilan umumiy oylik limit)
    const presCount = isPro ? (data.counts?.presentation || 0) : (monthly.presentation || 0);
    const presLimit = isPro ? null : monthLimit;
    const presRemaining = monthRemaining;
    const presPercent = isPro ? 0 : monthPercent;

    const presCountBadge = document.getElementById("presCountBadge");
    const presProgressBar = document.getElementById("presProgressBar");
    const presLimitText = document.getElementById("presLimitText");

    if (presCountBadge) {
      presCountBadge.textContent = `${presCount}/${presLimit === null ? '∞' : presLimit}`;
      if (isPro) {
        presCountBadge.style.background = "var(--amber-soft)";
        presCountBadge.style.color = "var(--amber)";
      } else if (monthUsed >= presLimit) {
        presCountBadge.style.background = "rgba(217,119,87,0.15)";
        presCountBadge.style.color = "var(--clay)";
      }
    }
    if (presProgressBar) presProgressBar.style.width = `${presPercent}%`;
    if (presLimitText) {
      if (isPro) {
        presLimitText.textContent = "Cheksiz (PRO)";
        presLimitText.style.color = "var(--amber)";
      } else if (monthUsed >= presLimit) {
        presLimitText.textContent = "Oylik limit tugagan! Keyingi oy yangilanadi";
        presLimitText.style.color = "var(--clay)";
      } else {
        presLimitText.textContent = `Bu oy qolgan (test + slayd): ${presRemaining}`;
        presLimitText.style.color = "var(--muted)";
      }
    }

    // Dars rejalari
    const planCount = data.counts?.lesson_plan || 0;
    const planCountBadge = document.getElementById("planCountBadge");
    const planProgressBar = document.getElementById("planProgressBar");
    const planLimitText = document.getElementById("planLimitText");

    if (planCountBadge) planCountBadge.textContent = `${planCount}/∞`;
    if (planProgressBar) planProgressBar.style.width = "0%";
    if (planLimitText) {
      planLimitText.textContent = "Cheksiz";
      planLimitText.style.color = "var(--muted)";
    }

  } catch (err) {
    console.error("Material stats yuklashda xatolik:", err);
  }
};

// Fanlar ro'yxatini yuklash
window.loadTeacherSubjects = async function() {
  const container = document.getElementById("subjectsListContainer");
  const badge = document.getElementById("countSubjectsBadge");
  const selectSubj = document.getElementById("genSelectSubject");

  if (!STATE.token) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects`, {
      headers: {
        "Authorization": `Bearer ${STATE.token}`
      }
    });

    if (!res.ok) {
      if (container) container.innerHTML = `<div style="text-align:center;color:var(--muted);padding:20px">Fanlarni yuklashda xatolik yuz berdi.</div>`;
      return;
    }

    const data = await res.json();
    STATE.teacherSubjects = data.subjects || [];

    if (badge) badge.textContent = STATE.teacherSubjects.length;

    // Material stats yuklash
    await window.loadTeacherMaterialStats();

    // Generator select dropdownni yangilash
    if (selectSubj) {
      const curVal = selectSubj.value;
      // Admin uchun boshqa o'qituvchining fani bo'lsa, egasi ham ko'rsatiladi
      selectSubj.innerHTML = `<option value="">-- Fanni tanlang --</option>` +
        STATE.teacherSubjects.map(s => `<option value="${escapeHtml(s.id)}" ${curVal === s.id ? 'selected' : ''}>${escapeHtml(s.name)} (${escapeHtml(s.group_name)})${s.is_own === false && s.teacher_name ? ` · ${escapeHtml(s.teacher_name)}` : ""}</option>`).join("");
      if (curVal) window.onGenSubjectChange();
      window.renderGenExtraSubjects();
    }

    if (!container) return;

    if (STATE.teacherSubjects.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align:center;padding:40px 20px">
          <div style="font-size:36px;margin-bottom:8px">📚</div>
          <h3 style="margin:0 0 6px">Hozircha fanlar biriktirilmagan</h3>
          <p style="font-size:13.5px;color:var(--muted);margin:0 0 16px">Yangi fan qo'shing yoki namunaviy fanlar ro'yxatidan foydalaning.</p>
          <button class="btn-primary" onclick="window.openAddSubjectModal()">➕ Yangi fan qo'shish</button>
        </div>
      `;
      return;
    }

    container.innerHTML = STATE.teacherSubjects.map(s => `
      <div class="card" style="padding:20px;border-left:4px solid var(--teal)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
          <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <span style="font-size:11px;font-weight:700;padding:2px 7px;background:var(--teal-soft);color:var(--teal);border-radius:4px">${escapeHtml(s.code || 'FAN')}</span>
              <span style="font-size:12px;color:var(--muted)">${escapeHtml(s.course_year)}-kurs · ${escapeHtml(s.group_name)} · ${escapeHtml(s.semester)}</span>
              ${s.is_own === false && s.teacher_name ? `<span style="font-size:11px;font-weight:700;padding:2px 7px;background:var(--amber-soft);color:var(--amber);border-radius:4px">👤 ${escapeHtml(s.teacher_name)}</span>` : ""}
            </div>
            <h3 style="margin:0 0 6px;font-size:18px;font-family:var(--serif)">${escapeHtml(s.name)}</h3>
            <p style="margin:0 0 10px;font-size:13px;color:var(--ink-2)">${escapeHtml(s.description || "Ushbu fan bo'yicha sillabus va dars materiallari.")}</p>
            
            <div style="display:flex;gap:12px;font-size:12.5px;color:var(--muted);flex-wrap:wrap">
              <span>📋 <b>${s.topics_count} ta</b> mavzu</span>
              <span>⚡ <b>${s.materials_count} ta</b> AI material tayyorlangan</span>
              <span>📅 Kiritilgan: ${s.created_at || 'Yaqinda'}</span>
            </div>
          </div>

          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn-primary" style="padding:7px 13px;font-size:12.5px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="window.toggleSubjectTopics('${s.id}')">
              📑 Mavzular (${s.topics_count})
            </button>
            <button class="btn-primary" style="padding:7px 13px;font-size:12.5px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="window.openUploadSyllabusModal('${s.id}', ${jsArg(s.name)})">
              📄 Sillabus yuklash
            </button>
            <button class="btn-primary" style="padding:7px 13px;font-size:12.5px" onclick="window.prepareGenerateForTopic('${s.id}', '', 'test')">
              ✨ AI Tayyorlash
            </button>
            <button class="btn-primary" style="padding:7px 13px;font-size:12.5px;background:var(--amber);border-color:var(--amber)" onclick="window.openUploadMaterialModal('${s.id}')" title="Tayyor test yoki slayd faylini yuklash (.docx, .pdf, .pptx, .txt)">
              ⬆️ Test/Slayd yuklash
            </button>
            ${s.is_own === false ? "" : `<button class="btn-primary" style="padding:7px 10px;font-size:12px;background:none;color:var(--clay);border:1px solid var(--line)" onclick="window.deleteTeacherSubject('${s.id}')" title="Fanni o'chirish">
              🗑️
            </button>`}
          </div>
        </div>

        <!-- Mavzular ro'yxati (yashirin konteyner) -->
        <div id="topicsContainer_${s.id}" style="display:none;margin-top:16px;border-top:1px solid var(--line);padding-top:14px">
          <div style="text-align:center;padding:10px;color:var(--muted)">Mavzular yuklanmoqda...</div>
        </div>
      </div>
    `).join("");

  } catch (e) {
    console.error("loadTeacherSubjects xatosi:", e);
  }
};

// Fanga tegishli mavzularni ochish / yopish
window.toggleSubjectTopics = async function(subjectId) {
  const container = document.getElementById(`topicsContainer_${subjectId}`);
  if (!container) return;

  if (container.style.display === "block") {
    container.style.display = "none";
    return;
  }

  container.style.display = "block";
  container.innerHTML = `<div style="text-align:center;padding:12px;color:var(--muted);font-size:13px">Sillabus mavzulari o'qilmoqda...</div>`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjectId}/topics`, {
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (!res.ok) {
      container.innerHTML = `<div style="color:var(--clay);font-size:13px;padding:8px">Mavzularni yuklab bo'lmadi.</div>`;
      return;
    }
    const data = await res.json();
    const topics = data.topics || [];

    if (topics.length === 0) {
      container.innerHTML = `
        <div style="padding:14px;background:var(--surface-2);border-radius:8px;font-size:13px;text-align:center">
          Ushbu fanga hali sillabus kiritilmagan.
          <button class="btn-primary" style="margin-left:10px;padding:4px 10px;font-size:12px" onclick="window.openUploadSyllabusModal('${subjectId}', ${jsArg(data.subject_name)})">
            Sillabus yuklash
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="font-weight:700;font-size:13px;margin-bottom:10px;color:var(--teal)">
        📋 16 Haftalik O'quv Rejasi va Dars Mavzulari:
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        ${topics.map(t => `
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 12px;background:var(--surface-2);border-radius:8px;border:1px solid var(--line);font-size:13px">
            <div style="display:flex;align-items:center;gap:10px">
              <span style="font-weight:700;color:var(--teal);min-width:55px">${escapeHtml(t.week_number)}-hafta:</span>
              <span style="font-weight:600;color:var(--ink)">${escapeHtml(t.title)}</span>
            </div>
            <div style="display:flex;gap:6px">
              <button class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--card);color:var(--ink);border:1px solid var(--line)" onclick="window.prepareGenerateForTopic('${subjectId}', ${jsArg(t.title)}, 'test')" title="Ushbu mavzu bo'yicha AI test tuzish">
                📝 Test
              </button>
              <button class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--teal);color:#fff" onclick="window.prepareGenerateForTopic('${subjectId}', ${jsArg(t.title)}, 'presentation')" title="Ushbu mavzu bo'yicha AI slaydlar tayyorlash">
                📊 Slayd
              </button>
              <button class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--surface);color:var(--ink);border:1px solid var(--line)" onclick="window.prepareGenerateForTopic('${subjectId}', ${jsArg(t.title)}, 'lesson_plan')" title="5 bosqichli dars ssenariysi">
                📋 Dars rejasi
              </button>
            </div>
          </div>
        `).join("")}
      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div style="color:var(--clay);font-size:13px">Xatolik: ${escapeHtml(err.message)}</div>`;
  }
};

// Yangi fan qo'shish modali
window.openAddSubjectModal = function() {
  const modal = document.getElementById("addSubjectModal");
  if (modal) modal.style.display = "flex";
  const fileInput = document.getElementById("newSubjDocxFile");
  if (fileInput) fileInput.value = "";
};

window.closeAddSubjectModal = function() {
  const modal = document.getElementById("addSubjectModal");
  if (modal) modal.style.display = "none";
};

// Yangi fan yaratishda .docx / .txt o'quv dasturidan avtomatik to'ldirish
window.handleNewSubjectDocxUpload = async function(e) {
  const file = e.target.files ? e.target.files[0] : null;
  if (!file) return;

  showToast(`⏳ "${file.name}" tahlil qilinmoqda...`, "info");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/parse-syllabus-file`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${STATE.token}`
      },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Faylni tahlil qilishda xatolik yuz berdi");
    }

    const data = await res.json();

    // Form elementlarini avtomatik to'ldirish
    if (data.subject_name) {
      const nameEl = document.getElementById("newSubjName");
      if (nameEl) nameEl.value = data.subject_name;
    }
    if (data.subject_code) {
      const codeEl = document.getElementById("newSubjCode");
      if (codeEl) codeEl.value = data.subject_code;
    }
    if (data.semester) {
      const semEl = document.getElementById("newSubjSemester");
      if (semEl) semEl.value = data.semester;
    }
    if (data.description) {
      const descEl = document.getElementById("newSubjDesc");
      if (descEl) descEl.value = data.description;
    }

    // Mavzularni sillabusga yozish
    const syllabusEl = document.getElementById("newSubjSyllabus");
    if (syllabusEl && data.formatted_text) {
      syllabusEl.value = data.formatted_text;
    }

    showToast(`✅ "${file.name}" tahlil qilindi: ${data.lecture_count} ta ma'ruza, ${data.seminar_count} ta seminar ajratildi!`, "success");

  } catch (err) {
    showToast(`Xatolik: ${err.message}`, "error");
  }
};

window.fillSampleSyllabus = function() {
  const ta = document.getElementById("newSubjSyllabus");
  if (!ta) return;
  ta.value = [
    "1. Introduction to Pedagogical Discourse & Classroom Interaction",
    "2. Teacher Talk Time (TTT) vs. Student Talk Time (STT) Balance",
    "3. Giving Clear Instructions & Checking Understanding (ICQs)",
    "4. Constructive Error Correction & Oral Feedback Techniques",
    "5. Scaffolding Strategies for Mixed-Ability Language Learners",
    "6. Questioning Techniques: Display vs. Referential Questions",
    "7. Managing Affective Filter & FL Anxiety in Speaking Tasks",
    "8. Midterm Formative Assessment: Peer Observation & Teaching Analysis",
    "9. Facilitating Group Work & Cooperative Learning in EFL",
    "10. Non-Verbal Communication & Body Language in the Classroom",
    "11. Elicitation Techniques vs. Direct Explanations",
    "12. Teaching Pronunciation & Suprasegmental Features Contextually",
    "13. Metacognitive Prompting & Student Reflection Strategies",
    "14. Handling Classroom Disruptions with Constructive Language",
    "15. Designing Communicative Tasks without Premature AI Reliance",
    "16. Final Teaching Portfolio Defense & Pedagogical Synthesis"
  ].join("\n");
};

window.submitNewSubject = async function(e) {
  if (e) e.preventDefault();
  const name = document.getElementById("newSubjName").value.trim();
  const code = document.getElementById("newSubjCode").value.trim();
  const group = document.getElementById("newSubjGroup").value.trim();
  const course = parseInt(document.getElementById("newSubjCourse").value) || 3;
  const semester = document.getElementById("newSubjSemester").value.trim();
  const desc = document.getElementById("newSubjDesc").value.trim();
  const syllabus = document.getElementById("newSubjSyllabus").value.trim();

  if (!name) {
    showToast("Fan nomini kiriting!", "error");
    return;
  }

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({
        name,
        code,
        group_name: group,
        course_year: course,
        semester,
        description: desc,
        syllabus_text: syllabus
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Fanni saqlab bo'lmadi");
    }

    showToast(`✅ '${name}' fani profilingizga muvaffaqiyatli saqlandi!`, "success");
    window.closeAddSubjectModal();
    window.loadTeacherSubjects();

  } catch (err) {
    showToast(`Xatolik: ${err.message}`, "error");
  }
};

window.deleteTeacherSubject = async function(subjectId) {
  if (!confirm("Haqiqatan ham ushbu fanni va uning barcha materiallarini o'chirmoqchimisiz?")) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjectId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (!res.ok) throw new Error("Fanni o'chirishda xatolik.");

    showToast("Fan muvaffaqiyatli o'chirildi.", "success");
    window.loadTeacherSubjects();
    window.loadTeacherMaterials();
  } catch (e) {
    showToast(e.message, "error");
  }
};

// Sillabus yuklash modali
window.openUploadSyllabusModal = function(subjectId, subjectName) {
  document.getElementById("uploadModalSubjectId").value = subjectId;
  const titleEl = document.getElementById("uploadModalSubjectTitle");
  if (titleEl) titleEl.textContent = `${subjectName} — Sillabus yuklash`;
  const ta = document.getElementById("uploadSyllabusText");
  if (ta) ta.value = "";
  const fileInput = document.getElementById("fileSyllabusInput");
  if (fileInput) fileInput.value = "";
  const noticeEl = document.getElementById("fileUploadStatusNotice");
  if (noticeEl) noticeEl.textContent = "Word (.docx) faylini tanlang, dastur mavzularni avtomatik ajratib beradi";
  const catSel = document.getElementById("syllabusCategorySelect");
  if (catSel) catSel.value = "lecture";
  STATE.parsedSyllabusData = null;

  const modal = document.getElementById("uploadSyllabusModal");
  if (modal) modal.style.display = "flex";
};

window.closeUploadSyllabusModal = function() {
  const modal = document.getElementById("uploadSyllabusModal");
  if (modal) modal.style.display = "none";
  STATE.parsedSyllabusData = null;
};

// ==================== TAYYOR TEST / SLAYD FAYLINI YUKLASH (O'QITUVCHI / ADMIN) ====================
// O'qituvchi o'z faylini (.docx/.pdf/.txt — test; .pptx/.pdf/.docx — slayd) fanga yuklaydi.
// Backend (POST /teacher/subjects/{id}/upload-material) faylni tahlil qilib interaktiv test/slayd yasaydi,
// asl fayl /uploads/materials/ da saqlanadi — talaba uni "Mustaqil topshiriqlar"da ishlaydi yoki yuklab oladi.
window.openUploadMaterialModal = async function(subjectId, materialType) {
  const modal = document.getElementById("uploadMaterialModal");
  if (!modal) return;
  if (!window.canCreateMaterials || !window.canCreateMaterials()) {
    showToast("Fayl yuklash faqat o'qituvchi yoki admin uchun.", "error");
    return;
  }
  // Fanlar ro'yxati (kerak bo'lsa yuklanadi)
  if (!(STATE.teacherSubjects || []).length && typeof window.loadTeacherSubjects === "function") {
    await window.loadTeacherSubjects();
  }
  const subjSel = document.getElementById("umSubjectSelect");
  if (subjSel) {
    subjSel.innerHTML = `<option value="">-- Fanni tanlang --</option>` +
      (STATE.teacherSubjects || []).map(s => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.name)} (${escapeHtml(s.group_name || "")})${s.is_own === false && s.teacher_name ? ` · ${escapeHtml(s.teacher_name)}` : ""}</option>`).join("");
    subjSel.value = subjectId || "";
    if (subjectId && subjSel.value !== subjectId) {
      // Talaba ro'yxatidan kelgan fan (STATE.studentSubjects) bo'lsa, uni ham qo'shamiz
      const st = (STATE.studentSubjects || []).find(s => String(s.id) === String(subjectId));
      if (st) {
        const opt = document.createElement("option");
        opt.value = st.id; opt.text = `${st.title || st.name} (${st.group_name || ""})`; opt.selected = true;
        subjSel.appendChild(opt);
      }
    }
  }
  const radio = document.querySelector(`input[name="umMaterialType"][value="${materialType === "presentation" ? "presentation" : "test"}"]`);
  if (radio) radio.checked = true;
  const fileInput = document.getElementById("umFileInput");
  if (fileInput) fileInput.value = "";
  const notice = document.getElementById("umFileNotice");
  if (notice) { notice.textContent = "Fayl hali tanlanmagan"; notice.style.color = "var(--muted)"; }
  const titleInp = document.getElementById("umTitle");
  if (titleInp) titleInp.value = "";
  const fileOnly = document.getElementById("umFileOnly");
  if (fileOnly) fileOnly.checked = false;
  const result = document.getElementById("umResult");
  if (result) { result.style.display = "none"; result.innerHTML = ""; }
  const btn = document.getElementById("btnUploadMaterial");
  if (btn) { btn.disabled = false; btn.innerHTML = "⬆️ Yuklash va saqlash"; }

  window.onUploadMaterialTypeChange();
  await window.onUploadMaterialSubjectChange();
  modal.style.display = "flex";
};

window.closeUploadMaterialModal = function() {
  const modal = document.getElementById("uploadMaterialModal");
  if (modal) modal.style.display = "none";
};

// Fan o'zgarganda sillabus mavzularini yuklash
window.onUploadMaterialSubjectChange = async function() {
  const subjSel = document.getElementById("umSubjectSelect");
  const topicSel = document.getElementById("umTopicSelect");
  if (!subjSel || !topicSel) return;
  topicSel.innerHTML = `<option value="">Umumiy dars mavzusi</option>`;
  if (!subjSel.value) return;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjSel.value}/topics`, { headers: { "Authorization": `Bearer ${STATE.token}` } });
    if (!res.ok) return;
    const data = await res.json();
    (data.topics || []).forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.title; opt.dataset.id = t.id || ""; opt.text = t.title;
      topicSel.appendChild(opt);
    });
  } catch (_) { /* mavzular bo'lmasa umumiy mavzu qoladi */ }
};

// Test / slayd turi o'zgarganda qabul qilinadigan fayl kengaytmalari va ko'rsatma
window.onUploadMaterialTypeChange = function() {
  const t = document.querySelector('input[name="umMaterialType"]:checked');
  const isTest = !t || t.value === "test";
  const input = document.getElementById("umFileInput");
  const label = document.getElementById("umFileLabel");
  const hint = document.getElementById("umTestHint");
  if (input) input.accept = isTest ? ".docx,.pdf,.txt" : ".pptx,.pdf,.docx,.txt";
  if (label) label.textContent = isTest ? "Test faylini tanlang (.docx, .pdf, .txt)" : "Slayd faylini tanlang (.pptx, .pdf, .docx, .txt)";
  if (hint) hint.style.display = isTest ? "block" : "none";
};

window.onUploadMaterialFileChange = function(e) {
  const file = e.target.files ? e.target.files[0] : null;
  const notice = document.getElementById("umFileNotice");
  if (!notice) return;
  if (file) {
    notice.innerHTML = `✅ <strong>${escapeHtml(file.name)}</strong> (${(file.size / 1024).toFixed(0)} KB)`;
    notice.style.color = "var(--teal)";
  } else {
    notice.textContent = "Fayl hali tanlanmagan";
    notice.style.color = "var(--muted)";
  }
};

window.submitUploadMaterial = async function() {
  const subjSel = document.getElementById("umSubjectSelect");
  const topicSel = document.getElementById("umTopicSelect");
  const fileInput = document.getElementById("umFileInput");
  const t = document.querySelector('input[name="umMaterialType"]:checked');
  const matType = t ? t.value : "test";
  const file = fileInput && fileInput.files ? fileInput.files[0] : null;
  const subjectId = subjSel ? subjSel.value : "";
  if (!subjectId) return showToast("Avval fanni tanlang.", "error");
  if (!file) return showToast("Yuklash uchun faylni tanlang.", "error");

  const fd = new FormData();
  fd.append("file", file);
  fd.append("material_type", matType);
  fd.append("topic_title", topicSel ? topicSel.value : "");
  const topicOpt = topicSel && topicSel.selectedOptions[0];
  fd.append("topic_id", topicOpt && topicOpt.dataset.id ? topicOpt.dataset.id : "");
  fd.append("title", (document.getElementById("umTitle") || {}).value || "");
  fd.append("mode", (document.getElementById("umFileOnly") || {}).checked ? "file" : "auto");

  const btn = document.getElementById("btnUploadMaterial");
  const result = document.getElementById("umResult");
  if (btn) { btn.disabled = true; btn.innerHTML = "⏳ Fayl tahlil qilinmoqda..."; }
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjectId}/upload-material`, {
      method: "POST", headers: { "Authorization": `Bearer ${STATE.token}` }, body: fd
    });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.detail || "Faylni yuklab bo'lmadi");

    showToast(`✅ ${d.message}`, "success");
    if (result) {
      const unit = matType === "test" ? "ta savol" : "ta slayd";
      const warn = (d.warnings || []).map(w => `<div style="margin-top:6px;padding:6px 10px;border-radius:6px;background:var(--amber-soft);font-size:12px">⚠️ ${escapeHtml(w)}</div>`).join("");
      result.style.display = "block";
      result.innerHTML = `
        <div style="padding:12px 14px;border:1.5px solid var(--teal);border-radius:10px;background:var(--teal-soft);font-size:13px">
          <div style="font-weight:700">${matType === "test" ? "📝" : "🖥️"} ${escapeHtml(d.title)}</div>
          <div style="margin-top:4px;color:var(--ink-2)">${d.items_count} ${unit}${d.file_only ? " · faqat fayl (talaba yuklab oladi)" : " · interaktiv"} · <a href="${escapeHtml(d.file_url)}" target="_blank" style="color:var(--teal)">📎 ${escapeHtml(d.file_name)}</a></div>
          ${warn}
          <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
            ${d.items_count > 0 ? `<button class="btn-primary" style="padding:6px 12px;font-size:12.5px" onclick="window.closeUploadMaterialModal();window.switchSubjectTab('materials');setTimeout(()=>window.viewSavedMaterial('${d.material_id}'),600)">👁️ Ko'rish</button>` : ""}
            <button class="btn-primary" style="padding:6px 12px;font-size:12.5px;background:none;color:var(--ink);border:1px solid var(--line)" onclick="document.getElementById('umFileInput').value='';document.getElementById('umFileNotice').textContent='Fayl hali tanlanmagan';document.getElementById('umResult').style.display='none'">➕ Yana fayl yuklash</button>
          </div>
        </div>`;
    }
    if (typeof window.loadTeacherMaterials === "function") window.loadTeacherMaterials();
    if (typeof window.loadTeacherSubjects === "function") window.loadTeacherSubjects();
  } catch (err) {
    showToast(`❌ ${err.message}`, "error");
    if (result) {
      result.style.display = "block";
      result.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:rgba(185,28,28,0.08);color:#B91C1C;font-size:12.5px">${escapeHtml(err.message)}</div>`;
    }
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = "⬆️ Yuklash va saqlash"; }
  }
};

// Yuklangan asl faylni ochish / yuklab olish (talaba uchun "ko'rildi" belgisi qo'yiladi)
window.downloadMaterialFile = function(materialId, url) {
  if (!url) return;
  if (STATE.currentUser && STATE.currentUser.role === "student" && typeof window.markStudentMaterialViewed === "function") {
    window.markStudentMaterialViewed(materialId);
  }
  window.open(url, "_blank");
};

window.fillStandardTopics = function() {
  const ta = document.getElementById("uploadSyllabusText");
  if (!ta) return;
  ta.value = [
    "1. Principles of Academic Discourse & Critical Thinking",
    "2. Developing Thesis Statement & Structured Arguments",
    "3. Integrating Empirical Evidence & Academic Citations",
    "4. Handling Counterarguments & Rebuttal Strategies",
    "5. Linguistic Accuracy & Complex Grammatical Structures",
    "6. Lexical Sophistication & Discipline-Specific Vocabulary",
    "7. Coherence, Transition Signals & Thematic Progression",
    "8. Midterm Formative Assessment: Essay Diagnostics",
    "9. Metacognitive Self-Monitoring & Revision Tactics",
    "10. Peer Review Protocols & Evaluative Language",
    "11. Overcoming L1 Transfer & Syntactic Calques",
    "12. Presentation Strategies for Academic Research",
    "13. Interactive Classroom Q&A and Academic Discussions",
    "14. Ethical AI Usage: Scaffolding vs. Cognitive Offloading",
    "15. Portfolio Compilation & Empirical Learning Evidence",
    "16. Final Academic Defense & Pedagogical Synthesis"
  ].join("\n");
};

// O'quv dasturi faylini (.docx / .txt) yuklash va tahlil qilish
window.handleSyllabusFileUpload = async function(e) {
  const file = e.target.files ? e.target.files[0] : null;
  if (!file) return;

  const noticeEl = document.getElementById("fileUploadStatusNotice");
  if (noticeEl) {
    noticeEl.innerHTML = `⏳ <strong>${escapeHtml(file.name)}</strong> tahlil qilinmoqda...`;
    noticeEl.style.color = "var(--teal)";
  }

  showToast(`⏳ "${file.name}" o'quv dasturi tahlil qilinmoqda...`, "info");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/parse-syllabus-file`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${STATE.token}`
      },
      body: formData
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Faylni tahlil qilishda xatolik");
    }

    const data = await res.json();
    STATE.parsedSyllabusData = data;

    // Mavzular toifasi bo'yicha textarea ga to'ldirish
    const catSel = document.getElementById("syllabusCategorySelect");
    const category = catSel ? catSel.value : "lecture";
    const ta = document.getElementById("uploadSyllabusText");

    if (ta) {
      if (category === "lecture") {
        ta.value = data.lecture_text || data.formatted_text;
      } else if (category === "seminar") {
        ta.value = data.seminar_text || data.formatted_text;
      } else if (category === "independent") {
        ta.value = data.independent_text || data.formatted_text;
      } else {
        ta.value = data.formatted_text;
      }
    }

    if (noticeEl) {
      noticeEl.innerHTML = `✅ <strong>${escapeHtml(file.name)}</strong>: ${escapeHtml(data.lecture_count)} ta ma'ruza, ${escapeHtml(data.seminar_count)} ta seminar, ${escapeHtml(data.independent_count)} ta mustaqil ta'lim topildi!`;
      noticeEl.style.color = "var(--teal)";
    }

    showToast(`✅ "${file.name}" tahlil qilindi: ${data.lecture_count} ta ma'ruza, ${data.seminar_count} ta seminar ajratildi!`, "success");

  } catch (err) {
    if (noticeEl) {
      noticeEl.textContent = `❌ Xatolik: ${err.message}`;
      noticeEl.style.color = "var(--clay)";
    }
    showToast(`Xatolik: ${err.message}`, "error");
  }
};

// Kategoriya o'zgarganda (Ma'ruza / Seminar / Mustaqil ta'lim / Barchasi)
window.onSyllabusCategoryChange = function() {
  const catSel = document.getElementById("syllabusCategorySelect");
  const category = catSel ? catSel.value : "lecture";
  const ta = document.getElementById("uploadSyllabusText");
  if (!ta) return;

  if (STATE.parsedSyllabusData) {
    const data = STATE.parsedSyllabusData;
    if (category === "lecture") {
      ta.value = data.lecture_text || data.formatted_text;
    } else if (category === "seminar") {
      ta.value = data.seminar_text || data.formatted_text;
    } else if (category === "independent") {
      ta.value = data.independent_text || data.formatted_text;
    } else {
      ta.value = data.formatted_text;
    }
    showToast(`Kategoriya o'zgartirildi: ${category.toUpperCase()}`, "info");
  }
};

// Sillabusni saqlash
window.submitUploadSyllabus = async function() {
  const subjectId = document.getElementById("uploadModalSubjectId").value;
  const fileInput = document.getElementById("fileSyllabusInput");
  const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
  const catSel = document.getElementById("syllabusCategorySelect");
  const category = catSel ? catSel.value : "lecture";
  const text = document.getElementById("uploadSyllabusText").value.trim();

  if (!hasFile && !text) {
    showToast("Sillabus mavzularini kiriting yoki fayl tanlang!", "error");
    return;
  }

  try {
    // Agar fayl tanlangan bo'lsa, to'g'ridan-to'g'ri fayl yuklash endpointiga jo'natish
    if (hasFile) {
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjectId}/upload-syllabus-file?category=${encodeURIComponent(category)}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${STATE.token}`
        },
        body: formData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Fayl orqali sillabusni saqlab bo'lmadi.");
      }

      const data = await res.json();
      showToast(`✅ ${data.message}`, "success");
      window.closeUploadSyllabusModal();
      window.loadTeacherSubjects();
      return;
    }

    // Aks holda tahrirlangan matn sifatida saqlash
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjectId}/syllabus`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({
        syllabus_text: text
      })
    });

    if (!res.ok) throw new Error("Sillabusni yuklab bo'lmadi.");

    const data = await res.json();
    showToast(`✅ ${data.message}`, "success");
    window.closeUploadSyllabusModal();
    window.loadTeacherSubjects();

  } catch (err) {
    showToast(`Xatolik: ${err.message}`, "error");
  }
};

// AI Generator
// Asosiy fandan tashqari "shu fanlarga ham biriktirilsin" ro'yxati
window.renderGenExtraSubjects = function() {
  const box = document.getElementById("genExtraSubjectsBox");
  const list = document.getElementById("genExtraSubjects");
  if (!box || !list) return;
  const cur = (document.getElementById("genSelectSubject") || {}).value;
  const prev = new Set(Array.from(list.querySelectorAll("input:checked")).map(i => i.value));
  const others = (STATE.teacherSubjects || []).filter(s => s.id !== cur);
  if (!cur || others.length === 0) { box.style.display = "none"; list.innerHTML = ""; return; }
  box.style.display = "block";
  list.innerHTML = others.map(s => `
    <label style="display:flex;align-items:center;gap:5px;cursor:pointer">
      <input type="checkbox" class="gen-extra-subject" value="${s.id}" ${prev.has(s.id) ? "checked" : ""}> ${escapeHtml(s.name)} <span style="color:var(--muted)">(${escapeHtml(s.group_name || "")})</span>
    </label>`).join("");
};

window.getGenExtraSubjectIds = function() {
  return Array.from(document.querySelectorAll("#genExtraSubjects input.gen-extra-subject:checked")).map(i => i.value);
};

window.onGenSubjectChange = async function() {
  const subjId = document.getElementById("genSelectSubject").value;
  const topicSel = document.getElementById("genSelectTopic");
  window.renderGenExtraSubjects();
  if (!topicSel) return;

  if (!subjId) {
    topicSel.innerHTML = `<option value="">-- Avval fanni tanlang --</option>`;
    return;
  }

  topicSel.innerHTML = `<option value="">Mavzular yuklanmoqda...</option>`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/subjects/${subjId}/topics`, {
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (!res.ok) throw new Error("Mavzular olinmadi");
    const data = await res.json();
    const topics = data.topics || [];

    if (topics.length === 0) {
      topicSel.innerHTML = `<option value="Umumiy dars mavzusi">1. Umumiy dars mavzusi (Sillabus hali kiritilmagan)</option>`;
      return;
    }

    topicSel.innerHTML = topics.map(t => `<option value="${escapeHtml(t.title)}" data-id="${escapeHtml(t.id || "")}">${escapeHtml(t.title)}</option>`).join("");

  } catch (e) {
    topicSel.innerHTML = `<option value="Umumiy dars">1. Umumiy dars mavzusi</option>`;
  }
};

window.prepareGenerateForTopic = async function(subjectId, topicTitle, materialType) {
  window.switchSubjectTab('generator');

  const subjSel = document.getElementById("genSelectSubject");
  if (subjSel) {
    subjSel.value = subjectId;
    await window.onGenSubjectChange();
  }

  if (topicTitle) {
    const topicSel = document.getElementById("genSelectTopic");
    if (topicSel) {
      // Find matching option or add it
      let found = false;
      for (let i = 0; i < topicSel.options.length; i++) {
        if (topicSel.options[i].value === topicTitle || topicSel.options[i].text.includes(topicTitle)) {
          topicSel.selectedIndex = i;
          found = true;
          break;
        }
      }
      if (!found) {
        const opt = document.createElement("option");
        opt.value = topicTitle;
        opt.text = topicTitle;
        opt.selected = true;
        topicSel.appendChild(opt);
      }
    }
  }

  if (materialType) {
    const radio = document.querySelector(`input[name="genMaterialType"][value="${materialType}"]`);
    if (radio) radio.checked = true;
  }

  // Scroll to generator card
  const genCard = document.getElementById("subTabGeneratorContent");
  if (genCard) genCard.scrollIntoView({ behavior: 'smooth' });
};

window.genSetCount = function(kind, n) {
  const input = document.getElementById(kind === "q" ? "genNumQuestions" : "genNumSlides");
  if (input) input.value = n;
  window.genSyncPreset(kind);
};
window.genSyncPreset = function(kind) {
  const input = document.getElementById(kind === "q" ? "genNumQuestions" : "genNumSlides");
  const val = input ? parseInt(input.value) : NaN;
  document.querySelectorAll(`.gen-preset[data-kind="${kind}"]`).forEach(b => {
    b.classList.toggle("active", parseInt(b.getAttribute("data-val")) === val);
  });
};
document.addEventListener("DOMContentLoaded", () => { window.genSyncPreset("q"); window.genSyncPreset("s"); });

window.describeGenCounts = function(matType, data) {
  if (!data) return "";
  if (matType === "writing") {
    let t = `✍️ ${data.min_words}–${data.max_words} so'z, ${(data.criteria || []).length} ta baholash mezoni` + (data.ai_generated ? " (AI vazifa)" : " (shablon vazifa)");
    if (data.ai_error) t += `<div style="margin-top:6px;padding:8px 10px;border-radius:6px;background:var(--amber-soft);color:var(--ink);font-size:12px">⚠️ ${escapeHtml(data.ai_error)}</div>`;
    return t;
  }
  if (matType === "test") {
    const got = data.questions_count || (data.questions || []).length;
    const req = data.requested_count || got;
    const ai = data.ai_questions_count;
    let t = `📝 ${got} / ${req} ta savol tayyorlandi`;
    if (typeof ai === "number" && ai < got) t += ` (${ai} tasi AI, ${got - ai} tasi pedagogik shablon)`;
    if (data.ai_error) t += `<div style="margin-top:6px;padding:8px 10px;border-radius:6px;background:var(--amber-soft);color:var(--ink);font-size:12px">⚠️ ${escapeHtml(data.ai_error)}</div>`;
    return t;
  }
  if (matType === "presentation") {
    const got = data.slides_count || (data.slides || []).length;
    const req = data.requested_count || got;
    const ai = data.ai_slides_count;
    const im = data.image_mode === "ai" ? "har slaydga AI rasm" : (data.image_mode === "photo" ? "tayyor fotolar" : "rasmsiz");
    let t = `📊 ${got} / ${req} ta slayd tayyorlandi · ${im}`;
    if (typeof ai === "number" && ai < got) t += ` (${ai} tasi AI, ${got - ai} tasi shablon)`;
    if (data.ai_error) t += `<div style="margin-top:6px;padding:8px 10px;border-radius:6px;background:var(--amber-soft);color:var(--ink);font-size:12px">⚠️ ${escapeHtml(data.ai_error)}</div>`;
    return t;
  }
  return "";
};

// Slayd rasmini ko'rsatish: AI rasm ochilmasa zaxira fotoga, u ham bo'lmasa yashiriladi
window.applySlideImage = function(wrapId, imgId, slide) {
  const wrap = document.getElementById(wrapId);
  const img = document.getElementById(imgId);
  if (!wrap || !img) return;
  const url = slide && slide.image_url;
  if (!url) { wrap.style.display = "none"; img.removeAttribute("src"); return; }
  wrap.style.display = "block";
  img.classList.remove("loaded");
  img.onload = () => img.classList.add("loaded");
  img.onerror = () => {
    if (slide.image_fallback_url && img.src !== slide.image_fallback_url && !img.dataset.fallbackTried) {
      img.dataset.fallbackTried = "1";
      img.src = slide.image_fallback_url;
    } else {
      wrap.style.display = "none";
    }
  };
  delete img.dataset.fallbackTried;
  // Eski tasvir qotib qolmasligi uchun tozalab yangi URL o'rnatiladi
  if (img.src !== url) {
    img.src = url;
  }
};

window.submitGenerateMaterial = async function() {
  const subjId = document.getElementById("genSelectSubject").value;
  const topicTitle = document.getElementById("genSelectTopic").value;
  const matTypeEl = document.querySelector('input[name="genMaterialType"]:checked');
  const matType = matTypeEl ? matTypeEl.value : "test";
  const diff = document.getElementById("genDifficulty").value;
  const extraPrompt = document.getElementById("genExtraPrompt").value.trim();
  const clamp = (v, lo, hi, d) => { const n = parseInt(v); return isNaN(n) ? d : Math.max(lo, Math.min(hi, n)); };
  const numQuestions = clamp(document.getElementById("genNumQuestions")?.value, 1, 60, 10);
  const numSlides = clamp(document.getElementById("genNumSlides")?.value, 1, 40, 8);
  const imageMode = document.getElementById("genImageMode") ? document.getElementById("genImageMode").value : "ai";
  const withImages = imageMode !== "none";
  const extraSubjectIds = window.getGenExtraSubjectIds();
  const topicOpt = document.getElementById("genSelectTopic").selectedOptions[0];
  const topicId = topicOpt && topicOpt.dataset.id ? topicOpt.dataset.id : null;
  const minWords = clamp(document.getElementById("genMinWords")?.value, 30, 2000, 150);
  const maxWords = clamp(document.getElementById("genMaxWords")?.value, 30, 3000, 200);
  const genLanguage = document.getElementById("genLanguage") ? document.getElementById("genLanguage").value : "uz";

  if (!subjId) {
    showToast("Iltimos, avval fanni tanlang!", "error");
    return;
  }
  if (!topicTitle) {
    showToast("Iltimos, mavzuni tanlang!", "error");
    return;
  }

  const btn = document.getElementById("btnGenerateMaterial");
  const resContainer = document.getElementById("genResultContainer");

  const origBtnText = btn.innerHTML;
  btn.disabled = true;
  const countLabel = matType === "test" ? `${numQuestions} ta savol` : (matType === "presentation" ? `${numSlides} ta slayd` : (matType === "writing" ? "yozma topshiriq" : "dars rejasi"));
  const etaSec = matType === "test" ? Math.ceil(numQuestions / 8) * 20 : (matType === "presentation" ? Math.ceil(numSlides / 6) * 25 : 20);
  btn.innerHTML = `<span>⏳</span> <span>AI ${countLabel} tayyorlamoqda... (taxminan ${etaSec} soniya)</span>`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/generate-material`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({
        subject_id: subjId,
        subject_ids: extraSubjectIds,
        topic_id: topicId,
        topic_title: topicTitle,
        material_type: matType,
        difficulty: diff,
        extra_instructions: extraPrompt,
        num_questions: numQuestions,
        num_slides: numSlides,
        with_images: withImages,
        image_mode: imageMode,
        min_words: Math.min(minWords, maxWords),
        max_words: Math.max(minWords, maxWords),
        language: genLanguage
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Generatsiya qilishda xatolik yuz berdi");
    }

    const respData = await res.json();
    const itemData = respData.data;

    showToast(`✅ ${respData.message}`, "success");

    // Doimiy saqlanganini ko'rsatish
    if (resContainer) {
      resContainer.style.display = "block";
      resContainer.innerHTML = `
        <div class="card" style="padding:22px;border:1.5px solid var(--teal);background:radial-gradient(circle at 90% 10%, rgba(13,110,110,0.06), transparent 50%), var(--card)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:14px">
            <div>
              <span style="font-size:11.5px;font-weight:700;padding:3px 8px;border-radius:4px;background:var(--teal-soft);color:var(--teal)">
                ${matType === 'test' ? '📝 NAZORAT TESTI' : (matType === 'presentation' ? '📊 INTERAKTIV PREZENTATSIYA' : (matType === 'writing' ? '✍️ YOZMA TOPSHIRIQ' : '📋 DARS ISHLANMASI'))}
              </span>
              <h3 style="margin:6px 0 2px;font-size:20px;font-family:var(--serif)">${escapeHtml(respData.title)}</h3>
              <p style="margin:0;font-size:13px;color:var(--muted)">Fan: <b>${escapeHtml((respData.assigned_subjects || [respData.subject_name]).join(", "))}</b> · Mavzu: <b>${escapeHtml(respData.topic_title)}</b></p>
              <div style="font-size:12px;color:var(--teal);margin-top:4px">💾 Ushbu material profilingizda saqlandi va o'chib ketmaydi.</div>
              <div style="font-size:12px;color:var(--ink-2);margin-top:4px">${window.describeGenCounts(matType, itemData)}</div>
            </div>
            <div style="display:flex;gap:8px">
              <button class="btn-primary" style="padding:9px 18px;font-size:13.5px" onclick="window.viewSavedMaterial('${respData.material_id}')">
                👁️ Ko'rish / Taqdimot qilish →
              </button>
            </div>
          </div>
        </div>
      `;
      resContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Statistika va materiallar ro'yxatini yangilash
    window.loadTeacherMaterials();
    window.loadTeacherSubjects();

    // To'g'ridan-to'g'ri ko'rish modali ochilsin
    if (matType === "presentation") {
      window.openPresentationModal(itemData.slides || [], respData.title, respData.subject_name, respData.material_id);
    } else if (matType === "test") {
      window.openTestModal(itemData, respData.title, respData.subject_name);
    } else if (matType === "writing") {
      window.openWritingPreview(itemData, respData.title, respData.subject_name, respData.topic_title);
    } else if (matType === "lesson_plan") {
      window.viewStudentLessonPlan(respData.material_id);
    }

  } catch (err) {
    showToast(`Xatolik: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = origBtnText;
  }
};

// Saqlangan Materiallar Ro'yxati
window.loadTeacherMaterials = async function() {
  const container = document.getElementById("materialsListContainer");
  const badge = document.getElementById("countMaterialsBadge");
  const filterType = document.getElementById("filterMaterialType") ? document.getElementById("filterMaterialType").value : "";

  if (!STATE.token) return;

  try {
    let url = `${STATE.apiBaseUrl}/teacher/materials`;
    if (filterType) url += `?material_type=${filterType}`;

    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (!res.ok) return;

    const data = await res.json();
    STATE.teacherMaterials = data.materials || [];

    if (badge) badge.textContent = STATE.teacherMaterials.length;

    if (!container) return;

    if (STATE.teacherMaterials.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align:center;padding:36px 20px">
          <div style="font-size:32px;margin-bottom:8px">📁</div>
          <h4 style="margin:0 0 6px">Hozircha saqlangan materiallar yo'q</h4>
          <p style="font-size:13px;color:var(--muted);margin:0 0 14px">AI Generator yordamida fanning biror mavzusiga test yoki slayd tayyorlang yoki tayyor faylingizni yuklang.</p>
          <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
            <button class="btn-primary" onclick="window.switchSubjectTab('generator')">✨ AI bilan tayyorlash</button>
            <button class="btn-primary" style="background:var(--amber);border-color:var(--amber)" onclick="window.openUploadMaterialModal()">⬆️ Fayldan yuklash</button>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = STATE.teacherMaterials.map(m => {
      const typeBadge = m.material_type === 'test' ? '📝 TEST' : (m.material_type === 'presentation' ? '📊 PREZENTATSIYA' : (m.material_type === 'writing' ? '✍️ YOZMA TOPSHIRIQ' : '📋 DARS REJASI'));
      const badgeBg = m.material_type === 'presentation' ? 'var(--amber-soft)' : 'var(--teal-soft)';
      const badgeColor = m.material_type === 'presentation' ? 'var(--amber)' : 'var(--teal)';
      const lang = (m.content && m.content.language) ? m.content.language.toLowerCase() : "";
      const langBadge = lang === 'en' ? '🇬🇧 EN' : (lang === 'ru' ? '🇷🇺 RU' : (lang === 'uz' ? '🇺🇿 UZ' : ''));

      return `
        <div class="card" style="padding:16px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
          <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
              <span style="font-size:11px;font-weight:700;padding:2px 7px;background:${badgeBg};color:${badgeColor};border-radius:4px">${typeBadge}</span>
              ${langBadge ? `<span style="font-size:11px;font-weight:700;padding:2px 6px;background:var(--surface-2);color:var(--ink-2);border-radius:4px">${langBadge}</span>` : ''}
              <span style="font-size:12px;color:var(--muted)">${escapeHtml(m.subject_name)} · ${escapeHtml(m.created_at)}</span>
            </div>
            <h4 style="margin:0 0 4px;font-size:16px;font-family:var(--serif)">${escapeHtml(m.title)}</h4>
            <div style="font-size:13px;color:var(--ink-2)">Mavzu: <b>${escapeHtml(m.topic_title)}</b></div>
            ${(m.content && m.content.file_url) ? `<div style="font-size:12px;margin-top:4px"><a href="${escapeHtml(m.content.file_url)}" target="_blank" style="color:var(--teal);font-weight:600">📎 ${escapeHtml(m.content.file_name || "Yuklangan fayl")}</a>${m.content.file_only ? ` <span style="color:var(--muted)">(faqat fayl)</span>` : ""}</div>` : ""}
          </div>

          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn-primary" style="padding:7px 14px;font-size:12.5px" onclick="window.viewSavedMaterial('${m.id}')">
              ${m.material_type === 'presentation' ? '🖥️ Taqdimot qilish' : "👁️ Ko'rish"}
            </button>
            <button class="btn-primary" style="padding:7px 12px;font-size:12.5px;background:none;color:var(--ink);border:1px solid var(--line)" onclick="window.openMaterialResults('${m.id}')" title="Talabalar natijalari">
              📊 Natijalar (${m.students_done || 0})
            </button>
            <button class="btn-primary" style="padding:7px 12px;font-size:12.5px;background:none;color:var(--ink);border:1px solid var(--line)" onclick="window.openAssignMaterial('${m.id}')" title="Boshqa fanlarga ham biriktirish">
              ➕ Fanga biriktirish
            </button>
            <button class="btn-primary" style="padding:7px 10px;font-size:12px;background:none;color:var(--clay);border:1px solid var(--line)" onclick="window.deleteSavedMaterial('${m.id}')" title="O'chirish">
              🗑️
            </button>
          </div>
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("loadTeacherMaterials xatosi:", err);
  }
};

window.viewSavedMaterial = function(materialId) {
  const item = STATE.teacherMaterials.find(m => m.id === materialId);
  if (!item) {
    showToast("Material topilmadi.", "error");
    return;
  }

  const content = item.content || {};

  // Faqat fayl sifatida yuklangan material (savol/slayd ajratilmagan) — asl faylni ochamiz
  const emptyUploaded = content.file_url && (
    (item.material_type === "test" && !(content.questions || []).length) ||
    (item.material_type === "presentation" && !(content.slides || []).length)
  );
  if (emptyUploaded) {
    window.downloadMaterialFile(item.id, content.file_url);
    return;
  }

  if (item.material_type === "presentation") {
    const slides = content.slides || [];
    window.openPresentationModal(slides, item.title, item.subject_name, item.id);
  } else if (item.material_type === "test") {
    window.openTestModal(content, item.title, item.subject_name);
  } else if (item.material_type === "writing") {
    window.openWritingPreview(content, item.title, item.subject_name, item.topic_title);
  } else if (item.material_type === "lesson_plan") {
    window.viewStudentLessonPlan(materialId);
  }
};

// Yozma topshiriqni o'qituvchi ko'rinishida (tahrirsiz) ko'rsatish
window.openWritingPreview = function(content, title, subjectName, topicTitle) {
  window.fillWritingModal(content || {}, { title, subject_title: subjectName, topic_title: topicTitle });
  const editor = document.getElementById("swEditor");
  const result = document.getElementById("swResult");
  if (editor) editor.style.display = "none";
  if (result) result.style.display = "none";
  const modal = document.getElementById("studentWritingModal");
  if (modal) modal.style.display = "flex";
};

// Materialni boshqa fanlarga biriktirish (checkbox ro'yxati)
window.openAssignMaterial = function(materialId) {
  const item = (STATE.teacherMaterials || []).find(m => m.id === materialId);
  if (!item) return;
  const others = (STATE.teacherSubjects || []).filter(s => s.id !== item.subject_id);
  const modal = document.getElementById("teacherResultsModal");
  document.getElementById("trTitle").textContent = `➕ "${item.title}" ni boshqa fanlarga biriktirish`;
  document.getElementById("trSummary").textContent = `Hozir: ${item.subject_name}. Tanlangan fanlarda nusxasi yaratiladi; talabalar o'sha fan ichida ko'radi.`;
  const body = document.getElementById("trBody");
  if (others.length === 0) {
    body.innerHTML = `<div style="color:var(--muted);font-size:13px">Boshqa fan yo'q. Avval "Fanlarim" bo'limida yangi fan qo'shing.</div>`;
  } else {
    body.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:14px">
        ${others.map(s => `<label style="display:flex;align-items:center;gap:8px;font-size:13.5px;cursor:pointer"><input type="checkbox" class="assign-subject" value="${s.id}"> ${escapeHtml(s.name)} <span style="color:var(--muted)">(${escapeHtml(s.group_name || "")})</span></label>`).join("")}
      </div>
      <button class="btn-primary" style="padding:9px 18px" onclick="window.submitAssignMaterial('${materialId}')">✅ Biriktirish</button>`;
  }
  modal.style.display = "flex";
};

window.submitAssignMaterial = async function(materialId) {
  const ids = Array.from(document.querySelectorAll("#trBody input.assign-subject:checked")).map(i => i.value);
  if (ids.length === 0) return showToast("Kamida bitta fan tanlang.", "warning");
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/materials/${materialId}/assign`, {
      method: "POST", headers: { "Content-Type": "application/json", "Authorization": `Bearer ${STATE.token}` },
      body: JSON.stringify({ subject_ids: ids })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || "Biriktirib bo'lmadi");
    showToast(`✅ ${d.message}`, "success");
    document.getElementById("teacherResultsModal").style.display = "none";
    window.loadTeacherMaterials();
    window.loadTeacherSubjects();
  } catch (e) {
    showToast(e.message, "error");
  }
};

// Material bo'yicha talabalar natijalari
window.openMaterialResults = async function(materialId) {
  const modal = document.getElementById("teacherResultsModal");
  const body = document.getElementById("trBody");
  document.getElementById("trTitle").textContent = "📊 Natijalar";
  document.getElementById("trSummary").textContent = "Yuklanmoqda...";
  body.innerHTML = "";
  modal.style.display = "flex";
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/materials/${materialId}/results`, { headers: { "Authorization": `Bearer ${STATE.token}` } });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || "Natijalarni olib bo'lmadi");
    const m = d.material, sm = d.summary;
    const isWriting = m.material_type === "writing", isTest = m.material_type === "test";
    document.getElementById("trTitle").textContent = `📊 ${m.title}`;
    document.getElementById("trSummary").textContent =
      `${sm.students} ta talaba · ${sm.attempts} ta urinish · bajargan: ${sm.completed}` +
      (sm.average_score !== null && sm.average_score !== undefined ? ` · o'rtacha: ${sm.average_score}%` : "") +
      ((isTest || isWriting) ? ` · o'tgan: ${sm.passed}` : "");
    if (!d.results.length) {
      body.innerHTML = `<div style="text-align:center;padding:26px;color:var(--muted)">Hali hech bir talaba bajarmagan.</div>`;
      return;
    }
    body.innerHTML = `
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="text-align:left;color:var(--muted);font-size:12px">
          <th style="padding:6px 8px;border-bottom:1px solid var(--line)">Talaba</th>
          <th style="padding:6px 8px;border-bottom:1px solid var(--line)">Holat</th>
          <th style="padding:6px 8px;border-bottom:1px solid var(--line)">Eng yaxshi</th>
          <th style="padding:6px 8px;border-bottom:1px solid var(--line)">Urinish</th>
          <th style="padding:6px 8px;border-bottom:1px solid var(--line)">Oxirgi</th>
          <th style="padding:6px 8px;border-bottom:1px solid var(--line)"></th>
        </tr></thead>
        <tbody>
          ${d.results.map(r => `
            <tr>
              <td style="padding:7px 8px;border-bottom:1px solid var(--line-2);font-weight:600">${escapeHtml(r.student_name || r.student_id)}</td>
              <td style="padding:7px 8px;border-bottom:1px solid var(--line-2)">${r.status === "completed" ? "✅ Bajargan" : "👁️ Ko'rgan"}</td>
              <td style="padding:7px 8px;border-bottom:1px solid var(--line-2)">${r.score !== null && r.score !== undefined ? `<b style="color:${r.passed ? '#15803D' : '#B91C1C'}">${r.score}%</b>${isTest && r.total_count ? ` (${r.correct_count}/${r.total_count})` : ""}` : "—"}</td>
              <td style="padding:7px 8px;border-bottom:1px solid var(--line-2)">${r.attempts}</td>
              <td style="padding:7px 8px;border-bottom:1px solid var(--line-2);color:var(--muted)">${r.created_at}</td>
              <td style="padding:7px 8px;border-bottom:1px solid var(--line-2)">${(isWriting || isTest) ? `<button class="btn-primary" style="padding:4px 10px;font-size:12px" onclick="window.openAttemptDetail('${materialId}','${r.id}')">Ko'rish</button>` : ""}</td>
            </tr>`).join("")}
        </tbody>
      </table>
      <div id="trDetail" style="margin-top:14px"></div>`;
  } catch (e) {
    document.getElementById("trSummary").textContent = "";
    body.innerHTML = `<div style="color:var(--clay)">⚠️ ${escapeHtml(e.message)}</div>`;
  }
};

window.openAttemptDetail = async function(materialId, attemptId) {
  const box = document.getElementById("trDetail");
  if (!box) return;
  box.innerHTML = `<div style="color:var(--muted);font-size:13px">Yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/materials/${materialId}/results/${attemptId}`, { headers: { "Authorization": `Bearer ${STATE.token}` } });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || "Urinish topilmadi");
    if (d.material_type === "writing") {
      const r = d.result || {};
      box.innerHTML = `
        <div class="card" style="padding:14px 16px">
          <div style="font-weight:700;margin-bottom:6px">✍️ ${escapeHtml(d.student_name)} — ${r.word_count || 0} so'z · ${d.score}% · ${escapeHtml(r.cefr_estimate || "")}</div>
          <div style="white-space:pre-wrap;font-size:13.5px;line-height:1.6;padding:10px 12px;background:var(--surface-2);border-radius:8px;margin-bottom:10px">${escapeHtml((d.answers || {}).text || "")}</div>
          ${window.renderRubricHtml(r, (d.answers || {}).self_rating)}
        </div>`;
    } else {
      const ans = d.answers || {};
      box.innerHTML = `<div class="card" style="padding:12px 14px;font-size:13px"><b>${escapeHtml(d.student_name)}</b>: ${d.correct_count}/${d.total_count} to'g'ri (${d.score}%). Javoblar: ${Object.entries(ans).map(([q, i]) => `${escapeHtml(q)}→${["A","B","C","D","E","F"][i] || i}`).join(", ")}</div>`;
    }
  } catch (e) {
    box.innerHTML = `<div style="color:var(--clay)">⚠️ ${escapeHtml(e.message)}</div>`;
  }
};

// Rubrika natijasini HTML ga aylantirish (talaba va o'qituvchi uchun umumiy)
window.renderRubricHtml = function(r, selfRating) {
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  let names = { content: "Mazmun", grammar: "Grammatika", lexis: "Leksika", coherence: "Bog'liqlik" };
  if (lang === "ru") {
    names = { content: "Содержание", grammar: "Грамматика", lexis: "Лексика", coherence: "Связность" };
  } else if (lang === "en") {
    names = { content: "Content", grammar: "Grammar", lexis: "Lexis", coherence: "Coherence" };
  }
  const rub = r.rubric || {};
  const selfLabel = lang === "ru" ? "самооценка" : (lang === "en" ? "self" : "o'zi");
  const rows = Object.keys(names).map(k => {
    const c = rub[k] || {};
    const sr = selfRating && selfRating[k] ? ` <span style="color:var(--muted);font-size:11.5px">(${selfLabel}: ${selfRating[k]})</span>` : "";
    return `<tr><td style="padding:5px 8px;border-bottom:1px solid var(--line-2);font-weight:600">${names[k]}</td>
      <td style="padding:5px 8px;border-bottom:1px solid var(--line-2);white-space:nowrap"><b>${c.score ?? "—"}</b>/5${sr}</td>
      <td style="padding:5px 8px;border-bottom:1px solid var(--line-2);color:var(--ink-2)">${escapeHtml(c.reason || "")}</td></tr>`;
  }).join("");
  const list = (arr, icon) => (arr || []).map(x => `<li>${icon} ${escapeHtml(x)}</li>`).join("");
  const aiScoreLabel = lang === "ru" ? "🤖 Оценка ИИ по рубрике" : (lang === "en" ? "🤖 AI Rubric Evaluation" : "🤖 AI rubrika bahosi");
  const localScoreLabel = lang === "ru" ? "🧮 Локальная оценка (ИИ выключен)" : (lang === "en" ? "🧮 Local evaluation (AI off)" : "🧮 Lokal (AI o'chiq) baho");
  return `
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px">${rows}</table>
    ${r.length_note ? `<div style="font-size:12.5px;color:var(--amber);margin-bottom:6px">📏 ${escapeHtml(r.length_note)}</div>` : ""}
    <ul style="margin:0 0 6px;padding-left:18px;font-size:13px">${list(r.strengths, "💪")}${list(r.improvements, "🔧")}</ul>
    ${r.overall_comment ? `<div style="font-size:13px;color:var(--ink-2)">💬 ${escapeHtml(r.overall_comment)}</div>` : ""}
    <div style="font-size:11.5px;color:var(--muted);margin-top:6px">${r.ai_generated ? aiScoreLabel : localScoreLabel}${r.model ? ` · ${escapeHtml(String(r.model))}` : ""}</div>`;
};

window.deleteSavedMaterial = async function(materialId) {
  if (!confirm("Ushbu saqlangan materialni o'chirmoqchimisiz?")) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/teacher/materials/${materialId}`, {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${STATE.token}` }
    });
    if (!res.ok) throw new Error("Materialni o'chirib bo'lmadi.");

    showToast("Material o'chirildi.", "success");
    window.loadTeacherMaterials();
    window.loadTeacherSubjects();
  } catch (e) {
    showToast(e.message, "error");
  }
};

// =========================================================================
// PREZENTATSIYA KO'RUVCHI (INTERAKTIV SLAYD KARUSELI)
// =========================================================================

window.openPresentationModal = function(slides, title, subjectName, materialId) {
  STATE.currentPresentation = {
    slides: slides || [],
    title: title || "Prezentatsiya",
    subjectName: subjectName || "Fan",
    materialId: materialId || null
  };
  STATE.currentSlideIndex = 0;

  const subjBadge = document.getElementById("presModalSubjectBadge");
  const titleEl = document.getElementById("presModalTitle");

  if (subjBadge) subjBadge.textContent = subjectName || "FAN";
  if (titleEl) titleEl.textContent = title || "Prezentatsiya";

  window.renderCurrentSlide();

  const modal = document.getElementById("viewPresentationModal");
  if (modal) modal.style.display = "flex";
};

window.closePresentationModal = function() {
  const modal = document.getElementById("viewPresentationModal");
  if (modal) modal.style.display = "none";
};

window.regenerateCurrentSlideImage = async function() {
  if (!STATE.currentPresentation || !STATE.currentPresentation.slides.length) return;
  const idx = STATE.currentSlideIndex;
  const s = STATE.currentPresentation.slides[idx];
  const matId = STATE.currentPresentation.materialId;
  const btn = document.getElementById("btnRegenerateSlideImage");
  const origBtnText = btn ? btn.innerHTML : "";

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "⏳ Yangilanmoqda...";
  }

  try {
    const token = STATE.token || localStorage.getItem("tilora_token") || "";
    let updated = false;

    // 1) Agar taqdimot bazada mavjud bo'lsa, backend orqali yangilab bazaga saqlash
    if (matId) {
      const resp = await fetch(`${STATE.apiBaseUrl}/teacher/materials/${matId}/slides/${idx + 1}/regenerate-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? `Bearer ${token}` : ""
        }
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.image_url) {
          s.image_url = data.image_url;
          s.image_source = "ai";
          updated = true;
        }
      }
    }

    // 2) Agar material hali saqlanmagan yoki offline bo'lsa, umumiy generator orqali
    if (!updated) {
      const resp = await fetch(`${STATE.apiBaseUrl}/teacher/materials/regenerate-slide-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? `Bearer ${token}` : ""
        },
        body: JSON.stringify({
          topic: STATE.currentPresentation.title || "",
          subject: STATE.currentPresentation.subjectName || "",
          slide_title: s.title || "",
          prompt: s.image_prompt || "",
          slide_index: idx
        })
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.image_url) {
          s.image_url = data.image_url;
          s.image_source = "ai";
          updated = true;
        }
      }
    }

    // 3) Fallback: bevosita yangi unikal seed bilan flux rasm URL yaratish
    if (!updated) {
      const randSeed = Math.floor(Math.random() * 9000000) + 1000000;
      const topic = STATE.currentPresentation.title || "";
      const prompt = s.image_prompt || s.title || topic;
      const cleanPrompt = encodeURIComponent(`${topic}, ${prompt}, high quality educational presentation visual, modern minimal aesthetic, 4k, clean, no text, no letters, no watermark`);
      s.image_url = `https://image.pollinations.ai/prompt/${cleanPrompt}?width=1280&height=720&nologo=true&seed=${randSeed}&model=flux`;
      s.image_source = "ai";
    }

    // Yangi rasmni render qilish
    window.renderCurrentSlide();
    showToast("Slayd uchun yangi unikal AI rasm generatsiya qilindi!", "success");
  } catch (err) {
    console.error("Rasm yangilash xatosi:", err);
    showToast("Rasmni yangilashda xatolik yuz berdi", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnText || "🔄 Yangi rasm olish";
    }
  }
};

window.renderCurrentSlide = function() {
  if (!STATE.currentPresentation || !STATE.currentPresentation.slides.length) return;

  const slides = STATE.currentPresentation.slides;
  const idx = STATE.currentSlideIndex;
  const s = slides[idx];

  const canvasEl = document.getElementById("presSlideCanvas");
  const counterEl = document.getElementById("presSlideCounter");
  const badgeEl = document.getElementById("presSlideBadge");
  const titleEl = document.getElementById("presSlideTitle");
  const bulletsEl = document.getElementById("presSlideBullets");
  const notesText = document.getElementById("presSpeakerNotesText");
  const notesBox = document.getElementById("presSpeakerNotesBox");
  const imagePromptBox = document.getElementById("presImagePromptBox");
  const imagePromptText = document.getElementById("presImagePromptText");

  const btnPrev = document.getElementById("btnPrevSlide");
  const btnNext = document.getElementById("btnNextSlide");

  if (counterEl) counterEl.textContent = `Slayd: ${idx + 1} / ${slides.length}`;
  if (badgeEl) badgeEl.textContent = s.visual_badge || `SLAYD #${idx + 1}`;
  if (titleEl) titleEl.textContent = s.title || `Slayd ${idx + 1}`;
  window.applySlideImage("presSlideImageWrap", "presSlideImage", s);

  // Orqa fonga mavzuga oid rasmni joylashtirish
  if (canvasEl) {
    if (s.image_url) {
      canvasEl.style.backgroundImage = "linear-gradient(135deg, rgba(10, 15, 30, 0.85) 0%, rgba(15, 23, 42, 0.94) 100%), url(" + JSON.stringify(String(s.image_url)) + ")";
      canvasEl.style.backgroundSize = "cover";
      canvasEl.style.backgroundPosition = "center";
      canvasEl.style.color = "#f8fafc";
      if (titleEl) {
        titleEl.style.color = "#ffffff";
        titleEl.style.textShadow = "0 2px 10px rgba(0,0,0,0.6)";
      }
      if (bulletsEl) {
        bulletsEl.style.color = "#f1f5f9";
      }
      if (notesBox) {
        notesBox.style.background = "rgba(15, 23, 42, 0.75)";
        notesBox.style.backdropFilter = "blur(6px)";
      }
    } else {
      canvasEl.style.backgroundImage = "radial-gradient(circle at 90% 10%, rgba(13,110,110,0.08), transparent 40%)";
      canvasEl.style.backgroundColor = "var(--card)";
      canvasEl.style.color = "var(--ink)";
      if (titleEl) {
        titleEl.style.color = "var(--ink)";
        titleEl.style.textShadow = "none";
      }
      if (bulletsEl) {
        bulletsEl.style.color = "var(--ink-2)";
      }
      if (notesBox) {
        notesBox.style.background = "var(--surface-2)";
        notesBox.style.backdropFilter = "none";
      }
    }
  }

  if (bulletsEl) {
    bulletsEl.innerHTML = (s.bullets || []).map(b => `<li style="margin-bottom:10px;line-height:1.6">${escapeHtml(b)}</li>`).join("");
  }

  if (notesText) {
    notesText.textContent = s.speaker_notes || "Ushbu slayd bo'yicha og'zaki tushuntirish beriladi.";
  }

  if (imagePromptBox && imagePromptText) {
    if (s.image_prompt && s.image_prompt.trim()) {
      imagePromptText.textContent = s.image_prompt;
      imagePromptBox.style.display = "block";
    } else {
      imagePromptBox.style.display = "none";
    }
  }

  if (btnPrev) btnPrev.disabled = (idx === 0);
  if (btnNext) btnNext.textContent = (idx === slides.length - 1) ? "Tamomlash ✓" : "Keyingi slayd →";
};

window.nextSlide = function() {
  if (!STATE.currentPresentation) return;
  const total = STATE.currentPresentation.slides.length;
  if (STATE.currentSlideIndex < total - 1) {
    STATE.currentSlideIndex++;
    window.renderCurrentSlide();
  } else {
    window.closePresentationModal();
    showToast("Taqdimot namoyishi yakunlandi!", "info");
  }
};

window.prevSlide = function() {
  if (!STATE.currentPresentation) return;
  if (STATE.currentSlideIndex > 0) {
    STATE.currentSlideIndex--;
    window.renderCurrentSlide();
  }
};

window.copyPresentationText = function() {
  if (!STATE.currentPresentation) return;
  const pres = STATE.currentPresentation;
  let text = `PREZENTATSIYA: ${pres.title}\nFan: ${pres.subjectName}\n\n`;

  pres.slides.forEach((s, i) => {
    text += `=== SLAYD ${i + 1}: ${s.title} ===\n`;
    (s.bullets || []).forEach(b => text += `• ${b}\n`);
    if (s.speaker_notes) text += `[Spiker eslatmasi]: ${s.speaker_notes}\n`;
    if (s.image_prompt) text += `[Rasm prompti]: ${s.image_prompt}\n`;
    text += `\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    showToast("📋 Barcha slaydlar matni nusxalandi!", "success");
  }).catch(() => {
    alert("Nusxalash imkoni bo'lmadi");
  });
};

// Klaviatura strelkalari bilan slaydlarni o'tkazish
window.addEventListener("keydown", function(e) {
  const modal = document.getElementById("viewPresentationModal");
  if (modal && modal.style.display === "flex") {
    if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
      window.nextSlide();
    } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
      window.prevSlide();
    } else if (e.key === "Escape") {
      window.closePresentationModal();
    }
  }
});

// =========================================================================
// TEST KO'RUVCHI
// =========================================================================

window.openTestModal = function(testData, title, subjectName) {
  STATE.currentTest = testData;
  STATE.showAnswerKeys = true;

  const subjEl = document.getElementById("testModalSubject");
  const titleEl = document.getElementById("testModalTitle");
  const topicEl = document.getElementById("testModalTopic");
  const qList = document.getElementById("testQuestionsList");

  if (subjEl) subjEl.textContent = subjectName || testData.subject || "FAN";
  if (titleEl) titleEl.textContent = title || testData.title || "Nazorat Testi";
  if (topicEl) topicEl.textContent = `Mavzu: ${testData.topic || ''} · Qiyinlik: ${testData.difficulty || 'B2'}`;

  window.renderTestQuestions();

  const modal = document.getElementById("viewTestModal");
  if (modal) modal.style.display = "flex";
};

window.closeTestModal = function() {
  const modal = document.getElementById("viewTestModal");
  if (modal) modal.style.display = "none";
};

window.toggleAnswerKeys = function() {
  STATE.showAnswerKeys = !STATE.showAnswerKeys;
  const btnText = document.getElementById("btnToggleKeyText");
  if (btnText) {
    btnText.textContent = STATE.showAnswerKeys ? "Javoblarni yashirish" : "Javoblarni ko'rsatish";
  }
  window.renderTestQuestions();
};

window.renderTestQuestions = function() {
  const qList = document.getElementById("testQuestionsList");
  if (!qList || !STATE.currentTest) return;

  const questions = STATE.currentTest.questions || [];
  const letters = ["A", "B", "C", "D"];

  qList.innerHTML = questions.map((q, idx) => {
    return `
      <div style="padding:14px 16px;background:var(--surface-2);border-radius:10px;border:1px solid var(--line)">
        <div style="font-weight:700;font-size:14px;color:var(--ink);margin-bottom:10px">
          ${idx + 1}. ${escapeHtml(q.question)}
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:10px">
          ${(q.options || []).map((opt, oIdx) => {
            const isCorrect = (oIdx === q.correct_index);
            const style = (STATE.showAnswerKeys && isCorrect)
              ? "background:rgba(13,110,110,0.12);border:1.5px solid var(--teal);color:var(--teal);font-weight:700"
              : "background:var(--card);border:1px solid var(--line);color:var(--ink-2)";

            return `
              <div style="padding:8px 12px;border-radius:6px;font-size:13px;display:flex;align-items:center;gap:8px;${style}">
                <span style="font-weight:700;min-width:20px">${letters[oIdx]})</span>
                <span>${escapeHtml(opt)}</span>
                ${(STATE.showAnswerKeys && isCorrect) ? '<span style="margin-left:auto;font-size:12px;color:var(--teal)">✓ To\'g\'ri javob</span>' : ''}
              </div>
            `;
          }).join("")}
        </div>
        ${(STATE.showAnswerKeys && q.explanation) ? `
          <div style="font-size:12px;color:var(--muted);background:rgba(0,0,0,0.03);padding:8px 10px;border-radius:6px;border-left:3px solid var(--teal)">
            <b>Izoh:</b> ${escapeHtml(q.explanation)}
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
};

window.printOrCopyTest = function() {
  if (!STATE.currentTest) return;
  const t = STATE.currentTest;
  let text = `TEST: ${t.title || 'Nazorat Testi'}\nFan: ${t.subject || ''}\nMavzu: ${t.topic || ''}\n\n`;

  const letters = ["A", "B", "C", "D"];
  (t.questions || []).forEach((q, i) => {
    text += `${i + 1}. ${q.question}\n`;
    (q.options || []).forEach((opt, oIdx) => {
      text += `   ${letters[oIdx]}) ${opt}\n`;
    });
    text += `   [To'g'ri javob: ${letters[q.correct_index] || 'A'}] — ${q.explanation || ''}\n\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    showToast("📋 Test savollari va javoblar kaliti nusxalandi!", "success");
  }).catch(() => {
    alert("Nusxalash imkoni bo'lmadi");
  });
};


// =========================================================================
// SUPER ADMINISTRATOR BOSHQARUVI (ARIZALAR, TO'LOVLAR VA FOYDALANUVCHILAR)
// =========================================================================

window.switchAdminTab = function(tabName) {
  const btnPending = document.getElementById("adminBtnTabPending");
  const btnTeachers = document.getElementById("adminBtnTabTeachers");
  const btnPayments = document.getElementById("adminBtnTabPayments");
  const btnAllUsers = document.getElementById("adminBtnTabAllUsers");
  const btnSystem = document.getElementById("adminBtnTabSystem");

  const tabPending = document.getElementById("adminTabContentPending");
  const tabTeachers = document.getElementById("adminTabContentTeachers");
  const tabPayments = document.getElementById("adminTabContentPayments");
  const tabAllUsers = document.getElementById("adminTabContentAllUsers");
  const tabSystem = document.getElementById("adminTabContentSystem");

  const btns = [btnPending, btnTeachers, btnPayments, btnAllUsers, btnSystem];
  const tabs = [tabPending, tabTeachers, tabPayments, tabAllUsers, tabSystem];

  btns.forEach(b => {
    if (b) {
      b.style.background = "none";
      b.style.color = "var(--ink)";
      b.style.border = "1px solid var(--line)";
    }
  });

  tabs.forEach(t => {
    if (t) t.style.display = "none";
  });

  if (tabName === "pending") {
    if (btnPending) { btnPending.style.background = "var(--teal)"; btnPending.style.color = "#fff"; btnPending.style.border = "none"; }
    if (tabPending) tabPending.style.display = "block";
  } else if (tabName === "teachers") {
    if (btnTeachers) { btnTeachers.style.background = "var(--teal)"; btnTeachers.style.color = "#fff"; btnTeachers.style.border = "none"; }
    if (tabTeachers) tabTeachers.style.display = "block";
    if (window.loadAdminTeachers) window.loadAdminTeachers();
  } else if (tabName === "payments") {
    if (btnPayments) { btnPayments.style.background = "var(--teal)"; btnPayments.style.color = "#fff"; btnPayments.style.border = "none"; }
    if (tabPayments) tabPayments.style.display = "block";
  } else if (tabName === "all_users") {
    if (btnAllUsers) { btnAllUsers.style.background = "var(--teal)"; btnAllUsers.style.color = "#fff"; btnAllUsers.style.border = "none"; }
    if (tabAllUsers) tabAllUsers.style.display = "block";
  } else if (tabName === "system") {
    if (btnSystem) { btnSystem.style.background = "var(--teal)"; btnSystem.style.color = "#fff"; btnSystem.style.border = "none"; }
    if (tabSystem) tabSystem.style.display = "block";
  }
};

window.loadAdminDashboard = async function() {
  if (!STATE.token || !STATE.currentUser || STATE.currentUser.role !== "admin") return;

  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${STATE.token}`
  };

  try {
    let adminErrShown = false;
    const adminJson = (r) => {
      if (!r.ok) {
        if (!adminErrShown) {
          adminErrShown = true;
          showToast(`Admin ma'lumotlari yuklanmadi (HTTP ${r.status})`, "error");
        }
        throw new Error("HTTP " + r.status);
      }
      return r.json();
    };
    const [pendingRes, paymentsRes, allUsersRes, teachersRes] = await Promise.all([
      fetch(`${STATE.apiBaseUrl}/admin/pending-users`, { headers }).then(adminJson).catch(() => ({ pending_users: [] })),
      fetch(`${STATE.apiBaseUrl}/admin/payments`, { headers }).then(adminJson).catch(() => ({ payments: [] })),
      fetch(`${STATE.apiBaseUrl}/admin/users`, { headers }).then(adminJson).catch(() => ({ users: [] })),
      fetch(`${STATE.apiBaseUrl}/admin/teachers`, { headers }).then(adminJson).catch(() => ({ teachers: [] }))
    ]);

    const pendingUsers = pendingRes.pending_users || [];
    const payments = paymentsRes.payments || [];
    const allUsers = allUsersRes.users || [];
    const teachers = teachersRes.teachers || [];

    const pendingPayments = payments.filter(p => p.status === "pending");
    const proUsers = allUsers.filter(u => u.subscription_tier === "pro");

    // Statistika kartalarini yangilash
    const statPendingUsers = document.getElementById("adminStatPendingUsers");
    const statTeachers = document.getElementById("adminStatTeachers");
    const statProUsers = document.getElementById("adminStatProUsers");
    const statPendingPayments = document.getElementById("adminStatPendingPayments");
    if (statPendingUsers) statPendingUsers.textContent = `${pendingUsers.length} nafar`;
    if (statTeachers) statTeachers.textContent = `${teachers.length} nafar`;
    if (statProUsers) statProUsers.textContent = `${proUsers.length} nafar`;
    if (statPendingPayments) statPendingPayments.textContent = `${pendingPayments.length} ta`;

    // Badgelarni yangilash
    const badgePending = document.getElementById("adminBadgePending");
    const badgeTeachers = document.getElementById("adminBadgeTeachers");
    const badgePayments = document.getElementById("adminBadgePayments");
    const badgeAllUsers = document.getElementById("adminBadgeAllUsers");
    if (badgePending) badgePending.textContent = pendingUsers.length;
    if (badgeTeachers) badgeTeachers.textContent = teachers.length;
    if (badgePayments) badgePayments.textContent = pendingPayments.length;
    if (badgeAllUsers) badgeAllUsers.textContent = allUsers.length;

    // 1. Yangi arizalar ro'yxatini chiqarish
    window.renderAdminPendingUsers(pendingUsers);

    // 2. To'lovlar ro'yxatini chiqarish
    window.renderAdminPayments(payments);

    // 3. Barcha foydalanuvchilar jadvalini chiqarish
    window.renderAdminAllUsers(allUsers);

    // 4. O'qituvchilar ro'yxatini chiqarish
    window.renderAdminTeachers(teachers);

  } catch (err) {
    console.error("Admin dashboard yuklashda xatolik:", err);
  }
};

window.renderAdminPendingUsers = function(users) {
  const container = document.getElementById("adminPendingUsersList");
  if (!container) return;

  if (users.length === 0) {
    container.innerHTML = `
      <div class="card" style="text-align:center;padding:36px;color:var(--muted)">
        <div style="font-size:36px;margin-bottom:8px">🎉</div>
        <div style="font-size:16px;font-weight:600;color:var(--ink)">Yangi tasdiqlash arizalari mavjud emas</div>
        <div style="font-size:13px;margin-top:4px">Barcha ro'yxatdan o'tgan foydalanuvchilar ko'rib chiqilgan.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = users.map(u => {
    let roleBadge = '<span style="background:var(--surface-2);color:var(--ink);padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600">🎓 Talaba</span>';
    if (u.role === "teacher") {
      roleBadge = '<span style="background:var(--teal-soft);color:var(--teal);padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:700">👩‍🏫 O\'qituvchi</span>';
    } else if (u.role === "researcher") {
      roleBadge = '<span style="background:#EDE9FE;color:#6D28D9;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:700">📊 Tadqiqotchi</span>';
    } else if (u.role === "developer") {
      roleBadge = '<span style="background:#EEF2FF;color:#4338CA;padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:700">💻 Dasturchi (API)</span>';
    }

    return `
      <div class="card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;border-left:4px solid var(--amber)">
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <span style="font-weight:700;font-size:15px;color:var(--ink)">${escapeHtml(u.full_name)}</span>
            ${roleBadge}
            <span style="font-size:11px;color:var(--muted)">${new Date(u.created_at).toLocaleString('uz-UZ')}</span>
          </div>
          <div style="font-size:13px;color:var(--ink-2);line-height:1.5">
            <b>Login / Email:</b> ${escapeHtml(u.email)} · <b>Telefon:</b> ${escapeHtml(u.phone_number || "Ko'rsatilmagan")} · <b>Guruh:</b> ${escapeHtml(u.group_name || "-")}
          </div>
        </div>
        <div style="display:flex;gap:8px">
          <button class="btn-primary" style="background:none;color:var(--clay);border:1px solid var(--clay);font-size:12.5px;padding:6px 14px" onclick="window.rejectUser('${u.id}', ${jsArg(u.full_name)})">
            ✕ Rad etish
          </button>
          <button class="btn-primary" style="background:var(--teal);font-size:12.5px;padding:6px 16px" onclick="window.approveUser('${u.id}', ${jsArg(u.full_name)})">
            ✓ Tasdiqlash (Ruxsat berish)
          </button>
        </div>
      </div>
    `;
  }).join("");
};

window.renderAdminPayments = function(payments) {
  const container = document.getElementById("adminPaymentsList");
  if (!container) return;

  if (payments.length === 0) {
    container.innerHTML = `
      <div class="card" style="text-align:center;padding:36px;color:var(--muted)">
        <div style="font-size:36px;margin-bottom:8px">💳</div>
        <div style="font-size:16px;font-weight:600;color:var(--ink)">Hozircha to'lov arizalari yo'q</div>
        <div style="font-size:13px;margin-top:4px">Foydalanuvchilar PRO obunaga to'lov qilganda shu yerda ko'rinadi.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = payments.map(p => {
    const isPending = p.status === "pending";
    const statusBadge = isPending 
      ? '<span style="background:var(--amber-soft);color:var(--amber);padding:3px 8px;border-radius:10px;font-size:11.5px;font-weight:700">⏳ Tasdiq kutilmoqda</span>'
      : (p.status === "approved" 
          ? '<span style="background:var(--teal-soft);color:var(--teal);padding:3px 8px;border-radius:10px;font-size:11.5px;font-weight:700">✓ Tasdiqlangan (PRO)</span>'
          : '<span style="background:var(--clay-soft);color:var(--clay);padding:3px 8px;border-radius:10px;font-size:11.5px;font-weight:700">✕ Rad etilgan</span>');

    return `
      <div class="card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;border-left:4px solid ${isPending ? 'var(--amber)' : (p.status === 'approved' ? 'var(--teal)' : 'var(--line)')}">
        <div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <span style="font-weight:700;font-size:15px;color:var(--ink)">${escapeHtml(p.user_name || p.user_email)}</span>
            <span style="font-size:12px;font-weight:700;color:var(--teal)">${p.amount.toLocaleString()} $</span>
            ${statusBadge}
            <span style="font-size:11px;color:var(--muted)">${new Date(p.created_at).toLocaleString('uz-UZ')}</span>
          </div>
          <div style="font-size:13px;color:var(--ink-2);line-height:1.5">
            <b>To'lov usuli:</b> ${escapeHtml((p.payment_method || '').toUpperCase())} · <b>Tranzaksiya / Chek ID:</b> <code>${escapeHtml(p.transaction_id || "Kiritilmagan")}</code> · <b>Roli:</b> ${escapeHtml(p.role)}
          </div>
        </div>
        ${isPending ? `
          <div style="display:flex;gap:8px">
            <button class="btn-primary" style="background:none;color:var(--clay);border:1px solid var(--clay);font-size:12.5px;padding:6px 14px" onclick="window.rejectPayment('${p.id}')">
              ✕ Rad etish
            </button>
            <button class="btn-primary" style="background:var(--amber);color:#fff;border:none;font-size:12.5px;padding:6px 16px;font-weight:700" onclick="window.approvePayment('${p.id}', ${jsArg(p.user_name || p.user_email)})">
              👑 Tasdiqlash (PRO ga o'tkazish)
            </button>
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
};

window.renderAdminAllUsers = function(users) {
  const tbody = document.getElementById("adminAllUsersTableBody");
  if (!tbody) return;

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--muted)">Foydalanuvchilar topilmadi</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const isPro = u.subscription_tier === "pro";
    const tierBadge = isPro 
      ? '<span style="background:var(--amber-soft);color:var(--amber);padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:700">👑 PRO</span>'
      : '<span style="background:var(--surface-2);color:var(--muted);padding:2px 8px;border-radius:10px;font-size:11.5px;font-weight:600">FREE</span>';

    const apprBadge = u.is_approved 
      ? '<span style="color:var(--teal);font-weight:600;font-size:12px">✓ Faol</span>'
      : '<span style="color:var(--amber);font-weight:600;font-size:12px">⏳ Tasdiqlanmagan</span>';

    const nextTier = isPro ? "free" : "pro";
    const tierBtnLabel = isPro ? "Free ga o'tkazish" : "👑 PRO berish";

    return `
      <tr style="border-bottom:1px solid var(--line);height:44px">
        <td><b>${escapeHtml(u.full_name || "-")}</b></td>
        <td>${escapeHtml(u.email)}</td>
        <td><span style="font-size:12px;text-transform:capitalize">${escapeHtml(u.role)}</span></td>
        <td>${apprBadge}</td>
        <td>${tierBadge}</td>
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn-primary" style="padding:4px 8px;font-size:11.5px;background:none;border:1px solid var(--line);color:var(--ink)" onclick="window.toggleUserTier('${u.id}', '${nextTier}')">
              ${tierBtnLabel}
            </button>
            <button class="btn-primary" style="padding:4px 8px;font-size:11.5px;background:none;border:1px solid var(--teal);color:var(--teal)" onclick="window.adminResetUserPassword('${u.id}', ${jsArg(u.full_name || '')}, ${jsArg(u.email)})" title="Yangi parol o'rnatish">
              🔑 Parol
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
};

window.adminResetUserPassword = async function(userId, userName, userEmail) {
  if (!STATE.token) return;
  const newPass = prompt(`${userName} (${userEmail}) uchun yangi parol kiriting:\n(Kamida 8 ta belgi)`, "");
  if (!newPass || newPass.trim().length < 8) {
    if (newPass !== null) showToast("Parol kamida 8 belgidan iborat bo'lishi kerak!", "error");
    return;
  }

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/users/${userId}/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({ password: newPass.trim() })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Parol yangilashda xatolik");
    showToast(`✓ ${userName}: Parol yangilandi`, "success");
    window.loadAdminDashboard();
  } catch (err) {
    showToast(err.message || "Xatolik yuz berdi", "error");
  }
};

window.approveUser = async function(userId, userName) {
  if (!STATE.token) return;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/users/${userId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Tasdiqlashda xatolik");

    showToast(`✓ ${userName || 'Foydalanuvchi'} tasdiqlandi! Endi tizimga kira oladi.`, "success");
    window.loadAdminDashboard();
  } catch (err) {
    showToast(err.message || "Tasdiqlashda xatolik", "error");
  }
};

window.rejectUser = async function(userId, userName) {
  if (!STATE.token) return;
  if (!confirm(`${userName || 'Ushbu foydalanuvchi'} arizasini rad etib, o'chirmoqchimisiz?`)) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/users/${userId}/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Rad etishda xatolik");

    showToast("Arizachi rad etildi va o'chirildi.", "info");
    window.loadAdminDashboard();
  } catch (err) {
    showToast(err.message || "Rad etishda xatolik", "error");
  }
};

window.approvePayment = async function(paymentId, userName) {
  if (!STATE.token) return;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/payments/${paymentId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "To'lovni tasdiqlashda xatolik");

    showToast(`👑 ${userName || 'Foydalanuvchi'} uchun to'lov tasdiqlandi va PRO tarif faollashtirildi!`, "success");
    window.loadAdminDashboard();
  } catch (err) {
    showToast(err.message || "To'lovni tasdiqlashda xatolik", "error");
  }
};

window.rejectPayment = async function(paymentId) {
  if (!STATE.token) return;
  if (!confirm("Ushbu to'lov arizasini rad etmoqchimisiz?")) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/payments/${paymentId}/reject`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Rad etishda xatolik");

    showToast("To'lov arizasi rad etildi.", "info");
    window.loadAdminDashboard();
  } catch (err) {
    showToast(err.message || "Rad etishda xatolik", "error");
  }
};

window.toggleUserTier = async function(userId, targetTier) {
  if (!STATE.token) return;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/users/${userId}/set-tier`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({ tier: targetTier })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Tarifni o'zgartirishda xatolik");

    showToast(`Tarif ${targetTier.toUpperCase()} ga o'zgartirildi!`, "success");
    window.loadAdminDashboard();
  } catch (err) {
    showToast(err.message || "Xatolik yuz berdi", "error");
  }
};

// =========================================================================
// SUPER ADMIN O'QITUVCHILARNI BOSHQARISH VA YARATISH FUNKSIYALARI
// =========================================================================

window.loadAdminTeachers = async function() {
  if (!STATE.token) return;
  const tbody = document.getElementById("adminTeachersTableBody");
  if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:20px;color:var(--muted)">O'qituvchilar yuklanmoqda...</td></tr>`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/teachers`, {
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      }
    });
    const data = await res.json();
    const teachers = data.teachers || [];
    window.renderAdminTeachers(teachers);

    const statTeachers = document.getElementById("adminStatTeachers");
    const badgeTeachers = document.getElementById("adminBadgeTeachers");
    if (statTeachers) statTeachers.textContent = `${teachers.length} nafar`;
    if (badgeTeachers) badgeTeachers.textContent = teachers.length;
  } catch (err) {
    console.error("O'qituvchilarni yuklashda xatolik:", err);
  }
};

window.renderAdminTeachers = function(teachers) {
  const tbody = document.getElementById("adminTeachersTableBody");
  if (!tbody) return;

  if (!teachers || teachers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:20px;color:var(--muted)">Hozircha o'qituvchilar mavjud emas. Yuqoridagi forma orqali yangi o'qituvchi yarating.</td></tr>`;
    return;
  }

  tbody.innerHTML = teachers.map(t => {
    const isPro = t.subscription_tier === "pro";
    const tierBadge = isPro 
      ? '<span style="background:var(--amber-soft);color:var(--amber);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">👑 PRO</span>'
      : '<span style="background:var(--surface-2);color:var(--muted);padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">FREE</span>';

    const subjectsStr = (t.subjects && t.subjects.length > 0)
      ? t.subjects.map(s => `<span style="background:var(--teal-soft);color:var(--teal);padding:2px 6px;border-radius:6px;font-size:11.5px;font-weight:600;display:inline-block;margin:1px 2px">${escapeHtml(s.name)}</span>`).join("")
      : '<span style="color:var(--muted);font-size:12px">Fan biriktirilmagan</span>';

    return `
      <tr style="border-bottom:1px solid var(--line);height:44px">
        <td><b>${escapeHtml(t.full_name || "-")}</b></td>
        <td><code>${escapeHtml(t.email)}</code></td>
        <td>${escapeHtml(t.phone_number || "-")}</td>
        <td>${subjectsStr}</td>
        <td>${tierBadge}</td>
        <td><span style="color:var(--teal);font-weight:600;font-size:12px">✓ Faol</span></td>
        <td>
          <button class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:none;border:1px solid var(--clay);color:var(--clay)" onclick="window.deleteTeacher('${t.id}', ${jsArg(t.full_name)})">
            🗑 O'chirish
          </button>
        </td>
      </tr>
    `;
  }).join("");
};

window.handleCreateTeacherSubmit = async function() {
  const fullName = document.getElementById("admTeachFullName")?.value.trim();
  const email = document.getElementById("admTeachEmail")?.value.trim();
  const password = document.getElementById("admTeachPassword")?.value.trim();
  const subjectName = document.getElementById("admTeachSubject")?.value.trim() || "";
  const phoneNumber = document.getElementById("admTeachPhone")?.value.trim() || "";
  const tier = document.getElementById("admTeachTier")?.value || "pro";
  const msgBox = document.getElementById("admTeachMsg");
  const submitBtn = document.getElementById("btnAdminCreateTeacher");

  if (!fullName || !email || !password) {
    if (msgBox) {
      msgBox.textContent = "Iltimos, o'qituvchining F.I.Sh, login/email va parolini kiriting.";
      msgBox.style.display = "block";
      msgBox.style.background = "var(--clay-soft)";
      msgBox.style.color = "var(--clay)";
      msgBox.style.border = "1px solid var(--clay)";
    }
    return;
  }

  if (password.length < 6) {
    if (msgBox) {
      msgBox.textContent = "Parol kamida 6 ta belgidan iborat bo'lishi kerak.";
      msgBox.style.display = "block";
      msgBox.style.background = "var(--clay-soft)";
      msgBox.style.color = "var(--clay)";
      msgBox.style.border = "1px solid var(--clay)";
    }
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Yaratilmoqda...";
  }

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/teachers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      },
      body: JSON.stringify({
        full_name: fullName,
        email: email,
        password: password,
        subject_name: subjectName,
        phone_number: phoneNumber,
        subscription_tier: tier,
        institution_id: "inst_buxdu"
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "O'qituvchi yaratishda xatolik yuz berdi");
    }

    if (msgBox) {
      msgBox.textContent = `✓ O'qituvchi ${fullName} muvaffaqiyatli yaratildi va hisob faollashtirildi! Login: ${data.teacher?.email || email}`;
      msgBox.style.display = "block";
      msgBox.style.background = "var(--teal-soft)";
      msgBox.style.color = "var(--teal)";
      msgBox.style.border = "1px solid var(--teal)";
    }

    showToast(`O'qituvchi ${fullName} muvaffaqiyatli yaratildi!`, "success");

    // Formani tozalash
    const fnInput = document.getElementById("admTeachFullName");
    const emInput = document.getElementById("admTeachEmail");
    const pwInput = document.getElementById("admTeachPassword");
    const sbInput = document.getElementById("admTeachSubject");
    const phInput = document.getElementById("admTeachPhone");
    if (fnInput) fnInput.value = "";
    if (emInput) emInput.value = "";
    if (pwInput) pwInput.value = "";
    if (sbInput) sbInput.value = "";
    if (phInput) phInput.value = "";

    // Ro'yxatni va statistikani yangilash
    window.loadAdminDashboard();
    window.loadAdminTeachers();

  } catch (err) {
    if (msgBox) {
      msgBox.textContent = err.message || "Xatolik yuz berdi";
      msgBox.style.display = "block";
      msgBox.style.background = "var(--clay-soft)";
      msgBox.style.color = "var(--clay)";
      msgBox.style.border = "1px solid var(--clay)";
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "✨ Yangi O'qituvchi Yaratish";
    }
  }
};

window.deleteTeacher = async function(teacherId, teacherName) {
  if (!STATE.token) return;
  if (!confirm(`Haqiqatan ham o'qituvchi ${teacherName || ''} hisobini o'chirmoqchimisiz?`)) return;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/admin/teachers/${teacherId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${STATE.token}`
      }
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "O'chirishda xatolik");

    showToast(`O'qituvchi hisobi o'chirildi.`, "info");
    window.loadAdminDashboard();
    window.loadAdminTeachers();
  } catch (err) {
    showToast(err.message || "O'chirishda xatolik", "error");
  }
};


// =========================================================================
// TALABALAR UCHUN FANLAR, TESTLAR VA SLAYDLAR MODULI
// =========================================================================

STATE.studentSubjects = [];
STATE.studentMaterials = [];
STATE.studentSubjectFilter = "all";
STATE.studentMaterialTypeFilter = "all";
STATE.currentStudentTest = null;
STATE.studentTestAnswers = {};
STATE.studentPresentation = null;
STATE.studentSlideIndex = 0;

// 1. Fanlar va materiallarni serverdan yuklash
// ==================== O'QITUVCHI / ADMIN: "MUSTAQIL TOPSHIRIQLAR" EKRANIDAN MATERIAL YARATISH ====================
// Talaba ekranida (s_student_materials) o'qituvchi yoki admin fan uchun to'g'ridan-to'g'ri
// test / slayd / yozma mashg'ulot / dars rejasi yaratishga o'tadi: AI generator (s_subjects)
// tanlangan fan va material turi bilan oldindan to'ldiriladi.
window.MATERIAL_CREATOR_TYPES = [
  { type: "test", icon: "📝", uz: "Test", en: "Test", ru: "Тест" },
  { type: "presentation", icon: "🖥️", uz: "Slayd", en: "Slides", ru: "Слайды" },
  { type: "writing", icon: "✍️", uz: "Yozma mashg'ulot", en: "Writing task", ru: "Письменное задание" },
  { type: "lesson_plan", icon: "📄", uz: "Dars rejasi", en: "Lesson plan", ru: "План урока" }
];

window.canCreateMaterials = function() {
  const role = STATE.currentUser ? STATE.currentUser.role : "guest";
  return role === "teacher" || role === "admin";
};

// O'qituvchi faqat o'z fanlari uchun, admin barcha fanlar uchun yarata oladi
window.canCreateForSubject = function(subj) {
  if (!window.canCreateMaterials() || !subj) return false;
  if (STATE.currentUser.role === "admin") return true;
  return !subj.teacher_id || String(subj.teacher_id) === String(STATE.currentUser.id);
};

// Fan kartasi / banner uchun "➕ Yaratish: Test · Slayd · Yozma · Reja" tugmalari
window.materialCreatorButtonsHtml = function(subj, mode) {
  if (!window.canCreateForSubject(subj)) return "";
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const head = lang === "ru" ? "➕ Создать:" : (lang === "en" ? "➕ Create:" : "➕ Yaratish:");
  const btns = window.MATERIAL_CREATOR_TYPES.map(t =>
    `<button type="button" class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--surface);color:var(--teal);border:1px solid var(--teal)" onclick="event.stopPropagation();window.openMaterialCreator('${escapeHtml(subj.id)}','${t.type}')">${t.icon} ${t[lang] || t.uz}</button>`
  ).join("");
  const extra = mode === "card" ? "padding-top:8px;border-top:1px dashed var(--line);" : "";
  const upLabel = lang === "ru" ? "Загрузить файл" : (lang === "en" ? "Upload file" : "Fayl yuklash");
  const upBtn = `<button type="button" class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:var(--amber-soft);color:var(--amber);border:1px solid var(--amber)" onclick="event.stopPropagation();window.openUploadMaterialModal('${escapeHtml(subj.id)}','test')" title="Tayyor test yoki slayd faylini yuklash">⬆️ ${upLabel}</button>`;
  return `<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;${extra}"><span style="font-size:11.5px;font-weight:700;color:var(--muted)">${head}</span>${btns}${upBtn}</div>`;
};

// Sarlavhadagi "✨ Material yaratish" tugmasi faqat o'qituvchi/admin uchun ko'rinadi
window.updateMaterialCreatorButton = function() {
  const btn = document.getElementById("smCreateBtn");
  if (!btn) return;
  const ok = window.canCreateMaterials();
  btn.style.display = ok ? "flex" : "none";
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const label = btn.querySelector("[data-creator-label]");
  if (label) label.textContent = lang === "ru" ? "Создать материал" : (lang === "en" ? "Create material" : "Material yaratish");
};

window.openMaterialCreator = async function(subjectId, materialType) {
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  if (!window.canCreateMaterials()) {
    showToast(lang === "ru" ? "Создавать материалы могут только преподаватель или администратор." : (lang === "en" ? "Only a teacher or admin can create materials." : "Material yaratish faqat o'qituvchi yoki admin uchun."), "error");
    return;
  }
  // Fan berilmagan bo'lsa, hozir tanlangan fan filtri olinadi
  if (!subjectId && STATE.studentSubjectFilter && STATE.studentSubjectFilter !== "all") {
    subjectId = STATE.studentSubjectFilter;
  }
  const subj = (STATE.studentSubjects || []).find(s => String(s.id) === String(subjectId));
  if (subj && !window.canCreateForSubject(subj)) {
    showToast(lang === "ru" ? "Этот предмет принадлежит другому преподавателю." : (lang === "en" ? "This course belongs to another teacher." : "Bu fan boshqa o'qituvchiga tegishli — faqat o'z fanlaringiz uchun material yaratishingiz mumkin."), "error");
    return;
  }

  // Generator ekraniga o'tish va fanlar ro'yxatini (dropdown) to'ldirib olish
  showScreen("s_subjects");
  if (typeof window.loadTeacherSubjects === "function") await window.loadTeacherSubjects();
  if (subjectId && !(STATE.teacherSubjects || []).some(s => String(s.id) === String(subjectId))) {
    showToast(lang === "ru" ? "Предмет не найден в списке генератора." : (lang === "en" ? "Course not found in the generator list." : "Fan generator ro'yxatida topilmadi, fanni qo'lda tanlang."), "error");
    subjectId = "";
  }
  await window.prepareGenerateForTopic(subjectId || "", "", materialType || "test");

  const t = window.MATERIAL_CREATOR_TYPES.find(x => x.type === (materialType || "test"));
  const typeName = t ? (t[lang] || t.uz) : "";
  const subjName = subj ? (subj.title || subj.name) : "";
  const msg = lang === "ru"
    ? `✨ Генератор готов: ${typeName}${subjName ? " · " + subjName : ""}. Выберите тему и нажмите «Создать».`
    : (lang === "en"
      ? `✨ Generator ready: ${typeName}${subjName ? " · " + subjName : ""}. Pick a topic and press Generate.`
      : `✨ Generator tayyor: ${typeName}${subjName ? " · " + subjName : ""}. Mavzuni tanlab "Tayyorlash" tugmasini bosing.`);
  showToast(msg, "success");
};

window.loadStudentSubjectsAndMaterials = async function() {
  const grid = document.getElementById("studentMaterialsGrid");
  const countBadge = document.getElementById("studentMaterialsCountBadge");
  const select = document.getElementById("studentSubjectFilterSelect");
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  window.updateMaterialCreatorButton();

  if (grid) {
    const loadingText = lang === "ru" ? "Загрузка учебных предметов и материалов..." : (lang === "en" ? "Loading courses and learning materials..." : "O'quv fanlari va materiallar yuklanmoqda...");
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--muted)">
        <div style="font-size:32px;margin-bottom:8px">⏳</div>
        <div>${loadingText}</div>
      </div>
    `;
  }

  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  try {
    // 1. Fanlar ro'yxatini yuklash
    const subjRes = await fetch(`${STATE.apiBaseUrl}/student/subjects`, { headers });
    if (subjRes.ok) {
      const subjData = await subjRes.json();
      STATE.studentSubjects = subjData.subjects || [];

      if (select) {
        const selectDefault = lang === "ru" ? "📂 Список предметов (выберите предмет)" : (lang === "en" ? "📂 Course list (select a course)" : "📂 Fanlar ro'yxati (fanni tanlang)");
        let optHtml = `<option value="all">${selectDefault}</option>`;
        STATE.studentSubjects.forEach(s => {
          let matCount = "";
          if (s.materials_count) {
            matCount = lang === "ru" ? ` (${s.materials_count} материалов)` : (lang === "en" ? ` (${s.materials_count} materials)` : ` (${s.materials_count} ta material)`);
          }
          const subjFallback = lang === "ru" ? "Предмет" : (lang === "en" ? "Course" : "Fan");
          optHtml += `<option value="${escapeHtml(s.id)}">${escapeHtml(s.title)} [${escapeHtml(s.code || s.semester || subjFallback)}]${matCount}</option>`;
        });
        select.innerHTML = optHtml;
        if (STATE.studentSubjectFilter) {
          select.value = STATE.studentSubjectFilter;
        }
      }
      window.renderStudentSubjectCards();
    }

    // 2. Materiallarni yuklash
    await window.loadStudentMaterials();
    window.onStudentSubjectFilterChange(true);
  } catch (err) {
    console.error("Talaba materiallarini yuklashda xatolik:", err);
    if (grid) {
      const retryBtn = lang === "ru" ? "Повторить" : (lang === "en" ? "Retry" : "Qaytadan urinish");
      const errPrefix = lang === "ru" ? "Ошибка при загрузке материалов:" : (lang === "en" ? "Error loading materials:" : "Materiallarni yuklashda xatolik yuz berdi:");
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--clay);background:var(--surface-2);border-radius:10px">
          <div>⚠️ ${errPrefix} ${err.message || 'Server bilan aloqa uzildi'}</div>
          <button class="btn-primary" style="margin-top:10px;padding:6px 14px" onclick="window.loadStudentSubjectsAndMaterials()">${retryBtn}</button>
        </div>
      `;
    }
  }
};

// 2. Tanlangan filtrlar bo'yicha materiallarni olish
window.loadStudentMaterials = async function() {
  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  let url = `${STATE.apiBaseUrl}/student/materials`;
  const params = [];
  if (STATE.studentSubjectFilter && STATE.studentSubjectFilter !== "all") {
    params.push(`subject_id=${STATE.studentSubjectFilter}`);
  }
  if (STATE.studentMaterialTypeFilter && STATE.studentMaterialTypeFilter !== "all") {
    params.push(`material_type=${STATE.studentMaterialTypeFilter}`);
  }
  if (params.length > 0) {
    url += `?${params.join("&")}`;
  }

  try {
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error("Materiallarni yuklab bo'lmadi");
    const data = await res.json();
    STATE.studentMaterials = data.materials || [];

    // Hisoblagichlarni yangilash
    window.updateStudentMaterialCounters();

    // Ekranga chiqarish
    window.filterStudentMaterialsDisplay();
  } catch (err) {
    console.error("Materiallarni olishda xatolik:", err);
    throw err;
  }
};

// 3. Tab hisoblagichlarini hisoblash
window.updateStudentMaterialCounters = function() {
  const all = STATE.studentMaterials;
  const countAll = all.length;
  let testCount = 0;
  let presCount = 0;
  let planCount = 0;
  let writingCount = 0;

  all.forEach(m => {
    if (m.material_type === "test") testCount++;
    else if (m.material_type === "presentation") presCount++;
    else if (m.material_type === "lesson_plan") planCount++;
    else if (m.material_type === "writing") writingCount++;
  });
  const elWriting = document.getElementById("smCountWriting");
  if (elWriting) elWriting.textContent = writingCount;

  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const badgeEl = document.getElementById("studentMaterialsCountBadge");
  if (badgeEl) {
    const unit = lang === "ru" ? "материалов" : (lang === "en" ? "materials" : "ta material");
    badgeEl.textContent = `${countAll} ${unit}`;
  }

  const elAll = document.getElementById("smCountAll");
  const elTest = document.getElementById("smCountTest");
  const elPres = document.getElementById("smCountPresentation");
  const elPlan = document.getElementById("smCountPlan");

  if (elAll) elAll.textContent = countAll;
  if (elTest) elTest.textContent = testCount;
  if (elPres) elPres.textContent = presCount;
  if (elPlan) elPlan.textContent = planCount;
};

// 4. Fan filtri o'zgarganda
// Fan kartalari: talaba avval fanni tanlaydi
window.renderStudentSubjectCards = function() {
  const grid = document.getElementById("studentSubjectsGrid");
  if (!grid) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const subs = STATE.studentSubjects || [];
  if (subs.length === 0) {
    const emptySubj = lang === "ru" ? "📂 Для вашей группы пока нет открытых предметов." : (lang === "en" ? "📂 No courses available for your group yet." : "📂 Sizning guruhingiz uchun hali fan ochilmagan.");
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--muted);background:var(--surface-2);border-radius:12px;border:1px dashed var(--line)">${emptySubj}</div>`;
    return;
  }
  grid.innerHTML = subs.map(s => {
    const c = s.counts || {};
    const total = s.materials_count || 0;
    const done = s.done_count || 0;
    const pct = s.progress_percent || 0;
    const topicsWord = lang === "ru" ? "тем" : (lang === "en" ? "topics" : "ta mavzu");
    const testWord = lang === "ru" ? "тестов" : (lang === "en" ? "tests" : "test");
    const presWord = lang === "ru" ? "слайдов" : (lang === "en" ? "slides" : "slayd");
    const writWord = lang === "ru" ? "письм." : (lang === "en" ? "writing" : "yozma");
    const planWord = lang === "ru" ? "планов" : (lang === "en" ? "plans" : "reja");
    const doneWord = lang === "ru" ? "Выполнено" : (lang === "en" ? "Completed" : "Bajarilgan");
    const btnOpen = lang === "ru" ? "Открыть задания →" : (lang === "en" ? "Open Tasks →" : "Topshiriqlarni ochish →");
    const subjFallback = lang === "ru" ? "ПРЕДМЕТ" : (lang === "en" ? "COURSE" : "FAN");

    return `
      <div class="card" style="padding:18px;border-radius:12px;cursor:pointer;display:flex;flex-direction:column;gap:10px" onclick="window.selectStudentSubject('${s.id}')">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
          <span class="chip full" style="font-size:11px">${escapeHtml(s.code || s.semester || subjFallback)}</span>
          <span style="font-size:11px;color:var(--muted)">${escapeHtml(s.group_name || "")}</span>
        </div>
        <h4 style="margin:0;font-size:16px;font-family:var(--serif);line-height:1.35">${escapeHtml(s.title || s.name)}</h4>
        <div style="font-size:12px;color:var(--muted)">👤 ${escapeHtml(s.teacher_name || "")} · ${s.topics_count || 0} ${topicsWord}</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:11.5px">
          <span style="padding:2px 8px;border-radius:6px;background:rgba(13,110,110,0.12);color:var(--teal)">📝 ${c.test || 0} ${testWord}</span>
          <span style="padding:2px 8px;border-radius:6px;background:rgba(79,70,229,0.12);color:#4F46E5">🖥️ ${c.presentation || 0} ${presWord}</span>
          <span style="padding:2px 8px;border-radius:6px;background:rgba(180,83,9,0.12);color:var(--amber)">✍️ ${c.writing || 0} ${writWord}</span>
          <span style="padding:2px 8px;border-radius:6px;background:var(--surface-2);color:var(--ink-2)">📄 ${c.lesson_plan || 0} ${planWord}</span>
        </div>
        ${window.materialCreatorButtonsHtml(s, "card")}
        <div>
          <div style="display:flex;justify-content:space-between;font-size:11.5px;color:var(--muted);margin-bottom:3px"><span>${doneWord}</span><span>${done}/${total} (${pct}%)</span></div>
          <div style="height:6px;border-radius:4px;background:var(--surface-2);overflow:hidden"><div style="height:100%;width:${pct}%;background:var(--teal)"></div></div>
        </div>
        <button class="btn-primary" style="padding:8px 12px;font-size:13px;font-weight:700">${btnOpen}</button>
      </div>`;
  }).join("");
};

window.selectStudentSubject = function(subjectId) {
  const select = document.getElementById("studentSubjectFilterSelect");
  if (select) select.value = subjectId;
  window.onStudentSubjectFilterChange();
};

window.onStudentSubjectFilterChange = function(silent) {
  const select = document.getElementById("studentSubjectFilterSelect");
  if (!select) return;
  STATE.studentSubjectFilter = select.value;
  const subjectsGrid = document.getElementById("studentSubjectsGrid");
  const materialsGrid = document.getElementById("studentMaterialsGrid");
  const subjectMode = !STATE.studentSubjectFilter || STATE.studentSubjectFilter === "all";
  if (subjectsGrid) subjectsGrid.style.display = subjectMode ? "grid" : "none";
  if (materialsGrid) materialsGrid.style.display = subjectMode ? "none" : "grid";

  const banner = document.getElementById("studentSelectedSubjectBanner");
  const stSubjTitle = document.getElementById("stSubjTitle");
  const stSubjDesc = document.getElementById("stSubjDesc");
  const stSubjBadge = document.getElementById("stSubjBadge");
  const stSubjTopicCount = document.getElementById("stSubjTopicCount");
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";

  if (STATE.studentSubjectFilter !== "all") {
    const subj = STATE.studentSubjects.find(s => String(s.id) === String(STATE.studentSubjectFilter));
    if (subj && banner) {
      banner.style.display = "block";
      if (stSubjTitle) stSubjTitle.textContent = subj.title;
      const defaultDesc = lang === "ru" ? "По этому предмету подготовлен силлабус и учебные материалы ИИ." : (lang === "en" ? "Syllabus and AI materials are ready for this course." : "Ushbu fan bo'yicha sillabus va AI materiallari tayyorlangan.");
      if (stSubjDesc) stSubjDesc.textContent = subj.description || defaultDesc;
      if (stSubjBadge) stSubjBadge.textContent = subj.code || subj.semester || (lang === "ru" ? "ПРЕДМЕТ" : (lang === "en" ? "COURSE" : "FAN"));
      const topicsSuffix = lang === "ru" ? "плановых тем" : (lang === "en" ? "scheduled topics" : "ta rejaviy mavzu");
      if (stSubjTopicCount) stSubjTopicCount.textContent = `${subj.topics_count || (subj.topics || []).length} ${topicsSuffix}`;
      const prog = document.getElementById("stSubjProgress");
      const doneLabel = lang === "ru" ? "Выполнено" : (lang === "en" ? "Completed" : "Bajarilgan");
      if (prog) prog.textContent = STATE.token ? `${doneLabel}: ${subj.done_count || 0}/${subj.materials_count || 0} (${subj.progress_percent || 0}%)` : "";
      // O'qituvchi / admin: shu fan uchun material yaratish tugmalari
      const createBox = document.getElementById("stSubjCreateBox");
      if (createBox) {
        const html = window.materialCreatorButtonsHtml(subj, "banner");
        createBox.innerHTML = html;
        createBox.style.display = html ? "block" : "none";
      }
    }
  } else {
    if (banner) banner.style.display = "none";
  }

  if (silent === true) return;
  window.loadStudentMaterials();
};

// 5. Material turi bo'yicha filtr (Tablar)
window.setStudentMaterialTypeFilter = function(type) {
  STATE.studentMaterialTypeFilter = type;

  const tabs = [
    { id: "smTabAll", key: "all" },
    { id: "smTabTest", key: "test" },
    { id: "smTabPresentation", key: "presentation" },
    { id: "smTabWriting", key: "writing" },
    { id: "smTabPlan", key: "lesson_plan" }
  ];

  tabs.forEach(t => {
    const btn = document.getElementById(t.id);
    if (!btn) return;
    if (t.key === type) {
      btn.style.background = "var(--teal)";
      btn.style.color = "#fff";
      btn.style.border = "none";
    } else {
      btn.style.background = "none";
      btn.style.color = "var(--ink)";
      btn.style.border = "1px solid var(--line)";
    }
  });

  window.loadStudentMaterials();
};

// 6. Qidiruv va kartalarni chizish
window.filterStudentMaterialsDisplay = function() {
  const grid = document.getElementById("studentMaterialsGrid");
  if (!grid) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";

  const searchInput = document.getElementById("studentMaterialSearchInput");
  const query = (searchInput ? searchInput.value : "").trim().toLowerCase();

  let list = STATE.studentMaterials;

  if (query) {
    list = list.filter(m => {
      const titleMatch = (m.title || "").toLowerCase().includes(query);
      const topicMatch = (m.topic_title || "").toLowerCase().includes(query);
      const subjMatch = (m.subject_title || "").toLowerCase().includes(query);
      return titleMatch || topicMatch || subjMatch;
    });
  }

  if (list.length === 0) {
    const emptyTitle = lang === "ru" ? "Учебные материалы не найдены" : (lang === "en" ? "No learning materials found" : "Hech qanday o'quv materiali topilmadi");
    let emptyDesc = "";
    if (query) {
      emptyDesc = lang === "ru" ? "По вашему запросу ничего не найдено." : (lang === "en" ? "No materials match your search query." : "Qidiruv bo'yicha mos material yo'q.");
    } else {
      emptyDesc = lang === "ru" ? "Преподаватель ещё не создал тесты или слайды по этому предмету." : (lang === "en" ? "The instructor has not created tests or slides for this course yet." : "O'qituvchi hali bu fan bo'yicha test yoki slaydlar yaratmagan.");
    }

    // O'qituvchi / admin uchun bo'sh holatda ham yaratish tugmalari ko'rsatiladi
    const curSubj = (STATE.studentSubjects || []).find(s => String(s.id) === String(STATE.studentSubjectFilter));
    const createHtml = curSubj ? window.materialCreatorButtonsHtml(curSubj, "empty") : "";

    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:50px 20px;background:var(--surface-2);border-radius:12px;border:1px dashed var(--line)">
        <div style="font-size:40px;margin-bottom:10px">📂</div>
        <h4 style="margin:0 0 6px;font-size:16px;color:var(--ink)">${emptyTitle}</h4>
        <p style="margin:0;font-size:13px;color:var(--muted)">${emptyDesc}</p>
        ${createHtml ? `<div style="display:flex;justify-content:center;margin-top:14px">${createHtml}</div>` : ""}
      </div>
    `;
    return;
  }

  grid.innerHTML = list.map(m => {
    const isTest = m.material_type === "test";
    const isPres = m.material_type === "presentation";
    const isPlan = m.material_type === "lesson_plan";
    const isWriting = m.material_type === "writing";

    let icon = "📄";
    let typeName = lang === "ru" ? "План урока" : (lang === "en" ? "Lesson Plan" : "Dars rejasi");
    let typeColor = "var(--amber)";
    let typeBg = "rgba(180,83,9,0.12)";

    const at = m.attempt;
    let statusHtml = "";
    if (at && at.status === "completed" && at.best_score !== null && at.best_score !== undefined) {
      const attWord = lang === "ru" ? "попытки" : (lang === "en" ? "attempts" : "urinish");
      statusHtml = `<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:${at.passed ? 'rgba(21,128,61,0.12)' : 'rgba(185,28,28,0.12)'};color:${at.passed ? '#15803D' : '#B91C1C'}">✅ ${at.best_score}%${at.attempts > 1 ? ` · ${at.attempts} ${attWord}` : ""}</span>`;
    } else if (at && at.status === "viewed") {
      const viewedLabel = lang === "ru" ? "👁️ Просмотрено" : (lang === "en" ? "👁️ Viewed" : "👁️ Ko'rilgan");
      statusHtml = `<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:var(--surface-2);color:var(--ink-2)">${viewedLabel}</span>`;
    } else if (STATE.token) {
      const pendingLabel = lang === "ru" ? "⏳ Не выполнено" : (lang === "en" ? "⏳ Pending" : "⏳ Bajarilmagan");
      statusHtml = `<span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:rgba(180,83,9,0.10);color:var(--amber)">${pendingLabel}</span>`;
    }

    if (isWriting) {
      icon = "✍️";
      typeName = lang === "ru" ? "Письменное задание" : (lang === "en" ? "Writing Task" : "Yozma mashg'ulot");
      typeColor = "#B45309";
      typeBg = "rgba(180,83,9,0.14)";
    } else if (isTest) {
      icon = "📝";
      typeName = lang === "ru" ? "Контрольный тест" : (lang === "en" ? "Assessment Test" : "Nazorat Testi");
      typeColor = "var(--teal)";
      typeBg = "rgba(13,110,110,0.12)";
    } else if (isPres) {
      icon = "🖥️";
      typeName = lang === "ru" ? "Презентация (Слайды)" : (lang === "en" ? "Presentation (Slides)" : "Taqdimot (Slaydlar)");
      typeColor = "#4F46E5";
      typeBg = "rgba(79,70,229,0.12)";
    }

    const dateLocale = lang === "ru" ? 'ru-RU' : (lang === "en" ? 'en-US' : 'uz-UZ');
    const createdDate = m.created_at ? new Date(m.created_at).toLocaleDateString(dateLocale) : "";
    const courseFallback = lang === "ru" ? "Предмет" : (lang === "en" ? "Course" : "Fan");
    const matFallback = lang === "ru" ? "Учебный материал" : (lang === "en" ? "Learning Material" : "O'quv materiali");
    const topicWord = lang === "ru" ? "Тема" : (lang === "en" ? "Topic" : "Mavzu");
    const generalTopic = lang === "ru" ? "Общая тема" : (lang === "en" ? "General Topic" : "Umumiy reja");

    // Action button labels
    const btnRetakeTest = lang === "ru" ? "Пересдать" : (lang === "en" ? "Retake" : "Qayta ishlash");
    const btnTakeTest = lang === "ru" ? "Пройти тест" : (lang === "en" ? "Take Test" : "Testni topshirish");
    const btnRewrite = lang === "ru" ? "Переписать" : (lang === "en" ? "Rewrite" : "Qayta yozish");
    const btnStartWriting = lang === "ru" ? "Начать задание" : (lang === "en" ? "Start Writing" : "Yozishni boshlash");
    const btnViewPres = lang === "ru" ? "Смотреть" : (lang === "en" ? "View" : "Ko'rish");
    const btnDownloadPres = lang === "ru" ? "Скачать" : (lang === "en" ? "Download" : "Yuklab olish");
    // O'qituvchi yuklagan asl fayl (.docx/.pdf/.pptx): talaba yuklab oladi; savol/slayd ajratilmagan bo'lsa faqat fayl
    const mContent = m.content || m.content_json || {};
    const fileUrl = mContent.file_url || "";
    const fileName = mContent.file_name || "";
    const hasItems = (m.items_count || 0) > 0;
    const btnFile = lang === "ru" ? "Скачать файл" : (lang === "en" ? "Download file" : "Faylni yuklab olish");
    const btnReadPlan = lang === "ru" ? "Читать план" : (lang === "en" ? "Read Plan" : "Rejani o'qish");

    return `
      <div class="card" style="display:flex;flex-direction:column;justify-content:space-between;padding:18px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04);transition:transform 0.15s, box-shadow 0.15s">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px">
            <span style="font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;background:${typeBg};color:${typeColor};display:inline-flex;align-items:center;gap:4px">
              <span>${icon}</span> <span>${typeName}</span>
            </span>
            <span style="display:flex;gap:6px;align-items:center">${statusHtml}<span style="font-size:11px;color:var(--muted);white-space:nowrap">${createdDate}</span></span>
          </div>

          <div style="font-size:11.5px;color:var(--muted);font-weight:600;margin-bottom:4px">
            📖 ${escapeHtml(m.subject_title || courseFallback)}
          </div>

          <h4 style="margin:0 0 8px;font-size:15.5px;font-family:var(--serif);color:var(--ink);line-height:1.35">
            ${escapeHtml(m.title || matFallback)}
          </h4>

          <div style="font-size:12.5px;color:var(--ink-2);margin-bottom:14px;background:var(--surface-2);padding:8px 10px;border-radius:8px">
            <b>${topicWord}:</b> ${escapeHtml(m.topic_title || generalTopic)}
          </div>
        </div>

        <div style="border-top:1px solid var(--line-2);padding-top:12px;display:flex;gap:8px;flex-wrap:wrap">
          ${isTest && hasItems ? `
            <button class="btn-primary" style="flex:1;padding:8px 14px;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:6px" onclick="window.startStudentTest('${m.id}')">
              <span>${at && at.status === "completed" ? "🔄" : "▶️"}</span> <span>${at && at.status === "completed" ? btnRetakeTest : btnTakeTest}</span>
            </button>
          ` : ''}

          ${fileUrl ? `
            <button class="btn-primary" style="${(isTest || isPres) && hasItems ? "" : "flex:1;"}padding:8px 12px;font-size:12.5px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;gap:5px" onclick="window.downloadMaterialFile('${m.id}','${escapeHtml(fileUrl)}')" title="${escapeHtml(fileName)}">
              <span>📎</span> <span>${btnFile}</span>
            </button>
          ` : ''}

          ${isWriting ? `
            <button class="btn-primary" style="flex:1;padding:8px 14px;font-size:13px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:6px" onclick="window.startStudentWriting('${m.id}')">
              <span>✍️</span> <span>${at && at.status === "completed" ? btnRewrite : btnStartWriting}</span>
            </button>
          ` : ''}

          ${isPres && hasItems ? `
            <button class="btn-primary" style="flex:1;padding:8px 12px;font-size:12.5px;display:flex;align-items:center;justify-content:center;gap:5px" onclick="window.viewStudentPresentation('${m.id}')">
              <span>👁️</span> <span>${btnViewPres}</span>
            </button>
            <button class="btn-primary" style="padding:8px 12px;font-size:12.5px;background:#15803D;color:#fff;border:none;font-weight:700;display:flex;align-items:center;gap:5px" onclick="window.downloadPresentationById('${m.id}')" title="Slaydni oflayn HTML/PDF sifatida yuklab olish">
              <span>📥</span> <span>${btnDownloadPres}</span>
            </button>
          ` : ''}

          ${isPlan ? `
            <button class="btn-primary" style="flex:1;padding:8px 14px;font-size:12.5px;display:flex;align-items:center;justify-content:center;gap:6px" onclick="window.viewStudentLessonPlan('${m.id}')">
              <span>📄</span> <span>${btnReadPlan}</span>
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }).join("");
};

// =========================================================================
// INTERAKTIV TEST RUNNER (TALABA TEST TOPSHIRISH VA NATIJANI TEKSHIRISH)
// =========================================================================

window.startStudentTest = async function(materialId) {
  const modal = document.getElementById("studentTestModal");
  const qList = document.getElementById("studentTestQuestionsList");
  const resCard = document.getElementById("studentTestResultCard");
  const footerActions = document.getElementById("studentTestFooterActions");
  // Natijadan keyin footer almashtirilgan bo'lsa, asl tugmalarni tiklash
  if (footerActions) {
    if (!STATE.testFooterHtml && footerActions.querySelector("#btnSubmitStudentTest")) STATE.testFooterHtml = footerActions.innerHTML;
    else if (STATE.testFooterHtml && !footerActions.querySelector("#btnSubmitStudentTest")) footerActions.innerHTML = STATE.testFooterHtml;
  }
  const submitBtn = document.getElementById("btnSubmitStudentTest");

  if (!modal || !qList) return;

  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";

  // Modallarni tozalash
  const loadText = lang === "ru" ? "Загрузка вопросов теста..." : (lang === "en" ? "Loading test questions..." : "Test savollari yuklanmoqda...");
  qList.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">${loadText}</div>`;
  if (resCard) resCard.style.display = "none";
  if (submitBtn) {
    submitBtn.style.display = "inline-flex";
    submitBtn.disabled = false;
    submitBtn.textContent = lang === "ru" ? "✅ Завершить тест и проверить результат" : (lang === "en" ? "✅ Finish Test & Check Result" : "✅ Testni yakunlash va natijani tekshirish");
  }

  STATE.studentTestAnswers = {};

  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}`, { headers });
    if (!res.ok) throw new Error("Test ma'lumotlarini yuklab bo'lmadi");
    const data = await res.json();
    STATE.currentStudentTest = data;

    const content = data.content_json || {};
    const questions = content.questions || [];

    // Header elementlarini to'ldirish
    const subjEl = document.getElementById("stModalSubject");
    const titleEl = document.getElementById("stModalTitle");
    const topicEl = document.getElementById("stModalTopic");
    const countText = document.getElementById("stModalCountText");

    const topicWord = lang === "ru" ? "Тема" : (lang === "en" ? "Topic" : "Mavzu");
    const defaultTopic = lang === "ru" ? "Общая тема" : (lang === "en" ? "General Topic" : "Umumiy mavzu");
    const testTitle = lang === "ru" ? "Контрольный тест" : (lang === "en" ? "Assessment Test" : "Nazorat Testi");
    const qUnit = lang === "ru" ? "вопросов" : (lang === "en" ? "questions" : "ta savol");

    if (subjEl) subjEl.textContent = data.subject_title || (lang === "ru" ? "ПРЕДМЕТ" : (lang === "en" ? "COURSE" : "FAN"));
    if (titleEl) titleEl.textContent = data.title || content.title || testTitle;
    if (topicEl) topicEl.textContent = `${topicWord}: ${data.topic_title || content.topic || defaultTopic}`;
    if (countText) countText.textContent = `${questions.length} ${qUnit}`;

    if (questions.length === 0) {
      const noQMsg = lang === "ru" ? "В этом тесте пока нет вопросов." : (lang === "en" ? "No questions in this test yet." : "Ushbu testda hali savollar mavjud emas.");
      qList.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">${noQMsg}</div>`;
      modal.style.display = "flex";
      return;
    }

    const letters = ["A", "B", "C", "D", "E", "F"];

    qList.innerHTML = questions.map((q, idx) => {
      const qId = q.id || `q_${idx + 1}`;
      const options = q.options || [];

      return `
        <div id="testQuestionBlock_${qId}" style="padding:16px 18px;background:var(--surface-2);border-radius:12px;border:1px solid var(--line)">
          <div style="font-weight:700;font-size:14.5px;color:var(--ink);margin-bottom:12px;line-height:1.4">
            <span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:var(--teal);color:#fff;text-align:center;line-height:24px;font-size:12px;margin-right:6px">${idx + 1}</span>
            ${escapeHtml(q.question)}
          </div>

          <div style="display:flex;flex-direction:column;gap:8px" id="optionsGroup_${qId}">
            ${options.map((opt, oIdx) => {
              return `
                <label id="optLabel_${qId}_${oIdx}" style="display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:8px;background:var(--card);border:1.5px solid var(--line);cursor:pointer;transition:all 0.15s">
                  <input type="radio" name="st_ans_${qId}" value="${oIdx}" onchange="window.onSelectStudentOption('${qId}', ${oIdx})" style="accent-color:var(--teal);cursor:pointer">
                  <span style="font-weight:700;min-width:22px;color:var(--ink)">${letters[oIdx]})</span>
                  <span style="font-size:13.5px;color:var(--ink-2);flex:1">${escapeHtml(opt)}</span>
                </label>
              `;
            }).join("")}
          </div>

          <div id="explanationBox_${qId}" style="display:none;margin-top:12px;padding:10px 14px;background:var(--card);border-radius:8px;border-left:4px solid var(--teal);font-size:13px;color:var(--ink-2)">
            <!-- Izoh / Rationale -->
          </div>
        </div>
      `;
    }).join("");

    modal.style.display = "flex";
  } catch (err) {
    console.error("Testni boshlashda xatolik:", err);
    showToast(err.message || "Testni yuklashda xatolik", "error");
  }
};

window.closeStudentTestModal = function() {
  const modal = document.getElementById("studentTestModal");
  if (modal) modal.style.display = "none";
};

// Variant tanlanganda
window.onSelectStudentOption = function(qId, optIdx) {
  STATE.studentTestAnswers[qId] = optIdx;

  // Variantlarni belgilash dizayni
  const optionsGroup = document.getElementById(`optionsGroup_${qId}`);
  if (optionsGroup) {
    const labels = optionsGroup.querySelectorAll("label");
    labels.forEach((lbl, idx) => {
      if (idx === optIdx) {
        lbl.style.borderColor = "var(--teal)";
        lbl.style.background = "var(--teal-soft)";
      } else {
        lbl.style.borderColor = "var(--line)";
        lbl.style.background = "var(--card)";
      }
    });
  }
};

// Test javoblarini yuborish va baholatish
window.submitStudentTestAnswers = async function(e) {
  if (e) e.preventDefault();
  if (!STATE.currentStudentTest) return;

  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const materialId = STATE.currentStudentTest.id;
  const questions = STATE.currentStudentTest.content_json?.questions || [];
  const totalQuestions = questions.length;

  const answeredCount = Object.keys(STATE.studentTestAnswers).length;
  if (answeredCount < totalQuestions) {
    const confirmMsg = lang === "ru"
      ? `Вы ответили на ${answeredCount} из ${totalQuestions} вопросов. Всё равно завершить тест?`
      : (lang === "en"
        ? `You answered ${answeredCount} out of ${totalQuestions} questions. Do you still want to finish?`
        : `Siz ${totalQuestions} ta savoldan ${answeredCount} tasiga javob berdingiz. Shunda ham testni yakunlamoqchimisiz?`);
    const confirmSubmit = confirm(confirmMsg);
    if (!confirmSubmit) return;
  }

  const submitBtn = document.getElementById("btnSubmitStudentTest");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = lang === "ru" ? "⏳ Проверка..." : (lang === "en" ? "⏳ Checking..." : "⏳ Tekshirilmoqda...");
  }

  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}/submit-test`, {
      method: "POST",
      headers,
      body: JSON.stringify({ answers: STATE.studentTestAnswers })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Testni baholashda xatolik");

    // Natijani ko'rsatish
    window.renderStudentTestResult(data);
    if (STATE.token) window.loadStudentMaterials().catch(() => {});
  } catch (err) {
    console.error("Test yuborishda xatolik:", err);
    showToast(err.message || "Testni tekshirib bo'lmadi", "error");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = lang === "ru" ? "✅ Завершить тест и проверить результат" : (lang === "en" ? "✅ Finish Test & Check Result" : "✅ Testni yakunlash va natijani tekshirish");
    }
  }
};

// Natijalar paneli va savollarni tahlil qilish
window.renderStudentTestResult = function(result) {
  const resCard = document.getElementById("studentTestResultCard");
  const submitBtn = document.getElementById("btnSubmitStudentTest");
  const footerActions = document.getElementById("studentTestFooterActions");
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";

  const total = result.total_questions || 0;
  const correct = result.correct_answers || 0;
  const pct = Math.round(result.score_percentage || 0);
  const grade = result.grade || "Baho";
  const passed = result.passed;

  const statusBg = passed ? "rgba(21,128,61,0.1)" : "rgba(185,28,28,0.1)";
  const statusBorder = passed ? "#15803D" : "#B91C1C";
  const statusIcon = passed ? "🎉" : "⚠️";
  
  let statusText = passed ? "Muvaffaqiyatli topshirildi!" : "Qoniqarsiz, ko'nikmalarni mustahkamlash zarur.";
  if (lang === "ru") {
    statusText = passed ? "Тест успешно сдан!" : "Неудовлетворительно, рекомендуется повторить материал.";
  } else if (lang === "en") {
    statusText = passed ? "Passed successfully!" : "Unsatisfactory, review is recommended.";
  }

  const resultTitle = lang === "ru" ? `Результат: ${correct} / ${total} правильно (${pct}%)` : (lang === "en" ? `Result: ${correct} / ${total} correct (${pct}%)` : `Natija: ${correct} / ${total} ta to'g'ri (${pct}%)`);
  const gradeLabel = lang === "ru" ? "Оценка:" : (lang === "en" ? "Grade level:" : "Olingan baho darajasi:");
  const masteryLabel = lang === "ru" ? "Усвоение" : (lang === "en" ? "Mastery" : "O'zlashtirish");

  if (resCard) {
    resCard.style.display = "block";
    resCard.style.background = statusBg;
    resCard.style.borderColor = statusBorder;
    resCard.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px">
        <div>
          <div style="font-size:12px;font-weight:700;color:${statusBorder};text-transform:uppercase;letter-spacing:0.5px">
            ${statusIcon} ${statusText}
          </div>
          <h3 style="margin:4px 0 2px;font-size:22px;font-family:var(--serif);color:var(--ink)">
            ${resultTitle}
          </h3>
          <div style="font-size:13px;color:var(--ink-2)">
            ${gradeLabel} <b>${grade}</b>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:36px;font-weight:800;color:${statusBorder};line-height:1">
            ${pct}%
          </div>
          <div style="font-size:11.5px;color:var(--muted)">${masteryLabel}</div>
        </div>
      </div>
    `;
    resCard.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // Savollarni tahliliy ko'rsatish (Green / Red)
  const reviews = result.reviews || [];
  const correctMarker = lang === "ru" ? "✓ Правильный ответ" : (lang === "en" ? "✓ Correct answer" : "✓ To'g'ri javob");
  const choiceMarker = lang === "ru" ? "✗ Ваш выбор" : (lang === "en" ? "✗ Your choice" : "✗ Siz tanlagan javob");
  const expTitle = lang === "ru" ? "💡 Пояснение и анализ:" : (lang === "en" ? "💡 Explanation & Analysis:" : "💡 Izoh va tahlil:");

  reviews.forEach(r => {
    const qId = r.question_id;
    const block = document.getElementById(`testQuestionBlock_${qId}`);
    const expBox = document.getElementById(`explanationBox_${qId}`);

    if (block) {
      block.style.borderColor = r.is_correct ? "#15803D" : "#B91C1C";
      block.style.background = r.is_correct ? "rgba(21,128,61,0.04)" : "rgba(185,28,28,0.04)";
    }

    (r.options || []).forEach((opt, oIdx) => {
      const lbl = document.getElementById(`optLabel_${qId}_${oIdx}`);
      if (!lbl) return;

      const isCorrectOpt = (oIdx === r.correct_index);
      const isStudentChoice = (oIdx === r.student_answer_idx);

      if (isCorrectOpt) {
        lbl.style.borderColor = "#15803D";
        lbl.style.background = "rgba(21,128,61,0.15)";
        lbl.style.fontWeight = "700";
        if (!lbl.querySelector(".ans-marker")) {
          lbl.insertAdjacentHTML("beforeend", `<span class="ans-marker" style="margin-left:auto;font-size:12px;color:#15803D">${correctMarker}</span>`);
        }
      } else if (isStudentChoice && !r.is_correct) {
        lbl.style.borderColor = "#B91C1C";
        lbl.style.background = "rgba(185,28,28,0.15)";
        lbl.style.fontWeight = "700";
        if (!lbl.querySelector(".ans-marker")) {
          lbl.insertAdjacentHTML("beforeend", `<span class="ans-marker" style="margin-left:auto;font-size:12px;color:#B91C1C">${choiceMarker}</span>`);
        }
      }
    });

    if (expBox && r.explanation) {
      expBox.style.display = "block";
      expBox.innerHTML = `
        <div style="font-weight:700;color:var(--teal);margin-bottom:2px">${expTitle}</div>
        <div>${escapeHtml(r.explanation)}</div>
      `;
    }
  });

  // Tugmalarni almashtirish: Qayta topshirish
  if (footerActions && STATE.currentStudentTest) {
    const matId = STATE.currentStudentTest.id;
    const closeText = lang === "ru" ? "Закрыть" : (lang === "en" ? "Close" : "Yopish");
    const retakeText = lang === "ru" ? "🔄 Пройти тест снова" : (lang === "en" ? "🔄 Retake Test" : "🔄 Testni qaytadan ishlash");
    footerActions.innerHTML = `
      <button type="button" class="btn-primary" style="background:none;color:var(--ink);border:1px solid var(--line)" onclick="window.closeStudentTestModal()">
        ${closeText}
      </button>
      <button type="button" class="btn-primary" style="padding:10px 22px;font-size:13.5px;font-weight:700" onclick="window.startStudentTest('${matId}')">
        ${retakeText}
      </button>
    `;
  }

  const toastMsg = lang === "ru" ? `Тест завершён! Ваш результат: ${correct}/${total} (${pct}%)` : (lang === "en" ? `Test completed! Your score: ${correct}/${total} (${pct}%)` : `Test yakunlandi! Natijangiz: ${correct}/${total} (${pct}%)`);
  showToast(toastMsg, passed ? "success" : "info");
};


// =========================================================================
// SLAYD KO'RUVCHI VA OFLAYN YUKLAB OLISH (DOWNLOAD PRESENTATION)
// =========================================================================

// Slayd / reja ochilganda "ko'rildi" (faqat tizimga kirgan talaba)
window.markStudentMaterialViewed = function(materialId) {
  if (!STATE.token || (STATE.currentUser && STATE.currentUser.role !== "student")) return;
  fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}/mark-viewed`, {
    method: "POST", headers: { "Authorization": `Bearer ${STATE.token}` }
  }).then(r => { if (r.ok) window.loadStudentMaterials().catch(() => {}); }).catch(() => {});
};

// =========================================================================
// YOZMA TOPSHIRIQ (MASHG'ULOT): YOZISH, O'Z-O'ZINI BAHOLASH, AI RUBRIKA
// =========================================================================

window.fillWritingModal = function(content, meta) {
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  let names = { content: "Mazmun", grammar: "Grammatika", lexis: "Leksika", coherence: "Bog'liqlik" };
  if (lang === "ru") {
    names = { content: "Содержание", grammar: "Грамматика", lexis: "Лексика", coherence: "Связность" };
  } else if (lang === "en") {
    names = { content: "Content", grammar: "Grammar", lexis: "Lexis", coherence: "Coherence" };
  }

  const courseFallback = lang === "ru" ? "ПРЕДМЕТ" : (lang === "en" ? "COURSE" : "FAN");
  const writingTitle = lang === "ru" ? "Письменное задание" : (lang === "en" ? "Writing Task" : "Yozma topshiriq");
  const topicWord = lang === "ru" ? "Тема" : (lang === "en" ? "Topic" : "Mavzu");
  const wordsWord = lang === "ru" ? "слов" : (lang === "en" ? "words" : "so'z");
  const taskLabel = lang === "ru" ? "📌 Задание:" : (lang === "en" ? "📌 Task:" : "📌 Vazifa:");
  const vocabTitle = lang === "ru" ? "🔑 Ключевые слова" : (lang === "en" ? "🔑 Key Vocabulary" : "🔑 Kalit so'zlar");
  const phrasesTitle = lang === "ru" ? "🧩 Полезные фразы" : (lang === "en" ? "🧩 Useful Phrases" : "🧩 Foydali iboralar");
  const structTitle = lang === "ru" ? "🏗️ Структура" : (lang === "en" ? "🏗️ Structure" : "🏗️ Tuzilma");
  const limitLabel = lang === "ru" ? "Требование:" : (lang === "en" ? "Requirement:" : "Talab:");

  document.getElementById("swSubject").textContent = meta.subject_title || meta.subject_name || content.subject || courseFallback;
  document.getElementById("swTitle").textContent = meta.title || content.title || writingTitle;
  document.getElementById("swTopic").textContent = `${topicWord}: ${meta.topic_title || content.topic || ""} · ${content.cefr_level || "B2"} · ${content.min_words || "?"}–${content.max_words || "?"} ${wordsWord}`;
  document.getElementById("swTask").innerHTML = `<b>${taskLabel}</b><br>${escapeHtml(content.task_prompt || "")}`;
  const sc = content.scaffold || {};
  const block = (title, arr) => (arr && arr.length) ? `<div style="padding:10px 12px;border-radius:8px;background:var(--surface-2)"><div style="font-weight:700;margin-bottom:4px">${title}</div><div style="color:var(--ink-2)">${arr.map(escapeHtml).join(" · ")}</div></div>` : "";
  document.getElementById("swScaffold").innerHTML =
    block(vocabTitle, sc.key_vocabulary) + block(phrasesTitle, sc.useful_phrases) + block(structTitle, sc.structure);
  document.getElementById("swCriteria").innerHTML = (content.criteria || []).map(c => `<div style="margin-bottom:4px"><b>${escapeHtml(c.name)}</b> — ${escapeHtml(c.description || "")}</div>`).join("");
  const sr = document.getElementById("swSelfRating");
  if (sr) sr.innerHTML = Object.keys(names).map(k => `
    <label style="display:flex;flex-direction:column;gap:3px"><span style="font-weight:600">${names[k]}</span>
      <select class="sw-self" data-key="${k}" style="padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:var(--surface)">
        <option value="">—</option>${[1,2,3,4,5].map(v => `<option value="${v}">${v}</option>`).join("")}
      </select></label>`).join("");
  const hint = document.getElementById("swLimitHint");
  if (hint) hint.textContent = `${limitLabel} ${content.min_words || "?"}–${content.max_words || "?"} ${wordsWord}`;
};

window.swUpdateWordCount = function() {
  const ta = document.getElementById("swText");
  const el = document.getElementById("swWordCount");
  if (!ta || !el) return;
  const n = (ta.value.match(/[A-Za-z'’\-]+|[\u0400-\u04FF]+/g) || []).length;
  const c = (STATE.currentStudentWriting || {}).content_json || {};
  const ok = (!c.min_words || n >= c.min_words) && (!c.max_words || n <= c.max_words);
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const wordsWord = lang === "ru" ? "слов" : (lang === "en" ? "words" : "so'z");
  el.textContent = `${n} ${wordsWord}`;
  el.style.color = n === 0 ? "var(--muted)" : (ok ? "#15803D" : "var(--amber)");
};

window.startStudentWriting = async function(materialId) {
  const modal = document.getElementById("studentWritingModal");
  if (!modal) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}`, { headers });
    if (!res.ok) throw new Error(lang === "ru" ? "Не удалось загрузить задание" : (lang === "en" ? "Failed to load task" : "Topshiriqni yuklab bo'lmadi"));
    const data = await res.json();
    const content = data.content_json || data.content || {};
    STATE.currentStudentWriting = { ...data, content_json: content };
    window.fillWritingModal(content, data);
    document.getElementById("swEditor").style.display = "block";
    const result = document.getElementById("swResult");
    result.style.display = "none"; result.innerHTML = "";
    document.getElementById("swText").value = "";
    const btn = document.getElementById("swSubmitBtn");
    btn.disabled = false;
    btn.textContent = lang === "ru" ? "📤 Отправить и получить оценку ИИ" : (lang === "en" ? "📤 Submit & Get AI Evaluation" : "📤 Topshirish va AI baho olish");
    window.swUpdateWordCount();
    if (data.attempt && data.attempt.status === "completed") {
      result.style.display = "block";
      const attWord = lang === "ru" ? "попытки" : (lang === "en" ? "attempts" : "urinish");
      const infoPrev = lang === "ru"
        ? `ℹ️ Вы уже сдавали: лучший результат <b>${data.attempt.best_score}%</b> (${data.attempt.attempts} ${attWord}). При повторной сдаче сохранится новая попытка.`
        : (lang === "en"
          ? `ℹ️ Previously submitted: best score <b>${data.attempt.best_score}%</b> (${data.attempt.attempts} ${attWord}). Re-submitting will save a new attempt.`
          : `ℹ️ Avval topshirgansiz: eng yaxshi natija <b>${data.attempt.best_score}%</b> (${data.attempt.attempts} urinish). Qayta yozsangiz, yangi urinish saqlanadi.`);
      result.innerHTML = `<div style="padding:10px 12px;border-radius:8px;background:var(--surface-2);font-size:13px">${infoPrev}</div>`;
    }
    modal.style.display = "flex";
  } catch (e) {
    showToast(e.message, "error");
  }
};

window.closeStudentWritingModal = function() {
  const modal = document.getElementById("studentWritingModal");
  if (modal) modal.style.display = "none";
};

window.submitStudentWriting = async function() {
  const cur = STATE.currentStudentWriting;
  if (!cur) return;
  const lang = window.getCurrentLang ? window.getCurrentLang() : "uz";
  const text = document.getElementById("swText").value.trim();
  const c = cur.content_json || {};
  const n = (text.match(/[A-Za-z'’\-]+|[\u0400-\u04FF]+/g) || []).length;
  const wordsWord = lang === "ru" ? "слов" : (lang === "en" ? "words" : "so'z");
  const tooShortMsg = lang === "ru" ? `Текст слишком короткий. Напишите не менее ${c.min_words || 50} ${wordsWord}.` : (lang === "en" ? `Text is too short. Please write at least ${c.min_words || 50} ${wordsWord}.` : `Matn juda qisqa. Kamida ${c.min_words || 50} so'z yozing.`);
  if (n < 20) return showToast(tooShortMsg, "warning");

  if (c.min_words && n < c.min_words) {
    const confirmShort = lang === "ru"
      ? `Вы написали ${n} ${wordsWord}, требуемый объём: ${c.min_words}. Всё равно отправить?`
      : (lang === "en"
        ? `You wrote ${n} ${wordsWord}, required: ${c.min_words}. Still want to submit?`
        : `Siz ${n} so'z yozdingiz, talab ${c.min_words}. Shunda ham topshirasizmi?`);
    if (!confirm(confirmShort)) return;
  }

  const selfRating = {};
  document.querySelectorAll("#swSelfRating select.sw-self").forEach(sel => { if (sel.value) selfRating[sel.dataset.key] = parseInt(sel.value); });
  const btn = document.getElementById("swSubmitBtn");
  btn.disabled = true;
  btn.textContent = lang === "ru" ? "⏳ ИИ оценивает по 4 критериям..." : (lang === "en" ? "⏳ AI evaluating by 4 criteria..." : "⏳ AI 4 mezon bo'yicha baholamoqda...");
  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;
  try {
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${cur.id}/submit-writing`, {
      method: "POST", headers, body: JSON.stringify({ text, self_rating: Object.keys(selfRating).length ? selfRating : null })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || (lang === "ru" ? "Ошибка при оценивании" : (lang === "en" ? "Evaluation error" : "Baholashda xatolik")));
    const box = document.getElementById("swResult");
    box.style.display = "block";
    const savedMsg = d.saved
      ? (lang === "ru" ? "💾 Результат сохранён" : (lang === "en" ? "💾 Result saved" : "💾 Natija saqlandi"))
      : (lang === "ru" ? "ℹ️ Войдите для сохранения" : (lang === "en" ? "ℹ️ Sign in to save" : "ℹ️ Saqlash uchun tizimga kiring"));

    box.innerHTML = `
      <div style="padding:16px 18px;border-radius:12px;border:1.5px solid ${d.passed ? '#15803D' : '#B91C1C'};background:${d.passed ? 'rgba(21,128,61,0.08)' : 'rgba(185,28,28,0.08)'}">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">
          <div style="font-size:18px;font-weight:800">${d.passed ? "✅" : "📝"} ${d.score_percentage}% <span style="font-size:13px;font-weight:600;color:var(--muted)">· ${d.word_count} ${wordsWord} · CEFR ${escapeHtml(d.cefr_estimate || "")}</span></div>
          <div style="font-size:12px;color:var(--muted)">${savedMsg}</div>
        </div>
        ${window.renderRubricHtml(d, d.self_rating)}
      </div>`;
    document.getElementById("swEditor").style.display = "none";
    const closeBtn = lang === "ru" ? "Закрыть" : (lang === "en" ? "Close" : "Yopish");
    const rewriteBtn = lang === "ru" ? "🔄 Переписать" : (lang === "en" ? "🔄 Rewrite" : "🔄 Qayta yozish");
    box.insertAdjacentHTML("beforeend", `<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:12px">
      <button type="button" class="btn-primary" style="background:none;color:var(--ink);border:1px solid var(--line)" onclick="window.closeStudentWritingModal()">${closeBtn}</button>
      <button type="button" class="btn-primary" onclick="window.startStudentWriting('${cur.id}')">${rewriteBtn}</button></div>`);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
    const gradedToast = lang === "ru" ? `Работа оценена: ${d.score_percentage}%` : (lang === "en" ? `Writing evaluated: ${d.score_percentage}%` : `Yozma ish baholandi: ${d.score_percentage}%`);
    showToast(gradedToast, d.passed ? "success" : "info");
    if (STATE.token) window.loadStudentMaterials().catch(() => {});
  } catch (e) {
    showToast(e.message, "error");
    btn.disabled = false;
    btn.textContent = lang === "ru" ? "📤 Отправить и получить оценку ИИ" : (lang === "en" ? "📤 Submit & Get AI Evaluation" : "📤 Topshirish va AI baho olish");
  }
};

window.viewStudentPresentation = async function(materialId) {
  const modal = document.getElementById("studentSlideModal");
  if (!modal) return;

  const lang = typeof window.getCurrentLang === "function" ? window.getCurrentLang() : "uz";
  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}`, { headers });
    if (!res.ok) {
      const errMsg = lang === "ru" ? "Не удалось загрузить презентацию" : (lang === "en" ? "Failed to load presentation" : "Prezentatsiyani yuklab bo'lmadi");
      throw new Error(errMsg);
    }
    const data = await res.json();

    const content = data.content_json || data.content || {};
    STATE.studentPresentation = { ...data, content_json: content };
    STATE.studentSlideIndex = 0;
    window.markStudentMaterialViewed(materialId);

    const subjBadge = document.getElementById("stSlideSubjectBadge");
    const modalTitle = document.getElementById("stSlideModalTitle");

    const defaultSubj = lang === "ru" ? "ПРЕДМЕТ" : (lang === "en" ? "SUBJECT" : "FAN");
    const defaultTitle = lang === "ru" ? "Презентация" : (lang === "en" ? "Presentation" : "Prezentatsiya");

    if (subjBadge) subjBadge.textContent = data.subject_title || data.subject_name || content.subject || defaultSubj;
    if (modalTitle) modalTitle.textContent = data.title || content.title || defaultTitle;

    window.renderCurrentStudentSlide();
    modal.style.display = "flex";
  } catch (err) {
    console.error("Slaydni ochishda xatolik:", err);
    showToast(err.message || (lang === "ru" ? "Не удалось открыть слайд" : (lang === "en" ? "Could not open slide" : "Slaydni ochib bo'lmadi")), "error");
  }
};

window.closeStudentSlideModal = function() {
  const modal = document.getElementById("studentSlideModal");
  if (modal) modal.style.display = "none";
};

window.renderCurrentStudentSlide = function() {
  if (!STATE.studentPresentation) return;

  const lang = typeof window.getCurrentLang === "function" ? window.getCurrentLang() : "uz";
  const content = STATE.studentPresentation.content_json || {};
  const slides = content.slides || [];
  const total = slides.length;
  const idx = STATE.studentSlideIndex || 0;

  const counterEl = document.getElementById("stSlideCounter");
  const badgeEl = document.getElementById("stSlideBadge");
  const titleEl = document.getElementById("stSlideTitle");
  const bulletsEl = document.getElementById("stSlideBullets");
  const notesBox = document.getElementById("stSpeakerNotesBox");
  const notesText = document.getElementById("stSpeakerNotesText");
  const imagePromptBox = document.getElementById("stImagePromptBox");
  const imagePromptText = document.getElementById("stImagePromptText");
  const btnPrev = document.getElementById("btnStPrevSlide");
  const btnNext = document.getElementById("btnStNextSlide");

  if (total === 0) {
    if (titleEl) titleEl.textContent = lang === "ru" ? "Слайды отсутствуют" : (lang === "en" ? "No slides available" : "Slaydlar mavjud emas");
    return;
  }

  const slide = slides[idx] || {};

  const counterPrefix = lang === "ru" ? "Слайд" : (lang === "en" ? "Slide" : "Slayd");
  if (counterEl) counterEl.textContent = `${counterPrefix}: ${idx + 1} / ${total}`;

  const defaultIntro = lang === "ru" ? "ВВЕДЕНИЕ И ОСНОВНАЯ ИДЕЯ" : (lang === "en" ? "INTRODUCTION & CORE IDEA" : "KIRISH & ASOSIY G'OYA");
  const defaultOutro = lang === "ru" ? "ВЫВОДЫ И ЛИТЕРАТУРА" : (lang === "en" ? "CONCLUSIONS & REFERENCES" : "XULOSA VA ADABIYOTLAR");
  const defaultSlide = lang === "ru" ? `СЛАЙД ${idx + 1}` : (lang === "en" ? `SLIDE ${idx + 1}` : `SLAYD ${idx + 1}`);

  if (badgeEl) badgeEl.textContent = slide.visual_badge || (idx === 0 ? defaultIntro : (idx === total - 1 ? defaultOutro : defaultSlide));
  if (titleEl) titleEl.textContent = slide.title || (lang === "ru" ? `Слайд ${idx + 1}` : (lang === "en" ? `Slide ${idx + 1}` : `Slayd ${idx + 1}`));
  window.applySlideImage("stSlideImageWrap", "stSlideImage", slide);

  if (bulletsEl) {
    const bullets = slide.bullets || [];
    bulletsEl.innerHTML = bullets.map(b => `<li style="margin-bottom:10px">${escapeHtml(b)}</li>`).join("");
  }

  if (notesBox && notesText) {
    if (slide.speaker_notes) {
      notesBox.style.display = "block";
      notesText.textContent = slide.speaker_notes;
    } else {
      notesBox.style.display = "none";
    }
  }

  if (imagePromptBox && imagePromptText) {
    if (slide.image_prompt && slide.image_prompt.trim()) {
      imagePromptText.textContent = slide.image_prompt;
      imagePromptBox.style.display = "block";
    } else {
      imagePromptBox.style.display = "none";
    }
  }

  if (btnPrev) btnPrev.disabled = (idx === 0);
  if (btnNext) btnNext.disabled = (idx >= total - 1);
};

window.prevStudentSlide = function() {
  if (!STATE.studentPresentation) return;
  if (STATE.studentSlideIndex > 0) {
    STATE.studentSlideIndex--;
    window.renderCurrentStudentSlide();
  }
};

window.nextStudentSlide = function() {
  if (!STATE.studentPresentation) return;
  const slides = STATE.studentPresentation.content_json?.slides || [];
  if (STATE.studentSlideIndex < slides.length - 1) {
    STATE.studentSlideIndex++;
    window.renderCurrentStudentSlide();
  }
};

window.copyStudentSlideText = function() {
  if (!STATE.studentPresentation) return;
  const lang = typeof window.getCurrentLang === "function" ? window.getCurrentLang() : "uz";
  const content = STATE.studentPresentation.content_json || {};
  const slides = content.slides || [];

  const presLabel = lang === "ru" ? "ПРЕЗЕНТАЦИЯ" : (lang === "en" ? "PRESENTATION" : "PREZENTATSIYA");
  const subjLabel = lang === "ru" ? "Предмет" : (lang === "en" ? "Subject" : "Fan");
  const topicLabel = lang === "ru" ? "Тема" : (lang === "en" ? "Topic" : "Mavzu");
  const slideLabel = lang === "ru" ? "СЛАЙД" : (lang === "en" ? "SLIDE" : "SLAYD");
  const noteLabel = lang === "ru" ? "Заметки докладчика" : (lang === "en" ? "Speaker notes" : "Spiker eslatmasi");
  const promptLabel = lang === "ru" ? "Промпт изображения" : (lang === "en" ? "Image prompt" : "Rasm prompti");

  let text = `${presLabel}: ${content.title || STATE.studentPresentation.title}\n${subjLabel}: ${STATE.studentPresentation.subject_title || ''}\n${topicLabel}: ${STATE.studentPresentation.topic_title || ''}\n\n`;

  slides.forEach((s, i) => {
    text += `=== ${slideLabel} ${i + 1}: ${s.title} ===\n`;
    (s.bullets || []).forEach(b => text += `• ${b}\n`);
    if (s.speaker_notes) text += `[${noteLabel}]: ${s.speaker_notes}\n`;
    if (s.image_prompt) text += `[${promptLabel}]: ${s.image_prompt}\n`;
    text += `\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    const successToast = lang === "ru" ? "📋 Текст презентации полностью скопирован!" : (lang === "en" ? "📋 Presentation text copied to clipboard!" : "📋 Slaydlar matni to'liq nusxalandi!");
    showToast(successToast, "success");
  }).catch(() => {
    const errAlert = lang === "ru" ? "Не удалось скопировать" : (lang === "en" ? "Could not copy" : "Nusxalash imkoni bo'lmadi");
    alert(errAlert);
  });
};

// Slaydni yuklab olish (ID bo'yicha to'g'ridan-to'g'ri)
window.downloadPresentationById = async function(materialId) {
  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  try {
    showToast("⏳ Taqdimot fayli shakllantirilmoqda...", "info");
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}`, { headers });
    if (!res.ok) throw new Error("Taqdimotni yuklab bo'lmadi");
    const data = await res.json();
    const content = data.content_json || data.content || {};
    window.generateAndDownloadPresentationHtml({ ...data, content_json: content });
  } catch (err) {
    console.error("Yuklab olishda xatolik:", err);
    showToast(err.message || "Taqdimotni yuklab bo'lmadi", "error");
  }
};

// Hozir ochiq turgan prezentatsiyani yuklab olish
window.downloadCurrentPresentation = function() {
  if (!STATE.studentPresentation) return;
  const content = STATE.studentPresentation.content_json || STATE.studentPresentation.content || {};
  window.generateAndDownloadPresentationHtml({ ...STATE.studentPresentation, content_json: content });
};

// Oflayn ishlovchi mustaqil HTML faylni shakllantirish va brauzerga yuklash
window.generateAndDownloadPresentationHtml = function(material) {
  const content = material.content_json || material.content || {};
  const slides = content.slides || [];
  const title = material.title || content.title || "Taqdimot";
  const subject = material.subject_title || material.subject_name || content.subject || "TILORA Ta'lim Platformasi";
  const topic = material.topic_title || content.topic || "";

  // Slaydlar HTML kontenti (<script> ichida xavfsiz bo'lishi uchun "</" ni ekranlaymiz)
  const slidesJsonString = JSON.stringify(slides).replace(/<\//g, '<\\/');

  const htmlSource = `<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)} — Slaydlar (TILORA)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0F172A;
      --card-bg: #1E293B;
      --card-border: #334155;
      --teal: #0D9488;
      --teal-light: #2DD4BF;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --accent: #38BDF8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      user-select: none;
    }
    header {
      padding: 16px 28px;
      background: rgba(30, 41, 59, 0.7);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      background: rgba(13, 148, 136, 0.2);
      color: var(--teal-light);
      border: 1px solid var(--teal);
    }
    .slide-area {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 30px;
    }
    .slide-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      width: 100%;
      max-width: 960px;
      min-height: 480px;
      padding: 48px 56px;
      box-shadow: 0 25px 60px rgba(0,0,0,0.5);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
    }
    .slide-title {
      font-family: 'Playfair Display', serif;
      font-size: 32px;
      color: var(--text-main);
      margin-bottom: 24px;
      line-height: 1.3;
    }
    .bullets {
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
    }
    .bullets li {
      font-size: 18px;
      line-height: 1.6;
      color: #E2E8F0;
      position: relative;
      padding-left: 28px;
    }
    .bullets li::before {
      content: "✦";
      position: absolute;
      left: 0;
      color: var(--teal-light);
      font-size: 16px;
    }
    .notes-box {
      margin-top: 24px;
      padding: 14px 18px;
      background: rgba(15, 23, 42, 0.6);
      border-left: 4px solid var(--teal);
      border-radius: 8px;
      font-size: 14px;
      color: var(--text-muted);
      font-style: italic;
    }
    footer {
      padding: 16px 28px;
      background: rgba(30, 41, 59, 0.7);
      backdrop-filter: blur(10px);
      border-top: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .btn {
      padding: 10px 20px;
      border-radius: 10px;
      border: 1px solid var(--card-border);
      background: rgba(255,255,255,0.05);
      color: var(--text-main);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .btn:hover:not(:disabled) {
      background: var(--teal);
      border-color: var(--teal);
      color: #fff;
    }
    .btn:disabled {
      opacity: 0.35;
      cursor: not-allowed;
    }
    .btn-green {
      background: #15803D;
      border-color: #15803D;
      color: #fff;
    }
    .btn-green:hover {
      background: #166534;
    }

    /* Print to PDF */
    @media print {
      body { background: #fff !important; color: #000 !important; }
      header, footer, .btn { display: none !important; }
      .slide-area { padding: 0 !important; }
      .slide-card {
        border: none !important;
        box-shadow: none !important;
        background: #fff !important;
        page-break-after: always;
        min-height: auto !important;
        padding: 40px !important;
      }
      .slide-title { color: #000 !important; font-size: 28pt !important; }
      .bullets li { color: #222 !important; font-size: 16pt !important; }
      .bullets li::before { color: #0D9488 !important; }
      .notes-box { color: #555 !important; background: #f4f4f4 !important; }
    }
  </style>
</head>
<body>

  <header>
    <div>
      <span class="badge">${escapeHtml(subject)}</span>
      <h3 style="font-size:16px;margin-top:4px;font-family:'Playfair Display', serif">${escapeHtml(title)}</h3>
      <div style="font-size:12px;color:var(--text-muted)">Mavzu: ${escapeHtml(topic)}</div>
    </div>
    <div style="display:flex;align-items:center;gap:12px">
      <span id="counter" style="font-size:14px;font-weight:700;color:var(--teal-light)">1 / ${slides.length}</span>
      <button class="btn btn-green" onclick="window.print()" title="PDF qilib saqlash yoki chop etish">🖨️ PDF / Chop etish</button>
    </div>
  </header>

  <main class="slide-area">
    <div class="slide-card">
      <div>
        <div id="slideBadge" class="badge" style="margin-bottom:14px">SLAYD 1</div>
        <h1 id="slideTitle" class="slide-title">Yuklanmoqda...</h1>
        <div id="slideImageWrap" style="display:none;margin:0 0 18px;border-radius:12px;overflow:hidden;background:rgba(15,23,42,0.5)">
          <img id="slideImage" alt="" style="display:block;width:100%;max-height:340px;object-fit:cover">
        </div>
        <ul id="slideBullets" class="bullets"></ul>
      </div>
      <div id="notesBox" class="notes-box">
        <strong>🎙️ Eslatma (Speaker Notes):</strong> <span id="notesText"></span>
      </div>
      <div id="imagePromptBox" class="notes-box" style="border-left-color: var(--accent); display: none;">
        <strong>🖼️ Rasm generatsiya prompti (Midjourney/DALL-E uchun):</strong> <span id="imagePromptText"></span>
      </div>
    </div>
  </main>

  <footer>
    <div style="font-size:12.5px;color:var(--text-muted)">
      Strelkalar (← va →) yoki Space bilan o'tkazishingiz mumkin · TILORA
    </div>
    <div style="display:flex;gap:10px">
      <button id="btnPrev" class="btn" onclick="prev()">← Oldingi</button>
      <button id="btnNext" class="btn" onclick="next()">Keyingi →</button>
    </div>
  </footer>

  <script>
    const slides = ${slidesJsonString};
    let currentIdx = 0;

    function render() {
      if (!slides || slides.length === 0) return;
      const s = slides[currentIdx];
      document.getElementById('counter').textContent = (currentIdx + 1) + ' / ' + slides.length;
      document.getElementById('slideBadge').textContent = currentIdx === 0 ? 'KIRISH VA MAQSAD' : (currentIdx === slides.length - 1 ? 'XULOSA VA ADABIYOTLAR' : 'SLAYD ' + (currentIdx + 1));
      document.getElementById('slideTitle').textContent = s.title || ('Slayd ' + (currentIdx + 1));

      const bulletsEl = document.getElementById('slideBullets');
      bulletsEl.innerHTML = (s.bullets || []).map(b => '<li>' + String(b == null ? '' : b).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</li>').join('');

      const imgWrap = document.getElementById('slideImageWrap');
      const img = document.getElementById('slideImage');
      if (s.image_url) {
        imgWrap.style.display = 'block';
        img.onerror = function() {
          if (s.image_fallback_url && img.src !== s.image_fallback_url) { img.src = s.image_fallback_url; }
          else { imgWrap.style.display = 'none'; }
        };
        img.src = s.image_url;
      } else {
        imgWrap.style.display = 'none';
        img.removeAttribute('src');
      }

      const notesBox = document.getElementById('notesBox');
      const notesText = document.getElementById('notesText');
      if (s.speaker_notes) {
        notesBox.style.display = 'block';
        notesText.textContent = s.speaker_notes;
      } else {
        notesBox.style.display = 'none';
      }

      const imagePromptBox = document.getElementById('imagePromptBox');
      const imagePromptText = document.getElementById('imagePromptText');
      if (s.image_prompt && s.image_prompt.trim()) {
        imagePromptBox.style.display = 'block';
        imagePromptText.textContent = s.image_prompt;
      } else {
        imagePromptBox.style.display = 'none';
      }

      document.getElementById('btnPrev').disabled = (currentIdx === 0);
      document.getElementById('btnNext').disabled = (currentIdx >= slides.length - 1);
    }

    function prev() {
      if (currentIdx > 0) { currentIdx--; render(); }
    }
    function next() {
      if (currentIdx < slides.length - 1) { currentIdx++; render(); }
    }

    window.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') next();
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') prev();
    });

    render();
  </script>
</body>
</html>`;

  // Fayl nomini tozalash (safe filename)
  const cleanTitle = (topic || title || "taqdimot").replace(/[^a-zA-Z0-9_\u0400-\u04FF\s-]/g, '').trim().replace(/\s+/g, '_');
  const filename = `${cleanTitle}_slaydlar.html`;

  // Blob yaratish va brauzer orqali yuklab olish
  const blob = new Blob([htmlSource], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast(`📥 "${filename}" muvaffaqiyatli yuklab olindi! Istalgan brauzerda oflayn ochishingiz mumkin.`, "success");
};

// Dars rejasini o'qish modali
window.viewStudentLessonPlan = async function(materialId) {
  const modal = document.getElementById("studentPlanModal");
  const contentArea = document.getElementById("studentPlanContentArea");
  if (!modal || !contentArea) return;

  const lang = typeof window.getCurrentLang === "function" ? window.getCurrentLang() : "uz";
  const loadingText = lang === "ru" ? "План урока загружается..." : (lang === "en" ? "Loading lesson plan..." : "Dars rejasi yuklanmoqda...");
  contentArea.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">${loadingText}</div>`;
  modal.style.display = "flex";

  const headers = { "Content-Type": "application/json" };
  if (STATE.token) headers["Authorization"] = `Bearer ${STATE.token}`;

  try {
    const res = await fetch(`${STATE.apiBaseUrl}/student/materials/${materialId}`, { headers });
    if (!res.ok) {
      const errLoad = lang === "ru" ? "Не удалось загрузить план урока" : (lang === "en" ? "Failed to load lesson plan" : "Dars rejasini yuklab bo'lmadi");
      throw new Error(errLoad);
    }
    const data = await res.json();
    const content = data.content_json || data.content || {};
    STATE.currentStudentLessonPlan = { ...data, content_json: content };
    window.markStudentMaterialViewed(materialId);

    const subjBadge = document.getElementById("stPlanSubjectBadge");
    const modalTitle = document.getElementById("stPlanModalTitle");
    const modalTopic = document.getElementById("stPlanModalTopic");

    const defaultSubj = lang === "ru" ? "ПРЕДМЕТ" : (lang === "en" ? "SUBJECT" : "FAN");
    const defaultTitle = lang === "ru" ? "План урока" : (lang === "en" ? "Lesson Plan" : "Dars Rejasi");
    const topicPrefix = lang === "ru" ? "Тема" : (lang === "en" ? "Topic" : "Mavzu");
    const durationPrefix = lang === "ru" ? "Длительность" : (lang === "en" ? "Duration" : "Davomiyligi");
    const defaultDuration = lang === "ru" ? "80 минут" : (lang === "en" ? "80 minutes" : "80 daqiqa");

    if (subjBadge) subjBadge.textContent = data.subject_title || data.subject_name || content.subject || defaultSubj;
    if (modalTitle) modalTitle.textContent = data.title || content.title || defaultTitle;
    if (modalTopic) modalTopic.textContent = `${topicPrefix}: ${data.topic_title || content.topic || ''} · ${durationPrefix}: ${content.duration || defaultDuration}`;

    const stages = content.stages || [];
    if (stages.length === 0) {
      const noStages = lang === "ru" ? "Этапы плана отсутствуют." : (lang === "en" ? "No stages found in lesson plan." : "Reja bosqichlari mavjud emas.");
      contentArea.innerHTML = `<div style="text-align:center;padding:30px;color:var(--muted)">${noStages}</div>`;
      return;
    }

    const formatLabel = lang === "ru" ? "Формат занятия" : (lang === "en" ? "Lesson format" : "Dars formati");
    const formatValue = lang === "ru" ? "5-этапный адаптивно-метакогнитивный семинар" : (lang === "en" ? "5-stage adaptive-metacognitive seminar" : "5 bosqichli adaptiv-metakognitiv seminar");
    const timeLabel = lang === "ru" ? "Время" : (lang === "en" ? "Duration" : "Vaqt");
    const actLabel = lang === "ru" ? "Деятельность" : (lang === "en" ? "Activity" : "Faoliyat");
    const teacherRoleLabel = lang === "ru" ? "👨‍🏫 Роль преподавателя:" : (lang === "en" ? "👨‍🏫 Teacher's role:" : "👨‍🏫 O'qituvchi roli:");
    const studentRoleLabel = lang === "ru" ? "👨‍🎓 Роль студента:" : (lang === "en" ? "👨‍🎓 Student's role:" : "👨‍🎓 Talaba roli:");
    const defaultTeacherRole = lang === "ru" ? "Направление и анализ" : (lang === "en" ? "Guiding & analysis" : "Yo'naltirish va tahlil");
    const defaultStudentRole = lang === "ru" ? "Самостоятельное и активное творчество" : (lang === "en" ? "Independent & active production" : "Mustaqil va faol ijod");

    contentArea.innerHTML = `
      <div style="background:var(--surface-2);border-radius:10px;padding:12px 16px;margin-bottom:8px;border:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <span style="font-size:13px;color:var(--ink-2)"><b>${formatLabel}:</b> ${formatValue}</span>
        <span class="chip full" style="font-size:11.5px">${timeLabel}: ${content.duration || defaultDuration}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px">
        ${stages.map((st, idx) => {
          const stageTitle = lang === "ru" ? `${idx + 1}-й этап: ${st.name || st.title || 'Этап'}` : (lang === "en" ? `Stage ${idx + 1}: ${st.name || st.title || 'Stage'}` : `${idx + 1}-bosqich: ${st.name || st.title || 'Bosqich'}`);
          const stageDuration = st.duration || (lang === "ru" ? "15 минут" : (lang === "en" ? "15 minutes" : "15 daqiqa"));
          return `
            <div style="border-radius:10px;padding:14px 16px;background:var(--surface-2);border:1px solid var(--line);border-left:4px solid var(--teal)">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px">
                <div style="font-weight:700;font-size:14.5px;color:var(--ink)">
                  ${escapeHtml(stageTitle)}
                </div>
                <span style="font-size:11.5px;padding:2px 8px;border-radius:6px;background:var(--teal-soft);color:var(--teal);font-weight:700">
                  ⏱️ ${escapeHtml(stageDuration)}
                </span>
              </div>
              <div style="font-size:13px;color:var(--ink-2);margin-bottom:8px;line-height:1.5">
                <b>${actLabel}:</b> ${escapeHtml(st.activity || st.description || '')}
              </div>
              <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(240px, 1fr));gap:8px;font-size:12.5px;color:var(--muted);background:var(--card);padding:10px 12px;border-radius:8px">
                <div><b>${teacherRoleLabel}</b> ${escapeHtml(st.teacher_role || defaultTeacherRole)}</div>
                <div><b>${studentRoleLabel}</b> ${escapeHtml(st.student_role || defaultStudentRole)}</div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  } catch (err) {
    console.error("Dars rejasini ochishda xatolik:", err);
    showToast(err.message || (lang === "ru" ? "Не удалось открыть план урока" : (lang === "en" ? "Could not open lesson plan" : "Dars rejasini ochib bo'lmadi")), "error");
    contentArea.innerHTML = `<div style="text-align:center;padding:20px;color:var(--clay)">${escapeHtml(err.message || (lang === "ru" ? "Произошла ошибка" : (lang === "en" ? "An error occurred" : "Xatolik yuz berdi")))}</div>`;
  }
};

window.closeStudentPlanModal = function() {
  const modal = document.getElementById("studentPlanModal");
  if (modal) modal.style.display = "none";
};

window.copyStudentPlanText = function() {
  if (!STATE.currentStudentLessonPlan) return;
  const lang = typeof window.getCurrentLang === "function" ? window.getCurrentLang() : "uz";
  const p = STATE.currentStudentLessonPlan;
  const content = p.content_json || p.content || {};
  const stages = content.stages || [];

  const planHeading = lang === "ru" ? "РАЗРАБОТКА УРОКА" : (lang === "en" ? "LESSON PLAN" : "DARS ISHLANMASI");
  const subjLabel = lang === "ru" ? "Предмет" : (lang === "en" ? "Subject" : "Fan");
  const topicLabel = lang === "ru" ? "Тема" : (lang === "en" ? "Topic" : "Mavzu");
  const durationLabel = lang === "ru" ? "Длительность" : (lang === "en" ? "Duration" : "Davomiyligi");
  const defaultDuration = lang === "ru" ? "80 минут" : (lang === "en" ? "80 minutes" : "80 daqiqa");
  const actLabel = lang === "ru" ? "Деятельность" : (lang === "en" ? "Activity" : "Faoliyat");
  const teacherLabel = lang === "ru" ? "Роль преподавателя" : (lang === "en" ? "Teacher role" : "O'qituvchi roli");
  const studentLabel = lang === "ru" ? "Роль студента" : (lang === "en" ? "Student role" : "Talaba roli");

  let text = `${planHeading}: ${p.title || content.title}\n${subjLabel}: ${p.subject_title || p.subject_name || content.subject || ''}\n${topicLabel}: ${p.topic_title || content.topic || ''}\n${durationLabel}: ${content.duration || defaultDuration}\n\n`;

  stages.forEach((st, idx) => {
    const stageHeader = lang === "ru" ? `${idx + 1}-Й ЭТАП` : (lang === "en" ? `STAGE ${idx + 1}` : `${idx + 1}-BOSQICH`);
    text += `${stageHeader}: ${st.name || st.title} (${st.duration || ''})\n`;
    text += `${actLabel}: ${st.activity || st.description || ''}\n`;
    text += `${teacherLabel}: ${st.teacher_role || ''}\n`;
    text += `${studentLabel}: ${st.student_role || ''}\n\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    const successToast = lang === "ru" ? "📋 План урока скопирован!" : (lang === "en" ? "📋 Lesson plan copied to clipboard!" : "📋 Dars rejasi matni nusxalandi!");
    showToast(successToast, "success");
  }).catch(() => {
    const errAlert = lang === "ru" ? "Не удалось скопировать" : (lang === "en" ? "Could not copy" : "Nusxalash imkoni bo'lmadi");
    alert(errAlert);
  });
};

// Klaviatura strelkalari talaba prezentatsiyasida ham ishlashi
window.addEventListener("keydown", function(e) {
  const modal = document.getElementById("studentSlideModal");
  if (modal && modal.style.display === "flex") {
    if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
      window.nextStudentSlide();
    } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
      window.prevStudentSlide();
    } else if (e.key === "Escape") {
      window.closeStudentSlideModal();
    }
  }
});

// ============================================================
// 10. RESTful API HUJJATLARI VA JONLI TESTER MODULI (API DOCS)
// ============================================================
(function() {
  'use strict';

  const API_DOCS_STORE = {
    activeTab: 'catalog',
    selectedCategory: 'all',
    searchQuery: '',
    selectedMethod: 'ALL'
  };

  const API_ENDPOINTS = [
    // --- 1. Autentifikatsiya ---
    {
      id: "auth_login",
      cat: "auth",
      method: "POST",
      path: "/api/auth/login",
      title: "Tizimga kirish va JWT token olish",
      desc: "Foydalanuvchi elektron pochtasi/logini va paroli orqali autentifikatsiyadan o'tib, 24 soatlik Bearer token oladi.",
      role: "Barchasi",
      principle: null,
      auth: false,
      body: {
        email: "sizning_loginingiz",
        password: "********"
      },
      response: {
        access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        token_type: "bearer",
        user: {
          id: "usr_teacher_01",
          email: "oqituvchi1@tilora.uz",
          full_name: "Adiba Ikramova",
          role: "teacher"
        }
      }
    },
    {
      id: "auth_register",
      cat: "auth",
      method: "POST",
      path: "/api/auth/register",
      title: "Yangi foydalanuvchini ro'yxatdan o'tkazish",
      desc: "Yangi talaba yoki o'qituvchi arizasi. O'qituvchilar Super Admin tomonidan tasdiqlangandan so'ng tizimga kira oladi.",
      role: "Barchasi",
      principle: null,
      auth: false,
      body: {
        email: "yangi_talaba@tilora.uz",
        password: "parol12345!",
        full_name: "Nilufar Sobirova",
        role: "student",
        institution_id: "inst_buxdu"
      },
      response: {
        message: "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi",
        user_id: "usr_student_99"
      }
    },

    // --- 2. Talaba va Profil ---
    {
      id: "student_profile",
      cat: "student",
      method: "GET",
      path: "/api/student/profile",
      title: "Talabaning 3 o'lchovli profili",
      desc: "Talabaning CEFR darajalari (Listening, Reading, Speaking, Writing), ESP kasbiy yo'nalishi va FLCAS affektiv-kognitiv ko'rsatkichlari.",
      role: "student, teacher, admin",
      principle: "2-Tamoyil: Sabab ochiq",
      auth: true,
      body: null,
      response: {
        cefr: { listening: "B1", reading: "B2", speaking: "A2", writing: "B1" },
        esp_track: "Filologiya va tillarni o'qitish (ingliz tili)",
        cognitive: { load_capacity: 45, pace_index: 62, anxiety_level: 71, autonomy_readiness: 40 }
      }
    },
    {
      id: "student_path",
      cat: "student",
      method: "GET",
      path: "/api/student/path",
      title: "16 haftalik shaxsiylashtirilgan o'quv yo'li",
      desc: "Talaba profili tahlili asosida generatsiya qilingan haftalik darslar, skaffolding darajalari va o'qituvchi tasdiqlagan bosqichlar.",
      role: "student, teacher, admin",
      principle: "Scaffolding Dinamikasi",
      auth: true,
      body: null,
      response: {
        weeks: [
          { week: 1, topic: "Tinglab tushunish: Dars kuzatuvi va asosiy pedagogik atamalar", scaffold: "none", status: "done" },
          { week: 4, topic: "Yozma nutq: Talabalar ishini baholash mezonlari", scaffold: "partial", status: "active" }
        ]
      }
    },
    {
      id: "student_diagnostic_submit",
      cat: "student",
      method: "POST",
      path: "/api/student/diagnostic",
      title: "Diagnostika testi va FLCAS anketasini topshirish",
      desc: "Talaba CEFR savollari javoblarini va Likert 1-5 shkalasidagi FLCAS anketasini topshiradi, profil avtomatik hisoblanadi.",
      role: "student",
      principle: null,
      auth: true,
      body: {
        answers: { "q_diag_1": "B", "q_diag_2": "C" },
        survey_answers: { "q_srv_1": 4, "q_srv_2": 5 }
      },
      response: {
        status: "success",
        message: "Profil muvaffaqiyatli yangilandi"
      }
    },

    // --- 3. 5 Bosqichli Mashg'ulot ---
    {
      id: "lesson_save_prod",
      cat: "lesson",
      method: "POST",
      path: "/api/lesson/stage3/save-production",
      title: "3-Bosqich: Mustaqil nutqiy mahsulot (AI yopiq)",
      desc: "1-TAMOYIL: Talaba tashqi AI yordamisiz o'z aqliy mehnati bilan yozgan matnini saqlaydi va tahlil bosqichiga o'tadi.",
      role: "student",
      principle: "1-Qoida: Mustaqil bosqichda AI yopiq",
      auth: true,
      body: {
        lesson_id: "lesson_w04",
        student_text: "Effective assessment requires transparent criteria such as content, coherence, lexis, and grammar. In my pedagogical view, formative assessment helps students identify areas of growth."
      },
      response: {
        saved: true,
        word_count: 32,
        stage: 4
      }
    },
    {
      id: "lesson_stage4_feedback",
      cat: "lesson",
      method: "GET",
      path: "/api/feedback/lesson/{lesson_id}",
      title: "4-Bosqich: Sababli tahlil va L1 interferensiyasi",
      desc: "2-TAMOYIL: Hattie & Timperley modeli asosidagi sababli izohlar. Xato to'g'rilab berilmaydi, faqat lingvistik sababi va ona tili ta'siri tushuntiriladi.",
      role: "student, teacher",
      principle: "2-Qoida: Sabab shablonda ochiq",
      auth: true,
      body: null,
      response: {
        feedbacks: [
          {
            type: "l1_transfer",
            fragment: "depends from",
            reason: "O'zbek tilidagi «bog'liq bo'lmoq» fe'li ta'sirida noto'g'ri predlog tanlangan (L1 interferensiyasi). Ingliz tilida «depend on» qo'llaniladi.",
            suggestion_type: "metacognitive_hint"
          }
        ]
      }
    },
    {
      id: "lesson_stage5_reflection",
      cat: "lesson",
      method: "POST",
      path: "/api/lesson/stage5/reflection",
      title: "5-Bosqich: Metakognitiv baholash va refleksiya",
      desc: "4-TAMOYIL: Talaba avval o'z bahosini qo'yadi, keyin AI mustaqil bahosi ochiladi. Talaba baholar farqini o'z so'zlari bilan tahlil qiladi.",
      role: "student",
      principle: "4-Qoida: Xulosani talaba chiqaradi",
      auth: true,
      body: {
        lesson_id: "lesson_w04",
        self_eval: { content: 4, grammar: 3, lexis: 4, coherence: 4 },
        reflection_gap: "Men grammatikamni 3 deb baholadim, AI ham 3 qo'ydi, chunki ona tili interferensiyasi bo'yicha 2 ta noaniqlik bor edi.",
        learning_goal: "Keyingi darsda bog'lovchilarni qayta tekshiraman."
      },
      response: {
        completed: true,
        reflection_recorded: true
      }
    },

    // --- 4. Takliflar va Pedagogik Muloqot ---
    {
      id: "proposals_recipients",
      cat: "proposals",
      method: "GET",
      path: "/api/proposals/recipients",
      title: "Dinamik qabul qiluvchilar ro'yxati",
      desc: "Bazada yangi qo'shilgan har qanday o'qituvchi va talaba shu zahoti chiqadigan dinamik ro'yxat (O'qituvchilar, guruhlar, talabalar).",
      role: "student, teacher, admin",
      principle: null,
      auth: true,
      body: null,
      response: {
        teachers: [
          { id: "usr_teacher_01", full_name: "Adiba Ikramova", email: "oqituvchi1@tilora.uz", role: "teacher", role_label: "O'qituvchi" },
          { id: "usr_admin_01", full_name: "Tizim Administratori", email: "admin@tilora.uz", role: "admin", role_label: "Administrator" }
        ],
        students: [
          { id: "usr_student_01", full_name: "Aziza Karimova", email: "talaba01@tilora.uz", role: "student", group_name: "302-guruh (Tajriba)" }
        ]
      }
    },
    {
      id: "proposals_list",
      cat: "proposals",
      method: "GET",
      path: "/api/proposals?tab=all&direction=all&status=all",
      title: "Takliflar ro'yxati va tablar soni",
      desc: "Multi-tab tizimi: Barchasi, Menga kelgan, Men yuborgan, Tizim (AI) takliflari va holat hisoblagichlari.",
      role: "student, teacher, admin",
      principle: "3-Qoida: Pedagogik Suverenitet",
      auth: true,
      body: null,
      response: {
        counts: { all: 12, inbox: 3, sent: 1, system: 8, pending: 5 },
        proposals: [
          {
            id: "prop_101",
            title: "Sillabusga keys kiritish taklifi",
            direction: "teacher_to_teacher",
            sender_name: "Adiba Ikramova",
            receiver_name: "Tizim Administratori",
            status: "pending",
            category: "methodology"
          }
        ]
      }
    },
    {
      id: "proposals_create",
      cat: "proposals",
      method: "POST",
      path: "/api/proposals",
      title: "Yangi taklif yuborish (barcha 4 yo'nalish)",
      desc: "O'qituvchilar o'zaro, talabadan o'qituvchiga, talabalar o'zaro (peer learning) yoki o'qituvchidan talabaga taklif kiritish.",
      role: "student, teacher, admin",
      principle: "3-Qoida: Hamkorlik va Suverenitet",
      auth: true,
      body: {
        receiver_id: "usr_admin_01",
        receiver_role: "teacher",
        proposal_type: "methodology",
        title: "Metodika yangilanishi bo'yicha taklif",
        proposal_text: "Talabalarning metakognitiv faolligini oshirish uchun har haftada bitta ochiq dars tavsiya etiladi.",
        basis: "Pedagogik tajriba sinov natijalari"
      },
      response: {
        status: "success",
        proposal: { id: "prop_uuid_123", status: "pending", direction: "teacher_to_admin" }
      }
    },
    {
      id: "proposals_approve",
      cat: "proposals",
      method: "POST",
      path: "/api/proposals/{id}/approve",
      title: "Taklifni qabul qilish / tasdiqlash",
      desc: "3-TAMOYIL: Qabul qiluvchi o'qituvchi taklifni tasdiqlaydi va pedagogik sharh qoldiradi. Yakuniy qaror o'qituvchida.",
      role: "teacher, admin",
      principle: "3-Qoida: Yakuniy qaror o'qituvchida",
      auth: true,
      body: {
        teacher_comment: "Metodik kengashda ma'qullandi va joriy etildi."
      },
      response: {
        status: "success",
        proposal: { id: "prop_uuid_123", status: "approved" }
      }
    },

    // --- 5. O'qituvchi va Sillabus ---
    {
      id: "teacher_subjects",
      cat: "teacher",
      method: "GET",
      path: "/api/teacher/subjects",
      title: "O'qituvchining fanlari ro'yxati",
      desc: "O'qituvchi yaratgan barcha o'quv fanlari, ularning sillabusi va biriktirilgan guruhlar.",
      role: "teacher, admin",
      principle: null,
      auth: true,
      body: null,
      response: [
        { id: "subj_01", name: "Ingliz tili akademik yozuvi (EAP)", code: "EAP-302", topics_count: 16 }
      ]
    },
    {
      id: "teacher_generate_syllabus",
      cat: "teacher",
      method: "POST",
      path: "/api/teacher/subjects/{id}/generate-syllabus",
      title: "AI yordamida 16 haftalik sillabus generatsiya qilish",
      desc: "Fanning nomi, yo'nalishi va maqsadidan kelib chiqib, DeepSeek AI 16 haftalik mavzular, ko'nikmalar va dars rejalarini yaratadi.",
      role: "teacher, admin",
      principle: "AI Yordamchi",
      auth: true,
      body: {
        total_weeks: 16,
        esp_focus: "academic_writing",
        target_cefr: "B2"
      },
      response: {
        status: "success",
        weeks_generated: 16
      }
    },

    // --- 6. Diagnostika Banki ---
    {
      id: "diag_questions",
      cat: "diagnostic",
      method: "GET",
      path: "/api/teacher-diagnostic/questions",
      title: "Diagnostika test savollari banki",
      desc: "CEFR 4 ko'nikmasi (Listening, Reading, Speaking, Writing) bo'yicha umumiy yoki fanlarga biriktirilgan savollar.",
      role: "teacher, admin",
      principle: null,
      auth: true,
      body: null,
      response: {
        questions: [
          { id: "dq_01", skill: "listening", cefr: "B1", question_text: "Listen and choose main idea", has_audio: true }
        ]
      }
    },
    {
      id: "diag_tts",
      cat: "diagnostic",
      method: "POST",
      path: "/api/teacher-diagnostic/tts",
      title: "AI yordamida matnni audio ovozga aylantirish (TTS)",
      desc: "Tinglab tushunish (listening) savollari uchun matnni professional inglizcha diksiya bilan audio faylga aylantirish.",
      role: "teacher, admin",
      principle: null,
      auth: true,
      body: {
        text: "The lecture will focus on formative assessment rubrics.",
        voice: "alloy"
      },
      response: {
        audio_url: "/uploads/audio/tts_preview_sample.mp3"
      }
    },

    // --- 7. Sun'iy Intellekt Vositalari ---
    {
      id: "ai_deepseek",
      cat: "ai",
      method: "POST",
      path: "/api/ai/deepseek-analyze",
      title: "DeepSeek AI bilan chuqur lingvistik tahlil",
      desc: "Matnni 4 ta akademik mezon (Task Achievement, Coherence, Lexis, Grammar) bo'yicha sun'iy intellekt tahlili va ball berish.",
      role: "student, teacher, admin",
      principle: "Shaffoflik & Sabab ko'rsatilgan",
      auth: true,
      body: {
        prompt: "Analyze the student text on formative assessment...",
        text: "Student essay sample..."
      },
      response: {
        evaluation: {
          task_achievement: 4,
          coherence_cohesion: 4,
          lexical_resource: 3.5,
          grammatical_accuracy: 3
        },
        feedback_summary: "Academic vocabulary is adequate; minor preposition errors noticed."
      }
    },

    // --- 8. DSc Tadqiqot Statistikasi ---
    {
      id: "research_overview",
      cat: "research",
      method: "GET",
      path: "/api/research/overview",
      title: "DSc 4-bobi matematik-statistik tahlillari",
      desc: "Tajriba va nazorat guruhlari (302 va 304) o'rtasidagi Styuydent t-kriteriyasi, ANOVA dispersiya tahlili va Bespalko K ko'rsatkichi.",
      role: "researcher, teacher, admin, guest, student",
      principle: "Akademik Dalillilik",
      auth: false,
      body: null,
      response: {
        sample_size: { total: 48, experimental: 24, control: 24 },
        t_criteria: { t_emp: 4.12, t_crit: 2.01, p_value: "< 0.001" },
        bespalko_k: { pre_test: 0.58, post_test: 0.81, threshold: 0.70 },
        significance: "Tajriba guruhi natijasi p < 0.001 darajada statistik jihatdan ishonchli."
      }
    },
    {
      id: "research_docx",
      cat: "research",
      method: "GET",
      path: "/api/research/export/docx",
      title: "Dissertatsiya jadvallarini Word (.docx) formatida yuklash",
      desc: "4.2-jadvaldan 4.9-jadvalgacha bo'lgan barcha ilmiy jadvallarni dissertatsiya formatidagi Word hujjati sifatida generatsiya qilib yuklash.",
      role: "researcher, admin",
      principle: null,
      auth: false,
      body: null,
      response: "Binary Stream (application/vnd.openxmlformats-officedocument.wordprocessingml.document)"
    },

    // --- 9. Tizim va Monitoring ---
    {
      id: "health_check",
      cat: "admin",
      method: "GET",
      path: "/health",
      title: "Tizim holati va 4 tamoyil monitoringi",
      desc: "Server ishchi holati, versiya va 4 ta pedagogik tamoyil faolligi holati.",
      role: "Barchasi",
      principle: null,
      auth: false,
      body: null,
      response: {
        status: "healthy",
        app: "TILORA Adaptiv Ta'lim Platformasi",
        version: "2.0.0",
        rules_active: ["1_ai_lock", "2_rationale_transparent", "3_teacher_sovereignty", "4_student_reflection"]
      }
    },
    {
      id: "network_info",
      cat: "admin",
      method: "GET",
      path: "/api/network-info",
      title: "Wi-Fi va Tarmoq IP manzillari",
      desc: "Lokal tarmoqdagi barcha faol IP manzillar (sinfda boshqa qurilmalar ulanishi uchun).",
      role: "Barchasi",
      principle: null,
      auth: false,
      body: null,
      response: {
        local_ips: ["127.0.0.1", "192.168.1.105"],
        port: 8010
      }
    }
  ];

  window.initApiDocs = function() {
    updateApiTokenBadge();
    renderApiEndpoints();
  };

  function updateApiTokenBadge() {
    const badge = document.getElementById("apiTokenStatusBadge");
    const text = document.getElementById("apiTokenStatusText");
    const token = STATE.token || localStorage.getItem("tilora_token");

    if (badge && text) {
      if (token) {
        badge.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10B981"></span> <span>Faol JWT Token mavjud (${escapeHtml(STATE.currentUser ? STATE.currentUser.full_name : 'Ulangan')})</span>`;
      } else {
        badge.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#F59E0B"></span> <span>Mehmon rejimi (Anonim)</span>`;
      }
    }
  }

  window.switchApiDocTab = function(tabName) {
    API_DOCS_STORE.activeTab = tabName;
    document.querySelectorAll(".api-doc-tab").forEach(btn => {
      if (btn.getAttribute("data-tab") === tabName) {
        btn.classList.add("active");
        btn.style.background = "";
        btn.style.color = "";
        btn.style.border = "";
      } else {
        btn.classList.remove("active");
        btn.style.background = "none";
        btn.style.color = "var(--ink)";
        btn.style.border = "1px solid var(--line)";
      }
    });

    document.querySelectorAll(".api-tab-content").forEach(content => {
      content.style.display = "none";
    });

    const activeContent = document.getElementById(`apiTabContent_${tabName}`);
    if (activeContent) {
      activeContent.style.display = "block";
    }

    if (tabName === "swagger") {
      const iframe = document.getElementById("swaggerIframe");
      if (iframe && !iframe.getAttribute("src")) {
        iframe.src = "/docs";
      }
    } else if (tabName === "keys") {
      if (typeof window.loadApiKeys === "function") {
        window.loadApiKeys();
      }
    }
  };

  window.setApiCategory = function(cat) {
    API_DOCS_STORE.selectedCategory = cat;
    document.querySelectorAll(".api-cat-btn").forEach(btn => {
      if (btn.getAttribute("data-cat") === cat) {
        btn.classList.add("active");
        btn.style.background = "var(--teal)";
        btn.style.color = "#fff";
      } else {
        btn.classList.remove("active");
        btn.style.background = "";
        btn.style.color = "";
      }
    });
    renderApiEndpoints();
  };

  window.filterApiEndpoints = function() {
    const searchInput = document.getElementById("apiSearchInput");
    const methodSelect = document.getElementById("apiMethodFilter");

    API_DOCS_STORE.searchQuery = (searchInput ? searchInput.value : "").trim().toLowerCase();
    API_DOCS_STORE.selectedMethod = methodSelect ? methodSelect.value : "ALL";

    renderApiEndpoints();
  };

  function renderApiEndpoints() {
    const container = document.getElementById("apiEndpointsContainer");
    if (!container) return;

    const query = API_DOCS_STORE.searchQuery;
    const cat = API_DOCS_STORE.selectedCategory;
    const method = API_DOCS_STORE.selectedMethod;

    const filtered = API_ENDPOINTS.filter(ep => {
      // 1. Kategoriya filtri
      if (cat !== 'all' && ep.cat !== cat) return false;
      // 2. Metod filtri
      if (method !== 'ALL' && ep.method !== method) return false;
      // 3. Matnli qidiruv
      if (query) {
        const text = (ep.path + " " + ep.title + " " + ep.desc + " " + ep.cat).toLowerCase();
        if (!text.includes(query)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align:center;padding:40px;color:var(--muted)">
          <div style="font-size:32px;margin-bottom:8px">🔍</div>
          <div style="font-size:15px;font-weight:600">Qidiruv bo'yicha hech qanday endpoint topilmadi</div>
          <div style="font-size:13px;margin-top:4px">Boshqa so'z bilan qidirib ko'ring yoki filtrlarni tozalang.</div>
        </div>
      `;
      return;
    }

    const methodColors = {
      GET: { bg: "rgba(13, 148, 136, 0.12)", color: "#0D9488", border: "#0D9488" },
      POST: { bg: "rgba(37, 99, 235, 0.12)", color: "#2563EB", border: "#2563EB" },
      PUT: { bg: "rgba(217, 119, 6, 0.12)", color: "#D97706", border: "#D97706" },
      DELETE: { bg: "rgba(225, 29, 72, 0.12)", color: "#E11D48", border: "#E11D48" }
    };

    container.innerHTML = filtered.map(ep => {
      const mc = methodColors[ep.method] || { bg: "#f3f4f6", color: "#374151", border: "#9ca3af" };
      const principleBadge = ep.principle ? `<span class="chip full" style="font-size:11px;background:#FEF3C7;color:#B45309;border:1px solid #FCD34D">⚖️ ${escapeHtml(ep.principle)}</span>` : '';
      const authBadge = ep.auth ? `<span class="chip part" style="font-size:11px">🔒 JWT Bearer</span>` : `<span class="chip none" style="font-size:11px">🌐 Ochiq</span>`;

      const bodyBlock = ep.body ? `
        <div style="margin-top:8px">
          <div style="font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase">Request Body (JSON):</div>
          <pre style="margin:4px 0 0;padding:8px 12px;border-radius:6px;background:var(--paper-2);border:1px solid var(--line);font-size:11.5px;line-height:1.4;overflow-x:auto;color:var(--ink)">${escapeHtml(JSON.stringify(ep.body, null, 2))}</pre>
        </div>
      ` : '';

      const respBlock = ep.response ? `
        <div style="margin-top:8px">
          <div style="font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase">Response Namunasi (JSON 200 OK):</div>
          <pre style="margin:4px 0 0;padding:8px 12px;border-radius:6px;background:var(--paper-2);border:1px solid var(--line);font-size:11.5px;line-height:1.4;overflow-x:auto;color:var(--teal)">${typeof ep.response === 'string' ? escapeHtml(ep.response) : escapeHtml(JSON.stringify(ep.response, null, 2))}</pre>
        </div>
      ` : '';

      return `
        <div class="card" style="padding:16px 20px;border-left:4px solid ${mc.color}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <span style="display:inline-block;padding:4px 10px;border-radius:6px;font-weight:800;font-size:12px;font-family:monospace;background:${mc.bg};color:${mc.color};border:1px solid ${mc.border}">${ep.method}</span>
              <code style="font-size:14.5px;font-weight:700;color:var(--ink);font-family:monospace">${escapeHtml(ep.path)}</code>
              ${principleBadge}
              ${authBadge}
              <span class="chip part" style="font-size:11px">👤 ${escapeHtml(ep.role)}</span>
            </div>

            <div style="display:flex;gap:8px;align-items:center">
              <button class="btn-primary" style="padding:5px 12px;font-size:12px;background:none;color:var(--ink);border:1px solid var(--line)" onclick="window.copyCurl('${ep.id}')">
                📋 cURL
              </button>
              <button class="btn-primary" style="padding:5px 14px;font-size:12px" onclick="window.loadEndpointIntoTester('${ep.id}')">
                ▶️ Sinash
              </button>
            </div>
          </div>

          <div style="margin-top:8px;font-size:14px;font-weight:600;color:var(--ink)">${escapeHtml(ep.title)}</div>
          <div style="margin-top:3px;font-size:13px;color:var(--ink-2);line-height:1.5">${escapeHtml(ep.desc)}</div>

          <details style="margin-top:10px;cursor:pointer">
            <summary style="font-size:12px;font-weight:700;color:var(--teal)">Ko'rsatish: Parametrlar va Namuna javob ▾</summary>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:8px">
              ${bodyBlock}
              ${respBlock}
            </div>
          </details>
        </div>
      `;
    }).join("");
  }

  window.copyCurl = function(id) {
    const ep = API_ENDPOINTS.find(e => e.id === id);
    if (!ep) return;

    const token = STATE.token || localStorage.getItem("tilora_token") || "YOUR_ACCESS_TOKEN";
    let cmd = `curl -X ${ep.method} "${window.location.origin}${ep.path}" \\\n`;
    if (ep.auth) {
      cmd += `  -H "Authorization: Bearer ${token}" \\\n`;
    }
    cmd += `  -H "Content-Type: application/json"`;
    if (ep.body && (ep.method === "POST" || ep.method === "PUT")) {
      cmd += ` \\\n  -d '${JSON.stringify(ep.body)}'`;
    }

    navigator.clipboard.writeText(cmd).then(() => {
      showToast("📋 cURL buyrug'i nusxalandi!", "success");
    }).catch(() => {
      alert("Nusxalash imkoni bo'lmadi");
    });
  };

  window.loadEndpointIntoTester = function(id) {
    const ep = API_ENDPOINTS.find(e => e.id === id);
    if (!ep) return;

    window.switchApiDocTab('tester');

    const methodInput = document.getElementById("apiTesterMethod");
    const urlInput = document.getElementById("apiTesterUrl");
    const bodyInput = document.getElementById("apiTesterBody");
    const authToggle = document.getElementById("apiTesterAuthToggle");

    if (methodInput) methodInput.value = ep.method;
    if (urlInput) urlInput.value = ep.path;
    if (authToggle) authToggle.checked = !!ep.auth;
    if (bodyInput) {
      bodyInput.value = ep.body ? JSON.stringify(ep.body, null, 2) : "";
    }
  };

  window.loadTesterPreset = function() {
    const select = document.getElementById("apiTesterPresetSelect");
    const val = select ? select.value : "";
    if (!val) return;

    const map = {
      get_recipients: { method: "GET", path: "/api/proposals/recipients", auth: true, body: "" },
      get_proposals: { method: "GET", path: "/api/proposals?tab=all", auth: true, body: "" },
      post_proposal: {
        method: "POST",
        path: "/api/proposals",
        auth: true,
        body: JSON.stringify({
          receiver_id: "usr_admin_01",
          receiver_role: "teacher",
          proposal_type: "methodology",
          title: "Amaliy mashg'ulot bo'yicha taklif",
          proposal_text: "Talabalar bilan seminar jarayonida qo'shimcha keys muhokamasi o'tkazish tavsiya qilinadi.",
          basis: "Metodik takomillashtirish"
        }, null, 2)
      },
      get_profile: { method: "GET", path: "/api/student/profile", auth: true, body: "" },
      get_path: { method: "GET", path: "/api/student/path", auth: true, body: "" },
      get_research_overview: { method: "GET", path: "/api/research/overview", auth: false, body: "" },
      get_subjects: { method: "GET", path: "/api/teacher/subjects", auth: true, body: "" },
      get_health: { method: "GET", path: "/health", auth: false, body: "" },
      get_network: { method: "GET", path: "/api/network-info", auth: false, body: "" }
    };

    const preset = map[val];
    if (preset) {
      document.getElementById("apiTesterMethod").value = preset.method;
      document.getElementById("apiTesterUrl").value = preset.path;
      document.getElementById("apiTesterAuthToggle").checked = preset.auth;
      document.getElementById("apiTesterBody").value = preset.body;
    }
  };

  window.apiTesterCopyToken = function() {
    const token = STATE.token || localStorage.getItem("tilora_token");
    if (!token) {
      showToast("Tizimda faol token mavjud emas. Avval tizimga kiring!", "warning");
      return;
    }
    navigator.clipboard.writeText(token).then(() => {
      showToast("🔑 JWT Token nusxalandi!", "success");
    });
  };

  window.apiTesterFormatBody = function() {
    const bodyInput = document.getElementById("apiTesterBody");
    if (!bodyInput || !bodyInput.value.trim()) return;
    try {
      const obj = JSON.parse(bodyInput.value);
      bodyInput.value = JSON.stringify(obj, null, 2);
    } catch (e) {
      showToast("JSON formatida xatolik bor!", "error");
    }
  };

  window.apiTesterCopyResponse = function() {
    const output = document.getElementById("apiTesterOutput");
    if (!output) return;
    navigator.clipboard.writeText(output.textContent).then(() => {
      showToast("📋 Javob nusxalandi!", "success");
    });
  };

  window.sendLiveApiRequest = async function() {
    const method = document.getElementById("apiTesterMethod").value;
    let url = document.getElementById("apiTesterUrl").value.trim();
    const useAuth = document.getElementById("apiTesterAuthToggle").checked;
    const rawHeaders = document.getElementById("apiTesterHeaders").value.trim();
    const rawBody = document.getElementById("apiTesterBody").value.trim();

    const output = document.getElementById("apiTesterOutput");
    const statusBadge = document.getElementById("apiTesterStatusBadge");
    const timeBadge = document.getElementById("apiTesterTimeBadge");

    if (!url) {
      showToast("Iltimos, URL manzilini kiriting!", "warning");
      return;
    }

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = window.location.origin + (url.startsWith("/") ? "" : "/") + url;
    }

    let headers = { "Content-Type": "application/json" };
    if (rawHeaders) {
      try {
        const parsed = JSON.parse(rawHeaders);
        headers = Object.assign(headers, parsed);
      } catch (e) {
        showToast("Headers JSON formati xato!", "error");
        return;
      }
    }

    if (useAuth) {
      const token = STATE.token || localStorage.getItem("tilora_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      } else {
        showToast("Diqqat: Faol login tokeni topilmadi!", "warning");
      }
    }

    output.innerHTML = `<div style="color:var(--muted);text-align:center;padding:30px">⏳ So'rov yuborilmoqda: ${escapeHtml(method)} ${escapeHtml(url)}...</div>`;
    statusBadge.style.display = "none";

    const startTime = performance.now();

    try {
      const options = {
        method: method,
        headers: headers
      };

      if ((method === "POST" || method === "PUT" || method === "PATCH") && rawBody) {
        options.body = rawBody;
      }

      const res = await fetch(url, options);
      const endTime = performance.now();
      const duration = Math.round(endTime - startTime);

      timeBadge.textContent = `${duration} ms`;
      statusBadge.style.display = "inline-block";
      statusBadge.textContent = `${res.status} ${res.statusText || (res.ok ? 'OK' : 'Error')}`;

      if (res.ok) {
        statusBadge.className = "chip full";
        statusBadge.style.background = "#DCFCE7";
        statusBadge.style.color = "#15803D";
      } else {
        statusBadge.className = "chip warn";
        statusBadge.style.background = "#FEE2E2";
        statusBadge.style.color = "#B91C1C";
      }

      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const json = await res.json();
        output.textContent = JSON.stringify(json, null, 2);
      } else {
        const text = await res.text();
        output.textContent = text;
      }
    } catch (err) {
      const endTime = performance.now();
      timeBadge.textContent = `${Math.round(endTime - startTime)} ms`;
      statusBadge.style.display = "inline-block";
      statusBadge.textContent = "Network Error";
      statusBadge.className = "chip warn";
      output.textContent = `[Xatolik]: Serverga ulanib bo'lmadi.\n${err.message}`;
    }
  };

  // ============================================================
  // API KALITLARI VA TOKENLAR BOSHQARUVI (API KEYS MANAGEMENT)
  // ============================================================
  let RAW_API_KEY_TEMP = "";

  window.loadApiKeys = async function() {
    const roleNotice = document.getElementById("apiKeyRoleNotice");
    const container = document.getElementById("apiKeysTableContainer");
    const statTotal = document.getElementById("apiKeyStatTotal");
    const statActive = document.getElementById("apiKeyStatActive");
    const statRevoked = document.getElementById("apiKeyStatRevoked");

    const token = STATE.token || localStorage.getItem("tilora_token");
    const currentUser = STATE.currentUser;
    const userRole = currentUser ? currentUser.role : "guest";

    // 1. Agar foydalanuvchi tizimga kirmagan bo'lsa yoki developer/admin bo'lmasa
    if (!token || (userRole !== "developer" && userRole !== "admin")) {
      if (roleNotice) {
        roleNotice.style.background = "var(--amber-soft)";
        roleNotice.style.borderColor = "rgba(217, 119, 6, 0.35)";
        roleNotice.innerHTML = `
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
            <div>
              <b style="color:#B45309">⚠️ Diqqat: API Kalitlarini boshqarish uchun Dasturchi (Developer) yoki Super Admin bo'lishingiz kerak.</b>
              <div style="font-size:12.5px;color:var(--ink-2);margin-top:2px">
                Hozirgi holat: <b>${escapeHtml(userRole)}</b>. API kalitlarini olish va integratsiya qilish uchun Dasturchi (Developer) yoki Super Admin profiliga kiring.
              </div>
            </div>
            <button class="btn-primary" style="padding:6px 14px;font-size:12px" onclick="window.openLoginModal && window.openLoginModal()">
              🔑 Tizimga kirish
            </button>
          </div>
        `;
      }
      if (container) {
        container.innerHTML = `
          <div style="text-align:center;padding:36px;color:var(--muted)">
            <div style="font-size:32px;margin-bottom:8px">🔒</div>
            <div style="font-size:15px;font-weight:600;color:var(--ink)">API Kalitlari faqat autentifikatsiyadan o'tgan dasturchilar uchun ko'rinadi</div>
            <div style="font-size:13px;margin-top:4px">Iltimos, yuqoridagi tugma orqali dasturchi yoki super admin profiliga kiring.</div>
          </div>
        `;
      }
      if (statTotal) statTotal.textContent = "0";
      if (statActive) statActive.textContent = "0";
      if (statRevoked) statRevoked.textContent = "0";
      return;
    }

    // Rol bo'yicha tushuntirish banneri
    if (roleNotice) {
      roleNotice.style.background = "var(--teal-soft)";
      roleNotice.style.borderColor = "rgba(13, 110, 110, 0.25)";
      if (userRole === "admin") {
        roleNotice.innerHTML = `
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:22px">👑</span>
            <div>
              <b style="color:var(--teal)">Super Administrator Paneli:</b> Siz platformadagi barcha dasturchilar va integratsiyalar uchun API kalitlarini generatsiya qila olasiz, bekor qila olasiz yoki yangi huquqlar biriktira olasiz.
            </div>
          </div>
        `;
      } else {
        roleNotice.innerHTML = `
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:22px">💻</span>
            <div>
              <b style="color:var(--teal)">Dasturchi (API Integrator) Xonasi:</b> Siz o'z ilovalaringiz, tashqi LMS (Moodle) yoki skriptlaringiz uchun shaxsiy API kalitlarini generatsiya qilib, ularni bekor qilishingiz yoki holatini kuzatishingiz mumkin.
            </div>
          </div>
        `;
      }
    }

    if (container) {
      container.innerHTML = `<div style="text-align:center;padding:24px;color:var(--muted)">⏳ API kalitlari yuklanmoqda...</div>`;
    }

    try {
      const res = await fetch(`${STATE.apiBaseUrl}/keys`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "API kalitlarni yuklab bo'lmadi");

      const keys = data.keys || [];
      const totalCount = keys.length;
      const activeCount = keys.filter(k => k.is_active).length;
      const revokedCount = totalCount - activeCount;

      if (statTotal) statTotal.textContent = totalCount;
      if (statActive) statActive.textContent = activeCount;
      if (statRevoked) statRevoked.textContent = revokedCount;

      if (keys.length === 0) {
        if (container) {
          container.innerHTML = `
            <div style="text-align:center;padding:36px;color:var(--muted)">
              <div style="font-size:36px;margin-bottom:8px">🔑</div>
              <div style="font-size:15px;font-weight:600;color:var(--ink)">Hozircha birorta ham API kalit yaratilmagan</div>
              <div style="font-size:13px;margin-top:4px;margin-bottom:14px">Integratsiya uchun yuqoridagi "Yangi API Kalit yaratish" tugmasini bosing.</div>
              <button class="btn-primary" style="padding:8px 18px;font-size:12.5px" onclick="window.openNewApiKeyModal()">➕ Birinchi kalitni yaratish</button>
            </div>
          `;
        }
        return;
      }

      // Kalitlar jadvalini yaratish
      let html = `
        <table style="width:100%;border-collapse:collapse;font-size:13px;text-align:left">
          <thead>
            <tr style="border-bottom:2px solid var(--line);color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:0.5px">
              <th style="padding:10px 12px">Kalit nomi & Maqsadi</th>
              <th style="padding:10px 12px">Prefiks (Identifikator)</th>
              <th style="padding:10px 12px">Roli</th>
              ${userRole === 'admin' ? '<th style="padding:10px 12px">Egasi (Foydalanuvchi)</th>' : ''}
              <th style="padding:10px 12px">Holati</th>
              <th style="padding:10px 12px">Limit</th>
              <th style="padding:10px 12px">So\'nggi foydalanish</th>
              <th style="padding:10px 12px;text-align:right">Amallar</th>
            </tr>
          </thead>
          <tbody>
      `;

      keys.forEach(k => {
        const statusBadge = k.is_active
          ? `<span class="chip full" style="font-size:11px;background:#DCFCE7;color:#15803D;border:1px solid #86EFAC">● Faol</span>`
          : (k.is_expired
              ? `<span class="chip warn" style="font-size:11px;background:#FEF3C7;color:#B45309;border:1px solid #FCD34D">⏳ Muddati o'tgan</span>`
              : `<span class="chip warn" style="font-size:11px;background:#FEE2E2;color:#B91C1C;border:1px solid #FCA5A5">✕ Bekor qilingan</span>`);

        const roleBadge = k.role === "admin"
          ? `<span class="chip part" style="font-size:11px;background:#FEF3C7;color:#92400E">👑 Admin</span>`
          : `<span class="chip part" style="font-size:11px;background:#EEF2FF;color:#4338CA">💻 Developer</span>`;

        html += `
          <tr style="border-bottom:1px solid var(--line);transition:background 0.15s">
            <td style="padding:12px;font-weight:600;color:var(--ink)">
              <div>${escapeHtml(k.name)}</div>
              <div style="font-size:11px;color:var(--muted);font-weight:normal">Yaratilgan: ${k.created_at || '-'}</div>
            </td>
            <td style="padding:12px">
              <code style="font-family:monospace;font-size:12.5px;padding:3px 6px;border-radius:4px;background:var(--surface-2);border:1px solid var(--line);color:var(--teal);font-weight:700">${escapeHtml(k.key_prefix)}</code>
            </td>
            <td style="padding:12px">${roleBadge}</td>
            ${userRole === 'admin' ? `
              <td style="padding:12px">
                <div style="font-weight:600;font-size:12.5px">${escapeHtml(k.user_name || '-')}</div>
                <div style="font-size:11px;color:var(--muted)">${escapeHtml(k.user_email || '')}</div>
              </td>
            ` : ''}
            <td style="padding:12px">${statusBadge}</td>
            <td style="padding:12px;font-size:12px;color:var(--ink-2)">${k.rate_limit || 120} req/m</td>
            <td style="padding:12px;font-size:11.5px;color:var(--muted)">${escapeHtml(k.last_used_at)}</td>
            <td style="padding:12px;text-align:right;white-space:nowrap">
              ${k.is_active ? `
                <button class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:none;color:var(--clay);border:1px solid var(--clay);margin-right:4px" onclick="window.revokeApiKey('${k.id}', ${jsArg(k.name)})">
                  Bekor qilish
                </button>
              ` : `
                <button class="btn-primary" style="padding:4px 10px;font-size:11.5px;background:none;color:#15803D;border:1px solid #15803D;margin-right:4px" onclick="window.activateApiKey('${k.id}')">
                  Faollashtirish
                </button>
              `}
              <button class="btn-primary" style="padding:4px 8px;font-size:11.5px;background:none;color:var(--muted);border:1px solid var(--line)" title="O'chirish" onclick="window.deleteApiKey('${k.id}', ${jsArg(k.name)})">
                🗑
              </button>
            </td>
          </tr>
        `;
      });

      html += `
          </tbody>
        </table>
      `;

      if (container) container.innerHTML = html;

    } catch (err) {
      if (container) {
        container.innerHTML = `
          <div style="padding:20px;text-align:center;color:var(--clay)">
            Xatolik yuz berdi: ${escapeHtml(err.message)}
          </div>
        `;
      }
    }
  };

  window.openNewApiKeyModal = async function() {
    const token = STATE.token || localStorage.getItem("tilora_token");
    const currentUser = STATE.currentUser;
    const userRole = currentUser ? currentUser.role : "guest";

    if (!token || (userRole !== "developer" && userRole !== "admin")) {
      showToast("API Kalit yaratish uchun avval Dasturchi yoki Super Admin sifatida tizimga kiring!", "warning");
      if (window.openLoginModal) window.openLoginModal();
      return;
    }

    const modal = document.getElementById("apiKeyModal");
    const targetUserWrap = document.getElementById("apiKeyTargetUserWrap");
    const targetUserSelect = document.getElementById("apiKeyTargetUserSelect");
    const roleWrap = document.getElementById("apiKeyRoleWrap");
    const nameInput = document.getElementById("apiKeyNameInput");

    if (nameInput) nameInput.value = "";

    // Super Admin bo'lsa, maqsadli foydalanuvchini tanlash imkoniyati
    if (userRole === "admin") {
      if (targetUserWrap) targetUserWrap.style.display = "block";
      if (roleWrap) roleWrap.style.display = "block";
      if (targetUserSelect) {
        targetUserSelect.innerHTML = `<option value="">O'zimga (Super Admin)</option>`;
        try {
          const res = await fetch(`${STATE.apiBaseUrl}/keys/developers-list`, {
            headers: { "Authorization": `Bearer ${token}` }
          });
          if (res.ok) {
            const list = await res.json();
            list.forEach(u => {
              const opt = document.createElement("option");
              opt.value = u.id;
              opt.textContent = `${u.full_name} (${u.email}) — ${u.role_label}`;
              targetUserSelect.appendChild(opt);
            });
          }
        } catch (e) {
          console.error("Developers list loading error:", e);
        }
      }
    } else {
      if (targetUserWrap) targetUserWrap.style.display = "none";
      if (roleWrap) roleWrap.style.display = "none";
    }

    if (modal) {
      modal.style.display = "flex";
      if (nameInput) setTimeout(() => nameInput.focus(), 100);
    }
  };

  window.closeApiKeyModal = function() {
    const modal = document.getElementById("apiKeyModal");
    if (modal) modal.style.display = "none";
  };

  window.submitNewApiKey = async function(e) {
    if (e && e.preventDefault) e.preventDefault();

    const token = STATE.token || localStorage.getItem("tilora_token");
    const userRole = STATE.currentUser ? STATE.currentUser.role : "guest";

    const nameInput = document.getElementById("apiKeyNameInput");
    const targetUserSelect = document.getElementById("apiKeyTargetUserSelect");
    const roleSelect = document.getElementById("apiKeyRoleSelect");
    const expiresSelect = document.getElementById("apiKeyExpiresSelect");
    const rateLimitSelect = document.getElementById("apiKeyRateLimitSelect");
    const submitBtn = document.getElementById("btnSubmitNewApiKey");

    const name = nameInput ? nameInput.value.trim() : "";
    if (!name) {
      showToast("Kalit nomini kiriting!", "warning");
      return;
    }

    const payload = {
      name: name,
      expires_days: parseInt(expiresSelect ? expiresSelect.value : "90", 10),
      rate_limit: parseInt(rateLimitSelect ? rateLimitSelect.value : "120", 10),
      role: (roleSelect && userRole === "admin") ? roleSelect.value : "developer"
    };

    if (userRole === "admin" && targetUserSelect && targetUserSelect.value) {
      payload.target_user_id = targetUserSelect.value;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Generatsiya qilinmoqda...";
    }

    try {
      const res = await fetch(`${STATE.apiBaseUrl}/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Kalit yaratishda xatolik yuz berdi");

      // Yaratilgan kalitni ko'rsatish
      RAW_API_KEY_TEMP = data.key.api_key;
      window.closeApiKeyModal();

      const resModal = document.getElementById("apiKeyResultModal");
      const rawInput = document.getElementById("apiKeyRawDisplayInput");
      const subTitle = document.getElementById("apiKeyResultSubTitle");

      if (rawInput) rawInput.value = RAW_API_KEY_TEMP;
      if (subTitle) {
        subTitle.textContent = `"${data.key.name}" kaliti yaratildi (${data.key.role} huquqi bilan)`;
      }

      if (resModal) resModal.style.display = "flex";

      showToast("🎉 API Kalit muvaffaqiyatli yaratildi!", "success");

      // Ro'yxatni qayta yangilash
      window.loadApiKeys();

    } catch (err) {
      showToast(err.message, "error");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "🔑 Kalitni generatsiya qilish";
      }
    }
  };

  window.copyRawApiKey = function() {
    const rawInput = document.getElementById("apiKeyRawDisplayInput");
    const key = rawInput ? rawInput.value : RAW_API_KEY_TEMP;
    if (!key) return;

    navigator.clipboard.writeText(key).then(() => {
      showToast("📋 Maxfiy API Kalit nusxalandi!", "success");
    }).catch(() => {
      if (rawInput) {
        rawInput.select();
        document.execCommand("copy");
        showToast("📋 Maxfiy API Kalit nusxalandi!", "success");
      }
    });
  };

  window.closeApiKeyResultModal = function() {
    const resModal = document.getElementById("apiKeyResultModal");
    if (resModal) resModal.style.display = "none";
    RAW_API_KEY_TEMP = "";
    const rawInput = document.getElementById("apiKeyRawDisplayInput");
    if (rawInput) rawInput.value = "";
  };

  window.revokeApiKey = async function(id, name) {
    if (!confirm(`Haqiqatan ham "${name}" API kalitini bekor qilmoqchimisiz? Kalit orqali qilingan keyingi so'rovlar rad etiladi.`)) {
      return;
    }

    const token = STATE.token || localStorage.getItem("tilora_token");
    try {
      const res = await fetch(`${STATE.apiBaseUrl}/keys/${id}/revoke`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Xatolik yuz berdi");

      showToast("Kalit bekor qilindi.", "success");
      window.loadApiKeys();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  window.activateApiKey = async function(id) {
    const token = STATE.token || localStorage.getItem("tilora_token");
    try {
      const res = await fetch(`${STATE.apiBaseUrl}/keys/${id}/activate`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Xatolik yuz berdi");

      showToast("Kalit qayta faollashtirildi!", "success");
      window.loadApiKeys();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  window.deleteApiKey = async function(id, name) {
    if (!confirm(`"${name}" API kalitini bazadan BUTUNLAY o'chirmoqchimisiz? Ushbu amalni qaytarib bo'lmaydi!`)) {
      return;
    }

    const token = STATE.token || localStorage.getItem("tilora_token");
    try {
      const res = await fetch(`${STATE.apiBaseUrl}/keys/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Xatolik yuz berdi");

      showToast("API Kalit butunlay o'chirildi.", "success");
      window.loadApiKeys();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();

