import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.session import configure_engine, init_db
from app.main import app
from app.ml.embeddings.encoder import reset_embedding_backend
from app.services.bootstrap import ensure_demo_user


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    reset_embedding_backend()
    get_settings.cache_clear()
    configure_engine(f"sqlite:///{db_path}")
    init_db()
    from app.database.session import SessionLocal

    db = SessionLocal()
    ensure_demo_user(db)
    db.close()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def auth_header(client: TestClient) -> dict[str, str]:
    settings = get_settings()
    r = client.post("/api/auth/login", json={"email": settings.demo_email, "password": settings.demo_password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
