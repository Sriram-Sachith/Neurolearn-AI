"""K-Means topic grouping with silhouette-selected K. Cluster names come from headings/keywords."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


@dataclass
class ClusterResult:
    labels: np.ndarray
    k: int
    silhouette: float | None
    names: dict[int, str]


def choose_k(embeddings: np.ndarray, k_min: int = 2, k_max: int = 8) -> tuple[int, float | None, np.ndarray]:
    n = embeddings.shape[0]
    if n < 3:
        return 1, None, np.zeros(n, dtype=int)
    best_k = 2
    best_score = -1.0
    best_labels = np.zeros(n, dtype=int)
    upper = min(k_max, n - 1)
    for k in range(k_min, upper + 1):
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = model.fit_predict(embeddings)
        if len(set(labels)) < 2:
            continue
        score = float(silhouette_score(embeddings, labels))
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels
    if best_score < 0:
        return 1, None, np.zeros(n, dtype=int)
    return best_k, best_score, best_labels


def name_clusters(
    labels: np.ndarray,
    headings: list[str],
    keywords: list[str],
) -> dict[int, str]:
    names: dict[int, str] = {}
    for cid in sorted(set(labels.tolist())):
        idxs = [i for i, lab in enumerate(labels) if lab == cid]
        cluster_headings = [headings[i] for i in idxs if i < len(headings) and headings[i]]
        if cluster_headings:
            names[int(cid)] = cluster_headings[0][:80]
        elif keywords:
            names[int(cid)] = keywords[cid % len(keywords)]
        else:
            names[int(cid)] = f"Topic {cid + 1}"
    return names


def cluster_topics(embeddings: np.ndarray, headings: list[str], keywords: list[str]) -> ClusterResult:
    k, sil, labels = choose_k(embeddings)
    names = name_clusters(labels, headings, keywords)
    return ClusterResult(labels=labels, k=k, silhouette=sil, names=names)
