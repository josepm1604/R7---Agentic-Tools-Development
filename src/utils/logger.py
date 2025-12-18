import json
import os
from datetime import datetime
from src.config import Config


class AgentLogger:
    def __init__(self):
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        self.log_file = os.path.join(Config.LOG_DIR, "execution.jsonl")

    def log_interaction(
        self, query: str, final_state: dict, latency: float, error: str = None
    ):
        """
        Registra la interacción extrayendo métricas clave del Estado de LangGraph.
        """

        # 1. Extraer decisión de herramienta (Trace)
        tool_used = final_state.get("tool_decision", "unknown")

        # 2. Calcular Hit Rate (Solo si se usó RAG)
        # ¿Encontramos documentos?
        docs = final_state.get("documents", [])
        retrieval_hit = len(docs) > 0 if tool_used in ["rag", "retrieve"] else None

        # 3. Construir la entrada de log
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "tool_selected": tool_used,
            "retrieval_hit": retrieval_hit,  # Métrica clave para E2
            "doc_count": len(docs) if docs else 0,
            "final_response": final_state.get("generation", str(error)),
            "latency_seconds": round(latency, 4),
            "status": "ERROR" if error else "SUCCESS",
        }

        # 4. Guardar (Append)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ Error al guardar log: {e}")
