# src/tools/rag_index.py
import os
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.config import Config


def get_embeddings():
    # Usamos el modelo ligero definido en Config (all-MiniLM-L6-v2)
    # model_kwargs={'device': 'cpu'} asegura que corra en CPU
    return HuggingFaceEmbeddings(
        model_name=Config.EMBEDDING_MODEL_ID, model_kwargs={"device": "cpu"}
    )


def get_vectordb():
    """Devuelve la instancia de la DB lista para usar"""
    return Chroma(
        persist_directory=Config.CHROMA_DIR, embedding_function=get_embeddings()
    )


def build_load_index(documents: List):
    os.makedirs(Config.CHROMA_DIR, exist_ok=True)

    # Si ya existen datos, no re-indexamos para ahorrar tiempo
    if os.path.exists(os.path.join(Config.CHROMA_DIR, "chroma.sqlite3")):
        print(f"[VectorDB] Cargando índice existente desde {Config.CHROMA_DIR}...")
        return get_vectordb()

    print(f"[VectorDB] Creando nuevo índice con {len(documents)} documentos...")
    vectordb = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        persist_directory=Config.CHROMA_DIR,
    )
    return vectordb
