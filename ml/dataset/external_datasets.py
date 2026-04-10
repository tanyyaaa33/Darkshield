"""
External / public corpus integration for DarkShield.

Princeton Web Transparency "Dark Patterns at Scale" (DAPD) shopping taxonomy:
https://webtransparency.cs.princeton.edu/dark-patterns/
Mathur et al., "Dark Patterns at Scale", 2019 — synthetic samples below are inspired
by their published category definitions when bulk CSV download is unavailable.

FTC: examples paraphrased from themes in FTC, "Bringing Dark Patterns to Light", 2022
(report on manipulative design) — retailer names anonymized.

CNIL / EU: paraphrases aligned with EU dark-pattern guidance (consent, subscriptions).
"""

from __future__ import annotations

import random
from typing import Any, Dict, List

# Map Princeton-style DAPD shopping labels → DarkShield 10-class schema (+ none).
PRINCETON_MAPPING: Dict[str, str] = {
    "Countdown Timer": "fake_urgency",
    "Limited-time Message": "fake_urgency",
    "High-demand Message": "fake_urgency",
    "Low-stock Message": "fake_urgency",
    "Confirm Shaming": "confirm_shaming",
    "Trick Question": "misdirection",
    "Sneak into Basket": "sneaking",
    "Hidden Costs": "hidden_costs",
    "Hidden Subscription": "forced_continuity",
    "Difficult to Cancel": "roach_motel",
    "Forced Enrollment": "forced_continuity",
    "Activity Notifications": "social_proof_manipulation",
    "Testimonials of Uncertain Origin": "social_proof_manipulation",
    "Misdirection": "misdirection",
    "Price Comparison Prevention": "bait_and_switch",
    "Bait and Switch": "bait_and_switch",
    "Visual Interference": "visual_interference",
    "Preselection": "sneaking",
    "Disguised Ad": "visual_interference",
    "Friend Spam": "social_proof_manipulation",
    "Forced Continuity": "forced_continuity",
}


def _princeton_synthetic_block(rng: random.Random, n: int = 500) -> List[Dict[str, Any]]:
    """Generate ``n`` synthetic lines inspired by DAPD shopping dark-pattern classes."""
    sites = [
        ("shop.example", "electronics"),
        ("deals.example", "fashion"),
        ("travel.example", "travel"),
        ("grocery.example", "fmcg"),
    ]
    templates: List[tuple] = []
    for p_label, ds_label in PRINCETON_MAPPING.items():
        templates.append(
            (
                ds_label,
                p_label,
                [
                    f"{p_label} style: only {rng.randint(2,9)} seats left at this fare — complete booking now.",
                    f"{p_label} style: No thanks, I want to pay full price — decline savings.",
                    f"{p_label} style: Your cart will expire in 0{rng.randint(1,9)}:{rng.randint(10,59)} minutes.",
                    f"{p_label} style: A protection plan was included — remove in cart if not needed.",
                    f"{p_label} style: Continue without reading 20 pages of terms (link in 6pt grey).",
                ],
            )
        )
    rows: List[Dict[str, Any]] = []
    while len(rows) < n:
        ds_label, p_label, opts = templates[rng.randint(0, len(templates) - 1)]
        site, vert = sites[rng.randint(0, len(sites) - 1)]
        text = opts[rng.randint(0, len(opts) - 1)] + f" ref#{len(rows)}"
        rows.append(
            {
                "text": text,
                "label": ds_label,
                "site": site,
                "vertical": vert,
                "source": "princeton",
            }
        )
    return rows


def _ftc_examples() -> List[Dict[str, Any]]:
    """~150 anonymized enforcement-style vignettes (themes from FTC 2022 dark pattern report)."""
    out: List[Dict[str, Any]] = []
    themes = [
        ("fake_urgency", "A major retailer showed a perpetual countdown that reset for each user session."),
        ("confirm_shaming", "A subscription service used guilt language on the decline button for a free trial."),
        ("hidden_costs", "A marketplace disclosed mandatory service fees only after the payment step."),
        ("forced_continuity", "A streaming offer converted to paid without a clear renewal date in the flow."),
        ("misdirection", "The unsubscribe path required navigating multiple nested menus with similar labels."),
        ("sneaking", "A warranty add-on was pre-checked during checkout for electronics."),
        ("social_proof_manipulation", "A seller displayed unverifiable 'thousands bought today' messaging."),
        ("bait_and_switch", "An advertised package price did not match the checkout total for the same SKU."),
        ("roach_motel", "Cancellation required a phone call during narrow hours despite online signup."),
        ("visual_interference", "The 'skip' control used low contrast and was placed far from the primary CTA."),
    ]
    retailers = [
        ("retailer-alpha.example", "electronics"),
        ("retailer-beta.example", "fmcg"),
        ("retailer-gamma.example", "travel"),
        ("retailer-delta.example", "food_delivery"),
    ]
    for i in range(150):
        lab, blurb = themes[i % len(themes)]
        site, vert = retailers[i % len(retailers)]
        out.append(
            {
                "text": f"{blurb} Case excerpt {i+1} (anonymized retailer).",
                "label": lab,
                "site": site,
                "vertical": vert,
                "source": "ftc",
            }
        )
    return out


