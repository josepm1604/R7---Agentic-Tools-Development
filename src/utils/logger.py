import json
import os
from datetime import datetime
from src.config import Config


class AuditLogger:
    def log_audit(self, query, steps, final_answer, latency):
        os.makedirs(Config.LOG_DIR, exist_ok=True)

        # Extraer trazas de las herramientas
        tool_trace = []
        for action, observation in steps:
            tool_trace.append(
                {
                    "tool": action.tool,
                    "tool_input": action.tool_input,
                    "log": action.log,  # El "Pensamiento" del modelo
                    "observation": str(observation)[:200]
                    + "...",  # Recortar para no llenar disco
                }
            )

        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "latency_seconds": round(latency, 2),
            "steps_count": len(steps),
            "trace": tool_trace,
            "final_response": final_answer,
        }

        with open(Config.LOG_AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
