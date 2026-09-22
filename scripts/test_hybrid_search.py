from app.database.database import SessionLocal
from app.retrieval.hybrid_search import hybrid_search


def main():
    query = "What is the company's leave policy?"

    db = SessionLocal()

    try:
        results = hybrid_search(
            query=query,
            db=db,
            top_k=5,
        )

        print(f"\nQuery: {query}\n")
        print("=" * 80)

        for rank, result in enumerate(results, start=1):
            chunk = result["chunk"]
            document = result["document"]

            print(f"\nResult #{rank}")
            print(f"Document       : {document.filename}")
            print(f"Page           : {chunk.page_number}")
            print(f"Chunk          : {chunk.chunk_index}")
            print(f"Vector distance: {result['vector_distance']}")
            print(f"Keyword rank   : {result['keyword_rank']:.6f}")
            print(f"RRF score      : {result['rrf_score']:.6f}")
            print(f"Content        : {chunk.content[:500]}")
            print("-" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()