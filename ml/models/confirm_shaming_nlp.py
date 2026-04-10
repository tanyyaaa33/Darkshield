"""
Confirm-shaming second-pass detector using TF-IDF cosine similarity to a reference corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.dataset.dark_patterns_seed import SEED_EXAMPLES

MODEL_PATH = _ROOT / "ml" / "models" / "saved" / "confirm_shaming_tfidf.pkl"
SIM_THRESHOLD = 0.45


def _reference_corpus(min_examples: int = 50) -> List[str]:
    """Collect at least ``min_examples`` confirm-shaming reference lines."""
    texts = [ex["text"] for ex in SEED_EXAMPLES if ex["label"] == "confirm_shaming"]
    if not texts:
        raise ValueError("No confirm_shaming seed examples available.")
    out = list(texts)
    k = 0
    while len(out) < min_examples:
        out.append(out[k % len(texts)] + f" refv{k}")
        k += 1
    return out


class ConfirmShamingNLP:
    """
    TF-IDF vectorizer fit on confirm-shaming references; cosine similarity scoring.

    If max similarity to the reference corpus exceeds ``SIM_THRESHOLD``, the text is
    flagged as confirm shaming with that similarity as confidence.
    """

    def __init__(self, threshold: float = SIM_THRESHOLD):
        self.threshold = threshold
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
            analyzer="word",
        )
        self._ref_matrix = None

    def fit(self, corpus: List[str] | None = None) -> "ConfirmShamingNLP":
        """Fit TF-IDF on reference confirm-shaming sentences."""
        corpus = corpus or _reference_corpus(50)
        self._ref_matrix = self._vectorizer.fit_transform(corpus)
        return self

    def max_similarity(self, text: str) -> float:
        """Return max cosine similarity between ``text`` and reference vectors."""
        if self._ref_matrix is None:
            raise RuntimeError("Call fit() before scoring.")
        v = self._vectorizer.transform([text])
        sims = cosine_similarity(v, self._ref_matrix)
        return float(np.max(sims))

    def classify(self, text: str) -> Tuple[bool, float]:
        """
        Return (is_confirm_shaming, confidence).

        Confidence is the max cosine similarity when above threshold, else the raw max sim.
        """
        s = self.max_similarity(text)
        return (s > self.threshold, float(s))

    def save(self, path: Path | None = None) -> Path:
        """Persist vectorizer state and reference matrix."""
        path = path or MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "threshold": self.threshold,
                "vectorizer": self._vectorizer,
                "ref_matrix": self._ref_matrix,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> "ConfirmShamingNLP":
        """Load a saved model bundle."""
        path = path or MODEL_PATH
        data = joblib.load(path)
        inst = cls(threshold=data["threshold"])
        inst._vectorizer = data["vectorizer"]
        inst._ref_matrix = data["ref_matrix"]
        return inst


def train_and_save_default() -> Path:
    """Fit on seed references and write ``confirm_shaming_tfidf.pkl``."""
    m = ConfirmShamingNLP().fit()
    return m.save()


if __name__ == "__main__":
    p = train_and_save_default()
    print("Saved", p)
