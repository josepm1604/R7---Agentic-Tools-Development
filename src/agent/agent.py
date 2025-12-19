import time
import re
from src.llm.model_loader import load_llm
from src.tools.rag_setup import get_rag_tool
from src.tools.calculator import CalculatorTool
from src.tools.verification import VerificationTool
from src.config import Config
from src.agent.guards import Guardrails
from src.utils.logger import AuditLogger

REACT_SYSTEM_PROMPT = """Eres un asistente inteligente de la UNI.
Para responder, DEBES usar un formato de PENSAMIENTO, ACCIÓN y OBSERVACIÓN.

Tus herramientas disponibles son:
1. calculator: Úsalo para cálculos matemáticos. Input: expresión (ej: 20*4).
2. verification: Úsalo para validar códigos de cursos (ej: CC102). Input: código.
3. rag_search: Úsalo para buscar información de la universidad, cursos o malla. Input: texto de búsqueda.

Formato OBLIGATORIO:
Question: la pregunta del usuario
Thought: debo pensar qué hacer...
Action: nombre_herramienta
Action Input: input_para_herramienta
Observation: resultado de la herramienta
... (repite Thought/Action/Observation si es necesario)
Thought: ya tengo la respuesta final
Final Answer: la respuesta final al usuario

Comienza!
"""


def run_agent(query: str):
    print("   [DEBUG] Iniciando run_agent...")

    # 1. Cargar LLM
    print("   [DEBUG] Cargando LLM...", end=" ")
    try:
        llm = load_llm()
        print("OK.")
    except Exception as e:
        print(f"FALLÓ ({e})")
        raise e

    guards = Guardrails()
    logger = AuditLogger()

    # 2. Inicializar Herramientas
    try:
        print("   [DEBUG] Cargando Calculadora...", end=" ")
        calc = CalculatorTool()
        print(f"OK")

        print("   [DEBUG] Cargando Verificación...", end=" ")
        verif = VerificationTool()
        print(f"OK")

        print("   [DEBUG] Cargando RAG...", end=" ")
        rag = get_rag_tool()
        print(f"OK")
    except Exception as e:
        print(f"\n\n❌ ERROR AL CARGAR HERRAMIENTAS: {e}")
        raise e

    tools_map = {
        "calculator": calc.run,
        "verification": verif.run,
        "rag_search": rag.run,
    }

    prompt_history = f"{REACT_SYSTEM_PROMPT}\nQuestion: {query}\n"
    steps_log = []
    start_time = time.time()
    guards.reset()

    print(f"   [DEBUG] Entrando al bucle ReAct ({Config.MAX_ITERATIONS} pasos)...")

    for i in range(Config.MAX_ITERATIONS):
        # A. PENSAMIENTO
        try:
            # CORRECCIÓN: Pasamos TODOS los stop tokens aquí
            # "Observation:" para el ReAct, "<|im_end|>" para el fin de turno del modelo
            stop_tokens = ["Observation:", "Observation", "<|im_end|>", "User:"]
            response = llm.invoke(prompt_history, stop=stop_tokens)
        except Exception as e:
            return f"Error al invocar LLM: {e}"

        # B. PARSING
        action_match = re.search(r"Action:\s*(.+?)(?:\n|$)", response)
        input_match = re.search(r"Action Input:\s*(.+?)(?:\n|$)", response)

        if "Final Answer:" in response:
            final_ans = response.split("Final Answer:")[-1].strip()
            duration = time.time() - start_time
            logger.log_audit(query, steps_log, final_ans, duration)
            return final_ans

        if not action_match:
            if i > 0:
                final_ans = response.replace("Thought:", "").strip()
                duration = time.time() - start_time
                logger.log_audit(query, steps_log, final_ans, duration)
                return final_ans
            else:
                prompt_history += f"{response}\nThought: No he indicado acción. Debo usar 'Action:' y 'Action Input:'.\n"
                continue

        tool_name = action_match.group(1).strip()
        tool_input = input_match.group(1).strip() if input_match else ""

        # C. GUARDRAILS
        observation = ""
        if not guards.check_and_track(tool_name):
            observation = (
                f"Error de Seguridad: Límite de uso excedido para {tool_name}."
            )
        elif not guards.validate_input(tool_input)[0]:
            observation = "Error de Seguridad: Input inválido."
        else:
            print(f"   --> Ejecutando {tool_name}...")
            try:
                clean_name = "rag_search" if "rag" in tool_name else tool_name
                if clean_name in tools_map:
                    result = tools_map[clean_name](tool_input)
                    observation = str(result)
                else:
                    observation = f"Herramienta {tool_name} no encontrada."
            except Exception as e:
                observation = f"Error: {e}"

        # E. ACTUALIZAR
        class StepAction:
            def __init__(self, t, i, l):
                self.tool = t
                self.tool_input = i
                self.log = l

        step_entry = (StepAction(tool_name, tool_input, response), observation)
        steps_log.append(step_entry)
        prompt_history += f"{response}\nObservation: {observation}\n"

    return "Límite de pasos alcanzado."
