import re
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Importaciones
from src.llm.model_loader import load_llm
from src.tools.rag_setup import rag_engine
from src.tools.calculator import CalculatorTool
from src.tools.verification import VerificationTool

# Instancias Globales
llm = load_llm()
calc_tool = CalculatorTool()
verif_tool = VerificationTool()


# 1. ESTADO DEL AGENTE
class AgentState(TypedDict):
    question: str
    documents: List[str]
    generation: str
    tool_decision: str  # 'rag' o 'calculator' o 'verification'


# --- NODOS ---


def router_node(state):
    """Nodo 0: Decide qué herramienta usar"""
    print("--- ROUTER ---")
    question = state["question"].lower()

    # 1. ¿Hay un código de curso? (Ej: CC311, MB165)
    # Regex busca 2 letras seguidas de 3 números
    if re.search(r"\b[A-Z]{2}\d{3}\b", question):
        return {"tool_decision": "verification"}

    # 2. ¿Es cálculo matemático?
    elif any(x in question.lower() for x in ["calcular", "suma", "+", "*", "/"]):
        return {"tool_decision": "calculator"}

    # 3. Si no, es pregunta general (RAG)
    else:
        return {"tool_decision": "rag"}


def calculator_node(state):
    """Nodo Calculadora"""
    print("--- CALCULATOR ---")
    question = state["question"]
    try:
        # Asumiendo que tu CalculatorTool tiene un método .run(query)
        result = calc_tool.run(question)
        response = f"El resultado del cálculo es: {result}"
    except Exception as e:
        response = f"Error al calcular: {str(e)}"

    return {"generation": response}


def verification_node(state):
    """Nodo Verificador"""
    print("--- VERIFICATION TOOL ---")
    question = state["question"]
    try:
        # Tu herramienta ya devuelve un string amigable ("APPROVED...", "REJECTED...")
        response = verif_tool.run(question)
    except Exception as e:
        response = f"Error verificando curso: {str(e)}"

    return {"generation": response}


def retrieve_node(state):
    """Nodo RAG 1: Busca documentos"""
    print("--- RETRIEVING ---")
    question = state["question"]
    documents = rag_engine(question)
    return {"documents": documents}


def grader_node(state):
    """Nodo RAG 2: Evalúa relevancia (Self-RAG Lite)"""
    print("--- GRADING ---")
    question = state["question"]
    documents = state.get("documents", [])

    prompt = PromptTemplate(
        template="""Pregunta: {question}
        Documento: {document}
        ¿Es relevante? Responde SI o NO.""",
        input_variables=["question", "document"],
    )
    chain = prompt | llm | StrOutputParser()

    filtered = []
    for d in documents:
        try:
            # Recortamos contenido para velocidad
            content = d.page_content[:400]
            score = chain.invoke({"question": question, "document": content})
            if "SI" in score.upper():
                filtered.append(d)
        except:
            continue

    return {"documents": filtered}


def generate_node(state):
    """Nodo RAG 3: Genera respuesta"""
    print("--- GENERATING ---")
    question = state["question"]
    documents = state.get("documents", [])

    if not documents:
        return {"generation": "No encontré información relevante en los documentos."}

    context = "\n".join([d.page_content for d in documents])
    prompt = f"Contexto: {context}\nPregunta: {question}\nRespuesta:"
    response = llm.invoke(prompt)
    return {"generation": response}


# --- CONSTRUCCIÓN DEL GRAFO ---

workflow = StateGraph(AgentState)

# Agregar Nodos
workflow.add_node("router", router_node)
workflow.add_node("calculator", calculator_node)
workflow.add_node("verification", verification_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grader_node)
workflow.add_node("generate", generate_node)


# Decisión Condicional
def decide_route(state):
    return state["tool_decision"]


# Definir Flujo
workflow.set_entry_point("router")


workflow.add_conditional_edges(
    "router",
    decide_route,
    {
        "calculator": "calculator",
        "verification": "verification",
        "rag": "retrieve",
    },
)

# Caminos lineales
workflow.add_edge("calculator", END)
workflow.add_edge("verification", END)
workflow.add_edge("retrieve", "grade")
workflow.add_edge("grade", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
