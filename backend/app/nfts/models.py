from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class NFT(SQLModel, table=True):
    __tablename__ = "nfts"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: uuid.UUID = Field(index=True)
    name: str
    description: str
    asset_id: int = Field(unique=True, index=True)
    tx_id: str
    metadata_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
