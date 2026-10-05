from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResult:
    data: dict[str, Any]
    raw_text: str
    latency_ms: float
    model_name: str
    prompt_chars: int
    output_chars: int
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str
    family: str

    @abstractmethod
    def generate(self, prompt: str, schema: dict[str, Any]) -> LLMResult:
        raise NotImplementedError

    def available(self) -> bool:
        return True
