from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.embedder import (
    BATCH_SIZE,
    generate_embeddings_in_batches,
)
from app.ingestion.page_chunker import chunk_pages
from app.ingestion.pdf_loader import extract_pdf_pages
from app.models.document import Document, DocumentChunk


def ingest_pdf(
    file_path: str,
    db: Session,
) -> Document:

    path = Path(file_path)

    print(f"Ingesting: {path.name}")

    # ---------------------------------------------------------
    # 1. Find existing document
    # ---------------------------------------------------------

    document = (
        db.query(Document)
        .filter(Document.filename == path.name)
        .first()
    )

    # ---------------------------------------------------------
    # 2. Extract PDF page-by-page
    # ---------------------------------------------------------

    pages = extract_pdf_pages(str(path))

    if not pages:
        raise ValueError(
            f"No text could be extracted from {path.name}"
        )

    # ---------------------------------------------------------
    # 3. Create page-aware chunks
    # ---------------------------------------------------------

    chunks = chunk_pages(pages)

    print(
        f"Document has {len(chunks)} total chunks "
        f"across {len(pages)} pages"
    )

    # ---------------------------------------------------------
    # 4. Create document if it doesn't exist
    # ---------------------------------------------------------

    if document is None:

        document = Document(
            filename=path.name,
            title=path.stem,
            document_type="pdf",
        )

        db.add(document)
        db.flush()

        existing_indices = set()

    else:

        existing_indices = {
            row.chunk_index
            for row in (
                db.query(DocumentChunk.chunk_index)
                .filter(
                    DocumentChunk.document_id == document.id
                )
                .all()
            )
        }

        print(
            f"Found {len(existing_indices)} chunks already "
            f"ingested for {path.name}"
        )

    # ---------------------------------------------------------
    # 5. Determine missing chunks
    # ---------------------------------------------------------

    missing = [
        chunk
        for chunk in chunks
        if chunk["chunk_index"] not in existing_indices
    ]

    if not missing:

        print(
            f"{path.name} is already fully ingested. "
            f"Skipping."
        )

        return document

    print(
        f"{len(missing)} chunks remaining to embed "
        f"for {path.name}"
    )

    # ---------------------------------------------------------
    # 6. Embed in batches
    # ---------------------------------------------------------

    for i in range(0, len(missing), BATCH_SIZE):

        batch = missing[i : i + BATCH_SIZE]

        batch_texts = [
            chunk["content"]
            for chunk in batch
        ]

        print(
            f"Embedding batch "
            f"{i // BATCH_SIZE + 1}..."
        )

        embeddings = generate_embeddings_in_batches(
            batch_texts,
            batch_size=BATCH_SIZE,
        )

        # -----------------------------------------------------
        # 7. Store chunks + metadata
        # -----------------------------------------------------

        for chunk, embedding in zip(
            batch,
            embeddings,
        ):

            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk["chunk_index"],
                    page_number=chunk["page_number"],
                    section=None,
                    content=chunk["content"],
                    embedding=embedding,
                )
            )

        # -----------------------------------------------------
        # 8. Commit after every batch
        # -----------------------------------------------------

        db.commit()

        print(
            f"Committed "
            f"{min(i + len(batch), len(missing))}"
            f"/{len(missing)} chunks"
        )

    print(
        f"Successfully ingested {path.name}"
    )

    return document