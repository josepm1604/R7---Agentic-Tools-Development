from datetime import datetime
import json
import os
from typing import Any, Sequence
from src.config import Config


class AuditLogger:
    def log_audit(
        self,
        query: str,
        steps: Sequence[tuple[Any, str]],
        final_answer: str,
        latency: float,
    ) -> None:
        os.makedirs(Config.LOG_DIR, exist_ok=True)

        tool_trace = []
        for action, observation in steps:
            tool_trace.append(
                {
                    "tool": action.tool,
                    "tool_input": action.tool_input,
                    "log": action.log,
                    "observation": str(observation)[:200] + "...",
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
