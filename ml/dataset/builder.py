"""
Build a labeled CSV from seed data, scraped JSON, and rule-based auto-labeling.
"""

from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.dataset.augmenter import balance_min_per_class
from ml.dataset.dark_patterns_seed import SEED_EXAMPLES
from ml.dataset.external_datasets import get_cnil_examples, get_ftc_examples, get_princeton_inspired_samples
from ml.dataset.text_normalize import normalize_text
from ml.models.adversarial_test import apply_obfuscation_random

SCRAPED_DIR = _ROOT / "data" / "scraped_raw"
LABELED_DIR = _ROOT / "data" / "labeled"
DATASET_CSV = LABELED_DIR / "dataset.csv"

# Canonical vertical for each retailer domain (must stay aligned with `site`, not random labels).
_DOMAIN_VERTICAL: Dict[str, str] = {
    "amazon.in": "electronics",
    "flipkart.com": "electronics",
    "myntra.com": "fashion",
    "nykaa.com": "fmcg",
    "bigbasket.com": "fmcg",
    "zomato.com": "food_delivery",
    "swiggy.com": "food_delivery",
    "makemytrip.com": "travel",
    "cleartrip.com": "travel",
    "irctc.co.in": "travel",
}


def _normalize_domain(site: str) -> str:
    s = str(site).strip().lower()
    if s.startswith("www."):
        s = s[4:]
    return s


def vertical_for_site(site: str) -> str:
    """Return the retail vertical for a domain; unknown sites default to ``ecommerce``."""
    return _DOMAIN_VERTICAL.get(_normalize_domain(site), "ecommerce")


ALL_LABELS = [
    "fake_urgency",
    "confirm_shaming",
    "hidden_costs",
    "visual_interference",
    "sneaking",
    "forced_continuity",
    "misdirection",
    "social_proof_manipulation",
    "bait_and_switch",
    "roach_motel",
    "none",
]


