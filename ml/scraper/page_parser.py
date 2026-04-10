"""
Extract visible text, buttons, timers, and price hints from HTML for DarkShield.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class ParsedPage:
    """Structured extraction from a single HTML document."""

    url: str
    site: str
    vertical: str
    text_chunks: List[str] = field(default_factory=list)
    button_texts: List[str] = field(default_factory=list)
    timer_snippets: List[str] = field(default_factory=list)
    price_snippets: List[str] = field(default_factory=list)


_SKIP_PARENT_TAGS = frozenset({"script", "style", "noscript", "template", "svg"})


def _visible_text_from_node(node: Tag) -> str:
    parts: List[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            t = str(child).strip()
            if t:
                parts.append(t)
        elif isinstance(child, Tag):
            if child.name in _SKIP_PARENT_TAGS:
                continue
            if child.name in ("br",):
                parts.append(" ")
                continue
            parts.append(_visible_text_from_node(child))
    return " ".join(p for p in parts if p).strip()


def extract_text_chunks(html: str, min_len: int = 10) -> List[str]:
    """Return deduplicated visible text segments longer than ``min_len`` characters."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_SKIP_PARENT_TAGS):
        tag.decompose()

    chunks: List[str] = []
    seen = set()
    for el in soup.find_all(string=True):
        if not isinstance(el, NavigableString):
            continue
        parent = el.parent
        if not isinstance(parent, Tag):
            continue
        if parent.name in _SKIP_PARENT_TAGS:
            continue
        raw = str(el).strip()
        if len(raw) < min_len:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        chunks.append(raw)
    return chunks


def extract_button_texts(html: str) -> List[str]:
    """Collect text from button-like elements."""
    soup = BeautifulSoup(html, "html.parser")
    texts: List[str] = []
    for sel in ["button", 'input[type="submit"]', 'input[type="button"]', "a.btn", "a.button"]:
        for el in soup.select(sel):
            if el.name == "input":
                t = el.get("value") or ""
            else:
                t = el.get_text(" ", strip=True)
            t = (t or "").strip()
            if len(t) >= 3:
                texts.append(t)
    return list(dict.fromkeys(texts))


_TIMER_RE = re.compile(
    r"\b\d{1,2}:\d{2}:\d{2}\b|\bends in\b|\boffer ends\b|\bonly \d+ left\b",
    re.I,
)


def extract_timer_snippets(chunks: List[str]) -> List[str]:
    """Filter chunks that look like countdown / urgency lines."""
    out: List[str] = []
    for c in chunks:
        if _TIMER_RE.search(c):
            out.append(c)
    return out[:50]


_PRICE_RE = re.compile(r"₹\s*[\d,]+(?:\.\d{2})?|INR\s*[\d,]+|Rs\.?\s*[\d,]+", re.I)


def extract_price_snippets(chunks: List[str]) -> List[str]:
    """Return lines containing rupee-style prices."""
    out: List[str] = []
    for c in chunks:
        if _PRICE_RE.search(c):
            out.append(c)
    return out[:80]


def parse_html_page(html: str, url: str, site: str, vertical: str) -> ParsedPage:
    """
    Parse raw HTML into :class:`ParsedPage`.

    :param site: Short domain key, e.g. ``amazon.in``.
    :param vertical: One of travel/fmcg/fashion/electronics/food_delivery.
    """
    chunks = extract_text_chunks(html)
    buttons = extract_button_texts(html)
    timers = extract_timer_snippets(chunks)
    prices = extract_price_snippets(chunks)
    return ParsedPage(
        url=url,
        site=site,
        vertical=vertical,
        text_chunks=chunks,
        button_texts=buttons,
        timer_snippets=timers,
        price_snippets=prices,
    )


def parsed_page_to_records(parsed: ParsedPage) -> List[dict]:
    """Flatten a parsed page into row dicts suitable for dataset building."""
    rows: List[dict] = []
    base = {"url": parsed.url, "site": parsed.site, "vertical": parsed.vertical, "source": "scraped"}

    for t in parsed.text_chunks:
        rows.append({**base, "text": t, "kind": "text"})
    for t in parsed.button_texts:
        rows.append({**base, "text": t, "kind": "button"})
    for t in parsed.timer_snippets:
        rows.append({**base, "text": t, "kind": "timer"})
    for t in parsed.price_snippets:
        rows.append({**base, "text": t, "kind": "price"})
    return rows
