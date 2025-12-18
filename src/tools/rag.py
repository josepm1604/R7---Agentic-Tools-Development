import os, re
from src.tools.base import BaseTool
from src.config import Config
from src.tools.rag_loader_uni import parse_plan_estudio_uni_pdf
from src.tools.rag_index import build_load_index
from src.tools.rag_retriever import build_hybrid_retriever


class RAGTool(BaseTool):
    def __init__(self):
        super().__init__(name="rag")
        self.data_dir = Config.DATA_PATH
        self.persist_dir = getattr(Config, "CHROMA_DIR", "data/chroma_index")

        docs = []
        for fn in os.listdir(self.data_dir):
            if fn.lower().endswith(".pdf"):
                path = os.path.join(self.data_dir, fn)
                tag = "UNI" if "2018" in fn or "UNI" in fn else "GENERAL"
                docs.extend(parse_plan_estudio_uni_pdf(path, tag))

        self.documents = docs
        self.vectordb = build_load_index(self.documents, self.persist_dir)
        self.retriever = build_hybrid_retriever(self.documents, self.vectordb, k=30)

    def extract_code(self, q: str):
        m = re.search(r"\b([A-Za-z]{2,4}[0-9A-Za-z]{2,4})\b", q or "")
        return m.group(1).upper() if m else None

    def run(self, query: str, k=30):
        code = self.extract_code(query)
        if code:
            hits = [d for d in self.documents if d.metadata.get("codigo") == code]
            if hits:
                return "\n".join([h.page_content for h in hits[:k]])

        q = (query or "").lower()

        results = self.retriever(query)
        return "\n\n".join([r.page_content for r in results[:k]])
