# API reference

Base URL in development: `http://127.0.0.1:8000` (the Vite dev server proxies
`/api` here). All `/api/*` endpoints except `/api/health` and the auth routes
require a `Authorization: Bearer <jwt>` header.

## Auth

| Method | Endpoint | Body | Returns |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | `{name, email, password}` | `{access_token, token_type, name, email}` |
| POST | `/api/auth/login` | `{email, password}` | `{access_token, token_type, name, email}` |
| GET | `/api/auth/me` | — | `{id, name, email, created_at}` |
| GET | `/api/health` | — | `{status, app}` |

## Documents & jobs

| Method | Endpoint | Notes |
| --- | --- | --- |
| POST | `/api/documents/upload` | multipart `file`, optional `?model_name=`. Creates a document and a background `ProcessingJob`. |
| GET | `/api/documents` | List the current user's documents. |
| GET | `/api/documents/{id}` | One document (ownership-checked). |
| GET | `/api/jobs/{job_id}` | Job status/progress (ownership-scoped). |

## Content (per document, ownership-checked)

| Method | Endpoint | Notes |
| --- | --- | --- |
| GET | `/api/notes/{document_id}` | Chapter notes. |
| GET | `/api/flashcards/{document_id}` | Cards with embedded `evidence[]` (passage + score + support_status). |
| GET | `/api/topics/{document_id}` | Topics (one per cluster). |
| GET | `/api/chunks/{document_id}` | Raw extracted chunks (no response model). |
| GET | `/api/quizzes/{document_id}` | Quizzes with items. |
| POST | `/api/notes/generate` | `{document_id, model_name?}` — regenerate notes. |
| POST | `/api/flashcards/generate` | Regenerate flashcards (replaces prior cards + evidence). |
| POST | `/api/quizzes/generate` | Regenerate quiz (replaces prior quizzes for the document). |
| PATCH | `/api/flashcards/{card_id}` | Edit a card's question/answer/difficulty/type. |
| DELETE | `/api/flashcards/{card_id}` | Delete a card. |

## Learning

| Method | Endpoint | Body | Notes |
| --- | --- | --- | --- |
| POST | `/api/quizzes/submit` | `{quiz_id, answers: {item_id: value}}` | Exact-match grading; returns `score`, `correct`, `total`. |
| POST | `/api/revision/submit` | `{card_id, rating}` (again/hard/good/easy) | SM-2 update. |
| GET | `/api/revision/today` | — | Today's due cards. |
| GET | `/api/learning/mastery` | — | Topic-level mastery estimate. |

## Dashboard & evaluation

| Method | Endpoint | Notes |
| --- | --- | --- |
| GET | `/api/dashboard/summary` | Counts, due_today, weak points, 7-day activity, recent docs. |
| GET | `/api/evaluation/compare` | Experiment bundle written by `experiments/run_all.py`. |
| GET | `/api/evaluation/providers` | Available LLM providers. |
| GET | `/api/evaluation/runs` | Recent `ModelRun` rows from the DB. |
| POST | `/api/evaluation/side-by-side` | `{document_id, model_a, model_b}` — generate notes with two models. |

## Data model (entities)

| Table | Key fields |
| --- | --- |
| `users` | id, name, email (unique), password_hash |
| `documents` | id, user_id, filename, original_name, status, storage_path |
| `chunks` | id, document_id, page_number, heading, text, char_start/end, extraction_method, ocr_confidence |
| `embeddings` | chunk_id (unique), vector (bytes), dim, model_name |
| `topics` | id, document_id, topic_name, cluster_id, parent_id, keywords |
| `notes` | id, document_id, title, content (JSON), kind, source_pages |
| `flashcards` | id, document_id, topic_id, question, answer, card_type, difficulty, support_status, source_pages |
| `card_evidence` | card_id, chunk_id, support_status, score, passage, page_number |
| `quizzes` / `quiz_items` / `quiz_attempts` | quiz + items (options JSON) + attempts (score, answers) |
| `revision_state` / `revision_history` | SM-2 state (n, ef, interval, next_review) + rating history |
| `model_runs` | model_name, task, experiment, latency_ms, output_chars |

`Document` cascades to chunks, topics, notes, flashcards, quizzes and jobs.
Deleting a document therefore cleans up all derived content.
