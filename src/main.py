import logging
import os
import sys
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent.agent import run_agent
from src.agent.guards import Guardrails
from src.config import Config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO if os.getenv("DEBUG") == "1" else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    guards = Guardrails()
    history: list[tuple[str, str]] = []

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

            valid, msg = guards.validate_input(query)
            if not valid:
                print(f"🚫 {msg}")
                continue

            print("⏳ Pensando...")
            response = run_agent(query, history)
            history.append((query, response))
            print(f"\nAgente> {response}")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 Salida limpia.")
            break
        except Exception:
            print("\n❌ ERROR CRÍTICO DETALLADO:")
            traceback.print_exc()


if __name__ == "__main__":
    main()
