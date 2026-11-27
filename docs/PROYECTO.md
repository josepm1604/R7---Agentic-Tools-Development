# Proyecto R7: Agentic Tools — Agente del plan de estudios UNI

Documento de estado: cómo era el proyecto, cómo es ahora y qué falta.
Fecha de esta revisión: 2026-11-25.

## 1. Qué es

Un agente conversacional que responde preguntas sobre el plan de estudios 2018 de la UNI
(`data/PLAN DE ESTUDIOS-2018-N6-CON ENLACE DE LOS SILABOS.pdf`) usando herramientas externas
(RAG, calculadora, catálogo estructurado). Corre en CPU, sin GPU y sin APIs externas.

Equipo de referencia: Ryzen AI 9 365, 8 hilos, 7.8 GB de RAM, WSL2, sin GPU NVIDIA.

---

## 2. Antes

Se distinguen dos momentos previos: la entrega E1 y el estado del repositorio al iniciar esta
revisión (commit `f63dba9`), que era una transición a medias hacia E2.

### 2.1 Entrega E1 (baseline)

| Aspecto | E1 |
|---|---|
| Enrutamiento | Determinista por reglas (`core.py`): código de curso -> verificación, cálculo -> calculadora, resto -> RAG |
| LLM | `flan-t5-large`, solo redacta la respuesta final |
| RAG | FAISS + `all-MiniLM-L6-v2` |
| Herramientas | Calculadora, RAG, verificación (mock) |
| Observabilidad | Logs JSONL (`logs/execution.jsonl`) |

### 2.2 Estado al iniciar esta revisión (transición a E2)

- **Dos agentes conviviendo:** `core.py` (router de E1) y `agent.py` (bucle ReAct de E2). `main.py` usaba el segundo.
- **Dos loggers** (`AgentLogger` y `AuditLogger`) y **tres implementaciones de RAG** (Chroma, FAISS/LangChain y LlamaIndex).
- **Modelo:** `qwen2.5-1.5b-instruct` configurado, pero el archivo no estaba en el repositorio (`models/` no existía), así que el agente no arrancaba.
- **Rendimiento:** los logs muestran 72 a 96 s por consulta RAG.
- **Carga repetida:** `run_agent` recargaba el LLM y el RAG en cada pregunta.
- **Calidad:** respuestas como "No tengo esa información" con el dato presente en el índice.
- **Documentación y tests desfasados:** el README describía E1; `test_rag.py` importaba un `RAGTool` que ya no existía; `evaluate_agent.py` importaba `src.agent.graph`, inexistente; 4 tests de la calculadora fallaban.

### 2.3 Defectos encontrados en esa base

| # | Defecto | Efecto |
|---|---|---|
| 1 | El parser leía créditos desde la columna 6 (`T. H.`, horas totales) en lugar de la 8 (`Créditos`) | **Todos** los créditos del índice estaban mal (Física I figuraba con 6; el PDF dice 5) |
| 2 | `Guardrails.check_and_track` convertía `rag_search` en `rag`, pero `Config.MAX_TOOL_CALLS` usa `rag_search` | El límite de llamadas al RAG nunca se aplicaba |
| 3 | El prompt incluía `Input: texto de búsqueda` | El modelo copiaba esa frase literal como consulta y entraba en bucle hasta agotar los 8 pasos |
| 4 | Embeddings en inglés (MiniLM) | La consulta "Física I" recuperaba electivos sin relación |
| 5 | `repetition_penalty` no es un parámetro de llama.cpp | Se ignoraba silenciosamente |
| 6 | Variable `rrequisito` (typo) en el parser | Posible `NameError` si ninguna columna parecía un prerrequisito |

---

## 3. Ahora

### 3.1 Arquitectura

```
main.py (CLI, memoria de 3 turnos)
   └─ run_agent()  ── bucle ReAct (Thought / Action / Observation), máx. 8 pasos
        ├─ LLM: Qwen2.5-3B-Instruct Q4_K_M (llama.cpp, CPU) + gramática GBNF
        ├─ Guardrails: validación de entrada y límite de llamadas por herramienta
        └─ Herramientas
             ├─ rag_search   LlamaIndex + MiniLM; coincidencia exacta por nombre de curso primero
             ├─ plan_ciclo   cursos de un ciclo + total de créditos (catálogo, sin LLM)
             ├─ plan_prereq  cadena completa de prerrequisitos (catálogo, sin LLM)
             ├─ calculator   aritmética segura
             └─ verification mock de elegibilidad (catálogo ficticio CS101...)
```

Archivos principales:

| Ruta | Función |
|---|---|
| `src/agent/agent.py` | Bucle ReAct, prompt, memoria, herramientas cacheadas |
| `src/agent/guards.py` | Guardrails |
| `src/llm/model_loader.py` | Carga única del LLM y gramática ReAct |
| `src/tools/rag_loader_uni.py` | Parser del PDF (tablas -> documentos con metadatos) |
| `src/tools/rag_setup.py` | Índice LlamaIndex y herramienta `rag_search` |
| `src/tools/catalog.py` | Catálogo estructurado, `plan_ciclo` y `plan_prereq` |
| `test/eval/` | Harness de evaluación (golden set + runner) |
| `test/unit/` | Tests unitarios |

### 3.2 Cambios realizados

**Modelo y rendimiento**
- Modelo cambiado a Qwen2.5-3B-Instruct Q4_K_M (~2 GB), elegido por tamaño según la RAM disponible.
- `CPU_NUM_THREADS` usa `os.cpu_count()` en lugar de 4 fijos.
- LLM y herramientas se cargan una sola vez por proceso (`lru_cache`).
- `repeat_penalty` en lugar del parámetro inexistente; `n_batch=512`.
- RAG: `k` de modo lista bajó de 15 a 8 y la salida se limita a 2500 caracteres.

