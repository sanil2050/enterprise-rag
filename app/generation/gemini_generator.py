import json

from fastapi import HTTPException
from openai import OpenAI

from app.config.settings import settings


MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"


client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)


SYSTEM_INSTRUCTION = """
You are an enterprise knowledge assistant.

Answer the user's question using ONLY the provided retrieved evidence.

There are two types of evidence:

1. DOCUMENT EVIDENCE
   - Retrieved document chunks.
   - These are authoritative textual evidence.

2. GRAPH EVIDENCE
   - Structured relationships extracted from enterprise documents.
   - Graph evidence is useful for understanding entities and relationships.
   - Graph evidence is grounded in its source document and chunk.
   - Do not treat graph relationships as independent facts if the
     underlying document evidence contradicts them.

Conversation history is provided only to understand references,
context, and follow-up questions.

Do NOT treat conversation history as authoritative evidence.

Rules:

1. Use only information explicitly supported by the retrieved evidence.
2. Do not use outside knowledge.
3. Use conversation history only to understand what the user is referring to.
4. If conversation history conflicts with retrieved evidence, follow the retrieved evidence.
5. Inspect ALL evidence before answering.
6. Synthesize relevant evidence from multiple document chunks and graph relationships when necessary.
7. Do not include unrelated information.
8. If the evidence does not contain enough information, say so clearly.
9. Every factual claim must be supported by one or more citation IDs.
10. Prefer direct document evidence when explaining detailed facts.
11. Use graph evidence to identify relationships and connect related entities.
12. Never invent graph relationships.
13. Never invent citation IDs.
14. If graph evidence and document evidence describe the same fact,
    prefer the document evidence for the final factual explanation.
15. Keep the answer concise but complete.

Return ONLY valid JSON using this exact structure:

{
  "answer": "your answer",
  "citations": [
    {
      "citation_id": "S1",
      "document": "filename.pdf",
      "page": 1,
      "chunk": 0
    }
  ]
}

Citation rules:

- Document evidence uses citation IDs such as S1, S2, S3.
- Graph evidence uses graph IDs such as G1, G2, G3.
- Only cite sources that actually support the answer.
- Do not invent citation IDs.
- Use the citation IDs provided in the evidence.
- Keep the answer concise but complete.
"""


def generate_answer(
    question: str,
    context: list[dict],
    graph_context: list[dict] | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:

    graph_context = graph_context or []
    conversation_history = conversation_history or []

    # =========================================================
    # 1. Conversation history
    # =========================================================

    if conversation_history:
        history_lines = []

        for message in conversation_history:
            history_lines.append(
                f"{message['role'].upper()}: {message['content']}"
            )

        history_text = "\n".join(history_lines)

    else:
        history_text = "No previous conversation."

    # =========================================================
    # 2. Document evidence
    # =========================================================

    evidence = []

    for index, item in enumerate(context, start=1):

        chunk = item["chunk"]
        document = item["document"]

        evidence.append(
            {
                "citation_id": f"S{index}",
                "document": document.filename,
                "page": chunk.page_number,
                "chunk": chunk.chunk_index,
                "content": chunk.content,
                "rerank_score": item.get("rerank_score"),
            }
        )

    # =========================================================
    # 3. Graph evidence
    # =========================================================

    graph_evidence = []

    for item in graph_context:

        graph_evidence.append(
            {
                "graph_id": item["graph_id"],
                "subject": item["subject"],
                "subject_type": item["subject_type"],
                "predicate": item["predicate"],
                "object": item["object"],
                "object_type": item["object_type"],
                "document": item["document"],
                "page": item["page"],
                "chunk": item["chunk"],
                "content": item["content"],
            }
        )

    # =========================================================
    # 4. Build prompt
    # =========================================================

    prompt = f"""
{SYSTEM_INSTRUCTION}

CONVERSATION HISTORY:

{history_text}

CURRENT USER QUESTION:

{question}

DOCUMENT EVIDENCE:

{json.dumps(evidence, indent=2)}

GRAPH EVIDENCE:

{json.dumps(graph_evidence, indent=2)}

Return ONLY the JSON object.
"""

    # =========================================================
    # 5. OpenRouter / DeepSeek R1 generation
    # =========================================================

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter generation failed: {exc}",
        ) from exc

    # =========================================================
    # 6. Validate response
    # =========================================================

    if not response.choices:
        print("OpenRouter returned no choices.")
        print(f"OpenRouter response: {response}")

        raise HTTPException(
            status_code=502,
            detail="OpenRouter returned no choices.",
        )

    message = response.choices[0].message

    text = message.content

    if not text:
        raise HTTPException(
            status_code=502,
            detail="OpenRouter returned an empty response.",
        )

    text = text.strip()

    # =========================================================
    # 7. Handle accidental markdown fences
    # =========================================================

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

    # =========================================================
    # 8. Parse JSON
    # =========================================================

    try:
        result = json.loads(text)

    except json.JSONDecodeError as exc:

        raise HTTPException(
            status_code=502,
            detail="OpenRouter returned invalid JSON.",
        ) from exc

    # =========================================================
    # 9. Validate response structure
    # =========================================================

    if not isinstance(result, dict):

        raise HTTPException(
            status_code=502,
            detail="OpenRouter returned an invalid response structure.",
        )

    if "answer" not in result:

        raise HTTPException(
            status_code=502,
            detail="OpenRouter response is missing the answer field.",
        )

    if "citations" not in result:
        result["citations"] = []

    return result