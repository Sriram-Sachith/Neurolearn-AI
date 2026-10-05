from __future__ import annotations

from pydantic import BaseModel, Field


class NoteChapter(BaseModel):
    title: str
    short_summary: str
    detailed_summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    definitions: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    source_pages: list[int] = Field(default_factory=list)


class NotesPayload(BaseModel):
    chapters: list[NoteChapter]


class FlashcardPayloadItem(BaseModel):
    question: str
    answer: str
    topic: str = "General"
    difficulty: str = "medium"
    card_type: str = "qa"
    source_pages: list[int] = Field(default_factory=list)
    evidence_chunk_ids: list[str] = Field(default_factory=list)


class FlashcardsPayload(BaseModel):
    cards: list[FlashcardPayloadItem]


class QuizPayloadItem(BaseModel):
    question: str
    qtype: str = "mcq"
    options: list[str] = Field(default_factory=list)
    answer: str
    explanation: str = ""
    topic: str = "General"
    difficulty: str = "medium"
    source_pages: list[int] = Field(default_factory=list)


class QuizPayload(BaseModel):
    items: list[QuizPayloadItem]
