# src/tools/rag_setup.py
import os
from src.config import Config
from src.tools.rag_loader_uni import parse_plan_estudio_uni_pdf
from src.tools.rag_index import build_load_index
from src.tools.rag_retriever import build_hybrid_retriever


def initialize_rag():
    """
    Función Singleton que prepara todo el sistema RAG.
    """
    # 1. Verificar si hay que indexar
    chroma_file = os.path.join(Config.CHROMA_DIR, "chroma.sqlite3")

    documents = []
    # Solo cargamos PDFs si no existe la DB para ahorrar RAM en arranques futuros
    if not os.path.exists(chroma_file):
        print("--- INDEXANDO PDFs (Solo primera vez) ---")
        for fn in os.listdir(Config.DATA_PATH):
            if fn.lower().endswith(".pdf"):
                path = os.path.join(Config.DATA_PATH, fn)
                tag = "UNI" if "UNI" in fn else "GENERAL"
                documents.extend(parse_plan_estudio_uni_pdf(path, tag))

    # 2. Obtener la DB (Crea o Carga)
    vectordb = build_load_index(documents)

    # 3. Crear el Retriever
    retriever = build_hybrid_retriever(vectordb, k=Config.K_RETRIEVAL)

    return retriever


# Instancia global para importar en el grafo
rag_engine = initialize_rag()