def _match_any(patterns: List[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)


_RULES: List[Tuple[str, List[re.Pattern]]] = [
    (
        "fake_urgency",
        [
            re.compile(r"\bonly\s+\d+\s+left\b", re.I),
            re.compile(r"\b\d{1,2}:\d{2}:\d{2}\b"),
            re.compile(r"\bhurry\b|\blimited\s+(time|stock|offer)\b|\bflash\s+sale\b", re.I),
            re.compile(r"\bends?\s+in\b|\boffer\s+ends\b|\blast\s+few\b", re.I),
            re.compile(r"\bsirf\b|\bjaldi\b|\bbacha\b", re.I),
            re.compile(r"\b\d+\s*(people|users)\s+viewing\b", re.I),
        ],
    ),
    (
        "confirm_shaming",
        [
            re.compile(r"\bno\s+thanks\b.*\b(prefer|want|enjoy)\b", re.I),
            re.compile(r"\bI\s+don'?t\s+want\b.*\b(save|savings|discount)\b", re.I),
            re.compile(r"\bdecline\b.*\b(free|benefit|protection)\b", re.I),
            re.compile(r"\bnahi\b.*\b(chahiye|discount)\b", re.I),
            re.compile(r"\bskip\b.*\b(savings|rewards|cashback)\b", re.I),
        ],
    ),
    (
        "hidden_costs",
        [
            re.compile(
                r"\b(convenience|platform|payment|gateway|processing)\s+fee\b",
                re.I,
            ),
            re.compile(r"\b(taxes?|gst)\b.*\b(checkout|final|payment)\b", re.I),
            re.compile(r"\badditional\s+charges\b|\bsurge\b|\bresort\s+fee\b", re.I),
            re.compile(r"\bshown\s+only\s+(at|before)\s+(checkout|payment)\b", re.I),
            re.compile(r"\bfinal\s+price\b.*\b(page|step)\b", re.I),
        ],
    ),
    (
        "visual_interference",
        [
            re.compile(r"\b(greyed\s+out|grayed\s+out|tiny\s+link|barely\s+visible)\b", re.I),
            re.compile(r"\bpre[- ]selected\b|\bhard\s+to\s+(see|find)\b", re.I),
            re.compile(r"\bclose\s*X\b.*\b(off|hidden)\b", re.I),
            re.compile(r"\bmisleading\s+button\b|\bfake\s+disabled\b", re.I),
        ],
    ),
    (
        "sneaking",
        [
            re.compile(r"\bauto[- ]?added\b|\b(pre[- ]?ticked|pre[- ]?selected)\b", re.I),
            re.compile(r"\badded\s+to\s+cart\b.*\b(default|automatic)\b", re.I),
            re.compile(r"\bdonation\b.*\b(cart|checkout)\b", re.I),
            re.compile(r"\binsurance\b.*\bpre\b", re.I),
        ],
    ),
    (
        "forced_continuity",
        [
            re.compile(r"\bauto[- ]?renew\b|\b(subscription|membership)\b.*\b(charge|billing)\b", re.I),
            re.compile(r"\bfree\s+trial\b.*\b(convert|renews|auto)\b", re.I),
            re.compile(r"\bunless\s+cancelled\b|\brecurring\b", re.I),
            re.compile(r"\b₹\d+/\s*month\b.*\brenew\b", re.I),
        ],
    ),
    (
        "misdirection",
        [
            re.compile(r"\bunsubscribe\b.*\b(tiny|hidden|bottom)\b", re.I),
            re.compile(r"\bskip\b.*\b(below|fold|footer)\b", re.I),
            re.compile(r"\buried\b.*\b(link|option)\b", re.I),
            re.compile(r"\bretention\b.*\b(screen|modal)\b", re.I),
        ],
    ),
    (
        "social_proof_manipulation",
        [
            re.compile(r"\bpeople\s+are\s+viewing\b|\bbooked\s+this\b.*\b(last|hour)\b", re.I),
            re.compile(r"\bfake[- ]looking\b|\b(incentivised|incentivized)\s+reviews\b", re.I),
            re.compile(r"\bamazon'?s\s+choice\b|\bbestseller\b", re.I),
            re.compile(r"\b\d+\+?\s*bought\b|\brated\s+by\b", re.I),
        ],
    ),
    (
        "bait_and_switch",
        [
            re.compile(r"\badvertised\b.*\b(landing|checkout)\b.*\b(₹|INR|higher)\b", re.I),
            re.compile(r"\bfrom\s+₹\b.*\b(becomes|totals)\b", re.I),
            re.compile(r"\bmax\s+discount\b|\bfine\s+print\b|\bexcludes\b", re.I),
            re.compile(r"\bwas\s+₹\b.*\b(inflated|mrp)\b", re.I),
        ],
    ),
    (
        "roach_motel",
        [
            re.compile(r"\bhard\s+to\s+cancel\b|\bclose\s+account\b.*\b(email|support|ticket)\b", re.I),
            re.compile(r"\bunsubscribe\b.*\b(app\s+only|not\s+on\s+website)\b", re.I),
            re.compile(r"\bdelete\s+account\b.*\b(missing|unclear)\b", re.I),
            re.compile(r"\bcancellation\s+fee\b.*\b\d+%\b", re.I),
        ],
    ),
]


def auto_label_text(text: str) -> str:
    """Apply keyword / regex rules; return a dark pattern label or ``none``."""
    t = text.strip()
    if len(t) < 10:
        return "none"
    for label, patterns in _RULES:
        if _match_any(patterns, t):
            return label
    return "none"


def _load_scraped_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not SCRAPED_DIR.exists():
        return rows
    for path in sorted(SCRAPED_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        site = data.get("site", "unknown")
        vertical = data.get("vertical", "electronics")
        for rec in data.get("records", []):
            txt = rec.get("text")
            if not txt or len(str(txt)) < 10:
                continue
            rows.append(
                {
                    "text": str(txt),
                    "label": auto_label_text(str(txt)),
                    "site": site,
                    "vertical": vertical,
                    "source": "scraped",
                }
            )
    return rows


def _synthetic_none_rows(target: int, seed: int = 7) -> List[Dict[str, Any]]:
    """Generate neutral e-commerce lines without dark-pattern cues."""
    rng = random.Random(seed)
    templates = [
        "Return window is {d} days for unused items with tags on {brand}.",
        "Customer support chat available 9 AM–9 PM IST on {brand}.",
        "Track shipment with AWB {n} on {brand} orders.",
        "Standard delivery ETA {d}–{d2} business days for {city} on {brand}.",
        "Product dimensions: {d} cm × {d2} cm; weight {w} kg — {brand} listing.",
        "Warranty: {d} months manufacturer warranty via authorized service on {brand}.",
        "Payment methods: UPI, cards, net banking accepted on {brand}.",
        "Seller rating {s}/5 with {n} ratings on {brand} marketplace.",
        "Menu updated {d} days ago — allergens listed for this dish on {brand}.",
        "PNR {pnr} status: {st} for train {n} on IRCTC partner view {brand}.",
        "Hotel amenity list: Wi‑Fi, breakfast, parking — {brand} details page.",
        "Flight baggage allowance {d} kg economy class — {brand} fare rules.",
        "Size guide: measure bust in inches; refer chart on {brand}.",
        "Ingredients INCI listed; patch test recommended — {brand} beauty.",
        "Grocery storage: refrigerate after opening — {brand} pack label.",
    ]
    brands = [
        ("amazon.in", "electronics"),
        ("flipkart.com", "electronics"),
        ("myntra.com", "fashion"),
        ("nykaa.com", "fmcg"),
        ("bigbasket.com", "fmcg"),
        ("zomato.com", "food_delivery"),
        ("swiggy.com", "food_delivery"),
        ("makemytrip.com", "travel"),
        ("cleartrip.com", "travel"),
        ("irctc.co.in", "travel"),
    ]
    cities = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune", "Kolkata"]
    statuses = ["confirmed", "waitlisted", "RAC", "cancelled"]
    out: List[Dict[str, Any]] = []
    while len(out) < target:
        tpl = rng.choice(templates)
        site, vert = rng.choice(brands)
        text = tpl.format(
            d=rng.randint(3, 30),
            d2=rng.randint(2, 12),
            w=round(rng.uniform(0.2, 8.0), 2),
            brand=site,
            city=rng.choice(cities),
            s=round(rng.uniform(3.8, 4.9), 1),
            n=rng.randint(50, 9999),
            pnr=rng.randint(1000000000, 9999999999),
            st=rng.choice(statuses),
        )
        if auto_label_text(text) != "none":
            continue
        out.append(
            {
                "text": text,
                "label": "none",
                "site": site,
                "vertical": vert,
                "source": "clean",
            }
        )
    return out


def _dedupe_by_text_cosine(df: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
    """Drop near-duplicate rows using TF-IDF cosine similarity (keep first)."""
    texts = df["text"].astype(str).tolist()
    n = len(texts)
    if n <= 1:
        return df.reset_index(drop=True)
    vec = TfidfVectorizer(max_features=9000, min_df=1, ngram_range=(1, 2))
    X = vec.fit_transform(texts)
    rep_indices: List[int] = []
    for i in range(n):
        if not rep_indices:
            rep_indices.append(i)
            continue
        sims = cosine_similarity(X[i], X[rep_indices])[0]
        if sims.size and float(sims.max()) >= threshold:
            continue
        rep_indices.append(i)
    return df.iloc[rep_indices].reset_index(drop=True)


def _append_adversarial_rows(df: pd.DataFrame, seed: int = 42, rate: float = 0.1) -> pd.DataFrame:
    """Add adversarially obfuscated copies of dark-pattern rows for robustness."""
    rng = random.Random(seed)
    dark = df[df["label"].ne("none")]
    if dark.empty:
        return df
    n_add = max(1, int(np.ceil(len(dark) * rate)))
    samp = dark.sample(n=min(n_add, len(dark)), random_state=seed)
    extra: List[Dict[str, Any]] = []
    for _, r in samp.iterrows():
        raw, _name = apply_obfuscation_random(str(r["text"]), rng)
        raw = re.sub(r"<[^>]+>", " ", raw)
        txt = normalize_text(raw)
        if len(txt) < 10:
            continue
        extra.append(
            {
                "text": txt,
                "label": r["label"],
                "site": r["site"],
                "vertical": r["vertical"],
                "source": "augmented",
            }
        )
    if not extra:
        return df
    return pd.concat([df, pd.DataFrame(extra)], ignore_index=True)


def _print_composition(df: pd.DataFrame) -> None:
    """Print dataset composition by ``source`` (approximate buckets)."""
    c = df["source"].fillna("unknown").value_counts()
    total = int(len(df))

    def pct(x: int) -> float:
        return round(100.0 * x / max(total, 1), 1)

    lines = ["Dataset composition:", ""]
    order = [
        ("seed", "Seed examples"),
        ("scraped", "Scraped + labeled"),
        ("princeton_inspired", "Princeton-inspired"),
        ("ftc", "FTC examples"),
        ("cnil", "CNIL examples"),
        ("augmented", "Augmented / adversarial"),
        ("clean", "None (clean)"),
    ]
    for key, title in order:
        v = int(c.get(key, 0))
        if v:
            lines.append(f"{title + ':':<22} {v:>5}  ({pct(v)}%)")
    lines.append(f"{'Total:':<22} {total:>5}")
    print("\n".join(lines))


def _oversample_to_balance(df: pd.DataFrame, min_total: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Resample per class so total row count reaches ``min_total`` with balanced labels."""
    rng = random.Random(seed)
    counts = df["label"].value_counts()
    labels = counts.index.tolist()
    per_class = max(int(min_total / len(labels)), counts.min())
    parts: List[pd.DataFrame] = []
    for lab in labels:
        sub = df[df["label"] == lab]
        if len(sub) >= per_class:
            parts.append(sub.sample(n=per_class, random_state=seed))
        else:
            extra = sub.sample(n=per_class - len(sub), replace=True, random_state=seed)
            parts.append(pd.concat([sub, extra], ignore_index=True))
    out = pd.concat(parts, ignore_index=True)
    return out.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def build_dataset(
    min_total: int = 5200,
    min_per_class: int = 150,
    seed: int = 42,
) -> Path:
    """
    Assemble ``dataset.csv`` under ``data/labeled/``.

    Merges seed, scraped, clean synthetic lines, external corpora (Princeton-style,
    FTC, CNIL), deduplicates, augments, adds adversarial robustness rows, and balances.
    """
    LABELED_DIR.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for ex in SEED_EXAMPLES:
        rows.append(
            {
                "text": ex["text"],
                "label": ex["label"],
                "site": ex["site"],
                "vertical": ex["vertical"],
                "source": "seed",
            }
        )

    rows.extend(_load_scraped_rows())
    rows.extend(_synthetic_none_rows(max(1000, min_total // 2), seed=seed))
    rows.extend(get_princeton_inspired_samples(seed=seed, n=500))
    rows.extend(get_ftc_examples())
    rows.extend(get_cnil_examples())

    df = pd.DataFrame(rows)
    df = df[df["text"].str.len() >= 10]
    df.drop_duplicates(subset=["text", "label"], inplace=True)
    df = _dedupe_by_text_cosine(df, threshold=0.95)

    dict_rows = df.to_dict("records")
    dict_rows = balance_min_per_class(dict_rows, min_per_class=min_per_class, seed=seed)
    df = pd.DataFrame(dict_rows)
    df = _oversample_to_balance(df, min_total=min_total, seed=seed)

    df["text"] = df["text"].map(lambda t: normalize_text(str(t)))
    df = df[df["text"].str.len() >= 10]

    df = _append_adversarial_rows(df, seed=seed, rate=0.10)

    df["vertical"] = df["site"].map(vertical_for_site)

    _print_composition(df)

    df.to_csv(DATASET_CSV, index=False, encoding="utf-8")
    print("Wrote", DATASET_CSV, "rows=", len(df))
    print(Counter(df["label"]))
    return DATASET_CSV


if __name__ == "__main__":
    build_dataset()
