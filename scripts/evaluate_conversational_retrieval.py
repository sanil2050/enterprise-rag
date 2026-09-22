from app.database.database import SessionLocal
from app.generation.query_rewriter import rewrite_query
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank


TEST_CASES = [
    {
        "question": "What is the vacation policy?",
        "history": [],
        "expected": [
            ("leave_policy.pdf", 7),
        ],
    },
    {
        "question": "How much can I roll over?",
        "history": [
            {
                "role": "user",
                "content": "What is the vacation policy?",
            },
            {
                "role": "assistant",
                "content": (
                    "Employees receive 20 vacation and personal days "
                    "per year and vacation rolls over up to a maximum "
                    "bank of 27 days."
                ),
            },
        ],
        "expected": [
            ("leave_policy.pdf", 7),
        ],
    },
    {
        "question": "What about parental leave?",
        "history": [],
        "expected": [
            ("leave_policy.pdf", 10),
        ],
    },
    {
        "question": "How much bereavement leave is available?",
        "history": [],
        "expected": [
            ("leave_policy.pdf", 11),
        ],
    },
    {
        "question": "What happens to unused vacation days?",
        "history": [],
        "expected": [
            ("leave_policy.pdf", 7),
        ],
    },
]


def is_relevant(result, expected_chunks):
    document = result["document"].filename
    chunk_index = result["chunk"].chunk_index

    return (document, chunk_index) in expected_chunks


def reciprocal_rank(results, expected_chunks):
    for rank, result in enumerate(results, start=1):
        if is_relevant(result, expected_chunks):
            return 1 / rank

    return 0.0


def main():
    db = SessionLocal()

    try:
        total = len(TEST_CASES)

        recall_at_1 = 0
        recall_at_3 = 0
        recall_at_5 = 0

        reciprocal_ranks = []

        print("=" * 70)
        print("CONVERSATIONAL RAG RETRIEVAL EVALUATION")
        print("=" * 70)

        for index, test_case in enumerate(TEST_CASES, start=1):

            question = test_case["question"]
            history = test_case["history"]

            expected_chunks = set(
                test_case["expected"]
            )

            print(f"\nTest {index}/{total}")
            print(f"Question: {question}")

            # --------------------------------------------------
            # Query rewriting
            # --------------------------------------------------

            if history:
                rewritten_query = rewrite_query(
                    question=question,
                    conversation_history=history,
                )
            else:
                rewritten_query = question

            print(
                f"Retrieval query: {rewritten_query}"
            )

            # --------------------------------------------------
            # Hybrid retrieval
            # --------------------------------------------------

            candidates = hybrid_search(
                query=rewritten_query,
                db=db,
                top_k=20,
                candidate_k=20,
                role="employee",
            )

            # --------------------------------------------------
            # Reranking
            # --------------------------------------------------

            results = rerank(
                query=rewritten_query,
                results=candidates,
                top_k=5,
            )

            # --------------------------------------------------
            # Display results
            # --------------------------------------------------

            for rank, result in enumerate(
                results,
                start=1,
            ):
                document = result["document"].filename
                chunk = result["chunk"]

                marker = ""

                if is_relevant(
                    result,
                    expected_chunks,
                ):
                    marker = "  <-- RELEVANT"

                print(
                    f"  {rank}. "
                    f"{document} | "
                    f"page={chunk.page_number} | "
                    f"chunk={chunk.chunk_index}"
                    f"{marker}"
                )

            # --------------------------------------------------
            # Recall@K
            # --------------------------------------------------

            if any(
                is_relevant(result, expected_chunks)
                for result in results[:1]
            ):
                recall_at_1 += 1

            if any(
                is_relevant(result, expected_chunks)
                for result in results[:3]
            ):
                recall_at_3 += 1

            if any(
                is_relevant(result, expected_chunks)
                for result in results[:5]
            ):
                recall_at_5 += 1

            # --------------------------------------------------
            # MRR
            # --------------------------------------------------

            rr = reciprocal_rank(
                results,
                expected_chunks,
            )

            reciprocal_ranks.append(rr)

            print(
                f"  Reciprocal Rank: {rr:.3f}"
            )

        # ------------------------------------------------------
        # Final metrics
        # ------------------------------------------------------

        mrr = (
            sum(reciprocal_ranks)
            / total
        )

        print("\n" + "=" * 70)
        print("FINAL METRICS")
        print("=" * 70)

        print(
            f"Recall@1: {recall_at_1 / total:.2%}"
        )

        print(
            f"Recall@3: {recall_at_3 / total:.2%}"
        )

        print(
            f"Recall@5: {recall_at_5 / total:.2%}"
        )

        print(
            f"MRR:      {mrr:.3f}"
        )

        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()