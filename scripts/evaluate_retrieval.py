from app.database.database import SessionLocal
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank


QUESTIONS = [
    "What is the company's leave policy?",
    "How many vacation days do employees receive?",
    "How much bereavement leave is available?",
    "What is the parental leave policy?",
    "What happens to unused vacation days?",
    "What are the summer hours?",
]


def main():
    db = SessionLocal()

    try:
        for question in QUESTIONS:
            print("\n")
            print("=" * 100)
            print(f"QUESTION: {question}")
            print("=" * 100)

            candidates = hybrid_search(
                query=question,
                db=db,
                top_k=20,
                candidate_k=20,
            )

            results = rerank(
                query=question,
                results=candidates,
                top_k=5,
            )

            for index, result in enumerate(results, start=1):
                chunk = result["chunk"]
                document = result["document"]

                print(f"\nResult #{index}")
                print(f"Document     : {document.filename}")
                print(f"Page         : {chunk.page_number}")
                print(f"Chunk        : {chunk.chunk_index}")
                print(f"RRF score    : {result['rrf_score']:.6f}")
                print(f"Rerank score : {result['rerank_score']:.6f}")
                print(f"Content      : {chunk.content[:700]}")
                print("-" * 100)

    finally:
        db.close()


if __name__ == "__main__":
    main()