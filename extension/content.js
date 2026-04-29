/**
 * DarkShield content script: DOM scan, local ONNX or API classification, highlighting.
 */

let DS_API = "http://127.0.0.1:5001/api/classify";

const DS_EXPLANATIONS = {
  fake_urgency: "Uses scarcity or countdown language to rush a purchase decision.",
  confirm_shaming: "Guilt-inducing opt-out copy that frames declining as a bad choice.",
  hidden_costs: "Fees, taxes, or surcharges are disclosed late (often at checkout).",
  visual_interference: "UI styling hides or de-emphasises the user-friendly choice.",
  sneaking: "Extra items, fees, or subscriptions are added without clear consent.",
  forced_continuity: "Paid renewal after a trial or subscription without strong notice.",
  misdirection: "Attention is steered away from unsubscribe, skip, or cheaper options.",
  social_proof_manipulation: "Questionable popularity or review signals to build false trust.",
  bait_and_switch: "Advertised price or terms do not match what checkout shows.",
  roach_motel: "Easy to start or subscribe, difficult to cancel or delete an account.",
  none: "No strong dark-pattern cues detected in this snippet.",
};

let dsLastSend = 0;
let dsFlushTimer = null;
let dsObserver = null;

function dsCollectTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
      const t = node.nodeValue.trim();
      if (t.length < 12) return NodeFilter.FILTER_REJECT;
      const p = node.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      if (p.getAttribute("aria-hidden") === "true" || p.hidden) return NodeFilter.FILTER_REJECT;
      const tag = p.tagName;
      if (["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "SVG"].includes(tag)) {
        return NodeFilter.FILTER_REJECT;
      }
      if (p.closest && p.closest(".darkshield-highlight")) return NodeFilter.FILTER_REJECT;
      const style = window.getComputedStyle(p);
      if (
        style.display === "none" ||
        style.visibility === "hidden" ||
        style.opacity === "0" ||
        style.pointerEvents === "none"
      ) {
        return NodeFilter.FILTER_REJECT;
      }
      const rect = p.getBoundingClientRect();
      if (!rect || rect.width < 24 || rect.height < 10 || rect.height > 160) {
        return NodeFilter.FILTER_REJECT;
      }
      if (style.position === "fixed" && rect.height > 80) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const out = [];
  while (walker.nextNode()) {
    const n = walker.currentNode;
    const text = n.nodeValue.trim();
    const pf = dsPreFilterExport(text);
    if (!pf.shouldClassify) continue;
    out.push({ text, node: n, likely: pf.likelyCategory });
  }
  return out;
}

function dsCanSend(throttleMs) {
  const now = Date.now();
  if (now - dsLastSend < throttleMs) return false;
  dsLastSend = now;
  return true;
}

function dsHumanPatternName(label) {
  return String(label || "").replace(/_/g, " ");
}

function dsShowPageSummaryToast(flagged, enabled) {
  if (enabled === false || !flagged.length) return;
  const onceKey = "darkshield_toast_once_" + location.hostname;
  if (sessionStorage.getItem(onceKey)) return;

  const existing = document.getElementById("darkshield-page-toast");
  if (existing) existing.remove();

  const counts = {};
  for (const r of flagged) {
    const lab = r.label || "unknown";
    counts[lab] = (counts[lab] || 0) + 1;
  }
  const items = Object.keys(counts)
    .sort()
    .map((lab) => {
      const n = counts[lab];
      const name = dsHumanPatternName(lab);
      return `<li><strong>${name}</strong> — ${n} on this page</li>`;
    })
    .join("");

  const wrap = document.createElement("div");
  wrap.id = "darkshield-page-toast";
  wrap.setAttribute("role", "status");
  wrap.setAttribute("aria-live", "polite");
  wrap.innerHTML = `
    <div class="ds-toast-title">DarkShield — patterns detected</div>
    <div class="ds-toast-body">
      This page may use manipulative UI copy. Highlights are marked on the page — hover for details.
      Click the <strong>DarkShield</strong> icon in your toolbar for the site score and breakdown.
      <ul class="ds-toast-list">${items}</ul>
    </div>
    <div class="ds-toast-actions">
      <button type="button" data-ds-toast="dismiss">Dismiss</button>
    </div>
  `;
  document.body.appendChild(wrap);
  sessionStorage.setItem(onceKey, "1");

  wrap.querySelector('[data-ds-toast="dismiss"]').addEventListener("click", () => {
    wrap.remove();
  });
}

