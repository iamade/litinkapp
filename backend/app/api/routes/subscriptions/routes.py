from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
import json
import uuid

from app.subscriptions.schemas import (
    UserSubscription,
    SubscriptionTierInfo,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    SubscriptionUsageStats,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    WebhookEvent,
)
from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.api.services.subscription import SubscriptionManager, SubscriptionTier
from app.core.services.stripe import stripe_service
from app.auth.models import User

router = APIRouter()


@router.get("/current", response_model=UserSubscription)
async def get_current_subscription(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get the current user's subscription"""
    # try:
    manager = SubscriptionManager(session)
    subscription = await manager.get_subscription(current_user.id)

    if not subscription:
        # Return free tier if no subscription exists
        # Construct a default free subscription object (not saved to DB)
        return {
            "id": str(uuid.uuid4()),  # Temporary ID
            "user_id": str(current_user.id),
            "tier": SubscriptionTier.FREE,
            "status": "active",
            "monthly_video_limit": 2,  # Hardcoded for now, ideally from TIER_LIMITS
            "video_quality": "720p",
            "has_watermark": True,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        }

    return subscription

    # except Exception as e:
    #     print(f"[SubscriptionsAPI] Error getting current subscription: {e}")
    #     raise HTTPException(status_code=500, detail="Failed to get subscription")


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create a Stripe checkout session for subscription"""
    try:
        manager = SubscriptionManager(session)

        # Disable backend integration for pro tier if needed (logic from original code)
        # if checkout_data.tier == SubscriptionTier.PRO:
        #     raise HTTPException(status_code=400, detail="Pro tier is coming soon")

        # Create or get Stripe customer
        customer_id = await stripe_service.create_or_get_customer(
            user_id=current_user.id,
            email=current_user.email,
            name=current_user.full_name,
        )

        # Create checkout session
        session_data = await manager.create_checkout_session(
            user_id=str(current_user.id),
            tier=checkout_data.tier,
            success_url=str(checkout_data.success_url),
            cancel_url=str(checkout_data.cancel_url),
        )

        return session_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[SubscriptionsAPI] Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook")
async def handle_stripe_webhook(
    request: Request, session: AsyncSession = Depends(get_session)
):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")

        if not signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        # Handle webhook signature verification via stripe_service
        event_data = await stripe_service.handle_webhook(payload, signature)

        # Process event via manager
        manager = SubscriptionManager(session)
        await manager.handle_subscription_webhook(event_data["event_type"], event_data)

        return {"status": "success"}

    except Exception as e:
        print(f"[SubscriptionsAPI] Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/usage", response_model=SubscriptionUsageStats)
async def get_usage_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get current usage statistics"""
    try:
        manager = SubscriptionManager(session)
        usage_stats = await manager.check_usage_limits(current_user.id)

        return {
            "current_period_videos": usage_stats["current_usage"]["videos"],
            "period_limit": usage_stats["limits"]["videos_per_month"],
            "remaining_videos": (
                usage_stats["videos_remaining"]
                if isinstance(usage_stats["videos_remaining"], int)
                else -1
            ),  # -1 for unlimited? or handle schema
            "period_start": datetime.fromisoformat(
                usage_stats["current_usage"]["period_start"]
            ),
            "period_end": datetime.fromisoformat(
                usage_stats["current_usage"]["period_end"]
            ),
            "can_generate_video": usage_stats["can_generate"],
        }

    except Exception as e:
        print(f"[SubscriptionsAPI] Error getting usage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage statistics")


@router.get("/tiers", response_model=List[SubscriptionTierInfo])
async def get_subscription_tiers(session: AsyncSession = Depends(get_session)):
    """Get available subscription tiers"""
    # try:
    manager = SubscriptionManager(session)
    tiers_data = manager.get_all_tiers()

    # Map to SubscriptionTierInfo schema
    mapped_tiers = []
    for tier_info in tiers_data:
        features = tier_info.get("features", {})
        mapped_tiers.append(
            {
                "tier": tier_info["tier"],
                "display_name": tier_info.get(
                    "display_name", tier_info["tier"].title()
                ),
                "description": tier_info.get("description", ""),
                "monthly_price": tier_info.get("monthly_price", 0),
                "monthly_video_limit": (
                    features.get("videos_per_month", 0)
                    if features.get("videos_per_month") != "unlimited"
                    else -1
                ),
                "video_quality": tier_info.get(
                    "video_quality", features.get("max_resolution", "720p")
                ),
                "has_watermark": tier_info.get(
                    "has_watermark", features.get("watermark", False)
                ),
                "max_video_duration": tier_info.get(
                    "max_video_duration", features.get("max_video_duration")
                ),
                "priority_processing": tier_info.get(
                    "priority_processing", features.get("priority", 0) > 0
                ),
                "features": features,
                "feature_highlights": tier_info.get("feature_highlights", []),
                "display_order": tier_info.get(
                    "display_order", features.get("priority", 0)
                ),
                "is_active": tier_info.get("is_active", True),
            }
        )

    return mapped_tiers

    # except Exception as e:
    #     print(f"[SubscriptionsAPI] Error getting subscription tiers: {e}")
    #     raise HTTPException(status_code=500, detail="Failed to get subscription tiers")


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    cancel_data: SubscriptionCancelRequest = SubscriptionCancelRequest(),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Cancel the current user's subscription"""
    try:
        manager = SubscriptionManager(session)
        result = await manager.cancel_subscription(
            current_user.id, cancel_at_period_end=cancel_data.cancel_at_period_end
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[SubscriptionsAPI] Error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/reactivate")
async def reactivate_subscription(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Reactivate a cancelled subscription"""
    try:
        manager = SubscriptionManager(session)
        result = await manager.reactivate_subscription(current_user.id)
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[SubscriptionsAPI] Error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to reactivate subscription")
