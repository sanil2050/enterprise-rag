from dataclasses import dataclass


MAX_AGENT_STEPS = 3


@dataclass
class AgentPlan:
    use_document_rag: bool
    use_graph_rag: bool
    reason: str


def create_plan(question: str) -> AgentPlan:
    """
    Create the initial retrieval plan.

    This planner is deterministic for now. It does not consume
    an additional Gemini request.
    """

    normalized = question.lower().strip()

    graph_keywords = [
        "who",
        "what benefits",
        "what products",
        "what services",
        "provides",
        "provided by",
        "related to",
        "associated with",
        "belongs to",
        "applies to",
        "available for",
        "connected to",
        "relationship",
        "relationships",
        "depends on",
        "requires",
        "allows",
        "offers",
        "includes",
    ]

    document_keywords = [
        "policy",
        "rule",
        "rules",
        "procedure",
        "process",
        "how much",
        "how many",
        "when",
        "deadline",
        "eligibility",
        "eligible",
        "limit",
        "amount",
        "percentage",
        "percent",
        "requirement",
        "requirements",
        "definition",
        "details",
        "explain",
        "what is",
        "can i",
        "do i",
    ]

    use_graph = any(
        keyword in normalized
        for keyword in graph_keywords
    )

    use_document = any(
        keyword in normalized
        for keyword in document_keywords
    )

    if not use_graph and not use_document:
        return AgentPlan(
            use_document_rag=True,
            use_graph_rag=False,
            reason="Defaulted to document retrieval.",
        )

    if use_graph and not use_document:
        return AgentPlan(
            use_document_rag=False,
            use_graph_rag=True,
            reason="Question appears relationship-oriented.",
        )

    if use_document and not use_graph:
        return AgentPlan(
            use_document_rag=True,
            use_graph_rag=False,
            reason="Question appears document/policy-oriented.",
        )

    return AgentPlan(
        use_document_rag=True,
        use_graph_rag=True,
        reason="Question benefits from both document and graph evidence.",
    )


def needs_additional_tool(
    question: str,
    document_results: list[dict],
    graph_results: list[dict],
    executed_tools: list[str],
) -> str | None:
    """
    Decide whether another retrieval tool should be executed.

    Returns:
        "document_rag"
        "graph_rag"
        None
    """

    has_documents = len(document_results) > 0
    has_graph = len(graph_results) > 0

    # ---------------------------------------------------------
    # If both evidence sources already returned useful results,
    # there is no reason to execute another tool.
    # ---------------------------------------------------------

    if has_documents and has_graph:
        return None

    # ---------------------------------------------------------
    # If GraphRAG was attempted but found nothing, try
    # document retrieval.
    # ---------------------------------------------------------

    if (
        "graph_rag" in executed_tools
        and not has_graph
        and "document_rag" not in executed_tools
    ):
        return "document_rag"

    # ---------------------------------------------------------
    # If document RAG was attempted but found nothing, try
    # GraphRAG.
    # ---------------------------------------------------------

    if (
        "document_rag" in executed_tools
        and not has_documents
        and "graph_rag" not in executed_tools
    ):
        return "graph_rag"

    # ---------------------------------------------------------
    # If only one source has evidence, determine whether the
    # question contains signals that justify the other source.
    # ---------------------------------------------------------

    normalized = question.lower()

    graph_signals = [
        "relationship",
        "relationships",
        "provides",
        "provided by",
        "related to",
        "associated with",
        "depends on",
        "requires",
        "offers",
        "includes",
    ]

    document_signals = [
        "policy",
        "rule",
        "procedure",
        "process",
        "limit",
        "amount",
        "percentage",
        "eligibility",
        "eligible",
        "deadline",
    ]

    if not has_graph and "graph_rag" not in executed_tools:

        if any(
            signal in normalized
            for signal in graph_signals
        ):
            return "graph_rag"

    if not has_documents and "document_rag" not in executed_tools:

        if any(
            signal in normalized
            for signal in document_signals
        ):
            return "document_rag"

    return None