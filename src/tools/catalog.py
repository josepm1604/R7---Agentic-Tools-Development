"""Catálogo estructurado del plan de estudios + herramientas exactas (sin LLM ni embeddings)."""

import difflib
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any

from src.config import Config
from src.tools.base import BaseTool
from src.tools.rag_loader_uni import parse_plan_estudio_uni_pdf

ORDINALES = {
    "primer": 1, "segundo": 2, "tercer": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "setimo": 7, "octavo": 8, "noveno": 9, "decimo": 10,
}  # fmt: skip


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, dict[str, Any]]:
    """{codigo: {codigo, nombre, ciclo, tipo, creditos, prereqs}} parseado del PDF."""
    courses = {}
    for fn in os.listdir(Config.DATA_PATH):
        if not fn.lower().endswith(".pdf"):
            continue
        for d in parse_plan_estudio_uni_pdf(os.path.join(Config.DATA_PATH, fn), "UNI"):
            f = dict(re.findall(r"^([^:\n]+):\s*(.*)$", d.page_content, re.M))
            pre = f.get("Pre-requisitos", "")
            courses[d.metadata["codigo"]] = {
                "codigo": d.metadata["codigo"],
                "nombre": f.get("Asignatura", ""),
                "ciclo": d.metadata["ciclo"],
                "tipo": d.metadata["tipo"],
                "creditos": int(d.metadata["creditos"]) if d.metadata["creditos"].isdigit() else 0,
                "prereqs": [] if "ninguno" in pre.lower() else re.findall(r"[A-Z]{2,}\w*\d\w*", pre),
            }  # fmt: skip
    return courses


def find_course(text: str) -> dict[str, Any] | None:
    """Curso por código, por nombre exacto o por coincidencia difusa (gana el nombre más largo)."""
    cat, t = load_catalog(), norm(text)
    for code in re.findall(r"\b(?=[a-z0-9]{4,6}\b)[a-z]{2,3}[a-z0-9]*\d[a-z0-9]*\b", t):
        if code.upper() in cat:
            return cat[code.upper()]
    hits = [c for c in cat.values() if re.search(rf"\b{re.escape(norm(c['nombre']))}\b", t)]
    if hits:
        return max(hits, key=lambda c: len(c["nombre"]))
    by_norm_name = {norm(c["nombre"]): c for c in cat.values() if c["nombre"]}
    cleaned = re.sub(
        r"\b(prerrequisitos?|requisitos?|creditos?|curso|asignatura|de|del|la|el|en|los|las|un|una|quiero|llevar|puedo|matricularme)\b",
        " ",
        t,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for candidate in (cleaned, t):
        if not candidate:
            continue
        fuzzy = difflib.get_close_matches(candidate, by_norm_name.keys(), n=1, cutoff=0.75)
        if fuzzy:
            return by_norm_name[fuzzy[0]]
    return None


def _cycle_name(text: str):
    t = norm(text)
    for word, n in ORDINALES.items():
        if re.search(rf"\b{word}\b", t):
            return n
    m = re.search(r"\b(\d{1,2})\b", t)
    return int(m.group(1)) if m else None


class CycleTool(BaseTool):
    """Lista los cursos de un ciclo y suma sus créditos."""

    def __init__(self):
        super().__init__(name="plan_ciclo")

    def run(self, input_text: str) -> str:
        n = _cycle_name(input_text)
        if n is None:
            return "Error: indica el ciclo (ej: Segundo ciclo o 2)."
        rows = [
            c for c in load_catalog().values()
            if _cycle_name(c["ciclo"]) == n and "ciclo" in norm(c["ciclo"])
        ]  # fmt: skip
        if not rows:
            return f"No hay cursos registrados para el ciclo {n}."
        lines = [f"- {c['nombre']} ({c['codigo']}, {c['creditos']} créditos)" for c in rows]
        return f"Ciclo {n}: {len(rows)} cursos, {sum(c['creditos'] for c in rows)} créditos en total.\n" + "\n".join(lines)


class PrereqTool(BaseTool):
    """Cadena completa de prerrequisitos de un curso."""

    def __init__(self):
        super().__init__(name="plan_prereq")

    def run(self, input_text: str) -> str:
        course = find_course(input_text)
        if not course:
            return "Error: curso no encontrado en el plan de estudios."
        cat, seen, order = load_catalog(), set(), []

        def visit(code):  # DFS: los más básicos primero
            for p in cat.get(code, {"prereqs": []})["prereqs"]:
                if p not in seen:
                    seen.add(p)
                    visit(p)
                    order.append(p)

        visit(course["codigo"])
        name = lambda c: f"{cat[c]['nombre']} ({c})" if c in cat else c
        direct = ", ".join(name(p) for p in course["prereqs"]) or "Ninguno"
        chain = " -> ".join(name(p) for p in order) or "Ninguno"
        return (
            f"{course['nombre']} ({course['codigo']}), {course['creditos']} créditos. "
            f"Prerrequisitos directos: {direct}. Cadena completa: {chain}."
        )
