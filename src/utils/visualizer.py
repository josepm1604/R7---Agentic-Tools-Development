import pandas as pd
import json
from src.config import Config


def show_report():
    """Genera tabla de métricas (E2 Observabilidad)."""
    data = []
    with open(Config.LOG_AUDIT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))

    df = pd.DataFrame(data)
    print("\n--- MÉTRICAS DE AGENTE AUTÓNOMO ---")
    print(f"Total de consultas: {len(df)}")
    print(f"Promedio de pasos por query: {df['steps_count'].mean():.2f}")
    print(f"Latencia promedio: {df['total_time'].mean():.2f}s")
    print("\nUso de herramientas por consulta:")
    print(df["tools_used"].explode().value_counts())
