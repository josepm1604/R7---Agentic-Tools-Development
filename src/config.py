import os


class Config:
    # --- RUTAS ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_PATH = os.path.join(BASE_DIR, "data")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    MODELS_DIR = os.path.join(BASE_DIR, "models")

    # Indices
    INDEX_DIR = os.path.join(BASE_DIR, "indexes")
    LLAMA_INDEX_DIR = os.path.join(INDEX_DIR, "llama_index")

    # --- MODELO (CPU) ---
    MODEL_NAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
    MODEL_PATH = os.path.join(MODELS_DIR, MODEL_NAME)
    CPU_NUM_THREADS = os.cpu_count() or 4

    # --- AGENTE & SEGURIDAD (E2) ---
    MAX_ITERATIONS = 8  # Evita bucles infinitos (ReAct loop)
    MAX_EXECUTION_TIME = 60  # Segundos máximos
    MAX_QUERY_CHARS = 300

    # Límites de Herramientas (Rate Limiting)
    MAX_TOOL_CALLS = {"calculator": 3, "verification": 5, "rag_search": 3}

    # --- OBSERVABILIDAD ---
    LOG_AUDIT_PATH = os.path.join(LOG_DIR, "audit_traces.jsonl")

    # --- RAG ---
    K_RECALL = 5
