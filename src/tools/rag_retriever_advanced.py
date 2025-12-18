# src/tools/rag_retriever_advanced.py
from langchain_classic.chains.query_constructor.base import AttributeInfo
from langchain_classic.retrievers.self_query.base import SelfQueryRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.config import Config


def build_advanced_retriever(vectordb, llm):
    """
    Crea un SelfQueryRetriever que entiende la estructura de tu PDF.
    """

    # 1. Describimos la Metadata para que el LLM sepa qué filtrar
    # Esto debe coincidir EXACTO con lo que guardamos en rag_loader_uni.py
    metadata_field_info = [
        AttributeInfo(
            name="ciclo",
            description="El ciclo académico del curso. Valores: 'Primer ciclo', 'Segundo ciclo', ... 'Décimo ciclo', 'Electivos'.",
            type="string",
        ),
        AttributeInfo(
            name="tipo",
            description="El tipo de curso. Valores: 'Obligatorio', 'Electivo de Especialidad', 'Electivo Complementario'.",
            type="string",
        ),
        AttributeInfo(
            name="creditos",
            description="El número de créditos del curso (ej: 4, 5).",
            type="integer",
        ),
    ]

    document_content_description = (
        "Resumen de cursos universitarios del plan de estudios UNI"
    )

    # 2. Creamos el Retriever Inteligente
    retriever = SelfQueryRetriever.from_llm(
        llm,
        vectordb,
        document_content_description,
        metadata_field_info,
        verbose=True,  # Para ver en consola cómo crea los filtros
        enable_limit=True,  # Permite al LLM decidir cuántos docs traer
    )

    return retriever
