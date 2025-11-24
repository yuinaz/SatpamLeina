/* dragdrop_phash.js — robust DnD v3.1 (with toasts)
   - Dropzone auto-detect/auto-create
   - Upload to multiple endpoints until success
   - Supports drop, click-to-browse, paste (URL/image)
   - Green check toast on success, red toast on error
*/
(() => {
  if (window.__SATPAMBOT_DND_V31__) return;
  window.__SATPAMBOT_DND_V31__ = true;

  const ENDPOINTS = [
    "/dashboard/api/phash/upload",
    "/api/phash/upload",
    "/dashboard/security/upload",
  ];

  // ---- Toasts --------------------------------------------------------------
  function ensureToastCSS() {
    if (document.getElementById("satpam-toast-style")) return;
    const css = `
      .satpam-toast-wrap{position:fixed;right:16px;top:16px;z-index:99999;display:flex;flex-direction:column;gap:8px}
      .satpam-toast{min-width:200px;max-width:420px;border-radius:12px;padding:10px 14px;box-shadow:0 8px 24px rgba(0,0,0,.25);
        color:#fff;display:flex;align-items:center;gap:10px;opacity:0;transform:translateY(-8px);transition:opacity .18s ease, transform .18s ease}
      .satpam-toast.show{opacity:1;transform:translateY(0)}
      .satpam-toast svg{width:18px;height:18px;flex:0 0 auto}
      .satpam-toast--ok{background:#059669}      /* emerald-600 */
      .satpam-toast--err{background:#dc2626}     /* red-600 */
      .satpam-toast__msg{line-height:1.3;font-size:14px;word-break:break-word}
    `.trim();
    const style = document.createElement("style");
    style.id = "satpam-toast-style";
    style.textContent = css;
    document.head.appendChild(style);
  }
  function toastContainer() {
    let box = document.querySelector(".satpam-toast-wrap");
    if (!box) {
      box = document.createElement("div");
      box.className = "satpam-toast-wrap";
      document.body.appendChild(box);
    }
    return box;
  }
  function iconOK() {
    return `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" fill="rgba(255,255,255,.12)"/>
      <path d="M7 12.5l3 3 7-7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
  }
  function iconERR() {
    return `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" fill="rgba(255,255,255,.12)"/>
      <path d="M8 8l8 8M16 8l-8 8" stroke="white" stroke-width="2" stroke-linecap="round"/>
    </svg>`;
  }
  function pushToast(msg, ok=true, ttl=2600) {
    ensureToastCSS();
    const box = toastContainer();
    const el = document.createElement("div");
    el.className = "satpam-toast " + (ok ? "satpam-toast--ok" : "satpam-toast--err");
    el.innerHTML = (ok ? iconOK() : iconERR()) + `<div class="satpam-toast__msg">${msg}</div>`;
    box.appendChild(el);
    // animate in
    requestAnimationFrame(() => el.classList.add("show"));
    // auto remove
    setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => el.remove(), 220);
    }, ttl);
  }

  // ---- Helpers -------------------------------------------------------------
  const qsFirst = (sels) => {
    for (const s of sels) {
      const el = document.querySelector(s);
      if (el) return el;
    }
    return null;
  };

  let zone = qsFirst(["#phish-dnd", "#dropZone", ".dropzone", "[data-dropzone]"]);
  if (!zone) {
    zone = document.createElement("div");
    zone.id = "dropZone";
    zone.className = "dropzone";
    zone.style.minHeight = "140px";
    zone.style.border = "2px dashed rgba(180, 180, 200, .6)";
    zone.style.borderRadius = "12px";
    zone.style.display = "flex";
    zone.style.alignItems = "center";
    zone.style.justifyContent = "center";
    zone.style.fontSize = "14px";
    zone.style.padding = "16px";
    zone.style.margin = "8px 0 16px";
    zone.style.userSelect = "none";
    zone.textContent = "Drop files here… (or click / paste URL)";
    const target = document.querySelector("main, .container, body");
    (target || document.body).prepend(zone);
  }

  // Hidden input for click-to-browse
  let picker = document.getElementById("dashPick");
  if (!picker) {
    picker = document.createElement("input");
    picker.type = "file";
    picker.multiple = true;
    picker.id = "dashPick";
    picker.style.display = "none";
    document.body.appendChild(picker);
  }

  const setBusy = (busy) => {
    zone.style.opacity = busy ? "0.7" : "";
    zone.style.pointerEvents = busy ? "none" : "";
    zone.dataset.busy = busy ? "1" : "";
  };

  const setDragover = (on) => {
    zone.style.background = on ? "rgba(80,120,255,.08)" : "";
    zone.style.boxShadow = on ? "0 0 0 2px rgba(80,120,255,.25) inset" : "";
  };

  const isUrl = (t) => {
    if (!t || typeof t !== "string") return false;
    try {
      const u = new URL(t.trim());
      return !!u.protocol && !!u.host;
    } catch (_) { return false; }
  };

  async function uploadFD(fd) {
    let lastErr = null;
    for (const url of ENDPOINTS) {
      try {
        const rsp = await fetch(url, { method: "POST", body: fd, credentials: "same-origin" });
        if (rsp.ok) return rsp;
        lastErr = new Error(`Upload failed: ${rsp.status} ${rsp.statusText}`);
      } catch (e) { lastErr = e; }
    }
    throw lastErr || new Error("Upload failed");
  }

  async function uploadFile(file) {
    const fd = new FormData();
    fd.append("file", file, file.name);
    return uploadFD(fd);
  }

  async function uploadUrl(url) {
    // Try JSON first, then fallback to form field "url"
    let lastErr = null;
    for (const ep of ENDPOINTS) {
      try {
        let rsp = await fetch(ep + "?mode=url", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url })
        });
        if (rsp.ok) return rsp;
        lastErr = new Error(`URL mode failed: ${rsp.status} ${rsp.statusText}`);
      } catch (e) { lastErr = e; }
      try {
        const fd = new FormData();
        fd.append("url", url);
        const rsp2 = await fetch(ep, { method: "POST", credentials: "same-origin", body: fd });
        if (rsp2.ok) return rsp2;
        lastErr = new Error(`Form mode failed: ${rsp2.status} ${rsp2.statusText}`);
      } catch (e) { lastErr = e; }
    }
    throw lastErr || new Error("URL upload failed");
  }

  async function handleFiles(list) {
    setBusy(true);
    let okCount = 0;
    try {
      for (const f of list) {
        await uploadFile(f);
        okCount++;
      }
      window.dispatchEvent(new CustomEvent("dnd:uploaded", { detail: { count: okCount } }));
      pushToast(okCount === 1 ? `Uploaded "${list[0].name}" ✓` : `Uploaded ${okCount} files ✓`, true);
    } catch (e) {
      const name = list && list[0] ? ` "${list[0].name}"` : "";
      pushToast(`Upload failed${name}`, false);
      console.error("[DnD] upload error:", e);
    } finally {
      setBusy(false);
    }
  }

  async function handleText(text) {
    const t = text && text.trim();
    if (!t) return;
    if (isUrl(t)) {
      setBusy(true);
      try {
        await uploadUrl(t);
        window.dispatchEvent(new CustomEvent("dnd:uploaded", { detail: { url: t } }));
        pushToast("URL uploaded ✓", true);
      } catch (e) {
        pushToast("URL upload failed", false);
        console.error("[DnD] url upload error:", e);
      } finally {
        setBusy(false);
      }
    }
  }

  // Event bindings
  zone.addEventListener("click", () => picker.click());
  picker.addEventListener("change", (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length) handleFiles(files);
    picker.value = "";
  });

  ["dragenter", "dragover"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragover(true);
    });
  });
  ["dragleave", "dragend"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragover(false);
    });
  });
  zone.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragover(false);
    const dt = e.dataTransfer;
    if (!dt) return;
    const files = Array.from(dt.files || []);
    if (files.length) return handleFiles(files);
    const text = dt.getData("text/plain");
    if (text) return handleText(text);
  });

  // Paste URL or image from clipboard
  document.addEventListener("paste", (e) => {
    const files = Array.from(e.clipboardData?.files || []);
    if (files.length) return handleFiles(files);
    const t = e.clipboardData?.getData("text/plain");
    if (t) return handleText(t);
  }, { capture: true });

  // Expose for debugging
  window.__satpam_dnd__ = { uploadUrl, uploadFile, pushToast };
})();