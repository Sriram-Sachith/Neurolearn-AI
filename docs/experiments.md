# Experiments

The project ships a measurable benchmark harness (`experiments/run_all.py`)
over the corpus in `benchmark/documents/`. It never writes placeholder
accuracy: if Ollama is offline, the LLM comparison records only the heuristic
extractors that actually ran.

Run everything:

```bash
python experiments/run_all.py
```

This writes JSON into `experiments/<category>/` and a manifest in
`benchmark/evaluation_results/manifest.json`, which the **Model Lab** page
reads through `/api/evaluation/compare`.

## Experiments

| ID | Experiment | What it measures | Output file |
| --- | --- | --- | --- |
| A | LLM comparison | Generation stats (latency, output chars, chapters, key points) for every *available* provider. Human rubric scores are omitted until a reviewer scores a sample. | `experiments/llm_comparison/results.json` |
| B | Flashcard quality | Per-document card count, duplicate rate, source-support rate, latency. Approach C: heuristic cards + TF-IDF evidence. | `experiments/flashcard_quality/results.json` |
| C | Retrieval | TF-IDF + cosine over lecture pages: Recall@5, MRR, retrieval latency. | `experiments/retrieval/results.json` |
| D | Hallucination | Unanswerable questions must be flagged `unverified` (cross-encoder→cosine fallback). | `experiments/retrieval/hallucination.json` |
| E | Performance | Five trials per stage (keywords, embed, cluster, heuristic notes): median/mean/stdev ms. | `experiments/performance/results.json` |
| F | Clustering | K-Means silhouette-selected K over document vectors. | `experiments/llm_comparison/clustering.json` |

## Benchmark corpus

`benchmark/documents/` contains lecture notes across college subjects
(machine learning, operating systems, databases, networks, calculus, …).
`benchmark/reference_questions/` holds gold retrieval questions (with
supporting page numbers) and deliberately unanswerable questions. These give
evidence to support model-selection decisions rather than guessing.

## Recent measured results (this machine)

These reflect the offline TF-IDF + heuristic configuration (no Ollama, no
sentence-transformers). Re-run `experiments/run_all.py` after installing
heavier dependencies to refresh them.

- **Retrieval (Experiment C):** Recall@5 = 1.0, MRR = 1.0 on the gold question
  set.
- **Hallucination (Experiment D):** unanswerable questions correctly flagged
  `unverified`.
- **Clustering (Experiment F):** K chosen by silhouette over the document
  vectors.
- **Flashcards (Experiment B):** duplicate rate and source-support rate per
  document.
- **Performance (Experiment E):** stage timings recorded with five trials.

The Model Lab renders all of the above as tables/charts and lists any still
missing files under "Not yet measured" with the exact command to run.
