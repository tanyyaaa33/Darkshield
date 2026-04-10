/**
 * Local inference: keyword_rules.json fast path + ONNX Runtime Web (optional).
 * Falls back to keywords-only if ORT or models are missing.
 */

const DS_ONNX_MODEL_URL = () => chrome.runtime.getURL("models/darkshield_pipeline.onnx");
const DS_LABELS_URL = () => chrome.runtime.getURL("models/labels.json");
const DS_KEYWORDS_URL = () => chrome.runtime.getURL("models/keyword_rules.json");

let dsKeywordMap = null;
let dsLabels = null;
let dsSession = null;
let dsOrtReady = false;

function dsLoadScriptOnce(src) {
  return new Promise((resolve, reject) => {
    const id = "darkshield-ort-script";
    if (document.getElementById(id)) {
      resolve();
      return;
    }
    const s = document.createElement("script");
    s.id = id;
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load " + src));
    (document.head || document.documentElement).appendChild(s);
  });
}

async function dsEnsureOrt() {
  if (dsOrtReady && globalThis.ort) return;
  try {
    await dsLoadScriptOnce(chrome.runtime.getURL("vendor/ort.min.js"));
  } catch {
    return;
  }
  if (!globalThis.ort) return;
  try {
    ort.env.wasm.wasmPaths = chrome.runtime.getURL("vendor/");
  } catch {
    /* ignore */
  }
  dsOrtReady = true;
}

async function dsLoadJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

async function dsEnsureKeywords() {
  if (dsKeywordMap) return;
  dsKeywordMap = await dsLoadJson(DS_KEYWORDS_URL());
}

async function dsEnsureLabels() {
  if (dsLabels) return;
  try {
    const j = await dsLoadJson(DS_LABELS_URL());
    dsLabels = j.labels || [];
  } catch {
    dsLabels = [];
  }
}

function dsKeywordClassify(text) {
  const lower = String(text || "").toLowerCase();
  let best = { label: "none", score: 0, method: "keyword" };
  for (const [lab, kws] of Object.entries(dsKeywordMap || {})) {
    let hits = 0;
    for (const kw of kws) {
      if (lower.includes(String(kw).toLowerCase())) hits += 1;
    }
    const score = hits / Math.max(kws.length, 1);
    if (hits > 0 && score > best.score) {
      best = { label: lab, score: Math.min(1, 0.55 + 0.1 * hits), method: "keyword" };
    }
  }
  return best;
}

function dsPickOutputTensor(outputs) {
  const vals = Object.values(outputs || {});
  for (const t of vals) {
    if (t && t.data && typeof t.data.length === "number" && t.data.length > 0) {
      const f = t.data;
      if (typeof f[0] === "number") return f;
    }
  }
  return null;
}

async function dsEnsureSession() {
  if (dsSession) return dsSession;
  await dsEnsureOrt();
  if (!globalThis.ort || !ort.InferenceSession) return null;
  try {
    dsSession = await ort.InferenceSession.create(DS_ONNX_MODEL_URL(), {
      executionProviders: ["wasm"],
    });
  } catch {
    dsSession = null;
  }
  return dsSession;
}

/**
 * Classify a single string. Returns {label, confidence, method}.
 */
async function classifyText(text) {
  await dsEnsureKeywords();
  await dsEnsureLabels();

  const kw = dsKeywordClassify(text);
  if (kw.label !== "none" && kw.score >= 0.65) {
    return {
      label: kw.label,
      confidence: Number(kw.score.toFixed(4)),
      method: "keyword",
    };
  }

  const session = await dsEnsureSession();
  if (!session) {
    return {
      label: kw.label !== "none" ? kw.label : "none",
      confidence: kw.label !== "none" ? Number(kw.score.toFixed(4)) : 0.2,
      method: "keyword",
    };
  }

  try {
    const inputName = session.inputNames && session.inputNames[0] ? session.inputNames[0] : "input";
    const feeds = {};
    feeds[inputName] = new ort.Tensor("string", [[String(text)]], [1, 1]);
    const out = await session.run(feeds);
    const vec = dsPickOutputTensor(out);
    if (!vec || !dsLabels.length) {
      return {
        label: kw.label !== "none" ? kw.label : "none",
        confidence: 0.4,
        method: "onnx_fallback_keyword",
      };
    }
    let idx = 0;
    let best = -Infinity;
    for (let i = 0; i < vec.length; i++) {
      if (vec[i] > best) {
        best = vec[i];
        idx = i;
      }
    }
    const lab = dsLabels[idx] || "none";
    const expSum = vec.reduce((a, b) => a + Math.exp(b - best), 0);
    const probs = vec.map((v) => Math.exp(v - best) / expSum);
    const conf = probs[idx] || 0.5;
    return { label: lab, confidence: Number(conf.toFixed(4)), method: "onnx" };
  } catch {
    return {
      label: kw.label !== "none" ? kw.label : "none",
      confidence: kw.label !== "none" ? Number(kw.score.toFixed(4)) : 0.25,
      method: "keyword",
    };
  }
}

/**
 * Batch classify for content script (sequential to limit memory).
 */
async function classifyBatch(texts) {
  const out = [];
  for (const t of texts) {
    out.push(await classifyText(t));
  }
  return out;
}

globalThis.DSOnnxClassifier = {
  classifyText,
  classifyBatch,
  init: async () => {
    await dsEnsureKeywords();
    await dsEnsureLabels();
    await dsEnsureSession();
  },
};
