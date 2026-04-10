"""
Flask route handlers for classification, transparency scores, and user reports.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Blueprint, current_app, jsonify, request

from api.schemas import ClassifyRequest, ReportRequest
from ml.compliance.regulatory_mapper import get_compliance_tags
from ml.database.transparency_db import (
    aggregate_stats,
    fetch_all_sites,
    fetch_detections_for_domain,
    fetch_leaderboard,
    insert_user_report,
)

bp = Blueprint("darkshield_api", __name__)

EXPLANATIONS: Dict[str, str] = {
    "fake_urgency": "Uses scarcity or countdown language to rush a purchase decision.",
    "confirm_shaming": "Guilt-inducing opt-out copy that frames declining as a bad choice.",
    "hidden_costs": "Fees, taxes, or surcharges are disclosed late (often at checkout).",
    "visual_interference": "UI styling hides or de-emphasises the user-friendly choice.",
    "sneaking": "Extra items, fees, or subscriptions are added without clear consent.",
    "forced_continuity": "Paid renewal after a trial or subscription without strong notice.",
    "misdirection": "Attention is steered away from unsubscribe, skip, or cheaper options.",
    "social_proof_manipulation": "Questionable popularity or review signals to build false trust.",
    "bait_and_switch": "Advertised price or terms do not match what checkout shows.",
    "roach_motel": "Easy to start or subscribe, difficult to cancel or delete an account.",
    "none": "No strong dark-pattern cues detected in this snippet.",
}


def _classify_batch(texts: List[str], include_compliance: bool = False) -> List[Dict[str, Any]]:
    """Run RF + confirm-shaming second pass for each text."""
    pipe = current_app.config["MODEL_PIPELINE"]
    cs = current_app.config["CONFIRM_SHAMING"]
    classes: List[str] = list(pipe.named_steps["clf"].classes_)
    out: List[Dict[str, Any]] = []
    probs = pipe.predict_proba(texts)
    preds = pipe.predict(texts)
    for i, t in enumerate(texts):
        rf_lab = preds[i]
        flag, cos_conf = cs.classify(t)
        if rf_lab == "confirm_shaming" or flag:
            lab = "confirm_shaming"
        else:
            lab = rf_lab
        if lab in classes:
            j = classes.index(lab)
            conf = float(probs[i, j])
        else:
            conf = 0.0
        if lab == "confirm_shaming":
            conf = float(max(conf, cos_conf if flag else conf))
        row: Dict[str, Any] = {
            "text": t,
            "label": lab,
            "confidence": round(min(1.0, max(0.0, conf)), 4),
            "explanation": EXPLANATIONS.get(lab, EXPLANATIONS["none"]),
        }
        if include_compliance and lab != "none":
            row["compliance"] = get_compliance_tags(lab)
        out.append(row)
    return out


@bp.post("/api/classify")
def classify():
    """Classify a batch of UI text snippets."""
    try:
        body = ClassifyRequest.from_json(request.get_json(force=True, silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if not body.texts:
        return jsonify({"error": "texts empty"}), 400
    inc = body.include_compliance or request.args.get("include_compliance", "").lower() in ("1", "true", "yes")
    results = _classify_batch(body.texts, include_compliance=inc)
    return jsonify(results)


@bp.get("/api/compliance-report")
def compliance_report():
    """Aggregate stored detections for a domain into regulation-oriented buckets."""
    from ml.compliance.regulatory_mapper import generate_compliance_report

    domain = request.args.get("domain", "").strip().lower()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    db_path = current_app.config["DB_PATH"]
    dets = fetch_detections_for_domain(db_path, domain)
    detections = [
        {
            "label": d["pattern_category"],
            "text": d.get("text_snippet", ""),
            "confidence": float(d.get("confidence") or 0.0),
        }
        for d in dets
    ]
    rep = generate_compliance_report(detections)
    return jsonify({"domain": domain, **rep})


@bp.get("/api/site-score")
def site_score():
    """Return stored manipulation metrics for a domain."""
    domain = request.args.get("domain", "").strip().lower()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    db_path = current_app.config["DB_PATH"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT * FROM sites WHERE domain = ?", (domain,))
        row = cur.fetchone()
        if not row:
            return jsonify(
                {
                    "domain": domain,
                    "manipulation_score": 0.0,
                    "pattern_breakdown": {},
                    "rank": -1,
                    "vertical": "unknown",
                }
            )
        site = dict(row)
        cur2 = conn.execute(
            """
            SELECT pattern_category, COUNT(*) c FROM detections d
            JOIN sites s ON s.id = d.site_id
            WHERE s.domain = ?
            GROUP BY pattern_category
            """,
            (domain,),
        )
        breakdown = {r[0]: int(r[1]) for r in cur2.fetchall()}
        all_sites = fetch_all_sites(db_path)
        rank = -1
        for i, s in enumerate(all_sites):
            if str(s["domain"]).lower() == domain:
                rank = i + 1
                break
        return jsonify(
            {
                "domain": domain,
                "manipulation_score": float(site["manipulation_score"]),
                "pattern_breakdown": breakdown,
                "rank": rank,
                "vertical": site["vertical"],
            }
        )
    finally:
        conn.close()


@bp.get("/api/leaderboard")
def leaderboard():
    """Ranked domains, optionally filtered by vertical."""
    vertical = request.args.get("vertical")
    limit = int(request.args.get("limit", 10))
    db_path = current_app.config["DB_PATH"]
    rows = fetch_leaderboard(db_path, vertical=vertical, limit=limit)
    payload = [
        {
            "domain": r["domain"],
            "score": float(r["manipulation_score"]),
            "top_pattern": r["top_pattern"],
            "pages_analyzed": int(r["pages_analyzed"] or 0),
        }
        for r in rows
    ]
    return jsonify(payload)


@bp.post("/api/report")
def report():
    """Persist a user report about a detection."""
    try:
        body = ReportRequest.from_json(request.get_json(force=True, silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    db_path = current_app.config["DB_PATH"]
    rid = insert_user_report(
        db_path,
        domain=body.domain,
        pattern_category=body.label,
        text_snippet=body.text,
        confirmed=body.confirmed,
    )
    return jsonify({"ok": True, "report_id": rid})


@bp.get("/api/stats")
def stats():
    """Global transparency database statistics."""
    db_path = current_app.config["DB_PATH"]
    s = aggregate_stats(db_path)
    meta_path = Path(current_app.config["ROOT"]) / "ml" / "models" / "saved" / "eval_results" / "summary.json"
    model_meta = {}
    if meta_path.exists():
        import json

        try:
            model_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            model_meta = {}
    return jsonify(
        {
            "total_sites": s["total_sites"],
            "total_patterns_detected": s["total_patterns_detected"],
            "most_common_pattern": s["most_common_pattern"],
            "worst_offender": s["worst_offender_domain"],
            "user_reports": s["total_user_reports"],
            "eval_macro_f1_merged": model_meta.get("macro_f1_merged_pred"),
            "evaluated_at": model_meta.get("evaluated_at"),
        }
    )


@bp.get("/api/health")
def health():
    return jsonify({"status": "ok"})
