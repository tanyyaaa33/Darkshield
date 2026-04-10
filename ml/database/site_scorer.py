"""
Per-domain manipulation scoring for the transparency database.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

# Category multipliers (spec: fake_urgency ×1.2, confirm_shaming ×1.5, hidden_costs ×1.3, others ×1.0)
PATTERN_WEIGHTS: Dict[str, float] = {
    "fake_urgency": 1.2,
    "confirm_shaming": 1.5,
    "hidden_costs": 1.3,
    "visual_interference": 1.0,
    "sneaking": 1.0,
    "forced_continuity": 1.0,
    "misdirection": 1.0,
    "social_proof_manipulation": 1.0,
    "bait_and_switch": 1.0,
    "roach_motel": 1.0,
    "none": 0.0,
}


def compute_manipulation_score(
    patterns_found: int,
    total_text_nodes_analyzed: int,
    pattern_categories: Iterable[str],
) -> float:
    """
    Compute a 0–100 manipulation score for a domain.

    Base ratio: patterns_found / max(total_text_nodes_analyzed, 1) * 100,
    multiplied by per-pattern weights, capped at 100.
    """
    denom = max(int(total_text_nodes_analyzed), 1)
    ratio = float(patterns_found) / float(denom)
    base = ratio * 100.0
    cats: List[str] = [c for c in pattern_categories if c and c != "none"]
    if patterns_found <= 0:
        return 0.0
    if not cats:
        return float(min(100.0, round(base, 2)))
    mean_w = sum(PATTERN_WEIGHTS.get(c, 1.0) for c in cats) / len(cats)
    return float(min(100.0, round(base * mean_w, 2)))


def get_top_offenders(db_path: str, limit: int = 20) -> List[Tuple[str, float, str]]:
    """
    Return top domains by manipulation score.

    Each tuple is (domain, manipulation_score, vertical).
    """
    from ml.database.transparency_db import fetch_all_sites

    rows = fetch_all_sites(db_path)
    rows.sort(key=lambda r: r["manipulation_score"], reverse=True)
    out: List[Tuple[str, float, str]] = []
    for r in rows[:limit]:
        out.append((r["domain"], float(r["manipulation_score"]), r["vertical"]))
    return out


def get_vertical_comparison(db_path: str) -> List[Dict[str, float]]:
    """Average manipulation score per vertical."""
    from ml.database.transparency_db import fetch_all_sites

    rows = fetch_all_sites(db_path)
    buckets: Dict[str, List[float]] = {}
    for r in rows:
        buckets.setdefault(r["vertical"], []).append(float(r["manipulation_score"]))
    return [
        {"vertical": v, "avg_manipulation_score": round(sum(vals) / len(vals), 2)}
        for v, vals in sorted(buckets.items())
    ]
