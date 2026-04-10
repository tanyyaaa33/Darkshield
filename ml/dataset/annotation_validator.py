"""
Human validation set export and inter-annotator agreement metrics.

Fill ``label_human1``..``label_human3`` in the CSV, then run ``compute_agreement``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DATASET_CSV = _ROOT / "data" / "labeled" / "dataset.csv"
VALIDATION_CSV = _ROOT / "data" / "labeled" / "human_validation_set.csv"
EVAL_DIR = _ROOT / "ml" / "models" / "saved" / "eval_results"


def _interpret_kappa(k: float) -> str:
    if k > 0.8:
        return "Almost perfect agreement — labels are highly reliable"
    if k >= 0.6:
        return "Substantial agreement — labels are reliable"
    return "Moderate agreement — consider label refinement"


def fleiss_kappa(rating_matrix: np.ndarray) -> float:
    """
    Fleiss' kappa for N subjects and k categories.

    ``rating_matrix`` shape (N, k): each row counts how many raters chose category j.
    All rows must sum to the same n (number of raters per item).
    """
    assert rating_matrix.ndim == 2
    n_items, k = rating_matrix.shape
    n_raters = rating_matrix.sum(axis=1)
    if not np.all(n_raters == n_raters[0]):
        raise ValueError("Each row must have the same number of rater assignments")
    n = int(n_raters[0])
    if n < 2:
        return 0.0

    p_j = rating_matrix.sum(axis=0) / (n_items * n)
    p_e = float(np.sum(p_j**2))

    p_i = np.zeros(n_items)
    for i in range(n_items):
        row = rating_matrix[i]
        p_i[i] = (np.sum(row * (row - 1))) / (n * (n - 1))
    p_bar = float(np.mean(p_i))

    if p_e >= 1.0:
        return 0.0
    return float((p_bar - p_e) / (1.0 - p_e))


def build_validation_set(n: int = 200, seed: int = 42) -> Path:
    """
    Stratified sample of ``n`` rows; write CSV with empty human label columns.
    """
    df = pd.read_csv(DATASET_CSV)
    df = df.dropna(subset=["text", "label"])
    rng = np.random.RandomState(seed)
    parts = []
    for lab, g in df.groupby("label"):
        k = max(1, int(round(n * len(g) / len(df))))
        parts.append(g.sample(n=min(k, len(g)), random_state=rng.randint(0, 10_000)))
    sample = pd.concat(parts, ignore_index=True)
    if len(sample) > n:
        sample = sample.sample(n=n, random_state=seed).reset_index(drop=True)
    elif len(sample) < n:
        extra = df.sample(n=n - len(sample), random_state=seed)
        sample = pd.concat([sample, extra], ignore_index=True).drop_duplicates(subset=["text"]).head(n)

    out = pd.DataFrame(
        {
            "id": range(1, len(sample) + 1),
            "text": sample["text"].astype(str),
            "label_model": sample["label"].astype(str),
            "label_human1": "",
            "label_human2": "",
            "label_human3": "",
        }
    )
    VALIDATION_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(VALIDATION_CSV, index=False, encoding="utf-8")
    print("Wrote", VALIDATION_CSV, "rows=", len(out))
    return VALIDATION_CSV


def compute_agreement(filepath: Optional[Path] = None) -> Dict[str, Any]:
    """
    After humans fill ``label_human*``, compute Cohen's kappa vs model and Fleiss kappa.
    """
    path = Path(filepath or VALIDATION_CSV)
    df = pd.read_csv(path)
    for col in ("label_human1", "label_human2", "label_human3"):
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col] == "", col] = np.nan

    filled = df.dropna(subset=["label_human1", "label_human2", "label_human3"], how="any")
    if filled.empty:
        raise ValueError("No rows with all three human labels filled.")

    y_m = filled["label_model"].astype(str)
    kappas = {}
    for i in (1, 2, 3):
        col = f"label_human{i}"
        k = cohen_kappa_score(y_m, filled[col])
        kappas[f"cohen_kappa_model_vs_human{i}"] = float(k)
        print(f"Cohen kappa (model vs human{i}): {k:.4f} — {_interpret_kappa(k)}")

    labels = sorted(pd.unique(pd.concat([filled["label_human1"], filled["label_human2"], filled["label_human3"]])))
    lab_to_idx = {l: i for i, l in enumerate(labels)}
    mat = np.zeros((len(filled), len(labels)), dtype=int)
    for r, (_, row) in enumerate(filled.iterrows()):
        for col in ("label_human1", "label_human2", "label_human3"):
            mat[r, lab_to_idx[str(row[col])]] += 1
    fk = fleiss_kappa(mat)
    print(f"Fleiss kappa (3 annotators): {fk:.4f} — {_interpret_kappa(fk)}")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "n_rows": int(len(filled)),
        **kappas,
        "fleiss_kappa": float(fk),
        "interpretation_fleiss": _interpret_kappa(fk),
    }
    (EVAL_DIR / "annotation_agreement.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["build", "score"])
    args = p.parse_args()
    if args.cmd == "build":
        build_validation_set()
    else:
        compute_agreement()
