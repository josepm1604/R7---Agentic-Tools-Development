import json
import os
import pandas as pd
from src.config import Config


def show_report() -> None:
    """Genera tabla de métricas (E2 Observabilidad)."""
    if not os.path.exists(Config.LOG_AUDIT_PATH):
        print(f"No existe el archivo de trazas: {Config.LOG_AUDIT_PATH}")
        return

    data = []
    with open(Config.LOG_AUDIT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))

    if not data:
        print("No hay trazas registradas todavía.")
        return

    df = pd.DataFrame(data)
    tools_series = df["trace"].apply(
        lambda steps: [s.get("tool") for s in steps] if isinstance(steps, list) else []
    )

    print("\n--- MÉTRICAS DE AGENTE AUTÓNOMO ---")
    print(f"Total de consultas: {len(df)}")
    print(f"Promedio de pasos por query: {df['steps_count'].mean():.2f}")
    print(f"Latencia promedio: {df['latency_seconds'].mean():.2f}s")
    print("\nUso de herramientas por consulta:")
    counts = tools_series.explode().dropna().value_counts()
    if counts.empty:
        print("(Sin llamadas a herramientas registradas)")
    else:
        print(counts.to_string())


if __name__ == "__main__":
    show_report()
