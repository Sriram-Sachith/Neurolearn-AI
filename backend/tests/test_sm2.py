from datetime import date

from app.services.learning_service import SM2State, mastery_score, sm2_update


def test_again_resets():
    s = SM2State(n=4, ef=2.5, interval_days=10)
    out = sm2_update(s, 1, today=date(2026, 1, 1))
    assert out.n == 0
    assert out.interval_days == 1
    assert str(out.next_review) == "2026-01-02"


def test_good_first_reviews():
    s0 = sm2_update(SM2State(), 4, today=date(2026, 1, 1))
    assert s0.n == 1 and s0.interval_days == 1
    s1 = sm2_update(s0, 4, today=date(2026, 1, 2))
    assert s1.n == 2 and s1.interval_days == 6
    s2 = sm2_update(s1, 5, today=date(2026, 1, 8))
    assert s2.n == 3
    assert s2.interval_days >= 6
    assert s2.ef >= 2.5


def test_ef_floor():
    s = SM2State(n=2, ef=1.31, interval_days=3)
    out = sm2_update(s, 1, today=date(2026, 1, 1))
    assert out.ef >= 1.3


def test_mastery_not_equal_to_single_correct():
    one = mastery_score([1], interval_days=1, n_reviews=1)
    mature = mastery_score([1, 1, 1, 1, 1], interval_days=21, n_reviews=8)
    assert one < mature
    assert 0 <= one <= 1
