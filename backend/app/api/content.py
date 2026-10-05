import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned_document
from app.database.session import get_db
from app.llm.providers.registry import get_provider
from app.models.chunk import Chunk
from app.models.flashcard import Flashcard
from app.models.note import Note
from app.models.quiz import Quiz, QuizItem
from app.models.topic import Topic
from app.models.user import User
from app.schemas.api import (
    EvidenceOut,
    FlashcardOut,
    FlashcardUpdate,
    GenerateRequest,
    NoteOut,
    QuizItemOut,
    QuizOut,
    TopicOut,
)
from app.services.generation_service import generate_flashcards, generate_notes, generate_quiz

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/notes/{document_id}", response_model=list[NoteOut])
def get_notes(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(document_id, user, db)
    return db.query(Note).filter(Note.document_id == document_id).all()


@router.get("/flashcards/{document_id}", response_model=list[FlashcardOut])
def get_cards(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(document_id, user, db)
    cards = db.query(Flashcard).filter(Flashcard.document_id == document_id).all()
    out = []
    for c in cards:
        ev = [
            EvidenceOut(
                chunk_id=e.chunk_id,
                support_status=e.support_status,
                score=e.score,
                passage=e.passage,
                page_number=e.page_number,
            )
            for e in c.evidence
        ]
        item = FlashcardOut.model_validate(c)
        item.evidence = ev
        out.append(item)
    return out


@router.get("/topics/{document_id}", response_model=list[TopicOut])
def get_topics(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(document_id, user, db)
    return db.query(Topic).filter(Topic.document_id == document_id).all()


@router.get("/chunks/{document_id}")
def get_chunks(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(document_id, user, db)
    rows = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    return [
        {
            "id": r.id,
            "page_number": r.page_number,
            "heading": r.heading,
            "text": r.text,
            "extraction_method": r.extraction_method,
        }
        for r in rows
    ]


@router.get("/quizzes/{document_id}", response_model=list[QuizOut])
def get_quizzes(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(document_id, user, db)
    quizzes = db.query(Quiz).filter(Quiz.document_id == document_id, Quiz.user_id == user.id).all()
    out = []
    for q in quizzes:
        items = []
        for it in q.items:
            items.append(
                QuizItemOut(
                    id=it.id,
                    question=it.question,
                    qtype=it.qtype,
                    options=json.loads(it.options_json or "[]"),
                    explanation=it.explanation,
                    topic_name=it.topic_name,
                    difficulty=it.difficulty,
                    source_pages=it.source_pages,
                )
            )
        out.append(QuizOut(id=q.id, title=q.title, items=items))
    return out


@router.post("/notes/generate", response_model=list[NoteOut])
def notes_generate(body: GenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(body.document_id, user, db)
    return generate_notes(db, body.document_id, get_provider(body.model_name))


@router.post("/flashcards/generate", response_model=list[FlashcardOut])
def cards_generate(body: GenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(body.document_id, user, db)
    cards = generate_flashcards(db, body.document_id, user.id, get_provider(body.model_name))
    return get_cards(body.document_id, db, user) if cards else []


@router.post("/quizzes/generate", response_model=QuizOut)
def quiz_generate(body: GenerateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(body.document_id, user, db)
    quiz = generate_quiz(db, body.document_id, user.id, get_provider(body.model_name))
    items = [
        QuizItemOut(
            id=it.id,
            question=it.question,
            qtype=it.qtype,
            options=json.loads(it.options_json or "[]"),
            explanation=it.explanation,
            topic_name=it.topic_name,
            difficulty=it.difficulty,
            source_pages=it.source_pages,
        )
        for it in quiz.items
    ]
    return QuizOut(id=quiz.id, title=quiz.title, items=items)


@router.patch("/flashcards/{card_id}", response_model=FlashcardOut)
def patch_card(card_id: str, body: FlashcardUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = db.get(Flashcard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    owned_document(card.document_id, user, db)
    if body.question is not None:
        card.question = body.question
    if body.answer is not None:
        card.answer = body.answer
    if body.difficulty is not None:
        card.difficulty = body.difficulty
    if body.card_type is not None:
        card.card_type = body.card_type
    db.commit()
    db.refresh(card)
    return FlashcardOut.model_validate(card)


@router.delete("/flashcards/{card_id}")
def delete_card(card_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    card = db.get(Flashcard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    owned_document(card.document_id, user, db)
    db.delete(card)
    db.commit()
    return {"ok": True}
