import os
import sys
from langchain_community.llms import LlamaCpp
from src.config import Config


def load_llm():
    """Carga el modelo optimizado para CPU."""
    if not os.path.exists(Config.MODEL_PATH):
        print(f"ERROR CRÍTICO: No se encuentra el modelo en {Config.MODEL_PATH}")
        raise FileNotFoundError(f"No existe el modelo en: {Config.MODEL_PATH}")

    return LlamaCpp(
        model_path=Config.MODEL_PATH,
        temperature=0.1,
        max_tokens=512,
        n_ctx=4096,
        n_threads=Config.CPU_NUM_THREADS,
        verbose=False,
        repetition_penalty=1.2,
        # CORRECCIÓN: Eliminamos 'stop' aquí para pasarlo dinámicamente en el agente
    )
