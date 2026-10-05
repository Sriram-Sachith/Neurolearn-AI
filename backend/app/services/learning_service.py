"""SM-2 spaced repetition and topic mastery estimates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


RATING_TO_Q = {
    "again": 1,
    "hard": 3,
    "good": 4,
    "easy": 5,
}


@dataclass
class SM2State:
    n: int = 0
    ef: float = 2.5
    interval_days: int = 0
    next_review: date | None = None


def sm2_update(state: SM2State, quality: int, today: date | None = None) -> SM2State:
    today = today or date.today()
    q = quality
    ef = state.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ef = max(1.3, ef)
    if q < 3:
        n = 0
        interval = 1
    else:
        if state.n == 0:
            interval = 1
        elif state.n == 1:
            interval = 6
        else:
            interval = int(round(state.interval_days * ef))
            interval = max(1, interval)
        n = state.n + 1
    return SM2State(n=n, ef=ef, interval_days=interval, next_review=today + timedelta(days=interval))


def mastery_score(recent_correct: list[int], interval_days: int, n_reviews: int) -> float:
    """Separate from raw quiz accuracy: recency-weighted accuracy * attempt confidence * interval maturity."""
    if not recent_correct:
        return 0.0
    weights = [0.5 ** i for i in range(len(recent_correct))][::-1]
    acc = sum(w * c for w, c in zip(weights, recent_correct)) / sum(weights)
    attempt_factor = min(1.0, n_reviews / 5.0)
    maturity = min(1.0, interval_days / 21.0)
    return round(float(acc * (0.5 + 0.3 * attempt_factor + 0.2 * maturity)), 4)
