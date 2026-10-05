from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.note import Note
from app.models.quiz import QuizAttempt
from app.models.revision import RevisionHistory, RevisionState
from app.models.user import User
from collections import defaultdict
from datetime import date, timedelta

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    doc_ids = [d.id for d in docs]
    notes_n = db.query(Note).filter(Note.document_id.in_(doc_ids)).count() if doc_ids else 0
    cards_n = db.query(Flashcard).filter(Flashcard.document_id.in_(doc_ids)).count() if doc_ids else 0
    due = (
        db.query(RevisionState)
        .filter(RevisionState.user_id == user.id, RevisionState.next_review <= date.today())
        .count()
    )
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).all()
    weak = []
    unsupported = (
        db.query(Flashcard)
        .filter(Flashcard.document_id.in_(doc_ids), Flashcard.support_status == "unverified")
        .limit(8)
        .all()
        if doc_ids
        else []
    )
    for c in unsupported:
        weak.append({"id": c.id, "label": c.question[:80], "reason": "unverified evidence"})
    hist = db.query(RevisionHistory).filter(RevisionHistory.user_id == user.id).all()
    by_day: dict[str, int] = defaultdict(int)
    for h in hist:
        if h.created_at:
            by_day[h.created_at.date().isoformat()] += 1
    weekly = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        weekly.append({"day": d, "reviews": by_day.get(d, 0)})
    return {
        "documents": len(docs),
        "notes": notes_n,
        "flashcards": cards_n,
        "due_today": due,
        "quiz_attempts": len(attempts),
        "last_document": docs[0].original_name if docs else None,
        "weak_points": weak,
        "weekly_activity": weekly,
        "recent_documents": [
            {"id": d.id, "name": d.original_name, "status": d.status} for d in docs[:8]
        ],
    }
