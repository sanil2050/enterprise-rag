from app.generation.citation_validator import validate_citations


def test_invalid_citation_id_is_removed():
    retrieved_context = [
        {
            "chunk": type(
                "Chunk",
                (),
                {
                    "page_number": 10,
                    "chunk_index": 25,
                    "content": "The security policy requires MFA.",
                },
            )(),
            "document": type(
                "Document",
                (),
                {
                    "filename": "security_policy.pdf",
                },
            )(),
        }
    ]

    generated_result = {
        "answer": "The policy requires MFA.",
        "citations": [
            {
                "citation_id": "S999",
                "document": "secret.pdf",
                "page": 999,
                "chunk": 999,
            }
        ],
    }

    result = validate_citations(generated_result, retrieved_context)

    assert result["citations"] == []
    assert "could not produce a properly cited answer" in result["answer"]


def test_valid_citation_is_preserved():
    retrieved_context = [
        {
            "chunk": type(
                "Chunk",
                (),
                {
                    "page_number": 10,
                    "chunk_index": 25,
                    "content": "The security policy requires MFA.",
                },
            )(),
            "document": type(
                "Document",
                (),
                {
                    "filename": "security_policy.pdf",
                },
            )(),
        }
    ]

    generated_result = {
        "answer": "The policy requires MFA.",
        "citations": [
            {
                "citation_id": "S1",
                "document": "security_policy.pdf",
                "page": 10,
                "chunk": 25,
            }
        ],
    }

    result = validate_citations(generated_result, retrieved_context)

    assert len(result["citations"]) == 1
    assert result["citations"][0]["citation_id"] == "S1"
    assert result["citations"][0]["document"] == "security_policy.pdf"
    assert result["citations"][0]["page"] == 10
    assert result["citations"][0]["chunk"] == 25


def test_uncited_answer_is_blocked_when_document_evidence_exists():
    retrieved_context = [
        {
            "chunk": type(
                "Chunk",
                (),
                {
                    "page_number": 10,
                    "chunk_index": 25,
                    "content": "The security policy requires MFA.",
                },
            )(),
            "document": type(
                "Document",
                (),
                {
                    "filename": "security_policy.pdf",
                },
            )(),
        }
    ]

    generated_result = {
        "answer": "The policy requires MFA.",
        "citations": [],
    }

    result = validate_citations(generated_result, retrieved_context)

    assert result["citations"] == []
    assert "could not produce a properly cited answer" in result["answer"]