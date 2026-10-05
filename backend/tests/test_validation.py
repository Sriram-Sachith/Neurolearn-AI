from app.services.validation_service import classify_support, duplicate_questions


def test_duplicate_near_identical():
    qs = [
        "What is supervised learning?",
        "What is supervised learning?",
        "Define photosynthesis.",
    ]
    drop = duplicate_questions(qs, threshold=0.9)
    assert 1 in drop
    assert 2 not in drop


def test_support_thresholds():
    assert classify_support(0.9) == "supported"
    assert classify_support(0.4) == "partially_supported"
    assert classify_support(0.1) == "unverified"
