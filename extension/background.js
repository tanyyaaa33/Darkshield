/**
 * Service worker: badge updates from content script messages.
 */

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(["inference_mode"], (cfg) => {
    if (cfg.inference_mode == null) {
      chrome.storage.local.set({ inference_mode: "local" });
    }
  });
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "DS_UPDATE") {
    const n = Number(msg.count || 0);
    const text = n > 0 ? String(Math.min(n, 99)) : "";
    chrome.action.setBadgeBackgroundColor({ color: n > 3 ? "#FF4444" : "#00FF88" });
    chrome.action.setBadgeText({ text });
    sendResponse({ ok: true });
  }
  return true;
});

chrome.action.setBadgeText({ text: "" });
