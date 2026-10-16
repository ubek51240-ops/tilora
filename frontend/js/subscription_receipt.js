/**
 * TILORA — PRO to'lov cheki (skrinshot / PDF) yuklash va ko'rish.
 *  - Obuna modalida chek faylini tanlash, ariza bilan birga yuborish (POST /auth/subscribe → POST /auth/subscribe/{id}/receipt)
 *  - "Mening to'lov arizalarim": holat, chekni keyinroq yuklash / ko'rish / o'chirish
 *  - Admin paneli: har bir to'lov kartasida "🧾 Chekni ko'rish" (autentifikatsiyali fetch → blob → modal)
 * app.js dagi submitSubscribePayment / renderAdminPayments / openSubscribeModal funksiyalari DOMContentLoaded dan keyin almashtiriladi.
 */
(function () {
  const esc = (s) => (window.escapeHtml ? window.escapeHtml(s == null ? "" : String(s)) : String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"));
  const toast = (m, t) => (window.showToast ? window.showToast(m, t) : console.log(m));
  const api = () => (window.STATE && STATE.apiBaseUrl) ? STATE.apiBaseUrl : "/api";
  const token = () => (window.STATE && STATE.token) ? STATE.token : "";
  const auth = () => ({ "Authorization": `Bearer ${token()}` });
  const $ = (id) => document.getElementById(id);
  const MAX_MB = 5;
  const ALLOWED = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
  const STATUS = {
    pending: ["⏳ Tasdiq kutilmoqda", "background:var(--amber-soft);color:var(--amber)"],
    approved: ["✓ Tasdiqlangan (PRO)", "background:var(--teal-soft);color:var(--teal)"],
    rejected: ["✕ Rad etilgan", "background:#FDE8E4;color:var(--clay)"],
  };
  let chosenFile = null;

  // ---------------- Fayl tanlash (modal) ----------------
  function validFile(f) {
    if (!f) return "Fayl tanlanmadi.";
    if (!ALLOWED.includes(f.type) && !/\.(jpe?g|png|webp|pdf)$/i.test(f.name)) return "Faqat JPG, PNG, WEBP yoki PDF chek yuklash mumkin.";
    if (f.size > MAX_MB * 1024 * 1024) return `Chek fayli ${MAX_MB} MB dan oshmasligi kerak.`;
    return null;
  }
  window.onSubscribeReceiptChosen = function (input) {
    const f = input.files && input.files[0];
    const err = validFile(f);
    if (err) { toast(err, "error"); window.clearSubscribeReceipt(); return; }
    chosenFile = f;
    markInvalid($("subReceiptDrop"), false);
    const label = $("subReceiptLabel"), prev = $("subReceiptPreview"), clr = $("subReceiptClear"), drop = $("subReceiptDrop");
    if (label) label.innerHTML = `<b>${esc(f.name)}</b><br><span style="font-size:11px;color:var(--muted)">${esc((f.size / 1024).toFixed(0))} KB · ariza bilan birga yuboriladi</span>`;
    if (drop) drop.style.borderStyle = "solid";
    if (clr) clr.style.display = "inline";
    if (prev) {
      if (f.type.startsWith("image/")) {
        const url = URL.createObjectURL(f);
        prev.src = url; prev.style.display = "block";
        prev.onload = () => URL.revokeObjectURL(url);
      } else { prev.style.display = "none"; }
    }
  };
  window.clearSubscribeReceipt = function () {
    chosenFile = null;
    const input = $("subReceiptFile"); if (input) input.value = "";
    const label = $("subReceiptLabel"), prev = $("subReceiptPreview"), clr = $("subReceiptClear"), drop = $("subReceiptDrop");
    if (label) label.innerHTML = `Click / Payme / bank ilovasidagi chek skrinshotini tanlang<br><span style="font-size:11px;color:var(--muted)">JPG, PNG, WEBP yoki PDF · ${MAX_MB} MB gacha</span>`;
    if (prev) { prev.style.display = "none"; prev.removeAttribute("src"); }
    if (clr) clr.style.display = "none";
    if (drop) drop.style.borderStyle = "dashed";
  };

  async function uploadReceipt(paymentId, file) {
    const fd = new FormData();
    fd.append("file", file, file.name);
    const res = await fetch(`${api()}/auth/subscribe/${encodeURIComponent(paymentId)}/receipt`, { method: "POST", headers: auth(), body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Chekni yuklashda xatolik");
    return data;
  }

  // ---------------- Ariza yuborish: chek + izoh MAJBURIY (bitta multipart so'rov) ----------------
  const NOTE_MIN = 5, NOTE_MAX = 500;
  function markInvalid(el, bad) { if (el) el.style.borderColor = bad ? "var(--clay)" : (el.id === "subReceiptDrop" ? "var(--amber)" : "var(--line)"); }
  function bindNoteCounter() {
    const ta = $("subUserNote"), cnt = $("subUserNoteCount");
    if (!ta || ta._bound) return;
    ta._bound = true;
    ta.addEventListener("input", () => { if (cnt) cnt.textContent = `${ta.value.length} / ${NOTE_MAX}`; markInvalid(ta, false); });
  }
  async function submitWithReceipt() {
    if (!window.STATE || !STATE.currentUser || !token()) { toast("Iltimos, avval profilga kiring!", "error"); return; }
    const methodEl = document.querySelector('input[name="payMethod"]:checked');
    const payMethod = methodEl ? methodEl.value : "click";
    const txInput = $("subTxId"), noteEl = $("subUserNote");
    const txId = txInput ? txInput.value.trim() : "";
    const note = noteEl ? noteEl.value.trim() : "";
    const btn = $("btnSubmitPaymentReq");
    const setBtn = (t, dis) => { if (btn) { btn.disabled = dis; btn.textContent = t; } };

    // Mijoz tomonidagi tekshiruv (server ham xuddi shuni majburiy qiladi)
    if (!chosenFile) { markInvalid($("subReceiptDrop"), true); toast("To'lov cheki majburiy: skrinshot yoki PDF faylni biriktiring.", "error"); return; }
    if (note.length < NOTE_MIN) { markInvalid(noteEl, true); if (noteEl) noteEl.focus(); toast(`Izoh majburiy: kamida ${NOTE_MIN} ta belgi yozing.`, "error"); return; }

    setBtn("Ariza va chek yuborilmoqda...", true);
    try {
      const fd = new FormData();
      fd.append("plan", "pro"); fd.append("payment_method", payMethod);
      fd.append("transaction_id", txId); fd.append("user_note", note);
      fd.append("file", chosenFile, chosenFile.name);
      const res = await fetch(`${api()}/auth/subscribe`, { method: "POST", headers: auth(), body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "To'lov arizasini yuborishda xatolik");
      if (txInput) txInput.value = "";
      if (noteEl) { noteEl.value = ""; const c = $("subUserNoteCount"); if (c) c.textContent = `0 / ${NOTE_MAX}`; }
      window.clearSubscribeReceipt();
      toast("👑 To'lov arizangiz va chek qabul qilindi! Super Admin tasdiqlashi bilan hisobingiz PRO ga o'tadi.", "success");
      await renderHistory();
      if (window.closeSubscribeModal) window.closeSubscribeModal();
    } catch (err) {
      toast(err.message || "To'lov arizasini yuborishda xatolik", "error");
    } finally {
      setBtn("💳 To'lov qildim, PRO arizasini yuborish →", false);
    }
  }

  // ---------------- Mening to'lov arizalarim ----------------
  async function renderHistory() {
    const box = $("subPaymentsHistory");
    if (!box || !token()) return;
    try {
      const res = await fetch(`${api()}/auth/subscription-status`, { headers: auth() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      const pays = d.payments || [];
      if (!pays.length) { box.innerHTML = ""; return; }
      box.innerHTML = `<div style="font-size:12.5px;font-weight:700;margin:4px 0 6px">Mening to'lov arizalarim</div>
        <div style="display:flex;flex-direction:column;gap:6px">${pays.map(p => {
          const st = STATUS[p.status] || [p.status, ""];
          const canUpload = p.status === "pending";
          return `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);font-size:12px">
            <span style="color:var(--muted)">${esc(p.created_at)}</span>
            <b>${esc(p.amount)} $</b> · ${esc((p.payment_method || "").toUpperCase())}
            <span style="padding:2px 8px;border-radius:9px;font-size:11px;font-weight:700;${st[1]}">${esc(st[0])}</span>
            ${p.has_receipt ? `<span style="color:var(--teal);font-size:11px">🧾 chek yuklangan</span>` : `<span style="color:var(--clay);font-size:11px">chek yo'q</span>`}
            <span style="flex:1"></span>
            ${p.has_receipt ? `<button type="button" class="btn-preset gen-preset" onclick="window.viewPaymentReceipt(${window.jsArg ? jsArg(p.id) : `'${p.id}'`})">Ko'rish</button>` : ""}
            ${canUpload ? `<label class="btn-preset gen-preset" style="cursor:pointer;margin:0">Chekni almashtirish<input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" style="display:none" onchange="window.uploadReceiptFor(${window.jsArg ? jsArg(p.id) : `'${p.id}'`}, this)"></label>` : ""}
            ${p.user_note ? `<div style="flex-basis:100%;color:var(--ink-2)"><b>Sizning izohingiz:</b> ${esc(p.user_note)}</div>` : ""}
            ${p.admin_note ? `<div style="flex-basis:100%;padding:6px 8px;border-radius:6px;${p.status === "rejected" ? "background:#FDE8E4;color:var(--clay)" : "background:var(--surface-2);color:var(--ink-2)"}"><b>${p.status === "rejected" ? "Rad etish sababi (admin izohi)" : "Admin izohi"}:</b> ${esc(p.admin_note)}</div>` : ""}
          </div>`;
        }).join("")}</div>`;
    } catch (e) {
      box.innerHTML = `<div style="font-size:12px;color:var(--muted)">Arizalar ro'yxati yuklanmadi (${esc(e.message)}).</div>`;
    }
  }
  window.uploadReceiptFor = async function (paymentId, input) {
    const f = input.files && input.files[0];
    const err = validFile(f);
    if (err) { toast(err, "error"); input.value = ""; return; }
    try {
      await uploadReceipt(paymentId, f);
      toast("🧾 Chek yuklandi. Admin ko'rib chiqadi.", "success");
      await renderHistory();
    } catch (e) { toast(e.message, "error"); }
    input.value = "";
  };

  // ---------------- Admin: rad etish — sabab (izoh) majburiy ----------------
  function ensureRejectModal() {
    let m = $("rejectPaymentModal");
    if (m) return m;
    m = document.createElement("div");
    m.id = "rejectPaymentModal";
    m.style.cssText = "display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.65);z-index:9999999;align-items:center;justify-content:center;padding:16px;box-sizing:border-box";
    m.innerHTML = `<div style="background:var(--card);border-radius:14px;padding:20px;max-width:460px;width:100%;border:1px solid var(--line);display:flex;flex-direction:column;gap:10px">
        <b style="font-size:16px">✕ To'lov arizasini rad etish</b>
        <div id="rejectPaymentWho" style="font-size:12.5px;color:var(--muted)"></div>
        <label style="font-size:12.5px;font-weight:600">Rad etish sababi (foydalanuvchi ko'radi) <span style="color:var(--clay)">* majburiy</span></label>
        <textarea id="rejectPaymentNote" rows="4" maxlength="500" placeholder="Masalan: Chekdagi summa 10 $ ga to'g'ri kelmaydi / chek o'qilmayapti, aniqroq skrinshot yuboring" style="width:100%;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-sizing:border-box;font-size:13px;font-family:inherit;resize:vertical"></textarea>
        <div id="rejectPaymentErr" style="font-size:12px;color:var(--clay);display:none"></div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button type="button" class="btn-preset gen-preset" onclick="window.closeRejectPayment()">Bekor qilish</button>
          <button type="button" id="rejectPaymentSubmit" class="btn-primary" style="background:var(--clay);color:#fff;border:none;font-size:13px;padding:7px 16px;font-weight:700">✕ Rad etish</button>
        </div></div>`;
    m.addEventListener("click", (e) => { if (e.target === m) window.closeRejectPayment(); });
    document.body.appendChild(m);
    return m;
  }
  window.closeRejectPayment = function () { const m = $("rejectPaymentModal"); if (m) m.style.display = "none"; };
  window.rejectPayment = function (paymentId, userName) {
    const m = ensureRejectModal();
    const ta = $("rejectPaymentNote"), err = $("rejectPaymentErr"), btn = $("rejectPaymentSubmit");
    ta.value = ""; err.style.display = "none";
    $("rejectPaymentWho").textContent = userName ? `Foydalanuvchi: ${userName}` : "";
    m.style.display = "flex";
    setTimeout(() => ta.focus(), 50);
    btn.onclick = async () => {
      const note = ta.value.trim();
      if (note.length < 3) { err.textContent = "Rad etish sababini yozing (kamida 3 belgi)."; err.style.display = "block"; ta.style.borderColor = "var(--clay)"; return; }
      btn.disabled = true;
      try {
        const res = await fetch(`${api()}/admin/payments/${encodeURIComponent(paymentId)}/reject`, {
          method: "POST", headers: { "Content-Type": "application/json", ...auth() }, body: JSON.stringify({ admin_note: note })
        });
        const d = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Rad etishda xatolik");
        window.closeRejectPayment();
        toast("To'lov arizasi rad etildi, sabab foydalanuvchiga ko'rinadi.", "info");
        if (window.loadAdminDashboard) window.loadAdminDashboard();
      } catch (e) { err.textContent = e.message; err.style.display = "block"; }
      finally { btn.disabled = false; }
    };
  };

  // ---------------- Chekni ko'rish (egasi yoki admin) ----------------
  function ensureViewer() {
    let m = $("receiptViewerModal");
    if (m) return m;
    m = document.createElement("div");
    m.id = "receiptViewerModal";
    m.style.cssText = "display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.75);z-index:9999999;align-items:center;justify-content:center;padding:16px;box-sizing:border-box";
    m.innerHTML = `<div style="background:var(--card);border-radius:14px;padding:16px;max-width:860px;width:100%;max-height:92vh;display:flex;flex-direction:column;gap:10px;border:1px solid var(--line);position:relative">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
          <b id="receiptViewerTitle" style="font-size:15px">🧾 To'lov cheki</b>
          <span style="flex:1"></span>
          <a id="receiptViewerDownload" class="btn-preset gen-preset" href="#" download="chek" style="text-decoration:none">⬇ Yuklab olish</a>
          <button type="button" class="btn-preset gen-preset" onclick="window.closeReceiptViewer()">Yopish ✕</button>
        </div>
        <div id="receiptViewerBody" style="flex:1;min-height:200px;overflow:auto;display:flex;align-items:center;justify-content:center;background:var(--surface-2);border-radius:10px"></div>
      </div>`;
    m.addEventListener("click", (e) => { if (e.target === m) window.closeReceiptViewer(); });
    document.body.appendChild(m);
    return m;
  }
  let currentBlobUrl = null;
  window.viewPaymentReceipt = async function (paymentId, title) {
    const m = ensureViewer();
    const body = $("receiptViewerBody");
    body.innerHTML = `<div style="color:var(--muted);font-size:13px;padding:30px">⏳ Chek yuklanmoqda...</div>`;
    $("receiptViewerTitle").textContent = title ? `🧾 Chek — ${title}` : "🧾 To'lov cheki";
    m.style.display = "flex";
    try {
      const res = await fetch(`${api()}/auth/subscribe/${encodeURIComponent(paymentId)}/receipt`, { headers: auth() });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `HTTP ${res.status}`); }
      const blob = await res.blob();
      if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl = URL.createObjectURL(blob);
      const dl = $("receiptViewerDownload");
      const isPdf = blob.type === "application/pdf";
      dl.href = currentBlobUrl; dl.download = `chek_${String(paymentId).slice(0, 8)}${isPdf ? ".pdf" : (blob.type === "image/png" ? ".png" : (blob.type === "image/webp" ? ".webp" : ".jpg"))}`;
      body.innerHTML = isPdf
        ? `<iframe src="${currentBlobUrl}" title="Chek (PDF)" style="width:100%;height:70vh;border:none;border-radius:10px"></iframe>`
        : `<img src="${currentBlobUrl}" alt="To'lov cheki" style="max-width:100%;max-height:75vh;border-radius:8px">`;
    } catch (e) {
      body.innerHTML = `<div style="color:var(--clay);font-size:13px;padding:30px">Chek ochilmadi: ${esc(e.message)}</div>`;
    }
  };
  window.closeReceiptViewer = function () {
    const m = $("receiptViewerModal"); if (m) m.style.display = "none";
    if (currentBlobUrl) { URL.revokeObjectURL(currentBlobUrl); currentBlobUrl = null; }
  };

  // ---------------- Admin: to'lov kartalariga chek tugmasi ----------------
  function renderAdminPaymentsWithReceipt(payments) {
    const container = $("adminPaymentsList");
    if (!container) return;
    if (!payments || !payments.length) {
      container.innerHTML = `<div class="card" style="text-align:center;padding:36px;color:var(--muted)">
        <div style="font-size:36px;margin-bottom:8px">💳</div>
        <div style="font-size:16px;font-weight:600;color:var(--ink)">Hozircha to'lov arizalari yo'q</div>
        <div style="font-size:13px;margin-top:4px">Foydalanuvchilar PRO obunaga to'lov qilganda shu yerda ko'rinadi.</div></div>`;
      return;
    }
    const J = (v) => (window.jsArg ? jsArg(v) : `'${String(v).replace(/'/g, "")}'`);
    container.innerHTML = payments.map(p => {
      const isPending = p.status === "pending";
      const st = STATUS[p.status] || [p.status, ""];
      const name = p.user_name || p.user_email;
      return `<div class="card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;border-left:4px solid ${isPending ? 'var(--amber)' : (p.status === 'approved' ? 'var(--teal)' : 'var(--line)')}">
        <div style="min-width:240px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">
            <span style="font-weight:700;font-size:15px;color:var(--ink)">${esc(name)}</span>
            <span style="font-size:12px;font-weight:700;color:var(--teal)">${esc(Number(p.amount || 0).toLocaleString())} $</span>
            <span style="padding:3px 8px;border-radius:10px;font-size:11.5px;font-weight:700;${st[1]}">${esc(st[0])}</span>
            <span style="font-size:11px;color:var(--muted)">${esc(p.created_at)}</span>
          </div>
          <div style="font-size:13px;color:var(--ink-2);line-height:1.5">
            <b>To'lov usuli:</b> ${esc((p.payment_method || '').toUpperCase())} · <b>Tranzaksiya / Chek ID:</b> <code>${esc(p.transaction_id || "Kiritilmagan")}</code> · <b>Roli:</b> ${esc(p.role)}
            ${p.user_email ? ` · <span style="color:var(--muted)">${esc(p.user_email)}</span>` : ""}
          </div>
          <div style="font-size:12.5px;margin-top:4px">
            ${p.has_receipt
              ? `<span style="color:var(--teal);font-weight:600">🧾 Chek yuklangan</span>`
              : `<span style="color:var(--clay)">🧾 Chek yuklanmagan</span> <span style="color:var(--muted)">— tranzaksiya raqami bo'yicha tekshiring</span>`}
            ${p.user_note ? `<div style="margin-top:4px;padding:6px 8px;border-radius:6px;background:var(--surface-2);color:var(--ink-2)"><b>Foydalanuvchi izohi:</b> ${esc(p.user_note)}</div>` : ""}
            ${p.admin_note ? `<div style="margin-top:4px;color:${p.status === "rejected" ? "var(--clay)" : "var(--muted)"}"><b>Admin izohi${p.status === "rejected" ? " (rad etish sababi)" : ""}:</b> ${esc(p.admin_note)}</div>` : ""}
          </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${p.has_receipt ? `<button class="btn-primary" style="background:var(--surface-2);color:var(--teal);border:1px solid var(--teal);font-size:12.5px;padding:6px 14px" onclick="window.viewPaymentReceipt(${J(p.id)}, ${J(name)})">🧾 Chekni ko'rish</button>` : ""}
          ${isPending ? `
            <button class="btn-primary" style="background:none;color:var(--clay);border:1px solid var(--clay);font-size:12.5px;padding:6px 14px" onclick="window.rejectPayment(${J(p.id)}, ${J(name)})">✕ Rad etish (izoh bilan)</button>
            <button class="btn-primary" style="background:var(--amber);color:#fff;border:none;font-size:12.5px;padding:6px 16px;font-weight:700" onclick="window.approvePayment(${J(p.id)}, ${J(name)})">👑 Tasdiqlash (PRO ga o'tkazish)</button>` : ""}
        </div>
      </div>`;
    }).join("");
  }

  // ---------------- app.js funksiyalarini almashtirish (initAuth DOMContentLoaded da ishlaydi) ----------------
  function install() {
    window.submitSubscribePayment = submitWithReceipt;
    bindNoteCounter();
    window.renderAdminPayments = renderAdminPaymentsWithReceipt;
    const origOpen = window.openSubscribeModal;
    window.openSubscribeModal = function () {
      if (typeof origOpen === "function") origOpen.apply(this, arguments);
      const modal = $("subscribeModal");
      if (modal && modal.style.display !== "none") renderHistory();
    };
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => setTimeout(install, 0));
  } else {
    setTimeout(install, 0);
  }
})();
