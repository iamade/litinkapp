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
            "max_video_duration": 60,  # seconds
            "max_resolution": "720p",
            "watermark": True,
            "priority": 0,
            "support": "community",
            "api_access": False,
            "price_monthly": 0,
        },
        SubscriptionTier.BASIC: {
            "videos_per_month": 10,
            "max_video_duration": 180,
            "max_resolution": "720p",
            "watermark": False,
            "priority": 1,
            "support": "email",
            "api_access": False,
            "price_monthly": 19,
        },
        SubscriptionTier.PRO: {
            "videos_per_month": 30,
            "max_video_duration": 300,
            "max_resolution": "1080p",
            "watermark": False,
            "priority": 2,
            "support": "priority_email",
            "api_access": False,
            "voice_cloning": True,
            "price_monthly": 49,
        },
        # Add other tiers as needed matching the Enum
    }

    def get_all_tiers(self) -> List[Dict[str, Any]]:
        """
        Get all available subscription tiers
        """
        tiers = []
        for tier, limits in self.TIER_LIMITS.items():
            tiers.append(
                {
                    "tier": tier.value,
                    "name": tier.value.title(),
                    "price_monthly": limits["price_monthly"],
                    "features": limits,
                }
            )
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
        limit_count = limits.get("videos_per_month", 0)

        is_unlimited = limit_count == "unlimited"
        can_generate = True
        videos_remaining = "unlimited"

        if not is_unlimited:
            can_generate = usage_count < limit_count
            videos_remaining = max(0, limit_count - usage_count)

        return {
            "tier": tier.value,
            "limits": limits,
            "current_usage": {
                "videos": usage_count,
                "period_start": current_period_start.isoformat(),
                "period_end": (current_period_start + timedelta(days=30)).isoformat(),
            },
            "can_generate": can_generate,
            "videos_remaining": videos_remaining,
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
                SubscriptionTier.BASIC: settings.STRIPE_BASIC_PRICE_ID,
                SubscriptionTier.PRO: settings.STRIPE_PRO_PRICE_ID,
                # Add other tiers
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
                    current_period_start=datetime.now(),
                    current_period_end=datetime.now() + timedelta(days=30),
                )
                self.session.add(subscription)
            else:
                subscription.tier = tier
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.stripe_customer_id = session_data["customer"]
                subscription.stripe_subscription_id = session_data["subscription"]
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
