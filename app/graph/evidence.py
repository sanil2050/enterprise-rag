from app.graph.retriever import graph_search


def build_graph_evidence(
    query: str,
    db,
    role: str | None = None,
    max_entities: int = 5,
    max_relationships: int = 20,
) -> list[dict]:
    """
    Retrieve authorized graph relationships and convert them
    into structured evidence for the generation layer.
    """

    relationships = graph_search(
        query=query,
        db=db,
        max_entities=max_entities,
        max_relationships=max_relationships,
        role=role,
    )

    evidence = []

    for index, relationship in enumerate(relationships, start=1):
        evidence.append(
            {
                "graph_id": f"G{index}",
                "subject": relationship["subject"],
                "subject_type": relationship["subject_type"],
                "predicate": relationship["predicate"],
                "object": relationship["object"],
                "object_type": relationship["object_type"],
                "document": relationship["document"],
                "page": relationship["page"],
                "chunk": relationship["chunk"],
                "content": relationship["content"],
            }
        )

    return evidence