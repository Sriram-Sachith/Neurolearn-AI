import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    topic_name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keywords: Mapped[str] = mapped_column(Text, default="")
    user_renamed: Mapped[int] = mapped_column(Integer, default=0)

    document = relationship("Document", back_populates="topics")
