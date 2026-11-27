import difflib
import os
import re
import unicodedata
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


def _infer_university_tag(filename: str) -> str:
    lower = filename.lower()
    if "uni" in lower or "plan de estudios" in lower:
        return "UNI"
    return "GENERAL"


def get_rag_tool() -> "LlamaIndexDynamicTool":
    print("📚 Inicializando RAG (LlamaIndex + Custom Parser)...", end=" ")

    embed_model = HuggingFaceEmbedding(model_name=Config.EMBEDDING_MODEL)
    Settings.embed_model = embed_model
    Settings.llm = None

    persist_dir = str(Config.LLAMA_INDEX_DIR)

    if not os.path.exists(persist_dir):
        print(f"\n(Indexando {Config.DATA_PATH} con lógica UNI)...")
        if not os.path.exists(Config.DATA_PATH):
            os.makedirs(Config.DATA_PATH, exist_ok=True)

        raw_docs = []
        for fn in os.listdir(Config.DATA_PATH):
            if fn.lower().endswith(".pdf"):
                path = os.path.join(Config.DATA_PATH, fn)
                tag = _infer_university_tag(fn)
                raw_docs.extend(parse_plan_estudio_uni_pdf(path, tag))

        llama_docs = [
            LlamaDocument(text=d.page_content, metadata=d.metadata) for d in raw_docs
        ]

        print(f"   -> Indexando {len(llama_docs)} fragmentos procesados...")
        index = VectorStoreIndex.from_documents(llama_docs, embed_model=embed_model)
        index.storage_context.persist(persist_dir)
    else:
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context, embed_model=embed_model)

    def _norm(s: str) -> str:
        return "".join(
            c
            for c in unicodedata.normalize("NFD", s.lower())
            if not unicodedata.combining(c)
        )

    # nombre de curso normalizado -> texto del chunk (evita depender solo del embedding)
    by_name = {}
    for node in index.docstore.docs.values():
        m = re.search(r"Asignatura:\s*(.+)", node.get_content())
        if m:
            by_name[_norm(m.group(1).strip())] = node.get_content()

    class LlamaIndexDynamicTool:
        def run(self, query: str) -> str:
            qn = _norm(query)
            # 1. Coincidencia exacta (el nombre más largo gana)
            hits = sorted(
                (n for n in by_name if re.search(rf"\b{re.escape(n)}\b", qn)),
                key=len,
            )
            if hits:
                return by_name[hits[-1]][:2500]

            # 2. Coincidencia difusa para errores ortográficos
            fuzzy = difflib.get_close_matches(qn.strip(), by_name.keys(), n=1, cutoff=0.75)
            if fuzzy:
                return by_name[fuzzy[0]][:2500]

            # 3. Recuperación semántica limpia (sin wrapper "Context information is below")
            keywords_list = [
                "lista",
                "todos",
                "malla",
                "plan",
                "electivos",
                "cursos de",
                "ciclo",
            ]
            dynamic_k = 8 if any(k in qn for k in keywords_list) else 3
            retriever = index.as_retriever(similarity_top_k=dynamic_k)
            nodes = retriever.retrieve(query)
            if not nodes:
                return "No se encontró información relevante en el plan de estudios."
            return "\n---\n".join(n.get_content() for n in nodes)[:2500]

    print("✅ Listo.")
    return LlamaIndexDynamicTool()
