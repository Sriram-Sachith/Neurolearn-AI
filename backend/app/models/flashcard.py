import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.user import utcnow


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    card_type: Mapped[str] = mapped_column(String(32), default="qa")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    source_pages: Mapped[str] = mapped_column(String(255), default="")
    support_status: Mapped[str] = mapped_column(String(32), default="unverified")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document = relationship("Document", back_populates="flashcards")
    evidence = relationship("CardEvidence", back_populates="card", cascade="all, delete-orphan")


class CardEvidence(Base):
    __tablename__ = "card_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id: Mapped[str] = mapped_column(ForeignKey("flashcards.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id"))
    support_status: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    passage: Mapped[str] = mapped_column(Text, default="")
    page_number: Mapped[int] = mapped_column(Integer, default=1)

    card = relationship("Flashcard", back_populates="evidence")
