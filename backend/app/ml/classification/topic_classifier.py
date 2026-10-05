"""Lightweight topic labels from keywords/headings (DistilBERT hook for later fine-tuning)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TopicGuess:
    label: str
    method: str


SUBJECT_HINTS = {
    "machine learning": ["supervised", "unsupervised", "regression", "classification", "neural"],
    "operating systems": ["process", "thread", "scheduler", "deadlock", "memory management"],
    "databases": ["sql", "normalization", "transaction", "index", "relational"],
    "networks": ["tcp", "ip", "routing", "packet", "osi"],
    "calculus": ["derivative", "integral", "limit", "differential"],
    "linear algebra": ["matrix", "vector", "eigen", "determinant"],
}


def classify_document(text: str, keywords: list[str]) -> TopicGuess:
    blob = (text + " " + " ".join(keywords)).lower()
    scores: dict[str, int] = {}
    for label, terms in SUBJECT_HINTS.items():
        scores[label] = sum(1 for t in terms if t in blob)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return TopicGuess(label=keywords[0] if keywords else "General", method="keyword-fallback")
    return TopicGuess(label=best.title(), method="lexicon-classifier")
