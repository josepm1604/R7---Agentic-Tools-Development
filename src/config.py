import os


class Config:
    # --- RUTAS ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_PATH = os.path.join(BASE_DIR, "data")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    MODELS_DIR = os.path.join(BASE_DIR, "models")  # Carpeta para el GGUF

    INDEX_DIR = os.path.join(BASE_DIR, "indexes")
    CHROMA_DIR = os.path.join(INDEX_DIR, "chroma")

    # --- MODELO LLM (GGUF para CPU) ---
    # Asegúrate de descargar este archivo y ponerlo en la carpeta 'models'
    MODEL_NAME = "qwen2.5-1.5b-instruct-q2_k.gguf"
    MODEL_PATH = os.path.join(MODELS_DIR, MODEL_NAME)

    # --- EMBEDDINGS ---
    # Este es ligero y funciona bien en CPU, lo mantenemos
    EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

    # --- PARÁMETROS RAG ---
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 150
    K_RETRIEVAL = 5
    K_FINAL = 3
    HYBRID_ALPHA = 0.55

    # --- GUARDRAILS ---
    MAX_TOOL_CALLS_PER_QUERY = 8
    MAX_CALLS_FOR_TOOL = {
        "rag": 5,
        "calculator": 3,
        "verification": 2,
    }
    MAX_QUERY_CHARS = 400

    # --- OBSERVABILIDAD ---
    LOG_JSONL_PATH = os.path.join(LOG_DIR, "agent_traces.jsonl")
    METRICS_JSONL_PATH = os.path.join(LOG_DIR, "metrics.jsonl")

    # --- CPU OPTIMIZATION ---
    # Ajusta esto según los núcleos físicos de tu máquina (deja 1 o 2 libres para el OS)
    CPU_NUM_THREADS = 4
