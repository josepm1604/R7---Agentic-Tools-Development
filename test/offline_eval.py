from rouge_score import rouge_scorer


def calculate_rouge(reference, candidate):
    scorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    scores = scorer.score(reference, candidate)
    return scores


# Golden Set (Preguntas y Respuestas Ideales)
test_set = [
    {
        "q": "¿Qué se ve en el ciclo 1?",
        "ref": "En el ciclo 1 se ven fundamentos de programación.",
    },
    {"q": "¿Cuánto dura el curso?", "ref": "El curso dura 16 semanas."},
]

print("Iniciando Evaluación...")
for test in test_set:
    # 1. Ejecutar Agente
    # response = app.invoke({"question": test["q"]})["generation"]
    response = "En el ciclo 1 se ven fundamentos..."  # Simulado

    # 2. Calcular Métrica
    scores = calculate_rouge(test["ref"], response)
    print(f"Query: {test['q']}")
    print(f"ROUGE-1: {scores['rouge1'].fmeasure:.2f}")
    print("-" * 20)
