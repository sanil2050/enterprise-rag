from app.database.database import SessionLocal
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank


def main():
    query = "What is the company's leave policy?"

    db = SessionLocal()

    try:
        candidates = hybrid_search(
            query=query,
            db=db,
            top_k=20,
            candidate_k=20,
        )

        print(f"\nHybrid candidates: {len(candidates)}")

        results = rerank(
            query=query,
            results=candidates,
            top_k=5,
        )

        print(f"Reranked results: {len(results)}")
        print("=" * 80)

        for rank, result in enumerate(results, start=1):
            chunk = result["chunk"]
            document = result["document"]

            print(f"\nResult #{rank}")
            print(f"Document    : {document.filename}")
            print(f"Page        : {chunk.page_number}")
            print(f"Chunk       : {chunk.chunk_index}")
            print(f"RRF score   : {result['rrf_score']:.6f}")
            print(f"Rerank score: {result['rerank_score']:.6f}")
            print(f"Content     : {chunk.content[:500]}")
            print("-" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()