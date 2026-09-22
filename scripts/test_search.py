from app.database.database import SessionLocal
from app.retrieval.vector_search import semantic_search


def main():
    query = "What is the company's leave policy?"

    db = SessionLocal()

    try:
        results = semantic_search(
            query=query,
            db=db,
            top_k=5,
        )

        print(f"\nQuery: {query}\n")
        print("=" * 80)

        for rank, row in enumerate(results, start=1):
            chunk = row[0]
            document = row[1]
            distance = row[2]

            print(f"\nResult #{rank}")
            print(f"Document : {document.filename}")
            print(f"Page     : {chunk.page_number}")
            print(f"Chunk    : {chunk.chunk_index}")
            print(f"Distance : {distance:.6f}")
            print(f"Content  : {chunk.content[:500]}")
            print("-" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()