"""Keyword extraction: KeyBERT when installed, otherwise TF-IDF n-grams."""

from __future__ import annotations

import logging
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


def extract_keywords(texts: list[str], top_k: int = 12) -> list[tuple[str, float]]:
    joined = [t for t in texts if t.strip()]
    if not joined:
        return []
    try:
        from keybert import KeyBERT

        kw_model = KeyBERT()
        pairs = kw_model.extract_keywords(" ".join(joined)[:20000], keyphrase_ngram_range=(1, 3), top_n=top_k)
        return [(p, float(s)) for p, s in pairs]
    except Exception:
        logger.info("KeyBERT unavailable; using TF-IDF keyword fallback")
        vec = TfidfVectorizer(ngram_range=(1, 3), stop_words="english", max_features=2000)
        X = vec.fit_transform(joined)
        scores = X.sum(axis=0).A1
        vocab = vec.get_feature_names_out()
        ranked = sorted(zip(vocab, scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(w, float(s)) for w, s in ranked]


def heading_counter(headings: list[str]) -> list[str]:
    cleaned = [h.strip() for h in headings if h and h.strip()]
    counts = Counter(cleaned)
    return [h for h, _ in counts.most_common(20)]