def _cnil_examples() -> List[Dict[str, Any]]:
    """100 guideline-style examples (confirm shaming, roach motel, forced continuity focus)."""
    out: List[Dict[str, Any]] = []
    bodies = [
        (
            "confirm_shaming",
            "Decline personalized experience — I accept worse recommendations (EU-style consent framing).",
        ),
        (
            "roach_motel",
            "To close your account, print and post a signed form — online signup was instant (guideline-style).",
        ),
        (
            "forced_continuity",
            "After 7 days your plan renews yearly — the price appears only in a collapsed FAQ panel.",
        ),
        (
            "confirm_shaming",
            "No thanks, I reject better pricing — continue with standard rates (manipulative opt-out).",
        ),
        (
            "roach_motel",
            "Premium support renews monthly unless you call a premium-rate line during business hours.",
        ),
    ]
    sites = [("eu-shop.example", "fashion"), ("privacy-demo.example", "electronics")]
    for i in range(100):
        lab, txt = bodies[i % len(bodies)]
        site, vert = sites[i % len(sites)]
        out.append(
            {
                "text": f"{txt} [CNIL-inspired {i+1}]",
                "label": lab,
                "site": site,
                "vertical": vert,
                "source": "cnil",
            }
        )
    return out


def get_princeton_inspired_samples(seed: int = 42, n: int = 500) -> List[Dict[str, Any]]:
    # Inspired by: Mathur et al., "Dark Patterns at Scale", CSCW 2019
    rng = random.Random(seed)
    rows = _princeton_synthetic_block(rng, n=n)
    sites_in = [
        ("flipkart.example", "electronics"),
        ("amazon.in.example", "electronics"),
        ("nykaa.example", "fashion"),
        ("makemytrip.example", "travel"),
        ("bigbasket.example", "fmcg"),
    ]
    for i, r in enumerate(rows):
        r["source"] = "princeton_inspired"
        site, vert = sites_in[i % len(sites_in)]
        r["site"], r["vertical"] = site, vert
        if "₹" not in r["text"]:
            r["text"] = f"{r['text']} — Flipkart/Amazon.in style checkout, sirf aaj ₹{rng.randint(99, 999)} se."
    return rows


def get_ftc_examples() -> List[Dict[str, Any]]:
    # Source: FTC Report "Bringing Dark Patterns to Light", Sept 2022
    out: List[Dict[str, Any]] = []
    themes = [
        (
            "hidden_costs",
            "Platform fee and GST surfaced only on the final pay step; MRP shown excluded mandatory surcharges.",
        ),
        (
            "forced_continuity",
            "Free trial converted to annual billing without a clear renewal date in the primary consent copy.",
        ),
        (
            "roach_motel",
            "Cancellation required calling support during narrow hours though signup was fully online.",
        ),
    ]
    retailers = [
        ("retailer-alpha.example", "electronics"),
        ("retailer-beta.example", "fmcg"),
        ("retailer-gamma.example", "travel"),
    ]
    for i in range(150):
        lab, blurb = themes[i % len(themes)]
        site, vert = retailers[i % len(retailers)]
        out.append(
            {
                "text": f"{blurb} FTC-style vignette {i + 1} (anonymized).",
                "label": lab,
                "site": site,
                "vertical": vert,
                "source": "ftc",
                "confidence": 0.95,
            }
        )
    return out


def get_cnil_examples() -> List[Dict[str, Any]]:
    # Source: CNIL Recommendation on Dark Patterns, 2022
    return _cnil_examples()


def load_external_rows(princeton_n: int = 500, seed: int = 42) -> List[Dict[str, Any]]:
    """Backward-compatible merge of the three public corpora."""
    return get_princeton_inspired_samples(seed=seed, n=princeton_n) + get_ftc_examples() + get_cnil_examples()
