from app.database.database import SessionLocal
from app.graph.retriever import graph_search


TEST_QUERIES = [
    "What is the vacation bank limit?",
    "What happens to unused vacation days?",
    "What is the sabbatical policy?",
    "What benefits does 37signals provide?",
]


def main():
    db = SessionLocal()

    try:

        for question in TEST_QUERIES:

            print("\n" + "=" * 80)
            print(f"QUESTION: {question}")
            print("=" * 80)

            results = graph_search(
                query=question,
                db=db,
                max_entities=5,
                max_relationships=10,
            )

            if not results:
                print("No graph results found.")
                continue

            for index, result in enumerate(results, start=1):

                print(
                    f"\n{index}. "
                    f"{result['subject']} "
                    f"--[{result['predicate']}]--> "
                    f"{result['object']}"
                )

                print(
                    f"   Source: "
                    f"{result['document']} | "
                    f"page={result['page']} | "
                    f"chunk={result['chunk']}"
                )

    finally:
        db.close()


if __name__ == "__main__":
    main()