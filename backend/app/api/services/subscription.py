from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import stripe
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings
from app.core.services.stripe import stripe_service
from app.subscriptions.models import (
    UserSubscription,
    SubscriptionTier,
    SubscriptionStatus,
    UsageLog,
    SubscriptionHistory,
)
import logging
import uuid

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages user subscriptions and tier-based access
    """

    TIER_LIMITS = {
        SubscriptionTier.FREE: {
            "videos_per_month": 2,
            "images_per_month": 50,  # For testing character images
            "books_upload_limit": 3,
            "video_books_limit": 1,
            "chapters_per_book": 2,
            "max_video_duration": 300,  # 5 minutes
            "max_resolution": "720p",
            "watermark": True,
            "priority": 0,
            "support": "community",
            "api_access": False,
            "model_selection": False,
            "voice_cloning": False,
            "price_monthly": 0,
            "display_name": "Free",
            "description": "Perfect for trying out the platform",
        },
        SubscriptionTier.BASIC: {
            "videos_per_month": 8,
            "books_upload_limit": 10,
            "video_books_limit": 3,
            "chapters_per_book": "unlimited",
            "max_video_duration": 900,  # 15 minutes
            "max_resolution": "720p",
            "watermark": False,
            "priority": 1,
            "support": "email",
            "api_access": False,
            "model_selection": False,
            "voice_cloning": False,
            "price_monthly": 29,
            "display_name": "Basic",
            "description": "Great for casual creators",
        },
        SubscriptionTier.PRO: {
            "videos_per_month": 20,
            "books_upload_limit": 25,
            "video_books_limit": 10,
            "chapters_per_book": "unlimited",
            "max_video_duration": 1800,  # 30 minutes
            "max_resolution": "1080p",
            "watermark": False,
            "priority": 2,
            "support": "priority_email",
            "api_access": False,
            "model_selection": True,
            "voice_cloning": True,
            "price_monthly": 79,
            "display_name": "Standard",
            "description": "For serious content creators",
        },
        SubscriptionTier.PREMIUM: {
            "videos_per_month": 60,
            "books_upload_limit": 100,
            "video_books_limit": 50,
            "chapters_per_book": "unlimited",
            "max_video_duration": 3600,  # 60 minutes
            "max_resolution": "4K",
            "watermark": False,
            "priority": 3,
            "support": "priority_email",
            "api_access": True,
            "model_selection": True,
            "voice_cloning": True,
            "price_monthly": 199,
            "display_name": "Premium",
            "description": "For power users",
        },
        SubscriptionTier.PROFESSIONAL: {
            "videos_per_month": 150,
            "books_upload_limit": "unlimited",
            "video_books_limit": "unlimited",
            "chapters_per_book": "unlimited",
            "max_video_duration": 5400,  # 90 minutes
            "max_resolution": "4K",
            "watermark": False,
            "priority": 4,
            "support": "dedicated_rep",
            "api_access": True,
            "model_selection": True,
            "voice_cloning": True,
            "price_monthly": 499,
            "display_name": "Professional",
            "description": "For studios & agencies",
        },
        SubscriptionTier.ENTERPRISE: {
            "videos_per_month": "unlimited",
            "books_upload_limit": "unlimited",
            "video_books_limit": "unlimited",
            "chapters_per_book": "unlimited",
            "max_video_duration": "unlimited",
            "max_resolution": "8K",
            "watermark": False,
            "priority": 5,
            "support": "24/7_dedicated",
            "api_access": True,
            "model_selection": True,
            "voice_cloning": True,
            "price_monthly": 0,  # Custom pricing
            "display_name": "Enterprise",
            "description": "For large organizations",
        },
    }

    def get_all_tiers(self) -> List[Dict[str, Any]]:
        """
        Get all available subscription tiers with full details
        """
        tiers = []
        display_order = 0
        for tier, limits in self.TIER_LIMITS.items():
            feature_highlights = []

            # Build feature highlights for display
            if limits.get("videos_per_month"):
                feature_highlights.append(f"{limits['videos_per_month']} videos/month")
            if limits.get("books_upload_limit"):
                feature_highlights.append(
                    f"{limits['books_upload_limit']} book uploads"
                )
            if limits.get("video_books_limit"):
                feature_highlights.append(
                    f"Videos for {limits['video_books_limit']} books"
                )
            if limits.get("max_resolution"):
                feature_highlights.append(f"{limits['max_resolution']} resolution")
            if not limits.get("watermark"):
                feature_highlights.append("No watermark")
            if limits.get("voice_cloning"):
                feature_highlights.append("Voice cloning")
            if limits.get("model_selection"):
                feature_highlights.append("AI model selection")
            if limits.get("priority", 0) >= 2:
                feature_highlights.append("Priority processing")

            tiers.append(
                {
                    "tier": tier.value,
                    "display_name": limits.get("display_name", tier.value.title()),
                    "description": limits.get("description", ""),
                    "monthly_price": limits["price_monthly"],
                    "video_quality": limits.get("max_resolution", "720p"),
                    "has_watermark": limits.get("watermark", True),
                    "max_video_duration": limits.get("max_video_duration"),
                    "monthly_video_limit": limits.get("videos_per_month", 0),
                    "priority_processing": limits.get("priority", 0) >= 2,
                    "features": limits,
                    "feature_highlights": feature_highlights,
                    "display_order": display_order,
                    "is_active": True,
                }
            )
            display_order += 1
        return tiers

    def __init__(self, session: AsyncSession):
        self.session = session
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def get_user_tier(self, user_id: uuid.UUID) -> SubscriptionTier:
        """
        Get user's current subscription tier
        """
        try:
            logger.info(f"Getting user tier for user_id: {user_id}")

            # Check database for active user subscription
            statement = select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            result = await self.session.exec(statement)
            subscription = result.first()

            if subscription:
                logger.info(
                    f"User {user_id} has active {subscription.tier} subscription"
                )
                return subscription.tier
            else:
                # Default to free tier
                logger.info(
                    f"User {user_id} has no active subscription, defaulting to FREE tier"
                )
                return SubscriptionTier.FREE
        except Exception as e:
            logger.error(f"Error getting user tier for {user_id}: {e}")
            return SubscriptionTier.FREE

    async def get_subscription(self, user_id: uuid.UUID) -> Optional[UserSubscription]:
        """
        Get user's current subscription
        """
        statement = select(UserSubscription).where(UserSubscription.user_id == user_id)
        result = await self.session.exec(statement)
        return result.first()

    async def cancel_subscription(
        self, user_id: uuid.UUID, cancel_at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel user's subscription
        """
        subscription = await self.get_subscription(user_id)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found")

        # Cancel via Stripe
        cancel_result = await stripe_service.cancel_subscription(
            subscription.stripe_subscription_id
        )

        # Update local database
        subscription.cancel_at_period_end = cancel_result["cancel_at_period_end"]
        subscription.updated_at = datetime.now()
        if cancel_at_period_end:
            # If cancelling at period end, we don't set cancelled_at yet?
            # Or maybe we do? The original code sets it if cancel_at_period_end is True?
            # Original: if cancel_data.cancel_at_period_end: update_data["cancelled_at"] = "now()"
            # Wait, usually cancelled_at is when it's fully cancelled.
            # But let's follow original logic if possible, or standard logic.
            # Standard: cancel_at_period_end=True means it will cancel later.
            pass
        else:
            # Immediate cancellation
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.now()

        self.session.add(subscription)

        # Log history
        history = SubscriptionHistory(
            user_id=user_id,
            event_type="cancelled",
            from_status=subscription.status,
            to_status="cancelled" if not cancel_at_period_end else subscription.status,
            metadata={"reason": "User requested cancellation"},
        )
        self.session.add(history)

        await self.session.commit()
        await self.session.refresh(subscription)

        return {
            "subscription_id": subscription.id,
            "status": cancel_result["status"],
            "cancel_at_period_end": cancel_result["cancel_at_period_end"],
            "current_period_end": cancel_result.get("current_period_end"),
        }

    async def reactivate_subscription(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Reactivate a cancelled subscription
        """
        subscription = await self.get_subscription(user_id)
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No subscription to reactivate")

        # Reactivate via Stripe
        reactivate_result = await stripe_service.reactivate_subscription(
            subscription.stripe_subscription_id
        )

        # Update local database
        old_status = subscription.status
        subscription.cancel_at_period_end = False
        subscription.cancelled_at = None
        subscription.updated_at = datetime.now()
        subscription.status = (
            SubscriptionStatus.ACTIVE
        )  # Assuming reactivation makes it active

        self.session.add(subscription)

        # Log history
        history = SubscriptionHistory(
            user_id=user_id,
            event_type="reactivated",
            from_status=old_status,
            to_status=reactivate_result["status"],
            metadata={"reason": "User reactivated subscription"},
        )
        self.session.add(history)

        await self.session.commit()

        return {"message": "Subscription reactivated successfully"}

    async def check_usage_limits(
        self, user_id: uuid.UUID, resource_type: str = "video"
    ) -> Dict[str, Any]:
        """
        Check if user has exceeded their usage limits
        """
        tier = await self.get_user_tier(user_id)
        limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS[SubscriptionTier.FREE])

        # Get current month's usage
        current_period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)

        statement = select(UsageLog).where(
            UsageLog.user_id == user_id,
            UsageLog.resource_type == resource_type,
            UsageLog.created_at >= current_period_start,
        )
        result = await self.session.exec(statement)
        usage_logs = result.all()

        usage_count = len(usage_logs)

        # Use correct limit key based on resource type
        limit_key = f"{resource_type}s_per_month"  # e.g., "videos_per_month", "images_per_month"
        limit_count = limits.get(limit_key, limits.get("videos_per_month", 0))

        is_unlimited = limit_count == "unlimited"
        can_generate = True
        remaining = "unlimited"

        if not is_unlimited:
            can_generate = usage_count < limit_count
            remaining = max(0, limit_count - usage_count)

        return {
            "tier": tier.value,
            "limits": limits,
            "current_usage": {
                resource_type: usage_count,
                "period_start": current_period_start.isoformat(),
                "period_end": (current_period_start + timedelta(days=30)).isoformat(),
            },
            "can_generate": can_generate,
            f"{resource_type}s_remaining": remaining,
        }

    async def create_checkout_session(
        self, user_id: str, tier: SubscriptionTier, success_url: str, cancel_url: str
    ) -> Dict[str, Any]:
        """
        Create Stripe checkout session for subscription
        """
        try:
            # Get price ID for tier (you need to create these in Stripe Dashboard)
            price_ids = {
                SubscriptionTier.FREE: settings.STRIPE_FREE_PRICE_ID,
                SubscriptionTier.BASIC: settings.STRIPE_BASIC_PRICE_ID,
                SubscriptionTier.PRO: settings.STRIPE_STANDARD_PRICE_ID,
                SubscriptionTier.PREMIUM: settings.STRIPE_PREMIUM_PRICE_ID,
                SubscriptionTier.PROFESSIONAL: settings.STRIPE_PROFESSIONAL_PRICE_ID,
                SubscriptionTier.ENTERPRISE: settings.STRIPE_ENTERPRISE_PRICE_ID,
            }

            price_id = price_ids.get(tier)
            if not price_id:
                raise ValueError(f"No price ID configured for tier: {tier.value}")

            # Create Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"user_id": str(user_id), "tier": tier.value},
            )

            return {"checkout_url": session.url, "session_id": session.id}

        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise

    async def handle_subscription_webhook(
        self, event_type: str, event_data: Dict[str, Any]
    ):
        """
        Handle Stripe webhook events for subscriptions
        """
        if event_type == "checkout.session.completed":
            session_data = event_data["object"]
            user_id = uuid.UUID(session_data["metadata"]["user_id"])
            tier_str = session_data["metadata"]["tier"]
            tier = SubscriptionTier(tier_str)

            # Get tier limits for this tier
            tier_limits = self.TIER_LIMITS.get(
                tier, self.TIER_LIMITS[SubscriptionTier.FREE]
            )

            # Update or create user subscription in database
            statement = select(UserSubscription).where(
                UserSubscription.user_id == user_id
            )
            result = await self.session.exec(statement)
            subscription = result.first()

            if not subscription:
                subscription = UserSubscription(
                    user_id=user_id,
                    tier=tier,
                    status=SubscriptionStatus.ACTIVE,
                    stripe_customer_id=session_data["customer"],
                    stripe_subscription_id=session_data["subscription"],
                    monthly_video_limit=tier_limits["videos_per_month"],
                    video_quality=tier_limits.get("max_resolution", "720p"),
                    has_watermark=tier_limits.get("watermark", False),
                    current_period_start=datetime.now(),
                    current_period_end=datetime.now() + timedelta(days=30),
                )
                self.session.add(subscription)
            else:
                subscription.tier = tier
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.stripe_customer_id = session_data["customer"]
                subscription.stripe_subscription_id = session_data["subscription"]
                subscription.monthly_video_limit = tier_limits["videos_per_month"]
                subscription.video_quality = tier_limits.get("max_resolution", "720p")
                subscription.has_watermark = tier_limits.get("watermark", False)
                subscription.current_period_start = datetime.now()
                subscription.current_period_end = datetime.now() + timedelta(days=30)
                self.session.add(subscription)

            await self.session.commit()
            logger.info(f"Subscription activated for user {user_id}: {tier}")

        elif event_type == "customer.subscription.deleted":
            subscription_data = event_data["object"]

            # Downgrade to free tier
            statement = select(UserSubscription).where(
                UserSubscription.stripe_subscription_id == subscription_data["id"]
            )
            result = await self.session.exec(statement)
            subscription = result.first()

            if subscription:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.tier = SubscriptionTier.FREE
                self.session.add(subscription)
                await self.session.commit()
                logger.info(f"Subscription cancelled: {subscription_data['id']}")

    async def record_usage(
        self,
        user_id: uuid.UUID,
        resource_type: str,
        cost_usd: float = 0.0,
        metadata: Dict[str, Any] = None,
    ):
        """
        Record usage for billing and limits tracking
        """
        try:
            # Get user's active subscription
            statement = select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
            )
            result = await self.session.exec(statement)
            subscription = result.first()

            subscription_id = subscription.id if subscription else None

            usage_log = UsageLog(
                user_id=user_id,
                subscription_id=subscription_id,
                resource_type=resource_type,
                usage_count=1,  # Default to 1 unit
                meta=metadata or {},  # Using 'meta' as per new model
            )
            self.session.add(usage_log)
            await self.session.commit()

            logger.info(
                f"Usage recorded for user {user_id}: {resource_type}, cost: ${cost_usd}"
            )

        except Exception as e:
            logger.error(f"Error recording usage: {str(e)}")

    async def can_user_generate_video(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Check if user can generate a video based on their subscription limits
        """
        usage_check = await self.check_usage_limits(user_id, "video")

        return {
            "can_generate": usage_check["can_generate"],
            "tier": usage_check["tier"],
            "videos_used": usage_check["current_usage"]["videos"],
            "videos_limit": usage_check["limits"].get("videos_per_month"),
            "videos_remaining": usage_check["videos_remaining"],
        }
