import os
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.config import Config


def get_vectordb(persist_dir: str):
    embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL_ID)
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)


def build_load_index(documents: List, persist_dir: str):
    os.makedirs(persist_dir, exist_ok=True)

    if os.path.exists(os.path.join(persist_dir, "chroma.sqlite3")):
        print(f"[VectorDB] Cargando índice existente desde {persist_dir}...")
        return get_vectordb(persist_dir)

    print(f"[VectorDB] Creando nuevo índice en {persist_dir}...")
    embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL_ID)

    vectordb = Chroma.from_documents(
        documents=documents, embedding=embeddings, persist_directory=persist_dir
    )

    return vectordb
