"""Notes, flashcards and quizzes from already-extracted document chunks."""

from __future__ import annotations

import json

import numpy as np
from sqlalchemy.orm import Session

from app.llm.generation.schemas import FlashcardsPayload, NotesPayload, QuizPayload
from app.llm.generation.validated import generate_validated
from app.llm.prompts.templates import DOCUMENT_WRAP, FLASHCARD_PROMPT, NOTES_PROMPT, QUIZ_PROMPT
from app.llm.providers.base import LLMProvider
from app.ml.embeddings.encoder import get_embedding_backend
from app.ml.embeddings.vector_store import NumpyVectorStore
from app.models.chunk import Chunk
from app.models.flashcard import CardEvidence, Flashcard
from app.models.model_run import ModelRun
from app.models.note import Note
from app.models.quiz import Quiz, QuizAttempt, QuizItem
from app.models.revision import RevisionState
from app.models.topic import Topic
from app.services.validation_service import classify_support, duplicate_questions, rerank_pairs
from datetime import date


def _blob(chunks: list[Chunk]) -> str:
    return "\n\n".join(c.text for c in chunks)[:12000]


def _store_for(chunks: list[Chunk]) -> tuple[NumpyVectorStore, object]:
    backend = get_embedding_backend()
    texts = [c.text for c in chunks] or ["empty"]
    backend.fit(texts)
    vectors = backend.encode(texts)
    store = NumpyVectorStore()
    if chunks:
        store.add([c.id for c in chunks], vectors)
    return store, backend


def generate_notes(db: Session, document_id: str, provider: LLMProvider) -> list[Note]:
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    payload, run = generate_validated(
        provider,
        NOTES_PROMPT + "\n" + DOCUMENT_WRAP.format(text=_blob(chunks)),
        {"task": "notes"},
        NotesPayload,
    )
    db.query(Note).filter(Note.document_id == document_id).delete()
    rows: list[Note] = []
    for ch in payload.chapters:
        row = Note(
            document_id=document_id,
            title=ch.title,
            content=json.dumps(ch.model_dump()),
            kind="chapter",
            source_pages=",".join(str(p) for p in ch.source_pages),
            model_name=provider.name,
        )
        db.add(row)
        rows.append(row)
    db.add(
        ModelRun(
            model_name=provider.name,
            task="notes",
            experiment="generate",
            latency_ms=run.latency_ms,
            output_chars=run.output_chars,
        )
    )
    db.commit()
    return rows


def generate_flashcards(db: Session, document_id: str, user_id: str, provider: LLMProvider) -> list[Flashcard]:
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    payload, run = generate_validated(
        provider,
        FLASHCARD_PROMPT + "\n" + DOCUMENT_WRAP.format(text=_blob(chunks)),
        {"task": "flashcards"},
        FlashcardsPayload,
    )
    drop = duplicate_questions([c.question for c in payload.cards])
    existing = db.query(Flashcard).filter(Flashcard.document_id == document_id).all()
    for fc in existing:
        db.delete(fc)
    db.flush()
    topic = db.query(Topic).filter(Topic.document_id == document_id).first()
    store, backend = _store_for(chunks)
    chunk_map = {c.id: c for c in chunks}
    saved: list[Flashcard] = []
    for i, item in enumerate(payload.cards):
        if i in drop or not item.question.strip() or not item.answer.strip():
            continue
        fc = Flashcard(
            document_id=document_id,
            topic_id=topic.id if topic else None,
            question=item.question,
            answer=item.answer,
            card_type=item.card_type,
            difficulty=item.difficulty if item.difficulty in {"easy", "medium", "hard"} else "medium",
            source_pages=",".join(str(p) for p in item.source_pages),
            model_name=provider.name,
        )
        db.add(fc)
        db.flush()
        query = fc.question + " " + fc.answer
        hits = store.search(backend.encode([query])[0], k=10) if chunks else []
        passages, ordered = [], []
        for cid, _ in hits:
            ch = chunk_map.get(cid)
            if ch:
                passages.append(ch.text)
                ordered.append(ch)
        if passages:
            scores = rerank_pairs(query, passages)
            best_i = int(np.argmax(scores))
            status = classify_support(float(scores[best_i]))
            fc.support_status = status
            best = ordered[best_i]
            db.add(
                CardEvidence(
                    card_id=fc.id,
                    chunk_id=best.id,
                    support_status=status,
                    score=float(scores[best_i]),
                    passage=best.text[:1500],
                    page_number=best.page_number,
                )
            )
            if not fc.source_pages:
                fc.source_pages = str(best.page_number)
        db.add(
            RevisionState(
                card_id=fc.id,
                user_id=user_id,
                n=0,
                ef=2.5,
                interval_days=0,
                next_review=date.today(),
            )
        )
        saved.append(fc)
    db.add(
        ModelRun(
            model_name=provider.name,
            task="flashcards",
            experiment="generate",
            latency_ms=run.latency_ms,
            output_chars=run.output_chars,
        )
    )
    db.commit()
    return saved


def generate_quiz(db: Session, document_id: str, user_id: str, provider: LLMProvider) -> Quiz:
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    payload, run = generate_validated(
        provider,
        QUIZ_PROMPT + "\n" + DOCUMENT_WRAP.format(text=_blob(chunks)),
        {"task": "quiz"},
        QuizPayload,
    )
    # Replace any prior quizzes for this document so regeneration does not stack duplicates.
    prior_quiz_ids = [q.id for q in db.query(Quiz).filter(Quiz.document_id == document_id).all()]
    if prior_quiz_ids:
        db.query(QuizAttempt).filter(QuizAttempt.quiz_id.in_(prior_quiz_ids)).delete(synchronize_session=False)
        db.query(QuizItem).filter(QuizItem.quiz_id.in_(prior_quiz_ids)).delete(synchronize_session=False)
        db.query(Quiz).filter(Quiz.document_id == document_id).delete(synchronize_session=False)
        db.flush()
    quiz = Quiz(document_id=document_id, user_id=user_id, title="Generated quiz")
    db.add(quiz)
    db.flush()
    for item in payload.items:
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
    db.add(
        ModelRun(
            model_name=provider.name,
            task="quiz",
            experiment="generate",
            latency_ms=run.latency_ms,
            output_chars=run.output_chars,
        )
    )
    db.commit()
    db.refresh(quiz)
    return quiz
