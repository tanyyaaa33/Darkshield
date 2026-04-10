"""
Map DarkShield pattern labels to illustrative regulatory / policy references.

This is an educational layer — not legal advice. Citations are abbreviated summaries.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, DefaultDict, Dict, List

REGULATORY_MAPPING: Dict[str, Dict[str, Any]] = {
    "fake_urgency": {
        "CCPA_2023": "CPRA / CCPA regulations — deceptive urgency and dark patterns (CPRA rulemaking themes)",
        "EU_Dark_Patterns": "EU Digital Services Act / consumer fairness — misleading urgency and countdowns",
        "FTC_Act": "FTC Act Section 5 — unfair or deceptive acts or practices",
        "India_IT_Rules_2021": "IT Rules, 2021 — intermediary due diligence; misleading commercial practices risk",
        "severity": "HIGH",
        "enforcement_cases": [
            "FTC enforcement themes on deceptive countdowns and stock claims (consumer protection settlements)",
        ],
    },
    "confirm_shaming": {
        "CCPA_2023": "CPRA dark pattern themes — manipulative consent / opt-out language",
        "EU_Dark_Patterns": "GDPR Art. 5(1)(a) fairness & transparency; EU dark-pattern guidance on consent",
        "FTC_Act": "FTC Act Section 5 — manipulative framing of choices",
        "India_IT_Rules_2021": "Rule 3(1)(b) — users shall not host misleading information (platform diligence context)",
        "severity": "HIGH",
        "enforcement_cases": [
            "CNIL / EU DPA actions on manipulative cookie/consent interfaces (themes)",
        ],
    },
    "hidden_costs": {
        "CCPA_2023": "Consumer transparency expectations under CPRA rulemaking themes",
        "EU_Dark_Patterns": "EU consumer law — unfair commercial practices (misleading price indications)",
        "FTC_Act": "FTC Act — failure to disclose material terms (fees, totals)",
        "India_IT_Rules_2021": "Consumer Protection Act 2019 alignment — misleading advertisements / unfair trade practices",
        "severity": "HIGH",
        "enforcement_cases": ["FTC cases on drip-priced fees and inadequate disclosure"],
    },
    "visual_interference": {
        "CCPA_2023": "CPRA dark pattern taxonomy — interface interference",
        "EU_Dark_Patterns": "EU fairness principles for online choice architecture",
        "FTC_Act": "FTC Act — interface design that obscures material information",
        "India_IT_Rules_2021": "Intermediary diligence — deceptive UI risk",
        "severity": "MEDIUM",
        "enforcement_cases": ["Regulator guidance on hard-to-find controls (themes)"],
    },
    "sneaking": {
        "CCPA_2023": "CPRA themes — sneaking / hidden charges in flows",
        "EU_Dark_Patterns": "Unfair commercial practices — unsolicited charges",
        "FTC_Act": "FTC Act — billing surprises and undisclosed add-ons",
        "India_IT_Rules_2021": "E-commerce consumer transparency norms (general alignment)",
        "severity": "HIGH",
        "enforcement_cases": ["FTC negative option / add-on enforcement themes"],
    },
    "forced_continuity": {
        "CCPA_2023": "Auto-renewal transparency themes under state consumer laws",
        "EU_Dark_Patterns": "EU consumer rights on subscriptions and cancellation clarity",
        "FTC_Act": "FTC ROSCA / subscription enforcement themes",
        "India_IT_Rules_2021": "Consumer protection — unfair contract terms risk",
        "severity": "HIGH",
        "enforcement_cases": ["FTC subscription cancellation enforcement (themes)"],
    },
    "misdirection": {
        "CCPA_2023": "Dark pattern taxonomy — misdirection",
        "EU_Dark_Patterns": "GDPR fairness — obscuring data choices",
        "FTC_Act": "FTC Act — burying material terms or choices",
        "India_IT_Rules_2021": "Intermediary diligence on deceptive design risk",
        "severity": "MEDIUM",
        "enforcement_cases": ["Global DPA guidance on deceptive cookie banners (themes)"],
    },
    "social_proof_manipulation": {
        "CCPA_2023": "Deceptive commercial messaging themes",
        "EU_Dark_Patterns": "Unfair commercial practices — misleading endorsements",
        "FTC_Act": "FTC Act — fake reviews / misleading social proof",
        "India_IT_Rules_2021": "Advertising Standards Council / CPA alignment (themes)",
        "severity": "MEDIUM",
        "enforcement_cases": ["FTC fake review enforcement (themes)"],
    },
    "bait_and_switch": {
        "CCPA_2023": "False or misleading advertising themes",
        "EU_Dark_Patterns": "EU UCP Directive — misleading actions / omissions",
        "FTC_Act": "FTC Act — bait-and-switch advertising",
        "India_IT_Rules_2021": "Consumer Protection Act — misleading advertisements",
        "severity": "HIGH",
        "enforcement_cases": ["FTC pricing and availability deception cases (themes)"],
    },
    "roach_motel": {
        "CCPA_2023": "Dark pattern taxonomy — obstruction / difficult exit",
        "EU_Dark_Patterns": "EU consumer law — unfair obstruction of cancellation",
        "FTC_Act": "FTC Act — unreasonable barriers to cancel",
        "India_IT_Rules_2021": "Consumer rights — unfair trade practice risk",
        "severity": "HIGH",
        "enforcement_cases": ["FTC cancellation friction enforcement (themes)"],
    },
    "none": {
        "severity": "NONE",
        "enforcement_cases": [],
    },
}


def get_compliance_tags(pattern_label: str) -> Dict[str, Any]:
    """Return regulatory context for a detected pattern."""
    return dict(REGULATORY_MAPPING.get(pattern_label, {"severity": "UNKNOWN", "enforcement_cases": []}))


def generate_compliance_report(detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate detections into a per-regulation summary."""
    violations: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0, "UNKNOWN": 0}
    best_pattern: str | None = None
    best_rank = -1
    for d in detections:
        lab = str(d.get("label", "none"))
        tags = get_compliance_tags(lab)
        if lab != "none":
            sc = rank.get(str(tags.get("severity", "NONE")), 0)
            if sc > best_rank:
                best_rank = sc
                best_pattern = lab
        for reg, article in tags.items():
            if reg in ("severity", "enforcement_cases"):
                continue
            violations[reg].append(
                {
                    "pattern": lab,
                    "article": article,
                    "text": (d.get("text") or "")[:500],
                    "confidence": float(d.get("confidence", 0.0)),
                }
            )
    return {
        "violations_by_regulation": dict(violations),
        "highest_severity_pattern": best_pattern or "none",
        "recommended_action": "Review highlighted UI copy and consent/cancellation flows; consult counsel for production compliance.",
    }
