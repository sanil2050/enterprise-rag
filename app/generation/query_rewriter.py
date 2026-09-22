import json

from openai import OpenAI

from app.config.settings import settings


MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"


client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)


SYSTEM_INSTRUCTION = """
You are a query rewriting component for an enterprise RAG system.

Your job is to rewrite the user's current question into a
self-contained search query that can be used to retrieve
relevant enterprise documents.

Use the conversation history only to resolve references such as:
- "it"
- "that"
- "they"
- "this"
- "the previous one"
- "how much"
- "what about that"

Rules:

1. Preserve the user's actual intent.
2. Use conversation history only when necessary.
3. Do not answer the question.
4. Do not add facts that are not present in the conversation.
5. Make the rewritten query self-contained.
6. Keep the query concise.
7. If the current question is already self-contained, return it unchanged.

Return ONLY valid JSON:

{
  "rewritten_query": "..."
}
"""


def fallback_rewrite(
    question: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Safe local fallback when OpenRouter rewriting is unavailable.

    For self-contained questions, simply return the original question.

    For conversational follow-ups, append recent conversation context
    so retrieval still has useful information without requiring the model.
    """

    conversation_history = conversation_history or []

    question = question.strip()

    if not conversation_history:
        return question

    # ---------------------------------------------------------
    # Keep only the most recent few messages.
    # ---------------------------------------------------------

    recent_history = conversation_history[-4:]

    history_lines = []

    for message in recent_history:
        role = message.get("role", "").upper()
        content = message.get("content", "").strip()

        if content:
            history_lines.append(
                f"{role}: {content}"
            )

    if not history_lines:
        return question

    # ---------------------------------------------------------
    # If the question already looks self-contained, don't
    # unnecessarily expand it.
    # ---------------------------------------------------------

    question_lower = question.lower()

    reference_words = {
        "it",
        "that",
        "this",
        "they",
        "them",
        "those",
        "these",
        "previous",
        "same",
        "also",
        "too",
    }

    contains_reference = any(
        word in question_lower.split()
        for word in reference_words
    )

    if not contains_reference:
        return question

    # ---------------------------------------------------------
    # Conservative fallback:
    # include recent conversation as retrieval context.
    #
    # We intentionally do NOT invent a rewritten answer.
    # ---------------------------------------------------------

    return (
        f"{question}\n\n"
        f"Recent conversation context:\n"
        f"{chr(10).join(history_lines)}"
    )


def rewrite_query(
    question: str,
    conversation_history: list[dict] | None = None,
) -> str:

    conversation_history = conversation_history or []

    # ---------------------------------------------------------
    # Build conversation history
    # ---------------------------------------------------------

    if conversation_history:

        history_lines = []

        for message in conversation_history:
            history_lines.append(
                f"{message['role'].upper()}: {message['content']}"
            )

        history_text = "\n".join(history_lines)

    else:
        history_text = "No previous conversation."

    # ---------------------------------------------------------
    # Build Nemotron / OpenRouter prompt
    # ---------------------------------------------------------

    prompt = f"""
{SYSTEM_INSTRUCTION}

CONVERSATION HISTORY:

{history_text}

CURRENT USER QUESTION:

{question}

Return ONLY the JSON object.
"""

    # ---------------------------------------------------------
    # Nemotron rewriting through OpenRouter
    # ---------------------------------------------------------

    try:

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.1,
        )

        if not response.choices:
            raise ValueError(
                "OpenRouter returned no choices."
            )

        message = response.choices[0].message

        text = message.content

        if not text:
            raise ValueError(
                "OpenRouter returned an empty response."
            )

        text = text.strip()

        # -----------------------------------------------------
        # Handle accidental markdown code fences
        # -----------------------------------------------------

        if text.startswith("```"):

            text = text.replace(
                "```json",
                "",
                1,
            )

            text = text.replace(
                "```",
                "",
            )

            text = text.strip()

        # -----------------------------------------------------
        # Parse JSON
        # -----------------------------------------------------

        result = json.loads(text)

        rewritten_query = result.get("rewritten_query")

        if not rewritten_query:
            raise ValueError(
                "Nemotron returned an empty rewritten query."
            )

        return rewritten_query.strip()

    # ---------------------------------------------------------
    # OpenRouter unavailable / malformed response
    # ---------------------------------------------------------

    except Exception as exc:

        print(
            "Query rewriting unavailable. "
            "Using local fallback. "
            f"Error: {type(exc).__name__}: {exc}"
        )

        return fallback_rewrite(
            question=question,
            conversation_history=conversation_history,
        )