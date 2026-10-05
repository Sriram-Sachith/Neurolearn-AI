from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ROOT_DIR, get_settings
from app.database.base import Base

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def configure_engine(url: str | None = None) -> Engine:
    global engine, SessionLocal
    settings = get_settings()
    db_url = url or settings.database_url
    if db_url.startswith("sqlite:///./"):
        rel = db_url.replace("sqlite:///./", "")
        db_url = f"sqlite:///{(ROOT_DIR / rel).resolve()}"
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, future=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    if db_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        configure_engine()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    if engine is None:
        configure_engine()
    assert engine is not None
    Base.metadata.create_all(bind=engine)
