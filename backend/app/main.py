from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, content, dashboard, documents, evaluation, jobs, learning
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database import session as db_session
from app.services.bootstrap import ensure_demo_user

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(content.router)
app.include_router(learning.router)
app.include_router(evaluation.router)
app.include_router(dashboard.router)


@app.on_event("startup")
def startup() -> None:
    settings.data_dir
    settings.upload_path
    db_session.init_db()
    db = db_session.SessionLocal()
    try:
        ensure_demo_user(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
