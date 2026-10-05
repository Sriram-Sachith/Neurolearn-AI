from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.llm.generation.schemas import FlashcardsPayload, NotesPayload, QuizPayload
from app.llm.generation.validated import generate_validated
from app.llm.prompts.templates import (
    DOCUMENT_WRAP,
    FLASHCARD_PROMPT,
    NOTES_PROMPT,
    QUIZ_PROMPT,
)
from app.llm.providers.registry import get_provider
from app.ml.classification.topic_classifier import classify_document
from app.ml.clustering.kmeans_topics import cluster_topics
from app.ml.embeddings.encoder import get_embedding_backend
from app.ml.embeddings.vector_store import NumpyVectorStore
from app.ml.keywords.extractor import extract_keywords
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.flashcard import CardEvidence, Flashcard
from app.models.job import ProcessingJob
from app.models.model_run import ModelRun
from app.models.note import Note
from app.models.quiz import Quiz, QuizItem
from app.models.revision import RevisionHistory, RevisionState
from app.models.topic import Topic
from app.services.chunking_service import chunk_pages
from app.services.extraction_service import extract_document
from app.services.validation_service import classify_support, duplicate_questions, rerank_pairs

logger = logging.getLogger(__name__)


def _update_job(db: Session, job: ProcessingJob, status: str, progress: int, error: str = "") -> None:
    job.status = status
    job.progress = progress
    job.error_message = error
    db.add(job)
    db.commit()
    db.refresh(job)


