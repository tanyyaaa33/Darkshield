# DarkShield Technical Deep Dive

This document is a full technical walkthrough of the DarkShield repository as currently implemented in your codebase.

---

## SECTION 1: PROJECT OVERVIEW

### 1.1 What problem DarkShield solves and why it matters

DarkShield is a transparency and research system for detecting dark-pattern-like language in e-commerce and travel interfaces.  
In practice, many websites use persuasive copy in ways that can pressure users into decisions they did not fully intend (for example, urgency timers, preselected add-ons, hidden late fees, and difficult cancellation flows).

DarkShield aims to:

1. Detect likely dark-pattern textual cues.
2. Explain why a snippet was flagged.
3. Store traceable evidence in SQLite.
4. Present site/vertical-level analytics via Streamlit.
5. Support extension-first use (local ONNX or API mode).

Why it matters:

- **User decision quality:** users should understand manipulative pressure.
- **Research reproducibility:** every detection is persisted with label/confidence.
- **Operational analysis:** scores can be compared across sites and verticals.
- **Interview relevance:** this project combines ML + browser runtime + backend + analytics.

### 1.2 What dark patterns are — all 10 categories with examples

DarkShield uses 10 target categories plus a `none` class:

1. **fake_urgency**  
   Example: "Only 2 left in stock — order in the next 00:03:42!"
2. **confirm_shaming**  
   Example: "No thanks, I prefer paying full MRP."
3. **hidden_costs**  
   Example: "Convenience fee of Rs49 will be added at checkout."
4. **visual_interference**  
   Example: "The 'No' button is greyed out until you scroll terms."
5. **sneaking**  
   Example: "Extended warranty silently pre-selected in cart."
6. **forced_continuity**  
   Example: "Free trial converts to paid monthly billing unless cancelled."
7. **misdirection**  
   Example: "Unsubscribe link buried in low-contrast footer text."
8. **social_proof_manipulation**  
   Example: "4982 people are viewing this right now."
9. **bait_and_switch**  
   Example: "Ad says Rs499, checkout shows Rs899."
10. **roach_motel**  
    Example: "Easy signup, but account deletion requires support ticket."

### 1.3 High-level architecture (4 components)

DarkShield has 4 major layers:

1. **Chrome extension**  
   - scans DOM text (`extension/content.js`)
   - classifies text (local ONNX via `extension/utils/onnx_classifier.js` or API call)
   - highlights snippets (`extension/utils/highlighter.js`)
   - popup renders breakdown/details (`extension/popup.js`)

2. **Flask API**  
   - endpoints in `api/routes.py` and `api/public_routes.py`
   - model inference + confirm-shaming second pass
   - SQLite reads/writes

3. **ML pipeline**  
   - dataset assembly (`ml/dataset/builder.py`)
   - training (`ml/models/train.py`)
   - ONNX export (`ml/models/export_onnx.py`)
   - evaluation/stats (`ml/models/evaluate.py`)

4. **Streamlit dashboard**  
   - UI in `dashboard/app.py`
   - reads SQLite and eval JSON
   - shows leaderboard, vertical analysis, deep dive, compliance context

### 1.4 Detailed ASCII data-flow diagram

```text
                   ┌──────────────────────────────────────────────────┐
                   │                 ML PIPELINE                      │
                   │  builder.py -> train.py -> export_onnx.py       │
                   │                    -> evaluate.py                │
                   └───────────────┬──────────────────────────────────┘
                                   │
                                   │ writes
                                   ▼
         ┌──────────────────────────────────────────────────────────────┐
         │ ml/models/saved/*.pkl + eval_results/*.json/*.html          │
         │ extension/models/darkshield_pipeline.onnx + labels.json     │
         └──────────────────────────────────────────────────────────────┘

Browser Tab (supported domain)
      │
      ▼
content.js
  ├─ DOM text extraction + prefilter (classifier.js)
  ├─ local mode -> onnx_classifier.js (keyword -> ONNX fallback chain)
  ├─ api mode   -> POST /api/classify
  └─ highlight via highlighter.js
      │
      ├─ save scan payload in chrome.storage.session/local
      └─ send DS_UPDATE to background.js (badge count)

popup.js
  ├─ reads dsLastScan from storage
  ├─ fetches /api/site-score
  ├─ shows risk + breakdown + evidence
  └─ can send DS_FOCUS_PATTERN to content.js (scroll to highlight)

                ┌──────────────────────────────┐
                │ Flask API (api/app.py)       │
                │ routes.py/public_routes.py    │
                │ _classify_batch (RF + cosine) │
                └──────────┬───────────────────┘
                           │
                           ▼
                    SQLite (data/darkshield.db)
                     tables: sites, detections,
                             user_reports, score_history
                           │
                           ▼
                  Streamlit dashboard/app.py
                (leaderboard, verticals, deep dive,
                 compliance/reporting, A/B analysis)

Note: "fraud_detector" is not a file/class in this repo. Equivalent runtime inference is
implemented in routes.py via _classify_batch() + confirm-shaming merge logic.
```

