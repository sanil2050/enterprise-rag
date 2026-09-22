from sqlalchemy.orm import Session

from app.retrieval.keyword_search import keyword_search
from app.retrieval.vector_search import semantic_search


def hybrid_search(
    query: str,
    db: Session,
    top_k: int = 10,
    candidate_k: int = 20,
    rrf_k: int = 60,
    role: str | None = None,
):
    vector_results = semantic_search(
        query=query,
        db=db,
        top_k=candidate_k,
        role=role,
    ) 

    keyword_results = keyword_search(
        query=query,
        db=db,
        top_k=candidate_k,
        role=role,
    ) 

    fused = {}

    # Vector ranking
    for rank, row in enumerate(vector_results, start=1):
        chunk = row[0]
        document = row[1]
        vector_distance = row[2]

        key = chunk.id

        if key not in fused:
            fused[key] = {
                "chunk": chunk,
                "document": document,
                "vector_distance": vector_distance,
                "keyword_rank": 0.0,
                "rrf_score": 0.0,
            }

        fused[key]["rrf_score"] += 1 / (
            rrf_k + rank
        )

    # Keyword ranking
    for rank, row in enumerate(keyword_results, start=1):
        chunk = row[0]
        document = row[1]
        keyword_rank = row[2]

        key = chunk.id

        if key not in fused:
            fused[key] = {
                "chunk": chunk,
                "document": document,
                "vector_distance": None,
                "keyword_rank": keyword_rank,
                "rrf_score": 0.0,
            }

        fused[key]["keyword_rank"] = keyword_rank

        fused[key]["rrf_score"] += 1 / (
            rrf_k + rank
        )

    results = sorted(
        fused.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    return results[:top_k]