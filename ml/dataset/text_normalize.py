"""
Text normalization for adversarial robustness (Unicode NFKC + common leet reversal).

Used when building training data and when evaluating obfuscated inputs.
Referenced from dataset builder and adversarial testing (mitigation path).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict

_LEET_MAP: Dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
}


def normalize_text(text: str) -> str:
    """
    Apply NFKC normalization and light leet-speak reversal for Latin tokens.

    Does not remove zero-width characters (handled separately in tests);
    call ``strip_control_and_zwsp`` when stripping invisible chars is desired.
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    out = []
    for ch in t:
        out.append(_LEET_MAP.get(ch, ch))
    t2 = "".join(out)
    t2 = re.sub(r"\s+", " ", t2).strip()
    return t2


def strip_control_and_zwsp(text: str) -> str:
    """Remove zero-width spaces and most format characters after NFKC."""
    t = normalize_text(text)
    cleaned = []
    for ch in t:
        cat = unicodedata.category(ch)
        if cat == "Cf" and ch in ("\u200b", "\u200c", "\u200d", "\ufeff"):
            continue
        cleaned.append(ch)
    return "".join(cleaned)
