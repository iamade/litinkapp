import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey


class Quiz(SQLModel, table=True):
    __tablename__ = "quizzes"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    chapter_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    book_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )

    title: str = Field(nullable=False)
    questions: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    difficulty: str = Field(default="medium")
    created_by: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    # Relationships
    attempts: List["QuizAttempt"] = Relationship(back_populates="quiz")


class QuizAttempt(SQLModel, table=True):
    __tablename__ = "quiz_attempts"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    quiz_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("quizzes.id"),
            nullable=False,
            index=True,
        )
    )

    answers: List[Dict[str, Any]] = Field(
        default=[], sa_column=Column(pg.JSONB, server_default=text("'[]'::jsonb"))
    )
    score: int = Field(default=0)
    time_taken: Optional[int] = Field(default=None)

    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    # Relationships
    quiz: Quiz = Relationship(back_populates="attempts")
