from langchain_community.retrievers import BM25Retriever


def build_hybrid_retriever(documents, vectordb, k=5):
    # 1. Crear BM25
    bm25 = BM25Retriever.from_documents(documents)
    bm25.k = k

    # 2. Crear Dense Retriever
    dense = vectordb.as_retriever(search_kwargs={"k": k})

    # 3. Definir la función de búsqueda manual (Closure)
    def retrieve(query: str):
        # NOTA: Usamos .invoke() en lugar de .get_relevant_documents()
        # para compatibilidad con versiones nuevas
        dense_docs = dense.invoke(query)
        bm25_docs = bm25.invoke(query)

        # “RRF” simple (Reciprocal Rank Fusion)
        scores = {}

        def add(docs, weight):
            for rank, d in enumerate(docs, start=1):
                # Clave única para evitar duplicados
                # (Usamos source + page + primeros 60 chars)
                key = (
                    d.metadata.get("source", "unknown"),
                    d.metadata.get("page", 0),
                    d.page_content[:60],
                )

                # Si no existe, lo inicializamos
                if key not in scores:
                    scores[key] = {"doc": d, "score": 0.0}

                # Fórmula RRF: peso * (1 / (rank + constante))
                scores[key]["score"] += weight * (1.0 / (rank + 60))

        # Pesos (Puedes ajustarlos)
        add(dense_docs, 0.5)  # Semántico
        add(bm25_docs, 0.5)  # Palabras Clave

        # Ordenar por puntaje final descendente
        ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

        # Devolver solo los documentos top-k
        return [x["doc"] for x in ranked[:k]]

    # Devolvemos la FUNCIÓN, no un objeto
    return retrieve
