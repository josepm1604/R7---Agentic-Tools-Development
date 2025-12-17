MAXIMO_LLAMADA_HERRAMIENTAS = {"calculator": 3, "rag": 5}


class Guardrails:
    def __init__(self):
        self.usage = {k: 0 for k in MAXIMO_LLAMADA_HERRAMIENTAS}

    def validate(self, tool_name, params):
        if not isinstance(params, str) or len(params) > 300:
            raise ValueError("Input Invalido")
        return True

    def verify_limits(self, tool_name):
        if self.usage[tool_name] >= MAXIMO_LLAMADA_HERRAMIENTAS[tool_name]:
            raise Exception(f"Limite alcanzado para {tool_name}")
        self.usage[tool_name] += 1
        return True
