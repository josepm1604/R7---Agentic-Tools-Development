import pytest
from src.tools.calculator import CalculatorTool


class TestCalculatorTool:
    @pytest.fixture
    def tool(self):
        return CalculatorTool()

    def test_aritmetica_basica(self, tool):
        assert tool.run("2 + 2") == "4"
        assert tool.run("10 - 4") == "6"
        assert tool.run("5 * 5") == "25"
        assert tool.run("20 / 2") == "10"

    def test_precedencia_y_parentesis(self, tool):
        assert tool.run("2 + 3 * 4") == "14"
        assert tool.run("(2 + 3) * 4") == "20"

    def test_extrae_expresion_de_frase(self, tool):
        assert tool.run("Por favor calcula cuanto es 25 * 4 gracias") == "100"
        assert tool.run("El resultado de 10+10 es requerido") == "20"

    def test_decimales(self, tool):
        assert tool.run("2.5 + 2.5") == "5"

    def test_manejo_de_errores(self, tool):
        res = tool.run("10 / 0")
        assert "división por cero" in res.lower()

        res2 = tool.run("La versión es 1.2.3")
        assert "no detecté" in res2.lower()

    def test_sin_calculo(self, tool):
        assert tool.run("Hola mundo") == "No se encontraron números para calcular."

    def test_bloquea_potencia_dos(self, tool):
        res = tool.run("9**9**9")
        assert "no permitida" in res.lower() or "error" in res.lower()

    def test_negativos(self, tool):
        assert tool.run("-5 + 12") == "7"
