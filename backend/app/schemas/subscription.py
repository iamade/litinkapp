from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class SubscriptionTierInfo(BaseModel):
    """Information about a subscription tier"""
    tier: SubscriptionTier
    display_name: str
    description: Optional[str] = None
    monthly_price: float
    stripe_price_id: Optional[str] = None
    stripe_product_id: Optional[str] = None
    monthly_video_limit: int
    video_quality: str
    has_watermark: bool
    max_video_duration: Optional[int] = None
    priority_processing: bool = False
    features: Dict[str, Any] = {}
    display_order: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class UserSubscriptionBase(BaseModel):
    """Base subscription model"""
    user_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    monthly_video_limit: int
    video_quality: str
    has_watermark: bool
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    videos_generated_this_period: int = 0
    next_billing_date: Optional[datetime] = None
    cancel_at_period_end: bool = False
    cancelled_at: Optional[datetime] = None


class UserSubscriptionCreate(UserSubscriptionBase):
    """Create subscription model"""
    pass


class UserSubscriptionUpdate(BaseModel):
    """Update subscription model"""
    tier: Optional[SubscriptionTier] = None
    status: Optional[SubscriptionStatus] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    monthly_video_limit: Optional[int] = None
    video_quality: Optional[str] = None
    has_watermark: Optional[bool] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    videos_generated_this_period: Optional[int] = None
    next_billing_date: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None
    cancelled_at: Optional[datetime] = None


class UserSubscription(UserSubscriptionBase):
    """Full subscription model"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CheckoutSessionCreate(BaseModel):
    """Create checkout session request"""
    tier: SubscriptionTier
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    """Checkout session response"""
    session_id: str
    url: str


class WebhookEvent(BaseModel):
    """Stripe webhook event"""
    event_type: str
    subscription_id: Optional[str] = None
    customer_id: Optional[str] = None
    status: Optional[str] = None
    price_id: Optional[str] = None
    current_period_start: Optional[int] = None
    current_period_end: Optional[int] = None
    cancel_at_period_end: Optional[bool] = None
    invoice_id: Optional[str] = None
    amount_paid: Optional[int] = None
    currency: Optional[str] = None
    amount_due: Optional[int] = None
    handled: bool = False


class UsageLogBase(BaseModel):
    """Base usage log model"""
    user_id: str
    subscription_id: str
    resource_type: str = "video_generation"
    resource_id: Optional[str] = None
    usage_count: int = 1
    metadata: Dict[str, Any] = {}
    billing_period_start: Optional[datetime] = None
    billing_period_end: Optional[datetime] = None


class UsageLogCreate(UsageLogBase):
    """Create usage log model"""
    pass


class UsageLog(UsageLogBase):
    """Full usage log model"""
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionUsageStats(BaseModel):
    """Current usage statistics"""
    current_period_videos: int
    period_limit: int
    remaining_videos: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    can_generate_video: bool


class SubscriptionHistoryBase(BaseModel):
    """Base subscription history model"""
    user_id: str
    subscription_id: Optional[str] = None
    event_type: str
    from_tier: Optional[SubscriptionTier] = None
    to_tier: Optional[SubscriptionTier] = None
    from_status: Optional[SubscriptionStatus] = None
    to_status: Optional[SubscriptionStatus] = None
    stripe_event_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    amount_paid: Optional[float] = None
    currency: str = "USD"
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SubscriptionHistoryCreate(SubscriptionHistoryBase):
    """Create subscription history model"""
    pass


class SubscriptionHistory(SubscriptionHistoryBase):
    """Full subscription history model"""
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentMethodInfo(BaseModel):
    """Payment method information"""
    id: str
    type: str
    card: Optional[Dict[str, Any]] = None


class SubscriptionCancelRequest(BaseModel):
    """Cancel subscription request"""
    cancel_at_period_end: bool = True


class SubscriptionCancelResponse(BaseModel):
    """Cancel subscription response"""
    subscription_id: str
    status: str
    cancel_at_period_end: bool
    current_period_end: Optional[int] = None