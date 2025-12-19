from src.config import Config


class Guardrails:
    def __init__(self):
        self.tool_usage = {k: 0 for k in Config.MAX_TOOL_CALLS}

    def reset(self):
        self.tool_usage = {k: 0 for k in Config.MAX_TOOL_CALLS}

    def validate_input(self, query):
        """Valida la consulta del usuario."""
        if len(query) > Config.MAX_QUERY_CHARS:
            return False, "Consulta demasiado larga."
        return True, "OK"

    def check_and_track(self, tool_name):
        """Aplica límites de uso de herramientas (Requisito E2)."""
        clean_name = tool_name.replace("rag_search", "rag")
        if clean_name in self.tool_usage:
            if self.tool_usage[clean_name] >= Config.MAX_TOOL_CALLS[clean_name]:
                return False
            self.tool_usage[clean_name] += 1
        return True
