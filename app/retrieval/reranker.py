from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model = CrossEncoder(MODEL_NAME)


def rerank(
    query: str,
    results: list[dict],
    top_k: int = 5,
) -> list[dict]:
    if not results:
        return []

    pairs = [
        (
            query,
            result["chunk"].content,
        )
        for result in results
    ]

    scores = _model.predict(pairs)

    for result, score in zip(results, scores):
        result["rerank_score"] = float(score)

    results.sort(
        key=lambda item: item["rerank_score"],
        reverse=True,
    )

    return results[:top_k]