---

## SECTION 2: THE DATASET — HOW THE TRAINING DATA WAS BUILT

Files used:
- `ml/dataset/dark_patterns_seed.py`
- `ml/dataset/external_datasets.py`
- `ml/dataset/builder.py`
- `ml/dataset/augmenter.py`
- `ml/dataset/annotation_validator.py`
- `data/labeled/ANNOTATION_GUIDE.md`

### 2.1 `dark_patterns_seed.py`

Purpose:
- Provides hand-curated seed examples for all categories.
- Rotates site assignments across Indian domains and verticals.
- Adds explicit `none` seeds.

Important implementation details:
- `_FAKE_URGENCY`, `_CONFIRM_SHAMING`, etc. each store many textual examples.
- `_SITES_ROT_ECOM`, `_SITES_ROT_FOOD`, `_SITES_ROT_TRAVEL` define canonical domain/vertical pairs.
- `_with_sites()` assigns each text to a rotating `(site, vertical)` tuple.
- `SEED_EXAMPLES` is assembled category-by-category and extended with `_NONE_SEEDS`.

### 2.2 `external_datasets.py`

Purpose:
- Generates additional synthetic/paraphrased corpora inspired by:
  - Princeton DAPD taxonomy
  - FTC dark pattern themes
  - CNIL/EU guidance themes

Key points:
- `PRINCETON_MAPPING` maps DAPD-style labels to DarkShield schema.
- `_princeton_synthetic_block()` creates templated rows.
- `get_princeton_inspired_samples()` rewrites source tags and assigns `.example` domains.
- `get_ftc_examples()` and `_ftc_examples()` generate enforcement-style vignettes with anonymized retailer names.
- `_cnil_examples()` emphasizes consent/obstruction patterns.

Important note:
- These corpora intentionally include placeholder `.example` domains (for anonymized/synthetic data).

### 2.3 `builder.py` end-to-end assembly flow

`build_dataset(min_total=5200, min_per_class=150, seed=42)`:

1. Initialize list of rows.
2. Append seed examples.
3. Append `_load_scraped_rows()` from `data/scraped_raw/*.json`.
4. Append synthetic neutral rows via `_synthetic_none_rows()`.
5. Append external corpora:
   - Princeton-inspired
   - FTC examples
   - CNIL examples
6. Convert to DataFrame and enforce minimal text length.
7. Drop exact duplicates on `(text, label)`.
8. Run `_dedupe_by_text_cosine(df, threshold=0.95)`.
9. Run `balance_min_per_class()` from `augmenter.py`.
10. Run `_oversample_to_balance()` for total-size balancing.
11. Normalize text with `normalize_text()`.
12. Add adversarial rows via `_append_adversarial_rows(rate=0.10)`.
13. Recompute vertical from `site` via `vertical_for_site()`.
14. Print composition report and save `data/labeled/dataset.csv`.

### 2.4 Cosine deduplication math

Used in `_dedupe_by_text_cosine()`:

1. Build TF-IDF matrix `X` over all texts.
2. For each row `i`, compute cosine similarity with retained representatives.
3. If `max(similarity) >= 0.95`, drop row as near-duplicate.

Cosine formula:

- `cos(a,b) = (a dot b) / (||a|| * ||b||)`

Where `a,b` are TF-IDF vectors.

### 2.5 Final dataset shape and composition

From your recent run output:
- Total rows written: **5664**
- Composition:
  - seed: 669 (11.8%)
  - scraped: 100 (1.8%)
  - princeton_inspired: 1529 (27.0%)
  - ftc: 432 (7.6%)
  - cnil: 261 (4.6%)
  - augmented: 2300 (40.6%)
  - clean none: 373 (6.6%)

Class counts reported:
- bait_and_switch 528
- sneaking 525
- confirm_shaming 525
- roach_motel 522
- forced_continuity 522
- fake_urgency 522
- visual_interference 517
- hidden_costs 513
- social_proof_manipulation 512
- misdirection 506
- none 472

### 2.6 `augmenter.py`

Core transforms:
- synonym replacement (`_synonym_replace`, WordNet)
- random delete (`_random_delete`)
- random insert (`_random_insert`)
- number swap (`_swap_numbers`)
- brand swap (`_swap_brands`)
- optional Hinglish prefix fragment

`augment_rows()` keeps site/vertical metadata from donor rows while generating new text.

Why augmentation helps:
- expands lexical variation
- improves robustness to wording drift
- reduces overfit to exact phrase templates

### 2.7 `annotation_validator.py`

Functions:
- `build_validation_set(n=200)` creates stratified CSV for human labeling.
- `compute_agreement()` computes:
  - Cohen’s kappa (model vs each annotator)
  - Fleiss’ kappa (among 3 annotators)

Kappa interpretation in code:
- >0.8: almost perfect
- >=0.6: substantial
- else: moderate