**Corrección de defectos** (los 6 de la sección 2.3): parser de créditos, guardrail de RAG, prompt con ejemplos concretos, coincidencia exacta por nombre de curso, parámetro de penalización y typo del parser. El índice `indexes/llama_index/` fue regenerado.

**Capacidades nuevas**
- Herramientas `plan_ciclo` y `plan_prereq`, exactas y sin LLM.
- Gramática GBNF que fuerza el formato ReAct (activable con `USE_GRAMMAR`).
- Memoria de los últimos 3 turnos en la CLI.
- Respuesta explícita "No encuentro esa información" cuando la observación no contiene el dato.

**Calidad de ingeniería**
- Harness de evaluación con golden set generado desde el PDF (24 casos: créditos, prerrequisitos, ciclos, cálculo y un caso sin respuesta). Separa `tool_ok` (la herramienta devuelve el dato) de `e2e_ok` (el agente responde bien).
- 20 tests unitarios, incluidas regresiones de los defectos 1 y 2.
- Código obsoleto eliminado: `core.py`, `rag.py`, `rag_index.py`, `rag_retriever*.py`, `evaluate*.py`, `test_rag.py`.
- Makefile y README actualizados a E2.

### 3.3 Resultados medidos

Todas las cifras son de una sola ejecución, no promedios.

| Consulta | Antes | Ahora |
|---|---|---|
| Créditos de Física I | 72 s, "No tengo esa información" | 13 s, "6 créditos" (dato incorrecto por el defecto 1; tras corregirlo, la herramienta devuelve 5) |
| Cálculo `12*7` | no medido | ~4 s, "84" |
| Cursos del segundo ciclo (antes de `plan_ciclo`) | 96 s | 15 s, pero con respuesta incorrecta |

Evaluación de herramientas sin LLM (`make eval`): **23 de 23**.

La evaluación extremo a extremo con LLM real (`make eval-agent-real`), con y sin gramática,
se lanzó pero **sus resultados no están incluidos aquí**. Quedan en `test/eval/results/`.
Hasta revisarlos no hay cifras de exactitud ni de latencia del agente completo con las
herramientas nuevas.

### 3.4 Cómo ejecutarlo

```bash
make install          # venv + dependencias
# descargar models/qwen2.5-3b-instruct-q4_k_m.gguf (Hugging Face: Qwen/Qwen2.5-3B-Instruct-GGUF)
make run              # CLI interactiva
make test             # tests unitarios
make eval             # herramientas, sin LLM
make eval-agent-real  # agente completo
make golden           # regenerar el golden set desde el PDF
```

---

## 4. Lo que falta

Ordenado por prioridad. Lo marcado como "no verificado" son hipótesis, no resultados.

### Alta prioridad
1. **Revisar y fijar la línea base del harness.** Leer los resultados de `test/eval/results/` con y sin gramática, decidir si `USE_GRAMMAR` queda activo y registrar la exactitud y la latencia reales.
2. **Conectar `verification` al catálogo real.** Hoy usa un catálogo ficticio (`CS101`, `MA101`) y su regex `[A-Z]{2}\d{3}` no reconoce códigos reales como `BFI01` o `CC112`. Debería validar prerrequisitos contra `catalog.py` y un historial de cursos aprobados del estudiante.
3. **Ampliar el golden set.** 24 casos es una muestra pequeña. Faltan preguntas de seguimiento (memoria), preguntas ambiguas, nombres con errores ortográficos y consultas por tipo (obligatorio/electivo).

### Media prioridad
4. **Consultas de lista con filtros combinados** ("electivos de especialidad de 6 créditos"): ampliar el catálogo con una herramienta de filtro por ciclo, tipo y créditos.
5. **Embeddings multilingües** (por ejemplo `paraphrase-multilingual-MiniLM-L12-v2`) o reranking. Obliga a reindexar y descargar otro modelo.
6. **Salida del RAG sin ruido:** para consultas sin coincidencia de nombre aún aparecen `Context information is below` y metadatos.
7. **Streaming de tokens** en la CLI para mejorar la percepción de espera.
8. **Medir el prompt caching** de llama.cpp entre pasos del bucle (no verificado que ya se aproveche).
9. **Comparar Qwen2.5-7B** (~4.7 GB) contra el 3B en el harness. Con 7.8 GB de RAM compartida con WSL queda justo; no probado.

### Baja prioridad
10. **Logs y visualizador:** `core.py` era el único que usaba `AgentLogger` y escribía `logs/execution.jsonl`. Con él eliminado, `src/utils/visualizer.py` (`make metrics`) puede quedar sin datos o roto; no lo revisé.
11. **Docker:** el `Dockerfile` no se revisó para el modelo nuevo ni para `llama-cpp-python`.
12. **`test/offline_eval.py`** depende de `rouge_score`, que no está en `requirements.txt`.
13. **`pytest.ini` está en `.gitignore`**, por lo que la configuración de tests no se versiona.
14. **Fijar versiones** en `requirements.txt` (hoy sin versiones).

### Límites conocidos
- El corte de salida del RAG a 2500 caracteres es un atajo; puede perder información en listas largas.
- El parser depende del formato de tabla del PDF actual. Otro formato o un PDF nuevo requiere revisar las columnas.
- Un modelo de 3B puede fallar en razonamiento de varios pasos; la gramática reduce errores de formato, no de contenido.
