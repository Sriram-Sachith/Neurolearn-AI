from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owned_document
from app.database.session import get_db
from app.evaluation.loader import load_experiment_bundle
from app.llm.generation.schemas import NotesPayload
from app.llm.generation.validated import generate_validated
from app.llm.prompts.templates import DOCUMENT_WRAP, NOTES_PROMPT
from app.llm.providers.registry import get_provider, list_providers
from app.models.chunk import Chunk
from app.models.model_run import ModelRun
from app.models.user import User
from app.schemas.api import SideBySideRequest

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/compare")
def compare(_user: User = Depends(get_current_user)):
    return load_experiment_bundle()


@router.get("/providers")
def providers(_user: User = Depends(get_current_user)):
    return list_providers()


@router.get("/runs")
def runs(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = db.query(ModelRun).order_by(ModelRun.created_at.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "model_name": r.model_name,
            "task": r.task,
            "experiment": r.experiment,
            "latency_ms": r.latency_ms,
            "memory_mb": r.memory_mb,
            "output_chars": r.output_chars,
            "tokens_per_sec": r.tokens_per_sec,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/side-by-side")
def side_by_side(body: SideBySideRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_document(body.document_id, user, db)
    chunks = db.query(Chunk).filter(Chunk.document_id == body.document_id).all()
    text = "\n\n".join(c.text for c in chunks)[:8000]
    prompt = NOTES_PROMPT + "\n" + DOCUMENT_WRAP.format(text=text)
    out = []
    for name in (body.model_a, body.model_b):
        provider = get_provider(name)
        notes, run = generate_validated(provider, prompt, {"task": "notes"}, NotesPayload)
        out.append(
            {
                "model": provider.name,
                "latency_ms": run.latency_ms,
                "output_chars": run.output_chars,
                "chapters": [c.model_dump() for c in notes.chapters],
            }
        )
    return {"document_id": body.document_id, "outputs": out}
