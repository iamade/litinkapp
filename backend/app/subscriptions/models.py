import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func
from enum import Enum


class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class UserSubscription(SQLModel, table=True):
    __tablename__ = "user_subscriptions"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, unique=True, index=True)
    )
    tier: SubscriptionTier = Field(
        sa_column=Column(
            pg.ENUM(SubscriptionTier, name="subscription_tier"),
            nullable=False,
            default=SubscriptionTier.FREE,
        )
    )
    status: SubscriptionStatus = Field(
        sa_column=Column(
            pg.ENUM(SubscriptionStatus, name="subscription_status"),
            nullable=False,
            default=SubscriptionStatus.ACTIVE,
        )
    )
    stripe_customer_id: Optional[str] = Field(default=None, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, index=True)
    stripe_price_id: Optional[str] = Field(default=None)

    current_period_start: Optional[datetime] = Field(
        default=None, sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    current_period_end: Optional[datetime] = Field(
        default=None, sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    cancel_at_period_end: bool = Field(default=False)
    cancelled_at: Optional[datetime] = Field(
        default=None, sa_column=Column(pg.TIMESTAMP(timezone=True))
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


class SubscriptionHistory(SQLModel, table=True):
    __tablename__ = "subscription_history"

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
    event_type: str = Field(nullable=False)
    from_tier: Optional[str] = Field(default=None)
    to_tier: Optional[str] = Field(default=None)
    from_status: Optional[str] = Field(default=None)
    to_status: Optional[str] = Field(default=None)

    stripe_event_id: Optional[str] = Field(default=None)
    meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )


class UsageLog(SQLModel, table=True):
    __tablename__ = "usage_logs"

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
    subscription_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), index=True)
    )
    resource_type: str = Field(default="video_generation", index=True)
    resource_id: Optional[str] = Field(default=None)
    usage_count: int = Field(default=1)

    meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
