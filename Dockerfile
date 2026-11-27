FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para compilar llama-cpp-python si no hay wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código, datos e índice precomputado
COPY src/ ./src/
COPY data/ ./data/
COPY indexes/ ./indexes/

# Usuario no-root y directorio de logs
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/logs /app/models \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "src.main"]
