import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func, ForeignKey


class GrantType(str, Enum):
    PROMO = "promo"
    PURCHASE = "purchase"
    FREE_TIER = "free_tier"


class PromoCode(SQLModel, table=True):
    __tablename__ = "promo_codes"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    code: str = Field(
        sa_column=Column(pg.VARCHAR(64), nullable=False, unique=True, index=True)
    )
    credit_amount: int = Field(nullable=False)
    expiry_days: int = Field(nullable=False, description="Days from redemption until credits expire")
    max_redemptions: int = Field(nullable=False)
    current_redemptions: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(pg.UUID(as_uuid=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )


class CreditGrant(SQLModel, table=True):
    __tablename__ = "credit_grants"

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
    credits_remaining: int = Field(nullable=False)
    credits_used: int = Field(default=0)
    expires_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False)
    )
    promo_code_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("promo_codes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    grant_type: GrantType = Field(
        sa_column=Column(
            pg.ENUM(GrantType, name="grant_type"),
            nullable=False,
            default=GrantType.PROMO,
        )
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
