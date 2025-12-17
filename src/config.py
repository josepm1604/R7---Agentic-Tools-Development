import os


class Config:
    # Modelo PreEntrenado
    LLM_MODEL_ID = "google/flan-t5-base"

    # Modelo de Embeddings
    EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

    # Rutas
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_PATH = os.path.join(BASE_DIR, "data")
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    INDEX_DIR = os.path.join(BASE_DIR, "indexes")
    CHROMA_DIR = os.path.join(INDEX_DIR, "chroma")

    # Parámetros RAG
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150

    K_RETRIEVAL = 5
    K_FINAL = 3
    HYBRID_ALPHA = 0.55

    # Guardrails
    MAX_TOOL_CALLS_PER_QUERY = 8
    MAX_CALLS_FOR_TOOL = {
        "rag": 5,
        "calculator": 3,
        "verification": 2,
    }
    MAX_QUERY_CHARS = 400

    # Observabilidad
    LOG_JSONL_PATH = os.path.join(LOG_DIR, "agent_traces.jsonl")
    METRICS_JSONL_PATH = os.path.join(LOG_DIR, "metrics.jsonl")

    # CPU
    CPU_NUM_THREADS = 4
