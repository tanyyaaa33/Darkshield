"""
Versioned public JSON API (rate-limited).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request

from ml.compliance.regulatory_mapper import get_compliance_tags

pub = Blueprint("public_api", __name__, url_prefix="")


def _db() -> str:
    return current_app.config["DB_PATH"]


def _risk_level(score: float) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


@pub.get("/api/v1/score")
def v1_score():
    domain = request.args.get("domain", "").strip().lower()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    conn = sqlite3.connect(_db())
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM sites WHERE domain = ?", (domain,)).fetchone()
        if not row:
            return jsonify(
                {
                    "domain": domain,
                    "manipulation_score": 0.0,
                    "risk_level": "LOW",
                    "top_patterns": [],
                    "pages_analyzed": 0,
                    "last_updated": None,
                    "compliance_flags": [],
                }
            )
        site = dict(row)
        cur = conn.execute(
            """
            SELECT pattern_category, COUNT(*) c FROM detections d
            JOIN sites s ON s.id = d.site_id WHERE s.domain = ?
            GROUP BY pattern_category ORDER BY c DESC LIMIT 5
            """,
            (domain,),
        )
        tops = [r[0] for r in cur.fetchall()]
        flags: List[str] = []
        for p in tops:
            tags = get_compliance_tags(p)
            for k in ("CCPA_2023", "EU_Dark_Patterns", "FTC_Act"):
                if k in tags:
                    flags.append(k)
        return jsonify(
            {
                "domain": domain,
                "manipulation_score": float(site["manipulation_score"]),
                "risk_level": _risk_level(float(site["manipulation_score"])),
                "top_patterns": tops,
                "pages_analyzed": int(site["pages_analyzed"] or 0),
                "last_updated": site.get("last_scraped"),
                "compliance_flags": sorted(set(flags)),
            }
        )
    finally:
        conn.close()


@pub.get("/api/v1/leaderboard")
def v1_leaderboard():
    vertical = request.args.get("vertical")
    limit = int(request.args.get("limit", 10))
    conn = sqlite3.connect(_db())
    conn.row_factory = sqlite3.Row
    try:
        q = "SELECT domain, manipulation_score, pages_analyzed, vertical FROM sites"
        args: List[Any] = []
        if vertical and vertical != "all":
            q += " WHERE vertical = ?"
            args.append(vertical)
        q += " ORDER BY manipulation_score DESC LIMIT ?"
        args.append(limit)
        rows = [dict(r) for r in conn.execute(q, args).fetchall()]
        return jsonify(rows)
    finally:
        conn.close()


@pub.get("/api/v1/categories")
def v1_categories():
    cats = [
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
    return jsonify({"categories": cats})


@pub.get("/api/v1/stats")
def v1_stats():
    conn = sqlite3.connect(_db())
    try:
        ns = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        nd = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        top = conn.execute(
            "SELECT pattern_category, COUNT(*) c FROM detections GROUP BY pattern_category ORDER BY c DESC LIMIT 1"
        ).fetchone()
        return jsonify(
            {
                "sites": int(ns),
                "patterns_detected": int(nd),
                "top_pattern": top[0] if top else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    finally:
        conn.close()
