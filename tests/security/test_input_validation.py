import pytest
from pydantic import ValidationError

from app.api.chat import ChatRequest


def test_question_must_be_at_least_3_characters():
    with pytest.raises(ValidationError):
        ChatRequest(question="Hi")


def test_question_cannot_exceed_4000_characters():
    with pytest.raises(ValidationError):
        ChatRequest(question="x" * 4001)


def test_extra_fields_are_rejected():
    payload = {
        "question": "What is the leave policy?",
        "unexpected_field": "attack",
    }

    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)


def test_valid_chat_request_is_accepted():
    request = ChatRequest(
        question="What is the leave policy?",
        conversation_id=10,
    )

    assert request.question == "What is the leave policy?"
    assert request.conversation_id == 10