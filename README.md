# DarkShield

DarkShield is a **dark-pattern transparency** stack focused on **Indian e-commerce**: it classifies manipulative UI copy, stores aggregate scores in **SQLite**, exposes a **Flask API**, ships a **Chrome extension (Manifest V3)**, and includes a **Streamlit dashboard** for exploration and reporting.

All data in this repository is **synthetic, rule-labeled, or scraped from public pages for research** — not user PII.

---

## What ships today

| Area | Features |
|------|----------|
| **ML core** | TF-IDF + **Random Forest** pipeline; optional **confirm-shaming** cosine second pass; training-time text normalization (Unicode / leet / zero-width mitigations). |
| **Dataset** | Builder merges **seed**, **scraped** JSON, synthetic **clean** lines, **Princeton DAPD–inspired** samples, **FTC**-themed lines, **CNIL**-style lines; **cosine dedupe** (~0.95); augmentation; **adversarial** row copies; target **5k+** rows. |
| **Evaluation** | Holdout metrics, confusion matrix HTML, **Cramér’s V**, **per-pattern χ²** vs vertical, **seaborn heatmap** (`vertical_pattern_heatmap.png`), `summary.json`, `metrics.json`, `chi_square_results.json`. |
| **Research / benchmark** | **`ml/models/bert_benchmark.py`** — fine-tunes **DistilBERT** on the same 80/20 split as RF; writes **`model_comparison.json`** (also optional **`requirements-bert.txt`** + **`accelerate`** — not in core `requirements.txt`). |
| **Robustness** | **`ml/models/adversarial_test.py`** — obfuscation transforms, F1 drop report, JSON under `eval_results/`. |
| **Human validation** | **`ml/dataset/annotation_validator.py`** — stratified CSV + Cohen’s / Fleiss’ kappa → **`annotation_agreement.json`**. Guide: **`data/labeled/ANNOTATION_GUIDE.md`**. |
| **ONNX / browser** | **`ml/models/export_onnx.py`** — full pipeline → **`extension/models/darkshield_pipeline.onnx`** + **`labels.json`**; **`keyword_rules.json`**; **`extension/utils/onnx_classifier.js`** loads **ONNX Runtime Web** from **`extension/vendor/`** (copy `ort.min.js` + `.wasm` from `onnxruntime-web/dist/`). |
| **Extension UX** | **Local inference** default (`chrome.storage` **`inference_mode`**: `local` \| `api`); keyword fast-path + ONNX; **popup** shows score, breakdown, **detailed expanders** (explanation + each snippet), **regulatory risk** banner; options page for API base + mode. |
| **API** | **`/api/classify`** (optional **`include_compliance`**), **`/api/compliance-report`**, site score, leaderboard, stats, health; **versioned public API** in **`api/public_routes.py`** (`/api/v1/score`, `leaderboard`, `categories`, `stats`) with **Flask-Limiter** (wired in **`api/app.py`**). |
| **Compliance** | **`ml/compliance/regulatory_mapper.py`** — pattern → illustrative regulation snippets (educational only). |
| **Database** | **`score_history`** table + **`temporal_tracker.py`** (weekly snapshots); dashboard time-series + sale-window hints. |
| **A/B heuristic** | **`ml/analysis/ab_test_detector.py`** — multi–user-agent fetches + variance; dashboard tab. |
| **Landing + docs** | **`landing/index.html`** (static demo UI); **`API_DOCS.md`** — endpoints, curl, rate limits. |
| **Paper draft** | **`scripts/generate_research_summary.py`** → **`research_paper.pdf`** (reads real JSON metrics). |

---

## Project structure

```
darkshield/
├── api/
│   ├── app.py                 # Flask factory + CORS + public blueprint + limiter
│   ├── routes.py              # classify, compliance, site-score, leaderboard, …
│   ├── public_routes.py       # /api/v1/* (rate-limited)
│   └── schemas.py
├── dashboard/
│   └── app.py                 # Streamlit: leaderboard, verticals, site deep dive,
│                              # Full pattern report, A/B tab, statistics
├── extension/
│   ├── manifest.json
│   ├── content.js             # DOM scan; local ONNX or API
│   ├── popup.html / popup.js
│   ├── options.html / options.js
│   ├── models/                # ONNX, labels.json, keyword_rules.json (from export)
│   ├── vendor/                # ort.min.js + *.wasm (from onnxruntime-web)
│   └── utils/                 # onnx_classifier.js, classifier.js, highlighter.js
├── landing/
│   └── index.html             # Public API landing (point at your API origin)
├── ml/
│   ├── analysis/              # ab_test_detector.py
│   ├── compliance/            # regulatory_mapper.py
│   ├── dataset/               # builder, augmenter, external_datasets, annotation_validator, …
│   ├── database/              # transparency_db.py, temporal_tracker.py, site_scorer
│   ├── models/                # train, evaluate, export_onnx, bert_benchmark, adversarial_test, …
│   └── scraper/
├── scripts/
│   ├── generate_research_summary.py
│   └── gen_extension_icon.py  # optional raster icons
├── data/
│   ├── labeled/               # dataset.csv, ANNOTATION_GUIDE.md, human_validation_set.csv (generated)
│   ├── scraped_raw/
│   └── darkshield.db          # created/updated by evaluate.py + API usage
├── requirements.txt           # Core stack (Flask, sklearn, skl2onnx, onnx, onnxruntime, …)
├── requirements-bert.txt      # torch, transformers, accelerate — DistilBERT only
├── API_DOCS.md
└── README.md
```

