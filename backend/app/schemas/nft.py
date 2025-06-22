from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NFTCollectible(BaseModel):
    id: str
    name: str
    description: str
    image_url: Optional[str] = None
    animation_url: Optional[str] = None
    story_moment: str
    rarity: str
    book_id: str
    chapter_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserCollectible(BaseModel):
    id: str
    user_id: str
    collectible_id: str
    earned_at: datetime
    blockchain_asset_id: Optional[int] = None
    transaction_id: Optional[str] = None

    class Config:
        from_attributes = True