Why inter-annotator agreement matters:
- verifies label consistency quality
- reveals ambiguous category boundaries
- reduces noise in supervised training signals

### 2.8 Sample row from `dataset.csv`

```csv
text,label,site,vertical,source,confidence
"Flipkart exchange flow pushes 'Yes' with animated arrow",misdirection,flipkart.com,electronics,seed,
```

---

## SECTION 3: TEXT PREPROCESSING AND FEATURE ENGINEERING

Files:
- `ml/dataset/text_normalize.py`
- `ml/dataset/feature_engineer.py`

### 3.1 `text_normalize.py` steps

1. Unicode normalization: `unicodedata.normalize("NFKC", text)`
2. Leet map replacement:
   - `0->o`, `1->i`, `3->e`, `4->a`, `5->s`, `7->t`, `@->a`, `$->s`
3. Whitespace collapse: `re.sub(r"\s+", " ", ...)`
4. Optional zero-width/control removal in `strip_control_and_zwsp()`

Why this matters:
- Evasion can use homoglyphs / odd Unicode.
- Attackers can inject invisible codepoints (ZWSP).
- Normalization makes model and keyword logic less brittle.

### 3.2 `feature_engineer.py`

`preprocess_for_model(text)` currently delegates to `normalize_text()`.
This is a thin abstraction so training pipeline can evolve preprocessing centrally.

### 3.3 TF-IDF math and settings in this project

In `train.py`:
- `ngram_range=(1,3)`
- `max_features=15000`
- `sublinear_tf=True`

Definitions:
- TF(term, doc): frequency of term in a document.
- IDF(term): downweights terms common across many documents.
- TF-IDF weight: TF * IDF (with project using sublinear TF).

Sublinear TF:
- uses `1 + log(tf)` instead of raw tf, reducing dominance of repeated tokens.

Why 1..3 grams:
- captures phrases like "no thanks", "only left", "auto renew", not just single words.

Why 15000 features:
- enough vocabulary breadth for mixed domains without excessive sparse noise.

Conceptual before/after example:

- Raw: `N0 thanks, I d0n't want sav1ngs!!!`
- Normalized: `No thanks, I don't want savings!!!`

Conceptual vector:
- Sparse vector with nonzero entries at grams like:
  - `no`, `thanks`, `no thanks`, `want savings`

---

## SECTION 4: THE MACHINE LEARNING PIPELINE

Files:
- `ml/models/train.py`
- `ml/models/confirm_shaming_nlp.py`
- `ml/models/evaluate.py`
- `ml/models/saved/eval_results/metrics.json`
- `ml/models/saved/model_comparison.json`
- `ml/models/saved/eval_results/chi_square_results.json`
- `ml/models/saved/eval_results/summary.json`
- `ml/models/saved/feature_importance.json`
- `ml/models/adversarial_test.py`
- `ml/models/saved/eval_results/adversarial_robustness.json`

### 4.1 Random Forest training design

Pipeline:
- `TfidfVectorizer(ngram_range=(1,3), max_features=15000, sublinear_tf=True)`
- `RandomForestClassifier(n_estimators=300, class_weight='balanced', n_jobs=-1)`

Why `n_estimators=300`:
- stabilizes ensemble variance without huge runtime.

Why `class_weight='balanced'`:
- penalizes errors in minority classes more heavily.

Training flow:
1. Load dataset.
2. Normalize text via `preprocess_for_model`.
3. Stratified train/test split.
4. Additional upsample balancing on training fold.
5. Fit pipeline.
6. Evaluate holdout macro-F1 and report.
7. Save model (`darkshield_rf.pkl`) + encoder + feature importance JSON.

Serialization:
- `joblib.dump()` stores sklearn objects efficiently for reuse in API.

### 4.2 Metrics explained with formulas

Precision:
- `TP / (TP + FP)`

Recall:
- `TP / (TP + FN)`

F1:
- `2 * (precision * recall) / (precision + recall)`

Macro F1:
- unweighted mean of per-class F1.

Weighted F1:
- support-weighted mean of per-class F1.

Confusion matrix:
- rows: true labels
- cols: predicted labels
- diagonal: correct counts
- off-diagonal: class confusions

### 4.3 Actual evaluation numbers (current files)

From `ml/models/saved/eval_results/summary.json`:
- `macro_f1_merged_pred`: **0.904630970887321**
- `chi2_vertical_dark.p_value`: **5.4315919321892294e-52**
- `chi2_vertical_dark.cramers_v`: **0.4697600374408151** (Strong)

From `metrics.json`:
- `macro_f1_merged_pred`: **0.904630970887321**
- travel vs fmcg `p_value`: **0.005876411410829059**

### 4.4 Confirm-shaming second pass (`confirm_shaming_nlp.py`)

Method:
- Fit TF-IDF on confirm-shaming reference corpus.
- Score new text by cosine similarity to reference matrix.
- Threshold = `SIM_THRESHOLD = 0.45`.

