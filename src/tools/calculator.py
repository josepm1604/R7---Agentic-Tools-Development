import re
from src.tools.base import BaseTool


class CalculatorTool(BaseTool):
    def __init__(self):
        super().__init__(name="calculator")

    def run(self, input_text: str) -> str:
        # 1. Limpieza previa
        # Reemplazar palabras comunes por operadores si el usuario escribe natural
        # Ej: "cuanto es 5 por 5" -> "5 * 5"
        text_clean = input_text.lower()
        text_clean = text_clean.replace(" por ", "*").replace(" x ", "*")
        text_clean = text_clean.replace(" entre ", "/").replace(" dividido ", "/")
        text_clean = text_clean.replace(" mas ", "+").replace(" más ", "+")
        text_clean = text_clean.replace(" menos ", "-")

        # 2. Regex mejorado: Busca secuencias de números y operadores
        matches = re.findall(r"[\d\+\-\*\/\.\(\)\s]+", text_clean)

        # Filtramos matches vacíos
        valid_exprs = [m.strip() for m in matches if any(char.isdigit() for char in m)]

        if not valid_exprs:
            return "No se encontraron números para calcular."

        # Tomamos la expresión más larga encontrada
        expr = max(valid_exprs, key=len)

        # 3. GUARDRAIL DE LÓGICA:
        # Si la expresión no tiene ningún operador matemático, es solo un número (ej: una fecha)
        # y no debemos calcularlo.
        if not any(op in expr for op in ["+", "-", "*", "/"]):
            return (
                f"No detecté una operación matemática válida (solo números: '{expr}')."
            )

        try:
            # 4. Evaluación segura (limitada)
            # Evaluamos la expresión matemática
            result = eval(expr, {"__builtins__": None}, {})

            # Formateo: Si es entero (5.0), mostrarlo como 5
            if isinstance(result, float) and result.is_integer():
                result = int(result)

            return str(result)

        except ZeroDivisionError:
            return "Error: División por cero."
        except Exception as e:
            return f"Error al calcular '{expr}': {str(e)}"
