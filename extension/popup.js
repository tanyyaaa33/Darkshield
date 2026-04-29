const DS_API_DEFAULT = "http://127.0.0.1:5001";

/** Mirrors ``api/routes.py`` EXPLANATIONS for the popup detailed view. */
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

const DS_PATTERN_META = {
  fake_urgency: { name: "Urgency pressure", icon: "⏳", example: "Only 2 left! Offer ends in 10 minutes." },
  confirm_shaming: { name: "Guilt-based persuasion", icon: "😬", example: "No thanks, I like paying full price." },
  hidden_costs: { name: "Late fee reveal", icon: "💸", example: "Handling fee appears only at checkout." },
  visual_interference: { name: "Interface distraction", icon: "🧩", example: "The safe option is hard to see or click." },
  sneaking: { name: "Sneaky additions", icon: "🛒", example: "Extra add-on is preselected in cart." },
  forced_continuity: { name: "Auto-renew pressure", icon: "🔁", example: "Trial silently converts to paid plan." },
  misdirection: { name: "Attention steering", icon: "🧭", example: "Skip link is hidden while CTA is prominent." },
  social_proof_manipulation: { name: "Trust signal manipulation", icon: "👥", example: "Questionable popularity counter boosts urgency." },
  bait_and_switch: { name: "Offer mismatch", icon: "🎣", example: "Displayed price changes later in checkout." },
  roach_motel: { name: "Hard-to-exit flow", icon: "🚪", example: "Easy to join, difficult to cancel." },
};

/** Aligns with ``ml/compliance/regulatory_mapper.py`` HIGH-severity patterns. */
const DS_HIGH_REGULATORY = new Set([
  "fake_urgency",
  "confirm_shaming",
  "hidden_costs",
  "sneaking",
  "forced_continuity",
  "bait_and_switch",
  "roach_motel",
]);

function dsHumanPattern(label) {
  if (DS_PATTERN_META[label]) return DS_PATTERN_META[label].name;
  return String(label || "unknown").replace(/_/g, " ");
}

function dsPatternIcon(label) {
  return (DS_PATTERN_META[label] && DS_PATTERN_META[label].icon) || "•";
}

async function dsJumpToPattern(tabId, patternQuery) {
  if (!tabId || !patternQuery) return;
  try {
    const response = await chrome.tabs.sendMessage(tabId, {
      type: "DS_FOCUS_PATTERN",
      payload: patternQuery,
    });
    if (response && response.ok) return;
  } catch {
    // Best effort only: content script may be unavailable on this page.
  }
  alert("Could not jump to highlighted text on this page. Reload the tab and try again.");
}

function dsRenderDetailedView(patterns, tabId) {
  const wrap = document.getElementById("ds-details");
  if (!wrap) return;
  wrap.innerHTML = "";
  const detailedOn = document.getElementById("ds-detailed-toggle")?.checked ?? false;
  if (!Array.isArray(patterns) || patterns.length === 0) {
    wrap.innerHTML = `<div class="label" style="text-align:left">No flagged snippets to show yet.</div>`;
    return;
  }
  const byLabel = new Map();
  for (const p of patterns) {
    const lab = p.label || "unknown";
    if (lab === "none" || lab === "unknown") continue;
    if (!byLabel.has(lab)) byLabel.set(lab, []);
    byLabel.get(lab).push(p);
  }
  const ordered = [...byLabel.entries()].sort((a, b) => b[1].length - a[1].length);
  for (const [lab, items] of ordered) {
    const human = dsHumanPattern(lab);
    const expl =
      (items[0] && items[0].explanation) || DS_EXPLANATIONS[lab] || DS_EXPLANATIONS.none;
    const det = document.createElement("details");
    det.open = detailedOn ? ordered.length <= 4 : false;
    const sum = document.createElement("summary");
    sum.textContent = `${dsPatternIcon(lab)} ${human} (${items.length} on this page)`;
    det.appendChild(sum);
    const pExpl = document.createElement("p");
    pExpl.className = "ds-detail-expl";
    pExpl.innerHTML = `
      <strong>What this means:</strong> ${expl}<br/>
      <strong>Why it matters:</strong> This wording can nudge decisions using pressure or friction.<br/>
      <strong>Example:</strong> ${(DS_PATTERN_META[lab] && DS_PATTERN_META[lab].example) || "See snippets below."}
    `;
    det.appendChild(pExpl);
    if (detailedOn) {
      items.forEach((item, idx) => {
        const meta = document.createElement("div");
        meta.className = "ds-snippet-meta";
        const c = item.confidence != null ? Number(item.confidence).toFixed(3) : "—";
        const method = item._method || item.method || "—";
        meta.textContent = `Snippet ${idx + 1} · confidence ${c} · method ${method}`;
        det.appendChild(meta);
        const pre = document.createElement("div");
        pre.className = "ds-snippet";
        pre.textContent = (item.text || "").trim() || "(empty)";
        det.appendChild(pre);
        const jumpBtn = document.createElement("button");
        jumpBtn.type = "button";
        jumpBtn.className = "ds-jump-btn";
        jumpBtn.textContent = "Show on page";
        jumpBtn.addEventListener("click", () => {
          dsJumpToPattern(tabId, {
            label: lab,
            text: item.text || "",
            index: idx,
          });
        });
        det.appendChild(jumpBtn);
      });
    }
    wrap.appendChild(det);
  }
  if (wrap.children.length === 0) {
    wrap.innerHTML = `<div class="label" style="text-align:left">No non-none patterns in the last scan.</div>`;
  }
}

