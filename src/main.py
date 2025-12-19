import os
import sys
import time
import traceback  # <--- NUEVO: Para ver el error real

# Asegurar path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.agent.agent import run_agent
from src.agent.guards import Guardrails


def main():
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    guards = Guardrails()

    print("\n" + "=" * 60)
    print(" 🤖 AGENTE UNI AUTÓNOMO (E2: ReAct Manual)")
    print("    Modo: White-Box Loop (Debug Mode)")
    print("=" * 60)
    print(" Escribe 'exit' para salir.\n")

    while True:
        try:
            query = input("\nUsuario> ")
            if query.lower() in ["exit", "salir", "quit"]:
                print("👋 Hasta luego.")
                break

            # Guardrail de entrada
            valid, msg = guards.validate_input(query)
            if not valid:
                print(f"🚫 {msg}")
                continue

            print("⏳ Pensando...")

            # Ejecutar Agente Manual
            response = run_agent(query)

            # Mostrar Respuesta
            print(f"\nAgente> {response}")

        except KeyboardInterrupt:
            print("\n👋 Salida forzada.")
            break
        except Exception:
            # <--- NUEVO: Imprimir el error completo
            print("\n❌ ERROR CRÍTICO DETALLADO:")
            traceback.print_exc()


if __name__ == "__main__":
    main()
