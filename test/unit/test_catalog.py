import pytest

from src.agent.guards import Guardrails
from src.tools.catalog import CycleTool, PrereqTool, find_course, load_catalog
from test.eval.run_eval import check


def test_parser_creditos_no_son_horas():
    # Regresión: el parser tomaba T.H. (6) en vez de Créditos (5)
    c = load_catalog()["BFI01"]
    assert c["nombre"] == "Física I" and c["creditos"] == 5


def test_ningun_curso_sin_creditos():
    assert all(c["creditos"] > 0 for c in load_catalog().values())


def test_find_course_por_nombre_sin_tildes():
    assert find_course("prerrequisitos de fisica ii")["codigo"] == "CF1B2"


def test_prereq_cadena_completa():
    out = PrereqTool().run("Introducción a la Electricidad y Magnetismo")
    assert "BFI01" in out and "BMA01" in out  # BMA01 es prerrequisito transitivo


def test_ciclo_suma_creditos():
    assert "21 créditos" in CycleTool().run("Segundo ciclo")


def test_ciclo_invalido():
    assert CycleTool().run("hola").startswith("Error")


def test_curso_inexistente():
    assert PrereqTool().run("Basket Subacuático").startswith("Error")


def test_guardrail_limita_rag():
    # Regresión: la clave rag_search no se aplicaba nunca
    g = Guardrails()
    assert [g.check_and_track("rag_search") for _ in range(4)] == [True, True, True, False]


def test_check_del_harness_detecta_fallos():
    case = {"expect_all": [r"\b5\b"]}
    assert check("Tiene 5 créditos", case) and not check("Tiene 6 créditos", case)


def test_find_course_fuzzy_con_typo():
    c = find_course("Calclo Integral")
    assert c is not None and c["codigo"] == "BMA02"


def test_guardrail_rechaza_herramienta_desconocida_y_vacia():
    g = Guardrails()
    assert not g.check_and_track("herramienta_inventada")
    assert not g.validate_input("   ")[0]
