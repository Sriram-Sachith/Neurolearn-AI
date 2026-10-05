# Model selection

NeuroLearn deliberately separates responsibilities across models rather than
using one LLM for everything. Each stage has a chosen model and a measured
fallback so the project runs on a bare MacBook without any heavyweight
dependencies.

## Local LLMs (Ollama)

The registry (`llm/providers/registry.py`) builds four providers:

| Provider | Role | Notes |
| --- | --- | --- |
| `qwen2.5:3b-instruct` | Notes, structured flashcards, quizzes | Strong instruction following; primary default. |
| `gemma2:2b-instruct` | Summarisation and explanations | Compared against Qwen in the Model Lab. |
| `heuristic-extractor` | Offline fallback | Deterministic regex/sentence heuristics; always available. |
| `heuristic-alt` | Stride-2 variant | Used for comparison only. |

`get_provider(name)` returns the named provider if available, else the first
live Ollama model (it pings `/api/tags`), else `heuristic-extractor`. This
means the pipeline never fails just because Ollama is not running — it
degrades gracefully to a deterministic offline provider and produces the same
JSON shapes.

The Ollama provider (`llm/providers/ollama.py`) requests `format: "json"`,
pins temperature/seed/context from config, and prepends a prompt-injection
guard that tells the model to treat the `BEGIN_DOCUMENT … END_DOCUMENT` block
as data, not instructions.

## Traditional ML / NLP

| Task | Chosen model | Fallback when missing |
| --- | --- | --- |
| Keyword extraction | KeyBERT | TF-IDF n-gram ranking (`ml/keywords/extractor.py`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | TF-IDF (768 features, 1-2 grams) |
| Vector store | FAISS | `NumpyVectorStore` (manual cosine) |
| Passage reranking | `cross-encoder/ms-marco-MiniLM-L6-v2` | Cosine similarity with the embedding backend |
| Topic classification | (DistilBERT hook documented) | Lexicon classifier over subject hints |
| Topic clustering | K-Means with silhouette-selected K | — |
| Spaced repetition | SM-2 | — |

## How to choose / extend

- **For a portfolio demo on a MacBook Air M4:** leave `EMBEDDING_BACKEND=tfidf`
  and run without Ollama. Everything works; the Model Lab shows measured
  heuristic/TF-IDF numbers. No model downloads needed.
- **For better retrieval:** `pip install sentence-transformers` and set
  `EMBEDDING_BACKEND=sentence-transformers`. The rerank step will then use the
  cross-encoder automatically if it can be loaded; otherwise it falls back to
  cosine.
- **For better generation:** install [Ollama](https://ollama.com) and pull
  `qwen2.5:3b-instruct`. The registry detects it automatically and the
  pipeline switches from the heuristic provider to the live LLM.
- **Adding a model:** implement `LLMProvider` and register it in
  `build_registry()`. No other code changes are required — generation,
  validation and evaluation all go through the interface.

## Selection rationale

Small quantised 3B–4B instruct models are the right starting point for an M4
Air with unified memory: low latency, low RAM, and good enough instruction
following for structured JSON output. Larger models are only worth it if the
recorded latency and memory measurements (Experiment E in the Model Lab) show
the trade-off is acceptable. We never assume a bigger model is better — we
measure.
