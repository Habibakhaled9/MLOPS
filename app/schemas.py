from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Response returned by the health endpoint."""

    status: Literal["healthy"]


class AskRequest(BaseModel):
    """Validated request for the ask endpoint."""

    question: str = Field(
        min_length=3,
        max_length=1000,
        examples=["What is a Docker container?"],
    )

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value: object) -> object:
        """Remove surrounding whitespace before length validation."""

        if isinstance(value, str):
            return value.strip()

        return value


class AskResponse(BaseModel):
    """Response returned by the ask endpoint."""

    question: str
    answer: str
    model: str


class QuestionHistoryItem(BaseModel):
    """One stored question and answer."""

    id: int
    question: str
    answer: str
    model_name: str
    created_at: datetime