import os, re, unicodedata
import pdfplumber
from typing import List
from langchain_core.documents import Document


def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def like_code(s: str) -> bool:
    s = (s or "").strip()
    return bool(re.fullmatch(r"[A-Z]{2,4}[0-9A-Z]{2,4}", s))


def parse_plan_estudio_uni_pdf(path: str, tag: str) -> List[Document]:
    docs: List[Document] = []
    with pdfplumber.open(path) as pdf:
        current_section = "Desconocido"
        for page_i, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    clean_row = [
                        str(c).replace("\n", " ").strip() if c else "" for c in row
                    ]

                    if not any(clean_row):
                        continue

                    row_norm = [normalize_text(c) for c in clean_row]
                    first = row_norm[0] if row_norm else ""

                    # Detectar cursos por ciclos
                    if "ciclo" in first and "total" not in first:
                        current_section = clean_row[0] or "Ciclo"
                        continue
                    if first in {"total", "totales"}:
                        continue

                    # Buscar código + nombre del curso al lado
                    code_idx = None
                    for i, celda in enumerate(clean_row):
                        if like_code(celda):
                            code_idx = i
                            break
                    if code_idx is None or code_idx + 1 >= len(clean_row):
                        continue

                    codigo = clean_row[code_idx]
                    nombre = clean_row[code_idx + 1]

                    if not nombre:
                        continue

                    # tipo de curso -> "Obligatorio", "Electivo", etc
                    sec_norm = normalize_text(current_section)
                    if "ciclo" in sec_norm:
                        tipo = "Obligatorio"
                        ciclo = current_section
                    elif "especialidad" in sec_norm:
                        tipo = "Electivo de Especialidad"
                        ciclo = "Electivos"
                    elif "complementarios" in sec_norm:
                        tipo = "Electivo Complementario"
                        ciclo = "Electivos"
                    else:
                        tipo = "Desconocido"
                        ciclo = current_section

                    content = f"{tag} Curso: {nombre} ({codigo})"
                    docs.append(
                        Document(
                            page_content=content,
                            metadata={
                                "universidad": tag,
                                "codigo": codigo,
                                "curso": nombre,
                                "ciclo": ciclo,
                                "tipo": tipo,
                                "source": os.path.basename(path),
                                "page": page_i,
                            },
                        )
                    )
    return docs
