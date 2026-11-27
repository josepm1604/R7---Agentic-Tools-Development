import ast
import operator
import re
from src.tools.base import BaseTool

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

MAX_ABS_VALUE = 1e12


def _eval_ast(node: ast.AST) -> float:
    """Evalua un árbol sintáctico aritmético de forma segura sin eval()."""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        if abs(node.value) > MAX_ABS_VALUE:
            raise ValueError("Número fuera de rango permitido.")
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            raise ValueError("Operación no permitida: potencias deshabilitadas por seguridad.")
        op_fn = _BIN_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Operador no permitido: {type(node.op).__name__}")
        result = op_fn(_eval_ast(node.left), _eval_ast(node.right))
        if abs(result) > MAX_ABS_VALUE:
            raise ValueError("Resultado fuera de rango permitido.")
        return result
    raise ValueError(f"Expresión no permitida: {type(node).__name__}")


class CalculatorTool(BaseTool):
    def __init__(self):
        super().__init__(name="calculator")

    def run(self, input_text: str) -> str:
        text_clean = input_text.lower()
        text_clean = text_clean.replace(" por ", "*").replace(" x ", "*")
        text_clean = text_clean.replace(" entre ", "/").replace(" dividido ", "/")
        text_clean = text_clean.replace(" mas ", "+").replace(" más ", "+")
        text_clean = text_clean.replace(" menos ", "-")

        matches = re.findall(r"[\d\+\-\*\/\.\(\)\s]+", text_clean)
        valid_exprs = [m.strip() for m in matches if any(char.isdigit() for char in m)]

        if not valid_exprs:
            return "No se encontraron números para calcular."

        expr = max(valid_exprs, key=len)

        if not any(op in expr for op in ["+", "-", "*", "/"]):
            return (
                f"No detecté una operación matemática válida (solo números: '{expr}')."
            )

        try:
            tree = ast.parse(expr, mode="eval")
            result = _eval_ast(tree)

            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)

        except ZeroDivisionError:
            return "Error: División por cero."
        except Exception as e:
            return f"Error al calcular '{expr}': {str(e)}"
