from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.retrieval.access_control import get_authorized_document_ids


def keyword_search(
    query: str,
    db: Session,
    top_k: int = 20,
    role: str | None = None,
):  
    authorized_document_ids = None

    if role is not None:
        authorized_document_ids = get_authorized_document_ids(
            db=db,
            role=role,
        )
    
    search_vector = func.to_tsvector(
        "english",
        DocumentChunk.content,
    )

    search_query = func.plainto_tsquery(
        "english",
        query,
    )

    keyword_rank = func.ts_rank(
        search_vector,
        search_query,
    )

    statement = (
        select(
            DocumentChunk,
            Document,
            keyword_rank.label("keyword_rank"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        )
        .where(
            search_vector.op("@@")(search_query)
        )
    )

    if authorized_document_ids is not None:
        statement = statement.where(
            DocumentChunk.document_id.in_(
                authorized_document_ids
            )
        )

    statement = (
        statement
        .order_by(keyword_rank.desc())
        .limit(top_k)
    ) 

    return db.execute(statement).all()