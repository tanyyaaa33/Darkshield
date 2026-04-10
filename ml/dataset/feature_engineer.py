"""
Training-time text preprocessing (normalization + obfuscation mitigations).
"""

from __future__ import annotations

from ml.dataset.text_normalize import normalize_text


def preprocess_for_model(text: str) -> str:
    """Unicode NFKC, strip zero-width / control noise, light leet reversal."""
    return normalize_text(str(text))
