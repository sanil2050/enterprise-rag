from app.database.database import SessionLocal
from app.graph.extractor import extract_graph_data, save_graph_data

from sqlalchemy import text


def get_processed_chunk_ids(db):

    rows = db.execute(
        text(
            """
            SELECT DISTINCT chunk_id
            FROM graph_relationships
            WHERE chunk_id IS NOT NULL
            """
        )
    ).fetchall()

    return {row[0] for row in rows}


def main():

    db = SessionLocal()

    try:

        chunks = db.execute(
            text(
                """
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.content,
                    d.filename
                FROM document_chunks dc
                JOIN documents d
                    ON d.id = dc.document_id
                WHERE d.filename = 'leave_policy.pdf'
                ORDER BY dc.id
                LIMIT 20
                """
            )
        ).mappings().all()

        processed_chunk_ids = get_processed_chunk_ids(db)

        print("=" * 70)
        print("RESUMABLE GRAPH EXTRACTION")
        print("=" * 70)

        print(
            f"Total chunks in current test set: {len(chunks)}"
        )

        print(
            f"Already processed: {len(processed_chunk_ids)}"
        )

        for index, chunk in enumerate(chunks, start=1):

            chunk_id = chunk["id"]

            print(
                f"\nProcessing {index}/{len(chunks)}: "
                f"{chunk['filename']} | "
                f"chunk_id={chunk_id}"
            )

            # -------------------------------------------------
            # Skip already processed chunks
            # -------------------------------------------------

            if chunk_id in processed_chunk_ids:

                print("  SKIPPED: already processed")

                continue

            # -------------------------------------------------
            # Gemini extraction
            # -------------------------------------------------

            try:

                graph_data = extract_graph_data(
                    chunk["content"]
                )

            except Exception as exc:

                print(
                    f"  FAILED: "
                    f"{type(exc).__name__}: {exc}"
                )

                # Move to next chunk instead of terminating
                # the entire graph-building process.
                continue

            # -------------------------------------------------
            # Save graph
            # -------------------------------------------------

            try:

                entity_count = len(
                    graph_data.get("entities", [])
                )

                relationship_count = len(
                    graph_data.get("relationships", [])
                )

                save_graph_data(
                    db=db,
                    graph_data=graph_data,
                    document_id=chunk["document_id"],
                    chunk_id=chunk_id,
                )

                db.commit()

                processed_chunk_ids.add(chunk_id)

                print(
                    f"  entities={entity_count}, "
                    f"relationships={relationship_count}"
                )

            except Exception as exc:

                db.rollback()

                print(
                    f"  DATABASE ERROR: "
                    f"{type(exc).__name__}: {exc}"
                )

        # -----------------------------------------------------
        # Final statistics
        # -----------------------------------------------------

        print("\n" + "=" * 70)
        print("GRAPH EXTRACTION COMPLETE")
        print("=" * 70)

        entity_count = db.execute(
            text(
                "SELECT COUNT(*) FROM graph_entities"
            )
        ).scalar()

        relationship_count = db.execute(
            text(
                "SELECT COUNT(*) FROM graph_relationships"
            )
        ).scalar()

        processed_count = db.execute(
            text(
                """
                SELECT COUNT(DISTINCT chunk_id)
                FROM graph_relationships
                WHERE chunk_id IS NOT NULL
                """
            )
        ).scalar()

        print(f"Graph entities: {entity_count}")
        print(f"Graph relationships: {relationship_count}")
        print(f"Processed chunks: {processed_count}")

    finally:

        db.close()


if __name__ == "__main__":
    main()