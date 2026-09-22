from app.generation.citation_validator import validate_citations


def make_context(document, page, chunk_index, content):
    return [
        {
            "chunk": type(
                "Chunk",
                (),
                {
                    "page_number": page,
                    "chunk_index": chunk_index,
                    "content": content,
                },
            )(),
            "document": type(
                "Document",
                (),
                {
                    "filename": document,
                },
            )(),
        }
    ]


def test_valid_citation_is_grounded_in_retrieved_context():
    context = make_context(
        "leave_policy.pdf",
        3,
        7,
        "Employees receive 20 vacation and personal days per year.",
    )

    generated_result = {
        "answer": "Employees receive 20 vacation and personal days per year.",
        "citations": [
            {
                "citation_id": "S1",
                "document": "leave_policy.pdf",
                "page": 3,
                "chunk": 7,
            }
        ],
    }

    result = validate_citations(generated_result, context)

    assert len(result["citations"]) == 1

    citation = result["citations"][0]

    assert citation["citation_id"] == "S1"
    assert citation["document"] == "leave_policy.pdf"
    assert citation["page"] == 3
    assert citation["chunk"] == 7


def test_fabricated_citation_is_not_grounded():
    context = make_context(
        "leave_policy.pdf",
        3,
        7,
        "Employees receive 20 vacation and personal days per year.",
    )

    generated_result = {
        "answer": "Employees receive 20 vacation and personal days per year.",
        "citations": [
            {
                "citation_id": "S999",
                "document": "secret.pdf",
                "page": 999,
                "chunk": 999,
            }
        ],
    }

    result = validate_citations(generated_result, context)

    assert result["citations"] == []
    assert "could not produce a properly cited answer" in result["answer"]