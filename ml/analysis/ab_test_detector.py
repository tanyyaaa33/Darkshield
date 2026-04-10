"""
Heuristic A/B testing detector: compare pattern presence across synthetic sessions.

Uses lightweight HTTP fetches (no Selenium) to avoid mandatory browser deps in CI.
For Selenium-based deep checks, extend ``_fetch_with_ua`` to use the project scraper.
"""

from __future__ import annotations

import random
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import numpy as np
import requests

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.dataset.builder import auto_label_text

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

UA_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
UA_FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
UA_MOBILE_ANDROID = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/122.0.0.0 Mobile Safari/537.36"
UA_MOBILE_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"


def _normalize_domain_url(domain: str) -> str:
    d = domain.strip()
    if not d.startswith("http"):
        d = "https://" + d
    return d


def _fetch_with_ua(url: str, ua: str, timeout: float = 12.0) -> str:
    r = requests.get(
        url,
        headers={"User-Agent": ua, "Accept-Language": "en-IN,en;q=0.9"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.text


def _visible_text_chunks(html: str, min_len: int = 24) -> List[str]:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"<[^>]+>", " ", html)
    parts = [p.strip() for p in re.split(r"\s+", html) if p and len(p.strip()) >= min_len]
    return parts[:400]


def scrape_and_classify(domain: str, html: str) -> List[Dict[str, Any]]:
    """Rule-based pseudo-labels on fetched HTML chunks."""
    found: List[Dict[str, Any]] = []
    for chunk in _visible_text_chunks(html):
        lab = auto_label_text(chunk)
        if lab != "none":
            found.append({"label": lab, "text": chunk[:240]})
    return found


def detect_ab_testing(domain: str, n_sessions: int = 10) -> Dict[str, Any]:
    """
    Fetch the homepage ``n_sessions`` times with rotating user agents and compare labels.
    """
    url = _normalize_domain_url(domain)
    uas = [UA_CHROME, UA_FIREFOX, UA_MOBILE_ANDROID, UA_MOBILE_IOS]
    sessions: List[Dict[str, Any]] = []
    for i in range(n_sessions):
        ua = uas[i % len(uas)]
        err = None
        html = ""
        try:
            html = _fetch_with_ua(url, ua)
        except requests.RequestException as exc:
            err = str(exc)
        patterns = scrape_and_classify(domain, html) if html else []
        sessions.append(
            {
                "user_agent": ua,
                "patterns_found": patterns,
                "session_id": str(uuid.uuid4()),
                "error": err,
            }
        )

    pattern_variance: Dict[str, Any] = {}
    for cat in CATEGORIES:
        presence = []
        for s in sessions:
            hit = any(p.get("label") == cat for p in s["patterns_found"])
            presence.append(1.0 if hit else 0.0)
        var = float(np.var(presence)) if presence else 0.0
        if var > 0.1:
            pattern_variance[cat] = {
                "shown_in_pct": float(np.mean(presence) * 100.0),
                "variance": var,
                "likely_ab_tested": True,
            }

    host = urlparse(url).hostname or domain
    return {
        "domain": host,
        "ab_tested_patterns": pattern_variance,
        "conclusion": f"{host} shows inconsistent surface-level pattern signals across {n_sessions} fetches — "
        f"{len(pattern_variance)} category/categories cross the variance heuristic.",
        "sessions": sessions,
    }


if __name__ == "__main__":
    import json

    d = sys.argv[1] if len(sys.argv) > 1 else "amazon.in"
    print(json.dumps(detect_ab_testing(d), indent=2)[:4000])
