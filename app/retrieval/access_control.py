from sqlalchemy import text
from sqlalchemy.orm import Session


def get_authorized_document_ids(
    db: Session,
    role: str,
) -> list[int]:
    statement = text(
        """
        SELECT document_id
        FROM document_access
        WHERE role = :role
        """
    )

    rows = db.execute(
        statement,
        {"role": role},
    ).fetchall()

    return [row[0] for row in rows]