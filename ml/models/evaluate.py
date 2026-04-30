"""
Full model evaluation, confusion matrix export, chi-square tests, and vertical charts.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from scipy.stats import chi2_contingency
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.database.site_scorer import compute_manipulation_score
from ml.database.transparency_db import init_db, replace_detections_for_site, upsert_site
from ml.models.confirm_shaming_nlp import ConfirmShamingNLP

DATASET_CSV = _ROOT / "data" / "labeled" / "dataset.csv"
MODEL_PATH = _ROOT / "ml" / "models" / "saved" / "darkshield_rf.pkl"
EVAL_DIR = _ROOT / "ml" / "models" / "saved" / "eval_results"
DB_PATH = _ROOT / "data" / "darkshield.db"

CATEGORIES = [
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
]


def cramers_v(chi2: float, n: int, r: int, k: int) -> float:
    """Cramér's V effect size for an r×k contingency table."""
    if n <= 0 or min(r, k) < 2:
        return 0.0
    return float(np.sqrt(chi2 / (n * (min(r, k) - 1))))


def _load_data(seed: int = 42):
    df = pd.read_csv(DATASET_CSV)
    df = df.dropna(subset=["text", "label"])
    X = df["text"].astype(str)
    y = df["label"].astype(str)
    meta = df[["site", "vertical"]].copy()
    X_train, X_test, y_train, y_test, m_train, m_test = train_test_split(
        X, y, meta, test_size=0.2, random_state=seed, stratify=y
    )
    X_test = X_test.reset_index(drop=True)
    y_test = y_test.reset_index(drop=True)
    m_test = m_test.reset_index(drop=True)
    return X_train, X_test, y_train, y_test, m_test


