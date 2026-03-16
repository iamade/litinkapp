from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field

from app.promo.models import GrantType


class RedeemPromoRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class RedeemPromoResponse(BaseModel):
    success: bool
    credits_granted: int
    expires_at: datetime


class CreditBalanceResponse(BaseModel):
    total_credits: int


class CreatePromoCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    credit_amount: int = Field(..., gt=0)
    expiry_days: int = Field(..., gt=0)
    max_redemptions: int = Field(..., gt=0)
    is_active: bool = True


class PromoCodeResponse(BaseModel):
    id: uuid.UUID
    code: str
    credit_amount: int
    expiry_days: int
    max_redemptions: int
    current_redemptions: int
    is_active: bool
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
