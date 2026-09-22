from app.ingestion.chunker import chunk_text


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[dict]:

    chunks = []

    global_chunk_index = 0

    for page in pages:

        page_chunks = chunk_text(
            page["text"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in page_chunks:

            chunks.append(
                {
                    "chunk_index": global_chunk_index,
                    "page_number": page["page_number"],
                    "content": chunk,
                }
            )

            global_chunk_index += 1

    return chunks