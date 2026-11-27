import difflib
import os
import re
import unicodedata
from collections import defaultdict
from typing import Any

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

_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "en", "y", "o",
    "que", "cuales", "cuantos", "son", "tiene", "hay", "para", "por", "con",
    "curso", "cursos", "asignatura", "plan", "estudios",
}


def _infer_university_tag(filename: str) -> str:
    lower = filename.lower()
    if "uni" in lower or "plan de estudios" in lower:
        return "UNI"
    return "GENERAL"


def _norm(s: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s.lower())
        if not unicodedata.combining(c)
    )


def _tokenize(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _norm(s)) if t not in _STOPWORDS]


class LlamaIndexDynamicTool:
    """Herramienta RAG++ con coincidencia exacta, difusa e híbrida (Vector + Léxica RRF)."""

    def __init__(self, index: VectorStoreIndex, default_fuzzy_cutoff: float = 0.75) -> None:
        self.index = index
        self.default_fuzzy_cutoff = default_fuzzy_cutoff
        self.by_name: dict[str, str] = {}
        self.docs_tokens: list[tuple[str, set[str], str]] = []

        for node in index.docstore.docs.values():
            content = node.get_content()
            m = re.search(r"Asignatura:\s*(.+)", content)
            if m:
                self.by_name[_norm(m.group(1).strip())] = content
            self.docs_tokens.append((node.node_id, set(_tokenize(content)), content))

    def _lexical_rank(self, query: str, top_k: int) -> list[tuple[str, str]]:
        q_tokens = set(_tokenize(query))
        if not q_tokens:
            return []
        scored: list[tuple[float, str, str]] = []
        for node_id, doc_toks, content in self.docs_tokens:
            overlap = len(q_tokens & doc_toks)
            if overlap > 0:
                score = overlap / (len(q_tokens) ** 0.5 * max(len(doc_toks), 1) ** 0.25)
                scored.append((score, node_id, content))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(nid, content) for _, nid, content in scored[:top_k]]

    def retrieve_hybrid(
        self,
        query: str,
        k: int,
        use_hybrid_rrf: bool = True,
    ) -> list[str]:
        retriever = self.index.as_retriever(similarity_top_k=k * 2 if use_hybrid_rrf else k)
        vec_nodes = retriever.retrieve(query)

        if not use_hybrid_rrf:
            return [n.get_content() for n in vec_nodes[:k]]

        rrf_scores: dict[str, float] = defaultdict(float)
        contents: dict[str, str] = {}

        for rank, node in enumerate(vec_nodes, start=1):
            nid = node.node.node_id
            rrf_scores[nid] += 1.0 / (60 + rank)
            contents[nid] = node.get_content()

        for rank, (nid, content) in enumerate(self._lexical_rank(query, top_k=k * 2), start=1):
            rrf_scores[nid] += 1.0 / (60 + rank)
            contents[nid] = content

        ranked_ids = sorted(rrf_scores, key=lambda nid: rrf_scores[nid], reverse=True)[:k]
        return [contents[nid] for nid in ranked_ids]

    def run(
        self,
        query: str,
        fuzzy_cutoff: float | None = None,
        k_override: int | None = None,
        use_hybrid_rrf: bool = True,
    ) -> str:
        qn = _norm(query)
        cutoff = self.default_fuzzy_cutoff if fuzzy_cutoff is None else fuzzy_cutoff

        # 1. Coincidencia exacta por nombre de curso (gana el más largo)
        hits = sorted(
            (n for n in self.by_name if re.search(rf"\b{re.escape(n)}\b", qn)),
            key=len,
        )
        if hits:
            return self.by_name[hits[-1]][:2500]

        # 2. Coincidencia difusa para errores ortográficos
        fuzzy = difflib.get_close_matches(qn.strip(), self.by_name.keys(), n=1, cutoff=cutoff)
        if fuzzy:
            return self.by_name[fuzzy[0]][:2500]

        # 3. Recuperación híbrida (Vector + Léxica con Reciprocal Rank Fusion)
        keywords_list = [
            "lista",
            "todos",
            "malla",
            "plan",
            "electivos",
            "cursos de",
            "ciclo",
        ]
        dynamic_k = k_override if k_override is not None else (
            8 if any(k in qn for k in keywords_list) else 3
        )
        chunks = self.retrieve_hybrid(query, k=dynamic_k, use_hybrid_rrf=use_hybrid_rrf)
        if not chunks:
            return "No se encontró información relevante en el plan de estudios."
        return "\n---\n".join(chunks)[:2500]


def get_rag_tool() -> LlamaIndexDynamicTool:
    print("📚 Inicializando RAG (LlamaIndex + Custom Parser)...", end=" ")

    embed_model = HuggingFaceEmbedding(model_name=Config.EMBEDDING_MODEL)
    Settings.embed_model = embed_model
    Settings.llm = None

    persist_dir = str(Config.LLAMA_INDEX_DIR)

    if not os.path.exists(persist_dir):
        print(f"\n(Indexando {Config.DATA_PATH} con lógica UNI)...")
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

    print("✅ Listo.")
    return LlamaIndexDynamicTool(index)
