import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import String, text


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
