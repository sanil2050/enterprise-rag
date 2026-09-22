from app.graph.evidence import build_graph_evidence
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank


def document_rag_tool(
    query: str,
    db,
    role: str,
) -> list[dict]:
    """
    Execute the existing hybrid RAG pipeline.
    """

    candidates = hybrid_search(
        query=query,
        db=db,
        top_k=20,
        candidate_k=20,
        role=role,
    )

    results = rerank(
        query=query,
        results=candidates,
        top_k=15,
    )

    return results


def graph_rag_tool(
    query: str,
    db,
    role: str,
) -> list[dict]:
    """
    Execute the GraphRAG retrieval pipeline.
    """

    return build_graph_evidence(
        query=query,
        db=db,
        role=role,
        max_entities=5,
        max_relationships=20,
    )