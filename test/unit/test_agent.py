import time
from src.agent.agent import Agent
from src.agent.guards import Guardrails
from src.tools.calculator import CalculatorTool


class _FakeLLM:
    def __init__(self, responses: list[str], delay_s: float = 0.0) -> None:
        self._responses = list(responses)
        self._delay_s = delay_s
        self.calls: list[list[dict[str, str]]] = []

    def create_chat_completion(self, messages, **kwargs):
        if self._delay_s:
            time.sleep(self._delay_s)
        self.calls.append(messages)
        content = self._responses.pop(0)
        return {"choices": [{"message": {"content": content}}]}


class _NoopLogger:
    def __init__(self) -> None:
        self.entries: list[tuple] = []

    def log_audit(self, query, steps, final_answer, latency) -> None:
        self.entries.append((query, steps, final_answer, latency))


def test_agent_direct_final_answer():
    llm = _FakeLLM(["Thought: Ya lo sé.\nFinal Answer: Hola UNI."])
    logger = _NoopLogger()
    agent = Agent(llm=llm, tools={"calculator": CalculatorTool()}, audit_logger=logger)

    res = agent.run("Hola")
    assert res.answer == "Hola UNI."
    assert res.steps == []
    assert not res.timed_out and not res.max_steps_reached
    assert len(logger.entries) == 1


def test_agent_tool_call_then_final_answer():
    llm = _FakeLLM(
        [
            "Thought: Debo calcular.\nAction: calculator\nAction Input: 12*7",
            "Thought: Ya tengo el resultado.\nFinal Answer: 84",
        ]
    )
    logger = _NoopLogger()
    agent = Agent(llm=llm, tools={"calculator": CalculatorTool()}, audit_logger=logger)

    res = agent.run("Cuánto es 12*7?")
    assert res.answer == "84"
    assert len(res.steps) == 1
    assert res.steps[0][0].tool == "calculator"
    assert res.steps[0][1] == "84"


def test_agent_retries_when_first_turn_has_no_action():
    llm = _FakeLLM(
        [
            "Thought: mm...",
            "Thought: Debo calcular.\nAction: calculator\nAction Input: 2+2",
            "Thought: listo\nFinal Answer: 4",
        ]
    )
    agent = Agent(llm=llm, tools={"calculator": CalculatorTool()}, audit_logger=_NoopLogger())

    res = agent.run("2+2")
    assert res.answer == "4"
    assert len(llm.calls) == 3


def test_agent_blocks_rate_limit_and_hits_max_steps():
    llm = _FakeLLM(
        [
            "Thought: calc 1\nAction: calculator\nAction Input: 1+1",
            "Thought: calc 2\nAction: calculator\nAction Input: 2+2",
            "Thought: calc 3\nAction: calculator\nAction Input: 3+3",
            "Thought: calc 4\nAction: calculator\nAction Input: 4+4",
        ]
    )
    agent = Agent(
        llm=llm,
        tools={"calculator": CalculatorTool()},
        guards=Guardrails(),
        audit_logger=_NoopLogger(),
        max_iterations=4,
    )

    res = agent.run("calcula")
    assert res.max_steps_reached
    assert "Herramienta no permitida o límite excedido" in res.steps[-1][1]


def test_agent_timeout():
    llm = _FakeLLM(["Thought: ...\nAction: calculator\nAction Input: 1+1"], delay_s=0.05)
    agent = Agent(
        llm=llm,
        tools={"calculator": CalculatorTool()},
        audit_logger=_NoopLogger(),
        max_execution_time=0.01,
        max_iterations=3,
    )

    res = agent.run("lento")
    assert res.timed_out
    assert "Tiempo máximo" in res.answer


def test_agent_passes_last_3_history_turns():
    llm = _FakeLLM(["Thought: listo\nFinal Answer: ok"])
    agent = Agent(llm=llm, tools={"calculator": CalculatorTool()}, audit_logger=_NoopLogger())
    history = [("q1", "a1"), ("q2", "a2"), ("q3", "a3"), ("q4", "a4")]

    agent.run("q5", history=history)
    sent_contents = [m["content"] for m in llm.calls[0]]
    assert "q1" not in sent_contents
    assert "q2" in sent_contents and "q4" in sent_contents and "q5" in sent_contents
