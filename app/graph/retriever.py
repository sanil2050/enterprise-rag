from sqlalchemy import text
from sqlalchemy.orm import Session

from app.retrieval.access_control import get_authorized_document_ids


def normalize_name(value: str) -> str:
    return " ".join(value.strip().lower().split())


def find_matching_entities(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[dict]:
    """
    Find graph entities whose names appear in the query.

    Entity matching itself is not treated as authorization.
    Authorization is enforced when retrieving relationships
    through their source documents.
    """

    normalized_query = normalize_name(query)

    rows = db.execute(
        text(
            """
            SELECT
                id,
                name,
                entity_type
            FROM graph_entities
            WHERE :query ILIKE '%' || normalized_name || '%'
            ORDER BY LENGTH(normalized_name) DESC
            LIMIT :limit
            """
        ),
        {
            "query": normalized_query,
            "limit": limit,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def graph_search(
    query: str,
    db: Session,
    max_entities: int = 5,
    max_relationships: int = 20,
    role: str | None = None,
) -> list[dict]:
    """
    Retrieve graph relationships connected to entities mentioned
    in the query.

    If a role is provided, only relationships whose source document
    is authorized for that role are returned.
    """

    entities = find_matching_entities(
        db=db,
        query=query,
        limit=max_entities,
    )

    if not entities:
        return []

    entity_ids = [entity["id"] for entity in entities]

    # ---------------------------------------------------------
    # Authorization
    # ---------------------------------------------------------

    authorized_document_ids = None

    if role is not None:
        authorized_document_ids = get_authorized_document_ids(
            db=db,
            role=role,
        )

        if not authorized_document_ids:
            return []

    # ---------------------------------------------------------
    # Graph relationship retrieval
    # ---------------------------------------------------------

    if role is None:
        rows = db.execute(
            text(
                """
                SELECT
                    gr.id AS relationship_id,

                    subject.id AS subject_id,
                    subject.name AS subject,
                    subject.entity_type AS subject_type,

                    gr.predicate,

                    object_entity.id AS object_id,
                    object_entity.name AS object,
                    object_entity.entity_type AS object_type,

                    d.filename,
                    dc.page_number,
                    dc.chunk_index,
                    dc.content

                FROM graph_relationships gr

                JOIN graph_entities subject
                    ON subject.id = gr.subject_entity_id

                JOIN graph_entities object_entity
                    ON object_entity.id = gr.object_entity_id

                JOIN documents d
                    ON d.id = gr.document_id

                JOIN document_chunks dc
                    ON dc.id = gr.chunk_id

                WHERE
                    (
                        gr.subject_entity_id = ANY(:entity_ids)
                        OR
                        gr.object_entity_id = ANY(:entity_ids)
                    )

                ORDER BY gr.id

                LIMIT :limit
                """
            ),
            {
                "entity_ids": entity_ids,
                "limit": max_relationships,
            },
        ).mappings().all()

    else:
        rows = db.execute(
            text(
                """
                SELECT
                    gr.id AS relationship_id,

                    subject.id AS subject_id,
                    subject.name AS subject,
                    subject.entity_type AS subject_type,

                    gr.predicate,

                    object_entity.id AS object_id,
                    object_entity.name AS object,
                    object_entity.entity_type AS object_type,

                    d.filename,
                    dc.page_number,
                    dc.chunk_index,
                    dc.content

                FROM graph_relationships gr

                JOIN graph_entities subject
                    ON subject.id = gr.subject_entity_id

                JOIN graph_entities object_entity
                    ON object_entity.id = gr.object_entity_id

                JOIN documents d
                    ON d.id = gr.document_id

                JOIN document_chunks dc
                    ON dc.id = gr.chunk_id

                WHERE
                    (
                        gr.subject_entity_id = ANY(:entity_ids)
                        OR
                        gr.object_entity_id = ANY(:entity_ids)
                    )
                    AND
                    gr.document_id = ANY(:authorized_document_ids)

                ORDER BY gr.id

                LIMIT :limit
                """
            ),
            {
                "entity_ids": entity_ids,
                "authorized_document_ids": authorized_document_ids,
                "limit": max_relationships,
            },
        ).mappings().all()

    results = []

    for row in rows:
        results.append(
            {
                "relationship_id": row["relationship_id"],
                "subject": row["subject"],
                "subject_type": row["subject_type"],
                "predicate": row["predicate"],
                "object": row["object"],
                "object_type": row["object_type"],
                "document": row["filename"],
                "page": row["page_number"],
                "chunk": row["chunk_index"],
                "content": row["content"],
            }
        )

    return results