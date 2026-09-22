import time

from app.agent.planner import (
    MAX_AGENT_STEPS,
    create_plan,
    needs_additional_tool,
)
from app.agent.tools import (
    document_rag_tool,
    graph_rag_tool,
)


def run_agent(
    question: str,
    rewritten_query: str,
    db,
    role: str,
) -> dict:
    start_time = time.perf_counter()

    plan = create_plan(question)

    document_results = []
    graph_results = []

    executed_tools = []
    tool_trace = []

    document_latency_ms = 0.0
    graph_latency_ms = 0.0

    # ---------------------------------------------------------
    # Initial planned document retrieval
    # ---------------------------------------------------------
    if plan.use_document_rag:
        tool_start = time.perf_counter()

        document_results = document_rag_tool(
            query=rewritten_query,
            db=db,
            role=role,
        )

        document_latency_ms += round(
            (time.perf_counter() - tool_start) * 1000,
            2,
        )

        executed_tools.append("document_rag")

        tool_trace.append({
            "step": len(tool_trace) + 1,
            "tool": "document_rag",
            "results": len(document_results),
            "latency_ms": document_latency_ms,
        })

    # ---------------------------------------------------------
    # Initial planned graph retrieval
    # ---------------------------------------------------------
    if plan.use_graph_rag and len(executed_tools) < MAX_AGENT_STEPS:
        tool_start = time.perf_counter()

        graph_results = graph_rag_tool(
            query=rewritten_query,
            db=db,
            role=role,
        )

        graph_latency_ms += round(
            (time.perf_counter() - tool_start) * 1000,
            2,
        )

        executed_tools.append("graph_rag")

        tool_trace.append({
            "step": len(tool_trace) + 1,
            "tool": "graph_rag",
            "results": len(graph_results),
            "latency_ms": graph_latency_ms,
        })

    # ---------------------------------------------------------
    # Bounded agent loop
    # ---------------------------------------------------------
    while len(executed_tools) < MAX_AGENT_STEPS:

        next_tool = needs_additional_tool(
            question=question,
            document_results=document_results,
            graph_results=graph_results,
            executed_tools=executed_tools,
        )

        if next_tool is None:
            break

        # -----------------------------------------------------
        # Additional document retrieval
        # -----------------------------------------------------
        if next_tool == "document_rag":
            tool_start = time.perf_counter()

            document_results = document_rag_tool(
                query=rewritten_query,
                db=db,
                role=role,
            )

            latency = round(
                (time.perf_counter() - tool_start) * 1000,
                2,
            )

            document_latency_ms += latency

            executed_tools.append("document_rag")

            tool_trace.append({
                "step": len(tool_trace) + 1,
                "tool": "document_rag",
                "results": len(document_results),
                "latency_ms": latency,
            })

        # -----------------------------------------------------
        # Additional graph retrieval
        # -----------------------------------------------------
        elif next_tool == "graph_rag":
            tool_start = time.perf_counter()

            graph_results = graph_rag_tool(
                query=rewritten_query,
                db=db,
                role=role,
            )

            latency = round(
                (time.perf_counter() - tool_start) * 1000,
                2,
            )

            graph_latency_ms += latency

            executed_tools.append("graph_rag")

            tool_trace.append({
                "step": len(tool_trace) + 1,
                "tool": "graph_rag",
                "results": len(graph_results),
                "latency_ms": latency,
            })

    # ---------------------------------------------------------
    # Stop reason
    # ---------------------------------------------------------
    if len(executed_tools) >= MAX_AGENT_STEPS:
        stop_reason = "Maximum agent steps reached."
    else:
        stop_reason = "Sufficient retrieval evidence collected."

    # ---------------------------------------------------------
    # Total agent latency
    # ---------------------------------------------------------
    total_latency_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    return {
        "plan": {
            "use_document_rag": plan.use_document_rag,
            "use_graph_rag": plan.use_graph_rag,
            "reason": plan.reason,
        },

        "document_results": document_results,
        "graph_results": graph_results,

        "executed_tools": executed_tools,
        "tool_trace": tool_trace,

        "stop_reason": stop_reason,

        "metrics": {
            "agent_steps": len(executed_tools),

            "document_results": len(document_results),
            "graph_results": len(graph_results),

            "document_latency_ms": round(
                document_latency_ms,
                2,
            ),

            "graph_latency_ms": round(
                graph_latency_ms,
                2,
            ),

            "total_agent_latency_ms": total_latency_ms,
        },
    }