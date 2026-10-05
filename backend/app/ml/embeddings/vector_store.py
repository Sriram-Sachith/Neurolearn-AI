from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class VectorStore(ABC):
    @abstractmethod
    def add(self, ids: list[str], vectors: np.ndarray) -> None: ...

    @abstractmethod
    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]: ...


class NumpyVectorStore(VectorStore):
    def __init__(self) -> None:
        self.ids: list[str] = []
        self.matrix: np.ndarray | None = None

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        self.ids.extend(ids)
        if self.matrix is None:
            self.matrix = vectors.astype(np.float32)
        else:
            self.matrix = np.vstack([self.matrix, vectors.astype(np.float32)])

    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        if self.matrix is None or not self.ids:
            return []
        q = query.reshape(1, -1).astype(np.float32)
        a = self.matrix
        denom = (np.linalg.norm(a, axis=1) * np.linalg.norm(q) + 1e-9)
        sims = (a @ q.T).ravel() / denom
        idx = np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in idx]


class FaissVectorStore(VectorStore):
    def __init__(self, dim: int) -> None:
        import faiss

        self.ids: list[str] = []
        self.index = faiss.IndexFlatIP(dim)

    def add(self, ids: list[str], vectors: np.ndarray) -> None:
        import faiss

        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
        normed = (vectors / norms).astype(np.float32)
        self.index.add(normed)
        self.ids.extend(ids)

    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        q = query.reshape(1, -1).astype(np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        scores, idxs = self.index.search(q, min(k, len(self.ids) or 1))
        out: list[tuple[str, float]] = []
        for i, score in zip(idxs[0], scores[0]):
            if i < 0 or i >= len(self.ids):
                continue
            out.append((self.ids[int(i)], float(score)))
        return out


def build_store(dim: int) -> VectorStore:
    from app.core.config import get_settings

    if get_settings().vector_store == "faiss":
        try:
            return FaissVectorStore(dim)
        except Exception:
            pass
    return NumpyVectorStore()
