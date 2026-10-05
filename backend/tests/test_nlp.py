from app.ml.clustering.kmeans_topics import cluster_topics
from app.ml.embeddings.encoder import TfidfBackend
from app.ml.keywords.extractor import extract_keywords


def test_keywords_and_clusters():
    docs = [
        "Supervised learning classification regression labelled data",
        "Unsupervised clustering dimensionality reduction",
        "Precision recall f1 score evaluation metrics",
        "Neural networks backpropagation gradient descent",
        "Decision trees random forests ensemble methods",
        "K means silhouette score cluster assignment",
    ]
    kws = extract_keywords(docs, top_k=5)
    assert kws
    backend = TfidfBackend()
    backend.fit(docs)
    vecs = backend.encode(docs)
    result = cluster_topics(vecs, ["SL", "UL", "Eval", "NN", "Trees", "KM"], [k[0] for k in kws])
    assert result.k >= 1
    assert result.names
