"""Lightweight request/response validation for the Flask API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ClassifyRequest:
    """POST /api/classify body."""

    texts: List[str]
    url: str = ""
    include_compliance: bool = False

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "ClassifyRequest":
        if not isinstance(data, dict) or "texts" not in data:
            raise ValueError("Missing texts array")
        texts = data.get("texts") or []
        if not isinstance(texts, list):
            raise ValueError("texts must be a list")
        return ClassifyRequest(
            texts=[str(t) for t in texts],
            url=str(data.get("url", "")),
            include_compliance=bool(data.get("include_compliance", False)),
        )


@dataclass
class ReportRequest:
    """POST /api/report body."""

    domain: str
    text: str
    label: str
    confirmed: bool

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "ReportRequest":
        for k in ("domain", "text", "label", "confirmed"):
            if k not in data:
                raise ValueError(f"Missing {k}")
        return ReportRequest(
            domain=str(data["domain"]),
            text=str(data["text"]),
            label=str(data["label"]),
            confirmed=bool(data["confirmed"]),
        )


@dataclass
class ClassifyResult:
    """Single classification output."""

    text: str
    label: str
    confidence: float
    explanation: str


@dataclass
class SiteScoreResponse:
    """GET /api/site-score response."""

    domain: str
    manipulation_score: float
    pattern_breakdown: Dict[str, int]
    rank: int
    vertical: str


@dataclass
class LeaderboardRow:
    domain: str
    score: float
    top_pattern: Optional[str]
    pages_analyzed: int


@dataclass
class StatsResponse:
    total_sites: int
    total_patterns_detected: int
    most_common_pattern: Optional[str]
    worst_offender: Optional[str]
    user_reports: int
