import pytest
from src.tools.verification import VerificationTool


class TestVerificationTool:
    @pytest.fixture
    def tool(self):
        return VerificationTool(student_history={"BMA01", "BFI01"})

    def test_aprobado_si_cumple_requisitos(self, tool):
        res = tool.run("Quiero llevar CF1B2")
        assert "approved" in res.lower()
        assert "CF1B2" in res

    def test_aprobado_por_nombre(self, tool):
        res = tool.run("Puedo llevar Cálculo Integral?")
        assert "approved" in res.lower()
        assert "BMA02" in res

    def test_rechazado_si_faltan_requisitos(self, tool):
        res = tool.run("Puedo matricularme en CC0C3?")
        assert "rejected" in res.lower()
        assert "CC521" in res

    def test_curso_no_encontrado(self, tool):
        res = tool.run("Quiero llevar ZZ999")
        assert "no encontrado" in res.lower()
        assert "ZZ999" in res

    def test_sin_codigo_en_input(self, tool):
        res = tool.run("Verifica mis requisitos por favor")
        assert "no se detect" in res.lower()

    def test_ya_aprobado(self, tool):
        res = tool.run("Puedo llevar BFI01 de nuevo?")
        assert "status" in res.lower()
        assert "ya aprobaste" in res.lower()
