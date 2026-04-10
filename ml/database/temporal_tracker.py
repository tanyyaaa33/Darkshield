"""
Weekly score snapshots for tracked domains (cron-friendly).

Run as a scheduled job: ``python -m ml.database.temporal_tracker``.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import schedule
    import time
except ImportError:  # pragma: no cover
    schedule = None
    time = None

from ml.database.transparency_db import get_score_history, init_db, insert_score_snapshot, list_tracked_domains

DB_PATH = _ROOT / "data" / "darkshield.db"


def _latest_snapshot(db_path: Path, domain: str):
    hist = get_score_history(db_path, domain)
    return hist[-1] if hist else None


def weekly_rescrape(db_path: Path | None = None) -> None:
    """
    Record current site scores as snapshots and log large week-over-week deltas.

    Full HTML re-scraping is environment-specific; this pass snapshots DB truth.
    """
    db_path = Path(db_path or DB_PATH)
    init_db(db_path)
    today = date.today().isoformat()
    for domain in list_tracked_domains(db_path):
        conn = __import__("sqlite3").connect(db_path)
        conn.row_factory = __import__("sqlite3").Row
        try:
            row = conn.execute("SELECT * FROM sites WHERE domain = ?", (domain,)).fetchone()
        finally:
            conn.close()
        if not row:
            continue
        score = float(row["manipulation_score"])
        patterns = int(row["total_patterns_found"] or 0)
        prev = _latest_snapshot(db_path, domain)
        prev_score = float(prev["manipulation_score"]) if prev else score
        delta = score - prev_score
        insert_score_snapshot(db_path, domain, score, patterns, today, delta)
        if prev and abs(delta) > 5.0:
            print(f"ALERT: {domain} manipulation score changed by {delta:+.1f} (now {score:.1f})")


def save_weekly_snapshot_job() -> None:
    weekly_rescrape(DB_PATH)


def run_scheduler_loop() -> None:
    """Blocking loop for machines that keep a long-running process."""
    if schedule is None:
        raise RuntimeError("Install `schedule` to use the scheduler loop.")
    schedule.every().monday.at("02:00").do(save_weekly_snapshot_job)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    weekly_rescrape(DB_PATH)
