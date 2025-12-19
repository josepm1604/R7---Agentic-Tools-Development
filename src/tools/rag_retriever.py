# src/tools/rag_retriever.py
from langchain_community.retrievers import BM25Retriever


def build_hybrid_retriever(vectordb):
    base_retriever = vectordb.as_retriever()

    def retrieve_func(query: str, k: int = 4):  # <--- ACEPTA K DINÁMICO
        base_retriever.search_kwargs["k"] = k
        return base_retriever.invoke(query)

    return retrieve_func
