from app.database.database import engine
from sqlalchemy import text


def setup_graph():
    with engine.begin() as connection:

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS graph_entities (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(500) NOT NULL,
                    entity_type VARCHAR(100) NOT NULL,
                    normalized_name VARCHAR(500) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(normalized_name, entity_type)
                );
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS graph_relationships (
                    id SERIAL PRIMARY KEY,

                    subject_entity_id INTEGER NOT NULL
                        REFERENCES graph_entities(id)
                        ON DELETE CASCADE,

                    predicate VARCHAR(300) NOT NULL,

                    object_entity_id INTEGER NOT NULL
                        REFERENCES graph_entities(id)
                        ON DELETE CASCADE,

                    document_id INTEGER
                        REFERENCES documents(id)
                        ON DELETE CASCADE,

                    chunk_id INTEGER
                        REFERENCES document_chunks(id)
                        ON DELETE CASCADE,

                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_graph_entities_name
                ON graph_entities(normalized_name);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_graph_relationships_subject
                ON graph_relationships(subject_entity_id);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_graph_relationships_object
                ON graph_relationships(object_entity_id);
                """
            )
        )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_graph_relationships_chunk
                ON graph_relationships(chunk_id);
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_relationship
                ON graph_relationships(
                    subject_entity_id,
                    predicate,
                    object_entity_id,
                    COALESCE(document_id, 0),
                    COALESCE(chunk_id, 0)
                );
                """
            )
        )


if __name__ == "__main__":
    setup_graph()
    print("Graph tables created successfully.")