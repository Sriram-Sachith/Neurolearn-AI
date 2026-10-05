# NeuroLearn AI

An intelligent, local-first study assistant that converts PDFs, lecture
slides, textbooks and scanned notes into structured short notes, flashcards,
quizzes and a personalised spaced-repetition plan — using multiple ML models,
local LLMs (Ollama) and evidence-grounded generation.

**Upload. Understand. Remember. Revise.**

## What it does

- **Smart notes** — chapter-wise short/detailed summaries, definitions,
  formulas and key points, each with source-page references.
- **Intelligent flashcards** — Q&A, definition, formula and concept cards with
  difficulty levels. Every card is linked to the source passage it was derived
  from and marked `supported`, `partially_supported` or `unverified`.
- **Adaptive quizzes** — MCQs, fill-in-the-blank and short-answer questions
  with explanations.
- **Topic intelligence** — keyword extraction, subject classification and
  K-Means topic clustering.
- **Personalised revision** — SM-2 spaced repetition, daily queue and
  topic-level mastery.
- **Model Lab** — compare providers and inspect *measured* experiment results
  (retrieval, clustering, flashcard quality, performance, hallucination). No
  placeholder accuracy.

## Architecture

React + TypeScript frontend → FastAPI backend → job orchestrator → document
engine (PyMuPDF/python-pptx/python-docx/Tesseract) → NLP engine (keywords,
classification, embeddings, clustering) → LLM engine (Ollama + heuristic
fallback) → validation engine (evidence, dedup, quality) → data & learning
layer (SQLAlchemy, SQLite/Postgres, SM-2). See [`docs/architecture.md`](docs/architecture.md).

A `LLMProvider` interface means models are swappable; the deterministic
heuristic provider guarantees the whole pipeline runs **offline with zero
external dependencies**. Ollama is a drop-in upgrade when available.

## Quick start (local, offline)

### 1. Backend

```bash
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

A demo account is seeded on startup: `demo@neurolearn.local` / `demo1234`.
SQLite is used by default (no Postgres required).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend.

### 3. (Optional) Run the benchmark experiments

```bash
python experiments/run_all.py
```

This populates the Model Lab with measured results. Without Ollama it records
the heuristic/TF-IDF numbers; install Ollama and re-run to compare live LLMs.

## Upgrading the model stack

| Step | Effect |
| --- | --- |
| `pip install sentence-transformers` + `EMBEDDING_BACKEND=sentence-transformers` | Better embeddings + cross-encoder reranking (auto-falls back to cosine offline). |
| Install [Ollama](https://ollama.com), `ollama pull qwen2.5:3b-instruct` | Pipeline switches from heuristic to the live LLM automatically. |
| Set `DATABASE_URL` to Postgres | Production persistence. |

See [`docs/model_selection.md`](docs/model_selection.md).

## Docker

```bash
docker compose up --build
```

Runs Postgres + backend + frontend. The app still boots in offline mode by
default; point `OLLAMA_BASE_URL` at your host Ollama to enable live LLMs.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — system architecture & module responsibilities
- [`docs/api.md`](docs/api.md) — REST endpoints & data model
- [`docs/model_selection.md`](docs/model_selection.md) — model choices & fallbacks
- [`docs/experiments.md`](docs/experiments.md) — benchmark experiments

## Tech stack

Python · FastAPI · SQLAlchemy · scikit-learn · PyMuPDF · Tesseract · Ollama ·
React · TypeScript · Vite · Recharts.

## Notes

The PDF this project was specified from (`pdf24_converted-2.pdf`) is a scanned
document; the spec was recovered via OCR and is reflected throughout this
implementation and the `docs/` folder.
