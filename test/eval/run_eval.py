"""Harness de evaluación.

  python -m test.eval.run_eval --no-llm        # solo herramientas (segundos, sin LLM)
  python -m test.eval.run_eval                 # extremo a extremo con el LLM real
  python -m test.eval.run_eval --category cycle --limit 3

Separa dos métricas: la herramienta devuelve el dato (tool_ok) y el agente responde bien (e2e_ok),
para saber si un fallo es del recuperador o del LLM. Guarda test/eval/results/<fecha>.json.
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)
from src.config import Config  # noqa: E402
from src.tools.catalog import norm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def check(text: str, case: dict) -> bool:
    t = norm(text)
    ok_all = all(re.search(p, t) for p in case.get("expect_all", []))
    any_ = case.get("expect_any")
    return ok_all and (not any_ or any(a in t for a in any_))


def last_tools() -> list:
    try:
        with open(Config.LOG_AUDIT_PATH, encoding="utf-8") as f:
            return [s["tool"] for s in json.loads(f.readlines()[-1])["trace"]]
    except (OSError, IndexError, KeyError, ValueError):
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--category")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    cases = json.load(open(os.path.join(HERE, "golden.json"), encoding="utf-8"))
    if a.category:
        cases = [c for c in cases if c["category"] == a.category]
    if a.limit:
        cases = cases[: a.limit]

    from src.agent.agent import _get_tools

    calc, verif, rag, cycle, prereq = _get_tools()
    tools = {
        "calculator": calc,
        "verification": verif,
        "rag_search": rag,
        "plan_ciclo": cycle,
        "plan_prereq": prereq,
    }

    if not a.no_llm:
        from src.agent.agent import run_agent

    results = []
    for c in cases:
        r = {"id": c["id"], "category": c["category"]}
        r["tool_ok"] = check(tools[c["tool"]].run(c["tool_input"]), c) if not c.get("skip_tool_check") else None
        if not a.no_llm:
            t0 = time.time()
            ans = run_agent(c["query"])
            r.update(latency=round(time.time() - t0, 1), answer=ans[:300], e2e_ok=check(ans, c))
            r["right_tool"] = c["tool"] in last_tools()
        results.append(r)
        print(f"{c['id']:<22} tool={r['tool_ok']!s:<5}" + (f" e2e={r['e2e_ok']!s:<5} {r['latency']}s" if not a.no_llm else ""))

    def rate(rows, k):
        vals = [x[k] for x in rows if x.get(k) is not None]
        return f"{sum(vals)}/{len(vals)}" if vals else "-"

    print("\n=== Resumen ===")
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    for cat, rows in by_cat.items():
        line = f"{cat:<9} tool_ok {rate(rows, 'tool_ok'):<6}"
        if not a.no_llm:
            line += f" e2e_ok {rate(rows, 'e2e_ok'):<6} right_tool {rate(rows, 'right_tool')}"
        print(line)
    print(f"TOTAL     tool_ok {rate(results, 'tool_ok')}", end="")
    if not a.no_llm:
        print(f"  e2e_ok {rate(results, 'e2e_ok')}  right_tool {rate(results, 'right_tool')}  latencia media {statistics.mean(r['latency'] for r in results):.1f}s", end="")
    print()

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out = os.path.join(HERE, "results", datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    json.dump({"model": Config.MODEL_NAME, "grammar": Config.USE_GRAMMAR, "results": results}, open(out, "w"), ensure_ascii=False, indent=1)
    print("Guardado:", out)


if __name__ == "__main__":
    main()