def run_pipeline(db: Session, job_id: str, model_name: str | None = None) -> None:
    job = db.get(ProcessingJob, job_id)
    if job is None:
        return
    doc = db.get(Document, job.document_id)
    if doc is None:
        _update_job(db, job, "failed", 0, "Document missing")
        return
    try:
        provider = get_provider(model_name or job.model_name or None)
        job.model_name = provider.name
        _update_job(db, job, "extracting", 10)
        extracted = extract_document(Path(doc.storage_path))

        _update_job(db, job, "chunking", 25)
        source_chunks = chunk_pages(extracted.pages)
        for fc in db.query(Flashcard).filter(Flashcard.document_id == doc.id).all():
            db.query(CardEvidence).filter(CardEvidence.card_id == fc.id).delete()
            db.query(RevisionHistory).filter(RevisionHistory.card_id == fc.id).delete()
            db.query(RevisionState).filter(RevisionState.card_id == fc.id).delete()
            db.delete(fc)
        db.query(Note).filter(Note.document_id == doc.id).delete()
        db.query(Topic).filter(Topic.document_id == doc.id).delete()
        chunks_old = db.query(Chunk).filter(Chunk.document_id == doc.id).all()
        for ch in chunks_old:
            db.query(Embedding).filter(Embedding.chunk_id == ch.id).delete()
            db.delete(ch)
        db.flush()
        chunk_rows: list[Chunk] = []
        for sc in source_chunks:
            row = Chunk(
                document_id=doc.id,
                page_number=sc.page_number,
                heading=sc.heading,
                text=sc.text,
                char_start=sc.char_start,
                char_end=sc.char_end,
                extraction_method=sc.extraction_method,
                ocr_confidence=sc.ocr_confidence,
            )
            db.add(row)
            chunk_rows.append(row)
        db.flush()

        texts = [c.text for c in chunk_rows]
        headings = [c.heading for c in chunk_rows]
        _update_job(db, job, "analysing", 40)
        keywords = extract_keywords(texts)
        kw_terms = [k for k, _ in keywords]
        blob = " ".join(texts)
        guess = classify_document(blob, kw_terms)

        _update_job(db, job, "embedding", 55)
        backend = get_embedding_backend()
        backend.fit(texts or ["empty"])
        vectors = backend.encode(texts or ["empty"])
        store = NumpyVectorStore()
        ids = [c.id for c in chunk_rows]
        if chunk_rows:
            store.add(ids, vectors)
            for c, vec in zip(chunk_rows, vectors):
                db.add(
                    Embedding(
                        chunk_id=c.id,
                        model_name=backend.name,
                        dim=int(vec.shape[0]),
                        vector=vec.astype(np.float32).tobytes(),
                    )
                )

        clustering = cluster_topics(vectors if len(texts) else np.zeros((1, 8)), headings, kw_terms)
        topic_rows: dict[int, Topic] = {}
        for cid, name in clustering.names.items():
            t = Topic(
                document_id=doc.id,
                topic_name=name,
                cluster_id=int(cid),
                keywords=", ".join(kw_terms[:8]),
            )
            db.add(t)
            topic_rows[int(cid)] = t
        db.flush()

        # Map each chunk to the topic of the cluster it was assigned to, so cards
        # can be linked to the topic of the chunk that best supports them rather
        # than every card being pinned to the first topic.
        chunk_topic_id: dict[str, str] = {}
        if chunk_rows and len(clustering.labels) == len(chunk_rows):
            for c, lab in zip(chunk_rows, clustering.labels):
                t = topic_rows.get(int(lab))
                if t:
                    chunk_topic_id[c.id] = t.id
        fallback_topic_id = next(iter(topic_rows.values())).id if topic_rows else None

        wrapped = DOCUMENT_WRAP.format(text=blob[:12000])
        _update_job(db, job, "generating", 70)
        notes, notes_run = generate_validated(
            provider,
            NOTES_PROMPT + "\n" + wrapped,
            {"task": "notes"},
            NotesPayload,
        )
        for ch in notes.chapters:
            db.add(
                Note(
                    document_id=doc.id,
                    title=ch.title,
                    content=json.dumps(ch.model_dump()),
                    kind="chapter",
                    source_pages=",".join(str(p) for p in ch.source_pages),
                    model_name=provider.name,
                )
            )
        db.add(
            ModelRun(
                model_name=provider.name,
                task="notes",
                experiment="pipeline",
                latency_ms=notes_run.latency_ms,
                output_chars=notes_run.output_chars,
            )
        )

        cards, cards_run = generate_validated(
            provider,
            FLASHCARD_PROMPT + "\n" + wrapped,
            {"task": "flashcards"},
            FlashcardsPayload,
        )
        drop = duplicate_questions([c.question for c in cards.cards])
        saved_cards: list[Flashcard] = []
        for i, item in enumerate(cards.cards):
            if i in drop:
                continue
            if not item.question.strip() or not item.answer.strip():
                continue
            fc = Flashcard(
                document_id=doc.id,
                topic_id=fallback_topic_id,
                question=item.question,
                answer=item.answer,
                card_type=item.card_type,
                difficulty=item.difficulty if item.difficulty in {"easy", "medium", "hard"} else "medium",
                source_pages=",".join(str(p) for p in item.source_pages),
                model_name=provider.name,
            )
            db.add(fc)
            saved_cards.append(fc)
        db.flush()

        quiz_payload, quiz_run = generate_validated(
            provider,
            QUIZ_PROMPT + "\n" + wrapped,
            {"task": "quiz"},
            QuizPayload,
        )
        quiz = Quiz(document_id=doc.id, user_id=job.user_id, title=f"Quiz · {doc.original_name}")
        db.add(quiz)
        db.flush()
        for item in quiz_payload.items:
            db.add(
                QuizItem(
                    quiz_id=quiz.id,
                    question=item.question,
                    qtype=item.qtype,
                    options_json=json.dumps(item.options),
                    answer=item.answer,
                    explanation=item.explanation,
                    topic_name=item.topic,
                    difficulty=item.difficulty,
                    source_pages=",".join(str(p) for p in item.source_pages),
                )
            )

        _update_job(db, job, "validating", 88)
        for fc in saved_cards:
            query = fc.question + " " + fc.answer
            hits = store.search(backend.encode([query])[0], k=10) if chunk_rows else []
            passages = []
            chunk_map = {c.id: c for c in chunk_rows}
            ordered = []
            for cid, _score in hits:
                ch = chunk_map.get(cid)
                if ch:
                    passages.append(ch.text)
                    ordered.append(ch)
            if passages:
                scores = rerank_pairs(query, passages)
                best_i = int(np.argmax(scores))
                best_score = float(scores[best_i])
                status = classify_support(best_score)
                fc.support_status = status
                best = ordered[best_i]
                # Link the card to the topic of the chunk that best supports it.
                fc.topic_id = chunk_topic_id.get(best.id) or fallback_topic_id
                db.add(
                    CardEvidence(
                        card_id=fc.id,
                        chunk_id=best.id,
                        support_status=status,
                        score=best_score,
                        passage=best.text[:1500],
                        page_number=best.page_number,
                    )
                )
                if not fc.source_pages:
                    fc.source_pages = str(best.page_number)
            db.add(
                RevisionState(
                    card_id=fc.id,
                    user_id=job.user_id,
                    n=0,
                    ef=2.5,
                    interval_days=0,
                    next_review=date.today(),
                )
            )

        db.add(
            ModelRun(
                model_name=provider.name,
                task="flashcards",
                experiment="pipeline",
                latency_ms=cards_run.latency_ms,
                output_chars=cards_run.output_chars,
            )
        )
        db.add(
            ModelRun(
                model_name=provider.name,
                task="quiz",
                experiment="pipeline",
                latency_ms=quiz_run.latency_ms,
                output_chars=quiz_run.output_chars,
            )
        )
        doc.status = "ready"
        _update_job(db, job, "completed", 100)
        logger.info("pipeline complete doc=%s topics=%s cards=%s", doc.id, guess.label, len(saved_cards))
    except Exception as exc:
        logger.exception("pipeline failed")
        doc.status = "failed"
        _update_job(db, job, "failed", job.progress, str(exc)[:500])