Classification logic:
- if RF predicts confirm_shaming OR cosine flag true -> final label confirm_shaming.
- confidence for confirm_shaming uses max of RF prob and cosine score.

Why second pass:
- confirm-shaming is highly linguistic and phrase-style sensitive.
- cosine reference matching increases recall for this category.

### 4.5 Chi-square and Cramér’s V

Contingency table:
- built on `vertical x is_dark`.

Chi-square:
- compares observed vs expected counts under independence.

Degrees of freedom:
- `(rows-1) * (cols-1)`

p-value:
- probability of seeing such discrepancy under null hypothesis.
- very small p => reject independence assumption.

Cramér’s V:
- `sqrt(chi2 / (n * (min(r,k)-1)))`

Interpretation in this run:
- V ~ 0.47 => strong association.

Per-pattern significance:
- all 10 pattern tests have `significant_01 = true` in `chi_square_results.json`.

### 4.6 DistilBERT benchmark

From `bert_benchmark.py` and `model_comparison.json`:

- Training args:
  - epochs = 3
  - batch size = 16
  - learning rate = 2e-5
  - weight decay = 0.01
- Comparison JSON currently records:
  - RF macro F1: 0.9146
  - DistilBERT macro F1: 0.993
  - RF latency: 21.064 ms/sample
  - DistilBERT latency: 8.144 ms/sample
  - RF size: 27.19 MB
  - DistilBERT size: 255.68 MB

Important consistency note:
- JSON narrative says RF chosen for deployment despite benchmark numbers; production decision is still RF for package/integration simplicity and existing extension pipeline behavior.

### 4.7 Adversarial robustness

Transforms in `adversarial_test.py`:
1. `leet_speak`
2. `unicode_substitution`
3. `css_hidden_text`
4. `zero_width_chars`
5. `split_words`

From `adversarial_robustness.json`:
- baseline dark-slice macro-F1: 0.9835
- major weakness: `split_words` drop 0.4763 (HIGH RISK)
- unicode substitution drop: 0.0885
- others near zero drop

Mitigation path:
- normalization + HTML stripping in `prepare_for_classifier()`.

---

## SECTION 5: ONNX EXPORT AND BROWSER INFERENCE

Files:
- `ml/models/export_onnx.py`
- `extension/utils/onnx_classifier.js`
- `extension/models/keyword_rules.json`
- `extension/models/labels.json`

### 5.1 What ONNX is and why used

ONNX is an interoperable model format for running inference outside training framework context.
Here it allows browser-side inference through ONNX Runtime Web.

### 5.2 `export_onnx.py` flow

1. Load sklearn pipeline `darkshield_rf.pkl`.
2. Extract classifier classes and write `labels.json`.
3. Convert pipeline using `convert_sklearn(... target_opset=12, zipmap=False)`.
4. Save `extension/models/darkshield_pipeline.onnx`.

### 5.3 Browser inference flow (`onnx_classifier.js`)

1. Load keyword rules and labels JSON.
2. Optional: load `vendor/ort.min.js`.
3. Keyword fast path:
   - count keyword hits by category
   - if score >= 0.65, return keyword label.
4. Else run ONNX:
   - feed tensor shape `[1,1]` string input
   - parse output tensor
   - softmax -> confidence
5. If ONNX unavailable/error:
   - fallback to keyword or `none`.

Batch flow:
- `classifyBatch()` is sequential over texts to reduce memory spikes.

### 5.4 Rules and labels

`keyword_rules.json` has category-specific terms, e.g.:
- fake_urgency: `only`, `limited stock`, `countdown`, `selling fast`
- hidden_costs: `convenience fee`, `gst`, `final price`

`labels.json` currently includes 11 labels in RF order:
- bait_and_switch, confirm_shaming, fake_urgency, forced_continuity, hidden_costs, misdirection, none, roach_motel, sneaking, social_proof_manipulation, visual_interference

---

## SECTION 6: THE CHROME EXTENSION — EVERY FILE EXPLAINED

Files:
- `extension/manifest.json`
- `extension/content.js`
- `extension/background.js`
- `extension/popup.html`
- `extension/popup.js`
- `extension/options.html`
- `extension/options.js`
- `extension/utils/classifier.js`
- `extension/utils/highlighter.js`
- `extension/styles/content.css`
- `extension/styles/popup.css`

### 6.1 `manifest.json`

MV3 extension with:
- permissions: `activeTab`, `storage`, `scripting`
- host permissions for supported domains + localhost API ports
- content scripts run at `document_idle` on configured hosts
- web_accessible_resources exposes ONNX model/labels/vendor files
- background service worker: `background.js`

Note:
- `badges` permission is not separately declared; badge API via `chrome.action` is used.
- explicit `content_security_policy` key is not present in this manifest.

### 6.2 `content.js` full runtime flow

On load:
1. `dsRunScan()`
2. `dsSetupObserver()` installs `MutationObserver` for dynamic content refresh.

