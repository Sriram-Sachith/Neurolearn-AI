from __future__ import annotations

from app.core.config import get_settings
from app.llm.providers.base import LLMProvider
from app.llm.providers.heuristic import HeuristicProvider
from app.llm.providers.ollama import OllamaProvider

_REGISTRY: dict[str, LLMProvider] | None = None


def build_registry() -> dict[str, LLMProvider]:
    settings = get_settings()
    providers: dict[str, LLMProvider] = {
        "heuristic-extractor": HeuristicProvider(),
        "heuristic-alt": HeuristicProvider(name="heuristic-alt", family="heuristic-v2", stride=2),
        settings.ollama_primary_model: OllamaProvider(settings.ollama_primary_model, "qwen"),
        settings.ollama_secondary_model: OllamaProvider(settings.ollama_secondary_model, "gemma"),
    }
    return providers


def get_registry() -> dict[str, LLMProvider]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_registry()
    return _REGISTRY


def list_providers() -> list[dict[str, str | bool]]:
    out = []
    for p in get_registry().values():
        out.append({"name": p.name, "family": p.family, "available": p.available()})
    return out


def get_provider(name: str | None) -> LLMProvider:
    registry = get_registry()
    if name and name in registry:
        provider = registry[name]
        if provider.available():
            return provider
    # Prefer a live Ollama model, else heuristic fallback.
    for p in registry.values():
        if isinstance(p, OllamaProvider) and p.available():
            return p
    return registry["heuristic-extractor"]
