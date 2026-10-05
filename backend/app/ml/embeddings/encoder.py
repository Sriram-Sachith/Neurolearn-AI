"""Swappable embedding backends: TF-IDF (default) and sentence-transformers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingBackend(ABC):
    name: str

    @abstractmethod
    def fit(self, texts: list[str]) -> None: ...

    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray: ...


class TfidfBackend(EmbeddingBackend):
    name = "tfidf"

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(max_features=768, ngram_range=(1, 2), stop_words="english")
        self._fitted = False

    def fit(self, texts: list[str]) -> None:
        corpus = texts or ["placeholder"]
        self.vectorizer.fit(corpus)
        self._fitted = True

    def encode(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts)
        dense = matrix.toarray().astype(np.float32)
        return dense


class SentenceTransformerBackend(EmbeddingBackend):
    name = "sentence-transformers"

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.name = model_name

    def fit(self, texts: list[str]) -> None:
        return

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, normalize_embeddings=True), dtype=np.float32)


_backend: EmbeddingBackend | None = None


def reset_embedding_backend() -> None:
    global _backend
    _backend = None


def get_embedding_backend() -> EmbeddingBackend:
    global _backend
    if _backend is not None:
        return _backend
    settings = get_settings()
    if settings.embedding_backend == "sentence-transformers":
        try:
            _backend = SentenceTransformerBackend(settings.embedding_model)
            return _backend
        except Exception as exc:
            logger.warning("Falling back to TF-IDF embeddings: %s", exc)
    _backend = TfidfBackend()
    return _backend


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return cosine_similarity(a, b)