def run_evaluation() -> dict:
    """Evaluate saved pipeline; write plots and JSON summary under ``eval_results``."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    pipe = joblib.load(MODEL_PATH)
    cs = ConfirmShamingNLP.load()

    X_train, X_test, y_train, y_test, m_test = _load_data()
    pred = pipe.predict(X_test)
    proba = pipe.predict_proba(X_test)
    classes = list(pipe.named_steps["clf"].classes_)

    merged_pred = []
    for i, txt in enumerate(X_test):
        flag, cos_conf = cs.classify(txt)
        rf_lab = pred[i]
        if rf_lab == "confirm_shaming" or flag:
            merged_pred.append("confirm_shaming")
        else:
            merged_pred.append(rf_lab)

    macro_f1 = f1_score(y_test, merged_pred, average="macro")
    report = classification_report(y_test, merged_pred, zero_division=0)
    cm = confusion_matrix(y_test, merged_pred, labels=sorted(y_test.unique()))

    print("Macro F1 (with confirm-shaming merge on predictions):", round(macro_f1, 4))
    print(report)

    labels = sorted(y_test.unique().tolist())
    fig_cm = go.Figure(
        data=go.Heatmap(
            z=cm,
            x=labels,
            y=labels,
            colorscale="Reds",
            colorbar=dict(title="Count"),
        )
    )
    fig_cm.update_layout(
        title="DarkShield Confusion Matrix (holdout)",
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        xaxis=dict(tickangle=75),
        yaxis=dict(autorange="reversed"),
    )
    cm_path = EVAL_DIR / "confusion_matrix.html"
    fig_cm.write_html(str(cm_path))

    # Chi-square: vertical × is_dark
    m_test = m_test.reset_index(drop=True)
    is_dark = y_test.ne("none").astype(int)
    vert = m_test["vertical"].astype(str)
    ct = pd.crosstab(vert, is_dark)
    chi2, p, dof, expected = 0.0, 1.0, 0, None
    n_total = int(ct.values.sum()) if ct.size else 0
    n_verticals, n_cols = ct.shape if ct.size else (0, 0)
    V = 0.0
    v_label = "Weak"
    try:
        if ct.shape[0] >= 2 and ct.shape[1] >= 2 and n_total > 0:
            chi2, p, dof, expected = chi2_contingency(ct.values)
            V = cramers_v(float(chi2), n_total, int(n_verticals), int(n_cols))
            v_label = "Strong" if V > 0.3 else "Moderate" if V > 0.1 else "Weak"
    except ValueError:
        chi2, p, dof = 0.0, 1.0, 0
    print("\nChi-square test: vertical × is_dark_pattern")
    print("chi2=", chi2, "p-value=", p, "dof=", dof)
    print(f"Cramér's V = {V:.3f} — {v_label} effect size")
    travel_fmcg = None
    if "travel" in ct.index and "fmcg" in ct.index:
        sub = ct.loc[["travel", "fmcg"]]
        chi2_2, p_2, _, _ = chi2_contingency(sub.values)
        travel_fmcg = {"chi2": float(chi2_2), "p_value": float(p_2)}
        print("Travel vs FMCG subset chi2=", chi2_2, "p=", p_2)

    per_pattern: dict = {}
    print("\nPer-pattern vertical association (label vs rest, χ²):")
    for pattern in CATEGORIES:
        mask = y_test.isin([pattern, "none"])
        if int(mask.sum()) < 20:
            continue
        sub_v = m_test[mask]["vertical"]
        sub_y = y_test[mask].eq(pattern).astype(int)
        contingency = pd.crosstab(sub_v, sub_y)
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            continue
        try:
            chi_p, p_p, dof_p, _ = chi2_contingency(contingency.values)
        except ValueError:
            continue
        sig = "SIGNIFICANT" if p_p < 0.01 else "not significant"
        print(f"{pattern}: chi2={chi_p:.2f}, p={p_p:.4f}, {sig}")
        per_pattern[pattern] = {
            "chi2": float(chi_p),
            "p_value": float(p_p),
            "dof": int(dof_p),
            "significant_01": bool(p_p < 0.01),
        }

    # Prevalence heatmap: vertical × label (% of rows in that vertical)
    prev = (
        pd.crosstab(m_test["vertical"].astype(str).values, y_test.astype(str).values, normalize="index")
        * 100.0
    )
    prev = prev.sort_index(axis=0)
    plt.figure(figsize=(max(10, prev.shape[1] * 0.45), max(4, prev.shape[0] * 0.35)))
    sns.heatmap(prev, annot=True, fmt=".1f", cmap="magma", vmin=0, vmax=100, cbar_kws={"label": "%"})
    plt.title("Pattern prevalence by vertical (holdout, % of vertical)")
    plt.ylabel("vertical")
    plt.xlabel("label")
    plt.tight_layout()
    heat_path = EVAL_DIR / "vertical_pattern_heatmap.png"
    plt.savefig(str(heat_path), dpi=150, bbox_inches="tight")
    plt.close()

    # Manipulation score bar by vertical (expected travel highest — driven by label rates in dataset)
    rows = []
    for v in sorted(m_test["vertical"].unique()):
        mask = m_test["vertical"].eq(v)
        labels = y_test[mask]
        texts = X_test[mask]
        patterns = labels[labels.ne("none")].tolist()
        score = compute_manipulation_score(len(patterns), int(len(texts)), patterns)
        rows.append({"vertical": v, "manipulation_score": score})
    vert_df = pd.DataFrame(rows)
    fig2 = px.bar(
        vert_df,
        x="manipulation_score",
        y="vertical",
        orientation="h",
        title="Mean manipulation score proxy by vertical (evaluation slice)",
        color="manipulation_score",
        color_continuous_scale="Reds",
    )
    fig2.write_html(str(EVAL_DIR / "vertical_manipulation_bar.html"))

    summary = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "macro_f1_merged_pred": float(macro_f1),
        "chi2_vertical_dark": {
            "chi2": float(chi2),
            "p_value": float(p),
            "dof": int(dof),
            "cramers_v": float(V),
            "cramers_v_interpretation": v_label,
            "n": n_total,
            "n_rows": int(n_verticals),
            "n_cols": int(n_cols),
        },
        "travel_vs_fmcg": travel_fmcg,
        "contingency_table": ct.to_dict(),
        "per_pattern_vertical_chi2": per_pattern,
        "vertical_pattern_heatmap": str(heat_path.relative_to(_ROOT)),
    }
    (EVAL_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    metrics_payload = {
        "evaluated_at": summary["evaluated_at"],
        "macro_f1_merged_pred": float(macro_f1),
        "travel_vs_fmcg": travel_fmcg,
    }
    (EVAL_DIR / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    chi_square_payload = {
        "vertical_vs_is_dark": {
            "chi2": float(chi2),
            "p_value": float(p),
            "dof": int(dof),
            "cramers_v": float(V),
            "interpretation": v_label,
            "n": n_total,
        },
        "per_pattern": per_pattern,
    }
    (EVAL_DIR / "chi_square_results.json").write_text(json.dumps(chi_square_payload, indent=2), encoding="utf-8")

    # Populate transparency DB from evaluation predictions
    init_db(DB_PATH)
    df_eval = m_test.copy()
    df_eval["text"] = X_test.values
    df_eval["true_label"] = y_test.values
    df_eval["pred_label"] = merged_pred
    df_eval["is_dark"] = df_eval["true_label"].ne("none")
    confs = []
    for i, lab in enumerate(merged_pred):
        txt = str(X_test.iloc[i])
        flag, cos_conf = cs.classify(txt)
        if lab in classes:
            j = classes.index(lab)
            base = float(proba[i, j])
        else:
            base = 0.0
        if lab == "confirm_shaming":
            confs.append(float(max(base, cos_conf if flag else base)))
        else:
            confs.append(base)
    df_eval["confidence"] = confs

    for domain, g in df_eval.groupby(df_eval["site"].astype(str)):
        # Public corpora use anonymized placeholder domains like "*.example".
        # For the dashboard, we want only real scraped/seed domains.
        if str(domain).endswith(".example"):
            continue
        patterns = g["pred_label"][g["pred_label"].ne("none")].tolist()
        score = compute_manipulation_score(
            int(g["pred_label"].ne("none").sum()),
            len(g),
            patterns,
        )
        vert_series = g["vertical"].astype(str)
        vertical = str(vert_series.mode().iloc[0]) if not vert_series.mode().empty else str(vert_series.iloc[0])
        upsert_site(
            DB_PATH,
            domain=domain,
            vertical=vertical,
            total_patterns=int(g["pred_label"].ne("none").sum()),
            manipulation_score=score,
            pages_analyzed=len(g),
        )
        dets = []
        for _, r in g.iterrows():
            if r["pred_label"] == "none":
                continue
            dets.append(
                {
                    "pattern_category": r["pred_label"],
                    "text_snippet": r["text"][:500],
                    "url": f"https://{domain}/eval-row",
                    "confidence": float(r["confidence"]),
                }
            )
        replace_detections_for_site(DB_PATH, domain, dets)

    return summary


if __name__ == "__main__":
    run_evaluation()
