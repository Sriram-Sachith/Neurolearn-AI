"""Deterministic local provider used for tests and when Ollama is not installed.

This is not an external LLM API. It extracts study artefacts from the provided
source text using NLP heuristics so the pipeline can run fully offline.
"""

from __future__ import annotations

import re
import time
from typing import Any

from app.llm.providers.base import LLMProvider, LLMResult


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


class HeuristicProvider(LLMProvider):
    def __init__(self, name: str = "heuristic-extractor", family: str = "heuristic", stride: int = 1) -> None:
        self.name = name
        self.family = family
        self.stride = stride

    def generate(self, prompt: str, schema: dict[str, Any]) -> LLMResult:
        start = time.perf_counter()
        source = prompt
        if "BEGIN_DOCUMENT" in prompt:
            source = prompt.split("BEGIN_DOCUMENT", 1)[-1].split("END_DOCUMENT", 1)[0]
        sents = _sentences(source)[:: self.stride]
        task = schema.get("task", "notes")
        if task == "notes":
            data = self._notes(sents, source)
        elif task == "flashcards":
            data = self._cards(sents)
        elif task == "quiz":
            data = self._quiz(sents)
        elif task == "entailment":
            data = {"supported": "yes" if sents else "no", "rationale": "Overlap with source sentences."}
        else:
            data = {"items": []}
        elapsed = (time.perf_counter() - start) * 1000
        import json

        raw = json.dumps(data)
        return LLMResult(
            data=data,
            raw_text=raw,
            latency_ms=elapsed,
            model_name=self.name,
            prompt_chars=len(prompt),
            output_chars=len(raw),
        )

    def _notes(self, sents: list[str], source: str) -> dict[str, Any]:
        defs = [s for s in sents if re.search(r"\bis\b|\bare\b|defined as", s.lower())][:8]
        key_points = sents[:10]
        return {
            "chapters": [
                {
                    "title": "Overview",
                    "short_summary": " ".join(sents[:2]) if sents else "No extractable text.",
                    "detailed_summary": " ".join(sents[:8]),
                    "key_points": key_points[:8],
                    "definitions": defs,
                    "formulas": [s for s in sents if any(ch in s for ch in "=∑σμ")][:5],
                    "examples": [s for s in sents if "example" in s.lower()][:3],
                    "source_pages": [1],
                }
            ]
        }

    def _cards(self, sents: list[str]) -> dict[str, Any]:
        cards = []
        for i, s in enumerate(sents[:12]):
            m = re.search(r"(.+?)\s+(is|are|means)\s+(.+)", s, re.I)
            if m:
                q = f"What {m.group(2)} {m.group(1).strip()}?"
                a = m.group(3).strip().rstrip(".")
            else:
                q = f"Explain: {s[:80]}"
                a = s
            diff = ["easy", "medium", "hard"][i % 3]
            cards.append(
                {
                    "question": q,
                    "answer": a,
                    "topic": "General",
                    "difficulty": diff,
                    "card_type": "definition" if m else "conceptual",
                    "source_pages": [1],
                    "evidence_chunk_ids": [],
                }
            )
        return {"cards": cards}

    def _quiz(self, sents: list[str]) -> dict[str, Any]:
        items = []
        for i, s in enumerate(sents[:6]):
            words = [w for w in re.findall(r"[A-Za-z]{5,}", s)]
            if not words:
                continue
            answer = words[0]
            distractors = (words[1:] + ["process", "vector", "layer", "index"])[:3]
            items.append(
                {
                    "question": s.replace(answer, "_____", 1) if answer in s else f"Fill: {s[:60]}",
                    "qtype": "mcq" if i % 3 == 0 else ("fill" if i % 3 == 1 else "short"),
                    "options": [answer] + distractors,
                    "answer": answer,
                    "explanation": s,
                    "topic": "General",
                    "difficulty": ["easy", "medium", "hard"][i % 3],
                    "source_pages": [1],
                }
            )
        return {"items": items}
