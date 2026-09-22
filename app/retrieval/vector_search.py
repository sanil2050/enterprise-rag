from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.embedder import generate_embedding
from app.models.document import Document, DocumentChunk
from app.retrieval.access_control import get_authorized_document_ids


def semantic_search(
    query: str,
    db: Session,
    top_k: int = 5,
    role: str | None = None,
):
    query_embedding = generate_embedding(query)

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    authorized_document_ids = None

    if role is not None:
        authorized_document_ids = get_authorized_document_ids(
            db=db,
            role=role,
        )

    statement = (
        select(
            DocumentChunk,
            Document,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .order_by(distance)
        .limit(top_k)
    )

    if authorized_document_ids is not None:
        statement = statement.where(
            DocumentChunk.document_id.in_(
                authorized_document_ids
            )
        )

    return db.execute(statement).all()