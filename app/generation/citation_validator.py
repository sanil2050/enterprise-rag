from typing import Any


def validate_citations(
    generated_result: dict[str, Any],
    retrieved_context: list[dict],
) -> dict[str, Any]:
    """
    Validate citation IDs against the evidence supplied to the model.

    If document evidence was retrieved, require at least one valid
    citation in the generated response.
    """

    evidence_by_id = {}

    for index, item in enumerate(retrieved_context, start=1):
        chunk = item["chunk"]
        document = item["document"]

        citation_id = f"S{index}"

        evidence_by_id[citation_id] = {
            "citation_id": citation_id,
            "document": document.filename,
            "page": chunk.page_number,
            "chunk": chunk.chunk_index,
            "excerpt": make_excerpt(chunk.content),
        }

    validated = []

    for citation in generated_result.get("citations", []):
        citation_id = citation.get("citation_id")

        if citation_id not in evidence_by_id:
            continue

        validated.append(evidence_by_id[citation_id])

    answer = generated_result.get("answer", "")

    # Document evidence was supplied, but the model returned no
    # valid citations. Do not allow an unsupported answer through.
    if retrieved_context and answer.strip() and not validated:
        return {
            "answer": (
                "I found relevant document evidence, but I could not "
                "produce a properly cited answer from it."
            ),
            "citations": [],
        }

    return {
        "answer": answer,
        "citations": validated,
    }


def make_excerpt(text: str, max_length: int = 300) -> str:
    text = " ".join(text.split())

    if len(text) <= max_length:
        return text

    return text[:max_length].rsplit(" ", 1)[0] + "..."