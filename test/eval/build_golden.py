"""Genera test/eval/golden.json desde el catálogo parseado del PDF (verdad = el PDF, no la memoria)."""

import json
import os
import random
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.tools.catalog import load_catalog, norm  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden.json")
ORD = ["Primer", "Segundo", "Tercer", "Cuarto"]


def name_re(n):  # nombre normalizado como regex
    return re.escape(norm(n))


def main():
    rnd = random.Random(0)
    cat = load_catalog()
    cases = []

    for c in rnd.sample([c for c in cat.values() if c["creditos"]], 10):
        cases.append({
            "id": f"credits-{c['codigo']}", "category": "credits",
            "query": f"Cuántos créditos tiene el curso {c['nombre']}",
            "tool": "rag_search", "tool_input": c["nombre"],
            "expect_all": [rf"\b{c['creditos']}\b"],
        })  # fmt: skip

    for c in rnd.sample([c for c in cat.values() if c["prereqs"]], 6):
        cases.append({
            "id": f"prereq-{c['codigo']}", "category": "prereq",
            "query": f"Cuáles son los prerrequisitos de {c['nombre']}",
            "tool": "plan_prereq", "tool_input": c["nombre"],
            "expect_all": [name_re(cat[p]["nombre"]) for p in c["prereqs"] if p in cat],
        })  # fmt: skip

    for i, word in enumerate(ORD, 1):
        rows = [c for c in cat.values() if c["ciclo"].lower().startswith(word.lower()[:4])]
        cases.append({
            "id": f"cycle-{i}", "category": "cycle",
            "query": f"Qué cursos hay en el {word.lower()} ciclo",
            "tool": "plan_ciclo", "tool_input": f"{word} ciclo",
            "expect_all": [name_re(c["nombre"]) for c in rows],
        })  # fmt: skip

    for q, exp in [("Cuánto es 12*7", "84"), ("Calcular 100/4", "25"), ("Cuánto es 15+27", "42")]:
        cases.append({
            "id": f"calc-{exp}", "category": "calc", "query": q,
            "tool": "calculator", "tool_input": q, "expect_all": [rf"\b{exp}\b"],
        })  # fmt: skip

    cases.append({
        "id": "verif-approved", "category": "verif",
        "query": "Puedo matricularme en CF1B2?",
        "tool": "verification", "tool_input": "CF1B2",
        "expect_all": [r"\bapproved\b", r"\bcf1b2\b"],
    })
    cases.append({
        "id": "verif-rejected", "category": "verif",
        "query": "Puedo llevar CC0C3?",
        "tool": "verification", "tool_input": "CC0C3",
        "expect_all": [r"\brejected\b", r"\bcc521\b"],
    })
    cases.append({
        "id": "fuzzy-1", "category": "credits",
        "query": "Cuántos créditos tiene Calclo Integral",
        "tool": "rag_search", "tool_input": "Calclo Integral",
        "expect_all": [r"\b5\b"],
    })

    cases.append({
        "id": "unknown-1", "category": "unknown",
        "query": "Cuántos créditos tiene el curso Basket Subacuático",
        "tool": "rag_search", "tool_input": "Basket Subacuático",
        "expect_all": [], "expect_any": ["no encuentro", "no tengo", "no se"],
        "skip_tool_check": True,
    })  # fmt: skip

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"{len(cases)} casos -> {OUT}")


if __name__ == "__main__":
    main()