function dsRiskLabel(score) {
  if (score <= 30) return { text: "Low manipulation risk", color: "#00d58a" };
  if (score <= 60) return { text: "Moderate manipulation risk", color: "#ffbe3d" };
  if (score <= 80) return { text: "High manipulation risk", color: "#ff7a3d" };
  return { text: "Severe manipulation risk", color: "#ff4f6d" };
}

async function dsGetActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function dsLoad() {
  const cfg = await chrome.storage.local.get(["dsApiBase", "dsHighlightEnabled", "dsDetailedView"]);
  const api = cfg.dsApiBase || DS_API_DEFAULT;
  document.getElementById("ds-api").textContent = api;

  const tab = await dsGetActiveTab();
  const url = tab?.url || "";
  let domain = "—";
  try {
    domain = new URL(url).hostname;
  } catch {
    domain = "—";
  }
  document.getElementById("ds-domain").textContent = domain;

  let scan = null;
  try {
    const s = await chrome.storage.session.get(["dsLastScan"]);
    scan = s.dsLastScan;
  } catch {
    const s2 = await chrome.storage.local.get(["dsLastScan"]);
    scan = s2.dsLastScan;
  }

  const breakdownEl = document.getElementById("ds-breakdown");
  breakdownEl.innerHTML = "";

  if (scan && scan.domain === domain && Array.isArray(scan.patterns)) {
    const rowFocusCounter = new Map();
    const counts = new Map();
    for (const p of scan.patterns) {
      const k = p.label || "unknown";
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    const total = [...counts.values()].reduce((a, b) => a + b, 0) || 1;
    for (const [k, v] of [...counts.entries()].sort((a, b) => b[1] - a[1])) {
      const pct = Math.round((v / total) * 100);
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `<div>${dsPatternIcon(k)} ${dsHumanPattern(k)} <span class="label">(${pct}%)</span></div><div class="badge">${v}</div>`;
      row.title = "Click to jump to a highlighted match on the page";
      row.addEventListener("click", () => {
        const nextIdx = rowFocusCounter.get(k) || 0;
        rowFocusCounter.set(k, nextIdx + 1);
        dsJumpToPattern(tab?.id, { label: k, index: nextIdx });
      });
      breakdownEl.appendChild(row);
    }
    if (counts.size === 0) {
      breakdownEl.innerHTML = `<div class="label">No patterns flagged on this page yet.</div>`;
    }

    dsRenderDetailedView(scan.patterns, tab?.id);

    const regWrap = document.getElementById("ds-regulatory-wrap");
    const regEl = document.getElementById("ds-regulatory");
    let highHit = null;
    for (const p of scan.patterns) {
      const lab = p.label || "";
      if (DS_HIGH_REGULATORY.has(lab)) {
        highHit = lab;
        break;
      }
    }
    if (highHit) {
      regWrap.style.display = "block";
      const human = dsHumanPattern(highHit);
      regEl.innerHTML = `⚖️ Potential regulatory concern detected: <strong>${human}</strong>. Educational only — not legal advice.
        <a href="https://www.ftc.gov/news-events/topics/truth-advertising-consumer-issues/dark-patterns" target="_blank" rel="noopener">Learn more</a>`;
      regEl.title =
        "Dark patterns in this category have appeared in regulator guidance and enforcement themes (e.g. urgency, subscriptions, opt-out shaming).";
    } else {
      regWrap.style.display = "none";
    }
  } else {
    breakdownEl.innerHTML = `<div class="label">No scan data for this tab yet. Load a product page and wait ~2s.</div>`;
    dsRenderDetailedView([], tab?.id);
    document.getElementById("ds-regulatory-wrap").style.display = "none";
  }

  let score = 0;
  try {
    const res = await fetch(`${api}/api/site-score?domain=${encodeURIComponent(domain)}`);
    const data = await res.json();
    score = Number(data.manipulation_score || 0);
  } catch {
    score = 0;
  }

  const gauge = document.getElementById("ds-gauge");
  const risk = dsRiskLabel(score);
  gauge.style.setProperty("--score", String(Math.max(0, Math.min(100, score))));
  gauge.style.setProperty("--g-color", risk.color);
  document.getElementById("ds-score").textContent = String(Math.round(score));
  document.getElementById("ds-risk").textContent = risk.text;

  const toggle = document.getElementById("ds-toggle-highlight");
  toggle.checked = cfg.dsHighlightEnabled !== false;
  toggle.addEventListener("change", async () => {
    await chrome.storage.local.set({ dsHighlightEnabled: !!toggle.checked });
  });

  document.getElementById("ds-open-dashboard").addEventListener("click", async () => {
    await chrome.tabs.create({ url: "http://localhost:8501" });
  });

  const detailToggle = document.getElementById("ds-detailed-toggle");
  if (detailToggle) {
    detailToggle.checked = cfg.dsDetailedView === true;
    detailToggle.addEventListener("change", async () => {
      await chrome.storage.local.set({ dsDetailedView: !!detailToggle.checked });
      dsRenderDetailedView((scan && scan.patterns) || [], tab?.id);
    });
  }

  document.getElementById("ds-report-fp").addEventListener("click", async () => {
    const snippet = prompt("Paste the flagged text snippet (optional)") || "";
    try {
      await fetch(`${api}/api/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain,
          text: snippet,
          label: "false_positive",
          confirmed: false,
        }),
      });
      alert("Report submitted (stored locally in SQLite via API).");
    } catch {
      alert("Could not reach API. Is Flask running on localhost:5001?");
    }
  });
}

dsLoad().catch((e) => console.warn(e));
