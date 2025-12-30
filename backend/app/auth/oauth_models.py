import uuid
from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    APPLE = "apple"
    MICROSOFT = "microsoft"


class UserOAuth(SQLModel, table=True):
    __tablename__ = "user_oauth"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="unique_provider_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    provider: OAuthProvider = Field(index=True)
    provider_user_id: str = Field(index=True, max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
