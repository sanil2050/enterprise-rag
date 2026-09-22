import json
import time

from google import genai
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings


MODEL_NAME = "gemini-3.6-flash"

client = genai.Client(
    api_key=settings.gemini_api_key
)


SYSTEM_INSTRUCTION = """
You are an information extraction component for an enterprise knowledge graph.

Extract only explicit entities and relationships from the provided
enterprise document chunk.

Rules:

1. Extract only information explicitly stated in the chunk.
2. Do not use outside knowledge.
3. Do not infer relationships that are not supported by the text.
4. Keep entity names concise and meaningful.
5. Use simple entity types such as:
   - PERSON
   - ORGANIZATION
   - POLICY
   - PRODUCT
   - BENEFIT
   - LEAVE_TYPE
   - DEPARTMENT
   - LOCATION
   - DATE
   - NUMBER
   - CONCEPT
   - OTHER

6. Relationships should be short factual predicates such as:
   - HAS_LIMIT
   - PROVIDES
   - APPLIES_TO
   - REQUIRES
   - ALLOWS
   - PAID_AS
   - PART_OF
   - AVAILABLE_FOR
   - DEFINED_BY
   - RELATED_TO

7. Do not create relationships unless both entities are explicitly
   supported by the chunk.

Return ONLY valid JSON:

{
  "entities": [
    {
      "name": "entity name",
      "entity_type": "ENTITY_TYPE"
    }
  ],
  "relationships": [
    {
      "subject": "entity name",
      "predicate": "RELATIONSHIP",
      "object": "entity name"
    }
  ]
}

If there are no useful entities or relationships:

{
  "entities": [],
  "relationships": []
}
"""


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def clean_json_response(raw_text: str) -> str:
    raw_text = raw_text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "", 1)
        raw_text = raw_text.replace("```", "")
        raw_text = raw_text.strip()

    return raw_text


def extract_graph_data(
    content: str,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> dict:

    last_error = None

    for attempt in range(1, max_retries + 1):

        try:

            prompt = f"""
{SYSTEM_INSTRUCTION}

DOCUMENT CHUNK:

{content}

Return ONLY the JSON object.
"""

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            raw_text = clean_json_response(response.text)

            result = json.loads(raw_text)

            if not isinstance(result, dict):
                raise ValueError("Gemini returned a non-object JSON result")

            if "entities" not in result:
                result["entities"] = []

            if "relationships" not in result:
                result["relationships"] = []

            return result

        except Exception as exc:

            last_error = exc

            print(
                f"    Gemini extraction attempt "
                f"{attempt}/{max_retries} failed: "
                f"{type(exc).__name__}: {exc}"
            )

            if attempt < max_retries:
                time.sleep(retry_delay)

    raise RuntimeError(
        f"Graph extraction failed after {max_retries} attempts: "
        f"{type(last_error).__name__}: {last_error}"
    )


def get_or_create_entity(
    db: Session,
    name: str,
    entity_type: str,
) -> int:

    normalized_name = normalize_name(name)

    result = db.execute(
        text(
            """
            SELECT id
            FROM graph_entities
            WHERE normalized_name = :normalized_name
              AND entity_type = :entity_type
            """
        ),
        {
            "normalized_name": normalized_name,
            "entity_type": entity_type,
        },
    ).first()

    if result:
        return result[0]

    result = db.execute(
        text(
            """
            INSERT INTO graph_entities (
                name,
                entity_type,
                normalized_name
            )
            VALUES (
                :name,
                :entity_type,
                :normalized_name
            )
            RETURNING id
            """
        ),
        {
            "name": name.strip(),
            "entity_type": entity_type,
            "normalized_name": normalized_name,
        },
    )

    return result.scalar_one()


def save_graph_data(
    db: Session,
    graph_data: dict,
    document_id: int,
    chunk_id: int,
):
    entity_ids = {}

    # ---------------------------------------------------------
    # Save entities
    # ---------------------------------------------------------

    for entity in graph_data.get("entities", []):

        name = entity.get("name", "").strip()
        entity_type = (
            entity.get("entity_type", "OTHER")
            .strip()
            .upper()
        )

        if not name:
            continue

        entity_id = get_or_create_entity(
            db=db,
            name=name,
            entity_type=entity_type,
        )

        entity_ids[normalize_name(name)] = entity_id

    # ---------------------------------------------------------
    # Save relationships
    # ---------------------------------------------------------

    for relationship in graph_data.get("relationships", []):

        subject = relationship.get("subject", "").strip()
        predicate = relationship.get("predicate", "").strip().upper()
        object_name = relationship.get("object", "").strip()

        if not subject or not predicate or not object_name:
            continue

        subject_id = entity_ids.get(
            normalize_name(subject)
        )

        object_id = entity_ids.get(
            normalize_name(object_name)
        )

        if subject_id is None or object_id is None:
            continue

        # Prevent duplicate relationship for the same
        # source document/chunk.
        existing = db.execute(
            text(
                """
                SELECT id
                FROM graph_relationships
                WHERE subject_entity_id = :subject_id
                  AND predicate = :predicate
                  AND object_entity_id = :object_id
                  AND document_id = :document_id
                  AND chunk_id = :chunk_id
                """
            ),
            {
                "subject_id": subject_id,
                "predicate": predicate,
                "object_id": object_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
            },
        ).first()

        if existing:
            continue

        db.execute(
            text(
                """
                INSERT INTO graph_relationships (
                    subject_entity_id,
                    predicate,
                    object_entity_id,
                    document_id,
                    chunk_id
                )
                VALUES (
                    :subject_id,
                    :predicate,
                    :object_id,
                    :document_id,
                    :chunk_id
                )
                """
            ),
            {
                "subject_id": subject_id,
                "predicate": predicate,
                "object_id": object_id,
                "document_id": document_id,
                "chunk_id": chunk_id,
            },
        )