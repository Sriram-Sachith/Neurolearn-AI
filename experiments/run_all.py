"""Run measurable experiments on the local benchmark corpus.

Never writes placeholder accuracy. If Ollama is offline, LLM comparison records
only the heuristic extractors that actually ran.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.llm.generation.schemas import FlashcardsPayload, NotesPayload
from app.llm.generation.validated import generate_validated
from app.llm.prompts.templates import DOCUMENT_WRAP, FLASHCARD_PROMPT, NOTES_PROMPT
from app.llm.providers.registry import get_provider, list_providers
from app.ml.clustering.kmeans_topics import cluster_topics
from app.ml.embeddings.encoder import TfidfBackend
from app.ml.keywords.extractor import extract_keywords
from app.ml.embeddings.vector_store import NumpyVectorStore
from app.services.chunking_service import chunk_pages
from app.services.extraction_service import ExtractedPage
from app.services.validation_service import classify_support, duplicate_questions, rerank_pairs


DOC_DIR = ROOT / "benchmark" / "documents"
GOLD = ROOT / "benchmark" / "reference_questions" / "gold_retrieval.json"
OUT_EVAL = ROOT / "benchmark" / "evaluation_results"


def load_docs() -> list[tuple[str, str]]:
    files = sorted(DOC_DIR.glob("*.txt"))
    return [(p.name, p.read_text(encoding="utf-8")) for p in files]


def run_retrieval() -> dict:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    docs = dict(load_docs())
    backend = TfidfBackend()
    corpus_ids: list[str] = []
    corpus_texts: list[str] = []
    pages: dict[str, int] = {}
    for item in gold["items"]:
        text = docs[item["document"]]
        # split by Page N
        parts = []
        current = 1
        buf: list[str] = []
        for line in text.splitlines():
            if line.strip().lower().startswith("page "):
                if buf:
                    parts.append((current, "\n".join(buf)))
                    buf = []
                try:
                    current = int(line.strip().split()[1])
                except Exception:
                    current = current + 1
            else:
                buf.append(line)
        if buf:
            parts.append((current, "\n".join(buf)))
        for page, body in parts:
            cid = f"{item['document']}:p{page}"
            corpus_ids.append(cid)
            corpus_texts.append(body)
            pages[cid] = page
    backend.fit(corpus_texts)
    store = NumpyVectorStore()
    store.add(corpus_ids, backend.encode(corpus_texts))
    recalls = []
    mrrs = []
    latencies = []
    for item in gold["items"]:
        q = item["question"]
        expected_pages = set(item["gold_pages"])
        t0 = time.perf_counter()
        vec = backend.encode([q])[0]
        hits = store.search(vec, k=5)
        latencies.append((time.perf_counter() - t0) * 1000)
        hit_pages = [pages[cid] for cid, _ in hits if cid.startswith(item["document"])]
        hit_set = set(hit_pages)
        recalls.append(1.0 if expected_pages & hit_set else 0.0)
        rank = None
        for i, p in enumerate(hit_pages, start=1):
            if p in expected_pages:
                rank = i
                break
        mrrs.append(0.0 if rank is None else 1.0 / rank)
    result = {
        "experiment": "C",
        "notes": "TF-IDF + cosine on lecture pages. Recall@5 is 1 if any gold page is in the top 5.",
        "n_queries": len(gold["items"]),
        "models": [
            {
                "name": "tfidf",
                "recall_at_5": round(sum(recalls) / len(recalls), 4),
                "mrr": round(sum(mrrs) / len(mrrs), 4),
                "latency_ms_median": round(statistics.median(latencies), 3),
                "latency_ms_stdev": round(statistics.pstdev(latencies), 3) if len(latencies) > 1 else 0.0,
            }
        ],
    }
    path = ROOT / "experiments" / "retrieval" / "results.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_hallucination() -> dict:
    gold = json.loads((ROOT / "benchmark" / "reference_questions" / "unanswerable.json").read_text())
    docs = dict(load_docs())
    backend = TfidfBackend()
    texts = list(docs.values())
    backend.fit(texts)
    store = NumpyVectorStore()
    store.add(list(docs.keys()), backend.encode(texts))
    flags = []
    for item in gold["items"]:
        vec = backend.encode([item["question"]])[0]
        hits = store.search(vec, k=3)
        passages = [docs[cid] for cid, _ in hits]
        scores = rerank_pairs(item["question"], passages) if passages else [0.0]
        status = classify_support(float(max(scores)))
        flags.append({"question": item["question"], "support_status": status, "expected": "unverified"})
    n_correct = sum(1 for f in flags if f["support_status"] == "unverified")
    result = {
        "experiment": "D",
        "notes": "Questions deliberately not answered in the corpus. Cross-encoder falls back to cosine if unavailable.",
        "n": len(flags),
        "flagged_unverified": n_correct,
        "rate": round(n_correct / len(flags), 4) if flags else None,
        "items": flags,
    }
    path = ROOT / "experiments" / "retrieval" / "hallucination.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_clustering() -> dict:
    docs = load_docs()
    texts = [t for _, t in docs]
    backend = TfidfBackend()
    backend.fit(texts)
    vecs = backend.encode(texts)
    headings = [name for name, _ in docs]
    kws = [k for k, _ in extract_keywords(texts, top_k=12)]
    result_c = cluster_topics(vecs, headings, kws)
    out = {
        "experiment": "F",
        "n_documents": len(docs),
        "best_k": result_c.k,
        "best_silhouette": result_c.silhouette,
        "names": result_c.names,
        "notes": "K chosen by silhouette on TF-IDF document vectors. Cluster names are filenames/keywords, not claimed academic labels.",
    }
    path = ROOT / "experiments" / "llm_comparison" / "clustering.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def run_flashcards() -> dict:
    docs = load_docs()
    provider = get_provider("heuristic-extractor")
    metrics = []
    for name, text in docs:
        pages = [ExtractedPage(page_number=1, heading=name, text=text, method="txt")]
        chunks = chunk_pages(pages)
        blob = "\n".join(c.text for c in chunks)
        cards, run = generate_validated(
            provider,
            FLASHCARD_PROMPT + "\n" + DOCUMENT_WRAP.format(text=blob[:8000]),
            {"task": "flashcards"},
            FlashcardsPayload,
        )
        drop = duplicate_questions([c.question for c in cards.cards])
        n = len(cards.cards)
        dup_rate = len(drop) / n if n else 0.0
        backend = TfidfBackend()
        passages = [c.text for c in chunks] or [text]
        backend.fit(passages)
        store = NumpyVectorStore()
        store.add([str(i) for i in range(len(passages))], backend.encode(passages))
        supported = 0
        for card in cards.cards:
            qv = backend.encode([card.question + " " + card.answer])[0]
            hits = store.search(qv, k=3)
            texts_h = [passages[int(i)] for i, _ in hits]
            scores = rerank_pairs(card.answer, texts_h)
            if classify_support(float(max(scores))) in {"supported", "partially_supported"}:
                supported += 1
        metrics.append(
            {
                "document": name,
                "n_cards": n,
                "duplicate_rate": round(dup_rate, 4),
                "source_support_rate": round(supported / n, 4) if n else 0.0,
                "latency_ms": round(run.latency_ms, 3),
            }
        )
    out = {
        "experiment": "B",
        "notes": "Approach C-like: heuristic cards + TF-IDF evidence. Direct LLM comparison requires Ollama.",
        "metrics": metrics,
    }
    path = ROOT / "experiments" / "flashcard_quality" / "results.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def run_llm() -> dict:
    docs = load_docs()[:3]
    text = docs[0][1][:6000]
    prompt = NOTES_PROMPT + "\n" + DOCUMENT_WRAP.format(text=text)
    runs = []
    providers = list_providers()
    for info in providers:
        if not info["available"]:
            continue
        p = get_provider(str(info["name"]))
        try:
            notes, run = generate_validated(p, prompt, {"task": "notes"}, NotesPayload)
        except Exception as exc:
            runs.append({"model": p.name, "error": str(exc)})
            continue
        n_chars = sum(len(c.short_summary) + len(c.detailed_summary) for c in notes.chapters)
        runs.append(
            {
                "model": p.name,
                "family": p.family,
                "latency_ms": round(run.latency_ms, 3),
                "output_chars": n_chars,
                "n_chapters": len(notes.chapters),
                "n_key_points": sum(len(c.key_points) for c in notes.chapters),
            }
        )
    out = {
        "experiment": "A",
        "notes": (
            "Human rubric scores are omitted until a reviewer scores a sample. "
            "Numbers below are measured generation stats only. "
            "Ollama models appear only if they answered /api/tags on this machine."
        ),
        "environment": {"python": sys.version.split()[0]},
        "runs": runs,
        "providers_seen": providers,
    }
    path = ROOT / "experiments" / "llm_comparison" / "results.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def run_performance() -> dict:
    docs = load_docs()
    text = docs[0][1]
    stages = {"extract_keywords": [], "embed_tfidf": [], "cluster": [], "heuristic_notes": []}
    for _ in range(5):
        t0 = time.perf_counter()
        extract_keywords([text], top_k=8)
        stages["extract_keywords"].append((time.perf_counter() - t0) * 1000)
        backend = TfidfBackend()
        t0 = time.perf_counter()
        backend.fit([text])
        backend.encode([text])
        stages["embed_tfidf"].append((time.perf_counter() - t0) * 1000)
        vecs = backend.encode([text, text[::-1], text[:200], text[200:400], text[400:600], text[600:800]])
        t0 = time.perf_counter()
        cluster_topics(vecs, ["a", "b", "c", "d", "e", "f"], ["k"])
        stages["cluster"].append((time.perf_counter() - t0) * 1000)
        p = get_provider("heuristic-extractor")
        t0 = time.perf_counter()
        generate_validated(p, NOTES_PROMPT + "\n" + DOCUMENT_WRAP.format(text=text[:4000]), {"task": "notes"}, NotesPayload)
        stages["heuristic_notes"].append((time.perf_counter() - t0) * 1000)
    summary = []
    for stage, vals in stages.items():
        summary.append(
            {
                "stage": stage,
                "median_ms": round(statistics.median(vals), 3),
                "mean_ms": round(statistics.mean(vals), 3),
                "stdev_ms": round(statistics.pstdev(vals), 3),
                "n_trials": len(vals),
            }
        )
    out = {
        "experiment": "E",
        "notes": "Five trials on this host. Peak GPU/RAM for Ollama is not recorded unless Ollama is installed.",
        "trials_summary": summary,
    }
    path = ROOT / "experiments" / "performance" / "results.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main() -> None:
    OUT_EVAL.mkdir(parents=True, exist_ok=True)
    bundle = {
        "retrieval": run_retrieval(),
        "hallucination": run_hallucination(),
        "clustering": run_clustering(),
        "flashcard_quality": run_flashcards(),
        "llm_comparison": run_llm(),
        "performance": run_performance(),
    }
    manifest = {
        "generated_by": "experiments/run_all.py",
        "contains_human_rubric": False,
        "files": [
            "experiments/retrieval/results.json",
            "experiments/retrieval/hallucination.json",
            "experiments/llm_comparison/clustering.json",
            "experiments/flashcard_quality/results.json",
            "experiments/llm_comparison/results.json",
            "experiments/performance/results.json",
        ],
    }
    (OUT_EVAL / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: "ok" for k in bundle}, indent=2))


if __name__ == "__main__":
    main()
