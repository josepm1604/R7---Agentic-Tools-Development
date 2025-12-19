import os
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings,
    Document as LlamaDocument,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from src.config import Config
from src.tools.rag_loader_uni import parse_plan_estudio_uni_pdf


def get_rag_tool():
    print("📚 Inicializando RAG (LlamaIndex + Custom Parser)...", end=" ")

    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    Settings.embed_model = embed_model
    Settings.llm = None

    persist_dir = Config.LLAMA_INDEX_DIR

    if not os.path.exists(persist_dir):
        print(f"\n(Indexando {Config.DATA_PATH} con lógica UNI)...")
        if not os.path.exists(Config.DATA_PATH):
            os.makedirs(Config.DATA_PATH, exist_ok=True)

        raw_docs = []
        for fn in os.listdir(Config.DATA_PATH):
            if fn.lower().endswith(".pdf"):
                path = os.path.join(Config.DATA_PATH, fn)
                tag = "UNI" if "UNI" in fn else "GENERAL"
                raw_docs.extend(parse_plan_estudio_uni_pdf(path, tag))

        llama_docs = []
        for d in raw_docs:
            doc = LlamaDocument(text=d.page_content, metadata=d.metadata)
            llama_docs.append(doc)

        print(f"   -> Indexando {len(llama_docs)} fragmentos procesados...")
        index = VectorStoreIndex.from_documents(llama_docs, embed_model=embed_model)
        index.storage_context.persist(persist_dir)
    else:
        # CORRECCIÓN: Usar 'persist_dir' en lugar de 'persist_directory'
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context, embed_model=embed_model)

    class LlamaIndexDynamicTool:
        def run(self, query: str):
            query_lower = query.lower()
            keywords_list = [
                "lista",
                "todos",
                "malla",
                "plan",
                "electivos",
                "cursos de",
                "ciclo",
            ]

            if any(k in query_lower for k in keywords_list):
                dynamic_k = 15
                print(f"   [RAG Strategy] Detectado modo LISTA -> k={dynamic_k}")
            else:
                dynamic_k = 3
                print(f"   [RAG Strategy] Detectado modo DATO -> k={dynamic_k}")

            query_engine = index.as_query_engine(similarity_top_k=dynamic_k)
            response = query_engine.query(query)
            return str(response)

    print("✅ Listo.")
    return LlamaIndexDynamicTool()
