IMAGE_NAME = agentic-r7
VENV_NAME = venv

ifeq ($(OS),Windows_NT)
    PYTHON = $(VENV_NAME)/Scripts/python.exe
else
    PYTHON = $(VENV_NAME)/bin/python3
endif

PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest

# Scripts de evaluación

.PHONY: all install run test eval eval-agent-real experiments golden clean docker-build docker-run setup

all: install run

$(VENV_NAME):
	python -m venv $(VENV_NAME)

install: $(VENV_NAME)
	$(PIP) install -r requirements.txt

setup: install

run:
	@echo "=== Ejecutando Agente ==="
	$(PYTHON) -m src.main

metrics:
	$(PYTHON) -m src.utils.visualizer

test:
	@echo "=== Ejecutando Tests ==="
	$(PYTEST) test/ -v

# Eval: herramientas sin LLM (segundos)
eval:
	$(PYTHON) -m test.eval.run_eval --no-llm

# Eval: agente completo con el LLM real (minutos)
eval-agent-real:
	$(PYTHON) -m test.eval.run_eval

# Experimentos paramétricos (fuzzy_cutoff, RRF, k)
experiments:
	$(PYTHON) -m test.eval.run_experiments

# Regenerar el golden set desde el PDF
golden:
	$(PYTHON) test/eval/build_golden.py

clean:
	@echo "=== Limpiando archivos temporales ==="
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/agent/__pycache__
	rm -rf src/tools/__pycache__
	rm -rf src/llm/__pycache__
	rm -rf src/utils/__pycache__
	rm -rf test/__pycache__
	rm -rf test/unit/__pycache__
	rm -rf test/integration/__pycache__
	rm -rf logs/

docker-build:
	docker build -t $(IMAGE_NAME) .

docker-run:
	docker run --rm -it -v $(PWD)/logs:/app/logs -v $(PWD)/models:/app/models:ro $(IMAGE_NAME)
