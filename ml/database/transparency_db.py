"""
SQLite transparency database: sites, detections, and user reports.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE,
    vertical TEXT,
    total_patterns_found INTEGER,
    manipulation_score REAL,
    last_scraped TIMESTAMP,
    pages_analyzed INTEGER
);

CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    pattern_category TEXT,
    text_snippet TEXT,
    url TEXT,
    confidence REAL,
    detected_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_reports (
    id INTEGER PRIMARY KEY,
    domain TEXT,
    pattern_category TEXT,
    text_snippet TEXT,
    confirmed BOOLEAN,
    reported_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS score_history (
    id INTEGER PRIMARY KEY,
    domain TEXT,
    manipulation_score REAL,
    patterns_found INTEGER,
    snapshot_date TEXT,
    delta_from_prev REAL
);
"""


def init_db(db_path: str | Path) -> None:
    """Create tables if they do not exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _domain_id(conn: sqlite3.Connection, domain: str) -> Optional[int]:
    cur = conn.execute("SELECT id FROM sites WHERE domain = ?", (domain,))
    row = cur.fetchone()
    return int(row[0]) if row else None


def upsert_site(
    db_path: str | Path,
    domain: str,
    vertical: str,
    total_patterns: int,
    manipulation_score: float,
    pages_analyzed: int,
) -> int:
    """Insert or update a site row; return site id."""
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        sid = _domain_id(conn, domain)
        if sid is None:
            cur = conn.execute(
                """
                INSERT INTO sites (domain, vertical, total_patterns_found, manipulation_score, last_scraped, pages_analyzed)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (domain, vertical, total_patterns, manipulation_score, now, pages_analyzed),
            )
            conn.commit()
            return int(cur.lastrowid)
        conn.execute(
            """
            UPDATE sites SET vertical=?, total_patterns_found=?, manipulation_score=?, last_scraped=?, pages_analyzed=?
            WHERE id=?
            """,
            (vertical, total_patterns, manipulation_score, now, pages_analyzed, sid),
        )
        conn.commit()
        return sid
    finally:
        conn.close()


def replace_detections_for_site(
    db_path: str | Path,
    domain: str,
    detections: Iterable[Dict[str, Any]],
) -> None:
    """Replace all detections for ``domain`` with the provided list."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        sid = _domain_id(conn, domain)
        if sid is None:
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                """
                INSERT INTO sites (domain, vertical, total_patterns_found, manipulation_score, last_scraped, pages_analyzed)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (domain, "unknown", 0, 0.0, now, 0),
            )
            conn.commit()
            sid = int(cur.lastrowid)
        conn.execute("DELETE FROM detections WHERE site_id = ?", (sid,))
        now = datetime.now(timezone.utc).isoformat()
        for d in detections:
            conn.execute(
                """
                INSERT INTO detections (site_id, pattern_category, text_snippet, url, confidence, detected_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    d["pattern_category"],
                    d.get("text_snippet", "")[:2000],
                    d.get("url", ""),
                    float(d.get("confidence", 0.0)),
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def insert_user_report(
    db_path: str | Path,
    domain: str,
    pattern_category: str,
    text_snippet: str,
    confirmed: bool,
) -> int:
    """Store a user-submitted report; return row id."""
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO user_reports (domain, pattern_category, text_snippet, confirmed, reported_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (domain, pattern_category, text_snippet[:2000], bool(confirmed), now),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def fetch_all_sites(db_path: str | Path) -> List[Dict[str, Any]]:
    """Return all site rows as dicts."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT * FROM sites ORDER BY manipulation_score DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def fetch_detections_for_domain(db_path: str | Path, domain: str) -> List[Dict[str, Any]]:
    """Return detections joined for a domain."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT d.* FROM detections d
            JOIN sites s ON s.id = d.site_id
            WHERE s.domain = ?
            ORDER BY d.detected_at DESC
            """,
            (domain,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def fetch_leaderboard(
    db_path: str | Path,
    vertical: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Sites ranked by manipulation score with top pattern category."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        q = """
        SELECT s.domain, s.vertical, s.manipulation_score, s.pages_analyzed,
               (SELECT pattern_category FROM detections d
                WHERE d.site_id = s.id
                GROUP BY pattern_category
                ORDER BY COUNT(*) DESC LIMIT 1) AS top_pattern
        FROM sites s
        """
        args: List[Any] = []
        if vertical and vertical != "all":
            q += " WHERE s.vertical = ?"
            args.append(vertical)
        q += " ORDER BY s.manipulation_score DESC LIMIT ?"
        args.append(limit)
        cur = conn.execute(q, args)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def insert_score_snapshot(
    db_path: str | Path,
    domain: str,
    manipulation_score: float,
    patterns_found: int,
    snapshot_date: str,
    delta_from_prev: float,
) -> None:
    """Append a weekly (or manual) manipulation score snapshot."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO score_history (domain, manipulation_score, patterns_found, snapshot_date, delta_from_prev)
            VALUES (?, ?, ?, ?, ?)
            """,
            (domain, float(manipulation_score), int(patterns_found), snapshot_date, float(delta_from_prev)),
        )
        conn.commit()
    finally:
        conn.close()


def get_score_history(db_path: str | Path, domain: str) -> List[Dict[str, Any]]:
    """Return time-series rows for a domain, oldest first."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT domain, manipulation_score, patterns_found, snapshot_date, delta_from_prev
            FROM score_history WHERE domain = ? ORDER BY snapshot_date ASC
            """,
            (domain,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def list_tracked_domains(db_path: str | Path) -> List[str]:
    """Domains present in the sites table."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT domain FROM sites")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def aggregate_stats(db_path: str | Path) -> Dict[str, Any]:
    """Dashboard/API aggregate statistics."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        total_sites = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        total_dets = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        total_reports = conn.execute("SELECT COUNT(*) FROM user_reports").fetchone()[0]
        top_pat = conn.execute(
            """
            SELECT pattern_category, COUNT(*) c FROM detections
            GROUP BY pattern_category ORDER BY c DESC LIMIT 1
            """
        ).fetchone()
        worst = conn.execute(
            "SELECT domain, manipulation_score FROM sites ORDER BY manipulation_score DESC LIMIT 1"
        ).fetchone()
        return {
            "total_sites": int(total_sites),
            "total_patterns_detected": int(total_dets),
            "total_user_reports": int(total_reports),
            "most_common_pattern": top_pat[0] if top_pat else None,
            "worst_offender_domain": worst[0] if worst else None,
            "worst_offender_score": float(worst[1]) if worst else 0.0,
        }
    finally:
        conn.close()
