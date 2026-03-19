import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import String, Integer, Text, text


class CreditTransaction(SQLModel, table=True):
    __tablename__ = "credit_transactions"

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
    amount: int = Field(nullable=False)
    # "reserved" | "confirmed" | "released"
    status: str = Field(
        sa_column=Column(String, nullable=False, default="reserved", index=True)
    )
    operation_type: str = Field(
        sa_column=Column(String, nullable=False, index=True)
    )
    # Idempotency key — e.g., image_generation_id, audio_generation_id, video_generation_id
    ref_id: Optional[str] = Field(
        sa_column=Column(String, nullable=True, index=True)
    )
    # For partial-confirm adjustments — links back to original reservation
    parent_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID(as_uuid=True), nullable=True),
    )
    meta: Optional[dict] = Field(
        default=None,
        sa_column=Column(pg.JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    # When a reservation expires (used by cleanup task)
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True),
    )


class CreditFailure(SQLModel, table=True):
    """Records credit confirm_deduction failures for reconciliation."""

    __tablename__ = "credit_failures"

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
    reservation_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False)
    )
    amount: int = Field(sa_column=Column(Integer, nullable=False))
    operation_type: str = Field(sa_column=Column(String, nullable=False))
    error_message: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    # "pending" | "resolved" | "voided"
    status: str = Field(
        sa_column=Column(String, nullable=False, default="pending")
    )
    retry_count: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=True),
    )
