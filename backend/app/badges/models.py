from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import List


class UserBadge(SQLModel, table=True):
    __tablename__ = "user_badges"

    user_id: str = Field(primary_key=True)
    badge_id: int = Field(primary_key=True, foreign_key="badges.id")
    earned_at: datetime = Field(default_factory=datetime.utcnow)


class Badge(SQLModel, table=True):
    __tablename__ = "badges"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    image_url: Optional[str] = None
    criteria: str
    rarity: str
    points: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
