"""Evidence linking, duplicate detection, and support classification."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.config import get_settings
from app.ml.embeddings.encoder import cosine, get_embedding_backend


@dataclass
class EvidenceHit:
    chunk_id: str
    score: float
    support_status: str
    passage: str
    page_number: int


def duplicate_questions(questions: list[str], threshold: float | None = None) -> set[int]:
    settings = get_settings()
    thr = threshold if threshold is not None else settings.duplicate_cosine_threshold
    if len(questions) < 2:
        return set()
    backend = get_embedding_backend()
    vecs = backend.encode(questions)
    sims = cosine(vecs, vecs)
    drop: set[int] = set()
    n = len(questions)
    for i in range(n):
        if i in drop:
            continue
        for j in range(i + 1, n):
            if sims[i, j] >= thr:
                drop.add(j)
    return drop


def classify_support(score: float) -> str:
    settings = get_settings()
    if score >= settings.evidence_support_threshold:
        return "supported"
    if score >= settings.evidence_partial_threshold:
        return "partially_supported"
    return "unverified"


def rerank_pairs(query: str, passages: list[str]) -> np.ndarray:
    """Cross-encoder when installed; otherwise cosine with the embedding backend."""
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(get_settings().cross_encoder_model)
        pairs = [(query, p) for p in passages]
        scores = model.predict(pairs)
        return np.asarray(scores, dtype=np.float32)
    except Exception:
        backend = get_embedding_backend()
        q = backend.encode([query])
        p = backend.encode(passages)
        return cosine(q, p).ravel().astype(np.float32)
