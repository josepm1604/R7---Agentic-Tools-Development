class Guardrails:
    def __init__(self):
        # Configuraciones
        self.MAX_QUERY_LENGTH = 300
        self.FORBIDDEN_WORDS = ["ignore instructions", "system prompt", "drop table"]

    def validate_input(self, query: str):
        """
        Revisa la entrada ANTES de enviarla al Agente.
        Retorna (True, "") si es válido, o (False, "mensaje de error") si no.
        """
        # 1. Validar Tipo
        if not isinstance(query, str):
            return False, "La entrada debe ser texto."

        # 2. Validar Longitud (Ahorra tokens y memoria RAM)
        if len(query) > self.MAX_QUERY_LENGTH:
            return (
                False,
                f"La consulta es demasiado larga (Máx {self.MAX_QUERY_LENGTH} caracteres).",
            )

        # 3. Validar Longitud Mínima
        if len(query.strip()) < 2:
            return False, "La consulta es demasiado corta."

        # 4. Inyección de Prompt básica (Seguridad)
        for bad_word in self.FORBIDDEN_WORDS:
            if bad_word in query.lower():
                return False, "Contenido no permitido detectado."

        return True, "OK"

    # Nota: verify_limits lo quitamos por ahora porque LangGraph maneja
    # la recursión interna con su parámetro 'recursion_limit'.
