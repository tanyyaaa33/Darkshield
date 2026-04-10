"""
Adversarial robustness tests: obfuscation transforms and F1 drop reporting.

Mitigations are implemented in ``ml.dataset.text_normalize`` and applied in dataset builder.
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.dataset.text_normalize import normalize_text

DATASET_CSV = _ROOT / "data" / "labeled" / "dataset.csv"
MODEL_PATH = _ROOT / "ml" / "models" / "saved" / "darkshield_rf.pkl"
EVAL_DIR = _ROOT / "ml" / "models" / "saved" / "eval_results"

ADVERSARIAL_TRANSFORMS: Dict[str, Callable[[str], str]] = {
    "leet_speak": lambda t: t.replace("o", "0").replace("O", "0").replace("e", "3").replace("E", "3").replace("i", "1").replace("I", "1"),
    "unicode_substitution": lambda t: t.replace("a", "\u0430").replace("A", "\u0410"),
    "css_hidden_text": lambda t: f'<span style="display:none">{t}</span>',
    "zero_width_chars": lambda t: t.replace(" ", " \u200b"),
    "split_words": lambda t: " ".join(
        [w[: max(1, len(w) // 2)] + "\u200b" + w[max(1, len(w) // 2) :] if len(w) > 2 else w for w in t.split()]
    ),
}


def apply_transform(name: str, text: str) -> str:
    fn = ADVERSARIAL_TRANSFORMS[name]
    return fn(text)


def apply_obfuscation_random(text: str, rng: random.Random) -> Tuple[str, str]:
    """Apply one random adversarial transform; return (new_text, transform_name)."""
    name = rng.choice(list(ADVERSARIAL_TRANSFORMS.keys()))
    return apply_transform(name, text), name


def _strip_html_for_model(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def prepare_for_classifier(text: str) -> str:
    """Pipeline-side mitigation: normalize + strip injected HTML wrappers."""
    t = _strip_html_for_model(text)
    return normalize_text(t)


def run_adversarial_report(
    seed: int = 42,
    n_samples: int = 100,
    test_size: float = 0.2,
) -> Dict[str, Any]:
    """
    Measure macro-F1 drop on held-out dark-pattern texts after each transform.

    Uses the same stratified split seed as training for comparability.
    """
    df = pd.read_csv(DATASET_CSV)
    df = df.dropna(subset=["text", "label"])
    dark = df[df["label"].ne("none")].copy()
    if len(dark) < n_samples:
        n_samples = len(dark)
    rng = random.Random(seed)
    sample = dark.sample(n=n_samples, random_state=seed)

    pipe = joblib.load(MODEL_PATH)
    all_labels = list(pipe.named_steps["clf"].classes_)

    X_full = df["text"].astype(str)
    y_full = df["label"].astype(str)
    _, X_test, _, y_test = train_test_split(X_full, y_full, test_size=test_size, random_state=seed, stratify=y_full)
    mask = y_test.ne("none")
    X_dark = X_test[mask].reset_index(drop=True)
    y_dark = y_test[mask].reset_index(drop=True)
    if len(X_dark) > n_samples:
        idx = rng.sample(range(len(X_dark)), n_samples)
        X_dark = X_dark.iloc[idx].reset_index(drop=True)
        y_dark = y_dark.iloc[idx].reset_index(drop=True)

    base_pred = pipe.predict(X_dark.tolist())
    base_f1 = f1_score(y_dark, base_pred, average="macro", zero_division=0)

    rows = []
    for tname, fn in ADVERSARIAL_TRANSFORMS.items():
        obf = [prepare_for_classifier(fn(x)) for x in X_dark.tolist()]
        pred = pipe.predict(obf)
        f1o = f1_score(y_dark, pred, average="macro", zero_division=0)
        drop = float(base_f1 - f1o)
        risk = "HIGH RISK" if drop > 0.25 else "Moderate" if drop > 0.12 else "Low"
        rows.append({"transform": tname, "f1_drop": round(drop, 4), "obfuscated_f1": round(float(f1o), 4), "vulnerable": risk})

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVAL_DIR / "adversarial_robustness.json"
    payload = {"baseline_macro_f1_dark_slice": float(base_f1), "n_samples": int(len(X_dark)), "results": rows}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Adversarial Robustness Report:")
    print(f"{'Transform':<24} | {'F1 Drop':>8} | {'Vulnerable?':>12}")
    for r in rows:
        print(f"{r['transform']:<24} | {r['f1_drop']:>+8.2f} | {r['vulnerable']:>12}")
    return payload


if __name__ == "__main__":
    run_adversarial_report()
