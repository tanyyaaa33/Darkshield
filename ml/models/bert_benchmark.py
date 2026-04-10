"""
Research-only DistilBERT fine-tuning benchmark vs the production RandomForest pipeline.

Not used by the Flask API or Chrome extension.
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from transformers import (
    DistilBertForSequenceClassification,
    DistilBertTokenizer,
    Trainer,
    TrainingArguments,
)

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DATASET_CSV = _ROOT / "data" / "labeled" / "dataset.csv"
MODEL_DIR = _ROOT / "ml" / "models" / "saved"
RF_PATH = MODEL_DIR / "darkshield_rf.pkl"
BERT_OUT = MODEL_DIR / "distilbert_darkshield"
COMP_PATH = MODEL_DIR / "model_comparison.json"


class _TextDataset(torch.utils.data.Dataset):
    def __init__(self, texts, labels, tokenizer, max_length: int):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        item = {k: v.squeeze(0) for k, v in enc.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
        return item


def _dir_size_mb(path: Path) -> float:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return round(total / (1024 * 1024), 2)


def _file_size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 2) if path.exists() else 0.0


def run_benchmark(seed: int = 42, test_size: float = 0.2) -> dict:
    if not DATASET_CSV.exists():
        raise FileNotFoundError(DATASET_CSV)
    if not RF_PATH.exists():
        raise FileNotFoundError("Train RandomForest first: ml/models/train.py")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        print("No GPU found — training will be slow (~30 min on CPU)")
        warnings.warn("No GPU detected — DistilBERT fine-tuning will be slow on CPU.", UserWarning)

    df = pd.read_csv(DATASET_CSV).dropna(subset=["text", "label"])
    texts = df["text"].astype(str).tolist()
    labels_raw = df["label"].astype(str).tolist()
    classes = sorted(set(labels_raw))
    lab2id = {c: i for i, c in enumerate(classes)}
    y_ids = [lab2id[t] for t in labels_raw]

    X_train, X_test, y_train, y_test = train_test_split(
        texts, y_ids, test_size=test_size, random_state=seed, stratify=y_ids
    )

    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
    model = DistilBertForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", num_labels=len(classes)
    )

    train_ds = _TextDataset(X_train, y_train, tokenizer, 128)
    test_ds = _TextDataset(X_test, y_test, tokenizer, 128)

    args = TrainingArguments(
        output_dir=str(BERT_OUT / "trainer_out"),
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        learning_rate=2e-5,
        weight_decay=0.01,
        logging_steps=50,
        eval_strategy="epoch",
        save_strategy="no",
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=test_ds,
    )
    trainer.train()

    BERT_OUT.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(BERT_OUT))
    tokenizer.save_pretrained(str(BERT_OUT))

    model.eval()
    model.to(device)

    def bert_predict_batch(txts: list[str]) -> np.ndarray:
        enc = tokenizer(
            txts,
            truncation=True,
            padding=True,
            max_length=128,
            return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            logits = model(**enc).logits
            pred = torch.argmax(logits, dim=-1).cpu().numpy()
        return pred

    y_test_labels = [classes[i] for i in y_test]
    bert_pred_ids = bert_predict_batch(X_test)
    bert_pred_labels = [classes[i] for i in bert_pred_ids]
    bert_f1 = f1_score(y_test_labels, bert_pred_labels, average="macro", zero_division=0)

    # Latency DistilBERT (single-sample average)
    n_lat = min(40, len(X_test))
    t0 = time.perf_counter()
    for i in range(n_lat):
        _ = bert_predict_batch([X_test[i]])
    bert_ms = (time.perf_counter() - t0) / n_lat * 1000.0

    pipe = joblib.load(RF_PATH)
    rf_pred = pipe.predict(X_test)
    rf_f1 = f1_score(y_test_labels, rf_pred, average="macro", zero_division=0)

    t1 = time.perf_counter()
    for i in range(n_lat):
        _ = pipe.predict([X_test[i]])
    rf_ms = (time.perf_counter() - t1) / n_lat * 1000.0

    rf_size = _file_size_mb(RF_PATH)
    bert_size = _dir_size_mb(BERT_OUT)

    ratio = bert_ms / max(rf_ms, 1e-6)
    tradeoff_pct = abs(bert_f1 - rf_f1) / max(rf_f1, 1e-6) * 100.0

    table = {
        "Random Forest": {
            "macro_f1": round(float(rf_f1), 4),
            "latency_ms_per_sample": round(float(rf_ms), 3),
            "size_mb": rf_size,
        },
        "DistilBERT": {
            "macro_f1": round(float(bert_f1), 4),
            "latency_ms_per_sample": round(float(bert_ms), 3),
            "size_mb": bert_size,
        },
    }

    conclusion = (
        f"RF chosen for extension deployment due to ~{ratio:.0f}x latency advantage "
        f"with ~{tradeoff_pct:.1f}% macro-F1 tradeoff vs DistilBERT on this holdout."
    )

    payload = {
        "device": str(device),
        "comparison_table": table,
        "latency_ratio_bert_over_rf": round(float(ratio), 2),
        "conclusion": conclusion,
        "random_forest": {
            "macro_f1": table["Random Forest"]["macro_f1"],
            "latency_ms": table["Random Forest"]["latency_ms_per_sample"],
            "model_size_mb": table["Random Forest"]["size_mb"],
        },
        "distilbert": {
            "macro_f1": table["DistilBERT"]["macro_f1"],
            "latency_ms": table["DistilBERT"]["latency_ms_per_sample"],
            "model_size_mb": table["DistilBERT"]["size_mb"],
        },
        "deployment_choice": "random_forest",
        "reason": f"{ratio:.0f}x latency advantage with ~{tradeoff_pct:.1f}% macro-F1 tradeoff — chosen for browser extension",
    }
    COMP_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Model          | Macro F1 | Latency (ms/sample) | Size")
    print(f"Random Forest  |  {table['Random Forest']['macro_f1']:<8}|  {table['Random Forest']['latency_ms_per_sample']}ms{' ' * (18 - len(str(table['Random Forest']['latency_ms_per_sample'])))}| {table['Random Forest']['size_mb']}MB")
    print(f"DistilBERT     |  {table['DistilBERT']['macro_f1']:<8}|  {table['DistilBERT']['latency_ms_per_sample']}ms{' ' * (18 - len(str(table['DistilBERT']['latency_ms_per_sample'])))}| {table['DistilBERT']['size_mb']}MB")
    print(conclusion)
    return payload


if __name__ == "__main__":
    run_benchmark()
