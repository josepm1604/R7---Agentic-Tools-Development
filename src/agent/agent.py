from dataclasses import dataclass
from functools import lru_cache
import logging
import re
import time
from typing import Any, Callable, Mapping, Sequence

from src.agent.guards import Guardrails
from src.config import Config
from src.llm.model_loader import get_react_grammar, load_llm
from src.tools.base import BaseTool
from src.tools.calculator import CalculatorTool
from src.tools.catalog import CycleTool, PrereqTool
from src.tools.rag_setup import get_rag_tool
from src.tools.verification import VerificationTool
from src.utils.logger import AuditLogger

logger = logging.getLogger(__name__)

REACT_SYSTEM_PROMPT = """Eres un asistente inteligente del plan de estudios de la UNI.
Para responder, DEBES usar el formato de PENSAMIENTO, ACCIÓN y OBSERVACIÓN.

Tus herramientas disponibles son:
1. calculator: Úsalo para cálculos matemáticos. Input: expresión (ej: 20*4).
2. verification: Úsalo para verificar si un estudiante puede matricularse en un curso (ej: BFI01, CF1B2). Input: código o nombre del curso.
3. rag_search: Úsalo para buscar datos de UN curso (créditos, tipo, ciclo). Input: el nombre del curso (ej: Física I).
4. plan_ciclo: Úsalo para listar los cursos de un ciclo y sus créditos totales. Input: el ciclo (ej: Segundo ciclo).
5. plan_prereq: Úsalo para ver los prerrequisitos de un curso. Input: el nombre del curso (ej: Física II).

Formato OBLIGATORIO:
Thought: debo pensar qué hacer...
Action: nombre_herramienta
Action Input: input_para_herramienta
(espera Observation)
... (repite Thought/Action/Observation si es necesario)
Thought: ya tengo la respuesta final
Final Answer: la respuesta final al usuario (concisa y sin repetir frases)

Si la Observation no contiene la respuesta, di en Final Answer: No encuentro esa información en el plan de estudios.

Ejemplo:
Usuario: Cuántos créditos tiene Cálculo II?
Thought: debo buscar el curso en el plan de estudios.
Action: rag_search
Action Input: Cálculo II
Observation: Asignatura: Cálculo II ... Créditos: 5
Thought: ya tengo la respuesta final
Final Answer: Cálculo II tiene 5 créditos."""


@dataclass
class StepAction:
    tool: str
    tool_input: str
    log: str


@dataclass
class AgentResult:
    answer: str
    steps: list[tuple[StepAction, str]]
    latency_s: float
    timed_out: bool = False
    max_steps_reached: bool = False


ToolLike = BaseTool | Callable[[str], str]


def _invoke_tool(tool: ToolLike, tool_input: str) -> str:
    if hasattr(tool, "run"):
        return str(tool.run(tool_input))  # type: ignore[union-attr]
    return str(tool(tool_input))


