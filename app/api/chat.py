import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.agent.service import run_agent
from app.api.auth import get_current_user
from app.api.request_context import get_request_id
from app.database.database import SessionLocal
from app.generation.citation_validator import validate_citations
from app.generation.gemini_generator import generate_answer
from app.generation.query_rewriter import rewrite_query
from app.observability.logging import logger


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


# ============================================================
# Request / Response Models
# ============================================================


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Question to ask the enterprise knowledge base",
    )

    conversation_id: int | None = Field(
        default=None,
        description="Conversation to continue",
    )


class Citation(BaseModel):
    citation_id: str
    document: str
    page: int
    chunk: int
    excerpt: str


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    citations: list[Citation]


# ============================================================
# Database Dependency
# ============================================================


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# Conversation Helpers
# ============================================================


def create_conversation(
    db: Session,
    user_id: int,
):
    result = db.execute(
        text(
            """
            INSERT INTO conversations (user_id, title)
            VALUES (:user_id, NULL)
            RETURNING id
            """
        ),
        {
            "user_id": user_id,
        },
    )

    conversation_id = result.scalar_one()

    db.commit()

    return conversation_id


def get_conversation_history(
    db: Session,
    conversation_id: int,
    user_id: int,
    limit: int = 6,
):
    result = db.execute(
        text(
            """
            SELECT
                m.role,
                m.content,
                m.created_at
            FROM messages m
            JOIN conversations c
                ON c.id = m.conversation_id
            WHERE c.id = :conversation_id
              AND c.user_id = :user_id
            ORDER BY m.created_at DESC
            LIMIT :limit
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "limit": limit,
        },
    )

    messages = result.mappings().all()

    return list(reversed(messages))


def save_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
):
    db.execute(
        text(
            """
            INSERT INTO messages (
                conversation_id,
                role,
                content
            )
            VALUES (
                :conversation_id,
                :role,
                :content
            )
            """
        ),
        {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        },
    )

    db.commit()


# ============================================================
# Chat Endpoint
# ============================================================


@router.post(
    "",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    user_id = current_user["id"]

    request_id = get_request_id(http_request)

    start_time = time.perf_counter()

    conversation_id = request.conversation_id

    try:

        # ====================================================
        # 1. Get or create conversation
        # ====================================================

        if request.conversation_id is None:

            conversation_id = create_conversation(
                db=db,
                user_id=user_id,
            )

        else:

            conversation = db.execute(
                text(
                    """
                    SELECT id
                    FROM conversations
                    WHERE id = :conversation_id
                      AND user_id = :user_id
                    """
                ),
                {
                    "conversation_id": request.conversation_id,
                    "user_id": user_id,
                },
            ).first()

            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found",
                )

        # ====================================================
        # 2. Conversation history
        # ====================================================

        history = get_conversation_history(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            limit=6,
        )

        # ====================================================
        # 3. Query rewriting
        # ====================================================

        rewrite_start = time.perf_counter()

        rewritten_query = rewrite_query(
            question=request.question,
            conversation_history=history,
        )

        rewrite_latency_ms = round(
            (time.perf_counter() - rewrite_start) * 1000,
            2,
        )

        # ====================================================
        # 4. Agentic workflow
        # ====================================================

        agent_start = time.perf_counter()

        agent_result = run_agent(
            question=request.question,
            rewritten_query=rewritten_query,
            db=db,
            role=current_user["role"],
        )

        agent_latency_ms = round(
            (time.perf_counter() - agent_start) * 1000,
            2,
        )

        document_results = agent_result["document_results"]
        graph_results = agent_result["graph_results"]
        agent_plan = agent_result["plan"]
        agent_metrics = agent_result["metrics"]
        executed_tools = agent_result["executed_tools"]
        tool_trace = agent_result["tool_trace"]
        stop_reason = agent_result["stop_reason"]

        # ====================================================
        # 5. Gemini generation
        # ====================================================

        generation_start = time.perf_counter()

        result = generate_answer(
            question=request.question,
            context=document_results,
            graph_context=graph_results,
            conversation_history=history,
        )

        generation_latency_ms = round(
            (time.perf_counter() - generation_start) * 1000,
            2,
        )

        # ====================================================
        # 6. Validate citations
        # ====================================================

        validated = validate_citations(
            generated_result=result,
            retrieved_context=document_results,
        )

        # ====================================================
        # 7. Save user message
        # ====================================================

        save_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )

        # ====================================================
        # 8. Save assistant response
        # ====================================================

        save_message(
            db=db,
            conversation_id=conversation_id,
            role="assistant",
            content=validated["answer"],
        )

        # ====================================================
        # 9. Observability
        # ====================================================

        total_latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "chat_request_completed",
            extra={
                "event_data": {
                    "request_id": request_id,
                    "user_id": user_id,
                    "role": current_user["role"],
                    "conversation_id": conversation_id,
                    "question": request.question,
                    "rewritten_query": rewritten_query,
                    "agent_steps": agent_metrics["agent_steps"],
                    "agent_executed_tools": executed_tools,
                    "agent_tool_trace": tool_trace,
                    "agent_stop_reason": stop_reason,

                    # Agent plan
                    "agent_use_document_rag": (
                        agent_plan["use_document_rag"]
                    ),
                    "agent_use_graph_rag": (
                        agent_plan["use_graph_rag"]
                    ),
                    "agent_reason": agent_plan["reason"],

                    # Agent metrics
                    "agent_document_results": (
                        agent_metrics["document_results"]
                    ),
                    "agent_graph_results": (
                        agent_metrics["graph_results"]
                    ),
                    "agent_document_latency_ms": (
                        agent_metrics["document_latency_ms"]
                    ),
                    "agent_graph_latency_ms": (
                        agent_metrics["graph_latency_ms"]
                    ),
                    "agent_latency_ms": agent_latency_ms,

                    # Answer metrics
                    "citations": len(
                        validated["citations"]
                    ),

                    # Latency
                    "rewrite_latency_ms": rewrite_latency_ms,
                    "generation_latency_ms": generation_latency_ms,
                    "total_latency_ms": total_latency_ms,

                    "status": "success",
                }
            },
        )

        # ====================================================
        # 10. Response
        # ====================================================

        return {
            "conversation_id": conversation_id,
            **validated,
        }

    # ========================================================
    # HTTP errors
    # ========================================================

    except HTTPException:
        raise

    # ========================================================
    # Unexpected errors
    # ========================================================

    except Exception as exc:

        total_latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.exception(
            "chat_request_failed",
            extra={
                "event_data": {
                    "request_id": request_id,
                    "user_id": user_id,
                    "role": current_user["role"],
                    "conversation_id": conversation_id,
                    "question": request.question,
                    "total_latency_ms": total_latency_ms,
                    "status": "error",
                    "error_type": type(exc).__name__,
                }
            },
        )

        raise