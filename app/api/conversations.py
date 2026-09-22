from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.api.auth import get_current_user


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: int
    title: str | None
    created_at: str
    updated_at: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=ConversationResponse)
def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = db.execute(
        text(
            """
            INSERT INTO conversations (user_id, title)
            VALUES (:user_id, :title)
            RETURNING id, title, created_at, updated_at
            """
        ),
        {
            "user_id": current_user["id"],
            "title": request.title,
        },
    )

    conversation = result.mappings().one()

    db.commit()

    return {
        "id": conversation["id"],
        "title": conversation["title"],
        "created_at": conversation["created_at"].isoformat(),
        "updated_at": conversation["updated_at"].isoformat(),
    }


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = db.execute(
        text(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
            """
        ),
        {
            "user_id": current_user["id"],
        },
    )

    conversations = result.mappings().all()

    return [
        {
            "id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"].isoformat(),
            "updated_at": conversation["updated_at"].isoformat(),
        }
        for conversation in conversations
    ]