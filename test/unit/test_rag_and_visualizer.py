from pathlib import Path
from src.agent.agent import _get_tools
from src.utils.visualizer import generate_charts


def test_rag_hybrid_rrf_retrieves_semantic_query():
    _, _, rag, _, _ = _get_tools()
    chunks = rag.retrieve_hybrid("electivos de inteligencia artificial", k=3, use_hybrid_rrf=True)
    assert len(chunks) == 3
    joined = "\n".join(chunks).lower()
    assert "inteligencia artificial" in joined or "algoritmos bioinspirados" in joined


def test_visualizer_generates_svg_charts(tmp_path: Path):
    charts = generate_charts(tmp_path)
    assert len(charts) == 2
    for chart in charts:
        assert chart.exists()
        assert chart.read_text(encoding="utf-8").startswith("<svg ")