function dsNormText(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function dsFindHighlightElement(query = {}) {
  const all = Array.from(document.querySelectorAll(".darkshield-highlight"));
  if (!all.length) return null;
  const label = String(query.label || "").trim();
  const index = Number.isFinite(Number(query.index)) ? Number(query.index) : 0;
  const targetText = dsNormText(query.text || "");
  const byLabel = label ? all.filter((el) => el.dataset.dsCategory === label) : all;
  if (!byLabel.length) return null;
  if (targetText) {
    const byText = byLabel.filter((el) => dsNormText(el.textContent).includes(targetText));
    if (byText.length) return byText[Math.max(0, Math.min(index, byText.length - 1))];
  }
  return byLabel[Math.max(0, Math.min(index, byLabel.length - 1))];
}

function dsFocusHighlight(query) {
  const target = dsFindHighlightElement(query);
  if (!target) return false;
  target.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  target.classList.add("darkshield-focus-target");
  const tip = target.querySelector(".darkshield-tooltip");
  if (tip) tip.classList.add("darkshield-tooltip-visible");
  setTimeout(() => {
    target.classList.remove("darkshield-focus-target");
    if (tip) tip.classList.remove("darkshield-tooltip-visible");
  }, 1800);
  return true;
}

async function dsPostClassify(batch, pageUrl) {
  const res = await fetch(DS_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texts: batch.map((b) => b.text), url: pageUrl }),
  });
  if (!res.ok) throw new Error(`classify HTTP ${res.status}`);
  return res.json();
}

async function dsClassifyLocal(batch) {
  if (!globalThis.DSOnnxClassifier || typeof globalThis.DSOnnxClassifier.classifyBatch !== "function") {
    throw new Error("DSOnnxClassifier unavailable");
  }
  const texts = batch.map((b) => b.text);
  const raw = await globalThis.DSOnnxClassifier.classifyBatch(texts);
  return raw.map((r, idx) => ({
    text: batch[idx].text,
    label: r.label,
    confidence: r.confidence,
    explanation: DS_EXPLANATIONS[r.label] || DS_EXPLANATIONS.none,
    _method: r.method,
  }));
}

async function dsRunScan() {
  const cfg = await chrome.storage.local.get([
    "dsHighlightEnabled",
    "dsApiBase",
    "dsPageSummaryToast",
    "inference_mode",
  ]);
  if (cfg.dsHighlightEnabled === false) return;
  const showSummary = cfg.dsPageSummaryToast !== false;
  const mode = cfg.inference_mode || "local";

  const base = (cfg.dsApiBase || "http://127.0.0.1:5001").replace(/\/$/, "");
  DS_API = `${base}/api/classify`;

  const items = dsCollectTextNodes(document.body);
  if (!items.length) return;

  const maxBatch = 40;
  const slice = items.slice(0, maxBatch);
  const pageUrl = location.href;

  if (!dsCanSend(2000)) {
    if (!dsFlushTimer) {
      dsFlushTimer = setTimeout(() => {
        dsFlushTimer = null;
        dsRunScan().catch(() => {});
      }, 2100);
    }
    return;
  }

  try {
    let results;
    if (mode === "local") {
      console.log("[DarkShield] Running local inference — no data leaves your browser");
      try {
        results = await dsClassifyLocal(slice);
      } catch (e) {
        console.warn("DarkShield local classify failed, falling back to API", e);
        results = await dsPostClassify(slice, pageUrl);
      }
    } else {
      results = await dsPostClassify(slice, pageUrl);
    }

    const flagged = [];
    results.forEach((r, idx) => {
      const item = slice[idx];
      if (!item || !item.node) return;
      if (!r.label || r.label === "none") return;
      dsHighlighter.dsHighlightTextNode(item.node, r.label, r.confidence || 0, r.explanation || "");
      flagged.push(r);
    });

    const domain = location.hostname;
    const payload = {
      domain,
      url: pageUrl,
      patterns: flagged,
      updatedAt: Date.now(),
    };
    try {
      await chrome.storage.session.set({ dsLastScan: payload });
    } catch {
      await chrome.storage.local.set({ dsLastScan: payload });
    }
    chrome.runtime.sendMessage({
      type: "DS_UPDATE",
      count: flagged.length,
      domain,
    });
    dsShowPageSummaryToast(flagged, showSummary);
  } catch (e) {
    console.warn("DarkShield classify failed", e);
  }
}

function dsSetupObserver() {
  if (dsObserver) dsObserver.disconnect();
  let t = null;
  dsObserver = new MutationObserver(() => {
    if (t) clearTimeout(t);
    t = setTimeout(() => {
      dsRunScan().catch(() => {});
    }, 650);
  });
  dsObserver.observe(document.documentElement, { subtree: true, childList: true, characterData: true });
}

(async () => {
  await dsRunScan();
  dsSetupObserver();
})();

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.type !== "DS_FOCUS_PATTERN") return;
  const ok = dsFocusHighlight(msg.payload || {});
  sendResponse({ ok });
});
