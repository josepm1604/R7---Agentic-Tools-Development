import os
import time
import sys
from src.config import Config
from src.agent.graph import app  # Tu cerebro (LangGraph)
from src.agent.guards import Guardrails  # Tu seguridad
from src.utils.logger import AgentLogger


def main():
    # 1. Setup inicial de directorios
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    # 2. Inicializar Guardrails
    guards = Guardrails()

    # Inicializar Logger
    logger = AgentLogger()

    print("╔══════════════════════════════════════════════════════╗")
    print("║   🤖 Sistema Agéntico UNI (Hardware Limitado E2)     ║")
    print("║   🧠 Modelo: Qwen2.5-1.5B (CPU Optimized)            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print("\nEscribe 'exit', 'salir' o 'quit' para terminar.")

    while True:
        try:
            # A. Entrada del Usuario
            user_query = input("\nUsuario> ")

            if user_query.lower() in ["exit", "salir", "quit"]:
                print("👋 Cerrando sistema. ¡Hasta luego!")
                break

            # B. FASE DE SEGURIDAD (Guardrails)
            # Validamos ANTES de tocar el modelo pesado
            is_valid, error_msg = guards.validate_input(user_query)

            if not is_valid:
                print(f"🚫 [BLOQUEADO]: {error_msg}")
                continue  # Saltamos al inicio del bucle sin gastar RAM

            # C. FASE DE EJECUCIÓN (LangGraph)
            print("⏳ Procesando...", end="\r")  # Feedback visual simple
            start_time = time.time()

            # Invocamos el grafo
            # LangGraph maneja el estado internamente
            result = app.invoke({"question": user_query})

            latency = time.time() - start_time

            logger.log_interaction(
                query=user_query, final_state=result, latency=latency
            )

            # D. Obtener respuesta final del estado
            final_answer = result.get("generation", "Error al generar respuesta.")

            # Limpiar línea de "Procesando..."
            sys.stdout.write("\033[K")

            print(f"Agente> {final_answer}")
            print(f"Analyzed in {latency:.2f}s")

        except KeyboardInterrupt:
            # Permite salir con Ctrl+C limpiamente
            print("\n👋 Salida forzada.")
            break
        except Exception as e:
            print(f"\n❌ Error crítico en runtime: {e}")
            logger.log_interaction(
                query=user_query, final_state={}, latency=0, error=str(e)
            )


if __name__ == "__main__":
    main()
