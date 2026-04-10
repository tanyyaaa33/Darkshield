"""
Text augmentation for minority dark-pattern classes using NLTK WordNet + heuristics.
"""

from __future__ import annotations

import random
import re
from typing import List

import nltk
from nltk.corpus import wordnet as wn

_BRANDS = [
    "Amazon.in",
    "Flipkart",
    "Myntra",
    "Nykaa",
    "BigBasket",
    "Zomato",
    "Swiggy",
    "MakeMyTrip",
    "Cleartrip",
    "IRCTC",
]

_HINGLISH_FRAGS = [
    "Sirf aaj!",
    "Jaldi karo!",
    "Abhi order karo",
    "India mein trusted",
    "Cash on delivery available",
]


def ensure_nltk_wordnet() -> None:
    """Download WordNet data if missing."""
    try:
        wn.synsets("test")
    except LookupError:
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)


def _synonym_replace(text: str, rng: random.Random, prob: float = 0.35) -> str:
    """Replace a few content words with WordNet synonyms."""
    ensure_nltk_wordnet()
    tokens = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
    out: List[str] = []
    for tok in tokens:
        if not tok.isalpha() or rng.random() > prob:
            out.append(tok)
            continue
        syns = wn.synsets(tok.lower())
        if not syns:
            out.append(tok)
            continue
        lemmas = [l.name().replace("_", " ") for l in syns[0].lemmas() if l.name().lower() != tok.lower()]
        if not lemmas:
            out.append(tok)
            continue
        rep = rng.choice(lemmas)
        out.append(rep.capitalize() if tok[:1].isupper() else rep)
    return re.sub(r"\s+([.,!?])", r"\1", " ".join(out))


def _random_delete(text: str, rng: random.Random, rate: float = 0.05) -> str:
    words = text.split()
    if len(words) < 4:
        return text
    kept = [w for w in words if rng.random() > rate]
    return " ".join(kept) if len(kept) >= 3 else text


def _random_insert(text: str, rng: random.Random, rate: float = 0.05) -> str:
    words = text.split()
    extras = ["₹", "only", "today", "India", "online", "order", "fast", "delivery"]
    for _ in range(max(1, int(len(words) * rate))):
        idx = rng.randint(0, len(words))
        words.insert(idx, rng.choice(extras))
    return " ".join(words)


def _swap_numbers(text: str, rng: random.Random) -> str:
    def repl(m: re.Match) -> str:
        n = int(m.group(0).replace(",", ""))
        delta = rng.randint(-3, 3)
        return str(max(0, n + delta))

    return re.sub(r"\d[\d,]*", repl, text)


def _swap_brands(text: str, rng: random.Random) -> str:
    t = text
    for b in _BRANDS:
        if b in t and rng.random() < 0.5:
            t = t.replace(b, rng.choice([x for x in _BRANDS if x != b]), 1)
    return t


def augment_text(text: str, rng: random.Random | None = None) -> str:
    """Apply a random subset of augmentation transforms."""
    rng = rng or random.Random()
    t = text
    if rng.random() < 0.6:
        t = _synonym_replace(t, rng, prob=0.25)
    if rng.random() < 0.5:
        t = _random_delete(t, rng, rate=0.05)
    if rng.random() < 0.5:
        t = _random_insert(t, rng, rate=0.05)
    if rng.random() < 0.4:
        t = _swap_numbers(t, rng)
    if rng.random() < 0.5:
        t = _swap_brands(t, rng)
    if rng.random() < 0.25:
        t = f"{rng.choice(_HINGLISH_FRAGS)} {t}"
    return t.strip()


def augment_text_neutral(text: str, rng: random.Random | None = None) -> str:
    """Augment likely-neutral lines without injecting urgency/opt-out n-grams."""
    rng = rng or random.Random()
    t = text
    if rng.random() < 0.7:
        t = _synonym_replace(t, rng, prob=0.2)
    if rng.random() < 0.5:
        t = _random_delete(t, rng, rate=0.04)
    if rng.random() < 0.45:
        t = _swap_numbers(t, rng)
    if rng.random() < 0.55:
        t = _swap_brands(t, rng)
    return t.strip()


def augment_rows(rows: List[dict], label: str, target_count: int, seed: int = 42) -> List[dict]:
    """
    Duplicate and augment rows for a single label until ``target_count`` rows exist.

    Each new row preserves site/vertical/source metadata from a random donor row.
    """
    rng = random.Random(seed)
    pool = [r for r in rows if r["label"] == label]
    if not pool:
        return rows
    out = list(rows)
    while sum(1 for r in out if r["label"] == label) < target_count:
        base = rng.choice(pool)
        new_text = augment_text_neutral(base["text"], rng) if label == "none" else augment_text(base["text"], rng)
        if not new_text or new_text == base["text"]:
            new_text = base["text"] + f" ({rng.randint(1000,9999)})"
        out.append(
            {
                "text": new_text,
                "label": label,
                "site": base["site"],
                "vertical": base["vertical"],
                "source": "augmented",
            }
        )
    return out


def balance_min_per_class(rows: List[dict], min_per_class: int = 150, seed: int = 42) -> List[dict]:
    """Ensure each label has at least ``min_per_class`` samples via augmentation."""
    labels = sorted({r["label"] for r in rows})
    out = list(rows)
    for lab in labels:
        out = augment_rows(out, lab, min_per_class, seed=seed + hash(lab) % 997)
    return out
