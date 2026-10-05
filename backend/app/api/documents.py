from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned_document
from app.core.config import get_settings
from app.database import session as db_session
from app.database.session import get_db
from app.models.document import Document
from app.models.job import ProcessingJob
from app.models.user import User
from app.schemas.api import DocumentOut, JobOut
from app.services.file_validation import FileValidationError, validate_upload
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _run_job(job_id: str) -> None:
    if db_session.SessionLocal is None:
        db_session.configure_engine()
    db = db_session.SessionLocal()
    try:
        run_pipeline(db, job_id)
    finally:
        db.close()


@router.post("/upload", response_model=JobOut)
async def upload(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    model_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    raw = await file.read()
    try:
        validated = validate_upload(file.filename or "upload.bin", raw, file.content_type)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = get_settings()
    dest_dir = settings.upload_path / user.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / validated.filename
    dest.write_bytes(validated.content)

    doc = Document(
        user_id=user.id,
        filename=validated.filename,
        original_name=file.filename or validated.filename,
        mime_type=validated.mime,
        size_bytes=validated.size,
        status="queued",
        storage_path=str(dest),
    )
    db.add(doc)
    db.flush()
    job = ProcessingJob(document_id=doc.id, user_id=user.id, status="queued", progress=0, model_name=model_name or "")
    db.add(job)
    db.commit()
    db.refresh(job)
    background.add_task(_run_job, job.id)
    return job


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Document]:
    return db.query(Document).filter(Document.user_id == user.id).order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Document:
    return owned_document(document_id, user, db)
