from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NFT(BaseModel):
    id: int
    owner_id: str  # This would be a UUID from Supabase Auth
    name: str
    description: str
    asset_id: int
    tx_id: str
    metadata_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class NFTCreate(BaseModel):
    name: str
    description: str
    metadata_url: str