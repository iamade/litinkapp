from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Badge(BaseModel):
    id: int
    name: str
    description: str
    image_url: Optional[str] = None
    criteria: str
    rarity: str
    points: int
    created_at: datetime

    class Config:
        from_attributes = True


class BadgeCreate(BaseModel):
    name: str
    description: str
    image_url: Optional[str] = None
    criteria: str
    rarity: str
    points: int