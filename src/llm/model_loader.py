import os
import sys
from langchain_community.llms import LlamaCpp
from src.config import Config


def load_llm():
    """
    Carga el modelo Qwen2.5 en formato GGUF usando llama.cpp.
    Optimizado para inferencia rápida en CPU con baja memoria (4GB RAM).
    """
    model_path = Config.MODEL_PATH

    # Verificación de seguridad
    if not os.path.exists(model_path):
        print(f"ERROR CRÍTICO: No se encontró el modelo en {model_path}")
        print("1. Crea una carpeta llamada 'models' en la raíz del proyecto.")
        print(f"2. Descarga el archivo '{Config.MODEL_NAME}' y guárdalo ahí.")
        sys.exit(1)

    print(f"🔄 Cargando modelo GGUF desde: {model_path} ...")

    # Instancia de LlamaCpp compatible con LangChain
    llm = LlamaCpp(
        model_path=model_path,
        temperature=0.1,  # Baja temperatura para seguir instrucciones (Agents)
        max_tokens=512,  # Longitud máxima de respuesta
        n_ctx=2048,  # Ventana de contexto (input + output)
        top_p=0.9,
        verbose=True,  # Muestra logs internos de llama.cpp (útil para debug)
        n_threads=Config.CPU_NUM_THREADS,  # Hilos de CPU
        n_gpu_layers=0,  # 0 = Todo en CPU (Ideal para tu setup sin GPU dedicada)
        f16_kv=True,  # Optimización de memoria
    )

    print("✅ Modelo cargado exitosamente en CPU.")
    return llm
