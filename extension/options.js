const DS_API_DEFAULT = "http://127.0.0.1:5001";

async function load() {
  const cfg = await chrome.storage.local.get(["dsApiBase", "dsPageSummaryToast", "inference_mode"]);
  document.getElementById("ds-api-base").value = cfg.dsApiBase || DS_API_DEFAULT;
  document.getElementById("ds-page-toast").checked = cfg.dsPageSummaryToast !== false;
  document.getElementById("ds-inference-mode").value = cfg.inference_mode === "api" ? "api" : "local";
}

document.getElementById("ds-save").addEventListener("click", async () => {
  const v = document.getElementById("ds-api-base").value.trim() || DS_API_DEFAULT;
  const toast = document.getElementById("ds-page-toast").checked;
  const mode = document.getElementById("ds-inference-mode").value === "api" ? "api" : "local";
  await chrome.storage.local.set({ dsApiBase: v, dsPageSummaryToast: toast, inference_mode: mode });
  document.getElementById("ds-status").textContent = "Saved.";
});

load().catch(() => {});
