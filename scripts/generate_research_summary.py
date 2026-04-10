#!/usr/bin/env python3
"""
Build a short (≤2 pages) executive PDF from saved experiment JSON under ``ml/models/saved/``.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SAVED = _ROOT / "ml" / "models" / "saved"
EVAL = SAVED / "eval_results"
OUT_PDF = _ROOT / "research_paper.pdf"

INTRO_TEXT = (
    "DarkShield is a transparency-oriented stack that combines a labeled corpus of manipulative UI copy, "
    "a TF–IDF + random forest baseline, optional neural benchmarking, and browser-local ONNX inference. "
    "This note summarizes metrics produced by the repository’s evaluation scripts."
)

CONCLUSION_TEXT = (
    "The random forest baseline remains the practical deployment choice when latency and bundle size dominate; "
    "DistilBERT offers higher offline F1 at a steep per-snippet latency cost. Vertical association tests and "
    "per-pattern χ² probes help characterize sector-specific prevalence. See Princeton DAPD (Mathur et al., 2019), "
    "FTC (2022) dark pattern report, CNIL/EU guidance, and CPRA/CCPA rulemaking themes for regulatory context."
)

REFERENCES = (
    "Mathur, A. et al. (2019). Dark Patterns at Scale. Princeton Web Transparency — DAPD. "
    "FTC (2022). Bringing Dark Patterns to Light. "
    "EU Digital Services Act / Omnibus consumer fairness instruments; CNIL cookie/consent guidance. "
    "California CPRA / CCPA regulations — dark pattern and deceptive design themes."
)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def generate_abstract(eval_results: dict) -> str:
    f1 = eval_results.get("macro_f1_merged_pred")
    ts = eval_results.get("evaluated_at", "")
    return (
        f"We report macro-F1 {f1} (merged confirm-shaming pass) on a stratified holdout when available "
        f"(evaluated_at={ts}). Chi-square outputs quantify vertical heterogeneity in dark-pattern prevalence."
    )


def generate_dataset_section() -> str:
    csv_path = _ROOT / "data" / "labeled" / "dataset.csv"
    n = 0
    if csv_path.exists():
        n = max(0, sum(1 for _ in csv_path.open(encoding="utf-8")) - 1)
    return (
        f"The training table ``dataset.csv`` contains approximately {n} rows after merges from seed, scraped pages, "
        "synthetic clean lines, Princeton DAPD–inspired synthetics, FTC-themed vignettes, and CNIL-aligned examples, "
        "with cosine de-duplication and adversarial augmentation in the builder pipeline."
    )


def generate_methodology_section(model_comparison: dict) -> str:
    if not model_comparison:
        return "Methodology: TF–IDF + RandomForest pipeline; optional DistilBERT fine-tune via HuggingFace Trainer."
    mc = model_comparison.get("comparison_table") or {}
    rf = mc.get("Random Forest", {})
    bert = mc.get("DistilBERT", {})
    return (
        f"Baseline RF macro-F1 ≈ {rf.get('macro_f1')}; DistilBERT macro-F1 ≈ {bert.get('macro_f1')}. "
        f"Latency (ms/snippet): RF {rf.get('latency_ms_per_sample')}, BERT {bert.get('latency_ms_per_sample')}. "
        f"Conclusion recorded in JSON: {model_comparison.get('conclusion', '')}"
    )


def generate_results_section(eval_results: dict, chi_square: dict) -> str:
    chi = eval_results.get("chi2_vertical_dark") or chi_square.get("vertical_vs_is_dark") or {}
    v = chi.get("cramers_v")
    p = chi.get("p_value")
    return (
        f"Global vertical × dark-pattern association: χ² p-value={p}, Cramér's V={v}. "
        f"Per-pattern tests and a prevalence heatmap are saved under ``{EVAL.relative_to(_ROOT)}``."
    )


def generate_discussion_section(chi_square: dict) -> str:
    per = chi_square.get("per_pattern") or {}
    sig = [k for k, v in per.items() if isinstance(v, dict) and v.get("significant_01")]
    return (
        "Patterns with significant vertical association (p<0.01) include: "
        + (", ".join(sig) if sig else "see per_pattern in chi_square_results.json")
        + ". Effect sizes should be interpreted alongside sampling bias from scrapers and synthetic rows."
    )


def build_pdf(sections: list, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "T",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=10,
        textColor=colors.HexColor("#0d1117"),
    )
    body = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14)
    story = []
    story.append(Paragraph("DarkShield — Research summary (auto-generated)", title_style))
    story.append(Paragraph(f"Generated {datetime.now(timezone.utc).date().isoformat()} UTC", body))
    story.append(Spacer(1, 12))
    for heading, text in sections:
        story.append(Paragraph(f"<b>{heading}</b>", body))
        story.append(Paragraph(text.replace("&", "&amp;"), body))
        story.append(Spacer(1, 8))

    mc = _read_json(SAVED / "model_comparison.json", {})
    tab = (mc or {}).get("comparison_table") or {}
    if tab:
        rows = [["Model", "Macro F1", "Latency ms/snippet", "Size"]]
        rf = tab.get("Random Forest", {})
        db = tab.get("DistilBERT", {})
        rows.append(
            [
                "Random Forest",
                str(rf.get("macro_f1", "")),
                str(rf.get("latency_ms_per_sample", "")),
                str(rf.get("size_mb", "")),
            ]
        )
        rows.append(
            [
                "DistilBERT",
                str(db.get("macro_f1", "")),
                str(db.get("latency_ms_per_sample", "")),
                str(db.get("size_mb", "")),
            ]
        )
        t = Table(rows, colWidths=[4 * cm, 3 * cm, 3.2 * cm, 3 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00ff88")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0d1117")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(Spacer(1, 6))
        story.append(t)

    doc.build(story)


def generate_paper() -> Path:
    summary_full = _read_json(EVAL / "summary.json", {})
    metrics = _read_json(EVAL / "metrics.json", {})
    eval_results = {**summary_full, **metrics}
    chi_square = _read_json(EVAL / "chi_square_results.json", {})
    model_comparison = _read_json(SAVED / "model_comparison.json", {})

    sections = [
        ("Abstract", generate_abstract(eval_results)),
        ("1. Introduction", INTRO_TEXT),
        ("2. Dataset", generate_dataset_section()),
        ("3. Methodology", generate_methodology_section(model_comparison)),
        ("4. Results", generate_results_section(eval_results, chi_square)),
        ("5. Discussion", generate_discussion_section(chi_square)),
        ("6. Conclusion", CONCLUSION_TEXT),
        ("References", REFERENCES),
    ]
    build_pdf(sections, OUT_PDF)
    return OUT_PDF


if __name__ == "__main__":
    p = generate_paper()
    print("Wrote", p)
