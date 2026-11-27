# Project R7: Agentic Tools Workflow

Agente conversacional local sobre el plan de estudios 2018 de la UNI, capaz de orquestar herramientas externas (catálogo estructurado, RAG, verificación de matrícula y calculadora segura) mediante un bucle ReAct en CPU.

## Arquitectura del Sistema

Agente ReAct (Thought -> Action -> Observation) sobre el plan de estudios de la UNI, ejecutado en CPU.

- **LLM**: `qwen2.5-3b-instruct-q4_k_m.gguf` vía llama.cpp (descargar a `models/`). Una gramática GBNF (`USE_GRAMMAR=1`) fuerza el formato ReAct.
- **Agente** (`src/agent/agent.py`): bucle ReAct manual, memoria de los últimos 3 turnos, guardrails y límites por herramienta (`guards.py`).
- **Herramientas**:
  - `rag_search`: LlamaIndex + embeddings `all-MiniLM-L6-v2`, con coincidencia exacta por nombre de curso.
  - `plan_ciclo`: cursos de un ciclo y total de créditos (catálogo estructurado, sin LLM).
  - `plan_prereq`: cadena completa de prerrequisitos.
  - `calculator`: aritmética segura.
  - `verification`: mock de elegibilidad de matrícula.
- **Observabilidad**: trazas de auditoría en `logs/audit_traces.jsonl`.

## Instalación y Ejecución

Usando el archivo `Makefile` incluido para gestionar el ciclo de vida de la aplicación. En este caso se ha usado un entorno virtual de python y no Docker.

1. Entorno Local

Crear entorno virtual e instalar dependencias:

```Bash
make install
```

Ejecutar el agente en modo interactivo (CLI):

```Bash
make run
```

2. Ejecución con Docker

Para garantizar que el entorno es idéntico al de desarrollo, construir la imagen:

```Bash
make docker-build
```

Ejecutar el contenedor:

```Bash
make docker-run
```

## Uso de Agentes

Tests unitarios (parser del PDF, herramientas, guardrails):

```Bash
make test
```

Harness de evaluación (golden set generado desde el PDF con `make golden`):

```Bash
make eval              # solo herramientas, sin LLM (segundos)
make eval-agent-real   # agente completo con el LLM real (minutos); guarda test/eval/results/*.json
```

Para comparar sin gramática: `USE_GRAMMAR=0 make eval-agent-real`.

## Video de Ejecución

El enlace al video de ejecución se encuentra en `docs/video.txt`.

## Informe

El informe del E1 está en `docs/Informe.pdf`.
