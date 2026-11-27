import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada del proyecto con soporte para variables de entorno y .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- RUTAS ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_PATH: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"
    MODELS_DIR: Path = BASE_DIR / "models"
    INDEX_DIR: Path = BASE_DIR / "indexes"
    LLAMA_INDEX_DIR: Path = INDEX_DIR / "llama_index"

    # --- MODELO (CPU) ---
    MODEL_NAME: str = "qwen2.5-3b-instruct-q4_k_m.gguf"
    CPU_NUM_THREADS: int = Field(default_factory=lambda: os.cpu_count() or 4)
    MAX_TOKENS: int = 384

    # --- AGENTE & SEGURIDAD (E2) ---
    MAX_ITERATIONS: int = 8
    MAX_EXECUTION_TIME: float = 60.0
    MAX_QUERY_CHARS: int = 300
    MAX_TOOL_CALLS: dict[str, int] = Field(
        default_factory=lambda: {
            "calculator": 3,
            "verification": 5,
            "rag_search": 3,
            "plan_ciclo": 2,
            "plan_prereq": 2,
        }
    )
    USE_GRAMMAR: bool = True

    # --- OBSERVABILIDAD ---
    LOG_AUDIT_PATH: Path = LOG_DIR / "audit_traces.jsonl"

    # --- RAG ---
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    K_RECALL: int = 5

    @property
    def MODEL_PATH(self) -> Path:
        return self.MODELS_DIR / self.MODEL_NAME


settings = Settings()
Config = settings
