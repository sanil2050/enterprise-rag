from app.database.database import SessionLocal
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank
from app.generation.gemini_generator import generate_answer


def main():
    question = "What is the company's leave policy?"

    db = SessionLocal()

    try:
        candidates = hybrid_search(
            query=question,
            db=db,
            top_k=20,
            candidate_k=20,
        )

        results = rerank(
            query=question,
            results=candidates,
            top_k=15,
        )

        result = generate_answer(
            question=question,
            context=results,
        )

        print("\n" + "=" * 80)
        print("QUESTION")
        print("=" * 80)
        print(question)

        print("\n" + "=" * 80)
        print("ANSWER")
        print("=" * 80)
        print(result["answer"])

        print("\n" + "=" * 80)
        print("CITATIONS")
        print("=" * 80)

        for citation in result["citations"]:
            print(
                f"{citation['citation_id']} -> "
                f"{citation['document']}, "
                f"page {citation['page']}, "
                f"chunk {citation['chunk']}"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()