`dsCollectTextNodes()`:
- tree-walk text nodes
- reject short text, hidden nodes, forbidden parent tags, suspicious geometry
- run prefilter via `dsPreFilterExport()`

Classification:
- mode from storage: `local` or `api`
- local: `DSOnnxClassifier.classifyBatch()`
- api: POST `/api/classify`
- batch capped at 40 candidates

Output handling:
- highlights flagged text using `dsHighlighter.dsHighlightTextNode`
- save scan payload in session/local storage
- send `DS_UPDATE` message to background for badge
- optional on-page toast

Jump navigation:
- listens for `DS_FOCUS_PATTERN`
- finds matching highlighted span
- scrolls + focus animation + tooltip display

### 6.3 `highlighter.js`

Key behavior:
- wraps text node with span `.darkshield-highlight`
- stores metadata in data attributes
- appends tooltip `.darkshield-tooltip`
- hover toggles tooltip visibility
- confidence > 0.85 adds pulse class

### 6.4 `background.js`

Service worker responsibilities:
- initialize default `inference_mode=local` on install
- handle `DS_UPDATE` messages
- set badge text (up to 99) and color:
  - >3: red
  - else: green

### 6.5 `popup.js`

Reads:
- current tab/domain
- `dsLastScan` payload
- API base + user settings

Renders:
- gauge from `/api/site-score`
- pattern breakdown with counts
- detailed grouped snippet view
- regulatory risk banner if high-severity categories present

Interactivity:
- click row to jump to page highlight
- per-snippet "Show on page"
- toggle detailed/simple
- report false positive via `/api/report`

### 6.6 `options.js`

Stores in `chrome.storage.local`:
- `dsApiBase`
- `dsPageSummaryToast`
- `inference_mode` (`local` or `api`)

---

## SECTION 7: THE FLASK API — EVERY ENDPOINT EXPLAINED

Files:
- `api/app.py`
- `api/routes.py`
- `api/public_routes.py`
- `api/schemas.py`

### 7.1 `app.py`

Factory pattern:
- `create_app()` configures app, loads model/db paths, initializes DB.
- loads:
  - RF pipeline (`darkshield_rf.pkl`)
  - confirm-shaming model (`confirm_shaming_tfidf.pkl`)
- enables CORS for `/api/*`.
- registers blueprints:
  - internal routes `bp`
  - public routes `pub`
- Flask-Limiter applies 100/hour to public v1 endpoints.

### 7.2 Internal endpoints (`routes.py`)

#### POST `/api/classify`
- Input schema: `ClassifyRequest` (`texts`, optional `url`, optional `include_compliance`)
- Flow: `_classify_batch()` -> RF + cosine confirm pass
- Output rows: `text,label,confidence,explanation[,compliance]`

#### GET `/api/compliance-report?domain=...`
- Pulls detections for domain from SQLite.
- Aggregates with `generate_compliance_report()`.

#### GET `/api/site-score?domain=...`
- Returns:
  - domain
  - manipulation_score
  - pattern_breakdown
  - rank
  - vertical

#### GET `/api/leaderboard?vertical=&limit=`
- Uses `fetch_leaderboard` from DB module.

#### POST `/api/report`
- Persists user false-positive/feedback rows into `user_reports`.

#### GET `/api/stats`
- aggregate stats + optional eval metadata from `summary.json`.

#### GET `/api/health`
- simple status check `{status: ok}`.

### 7.3 Public endpoints (`public_routes.py`)

#### GET `/api/v1/score?domain=...`
- Risk level mapping:
  - <=30 LOW
  - <=60 MEDIUM
  - <=80 HIGH
  - else CRITICAL
- returns top patterns and compliance flags.

#### GET `/api/v1/leaderboard?vertical=&limit=`
- ranked rows with score/pages/vertical.

#### GET `/api/v1/categories`
- static category list.

#### GET `/api/v1/stats`
- counts for sites, detections, top pattern, generated_at.

### 7.4 `schemas.py`

Uses Python dataclasses (not Pydantic).  
Validation is manual in `.from_json()` methods:
- required field checks
- type normalization to strings/bools/lists

---

## SECTION 8: THE DATABASE — SCHEMA AND QUERIES

Files:
- `ml/database/transparency_db.py`
- `ml/database/site_scorer.py`
- `ml/database/temporal_tracker.py`
- `data/darkshield.db`

### 8.1 Tables and columns

From `.schema`:

1. `sites`
   - `id` INTEGER PK
   - `domain` TEXT UNIQUE
   - `vertical` TEXT
   - `total_patterns_found` INTEGER
   - `manipulation_score` REAL
   - `last_scraped` TIMESTAMP
   - `pages_analyzed` INTEGER

2. `detections`
   - `id`, `site_id`, `pattern_category`, `text_snippet`, `url`, `confidence`, `detected_at`

3. `user_reports`
   - `id`, `domain`, `pattern_category`, `text_snippet`, `confirmed`, `reported_at`

