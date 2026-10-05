import time

from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_upload_pipeline_creates_notes_and_cards(client: TestClient):
    h = auth_header(client)
    text = (
        "Machine Learning. Supervised learning is a machine learning approach that learns from labelled training data. "
        "Unsupervised learning finds structure without labels. Classification assigns discrete classes. "
        "Regression predicts continuous values. Precision is the fraction of retrieved instances that are relevant. "
        "Recall is the fraction of relevant instances that were retrieved. "
        "A neural network consists of layers of units that transform representations. "
        "Overfitting happens when a model memorises training examples. "
        "Cross validation estimates generalisation by holding out folds. "
    ) * 3
    r = client.post(
        "/api/documents/upload",
        headers=h,
        files={"file": ("ml.txt", text.encode(), "text/plain")},
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]
    doc_id = r.json()["document_id"]
    status = None
    for _ in range(40):
        jr = client.get(f"/api/jobs/{job_id}", headers=h)
        status = jr.json()["status"]
        if status in {"completed", "failed"}:
            break
        time.sleep(0.15)
    assert status == "completed", jr.json()
    notes = client.get(f"/api/notes/{doc_id}", headers=h)
    cards = client.get(f"/api/flashcards/{doc_id}", headers=h)
    topics = client.get(f"/api/topics/{doc_id}", headers=h)
    assert notes.status_code == 200 and notes.json()
    assert cards.status_code == 200 and cards.json()
    assert topics.status_code == 200
    card0 = cards.json()[0]
    assert "support_status" in card0
    assert card0["support_status"] in {"supported", "partially_supported", "unverified"}
    today = client.get("/api/revision/today", headers=h)
    assert today.status_code == 200
    if today.json():
        cid = today.json()[0]["card_id"]
        sub = client.post("/api/revision/submit", headers=h, json={"card_id": cid, "rating": "good"})
        assert sub.status_code == 200
        assert "next_review" in sub.json()