class Agent:
    """Agente ReAct desacoplado de la CLI con inyección de dependencias."""

    def __init__(
        self,
        llm: Any,
        tools: Mapping[str, ToolLike],
        guards: Guardrails | None = None,
        audit_logger: AuditLogger | None = None,
        grammar: Any | None = None,
        max_iterations: int | None = None,
        max_execution_time: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.llm = llm
        self.tools = dict(tools)
        self.guards = guards or Guardrails()
        self.audit_logger = audit_logger or AuditLogger()
        self.grammar = grammar
        self.max_iterations = max_iterations or Config.MAX_ITERATIONS
        self.max_execution_time = max_execution_time or Config.MAX_EXECUTION_TIME
        self.max_tokens = max_tokens or Config.MAX_TOKENS

    def run(
        self,
        query: str,
        history: Sequence[tuple[str, str]] | None = None,
    ) -> AgentResult:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT}
        ]
        for q, a in (history or [])[-3:]:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": f"Final Answer: {a}"})
        messages.append({"role": "user", "content": query})

        steps_log: list[tuple[StepAction, str]] = []
        start_time = time.time()
        self.guards.reset()

        logger.debug("Iniciando bucle ReAct (%d pasos máx.)", self.max_iterations)

        for i in range(self.max_iterations):
            elapsed = time.time() - start_time
            if elapsed > self.max_execution_time:
                timeout_msg = (
                    f"Tiempo máximo de ejecución alcanzado ({self.max_execution_time:.0f}s)."
                )
                self.audit_logger.log_audit(query, steps_log, timeout_msg, elapsed)
                return AgentResult(
                    answer=timeout_msg,
                    steps=steps_log,
                    latency_s=elapsed,
                    timed_out=True,
                )

            try:
                stop_tokens = ["Observation:", "\nObservation", "<|im_end|>"]
                completion = self.llm.create_chat_completion(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=self.max_tokens,
                    repeat_penalty=1.15,
                    stop=stop_tokens,
                    grammar=self.grammar,
                )
                response = completion["choices"][0]["message"]["content"] or ""
            except Exception as e:
                elapsed = time.time() - start_time
                err_msg = f"Error al invocar LLM: {e}"
                self.audit_logger.log_audit(query, steps_log, err_msg, elapsed)
                return AgentResult(answer=err_msg, steps=steps_log, latency_s=elapsed)

            action_match = re.search(r"Action:\s*(.+?)(?:\n|$)", response)
            input_match = re.search(r"Action Input:\s*(.+?)(?:\n|$)", response)

            if "Final Answer:" in response:
                final_ans = response.split("Final Answer:")[-1].strip()
                elapsed = time.time() - start_time
                self.audit_logger.log_audit(query, steps_log, final_ans, elapsed)
                return AgentResult(answer=final_ans, steps=steps_log, latency_s=elapsed)

            if not action_match:
                if i > 0:
                    final_ans = response.replace("Thought:", "").strip()
                    elapsed = time.time() - start_time
                    self.audit_logger.log_audit(query, steps_log, final_ans, elapsed)
                    return AgentResult(answer=final_ans, steps=steps_log, latency_s=elapsed)
                messages.append({"role": "assistant", "content": response})
                messages.append(
                    {
                        "role": "user",
                        "content": "No indicaste una acción. Usa 'Action:' y 'Action Input:', o 'Final Answer:'.",
                    }
                )
                continue

            tool_name = action_match.group(1).strip()
            tool_input = input_match.group(1).strip() if input_match else ""

            if not self.guards.check_and_track(tool_name):
                observation = f"Error de Seguridad: Herramienta no permitida o límite excedido para {tool_name}."
            elif not self.guards.validate_input(tool_input)[0]:
                observation = "Error de Seguridad: Input inválido."
            else:
                logger.info("Ejecutando herramienta: %s", tool_name)
                try:
                    clean_name = "rag_search" if "rag" in tool_name else tool_name
                    observation = _invoke_tool(self.tools[clean_name], tool_input)
                except Exception as e:
                    observation = f"Error: {e}"

            steps_log.append((StepAction(tool_name, tool_input, response), observation))
            messages.append({"role": "assistant", "content": response})
            messages.append(
                {
                    "role": "user",
                    "content": f"Observation: {observation}\nSi ya tienes el dato necesario, responde ahora con 'Thought:' y 'Final Answer:'.",
                }
            )

        elapsed = time.time() - start_time
        limit_msg = "Límite de pasos alcanzado."
        self.audit_logger.log_audit(query, steps_log, limit_msg, elapsed)
        return AgentResult(
            answer=limit_msg,
            steps=steps_log,
            latency_s=elapsed,
            max_steps_reached=True,
        )


@lru_cache(maxsize=1)
def _get_tools() -> tuple[CalculatorTool, VerificationTool, Any, CycleTool, PrereqTool]:
    return CalculatorTool(), VerificationTool(), get_rag_tool(), CycleTool(), PrereqTool()


@lru_cache(maxsize=1)
def get_default_agent() -> Agent:
    calc, verif, rag, cycle, prereq = _get_tools()
    tools: dict[str, ToolLike] = {
        "calculator": calc,
        "verification": verif,
        "rag_search": rag,
        "plan_ciclo": cycle,
        "plan_prereq": prereq,
    }
    return Agent(
        llm=load_llm(),
        tools=tools,
        grammar=get_react_grammar(),
    )


def run_agent(query: str, history: Sequence[tuple[str, str]] | None = None) -> str:
    """Fachada compatible para ejecutar el agente por defecto."""
    return get_default_agent().run(query, history).answer
