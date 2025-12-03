import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import text, func


class AdminSetting(SQLModel, table=True):
    __tablename__ = "admin_settings"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    setting_key: str = Field(index=True, unique=True)
    setting_value: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    description: Optional[str] = Field(default=None)
    updated_by: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True))
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=func.current_timestamp(),
        ),
    )


class AdminAlert(SQLModel, table=True):
    __tablename__ = "admin_alerts"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    alert_type: str = Field(index=True)
    severity: str = Field(index=True)  # info, warning, critical
    message: str
    metric_value: Optional[float] = Field(default=None)
    threshold_value: Optional[float] = Field(default=None)
    meta: Dict[str, Any] = Field(
        default={}, sa_column=Column(pg.JSONB, server_default=text("'{}'::jsonb"))
    )
    acknowledged_at: Optional[datetime] = Field(
        default=None, sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    acknowledged_by: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True))
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
