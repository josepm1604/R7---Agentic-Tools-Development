"""Experimentos paramétricos sobre RAG++ y herramientas (Issue #10).

Ejecutar:
  python -m test.eval.run_experiments
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from src.agent.agent import _get_tools  # noqa: E402
from src.config import Config  # noqa: E402
from src.utils.visualizer import render_horizontal_bar_svg  # noqa: E402
from test.eval.run_eval import check  # noqa: E402

SEMANTIC_BENCHMARK = [
    ("electivos de inteligencia artificial", r"cc421|inteligencia artificial|algoritmos bioinspirados"),
    ("seguridad en sistemas informaticos", r"cc411"),
    ("cursos de programacion paralela", r"cc332|computacion paralela|nucleo y redes"),
    ("calculo de probabilidades", r"cm1h2"),
]


def run_experiments() -> dict:
    _, _, rag, _, _ = _get_tools()
    golden = json.loads((ROOT / "test" / "eval" / "golden.json").read_text(encoding="utf-8"))
    credit_cases = [c for c in golden if c["category"] == "credits"]

    # 1. Barrido de fuzzy_cutoff
    fuzzy_results = []
    for cutoff in (0.65, 0.75, 0.85, 0.95):
        ok = sum(
            1 for c in credit_cases
            if check(rag.run(c["tool_input"], fuzzy_cutoff=cutoff), c)
        )
        fuzzy_results.append({"fuzzy_cutoff": cutoff, "passed": ok, "total": len(credit_cases)})

    # 2. Vector-only vs Híbrido (Vector + Léxico RRF) en consultas semánticas sin nombre exacto
    rrf_results = []
    for use_rrf in (False, True):
        ok = 0
        for q, pattern in SEMANTIC_BENCHMARK:
            chunks = rag.retrieve_hybrid(q, k=3, use_hybrid_rrf=use_rrf)
            joined = "\n".join(chunks).lower()
            if __import__("re").search(pattern, joined):
                ok += 1
        rrf_results.append({
            "mode": "Híbrido (Vector+RRF)" if use_rrf else "Solo Vector",
            "passed": ok,
            "total": len(SEMANTIC_BENCHMARK),
        })

    # 3. Barrido de k_override (tamaño de contexto recuperado)
    k_results = []
    for k in (1, 3, 5, 8):
        ok = 0
        total_chars = 0
        for q, pattern in SEMANTIC_BENCHMARK:
            out = "\n".join(rag.retrieve_hybrid(q, k=k, use_hybrid_rrf=True))
            total_chars += len(out)
            if __import__("re").search(pattern, out.lower()):
                ok += 1
        k_results.append({
            "k": k,
            "passed": ok,
            "total": len(SEMANTIC_BENCHMARK),
            "avg_chars": round(total_chars / len(SEMANTIC_BENCHMARK)),
        })

    summary = {
        "fuzzy_cutoff_sweep": fuzzy_results,
        "hybrid_rrf_comparison": rrf_results,
        "k_recall_sweep": k_results,
    }

    out_json = ROOT / "test" / "eval" / "results" / "experiments_latest.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    chart_items = [
        (f"fuzzy={r['fuzzy_cutoff']}", (r["passed"] / r["total"]) * 100.0)
        for r in fuzzy_results
    ] + [
        (r["mode"], (r["passed"] / r["total"]) * 100.0)
        for r in rrf_results
    ] + [
        (f"RRF k={r['k']}", (r["passed"] / r["total"]) * 100.0)
        for r in k_results
    ]
    chart_svg = render_horizontal_bar_svg(
        "Comparativa de experimentos paramétricos (% acierto)",
        chart_items,
        unit="%",
        color="#7c3aed",
    )
    chart_path = Config.BASE_DIR / "docs" / "charts" / "experiments_comparison.svg"
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_text(chart_svg, encoding="utf-8")

    print("=== Experimentos Paramétricos ===")
    print("1) fuzzy_cutoff:", fuzzy_results)
    print("2) Vector vs RRF:", rrf_results)
    print("3) k_recall:", k_results)
    print("Guardado:", out_json)
    print("Gráfico:", chart_path)
    return summary


if __name__ == "__main__":
    run_experiments()
