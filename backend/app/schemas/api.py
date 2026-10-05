from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: str
    filename: str
    original_name: str
    status: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: str
    document_id: str
    status: str
    progress: int
    error_message: str
    model_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteOut(BaseModel):
    id: str
    document_id: str
    title: str
    content: str
    kind: str
    source_pages: str
    model_name: str

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    chunk_id: str
    support_status: str
    score: float
    passage: str
    page_number: int

    model_config = {"from_attributes": True}


class FlashcardOut(BaseModel):
    id: str
    document_id: str
    question: str
    answer: str
    card_type: str
    difficulty: str
    source_pages: str
    support_status: str
    model_name: str
    evidence: list[EvidenceOut] = []

    model_config = {"from_attributes": True}


class TopicOut(BaseModel):
    id: str
    topic_name: str
    cluster_id: int | None
    keywords: str

    model_config = {"from_attributes": True}


class QuizItemOut(BaseModel):
    id: str
    question: str
    qtype: str
    options: list[str]
    explanation: str
    topic_name: str
    difficulty: str
    source_pages: str


class QuizOut(BaseModel):
    id: str
    title: str
    items: list[QuizItemOut]


class QuizSubmit(BaseModel):
    quiz_id: str
    answers: dict[str, str]


class RevisionSubmit(BaseModel):
    card_id: str
    rating: str  # again|hard|good|easy


class RevisionCardOut(BaseModel):
    card_id: str
    question: str
    answer: str
    difficulty: str
    support_status: str
    next_review: date | None
    n: int
    ef: float


class GenerateRequest(BaseModel):
    document_id: str
    model_name: str | None = None


class FlashcardUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    difficulty: str | None = None
    card_type: str | None = None


class SideBySideRequest(BaseModel):
    document_id: str
    model_a: str
    model_b: str


class ProviderOut(BaseModel):
    name: str
    family: str
    available: bool


class EmptyModel(BaseModel):
    extra: Any | None = None
