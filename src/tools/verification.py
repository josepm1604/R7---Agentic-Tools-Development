import re
from typing import Iterable, Optional
from src.tools.base import BaseTool
from src.tools.catalog import find_course, load_catalog


DEFAULT_STUDENT_HISTORY = {"BMA01", "BFI01"}


class VerificationTool(BaseTool):
    """Verifica elegibilidad de matrícula usando el catálogo real del plan de estudios."""

    def __init__(self, student_history: Optional[Iterable[str]] = None):
        super().__init__(name="verification")
        self.student_history = (
            {c.upper() for c in student_history}
            if student_history is not None
            else set(DEFAULT_STUDENT_HISTORY)
        )

    def run(self, input_text: str) -> str:
        """Analiza el texto buscando un código o nombre de curso del catálogo UNI y verifica elegibilidad."""
        catalog = load_catalog()
        course = find_course(input_text)

        if not course:
            code_match = re.search(r"\b(?=[A-Z0-9]{4,6}\b)[A-Z]{2,3}[A-Z0-9]*\d[A-Z0-9]*\b", input_text.upper())
            if code_match:
                return f"Error: Curso {code_match.group(0)} no encontrado en el catálogo."
            return "Error: No se detectó un código o nombre de curso válido (ejemplo: BFI01, CF1B2)."

        course_code = course["codigo"]

        if course_code in self.student_history:
            return f"Status: Ya aprobaste {course_code} ({course['nombre']})."

        requirements = course["prereqs"]
        missing_reqs = [req for req in requirements if req not in self.student_history]

        if missing_reqs:
            missing_names = [
                f"{req} ({catalog[req]['nombre']})" if req in catalog else req
                for req in missing_reqs
            ]
            return (
                f"REJECTED: No puedes llevar {course_code} ({course['nombre']}). "
                f"Faltan prerrequisitos: {', '.join(missing_names)}."
            )

        return f"APPROVED: Puedes matricularte en {course_code} ({course['nombre']})."