---

## Requirements

- **Python:** **3.10–3.12** is the smoothest for ML wheels. **3.14** works for the core app if pip can install **`onnx`** / **`skl2onnx`** wheels; DistilBERT may need **`requirements-bert.txt`** or a 3.12 venv if `tokenizers` fails to install.
- **Chrome** (for the extension and optional Selenium scraper).

---

## Setup (from scratch)

```bash
cd /path/to/darkshield
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

**NLTK** (WordNet augmenter — may download on first augment):

```bash
python -c "import nltk; nltk.download('wordnet', quiet=True); nltk.download('omw-1.4', quiet=True)"
```

**Optional: DistilBERT benchmark**

```bash
pip install -r requirements-bert.txt
```

**Optional: extension toolbar icon (PNG)**

```bash
python scripts/gen_extension_icon.py
```

**ONNX Runtime Web (browser):** copy **`ort.min.js`** and **`*.wasm`** from `node_modules/onnxruntime-web/dist/` into **`extension/vendor/`** so local inference works offline.

---

## Pipeline (run in order)

```bash
source .venv/bin/activate
cd /path/to/darkshield

# 1) Dataset (offline-capable; optional scrape feeds scraped_raw/)
python ml/dataset/builder.py

# 2) Train RF + persist pipeline
python ml/models/train.py

# 3) Confirm-shaming helper (if you use the merged eval path)
python ml/models/confirm_shaming_nlp.py

# 4) Export ONNX + keyword JSON for the extension
python ml/models/export_onnx.py

# 5) Evaluate, write plots/JSON, refresh SQLite from holdout logic
python ml/models/evaluate.py
```

**Optional:**

```bash
python ml/models/bert_benchmark.py          # DistilBERT vs RF (research)
python ml/models/adversarial_test.py        # Robustness JSON
python -m ml.database.temporal_tracker      # Append score_history snapshots
python scripts/generate_research_summary.py # research_paper.pdf
python ml/dataset/annotation_validator.py build   # human validation CSV
```

---

## Run services

**API** (default port **5000**):

```bash
source .venv/bin/activate
python -m api.app
```

If **port 5000 is busy** (common on macOS — AirPlay or another process):

```bash
PORT=5001 python -m api.app
```

Set the extension **API base URL** (Options) to match.

**Dashboard:**

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

Use the sidebar → **Full pattern report** for plain-language pattern definitions, regulatory context, and **every stored detection** per site.

**Extension:** `chrome://extensions` → Developer mode → **Load unpacked** → select the **`extension/`** folder. Reload the extension after code changes.

---

## Extension behavior

- **`inference_mode`** (storage): **`local`** (default) = ONNX + keywords in the browser; **`api`** = POST to Flask **`/api/classify`**.
- Console (local mode): `[DarkShield] Running local inference — no data leaves your browser`.
- **Popup:** manipulation score from DB, pattern counts, **expandable detailed view** (explanation + snippets), optional regulatory banner.

---

## API quick reference

Full detail: **[API_DOCS.md](API_DOCS.md)**.

Examples:

```bash
curl -s http://127.0.0.1:5000/api/classify \
  -H 'Content-Type: application/json' \
  -d '{"texts":["Only 2 left — ends in 00:15:00"],"include_compliance":true}'

curl -s 'http://127.0.0.1:5000/api/site-score?domain=amazon.in'
curl -s 'http://127.0.0.1:5000/api/v1/score?domain=amazon.in'
```

---

## Evaluation outputs

Under **`ml/models/saved/eval_results/`**:

- `summary.json`, `metrics.json`, `chi_square_results.json`
- `confusion_matrix.html`, `vertical_manipulation_bar.html`, **`vertical_pattern_heatmap.png`**

**Chi-square / Cramér’s V:** tests association of **vertical × dark prevalence** on the holdout slice; small **p** means dependence in this dataset — not proof of causality.

---

## Landing page

Open **`landing/index.html`** in a browser (or serve statically). Point the demo **API base** field at your running Flask origin (e.g. `http://127.0.0.1:5000`).

---

## Architecture (high level)

```
┌─────────────────┐     local ONNX / optional API    ┌─────────────────┐
│ Chrome extension│ ◄────────────────────────────► │ Flask API       │
│ (DOM + keywords)│                                   │ (RF + confirm)  │
└────────┬────────┘                                   └────────┬────────┘
         │                                                     │
         │  transparency score / detections                   │
         ▼                                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ SQLite (darkshield.db) — sites, detections, score_history, user_reports  │
└─────────────────────────────────────────────────────────────────────────┘
         ▲
         │  reads
┌────────┴────────┐
│ Streamlit       │
│ dashboard       │
└─────────────────┘
```

---

## License / disclaimer

Regulatory strings in the codebase are **illustrative** and **not legal advice**. The extension and API are intended for **research and transparency**, not automated enforcement.
