# src/tools/rag_retriever.py
from langchain_community.retrievers import BM25Retriever


def build_hybrid_retriever(vectordb, k=4):
    """
    Combina búsqueda semántica (Chroma) con palabras clave (BM25).
    Ideal para cuando el usuario busca códigos exactos 'CC311'.
    """

    # 1. Configurar Dense Retriever (Semántico)
    dense_retriever = vectordb.as_retriever(search_kwargs={"k": k})

    # NOTA: BM25 requiere los documentos en memoria.
    # Para optimizar en E2, intentaremos usar solo Dense si hay poca RAM,
    # pero si puedes cargar los docs, el híbrido es mejor.

    def retrieve_func(query: str):
        # Búsqueda Vectorial (Semántica)
        docs = dense_retriever.invoke(query)
        return docs

    # Si quisieras reactivar el híbrido completo, necesitarías pasarle
    # la lista de 'documents' raw a esta función, pero consume RAM.
    # Para 4GB RAM, te recomiendo empezar solo con Dense (Chroma).

    return retrieve_func
