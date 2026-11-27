import os
from functools import lru_cache
from llama_cpp import Llama, LlamaGrammar
from src.config import Config


def _react_grammar_str() -> str:
    """GBNF que obliga el formato ReAct y permite respuestas finales multilínea."""
    tools = " | ".join(f'"{t}"' for t in Config.MAX_TOOL_CALLS)
    return (
        'root ::= "Thought: " line "\\n" ("Action: " tool "\\nAction Input: " line "\\n" | "Final Answer: " answer)\n'
        f"tool ::= {tools}\n"
        'line ::= [^\\n]+\n'
        'answer ::= [^\\n]+ ("\\n" [^\\n]+)*\n'
    )


@lru_cache(maxsize=1)
def get_react_grammar() -> LlamaGrammar | None:
    if not Config.USE_GRAMMAR:
        return None
    return LlamaGrammar.from_string(_react_grammar_str())


@lru_cache(maxsize=1)  # se carga una sola vez por proceso
def load_llm() -> Llama:
    """Carga el modelo Qwen2.5 optimizado para CPU con soporte ChatML."""
    if not os.path.exists(Config.MODEL_PATH):
        print(f"ERROR CRÍTICO: No se encuentra el modelo en {Config.MODEL_PATH}")
        raise FileNotFoundError(f"No existe el modelo en: {Config.MODEL_PATH}")

    return Llama(
        model_path=Config.MODEL_PATH,
        n_ctx=4096,
        n_threads=Config.CPU_NUM_THREADS,
        n_batch=512,
        verbose=False,
    )
