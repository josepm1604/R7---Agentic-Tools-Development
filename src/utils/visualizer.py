from html import escape
import json
import os
from pathlib import Path
import pandas as pd
from src.config import Config


def _load_traces() -> list[dict]:
    if not os.path.exists(Config.LOG_AUDIT_PATH):
        return []
    data: list[dict] = []
    with open(Config.LOG_AUDIT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def render_horizontal_bar_svg(
    title: str,
    items: list[tuple[str, float]],
    unit: str = "",
    color: str = "#2563eb",
) -> str:
    """Genera un gráfico SVG limpio de barras horizontales sin dependencias externas."""
    width = 680
    row_h = 34
    top_pad = 54
    left_pad = 190
    right_pad = 80
    height = top_pad + max(len(items), 1) * row_h + 24
    max_val = max((v for _, v in items), default=1.0) or 1.0
    bar_max_w = width - left_pad - right_pad

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" rx="8"/>',
        f'<text x="20" y="32" font-family="sans-serif" font-size="16" font-weight="bold" fill="#0f172a">{escape(title)}</text>',
    ]
    for idx, (label, val) in enumerate(items):
        y = top_pad + idx * row_h
        w = max((val / max_val) * bar_max_w, 2.0) if val > 0 else 0.0
        val_txt = f"{val:.1f}{unit}" if isinstance(val, float) and not val.is_integer() else f"{int(val)}{unit}"
        lines.append(
            f'<text x="{left_pad - 10}" y="{y + 18}" text-anchor="end" font-family="sans-serif" font-size="12" fill="#334155">{escape(label)}</text>'
        )
        lines.append(
            f'<rect x="{left_pad}" y="{y + 4}" width="{w:.1f}" height="20" rx="4" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{left_pad + w + 8:.1f}" y="{y + 18}" font-family="sans-serif" font-size="12" font-weight="bold" fill="#0f172a">{escape(val_txt)}</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def generate_charts(output_dir: Path | str = "docs/charts") -> list[Path]:
    """Genera gráficos SVG de observabilidad a partir de logs/audit_traces.jsonl."""
    data = _load_traces()
    if not data:
        return []

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    generated: list[Path] = []

    tools_series = df["trace"].apply(
        lambda steps: [s.get("tool") for s in steps] if isinstance(steps, list) else []
    )
    counts = tools_series.explode().dropna().value_counts()
    if not counts.empty:
        tool_svg = render_horizontal_bar_svg(
            "Uso de herramientas (audit_traces.jsonl)",
            [(str(k), float(v)) for k, v in counts.items()],
            color="#2563eb",
        )
        p1 = out_path / "tool_usage.svg"
        p1.write_text(tool_svg, encoding="utf-8")
        generated.append(p1)

    if "latency_seconds" in df.columns:
        lat_items = [
            (f"#{i + 1} ({row['steps_count']}p)", float(row["latency_seconds"]))
            for i, row in df.tail(12).reset_index(drop=True).iterrows()
        ]
        lat_svg = render_horizontal_bar_svg(
            f"Latencia de últimas {len(lat_items)} consultas (media global: {df['latency_seconds'].mean():.1f}s)",
            lat_items,
            unit="s",
            color="#059669",
        )
        p2 = out_path / "latency_distribution.svg"
        p2.write_text(lat_svg, encoding="utf-8")
        generated.append(p2)

    return generated


def show_report() -> None:
    """Genera tabla de métricas y gráficos SVG (Observabilidad)."""
    data = _load_traces()
    if not data:
        print(f"No hay trazas registradas en: {Config.LOG_AUDIT_PATH}")
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

    charts = generate_charts(Config.BASE_DIR / "docs" / "charts")
    if charts:
        print("\nGráficos generados:")
        for p in charts:
            print(f" - {p}")


if __name__ == "__main__":
    show_report()
