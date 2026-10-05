import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.flashcard import Flashcard
from app.models.quiz import Quiz, QuizAttempt, QuizItem
from app.models.revision import RevisionHistory, RevisionState
from app.models.user import User
from app.schemas.api import QuizSubmit, RevisionCardOut, RevisionSubmit
from app.services.learning_service import RATING_TO_Q, SM2State, mastery_score, sm2_update

router = APIRouter(prefix="/api", tags=["learning"])


@router.post("/quizzes/submit")
def submit_quiz(body: QuizSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    quiz = db.get(Quiz, body.quiz_id)
    if quiz is None or quiz.user_id != user.id:
        raise HTTPException(status_code=404, detail="Quiz not found")
    items = db.query(QuizItem).filter(QuizItem.quiz_id == quiz.id).all()
    correct = 0
    details = []
    for it in items:
        given = (body.answers.get(it.id) or "").strip().lower()
        ok = given == it.answer.strip().lower()
        if ok:
            correct += 1
        details.append({"id": it.id, "correct": ok, "expected": it.answer, "explanation": it.explanation})
    score = correct / len(items) if items else 0.0
    att = QuizAttempt(quiz_id=quiz.id, user_id=user.id, score=score, answers_json=json.dumps(body.answers))
    db.add(att)
    db.commit()
    return {"score": score, "correct": correct, "total": len(items), "details": details}


@router.post("/revision/submit")
def submit_revision(body: RevisionSubmit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rating = body.rating.lower()
    if rating not in RATING_TO_Q:
        raise HTTPException(status_code=400, detail="rating must be again|hard|good|easy")
    card = db.get(Flashcard, body.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    from app.models.document import Document

    doc = db.get(Document, card.document_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    state = (
        db.query(RevisionState)
        .filter(RevisionState.card_id == card.id, RevisionState.user_id == user.id)
        .first()
    )
    if state is None:
        state = RevisionState(card_id=card.id, user_id=user.id, next_review=date.today())
        db.add(state)
        db.flush()
    q = RATING_TO_Q[rating]
    updated = sm2_update(SM2State(n=state.n, ef=state.ef, interval_days=state.interval_days), q)
    state.n = updated.n
    state.ef = updated.ef
    state.interval_days = updated.interval_days
    state.next_review = updated.next_review
    state.last_rating = q
    db.add(RevisionHistory(card_id=card.id, user_id=user.id, rating=q, quality=q))
    db.commit()
    return {
        "n": state.n,
        "ef": state.ef,
        "interval_days": state.interval_days,
        "next_review": str(state.next_review),
    }


@router.get("/revision/today", response_model=list[RevisionCardOut])
def revision_today(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    rows = (
        db.query(RevisionState, Flashcard)
        .join(Flashcard, Flashcard.id == RevisionState.card_id)
        .filter(RevisionState.user_id == user.id, RevisionState.next_review <= today)
        .all()
    )
    out = []
    for state, card in rows:
        out.append(
            RevisionCardOut(
                card_id=card.id,
                question=card.question,
                answer=card.answer,
                difficulty=card.difficulty,
                support_status=card.support_status,
                next_review=state.next_review,
                n=state.n,
                ef=state.ef,
            )
        )
    return out


@router.get("/learning/mastery")
def mastery(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    states = db.query(RevisionState).filter(RevisionState.user_id == user.id).all()
    hist = db.query(RevisionHistory).filter(RevisionHistory.user_id == user.id).all()
    by_card: dict[str, list[int]] = {}
    for h in hist:
        by_card.setdefault(h.card_id, []).append(1 if h.quality >= 3 else 0)
    topics: dict[str, list[float]] = {}
    for st in states:
        card = db.get(Flashcard, st.card_id)
        if card is None:
            continue
        recents = by_card.get(st.card_id, [])[-8:]
        score = mastery_score(recents, st.interval_days, st.n)
        topics.setdefault(card.difficulty, []).append(score)
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).all()
    quiz_acc = sum(a.score for a in attempts) / len(attempts) if attempts else None
    return {
        "quiz_accuracy": quiz_acc,
        "mastery_by_difficulty": {k: (sum(v) / len(v) if v else 0) for k, v in topics.items()},
        "due_today": len(
            [s for s in states if s.next_review and s.next_review <= date.today()]
        ),
        "note": "Mastery is recency-weighted and interval-aware; it is not equal to quiz accuracy.",
    }
