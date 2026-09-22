from app.database.database import SessionLocal
from sqlalchemy import text


def main():
    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # Show entities
        # ---------------------------------------------------------

        print("\n")
        print("=" * 80)
        print("GRAPH ENTITIES")
        print("=" * 80)

        entities = db.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    entity_type
                FROM graph_entities
                ORDER BY id
                LIMIT 100
                """
            )
        ).mappings().all()

        if not entities:
            print("No entities found.")

        else:
            for entity in entities:
                print(
                    f"{entity['id']:4} | "
                    f"{entity['entity_type']:15} | "
                    f"{entity['name']}"
                )

        # ---------------------------------------------------------
        # Show relationships
        # ---------------------------------------------------------

        print("\n")
        print("=" * 80)
        print("GRAPH RELATIONSHIPS")
        print("=" * 80)

        relationships = db.execute(
            text(
                """
                SELECT
                    ge1.name AS subject,
                    ge1.entity_type AS subject_type,
                    gr.predicate,
                    ge2.name AS object,
                    ge2.entity_type AS object_type,
                    d.filename,
                    dc.page_number,
                    dc.chunk_index
                FROM graph_relationships gr

                JOIN graph_entities ge1
                    ON ge1.id = gr.subject_entity_id

                JOIN graph_entities ge2
                    ON ge2.id = gr.object_entity_id

                JOIN documents d
                    ON d.id = gr.document_id

                JOIN document_chunks dc
                    ON dc.id = gr.chunk_id

                ORDER BY gr.id
                LIMIT 100
                """
            )
        ).mappings().all()

        if not relationships:
            print("No relationships found.")

        else:
            for relationship in relationships:
                print(
                    f"{relationship['subject']} "
                    f"--[{relationship['predicate']}]--> "
                    f"{relationship['object']}"
                )

                print(
                    f"    Source: "
                    f"{relationship['filename']} | "
                    f"page={relationship['page_number']} | "
                    f"chunk={relationship['chunk_index']}"
                )

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------

        entity_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM graph_entities
                """
            )
        ).scalar()

        relationship_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM graph_relationships
                """
            )
        ).scalar()

        print("\n")
        print("=" * 80)
        print("GRAPH SUMMARY")
        print("=" * 80)

        print(f"Total entities:       {entity_count}")
        print(f"Total relationships:  {relationship_count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()