4. `score_history`
   - `id`, `domain`, `manipulation_score`, `patterns_found`, `snapshot_date`, `delta_from_prev`

### 8.2 Current DB sample (from live query)

Top sites currently:
- flipkart.com | electronics | 100.0 | pages_analyzed 46
- swiggy.com | food_delivery | 98.26 | 23
- amazon.in | electronics | 94.13 | 46
- makemytrip.com | travel | 91.49 | 47
- irctc.co.in | travel | 84.76 | 21
- zomato.com | food_delivery | 80.53 | 19
- myntra.com | fashion | 72.89 | 45
- nykaa.com | fmcg | 71.75 | 63
- bigbasket.com | fmcg | 63.05 | 59
- cleartrip.com | travel | 60.67 | 30

Pattern counts:
- confirm_shaming 70
- hidden_costs 33
- misdirection 29
- visual_interference 26
- sneaking 25
- social_proof_manipulation 21
- roach_motel 21
- fake_urgency 20
- bait_and_switch 19
- forced_continuity 12

### 8.3 Manipulation score formula (`site_scorer.py`)

Inputs:
- patterns_found
- total_text_nodes_analyzed
- list of predicted pattern categories

Steps:
1. `ratio = patterns_found / max(total_text_nodes_analyzed,1)`
2. `base = ratio * 100`
3. compute average category weight from `PATTERN_WEIGHTS`
4. score = `min(100, round(base * mean_w, 2))`

Weights:
- fake_urgency 1.2
- confirm_shaming 1.5
- hidden_costs 1.3
- others 1.0

### 8.4 Temporal tracking (`temporal_tracker.py`)

Current implementation:
- `weekly_rescrape()` does snapshotting from existing `sites` table, not HTML rescrape.
- computes delta vs previous snapshot and stores in `score_history`.
- optional scheduler loop via `schedule` package.

Important gap vs your requested items:
- `INDIAN_SALE_EVENTS` dict is **not present** in current code.
- `generate_temporal_insights()` function is **not present** in current code.

---

## SECTION 9: THE STREAMLIT DASHBOARD — EVERY PAGE EXPLAINED

File:
- `dashboard/app.py`

### 9.1 Page routing

Sidebar sections:
- Leaderboard
- Data Collection & Observations
- Vertical Analysis
- Site Deep Dive
- Full Pattern Report
- A/B Test Detection
- Statistics

### 9.2 Leaderboard

Data source: `fetch_all_sites(DB_PATH)`  
Features:
- vertical filter
- KPI cards (avg score, risk level, total patterns)
- horizontal bar chart by `manipulation_score`
- table with risk level and pages analyzed
- intro expanders shown only here

### 9.3 Vertical Analysis

Data source:
- DB sites + `get_vertical_comparison()`
- `summary.json` for chi-square stats

Visuals:
- box plot of per-site scores by vertical
- bar chart of average score by vertical
- optional advanced stacked pattern composition chart

### 9.4 Site Deep Dive

Data source: detections for selected domain and `score_history`.

Visuals:
- metrics (snippet count, pattern types, avg confidence)
- donut chart of pattern distribution
- daily detection line plot
- weekly trend if score history exists
- detailed snippets table

### 9.5 Full Pattern Report

Tab 1: Pattern encyclopedia
- definitions from `api.routes.EXPLANATIONS`
- examples from `PATTERN_EXAMPLES`
- compliance tags from `get_compliance_tags()`

Tab 2: all detections by site
- domain selector
- per-pattern grouped snippet evidence with confidence + URL captions

### 9.6 A/B Test Detection

Calls `detect_ab_testing(domain, n_sessions=10)` from `ml/analysis/ab_test_detector.py`.

Shows:
- conclusion text
- aggregate keys
- session-level debug details

### 9.7 Statistics

From `aggregate_stats()`:
- total sites
- total detections
- user reports
- most common pattern
- worst-offender domain/score
- latest eval timestamp + macro F1 (if summary exists)

---

## SECTION 10: COMPLIANCE AND REGULATORY LAYER

File:
- `ml/compliance/regulatory_mapper.py`

### 10.1 Mapping design

`REGULATORY_MAPPING` maps each pattern to:
- CCPA/CPRA theme
- EU dark-pattern/fairness theme
- FTC Act framing
- India IT/consumer-protection aligned note
- severity level
- example enforcement theme list

Severity values used:
- HIGH / MEDIUM / NONE / UNKNOWN

### 10.2 API functions

`get_compliance_tags(pattern_label)`:
- direct dictionary lookup (returns dict copy)

`generate_compliance_report(detections)`:
- groups per regulation key
- tracks highest severity pattern
- outputs:
  - violations_by_regulation
  - highest_severity_pattern
  - recommended_action

---

## SECTION 11: A/B TEST DETECTION

File:
- `ml/analysis/ab_test_detector.py`

### 11.1 Purpose

