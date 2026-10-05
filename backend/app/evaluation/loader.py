"""Evaluation dashboard reads *files on disk* — never invented numbers."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import ROOT_DIR


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_experiment_bundle() -> dict:
    experiments = ROOT_DIR / "experiments"
    eval_dir = ROOT_DIR / "benchmark" / "evaluation_results"
    files = {
        "llm_comparison": experiments / "llm_comparison" / "results.json",
        "retrieval": experiments / "retrieval" / "results.json",
        "flashcard_quality": experiments / "flashcard_quality" / "results.json",
        "performance": experiments / "performance" / "results.json",
        "clustering": experiments / "llm_comparison" / "clustering.json",
        "hallucination": experiments / "retrieval" / "hallucination.json",
        "manifest": eval_dir / "manifest.json",
    }
    out: dict = {"status": "ok", "experiments": {}, "missing": []}
    for key, path in files.items():
        data = _load_json(path)
        if data is None:
            out["missing"].append(str(path.relative_to(ROOT_DIR)))
        else:
            out["experiments"][key] = data
    return out
