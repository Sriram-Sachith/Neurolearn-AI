from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import auth_header


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_demo(client: TestClient):
    h = auth_header(client)
    assert "Bearer" in h["Authorization"]


def test_register_and_isolation(client: TestClient):
    a = client.post("/api/auth/register", json={"name": "A", "email": "a@x.com", "password": "secret1"})
    b = client.post("/api/auth/register", json={"name": "B", "email": "b@x.com", "password": "secret1"})
    assert a.status_code == 200 and b.status_code == 200
    ha = {"Authorization": f"Bearer {a.json()['access_token']}"}
    hb = {"Authorization": f"Bearer {b.json()['access_token']}"}
    up = client.post(
        "/api/documents/upload",
        headers=ha,
        files={"file": ("lec.txt", b"Supervised learning uses labelled data.", "text/plain")},
    )
    assert up.status_code == 200
    docs_b = client.get("/api/documents", headers=hb)
    assert docs_b.json() == []
    job_id = up.json()["id"]
    steal = client.get(f"/api/jobs/{job_id}", headers=hb)
    assert steal.status_code == 404