Detect variability in dark-pattern signals across repeated homepage fetches with rotating user agents.

### 11.2 Flow

1. Normalize domain URL.
2. Iterate `n_sessions`.
3. Rotate among desktop/mobile UA strings.
4. Fetch HTML via requests.
5. Strip scripts/styles/tags into chunk list.
6. Rule-label chunks via `auto_label_text()`.
7. For each category, compute binary presence vector across sessions.
8. Compute variance.
9. If variance > 0.1, mark as `likely_ab_tested`.

Output:
- `ab_tested_patterns`
- conclusion
- session diagnostics

---

## SECTION 12: THE SCRAPER

Files:
- `ml/scraper/selenium_scraper.py`
- `ml/scraper/page_parser.py`

### 12.1 Selenium scraper

Key points:
- headless Chrome driver
- randomized delays (`_jitter_delay`) to reduce anti-bot pressure
- target list includes amazon, flipkart, makemytrip, zomato, myntra, nykaa, bigbasket, swiggy, cleartrip, irctc
- writes one JSON per URL to `data/scraped_raw/`

Driver logic:
- prefers local `.chromedriver` or env `CHROMEDRIVER_PATH`
- fallback to webdriver_manager download

`default_url_list(min_pages)`:
- repeats seed URL list and appends `?ds_page=i` synthetic query when needed to reach target count.

### 12.2 `page_parser.py`

Functions:
- `extract_text_chunks()`: visible text strings
- `extract_button_texts()`: button-like selectors
- `extract_timer_snippets()`: regex-based urgency snippets
- `extract_price_snippets()`: rupee/INR price lines
- `parse_html_page()`: structured `ParsedPage`
- `parsed_page_to_records()`: flatten into records with `kind` field

### 12.3 Auto-labeling of scraped text

In `builder.py`, scraped records are assigned labels with `auto_label_text()`, using regex rule sets for all 10 classes.

---

## SECTION 13: RESEARCH AND BENCHMARKING

Files:
- `ml/models/bert_benchmark.py`
- `ml/models/adversarial_test.py`
- `scripts/generate_research_summary.py`
- `research_paper.pdf`

### 13.1 DistilBERT benchmark implementation

`bert_benchmark.py`:
- loads `dataset.csv`
- encodes labels
- train/test split
- tokenizer/model: `distilbert-base-uncased`
- trainer args:
  - epochs 3
  - batch 16
  - lr 2e-5
- computes macro F1 and per-sample latency
- compares with RF loaded from pickle
- writes `model_comparison.json`

### 13.2 Adversarial testing

`adversarial_test.py`:
- applies each transform to dark-slice test set
- uses macro-F1 drop as vulnerability indicator
- writes `adversarial_robustness.json`

### 13.3 Research summary generator

`generate_research_summary.py`:
- loads live JSON metrics
- creates report sections
- builds PDF with ReportLab
- includes comparison table

### 13.4 `research_paper.pdf` (current content)

Your stored PDF includes:
- abstract with macro F1 reference
- dataset/methodology/results/discussion/conclusion
- model comparison table

---

## SECTION 14: END-TO-END WALKTHROUGH

### Scenario A: User visits Flipkart page with extension

1. Chrome injects content scripts from manifest.
2. `content.js` executes `dsRunScan()`.
3. DOM text nodes extracted with filtering.
4. Prefilter narrows candidate list.
5. Classifier runs in selected mode:
   - local: keyword+ONNX
   - api: POST `/api/classify`
6. Non-`none` labels are highlighted via `highlighter.js`.
7. Scan payload saved into chrome storage.
8. Message `DS_UPDATE` sent to `background.js`.
9. Badge shows count.
10. Popup opened:
    - reads scan payload
    - calls `/api/site-score`
    - renders gauge, breakdown, details
11. User clicks pattern row:
    - popup sends `DS_FOCUS_PATTERN`
    - content script scrolls to highlight and flashes focus ring.

### Scenario B: API query cycle

1. Client POSTs `/api/classify` with text array.
2. `ClassifyRequest.from_json()` validates payload.
3. `_classify_batch()` computes RF prediction + proba.
4. confirm-shaming cosine pass runs.
5. merged label/confidence produced.
6. optional compliance tags attached.
7. JSON array returned.

### Scenario C: Full pipeline run

1. `python ml/scraper/selenium_scraper.py`
   - writes `data/scraped_raw/*.json`.
2. `python ml/dataset/builder.py`
   - writes `data/labeled/dataset.csv`.
3. `python ml/models/train.py`
   - writes RF model + encoder + feature importance JSON.
4. `python ml/models/export_onnx.py`
   - writes `extension/models/darkshield_pipeline.onnx` + labels.
5. `python ml/models/evaluate.py`
   - writes eval JSON/plots + populates SQLite DB.
6. `python -m api.app` + `streamlit run dashboard/app.py`
   - serves API and dashboard.

---

## SECTION 15: TECHNOLOGIES USED — COMPLETE REFERENCE

