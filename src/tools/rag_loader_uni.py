from dataclasses import dataclass
import os, re, unicodedata
import pdfplumber
from typing import Any, List


@dataclass
class Document:
    page_content: str
    metadata: dict[str, Any]


def normalize_text(s: str) -> str:
    """Limpia texto para comparaciones (quita tildes, mayúsculas)"""
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.strip()


def clean_cell(text):
    """Limpia saltos de linea y espacios extra de una celda"""
    if not text:
        return ""
    return str(text).replace("\n", " ").strip()


def parse_plan_estudio_uni_pdf(path: str, tag: str) -> List[Document]:
    docs: List[Document] = []

    # ESTADO GLOBAL: Recordar en qué sección estamos mientras bajamos por el PDF
    current_cycle = "Ciclo Desconocido"
    current_type = "Obligatorio"  # Por defecto los ciclos numerados son obligatorios

    print(f"Procesando PDF UNI: {os.path.basename(path)}...")

    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()

            if not tables:
                continue

            for table in tables:
                for row in table:
                    # Limpieza básica de la fila
                    row = [clean_cell(c) for c in row]

                    # Filtramos filas vacías
                    if not any(row):
                        continue

                    # Normalizamos la primera celda para detectar Cabeceras
                    first_cell_norm = normalize_text(row[0])

                    # --- 1. DETECCIÓN DE CABECERAS (Cambio de Estado) ---

                    # Caso: "Primer ciclo", "Segundo ciclo"...
                    if "ciclo" in first_cell_norm and "total" not in first_cell_norm:
                        current_cycle = row[0]  # Ej: "Primer ciclo"
                        current_type = "Obligatorio"
                        continue  # Saltamos la fila, solo actualizamos estado

                    # Caso: "Cursos Electivos de Especialidad"
                    if (
                        "electivos" in first_cell_norm
                        and "especialidad" in first_cell_norm
                    ):
                        current_cycle = "Electivos de Especialidad"
                        current_type = "Electivo (Especialidad)"
                        continue

                    # Caso: "Cursos Electivos Complementarios"
                    if (
                        "electivos" in first_cell_norm
                        and "complementarios" in first_cell_norm
                    ):
                        current_cycle = "Electivos Complementarios"
                        current_type = "Electivo (Complementario)"
                        continue

                    # Ignorar filas basura
                    if (
                        "nombre del curso" in first_cell_norm
                        or "total" in first_cell_norm
                    ):
                        continue

                    # --- 2. EXTRACCIÓN DEL CURSO ---
                    # En tus tablas UNI: Col 0=Código, Col 1=Nombre, Col 8=Créditos, Col 10=Requisitos
                    # Usamos índices seguros

                    codigo = row[0]
                    # Validación fuerte de código (Ej: BFI01, CC311)
                    if len(codigo) < 4 or not any(c.isdigit() for c in codigo):
                        continue

                    nombre = row[1]
                    if not nombre:
                        continue

                    # Créditos (buscamos en columnas típicas o por valor numérico)
                    creditos = "N/A"
                    # Col 8 = Créditos (col 6 es T.H. = horas totales, no créditos)
                    for col_idx in range(8, len(row)):
                        val = row[col_idx]
                        if val.isdigit() and 1 <= int(val) <= 9:
                            creditos = val
                            break

                    # Pre-requisitos (Usualmente la última o penúltima columna con texto)
                    requisito = "Ninguno"
                    for col_idx in range(len(row) - 1, 3, -1):
                        val = str(row[col_idx])
                        if not val or not val.strip():
                            continue

                        # CORRECCIÓN: Ignorar columnas que son nombres de archivo PDF
                        if ".pdf" in val.lower() or "silabo" in val.lower():
                            continue

                        # Si encontramos algo que parece un requisito
                        if "ninguno" in val.lower() or (
                            any(c.isdigit() for c in val) and val[0].isupper()
                        ):
                            requisito = val
                            break

                    # --- 3. CONSTRUCCIÓN DEL TEXTO ENRIQUECIDO (La Magia) ---
                    # Aquí creamos un párrafo que contiene TODA la info necesaria para el RAG.
                    # Si el usuario busca "cursos primer ciclo", el match ocurrirá aquí.

                    content = (
                        f"Universidad: {tag}\n"
                        f"Asignatura: {nombre}\n"
                        f"Código: {codigo}\n"
                        f"Ubicación: {current_cycle}\n"  # <--- INYECCIÓN DE CONTEXTO
                        f"Tipo: {current_type}\n"
                        f"Créditos: {creditos}\n"
                        f"Pre-requisitos: {requisito}"
                    )

                    # Metadatos para filtrado avanzado (opcional pero recomendado)
                    metadata = {
                        "source": os.path.basename(path),
                        "page": page_num,
                        "codigo": codigo,
                        "ciclo": current_cycle,
                        "tipo": current_type,
                        "creditos": creditos,
                    }

                    docs.append(Document(page_content=content, metadata=metadata))

    return docs
