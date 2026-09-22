from app.generation.query_rewriter import rewrite_query


history = [
    {
        "role": "user",
        "content": "What is the parental leave policy?",
    },
    {
        "role": "assistant",
        "content": (
            "Primary caregivers can receive up to 16 weeks "
            "of parental leave at 100% pay."
        ),
    },
]

question = "Is that paid?"

print("Starting query rewriter test...")

try:
    rewritten = rewrite_query(
        question=question,
        conversation_history=history,
    )

    print("\nOriginal:")
    print(question)

    print("\nRewritten:")
    print(rewritten)

except Exception as exc:
    print("\nQuery rewriter failed:")
    print(type(exc).__name__)
    print(str(exc))