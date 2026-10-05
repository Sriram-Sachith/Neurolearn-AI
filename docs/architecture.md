# Architecture

NeuroLearn AI is a local-first study assistant that turns PDFs, slides,
textbooks and scanned notes into structured notes, flashcards, quizzes and a
spaced-repetition plan. It combines traditional ML/NLP, local LLMs (Ollama),
semantic retrieval and backend engineering.

## High-level layers

```
React + TypeScript frontend   (Vite, port 5173)
  Upload · Notes · Flashcards · Quizzes · Model Lab
        │  (REST, proxied to /api)
        ▼
FastAPI backend                (uvicorn, port 8000)
  Auth · REST API · request validation
        │
        ▼
Job orchestrator              FastAPI BackgroundTasks
  Background jobs · status · pipeline coordination
        │
        ├── Document engine      PyMuPDF · python-pptx · python-docx · Tesseract
        ├── NLP engine           keywords · classification · embeddings · clustering
        ├── LLM engine           Ollama providers · heuristic fallback
        └── Validation engine    evidence · deduplication · quality checks
        │
        ▼
Data & learning layer
  SQLAlchemy models · SQLite (default) / PostgreSQL · vectors · files · SM-2
```

The frontend talks to the backend over `/api`. In development the Vite dev
server proxies `/api` to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`).

## Request flow

1. **Upload** — `POST /api/documents/upload` validates the file
   (`services/file_validation.py`), persists it, creates a `Document` and a
   `ProcessingJob`, then schedules `pipeline.run_pipeline` as a FastAPI
   `BackgroundTask` in a fresh session.
2. **Pipeline** (`services/pipeline.py`) runs the stages below, updating job
   progress between each:
   - extract → chunk → wipe prior artifacts → recreate chunks
   - keywords → classify subject → embed + store + persist embeddings
   - cluster → create topics → generate notes/flashcards/quiz (each via
     `generate_validated`)
   - evidence-validate each card (retrieve top-k, rerank, classify support,
     write `CardEvidence` + seed `RevisionState`)
   - write `ModelRun` rows → mark document `ready`
3. **On-demand regeneration** — `POST /api/{notes,flashcards,quizzes}/generate`
   re-runs only the LLM + validation steps against existing chunks
   (`services/generation_service.py`).
4. **Learning** — quiz submission and SM-2 revision live in
   `services/learning_service.py`, exposed via `api/learning.py`.

## Module responsibilities

| Module | Responsibility |
| --- | --- |
| `services/extraction_service.py` | PDF/PPTX/DOCX/TXT/image + Tesseract OCR |
| `services/chunking_service.py` | ~400-token sliding window, preserves page + heading |
| `services/pipeline.py` | End-to-end orchestration of every stage |
| `services/generation_service.py` | On-demand notes/flashcards/quiz regeneration |
| `services/validation_service.py` | Duplicate detection, support classification, reranking |
| `services/learning_service.py` | SM-2 spaced repetition + mastery estimate |
| `services/file_validation.py` | Extension allowlist + magic-byte sniffing |
| `services/bootstrap.py` | Idempotent demo-user seeding on startup |
| `ml/keywords` | KeyBERT (optional) → TF-IDF n-gram fallback |
| `ml/classification` | Lexicon subject classifier |
| `ml/embeddings` | TF-IDF (default) / Sentence-Transformers backends + vector store |
| `ml/clustering` | K-Means with silhouette-selected K |
| `llm/providers` | `LLMProvider` ABC + Ollama + heuristic providers + registry |
| `llm/generation` | Pydantic schema validation with retries |
| `llm/prompts` | Prompt templates with BEGIN/END document guard |
| `evaluation/loader.py` | Loads on-disk experiment JSON for the Model Lab |

## Provider abstraction

Generation never calls Ollama directly. Everything goes through the
`LLMProvider` interface (`llm/providers/base.py`):

```python
class LLMProvider:
    def generate(self, prompt: str, schema: dict) -> LLMResult: ...
    def available(self) -> bool: ...
```

`registry.get_provider(name)` returns the named provider if available, else
the first live Ollama model, else the deterministic `heuristic-extractor`. This
guarantees the whole pipeline runs offline with zero external dependencies —
Ollama is a drop-in upgrade when available.

## Offline capability

Every optional heavyweight dependency (sentence-transformers, KeyBERT, FAISS,
torch) has a TF-IDF / cosine / heuristic fallback. The application starts and
processes documents fully offline. Installing the extras improves retrieval
and reranking quality but is never required to run.

## Database

SQLAlchemy ORM models under `app/models/`. Schema is created with
`Base.metadata.create_all` on startup (no Alembic migrations are required for
the SQLite prototype). The default `DATABASE_URL` is a local SQLite file; set a
PostgreSQL URL in `.env` for production. See `docs/api.md` for endpoints and
the model relationships.
