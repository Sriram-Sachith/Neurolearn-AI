from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), extra="ignore")

    app_name: str = "NeuroLearn AI"
    app_env: str = "development"
    secret_key: str = "dev-only-change-me"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./data/neurolearn.db"
    upload_dir: str = "./storage/uploads"
    max_upload_mb: int = 50

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_primary_model: str = "qwen2.5:3b-instruct"
    ollama_secondary_model: str = "gemma2:2b-instruct"
    llm_timeout_seconds: int = 180
    llm_temperature: float = 0.2
    llm_seed: int = 42
    llm_context_size: int = 4096

    vector_store: str = "numpy"
    embedding_backend: str = "tfidf"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"

    duplicate_cosine_threshold: float = 0.90
    evidence_support_threshold: float = 0.55
    evidence_partial_threshold: float = 0.35

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    demo_email: str = "demo@neurolearn.local"
    demo_password: str = "demo1234"
    demo_name: str = "Demo Student"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        if not p.is_absolute():
            p = ROOT_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def data_dir(self) -> Path:
        p = ROOT_DIR / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