| Technology | What it is | Why used in DarkShield |
|---|---|---|
| Python | Core backend/ML language | End-to-end orchestration |
| Flask | Lightweight web API | Simple inference + data endpoints |
| SQLite | Embedded relational DB | Local persistence without infra |
| SQLAlchemy | ORM | **Not used in current codebase** |
| scikit-learn | Classical ML toolkit | TF-IDF + RF pipeline |
| TF-IDF | Sparse text representation | Fast interpretable baseline |
| Random Forest | Ensemble classifier | Stable multiclass performance |
| DistilBERT/Transformers | Deep NLP benchmark | Research comparison only |
| ONNX / skl2onnx | Cross-runtime model export | Browser local inference support |
| ONNX Runtime Web | ONNX execution in JS | Extension local mode |
| Selenium | Browser automation | Real-site scraping to JSON |
| BeautifulSoup | HTML parsing | Text/button extraction in parser |
| NLTK WordNet | Lexical resource | Data augmentation synonyms |
| Pandas / NumPy / SciPy | Data/stat stack | Processing + chi-square tests |
| Seaborn / Matplotlib / Plotly | Visualization | Eval plots + dashboard visuals |
| Streamlit | UI for analytics | Rapid local dashboard |
| Chrome Extension MV3 | Browser integration | On-page detection + popup UX |
| JavaScript | Extension runtime | DOM scan, ONNX, popup interactions |
| CORS | Cross-origin policy handling | Extension/API communication |
| Flask-Limiter | Rate limiting | `/api/v1/*` guardrails |
| Joblib | Model serialization | Persist sklearn and helper bundles |
| ReportLab | PDF generation | Auto research summary PDF |
| Schedule | simple scheduler | Optional weekly snapshot loop |

---

## SECTION 16: INTERVIEW PREPARATION — QUESTIONS AND ANSWERS

### 1) Why Random Forest over other classifiers?
RF gave strong macro-F1 while remaining straightforward to ship in Python and convert for extension-compatible workflows. It also supports interpretable feature importance and robust multiclass behavior.

### 2) Explain TF-IDF and limitations
TF-IDF weights tokens by per-document frequency and corpus rarity. Limitations: sparse vectors, weak semantic understanding, no deep context. Improvements: contextual embeddings, char-level modeling, hybrid rules + transformers.

### 3) What is chi-square testing here?
It tests whether dark/non-dark prevalence is independent of vertical. Very low p-values imply dependence in this dataset.

### 4) Why ONNX for browser inference?
Interchange format lets model run in JS runtime without Python backend. Alternatives: pure API inference, WebAssembly custom model, TensorFlow.js conversion.

### 5) What does 8.5% failure look like?
False positives/negatives among close categories (e.g., misdirection vs visual_interference; confirm_shaming interplay). Boundary ambiguity and adversarial tokenization are key error sources.

### 6) How does system handle unseen website?
Model predicts from text semantics; unknown domain can still be scored if snippet patterns match learned categories. Domain-specific priors are limited.

### 7) Scale to 10M DAU changes
Move from SQLite to distributed DB, queue inference, horizontally scale API, caching, telemetry pipeline, model serving infra, async retraining, robust privacy governance.

### 8) Ethical concerns
False accusation risk, overconfidence in probabilistic labels, legal interpretation limits, scraping ethics/terms, user consent and storage transparency.

### 9) Dataset improvements
Increase truly scraped diverse data, reduce synthetic ratio, stronger human annotation rounds, active learning for hard negatives, multilingual coverage.

### 10) Cramér’s V vs p-value
p-value tells if association likely non-random; Cramér’s V tells effect size magnitude.

### 11) Precision vs recall tuning
Precision for minimizing false alarms; recall for catching more risky cues. In safety/transparency context, balance is task-dependent; confirm-shaming pass biases toward recall.

### 12) Why MutationObserver?
Modern pages update after initial load. Observer rescans dynamic DOM changes so detections remain current.

### 13) DistilBERT faster in JSON than RF?
Your stored benchmark JSON reports DistilBERT lower latency per sample, but much larger model size and integration complexity. In practice, deployment choice remains RF in this codebase.

### 14) If sites obfuscate text?
Add char/subword models, stronger normalization, OCR for image text, anti-obfuscation transforms in training, adversarial training loops.

### 15) Why confirm-shaming second pass?
It isolates a linguistically specific class with high phrase-level similarity structure and boosts recall by explicit reference matching.

---

## Appendix: Reality checks against requested assumptions

1. `fraud_detector` component is not present; classification logic lives in `api/routes.py` `_classify_batch()`.
2. `schemas.py` uses dataclasses/manual validation, not Pydantic.
3. `temporal_tracker.py` currently snapshots scores; it does not define `INDIAN_SALE_EVENTS` or `generate_temporal_insights()`.
4. SQLAlchemy is not used in repository implementation.
5. Manifest does not currently declare explicit custom CSP block.

