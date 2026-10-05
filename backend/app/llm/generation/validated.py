from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.providers.base import LLMProvider, LLMResult

T = TypeVar("T", bound=BaseModel)


def generate_validated(
    provider: LLMProvider,
    prompt: str,
    schema_hint: dict,
    model_cls: type[T],
    retries: int = 2,
) -> tuple[T, LLMResult]:
    last_error = "unknown"
    last_result: LLMResult | None = None
    for attempt in range(retries + 1):
        extra = "" if attempt == 0 else f"\nPrevious output was invalid JSON ({last_error}). Return schema-valid JSON only."
        result = provider.generate(prompt + extra, schema_hint)
        last_result = result
        try:
            parsed = model_cls.model_validate(result.data)
            return parsed, result
        except ValidationError as exc:
            last_error = str(exc)
            # try parsing raw_text
            try:
                parsed = model_cls.model_validate_json(result.raw_text)
                return parsed, result
            except Exception:
                continue
    raise ValueError(f"LLM output failed schema validation: {last_error}")
