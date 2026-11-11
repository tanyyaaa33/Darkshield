# DarkShield

DarkShield is a Manifest V3 Chrome extension, a Flask API, a Streamlit dashboard, and a SQLite database. The extension classifies visible text on a fixed list of sites. Inference in the browser uses ONNX Runtime Web. The classifier is a TF-IDF Random Forest.

## What it detects

There are 10 pattern labels:

`bait_and_switch`, `confirm_shaming`, `fake_urgency`, `forced_continuity`, `hidden_costs`, `misdirection`, `roach_motel`, `sneaking`, `social_proof_manipulation`, `visual_interference`.

`none` means none of those ten. The content script (`extension/content.js`) collects visible text and registers a `MutationObserver` to scan again after DOM changes. It runs only on the hosts in `extension/manifest.json`: amazon.in, flipkart.com, myntra.com, nykaa.com, bigbasket.com, swiggy.com, zomato.com, makemytrip.com, cleartrip.com, and irctc.co.in.

## Figure to cite

Merged holdout macro F1 in `ml/models/saved/eval_results/metrics.json` is **0.904630970887321** (about 0.9046, **90.5%**). That is the number to show users.

`ml/models/saved/model_comparison.json` is a separate comparison. Random Forest macro F1 is 0.9146 and the model is about 27 MB. DistilBERT macro F1 is 0.993 and the model is about 256 MB. The extension ships the Random Forest because of that size. DistilBERT weights are not in this repo.

## Dataset

`data/labeled/dataset.csv` has a header plus **5,663** data rows (`text`, `label`, `site`, `vertical`, `source`, `confidence`).

`source` counts in this file: augmented 2,643, princeton_inspired 1,567, seed 674, scraped 457, ftc 245, clean 52, cnil 25. The rows mix scraped public pages, seed phrases, and synthetic samples (augmented text and rewritten external examples). This is not a purely human-labeled dataset.

## Load the extension unpacked

Chrome is required. These files are already in the tree, so a clean clone does not need a build before Load unpacked:

- `extension/vendor/ort.min.js`
- `extension/vendor/ort-wasm-simd-threaded.wasm` and the other `ort-wasm-simd-threaded*.wasm` files
- `extension/models/darkshield_pipeline.onnx`, `labels.json`, `keyword_rules.json`
- `extension/icons/icon.png` (128×128 PNG, used for the 16, 48, and 128 slots)

1. Clone the repo.
2. Open `chrome://extensions`.
3. Turn on Developer mode.
4. Click **Load unpacked**.
5. Select the `extension/` directory.

If `extension/vendor/ort.min.js` or the `.wasm` files are missing:

```bash
npm install
cp node_modules/onnxruntime-web/dist/ort.min.js extension/vendor/
cp node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded*.wasm extension/vendor/
```

Host permissions stay the site list above, plus `localhost` and `127.0.0.1` on ports 5000 and 5001 for the local API. Do not replace that list with `<all_urls>`.

The default inference mode is local. Settings can switch to API mode. The default API base is `http://127.0.0.1:5001`.

## Run the API

Python 3.10 or newer. `requirements.txt` says 3.10–3.12 have the widest wheel coverage. The ONNX pins in that file also target current 3.14 wheels.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
PORT=5001 python -m api.app
```

`python -m api.app` listens on port 5000 unless `PORT` is set. On macOS, Control Center often already binds port 5000. The extension calls port 5001 by default, and the manifest allows both.

```bash
curl http://127.0.0.1:5001/api/health
```

The body is `{"status":"ok"}`.

`/api/v1/score`, `/api/v1/leaderboard`, `/api/v1/categories`, and `/api/v1/stats` are limited to **100 requests per hour** per client IP. Counts are kept in memory and reset when the process restarts. `/api/health`, `/api/classify`, and the other `/api/` routes are not under that limit.

The process loads `ml/models/saved/darkshield_rf.pkl` and `ml/models/saved/confirm_shaming_tfidf.pkl`. Installing does not require retraining.

## Run the dashboard

Use the same virtualenv. `data/darkshield.db` is already in the repo.

```bash
streamlit run dashboard/app.py
```

Streamlit’s default URL is `http://localhost:8501`. The popup button **View Full Report** opens that URL.

## What it will not do

- It will not block a purchase, cancel a subscription, or change the site’s controls. It highlights text and stores the last scan in `chrome.storage`.
- It will not run on hosts outside `extension/manifest.json`.
- It will not give legal advice. Regulatory strings in the API and dashboard are illustrative.
- A live-page label can be wrong. Cite the 90.5% merged holdout macro F1 above, not a guarantee for one page.
- Local mode classifies in the browser when ONNX Runtime Web loads. If that fails, `extension/content.js` POSTs the snippet text and page URL to the configured API. API mode always sends them. The default API is on your machine (`http://127.0.0.1:5001`).
- It is not a Chrome Web Store listing. This repo has no privacy-policy URL.
- It does not include the DistilBERT model.
- A ChromeDriver binary is not part of install. `.chromedriver` is gitignored. Loading the extension and running the API do not need it.

## License

MIT. See [LICENSE](LICENSE).
