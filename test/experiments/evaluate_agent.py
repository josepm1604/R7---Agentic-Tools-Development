import sys
import os
import time
import json
import math
import re

# Añadir ruta raíz al path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.config import Config
from src.agent.graph import app  # <--- IMPORTAMOS EL GRAFO, NO EL AGENTE VIEJO


# Función auxiliar para leer logs
def read_last_log_entry():
    """Lee la última entrada del log para ver qué herramienta se usó internamente."""
    log_path = os.path.join(Config.LOG_DIR, "execution.jsonl")
    if not os.path.exists(log_path):
        return {}

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return {}
            return json.loads(lines[-1])
    except:
        return {}


def evaluate_cases(cases, section_name: str):
    print(f"\n=== Evaluación: {section_name} ===")
    print("-" * 100)
    print(f"{'Query':<40} | {'Tool Used':<12} | {'Output OK':<8} | {'Latency':<6}")
    print("-" * 100)

    hits = 0
    latencies = []

    for c in cases:
        query = c["query"]
        expected_content = c["expected"]  # Lo que esperamos ver en la respuesta
        expected_tool_key = c.get(
            "expected_tool_key", None
        )  # 'calculator', 'verification'

        t0 = time.time()

        # --- EJECUCIÓN DEL GRAFO ---
        try:
            result = app.invoke({"question": query})
            final_response = result.get("generation", "")

            # Intentamos leer qué herramienta decidió el router (si está en el estado)
            # Nota: En nuestro grafo, guardamos 'tool_decision' en el estado
            tool_used = result.get("tool_decision", "rag")

        except Exception as e:
            final_response = f"ERROR: {e}"
            tool_used = "error"

        dt = time.time() - t0
        latencies.append(dt)

        # --- VALIDACIÓN ---
        # 1. ¿La respuesta contiene el dato esperado?
        is_correct = False

        # Normalización para comparar
        resp_norm = str(final_response).lower()
        exp_norm = str(expected_content).lower()

        if expected_tool_key == "calculator":
            # Para calculadora, buscamos el número exacto
            # Si espera 25.0, buscamos "25" en el texto
            is_correct = str(int(float(expected_content))) in resp_norm
        else:
            # Para texto, búsqueda parcial
            is_correct = exp_norm in resp_norm

        if is_correct:
            hits += 1

        # Color para consola (opcional)
        status_icon = "✅" if is_correct else "❌"

        print(
            f"{query[:38]:<40} | {tool_used:<12} | {status_icon} {str(is_correct):<5} | {dt:.2f}s"
        )
        if not is_correct:
            print(f"   >>> Expected: {expected_content}")
            print(f"   >>> Got: {final_response[:100]}...")

    accuracy = (hits / len(cases)) * 100
    avg_latency = sum(latencies) / len(cases)

    print("-" * 100)
    print(f"Section Accuracy: {accuracy:.2f}% | Avg Latency: {avg_latency:.2f}s")
    return {"acc": accuracy, "lat": avg_latency}


def main():
    print("🧪 Iniciando Evaluación E2 (LangGraph)")

    # 1. Casos de Calculadora
    calc_cases = [
        {
            "query": "Cuanto es 20 + 5",
            "expected": 25,
            "expected_tool_key": "calculator",
        },
        {
            "query": "Calcula 10 * 10",
            "expected": 100,
            "expected_tool_key": "calculator",
        },
        # Caso complejo
        {
            "query": "Si tengo 50 soles y gasto 10, cuanto me queda?",
            "expected": 40,
            "expected_tool_key": "calculator",
        },
    ]

    # 2. Casos de Verificación (Códigos de Curso)
    # Ajusta los códigos según tu diccionario en verification.py
    verif_cases = [
        {
            "query": "Puedo llevar CC311?",
            "expected": "APPROVED",
            "expected_tool_key": "verification",
        },
        # Asumiendo que definiste BFI01 con prerrequisitos
        {
            "query": "Soy apto para BFI01?",
            "expected": "REJECTED",
            "expected_tool_key": "verification",
        },
        # Caso borde: código inexistente
        {
            "query": "Puedo llevar XX999?",
            "expected": "no encontrado",
            "expected_tool_key": "verification",
        },
    ]

    # 3. Casos RAG (Documentos PDF)
    rag_cases = [
        # Pregunta general que debe responderse con el PDF
        {
            "query": "¿Qué cursos son del primer ciclo?",
            "expected": "ciclo",
            "expected_tool_key": "rag",
        },
        # Pregunta que no debería saber
        {
            "query": "¿Quién ganó el mundial 2022?",
            "expected": "no encontré",
            "expected_tool_key": "rag",
        },
    ]

    # Ejecutar
    evaluate_cases(calc_cases, "Calculadora")
    evaluate_cases(verif_cases, "Verificación")
    evaluate_cases(rag_cases, "RAG (Retrieval)")


if __name__ == "__main__":
    main()
