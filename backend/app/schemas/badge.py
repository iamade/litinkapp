from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Badge(BaseModel):
    id: str
    name: str
    description: str
    image_url: Optional[str] = None
    criteria: str
    rarity: str
    points: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserBadge(BaseModel):
    id: str
    user_id: str
    badge_id: str
    earned_at: datetime
    blockchain_asset_id: Optional[int] = None
    transaction_id: Optional[str] = None

    class Config:
        from_attributes = True