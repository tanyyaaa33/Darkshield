"""
Train TF-IDF + Random Forest pipeline for DarkShield multi-class classification.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.dataset.feature_engineer import preprocess_for_model

DATASET_CSV = _ROOT / "data" / "labeled" / "dataset.csv"
MODEL_DIR = _ROOT / "ml" / "models" / "saved"


def build_pipeline() -> Pipeline:
    """Create the sklearn estimator pipeline per project specification."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 3),
                    max_features=15000,
                    sublinear_tf=True,
                    analyzer="word",
                ),
            ),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=300,
                    class_weight="balanced",
                    max_depth=None,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _top_feature_importance(pipeline: Pipeline, top_k: int = 20) -> list:
    tfidf: TfidfVectorizer = pipeline.named_steps["tfidf"]
    clf: RandomForestClassifier = pipeline.named_steps["clf"]
    names = tfidf.get_feature_names_out()
    imp = clf.feature_importances_
    order = imp.argsort()[::-1][:top_k]
    return [{"feature": names[i], "importance": float(imp[i])} for i in order]


def train_and_save(test_size: float = 0.2, seed: int = 42) -> dict:
    """
    Load dataset, train/test split, fit pipeline, persist artifacts.

    :return: Dict with macro F1 and paths written.
    """
    if not DATASET_CSV.exists():
        raise FileNotFoundError(f"Missing {DATASET_CSV}; run ml/dataset/builder.py first.")

    df = pd.read_csv(DATASET_CSV)
    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).map(preprocess_for_model)
    df = df[df["text"].str.len() >= 8]
    X = df["text"].astype(str)
    y = df["label"].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    le = LabelEncoder()
    le.fit(y)

    # Upsample minority classes in the training fold to improve macro-F1 stability
    tr = pd.DataFrame({"text": X_train, "label": y_train})
    max_n = int(tr["label"].value_counts().max())
    parts = []
    for lab, sub in tr.groupby("label"):
        if len(sub) < max_n:
            sub = sub.sample(n=max_n, replace=True, random_state=seed)
        parts.append(sub)
    tr_bal = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed)
    X_train_b = tr_bal["text"].astype(str)
    y_train_b = tr_bal["label"].astype(str)

    pipe = build_pipeline()
    pipe.fit(X_train_b, y_train_b)

    pred = pipe.predict(X_test)
    macro_f1 = f1_score(y_test, pred, average="macro")
    print("Macro F1 (holdout):", round(macro_f1, 4))
    print("\nClassification report:\n", classification_report(y_test, pred, zero_division=0))
    print("Confusion matrix labels:", sorted(y.unique().tolist()))
    print(confusion_matrix(y_test, pred))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_DIR / "darkshield_rf.pkl")
    joblib.dump(le, MODEL_DIR / "label_encoder.pkl")

    fi_path = MODEL_DIR / "feature_importance.json"
    fi_path.write_text(json.dumps(_top_feature_importance(pipe, 20), indent=2), encoding="utf-8")

    return {
        "macro_f1": float(macro_f1),
        "model_path": str(MODEL_DIR / "darkshield_rf.pkl"),
        "encoder_path": str(MODEL_DIR / "label_encoder.pkl"),
        "feature_importance_path": str(fi_path),
    }


if __name__ == "__main__":
    train_and_save()
