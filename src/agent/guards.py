from src.config import Config


class Guardrails:
    def __init__(self):
        self.tool_usage = {k: 0 for k in Config.MAX_TOOL_CALLS}

    def reset(self):
        self.tool_usage = {k: 0 for k in Config.MAX_TOOL_CALLS}

    def validate_input(self, query: str) -> tuple[bool, str]:
        """Valida la consulta del usuario."""
        if not query or not query.strip():
            return False, "La consulta no puede estar vacía."
        if len(query) > Config.MAX_QUERY_CHARS:
            return False, "Consulta demasiado larga."
        return True, "OK"

    def check_and_track(self, tool_name: str) -> bool:
        """Aplica límites de uso de herramientas y rechaza herramientas desconocidas."""
        if "rag" in tool_name:
            tool_name = "rag_search"
        if tool_name not in self.tool_usage:
            return False
        if self.tool_usage[tool_name] >= Config.MAX_TOOL_CALLS[tool_name]:
            return False
        self.tool_usage[tool_name] += 1
        return True
